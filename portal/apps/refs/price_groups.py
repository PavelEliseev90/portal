"""Ценовые группы: справочник, настройки ДЦ, выбор последней версии."""

from refs.models import RefGroupPrice, RefUnit

PRICE_GROUP_CODE_BY_RANGE = {
    200: '200',
    400: '400',
    700: '700',
    1200: '1200',
    2000: '2000',
    3000: '3000',
    5000: '5000',
    5001: '5001',
}

PRICE_GROUP_RANGES = [
    {'code': '200', 'name': '200', 'min_price_rub': 0, 'max_price_rub': 200_000, 'sort_order': 1, 'label_1c': '200'},
    {'code': '400', 'name': '400', 'min_price_rub': 200_000, 'max_price_rub': 400_000, 'sort_order': 2, 'label_1c': '400'},
    {'code': '700', 'name': '700', 'min_price_rub': 400_000, 'max_price_rub': 700_000, 'sort_order': 3, 'label_1c': '700'},
    {'code': '1200', 'name': '1 200', 'min_price_rub': 700_000, 'max_price_rub': 1_200_000, 'sort_order': 4, 'label_1c': '1 200'},
    {'code': '2000', 'name': '2 000', 'min_price_rub': 1_200_000, 'max_price_rub': 2_000_000, 'sort_order': 5, 'label_1c': '2 000'},
    {'code': '3000', 'name': '3 000', 'min_price_rub': 2_000_000, 'max_price_rub': 3_000_000, 'sort_order': 6, 'label_1c': '3 000'},
    {'code': '5000', 'name': '5 000', 'min_price_rub': 3_000_000, 'max_price_rub': 5_000_000, 'sort_order': 7, 'label_1c': '5 000'},
    {'code': '5001', 'name': '5 000+', 'min_price_rub': 5_000_000, 'max_price_rub': None, 'sort_order': 8, 'label_1c': '5 000+'},
]

# PK существующих записей refGroupPrice для первичного заполнения code (см. refresh_data / TradeInFunnel).
PRICE_GROUP_LEGACY_PKS = {
    '200': [7],
    '400': [1],
    '700': [6],
    '1200': [2, 9],
    '2000': [3, 10],
    '3000': [4],
    '5000': [5, 8, 11],
    '5001': [12],
}

# Поля RefUnit (кириллическая «с» в ratio_1с_*) → поля UnitPriceGroupSettings.
LEGACY_UNIT_FIELD_MAP = {
    'ratio_1c_test_price': 'ratio_1с_test_price',
    'ratio_1c_rdo': 'ratio_1с_rdo',
    'ratio_1c_kor': 'ratio_1с_kor',
    'ratio_1c_txt': 'ratio_1с_txt',
    'ratio_avtohub_test_price': 'ratio_avtohub_test_price',
    'ratio_avtohub_rdo': 'ratio_avtohub_rdo',
    'ratio_avtohub_kor': 'ratio_avtohub_kor',
    'ratio_avtohub_txt': 'ratio_avtohub_txt',
    'percent_txt': 'percent_txt',
    'percent_torg_txt': 'percent_torg_txt',
    'discount_tt': 'discount_tt',
    'discount_torg': 'discount_torg',
}


def get_price_group_by_code(code):
    if code is None:
        return None
    return RefGroupPrice.objects.filter(code=str(code), is_active=True).first()


def get_price_group_by_range(price_range):
    return get_price_group_by_code(str(price_range))


def get_active_price_groups():
    """Активные ценовые группы из справочника (источник для UI и сохранения)."""
    qs = (
        RefGroupPrice.objects
        .filter(is_active=True)
        .exclude(code='')
        .order_by('sort_order', 'code')
    )
    if qs.exists():
        return list(qs)
    seed_price_groups()
    return list(
        RefGroupPrice.objects
        .filter(is_active=True)
        .exclude(code='')
        .order_by('sort_order', 'code')
    )


def get_active_price_group_codes():
    return [group.code for group in get_active_price_groups()]


def resolve_price_group_by_amount(amount_rub):
    """Определить ЦГ по сумме в рублях (верхняя граница диапазона exclusive, как в eco/views)."""
    if amount_rub is None:
        return None
    amount = int(amount_rub)
    groups = get_active_price_groups()
    if groups:
        for group in groups:
            min_p = group.min_price_rub or 0
            max_p = group.max_price_rub
            if amount < min_p:
                continue
            if max_p is None or amount < max_p:
                return group
        for group in reversed(groups):
            if group.max_price_rub is None:
                return group
        return groups[-1]

    for item in PRICE_GROUP_RANGES:
        min_p = item['min_price_rub']
        max_p = item['max_price_rub']
        if amount < min_p:
            continue
        if max_p is None or amount < max_p:
            return get_price_group_by_code(item['code'])
    return get_price_group_by_code('5001')


def get_latest_unit_price_group_settings(unit, price_group):
    from refs.unit_price_group_settings import UnitPriceGroupSettings

    if unit is None or price_group is None:
        return None
    unit_id = unit.pk if hasattr(unit, 'pk') else unit
    price_group_id = price_group.pk if hasattr(price_group, 'pk') else price_group
    return (
        UnitPriceGroupSettings.objects
        .filter(unit_id=unit_id, price_group_id=price_group_id)
        .order_by('-created_at', '-id')
        .first()
    )


def get_latest_settings_map_for_unit(unit):
    """Последняя запись на каждую ЦГ для подразделения: code -> UnitPriceGroupSettings."""
    if unit is None:
        return {}

    result = {}
    for price_group in get_active_price_groups():
        row = get_latest_unit_price_group_settings(unit, price_group)
        if row is not None:
            result[price_group.code] = row
    return result


def seed_price_groups():
    """Заполнить code/пороги у RefGroupPrice (идемпотентно)."""
    for item in PRICE_GROUP_RANGES:
        canonical = None
        for pk in PRICE_GROUP_LEGACY_PKS.get(item['code'], []):
            group = RefGroupPrice.objects.filter(pk=pk).first()
            if not group:
                continue
            group.code = item['code']
            group.min_price_rub = item['min_price_rub']
            group.max_price_rub = item['max_price_rub']
            group.sort_order = item['sort_order']
            group.label_1c = item['label_1c']
            group.is_active = True
            if not group.name:
                group.name = item['name']
            group.save()
            if canonical is None:
                canonical = group
        if canonical is None:
            RefGroupPrice.objects.get_or_create(
                code=item['code'],
                defaults={
                    'name': item['name'],
                    'min_price_rub': item['min_price_rub'],
                    'max_price_rub': item['max_price_rub'],
                    'sort_order': item['sort_order'],
                    'label_1c': item['label_1c'],
                    'is_active': True,
                },
            )
