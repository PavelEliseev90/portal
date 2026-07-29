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
    zg_totals = defaultdict(lambda: {'count': 0, 'prices': []})
    month_totals = defaultdict(int)

    rows = qs.only('dataTime', 'amount')

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

    return {
        'month_keys': month_keys,
        'month_labels': month_labels,
        'chart': {
            'labels': month_labels,
            'month_keys': month_keys,
            'datasets': datasets,
            'month_totals': chart_month_totals,
        },
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

    for s in ship_qs.only('rlk_id', 'dataTime', 'amount').iterator(chunk_size=2000):
        if not s.dataTime or not s.rlk_id:
            continue
        price = float(s.amount or 0)
        if price <= 0:
            continue
        row_zg = zg_from_price(price)
        if row_zg != target_zg:
            continue
        rlk_ids.add(s.rlk_id)
        prices.append(price)
        ship_items.append({
            'rlk_id': s.rlk_id,
            'date_sale': s.dataTime,
            'price_sale': price,
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
        },
    }

