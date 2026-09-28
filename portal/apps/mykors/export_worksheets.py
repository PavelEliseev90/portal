"""
Выгрузка рабочих листов (DocRLK) в MyKors.
"""
import logging
import time
from typing import Optional

from documents.models import DocRLK
from mykors import conf
from mykors.client import MykorsClientError, ingest_worksheet
from mykors.payload import worksheet_to_ingest_payload

logger = logging.getLogger(__name__)


def worksheets_queryset():
    """Рабочие листы со всеми связанными сущностями."""
    return (
        DocRLK.objects
        .filter(uin__isnull=False)
        .exclude(uin='')
        .select_related(
            'unit',
            'unit__city',
            'unit_dc',
            'staff',
            'cars',
            'type',
            'staffECO1',
            'staffECO2',
            'contacType',
            'customer',
            'type_archive',
            'status',
        )
        .order_by('-id')
    )


def export_worksheets(*, limit: Optional[int] = 10, uin: Optional[str] = None) -> dict:
    """
    Выгружает рабочие листы в MyKors.
    :param limit: ограничение количества
    :param uin: выгрузить конкретный РЛК по UIN
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

    qs = worksheets_queryset()
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
        payload = worksheet_to_ingest_payload(doc)
        if not payload.get('uin'):
            stats['skipped'] += 1
            continue

        try:
            result = ingest_worksheet(payload)
        except MykorsClientError as exc:
            stats['errors'] += 1
            logger.warning('MyKors export_worksheets exception uin=%s: %s', doc.uin, exc)
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

    logger.info('MyKors worksheets export finished: %s', stats)
    return stats
