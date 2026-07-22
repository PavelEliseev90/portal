"""Аналитика работы аукциона Авито за период."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time, timedelta

from django.conf import settings
from django.db.models import Avg, Count, Q
from django.utils import timezone

from auction_avito.models import (
    AvitoAutoBidDecision,
    AvitoBidHistory,
    AvitoLot,
    AvitoLotOffer,
)
from auction_avito.services.auto_bid import (
    REASON_CATEGORY_GROUP,
    REASON_CATEGORY_LABELS,
    REASON_GROUP_LABELS,
)
from auction_avito.services.outcome import OUTCOME_NAMES


def _parse_date(raw, default):
    raw = (raw or '').strip()
    if not raw:
        return default
    try:
        return datetime.strptime(raw, '%Y-%m-%d').date()
    except ValueError:
        return default


def _today():
    # localdate() падает при naive now (USE_TZ=False)
    return timezone.now().date()


def resolve_period(request, *, default_days: int = 30):
    today = _today()
    date_to = _parse_date(request.GET.get('date_to'), today)
    date_from = _parse_date(
        request.GET.get('date_from'),
        today - timedelta(days=max(1, default_days) - 1),
    )
    if date_from > date_to:
        date_from, date_to = date_to, date_from
    return date_from, date_to


def _aware(dt: datetime) -> datetime:
    if timezone.is_aware(dt):
        return dt
    if getattr(settings, 'USE_TZ', False):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _day_bounds(date_from, date_to):
    start = _aware(datetime.combine(date_from, time.min))
    end = _aware(datetime.combine(date_to, time.max))
    return start, end


def _pct(part, whole) -> float:
    try:
        part_n = float(part or 0)
        whole_n = float(whole or 0)
    except (TypeError, ValueError):
        return 0.0
    if whole_n <= 0:
        return 0.0
    return round(100.0 * part_n / whole_n, 1)


def build_analytics_context(request) -> dict:
    from django.urls import reverse

    date_from, date_to = resolve_period(request)
    start, end = _day_bounds(date_from, date_to)
    lot_list_base = reverse('auction_avito:lot_list')
    period_qs = (
        f'date_from={date_from.isoformat()}&date_to={date_to.isoformat()}'
    )

    lots_qs = AvitoLot.objects.filter(
        Q(finish_at__gte=start, finish_at__lte=end)
        | Q(finish_at__isnull=True, synced_at__gte=start, synced_at__lte=end)
    )
    lots_total = lots_qs.count()

    offers_in_period = AvitoLotOffer.objects.filter(lot__in=lots_qs).select_related('lot')
    lots_with_bids = (
        offers_in_period.filter(bid__gt=0).values('lot_id').distinct().count()
    )
    bids_total = AvitoBidHistory.objects.filter(
        Q(bid_made_at__gte=start, bid_made_at__lte=end)
        | Q(bid_made_at__isnull=True, recorded_at__gte=start, recorded_at__lte=end)
    ).count()
    # Fallback: если истории мало — считаем ненулевые текущие ставки как минимум 1
    if bids_total == 0:
        bids_total = offers_in_period.filter(bid__gt=0).count()

    avg_bids_per_lot = (
        round(bids_total / lots_with_bids, 2) if lots_with_bids else 0
    )

    # Итоги торгов
    outcome_rows = list(
        offers_in_period
        .exclude(outcome_code='')
        .values('outcome_code')
        .annotate(cnt=Count('id'))
        .order_by('-cnt')
    )
    outcome_counters = []
    for row in outcome_rows:
        code = row['outcome_code']
        outcome_counters.append({
            'code': code,
            'label': OUTCOME_NAMES.get(code, code),
            'count': row['cnt'],
            'pct': 0,
            'list_url': f'{lot_list_base}?outcome={code}&activity=&{period_qs}',
            'filter_kind': 'outcome',
        })
    # Также status won/lost без outcome
    status_extra = list(
        offers_in_period
        .filter(outcome_code='', status_code__in=('won', 'lost', 'finished'))
        .values('status_code')
        .annotate(cnt=Count('id'))
    )
    for row in status_extra:
        code = row['status_code']
        outcome_counters.append({
            'code': code,
            'label': f'Статус: {code}',
            'count': row['cnt'],
            'pct': 0,
            'list_url': f'{lot_list_base}?status={code}&activity=&{period_qs}',
            'filter_kind': 'status',
        })
    # Пересчитать % для всех карточек от общей суммы
    outcomes_sum = sum(o['count'] for o in outcome_counters) or 0
    for o in outcome_counters:
        o['pct'] = _pct(o['count'], outcomes_sum)

    # Автоставки: журнал решений
    decisions = AvitoAutoBidDecision.objects.filter(created_at__gte=start, created_at__lte=end)
    decisions_total = decisions.count()
    decisions_ok = decisions.filter(should_bid=True).count()
    decisions_skip = decisions_total - decisions_ok

    skip_by_cat = list(
        decisions.filter(should_bid=False)
        .values('reason_category')
        .annotate(
            cnt=Count('id'),
            lots=Count('lot_id_ext', distinct=True),
        )
        .order_by('-cnt')
    )
    skip_categories = []
    skip_groups = defaultdict(lambda: {'count': 0, 'lots': 0, 'items': []})
    for row in skip_by_cat:
        cat = row['reason_category'] or 'other'
        item = {
            'code': cat,
            'label': REASON_CATEGORY_LABELS.get(cat, cat),
            'count': row['cnt'],
            'lots': row['lots'] or 0,
            'group': REASON_CATEGORY_GROUP.get(cat, 'other'),
            'pct': _pct(row['cnt'], decisions_skip),
        }
        skip_categories.append(item)
        g = item['group']
        skip_groups[g]['count'] += item['count']
        skip_groups[g]['lots'] += item['lots']
        skip_groups[g]['items'].append(item)

    skip_group_blocks = [
        {
            'code': code,
            'label': REASON_GROUP_LABELS.get(code, code),
            'count': data['count'],
            'lots': data['lots'],
            'pct': _pct(data['count'], decisions_skip),
            'items': data['items'],
        }
        for code, data in skip_groups.items()
        if data['count']
    ]
    skip_group_blocks.sort(key=lambda x: -x['count'])

    # Топ точных reason-текстов среди пропусков
    top_reasons = list(
        decisions.filter(should_bid=False)
        .exclude(reason='')
        .values('reason', 'reason_category')
        .annotate(cnt=Count('id'))
        .order_by('-cnt')[:15]
    )

    # Модели / пробеги на аукционе
    model_stats = list(
        lots_qs
        .filter(vehicle_avito__isnull=False)
        .values(
            'vehicle_avito__brand_name',
            'vehicle_avito__model_name',
        )
        .annotate(
            cnt=Count('id'),
            avg_mileage=Avg('vehicle_avito__mileage'),
            avg_year=Avg('vehicle_avito__year'),
            with_bid=Count('offers', filter=Q(offers__bid__gt=0), distinct=True),
        )
        .order_by('-cnt')[:25]
    )
    for row in model_stats:
        row['brand'] = row.pop('vehicle_avito__brand_name') or '—'
        row['model'] = row.pop('vehicle_avito__model_name') or '—'
        row['avg_mileage'] = int(row['avg_mileage'] or 0)
        row['avg_year'] = int(row['avg_year'] or 0) if row['avg_year'] else None
        row['pct'] = _pct(row['cnt'], lots_total)
        row['bid_pct'] = _pct(row['with_bid'], row['cnt'])

    buckets = {
        '0–50 тыс.': 0,
        '50–100 тыс.': 0,
        '100–150 тыс.': 0,
        '150–200 тыс.': 0,
        '200+ тыс.': 0,
    }
    vehicles = lots_qs.filter(
        vehicle_avito__mileage__isnull=False,
        vehicle_avito__mileage__gt=0,
    ).values_list('vehicle_avito__mileage', flat=True)
    for m in vehicles:
        try:
            m = int(m)
        except (TypeError, ValueError):
            continue
        if m < 50_000:
            buckets['0–50 тыс.'] += 1
        elif m < 100_000:
            buckets['50–100 тыс.'] += 1
        elif m < 150_000:
            buckets['100–150 тыс.'] += 1
        elif m < 200_000:
            buckets['150–200 тыс.'] += 1
        else:
            buckets['200+ тыс.'] += 1
    mileage_base = sum(buckets.values()) or 0
    mileage_buckets = [
        {'label': k, 'count': v, 'pct': _pct(v, mileage_base)}
        for k, v in buckets.items() if v
    ]

    year_stats = list(
        lots_qs
        .filter(vehicle_avito__year__isnull=False, vehicle_avito__year__gt=0)
        .values('vehicle_avito__year')
        .annotate(cnt=Count('id'))
        .order_by('-vehicle_avito__year')[:15]
    )
    year_base = sum(row['cnt'] for row in year_stats) or 0
    # Полная база по годам (не только топ-15) для корректного %
    year_base_all = (
        lots_qs
        .filter(vehicle_avito__year__isnull=False, vehicle_avito__year__gt=0)
        .count()
    ) or year_base
    for row in year_stats:
        row['year'] = row.pop('vehicle_avito__year')
        row['pct'] = _pct(row['cnt'], year_base_all)

    avg_mileage_all = lots_qs.filter(
        vehicle_avito__mileage__gt=0,
    ).aggregate(v=Avg('vehicle_avito__mileage'))['v']
    avg_year_all = lots_qs.filter(
        vehicle_avito__year__gt=0,
    ).aggregate(v=Avg('vehicle_avito__year'))['v']

    bid_share = _pct(lots_with_bids, lots_total)
    ok_share = _pct(decisions_ok, decisions_total)

    return {
        'type': 'auction_avito_analytics',
        'filters': {
            'date_from': date_from.isoformat(),
            'date_to': date_to.isoformat(),
        },
        'kpis': {
            'lots_total': lots_total,
            'lots_with_bids': lots_with_bids,
            'bids_total': bids_total,
            'avg_bids_per_lot': avg_bids_per_lot,
            'bid_share': bid_share,
            'avg_mileage': int(avg_mileage_all or 0),
            'avg_year': int(avg_year_all or 0) if avg_year_all else None,
            'decisions_total': decisions_total,
            'decisions_ok': decisions_ok,
            'decisions_skip': decisions_skip,
            'ok_share': ok_share,
            'outcomes_total': outcomes_sum,
            'mileage_total': mileage_base,
            'years_total': year_base_all,
        },
        'outcomes': outcome_counters,
        'auto_bid': {
            'categories': skip_categories,
            'groups': skip_group_blocks,
            'top_reasons': top_reasons,
            'has_data': decisions_total > 0,
        },
        'models': model_stats,
        'mileage_buckets': mileage_buckets,
        'years': year_stats,
    }
