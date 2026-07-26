"""
Решение об автоставке по настройкам портала и расчёту выкупа.
"""
from __future__ import annotations

import math
from typing import Any


def _as_int(value, default=None):
    if value in (None, ''):
        return default
    try:
        return int(float(str(value).replace(' ', '').replace(',', '.')))
    except (TypeError, ValueError):
        return default


def round_up_to(value, step) -> int:
    """Округление ставки вверх до кратного step (например 820500 → 821000 при step=1000)."""
    value = int(value)
    step = max(1, int(step or 1))
    if step == 1:
        return value
    return int(math.ceil(value / step) * step)


def categorize_auto_bid_reason(reason: str, *, should_bid: bool = False, filters_ok: bool = True) -> str:
    """
    Стабильный код причины для аналитики.
    Группы: disabled | filter_* | economics_* | already_* | ok | other
    """
    if should_bid:
        return 'ok'
    text = (reason or '').strip().lower()
    if not text:
        return 'other'
    if 'выключен' in text:
        return 'disabled'
    if text.startswith('фильтр:'):
        body = text[len('фильтр:'):].strip()
        if body.startswith('год'):
            return 'filter_year'
        if body.startswith('пробег'):
            return 'filter_mileage'
        if 'такси' in body or 'taxi' in body:
            return 'filter_taxi'
        if 'каршеринг' in body or 'carsharing' in body:
            return 'filter_carsharing'
        if 'скруч' in body or 'mileagetwisted' in body:
            return 'filter_mileage_twisted'
        return 'filter_other'
    if not filters_ok:
        return 'filter_other'
    if 'нет рассчитанного выкупа' in text:
        return 'no_buyout'
    if 'minavailablebid' in text and 'нет минимальной' in text:
        return 'no_min_bid'
    if '≤ minavailablebid' in text or '<= minavailablebid' in text:
        return 'buyout_le_min'
    if '≤ maxbid' in text or '<= maxbid' in text:
        return 'buyout_le_max'
    if 'уже наша' in text or 'уже есть наша ставка' in text:
        return 'already_ours'
    if '≥ выкупа' in text or '>= выкупа' in text:
        return 'next_ge_buyout'
    if 'минимальн' in text and 'ставк' in text:
        return 'below_min_bid'
    if 'ручн' in text and 'потол' in text:
        return 'above_manual_max'
    if text.startswith('ok'):
        return 'ok'
    return 'other'


REASON_CATEGORY_LABELS = {
    'ok': 'Ставка разрешена',
    'disabled': 'Автоставки выключены',
    'filter_year': 'Фильтр: год',
    'filter_mileage': 'Фильтр: пробег',
    'filter_taxi': 'Фильтр: такси',
    'filter_carsharing': 'Фильтр: каршеринг',
    'filter_mileage_twisted': 'Фильтр: скрутка пробега',
    'filter_other': 'Фильтр: прочее',
    'no_buyout': 'Нет выкупа',
    'no_min_bid': 'Нет minAvailableBid',
    'buyout_le_min': 'Выкуп ≤ minAvailableBid',
    'buyout_le_max': 'Выкуп ≤ maxBid',
    'already_ours': 'Уже наша ставка / мы лидируем',
    'next_ge_buyout': 'След. ставка ≥ выкупа',
    'below_min_bid': 'Ставка ниже минимальной в настройках',
    'above_manual_max': 'Выше ручного потолка',
    'other': 'Прочее',
}

REASON_CATEGORY_GROUP = {
    'disabled': 'system',
    'filter_year': 'filters',
    'filter_mileage': 'filters',
    'filter_taxi': 'filters',
    'filter_carsharing': 'filters',
    'filter_mileage_twisted': 'filters',
    'filter_other': 'filters',
    'no_buyout': 'economics',
    'no_min_bid': 'economics',
    'buyout_le_min': 'economics',
    'buyout_le_max': 'economics',
    'next_ge_buyout': 'economics',
    'below_min_bid': 'economics',
    'above_manual_max': 'economics',
    'already_ours': 'already',
    'ok': 'ok',
    'other': 'other',
}

REASON_GROUP_LABELS = {
    'system': 'Система',
    'filters': 'Не прошли фильтры настроек',
    'economics': 'Экономика / выкуп',
    'already': 'Уже в торгах',
    'ok': 'Разрешено ставить',
    'other': 'Прочее',
}


def extract_risk_flags_from_payload(payload: dict | None) -> dict:
    """taxi / carsharing / mileageTwisted по событиям Автотеки (status != ok)."""
    flags = {'taxi': False, 'carsharing': False, 'mileageTwisted': False}
    if not isinstance(payload, dict):
        return flags
    events = (
        ((payload.get('autoteka') or {}).get('report') or {}).get('events')
        or payload.get('autotekaEvents')
        or []
    )
    for ev in events:
        if not isinstance(ev, dict):
            continue
        etype = (ev.get('type') or '').strip()
        if etype not in flags:
            continue
        status = (ev.get('status') or '').strip().lower()
        if status and status != 'ok':
            flags[etype] = True
        elif not status and ev.get('description'):
            flags[etype] = True
    # явные флаги из клиента
    for key in flags:
        if payload.get(key) in (True, 'true', '1', 1):
            flags[key] = True
    return flags


def extract_risk_flags_from_lot(lot) -> dict:
    flags = {'taxi': False, 'carsharing': False, 'mileageTwisted': False}
    report = getattr(lot, 'autoteka', None)
    if report is None:
        return flags
    for ev in report.events.all():
        etype = (ev.event_type or '').strip()
        if etype not in flags:
            continue
        status = (ev.status or '').strip().lower()
        if status != 'ok':
            flags[etype] = True
    return flags


def settings_pass_filters(
    settings,
    *,
    year=None,
    mileage=None,
    risk_flags: dict | None = None,
) -> tuple[bool, str]:
    risk_flags = risk_flags or {}
    year = _as_int(year)
    mileage = _as_int(mileage)

    if settings.year_min is not None and year is not None and year < settings.year_min:
        return False, f'год {year} < {settings.year_min}'
    if settings.year_max is not None and year is not None and year > settings.year_max:
        return False, f'год {year} > {settings.year_max}'
    if settings.mileage_min is not None and mileage is not None and mileage < settings.mileage_min:
        return False, f'пробег {mileage} < {settings.mileage_min}'
    if settings.mileage_max is not None and mileage is not None and mileage > settings.mileage_max:
        return False, f'пробег {mileage} > {settings.mileage_max}'

    if settings.block_taxi and risk_flags.get('taxi'):
        return False, 'такси (taxi)'
    if settings.block_carsharing and risk_flags.get('carsharing'):
        return False, 'каршеринг (carsharing)'
    if settings.block_mileage_twisted and risk_flags.get('mileageTwisted'):
        return False, 'скрученный пробег (mileageTwisted)'

    return True, 'ok'


def decide_auto_bid(
    settings,
    *,
    buyout_price,
    min_available_bid,
    max_bid,
    min_bid_step,
    our_bid=None,
    year=None,
    mileage=None,
    risk_flags: dict | None = None,
) -> dict[str, Any]:
    """
    Алгоритм:
    1) фильтры настроек (пробег/год/такси/каршеринг/скрутка);
    2) выкуп > minAvailableBid;
    3) нет maxBid (ставок ещё нет):
         next = round_up(minAvailableBid + minBidStep);
         ставим, если next < выкупа;
    4) есть maxBid:
         maxBid не наша и выкуп > maxBid;
         next = round_up(maxBid + minBidStep);
         ставим, если next < выкупа.

    После каждого обновления ленты парсер заново считает и вызывает этот decide.
    """
    result = {
        'should_bid': False,
        'bid_amount': None,
        'reason': '',
        'reason_category': 'other',
        'buyout_price': _as_int(buyout_price),
        'min_available_bid': _as_int(min_available_bid),
        'max_bid': _as_int(max_bid),
        'min_bid_step': _as_int(min_bid_step, 0) or 0,
        'our_bid': _as_int(our_bid),
        'next_bid': None,
        'filters_ok': False,
        'mode': None,
    }

    if not getattr(settings, 'auto_bid_enabled', False):
        result['reason'] = 'автоставки выключены в настройках'
        result['reason_category'] = categorize_auto_bid_reason(result['reason'], should_bid=False)
        return result

    ok, reason = settings_pass_filters(
        settings,
        year=year,
        mileage=mileage,
        risk_flags=risk_flags,
    )
    result['filters_ok'] = ok
    if not ok:
        result['reason'] = f'фильтр: {reason}'
        result['reason_category'] = categorize_auto_bid_reason(
            result['reason'], should_bid=False, filters_ok=False,
        )
        return result

    buyout = result['buyout_price']
    min_avail = result['min_available_bid']
    max_bid_v = result['max_bid']
    step = result['min_bid_step']
    our = result['our_bid']
    no_max_bid = max_bid_v is None or max_bid_v <= 0

    if not buyout or buyout <= 0:
        result['reason'] = 'нет рассчитанного выкупа'
        result['reason_category'] = categorize_auto_bid_reason(result['reason'])
        return result
    if min_avail is None:
        result['reason'] = 'нет минимальной доступной ставки (minAvailableBid)'
        result['reason_category'] = categorize_auto_bid_reason(result['reason'])
        return result

    if buyout <= min_avail:
        result['reason'] = f'выкуп {buyout} ≤ minAvailableBid {min_avail}'
        result['reason_category'] = categorize_auto_bid_reason(result['reason'])
        return result

    round_to = _as_int(getattr(settings, 'bid_round_to', 1000), 1000) or 1000

    if no_max_bid:
        # Ставок ещё нет — первая ставка от минимума + шаг.
        result['mode'] = 'first_from_min'
        if our is not None and our > 0 and our >= min_avail:
            result['reason'] = 'уже есть наша ставка при пустом maxBid — ждём обновления лота'
            result['reason_category'] = categorize_auto_bid_reason(result['reason'])
            return result
        next_bid = round_up_to(min_avail + max(step, 0), round_to)
        result['next_bid'] = next_bid
        if next_bid >= buyout:
            result['reason'] = (
                f'первая ставка {next_bid} (minAvailableBid+шаг↑{round_to}) ≥ выкупа {buyout}'
            )
            result['reason_category'] = categorize_auto_bid_reason(result['reason'])
            return result
        min_bid_floor = _as_int(getattr(settings, 'min_bid_amount', None))
        if min_bid_floor and min_bid_floor > 0 and next_bid < min_bid_floor:
            result['reason'] = (
                f'ставка {next_bid} ниже минимальной в настройках ({min_bid_floor})'
            )
            result['reason_category'] = categorize_auto_bid_reason(result['reason'])
            return result
        result['should_bid'] = True
        result['bid_amount'] = next_bid
        result['reason'] = 'ok (первая ставка: min+шаг)'
        result['reason_category'] = 'ok'
        return result

    # Есть maxBid по лоту
    result['mode'] = 'raise_max'
    if buyout <= max_bid_v:
        result['reason'] = f'выкуп {buyout} ≤ maxBid {max_bid_v}'
        result['reason_category'] = categorize_auto_bid_reason(result['reason'])
        return result

    max_is_ours = our is not None and our > 0 and our == max_bid_v
    if max_is_ours:
        result['reason'] = 'максимальная ставка по лоту уже наша'
        result['reason_category'] = categorize_auto_bid_reason(result['reason'])
        return result

    next_bid = round_up_to(max_bid_v + max(step, 0), round_to)
    result['next_bid'] = next_bid

    if next_bid >= buyout:
        result['reason'] = (
            f'следующая ставка {next_bid} (maxBid+шаг↑{round_to}) ≥ выкупа {buyout}'
        )
        result['reason_category'] = categorize_auto_bid_reason(result['reason'])
        return result
    if next_bid < min_avail:
        next_bid = round_up_to(min_avail + max(step, 0), round_to)
        result['next_bid'] = next_bid
        if next_bid >= buyout:
            result['reason'] = (
                f'после выравнивания к minAvailableBid {next_bid} ≥ выкупа {buyout}'
            )
            result['reason_category'] = categorize_auto_bid_reason(result['reason'])
            return result

    result['should_bid'] = True
    result['bid_amount'] = next_bid
    result['reason'] = 'ok'
    result['reason_category'] = 'ok'

    min_bid_floor = _as_int(getattr(settings, 'min_bid_amount', None))
    if min_bid_floor and min_bid_floor > 0 and next_bid < min_bid_floor:
        result['should_bid'] = False
        result['bid_amount'] = None
        result['reason'] = (
            f'ставка {next_bid} ниже минимальной в настройках ({min_bid_floor})'
        )
        result['reason_category'] = categorize_auto_bid_reason(result['reason'])
        return result

    return result
