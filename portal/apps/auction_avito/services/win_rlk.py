"""
Создание рабочего листа в 1С при выигрыше лота («Продавец выбрал вас»).

Подразделение берётся с площадки лота (AvitoVenue.unit); URL HTTP-сервиса —
из информационной базы подразделения (RefUnit.ib).
В 1С должен быть обработчик Type=CreateAvitoWorksheet, возвращающий Number/Date/Uin.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import requests
from django.utils import timezone
from django.utils.dateparse import parse_datetime

logger = logging.getLogger(__name__)

CREATE_AVITO_WORKSHEET_TYPE = 'CreateAvitoWorksheet'

# Fallback, как в task_manager (если у ИБ не заполнены server/base).
_URL_HS_KORS = 'http://a01srv1cka/zbusiness/hs/mb'
_URL_HS_ALFA = 'http://k01srv1c10/ralfa01/hs/mb'


def resolve_win_rlk_unit(offer):
    """Подразделение для РЛ: площадка лота → unit."""
    lot = getattr(offer, 'lot', None)
    venue = getattr(lot, 'venue', None) if lot else None
    unit = getattr(venue, 'unit', None) if venue else None
    if unit is not None:
        return unit
    return None


def hs_url_for_unit(unit) -> str | None:
    """URL HTTP-сервиса 1С по ИБ подразделения."""
    if unit is None:
        return None
    ib = getattr(unit, 'ib', None)
    if ib is not None:
        server = (getattr(ib, 'server', None) or '').strip()
        base = (getattr(ib, 'base', None) or '').strip()
        if server and base:
            return f'http://{server.lower()}/{base.lower()}/hs/mb'
        if getattr(ib, 'alfa', False):
            return _URL_HS_ALFA
    return _URL_HS_KORS


def _dt_iso(dt) -> str:
    if dt is None:
        return ''
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


def _money(v):
    if v in (None, ''):
        return None
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        return None


def build_create_avito_worksheet_payload(offer, unit) -> dict[str, Any]:
    lot = offer.lot
    venue = getattr(lot, 'venue', None) if lot else None
    vehicle = getattr(lot, 'vehicle_avito', None) if lot else None
    ah = getattr(lot, 'vehicle_autohub', None) if lot else None
    calc = None
    if lot is not None:
        calc = lot.calculations.filter(is_success=True).order_by('-calculated_at').first()
    account = getattr(offer, 'account', None)
    ib = getattr(unit, 'ib', None) if unit else None

    car_label_parts = []
    if vehicle:
        for part in (
            vehicle.brand_name,
            vehicle.model_name,
            vehicle.generation_name,
            vehicle.year,
        ):
            if part not in (None, ''):
                car_label_parts.append(str(part))
    car_label = ' '.join(car_label_parts).strip()

    return {
        'Type': CREATE_AVITO_WORKSHEET_TYPE,
        'Unit': {
            'Uin': (unit.uin or '') if unit else '',
            'Name': (unit.name or '') if unit else '',
            'Id': unit.pk if unit else None,
        },
        'Ib': {
            'Name': (ib.name or '') if ib else '',
            'Server': (ib.server or '') if ib else '',
            'Base': (ib.base or '') if ib else '',
            'Alfa': bool(getattr(ib, 'alfa', False)) if ib else False,
        },
        'Venue': {
            'DealerId': getattr(venue, 'dealer_id', None) if venue else None,
            'Name': (getattr(venue, 'name', None) or '') if venue else '',
            'City': (venue.city.name if venue and venue.city_id else '') if venue else '',
        },
        'Lot': {
            'LotId': getattr(lot, 'lot_id', None) if lot else None,
            'SellerPlaceName': (getattr(lot, 'seller_place_name', None) or '') if lot else '',
            'Description': (getattr(lot, 'description', None) or '') if lot else '',
            'MinPrice': getattr(lot, 'min_price', None) if lot else None,
            'MaxBid': getattr(lot, 'max_bid', None) if lot else None,
            'FinishAt': _dt_iso(getattr(lot, 'finish_at', None) if lot else None),
        },
        'Offer': {
            'LotOfferId': offer.lot_offer_id,
            'Bid': offer.bid,
            'StatusCode': offer.status_code or '',
            'OutcomeCode': offer.outcome_code or '',
            'OutcomeTitle': offer.outcome_title or '',
            'OutcomeDetail': offer.outcome_detail or '',
            'AccountDealerId': getattr(account, 'dealer_id', None) if account else None,
            'AccountBidderId': getattr(account, 'bidder_id', None) if account else None,
        },
        'Vehicle': {
            'Brand': getattr(vehicle, 'brand_name', '') or '',
            'Model': getattr(vehicle, 'model_name', '') or '',
            'Generation': getattr(vehicle, 'generation_name', '') or '',
            'Modification': getattr(vehicle, 'modification_name', '') or '',
            'Year': getattr(vehicle, 'year', None),
            'Mileage': getattr(vehicle, 'mileage', None),
            'BodyType': getattr(vehicle, 'body_type_name', '') or '',
            'EngineType': getattr(vehicle, 'engine_type_name', '') or '',
            'Transmission': getattr(vehicle, 'transmission_name', '') or '',
            'Drive': getattr(vehicle, 'drive_name', '') or '',
            'Color': getattr(vehicle, 'color_name', '') or '',
            'Owners': getattr(vehicle, 'owners_count_name', '') or '',
            'RegistrationNumber': getattr(vehicle, 'registration_number', '') or '',
            'Label': car_label,
            'Autohub': {
                'BrandId': getattr(ah, 'brand_id', None),
                'ModelId': getattr(ah, 'model_id', None),
                'GenerationId': getattr(ah, 'generation_id', None),
                'ModificationId': getattr(ah, 'modification_id', None),
                'ComplectationId': getattr(ah, 'complectation_id', None),
                'KmDistance': getattr(ah, 'km_distance', None),
                'OwnerCount': getattr(ah, 'owner_count', None),
            } if ah else {},
        },
        'Calculation': {
            'EstimationPrice': _money(getattr(calc, 'estimation_price', None) if calc else None),
            'Profit': _money(getattr(calc, 'profit', None) if calc else None),
            'Zna': _money(getattr(calc, 'zna', None) if calc else None),
            'Mileage': getattr(calc, 'mileage', None) if calc else None,
            'Year': getattr(calc, 'year', None) if calc else None,
            'CalculatedAt': _dt_iso(getattr(calc, 'calculated_at', None) if calc else None),
        } if calc else {},
        'Comment': (
            f'Аукцион Авито: лот {getattr(lot, "lot_id", "—")}, '
            f'offer {offer.lot_offer_id}, ставка {offer.bid or "—"}'
        ),
        'ClientName': car_label or f'Авито лот {getattr(lot, "lot_id", "")}',
        'Source': 'auction_avito',
    }


def _unwrap_1c_payload(raw: Any) -> dict:
    if not isinstance(raw, dict):
        return {}
    nested = raw.get('Data')
    if isinstance(nested, dict):
        # Data — обёртка ответа; поля Number/Uin/Date могут быть внутри.
        merged = {k: v for k, v in raw.items() if k != 'Data'}
        merged.update(nested)
        return merged
    return raw


def _parse_rlk_date(value) -> datetime | None:
    if value in (None, ''):
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    candidate = text
    if ' ' in text and 'T' not in text[:11]:
        candidate = text.replace(' ', 'T', 1)
    dt = parse_datetime(candidate)
    if dt is not None:
        return dt
    for fmt in ('%d.%m.%Y %H:%M:%S', '%d.%m.%Y %H:%M', '%d.%m.%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _extract_rlk_fields(payload: dict) -> dict[str, Any]:
    data = _unwrap_1c_payload(payload)
    number = (
        data.get('Number')
        or data.get('Nomer')
        or data.get('nomer')
        or data.get('WorksheetNumber')
        or ''
    )
    uin = data.get('Uin') or data.get('uin') or data.get('UID') or data.get('Guid') or ''
    date_raw = (
        data.get('Date')
        or data.get('dataTime')
        or data.get('WorksheetDate')
        or data.get('Дата')
    )
    success = data.get('Success')
    if success is None:
        success = bool(str(number).strip() or str(uin).strip())
    error = (
        data.get('Error')
        or data.get('Answer')
        or data.get('Message')
        or data.get('Text')
        or ''
    )
    return {
        'success': bool(success),
        'number': str(number or '').strip()[:100],
        'uin': str(uin or '').strip()[:200],
        'date': _parse_rlk_date(date_raw),
        'error': str(error or '').strip()[:2000],
        'raw': data,
    }


def _link_doc_rlk(uin: str, number: str, date_value, unit):
    """При наличии UIN пытаемся связать с DocRLK в портале (если уже пришёл из обмена)."""
    if not uin:
        return None
    from documents.models import DocRLK

    rlk = DocRLK.objects.filter(uin=uin).order_by('-id').first()
    if rlk is None and number:
        qs = DocRLK.objects.filter(nomer=number)
        if unit is not None:
            qs = qs.filter(unit=unit)
        rlk = qs.order_by('-id').first()
    return rlk


def create_win_rlk_in_1c(offer, *, force: bool = False) -> dict[str, Any]:
    """
    Отправляет данные лота в 1С для создания РЛ и сохраняет Number/Date/Uin на оффере.

    Возвращает dict: ok, reason, number, date, uin, update_fields, url, …
    Не бросает наружу сетевые ошибки — пишет их в offer.win_rlk_error.
    """
    from auction_avito.models import AvitoLotOffer

    offer = (
        AvitoLotOffer.objects.select_related(
            'lot',
            'lot__venue',
            'lot__venue__city',
            'lot__venue__unit',
            'lot__venue__unit__ib',
            'lot__vehicle_avito',
            'lot__vehicle_autohub',
            'account',
        ).get(pk=offer.pk)
    )

    update_fields: list[str] = []
    now = timezone.now()

    if not force and (offer.win_rlk_number or '').strip():
        return {
            'ok': True,
            'reason': 'already_created',
            'number': offer.win_rlk_number,
            'uin': offer.win_rlk_uin,
            'date': offer.win_rlk_date,
            'update_fields': [],
        }

    unit = resolve_win_rlk_unit(offer)
    if unit is None:
        err = 'У площадки лота не указано подразделение (AvitoVenue.unit).'
        offer.win_rlk_error = err
        offer.win_rlk_created_at = now
        offer.save(update_fields=['win_rlk_error', 'win_rlk_created_at'])
        logger.warning(
            'avito win RLK: no venue.unit lotOfferId=%s lotId=%s',
            offer.lot_offer_id,
            getattr(offer.lot, 'lot_id', None),
        )
        return {
            'ok': False,
            'reason': 'no_unit',
            'error': err,
            'update_fields': ['win_rlk_error', 'win_rlk_created_at'],
        }

    url = hs_url_for_unit(unit)
    if not url:
        err = f'Не удалось определить URL 1С для подразделения {unit.name}.'
        offer.win_rlk_error = err
        offer.win_rlk_created_at = now
        offer.save(update_fields=['win_rlk_error', 'win_rlk_created_at'])
        return {
            'ok': False,
            'reason': 'no_url',
            'error': err,
            'update_fields': ['win_rlk_error', 'win_rlk_created_at'],
        }

    payload = build_create_avito_worksheet_payload(offer, unit)
    try:
        response = requests.post(url, json=payload, timeout=60)
    except requests.RequestException as exc:
        err = f'Ошибка запроса к 1С ({url}): {exc}'
        offer.win_rlk_error = err[:2000]
        offer.win_rlk_created_at = now
        offer.save(update_fields=['win_rlk_error', 'win_rlk_created_at'])
        logger.exception(
            'avito win RLK request failed lotOfferId=%s url=%s',
            offer.lot_offer_id,
            url,
        )
        return {
            'ok': False,
            'reason': 'request_error',
            'error': err,
            'url': url,
            'update_fields': ['win_rlk_error', 'win_rlk_created_at'],
        }

    body_text = (response.text or '')[:4000]
    parsed: dict = {}
    try:
        parsed = response.json() if body_text else {}
    except (ValueError, json.JSONDecodeError):
        parsed = {}

    extracted = _extract_rlk_fields(parsed if isinstance(parsed, dict) else {})
    offer.win_rlk_created_at = now
    update_fields.extend(['win_rlk_created_at'])

    if response.status_code != 200 or not extracted['success'] or not (
        extracted['number'] or extracted['uin']
    ):
        err = (
            extracted['error']
            or f'1С не создала РЛ (HTTP {response.status_code}): {body_text[:500]}'
        )
        offer.win_rlk_error = err[:2000]
        update_fields.append('win_rlk_error')
        offer.save(update_fields=list(dict.fromkeys(update_fields)))
        logger.warning(
            'avito win RLK failed lotOfferId=%s status=%s body=%s',
            offer.lot_offer_id,
            response.status_code,
            body_text[:500],
        )
        return {
            'ok': False,
            'reason': '1c_error',
            'error': err,
            'url': url,
            'status_code': response.status_code,
            'update_fields': list(dict.fromkeys(update_fields)),
        }

    offer.win_rlk_number = extracted['number']
    offer.win_rlk_uin = extracted['uin']
    offer.win_rlk_date = extracted['date'] or now
    offer.win_rlk_error = ''
    update_fields.extend([
        'win_rlk_number', 'win_rlk_uin', 'win_rlk_date', 'win_rlk_error',
    ])

    rlk = _link_doc_rlk(offer.win_rlk_uin, offer.win_rlk_number, offer.win_rlk_date, unit)
    if rlk is not None:
        offer.win_rlk = rlk
        update_fields.append('win_rlk')

    offer.save(update_fields=list(dict.fromkeys(update_fields)))
    logger.info(
        'avito win RLK ok lotOfferId=%s number=%s uin=%s unit=%s',
        offer.lot_offer_id,
        offer.win_rlk_number,
        offer.win_rlk_uin,
        unit.pk,
    )
    return {
        'ok': True,
        'reason': 'created',
        'number': offer.win_rlk_number,
        'uin': offer.win_rlk_uin,
        'date': offer.win_rlk_date,
        'url': url,
        'update_fields': list(dict.fromkeys(update_fields)),
    }
