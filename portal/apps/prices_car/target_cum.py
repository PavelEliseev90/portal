"""
Целевая кумулятивная маржа (Target Cum / АвтоК) для новых автомобилей.

Формула: Себестоимость × Медианная маржа аналогов × Коэффициент ликвидности
"""
from __future__ import annotations

import statistics
from datetime import datetime, timedelta

from django.db.models import Count, Sum

ANALYSIS_DAYS = 60
MIN_DEALS_AFTER_TRIM = 15
TRIM_FRACTION = 0.15
COST_BANDS = (0.10, 0.15, 0.20)
SEARCH_LEVELS = ('complectation', 'model', 'brand')

LIQUIDITY_BANDS = (
    (1 / 3, 1.12, 'Очень быстро'),
    (2 / 3, 1.05, 'Быстро'),
)


def get_analysis_days_for_car(car, brand=None) -> int:
    """
    Определить период анализа статистики продаж (в днях) для автомобиля.
    Приоритет:
    1. Индивидуальный analysis_period_days бренда (PriceCarBrand).
    2. Общий период по умолчанию из настроек алгоритма (PriceCarAlgorithmSettings).
    3. Константа ANALYSIS_DAYS = 60 (fallback).
    """
    if brand is None and car is not None:
        try:
            from prices_car.brand_resolve import resolve_price_car_brand_for_car
            brand = resolve_price_car_brand_for_car(car)
        except Exception:
            brand = None

    if brand and getattr(brand, 'analysis_period_days', None):
        return int(brand.analysis_period_days)

    try:
        from prices_car.models import PriceCarAlgorithmSettings
        return PriceCarAlgorithmSettings.get_default_analysis_days()
    except Exception:
        return ANALYSIS_DAYS


def _liquidity_multiplier(ratio: float) -> tuple[float, str]:
    if ratio <= 0:
        return 1.0, 'Норма'
    for threshold, multiplier, label in LIQUIDITY_BANDS:
        if ratio <= threshold:
            return multiplier, label
    if ratio < 3:
        return 1.0, 'Норма'
    if ratio < 5:
        return 0.94, 'Замедленная'
    if ratio < 8:
        return 0.79, 'Зависшая'
    return 0.63, 'Глубокий сток (максимальное снижение порога)'


def _cumulative_margin(record) -> float:
    parts = (
        record.SummaRabot,
        record.ValovayaPribylZChShiny,
        record.ValovayaPribylZCh,
        record.SummaTreydInPoPlanu,
        record.VPOPFU,
        record.SummaMarzhiBezNDS,
        record.SummaGosreg,
    )
    return sum(float(p or 0) for p in parts)


def _margin_pct(record) -> float | None:
    cost = float(record.SebestoimostPoDokumentu or 0)
    if cost <= 0:
        return None
    return _cumulative_margin(record) / cost * 100


def _sale_days(record) -> int | None:
    if not record.DataPostupleniya or not record.DataProdazhi:
        return None
    days = (record.DataProdazhi - record.DataPostupleniya).days
    return days if days >= 0 else None


def _trim_outliers(values: list[float]) -> list[float] | None:
    if len(values) < MIN_DEALS_AFTER_TRIM:
        return None
    ordered = sorted(values)
    cut = int(len(ordered) * TRIM_FRACTION)
    trimmed = ordered[cut:len(ordered) - cut] if cut else ordered
    if len(trimmed) < MIN_DEALS_AFTER_TRIM:
        return None
    return trimmed


def _median(values: list[float]) -> float:
    return float(statistics.median(values))


def _model_modification_ids(car) -> set[int]:
    from refs.models import AutoruModification

    model = car.modification_autoru.model
    return set(
        AutoruModification.objects.filter(model=model)
        .exclude(idSite__isnull=True)
        .values_list('idSite', flat=True)
    )


def _fetch_sales_records(car, days: int | None = None) -> list[dict]:
    from powerbi.models import Cumulative

    if days is None:
        days = get_analysis_days_for_car(car)

    mark = car.modification_autoru.model.mark.name.upper()
    dt_end = datetime.now()
    dt_start = dt_end - timedelta(days=days)

    qs = Cumulative.objects.filter(
        TipProdazhi='Розница',
        DataProdazhi__gte=dt_start,
        DataProdazhi__lte=dt_end,
        Marka=mark,
        ListOtsenkiVIN=None,
        SebestoimostPoDokumentu__gt=0,
    ).exclude(RRTS='0')

    records = []
    for row in qs.iterator():
        margin_pct = _margin_pct(row)
        if margin_pct is None:
            continue
        records.append({
            'cost': float(row.SebestoimostPoDokumentu),
            'margin_pct': margin_pct,
            'days': _sale_days(row),
            'trade_in': float(row.KolichestvoTreydIn or 0) > 0,
            'mod_id': row.IDModifikatsii,
            'compl_id': row.IdKomplektatsii,
        })
    return records


def _matches_level(rec: dict, level: str, *, model_mod_ids: set[int], complectation_id) -> bool:
    if level == 'complectation':
        return complectation_id is not None and rec['compl_id'] == complectation_id
    if level == 'model':
        return rec['mod_id'] in model_mod_ids
    return True


def _filter_analogs(
    records: list[dict],
    *,
    car_cost: float,
    cost_pct: float,
    level: str,
    with_trade_in: bool,
    model_mod_ids: set[int],
    complectation_id,
) -> list[dict]:
    low = car_cost * (1 - cost_pct)
    high = car_cost * (1 + cost_pct)
    result = []
    for rec in records:
        if rec['trade_in'] != with_trade_in:
            continue
        if not (low <= rec['cost'] <= high):
            continue
        if not _matches_level(rec, level, model_mod_ids=model_mod_ids, complectation_id=complectation_id):
            continue
        result.append(rec)
    return result


def _search_analog_set(
    records: list[dict],
    *,
    car_cost: float,
    with_trade_in: bool,
    model_mod_ids: set[int],
    complectation_id,
) -> tuple[list[dict], str] | tuple[None, None]:
    levels = list(SEARCH_LEVELS)
    if complectation_id is None:
        levels = [lvl for lvl in levels if lvl != 'complectation']

    for cost_pct in COST_BANDS:
        for level in levels:
            analogs = _filter_analogs(
                records,
                car_cost=car_cost,
                cost_pct=cost_pct,
                level=level,
                with_trade_in=with_trade_in,
                model_mod_ids=model_mod_ids,
                complectation_id=complectation_id,
            )
            margin_pcts = [a['margin_pct'] for a in analogs]
            trimmed = _trim_outliers(margin_pcts)
            if trimmed is not None:
                label = (
                    f'{level}, ±{int(cost_pct * 100)}%, '
                    f'{"с trade-in" if with_trade_in else "без trade-in"}'
                )
                return analogs, label
    return None, None


def _brand_monthly_fallback(car, brand_km, irc, is_yellow: bool = False) -> dict | None:
    """Целевой КМ на месяц (BrandKM), если аналогов недостаточно."""
    from refs.models import RefCarsOrganization

    if brand_km is None:
        return None

    mark = car.modification_autoru.model.mark
    stock = RefCarsOrganization.objects.filter(
        modification_autoru__model__mark=mark,
        is_new=True,
    ).exclude(quantity=0).exclude(price=0).aggregate(Sum('price'), Count('id'))

    stock_sum = stock['price__sum']
    stock_count = stock['id__count'] or 0
    brand_km_val = brand_km.km
    price = car.price or 0
    irc_val = float(irc or 1)

    if stock_sum and stock_count > 0:
        avg_price = stock_sum / stock_count
        km_pct = brand_km_val / avg_price * 100
        km_stage_pct = round(km_pct, 2) * irc_val
        km_value = price * km_stage_pct / 100
        description = (
            f'Fallback: целевой КМ бренда {mark.name} на месяц '
            f'({brand_km.month.strftime("%m.%Y") if brand_km.month else "—"})'
        )
    else:
        km_stage_pct = round(float(brand_km_val), 2) * irc_val
        km_value = price * km_stage_pct / 100 if price else brand_km_val
        if km_value == 0:
            km_value = brand_km_val
        description = f'Fallback: целевой КМ бренда {mark.name} без стока марки'

    liquidity_mult = 0.63 if is_yellow else 1.0
    liquidity_lbl = 'Глубокий сток (максимальное снижение порога)' if is_yellow else 'Норма'
    if is_yellow:
        km_value = km_value * liquidity_mult
        description += f' [жёлтый АМ: {liquidity_lbl} ×{liquidity_mult}]'

    return {
        'km_min_automatic': round(km_value, 2),
        'km_description': description,
        'fallback': True,
        'median_margin_pct': None,
        'liquidity_multiplier': liquidity_mult,
        'liquidity_label': liquidity_lbl,
        'analog_count': 0,
        'search_label': 'Целевой КМ на месяц',
        'days_in_stock': car.days_in_stok or 0,
        'avg_sale_days': None,
        'liquidity_ratio': None,
        'car_cost': car.cost_price or 0,
        'is_yellow': is_yellow,
    }


TACTIC_MULTIPLIERS = {
    'max_margin': (1.10, 'Тактика: Макс. маржа (×1.10)'),
    'balanced': (1.00, 'Тактика: Баланс (×1.00)'),
    'max_volume': (0.85, 'Тактика: Макс. штуки (×0.85)'),
}


def calculate_target_cum(
    car,
    *,
    brand_km=None,
    irc=None,
    with_trade_in: bool = False,
    dc_tactic: str | None = None,
    analysis_days: int | None = None,
    is_yellow: bool | None = None,
) -> dict | None:
    """
    Рассчитать целевую кумулятивную маржу (АвтоК) для автомобиля.
    Возвращает dict в формате automatic_* или None.
    Поддерживает тактику ДЦ (max_margin, balanced, max_volume) и период анализа.
    Для «жёлтых» автомобилей (сдан рапорт перед импортером) сразу применяется
    коэффициент ликвидности «Глубокий сток (максимальное снижение порога)» (×0.63).
    """
    if car is None or car.modification_autoru is None:
        return None

    if is_yellow is None:
        is_yellow = bool(getattr(car, 'is_yellow', False))

    # Определение тактики ДЦ, если не передана явно
    if dc_tactic is None and getattr(car, 'unit_id', None):
        try:
            from prices_car.models import DcMonthlyPlan
            from django.utils import timezone
            month_start = timezone.now().date().replace(day=1)
            plan = DcMonthlyPlan.objects.filter(unit_id=car.unit_id, month=month_start).first()
            if plan:
                dc_tactic = plan.tactic
        except Exception:
            pass

    tactic_mult, tactic_label = TACTIC_MULTIPLIERS.get(dc_tactic, (1.0, ''))

    car_cost = int(car.cost_price or 0)
    if car_cost <= 0:
        return _brand_monthly_fallback(car, brand_km, irc, is_yellow=is_yellow)

    brand_obj = getattr(brand_km, 'brand', None) if brand_km else None
    if analysis_days is None:
        analysis_days = get_analysis_days_for_car(car, brand=brand_obj)

    records = _fetch_sales_records(car, days=analysis_days)
    model_mod_ids = _model_modification_ids(car)
    complectation_id = (
        car.complectation_autoru.idSite
        if car.complectation_autoru_id and car.complectation_autoru
        else None
    )

    analogs, search_label = _search_analog_set(
        records,
        car_cost=car_cost,
        with_trade_in=with_trade_in,
        model_mod_ids=model_mod_ids,
        complectation_id=complectation_id,
    )

    if not analogs:
        return _brand_monthly_fallback(car, brand_km, irc, is_yellow=is_yellow)

    margin_pcts = [a['margin_pct'] for a in analogs]
    trimmed = _trim_outliers(margin_pcts)
    if trimmed is None:
        return _brand_monthly_fallback(car, brand_km, irc, is_yellow=is_yellow)

    median_margin_pct = _median(trimmed)

    sale_days = [a['days'] for a in analogs if a['days'] is not None]
    avg_sale_days = _median(sale_days) if sale_days else None
    days_in_stock = int(car.days_in_stok or 0)

    if avg_sale_days and avg_sale_days > 0:
        liquidity_ratio = days_in_stock / avg_sale_days
    else:
        liquidity_ratio = 1.0

    # Если машина желтая — сразу применяется «Глубокий сток (максимальное снижение порога)»
    if is_yellow:
        liquidity_multiplier = 0.63
        liquidity_label = 'Глубокий сток (максимальное снижение порога)'
    else:
        liquidity_multiplier, liquidity_label = _liquidity_multiplier(liquidity_ratio)

    adjusted_margin_pct = median_margin_pct * liquidity_multiplier * tactic_mult
    km_value = car_cost * adjusted_margin_pct / 100

    mark_name = car.modification_autoru.model.mark.name
    model_name = car.modification_autoru.model.name
    tactic_desc = f', {tactic_label}' if tactic_label else ''
    days_desc = f' за {analysis_days} дн.'
    yellow_desc = ', жёлтый АМ' if is_yellow else ''
    description = (
        f'АвтоК: {mark_name} {model_name}, аналоги {search_label}{days_desc} '
        f'({len(trimmed)} сделок), медиана {median_margin_pct:.2f}%, '
        f'ликвидность {liquidity_label} (×{liquidity_multiplier:.2f}){yellow_desc}{tactic_desc}'
    )

    return {
        'km_min_automatic': round(km_value, 2),
        'km_description': description,
        'fallback': False,
        'median_margin_pct': round(median_margin_pct, 4),
        'adjusted_margin_pct': round(adjusted_margin_pct, 4),
        'liquidity_multiplier': liquidity_multiplier,
        'liquidity_label': liquidity_label,
        'liquidity_ratio': round(liquidity_ratio, 2) if liquidity_ratio is not None else None,
        'tactic_multiplier': tactic_mult,
        'tactic_label': tactic_label,
        'analog_count': len(trimmed),
        'search_label': search_label,
        'analysis_days': analysis_days,
        'days_in_stock': days_in_stock,
        'avg_sale_days': round(avg_sale_days, 1) if avg_sale_days is not None else None,
        'car_cost': car_cost,
        'is_yellow': is_yellow,
    }
