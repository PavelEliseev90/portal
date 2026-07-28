"""Аналитика оценок по ценовым группам (помесячно).

Источник: TradeInFunnel (как в воронке приёма).
«Оценка» — есть дата начала оценки в периоде.
«Принята» — заполнена date_reception_success (не 01.01.0001).
ЦГ — zg_name из воронки, иначе расчёт по цене (zna / price_after / price_before).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Optional

from dateutil.relativedelta import relativedelta
from django.db.models import Q

from analytics.models import TradeInFunnel
from refs.price_groups import PRICE_GROUP_RANGES


DATE_INVALID = datetime(1, 1, 1)

ZG_ORDER = [row['name'] for row in PRICE_GROUP_RANGES] + ['Неопределена']

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
    '5000': '5 000',
    '5 000': '5 000',
    '5001': '5 000+',
    '5 000+': '5 000+',
    '5000+': '5 000+',
}

ZG_COLORS = {
    '200': '#94a3b8',
    '400': '#60a5fa',
    '700': '#34d399',
    '1 200': '#a78bfa',
    '2 000': '#fbbf24',
    '3 000': '#fb7185',
    '5 000': '#38bdf8',
    '5 000+': '#f97316',
    'Неопределена': '#cbd5e1',
}


def zg_from_price(price) -> str:
    try:
        value = float(price or 0)
    except (TypeError, ValueError):
        value = 0
    if value <= 0:
        return 'Неопределена'
    for row in PRICE_GROUP_RANGES:
        max_p = row.get('max_price_rub')
        min_p = row.get('min_price_rub') or 0
        if max_p is None:
            if value >= min_p:
                return row['name']
        elif min_p <= value < max_p:
            return row['name']
    return 'Неопределена'


def normalize_zg_name(raw: Optional[str], price=None) -> str:
    if raw:
        key = str(raw).strip()
        if key in ZG_ALIASES:
            return ZG_ALIASES[key]
        compact = key.replace(' ', '')
        for alias, name in ZG_ALIASES.items():
            if alias.replace(' ', '') == compact:
                return name
    return zg_from_price(price)


def resolve_funnel_price(row: TradeInFunnel):
    for attr in ('zna', 'price_after', 'price_before', 'price_remote', 'price_reception_staff'):
        val = getattr(row, attr, None)
        try:
            num = float(val or 0)
        except (TypeError, ValueError):
            num = 0
        if num > 0:
            return num
    return 0


def is_accepted(row: TradeInFunnel) -> bool:
    dt = row.date_reception_success
    if not dt:
        return False
    return dt != DATE_INVALID and dt.year > 1


def _month_key(dt: datetime) -> str:
    return dt.strftime('%Y-%m')


def _month_label(dt: datetime) -> str:
    months = (
        '', 'янв', 'фев', 'мар', 'апр', 'май', 'июн',
        'июл', 'авг', 'сен', 'окт', 'ноя', 'дек',
    )
    return f'{months[dt.month]} {dt.year}'


def _iter_months(date_start: datetime, date_end: datetime):
    cur = date_start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = date_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    out = []
    while cur <= end:
        out.append(cur)
        cur = cur + relativedelta(months=1)
    return out


def _pct(part: int, total: int) -> float:
    if not total:
        return 0.0
    return round(100.0 * part / total, 1)


def _cell(total: int, accepted: int) -> dict:
    return {
        'total': total,
        'accepted': accepted,
        'rate': _pct(accepted, total),
        'empty': total <= 0,
    }


def build_estimation_zg_analytics(
    *,
    date_start: datetime,
    date_end: datetime,
    unit_id: Optional[int] = None,
    staff_id: Optional[int] = None,
    analyst_id: Optional[int] = None,
    type_id: Optional[int] = None,
) -> dict:
    qs = TradeInFunnel.objects.filter(
        date_start_estimation__gte=date_start,
        date_start_estimation__lte=date_end,
        estimation_id__isnull=False,
    ).exclude(date_start_estimation=DATE_INVALID)

    if unit_id:
        qs = qs.filter(unit_id=unit_id)
    if staff_id:
        qs = qs.filter(staff_id=staff_id)
    if analyst_id:
        qs = qs.filter(
            Q(analyst_before_id=analyst_id)
            | Q(analyst_after_id=analyst_id)
            | Q(analyst_remote_id=analyst_id)
        )
    if type_id:
        qs = qs.filter(type_reception_id=type_id)

    bucket = defaultdict(lambda: defaultdict(lambda: {'total': 0, 'accepted': 0}))
    zg_totals = defaultdict(lambda: {'total': 0, 'accepted': 0})
    month_totals = defaultdict(lambda: {'total': 0, 'accepted': 0})

    rows = qs.only(
        'date_start_estimation',
        'date_reception_success',
        'zg_name',
        'zna',
        'price_after',
        'price_before',
        'price_remote',
        'price_reception_staff',
    )

    for row in rows.iterator(chunk_size=2000):
        if not row.date_start_estimation:
            continue
        mk = _month_key(row.date_start_estimation)
        zg = normalize_zg_name(row.zg_name, resolve_funnel_price(row))
        accepted = 1 if is_accepted(row) else 0
        bucket[mk][zg]['total'] += 1
        bucket[mk][zg]['accepted'] += accepted
        zg_totals[zg]['total'] += 1
        zg_totals[zg]['accepted'] += accepted
        month_totals[mk]['total'] += 1
        month_totals[mk]['accepted'] += accepted

    months = _iter_months(date_start, date_end)
    month_keys = [_month_key(m) for m in months]
    month_labels = [_month_label(m) for m in months]

    seen = set()
    for mk in month_keys:
        seen.update(bucket[mk].keys())
    zg_list = [z for z in ZG_ORDER if z in seen or zg_totals[z]['total'] > 0]
    if not zg_list:
        zg_list = [row['name'] for row in PRICE_GROUP_RANGES]

    datasets = []
    for zg in zg_list:
        datasets.append({
            'label': f'ЦГ {zg}',
            'zg': zg,
            'backgroundColor': ZG_COLORS.get(zg, '#94a3b8'),
            'data': [bucket[mk][zg]['total'] for mk in month_keys],
            'accepted': [bucket[mk][zg]['accepted'] for mk in month_keys],
            'rate': [
                _pct(bucket[mk][zg]['accepted'], bucket[mk][zg]['total'])
                for mk in month_keys
            ],
        })

    # Pivot: строки = ЦГ, столбцы = месяцы; ячейка = оценки / принято / %
    pivot_rows = []
    for zg in zg_list:
        cells = []
        for mk in month_keys:
            cell = bucket[mk][zg]
            cells.append(_cell(cell['total'], cell['accepted']))
        zt = zg_totals[zg]
        pivot_rows.append({
            'zg': zg,
            'cells': cells,
            'total': _cell(zt['total'], zt['accepted']),
        })

    footer_cells = [
        _cell(month_totals[mk]['total'], month_totals[mk]['accepted'])
        for mk in month_keys
    ]
    grand_total = sum(v['total'] for v in month_totals.values())
    grand_accepted = sum(v['accepted'] for v in month_totals.values())
    pivot_footer = {
        'zg': 'Итого',
        'cells': footer_cells,
        'total': _cell(grand_total, grand_accepted),
        'is_total': True,
    }

    zg_summary = []
    for zg in zg_list:
        t = zg_totals[zg]['total']
        a = zg_totals[zg]['accepted']
        if t <= 0:
            continue
        zg_summary.append({
            'zg': zg,
            'total': t,
            'accepted': a,
            'rate': _pct(a, t),
        })

    return {
        'month_keys': month_keys,
        'month_labels': month_labels,
        'zg_list': zg_list,
        'chart': {
            'labels': month_labels,
            'datasets': datasets,
            'month_totals': [month_totals[mk]['total'] for mk in month_keys],
        },
        'pivot_rows': pivot_rows,
        'pivot_footer': pivot_footer,
        'zg_summary': zg_summary,
        'summary': {
            'total': grand_total,
            'accepted': grand_accepted,
            'rate': _pct(grand_accepted, grand_total),
            'months': len(month_keys),
        },
    }
