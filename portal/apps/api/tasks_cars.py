"""
Фоновые задачи по складам / refresh_cars.
Фото качаются асинхронно, чтобы /api/v1/refresh_cars/ быстро отвечал 1С.
Очередь: refresh_cars_photos (отдельный process_tasks, не путать со stock / Power BI).
"""
from __future__ import annotations

import logging
import tempfile

import requests
from background_task import background
from django.core import files

from refs.models import RefCarsOrganization, RefCarsOrganizationFiles

logger = logging.getLogger(__name__)


def normalize_photos_payload(photos) -> list:
    """Сериализуемый список фото для background_task (JSON)."""
    if not photos:
        return []
    out = []
    for p in photos:
        if not isinstance(p, dict):
            continue
        out.append({
            'Name': p.get('Name') or '',
            'Url': p.get('Url') or '',
            'UrlMini': p.get('UrlMini') or '',
            'Main': bool(p.get('Main')),
            'Date': p.get('Date'),
        })
    return out


def _download_to_tempfile(url: str):
    """Скачивает URL во временный файл. None при ошибке."""
    if not url:
        return None
    try:
        response = requests.get(url, stream=True, timeout=60)
        if response.status_code != requests.codes.ok:
            return None
        lf = tempfile.NamedTemporaryFile()
        for block in response.iter_content(1024 * 8):
            if not block:
                break
            lf.write(block)
        lf.flush()
        return lf
    except Exception:
        logger.exception('load_photos: download failed url=%s', url)
        return None


def load_photos(car: RefCarsOrganization, photos: list) -> None:
    """Скачивает фото авто со склада и пишет в RefCarsOrganizationFiles."""
    photos = photos or []
    names = {
        p.get('Name')
        for p in photos
        if isinstance(p, dict) and p.get('Name')
    }

    ref_photos = RefCarsOrganizationFiles.objects.filter(сars_organization=car)
    for ref_photo in ref_photos:
        if ref_photo.name not in names:
            ref_photo.delete()

    if not names:
        return

    existing_names = set(
        RefCarsOrganizationFiles.objects.filter(сars_organization=car)
        .values_list('name', flat=True)
    )

    for photo in photos:
        if not isinstance(photo, dict):
            continue
        name = photo.get('Name') or ''
        if not name or name in existing_names:
            continue

        url = photo.get('Url') or ''
        url_mini = photo.get('UrlMini') or ''

        photo_object = RefCarsOrganizationFiles()
        photo_object.сars_organization = car
        photo_object.name = name
        photo_object.url = url
        photo_object.url_mini = url_mini
        photo_object.main = bool(photo.get('Main'))
        if photo.get('Date'):
            photo_object.date = photo['Date']

        lf = _download_to_tempfile(url)
        if lf is None:
            continue
        file_name = url.split('/')[-1] or name
        photo_object.file.save(file_name, files.File(lf))

        lf_mini = _download_to_tempfile(url_mini)
        if lf_mini is None:
            # полное фото уже сохранено — оставляем запись без мини
            photo_object.save()
            continue
        file_name_mini = url_mini.split('/')[-1] or ('mini_' + name)
        photo_object.file_mini.save(file_name_mini, files.File(lf_mini))
        photo_object.save()


@background(queue='refresh_cars_photos')
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
