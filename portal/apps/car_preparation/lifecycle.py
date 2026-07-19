"""
Жизненный цикл подготовки: пакеты, материалы ЗН, переход на контроль качества.
"""
from __future__ import annotations

from decimal import Decimal

from django.utils import timezone


def sync_preparation_package_status(prep_package) -> str:
    """
    Обновляет status пакета по работам.
    Возвращает новый статус.
    """
    if not prep_package or prep_package.status == 'cancelled':
        return getattr(prep_package, 'status', 'pending')

    items = list(prep_package.work_items.all())
    if not items:
        return prep_package.status

    statuses = {wi.status for wi in items}
    if statuses and statuses <= {'completed', 'skipped'}:
        new_status = 'completed'
    elif 'in_progress' in statuses or 'completed' in statuses:
        new_status = 'in_progress'
    else:
        new_status = 'pending'

    if prep_package.status != new_status:
        prep_package.status = new_status
        prep_package.save(update_fields=['status', 'date_updated'])
    return new_status


def copy_planned_materials_to_work_order_item(wo_item, prep_item) -> int:
    """Копирует PlannedMaterialConsumption → WorkOrderItemMaterial. Возвращает число строк."""
    from .models import PlannedMaterialConsumption, WorkOrderItemMaterial

    if not wo_item or not prep_item:
        return 0
    created = 0
    planned = PlannedMaterialConsumption.objects.filter(
        work_item=prep_item,
    ).select_related('material')
    for row in planned:
        if not row.material_id:
            continue
        if wo_item.materials.filter(material_id=row.material_id).exists():
            continue
        qty = row.qty_planned or Decimal('0')
        if qty <= 0:
            continue
        WorkOrderItemMaterial.objects.create(
            work_order_item=wo_item,
            material_id=row.material_id,
            quantity=qty,
            unit_price=Decimal('0'),
            comment='Из плана пакета',
        )
        created += 1
    return created


def maybe_move_preparation_to_quality_check(preparation) -> bool:
    """
    Если все работы подготовки завершены — статус quality_check + уведомление инспектору/ответственному.
    Не трогает уже completed.
    """
    from .models import RefCarPreparationStatus
    from .notifications import create_quality_check_notification

    if not preparation:
        return False
    status_code = getattr(getattr(preparation, 'status', None), 'code', None)
    if status_code in ('completed', 'quality_check', 'cancelled'):
        return False

    items = preparation.work_items.all()
    if not items.exists():
        return False
    if items.exclude(status__in=['completed', 'skipped']).exists():
        return False

    qc_status = RefCarPreparationStatus.objects.filter(code='quality_check').first()
    if not qc_status:
        qc_status, _ = RefCarPreparationStatus.objects.get_or_create(
            code='quality_check',
            defaults={
                'name': 'Контроль качества',
                'color': '#f59e0b',
                'is_final': False,
                'can_edit': True,
            },
        )

    preparation.status = qc_status
    preparation.save(update_fields=['status', 'date_updated'])
    create_quality_check_notification(preparation)
    try:
        from .chat_utils import notify_quality_check
        notify_quality_check(preparation)
    except Exception:
        pass
    return True


def catalog_package_composition(catalog_package) -> dict:
    """Полный состав каталожного пакета для UI."""
    from estimation_engine.models import PreparationWorkPackageLine

    lines_out = []
    if not catalog_package:
        return {
            'lines': [],
            'estimation_reduction_amount': 0,
            'works': 0,
            'materials': 0,
            'parts': 0,
            'services': 0,
        }

    qs = (
        catalog_package.lines.filter(is_active=True)
        .select_related('work', 'material', 'part', 'service', 'service_offering')
        .order_by('sort_order', 'id')
    )
    counts = {'WORK': 0, 'MATERIAL': 0, 'PART': 0, 'SERVICE': 0}
    for line in qs:
        label = ''
        if line.line_type == PreparationWorkPackageLine.LINE_WORK and line.work_id:
            label = line.work.name
            counts['WORK'] += 1
        elif line.line_type == PreparationWorkPackageLine.LINE_MATERIAL and line.material_id:
            label = line.material.name
            counts['MATERIAL'] += 1
        elif line.line_type == PreparationWorkPackageLine.LINE_PART and line.part_id:
            label = line.part.name
            counts['PART'] += 1
        elif line.line_type == PreparationWorkPackageLine.LINE_SERVICE:
            if line.service_offering_id:
                label = f'{line.service_offering.service.name} / {line.service_offering.provider.name}'
            elif line.service_id:
                label = line.service.name
            counts['SERVICE'] += 1
        else:
            label = line.line_type
        lines_out.append({
            'line_type': line.line_type,
            'label': label,
            'quantity': str(line.quantity),
            'norm_hours': str(line.norm_hours),
            'unit_cost': str(line.unit_cost),
            'is_required': line.is_required,
        })

    reduction = getattr(catalog_package, 'estimation_reduction_amount', 0) or 0
    return {
        'lines': lines_out,
        'estimation_reduction_amount': str(reduction),
        'works': counts['WORK'],
        'materials': counts['MATERIAL'],
        'parts': counts['PART'],
        'services': counts['SERVICE'],
    }
