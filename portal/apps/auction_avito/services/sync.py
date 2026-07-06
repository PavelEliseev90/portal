"""
Синхронизация offers[] из API Авито в модели auction_avito.

Использование (после реализации HTTP-клиента):
    from auction_avito.services.sync import upsert_offer_from_api

    for item in payload['offers']:
        upsert_offer_from_api(account, item)
"""
from django.db import transaction
from django.utils.dateparse import parse_datetime

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
from auction_avito.services.venues import resolve_venue_from_payload, upsert_venue


def _dt(value):
    if not value:
        return None
    return parse_datetime(value)


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
                'url': img.get('url') or '',
                'url_preview': img.get('urlPreview') or '',
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
            name=eq.get('name') or '',
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
        'seller_place_name': lot_data.get('sellerPlaceName') or '',
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

    if venue is not None:
        defaults['venue'] = venue

    lot, created = AvitoLot.objects.get_or_create(lot_id=lot_id, defaults=full_defaults)
    if not created:
        for key, value in defaults.items():
            setattr(lot, key, value)
        lot.save(update_fields=list(defaults.keys()))
    apply_lot_related_data(lot, lot_data)
    return lot


def _upsert_vehicle_avito(lot: AvitoLot, vehicle: dict):
    if not vehicle:
        return
    AvitoLotVehicle.objects.update_or_create(
        lot=lot,
        defaults={
            'brand_id': (vehicle.get('brand') or {}).get('id'),
            'brand_name': (vehicle.get('brand') or {}).get('name') or '',
            'model_id': (vehicle.get('model') or {}).get('id'),
            'model_name': (vehicle.get('model') or {}).get('name') or '',
            'generation_id': (vehicle.get('generation') or {}).get('id'),
            'generation_name': (vehicle.get('generation') or {}).get('name') or '',
            'modification_id': (vehicle.get('modification') or {}).get('id'),
            'modification_name': (vehicle.get('modification') or {}).get('name') or '',
            'configuration_id': (vehicle.get('configuration') or {}).get('id'),
            'configuration_name': (vehicle.get('configuration') or {}).get('name') or '',
            'year': (vehicle.get('year') or {}).get('name') or (vehicle.get('year') or {}).get('id'),
            'mileage': vehicle.get('mileage'),
            'body_type_name': (vehicle.get('bodyType') or {}).get('name') or '',
            'engine_type_name': (vehicle.get('engineType') or {}).get('name') or '',
            'transmission_name': (vehicle.get('transmission') or {}).get('name') or '',
            'drive_name': (vehicle.get('drive') or {}).get('name') or '',
            'color_name': (vehicle.get('color') or {}).get('name') or '',
            'condition_name': (vehicle.get('condition') or {}).get('name') or '',
            'owners_count_name': (vehicle.get('ownersCount') or {}).get('name') or '',
            'doors_count': (vehicle.get('doorsCount') or {}).get('name'),
            'wheel_name': (vehicle.get('wheel') or {}).get('name') or '',
            'vehicle_type_name': (vehicle.get('vehicleType') or {}).get('name') or '',
            'registration_in_russia': (vehicle.get('registrationInRussia') or {}).get('name') or '',
            'registration_number': vehicle.get('registrationNumber') or '',
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
            'year': ah.get('year'),
            'km_distance': ah.get('kmDistance'),
            'owner_count': ah.get('ownerCount'),
            'body_type': ah.get('bodyType') or '',
            'body_door_count': ah.get('bodyDoorCount'),
            'drive_type': ah.get('driveType') or '',
            'engine_type': ah.get('engineType') or '',
            'engine_volume': ah.get('engineVolume'),
            'engine_power': ah.get('enginePower'),
            'gearbox_type': ah.get('gearboxType') or '',
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

    lot_data = dict(offer_data['lot'])
    if not lot_data.get('badges') and not lot_data.get('badgesByStyle'):
        if offer_data.get('badges'):
            lot_data['badges'] = offer_data.get('badges')
        if offer_data.get('badgesByStyle'):
            lot_data['badgesByStyle'] = offer_data.get('badgesByStyle')
    venue = resolve_venue_from_payload(offer_data, lot_data)
    if venue is None and account.dealer_id:
        venue = upsert_venue({
            'dealer_id': account.dealer_id,
            'name': lot_data.get('sellerPlaceName') or '',
            'city_name': '',
        })
    lot = _upsert_lot(lot_data, venue=venue)
    _upsert_vehicle_avito(lot, lot_data.get('vehicle') or {})
    _upsert_vehicle_autohub(lot, lot_data.get('autohubVehicle') or {})

    autoteka = lot_data.get('autoteka') or {}
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
            'status_code': status_code,
            'status_name': status_name or '',
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
            'bid_made_by_email': bid_user.get('email') or '',
            'bid_made_by_first_name': bid_user.get('firstName') or '',
            'bid_made_by_last_name': bid_user.get('lastName') or '',
            'bid_made_by_middle_name': bid_user.get('middleName') or '',
            'raw_offer_json': offer_data,
        },
    )

    sync_offer_badges(offer, offer_data)

    new_bid = offer_data.get('bid')
    if new_bid is not None and new_bid != old_bid:
        try:
            from auction_avito.chat_utils import notify_new_bid_in_feed
            notify_new_bid_in_feed(offer.lot, new_bid, old_bid)
        except Exception:
            pass

    try:
        from auction_avito.services.expiry import expire_overdue_lots
        expire_overdue_lots()
    except Exception:
        pass

    return offer
