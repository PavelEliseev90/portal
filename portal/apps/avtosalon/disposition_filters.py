# -*- coding: utf-8 -*-
"""Фильтры и сохранённые пресеты диспозиции (стандарт как у ASP reports)."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from django.db.models import Count, Q, QuerySet
from django.http import QueryDict

from asp.models import ReportSavedFilter
from asp.saved_filters import (
    filter_data_to_querydict,
    get_accessible_saved_filter,
    saved_filters_for_template,
)

DISPOSITION_KEY = 'disposition'

SKIP_KEYS = frozenset({'page', 'ajax', 'saved_filter'})

MULTI_KEYS = frozenset({
    'mark', 'mark[]',
    'model', 'model[]',
    'body_type', 'body_type[]',
    'gear_type', 'gear_type[]',
    'drive_type', 'drive_type[]',
    'evaluation_type', 'evaluation_type[]',
    'unit', 'unit[]',
    'store', 'store[]',
})

ORDER_WHITELIST = frozenset({
    'date_create', '-date_create',
    'price', '-price',
    'year', '-year',
    'run', '-run',
    'days_in_stok', '-days_in_stok',
    'lo_link_number', '-lo_link_number',
})

STATUS_LABELS = {
    'all': 'Все',
    'ready': 'Готов',
    'sale': 'В продаже',
    'auction': 'Аукцион',
    'reserve': 'В резерве',
    'transit': 'Транзит',
    'preparation': 'Подготовка',
    'repair': 'Ремонт',
    'warehouse': 'Склад',
    'sold': 'Проданные',
    'no_sale': 'Не продавать',
    'returned': 'Возвращенные',
}


def _int_list(get, *keys) -> list[int]:
    getlist = getattr(get, 'getlist', None)
    raw: list[str] = []
    if callable(getlist):
        for key in keys:
            raw.extend(getlist(key) or [])
    out: list[int] = []
    seen = set()
    for item in raw:
        try:
            val = int(str(item).strip())
        except (TypeError, ValueError):
            continue
        if val not in seen:
            seen.add(val)
            out.append(val)
    return out


def snapshot_disposition_filters(get) -> dict[str, Any]:
    """GET → JSON для сохранённого пресета."""
    data: dict[str, Any] = {}
    getlist = getattr(get, 'getlist', None)
    multi_canon = (
        ('mark', ('mark', 'mark[]')),
        ('model', ('model', 'model[]')),
        ('body_type', ('body_type', 'body_type[]')),
        ('gear_type', ('gear_type', 'gear_type[]')),
        ('drive_type', ('drive_type', 'drive_type[]')),
        ('evaluation_type', ('evaluation_type', 'evaluation_type[]')),
        ('unit', ('unit', 'unit[]')),
        ('store', ('store', 'store[]')),
    )
    if callable(getlist):
        for canon, aliases in multi_canon:
            values = []
            for key in aliases:
                values.extend(getlist(key) or [])
            values = [str(v).strip() for v in values if str(v).strip()]
            if values:
                data[canon] = list(dict.fromkeys(values))

    for key in get.keys():
        if key in SKIP_KEYS or key in MULTI_KEYS:
            continue
        val = get.get(key)
        if val in (None, ''):
            continue
        data[key] = str(val).strip()
    return data


def resolve_disposition_get(request) -> QueryDict:
    """Раскрыть ?saved_filter=id в QueryDict."""
    base = request.GET.copy()
    if not isinstance(base, QueryDict):
        base = QueryDict(mutable=True)
    else:
        base = base.copy()

    raw_id = (base.get('saved_filter') or '').strip()
    if not raw_id.isdigit():
        return base

    preset = get_accessible_saved_filter(request.user, DISPOSITION_KEY, int(raw_id))
    if preset is None:
        return base

    extras = {'saved_filter': raw_id}
    if base.get('status'):
        extras['status'] = base.get('status')
    if base.get('order_by'):
        extras['order_by'] = base.get('order_by')
    if base.get('page'):
        extras['page'] = base.get('page')

    return filter_data_to_querydict(preset.filter_data, extras=extras)


def accessible_disposition_filters_qs(user):
    return (
        ReportSavedFilter.objects
        .filter(report_key=DISPOSITION_KEY)
        .filter(Q(user=user) | Q(is_shared=True))
        .select_related('user')
        .order_by('order', 'name', 'id')
    )


def apply_status_filter(qs: QuerySet, status_type: str) -> QuerySet:
    if status_type in ('all', '', None):
        return qs
    if status_type == 'warehouse':
        return qs.filter(status__name__icontains='Склад')
    if status_type == 'ready':
        return qs.filter(status__name__icontains='Готов')
    if status_type == 'sale':
        return qs.filter(status__name__icontains='В продаже')
    if status_type == 'auction':
        return qs.filter(status__name__icontains='Аукцион')
    if status_type == 'reserve':
        return qs.filter(reserve__gt=0)
    if status_type == 'transit':
        return qs.filter(status__name__icontains='Транзит')
    if status_type == 'preparation':
        return qs.filter(status__name__icontains='Подготовка')
    if status_type == 'repair':
        return qs.filter(status__name__icontains='Ремонт')
    if status_type == 'sold':
        return qs.filter(status__name__icontains='Продан')
    if status_type == 'no_sale':
        return qs.filter(status__name__icontains='Не продавать')
    if status_type == 'returned':
        return qs.filter(status__name__icontains='Возвращен')
    return qs


def parse_filters(get) -> dict[str, Any]:
    status = (get.get('status') or 'all').strip() or 'all'
    try:
        select_count = int(get.get('select_count') or 50)
    except (TypeError, ValueError):
        select_count = 50
    select_count = max(10, min(select_count, 200))

    order_by = (get.get('order_by') or '-date_create').strip()
    if order_by not in ORDER_WHITELIST:
        order_by = '-date_create'

    mark_ids = _int_list(get, 'mark', 'mark[]')
    model_ids = _int_list(get, 'model', 'model[]')
    body_type_ids = _int_list(get, 'body_type', 'body_type[]')
    gear_type_ids = _int_list(get, 'gear_type', 'gear_type[]')
    drive_type_ids = _int_list(get, 'drive_type', 'drive_type[]')
    evaluation_type_ids = _int_list(get, 'evaluation_type', 'evaluation_type[]')
    unit_ids = _int_list(get, 'unit', 'unit[]')
    store_ids = _int_list(get, 'store', 'store[]')

    return {
        'status': status,
        'status_label': STATUS_LABELS.get(status, 'Все'),
        'select_count': select_count,
        'order_by': order_by,
        'vin': (get.get('vin') or '').strip(),
        'search_fields': (get.get('search_fields') or '').strip(),
        'year_start': (get.get('year_start') or '').strip(),
        'year_end': (get.get('year_end') or '').strip(),
        'price_start': (get.get('price_start') or '').strip(),
        'price_end': (get.get('price_end') or '').strip(),
        'stock_number': (get.get('stock_number') or '').strip(),
        'no_photo': (get.get('no_photo') or '').strip(),
        'promotion': (get.get('promotion') or '').strip(),
        'color': (get.get('color') or '').strip(),
        'run_start': (get.get('run_start') or '').strip(),
        'run_end': (get.get('run_end') or '').strip(),
        'engine_volume_start': (get.get('engine_volume_start') or '').strip(),
        'engine_volume_end': (get.get('engine_volume_end') or '').strip(),
        'days_in_stock_start': (get.get('days_in_stock_start') or '').strip(),
        'days_in_stock_end': (get.get('days_in_stock_end') or '').strip(),
        'mark_ids': mark_ids,
        'model_ids': model_ids,
        'body_type_ids': body_type_ids,
        'gear_type_ids': gear_type_ids,
        'drive_type_ids': drive_type_ids,
        'evaluation_type_ids': evaluation_type_ids,
        'unit_ids': unit_ids,
        'store_ids': store_ids,
        'saved_filter': (get.get('saved_filter') or '').strip(),
    }


def apply_filters(qs: QuerySet, f: dict[str, Any]) -> QuerySet:
    qs = apply_status_filter(qs, f['status'])

    if f['vin']:
        qs = qs.filter(Q(vin__icontains=f['vin']) | Q(vin2__icontains=f['vin']))
    if f['search_fields']:
        qs = qs.filter(search_fields__icontains=f['search_fields'])
    if f['mark_ids']:
        qs = qs.filter(modification_autoru__model__mark__id__in=f['mark_ids'])
    if f['model_ids']:
        qs = qs.filter(modification_autoru__model__id__in=f['model_ids'])

    for field, key, cast in (
        ('year__gte', 'year_start', int),
        ('year__lte', 'year_end', int),
        ('price__gte', 'price_start', lambda x: int(float(x))),
        ('price__lte', 'price_end', lambda x: int(float(x))),
        ('run__gte', 'run_start', int),
        ('run__lte', 'run_end', int),
        ('modification_autoru__engineVolume__gte', 'engine_volume_start', float),
        ('modification_autoru__engineVolume__lte', 'engine_volume_end', float),
    ):
        raw = f.get(key) or ''
        if not raw:
            continue
        try:
            qs = qs.filter(**{field: cast(raw)})
        except (TypeError, ValueError):
            pass

    if f['stock_number']:
        qs = qs.filter(lo_link_number__icontains=f['stock_number'])
    if f['no_photo'] == 'on':
        qs = qs.annotate(photos_count=Count('refcarsorganizationfiles__id')).filter(photos_count=0)
    if f['promotion'] == 'on':
        qs = qs.filter(stage_price__name__icontains='акция')
    if f['body_type_ids']:
        qs = qs.filter(modification_autoru__typeBody__id__in=f['body_type_ids'])
    if f['gear_type_ids']:
        qs = qs.filter(modification_autoru__typeGear__id__in=f['gear_type_ids'])
    if f['drive_type_ids']:
        qs = qs.filter(type_drive__id__in=f['drive_type_ids'])
    if f['evaluation_type_ids']:
        qs = qs.filter(evaluation__id__in=f['evaluation_type_ids'])
    if f['unit_ids']:
        qs = qs.filter(unit__id__in=f['unit_ids'])
    if f['store_ids']:
        qs = qs.filter(store__id__in=f['store_ids'])
    if f['color']:
        qs = qs.filter(color__icontains=f['color'])

    if f['days_in_stock_start']:
        try:
            days = int(f['days_in_stock_start'])
            qs = qs.filter(date_create__lte=datetime.now().date() - timedelta(days=days))
        except ValueError:
            pass
    if f['days_in_stock_end']:
        try:
            days = int(f['days_in_stock_end'])
            qs = qs.filter(date_create__gte=datetime.now().date() - timedelta(days=days))
        except ValueError:
            pass

    return qs.order_by(f['order_by'])


def has_active_filters(f: dict[str, Any]) -> bool:
    if f['status'] not in ('all', ''):
        return True
    keys = (
        'vin', 'search_fields', 'year_start', 'year_end', 'price_start', 'price_end',
        'stock_number', 'color', 'run_start', 'run_end', 'engine_volume_start',
        'engine_volume_end', 'days_in_stock_start', 'days_in_stock_end',
    )
    if any(f.get(k) for k in keys):
        return True
    if f.get('no_photo') == 'on' or f.get('promotion') == 'on':
        return True
    return any(f.get(k) for k in (
        'mark_ids', 'model_ids', 'body_type_ids', 'gear_type_ids',
        'drive_type_ids', 'evaluation_type_ids', 'unit_ids', 'store_ids',
    ))


def disposition_saved_filters(user, active_id: str | None = None) -> list[dict]:
    return saved_filters_for_template(user, DISPOSITION_KEY, active_id)
