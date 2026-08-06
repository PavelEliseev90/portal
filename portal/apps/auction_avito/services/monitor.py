"""Онлайн-монитор аукциона Авито: активные лоты, наши ставки, ожидание итога."""
from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, Max, OuterRef, Prefetch, Q, Subquery
from django.utils import timezone

from auction_avito.models import (
    AvitoBidderAccount,
    AvitoLot,
    AvitoLotCalculation,
    AvitoLotOffer,
)
from auction_avito.services.offer_status import active_lots_q
from auction_avito.services.outcome import (
    FINAL_OUTCOMES,
    OUTCOME_WAITING,
    OUTCOME_UNKNOWN,
    OUTCOME_WON,
    WIN_NOTIFY_OUTCOMES,
)

# Подписи площадок (наши dealerId) — синхронно с tools/maxposter_auction/dealers.js
KNOWN_DEALER_LABELS = {
    2104: 'КорсАвто Тула',
    2106: 'КорсАвто Новомосковск',
    2107: 'КорсАвто Калуга',
    2849: 'КорсАвто Ярославль',
    3195: 'КорсГрупп Тверь',
    3328: 'КорсАвто Коломна',
    3624: 'КорсГрупп Орел',
    3931: 'КорсАвто Курск',
    4610: 'КорсАвто Октябрьская',
    8470: 'КорсАвто премиум',
    8792: 'КорсАвто Серпухов',
    8795: 'Корс Авто автомобили с пробегом',
    9665: 'КорсАвто Ногинск',
    9837: 'Корсавто Тула Рязанская 7В',
    10071: 'КорсАвто Обнинск',
    10278: 'КорсАвто Курск Октябрьская',
}


def dealer_label(dealer_id) -> str:
    try:
        did = int(dealer_id)
    except (TypeError, ValueError):
        return str(dealer_id or '')
    name = KNOWN_DEALER_LABELS.get(did)
    return f'{did}: {name}' if name else str(did)


def parse_dealer_ids(raw_values) -> list[int]:
    if raw_values is None:
        return []
    if isinstance(raw_values, str):
        raw_values = raw_values.replace(';', ',').split(',')
    out = []
    seen = set()
    for item in raw_values:
        try:
            did = int(str(item).strip())
        except (TypeError, ValueError):
            continue
        if did in seen:
            continue
        seen.add(did)
        out.append(did)
    return out


def waiting_outcome_offers_q():
    """Завершённые / «зависшие» офферы со ставкой без финального статуса."""
    now = timezone.now()
    terminal = ['finished', 'ended', 'canceled', 'won', 'lost']
    return (
        Q(bid__gt=0)
        & (
            Q(lot__finish_at__lte=now)
            | Q(lot__origin_finish_at__lte=now)
            | Q(status_code__in=terminal)
            | Q(lot__finish_at__isnull=True, lot__origin_finish_at__isnull=True)
        )
        & ~Q(outcome_code__in=list(FINAL_OUTCOMES))
        & (
            Q(outcome_code='')
            | Q(outcome_code=OUTCOME_UNKNOWN)
            | Q(outcome_code=OUTCOME_WAITING)
            | Q(outcome_synced_at__isnull=True)
        )
    )


def won_pending_offers_q():
    """Выигранные / «не обработан» офферы, ещё не отмеченные «передан в работу»."""
    return (
        Q(bid__gt=0)
        & Q(handed_to_work_at__isnull=True)
        & Q(outcome_code__in=list(WIN_NOTIFY_OUTCOMES))
    )


def _dealer_filter_q(dealer_ids: list[int]) -> Q:
    if not dealer_ids:
        return Q()
    return Q(offers__account__dealer_id__in=dealer_ids)


def monitor_counts(*, dealer_ids: list[int] | None = None) -> dict:
    dealer_ids = dealer_ids or []
    dq = _dealer_filter_q(dealer_ids)

    active_qs = AvitoLot.objects.filter(active_lots_q())
    if dealer_ids:
        active_qs = active_qs.filter(dq)
    active = active_qs.distinct().count()

    active_our_bid_qs = AvitoLot.objects.filter(active_lots_q(), offers__bid__gt=0)
    if dealer_ids:
        active_our_bid_qs = active_our_bid_qs.filter(dq)
    active_our_bid = active_our_bid_qs.distinct().count()

    waiting_qs = AvitoLotOffer.objects.filter(waiting_outcome_offers_q())
    if dealer_ids:
        waiting_qs = waiting_qs.filter(account__dealer_id__in=dealer_ids)
    waiting = waiting_qs.values('lot_id').distinct().count()

    won_qs = AvitoLotOffer.objects.filter(won_pending_offers_q())
    if dealer_ids:
        won_qs = won_qs.filter(account__dealer_id__in=dealer_ids)
    won_pending = won_qs.values('lot_id').distinct().count()

    history_today = monitor_history_today_count(dealer_ids=dealer_ids)

    return {
        'active': active,
        'active_our_bid': active_our_bid,
        'waiting_decision': waiting,
        'won_pending': won_pending,
        'history_today': history_today,
    }


def monitor_dealer_counts() -> dict[int, dict]:
    """
    Счётчики по каждой площадке (dealer_id):
    active / active_our_bid / waiting_decision / won_pending.
    """
    empty = {
        'active': 0,
        'active_our_bid': 0,
        'waiting_decision': 0,
        'won_pending': 0,
    }
    by_dealer: dict[int, dict] = {}

    def _bucket(did) -> dict:
        try:
            key = int(did)
        except (TypeError, ValueError):
            return empty
        if key not in by_dealer:
            by_dealer[key] = dict(empty)
        return by_dealer[key]

    active_rows = (
        AvitoLot.objects
        .filter(active_lots_q())
        .values('offers__account__dealer_id')
        .annotate(n=Count('id', distinct=True))
    )
    for row in active_rows:
        did = row.get('offers__account__dealer_id')
        if did is None:
            continue
        _bucket(did)['active'] = int(row['n'] or 0)

    bid_rows = (
        AvitoLot.objects
        .filter(active_lots_q(), offers__bid__gt=0)
        .values('offers__account__dealer_id')
        .annotate(n=Count('id', distinct=True))
    )
    for row in bid_rows:
        did = row.get('offers__account__dealer_id')
        if did is None:
            continue
        _bucket(did)['active_our_bid'] = int(row['n'] or 0)

    waiting_rows = (
        AvitoLotOffer.objects
        .filter(waiting_outcome_offers_q())
        .values('account__dealer_id')
        .annotate(n=Count('lot_id', distinct=True))
    )
    for row in waiting_rows:
        did = row.get('account__dealer_id')
        if did is None:
            continue
        _bucket(did)['waiting_decision'] = int(row['n'] or 0)

    won_rows = (
        AvitoLotOffer.objects
        .filter(won_pending_offers_q())
        .values('account__dealer_id')
        .annotate(n=Count('lot_id', distinct=True))
    )
    for row in won_rows:
        did = row.get('account__dealer_id')
        if did is None:
            continue
        _bucket(did)['won_pending'] = int(row['n'] or 0)

    return by_dealer


def build_monitor_dealer_choices(selected_ids: list[int] | None = None) -> list[dict]:
    """Список площадок для фильтра монитора со счётчиками."""
    selected_ids = selected_ids or []
    selected_set = set(selected_ids)
    per = monitor_dealer_counts()

    ids = set(KNOWN_DEALER_LABELS) | set(per.keys())
    for did in AvitoBidderAccount.objects.filter(is_active=True).values_list('dealer_id', flat=True):
        ids.add(did)

    rows = []
    for did in sorted(ids):
        c = per.get(did) or {
            'active': 0,
            'active_our_bid': 0,
            'waiting_decision': 0,
            'won_pending': 0,
        }
        rows.append({
            'id': did,
            'label': dealer_label(did),
            'selected': did in selected_set,
            'active': c['active'],
            'active_our_bid': c['active_our_bid'],
            'waiting_decision': c['waiting_decision'],
            'won_pending': c['won_pending'],
            'total': (
                c['active']
                + c['active_our_bid']
                + c['waiting_decision']
                + c['won_pending']
            ),
        })
    return rows


def _today_bounds():
    """Начало/конец текущего локального дня (aware или naive — как в проекте)."""
    now = timezone.now()
    if timezone.is_aware(now):
        now = timezone.localtime(now)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end


def monitor_history_today_count(*, dealer_ids: list[int] | None = None) -> int:
    """Лёгкий счётчик событий за сегодня (для KPI, без сборки ленты)."""
    from auction_avito.models import AvitoAutoBidDecision, AvitoBidHistory, AvitoLotCalculation

    dealer_ids = dealer_ids or []
    start, end = _today_bounds()

    lots = AvitoLot.objects.filter(
        Q(created_at__gte=start, created_at__lt=end)
        | Q(
            pk__in=AvitoLotCalculation.objects.filter(
                is_success=True,
                calculated_at__gte=start,
                calculated_at__lt=end,
            ).values('lot_id')
        )
    )
    if dealer_ids:
        lots = lots.filter(offers__account__dealer_id__in=dealer_ids)
    n_lots = lots.distinct().count()

    bids = AvitoBidHistory.objects.filter(recorded_at__gte=start, recorded_at__lt=end)
    if dealer_ids:
        bids = bids.filter(offer__account__dealer_id__in=dealer_ids)
    n_bids = bids.count()

    outs = AvitoLotOffer.objects.filter(
        outcome_synced_at__gte=start,
        outcome_synced_at__lt=end,
    ).exclude(outcome_code='')
    if dealer_ids:
        outs = outs.filter(account__dealer_id__in=dealer_ids)
    # KPI как в ленте: уникальные пары лот + код итога
    n_outs = len({
        (o['lot__lot_id'], o['outcome_code'])
        for o in outs.values('lot__lot_id', 'outcome_code')
    })

    hands = AvitoLotOffer.objects.filter(
        handed_to_work_at__gte=start,
        handed_to_work_at__lt=end,
    )
    if dealer_ids:
        hands = hands.filter(account__dealer_id__in=dealer_ids)
    n_hands = hands.count()

    ab = AvitoAutoBidDecision.objects.filter(
        created_at__gte=start,
        created_at__lt=end,
        should_bid=True,
    )
    if dealer_ids:
        ab = ab.filter(
            Q(offer__account__dealer_id__in=dealer_ids)
            | Q(offer__isnull=True, lot__offers__account__dealer_id__in=dealer_ids)
        ).distinct()
    n_ab = ab.count()

    return n_lots + n_bids + n_outs + n_hands + n_ab


def _lot_title(lot) -> str:
    vehicle = getattr(lot, 'vehicle_avito', None) or getattr(lot, 'vehicle_autohub', None)
    brand = getattr(vehicle, 'brand_name', '') or ''
    model = getattr(vehicle, 'model_name', '') or ''
    title = f'{brand} {model}'.strip()
    return title or f'Лот {lot.lot_id}'


def _money_ru(v) -> str:
    try:
        return f'{int(v):,}'.replace(',', ' ')
    except (TypeError, ValueError):
        return str(v or '')


def monitor_today_history(*, dealer_ids: list[int] | None = None, limit: int = 200) -> list[dict]:
    """
    Лента событий за сегодня: новые лоты, ставки, итоги, передача в работу, автоставки.
    """
    from auction_avito.models import AvitoAutoBidDecision, AvitoBidHistory, AvitoLotCalculation
    from auction_avito.services.outcome import OUTCOME_NAMES

    dealer_ids = dealer_ids or []
    start, end = _today_bounds()
    events: list[dict] = []

    # 1) Новые лоты (по created_at API или первому успешному расчёту за сегодня)
    lot_qs = (
        AvitoLot.objects
        .select_related('venue', 'vehicle_avito')
        .filter(
            Q(created_at__gte=start, created_at__lt=end)
            | Q(
                pk__in=AvitoLotCalculation.objects.filter(
                    is_success=True,
                    calculated_at__gte=start,
                    calculated_at__lt=end,
                ).values_list('lot_id', flat=True)
            )
        )
    )
    if dealer_ids:
        lot_qs = lot_qs.filter(offers__account__dealer_id__in=dealer_ids).distinct()

    seen_new_lots = set()
    for lot in lot_qs[:150]:
        if lot.pk in seen_new_lots:
            continue
        seen_new_lots.add(lot.pk)
        at = lot.created_at
        if not at or at < start or at >= end:
            # берём время первого расчёта за сегодня
            calc = (
                lot.calculations
                .filter(is_success=True, calculated_at__gte=start, calculated_at__lt=end)
                .order_by('calculated_at')
                .first()
            )
            at = calc.calculated_at if calc else timezone.now()
        events.append({
            'id': f'new-{lot.pk}',
            'kind': 'new_lot',
            'kindLabel': 'Новый лот',
            'at': at,
            'title': _lot_title(lot),
            'detail': f'лот {lot.lot_id}',
            'lotPk': lot.pk,
            'lotId': lot.lot_id,
            'portalLotUrl': f'/auction_avito/lots/{lot.pk}/',
            'dealerLabel': '',
            'place': (lot.venue.display_label if lot.venue_id else '') or (lot.seller_place_name or ''),
        })

    # 2) Наши ставки
    bid_qs = (
        AvitoBidHistory.objects
        .select_related('offer', 'offer__lot', 'offer__lot__vehicle_avito', 'offer__account')
        .filter(recorded_at__gte=start, recorded_at__lt=end)
    )
    if dealer_ids:
        bid_qs = bid_qs.filter(offer__account__dealer_id__in=dealer_ids)
    for h in bid_qs.order_by('-recorded_at')[:200]:
        offer = h.offer
        lot = offer.lot if offer else None
        if not lot:
            continue
        at = h.bid_made_at or h.recorded_at
        events.append({
            'id': f'bid-{h.pk}',
            'kind': 'bid',
            'kindLabel': 'Ставка',
            'at': at,
            'title': _lot_title(lot),
            'detail': f'{_money_ru(h.bid)} ₽ · лот {lot.lot_id}',
            'lotPk': lot.pk,
            'lotId': lot.lot_id,
            'portalLotUrl': f'/auction_avito/lots/{lot.pk}/',
            'dealerLabel': dealer_label(offer.account.dealer_id) if offer.account_id else '',
            'place': '',
        })

    # 3) Итоги (смена outcome) — по лоту один раз на код итога (первое время sync).
    out_qs = (
        AvitoLotOffer.objects
        .select_related('lot', 'lot__vehicle_avito', 'account')
        .filter(outcome_synced_at__gte=start, outcome_synced_at__lt=end)
        .exclude(outcome_code='')
    )
    if dealer_ids:
        out_qs = out_qs.filter(account__dealer_id__in=dealer_ids)
    seen_lot_outcomes: set[tuple] = set()
    for offer in out_qs.order_by('outcome_synced_at', 'id')[:400]:
        lot = offer.lot
        code = (offer.outcome_code or '').strip()
        lot_id = getattr(lot, 'lot_id', None) or offer.pk
        dedupe_key = (lot_id, code)
        if dedupe_key in seen_lot_outcomes:
            continue
        seen_lot_outcomes.add(dedupe_key)
        label = OUTCOME_NAMES.get(code, code)
        detail_bits = [label]
        title = (offer.outcome_title or '').strip()
        if title and title.casefold() != label.casefold():
            detail_bits.append(title)
        detail = (offer.outcome_detail or '').strip()
        if detail and detail.casefold() not in {b.casefold() for b in detail_bits}:
            detail_bits.append(detail)
        events.append({
            'id': f'out-{lot_id}-{code}',
            'kind': 'outcome',
            'kindLabel': 'Итог',
            'at': offer.outcome_synced_at,
            'title': _lot_title(lot),
            'detail': ' · '.join(detail_bits) + f' · лот {lot.lot_id}',
            'lotPk': lot.pk,
            'lotId': lot.lot_id,
            'portalLotUrl': f'/auction_avito/lots/{lot.pk}/',
            'dealerLabel': dealer_label(offer.account.dealer_id) if offer.account_id else '',
            'place': '',
            'outcomeCode': code,
        })

    # 4) Переданы в работу
    hand_qs = (
        AvitoLotOffer.objects
        .select_related('lot', 'lot__vehicle_avito', 'account', 'handed_to_work_by')
        .filter(handed_to_work_at__gte=start, handed_to_work_at__lt=end)
    )
    if dealer_ids:
        hand_qs = hand_qs.filter(account__dealer_id__in=dealer_ids)
    for offer in hand_qs.order_by('-handed_to_work_at')[:100]:
        lot = offer.lot
        who = ''
        if offer.handed_to_work_by_id:
            u = offer.handed_to_work_by
            who = f'{u.last_name or ""} {u.first_name or ""}'.strip() or u.username
        events.append({
            'id': f'hand-{offer.pk}',
            'kind': 'handed',
            'kindLabel': 'В работу',
            'at': offer.handed_to_work_at,
            'title': _lot_title(lot),
            'detail': (f'передан в работу' + (f' · {who}' if who else '')) + f' · лот {lot.lot_id}',
            'lotPk': lot.pk,
            'lotId': lot.lot_id,
            'portalLotUrl': f'/auction_avito/lots/{lot.pk}/',
            'dealerLabel': dealer_label(offer.account.dealer_id) if offer.account_id else '',
            'place': '',
        })

    # 5) Автоставка разрешена (should_bid) — без спама skip
    ab_qs = (
        AvitoAutoBidDecision.objects
        .select_related('lot', 'lot__vehicle_avito', 'offer', 'offer__account')
        .filter(created_at__gte=start, created_at__lt=end, should_bid=True)
    )
    if dealer_ids:
        ab_qs = ab_qs.filter(
            Q(offer__account__dealer_id__in=dealer_ids)
            | Q(offer__isnull=True, lot__offers__account__dealer_id__in=dealer_ids)
        ).distinct()
    for d in ab_qs.order_by('-created_at')[:100]:
        lot = d.lot
        if not lot and d.offer_id:
            lot = d.offer.lot
        if not lot:
            continue
        amount = d.bid_amount or d.next_bid
        detail = d.reason or 'автоставка разрешена'
        if amount:
            detail = f'{detail} · {_money_ru(amount)} ₽'
        dealer = ''
        if d.offer_id and d.offer.account_id:
            dealer = dealer_label(d.offer.account.dealer_id)
        events.append({
            'id': f'ab-{d.pk}',
            'kind': 'autobid',
            'kindLabel': 'Автоставка',
            'at': d.created_at,
            'title': _lot_title(lot),
            'detail': f'{detail} · лот {lot.lot_id}',
            'lotPk': lot.pk,
            'lotId': lot.lot_id,
            'portalLotUrl': f'/auction_avito/lots/{lot.pk}/',
            'dealerLabel': dealer,
            'place': '',
        })

    # Сортировка и сериализация времени
    events.sort(key=lambda e: e.get('at') or start, reverse=True)
    out = []
    seen_ids = set()
    for ev in events:
        eid = ev.get('id')
        if eid in seen_ids:
            continue
        seen_ids.add(eid)
        at = ev.get('at')
        ev['atHuman'] = _format_dt_local(at) if at else ''
        ev['atIso'] = ''
        if at:
            try:
                ev['atIso'] = timezone.localtime(at).isoformat()
            except Exception:
                ev['atIso'] = str(at)
        # datetime не JSON-сериализуется в json_script напрямую если оставить объект —
        # уберём сырой at из ответа для шаблона/JSON
        ev.pop('at', None)
        out.append(ev)
        if len(out) >= limit:
            break
    return out


def monitor_revision(*, dealer_ids: list[int] | None = None) -> str:
    """
    Короткий отпечаток состояния для автообновления монитора.
    Меняется при новых/изменённых лотах, ставках, итогах, «в работу».
    """
    dealer_ids = dealer_ids or []
    offer_qs = AvitoLotOffer.objects.all()
    lot_qs = AvitoLot.objects.all()
    if dealer_ids:
        offer_qs = offer_qs.filter(account__dealer_id__in=dealer_ids)
        lot_qs = lot_qs.filter(offers__account__dealer_id__in=dealer_ids).distinct()

    from auction_avito.models import AvitoBidHistory

    hist_qs = AvitoBidHistory.objects.all()
    if dealer_ids:
        hist_qs = hist_qs.filter(offer__account__dealer_id__in=dealer_ids)

    offer_agg = offer_qs.aggregate(
        n=Count('id'),
        bid_sum=Max('bid'),
        upd=Max('updated_at'),
        out=Max('outcome_synced_at'),
        hand=Max('handed_to_work_at'),
    )
    lot_agg = lot_qs.aggregate(
        n=Count('id'),
        sync=Max('synced_at'),
        max_bid=Max('max_bid'),
        finish=Max('finish_at'),
    )
    hist_agg = hist_qs.aggregate(n=Count('id'), rec=Max('recorded_at'))
    counts = monitor_counts(dealer_ids=dealer_ids)

    def _ts(v):
        if not v:
            return ''
        try:
            return v.isoformat()
        except Exception:
            return str(v)

    return '|'.join([
        str(counts.get('active', 0)),
        str(counts.get('active_our_bid', 0)),
        str(counts.get('waiting_decision', 0)),
        str(counts.get('won_pending', 0)),
        str(offer_agg.get('n') or 0),
        str(offer_agg.get('bid_sum') or 0),
        _ts(offer_agg.get('upd')),
        _ts(offer_agg.get('out')),
        _ts(offer_agg.get('hand')),
        str(lot_agg.get('n') or 0),
        str(lot_agg.get('max_bid') or 0),
        _ts(lot_agg.get('sync')),
        _ts(lot_agg.get('finish')),
        str(hist_agg.get('n') or 0),
        _ts(hist_agg.get('rec')),
    ])


def _annotate_buyout(qs):
    latest_calc = AvitoLotCalculation.objects.filter(
        lot=OuterRef('pk'),
        is_success=True,
    ).order_by('-calculated_at')
    return qs.annotate(
        latest_estimation_price=Subquery(latest_calc.values('estimation_price')[:1]),
        latest_zna=Subquery(latest_calc.values('zna')[:1]),
        latest_profit=Subquery(latest_calc.values('profit')[:1]),
        latest_calc_id=Subquery(latest_calc.values('pk')[:1]),
    )


def monitor_lots_queryset(*, mode: str = 'active', dealer_ids: list[int] | None = None):
    from auction_avito.models import AvitoAutoBidDecision, AvitoBidHistory

    dealer_ids = dealer_ids or []
    mode = (mode or 'active').strip()

    offer_qs = (
        AvitoLotOffer.objects
        .select_related('account', 'manual_max_bid_set_by')
        .prefetch_related(
            Prefetch(
                'bid_history',
                queryset=AvitoBidHistory.objects.order_by('-bid_made_at', '-recorded_at'),
            ),
            Prefetch(
                'auto_bid_decisions',
                queryset=AvitoAutoBidDecision.objects.order_by('-created_at'),
                to_attr='decisions_desc',
            ),
        )
        .order_by('-updated_at')
    )
    if dealer_ids:
        offer_qs = offer_qs.filter(account__dealer_id__in=dealer_ids)

    base = (
        AvitoLot.objects
        .select_related('venue', 'venue__city', 'vehicle_avito')
        .prefetch_related(
            Prefetch('offers', queryset=offer_qs),
            'images',
        )
    )

    if mode == 'active_our_bid':
        qs = base.filter(active_lots_q(), offers__bid__gt=0)
        if dealer_ids:
            qs = qs.filter(offers__account__dealer_id__in=dealer_ids, offers__bid__gt=0)
        qs = qs.distinct()
    elif mode == 'waiting':
        offer_lot_ids = (
            AvitoLotOffer.objects
            .filter(waiting_outcome_offers_q())
            .filter(Q(account__dealer_id__in=dealer_ids) if dealer_ids else Q())
            .values_list('lot_id', flat=True)
            .distinct()
        )
        qs = base.filter(pk__in=offer_lot_ids)
    elif mode == 'won_pending':
        offer_lot_ids = (
            AvitoLotOffer.objects
            .filter(won_pending_offers_q())
            .filter(Q(account__dealer_id__in=dealer_ids) if dealer_ids else Q())
            .values_list('lot_id', flat=True)
            .distinct()
        )
        qs = base.filter(pk__in=offer_lot_ids)
    else:
        qs = base.filter(active_lots_q())
        if dealer_ids:
            qs = qs.filter(offers__account__dealer_id__in=dealer_ids)
        qs = qs.distinct()

    if mode == 'won_pending':
        return _annotate_buyout(qs).order_by('-synced_at', '-lot_id')
    return _annotate_buyout(qs).order_by('finish_at', 'lot_id')


def _format_dt_local(dt) -> str:
    if not dt:
        return ''
    try:
        return timezone.localtime(dt).strftime('%d.%m.%Y %H:%M')
    except Exception:
        try:
            return dt.strftime('%d.%m.%Y %H:%M')
        except Exception:
            return str(dt)


def _bid_position(*, our_bid, max_bid, our_bids_count: int) -> dict:
    """
    Позиция нашей ставки на лоте.
    outbid — перебита; sole — одна наша и она макс; leading — лидируем при >1 нашей ставке;
    none — ставки нет.
    """
    try:
        our_n = int(our_bid) if our_bid not in (None, '') else 0
    except (TypeError, ValueError):
        our_n = 0
    try:
        max_n = int(max_bid) if max_bid not in (None, '') else 0
    except (TypeError, ValueError):
        max_n = 0

    if our_n <= 0:
        return {
            'code': 'none',
            'label': '',
            'rowClass': '',
            'isOutbid': False,
            'isSole': False,
            'isLeading': False,
        }
    if max_n > our_n:
        return {
            'code': 'outbid',
            'label': 'Ставка перебита',
            'rowClass': 'mon-row-outbid',
            'isOutbid': True,
            'isSole': False,
            'isLeading': False,
        }
    # our_n >= max_n (или max пустой — считаем лидером по своей ставке)
    if our_bids_count <= 1 and (max_n <= 0 or max_n == our_n):
        return {
            'code': 'sole',
            'label': 'Без конкурентов',
            'rowClass': 'mon-row-sole',
            'isOutbid': False,
            'isSole': True,
            'isLeading': True,
        }
    return {
        'code': 'leading',
        'label': 'Наша ставка лидирует',
        'rowClass': 'mon-row-leading',
        'isOutbid': False,
        'isSole': False,
        'isLeading': True,
    }


def serialize_monitor_lot(lot) -> dict:
    from auction_avito.services.auto_bid import REASON_CATEGORY_LABELS

    offers = list(lot.offers.all())
    primary = None
    for o in offers:
        if (o.bid or 0) > 0:
            primary = o
            break
    if primary is None and offers:
        primary = offers[0]

    vehicle = getattr(lot, 'vehicle_avito', None) or getattr(lot, 'vehicle_autohub', None)
    brand = getattr(vehicle, 'brand_name', '') or ''
    model = getattr(vehicle, 'model_name', '') or ''
    year = getattr(vehicle, 'year', None)
    mileage = getattr(vehicle, 'mileage', None)
    title = f'{brand} {model}'.strip() or f'Лот {lot.lot_id}'

    photo = ''
    images = list(lot.images.all()[:1]) if hasattr(lot, 'images') else []
    if images:
        img = images[0]
        photo = getattr(img, 'display_url', None) or ''
        if not photo:
            file_field = getattr(img, 'file', None)
            if file_field:
                try:
                    photo = file_field.url
                except Exception:
                    photo = ''
            if not photo:
                photo = getattr(img, 'url_preview', '') or getattr(img, 'url', '') or ''

    buyout = getattr(lot, 'latest_estimation_price', None)
    zna = getattr(lot, 'latest_zna', None)
    profit = getattr(lot, 'latest_profit', None)
    our_bid = primary.bid if primary else None
    manual_max = primary.manual_max_bid if primary else None
    manual_max_set_at = (
        _format_dt_local(primary.manual_max_bid_set_at) if primary else None
    )
    manual_max_set_by = ''
    if primary is not None:
        from auction_avito.services.manual_max import user_display_name
        manual_max_set_by = user_display_name(getattr(primary, 'manual_max_bid_set_by', None))
    dealer_id = primary.account.dealer_id if primary and primary.account_id else None
    max_bid = lot.max_bid

    # История наших ставок (по всем офферам лота) — только чтение
    bid_history = []
    for o in offers:
        for h in list(o.bid_history.all()):
            bid_history.append({
                'id': h.pk,
                'bid': h.bid,
                'bidMadeAt': _format_dt_local(h.bid_made_at),
                'comment': h.comment or '',
                'dealerId': o.account.dealer_id if o.account_id else None,
            })
    bid_history.sort(
        key=lambda x: (x.get('bidMadeAt') or '', x.get('id') or 0),
        reverse=True,
    )
    our_bids_count = len(bid_history)
    if our_bids_count == 0 and our_bid:
        our_bids_count = 1
        bid_history = [{
            'id': None,
            'bid': our_bid,
            'bidMadeAt': '',
            'comment': '',
            'dealerId': dealer_id,
        }]

    position = _bid_position(
        our_bid=our_bid,
        max_bid=max_bid,
        our_bids_count=our_bids_count,
    )

    # Последнее решение автоставки
    auto_decision = None
    if primary and hasattr(primary, 'decisions_desc') and primary.decisions_desc:
        auto_decision = primary.decisions_desc[0]
    elif primary:
        auto_decision = primary.auto_bid_decisions.order_by('-created_at').first()

    if auto_decision:
        auto_reason = (auto_decision.reason or '').strip()
        auto_category = (auto_decision.reason_category or '').strip()
        auto_should = bool(auto_decision.should_bid)
        auto_label = REASON_CATEGORY_LABELS.get(auto_category, '') or (
            'Ставка разрешена' if auto_should else 'Пропуск'
        )
        auto_text = auto_reason or auto_label
        auto_at = _format_dt_local(auto_decision.created_at)
    else:
        # Фоллбек без журнала — по текущей позиции ставки
        auto_should = False
        auto_category = ''
        auto_at = ''
        if position['isOutbid']:
            auto_text = 'Наша ставка перебита — нужна доставка / пересчёт'
            auto_label = 'Перебита'
        elif position['isSole']:
            auto_text = 'Наша ставка единственная (без конкурентов)'
            auto_label = 'Без конкурентов'
        elif position['isLeading']:
            auto_text = 'Наша ставка лидирует'
            auto_label = 'Лидируем'
        elif our_bid:
            auto_text = 'Есть наша ставка'
            auto_label = 'Ставка есть'
        else:
            auto_text = 'Автоставка ещё не оценивалась'
            auto_label = 'Нет оценки'

    # Позиция ставки важнее устаревшего skip/ok из журнала
    if position['isOutbid']:
        display_badge = 'Ставка перебита'
        if auto_text and 'перебит' not in auto_text.lower():
            display_auto = f'Ставка перебита. {auto_text}'
        else:
            display_auto = auto_text or 'Наша ставка перебита'
    elif position['isSole']:
        display_badge = 'Без конкурентов'
        display_auto = auto_text if auto_category == 'already_ours' else (
            'Без конкурентов — наша ставка единственная и максимальная'
        )
    elif position['isLeading']:
        display_badge = 'Наша ставка лидирует'
        display_auto = auto_text if (
            'лидир' in (auto_text or '').lower()
            or auto_category == 'already_ours'
        ) else 'Наша ставка лидирует'
    else:
        display_auto = auto_text
        display_badge = auto_label if not our_bid else (position['label'] or auto_label)

    finish = lot.finish_at
    try:
        finish_iso = finish.strftime('%d.%m.%Y %H:%M') if finish else ''
        finish_human = str(finish_iso or '')
    except Exception:
        finish_iso = str(finish or '')
        finish_human = finish_iso

    maxposter_url = ''
    if primary and primary.lot_offer_id:
        maxposter_url = f'https://app.maxposter.ru/dealer/auction/{primary.lot_offer_id}/view'

    seller_wish_price = lot.min_price  # «Желание продавца» на карточке лота
    trade_in_comment = (lot.trade_in_comment or '').strip()
    if not trade_in_comment:
        trade_in_comment = str(((lot.raw_lot_json or {}).get('tradeIn') or {}).get('comment') or '').strip()

    return {
        'lotPk': lot.pk,
        'lotId': lot.lot_id,
        'lotOfferId': primary.lot_offer_id if primary else None,
        'title': title,
        'brand': brand,
        'model': model,
        'year': year,
        'mileage': mileage,
        'photo': photo,
        'statusCode': primary.status_code if primary else '',
        'statusName': primary.status_name if primary else '',
        'outcomeCode': primary.outcome_code if primary else '',
        'outcomeTitle': primary.outcome_title if primary else '',
        'outcomeDetail': primary.outcome_detail if primary else '',
        'minPrice': seller_wish_price,
        'sellerWishPrice': seller_wish_price,
        'tradeInComment': trade_in_comment,
        'minAvailableBid': lot.min_available_bid,
        'maxAvailableBid': lot.max_available_bid,
        'maxBid': max_bid,
        'minBidStep': primary.min_bid_step if primary else None,
        'bidL1': lot.bid_l1,
        'bidL2': lot.bid_l2,
        'imvLow': lot.imv_low,
        'imvMedian': lot.imv_median,
        'imvHigh': lot.imv_high,
        'ourBid': our_bid,
        'ourBidsCount': our_bids_count,
        'manualMaxBid': manual_max,
        'manualMaxBidSetAt': manual_max_set_at,
        'manualMaxBidSetBy': manual_max_set_by,
        'buyout': int(buyout) if buyout not in (None, '') else None,
        'zna': int(zna) if zna not in (None, '') else None,
        'profit': int(profit) if profit not in (None, '') else None,
        'dealerId': dealer_id,
        'dealerLabel': dealer_label(dealer_id) if dealer_id else '',
        'place': (lot.venue.display_label if lot.venue_id else '') or (lot.seller_place_name or ''),
        'finishAt': finish_iso,
        'finishHuman': finish_human,
        'portalLotUrl': f'/auction_avito/lots/{lot.pk}/',
        'maxposterUrl': maxposter_url,
        'bidPosition': position['code'],
        'bidPositionLabel': position['label'],
        'rowClass': position['rowClass'],
        'isOutbid': position['isOutbid'],
        'isSole': position['isSole'],
        'isLeading': position['isLeading'],
        'autoBidShould': auto_should,
        'autoBidCategory': auto_category,
        'autoBidReason': auto_text,
        'autoBidLabel': display_badge,
        'autoBidText': display_auto,
        'autoBidAt': auto_at,
        'bidHistory': bid_history,
        'handedToWorkAt': _format_dt_local(primary.handed_to_work_at) if primary else '',
        'isHandedToWork': bool(primary and primary.handed_to_work_at),
        'canHandToWork': bool(
            primary
            and not primary.handed_to_work_at
            and (
                (primary.outcome_code or '') in WIN_NOTIFY_OUTCOMES
                or (primary.status_code or '') == OUTCOME_WON
            )
        ),
    }


def platform_email_rows():
    accounts = {
        a.dealer_id: a
        for a in AvitoBidderAccount.objects.filter(is_active=True).order_by('dealer_id')
    }
    dealer_ids = sorted(set(KNOWN_DEALER_LABELS) | set(accounts))
    rows = []
    for did in dealer_ids:
        acc = accounts.get(did)
        rows.append({
            'dealer_id': did,
            'label': dealer_label(did),
            'account': acc,
            'emails': (acc.win_notify_emails if acc else '') or '',
            'has_account': acc is not None,
        })
    return rows
