"""Онлайн-монитор аукциона Авито: активные лоты, наши ставки, ожидание итога."""
from __future__ import annotations

from django.db.models import OuterRef, Prefetch, Q, Subquery

from auction_avito.models import (
    AvitoBidderAccount,
    AvitoLot,
    AvitoLotCalculation,
    AvitoLotOffer,
)
from auction_avito.services.offer_status import active_lots_q
from auction_avito.services.outcome import FINAL_OUTCOMES, OUTCOME_WAITING, OUTCOME_UNKNOWN
from django.utils import timezone

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

    return {
        'active': active,
        'active_our_bid': active_our_bid,
        'waiting_decision': waiting,
    }


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
        .select_related('account')
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
    else:
        qs = base.filter(active_lots_q())
        if dealer_ids:
            qs = qs.filter(offers__account__dealer_id__in=dealer_ids)
        qs = qs.distinct()

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
        finish_iso = finish.strftime('%Y-%m-%dT%H:%M:%S') if finish else ''
        finish_human = timezone.localtime(finish).strftime('%d.%m.%Y %H:%M') if finish else ''
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
