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
from django.core.cache import cache
from django.db.models import F

from eco.estimation_zg_analytics import (
    _iter_months,
    _median,
    _month_key,
    _month_label,
    _segment_key,
)

_CACHE_TTL = 300  # 5 мин
_CACHE_VERSION = 'v2'


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


def _segment_key_from_ids(gen_id, mark_id, model_id, mod_pk, car_id) -> str:
    """Тот же ключ, что `_segment_key`, но из плоских id (без ORM)."""
    gen = gen_id or 0
    mark = mark_id or 0
    model = model_id or 0
    if gen or mark or model:
        return f'g:{gen}|m:{mark}|md:{model}'
    if mod_pk:
        return f'mod:{mod_pk}'
    if car_id:
        return f'car:{car_id}'
    return 'unknown'


def _ident_from_row(row: dict) -> dict:
    mark_name = (row.get('mark_name') or '').strip()
    model_name = (row.get('model_name') or '').strip()
    if not mark_name:
        mark_name = (row.get('car_mark') or '').strip() or '—'
    if not model_name:
        model_name = (row.get('car_model') or '').strip() or '—'
    return {
        'mark_id': row.get('mark_id') or 0,
        'model_id': row.get('model_id') or 0,
        'mark_name': mark_name,
        'model_name': model_name,
        'gen_id': row.get('gen_id') or 0,
        'gen_label': ((row.get('gen_label') or '')[:80]),
    }


def _load_latest_segments(
    date_start,
    date_end,
    unit_id=None,
    mark_id=None,
    model_id=None,
    mark_name=None,
    model_name=None,
    car_id=None,
):
    """(month, segment) -> snapshot dict with identity.

    Оптимизация: values()+annotate вместо select_related ORM-объектов;
    обход от новых к старым — первый снимок по ключу побеждает.
    """
    from register.models import RegEstimationRefCarsOrganizations

    qs = RegEstimationRefCarsOrganizations.objects.filter(
        date__gte=date_start,
        date__lte=date_end,
        avg_price__gt=0,
    )
    if car_id:
        qs = qs.filter(car_id=car_id)
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

    rows = (
        qs.annotate(
            gen_id=F('car__modification_autoru__idSiteGeneration'),
            mark_id=F('car__modification_autoru__model__mark_id'),
            model_id=F('car__modification_autoru__model_id'),
            mark_name=F('car__modification_autoru__model__mark__name'),
            model_name=F('car__modification_autoru__model__name'),
            gen_label=F('car__modification_autoru__name'),
            car_vin=F('car__vin'),
            unit_name=F('car__unit__name'),
            car_mark=F('car__mark'),
            car_model=F('car__model'),
            mod_pk=F('car__modification_autoru_id'),
        )
        .values(
            'date', 'avg_price', 'avg_days', 'total', 'price', 'car_id',
            'gen_id', 'mark_id', 'model_id', 'mark_name', 'model_name',
            'gen_label', 'car_vin', 'unit_name', 'car_mark', 'car_model', 'mod_pk',
        )
        .order_by('-date')
    )

    latest = {}
    for row in rows.iterator(chunk_size=4000):
        dt = row.get('date')
        if not dt or not row.get('car_id'):
            continue
        mk = _month_key(dt)
        seg = _segment_key_from_ids(
            row.get('gen_id'),
            row.get('mark_id'),
            row.get('model_id'),
            row.get('mod_pk'),
            row.get('car_id'),
        )
        key = (mk, seg)
        if key in latest:
            continue
        ident = _ident_from_row(row)
        latest[key] = {
            'date': dt,
            'month': mk,
            'segment': seg,
            'avg_price': row.get('avg_price') or 0,
            'avg_days': row.get('avg_days') or 0,
            'total': row.get('total') or 0,
            'price': row.get('price') or 0,
            'vin': (row.get('car_vin') or '') or '',
            'unit': (row.get('unit_name') or '') or '',
            'car_id': row.get('car_id'),
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


def _cache_key(prefix: str, **parts) -> str:
    bits = [_CACHE_VERSION, prefix]
    for k in sorted(parts.keys()):
        bits.append(f'{k}={parts[k]}')
    return 'mt:' + '|'.join(bits)


def build_market_model_trends(
    *,
    date_start: datetime,
    date_end: datetime,
    unit_id: Optional[int] = None,
    mark_id: Optional[int] = None,
    mark_q: str = '',
    sort: str = 'volatility',
    limit: int = 100,
    use_cache: bool = True,
) -> dict:
    ck = _cache_key(
        'list',
        ds=date_start.strftime('%Y-%m-%d'),
        de=date_end.strftime('%Y-%m-%d'),
        u=unit_id or 0,
        m=mark_id or 0,
        q=(mark_q or '').strip().lower(),
        s=sort,
        lim=limit or 0,
    )
    if use_cache:
        cached = cache.get(ck)
        if cached is not None:
            return cached

    latest = _load_latest_segments(
        date_start, date_end, unit_id=unit_id, mark_id=mark_id,
        mark_name=mark_q.strip() or None,
    )
    months = _iter_months(date_start, date_end)
    month_keys = [_month_key(m) for m in months]
    month_labels = [_month_label(m) for m in months]

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
        price_delta = _delta_pct(last['med_avg'], first['med_avg'])
        total_delta = _delta_pct(last['med_total'], first['med_total'])
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

    result = {
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
    if use_cache:
        cache.set(ck, result, _CACHE_TTL)
    return result


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


def build_market_car_trends(
    *,
    car,
    date_start: datetime,
    date_end: datetime,
) -> dict:
    """Тренд Autohub по конкретному авто + контекст модели/поколения."""
    from register.models import RegEstimationRefCarsOrganizations

    ident = _car_identity(car)
    car_seg = _segment_key(car)

    qs = (
        RegEstimationRefCarsOrganizations.objects
        .filter(
            car_id=car.pk,
            date__gte=date_start,
            date__lte=date_end,
            avg_price__gt=0,
        )
        .values('date', 'avg_price', 'avg_days', 'total', 'price', 'position')
        .order_by('date')
    )
    timeline = []
    for row in qs.iterator(chunk_size=500):
        dt = row.get('date')
        if not dt:
            continue
        timeline.append({
            'date': dt,
            'date_label': dt.strftime('%d.%m.%y'),
            'month': _month_key(dt),
            'avg_price': row.get('avg_price') or 0,
            'avg_days': row.get('avg_days') or 0,
            'total': row.get('total') or 0,
            'price': row.get('price') or 0,
            'position': row.get('position') or 0,
            'spread': (
                round(100.0 * ((row.get('price') or 0) - (row.get('avg_price') or 0)) / (row.get('avg_price') or 1), 1)
                if (row.get('avg_price') or 0) > 0 and (row.get('price') or 0) > 0
                else None
            ),
        })

    # Последний снимок в каждом месяце по этому авто
    months = _iter_months(date_start, date_end)
    month_keys = [_month_key(m) for m in months]
    month_labels = [_month_label(m) for m in months]
    by_month_last = {}
    for point in timeline:
        by_month_last[point['month']] = point

    car_series = []
    prev_avg = None
    for i, month in enumerate(month_keys):
        point = by_month_last.get(month)
        if not point:
            car_series.append({
                'month': month,
                'label': month_labels[i],
                'avg_price': None,
                'total': None,
                'days': None,
                'our_price': None,
                'spread': None,
                'delta': None,
                'has_data': False,
            })
            continue
        delta = _delta_pct(point['avg_price'], prev_avg)
        prev_avg = point['avg_price']
        car_series.append({
            'month': month,
            'label': month_labels[i],
            'avg_price': point['avg_price'],
            'total': point['total'],
            'days': point['avg_days'],
            'our_price': point['price'] or None,
            'spread': point['spread'],
            'delta': delta,
            'has_data': True,
        })

    # Контекст модели (все сегменты mark+model) и своего поколения
    model_detail = None
    if ident['mark_id'] or ident['model_id'] or (ident['mark_name'] and ident['model_name']):
        model_detail = build_market_model_detail(
            date_start=date_start,
            date_end=date_end,
            mark_id=ident['mark_id'] or None,
            model_id=ident['model_id'] or None,
            mark_name='' if ident['mark_id'] else ident['mark_name'],
            model_name='' if ident['model_id'] else ident['model_name'],
            unit_id=None,
        )

    gen_series = []
    if model_detail and ident['gen_id']:
        for gen in model_detail.get('generations') or []:
            if gen.get('gen_id') == ident['gen_id']:
                for i, month in enumerate(month_keys):
                    g = gen['series'][i] if i < len(gen['series']) else {}
                    gen_series.append({
                        'month': month,
                        'label': month_labels[i],
                        'avg_price': g.get('med_avg') if g.get('segments') else None,
                        'total': g.get('med_total') if g.get('segments') else None,
                    })
                break

    non_empty = [s for s in car_series if s['has_data']]
    overall_delta = None
    if len(non_empty) >= 2:
        overall_delta = _delta_pct(non_empty[-1]['avg_price'], non_empty[0]['avg_price'])

    last = non_empty[-1] if non_empty else None
    model_avg_by_month = {}
    if model_detail:
        for s in model_detail.get('series') or []:
            if s.get('segments'):
                model_avg_by_month[s['month']] = s['med_avg']

    for s in car_series:
        s['model_avg'] = model_avg_by_month.get(s['month'])

    chart = {
        'labels': [p['date_label'] for p in timeline],
        'avg_price': [p['avg_price'] for p in timeline],
        'our_price': [p['price'] if p['price'] else None for p in timeline],
        'total': [p['total'] for p in timeline],
        'days': [p['avg_days'] for p in timeline],
        'month_labels': month_labels,
        'month_avg': [s['avg_price'] for s in car_series],
        'month_our': [s['our_price'] for s in car_series],
        'month_model_avg': [model_avg_by_month.get(m) for m in month_keys],
        'month_gen_avg': [s['avg_price'] for s in gen_series] if gen_series else [],
    }

    return {
        'car': {
            'id': car.pk,
            'slug': getattr(car, 'slug', '') or '',
            'vin': getattr(car, 'vin', '') or '',
            'title': f"{ident['mark_name']} {ident['model_name']}".strip(),
            'unit': (car.unit.name if getattr(car, 'unit_id', None) else '') or '',
            'price': getattr(car, 'price', None) or 0,
            'days_in_stok': getattr(car, 'days_in_stok', None) or 0,
            **ident,
            'segment': car_seg,
        },
        'month_keys': month_keys,
        'month_labels': month_labels,
        'timeline': timeline,
        'car_series': car_series,
        'gen_series': gen_series,
        'model_detail': model_detail,
        'chart': chart,
        'summary': {
            'snapshots': len(timeline),
            'months_with_data': len(non_empty),
            'overall_delta': overall_delta,
            'last_avg': last['avg_price'] if last else 0,
            'last_total': last['total'] if last else 0,
            'last_days': last['days'] if last else 0,
            'last_our': last['our_price'] if last else 0,
            'last_spread': last['spread'] if last else None,
        },
    }


def _parse_trend_date(value, default, is_end=False):
    if not value:
        return default
    try:
        year, month, day = [int(part) for part in value.split('-')]
        parsed = default.replace(year=year, month=month, day=day)
        if is_end:
            parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=0)
        else:
            parsed = parsed.replace(hour=0, minute=0, second=0, microsecond=0)
        return parsed
    except Exception:
        return default


def market_car_trends_page_params(car, request, *, embedded=False):
    """Контекст страницы / встраивания тренда рынка по автомобилю."""
    import json as _json
    from urllib.parse import urlencode

    now = datetime.now()
    default_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    default_start = (now - relativedelta(months=5)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    date_start = _parse_trend_date(request.GET.get('date_start', ''), default_start, is_end=False)
    date_end = _parse_trend_date(request.GET.get('date_end', ''), default_end, is_end=True)

    data = build_market_car_trends(car=car, date_start=date_start, date_end=date_end)

    model_url = ''
    if data['car']['mark_id'] or data['car']['model_id']:
        qs = {k: v for k, v in {
            'mark_id': data['car']['mark_id'] or '',
            'model_id': data['car']['model_id'] or '',
            'mark': data['car']['mark_name'],
            'model': data['car']['model_name'],
            'date_start': date_start.strftime('%Y-%m-%d'),
            'date_end': date_end.strftime('%Y-%m-%d'),
        }.items() if v}
        model_url = '/eco/market-trends/model/?' + urlencode(qs)

    slug = getattr(car, 'slug', '') or ''
    return {
        'data': data,
        'chart_json': _json.dumps(data['chart'], ensure_ascii=False),
        'filters': {
            'date_start': date_start.strftime('%Y-%m-%d'),
            'date_end': date_end.strftime('%Y-%m-%d'),
        },
        'price_edit_url': f'/cars/{slug}/price_edit/?page=12',
        'model_url': model_url,
        'list_url': '/eco/market-trends/',
        'embedded': embedded,
    }
