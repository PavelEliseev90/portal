"""
Связь рабочего листа / интерактивной оценки с выигранным лотом Avito.
"""
from __future__ import annotations

from typing import Any, Optional

from django.urls import reverse


def get_avito_offer_for_rlk(doc_rlk) -> Optional[Any]:
    """Оффер выигрыша, привязанный к DocRLK (FK или UIN/номер)."""
    if doc_rlk is None:
        return None

    from auction_avito.models import AvitoLotOffer
    from auction_avito.services.win_rlk import _link_doc_rlk

    offer = (
        AvitoLotOffer.objects.filter(win_rlk_id=doc_rlk.pk)
        .select_related(
            'lot',
            'lot__venue',
            'lot__venue__city',
            'lot__venue__unit',
            'lot__vehicle_avito',
            'lot__vehicle_autohub',
            'account',
            'win_rlk',
        )
        .order_by('-updated_at', '-id')
        .first()
    )
    if offer is not None:
        return offer

    uin = (getattr(doc_rlk, 'uin', None) or '').strip()
    number = (getattr(doc_rlk, 'nomer', None) or '').strip()
    if not uin and not number:
        return None

    qs = AvitoLotOffer.objects.all()
    if uin:
        found = (
            qs.filter(win_rlk_uin=uin)
            .select_related(
                'lot',
                'lot__venue',
                'lot__venue__city',
                'lot__venue__unit',
                'lot__vehicle_avito',
                'lot__vehicle_autohub',
                'account',
            )
            .order_by('-updated_at', '-id')
            .first()
        )
        if found is not None:
            if found.win_rlk_id != doc_rlk.pk:
                AvitoLotOffer.objects.filter(pk=found.pk).update(win_rlk_id=doc_rlk.pk)
                found.win_rlk_id = doc_rlk.pk
            return found

    if number:
        found = (
            qs.filter(win_rlk_number=number)
            .select_related(
                'lot',
                'lot__venue',
                'lot__venue__city',
                'lot__venue__unit',
                'lot__vehicle_avito',
                'lot__vehicle_autohub',
                'account',
            )
            .order_by('-updated_at', '-id')
            .first()
        )
        if found is not None:
            if found.win_rlk_id != doc_rlk.pk:
                AvitoLotOffer.objects.filter(pk=found.pk).update(win_rlk_id=doc_rlk.pk)
                found.win_rlk_id = doc_rlk.pk
            return found

    # На случай, если DocRLK уже есть, а на оффере только номер/UIN ещё не совпали —
    # пробуем связать через тот же поиск, что при создании РЛ.
    unit = getattr(doc_rlk, 'unit', None)
    linked = _link_doc_rlk(uin, number, getattr(doc_rlk, 'dataTime', None), unit)
    if linked is not None and linked.pk == doc_rlk.pk:
        return (
            AvitoLotOffer.objects.filter(win_rlk_id=doc_rlk.pk)
            .select_related(
                'lot',
                'lot__venue',
                'lot__vehicle_avito',
                'lot__vehicle_autohub',
            )
            .first()
        )
    return None


def _vehicle_fill_hints(lot) -> dict[str, Any]:
    """Параметры авто с лота — подсказки для заполнения оценки."""
    vehicle = getattr(lot, 'vehicle_avito', None) if lot else None
    ah = getattr(lot, 'vehicle_autohub', None) if lot else None
    hints = {
        'brand': '',
        'model': '',
        'generation': '',
        'modification': '',
        'configuration': '',
        'year': None,
        'mileage': None,
        'body': '',
        'engine': '',
        'transmission': '',
        'drive': '',
        'color': '',
        'owners': '',
        'doors': None,
        'plate': '',
        'engine_volume': None,
        'engine_power': None,
    }
    if vehicle is not None:
        hints.update({
            'brand': vehicle.brand_name or '',
            'model': vehicle.model_name or '',
            'generation': vehicle.generation_name or '',
            'modification': vehicle.modification_name or '',
            'configuration': vehicle.configuration_name or '',
            'year': vehicle.year,
            'mileage': vehicle.mileage,
            'body': vehicle.body_type_name or '',
            'engine': vehicle.engine_type_name or '',
            'transmission': vehicle.transmission_name or '',
            'drive': vehicle.drive_name or '',
            'color': vehicle.color_name or '',
            'owners': vehicle.owners_count_name or '',
            'doors': vehicle.doors_count,
            'plate': vehicle.registration_number or '',
        })
    if ah is not None:
        if not hints['year']:
            hints['year'] = ah.year
        if not hints['mileage']:
            hints['mileage'] = ah.km_distance
        if not hints['body']:
            hints['body'] = ah.body_type or ''
        if not hints['engine']:
            hints['engine'] = ah.engine_type or ''
        if not hints['transmission']:
            hints['transmission'] = ah.gearbox_type or ''
        if not hints['drive']:
            hints['drive'] = ah.drive_type or ''
        if not hints['owners'] and ah.owner_count is not None:
            hints['owners'] = str(ah.owner_count)
        if not hints['doors']:
            hints['doors'] = ah.body_door_count
        hints['engine_volume'] = ah.engine_volume
        hints['engine_power'] = ah.engine_power
    return hints


def build_avito_auction_estimation_context(doc_rlk) -> Optional[dict[str, Any]]:
    """
    Контекст для UI оценки / ECO: лот, ставка, расчёт, подсказки по авто.
    None — если РЛ не из аукциона Avito.
    """
    offer = get_avito_offer_for_rlk(doc_rlk)
    if offer is None:
        return None

    lot = offer.lot
    calc = None
    if lot is not None:
        calc = (
            lot.calculations.filter(is_success=True)
            .order_by('-calculated_at')
            .first()
        )

    lot_url = ''
    if lot is not None:
        try:
            lot_url = reverse('auction_avito:lot_detail', kwargs={'pk': lot.pk})
        except Exception:
            lot_url = f'/auction_avito/lots/{lot.pk}/'

    maxposter_url = ''
    if offer.lot_offer_id:
        maxposter_url = (
            f'https://app.maxposter.ru/dealer/auction/{offer.lot_offer_id}/view'
        )

    vehicle_label_parts = []
    hints = _vehicle_fill_hints(lot)
    for part in (hints['brand'], hints['model'], hints['generation'], hints['year']):
        if part not in (None, ''):
            vehicle_label_parts.append(str(part))

    return {
        'is_avito_auction': True,
        'offer': offer,
        'lot': lot,
        'calc': calc,
        'bid': offer.bid,
        'manual_max_bid': offer.manual_max_bid,
        'outcome_code': offer.outcome_code,
        'outcome_title': offer.outcome_title,
        'win_rlk_number': offer.win_rlk_number,
        'win_rlk_uin': offer.win_rlk_uin,
        'win_rlk_date': offer.win_rlk_date,
        'lot_url': lot_url,
        'maxposter_url': maxposter_url,
        'vehicle_label': ' '.join(vehicle_label_parts).strip() or 'Лот Avito',
        'vehicle_hints': hints,
        'venue_name': (
            lot.venue.display_label if lot and lot.venue_id else ''
        ),
        'seller_place': (lot.seller_place_name if lot else '') or '',
        'description': (lot.description if lot else '') or '',
        'min_price': lot.min_price if lot else None,
        'max_bid': lot.max_bid if lot else None,
        'finish_at': lot.finish_at if lot else None,
        'price_steps': (calc.price_steps if calc else None) or [],
        'estimation_price': calc.estimation_price if calc else None,
        'zna': calc.zna if calc else None,
        'zg': (calc.price_group if calc else '') or '',
        'kf': calc.kf if calc else None,
    }
