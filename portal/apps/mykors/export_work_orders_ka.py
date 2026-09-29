"""
Выгрузка заказ-нарядов КорсАвто (DocZNKA) в MyKors.
"""
import logging
import time
from typing import Optional

from documents.models import DocZNKA
from mykors import conf
from mykors.client import MykorsClientError, ingest_work_order_ka
from mykors.payload import work_order_ka_to_ingest_payload

logger = logging.getLogger(__name__)


def work_orders_ka_queryset():
    """Заказ-наряды КорсАвто со всеми связанными сущностями."""
    return (
        DocZNKA.objects
        .filter(uin__isnull=False)
        .exclude(uin='')
        .select_related(
            'organization',
            'unit',
            'master',
            'masterOut',
            'customer',
            'cars',
            'typeRemont',
            'readyStatus',
            'lo',
        )
        .order_by('-id')
    )


def export_work_orders_ka(*, limit: Optional[int] = 10, uin: Optional[str] = None) -> dict:
    """
    Выгружает заказ-наряды КорсАвто в MyKors.
    :param limit: ограничение количества
    :param uin: выгрузить конкретный ЗН по UIN
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

    qs = work_orders_ka_queryset()
    if uin:
        qs = qs.filter(uin=uin)

    if limit and limit > 0:
        docs = list(qs[:limit])
    else:
        docs = list(qs)

    stats = {
        'enabled': True,
        'total': len(docs),
        'sent': 0,
        'created': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0,
    }

    delay = conf.request_delay_sec()

    for doc in docs:
        payload = work_order_ka_to_ingest_payload(doc)
        if not payload.get('uin'):
            stats['skipped'] += 1
            continue

        try:
            result = ingest_work_order_ka(payload)
        except MykorsClientError as exc:
            stats['errors'] += 1
            logger.warning('MyKors export_work_orders_ka exception uin=%s: %s', doc.uin, exc)
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

    logger.info('MyKors work orders KA export finished: %s', stats)
    return stats
