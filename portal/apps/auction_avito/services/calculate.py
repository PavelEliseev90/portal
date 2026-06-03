"""
Сохранение лота и истории расчётов из POST /api/calculate_car/.
"""
from django.db import transaction

from auction_avito.models import (
    AvitoAutotekaEvent,
    AvitoAutotekaReport,
    AvitoBidderAccount,
    AvitoLotCalculation,
    AvitoLotOffer,
)
from auction_avito.services.sync import (
    _upsert_lot,
    _upsert_vehicle_autohub,
    _upsert_vehicle_avito,
    upsert_offer_from_api,
)
from auction_avito.services.venues import resolve_venue_from_payload


def _extract_ids(payload: dict) -> dict:
    lot_block = payload.get('lot') or {}
    return {
        'lot_id': payload.get('lotId') or lot_block.get('lotId'),
        'lot_offer_id': payload.get('lotOfferId'),
        'bidder_id': payload.get('bidderId') or 72,
        'dealer_id': payload.get('dealerId') or 2107,
    }


def _get_or_create_account(bidder_id: int, dealer_id: int) -> AvitoBidderAccount:
    account, created = AvitoBidderAccount.objects.get_or_create(
        bidder_id=bidder_id,
        defaults={'dealer_id': dealer_id},
    )
    if not created and account.dealer_id != dealer_id:
        account.dealer_id = dealer_id
        account.save(update_fields=['dealer_id'])
    return account


def _lot_payload_from_calculate_request(payload: dict, lot_id: int) -> dict:
    """Собирает структуру lot для upsert из тела calculate_car."""
    if payload.get('lot') and isinstance(payload['lot'], dict):
        data = dict(payload['lot'])
        data['lotId'] = lot_id
        return data
    return {
        'lotId': lot_id,
        'minPrice': payload.get('minPrice'),
        'minAvailableBid': payload.get('minAvailableBid'),
        'maxAvailableBid': payload.get('maxAvailableBid'),
        'maxBid': payload.get('maxBid'),
        'tradeIn': payload.get('tradeIn'),
        'vehicle': payload.get('vehicle'),
        'autohubVehicle': payload.get('autohubVehicle'),
        'autoteka': payload.get('autoteka'),
        'description': payload.get('description') or '',
        'sellerPlaceName': payload.get('sellerPlaceName') or '',
        'imvMarketRange': payload.get('imvMarketRange'),
        'bidGroupV2': payload.get('bidGroupV2'),
        'images': payload.get('images') or [],
        'badges': payload.get('badges') or [],
        'badgesByStyle': payload.get('badgesByStyle') or [],
        'equipment': payload.get('equipment') or [],
        'finishAt': payload.get('finishAt'),
        'expiresAt': payload.get('expiresAt'),
    }


def _offer_payload_from_calculate_request(payload: dict, lot_id: int) -> dict | None:
    """Собирает offer для upsert_offer_from_api из тела calculate_car."""
    lot_offer_id = payload.get('lotOfferId')
    if not lot_offer_id:
        return None
    if payload.get('lot') and isinstance(payload['lot'], dict):
        return payload
    return {
        'lotOfferId': lot_offer_id,
        'lot': _lot_payload_from_calculate_request(payload, lot_id),
        'bidderId': payload.get('bidderId'),
        'dealerId': payload.get('dealerId'),
        'badges': payload.get('badges') or [],
        'badgesByStyle': payload.get('badgesByStyle') or [],
        'status': payload.get('status') or {},
        'bid': payload.get('bid'),
        'bidMadeAt': payload.get('bidMadeAt'),
        'minBidStep': payload.get('minBidStep'),
        'saleCost': payload.get('saleCost'),
        'presalePreparationCost': payload.get('presalePreparationCost'),
        'gm1Money': payload.get('gm1Money'),
        'gm1Percent': payload.get('gm1Percent'),
        'createdAt': payload.get('createdAt'),
        'updatedAt': payload.get('updatedAt'),
        'hiddenBy': payload.get('hiddenBy') or [],
        'isBuyoutOnSiteAvailable': payload.get('isBuyoutOnSiteAvailable', False),
        'isInspectionOnSiteAvailable': payload.get('isInspectionOnSiteAvailable', False),
        'bidMadeByUser': payload.get('bidMadeByUser') or {},
    }


@transaction.atomic
def upsert_lot_from_calculate_request(payload: dict):
    """
    Создаёт/обновляет лот (и оффер, если передан полный offer) по данным запроса расчёта.
    Возвращает (lot, offer|None) или (None, None) если нет lotId.
    """
    ids = _extract_ids(payload)
    lot_id = ids['lot_id']
    if not lot_id:
        return None, None

    lot_id = int(lot_id)
    account = _get_or_create_account(ids['bidder_id'], ids['dealer_id'])
    offer = None

    offer_payload = _offer_payload_from_calculate_request(payload, lot_id)
    if offer_payload:
        offer = upsert_offer_from_api(account, offer_payload)
        return offer.lot, offer

    lot_data = _lot_payload_from_calculate_request(payload, lot_id)
    if isinstance(payload.get('lot'), dict):
        lot_block = payload['lot']
        if lot_block.get('badges') and not lot_data.get('badges'):
            lot_data['badges'] = lot_block['badges']
        if lot_block.get('images') and not lot_data.get('images'):
            lot_data['images'] = lot_block['images']

    venue = resolve_venue_from_payload(payload, lot_data)
    lot = _upsert_lot(lot_data, venue=venue)
    _upsert_vehicle_avito(lot, lot_data.get('vehicle') or payload.get('vehicle') or {})
    _upsert_vehicle_autohub(lot, lot_data.get('autohubVehicle') or payload.get('autohubVehicle') or {})

    autoteka = lot_data.get('autoteka') or payload.get('autoteka')
    if autoteka:
        report, _ = AvitoAutotekaReport.objects.update_or_create(
            lot=lot,
            defaults={'state_status': (autoteka.get('state') or {}).get('status') or ''},
        )
        report.events.all().delete()
        for ev in (autoteka.get('report') or {}).get('events') or []:
            AvitoAutotekaEvent.objects.create(
                report=report,
                event_type=ev.get('type') or '',
                status=ev.get('status') or '',
                description=ev.get('description') or '',
            )

    return lot, None


def _int_or_none(value):
    if value is None or value == '':
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


@transaction.atomic
def save_calculation_result(
    payload: dict,
    result: dict,
    *,
    unit=None,
    user=None,
    error_message: str = '',
) -> AvitoLotCalculation | None:
    """
    Сохраняет успешный или неуспешный расчёт в историю лота.
    """
    lot, offer = upsert_lot_from_calculate_request(payload)
    if lot is None:
        return None

    vehicle = payload.get('vehicle') or {}
    year_val = vehicle.get('year')
    if isinstance(year_val, dict):
        year_val = year_val.get('id') or year_val.get('name')

    calc = AvitoLotCalculation.objects.create(
        lot=lot,
        offer=offer,
        unit=unit,
        user=user if user and getattr(user, 'is_authenticated', False) else None,
        is_success=not error_message and isinstance(result, dict),
        error_message=error_message or '',
        min_price=_int_or_none(payload.get('minPrice')),
        mileage=_int_or_none(vehicle.get('mileage')),
        year=_int_or_none(year_val),
        raw_request_json=payload,
        raw_answer_json=result if isinstance(result, dict) else {'error': str(result)},
    )

    if not isinstance(result, dict):
        return calc

    auction_note = ''
    if result.get('auction'):
        for ev in (payload.get('autoteka') or {}).get('report', {}).get('events', []):
            if ev.get('status') != 'ok' and ev.get('type') in (
                'taxi', 'carsharing', 'mileageTwisted',
            ):
                auction_note += (ev.get('description') or ev.get('type')) + ' / '

    calc.estimation_price = _int_or_none(result.get('estimation_price'))
    calc.profit = _int_or_none(result.get('profit'))
    calc.zna = _int_or_none(result.get('zna'))
    calc.avg_days_in_sale = _int_or_none(result.get('hub_price_avg'))
    calc.price_group = str(result.get('zg') or '')[:30]
    calc.kf = result.get('kf')
    calc.price_sale = _int_or_none(result.get('price_sale') or result.get('sale'))
    calc.price_sale_rdo = _int_or_none(result.get('price_sale_rdo'))
    calc.price_sale_kor = _int_or_none(result.get('price_sale_kor'))
    calc.cna_expenses = _int_or_none(result.get('cna_expenses'))
    calc.zachita_ot_ubitka = _int_or_none(result.get('zachita_ot_ubitka'))
    calc.finance_price = _int_or_none(result.get('finance_price'))
    calc.iznos_price = _int_or_none(result.get('iznos_price'))
    calc.discount_torg = _int_or_none(result.get('discount_torg'))
    calc.auction_risk = bool(result.get('auction'))
    calc.auction_risk_note = auction_note.strip(' / ')
    calc.price_steps = result.get('list_info_price') or []
    calc.save()
    return calc


def persist_auction_calculation(payload, result, unit=None, user=None, error_message=''):
    """Обёртка для вызова из API: не пробрасывает исключения наружу."""
    try:
        return save_calculation_result(
            payload,
            result,
            unit=unit,
            user=user,
            error_message=error_message,
        )
    except Exception as exc:
        try:
            save_calculation_result(
                payload,
                result if isinstance(result, dict) else {},
                unit=unit,
                user=user,
                error_message=error_message or str(exc),
            )
        except Exception:
            pass
        return None
