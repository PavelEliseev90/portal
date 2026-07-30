"""
Сохранение лота и истории расчётов из POST /api/calculate_car/.
"""
import json
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from refs.price_groups import normalize_price_group_display

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

# Повторный Maxposter/формула не чаще, чем раз в TTL — берём последний успешный расчёт лота.
CALC_REUSE_TTL = timedelta(hours=2)


def _compat_dt(dt):
    """
    Приводит datetime к тому же виду, что timezone.now() при текущих settings.USE_TZ.
    Иначе: TypeError can't subtract offset-naive and offset-aware datetimes.
    """
    if dt is None:
        return None
    from django.conf import settings

    if settings.USE_TZ:
        if timezone.is_naive(dt):
            return timezone.make_aware(dt, timezone.get_current_timezone())
        return dt
    # USE_TZ=False → now() naive; с БД иногда приходит aware
    if timezone.is_aware(dt):
        return timezone.make_naive(dt, timezone.get_current_timezone())
    return dt


def _age_seconds(earlier, later=None):
    """Разница later - earlier в секундах; при любой ошибке дат — None."""
    try:
        a = _compat_dt(earlier)
        b = _compat_dt(later if later is not None else timezone.now())
        if a is None or b is None:
            return None
        # Последний предохранитель, если драйвер БД вернул неожиданный tzinfo
        if timezone.is_aware(a) and timezone.is_naive(b):
            a = timezone.make_naive(a, timezone.get_current_timezone())
        elif timezone.is_naive(a) and timezone.is_aware(b):
            b = timezone.make_naive(b, timezone.get_current_timezone())
        return (b - a).total_seconds()
    except Exception:
        return None


def _force_recalc_requested(payload: dict) -> bool:
    if not isinstance(payload, dict):
        return False
    for key in ('forceRecalc', 'force_recalc', 'force', 'recalculate'):
        val = payload.get(key)
        if val in (True, 1, '1', 'true', 'True', 'yes', 'YES'):
            return True
    return False


def get_reusable_calculation(payload: dict, *, force: bool = False, max_age=None):
    """
    Последний успешный расчёт лота младше TTL (по умолчанию 2 часа).

    Назначение: парсер на каждом reload шлёт ВСЕ лоты в /api/calculate_car/,
    а здесь решаем — дергать Maxposter/zna заново или отдать сохранённый выкуп.
    forceRecalc / force=True — всегда новый расчёт (ручная кнопка).
    """
    if force or _force_recalc_requested(payload):
        return None

    payload = normalize_calculate_car_request(payload if isinstance(payload, dict) else {})
    lot_id = _int_id(_extract_ids(payload).get('lot_id'))
    if not lot_id:
        return None

    ttl = max_age if max_age is not None else CALC_REUSE_TTL
    if not isinstance(ttl, timedelta):
        try:
            ttl = timedelta(hours=float(ttl))
        except (TypeError, ValueError):
            ttl = CALC_REUSE_TTL

    calc = (
        AvitoLotCalculation.objects
        .filter(
            lot__lot_id=lot_id,
            is_success=True,
            estimation_price__isnull=False,
        )
        .select_related('lot', 'offer')
        .order_by('-calculated_at')
        .first()
    )
    if calc is None or calc.calculated_at is None:
        return None

    age_sec = _age_seconds(calc.calculated_at)
    if age_sec is None:
        # Непонятные даты — безопаснее пересчитать, чем падать
        return None
    if age_sec > ttl.total_seconds():
        return None

    # После смены настроек формулы (ТХТ, комиссия и т.п.) старый кэш невалиден.
    try:
        from auction_avito.models import AvitoAuctionSettings
        settings_updated = AvitoAuctionSettings.get_solo().updated_at
        # settings_updated - calculated_at > 0 → настройки новее расчёта
        delta = _age_seconds(calc.calculated_at, settings_updated)
        if delta is not None and delta > 0:
            return None
    except Exception:
        pass

    return calc


def answer_from_cached_calculation(calc: AvitoLotCalculation) -> dict:
    """Собирает answer для API из сохранённого расчёта (без повторного Maxposter)."""
    raw = calc.raw_answer_json if isinstance(calc.raw_answer_json, dict) else {}
    answer = {}
    if isinstance(raw, dict) and raw:
        answer = {
            k: v for k, v in raw.items()
            if k not in ('avito_sync', 'avito_calculation_id', 'avito_lot_id', 'from_cache', 'cached_at', 'cached_calculation_id')
        }

    # Гарантируем ключевые поля из колонок БД (надёжнее сырого JSON).
    defaults = {
        'estimation_price': calc.estimation_price,
        'profit': calc.profit,
        'zna': calc.zna,
        'hub_sale_price_avg': calc.zna,
        'hub_price_avg': calc.avg_days_in_sale,
        'zg': calc.price_group,
        'kf': calc.kf,
        'sale': calc.price_sale,
        'price_sale': calc.price_sale,
        'price_sale_rdo': calc.price_sale_rdo,
        'price_sale_kor': calc.price_sale_kor,
        'cna_expenses': calc.cna_expenses,
        'zachita_ot_ubitka': calc.zachita_ot_ubitka,
        'finance_price': calc.finance_price,
        'iznos_price': calc.iznos_price,
        'discount_torg': calc.discount_torg,
        'auction': calc.auction_risk,
        'list_info_price': calc.price_steps or [],
    }
    for key, val in defaults.items():
        if answer.get(key) is None and val is not None:
            answer[key] = val

    calculated_at = _compat_dt(calc.calculated_at)
    answer['from_cache'] = True
    answer['cached_calculation_id'] = calc.pk
    answer['cached_at'] = calculated_at.isoformat() if calculated_at else None
    return answer


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

    offer_payload = build_offer_sync_payload(payload)
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
    calc.price_group = normalize_price_group_display(result.get('zg'), price=result.get('zna'))[:30]
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
    except Exception:
        import logging
        logging.getLogger(__name__).exception('persist_auction_calculation failed')
        return None


def attach_avito_sync_to_answer(answer, calc=None):
    """Добавляет avito_sync в ответ calculate_car после upsert лота и расчёта."""
    if not isinstance(answer, dict) or calc is None:
        return answer
    sync_payload = build_calculation_sync_response(calc)
    if sync_payload:
        answer['avito_sync'] = sync_payload
        answer['avito_calculation_id'] = calc.pk
        answer['avito_lot_id'] = calc.lot_id
    return answer


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


def _ensure_vehicle_year_dict(vehicle: dict) -> dict:
    """calculate_car ждёт vehicle.year.id."""
    out = dict(vehicle or {})
    year = out.get('year')
    if isinstance(year, dict):
        if year.get('id') in (None, '') and year.get('name') not in (None, ''):
            try:
                year = {**year, 'id': int(year['name'])}
            except (TypeError, ValueError):
                pass
        out['year'] = year
        return out
    if year not in (None, ''):
        try:
            y = int(year)
            out['year'] = {'id': y, 'name': str(y)}
        except (TypeError, ValueError):
            out['year'] = {'id': year, 'name': str(year)}
    return out


def build_calculate_car_payload_from_lot(lot, *, force_recalc: bool = True) -> dict:
    """
    Собирает тело для /api/calculate_car/ из сохранённого лота/оффера.
    Приоритет: raw_offer_json → raw_lot_json → поля моделей vehicle_*.
    """
    offer = (
        lot.offers
        .select_related('account')
        .order_by('-updated_at', '-id')
        .first()
    )
    payload = {}

    raw_offer = getattr(offer, 'raw_offer_json', None) if offer else None
    if isinstance(raw_offer, dict) and raw_offer:
        payload = dict(raw_offer)

    raw_lot = lot.raw_lot_json if isinstance(lot.raw_lot_json, dict) else {}
    if raw_lot:
        lot_block = dict(payload.get('lot') or {})
        for key, value in raw_lot.items():
            if lot_block.get(key) in (None, '', [], {}):
                lot_block[key] = value
        if lot_block.get('lotId') in (None, ''):
            lot_block['lotId'] = lot.lot_id
        payload['lot'] = lot_block

    payload['lotId'] = lot.lot_id
    if offer and offer.lot_offer_id:
        payload['lotOfferId'] = offer.lot_offer_id
    if offer and offer.account_id:
        payload.setdefault('dealerId', offer.account.dealer_id)
        payload.setdefault('bidderId', offer.account.bidder_id)
    if getattr(lot, 'venue_id', None) and lot.venue_id:
        payload.setdefault('dealerId', lot.venue.dealer_id)

    # Дозаполнение из нормализованных моделей, если сырого JSON мало.
    ah = getattr(lot, 'vehicle_autohub', None)
    va = getattr(lot, 'vehicle_avito', None)

    if not isinstance(payload.get('autohubVehicle'), dict) or not payload.get('autohubVehicle'):
        if ah and ah.modification_id:
            payload['autohubVehicle'] = {
                'brandID': ah.brand_id,
                'modelID': ah.model_id,
                'generationID': ah.generation_id,
                'modificationID': ah.modification_id,
                'complectationID': ah.complectation_id,
                'bodyConfigurationID': ah.body_configuration_id,
                'year': ah.year,
                'kmDistance': ah.km_distance,
                'ownerCount': ah.owner_count,
                'bodyType': ah.body_type or '',
                'bodyDoorCount': ah.body_door_count,
                'driveType': ah.drive_type or '',
                'engineType': ah.engine_type or '',
                'engineVolume': ah.engine_volume,
                'enginePower': ah.engine_power,
                'gearboxType': ah.gearbox_type or '',
                'armored': bool(ah.armored),
                'equipment': ah.equipment_ids or [],
            }

    if not isinstance(payload.get('vehicle'), dict) or not payload.get('vehicle'):
        year = None
        mileage = None
        if va:
            year = va.year
            mileage = va.mileage
        if ah:
            year = year or ah.year
            mileage = mileage if mileage not in (None, '') else ah.km_distance
        if year is not None or mileage is not None:
            payload['vehicle'] = {
                'mileage': mileage,
                'year': {'id': year, 'name': str(year) if year is not None else ''},
            }
            if va:
                payload['vehicle'].update({
                    'brand': {'id': va.brand_id, 'name': va.brand_name or ''},
                    'model': {'id': va.model_id, 'name': va.model_name or ''},
                    'generation': {'id': va.generation_id, 'name': va.generation_name or ''},
                    'modification': {'id': va.modification_id, 'name': va.modification_name or ''},
                })
    else:
        payload['vehicle'] = _ensure_vehicle_year_dict(payload['vehicle'])

    if payload.get('minPrice') in (None, ''):
        min_price = lot.min_price
        if min_price is None:
            min_price = (payload.get('lot') or {}).get('minPrice')
        if min_price is None and offer:
            min_price = (offer.raw_offer_json or {}).get('minPrice')
        if min_price is not None:
            payload['minPrice'] = min_price

    if force_recalc:
        payload['forceRecalc'] = True

    return normalize_calculate_car_request(payload)


def validate_calculate_car_payload(payload):
    """Короткая проверка перед вызовом calculate_car. None = ок."""
    if not isinstance(payload, dict):
        return 'Пустой payload расчёта'
    vehicle = payload.get('vehicle') or {}
    ah = payload.get('autohubVehicle') or {}
    year = vehicle.get('year') if isinstance(vehicle, dict) else None
    year_id = year.get('id') if isinstance(year, dict) else year
    mileage = vehicle.get('mileage') if isinstance(vehicle, dict) else None
    if year_id in (None, ''):
        return 'Нет года выпуска (vehicle.year) — синхронизируйте лот с Maxposter'
    if mileage in (None, ''):
        return 'Нет пробега (vehicle.mileage) — синхронизируйте лот с Maxposter'
    if payload.get('minPrice') in (None, ''):
        return 'Нет minPrice — синхронизируйте лот с Maxposter'
    if not isinstance(ah, dict) or ah.get('modificationID') in (None, ''):
        return 'Нет autohubVehicle.modificationID — синхронизируйте лот с Maxposter'
    return None


def run_calculate_car_for_lot(lot, *, user=None, force_recalc: bool = True) -> dict:
    """
    Тот же путь, что POST /api/calculate_car/: собирает payload из лота и вызывает view.
    Возвращает {ok, answer|error, status_code, payload_error?}.
    """
    from rest_framework.test import APIRequestFactory, force_authenticate
    from api.views import calculate_car

    payload = build_calculate_car_payload_from_lot(lot, force_recalc=force_recalc)
    err = validate_calculate_car_payload(payload)
    if err:
        return {'ok': False, 'error': err, 'status_code': 400, 'payload': payload}

    factory = APIRequestFactory()
    req = factory.post('/api/calculate_car/', payload, format='json')
    if user is not None:
        force_authenticate(req, user=user)
    response = calculate_car(req)
    status_code = getattr(response, 'status_code', 500)
    data = getattr(response, 'data', None)
    if data is None:
        try:
            data = json.loads(response.content.decode('utf-8'))
        except Exception:
            data = {'error': 'empty response'}

    if status_code >= 400:
        error = ''
        if isinstance(data, dict):
            error = data.get('error') or data.get('answer') or str(data)
        else:
            error = str(data)
        return {
            'ok': False,
            'error': error or f'HTTP {status_code}',
            'status_code': status_code,
            'data': data,
            'payload': payload,
        }

    # calculate_car почти всегда HTTP 200: при сбое answer — строка или dict с error
    answer = data.get('answer') if isinstance(data, dict) else data
    if isinstance(answer, str):
        return {
            'ok': False,
            'error': answer,
            'status_code': status_code,
            'data': data,
            'payload': payload,
        }
    if isinstance(answer, dict) and answer.get('error') and answer.get('estimation_price') in (None, ''):
        return {
            'ok': False,
            'error': answer.get('error'),
            'status_code': status_code,
            'data': data,
            'payload': payload,
        }

    return {
        'ok': True,
        'answer': answer,
        'status_code': status_code,
        'data': data,
        'payload': payload,
    }
