"""Аналитика оценок по ценовым группам (помесячно).

Источник оценок: TradeInFunnel.
«Оценка» — дата начала оценки в периоде.
«Принята» — date_reception_success (не 01.01.0001).
ЦГ — zg_name из воронки (ЦНА), иначе пересчёт по цене теми же порогами.

Autohub: regEstimationRefCarsOrganizations — сегменты склада с дедупом,
ЦГ по avg_price теми же порогами.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Optional

from dateutil.relativedelta import relativedelta
from django.db.models import Q

from analytics.models import TradeInFunnel
from refs.price_groups import (
    PRICE_GROUP_RANGES,
    ZG_ORDER,
    normalize_price_group_display as normalize_zg_name,
    zg_display_from_price as zg_from_price,
)

DATE_INVALID = datetime(1, 1, 1)

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

UNIT_COLORS = [
    '#2563eb', '#16a34a', '#dc2626', '#9333ea', '#ea580c',
    '#0891b2', '#ca8a04', '#db2777', '#4f46e5', '#059669',
    '#e11d48', '#7c3aed', '#0d9488', '#d97706', '#64748b',
    '#0284c7', '#65a30d', '#c026d3', '#f59e0b', '#475569',
]


def _unit_color(index: int) -> str:
    return UNIT_COLORS[index % len(UNIT_COLORS)]


def _unit_label(unit_id, unit_name: Optional[str] = None) -> str:
    name = (unit_name or '').strip()
    if name:
        return name
    if unit_id:
        return f'ДЦ #{unit_id}'
    return 'Без ДЦ'


def normalize_chart_view(raw) -> str:
    v = str(raw or 'zg').strip().lower()
    return 'unit' if v in ('unit', 'dc', 'units', 'дц') else 'zg'


def _median(values) -> float:
    vals = [float(v) for v in values if v is not None]
    if not vals:
        return 0.0
    vals.sort()
    n = len(vals)
    mid = n // 2
    if n % 2:
        return vals[mid]
    return (vals[mid - 1] + vals[mid]) / 2.0


def _segment_key(car) -> str:
    """Ключ сегмента рынка: поколение Autoru, иначе modification_id / car_id."""
    if car is None:
        return 'unknown'
    mod = getattr(car, 'modification_autoru', None)
    if mod is not None:
        gen = getattr(mod, 'idSiteGeneration', None) or 0
        mark = 0
        model = 0
        try:
            mark = mod.model.mark_id or 0
            model = mod.model_id or 0
        except Exception:
            pass
        if gen or mark or model:
            return f'g:{gen}|m:{mark}|md:{model}'
        if mod.pk:
            return f'mod:{mod.pk}'
    return f'car:{car.pk}'


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


def normalize_accepted_filter(raw) -> str:
    """Фильтр принятия: all | yes | no."""
    v = str(raw or 'all').strip().lower()
    if v in ('yes', '1', 'да', 'accepted', 'true'):
        return 'yes'
    if v in ('no', '0', 'нет', 'rejected', 'false'):
        return 'no'
    return 'all'


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


def _cell(total: int, accepted: int, month_key: str = '') -> dict:
    return {
        'total': total,
        'accepted': accepted,
        'rate': _pct(accepted, total),
        'empty': total <= 0,
        'month_key': month_key,
    }


def _build_estimation_unit_breakdown(
    unit_bucket,
    unit_names: dict,
    month_keys: list,
    month_labels: list,
    month_totals: dict,
) -> dict:
    """График и сводная таблица: месяцы × ДЦ (оценки)."""
    unit_totals = defaultdict(lambda: {'total': 0, 'accepted': 0})
    for mk in month_keys:
        for uid, cell in unit_bucket[mk].items():
            unit_totals[uid]['total'] += cell['total']
            unit_totals[uid]['accepted'] += cell['accepted']

    unit_list = sorted(
        unit_totals.keys(),
        key=lambda u: (-unit_totals[u]['total'], _unit_label(u, unit_names.get(u))),
    )

    datasets = []
    for i, uid in enumerate(unit_list):
        label = _unit_label(uid, unit_names.get(uid))
        datasets.append({
            'label': label,
            'unit_id': uid,
            'backgroundColor': _unit_color(i),
            'data': [unit_bucket[mk][uid]['total'] for mk in month_keys],
            'accepted': [unit_bucket[mk][uid]['accepted'] for mk in month_keys],
            'rate': [
                _pct(unit_bucket[mk][uid]['accepted'], unit_bucket[mk][uid]['total'])
                for mk in month_keys
            ],
        })

    pivot_rows = []
    for uid in unit_list:
        cells = []
        for mk in month_keys:
            cell = unit_bucket[mk][uid]
            cells.append(_cell(cell['total'], cell['accepted'], mk))
        ut = unit_totals[uid]
        pivot_rows.append({
            'unit_id': uid,
            'unit_name': _unit_label(uid, unit_names.get(uid)),
            'cells': cells,
            'total': _cell(ut['total'], ut['accepted']),
        })

    footer_cells = [
        _cell(month_totals[mk]['total'], month_totals[mk]['accepted'], mk)
        for mk in month_keys
    ]
    grand_total = sum(v['total'] for v in month_totals.values())
    grand_accepted = sum(v['accepted'] for v in month_totals.values())
    pivot_footer = {
        'unit_name': 'Итого',
        'cells': footer_cells,
        'total': _cell(grand_total, grand_accepted),
        'is_total': True,
    }

    return {
        'labels': month_labels,
        'month_keys': month_keys,
        'datasets': datasets,
        'month_totals': [month_totals[mk]['total'] for mk in month_keys],
        'pivot_rows': pivot_rows,
        'pivot_footer': pivot_footer,
    }


def build_estimation_zg_analytics(
    *,
    date_start: datetime,
    date_end: datetime,
    unit_id: Optional[int] = None,
    staff_id: Optional[int] = None,
    analyst_id: Optional[int] = None,
    type_id: Optional[int] = None,
    accepted: Optional[str] = None,
) -> dict:
    accepted_filter = normalize_accepted_filter(accepted)

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
    unit_bucket = defaultdict(lambda: defaultdict(lambda: {'total': 0, 'accepted': 0}))
    unit_names = {}
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
        'unit_id',
        'unit_name',
    )

    for row in rows.iterator(chunk_size=2000):
        if not row.date_start_estimation:
            continue
        acc = is_accepted(row)
        if accepted_filter == 'yes' and not acc:
            continue
        if accepted_filter == 'no' and acc:
            continue
        mk = _month_key(row.date_start_estimation)
        zg = normalize_zg_name(row.zg_name, resolve_funnel_price(row))
        accepted_n = 1 if acc else 0
        bucket[mk][zg]['total'] += 1
        bucket[mk][zg]['accepted'] += accepted_n
        zg_totals[zg]['total'] += 1
        zg_totals[zg]['accepted'] += accepted_n
        month_totals[mk]['total'] += 1
        month_totals[mk]['accepted'] += accepted_n
        if not unit_id:
            uid = int(row.unit_id or 0)
            if row.unit_name:
                unit_names[uid] = str(row.unit_name).strip()
            unit_bucket[mk][uid]['total'] += 1
            unit_bucket[mk][uid]['accepted'] += accepted_n

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
            cells.append(_cell(cell['total'], cell['accepted'], mk))
        zt = zg_totals[zg]
        pivot_rows.append({
            'zg': zg,
            'cells': cells,
            'total': _cell(zt['total'], zt['accepted']),
        })

    footer_cells = [
        _cell(month_totals[mk]['total'], month_totals[mk]['accepted'], mk)
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

    unit_breakdown = None
    if not unit_id:
        unit_breakdown = _build_estimation_unit_breakdown(
            unit_bucket,
            unit_names,
            month_keys,
            month_labels,
            month_totals,
        )

    return {
        'month_keys': month_keys,
        'month_labels': month_labels,
        'zg_list': zg_list,
        'chart': {
            'labels': month_labels,
            'month_keys': month_keys,
            'datasets': datasets,
            'month_totals': [month_totals[mk]['total'] for mk in month_keys],
        },
        'unit_chart': unit_breakdown,
        'unit_pivot_rows': (unit_breakdown or {}).get('pivot_rows', []),
        'unit_pivot_footer': (unit_breakdown or {}).get('pivot_footer'),
        'pivot_rows': pivot_rows,
        'pivot_footer': pivot_footer,
        'zg_summary': zg_summary,
        'summary': {
            'total': grand_total,
            'accepted': grand_accepted,
            'rate': _pct(grand_accepted, grand_total),
            'months': len(month_keys),
        },
        'accepted_filter': accepted_filter,
        'month_keys': month_keys,
    }


def _hub_cell(segments_count, totals, days, avgs, above_n=0, month_key: str = '') -> dict:
    n = int(segments_count or 0)
    empty = n <= 0
    return {
        'segments': n,
        'med_total': round(_median(totals)) if not empty else 0,
        'med_days': round(_median(days), 1) if not empty else 0,
        'med_avg': round(_median(avgs)) if not empty else 0,
        'above_share': _pct(above_n, n) if not empty else 0,
        'empty': empty,
        'month_key': month_key,
    }


def build_autohub_zg_analytics(
    *,
    date_start: datetime,
    date_end: datetime,
    unit_id: Optional[int] = None,
) -> dict:
    """
    Autohub-снимки склада (regEstimationRefCarsOrganizations) по ЦГ × месяц.

    ЦГ — по avg_price (средняя рынка в сегменте), пороги как у ЦНА.
    Дедуп: в месяце один сегмент (поколение/марка+модель) → последний снимок.
    Метрики ячейки: число сегментов, медиана total / avg_days / avg_price,
    доля снимков где наша price > avg_price.
    """
    from register.models import RegEstimationRefCarsOrganizations

    qs = RegEstimationRefCarsOrganizations.objects.filter(
        date__gte=date_start,
        date__lte=date_end,
        avg_price__gt=0,
    ).select_related(
        'car',
        'car__modification_autoru',
        'car__modification_autoru__model',
        'car__modification_autoru__model__mark',
        'car__unit',
    )

    if unit_id:
        qs = qs.filter(car__unit_id=unit_id)

    # (month, segment) -> latest snapshot fields
    latest = {}
    for row in qs.iterator(chunk_size=2000):
        if not row.date:
            continue
        mk = _month_key(row.date)
        seg = _segment_key(row.car)
        key = (mk, seg)
        prev = latest.get(key)
        if prev is None or row.date > prev['date']:
            latest[key] = {
                'date': row.date,
                'avg_price': row.avg_price or 0,
                'avg_days': row.avg_days or 0,
                'total': row.total or 0,
                'price': row.price or 0,
                'zg': zg_from_price(row.avg_price),
            }

    # month -> zg -> lists
    bucket = defaultdict(lambda: defaultdict(lambda: {
        'segments': 0,
        'totals': [],
        'days': [],
        'avgs': [],
        'above': 0,
    }))
    month_seg_count = defaultdict(int)

    for (mk, _seg), snap in latest.items():
        zg = snap['zg']
        cell = bucket[mk][zg]
        cell['segments'] += 1
        cell['totals'].append(snap['total'])
        cell['days'].append(snap['avg_days'])
        cell['avgs'].append(snap['avg_price'])
        if snap['price'] > 0 and snap['avg_price'] > 0 and snap['price'] > snap['avg_price']:
            cell['above'] += 1
        month_seg_count[mk] += 1

    months = _iter_months(date_start, date_end)
    month_keys = [_month_key(m) for m in months]
    month_labels = [_month_label(m) for m in months]

    seen = set()
    for mk in month_keys:
        seen.update(bucket[mk].keys())
    zg_list = [z for z in ZG_ORDER if z in seen]
    if not zg_list:
        zg_list = [row['name'] for row in PRICE_GROUP_RANGES]

    datasets = []
    for zg in zg_list:
        datasets.append({
            'label': f'ЦГ {zg}',
            'zg': zg,
            'backgroundColor': ZG_COLORS.get(zg, '#94a3b8'),
            'data': [bucket[mk][zg]['segments'] for mk in month_keys],
        })

    pivot_rows = []
    zg_period = defaultdict(lambda: {
        'segments': 0, 'totals': [], 'days': [], 'avgs': [], 'above': 0,
    })
    for zg in zg_list:
        cells = []
        for mk in month_keys:
            b = bucket[mk][zg]
            cells.append(_hub_cell(
                b['segments'], b['totals'], b['days'], b['avgs'], b['above'], mk,
            ))
            if b['segments']:
                zg_period[zg]['segments'] += b['segments']
                zg_period[zg]['totals'].extend(b['totals'])
                zg_period[zg]['days'].extend(b['days'])
                zg_period[zg]['avgs'].extend(b['avgs'])
                zg_period[zg]['above'] += b['above']
        zp = zg_period[zg]
        pivot_rows.append({
            'zg': zg,
            'cells': cells,
            'total': _hub_cell(
                zp['segments'], zp['totals'], zp['days'], zp['avgs'], zp['above'],
            ),
        })

    footer_cells = []
    all_totals, all_days, all_avgs = [], [], []
    all_segments = 0
    all_above = 0
    for mk in month_keys:
        totals, days, avgs = [], [], []
        segs = 0
        above = 0
        for zg in zg_list:
            b = bucket[mk][zg]
            segs += b['segments']
            totals.extend(b['totals'])
            days.extend(b['days'])
            avgs.extend(b['avgs'])
            above += b['above']
        footer_cells.append(_hub_cell(segs, totals, days, avgs, above, mk))
        all_segments += segs
        all_totals.extend(totals)
        all_days.extend(days)
        all_avgs.extend(avgs)
        all_above += above

    pivot_footer = {
        'zg': 'Итого',
        'cells': footer_cells,
        'total': _hub_cell(all_segments, all_totals, all_days, all_avgs, all_above),
        'is_total': True,
    }

    return {
        'month_keys': month_keys,
        'month_labels': month_labels,
        'zg_list': zg_list,
        'chart': {
            'labels': month_labels,
            'month_keys': month_keys,
            'datasets': datasets,
            'month_totals': [month_seg_count[mk] for mk in month_keys],
        },
        'pivot_rows': pivot_rows,
        'pivot_footer': pivot_footer,
        'summary': {
            'segments': all_segments,
            'med_total': round(_median(all_totals)) if all_totals else 0,
            'med_days': round(_median(all_days), 1) if all_days else 0,
            'med_avg': round(_median(all_avgs)) if all_avgs else 0,
            'above_share': _pct(all_above, all_segments),
            'months': len(month_keys),
        },
        'month_keys': month_keys,
    }


def _month_bounds(month_key: str):
    """YYYY-MM → (date_start, date_end) inclusive."""
    start = datetime.strptime(month_key + '-01', '%Y-%m-%d')
    end = (start + relativedelta(months=1)) - relativedelta(seconds=1)
    return start, end


def build_estimation_zg_detail(
    *,
    month_key: str,
    zg: str,
    unit_id: Optional[int] = None,
    staff_id: Optional[int] = None,
    analyst_id: Optional[int] = None,
    type_id: Optional[int] = None,
    accepted: Optional[str] = None,
) -> dict:
    """Список оценок за месяц × ЦГ."""
    date_start, date_end = _month_bounds(month_key)
    target_zg = normalize_zg_name(zg)
    accepted_filter = normalize_accepted_filter(accepted)

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

    rows = []
    accepted_n = 0
    for row in qs.order_by('-date_start_estimation').iterator(chunk_size=1000):
        row_zg = normalize_zg_name(row.zg_name, resolve_funnel_price(row))
        if row_zg != target_zg:
            continue
        acc = is_accepted(row)
        if accepted_filter == 'yes' and not acc:
            continue
        if accepted_filter == 'no' and acc:
            continue
        if acc:
            accepted_n += 1
        rows.append({
            'rlk_id': row.rlk_id,
            'rlk_number': row.rlk_number or '',
            'estimation_id': row.estimation_id,
            'vin': row.vin or '',
            'mark': row.mark_name or '',
            'model': row.model_name or '',
            'unit': row.unit_name or '',
            'staff': row.staff_name or '',
            'stage': row.stage or '',
            'zna': float(row.zna or 0),
            'price_before': float(row.price_before or 0),
            'price_after': float(row.price_after or 0),
            'zg': row_zg,
            'start_estimation': row.date_start_estimation,
            'date_reception': row.date_reception_success if acc else None,
            'accepted': acc,
        })

    return {
        'source': 'estimations',
        'month_key': month_key,
        'month_label': _month_label(date_start),
        'zg': target_zg,
        'rows': rows,
        'summary': {
            'total': len(rows),
            'accepted': accepted_n,
            'rate': _pct(accepted_n, len(rows)),
        },
    }


def build_autohub_zg_detail(
    *,
    month_key: str,
    zg: str,
    unit_id: Optional[int] = None,
) -> dict:
    """Список сегментов Autohub за месяц × ЦГ (после дедупа)."""
    from register.models import RegEstimationRefCarsOrganizations

    date_start, date_end = _month_bounds(month_key)
    target_zg = normalize_zg_name(zg)

    qs = RegEstimationRefCarsOrganizations.objects.filter(
        date__gte=date_start,
        date__lte=date_end,
        avg_price__gt=0,
    ).select_related(
        'car',
        'car__modification_autoru',
        'car__modification_autoru__model',
        'car__modification_autoru__model__mark',
        'car__unit',
    )
    if unit_id:
        qs = qs.filter(car__unit_id=unit_id)

    latest = {}
    for row in qs.iterator(chunk_size=2000):
        if not row.date:
            continue
        if _month_key(row.date) != month_key:
            continue
        seg = _segment_key(row.car)
        prev = latest.get(seg)
        if prev is None or row.date > prev['date']:
            car = row.car
            mark = ''
            model = ''
            mod_name = ''
            try:
                mark = car.modification_autoru.model.mark.name
                model = car.modification_autoru.model.name
                mod_name = car.modification_autoru.name
            except Exception:
                mark = getattr(car, 'mark', '') or ''
                model = getattr(car, 'model', '') or ''
                mod_name = getattr(car, 'modification', '') or ''
            latest[seg] = {
                'date': row.date,
                'segment': seg,
                'car_id': car.pk if car else None,
                'vin': (car.vin if car else '') or '',
                'unit': (car.unit.name if car and car.unit_id else '') or '',
                'mark': mark,
                'model': model,
                'modification': mod_name,
                'avg_price': row.avg_price or 0,
                'avg_days': row.avg_days or 0,
                'total': row.total or 0,
                'price': row.price or 0,
                'zg': zg_from_price(row.avg_price),
                'above': bool(row.price and row.avg_price and row.price > row.avg_price),
            }

    rows = [v for v in latest.values() if v['zg'] == target_zg]
    rows.sort(key=lambda x: (-x['total'], -x['avg_price']))

    above_n = sum(1 for r in rows if r['above'])
    return {
        'source': 'autohub',
        'month_key': month_key,
        'month_label': _month_label(date_start),
        'zg': target_zg,
        'rows': rows,
        'summary': {
            'segments': len(rows),
            'med_total': round(_median([r['total'] for r in rows])) if rows else 0,
            'med_days': round(_median([r['avg_days'] for r in rows]), 1) if rows else 0,
            'med_avg': round(_median([r['avg_price'] for r in rows])) if rows else 0,
            'above_share': _pct(above_n, len(rows)),
        },
    }
