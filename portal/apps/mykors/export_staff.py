"""
Выгрузка сотрудников (User + Profiles) в MyKors.
Запуск — отдельной management-командой или фоновой задачей.
"""
import logging
import time
from typing import Optional

from django.contrib.auth.models import User

from mykors import conf
from mykors.client import MykorsClientError, ingest_staff
from mykors.payload import user_to_ingest_payload

logger = logging.getLogger(__name__)


def staff_queryset():
    """Сотрудники портала с профилями и связанными подразделениями."""
    return (
        User.objects
        .filter(is_active=True)
        .select_related('profiles')
        .prefetch_related(
            'profiles__available_units',
            'profiles__available_units__city',
            'profiles__korsavto_stores',
            'profiles__korsavto_stores__city',
            'profiles__korsavto_stores__unit',
        )
        .order_by('id')
    )


def export_staff(*, limit: Optional[int] = None, user_id: Optional[int] = None) -> dict:
    """
    Выгружает сотрудников в MyKors по эндпоинту /api/portal/v1/staff/ingest/.
    :param limit: ограничение количества
    :param user_id: выгрузить одного пользователя по ID
    """
    if not conf.is_enabled():
        logger.info('MyKors export skipped: disabled or keys empty')
        return {
            'enabled': False,
            'total': 0,
            'sent': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0,
        }

    qs = staff_queryset()
    if user_id:
        qs = qs.filter(pk=user_id)

    if limit and limit > 0:
        users = list(qs[:limit])
    else:
        users = list(qs)

    stats = {
        'enabled': True,
        'total': len(users),
        'sent': 0,
        'created': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0,
    }

    delay = conf.request_delay_sec()

    for user in users:
        payload = user_to_ingest_payload(user)
        if not payload.get('portal_user_id') or not payload.get('username'):
            stats['skipped'] += 1
            continue

        try:
            result = ingest_staff(payload)
        except MykorsClientError as exc:
            stats['errors'] += 1
            logger.warning(
                'MyKors export_staff exception user_id=%s: %s',
                user.pk, exc,
            )
            continue

        if result.get('ok'):
            stats['sent'] += 1
            if result.get('created'):
                stats['created'] += 1
            else:
                stats['updated'] += 1
        else:
            stats['errors'] += 1

        if delay > 0:
            time.sleep(delay)

    logger.info('MyKors staff export finished: %s', stats)
    return stats
