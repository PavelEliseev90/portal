"""
Явная передача снимка плана оценки в car_preparation.

Контракт:
  EstimationPlanSnapshot
    → пакеты EstimationPlanPackage (единица согласования)
    → CarPreparation
    → CarPreparationPackage (группа на документе подготовки)
    → CarPreparationWorkItem для WORK (is_confirmed=False, в составе пакета)
    → PlannedMaterialConsumption для MATERIAL
    → PART/SERVICE остаются в snapshot до подбора/ЗН

Не вызывается из legacy-расчёта. Нет сигналов. Только явный handoff.
Не создаёт WorkOrder и CarPreparationWorkSchedule.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from car_preparation.models import (
    CarPreparation,
    CarPreparationPackage,
    CarPreparationWorkItem,
    PlannedMaterialConsumption,
    RefCarPreparationStatus,
)
from refs.models import RefCarsOrganization

from .models import (
    EstimationPlanLine,
    EstimationPlanPackage,
    EstimationPlanSnapshot,
    EstimationPreparationTransfer,
)


class TransferError(Exception):
    """Ошибка передачи плана в подготовку."""


def _hours_to_minutes(norm_hours) -> int:
    try:
        return max(0, int(round(float(norm_hours or 0) * 60)))
    except (TypeError, ValueError):
        return 0


def resolve_car_for_snapshot(snapshot: EstimationPlanSnapshot) -> RefCarsOrganization:
    if snapshot.car_id:
        return snapshot.car
    vin = (snapshot.vin or '').strip()
    if not vin and snapshot.estimation_id:
        vin = (getattr(snapshot.estimation, 'vin', None) or '').strip()
    if not vin:
        raise TransferError('Не удалось определить VIN для передачи в подготовку.')
    car = (
        RefCarsOrganization.objects.filter(vin__iexact=vin)
        .order_by('-id')
        .first()
    )
    if car is None:
        raise TransferError(f'Автомобиль склада с VIN {vin} не найден.')
    return car


def _default_preparation_status():
    return (
        RefCarPreparationStatus.objects.filter(code='new').first()
        or RefCarPreparationStatus.objects.order_by('id').first()
    )


def _get_or_create_prep_package(
    preparation: CarPreparation,
    plan_package: EstimationPlanPackage,
) -> tuple[CarPreparationPackage, bool]:
    existing = None
    if getattr(plan_package, 'preparation_package_id', None):
        existing = plan_package.preparation_package
    if existing is None and plan_package.code:
        existing = (
            CarPreparationPackage.objects.filter(
                preparation=preparation,
                code=plan_package.code,
            )
            .order_by('id')
            .first()
        )
    if existing is None and plan_package.name:
        existing = (
            CarPreparationPackage.objects.filter(
                preparation=preparation,
                name=plan_package.name,
                source_package_id=plan_package.work_package_id,
            )
            .order_by('id')
            .first()
        )

    if existing is not None:
        existing.route_type = plan_package.route_type or existing.route_type
        existing.repair_zone_id = plan_package.repair_zone_id or existing.repair_zone_id
        existing.planned_time = _hours_to_minutes(plan_package.total_norm_hours)
        existing.cost = Decimal(plan_package.total_cost or 0)
        existing.save()
        return existing, False

    created = CarPreparationPackage.objects.create(
        preparation=preparation,
        source_package_id=plan_package.work_package_id,
        code=plan_package.code or getattr(plan_package.work_package, 'code', '') or '',
        name=plan_package.name,
        route_type=plan_package.route_type or CarPreparationPackage.ROUTE_IN_HOUSE,
        repair_zone_id=plan_package.repair_zone_id,
        status='pending',
        is_confirmed=False,
        planned_time=_hours_to_minutes(plan_package.total_norm_hours),
        cost=Decimal(plan_package.total_cost or 0),
        sort_order=plan_package.sort_order or 0,
        comment=f'Из плана оценки #{plan_package.snapshot.estimation_id}',
    )
    return created, True


@transaction.atomic
def transfer_snapshot_to_preparation(
    snapshot: EstimationPlanSnapshot,
    *,
    car: RefCarsOrganization | None = None,
    allow_draft: bool = False,
) -> EstimationPreparationTransfer:
    """
    Идемпотентно переносит согласованные пакеты в документ подготовки.

    - создаёт CarPreparationPackage на каждый EstimationPlanPackage;
    - WORK → work_item внутри пакета, is_confirmed=False;
    - MATERIAL → PlannedMaterialConsumption;
    - PART/SERVICE не раскрываются в work_items.
    """
    snapshot = (
        EstimationPlanSnapshot.objects.select_related('estimation', 'car', 'unit')
        .prefetch_related('packages__lines', 'lines')
        .get(pk=snapshot.pk)
    )

    if snapshot.status == EstimationPlanSnapshot.STATUS_SUPERSEDED:
        raise TransferError('Нельзя передать заменённый снимок плана.')
    if snapshot.status == EstimationPlanSnapshot.STATUS_DRAFT and not allow_draft:
        raise TransferError('Снимок должен быть согласован перед передачей.')

    try:
        car = car or resolve_car_for_snapshot(snapshot)
    except TransferError as exc:
        transfer = EstimationPreparationTransfer.objects.create(
            snapshot=snapshot,
            status=EstimationPreparationTransfer.STATUS_FAILED,
            error_message=str(exc),
        )
        raise

    preparation = snapshot.preparation
    created_prep = False
    if preparation is None:
        preparation = (
            CarPreparation.objects.filter(car=car)
            .exclude(status__is_final=True)
            .order_by('-id')
            .first()
        )
    if preparation is None:
        preparation = CarPreparation.objects.create(
            car=car,
            unit=snapshot.unit or getattr(car, 'unit', None),
            status=_default_preparation_status(),
            comment_initial=(
                f'Создано из снимка плана оценки #{snapshot.estimation_id} '
                f'(rev {snapshot.revision}).'
            ),
        )
        created_prep = True
    elif snapshot.unit_id and preparation.unit_id is None:
        preparation.unit = snapshot.unit
        preparation.save(update_fields=['unit'])

    plan_packages = list(snapshot.packages.all())
    # Строки без пакета — «плоский» fallback
    orphan_lines = [line for line in snapshot.lines.all() if line.plan_package_id is None]

    created_packages = 0
    created_work_items = 0
    updated_work_items = 0
    created_materials = 0
    skipped_lines = 0
    details = {
        'created_preparation': created_prep,
        'packages': [],
        'works': [],
        'materials': [],
        'skipped': [],
        'deferred_parts_services': [],
    }

    def process_lines(lines, prep_package: CarPreparationPackage | None):
        nonlocal created_work_items, updated_work_items, created_materials, skipped_lines
        coverage_to_work_item: dict[str, CarPreparationWorkItem] = {}

        work_lines = [line for line in lines if line.line_type == EstimationPlanLine.LINE_WORK]
        material_lines = [line for line in lines if line.line_type == EstimationPlanLine.LINE_MATERIAL]
        other_lines = [
            line for line in lines
            if line.line_type in (EstimationPlanLine.LINE_PART, EstimationPlanLine.LINE_SERVICE)
        ]

        for line in work_lines:
            if not line.work_id:
                skipped_lines += 1
                details['skipped'].append({'line_id': line.id, 'reason': 'work_missing'})
                continue

            planned_minutes = line.planned_minutes or _hours_to_minutes(line.norm_hours)
            cost = Decimal(line.cost or 0)
            work_item = line.preparation_work_item
            if work_item is None:
                qs = CarPreparationWorkItem.objects.filter(
                    preparation=preparation,
                    work_id=line.work_id,
                )
                if prep_package is not None:
                    qs = qs.filter(preparation_package=prep_package)
                work_item = qs.order_by('id').first()

            if work_item is None:
                work_item = CarPreparationWorkItem.objects.create(
                    preparation=preparation,
                    preparation_package=prep_package,
                    work_id=line.work_id,
                    status='pending',
                    is_confirmed=False,
                    planned_time=planned_minutes,
                    cost=cost,
                    comment=(
                        f'Из пакета «{prep_package.name}»; '
                        if prep_package else ''
                    ) + f'оценка #{snapshot.estimation_id}; {line.section}',
                )
                created_work_items += 1
                details['works'].append({
                    'line_id': line.id,
                    'action': 'created',
                    'work_item_id': work_item.id,
                    'package_id': getattr(prep_package, 'id', None),
                })
            elif work_item.status == 'pending':
                work_item.planned_time = planned_minutes
                work_item.cost = cost
                if prep_package and work_item.preparation_package_id is None:
                    work_item.preparation_package = prep_package
                work_item.is_confirmed = False
                work_item.save()
                updated_work_items += 1
                details['works'].append({
                    'line_id': line.id,
                    'action': 'updated',
                    'work_item_id': work_item.id,
                })
            else:
                skipped_lines += 1
                details['skipped'].append({
                    'line_id': line.id,
                    'reason': f'work_item_status={work_item.status}',
                    'work_item_id': work_item.id,
                })

            if line.preparation_work_item_id != work_item.id:
                line.preparation_work_item = work_item
                line.save(update_fields=['preparation_work_item', 'updated_at'])
            if line.coverage_key:
                coverage_to_work_item[line.coverage_key] = work_item

        for line in material_lines:
            if not line.material_id:
                skipped_lines += 1
                details['skipped'].append({'line_id': line.id, 'reason': 'material_missing'})
                continue
            parent = coverage_to_work_item.get(line.parent_coverage_key) if line.parent_coverage_key else None
            if parent is None and line.preparation_work_item_id:
                parent = line.preparation_work_item
            if parent is None:
                skipped_lines += 1
                details['skipped'].append({
                    'line_id': line.id,
                    'reason': 'material_without_parent_work',
                })
                continue

            planned, created = PlannedMaterialConsumption.objects.get_or_create(
                work_item=parent,
                material_id=line.material_id,
                defaults={'qty_planned': Decimal(line.quantity or 0)},
            )
            if created:
                created_materials += 1
                details['materials'].append({
                    'line_id': line.id,
                    'action': 'created',
                    'planned_id': planned.id,
                })
            elif parent.status == 'pending':
                planned.qty_planned = Decimal(line.quantity or 0)
                planned.save(update_fields=['qty_planned'])
            else:
                skipped_lines += 1
                details['skipped'].append({
                    'line_id': line.id,
                    'reason': 'parent_work_not_pending',
                })

            if line.preparation_work_item_id != parent.id:
                line.preparation_work_item = parent
                line.save(update_fields=['preparation_work_item', 'updated_at'])

        for line in other_lines:
            details['deferred_parts_services'].append({
                'line_id': line.id,
                'line_type': line.line_type,
                'name': line.name,
                'package_id': getattr(prep_package, 'id', None),
            })

    if plan_packages:
        for plan_package in plan_packages:
            prep_package, was_created = _get_or_create_prep_package(preparation, plan_package)
            if was_created:
                created_packages += 1
            details['packages'].append({
                'plan_package_id': plan_package.id,
                'preparation_package_id': prep_package.id,
                'action': 'created' if was_created else 'updated',
            })
            if (
                hasattr(plan_package, 'preparation_package_id')
                and plan_package.preparation_package_id != prep_package.id
            ):
                plan_package.preparation_package = prep_package
                plan_package.save(update_fields=['preparation_package', 'updated_at'])
            process_lines(list(plan_package.lines.all()), prep_package)
    else:
        process_lines(orphan_lines or list(snapshot.lines.all()), None)

    if orphan_lines and plan_packages:
        process_lines(orphan_lines, None)

    if created_packages == 0 and created_work_items == 0 and updated_work_items == 0 and created_materials == 0:
        status = EstimationPreparationTransfer.STATUS_FAILED
        error_message = 'Не удалось создать или обновить пакеты/работы подготовки.'
        if plan_packages or snapshot.lines.exists():
            status = EstimationPreparationTransfer.STATUS_PARTIAL
            error_message = 'Пакеты/работы не обновлены (возможно, уже в исполнении).'
    elif skipped_lines > 0 or details['deferred_parts_services']:
        status = EstimationPreparationTransfer.STATUS_PARTIAL
        error_message = ''
    else:
        status = EstimationPreparationTransfer.STATUS_SUCCESS
        error_message = ''

    transfer = EstimationPreparationTransfer.objects.create(
        snapshot=snapshot,
        preparation=preparation,
        status=status,
        created_packages=created_packages,
        created_work_items=created_work_items,
        updated_work_items=updated_work_items,
        created_materials=created_materials,
        skipped_lines=skipped_lines + len(details['deferred_parts_services']),
        error_message=error_message,
        details=details,
    )

    snapshot.car = car
    snapshot.preparation = preparation
    snapshot.vin = snapshot.vin or getattr(car, 'vin', '') or ''
    if status in (
        EstimationPreparationTransfer.STATUS_SUCCESS,
        EstimationPreparationTransfer.STATUS_PARTIAL,
    ):
        snapshot.status = EstimationPlanSnapshot.STATUS_TRANSFERRED
        snapshot.transferred_at = timezone.now()
    snapshot.save(
        update_fields=[
            'car',
            'preparation',
            'vin',
            'status',
            'transferred_at',
            'updated_at',
        ],
    )

    if status == EstimationPreparationTransfer.STATUS_FAILED:
        raise TransferError(error_message or 'Передача не выполнена.')

    try:
        from car_preparation.chat_utils import notify_preparation_created, post_prep_system_event
        if created_prep:
            notify_preparation_created(preparation)
        post_prep_system_event(
            preparation,
            (
                f'Передано из плана оценки #{snapshot.estimation_id}\n'
                f'Пакетов: {created_packages}, работ: {created_work_items}, '
                f'материалов: {created_materials}'
            ),
        )
    except Exception:
        pass

    return transfer
