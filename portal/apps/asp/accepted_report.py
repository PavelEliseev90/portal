# -*- coding: utf-8 -*-
"""Отчёт по принятым (DocLO) ОП АСП — быстрые агрегаты + ленивые детали."""
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
from documents.models import DocLO
from refs.models import RefTypeReceptionCarsOrganization

SUM_MAP = {
    'cost_price': sum_money('cost_price'),
    'bcp': sum_money('bcp'),
    'run': sum_money('run'),
    'owners': sum_money('owners'),
    'keys': sum_money('keys'),
}


def filtered_accepted_qs(filters: dict[str, Any]):
    unit_ids = allowed_unit_ids(filters)
    qs = DocLO.objects.filter(active=True, unit_id__in=unit_ids)

    if filters.get('date_from'):
        qs = qs.filter(dataTime__date__gte=filters['date_from'])
    if filters.get('date_to'):
        qs = qs.filter(dataTime__date__lte=filters['date_to'])

    vin = filters.get('vin') or ''
    if vin:
        qs = qs.filter(Q(vin__icontains=vin) | Q(vin2__icontains=vin))
    mark = filters.get('mark') or ''
    if mark:
        qs = qs.filter(Q(cars__mark__icontains=mark) | Q(name_new_auto__icontains=mark))
    model = filters.get('model') or ''
    if model:
        qs = qs.filter(Q(cars__model__icontains=model) | Q(name_new_auto__icontains=model))
    person = filters.get('person') or ''
    if person:
        qs = qs.filter(staff__name__icontains=person)
    type_reception = filters.get('type_reception') or ''
    if type_reception:
        qs = qs.filter(type_reception__name__icontains=type_reception)
    client = filters.get('client') or ''
    if client:
        qs = qs.filter(Q(clientName__icontains=client) | Q(customer__name__icontains=client))
    nomer = filters.get('nomer') or ''
    if nomer:
        qs = qs.filter(Q(nomer__icontains=nomer) | Q(rlk__nomer__icontains=nomer))
    return qs


DETAIL_VALUES = (
    'id', 'nomer', 'dataTime', 'unit_id', 'unit__name', 'store__name',
    'staff_id', 'staff__name', 'vin', 'vin2', 'year', 'run', 'owners', 'keys',
    'carsGRZ', 'clientName', 'cost_price', 'bcp', 'rlk_id', 'rlk__nomer',
    'auction', 'type_reception__name', 'kolesa2_reception',
    'cars__mark', 'cars__model', 'cars__vin',
)


def _lo_row_from_values(row: dict) -> dict[str, Any]:
    return {
        'id': row['id'],
        'nomer': row.get('nomer') or '',
        'date': row.get('dataTime'),
        'unit_id': row.get('unit_id'),
        'unit_name': row.get('unit__name') or '—',
        'store_name': row.get('store__name') or '',
        'person_id': row.get('staff_id') or 0,
        'person_name': row.get('staff__name') or 'Без оценщика',
        'vin': row.get('vin') or row.get('cars__vin') or '',
        'mark': row.get('cars__mark') or '',
        'model': row.get('cars__model') or '',
        'year': row.get('year') or 0,
        'run': row.get('run') or 0,
        'owners': row.get('owners') or 0,
        'keys': row.get('keys') or 0,
        'plate': row.get('carsGRZ') or '',
        'client': row.get('clientName') or '',
        'type_reception': row.get('type_reception__name') or '',
        'kolesa2_reception': bool(row.get('kolesa2_reception')),
        'cost_price': money(row.get('cost_price')),
        'bcp': money(row.get('bcp')),
        'rlk_id': row.get('rlk_id'),
        'rlk_nomer': row.get('rlk__nomer') or '',
        'auction': bool(row.get('auction')),
    }


def iter_detail_rows(qs, limit=GROUP_DETAIL_LIMIT):
    return [
        _lo_row_from_values(row)
        for row in qs.order_by('-dataTime', '-pk').values(*DETAIL_VALUES)[:limit]
    ]


def build_group_details(get) -> dict[str, Any]:
    filters = parse_common_filters(get, default_month=True)
    qs = filtered_accepted_qs(filters)
    key = filters.get('group_key') or ''
    view = filters.get('view') or 'by_unit'
    try:
        key_int = int(key)
    except (TypeError, ValueError):
        key_int = 0
    if view == 'by_person':
        if key_int:
            qs = qs.filter(staff_id=key_int)
        else:
            qs = qs.filter(staff__isnull=True)
    else:
        if key_int:
            qs = qs.filter(unit_id=key_int)
        else:
            qs = qs.filter(unit__isnull=True)
    return details_payload(iter_detail_rows(qs))


def build_accepted_report(get) -> dict[str, Any]:
    filters = parse_common_filters(get, default_month=True)
    qs = filtered_accepted_qs(filters)
    totals = aggregate_totals(qs, SUM_MAP)

    view = filters['view']
    rows = []
    groups = []
    page_obj = None
    paginator = None

    if view == 'main':
        _ui, orm_order = resolve_order_by('accepted', filters.get('order_by'))
        filters['order_by'] = _ui
        values_qs = qs.order_by(*orm_order).values(*DETAIL_VALUES)
        rows, page_obj, paginator = paginate_values_qs(
            values_qs, filters['page'], row_mapper=_lo_row_from_values,
        )
        truncated = False
    elif view == 'by_unit':
        groups = aggregate_groups(
            qs,
            group_id_field='unit_id',
            group_name_field='unit__name',
            field_map=SUM_MAP,
        )
        truncated = False
    else:
        groups = aggregate_groups(
            qs,
            group_id_field='staff_id',
            group_name_field='staff__name',
            field_map=SUM_MAP,
        )
        for g in groups:
            if not g['label'] or g['label'] == '—':
                g['label'] = 'Без оценщика'
        truncated = False

    type_receptions = list(
        RefTypeReceptionCarsOrganization.objects.exclude(name='').order_by('name').values_list('name', flat=True)[:50]
    )

    return report_shell(
        filters=filters,
        totals=totals,
        rows=rows,
        groups=groups,
        view=view,
        title='Принятые автомобили ОП АСП',
        subtitle='По проведённым листам оценки. Итоги — из БД, детали групп — по клику.',
        person_label='Оценщик',
        page_obj=page_obj,
        paginator=paginator,
        truncated=truncated,
        extra={
            'type_receptions': type_receptions,
            'show_dates': True,
            'details_url': '/asp/reports/accepted/',
        },
    )
