"""Ценовые группы: справочник, настройки ДЦ, выбор последней версии."""

from __future__ import annotations

from typing import Optional

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

DISPLAY_BY_CODE = {row['code']: row['name'] for row in PRICE_GROUP_RANGES}
LABEL_1C_BY_CODE = {row['code']: row['label_1c'] for row in PRICE_GROUP_RANGES}
RANGE_BY_CODE = {row['code']: row for row in PRICE_GROUP_RANGES}

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

STAGE_CORRECTION_1C_ATTR = {
    1: 'correction_txt_1c_{code}',
    2: 'correction_rdo_1c_{code}',
    3: 'correction_kor_1c_{code}',
    4: 'correction_test_1c_{code}',
}

# Все известные варианты написания → каноническое отображение (name / label_1c).
ZG_ALIASES = {
    '200': '200',
    '400': '400',
    '700': '700',
    '1200': '1 200',
    '1 200': '1 200',
    '1 200 ': '1 200',
    '2000': '2 000',
    '2 000': '2 000',
    '3000': '3 000',
    '3 000': '3 000',
    '3 001+': '3 000',
    '3001+': '3 000',
    '5000': '5 000',
    '5 000': '5 000',
    '5001': '5 000+',
    '5 000+': '5 000+',
    '5000+': '5 000+',
}

ZG_ORDER = [row['name'] for row in PRICE_GROUP_RANGES] + ['Неопределена']


def _compact(value) -> str:
    return str(value or '').strip().replace(' ', '').lower()


def zg_display_from_price(price) -> str:
    """ЦГ (отображение) по сумме в рублях — пороги как в TradeInFunnel / аналитике."""
    try:
        value = float(price or 0)
    except (TypeError, ValueError):
        value = 0
    if value <= 0:
        return 'Неопределена'
    if value <= 200_000:
        return '200'
    if value <= 400_000:
        return '400'
    if value <= 700_000:
        return '700'
    if value <= 1_200_000:
        return '1 200'
    if value <= 2_000_000:
        return '2 000'
    if value <= 3_000_000:
        return '3 000'
    if value <= 5_000_000:
        return '5 000'
    return '5 000+'


def normalize_price_group_display(raw: Optional[str] = None, price=None) -> str:
    """
    Привести произвольное значение ЦГ к каноническому отображению: «1 200», «2 000», …
    Если raw пустой — пересчитать по price (если задан).
    """
    if raw:
        key = str(raw).strip()
        if key in ZG_ALIASES:
            return ZG_ALIASES[key]
        compact = _compact(key)
        for alias, name in ZG_ALIASES.items():
            if _compact(alias) == compact:
                return name
    return zg_display_from_price(price)


def price_group_code(
    raw: Optional[str] = None,
    *,
    price_group: Optional[RefGroupPrice] = None,
    price=None,
) -> str:
    """
    Технический код ЦГ без пробелов: 1200, 2000, 5001.
    Приоритет: price_group.code → нормализация raw/name → пересчёт по price.
    """
    if price_group is not None:
        code = str(getattr(price_group, 'code', '') or '').strip()
        if code:
            return code
        raw = getattr(price_group, 'name', None) or raw

    display = normalize_price_group_display(raw, price=price)
    if display == 'Неопределена':
        return ''
    for row in PRICE_GROUP_RANGES:
        if row['name'] == display:
            return row['code']
    compact = _compact(display)
    for row in PRICE_GROUP_RANGES:
        if _compact(row['name']) == compact or _compact(row['code']) == compact:
            return row['code']
    return ''


def apply_canonical_price_group_fields(group: RefGroupPrice) -> None:
    """Проставить code / name / label_1c по справочнику перед сохранением."""
    code = str(getattr(group, 'code', '') or '').strip()
    if code and code in DISPLAY_BY_CODE:
        group.name = DISPLAY_BY_CODE[code]
        group.label_1c = LABEL_1C_BY_CODE[code]
        item = RANGE_BY_CODE[code]
        if group.min_price_rub is None:
            group.min_price_rub = item['min_price_rub']
        if group.max_price_rub is None and item['max_price_rub'] is not None:
            group.max_price_rub = item['max_price_rub']
        if not group.sort_order:
            group.sort_order = item['sort_order']
        return

    resolved_code = price_group_code(group.name)
    if resolved_code:
        group.code = resolved_code
        group.name = DISPLAY_BY_CODE[resolved_code]
        group.label_1c = LABEL_1C_BY_CODE[resolved_code]


def get_unit_correction_kf_1c(unit, stage_pk, price_group, default=100):
    """Коэффициент коррекции 1С для подразделения по ЦГ и этапу цены."""
    if unit is None or not stage_pk or price_group is None:
        return default
    code = price_group_code(price_group=price_group)
    if not code:
        return default
    tpl = STAGE_CORRECTION_1C_ATTR.get(int(stage_pk))
    if not tpl:
        return default
    value = getattr(unit, tpl.format(code=code), default)
    return value if value not in (None, '') else default


def _find_price_group_qs(qs, compact_target: str):
    for group in qs:
        if _compact(group.code) == compact_target or _compact(group.name) == compact_target:
            return group
        if _compact(group.label_1c) == compact_target:
            return group
    return None


def resolve_price_group_ref(
    raw=None,
    *,
    price=None,
    price_group=None,
    create: bool = False,
):
    """
    Найти RefGroupPrice по произвольному значению из API / 1С («1200», «1 200», code и т.д.).
    При create=True создаёт запись с каноническими полями, если не найдена.
    """
    if price_group is not None and getattr(price_group, 'pk', None):
        return price_group

    text = str(raw or '').strip()
    if not text and price in (None, ''):
        return None

    display = normalize_price_group_display(text, price=price)
    if display == 'Неопределена' and not text:
        return None

    code = price_group_code(text, price=price) if text else price_group_code(display)

    if code:
        for active_only in (True, False):
            qs = RefGroupPrice.objects.filter(code=code)
            if active_only:
                qs = qs.filter(is_active=True)
            found = qs.first()
            if found:
                return found

    if display and display != 'Неопределена':
        for field in ('name', 'label_1c'):
            for active_only in (True, False):
                qs = RefGroupPrice.objects.filter(**{field: display})
                if active_only:
                    qs = qs.filter(is_active=True)
                found = qs.first()
                if found:
                    return found

    compact_target = _compact(text or display)
    if compact_target:
        found = _find_price_group_qs(
            RefGroupPrice.objects.filter(is_active=True).order_by('sort_order', 'code'),
            compact_target,
        )
        if found:
            return found
        found = _find_price_group_qs(
            RefGroupPrice.objects.all().order_by('sort_order', 'code'),
            compact_target,
        )
        if found:
            return found

    if not create:
        return None

    group = RefGroupPrice()
    if code:
        group.code = code
        item = RANGE_BY_CODE.get(code, {})
        group.name = DISPLAY_BY_CODE.get(code, display or text)
        group.label_1c = LABEL_1C_BY_CODE.get(code, display or text)
        group.min_price_rub = item.get('min_price_rub')
        group.max_price_rub = item.get('max_price_rub')
        group.sort_order = item.get('sort_order') or 0
        group.is_active = True
    else:
        group.name = display or text
    group.save()
    return group


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
            group.name = item['name']
            group.min_price_rub = item['min_price_rub']
            group.max_price_rub = item['max_price_rub']
            group.sort_order = item['sort_order']
            group.label_1c = item['label_1c']
            group.is_active = True
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


def find_duplicate_price_groups():
    """Активные записи с одинаковым code (для аудита перед слиянием)."""
    from collections import defaultdict

    buckets = defaultdict(list)
    for group in RefGroupPrice.objects.filter(is_active=True).exclude(code='').order_by('code', 'id'):
        buckets[group.code].append(group)
    return {code: rows for code, rows in buckets.items() if len(rows) > 1}
