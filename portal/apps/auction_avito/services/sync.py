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
    AvitoLotAutohubVehicle,
    AvitoLotEquipment,
    AvitoLotImage,
    AvitoLotOffer,
    AvitoLotVehicle,
    AvitoLotBadge,
    AvitoOfferBadge,
)


def _dt(value):
    if not value:
        return None
    return parse_datetime(value)


def _upsert_lot(lot_data: dict) -> AvitoLot:
    lot_id = lot_data['lotId']
    imv = lot_data.get('imvMarketRange') or {}
    bid_group = lot_data.get('bidGroupV2') or {}
    trade = lot_data.get('tradeIn') or {}

    lot, _ = AvitoLot.objects.update_or_create(
        lot_id=lot_id,
        defaults={
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
        },
    )
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
    lot_data = offer_data['lot']
    lot = _upsert_lot(lot_data)
    _upsert_vehicle_avito(lot, lot_data.get('vehicle') or {})
    _upsert_vehicle_autohub(lot, lot_data.get('autohubVehicle') or {})

    # Images
    lot.images.all().delete()
    for i, img in enumerate(lot_data.get('images') or []):
        AvitoLotImage.objects.create(
            lot=lot,
            image_id=img['id'],
            url=img['url'],
            url_preview=img.get('urlPreview') or '',
            sort_order=i,
        )

    # Equipment
    lot.equipment.all().delete()
    for eq in lot_data.get('equipment') or []:
        AvitoLotEquipment.objects.create(
            lot=lot,
            name=eq.get('name') or '',
            values=eq.get('values') or [],
        )

    # Autoteka
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

    # Lot badges
    lot.badges.all().delete()
    for b in lot_data.get('badges') or []:
        AvitoLotBadge.objects.create(
            lot=lot,
            avito_badge_id=b['id'],
            badge_type=b.get('badgeType') or '',
            title=b.get('title') or '',
            description=b.get('description') or '',
            priority=b.get('priority') or 0,
        )

    status = offer_data.get('status') or {}
    bid_user = offer_data.get('bidMadeByUser') or {}

    offer, _ = AvitoLotOffer.objects.update_or_create(
        lot_offer_id=offer_data['lotOfferId'],
        defaults={
            'lot': lot,
            'account': account,
            'status_code': status.get('status') or '',
            'status_name': status.get('name') or '',
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

    offer.badges.all().delete()
    for b in offer_data.get('badges') or []:
        AvitoOfferBadge.objects.create(
            offer=offer,
            avito_badge_id=b['id'],
            badge_type=b.get('badgeType') or '',
            title=b.get('title') or '',
            description=b.get('description') or '',
            priority=b.get('priority') or 0,
        )
    for group in offer_data.get('badgesByStyle') or []:
        style = group.get('style') or ''
        for b in group.get('badges') or []:
            AvitoOfferBadge.objects.create(
                offer=offer,
                avito_badge_id=b['id'],
                badge_type=b.get('badgeType') or '',
                title=b.get('title') or '',
                description=b.get('description') or '',
                priority=b.get('priority') or 0,
                style=style,
            )

    return offer
