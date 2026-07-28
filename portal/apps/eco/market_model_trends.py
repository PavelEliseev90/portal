"""Тренд рынка Autohub по маркам/моделям (помесячно).

Источник: regEstimationRefCarsOrganizations.
В месяце сегмент (поколение) — один раз (последний снимок).
По модели: медианы avg_price / total / avg_days / нашей price.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Optional

from dateutil.relativedelta import relativedelta

from eco.estimation_zg_analytics import (
    _iter_months,
    _median,
    _month_key,
    _month_label,
    _pct,
    _segment_key,
)


def _car_identity(car):
    mark_id = model_id = 0
    mark_name = model_name = ''
    gen_id = 0
    gen_label = ''
    if car is None:
        return {
            'mark_id': 0, 'model_id': 0, 'mark_name': '—', 'model_name': '—',
            'gen_id': 0, 'gen_label': '',
        }
    mod = getattr(car, 'modification_autoru', None)
    if mod is not None:
        gen_id = getattr(mod, 'idSiteGeneration', None) or 0
        try:
            model = mod.model
            mark = model.mark if model else None
            model_id = model.pk if model else 0
            mark_id = mark.pk if mark else 0
            model_name = (model.name if model else '') or ''
            mark_name = (mark.name if mark else '') or ''
        except Exception:
            pass
        gen_label = (getattr(mod, 'name', '') or '')[:80]
    if not mark_name:
        mark_name = (getattr(car, 'mark', '') or '').strip() or '—'
    if not model_name:
        model_name = (getattr(car, 'model', '') or '').strip() or '—'
    return {
        'mark_id': mark_id or 0,
        'model_id': model_id or 0,
        'mark_name': mark_name,
        'model_name': model_name,
        'gen_id': gen_id or 0,
        'gen_label': gen_label,
    }


def _model_key(ident) -> str:
    if ident['mark_id'] and ident['model_id']:
        return f"id:{ident['mark_id']}:{ident['model_id']}"
    return f"name:{(ident['mark_name'] or '').lower()}:{(ident['model_name'] or '').lower()}"


def _delta_pct(curr, prev) -> Optional[float]:
    if prev is None or prev == 0 or curr is None:
        return None
    return round(100.0 * (curr - prev) / prev, 1)


def _load_latest_segments(date_start, date_end, unit_id=None, mark_id=None, model_id=None, mark_name=None, model_name=None):
    """(month, segment) -> snapshot dict with identity."""
    from register.models import RegEstimationRefCarsOrganizations

    qs = RegEstimationRefCarsOrganizations.objects.filter(
        date__gte=date_start,
        date__lte=date_end,
        avg_price__gt=0,
    ).select_related(
        'car',
        'car__unit',
        'car__modification_autoru',
        'car__modification_autoru__model',
        'car__modification_autoru__model__mark',
    )
    if unit_id:
        qs = qs.filter(car__unit_id=unit_id)
    if mark_id:
        qs = qs.filter(car__modification_autoru__model__mark_id=mark_id)
    if model_id:
        qs = qs.filter(car__modification_autoru__model_id=model_id)
    if mark_name and not mark_id:
        qs = qs.filter(car__modification_autoru__model__mark__name__iexact=mark_name)
    if model_name and not model_id:
        qs = qs.filter(car__modification_autoru__model__name__iexact=model_name)

    latest = {}
    for row in qs.iterator(chunk_size=2000):
        if not row.date or not row.car_id:
            continue
        mk = _month_key(row.date)
        seg = _segment_key(row.car)
        key = (mk, seg)
        prev = latest.get(key)
        if prev is not None and row.date <= prev['date']:
            continue
        ident = _car_identity(row.car)
        latest[key] = {
            'date': row.date,
            'month': mk,
            'segment': seg,
            'avg_price': row.avg_price or 0,
            'avg_days': row.avg_days or 0,
            'total': row.total or 0,
            'price': row.price or 0,
            'vin': (row.car.vin if row.car else '') or '',
            'unit': (row.car.unit.name if row.car and row.car.unit_id else '') or '',
            **ident,
            'model_key': _model_key(ident),
        }
    return latest


def _agg_month_metrics(snaps):
    if not snaps:
        return {
            'segments': 0,
            'med_avg': 0,
            'med_total': 0,
            'med_days': 0.0,
            'med_our': 0,
        }
    return {
        'segments': len(snaps),
        'med_avg': round(_median([s['avg_price'] for s in snaps])),
        'med_total': round(_median([s['total'] for s in snaps])),
        'med_days': round(_median([s['avg_days'] for s in snaps]), 1),
        'med_our': round(_median([s['price'] for s in snaps if s.get('price')])),
    }


def build_market_model_trends(
    *,
    date_start: datetime,
    date_end: datetime,
    unit_id: Optional[int] = None,
    mark_id: Optional[int] = None,
    mark_q: str = '',
    sort: str = 'volatility',
    limit: int = 100,
) -> dict:
    latest = _load_latest_segments(
        date_start, date_end, unit_id=unit_id, mark_id=mark_id,
        mark_name=mark_q.strip() or None,
    )
    months = _iter_months(date_start, date_end)
    month_keys = [_month_key(m) for m in months]
    month_labels = [_month_label(m) for m in months]

    # model_key -> month -> list snaps
    by_model = defaultdict(lambda: defaultdict(list))
    meta = {}
    for snap in latest.values():
        mk = snap['model_key']
        by_model[mk][snap['month']].append(snap)
        if mk not in meta:
            meta[mk] = {
                'mark_id': snap['mark_id'],
                'model_id': snap['model_id'],
                'mark_name': snap['mark_name'],
                'model_name': snap['model_name'],
                'model_key': mk,
            }

    rows = []
    for mk, month_map in by_model.items():
        series = []
        for month in month_keys:
            metrics = _agg_month_metrics(month_map.get(month) or [])
            series.append({'month': month, **metrics})

        non_empty = [s for s in series if s['segments'] > 0]
        if len(non_empty) < 1:
            continue
        first = non_empty[0]
        last = non_empty[-1]
        # Δ между первым и последним месяцем с данными
        price_delta = _delta_pct(last['med_avg'], first['med_avg'])
        total_delta = _delta_pct(last['med_total'], first['med_total'])
        # Δ последний vs предыдущий с данными
        mom_delta = None
        if len(non_empty) >= 2:
            mom_delta = _delta_pct(non_empty[-1]['med_avg'], non_empty[-2]['med_avg'])

        coverage = sum(1 for s in series if s['segments'] > 0)
        rows.append({
            **meta[mk],
            'series': series,
            'first_avg': first['med_avg'],
            'last_avg': last['med_avg'],
            'price_delta': price_delta,
            'total_delta': total_delta,
            'mom_delta': mom_delta,
            'last_total': last['med_total'],
            'last_days': last['med_days'],
            'last_our': last['med_our'],
            'coverage_months': coverage,
            'segments_total': sum(s['segments'] for s in series),
            'abs_delta': abs(price_delta) if price_delta is not None else -1,
        })

    if sort == 'coverage':
        rows.sort(key=lambda r: (-r['coverage_months'], -r['segments_total'], r['mark_name'], r['model_name']))
    elif sort == 'price_up':
        rows.sort(key=lambda r: (
            r['price_delta'] is None,
            -(r['price_delta'] or 0),
            r['mark_name'], r['model_name'],
        ))
    elif sort == 'price_down':
        rows.sort(key=lambda r: (
            r['price_delta'] is None,
            (r['price_delta'] if r['price_delta'] is not None else 9999),
            r['mark_name'], r['model_name'],
        ))
    else:  # volatility
        rows.sort(key=lambda r: (-r['abs_delta'], -r['coverage_months'], r['mark_name'], r['model_name']))

    if limit and limit > 0:
        rows = rows[:limit]

    rising = sum(1 for r in rows if (r['price_delta'] or 0) > 1)
    falling = sum(1 for r in rows if (r['price_delta'] or 0) < -1)
    flat = sum(1 for r in rows if r['price_delta'] is not None and abs(r['price_delta']) <= 1)

    return {
        'month_keys': month_keys,
        'month_labels': month_labels,
        'rows': rows,
        'summary': {
            'models': len(rows),
            'rising': rising,
            'falling': falling,
            'flat': flat,
            'months': len(month_keys),
        },
    }


def build_market_model_detail(
    *,
    date_start: datetime,
    date_end: datetime,
    mark_id: Optional[int] = None,
    model_id: Optional[int] = None,
    mark_name: str = '',
    model_name: str = '',
    unit_id: Optional[int] = None,
) -> dict:
    latest = _load_latest_segments(
        date_start, date_end,
        unit_id=unit_id,
        mark_id=mark_id,
        model_id=model_id,
        mark_name=mark_name or None,
        model_name=model_name or None,
    )
    months = _iter_months(date_start, date_end)
    month_keys = [_month_key(m) for m in months]
    month_labels = [_month_label(m) for m in months]

    by_month = defaultdict(list)
    by_month_gen = defaultdict(lambda: defaultdict(list))
    title_mark = mark_name or ''
    title_model = model_name or ''
    for snap in latest.values():
        if mark_id and snap['mark_id'] != mark_id:
            continue
        if model_id and snap['model_id'] != model_id:
            continue
        if mark_name and not mark_id and snap['mark_name'].lower() != mark_name.lower():
            continue
        if model_name and not model_id and snap['model_name'].lower() != model_name.lower():
            continue
        by_month[snap['month']].append(snap)
        gen_key = snap['gen_id'] or snap['segment']
        by_month_gen[snap['month']][gen_key].append(snap)
        title_mark = snap['mark_name'] or title_mark
        title_model = snap['model_name'] or title_model

    series = []
    prev_avg = None
    for i, month in enumerate(month_keys):
        metrics = _agg_month_metrics(by_month.get(month) or [])
        delta = _delta_pct(metrics['med_avg'], prev_avg) if metrics['segments'] else None
        if metrics['segments']:
            prev_avg = metrics['med_avg']
        spread = None
        if metrics['med_avg'] and metrics['med_our']:
            spread = round(100.0 * (metrics['med_our'] - metrics['med_avg']) / metrics['med_avg'], 1)
        series.append({
            'month': month,
            'label': month_labels[i],
            **metrics,
            'delta': delta,
            'spread': spread,
        })

    # generations: list with monthly series condensed
    gen_meta = {}
    gen_month = defaultdict(lambda: defaultdict(list))
    for snap in latest.values():
        if mark_id and snap['mark_id'] != mark_id:
            continue
        if model_id and snap['model_id'] != model_id:
            continue
        gk = str(snap['gen_id'] or snap['segment'])
        gen_month[gk][snap['month']].append(snap)
        if gk not in gen_meta:
            gen_meta[gk] = {
                'gen_id': snap['gen_id'],
                'gen_label': snap['gen_label'] or f"поколение {snap['gen_id'] or '—'}",
            }

    generations = []
    for gk, month_map in gen_month.items():
        g_series = []
        for month in month_keys:
            g_series.append({'month': month, **_agg_month_metrics(month_map.get(month) or [])})
        non_empty = [s for s in g_series if s['segments'] > 0]
        if not non_empty:
            continue
        first, last = non_empty[0], non_empty[-1]
        generations.append({
            **gen_meta[gk],
            'series': g_series,
            'first_avg': first['med_avg'],
            'last_avg': last['med_avg'],
            'price_delta': _delta_pct(last['med_avg'], first['med_avg']),
            'last_total': last['med_total'],
            'segments_total': sum(s['segments'] for s in g_series),
        })
    generations.sort(key=lambda g: (-g['segments_total'], g['gen_label']))

    chart = {
        'labels': month_labels,
        'month_keys': month_keys,
        'avg_price': [s['med_avg'] if s['segments'] else None for s in series],
        'total': [s['med_total'] if s['segments'] else None for s in series],
        'our_price': [s['med_our'] if s['segments'] and s['med_our'] else None for s in series],
        'days': [s['med_days'] if s['segments'] else None for s in series],
    }

    non_empty = [s for s in series if s['segments'] > 0]
    overall_delta = None
    if len(non_empty) >= 2:
        overall_delta = _delta_pct(non_empty[-1]['med_avg'], non_empty[0]['med_avg'])

    return {
        'mark_name': title_mark or '—',
        'model_name': title_model or '—',
        'mark_id': mark_id or 0,
        'model_id': model_id or 0,
        'month_keys': month_keys,
        'month_labels': month_labels,
        'series': series,
        'generations': generations,
        'chart': chart,
        'summary': {
            'months_with_data': len(non_empty),
            'overall_delta': overall_delta,
            'last_avg': non_empty[-1]['med_avg'] if non_empty else 0,
            'last_total': non_empty[-1]['med_total'] if non_empty else 0,
            'last_days': non_empty[-1]['med_days'] if non_empty else 0,
            'segments': sum(s['segments'] for s in series),
        },
    }


def build_market_model_month_detail(
    *,
    month_key: str,
    mark_id: Optional[int] = None,
    model_id: Optional[int] = None,
    mark_name: str = '',
    model_name: str = '',
    unit_id: Optional[int] = None,
) -> dict:
    start = datetime.strptime(month_key + '-01', '%Y-%m-%d')
    end = (start + relativedelta(months=1)) - relativedelta(seconds=1)
    latest = _load_latest_segments(
        start, end,
        unit_id=unit_id,
        mark_id=mark_id,
        model_id=model_id,
        mark_name=mark_name or None,
        model_name=model_name or None,
    )
    rows = sorted(latest.values(), key=lambda s: (-s['avg_price'], s['mark_name'], s['model_name']))
    title_mark = mark_name
    title_model = model_name
    if rows:
        title_mark = rows[0]['mark_name']
        title_model = rows[0]['model_name']
    metrics = _agg_month_metrics(rows)
    return {
        'month_key': month_key,
        'month_label': _month_label(start),
        'mark_name': title_mark or '—',
        'model_name': title_model or '—',
        'rows': rows,
        'summary': metrics,
    }
