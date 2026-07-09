"""Разрешение/создание оффера для API фиксации ставки."""
from __future__ import annotations

from auction_avito.models import AvitoBidderAccount, AvitoLot, AvitoLotOffer
from auction_avito.services.calculate import _get_or_create_account
from auction_avito.services.sync import upsert_offer_from_api


def _int_or_none(value):
    if value in (None, ''):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def resolve_or_create_offer_for_bid(data: dict) -> tuple[AvitoLotOffer | None, str]:
    """Возвращает (offer, note). note пустой — найден существующий оффер."""
    lot_offer_id = _int_or_none(data.get('LotOfferId') or data.get('lotOfferId'))
    lot_id = _int_or_none(data.get('LotId') or data.get('lotId'))

    if lot_offer_id is not None:
        offer = (
            AvitoLotOffer.objects
            .select_related('lot', 'account')
            .filter(lot_offer_id=lot_offer_id)
            .first()
        )
        if offer:
            return offer, ''

    if lot_id is not None:
        offer = (
            AvitoLotOffer.objects
            .select_related('lot', 'account')
            .filter(lot__lot_id=lot_id)
            .order_by('-updated_at')
            .first()
        )
        if offer:
            return offer, 'resolved_by_lot_id'

    # Частая путаница: в LotOfferId передали lotId
    if lot_offer_id is not None and lot_id is None:
        offer = (
            AvitoLotOffer.objects
            .select_related('lot', 'account')
            .filter(lot__lot_id=lot_offer_id)
            .order_by('-updated_at')
            .first()
        )
        if offer:
            return offer, 'resolved_lot_offer_id_as_lot_id'
        lot = AvitoLot.objects.filter(lot_id=lot_offer_id).first()
        if lot:
            offer = lot.offers.select_related('lot', 'account').order_by('-updated_at').first()
            if offer:
                return offer, 'resolved_lot_offer_id_as_lot_id'
            lot_id = lot.lot_id

    if lot_offer_id is None:
        return None, ''

    if lot_id is None:
        lot = AvitoLot.objects.filter(lot_id=lot_offer_id).first()
        if lot:
            lot_id = lot.lot_id

    if lot_id is None:
        return None, ''

    bidder_id = _int_or_none(data.get('BidderId') or data.get('bidderId')) or 72
    dealer_id = _int_or_none(data.get('DealerId') or data.get('dealerId')) or 2107
    account = _get_or_create_account(bidder_id, dealer_id)

    offer_payload = {
        'lotOfferId': lot_offer_id,
        'bidderId': bidder_id,
        'dealerId': dealer_id,
        'lot': {
            'lotId': lot_id,
            'sellerPlaceName': data.get('SellerPlaceName') or data.get('sellerPlaceName') or '',
        },
        'status': {'status': 'inprogress', 'name': 'Активен'},
    }
    offer = upsert_offer_from_api(account, offer_payload)
    return offer, 'created_from_bid_api'


def offer_not_found_payload(data: dict, lot_offer_id) -> dict:
    lot_id = _int_or_none(data.get('LotId') or data.get('lotId'))
    hints = [
        'Проверьте LotOfferId (offerId) и LotId (lotId) — это разные идентификаторы.',
        'Если лот ещё не загружен, передайте LotId вместе с LotOfferId, BidderId и DealerId.',
        'Либо сначала вызовите /api/calculate_car/ для этого лота.',
    ]
    payload = {
        'error': 'offer not found',
        'lotOfferId': lot_offer_id,
        'lotId': lot_id,
        'hints': hints,
    }
    if lot_offer_id is not None:
        payload['offers_with_lot_id'] = AvitoLotOffer.objects.filter(
            lot__lot_id=lot_offer_id,
        ).count()
        payload['lot_exists'] = AvitoLot.objects.filter(lot_id=lot_offer_id).exists()
    return payload
