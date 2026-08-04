"""Воронка аукциона Авито: лоты → наши ставки → выбрали нас, разбивка по ЦГ."""
from __future__ import annotations

import json
from collections import defaultdict

from django.db.models import OuterRef, Q, Subquery
from django.urls import reverse

from auction_avito.models import AvitoLot, AvitoLotCalculation, AvitoLotOffer
from auction_avito.services.analytics import _pct, resolve_period, _day_bounds
from auction_avito.services.outcome import OUTCOME_NAMES, OUTCOME_NOT_TAKEN, OUTCOME_WON
from refs.price_groups import ZG_ORDER, normalize_price_group_display

# Цвета воронки (не ЦГ): всего / ставки / выигрыш — чтобы сегменты читались в одном столбике ЦГ.
FUNNEL_COLORS = {
    'total': '#94a3b8',
    'with_bids': '#2563eb',
    'won': '#16a34a',
    'not_taken': '#f59e0b',
}

ZG_UNDEFINED = 'Неопределена'


def _parse_zg_filter(raw) -> list[str]:
    """Список выбранных ЦГ из GET (zg / zg[] / comma-separated)."""
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        values = list(raw)
    else:
        values = str(raw).split(',')
    selected = []
    seen = set()
    for item in values:
        name = normalize_price_group_display(str(item or '').strip())
        if not name or name in seen:
            continue
        if name not in ZG_ORDER and name != ZG_UNDEFINED:
            # оставляем как есть только если это уже каноническое имя
            continue
        seen.add(name)
        selected.append(name)
    return selected


def _latest_calc_subqueries():
    latest = (
        AvitoLotCalculation.objects
        .filter(lot=OuterRef('pk'), is_success=True)
        .order_by('-calculated_at', '-pk')
    )
    return (
        Subquery(latest.values('price_group')[:1]),
        Subquery(latest.values('zna')[:1]),
        Subquery(latest.values('estimation_price')[:1]),
    )


def _resolve_lot_zg(price_group_raw, zna, estimation_price) -> str:
    price = zna if zna not in (None, 0, '0', '') else estimation_price
    return normalize_price_group_display(price_group_raw, price=price) or ZG_UNDEFINED


def build_funnel_context(request) -> dict:
    date_from, date_to = resolve_period(request, default_days=30)
    start, end = _day_bounds(date_from, date_to)

    selected_zg = _parse_zg_filter(request.GET.getlist('zg') or request.GET.get('zg'))

    pg_sq, zna_sq, est_sq = _latest_calc_subqueries()
    lots_qs = (
        AvitoLot.objects
        .filter(
            Q(finish_at__gte=start, finish_at__lte=end)
            | Q(finish_at__isnull=True, synced_at__gte=start, synced_at__lte=end)
        )
        .annotate(
            calc_price_group=pg_sq,
            calc_zna=zna_sq,
            calc_estimation_price=est_sq,
        )
    )

    lot_rows = list(lots_qs.values(
        'id',
        'calc_price_group',
        'calc_zna',
        'calc_estimation_price',
    ))
    lot_ids = [row['id'] for row in lot_rows]

    offers_by_lot = defaultdict(list)
    if lot_ids:
        for offer in (
            AvitoLotOffer.objects
            .filter(lot_id__in=lot_ids)
            .values('lot_id', 'bid', 'outcome_code')
        ):
            offers_by_lot[offer['lot_id']].append(offer)

    # Агрегаты по ЦГ
    by_zg = {
        zg: {
            'zg': zg,
            'total': 0,
            'with_bids': 0,
            'won': 0,
            'not_taken': 0,
            'lost': 0,
            'waiting': 0,
            'other_outcome': 0,
        }
        for zg in ZG_ORDER
    }

    summary = {
        'total': 0,
        'with_bids': 0,
        'won': 0,
        'not_taken': 0,
        'lost': 0,
        'waiting': 0,
        'no_calc': 0,
    }

    filtered_rows = []
    for row in lot_rows:
        zg = _resolve_lot_zg(
            row.get('calc_price_group'),
            row.get('calc_zna'),
            row.get('calc_estimation_price'),
        )
        if zg not in by_zg:
            by_zg[zg] = {
                'zg': zg,
                'total': 0,
                'with_bids': 0,
                'won': 0,
                'not_taken': 0,
                'lost': 0,
                'waiting': 0,
                'other_outcome': 0,
            }
        if selected_zg and zg not in selected_zg:
            continue

        offers = offers_by_lot.get(row['id'], [])
        has_bid = any(int(o.get('bid') or 0) > 0 for o in offers)
        outcomes = {(o.get('outcome_code') or '').strip() for o in offers}
        is_won = OUTCOME_WON in outcomes
        is_not_taken = OUTCOME_NOT_TAKEN in outcomes and not is_won
        is_lost = 'lost' in outcomes and not is_won
        is_waiting = 'waiting_seller' in outcomes and not is_won and not is_lost

        bucket = by_zg[zg]
        bucket['total'] += 1
        summary['total'] += 1
        if not row.get('calc_price_group') and not row.get('calc_zna'):
            summary['no_calc'] += 1

        if has_bid:
            bucket['with_bids'] += 1
            summary['with_bids'] += 1
        if is_won:
            bucket['won'] += 1
            summary['won'] += 1
        elif is_not_taken:
            bucket['not_taken'] += 1
            summary['not_taken'] += 1
        elif is_lost:
            bucket['lost'] += 1
            summary['lost'] += 1
        elif is_waiting:
            bucket['waiting'] += 1
            summary['waiting'] += 1
        elif has_bid and outcomes - {''}:
            bucket['other_outcome'] += 1

        filtered_rows.append({
            'id': row['id'],
            'zg': zg,
            'has_bid': has_bid,
            'won': is_won,
        })

    zg_list = [zg for zg in ZG_ORDER if by_zg.get(zg, {}).get('total', 0) > 0]
    for zg, bucket in by_zg.items():
        if zg not in zg_list and bucket['total'] > 0:
            zg_list.append(zg)
    # если после фильтра пусто, всё равно показать выбранные / канонический порядок
    if not zg_list and selected_zg:
        zg_list = [zg for zg in ZG_ORDER if zg in selected_zg] or list(selected_zg)
    if not zg_list:
        zg_list = list(ZG_ORDER)

    rows = []
    for zg in zg_list:
        b = by_zg.get(zg) or {
            'zg': zg,
            'total': 0,
            'with_bids': 0,
            'won': 0,
            'not_taken': 0,
            'lost': 0,
            'waiting': 0,
            'other_outcome': 0,
        }
        rows.append({
            **b,
            'bid_share': _pct(b['with_bids'], b['total']),
            'win_share_of_total': _pct(b['won'], b['total']),
            'win_share_of_bids': _pct(b['won'], b['with_bids']),
            'color': FUNNEL_COLORS['total'],
        })

    chart = {
        'labels': zg_list,
        'datasets': [
            {
                'label': 'Всего лотов',
                'data': [(by_zg.get(zg) or {}).get('total', 0) for zg in zg_list],
                'backgroundColor': FUNNEL_COLORS['total'],
                'borderRadius': 6,
            },
            {
                'label': 'С нашими ставками',
                'data': [(by_zg.get(zg) or {}).get('with_bids', 0) for zg in zg_list],
                'backgroundColor': FUNNEL_COLORS['with_bids'],
                'borderRadius': 6,
            },
            {
                'label': 'Выбрали нас',
                'data': [(by_zg.get(zg) or {}).get('won', 0) for zg in zg_list],
                'backgroundColor': FUNNEL_COLORS['won'],
                'borderRadius': 6,
            },
        ],
    }

    lot_list_base = reverse('auction_avito:lot_list')
    period_qs = f'date_from={date_from.isoformat()}&date_to={date_to.isoformat()}'

    summary.update({
        'bid_share': _pct(summary['with_bids'], summary['total']),
        'win_share_of_total': _pct(summary['won'], summary['total']),
        'win_share_of_bids': _pct(summary['won'], summary['with_bids']),
        'not_taken_share_of_bids': _pct(summary['not_taken'], summary['with_bids']),
    })

    return {
        'type': 'auction_avito_funnel',
        'filters': {
            'date_from': date_from.isoformat(),
            'date_to': date_to.isoformat(),
            'zg': selected_zg,
        },
        'zg_choices': ZG_ORDER,
        'summary': summary,
        'rows': rows,
        'chart': chart,
        'chart_json': json.dumps(chart, ensure_ascii=False),
        'funnel_colors': FUNNEL_COLORS,
        'outcome_labels': {
            'won': OUTCOME_NAMES.get(OUTCOME_WON, 'Выбрали нас'),
            'not_taken': OUTCOME_NAMES.get(OUTCOME_NOT_TAKEN, 'Не обработан'),
        },
        'links': {
            'lots_all': f'{lot_list_base}?activity=&{period_qs}',
            'lots_bids': f'{lot_list_base}?activity=&{period_qs}',
            'lots_won': f'{lot_list_base}?outcome=won&activity=&{period_qs}',
        },
        'hint': (
            'ЦГ берётся из последнего успешного расчёта выкупа лота '
            '(AvitoLotCalculation.price_group / ZNA). '
            '«Выбрали нас» — outcome_code=won.'
        ),
    }
