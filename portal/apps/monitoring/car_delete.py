# -*- coding: utf-8 -*-
"""Просмотр и удаление автомобиля организации вместе со связанными записями."""
from __future__ import annotations

import logging
from typing import Any

from django.db import models, transaction
from django.db.models.deletion import CASCADE, PROTECT, SET_DEFAULT, SET_NULL

from refs.models import RefCarsOrganization

logger = logging.getLogger('monitoring.car_delete')

SAMPLE_LIMIT = 25
SEARCH_LIMIT = 40


def search_organization_cars(query: str, limit: int = SEARCH_LIMIT) -> list[RefCarsOrganization]:
    q = (query or '').strip()
    if not q:
        return []
    qs = RefCarsOrganization.objects.select_related('unit', 'store', 'lo', 'organization')
    filters = (
        models.Q(vin__icontains=q)
        | models.Q(vin2__icontains=q)
        | models.Q(slug__icontains=q)
        | models.Q(plate_number__icontains=q)
        | models.Q(lo_link_number__icontains=q)
        | models.Q(lo_uin__icontains=q)
        | models.Q(name__icontains=q)
    )
    if q.isdigit():
        filters = filters | models.Q(pk=int(q))
    return list(qs.filter(filters).order_by('-id')[:limit])


def _on_delete_info(on_delete) -> tuple[str, str]:
    if on_delete is CASCADE:
        return 'delete', 'Будет удалено вместе с автомобилем'
    if on_delete is PROTECT:
        return 'protect', 'Блокирует удаление — снимем перед удалением автомобиля'
    if on_delete in (SET_NULL, SET_DEFAULT):
        return 'null', 'Запись останется, ссылка на автомобиль очистится'
    return 'other', 'Особая связь — проверьте вручную'


def _obj_label(obj) -> str:
    bits = [f'id={obj.pk}']
    for attr in ('nomer', 'number', 'uin', 'vin', 'slug', 'name', 'date', 'dataTime'):
        val = getattr(obj, attr, None)
        if val not in (None, ''):
            bits.append(f'{attr}={val}')
            break
    try:
        text = str(obj)
        if text and text not in bits:
            bits.append(text[:120])
    except Exception:
        pass
    return ' · '.join(bits)


def _related_manager(car, rel):
    accessor = rel.get_accessor_name()
    if not accessor:
        return None, None
    try:
        related = getattr(car, accessor)
    except Exception:
        return accessor, None
    return accessor, related


def inspect_car_relations(car: RefCarsOrganization, sample_limit: int = SAMPLE_LIMIT) -> dict[str, Any]:
    groups = []
    total = 0
    delete_count = 0
    null_count = 0
    protect_count = 0

    for rel in car._meta.related_objects:
        if getattr(rel, 'parent_link', False):
            continue
        accessor, related = _related_manager(car, rel)
        if related is None and accessor is None:
            continue

        on_delete = getattr(rel, 'on_delete', None)
        if on_delete is None:
            action, action_label = 'null', 'Связь будет разорвана, запись останется'
        else:
            action, action_label = _on_delete_info(on_delete)
        model = rel.related_model
        verbose = str(model._meta.verbose_name_plural or model._meta.label)

        items = []
        count = 0
        if related is None:
            continue
        if hasattr(related, 'all'):
            qs = related.all()
            count = qs.count()
            if count:
                for obj in qs[:sample_limit]:
                    items.append({'pk': obj.pk, 'label': _obj_label(obj)})
        else:
            count = 1
            items.append({'pk': related.pk, 'label': _obj_label(related)})

        if not count:
            continue

        total += count
        if action == 'delete':
            delete_count += count
        elif action == 'null':
            null_count += count
        elif action == 'protect':
            protect_count += count

        groups.append({
            'model': model._meta.label,
            'verbose': verbose,
            'accessor': accessor,
            'action': action,
            'action_label': action_label,
            'count': count,
            'items': items,
            'truncated': count > sample_limit,
        })

    groups.sort(key=lambda g: (-g['count'], g['verbose']))
    return {
        'groups': groups,
        'total': total,
        'delete_count': delete_count,
        'null_count': null_count,
        'protect_count': protect_count,
        'sample_limit': sample_limit,
    }


def related_total(car: RefCarsOrganization) -> int:
    total = 0
    for rel in car._meta.related_objects:
        if getattr(rel, 'parent_link', False):
            continue
        _accessor, related = _related_manager(car, rel)
        if related is None:
            continue
        if hasattr(related, 'all'):
            total += related.all().count()
        else:
            total += 1
    return total


@transaction.atomic
def delete_organization_car(car: RefCarsOrganization, *, user=None) -> dict[str, Any]:
    """Удаляет PROTECT-связанные записи, затем сам автомобиль (CASCADE / SET_NULL).

    Лист оценки, подразделение и прочие справочники, на которые ссылается авто,
    не удаляются.
    """
    snapshot = inspect_car_relations(car)
    car_pk = car.pk
    vin = car.vin or ''
    slug = car.slug or ''
    name = car.name or ''

    for group in snapshot['groups']:
        if group['action'] != 'protect':
            continue
        accessor = group['accessor']
        related = getattr(car, accessor, None)
        if related is None:
            continue
        if hasattr(related, 'all'):
            related.all().delete()
        else:
            related.delete()

    car.delete()

    logger.warning(
        'Deleted RefCarsOrganization pk=%s vin=%s slug=%s related=%s user=%s',
        car_pk,
        vin,
        slug,
        snapshot['total'],
        getattr(user, 'username', None) or user,
    )
    return {
        'pk': car_pk,
        'vin': vin,
        'slug': slug,
        'name': name,
        'related_total': snapshot['total'],
        'groups': snapshot['groups'],
    }
