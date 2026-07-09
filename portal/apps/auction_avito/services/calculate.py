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
    enrich_lot_data_from_payload,
    upsert_offer_from_api,
)
from auction_avito.services.venues import resolve_venue_from_payload


def _extract_ids(payload: dict) -> dict:
    lot_block = payload.get('lot') or {}
    return {
        'lot_id': payload.get('lotId') or lot_block.get('lotId'),
        'lot_offer_id': payload.get('lotOfferId') or lot_block.get('lotOfferId'),
        'bidder_id': payload.get('bidderId') or lot_block.get('bidderId') or 72,
        'dealer_id': payload.get('dealerId') or lot_block.get('dealerId') or 2107,
    }


def _int_id(value):
    if value in (None, ''):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def ensure_lot_synced_from_calculate_request(payload: dict) -> dict | None:
    """
    Создаёт/обновляет лот и оффер на портале до расчёта цены.
    Ключ связки: lotOfferId (оффер) + lotId (лот Maxposter) — оба обязательны.
    """
    payload = normalize_calculate_car_request(payload)
    ids = _extract_ids(payload)
    lot_id = _int_id(ids['lot_id'])
    lot_offer_id = _int_id(ids['lot_offer_id'])
    if not lot_id or not lot_offer_id:
        return None

    payload['lotId'] = lot_id
    payload['lotOfferId'] = lot_offer_id
    lot, offer = upsert_lot_from_calculate_request(payload)
    if offer is None:
        return None

    from auction_avito.services.offer_api import build_offer_state_response

    state = build_offer_state_response(offer)
    state['lotId'] = lot.lot_id
    state['lotOfferId'] = offer.lot_offer_id
    return state


def normalize_calculate_car_request(payload: dict) -> dict:
    """
    Нормализует тело запроса: полный offer Maxposter или плоский lot.
    calculate_car ожидает vehicle/autohubVehicle/minPrice на корне.
    """
    if not isinstance(payload, dict):
        return payload

    data = dict(payload)
    pascal_aliases = (
        ('lotId', 'LotId'),
        ('lotOfferId', 'LotOfferId'),
        ('dealerId', 'DealerId'),
        ('bidderId', 'BidderId'),
        ('bid', 'Bid'),
        ('bidMadeAt', 'BidMadeAt'),
    )
    for camel, pascal in pascal_aliases:
        if data.get(camel) in (None, '') and data.get(pascal) not in (None, ''):
            data[camel] = data[pascal]

    lot = data.get('lot')
    if isinstance(lot, dict):
        root_from_lot = (
            'vehicle', 'autohubVehicle', 'minPrice', 'minAvailableBid', 'maxAvailableBid',
            'maxBid', 'autoteka', 'description', 'sellerPlaceName', 'finishAt', 'expiresAt',
            'originFinishAt', 'images', 'badges', 'badgesByStyle', 'equipment', 'imvMarketRange',
            'bidGroupV2', 'tradeIn', 'createdAt', 'updatedAt',
        )
        for key in root_from_lot:
            if key in lot and key not in data:
                data[key] = lot[key]

        if data.get('lotId') in (None, '') and lot.get('lotId') not in (None, ''):
            data['lotId'] = lot['lotId']
        if data.get('lotOfferId') in (None, '') and lot.get('lotOfferId') not in (None, ''):
            data['lotOfferId'] = lot['lotOfferId']
        if data.get('dealerId') in (None, '') and lot.get('dealerId') not in (None, ''):
            data['dealerId'] = lot['dealerId']

    data['lot'] = enrich_lot_data_from_payload(data)

    return data


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
    data = enrich_lot_data_from_payload(payload)
    data['lotId'] = lot_id
    return data


def build_offer_sync_payload(payload: dict) -> dict | None:
    """Полный offer для upsert_offer_from_api (расчёт / ставка / парсер)."""
    payload = normalize_calculate_car_request(payload)
    ids = _extract_ids(payload)
    lot_id = _int_id(ids['lot_id'])
    lot_offer_id = _int_id(ids['lot_offer_id'])
    if not lot_offer_id or not lot_id:
        return None

    lot_data = enrich_lot_data_from_payload(payload)
    lot_data['lotId'] = lot_id

    out = dict(payload)
    out['lotId'] = lot_id
    out['lotOfferId'] = lot_offer_id
    out['lot'] = lot_data
    out.setdefault('bidderId', ids['bidder_id'])
    out.setdefault('dealerId', ids['dealer_id'])
    if not isinstance(out.get('status'), dict):
        out['status'] = out.get('status') or {}
    return out


def _offer_payload_from_calculate_request(payload: dict, lot_id: int) -> dict | None:
    """Собирает offer для upsert_offer_from_api из тела calculate_car."""
    built = build_offer_sync_payload(payload)
    if built:
        return built
    return None


@transaction.atomic
def upsert_lot_from_calculate_request(payload: dict):
    """
    Создаёт/обновляет лот (и оффер, если передан полный offer) по данным запроса расчёта.
    Возвращает (lot, offer|None) или (None, None) если нет lotId.
    """
    payload = normalize_calculate_car_request(payload)
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
    payload = normalize_calculate_car_request(payload)
    ids = _extract_ids(payload)
    lot_existed = False
    if ids.get('lot_id'):
        from auction_avito.models import AvitoLot
        lot_existed = AvitoLot.objects.filter(lot_id=int(ids['lot_id'])).exists()

    lot, offer = upsert_lot_from_calculate_request(payload)
    if lot is None:
        return None

    if not lot_existed and not error_message and isinstance(result, dict):
        try:
            from auction_avito.chat_utils import notify_new_lot_in_feed
            notify_new_lot_in_feed(lot, user=user)
        except Exception:
            pass

    try:
        from auction_avito.services.expiry import expire_overdue_lots
        expire_overdue_lots()
    except Exception:
        pass

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
            return save_calculation_result(
                payload,
                result if isinstance(result, dict) else {},
                unit=unit,
                user=user,
                error_message=error_message or str(exc),
            )
        except Exception:
            pass
        return None


def build_calculation_sync_response(calc) -> dict | None:
    """Состояние лота/оффера после расчёта для парсера."""
    if calc is None:
        return None
    from auction_avito.services.offer_api import build_offer_state_response

    offer = calc.offer
    if offer is None and calc.lot_id:
        offer = (
            calc.lot.offers
            .select_related('lot', 'account', 'lot__venue', 'lot__venue__city')
            .order_by('-updated_at')
            .first()
        )
    if offer is None:
        lot = calc.lot
        lot_offer_id = None
        raw = calc.raw_request_json if isinstance(calc.raw_request_json, dict) else {}
        ids = _extract_ids(raw)
        lot_offer_id = _int_id(ids.get('lot_offer_id'))
        return {
            'ok': True,
            'lotId': lot.lot_id if lot else None,
            'lotOfferId': lot_offer_id,
            'lotPk': lot.pk if lot else None,
            'bid': None,
            'bidMadeAt': '',
            'calculationId': calc.pk,
        }

    state = build_offer_state_response(offer)
    state['calculationId'] = calc.pk
    state['lotId'] = offer.lot.lot_id if offer.lot_id else state.get('lotId')
    state['lotOfferId'] = offer.lot_offer_id
    return state
