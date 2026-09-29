"""
Выгрузка листов оценок (DocLO) в MyKors.
"""
import logging
import time
from typing import Optional

from documents.models import DocLO
from mykors import conf
from mykors.client import MykorsClientError, ingest_evaluation
from mykors.payload import evaluation_to_ingest_payload

logger = logging.getLogger(__name__)


def evaluations_queryset():
    """Листы оценок со всеми связанными сущностями."""
    return (
        DocLO.objects
        .filter(uin__isnull=False)
        .exclude(uin='')
        .select_related(
            'organization',
            'filial',
            'unit',
            'store',
            'type_reception',
            'staff',
            'customer',
            'cars',
            'rlk',
            'modification_autoru',
            'complectation_autoru',
        )
        .order_by('-id')
    )


def export_evaluations(*, limit: Optional[int] = 10, uin: Optional[str] = None) -> dict:
    """
    Выгружает листы оценок в MyKors.
    :param limit: ограничение количества
    :param uin: выгрузить конкретный лист оценки по UIN
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

    qs = evaluations_queryset()
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
        payload = evaluation_to_ingest_payload(doc)
        if not payload.get('uin'):
            stats['skipped'] += 1
            continue

        try:
            result = ingest_evaluation(payload)
        except MykorsClientError as exc:
            stats['errors'] += 1
            logger.warning('MyKors export_evaluations exception uin=%s: %s', doc.uin, exc)
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

    logger.info('MyKors evaluations export finished: %s', stats)
    return stats
