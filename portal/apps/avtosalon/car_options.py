"""
Опции автомобиля (AvtohubOptions) для карточки price_edit.
"""
from collections import defaultdict

from django.db.models import Prefetch

from avtosalon.models import (
    AvtohubComplectations,
    AvtohubModifications,
    AvtohubOptions,
    CarsOrganizationEquipment,
)

_OPTIONS_ORDER = (
    'groupId__sortOrder',
    'groupId__name',
    'sortOrder',
    'name',
)

_OPTIONS_PREFETCH = Prefetch(
    'equipment',
    queryset=AvtohubOptions.objects.select_related('groupId').order_by(*_OPTIONS_ORDER),
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


def get_options_queryset(avtohub_mod=None, modification_id_avtohub=None):
    qs = AvtohubOptions.objects.select_related('groupId').order_by(
        'groupId__sortOrder', 'groupId__name', 'sortOrder', 'name',
    )
    mod_id = modification_id_avtohub
    if avtohub_mod:
        mod_id = avtohub_mod.id_avtohub
    if mod_id:
        qs = qs.filter(
            avtohubcomplectations__modificationId=mod_id,
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


def serialize_avtohub_option(opt):
    group = opt.groupId
    return {
        'id': opt.id,
        'id_avtohub': opt.id_avtohub,
        'name': opt.name or '',
        'sort_order': opt.sortOrder,
        'key_equipment': bool(opt.keyEquipment),
        'include': list(opt.include or []),
        'exclude': list(opt.exclude or []),
        'group': None if not group else {
            'id': group.id,
            'id_avtohub': group.id_avtohub,
            'name': group.name or '',
            'sort_order': group.sortOrder,
        },
    }


def build_avtohub_options_groups(options_qs):
    groups_dict = {}
    for opt in options_qs:
        group = opt.groupId
        group_key = group.id if group else 0
        if group_key not in groups_dict:
            groups_dict[group_key] = {
                'id': group.id if group else None,
                'id_avtohub': group.id_avtohub if group else None,
                'name': group.name if group else 'Без группы',
                'sort_order': group.sortOrder if group else 999,
                'options': [],
            }
        groups_dict[group_key]['options'].append(serialize_avtohub_option(opt))
    return sorted(
        groups_dict.values(),
        key=lambda g: (g['sort_order'], g['name'] or ''),
    )


def serialize_avtohub_modification_brief(mod):
    return {
        'id': mod.id,
        'id_avtohub': mod.id_avtohub,
        'autoru_id': mod.autoruId,
        'name': mod.name or '',
        'year_from': mod.yearFrom,
        'year_to': mod.yearTo,
        'is_active': bool(mod.isActive),
    }


def serialize_avtohub_complectation_brief(comp, groups=None):
    options_count = 0
    if groups is not None:
        options_count = sum(len(g['options']) for g in groups)
    return {
        'id': comp.id,
        'id_avtohub': comp.id_avtohub,
        'autoru_id': comp.autoruId,
        'name': comp.name or '',
        'modification_id': comp.modificationId,
        'is_active': bool(comp.isActive),
        'options_count': options_count,
        'groups': groups or [],
    }


def _complectation_option_groups(comp):
    return build_avtohub_options_groups(comp.equipment.all())


def build_avtohub_options_by_complectation_autoru(autoru_id):
    complectations = list(
        AvtohubComplectations.objects.filter(autoruId=autoru_id)
        .prefetch_related(_OPTIONS_PREFETCH)
        .order_by('name', 'id')
    )
    mod_ids = {comp.modificationId for comp in complectations if comp.modificationId}
    modifications_map = {
        mod.id_avtohub: serialize_avtohub_modification_brief(mod)
        for mod in AvtohubModifications.objects.filter(id_avtohub__in=mod_ids)
    }

    items = []
    total_options = 0
    for comp in complectations:
        groups = _complectation_option_groups(comp)
        opt_count = sum(len(g['options']) for g in groups)
        total_options += opt_count
        item = serialize_avtohub_complectation_brief(comp, groups)
        item['modification'] = modifications_map.get(comp.modificationId)
        items.append(item)

    return {
        'ok': True,
        'mode': 'complectation_autoru',
        'autoru_id': autoru_id,
        'complectations': items,
        'count': total_options,
    }


def build_avtohub_options_by_modification_autoru(autoru_id):
    modifications = list(
        AvtohubModifications.objects.filter(autoruId=autoru_id).order_by('name', 'id')
    )
    if not modifications:
        return {
            'ok': True,
            'mode': 'modification_autoru',
            'autoru_id': autoru_id,
            'modifications': [],
            'count': 0,
        }

    mod_id_avtohub_list = [mod.id_avtohub for mod in modifications]
    complectations = list(
        AvtohubComplectations.objects.filter(modificationId__in=mod_id_avtohub_list)
        .prefetch_related(_OPTIONS_PREFETCH)
        .order_by('name', 'id')
    )
    comp_by_mod = defaultdict(list)
    for comp in complectations:
        comp_by_mod[comp.modificationId].append(comp)

    result_modifications = []
    total_options = 0
    for mod in modifications:
        comps_data = []
        for comp in comp_by_mod.get(mod.id_avtohub, []):
            groups = _complectation_option_groups(comp)
            opt_count = sum(len(g['options']) for g in groups)
            total_options += opt_count
            comps_data.append(serialize_avtohub_complectation_brief(comp, groups))
        item = serialize_avtohub_modification_brief(mod)
        item['complectations'] = comps_data
        result_modifications.append(item)

    return {
        'ok': True,
        'mode': 'modification_autoru',
        'autoru_id': autoru_id,
        'modifications': result_modifications,
        'count': total_options,
    }


def get_avtohub_options_autoru_filter(request_get):
    comp_autoru = (
        request_get.get('complectation_autoru_id')
        or request_get.get('complectation_autoru')
        or ''
    ).strip()
    if comp_autoru.isdigit():
        return build_avtohub_options_by_complectation_autoru(int(comp_autoru))

    mod_autoru = (
        request_get.get('modification_autoru_id')
        or request_get.get('modification_autoru')
        or ''
    ).strip()
    if mod_autoru.isdigit():
        return build_avtohub_options_by_modification_autoru(int(mod_autoru))

    return None


def get_avtohub_options_queryset(request_get):
    """Фильтры GET-параметров для API справочника AvtohubOptions."""
    from refs.models import RefCarsOrganization

    qs = get_options_queryset(None)

    modification_id = (request_get.get('modification_id') or '').strip()
    if modification_id.isdigit():
        qs = get_options_queryset(modification_id_avtohub=int(modification_id))

    car_id = (request_get.get('car_id') or '').strip()
    if car_id.isdigit():
        car = RefCarsOrganization.objects.filter(pk=int(car_id)).first()
        if car:
            avtohub_mod = get_avtohub_modification(car)
            qs = get_options_queryset(avtohub_mod)
            if not qs.exists():
                qs = get_options_queryset(None)

    group_id = (request_get.get('group_id') or '').strip()
    if group_id.isdigit():
        qs = qs.filter(groupId_id=int(group_id))

    group_id_avtohub = (request_get.get('group_id_avtohub') or '').strip()
    if group_id_avtohub.isdigit():
        qs = qs.filter(groupId__id_avtohub=int(group_id_avtohub))

    id_avtohub = (request_get.get('id_avtohub') or '').strip()
    if id_avtohub.isdigit():
        qs = qs.filter(id_avtohub=int(id_avtohub))

    name = (request_get.get('name') or request_get.get('q') or '').strip()
    if name:
        qs = qs.filter(name__icontains=name)

    return qs


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
