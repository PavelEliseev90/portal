"""API-сериализация состояния оффера/ставки для парсера и внешних клиентов."""
from __future__ import annotations

from auction_avito.models import AvitoBidHistory, AvitoLotOffer
from auction_avito.services.bid_history import extract_bid_comment


def _int_or_none(value):
    if value in (None, ''):
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def resolve_offer_by_ids(
    *,
    lot_offer_id=None,
    lot_id=None,
) -> AvitoLotOffer | None:
    if lot_offer_id not in (None, ''):
        offer = (
            AvitoLotOffer.objects
            .select_related('lot', 'account', 'lot__venue', 'lot__venue__city')
            .filter(lot_offer_id=int(lot_offer_id))
            .first()
        )
        if offer:
            return offer

    if lot_id not in (None, ''):
        return (
            AvitoLotOffer.objects
            .select_related('lot', 'account', 'lot__venue', 'lot__venue__city')
            .filter(lot__lot_id=int(lot_id))
            .order_by('-updated_at')
            .first()
        )
    return None


def _format_dt(value) -> str:
    if not value:
        return ''
    try:
        return value.strftime('%Y-%m-%dT%H:%M:%S')
    except Exception:
        return str(value)


def serialize_bid_history_entry(entry: AvitoBidHistory) -> dict:
    return {
        'id': entry.pk,
        'bid': entry.bid,
        'bidMadeAt': _format_dt(entry.bid_made_at),
        'comment': entry.comment or '',
        'recordedAt': _format_dt(entry.recorded_at),
    }


def build_offer_state_response(offer: AvitoLotOffer, *, history_limit: int = 5) -> dict:
    lot = offer.lot
    history_qs = (
        offer.bid_history
        .order_by('-bid_made_at', '-recorded_at')[:max(1, history_limit)]
    )
    latest_history = history_qs.first()
    comment = extract_bid_comment(offer.raw_offer_json or {})
    if not comment and latest_history:
        comment = latest_history.comment or ''

    venue = lot.venue if lot else None
    venue_label = venue.display_label if venue else (lot.seller_place_name if lot else '')

    sync_stats = {}
    if lot:
        from auction_avito.models import AvitoAutotekaReport
        sync_stats = {
            'images': lot.images.count(),
            'lotBadges': lot.badges.count(),
            'equipment': lot.equipment.count(),
            'hasVehicleAvito': hasattr(lot, 'vehicle_avito'),
            'hasVehicleAutohub': hasattr(lot, 'vehicle_autohub'),
            'hasAutoteka': AvitoAutotekaReport.objects.filter(lot=lot).exists(),
        }
    sync_stats['offerBadges'] = offer.badges.count()

    return {
        'ok': True,
        'lotOfferId': offer.lot_offer_id,
        'lotId': lot.lot_id if lot else None,
        'lotPk': lot.pk if lot else None,
        'bid': offer.bid,
        'manualMaxBid': offer.manual_max_bid,
        'bidMadeAt': _format_dt(offer.bid_made_at),
        'bidComment': comment,
        'status': {
            'status': offer.status_code or '',
            'name': offer.status_name or '',
        },
        'outcome': {
            'code': offer.outcome_code or '',
            'title': offer.outcome_title or '',
            'detail': offer.outcome_detail or '',
            'syncedAt': _format_dt(offer.outcome_synced_at),
            'winEmailSentAt': _format_dt(offer.win_email_sent_at),
        },
        'dealerId': offer.account.dealer_id if offer.account_id else None,
        'bidderId': offer.account.bidder_id if offer.account_id else None,
        'venueLabel': venue_label,
        'historyId': latest_history.pk if latest_history else None,
        'history': [serialize_bid_history_entry(h) for h in history_qs],
        'portalLotUrl': f'/auction_avito/lots/{lot.pk}/' if lot else '',
        'syncStats': sync_stats,
    }


def build_offers_state_map(
    *,
    lot_offer_ids: list | None = None,
    lot_ids: list | None = None,
    history_limit: int = 3,
) -> dict:
    offer_ids = {_int_or_none(x) for x in (lot_offer_ids or [])}
    offer_ids.discard(None)
    lot_id_set = {_int_or_none(x) for x in (lot_ids or [])}
    lot_id_set.discard(None)

    by_offer: dict[str, dict] = {}
    by_lot: dict[str, dict] = {}

    if offer_ids:
        for offer in (
            AvitoLotOffer.objects
            .select_related('lot', 'account', 'lot__venue', 'lot__venue__city')
            .filter(lot_offer_id__in=offer_ids)
        ):
            payload = build_offer_state_response(offer, history_limit=history_limit)
            by_offer[str(offer.lot_offer_id)] = payload
            if offer.lot_id:
                by_lot[str(offer.lot.lot_id)] = payload

    missing_lot_ids = lot_id_set - {int(k) for k in by_lot.keys()}
    if missing_lot_ids:
        for lot_id in missing_lot_ids:
            offer = resolve_offer_by_ids(lot_id=lot_id)
            if offer:
                payload = build_offer_state_response(offer, history_limit=history_limit)
                by_lot[str(lot_id)] = payload
                by_offer.setdefault(str(offer.lot_offer_id), payload)

    return {
        'ok': True,
        'byLotOfferId': by_offer,
        'byLotId': by_lot,
    }
