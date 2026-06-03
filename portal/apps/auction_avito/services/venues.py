"""
Площадки (dealerId + наименование + город) для лотов аукциона Авито.
"""
from __future__ import annotations

from auction_avito.models import AvitoVenue
from refs.models import RefCity


def extract_venue_hints(*sources: dict | None) -> dict:
    """
    Собирает dealerId, наименование и город (строка) из корня offer / lot / calculate_car.
    """
    dealer_id = None
    name = ''
    city_name = ''

    for src in sources:
        if not src:
            continue
        if dealer_id is None and src.get('dealerId') is not None:
            try:
                dealer_id = int(src['dealerId'])
            except (TypeError, ValueError):
                pass
        for key in ('sellerPlaceName', 'dealerName', 'placeName', 'sellerPlace'):
            val = src.get(key)
            if val and not name:
                name = str(val).strip()
        for key in ('sellerPlaceCity', 'dealerCity', 'city', 'placeCity'):
            val = src.get(key)
            if val and not city_name:
                if isinstance(val, dict):
                    city_name = str(val.get('name') or val.get('id') or '').strip()
                else:
                    city_name = str(val).strip()

    if not city_name and name and ',' in name:
        city_part, _, rest = name.partition(',')
        rest = rest.strip()
        if rest:
            city_name = city_part.strip()
            name = rest

    return {'dealer_id': dealer_id, 'name': name, 'city_name': city_name}


def resolve_ref_city(city_name: str) -> RefCity | None:
    city_name = (city_name or '').strip()
    if not city_name:
        return None
    return RefCity.objects.filter(name__iexact=city_name).first()


def upsert_venue(hints: dict) -> AvitoVenue | None:
    dealer_id = hints.get('dealer_id')
    if dealer_id is None:
        return None

    dealer_id = int(dealer_id)
    ref_city = resolve_ref_city(hints.get('city_name') or '')
    defaults = {
        'name': (hints.get('name') or '')[:500],
        'city': ref_city,
    }
    venue, created = AvitoVenue.objects.get_or_create(
        dealer_id=dealer_id,
        defaults=defaults,
    )
    if created:
        return venue

    update_fields = []
    # Наименование и город задаются вручную в админке — не перезаписываем при синхронизации.
    if not (venue.name or '').strip() and defaults['name']:
        venue.name = defaults['name']
        update_fields.append('name')
    if not venue.city_id and ref_city:
        venue.city = ref_city
        update_fields.append('city')
    if update_fields:
        venue.save(update_fields=update_fields)
    return venue


def resolve_venue_from_payload(payload: dict, lot_data: dict | None = None) -> AvitoVenue | None:
    lot_block = lot_data if lot_data is not None else (payload.get('lot') or {})
    hints = extract_venue_hints(payload, lot_block)
    return upsert_venue(hints)
