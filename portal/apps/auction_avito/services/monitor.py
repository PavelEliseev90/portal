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
    """Завершённые офферы со ставкой без финального статуса."""
    now = timezone.now()
    return (
        Q(bid__gt=0)
        & (Q(lot__finish_at__lte=now) | Q(status_code__in=['finished', 'ended', 'canceled', 'won', 'lost']))
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
    )


def monitor_lots_queryset(*, mode: str = 'active', dealer_ids: list[int] | None = None):
    dealer_ids = dealer_ids or []
    mode = (mode or 'active').strip()

    offer_qs = (
        AvitoLotOffer.objects
        .select_related('account')
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


def serialize_monitor_lot(lot) -> dict:
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
    our_bid = primary.bid if primary else None
    manual_max = primary.manual_max_bid if primary else None
    dealer_id = primary.account.dealer_id if primary and primary.account_id else None

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
        'minPrice': lot.min_price,
        'minAvailableBid': lot.min_available_bid,
        'maxBid': lot.max_bid,
        'minBidStep': primary.min_bid_step if primary else None,
        'ourBid': our_bid,
        'manualMaxBid': manual_max,
        'buyout': int(buyout) if buyout not in (None, '') else None,
        'dealerId': dealer_id,
        'dealerLabel': dealer_label(dealer_id) if dealer_id else '',
        'place': (lot.venue.display_label if lot.venue_id else '') or (lot.seller_place_name or ''),
        'finishAt': finish_iso,
        'finishHuman': finish_human,
        'portalLotUrl': f'/auction_avito/lots/{lot.pk}/',
        'maxposterUrl': maxposter_url,
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
