"""Аналитика запросов повышения цены по интерактивным оценкам."""
from __future__ import annotations

from collections import defaultdict
from typing import Optional

from django.db.models import Prefetch

from refs.price_groups import (
    ZG_ORDER,
    normalize_price_group_display as normalize_zg_name,
    zg_display_from_price,
)
from register.models import (
    RegInteractivOcenkaPriceIncreaseRequest,
    RegInteractivOcenkaRLK,
)

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

TOP_BADGE_META = (
    {'rank': 1, 'label': 'Топ-1', 'class': 'badge-top-1'},
    {'rank': 2, 'label': 'Топ-2', 'class': 'badge-top-2'},
    {'rank': 3, 'label': 'Топ-3', 'class': 'badge-top-3'},
)


def _safe_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _base_price(soglasovanie) -> float:
    if soglasovanie is None:
        return 0.0
    for attr in ('price_zna_2', 'price_after_kd', 'price_before_kd', 'price_reception'):
        num = _safe_float(getattr(soglasovanie, attr, 0))
        if num > 0:
            return num
    return 0.0


def _unit_label(unit_id, unit_name: Optional[str] = None) -> str:
    name = (unit_name or '').strip()
    if name:
        return name
    if unit_id:
        return f'ДЦ #{unit_id}'
    return 'Без ДЦ'


def _resolve_interactiv_rlk(soglasovanie):
    if soglasovanie is None:
        return None
    related = getattr(soglasovanie, '_prefetched_objects_cache', {}).get('reginteractivocenkarlk_set')
    if related is not None:
        return related[0] if related else None
    return (
        RegInteractivOcenkaRLK.objects
        .filter(page_soglasovanie=soglasovanie)
        .select_related('unit', 'rlk', 'estimation', 'staff_rlk')
        .first()
    )


def _car_title(estimation) -> str:
    if estimation is None:
        return '—'
    mark = (getattr(estimation, 'mark_name', '') or '').strip()
    model = (getattr(estimation, 'model_name', '') or '').strip()
    if mark or model:
        return f'{mark} {model}'.strip()
    try:
        mod = estimation.modification
        if mod is not None:
            return str(mod)
    except Exception:
        pass
    return '—'


def _user_label(user) -> str:
    if user is None:
        return '—'
    eco_name = ''
    try:
        eco_name = (user.profiles.eco_name or '').strip()
    except Exception:
        eco_name = ''
    if eco_name:
        return eco_name
    name = f'{user.last_name or ""} {user.first_name or ""}'.strip()
    return name or user.username or '—'


def _queryset(date_start, date_end, unit_id=None):
    qs = (
        RegInteractivOcenkaPriceIncreaseRequest.objects
        .filter(created_at__gte=date_start, created_at__lte=date_end)
        .select_related(
            'user',
            'user__profiles',
            'soglasovanie',
            'soglasovanie__reginteractivocenka',
        )
        .prefetch_related(
            Prefetch(
                'soglasovanie__reginteractivocenkarlk_set',
                queryset=RegInteractivOcenkaRLK.objects.select_related(
                    'unit', 'rlk', 'estimation', 'staff_rlk',
                ),
            )
        )
        .order_by('-created_at')
    )
    # unit_id=0 — только запросы без подразделения
    if unit_id == 0:
        qs = qs.filter(
            soglasovanie__reginteractivocenkarlk__unit__isnull=True
        ).distinct()
    elif unit_id:
        qs = qs.filter(soglasovanie__reginteractivocenkarlk__unit_id=unit_id).distinct()
    return qs


def _serialize_row(req) -> dict:
    sog = req.soglasovanie
    interactiv = _resolve_interactiv_rlk(sog)
    estimation = None
    if interactiv is not None and interactiv.estimation_id:
        estimation = interactiv.estimation
    if estimation is None and sog is not None:
        estimation = getattr(sog, 'reginteractivocenka', None)

    unit = getattr(interactiv, 'unit', None) if interactiv else None
    unit_id = unit.pk if unit else None
    unit_name = unit.name if unit else ''
    rlk = getattr(interactiv, 'rlk', None) if interactiv else None
    base = _base_price(sog)
    desired = int(req.desired_price or 0)
    delta = desired - int(base) if base > 0 and desired > 0 else None
    zg = zg_display_from_price(base if base > 0 else desired)
    zg = normalize_zg_name(zg) or 'Неопределена'

    return {
        'id': req.pk,
        'created_at': req.created_at,
        'desired_price': desired,
        'base_price': int(base) if base > 0 else 0,
        'delta': delta,
        'comment': (req.comment or '').strip(),
        'user_name': _user_label(req.user),
        'unit_id': unit_id,
        'unit_name': _unit_label(unit_id, unit_name),
        'rlk_id': rlk.pk if rlk else None,
        'rlk_number': getattr(rlk, 'nomer', '') if rlk else '',
        'estimation_id': estimation.pk if estimation else None,
        'car': _car_title(estimation),
        'vin': (getattr(estimation, 'vin', '') or '') if estimation else '',
        'zg': zg,
        'staff': getattr(getattr(interactiv, 'staff_rlk', None), 'name', '') if interactiv else '',
    }


def build_price_increase_analytics(date_start, date_end, unit_id=None) -> dict:
    rows = [_serialize_row(req) for req in _queryset(date_start, date_end, unit_id=unit_id)]

    by_zg = defaultdict(lambda: {'count': 0, 'desired_sum': 0, 'delta_sum': 0, 'delta_n': 0})
    by_unit = defaultdict(lambda: {
        'unit_id': None,
        'unit_name': 'Без ДЦ',
        'count': 0,
        'desired_sum': 0,
        'delta_sum': 0,
        'delta_n': 0,
        'zg_counts': defaultdict(int),
    })

    for row in rows:
        zg = row['zg']
        by_zg[zg]['count'] += 1
        by_zg[zg]['desired_sum'] += row['desired_price']
        if row['delta'] is not None:
            by_zg[zg]['delta_sum'] += row['delta']
            by_zg[zg]['delta_n'] += 1

        key = row['unit_id'] or 0
        u = by_unit[key]
        u['unit_id'] = row['unit_id']
        u['unit_name'] = row['unit_name']
        u['count'] += 1
        u['desired_sum'] += row['desired_price']
        u['zg_counts'][zg] += 1
        if row['delta'] is not None:
            u['delta_sum'] += row['delta']
            u['delta_n'] += 1

    zg_summary = []
    for zg in ZG_ORDER:
        data = by_zg.get(zg)
        if not data and zg == 'Неопределена':
            continue
        if not data:
            continue
        zg_summary.append({
            'zg': zg,
            'count': data['count'],
            'avg_desired': int(round(data['desired_sum'] / data['count'])) if data['count'] else 0,
            'avg_delta': int(round(data['delta_sum'] / data['delta_n'])) if data['delta_n'] else None,
            'color': ZG_COLORS.get(zg, '#94a3b8'),
        })
    for zg, data in by_zg.items():
        if zg in ZG_ORDER:
            continue
        zg_summary.append({
            'zg': zg,
            'count': data['count'],
            'avg_desired': int(round(data['desired_sum'] / data['count'])) if data['count'] else 0,
            'avg_delta': int(round(data['delta_sum'] / data['delta_n'])) if data['delta_n'] else None,
            'color': ZG_COLORS.get(zg, '#94a3b8'),
        })

    unit_rows = []
    for unit in by_unit.values():
        unit_rows.append({
            'unit_id': unit['unit_id'],
            'unit_name': unit['unit_name'],
            'count': unit['count'],
            'avg_desired': int(round(unit['desired_sum'] / unit['count'])) if unit['count'] else 0,
            'avg_delta': int(round(unit['delta_sum'] / unit['delta_n'])) if unit['delta_n'] else None,
            'top_zg': max(unit['zg_counts'].items(), key=lambda x: x[1])[0] if unit['zg_counts'] else '—',
        })
    unit_rows.sort(key=lambda x: (-x['count'], x['unit_name']))

    top3 = []
    for meta, unit in zip(TOP_BADGE_META, unit_rows[:3]):
        top3.append({
            **meta,
            'unit_id': unit['unit_id'],
            'unit_name': unit['unit_name'],
            'count': unit['count'],
        })
    top_rank_by_unit = {item['unit_id']: item for item in top3 if item['unit_id'] is not None}
    # «Без ДЦ» тоже может попасть в топ
    if any(item['unit_id'] is None for item in top3):
        for item in top3:
            if item['unit_id'] is None:
                top_rank_by_unit[None] = item

    for unit in unit_rows:
        badge = top_rank_by_unit.get(unit['unit_id'])
        unit['top_badge'] = badge

    total = len(rows)
    deltas = [r['delta'] for r in rows if r['delta'] is not None]
    summary = {
        'total': total,
        'units': len(unit_rows),
        'avg_desired': int(round(sum(r['desired_price'] for r in rows) / total)) if total else 0,
        'avg_delta': int(round(sum(deltas) / len(deltas))) if deltas else None,
        'unique_estimations': len({r['estimation_id'] for r in rows if r['estimation_id']}),
    }

    chart = {
        'labels': [item['zg'] for item in zg_summary],
        'counts': [item['count'] for item in zg_summary],
        'colors': [item['color'] for item in zg_summary],
        'avg_delta': [item['avg_delta'] if item['avg_delta'] is not None else 0 for item in zg_summary],
    }

    return {
        'summary': summary,
        'zg_summary': zg_summary,
        'unit_rows': unit_rows,
        'top3': top3,
        'chart': chart,
        'rows_preview': rows[:20],
    }


def build_price_increase_detail(date_start, date_end, unit_id=None, zg=None) -> dict:
    zg_norm = normalize_zg_name(zg) if zg else ''
    # unit_id=0 — без ДЦ: берём весь период и отфильтровываем в Python
    qs_unit_id = None if unit_id == 0 else unit_id
    rows = [_serialize_row(req) for req in _queryset(date_start, date_end, unit_id=qs_unit_id)]
    if unit_id == 0:
        rows = [r for r in rows if r['unit_id'] is None]
    if zg_norm:
        rows = [r for r in rows if r['zg'] == zg_norm]

    unit_name = 'Все ДЦ'
    if unit_id == 0:
        unit_name = 'Без ДЦ'
    elif unit_id:
        unit_name = next(
            (r['unit_name'] for r in rows if r['unit_id'] == unit_id),
            f'ДЦ #{unit_id}',
        )
        if not rows:
            from refs.models import RefUnit
            unit = RefUnit.objects.filter(pk=unit_id).first()
            unit_name = unit.name if unit else f'ДЦ #{unit_id}'

    return {
        'unit_id': unit_id,
        'unit_name': unit_name,
        'zg': zg_norm or '',
        'rows': rows,
        'summary': {
            'total': len(rows),
            'avg_desired': int(round(sum(r['desired_price'] for r in rows) / len(rows))) if rows else 0,
            'avg_delta': (
                int(round(sum(r['delta'] for r in rows if r['delta'] is not None)
                          / max(1, len([r for r in rows if r['delta'] is not None]))))
                if any(r['delta'] is not None for r in rows) else None
            ),
        },
    }
