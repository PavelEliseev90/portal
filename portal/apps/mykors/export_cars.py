"""
Выгрузка автомобилей в наличии на MyKors.

Намеренно без signals / post_save: не влияет на сохранение авто в портале.
Запуск — отдельной management-командой / очередью background_task.
"""
import logging
import time

from django.db.models import Q

from mykors import conf
from mykors.client import MykorsClientError, ingest_car
from mykors.models import MykorsCarSyncState
from mykors.payload import car_to_ingest_payload, payload_hash

logger = logging.getLogger(__name__)


def stock_cars_queryset():
    """Авто в наличии с VIN. Только чтение."""
    from refs.models import RefCarsOrganization

    return (
        RefCarsOrganization.objects
        .filter(quantity__gt=0)
        .exclude(Q(vin='') | Q(vin__isnull=True))
        .select_related(
            'organization',
            'unit',
            'unit__city',
            'store',
            'store__city',
            'store__unit',
            'modification_autoru',
            'modification_autoru__model',
            'modification_autoru__model__mark',
            'modification_autoru__typeBody',
            'modification_autoru__typeEngine',
            'modification_autoru__typeGear',
            'complectation_autoru',
            'complectation_autoru__modification',
        )
        .order_by('id')
    )


def export_stock_cars(*, force=False, limit=None, car_id=None):
    """
    Выгружает сток в MyKors.
    :param force: игнорировать hash (слать всё)
    :param limit: ограничение количества
    :param car_id: выгрузить одну машину
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

    qs = stock_cars_queryset()
    if car_id:
        qs = qs.filter(pk=car_id)

    batch = limit if limit is not None else conf.batch_limit()
    if batch and batch > 0:
        car_ids = list(qs.values_list('id', flat=True)[:batch])
    else:
        car_ids = list(qs.values_list('id', flat=True))

    stats = {
        'enabled': True,
        'total': 0,
        'sent': 0,
        'created': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0,
    }
    if not car_ids:
        return stats

    skip_unchanged = conf.skip_unchanged() and not force
    delay = conf.request_delay_sec()

    states = {
        s.car_id: s
        for s in MykorsCarSyncState.objects.filter(car_id__in=car_ids)
    }

    cars = {
        c.pk: c
        for c in stock_cars_queryset().filter(pk__in=car_ids)
    }

    # Фото пачкой — без N+1 на каждую машину
    from collections import defaultdict
    from refs.models import RefCarsOrganizationFiles

    photos_by_car = defaultdict(list)
    for photo in (
        RefCarsOrganizationFiles.objects
        .filter(сars_organization_id__in=car_ids)
        .order_by('-main', 'id')
        .iterator(chunk_size=500)
    ):
        photos_by_car[photo.сars_organization_id].append(photo)

    for cid in car_ids:
        car = cars.get(cid)
        if car is None:
            continue
        car._mykors_photos = photos_by_car.get(cid, [])
        stats['total'] += 1
        payload = car_to_ingest_payload(car)
        if not payload.get('vin'):
            stats['skipped'] += 1
            continue

        ph = payload_hash(payload)
        state = states.get(car.pk)
        if skip_unchanged and state and state.last_ok and state.payload_hash == ph:
            stats['skipped'] += 1
            continue

        try:
            result = ingest_car(payload)
        except MykorsClientError as exc:
            stats['errors'] += 1
            _upsert_state(
                state, car, ph,
                ok=False, status_code=getattr(exc, 'status_code', None),
                remote_id=None, error=str(exc),
            )
            if delay > 0:
                time.sleep(delay)
            continue

        if result['ok']:
            stats['sent'] += 1
            if result.get('created'):
                stats['created'] += 1
            else:
                stats['updated'] += 1
            state = _upsert_state(
                state, car, ph,
                ok=True, status_code=result['status_code'],
                remote_id=result.get('remote_id'), error='',
            )
            states[car.pk] = state
        else:
            stats['errors'] += 1
            state = _upsert_state(
                state, car, ph,
                ok=False, status_code=result['status_code'],
                remote_id=result.get('remote_id'),
                error=result.get('body') or 'HTTP error',
            )
            states[car.pk] = state

        if delay > 0:
            time.sleep(delay)

    logger.info('MyKors stock export finished: %s', stats)
    return stats


def _upsert_state(state, car, ph, *, ok, status_code, remote_id, error):
    if state is None:
        state = MykorsCarSyncState(car_id=car.pk, vin=car.vin or '')
    state.vin = (car.vin or '')[:18]
    state.mark_result(
        ok=ok,
        status_code=status_code,
        remote_id=remote_id,
        error=error,
        payload_hash_value=ph,
    )
    return state
