# -*- coding: utf-8 -*-
"""Отчёт по остаткам ОП АСП — быстрые агрегаты + ленивые детали групп."""
from __future__ import annotations

from typing import Any

from django.db.models import Q

from asp.report_common import (
    GROUP_DETAIL_LIMIT,
    aggregate_groups,
    aggregate_totals,
    allowed_unit_ids,
    details_payload,
    money,
    paginate_values_qs,
    parse_common_filters,
    report_shell,
    sum_money,
)
from asp.report_table import resolve_order_by
from refs.models import RefCarsOrganization, RefStatusCarsOrganization

SUM_MAP = {
    'price': sum_money('price'),
    'cost_price': sum_money('cost_price'),
    'outlay': sum_money('outlay'),
    'bcp': sum_money('bcp'),
    'quantity': sum_money('quantity'),
    'days_in_stok': sum_money('days_in_stok'),
}


def filtered_stock_qs(filters: dict[str, Any]):
    unit_ids = allowed_unit_ids(filters)
    qs = RefCarsOrganization.objects.filter(quantity__gt=0, unit_id__in=unit_ids)

    vin = filters.get('vin') or ''
    if vin:
        qs = qs.filter(Q(vin__icontains=vin) | Q(vin2__icontains=vin))
    mark = filters.get('mark') or ''
    if mark:
        qs = qs.filter(mark__icontains=mark)
    model = filters.get('model') or ''
    if model:
        qs = qs.filter(model__icontains=model)
    status = filters.get('status') or ''
    if status.isdigit():
        qs = qs.filter(status_id=int(status))
    elif status:
        qs = qs.filter(status__name__icontains=status)
    person = filters.get('person') or ''
    if person:
        qs = qs.filter(lo__staff__name__icontains=person)
    type_reception = filters.get('type_reception') or ''
    if type_reception:
        qs = qs.filter(type_reception__name__icontains=type_reception)
    type_sale = filters.get('type_sale') or ''
    if type_sale:
        qs = qs.filter(type_sale__name__icontains=type_sale)
    days_from = filters.get('days_from') or ''
    if days_from.isdigit():
        qs = qs.filter(days_in_stok__gte=int(days_from))
    days_to = filters.get('days_to') or ''
    if days_to.isdigit():
        qs = qs.filter(days_in_stok__lte=int(days_to))
    return qs


def _enrich_totals(totals: dict) -> dict:
    totals['margin'] = totals.get('price', 0) - totals.get('cost_price', 0) - totals.get('outlay', 0)
    if totals['count']:
        totals['avg_days'] = totals['days_in_stok'] / totals['count']
        totals['avg_price'] = totals['price'] / totals['count']
        totals['margin_pct'] = (totals['margin'] / totals['price'] * 100) if totals['price'] else 0
    else:
        totals['avg_days'] = 0
        totals['avg_price'] = 0
        totals['margin_pct'] = 0
    return totals


def _car_row_from_values(row: dict) -> dict[str, Any]:
    price = money(row.get('price'))
    cost = money(row.get('cost_price'))
    outlay = money(row.get('outlay'))
    iznos = row.get('lo__rlk__reginteractivocenka__iznos')
    return {
        'id': row['id'],
        'slug': row.get('slug') or '',
        'vin': row.get('vin') or '',
        'mark': row.get('mark') or '',
        'model': row.get('model') or '',
        'year': row.get('year') or 0,
        'run': row.get('run') or 0,
        'unit_id': row.get('unit_id'),
        'unit_name': row.get('unit__name') or '—',
        'store_name': row.get('store__name') or '',
        'status_name': row.get('status__name') or '—',
        'type_reception': (
            row.get('type_reception__name')
            or row.get('lo__type_reception__name')
            or ''
        ),
        'type_sale': row.get('type_sale__name') or '',
        'stage_price': row.get('stage_price__name') or '',
        'group_price': row.get('group_price__name') or '',
        'iznos': bool(iznos) if iznos is not None else None,
        'has_iznos': iznos is not None,
        'person_id': row.get('lo__staff_id') or 0,
        'person_name': row.get('lo__staff__name') or 'Без оценщика',
        'unit_source_name': row.get('lo__rlk__unit_dc__name') or '',
        'kolesa2_reception': bool(row.get('lo__kolesa2_reception')),
        'price': price,
        'cost_price': cost,
        'outlay': outlay,
        'bcp': money(row.get('bcp')),
        'margin': price - cost - outlay,
        'quantity': int(row.get('quantity') or 0),
        'days_in_stok': int(row.get('days_in_stok') or 0),
    }


DETAIL_VALUES = (
    'id', 'slug', 'vin', 'mark', 'model', 'year', 'run', 'unit_id', 'unit__name',
    'store__name', 'status__name', 'type_reception__name', 'type_sale__name',
    'stage_price__name', 'group_price__name', 'lo__staff_id', 'lo__staff__name',
    'lo__kolesa2_reception', 'lo__rlk__unit_dc__name',
    'lo__type_reception__name', 'lo__rlk__reginteractivocenka__iznos',
    'price', 'cost_price', 'outlay', 'bcp', 'quantity', 'days_in_stok',
)


def iter_detail_rows(qs, limit=GROUP_DETAIL_LIMIT):
    return [
        _car_row_from_values(row)
        for row in qs.order_by('-days_in_stok', 'mark', 'model').values(*DETAIL_VALUES)[:limit]
    ]


def build_group_details(get) -> dict[str, Any]:
    filters = parse_common_filters(get)
    qs = filtered_stock_qs(filters)
    key = filters.get('group_key') or ''
    view = filters.get('view') or 'by_unit'
    try:
        key_int = int(key)
    except (TypeError, ValueError):
        key_int = 0
    if view == 'by_person':
        if key_int:
            qs = qs.filter(lo__staff_id=key_int)
        else:
            qs = qs.filter(Q(lo__isnull=True) | Q(lo__staff__isnull=True))
    else:
        if key_int:
            qs = qs.filter(unit_id=key_int)
        else:
            qs = qs.filter(unit__isnull=True)
    return details_payload(iter_detail_rows(qs))


def build_stock_report(get) -> dict[str, Any]:
    filters = parse_common_filters(get, default_month=False)
    qs = filtered_stock_qs(filters)
    totals = _enrich_totals(aggregate_totals(qs, SUM_MAP))

    view = filters['view']
    rows = []
    groups = []
    page_obj = None
    paginator = None

    if view == 'main':
        _ui, orm_order = resolve_order_by('stock', filters.get('order_by'))
        filters['order_by'] = _ui
        values_qs = qs.order_by(*orm_order).values(*DETAIL_VALUES)
        rows, page_obj, paginator = paginate_values_qs(
            values_qs, filters['page'], row_mapper=_car_row_from_values,
        )
        truncated = False
    elif view == 'by_unit':
        groups = aggregate_groups(
            qs,
            group_id_field='unit_id',
            group_name_field='unit__name',
            field_map=SUM_MAP,
        )
        for g in groups:
            g['margin'] = g['price'] - g['cost_price'] - g['outlay']
            g['avg_days'] = (g['days_in_stok'] / g['count']) if g['count'] else 0
            g['margin_pct'] = (g['margin'] / g['price'] * 100) if g['price'] else 0
        truncated = False
    else:
        groups = aggregate_groups(
            qs,
            group_id_field='lo__staff_id',
            group_name_field='lo__staff__name',
            field_map=SUM_MAP,
        )
        for g in groups:
            if not g['label'] or g['label'] == '—':
                g['label'] = 'Без оценщика'
            g['margin'] = g['price'] - g['cost_price'] - g['outlay']
            g['avg_days'] = (g['days_in_stok'] / g['count']) if g['count'] else 0
            g['margin_pct'] = (g['margin'] / g['price'] * 100) if g['price'] else 0
        truncated = False

    statuses = list(
        RefStatusCarsOrganization.objects.exclude(name='').order_by('name').values('id', 'name')
    )

    return report_shell(
        filters=filters,
        totals=totals,
        rows=rows,
        groups=groups,
        view=view,
        title='Остатки ОП АСП',
        subtitle='Автомобили на складе подразделений «Отдел продаж АСП». Итоги — из БД, детали групп — по клику.',
        person_label='Оценщик',
        page_obj=page_obj,
        paginator=paginator,
        truncated=truncated,
        extra={
            'statuses': statuses,
            'show_days_filter': True,
            'show_status_filter': True,
            'details_url': '/asp/reports/stock/',
        },
    )
