"""
Синхронизация offers[] из API Авито в модели auction_avito.

Использование (после реализации HTTP-клиента):
    from auction_avito.services.sync import upsert_offer_from_api

    for item in payload['offers']:
        upsert_offer_from_api(account, item)
"""
import re

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

_RE_NAIVE_DT = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})')

from auction_avito.models import (
    AvitoAutotekaEvent,
    AvitoAutotekaReport,
    AvitoBidderAccount,
    AvitoLot,
    AvitoVenue,
    AvitoLotAutohubVehicle,
    AvitoLotBadge,
    AvitoLotEquipment,
    AvitoLotImage,
    AvitoLotOffer,
    AvitoLotVehicle,
    AvitoOfferBadge,
)
from auction_avito.services.badges import sync_lot_badges_records, sync_offer_badges_records
from auction_avito.services.venues import get_or_create_venue_by_dealer, resolve_venue_from_payload


# Поля лота: могут приходить на корне offer (парсер) или внутри lot (API Maxposter).
LOT_MERGE_KEYS = (
    'vehicle', 'autohubVehicle', 'minPrice', 'minAvailableBid', 'maxAvailableBid',
    'maxBid', 'autoteka', 'description', 'sellerPlaceName', 'finishAt', 'expiresAt',
    'originFinishAt', 'images', 'badges', 'badgesByStyle', 'equipment',
    'imvMarketRange', 'bidGroupV2', 'tradeIn', 'createdAt', 'updatedAt', 'dealerId',
)


def enrich_lot_data_from_payload(payload: dict) -> dict:
    """
    Собирает полный lot{} из корня offer и вложенного lot.
    Нужно для парсера: badgesByStyle/images часто на корне offer, а upsert читает lot.*.
    """
    if not isinstance(payload, dict):
        return {}
    lot = dict(payload.get('lot') or {})
    lot_id = payload.get('lotId') or lot.get('lotId')
    if lot_id is not None:
        lot['lotId'] = lot_id

    for key in LOT_MERGE_KEYS:
        root_val = payload.get(key)
        lot_val = lot.get(key)
        if root_val in (None, '', [], {}):
            continue
        if lot_val in (None, '', [], {}):
            lot[key] = root_val

    if payload.get('badgesByStyle'):
        lot['badgesByStyle'] = payload['badgesByStyle']
    if payload.get('badges') is not None:
        lot['badges'] = payload['badges']

    return lot


def _strip_tz(value):
    """2026-07-10T12:45:00+03:00 → 2026-07-10T12:45:00"""
    if value in (None, ''):
        return value
    if hasattr(value, 'year') and not isinstance(value, str):
        value = value.isoformat()
    s = str(value).strip()
    m = _RE_NAIVE_DT.match(s)
    return m.group(1) if m else s


def _dt(value):
    """Строка или datetime → naive local (USE_TZ=False)."""
    if value in (None, ''):
        return None
    if hasattr(value, 'year') and not isinstance(value, str):
        dt = value
    else:
        dt = parse_datetime(_strip_tz(value))
    if dt is None:
        return None
    if timezone.is_aware(dt):
        return timezone.make_naive(dt, timezone.get_current_timezone())
    return dt


def _clip(value, max_len: int) -> str:
    text = '' if value is None else str(value)
    if max_len <= 0:
        return ''
    return text[:max_len]


def _named(obj, default: str = '') -> str:
    """Достаёт name из dict/{name} или строки API."""
    if isinstance(obj, dict):
        val = obj.get('name')
        if val in (None, ''):
            val = obj.get('id')
        return '' if val in (None, '') else str(val)
    if obj in (None, ''):
        return default
    return str(obj)


def _named_id(obj):
    if isinstance(obj, dict):
        return obj.get('id')
    return None


def _as_int(value):
    if value in (None, ''):
        return None
    if isinstance(value, dict):
        value = value.get('name') or value.get('id')
    try:
        return int(float(str(value).replace(' ', '').replace(',', '.')))
    except (TypeError, ValueError):
        return None


def sync_lot_images(lot, images: list, *, replace: bool = True) -> int:
    """
    Сохраняет фото лота из массива API (lot.images[]).
    replace=False — только дописывает URL-фото Авито, не трогает загруженные в портал.
    """
    if replace:
        lot.images.filter(source=AvitoLotImage.SOURCE_AVITO).delete()
    count = 0
    base_order = lot.images.count() if not replace else 0
    for i, img in enumerate(images or []):
        if not img.get('url') and not img.get('urlPreview'):
            continue
        image_id = img.get('id')
        if image_id is None:
            image_id = -(base_order + i + 1)
        AvitoLotImage.objects.update_or_create(
            lot=lot,
            image_id=image_id,
            defaults={
                'source': AvitoLotImage.SOURCE_AVITO,
                'url': _clip(img.get('url') or '', 2048),
                'url_preview': _clip(img.get('urlPreview') or '', 2048),
                'file': None,
                'sort_order': base_order + i if not replace else i,
            },
        )
        count += 1
    return count


def sync_lot_badges(lot, badges: list | None, badges_by_style=None) -> int:
    """Бейджи уровня lot (lot.badges)."""
    return sync_lot_badges_records(
        lot, badges=badges, badges_by_style=badges_by_style,
    )


def sync_offer_badges(offer, offer_data: dict) -> int:
    """Бейджи оффера: badges[] и badgesByStyle[]."""
    return sync_offer_badges_records(offer, offer_data)


def sync_lot_equipment(lot, equipment: list | None) -> int:
    """lot.equipment[] — группы опций."""
    lot.equipment.all().delete()
    count = 0
    for eq in equipment or []:
        AvitoLotEquipment.objects.create(
            lot=lot,
            name=_clip(eq.get('name') or '', 300),
            values=eq.get('values') or [],
        )
        count += 1
    return count


def apply_lot_related_data(lot: AvitoLot, lot_data: dict) -> dict:
    """Фото, бейджи и комплектация лота — при каждом upsert."""
    return {
        'images': sync_lot_images(lot, lot_data.get('images') or [], replace=True),
        'badges': sync_lot_badges(
            lot,
            lot_data.get('badges'),
            lot_data.get('badgesByStyle'),
        ),
        'equipment': sync_lot_equipment(lot, lot_data.get('equipment')),
    }


def _upsert_lot(lot_data: dict, *, venue: AvitoVenue | None = None) -> AvitoLot:
    lot_id = lot_data['lotId']
    imv = lot_data.get('imvMarketRange') or {}
    bid_group = lot_data.get('bidGroupV2') or {}
    trade = lot_data.get('tradeIn') or {}

    full_defaults = {
        'description': lot_data.get('description') or '',
        'seller_place_name': _clip(lot_data.get('sellerPlaceName') or '', 500),
        'min_price': lot_data.get('minPrice'),
        'min_available_bid': lot_data.get('minAvailableBid'),
        'max_available_bid': lot_data.get('maxAvailableBid'),
        'max_bid': lot_data.get('maxBid'),
        'bid_l1': bid_group.get('l1'),
        'bid_l2': bid_group.get('l2'),
        'imv_low': imv.get('low'),
        'imv_median': imv.get('median'),
        'imv_high': imv.get('high'),
        'created_at': _dt(lot_data.get('createdAt')),
        'updated_at': _dt(lot_data.get('updatedAt')),
        'finish_at': _dt(lot_data.get('finishAt')),
        'origin_finish_at': _dt(lot_data.get('originFinishAt')),
        'expires_at': _dt(lot_data.get('expiresAt')),
        'trade_in_considers': trade.get('considersTradeIn'),
        'trade_in_looking_for_used': trade.get('lookingForUsedCar'),
        'trade_in_comment': trade.get('comment'),
        'raw_lot_json': lot_data,
    }

    scalar_api_keys = {
        'description': 'description',
        'seller_place_name': 'sellerPlaceName',
        'min_price': 'minPrice',
        'min_available_bid': 'minAvailableBid',
        'max_available_bid': 'maxAvailableBid',
        'max_bid': 'maxBid',
        'created_at': 'createdAt',
        'updated_at': 'updatedAt',
        'finish_at': 'finishAt',
        'origin_finish_at': 'originFinishAt',
        'expires_at': 'expiresAt',
    }
    defaults = {'raw_lot_json': lot_data}
    for field, api_key in scalar_api_keys.items():
        if api_key in lot_data:
            defaults[field] = full_defaults[field]

    if 'bidGroupV2' in lot_data:
        defaults['bid_l1'] = full_defaults['bid_l1']
        defaults['bid_l2'] = full_defaults['bid_l2']
    if 'imvMarketRange' in lot_data:
        defaults['imv_low'] = full_defaults['imv_low']
        defaults['imv_median'] = full_defaults['imv_median']
        defaults['imv_high'] = full_defaults['imv_high']
    if 'tradeIn' in lot_data:
        defaults['trade_in_considers'] = full_defaults['trade_in_considers']
        defaults['trade_in_looking_for_used'] = full_defaults['trade_in_looking_for_used']
        defaults['trade_in_comment'] = full_defaults['trade_in_comment']

    create_defaults = dict(full_defaults)
    if venue is not None:
        create_defaults['venue'] = venue

    lot, created = AvitoLot.objects.get_or_create(lot_id=lot_id, defaults=create_defaults)
    if not created:
        for key, value in defaults.items():
            setattr(lot, key, value)
        update_fields = list(defaults.keys())
        if venue is not None and not lot.venue_id:
            lot.venue = venue
            update_fields.append('venue')
        lot.save(update_fields=update_fields)
    apply_lot_related_data(lot, lot_data)
    return lot


def _upsert_vehicle_avito(lot: AvitoLot, vehicle: dict):
    if not vehicle:
        return
    AvitoLotVehicle.objects.update_or_create(
        lot=lot,
        defaults={
            'brand_id': _named_id(vehicle.get('brand')),
            'brand_name': _clip(_named(vehicle.get('brand')), 200),
            'model_id': _named_id(vehicle.get('model')),
            'model_name': _clip(_named(vehicle.get('model')), 200),
            'generation_id': _named_id(vehicle.get('generation')),
            'generation_name': _clip(_named(vehicle.get('generation')), 300),
            'modification_id': _named_id(vehicle.get('modification')),
            'modification_name': _clip(_named(vehicle.get('modification')), 300),
            'configuration_id': _named_id(vehicle.get('configuration')),
            'configuration_name': _clip(_named(vehicle.get('configuration')), 200),
            'year': _as_int(vehicle.get('year')),
            'mileage': _as_int(vehicle.get('mileage')),
            'body_type_name': _clip(_named(vehicle.get('bodyType')), 100),
            'engine_type_name': _clip(_named(vehicle.get('engineType')), 100),
            'transmission_name': _clip(_named(vehicle.get('transmission')), 100),
            'drive_name': _clip(_named(vehicle.get('drive')), 100),
            'color_name': _clip(_named(vehicle.get('color')), 100),
            'condition_name': _clip(_named(vehicle.get('condition')), 100),
            'owners_count_name': _clip(_named(vehicle.get('ownersCount')), 50),
            'doors_count': _as_int(vehicle.get('doorsCount')),
            'wheel_name': _clip(_named(vehicle.get('wheel')), 50),
            'vehicle_type_name': _clip(_named(vehicle.get('vehicleType')), 100),
            'registration_in_russia': _clip(_named(vehicle.get('registrationInRussia')), 100),
            'registration_number': _clip(vehicle.get('registrationNumber') or '', 50),
        },
    )


def _upsert_vehicle_autohub(lot: AvitoLot, ah: dict):
    if not ah:
        return
    AvitoLotAutohubVehicle.objects.update_or_create(
        lot=lot,
        defaults={
            'brand_id': ah.get('brandID'),
            'model_id': ah.get('modelID'),
            'generation_id': ah.get('generationID'),
            'modification_id': ah.get('modificationID'),
            'complectation_id': ah.get('complectationID'),
            'body_configuration_id': ah.get('bodyConfigurationID'),
            'year': _as_int(ah.get('year')),
            'km_distance': _as_int(ah.get('kmDistance')),
            'owner_count': _as_int(ah.get('ownerCount')),
            'body_type': _clip(ah.get('bodyType') or '', 50),
            'body_door_count': _as_int(ah.get('bodyDoorCount')),
            'drive_type': _clip(ah.get('driveType') or '', 30),
            'engine_type': _clip(ah.get('engineType') or '', 30),
            'engine_volume': ah.get('engineVolume'),
            'engine_power': ah.get('enginePower'),
            'gearbox_type': _clip(ah.get('gearboxType') or '', 30),
            'armored': ah.get('armored', False),
            'equipment_ids': ah.get('equipment') or [],
        },
    )


@transaction.atomic
def upsert_offer_from_api(account: AvitoBidderAccount, offer_data: dict) -> AvitoLotOffer:
    existing_offer = AvitoLotOffer.objects.filter(
        lot_offer_id=offer_data['lotOfferId'],
    ).first()
    old_bid = existing_offer.bid if existing_offer else None

    lot_data = enrich_lot_data_from_payload(offer_data)
    if not lot_data.get('lotId'):
        nested = offer_data.get('lot') or {}
        if nested.get('lotId') is not None:
            lot_data['lotId'] = nested['lotId']
    venue = resolve_venue_from_payload(offer_data, lot_data)
    if venue is None and account.dealer_id:
        venue = get_or_create_venue_by_dealer(account.dealer_id)
    lot = _upsert_lot(lot_data, venue=venue)
    _upsert_vehicle_avito(lot, lot_data.get('vehicle') or {})
    _upsert_vehicle_autohub(lot, lot_data.get('autohubVehicle') or {})

    autoteka = lot_data.get('autoteka') or {}
    report, _ = AvitoAutotekaReport.objects.update_or_create(
        lot=lot,
        defaults={'state_status': _clip((autoteka.get('state') or {}).get('status') or '', 50)},
    )
    report.events.all().delete()
    for ev in (autoteka.get('report') or {}).get('events') or []:
        AvitoAutotekaEvent.objects.create(
            report=report,
            event_type=_clip(ev.get('type') or '', 100),
            status=_clip(ev.get('status') or '', 50),
            description=ev.get('description') or '',
        )

    status = offer_data.get('status') or {}
    bid_user = offer_data.get('bidMadeByUser') or {}

    status_code = status.get('status') if 'status' in offer_data else None
    status_name = status.get('name') if 'status' in offer_data else None
    if status_code is None and existing_offer is not None:
        status_code = existing_offer.status_code
        status_name = existing_offer.status_name

    from auction_avito.services.offer_status import normalize_offer_status
    status_code, status_name = normalize_offer_status(
        status_code or '',
        lot.finish_at,
    )

    offer, _ = AvitoLotOffer.objects.update_or_create(
        lot_offer_id=offer_data['lotOfferId'],
        defaults={
            'lot': lot,
            'account': account,
            'status_code': _clip(status_code or '', 30),
            'status_name': _clip(status_name or '', 100),
            'bid': offer_data.get('bid'),
            'bid_made_at': _dt(offer_data.get('bidMadeAt')),
            'min_bid_step': offer_data.get('minBidStep'),
            'sale_cost': offer_data.get('saleCost'),
            'presale_preparation_cost': offer_data.get('presalePreparationCost'),
            'gm1_money': offer_data.get('gm1Money'),
            'gm1_percent': offer_data.get('gm1Percent'),
            'created_at': _dt(offer_data.get('createdAt')),
            'updated_at': _dt(offer_data.get('updatedAt')),
            'hidden_by_user_ids': offer_data.get('hiddenBy') or [],
            'is_buyout_on_site_available': offer_data.get('isBuyoutOnSiteAvailable', False),
            'is_inspection_on_site_available': offer_data.get('isInspectionOnSiteAvailable', False),
            'bid_made_by_avito_user_id': (bid_user.get('id') if bid_user else None),
            'bid_made_by_email': _clip(bid_user.get('email') or '', 254),
            'bid_made_by_first_name': _clip(bid_user.get('firstName') or '', 100),
            'bid_made_by_last_name': _clip(bid_user.get('lastName') or '', 100),
            'bid_made_by_middle_name': _clip(bid_user.get('middleName') or '', 100),
            'raw_offer_json': offer_data,
        },
    )

    sync_offer_badges(offer, offer_data)

    new_bid = offer_data.get('bid')
    if new_bid is not None and new_bid != old_bid:
        try:
            from auction_avito.services.bid_history import record_bid_history
            record_bid_history(offer, new_bid, offer_data)
        except Exception:
            pass
        try:
            from auction_avito.chat_utils import notify_new_bid_in_feed
            notify_new_bid_in_feed(offer.lot, new_bid, old_bid)
        except Exception:
            pass

    return offer
