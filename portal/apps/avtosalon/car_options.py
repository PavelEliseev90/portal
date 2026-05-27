"""
Опции автомобиля (AvtohubOptions) для карточки price_edit.
"""
from avtosalon.models import (
    AvtohubComplectations,
    AvtohubModifications,
    AvtohubOptions,
    CarsOrganizationEquipment,
)


def get_avtohub_modification(car):
    """AvtohubModifications по AutoruModification.idSite / idSiteTech."""
    mod = car.modification_autoru
    if not mod:
        return None
    for autoru_id in (mod.idSite, mod.idSiteTech):
        if autoru_id:
            ah = AvtohubModifications.objects.filter(autoruId=autoru_id).first()
            if ah:
                return ah
    return None


def get_avtohub_complectation(car, avtohub_mod=None):
    """AvtohubComplectations по AutoruComplectation.idSite."""
    comp = car.complectation_autoru
    if not comp or not comp.idSite:
        return None
    qs = AvtohubComplectations.objects.filter(autoruId=comp.idSite)
    if avtohub_mod:
        qs = qs.filter(modificationId=avtohub_mod.id_avtohub)
    return qs.first()


def get_car_selected_option_ids(car):
    return set(
        CarsOrganizationEquipment.objects.filter(car=car).values_list('option_id', flat=True)
    )


def get_complectation_option_ids(avtohub_comp):
    if not avtohub_comp:
        return set()
    return set(avtohub_comp.equipment.values_list('id', flat=True))


def get_modification_option_ids(avtohub_mod):
    if not avtohub_mod:
        return set()
    return set(
        AvtohubOptions.objects.filter(
            avtohubcomplectations__modificationId=avtohub_mod.id_avtohub,
        ).distinct().values_list('id', flat=True)
    )


def get_options_queryset(avtohub_mod=None):
    qs = AvtohubOptions.objects.select_related('groupId').order_by(
        'groupId__sortOrder', 'groupId__name', 'sortOrder', 'name',
    )
    if avtohub_mod:
        qs = qs.filter(
            avtohubcomplectations__modificationId=avtohub_mod.id_avtohub,
        ).distinct()
    return qs


def build_option_groups(options_qs, selected_ids):
    selected_ids = set(selected_ids or [])
    groups_dict = {}
    for opt in options_qs:
        group = opt.groupId
        group_key = group.id if group else 0
        if group_key not in groups_dict:
            groups_dict[group_key] = {
                'id': group.id if group else None,
                'name': group.name if group else 'Без группы',
                'sort_order': group.sortOrder if group else 999,
                'options': [],
            }
        groups_dict[group_key]['options'].append({
            'id': opt.id,
            'name': opt.name or '',
            'key_equipment': opt.keyEquipment,
            'checked': opt.id in selected_ids,
        })
    return sorted(
        groups_dict.values(),
        key=lambda g: (g['sort_order'], g['name'] or ''),
    )


def save_car_equipment(car, option_ids, user=None):
    option_ids = {int(x) for x in option_ids if str(x).isdigit()}
    CarsOrganizationEquipment.objects.filter(car=car).exclude(option_id__in=option_ids).delete()
    existing = set(
        CarsOrganizationEquipment.objects.filter(car=car).values_list('option_id', flat=True)
    )
    to_create = [
        CarsOrganizationEquipment(car=car, option_id=oid, user=user)
        for oid in option_ids
        if oid not in existing
    ]
    if to_create:
        CarsOrganizationEquipment.objects.bulk_create(to_create)


def build_car_options_context(car):
    """Контекст для вкладки «Опции»."""
    avtohub_mod = get_avtohub_modification(car)
    avtohub_comp = get_avtohub_complectation(car, avtohub_mod)

    selected_ids = get_car_selected_option_ids(car)
    suggested_complectation_ids = get_complectation_option_ids(avtohub_comp)
    suggested_modification_ids = get_modification_option_ids(avtohub_mod)

    auto_prefill_applied = False
    if not selected_ids and suggested_complectation_ids:
        selected_ids = set(suggested_complectation_ids)
        auto_prefill_applied = True

    options_qs = get_options_queryset(avtohub_mod)
    if not options_qs.exists():
        options_qs = get_options_queryset(None)

    groups = build_option_groups(options_qs, selected_ids)
    total_options = sum(len(g['options']) for g in groups)
    selected_count = sum(1 for g in groups for o in g['options'] if o['checked'])

    return {
        'options_groups': groups,
        'options_selected_count': selected_count,
        'options_total_count': total_options,
        'avtohub_modification': avtohub_mod,
        'avtohub_complectation': avtohub_comp,
        'has_complectation_autoru': bool(car.complectation_autoru_id),
        'complectation_autoru_name': (
            car.complectation_autoru.name if car.complectation_autoru_id else ''
        ),
        'suggested_complectation_ids': list(suggested_complectation_ids),
        'suggested_modification_ids': list(suggested_modification_ids),
        'auto_prefill_applied': auto_prefill_applied,
        'can_prefill_complectation': bool(suggested_complectation_ids),
        'can_prefill_modification': bool(suggested_modification_ids),
    }
