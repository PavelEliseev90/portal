"""
Фоновые задачи по складам / refresh_cars.
Фото качаются асинхронно, чтобы /api/v1/refresh_cars/ быстро отвечал 1С.
Очередь: refresh_cars_photos (отдельный process_tasks, не путать со stock / Power BI).
"""
from __future__ import annotations

import logging
import os
import tempfile

import requests
from background_task import background
from django.core import files
from django.db.models import Q

from refs.models import RefCarsOrganization, RefCarsOrganizationFiles

logger = logging.getLogger(__name__)

DOWNLOAD_HEADERS = {
    'User-Agent': 'KorsPortal/1.0 (cars photo sync)',
}


def _photo_field(name: str, photo: dict):
    """Поддержка разных регистров ключей из 1С."""
    if not isinstance(photo, dict):
        return ''
    for key in (name, name.lower(), name.upper()):
        val = photo.get(key)
        if val not in (None, ''):
            return val
    return ''


def normalize_photos_payload(photos) -> list:
    """Сериализуемый список фото для background_task (JSON)."""
    if not photos:
        return []
    out = []
    for p in photos:
        if not isinstance(p, dict):
            continue
        name = _photo_field('Name', p) or ''
        url = _photo_field('Url', p) or ''
        url_mini = _photo_field('UrlMini', p) or ''
        if not name and not url:
            continue
        if not name:
            name = url.split('/')[-1] or 'photo'
        out.append({
            'Name': str(name),
            'Url': str(url),
            'UrlMini': str(url_mini),
            'Main': bool(_photo_field('Main', p) or p.get('main')),
            'Date': _photo_field('Date', p) or p.get('date'),
        })
    return out


def _file_is_downloaded(file_field) -> bool:
    return bool(file_field and getattr(file_field, 'name', ''))


def _download_to_tempfile(url: str):
    """Скачивает URL во временный файл. None при ошибке."""
    url = (url or '').strip()
    if not url:
        return None, None
    tmp_path = None
    try:
        response = requests.get(
            url,
            stream=True,
            timeout=60,
            headers=DOWNLOAD_HEADERS,
            allow_redirects=True,
        )
        if response.status_code != requests.codes.ok:
            logger.warning(
                'load_photos: bad status %s url=%s',
                response.status_code,
                url[:200],
            )
            return None, None
        fd, tmp_path = tempfile.mkstemp(suffix='.img')
        with os.fdopen(fd, 'wb') as tmp:
            for block in response.iter_content(1024 * 8):
                if block:
                    tmp.write(block)
        return tmp_path, os.path.basename(url.split('?')[0]) or 'photo.jpg'
    except Exception:
        logger.exception('load_photos: download failed url=%s', url[:200])
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        return None, None


def _save_file_from_temp(photo_object, field_name: str, tmp_path: str, file_name: str) -> bool:
    if not tmp_path or not os.path.exists(tmp_path):
        return False
    try:
        with open(tmp_path, 'rb') as fh:
            getattr(photo_object, field_name).save(file_name, files.File(fh), save=False)
        return True
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def load_photos(car: RefCarsOrganization, photos: list) -> None:
    """Скачивает фото авто со склада и пишет в RefCarsOrganizationFiles."""
    photos = normalize_photos_payload(photos or [])
    names = {p.get('Name') for p in photos if p.get('Name')}

    ref_photos = RefCarsOrganizationFiles.objects.filter(сars_organization=car)
    for ref_photo in ref_photos:
        if ref_photo.name not in names:
            ref_photo.delete()

    if not names:
        return

    for photo in photos:
        name = photo.get('Name') or ''
        if not name:
            continue

        url = photo.get('Url') or ''
        url_mini = photo.get('UrlMini') or ''

        photo_object = RefCarsOrganizationFiles.objects.filter(
            сars_organization=car,
            name=name,
        ).first()

        if photo_object and _file_is_downloaded(photo_object.file):
            # Уже скачано — обновляем только метаданные.
            photo_object.url = url or photo_object.url
            photo_object.url_mini = url_mini or photo_object.url_mini
            photo_object.main = bool(photo.get('Main'))
            if photo.get('Date'):
                photo_object.date = photo['Date']
            photo_object.save(update_fields=['url', 'url_mini', 'main', 'date'])
            continue

        if photo_object is None:
            photo_object = RefCarsOrganizationFiles(сars_organization=car, name=name)

        photo_object.url = url
        photo_object.url_mini = url_mini
        photo_object.main = bool(photo.get('Main'))
        if photo.get('Date'):
            photo_object.date = photo['Date']

        if not url:
            photo_object.save()
            continue

        tmp_path, file_name = _download_to_tempfile(url)
        if tmp_path is None:
            # Сохраняем URL для мониторинга и повторной загрузки.
            photo_object.save()
            continue

        _save_file_from_temp(photo_object, 'file', tmp_path, file_name)

        if url_mini:
            tmp_mini, mini_name = _download_to_tempfile(url_mini)
            if tmp_mini:
                _save_file_from_temp(
                    photo_object,
                    'file_mini',
                    tmp_mini,
                    mini_name or ('mini_' + file_name),
                )

        photo_object.save()


def retry_pending_photos(car: RefCarsOrganization) -> int:
    """Повторно скачать фото с сохранёнными URL (без file). Возвращает число попыток."""
    pending = RefCarsOrganizationFiles.objects.filter(сars_organization=car).filter(
        Q(file='') | Q(file__isnull=True),
    ).exclude(url='')
    photos = [
        {
            'Name': row.name,
            'Url': row.url,
            'UrlMini': row.url_mini,
            'Main': row.main,
            'Date': row.date,
        }
        for row in pending
    ]
    if not photos:
        return 0
    load_photos(car, photos)
    return len(photos)


@background(queue='refresh_cars_photos', remove_existing_tasks=True)
def load_photos_async(car_id: int, photos: list) -> None:
    """Фоновая загрузка фото после refresh_cars."""
    try:
        car = RefCarsOrganization.objects.get(pk=car_id)
    except RefCarsOrganization.DoesNotExist:
        logger.warning('load_photos_async: car %s not found', car_id)
        return
    try:
        load_photos(car, photos or [])
    except Exception:
        logger.exception('load_photos_async failed car_id=%s', car_id)


@background(queue='refresh_cars_photos', remove_existing_tasks=True)
def retry_pending_photos_async(car_id: int) -> None:
    try:
        car = RefCarsOrganization.objects.get(pk=car_id)
    except RefCarsOrganization.DoesNotExist:
        return
    retry_pending_photos(car)
