# -*- coding: utf-8 -*-
"""Метрики и обслуживание очереди фото автомобилей организации."""
from __future__ import annotations

import json
from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone

from refs.models import RefCarsOrganization, RefCarsOrganizationFiles

PHOTOS_QUEUE = 'refresh_cars_photos'
TASK_LOAD = 'load_photos_async'
TASK_RETRY = 'retry_pending_photos_async'

FILE_DOWNLOADED = Q(refcarsorganizationfiles__file__gt='')


def _max_run_time_seconds() -> int:
    return int(getattr(settings, 'MAX_RUN_TIME', 3600))


def _photos_queue_qs():
    try:
        from background_task.models import Task
    except ImportError:
        return None
    return Task.objects.filter(queue=PHOTOS_QUEUE)


def _stock_qs():
    return RefCarsOrganization.objects.filter(quantity__gt=0)


def count_cars_without_photos() -> int:
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
    return RefCarsOrganizationFiles.objects.filter(
        Q(file='') | Q(file__isnull=True),
    ).exclude(url='').count()


def count_cars_with_pending_photo_files() -> int:
    return (
        _stock_qs()
        .filter(refcarsorganizationfiles__url__gt='')
        .filter(Q(refcarsorganizationfiles__file='') | Q(refcarsorganizationfiles__file__isnull=True))
        .distinct()
        .count()
    )


def _task_car_id(task) -> int | None:
    try:
        args, _kwargs = task.params()
        if args:
            return int(args[0])
    except (TypeError, ValueError, json.JSONDecodeError, IndexError):
        pass
    return None


def background_queue_counts():
    """
    Счётчики очереди refresh_cars_photos по логике django-background-task.
    «Заняты» = lock свежий (< MAX_RUN_TIME). «Зависшие» = lock просрочен или без locked_at.
    """
    empty = {
        'total': 0,
        'ready': 0,
        'locked_active': 0,
        'locked_stale': 0,
        'failed': 0,
        'scheduled_future': 0,
        'max_run_time_sec': _max_run_time_seconds(),
        # legacy keys для hub
        'pending': 0,
        'locked': 0,
    }
    qs = _photos_queue_qs()
    if qs is None:
        return empty

    now = timezone.now()
    expires_at = now - timedelta(seconds=_max_run_time_seconds())
    base = qs.filter(failed_at__isnull=True)

    ready = base.filter(
        Q(locked_by__isnull=True) | Q(locked_by='') | Q(locked_at__lt=expires_at),
        run_at__lte=now,
    ).count()

    locked_active = base.filter(
        locked_by__gt='',
        locked_at__gte=expires_at,
    ).count()

    locked_stale = base.filter(
        locked_by__gt='',
    ).filter(
        Q(locked_at__isnull=True) | Q(locked_at__lt=expires_at),
    ).count()

    failed = qs.filter(failed_at__isnull=False).count()
    scheduled_future = base.filter(run_at__gt=now).count()
    total = qs.count()

    return {
        'total': total,
        'ready': ready,
        'locked_active': locked_active,
        'locked_stale': locked_stale,
        'failed': failed,
        'scheduled_future': scheduled_future,
        'max_run_time_sec': _max_run_time_seconds(),
        'pending': ready,
        'locked': locked_active + locked_stale,
    }


def cleanup_photo_queue(dedupe: bool = True, delete_failed: bool = True) -> dict:
    """
    Обслуживание очереди: снять зависшие lock, удалить failed, убрать дубликаты по car_id.
    """
    qs = _photos_queue_qs()
    if qs is None:
        return {'released': 0, 'failed_deleted': 0, 'duplicates_deleted': 0}

    now = timezone.now()
    expires_at = now - timedelta(seconds=_max_run_time_seconds())

    released = qs.filter(
        failed_at__isnull=True,
        locked_by__gt='',
    ).filter(
        Q(locked_at__isnull=True) | Q(locked_at__lt=expires_at),
    ).update(locked_by='', locked_at=None)

    failed_deleted = 0
    if delete_failed:
        failed_deleted, _ = qs.filter(failed_at__isnull=False).delete()

    duplicates_deleted = 0
    if dedupe:
        duplicates_deleted = _dedupe_photo_tasks(qs)

    return {
        'released': released,
        'failed_deleted': failed_deleted,
        'duplicates_deleted': duplicates_deleted,
    }


def _dedupe_photo_tasks(qs) -> int:
    """Оставляем одну (самую новую) задачу load/retry на car_id среди свободных."""
    candidates = qs.filter(
        failed_at__isnull=True,
        locked_by='',
    ).filter(
        Q(task_name__icontains=TASK_LOAD) | Q(task_name__icontains=TASK_RETRY),
    ).order_by('-run_at', '-id')

    seen: set[int] = set()
    delete_ids: list[int] = []
    for task in candidates.iterator(chunk_size=500):
        car_id = _task_car_id(task)
        if car_id is None:
            continue
        if car_id in seen:
            delete_ids.append(task.pk)
        else:
            seen.add(car_id)

    if not delete_ids:
        return 0
    deleted, _ = qs.model.objects.filter(pk__in=delete_ids).delete()
    return deleted


def enqueue_pending_photo_retries(limit: int = 500) -> int:
    """Поставить в очередь повторную загрузку по URL из БД (авто в наличии)."""
    from api.tasks_cars import retry_pending_photos_async

    car_ids = (
        RefCarsOrganizationFiles.objects.filter(
            Q(file='') | Q(file__isnull=True),
        )
        .exclude(url='')
        .filter(сars_organization__quantity__gt=0)
        .values_list('сars_organization_id', flat=True)
        .distinct()[:limit]
    )
    queued = 0
    for car_id in car_ids:
        if car_id:
            retry_pending_photos_async(car_id, remove_existing_tasks=True)
            queued += 1
    return queued


def cars_photos_hub_counts():
    pending_files = count_pending_photo_files()
    queue = background_queue_counts()
    return {
        'cars_no_photos': count_cars_without_photos(),
        'cars_pending_photo_files': count_cars_with_pending_photo_files(),
        'photos_pending_files': pending_files,
        'photos_queue_total': queue['total'],
        'photos_queue_ready': queue['ready'],
        'photos_queue_locked_active': queue['locked_active'],
        'photos_queue_locked_stale': queue['locked_stale'],
        'photos_queue_failed': queue['failed'],
        'photos_queue_scheduled_future': queue['scheduled_future'],
        'photos_queue_max_run_sec': queue['max_run_time_sec'],
        # совместимость со старым шаблоном
        'photos_queue_pending': queue['ready'],
        'photos_queue_locked': queue['locked_active'] + queue['locked_stale'],
        'photos_not_downloaded_total': pending_files + count_cars_without_photos(),
    }
