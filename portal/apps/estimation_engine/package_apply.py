"""
Применение пакета из каталога к документу CarPreparation.

Общий expand для ручного добавления на подготовке.
Передача из оценки остаётся в transfer.py (идёт через snapshot).
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
)

from .models import PreparationWorkPackage, PreparationWorkPackageLine


class PackageApplyError(Exception):
    """Ошибка применения пакета к подготовке."""


def _hours_to_minutes(norm_hours) -> int:
    try:
        return max(0, int(round(float(norm_hours or 0) * 60)))
    except (TypeError, ValueError):
        return 0


@transaction.atomic
def apply_catalog_package_to_preparation(
    preparation: CarPreparation,
    catalog_package: PreparationWorkPackage,
    *,
    confirm: bool = False,
    comment: str = '',
) -> tuple[CarPreparationPackage, dict]:
    """
    Создаёт экземпляр CarPreparationPackage и раскрывает строки каталога.

    WORK → CarPreparationWorkItem (в составе пакета)
    MATERIAL → PlannedMaterialConsumption (через parent_coverage_key)
    PART / SERVICE — не раскрываются в work_items (остаются в каталоге/оценке)

    Возвращает (экземпляр, stats).
    """
    if not catalog_package.is_active:
        raise PackageApplyError('Пакет неактивен.')
    if catalog_package.status == PreparationWorkPackage.STATUS_ARCHIVED:
        raise PackageApplyError('Пакет в архиве.')

    lines = list(
        catalog_package.lines.filter(is_active=True).select_related(
            'work', 'material', 'part', 'service', 'service_offering',
        ).order_by('sort_order', 'id')
    )
    work_lines = [ln for ln in lines if ln.line_type == PreparationWorkPackageLine.LINE_WORK]
    material_lines = [ln for ln in lines if ln.line_type == PreparationWorkPackageLine.LINE_MATERIAL]

    total_minutes = sum(
        _hours_to_minutes(ln.norm_hours) or (ln.work.estimated_time if ln.work_id else 0)
        for ln in work_lines
    )

    prep_package = CarPreparationPackage.objects.create(
        preparation=preparation,
        source_package=catalog_package,
        code=catalog_package.code or '',
        name=catalog_package.name,
        route_type=catalog_package.route_type or CarPreparationPackage.ROUTE_IN_HOUSE,
        repair_zone_id=catalog_package.default_repair_zone_id,
        status='pending',
        is_confirmed=confirm,
        planned_time=total_minutes,
        sort_order=catalog_package.sort_order or 0,
        comment=comment or f'Добавлен из каталога «{catalog_package.code}»',
    )

    created_works = 0
    skipped_works = 0
    created_materials = 0
    coverage_to_work_item: dict[str, CarPreparationWorkItem] = {}
    work_item_ids: list[int] = []

    for line in work_lines:
        if not line.work_id or not line.work or not line.work.is_active:
            skipped_works += 1
            continue

        planned_minutes = _hours_to_minutes(line.norm_hours) or (line.work.estimated_time or 0)
        work_item = CarPreparationWorkItem.objects.filter(
            preparation=preparation,
            work_id=line.work_id,
            preparation_package=prep_package,
        ).order_by('id').first()

        if work_item is None:
            # Та же работа уже есть вне этого пакета — не дублируем, привязываем если без пакета
            orphan = CarPreparationWorkItem.objects.filter(
                preparation=preparation,
                work_id=line.work_id,
                preparation_package__isnull=True,
                status='pending',
            ).order_by('id').first()
            if orphan is not None:
                work_item = orphan
                work_item.preparation_package = prep_package
                work_item.planned_time = work_item.planned_time or planned_minutes
                work_item.is_confirmed = confirm or work_item.is_confirmed
                if confirm:
                    work_item.confirmed_at = timezone.now()
                work_item.comment = (
                    work_item.comment or f'Пакет «{catalog_package.name}»'
                )
                work_item.save()
            else:
                existing_other = CarPreparationWorkItem.objects.filter(
                    preparation=preparation,
                    work_id=line.work_id,
                ).exclude(status__in=['rejected', 'skipped']).order_by('id').first()
                if existing_other is not None:
                    # Работа уже есть в другом пакете — не создаём дубль
                    skipped_works += 1
                    work_item = existing_other
                else:
                    work_item = CarPreparationWorkItem.objects.create(
                        preparation=preparation,
                        preparation_package=prep_package,
                        work_id=line.work_id,
                        status='pending',
                        is_confirmed=confirm,
                        confirmed_at=timezone.now() if confirm else None,
                        planned_time=planned_minutes,
                        comment=f'Пакет «{catalog_package.name}»',
                    )
                    created_works += 1

        if line.coverage_key:
            coverage_to_work_item[line.coverage_key] = work_item
        work_item_ids.append(work_item.id)

    for line in material_lines:
        if not line.material_id:
            continue
        parent = None
        if line.parent_coverage_key:
            parent = coverage_to_work_item.get(line.parent_coverage_key)
        if parent is None and work_item_ids:
            # fallback: первый work item пакета
            parent = CarPreparationWorkItem.objects.filter(
                preparation_package=prep_package,
            ).order_by('id').first()
        if parent is None:
            continue
        _, created = PlannedMaterialConsumption.objects.get_or_create(
            work_item=parent,
            material_id=line.material_id,
            defaults={'qty_planned': Decimal(line.quantity or 0)},
        )
        if created:
            created_materials += 1

    if confirm:
        prep_package.work_items.filter(status='pending').update(
            is_confirmed=True,
            confirmed_at=timezone.now(),
        )

    preparation.progress_percent = preparation.calculate_progress()
    preparation.save(update_fields=['progress_percent', 'date_updated'])

    stats = {
        'package_id': prep_package.id,
        'catalog_package_id': catalog_package.id,
        'created_works': created_works,
        'skipped_works': skipped_works,
        'created_materials': created_materials,
        'work_item_ids': work_item_ids,
        'confirmed': confirm,
    }
    return prep_package, stats


@transaction.atomic
def confirm_preparation_package(
    prep_package: CarPreparationPackage,
    *,
    confirmed: bool = True,
) -> CarPreparationPackage:
    """Подтверждает или снимает подтверждение с пакета и его работ."""
    prep_package.is_confirmed = confirmed
    prep_package.save(update_fields=['is_confirmed', 'date_updated'])
    qs = prep_package.work_items.filter(status='pending')
    if confirmed:
        qs.update(is_confirmed=True, confirmed_at=timezone.now())
    else:
        qs.update(is_confirmed=False, confirmed_at=None)
    prep = prep_package.preparation
    prep.progress_percent = prep.calculate_progress()
    prep.save(update_fields=['progress_percent', 'date_updated'])
    return prep_package
