"""
Загрузка фотографий лота: из сохранённого JSON, API offers или файлов с диска.
"""
import logging

import requests
from django.conf import settings
from requests.auth import HTTPBasicAuth

from auction_avito.models import AvitoBidderAccount, AvitoLot, AvitoLotImage, AvitoLotOffer
from auction_avito.services.sync import sync_lot_images, upsert_offer_from_api

logger = logging.getLogger(__name__)


def _images_from_payload(payload: dict) -> list:
    if not payload:
        return []
    if isinstance(payload.get('images'), list):
        return payload['images']
    lot = payload.get('lot')
    if isinstance(lot, dict) and isinstance(lot.get('images'), list):
        return lot['images']
    return []


def reload_images_from_stored_json(lot: AvitoLot) -> tuple[int, str]:
    """Берёт images из raw_lot_json или raw_offer_json оффера."""
    images = _images_from_payload(lot.raw_lot_json)
    source = 'raw_lot_json'

    if not images:
        offer = lot.offers.order_by('-updated_at').first()
        if offer and offer.raw_offer_json:
            images = _images_from_payload(offer.raw_offer_json)
            source = 'raw_offer_json'

    if not images:
        return 0, 'В сохранённых данных лота нет массива images.'

    count = sync_lot_images(lot, images, replace=True)
    return count, f'Загружено {count} фото из {source}.'


def _find_offer_in_response(data, lot: AvitoLot, offer: AvitoLotOffer | None) -> dict | None:
    offers = data.get('offers') if isinstance(data, dict) else data
    if not isinstance(offers, list):
        return None
    for item in offers:
        lot_data = item.get('lot') or {}
        if lot_data.get('lotId') == lot.lot_id:
            return item
        if offer and item.get('lotOfferId') == offer.lot_offer_id:
            return item
    return None


def fetch_images_from_auction_api(lot: AvitoLot) -> tuple[int, str]:
    """
    Запрос списка offers (если задан AVITO_AUCTION_OFFERS_URL в settings).
    """
    api_url = getattr(settings, 'AVITO_AUCTION_OFFERS_URL', '') or ''
    if not api_url:
        return 0, 'API не настроен (AVITO_AUCTION_OFFERS_URL).'

    offer = lot.offers.select_related('account').order_by('-updated_at').first()
    account = offer.account if offer else None
    if not account:
        account = AvitoBidderAccount.objects.filter(is_active=True).first()
    if not account:
        return 0, 'Нет аккаунта AvitoBidderAccount для запроса.'

    username = getattr(settings, 'AVITO_AUCTION_API_USER', 'korsgroup@maxposter.ru')
    password = getattr(settings, 'AVITO_AUCTION_API_PASSWORD', '')

    try:
        params = {'dealerId': account.dealer_id}
        if getattr(settings, 'AVITO_AUCTION_API_BIDDER_ID', None):
            params['bidderId'] = settings.AVITO_AUCTION_API_BIDDER_ID

        response = requests.get(
            api_url,
            params=params,
            auth=HTTPBasicAuth(username, password),
            timeout=45,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        logger.exception('Avito auction offers API failed')
        return 0, f'Ошибка API: {exc}'

    offer_data = _find_offer_in_response(data, lot, offer)
    if not offer_data:
        return 0, f'Лот {lot.lot_id} не найден в ответе API.'

    upsert_offer_from_api(account, offer_data)
    count = len(offer_data.get('lot', {}).get('images') or [])
    return count, f'Синхронизировано с API: {count} фото.'


def load_lot_images(lot: AvitoLot, *, try_api: bool = True) -> dict:
    """
    Полная попытка загрузки: сначала API (если настроен), затем JSON из БД.
    """
    messages = []

    if try_api and getattr(settings, 'AVITO_AUCTION_OFFERS_URL', ''):
        count, msg = fetch_images_from_auction_api(lot)
        messages.append(msg)
        if count > 0:
            return {'ok': True, 'count': count, 'message': ' '.join(messages)}

    count, msg = reload_images_from_stored_json(lot)
    messages.append(msg)
    return {'ok': count > 0, 'count': count, 'message': ' '.join(messages)}


def save_uploaded_files(lot: AvitoLot, files) -> tuple[int, str]:
    """Добавляет фото, загруженные пользователем с диска (не удаляет URL с Авито)."""
    saved = 0
    base_order = lot.images.count()
    for i, uploaded in enumerate(files):
        if not uploaded:
            continue
        image_id = -(base_order + i + 1)
        while lot.images.filter(image_id=image_id).exists():
            image_id -= 1
        AvitoLotImage.objects.create(
            lot=lot,
            image_id=image_id,
            source=AvitoLotImage.SOURCE_UPLOAD,
            url='',
            url_preview='',
            file=uploaded,
            sort_order=base_order + i,
        )
        saved += 1
    if saved:
        return saved, f'Добавлено файлов: {saved}.'
    return 0, 'Файлы не выбраны.'
