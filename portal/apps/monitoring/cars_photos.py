# -*- coding: utf-8 -*-
"""Метрики и запросы по фото автомобилей организации (RefCarsOrganization)."""
from django.db.models import Count, Q

from refs.models import RefCarsOrganization, RefCarsOrganizationFiles

PHOTOS_QUEUE = 'refresh_cars_photos'

# Файл считается загруженным только если в storage есть имя файла.
FILE_DOWNLOADED = Q(refcarsorganizationfiles__file__gt='')


def _stock_qs():
    return RefCarsOrganization.objects.filter(quantity__gt=0)


def count_cars_without_photos() -> int:
    """Авто в наличии без ни одного скачанного файла."""
    return (
        _stock_qs()
        .annotate(
            downloaded=Count(
                'refcarsorganizationfiles',
                filter=FILE_DOWNLOADED,
                distinct=True,
            ),
        )
        .filter(downloaded=0)
        .count()
    )


def count_pending_photo_files() -> int:
    """Записи RefCarsOrganizationFiles с URL, но без скачанного file."""
    return RefCarsOrganizationFiles.objects.filter(
        Q(file='') | Q(file__isnull=True),
    ).exclude(url='').count()


def count_cars_with_pending_photo_files() -> int:
    """Авто в наличии, у которых есть хотя бы одно фото «URL есть, file нет»."""
    return (
        _stock_qs()
        .filter(
            refcarsorganizationfiles__url__gt='',
        )
        .filter(
            Q(refcarsorganizationfiles__file='')
            | Q(refcarsorganizationfiles__file__isnull=True),
        )
        .distinct()
        .count()
    )


def background_queue_counts():
    """Состояние очереди background_task refresh_cars_photos."""
    try:
        from background_task.models import Task
    except ImportError:
        return {'pending': 0, 'failed': 0, 'locked': 0}

    base = Task.objects.filter(queue=PHOTOS_QUEUE)
    return {
        'pending': base.filter(failed_at__isnull=True, locked_by='').count(),
        'failed': base.filter(failed_at__isnull=False).count(),
        'locked': base.filter(failed_at__isnull=True).exclude(locked_by='').count(),
    }


def cars_photos_hub_counts():
    pending_files = count_pending_photo_files()
    queue = background_queue_counts()
    return {
        'cars_no_photos': count_cars_without_photos(),
        'cars_pending_photo_files': count_cars_with_pending_photo_files(),
        'photos_pending_files': pending_files,
        'photos_queue_pending': queue['pending'],
        'photos_queue_failed': queue['failed'],
        'photos_queue_locked': queue['locked'],
        'photos_not_downloaded_total': pending_files + count_cars_without_photos(),
    }
