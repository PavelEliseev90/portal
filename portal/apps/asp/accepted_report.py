# -*- coding: utf-8 -*-
"""Отчёт по принятым (DocLO) ОП АСП — быстрые агрегаты + ленивые детали."""
from __future__ import annotations

from typing import Any

from django.db.models import CharField, F, Q, Value
from django.db.models.functions import Coalesce

from asp.report_common import (
    GROUP_DETAIL_LIMIT,
    aggregate_groups,
    aggregate_totals,
    allowed_unit_ids,
    apply_type_reception_filter,
    details_payload,
    money,
    paginate_values_qs,
    parse_common_filters,
    report_shell,
    sum_money,
)
from asp.report_table import resolve_order_by
from documents.models import DocLO

SUM_MAP = {
    'cost_price': sum_money('cost_price'),
    'bcp': sum_money('bcp'),
    'run': sum_money('run'),
    'owners': sum_money('owners'),
    'keys': sum_money('keys'),
}


def _annotate_report_staff(qs):
    """Оценщик: вкладка приёма → интерактивная оценка → ЛО."""
    return qs.annotate(
        report_staff_id=Coalesce(
            F('rlk__reginteractivocenkarlk__page_reception__staff_id'),
            F('rlk__reginteractivocenkarlk__staff_rlk_id'),
            F('rlk__reginteractivocenka__staff_id'),
            F('rlk__reginteractivocenkarlk__estimation__staff_id'),
            F('staff_id'),
        ),
        report_staff_name=Coalesce(
            F('rlk__reginteractivocenkarlk__page_reception__staff__name'),
            F('rlk__reginteractivocenkarlk__staff_rlk__name'),
            F('rlk__reginteractivocenka__staff__name'),
            F('rlk__reginteractivocenkarlk__estimation__staff__name'),
            F('staff__name'),
            Value(''),
            output_field=CharField(),
        ),
    )


def _apply_alfa_transition_filter(qs, unit_ids: list[int]):
    """Отбор ЛО по дате перехода подразделения на Альфа-Авто.

    Если у подразделения заполнена alfa_auto_transition_date:
    - ИБ не Альфа (ib.alfa=False) → документы строго до этой даты;
    - ИБ Альфа (ib.alfa=True) → документы с этой даты включительно.
    Без даты перехода ограничение не накладывается.
    """
    if not unit_ids:
        return qs

    from refs.models import RefUnit

    units = list(
        RefUnit.objects
        .filter(pk__in=unit_ids, alfa_auto_transition_date__isnull=False)
        .select_related('ib')
        .only('id', 'alfa_auto_transition_date', 'ib_id', 'ib__alfa')
    )
    if not units:
        return qs

    transition_ids = {u.pk for u in units}
    plain_ids = [uid for uid in unit_ids if uid not in transition_ids]

    date_q = Q()
    if plain_ids:
        date_q |= Q(unit_id__in=plain_ids)

    for unit in units:
        transition = unit.alfa_auto_transition_date
        is_alfa = bool(getattr(getattr(unit, 'ib', None), 'alfa', False))
        if is_alfa:
            date_q |= Q(unit_id=unit.pk, dataTime__date__gte=transition)
        else:
            date_q |= Q(unit_id=unit.pk, dataTime__date__lt=transition)

    return qs.filter(date_q)


def filtered_accepted_qs(filters: dict[str, Any]):
    unit_ids = allowed_unit_ids(filters)
    qs = _annotate_report_staff(
        DocLO.objects.filter(active=True, unit_id__in=unit_ids)
    )
    qs = _apply_alfa_transition_filter(qs, unit_ids)

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
        qs = qs.filter(report_staff_name__icontains=person)
    qs = apply_type_reception_filter(qs, filters, 'type_reception_id')
    client = filters.get('client') or ''
    if client:
        qs = qs.filter(Q(clientName__icontains=client) | Q(customer__name__icontains=client))
    nomer = filters.get('nomer') or ''
    if nomer:
        qs = qs.filter(Q(nomer__icontains=nomer) | Q(rlk__nomer__icontains=nomer))
    return qs


DETAIL_VALUES = (
    'id', 'nomer', 'dataTime', 'unit_id', 'unit__name', 'store__name',
    'staff_id', 'staff__name', 'report_staff_id', 'report_staff_name',
    'vin', 'vin2', 'year', 'run', 'owners', 'keys',
    'carsGRZ', 'clientName', 'cost_price', 'bcp', 'rlk_id', 'rlk__nomer',
    'auction', 'type_reception__name', 'kolesa2_reception',
    'cars__mark', 'cars__model', 'cars__vin', 'rlk__unit_dc__name',
    'rlk__reginteractivocenka__iznos',
)


def _lo_row_from_values(row: dict) -> dict[str, Any]:
    iznos = row.get('rlk__reginteractivocenka__iznos')
    person_name = (row.get('report_staff_name') or row.get('staff__name') or '').strip()
    return {
        'id': row['id'],
        'nomer': row.get('nomer') or '',
        'date': row.get('dataTime'),
        'unit_id': row.get('unit_id'),
        'unit_name': row.get('unit__name') or '—',
        'unit_source_name': row.get('rlk__unit_dc__name') or '',
        'store_name': row.get('store__name') or '',
        'person_id': row.get('report_staff_id') or row.get('staff_id') or 0,
        'person_name': person_name or 'Без оценщика',
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
        'group_price': '',
        'stage_price': '',
        'iznos': bool(iznos) if iznos is not None else None,
        'has_iznos': iznos is not None,
        'kolesa2_reception': bool(row.get('kolesa2_reception')),
        'cost_price': money(row.get('cost_price')),
        'bcp': money(row.get('bcp')),
        'rlk_id': row.get('rlk_id'),
        'rlk_nomer': row.get('rlk__nomer') or '',
        'auction': bool(row.get('auction')),
        'slug': '',
    }


def _apply_stock_price_fields(rows: list[dict]) -> None:
    """ЦГ и этап УС с карточки автомобиля, связанной с листом оценки."""
    lo_ids = []
    seen = set()
    for row in rows:
        lo_id = row.get('id')
        if lo_id and lo_id not in seen:
            seen.add(lo_id)
            lo_ids.append(lo_id)
    if not lo_ids:
        return
    try:
        from refs.models import RefCarsOrganization
    except Exception:
        return

    by_lo_vin = {}
    by_lo = {}
    chunk = 500
    for i in range(0, len(lo_ids), chunk):
        part = lo_ids[i:i + chunk]
        qs = (
            RefCarsOrganization.objects
            .filter(lo_id__in=part)
            .order_by('-pk')
            .values('lo_id', 'vin', 'slug', 'group_price__name', 'stage_price__name')
        )
        for item in qs:
            lo_id = item.get('lo_id')
            vin = (item.get('vin') or '').strip().upper()
            payload = {
                'group_price': item.get('group_price__name') or '',
                'stage_price': item.get('stage_price__name') or '',
                'slug': item.get('slug') or '',
            }
            if vin and (lo_id, vin) not in by_lo_vin:
                by_lo_vin[(lo_id, vin)] = payload
            if lo_id not in by_lo:
                by_lo[lo_id] = payload

    for row in rows:
        lo_id = row.get('id')
        vin = (row.get('vin') or '').strip().upper()
        info = by_lo_vin.get((lo_id, vin)) if lo_id and vin else None
        if not info and lo_id:
            info = by_lo.get(lo_id)
        info = info or {}
        row['group_price'] = info.get('group_price') or ''
        row['stage_price'] = info.get('stage_price') or ''
        row['slug'] = info.get('slug') or ''


def _lo_rows_from_values(values: list[dict]) -> list[dict[str, Any]]:
    rows = [_lo_row_from_values(row) for row in values]
    _apply_stock_price_fields(rows)
    return rows


def iter_detail_rows(qs, limit=GROUP_DETAIL_LIMIT):
    values = list(qs.order_by('-dataTime', '-pk').values(*DETAIL_VALUES)[:limit])
    return _lo_rows_from_values(values)


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
            qs = qs.filter(report_staff_id=key_int)
        else:
            qs = qs.filter(report_staff_id__isnull=True)
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
        _apply_stock_price_fields(rows)
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
            group_id_field='report_staff_id',
            group_name_field='report_staff_name',
            field_map=SUM_MAP,
        )
        for g in groups:
            if not g['label'] or g['label'] == '—':
                g['label'] = 'Без оценщика'
        truncated = False

    return report_shell(
        filters=filters,
        totals=totals,
        rows=rows,
        groups=groups,
        view=view,
        title='Принятые автомобили ОП АСП',
        subtitle='По проведённым листам оценки. Для подразделений с датой перехода на Альфа: Корс — до даты, Альфа — с даты. Итоги — из БД, детали групп — по клику.',
        person_label='Оценщик',
        page_obj=page_obj,
        paginator=paginator,
        truncated=truncated,
        extra={
            'show_dates': True,
            'details_url': '/asp/reports/accepted/',
        },
    )
