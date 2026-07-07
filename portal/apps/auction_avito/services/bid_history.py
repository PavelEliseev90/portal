"""История наших ставок по лоту (AvitoBidHistory)."""
from __future__ import annotations

from auction_avito.models import AvitoBidHistory, AvitoLot, AvitoLotOffer


def extract_bid_comment(offer_data: dict) -> str:
    if not offer_data:
        return ''
    for key in ('bidComment', 'comment', 'bid_comment', 'note', 'notes'):
        val = offer_data.get(key)
        if val and str(val).strip():
            return str(val).strip()
    bid_block = offer_data.get('bid')
    if isinstance(bid_block, dict):
        for key in ('comment', 'bidComment', 'note'):
            val = bid_block.get(key)
            if val and str(val).strip():
                return str(val).strip()
    return ''


def record_bid_history(offer: AvitoLotOffer, bid: int, offer_data: dict) -> AvitoBidHistory | None:
    """Сохранить запись истории при изменении ставки."""
    if bid is None:
        return None

    from auction_avito.services.sync import _dt

    bid_made_at = _dt(offer_data.get('bidMadeAt'))
    comment = extract_bid_comment(offer_data)
    bid_user = offer_data.get('bidMadeByUser') or {}

    existing = offer.bid_history.filter(bid=bid)
    if bid_made_at:
        existing = existing.filter(bid_made_at=bid_made_at)
    if existing.exists():
        entry = existing.order_by('-recorded_at').first()
        if entry and comment and not entry.comment:
            entry.comment = comment
            entry.save(update_fields=['comment'])
        return entry

    return AvitoBidHistory.objects.create(
        offer=offer,
        bid=bid,
        bid_made_at=bid_made_at,
        bid_made_by_avito_user_id=(bid_user.get('id') if bid_user else None),
        comment=comment,
    )


def ensure_offer_bid_history_backfill(offer: AvitoLotOffer) -> None:
    """Если история пуста — добавить текущую ставку оффера (для уже синхронизированных лотов)."""
    if offer.bid is None or offer.bid_history.exists():
        return
    record_bid_history(offer, offer.bid, offer.raw_offer_json or {})


def get_lot_bid_history(lot: AvitoLot):
    """Все наши ставки по лоту (через офферы), новые сверху."""
    for offer in lot.offers.all():
        ensure_offer_bid_history_backfill(offer)
    return (
        AvitoBidHistory.objects
        .filter(offer__lot=lot)
        .select_related('offer', 'offer__account')
        .order_by('-bid_made_at', '-recorded_at')
    )
