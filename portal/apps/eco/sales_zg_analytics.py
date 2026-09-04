"""Аналитика продаж по ценовым группам (ЦГ).

Помесячно и разрез ЦГ×месяц.

Источник: DocCarShipment (отгрузки / продажи).
Период: dataTime.
ЦГ пересчитывается по сумме продажи (amount, пороги как у ЦНА).
Ячейка: количество продаж · медиана цены продаж.

Для detail-таблицы подтягиваем витринные поля из TradeInFunnel по rlk_id.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Optional

from analytics.models import TradeInFunnel

from documents.models import DocCarShipment

from eco.estimation_zg_analytics import (
    ZG_COLORS,
    ZG_ORDER,
    _iter_months,
    _median,
    _month_bounds,
    _month_key,
    _month_label,
    _unit_color,
    _unit_label,
    normalize_zg_name,
    zg_from_price,
)


def _sale_cell(count: int, prices: list, month_key: str = '') -> dict:
    empty = (count or 0) <= 0
    return {
        'count': int(count or 0),
        'med_price': int(round(_median(prices))) if not empty else 0,
        'empty': empty,
        'month_key': month_key,
    }


def _build_sales_unit_breakdown(
    unit_bucket,
    unit_names: dict,
    month_keys: list,
    month_labels: list,
    month_totals: dict,
) -> dict:
    """График и сводная таблица: месяцы × ДЦ (продажи)."""
    unit_totals = defaultdict(lambda: {'count': 0, 'prices': []})
    for mk in month_keys:
        for uid, cell in unit_bucket[mk].items():
            unit_totals[uid]['count'] += cell['count']
            unit_totals[uid]['prices'].extend(cell['prices'])

    unit_list = sorted(
        unit_totals.keys(),
        key=lambda u: (-unit_totals[u]['count'], _unit_label(u, unit_names.get(u))),
    )

    datasets = []
    for i, uid in enumerate(unit_list):
        label = _unit_label(uid, unit_names.get(uid))
        datasets.append({
            'label': label,
            'unit_id': uid,
            'backgroundColor': _unit_color(i),
            'data': [unit_bucket[mk][uid]['count'] for mk in month_keys],
        })

    pivot_rows = []
    for uid in unit_list:
        cells = []
        for mk in month_keys:
            cell = unit_bucket[mk][uid]
            cells.append(_sale_cell(cell['count'], cell['prices'], mk))
        ut = unit_totals[uid]
        pivot_rows.append({
            'unit_id': uid,
            'unit_name': _unit_label(uid, unit_names.get(uid)),
            'cells': cells,
            'total': _sale_cell(ut['count'], ut['prices']),
        })

    grand_total = sum(month_totals.values())
    grand_prices = []
    for mk in month_keys:
        for uid in unit_bucket[mk]:
            grand_prices.extend(unit_bucket[mk][uid]['prices'])
    pivot_footer = {
        'unit_name': 'Итого',
        'cells': [
            _sale_cell(month_totals[mk], [
                p for uid in unit_bucket[mk] for p in unit_bucket[mk][uid]['prices']
            ], mk)
            for mk in month_keys
        ],
        'total': _sale_cell(grand_total, grand_prices),
        'is_total': True,
    }

    return {
        'labels': month_labels,
        'month_keys': month_keys,
        'datasets': datasets,
        'month_totals': [month_totals[mk] for mk in month_keys],
        'pivot_rows': pivot_rows,
        'pivot_footer': pivot_footer,
    }


def build_sales_zg_analytics(
    *,
    date_start: datetime,
    date_end: datetime,
    unit_id: Optional[int] = None,
) -> dict:
    qs = DocCarShipment.objects.filter(
        active=True,
        dataTime__gte=date_start,
        dataTime__lte=date_end,
    ).filter(amount__gt=0)

    if unit_id:
        qs = qs.filter(unit__id=unit_id)

    # month -> zg -> aggregation
    bucket = defaultdict(lambda: defaultdict(lambda: {'count': 0, 'prices': []}))
    unit_bucket = defaultdict(lambda: defaultdict(lambda: {'count': 0, 'prices': []}))
    unit_names = {}
    zg_totals = defaultdict(lambda: {'count': 0, 'prices': []})
    month_totals = defaultdict(int)

    rows = qs.select_related('unit').only('dataTime', 'amount', 'unit_id', 'unit__name')

    for row in rows.iterator(chunk_size=2000):
        if not row.dataTime:
            continue
        mk = _month_key(row.dataTime)
        price = float(row.amount or 0)
        if price <= 0:
            continue
        zg = zg_from_price(price)
        bucket[mk][zg]['count'] += 1
        bucket[mk][zg]['prices'].append(price)
        zg_totals[zg]['count'] += 1
        zg_totals[zg]['prices'].append(price)
        month_totals[mk] += 1
        if not unit_id:
            uid = int(row.unit_id or 0)
            if row.unit is not None and row.unit.name:
                unit_names[uid] = str(row.unit.name).strip()
            unit_bucket[mk][uid]['count'] += 1
            unit_bucket[mk][uid]['prices'].append(price)

    months = _iter_months(date_start, date_end)
    month_keys = [_month_key(m) for m in months]
    month_labels = [_month_label(m) for m in months]

    seen = set()
    for mk in month_keys:
        for zg in bucket[mk].keys():
            seen.add(zg)

    zg_list = [z for z in ZG_ORDER if z in seen]
    if not zg_list:
        # если вдруг нет продаж с price_sale>0 — показываем пустую сводку
        zg_list = []

    datasets = []
    chart_month_totals = [month_totals[mk] for mk in month_keys]

    for zg in zg_list:
        datasets.append({
            'label': f'ЦГ {zg}',
            'zg': zg,
            'backgroundColor': ZG_COLORS.get(zg, '#94a3b8'),
            'data': [bucket[mk][zg]['count'] for mk in month_keys],
        })

    pivot_rows = []
    for zg in zg_list:
        cells = []
        for mk in month_keys:
            b = bucket[mk][zg]
            cells.append(_sale_cell(b['count'], b['prices'], mk))
        zt = zg_totals[zg]
        pivot_rows.append({
            'zg': zg,
            'cells': cells,
            'total': _sale_cell(zt['count'], zt['prices']),
        })

    grand_total = sum(month_totals.values())
    grand_prices = []
    # собрать медиану по всему периоду (для footer) — чтобы было стабильно
    for mk in month_keys:
        for zg in zg_list:
            grand_prices.extend(bucket[mk][zg]['prices'])
    pivot_footer = {
        'zg': 'Итого',
        'cells': [
            _sale_cell(month_totals[mk], [
                p for zg in zg_list for p in bucket[mk][zg]['prices']
            ], mk)
            for mk in month_keys
        ],
        'total': _sale_cell(grand_total, grand_prices),
        'is_total': True,
    }

    grand_med_price = int(round(_median(grand_prices))) if grand_prices else 0

    unit_breakdown = None
    if not unit_id:
        unit_breakdown = _build_sales_unit_breakdown(
            unit_bucket,
            unit_names,
            month_keys,
            month_labels,
            month_totals,
        )

    return {
        'month_keys': month_keys,
        'month_labels': month_labels,
        'chart': {
            'labels': month_labels,
            'month_keys': month_keys,
            'datasets': datasets,
            'month_totals': chart_month_totals,
        },
        'unit_chart': unit_breakdown,
        'unit_pivot_rows': (unit_breakdown or {}).get('pivot_rows', []),
        'unit_pivot_footer': (unit_breakdown or {}).get('pivot_footer'),
        'pivot_rows': pivot_rows,
        'pivot_footer': pivot_footer,
        'summary': {
            'total': grand_total,
            'med_price': grand_med_price,
            'months': len(month_keys),
        },
    }


def build_sales_zg_detail(
    *,
    month_key: str,
    zg: str,
    unit_id: Optional[int] = None,
) -> dict:
    date_start, date_end = _month_bounds(month_key)
    target_zg = normalize_zg_name(zg)

    ship_qs = DocCarShipment.objects.filter(
        active=True,
        dataTime__gte=date_start,
        dataTime__lte=date_end,
    ).filter(amount__gt=0)

    if unit_id:
        ship_qs = ship_qs.filter(unit__id=unit_id)

    ship_items = []
    rlk_ids = set()
    prices = []
    sum_reward_credit = 0.0
    sum_reward_opfu = 0.0
    sum_kits = 0.0

    for s in ship_qs.only(
        'rlk_id', 'dataTime', 'amount',
        'amount_reward_credit', 'amount_reward_opfu', 'amount_kits',
    ).iterator(chunk_size=2000):
        if not s.dataTime or not s.rlk_id:
            continue
        price = float(s.amount or 0)
        if price <= 0:
            continue
        row_zg = zg_from_price(price)
        if row_zg != target_zg:
            continue
        reward_credit = float(s.amount_reward_credit or 0)
        reward_opfu = float(s.amount_reward_opfu or 0)
        kits = float(s.amount_kits or 0)
        rlk_ids.add(s.rlk_id)
        prices.append(price)
        sum_reward_credit += reward_credit
        sum_reward_opfu += reward_opfu
        sum_kits += kits
        ship_items.append({
            'rlk_id': s.rlk_id,
            'date_sale': s.dataTime,
            'price_sale': price,
            'amount_reward_credit': reward_credit,
            'amount_reward_opfu': reward_opfu,
            'amount_kits': kits,
        })

    funnel_map = {}
    if rlk_ids:
        funnels = TradeInFunnel.objects.filter(rlk_id__in=rlk_ids).only(
            'rlk_id',
            'rlk_number',
            'date_rlk',
            'mark_name',
            'model_name',
            'vin',
            'unit_name',
            'unit_source_name',
            'type_reception_name',
            'stage',
        )
        funnel_map = {f.rlk_id: f for f in funnels}

    rows = []
    for item in sorted(ship_items, key=lambda x: x['date_sale'], reverse=True):
        f = funnel_map.get(item['rlk_id'])
        rows.append({
            'rlk_id': item['rlk_id'],
            'rlk_number': (f.rlk_number if f else '') or '',
            'date_sale': item['date_sale'],
            'date_rlk': (f.date_rlk if f else None),
            'mark': (f.mark_name if f else '') or '',
            'model': (f.model_name if f else '') or '',
            'vin': (f.vin if f else '') or '',
            'unit': (f.unit_name if f else '') or '',
            'unit_source': (f.unit_source_name if f else '') or '',
            'type_name': (f.type_reception_name if f else '') or '',
            'stage': (f.stage if f else '') or '',
            'price_sale': item['price_sale'],
            'amount_reward_credit': item['amount_reward_credit'],
            'amount_reward_opfu': item['amount_reward_opfu'],
            'amount_kits': item['amount_kits'],
        })

    total = len(rows)
    return {
        'source': 'sales',
        'month_key': month_key,
        'month_label': _month_label(date_start),
        'zg': target_zg,
        'rows': rows,
        'summary': {
            'total': total,
            'med_price': int(round(_median(prices))) if prices else 0,
            'amount_reward_credit': int(round(sum_reward_credit)),
            'amount_reward_opfu': int(round(sum_reward_opfu)),
            'amount_kits': int(round(sum_kits)),
        },
    }

