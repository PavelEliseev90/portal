# -*- coding: utf-8 -*-
"""Списки СОП / отгрузок: фильтры, столбцы, сортировка, Excel, сохранённые пресеты."""
from __future__ import annotations

import json
from io import BytesIO
from typing import Any
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import OuterRef, Q, QuerySet, Subquery
from django.http import HttpResponse, QueryDict
from django.utils import timezone
from openpyxl import Workbook

from asp.models import ReportSavedFilter
from asp.report_common import (
    asp_type_receptions_qs,
    filters_for_template,
    month_bounds,
    parse_date,
    parse_int_ids,
)
from asp.saved_filters import (
    filter_data_to_querydict,
    get_accessible_saved_filter,
    saved_filters_for_template,
    snapshot_filter_data,
)
from documents.models import DocCarAgreement, DocCarShipment
from refs.models import RefCarsOrganization, RefUnit

AGREEMENT_KEY = 'docs_agreement'
SHIPMENT_KEY = 'docs_shipment'

PAGE_SIZE = 50
COLUMNS_COOKIE_PREFIX = 'docs_cols_'
COLUMNS_COOKIE_MAX_AGE = 60 * 60 * 24 * 365
COLUMNS_COOKIE_VERSION = {
    AGREEMENT_KEY: 'v1',
    SHIPMENT_KEY: 'v1',
}

SKIP_KEYS = frozenset({'page', 'ajax', 'export', 'saved_filter'})

AGREEMENT_DEFAULT_COLUMNS = [
    'open', 'date', 'nomer', 'unit', 'client', 'car', 'vin',
    'check_estimated', 'check_actual', 'amount', 'person', 'type_sale',
]
AGREEMENT_COLUMN_DEFS = {
    'open': {'label': '#', 'sortable': False, 'num': False},
    'date': {'label': 'Дата', 'sortable': True, 'sort_key': 'date', 'num': False},
    'nomer': {'label': 'Номер', 'sortable': True, 'sort_key': 'nomer', 'num': False},
    'unit': {'label': 'Подразделение', 'sortable': True, 'sort_key': 'unit', 'num': False},
    'client': {'label': 'Клиент', 'sortable': True, 'sort_key': 'client', 'num': False},
    'car': {'label': 'Автомобиль', 'sortable': True, 'sort_key': 'car', 'num': False},
    'vin': {'label': 'VIN', 'sortable': True, 'sort_key': 'vin', 'num': False},
    'check_estimated': {'label': 'Расчётный КМ', 'sortable': True, 'sort_key': 'check_estimated', 'num': False},
    'check_actual': {'label': 'Фактический КМ', 'sortable': True, 'sort_key': 'check_actual', 'num': False},
    'amount': {'label': 'Цена', 'sortable': True, 'sort_key': 'amount', 'num': True},
    'cm_est': {'label': 'КМ расчёт', 'sortable': True, 'sort_key': 'cm_est', 'num': True},
    'cm_actual': {'label': 'КМ факт', 'sortable': True, 'sort_key': 'cm_actual', 'num': True},
    'person': {'label': 'Сотрудник', 'sortable': True, 'sort_key': 'person', 'num': False},
    'type_sale': {'label': 'Тип продажи', 'sortable': True, 'sort_key': 'type_sale', 'num': False},
    'type_reception': {'label': 'Тип приёма', 'sortable': True, 'sort_key': 'type_reception', 'num': False},
    'mark': {'label': 'Марка', 'sortable': True, 'sort_key': 'mark', 'num': False},
    'model': {'label': 'Модель', 'sortable': True, 'sort_key': 'model', 'num': False},
    'year': {'label': 'Год', 'sortable': True, 'sort_key': 'year', 'num': False},
    'run': {'label': 'Пробег', 'sortable': True, 'sort_key': 'run', 'num': True},
}
AGREEMENT_SORT = {
    'date': 'dataTime',
    'nomer': 'nomer',
    'unit': 'unit__name',
    'client': 'client__name',
    'car': 'lo_mark',
    'vin': 'lo_vin',
    'check_estimated': 'check_estimated',
    'check_actual': 'check_actual',
    'amount': 'amount',
    'cm_est': 'cm_est',
    'cm_actual': 'cm_actual',
    'person': 'staff__name',
    'type_sale': 'typeSale',
    'type_reception': 'lo_type_reception',
    'mark': 'lo_mark',
    'model': 'lo_model',
    'year': 'lo_year',
    'run': 'lo_run',
}

SHIPMENT_DEFAULT_COLUMNS = [
    'open', 'date', 'nomer', 'unit', 'client', 'car', 'vin',
    'amount', 'type_sale', 'agreement', 'person',
]
SHIPMENT_COLUMN_DEFS = {
    'open': {'label': '#', 'sortable': False, 'num': False},
    'date': {'label': 'Дата', 'sortable': True, 'sort_key': 'date', 'num': False},
    'nomer': {'label': 'Номер', 'sortable': True, 'sort_key': 'nomer', 'num': False},
    'unit': {'label': 'Подразделение', 'sortable': True, 'sort_key': 'unit', 'num': False},
    'client': {'label': 'Клиент', 'sortable': True, 'sort_key': 'client', 'num': False},
    'car': {'label': 'Автомобиль', 'sortable': True, 'sort_key': 'car', 'num': False},
    'vin': {'label': 'VIN', 'sortable': True, 'sort_key': 'vin', 'num': False},
    'amount': {'label': 'Цена', 'sortable': True, 'sort_key': 'amount', 'num': True},
    'cost_price': {'label': 'Себест.', 'sortable': True, 'sort_key': 'cost_price', 'num': True},
    'outlay': {'label': 'Расходы', 'sortable': True, 'sort_key': 'outlay', 'num': True},
    'type_sale': {'label': 'Тип продажи', 'sortable': True, 'sort_key': 'type_sale', 'num': False},
    'agreement': {'label': 'Соглашение', 'sortable': True, 'sort_key': 'agreement', 'num': False},
    'person': {'label': 'Сотрудник', 'sortable': True, 'sort_key': 'person', 'num': False},
    'type_reception': {'label': 'Тип приёма', 'sortable': True, 'sort_key': 'type_reception', 'num': False},
    'mark': {'label': 'Марка', 'sortable': True, 'sort_key': 'mark', 'num': False},
    'model': {'label': 'Модель', 'sortable': True, 'sort_key': 'model', 'num': False},
    'year': {'label': 'Год', 'sortable': True, 'sort_key': 'year', 'num': False},
    'run': {'label': 'Пробег', 'sortable': True, 'sort_key': 'run', 'num': True},
}
SHIPMENT_SORT = {
    'date': 'dataTime',
    'nomer': 'nomer',
    'unit': 'unit__name',
    'client': 'client__name',
    'car': 'lo_mark',
    'vin': 'lo_vin',
    'amount': 'amount',
    'cost_price': 'cost_price',
    'outlay': 'outlay',
    'type_sale': 'typeSale',
    'agreement': 'agreement__nomer',
    'person': 'staff__name',
    'type_reception': 'lo_type_reception',
    'mark': 'lo_mark',
    'model': 'lo_model',
    'year': 'lo_year',
    'run': 'lo_run',
}

REPORTS = {
    AGREEMENT_KEY: {
        'defs': AGREEMENT_COLUMN_DEFS,
        'defaults': AGREEMENT_DEFAULT_COLUMNS,
        'sort': AGREEMENT_SORT,
        'default_order': '-date',
        'title': 'Соглашения о покупке а/м',
        'subtitle': 'Список соглашений о покупке автомобилей',
        'list_type': 'doc_car_agreement',
        'model': DocCarAgreement,
    },
    SHIPMENT_KEY: {
        'defs': SHIPMENT_COLUMN_DEFS,
        'defaults': SHIPMENT_DEFAULT_COLUMNS,
        'sort': SHIPMENT_SORT,
        'default_order': '-date',
        'title': 'Отгрузки автомобилей',
        'subtitle': 'Список документов отгрузки',
        'list_type': 'doc_car_shipment',
        'model': DocCarShipment,
    },
}


def cookie_name(report_key: str) -> str:
    ver = COLUMNS_COOKIE_VERSION.get(report_key)
    if ver:
        return f'{COLUMNS_COOKIE_PREFIX}{report_key}_{ver}'
    return f'{COLUMNS_COOKIE_PREFIX}{report_key}'


def docs_units_qs():
    return RefUnit.objects.filter(buauto=True).only('id', 'name').order_by('name')


def _parse_multi_ids(get, *keys: str) -> list[int]:
    getlist = getattr(get, 'getlist', None)
    raw = []
    if callable(getlist):
        for key in keys:
            raw.extend(list(getlist(key) or []))
            raw.extend(list(getlist(f'{key}[]') or []))
    return parse_int_ids(raw)


def parse_filters(get, *, default_month: bool = True) -> dict[str, Any]:
    raw_from = get.get('date_from') or get.get('date_start')
    raw_to = get.get('date_to') or get.get('date_end')
    date_from = parse_date(raw_from)
    date_to = parse_date(raw_to)
    has_date_params = any(
        key in get for key in ('date_from', 'date_to', 'date_start', 'date_end')
    )
    if default_month and not has_date_params and date_from is None and date_to is None:
        date_from, date_to = month_bounds()

    unit_ids = _parse_multi_ids(get, 'unit', 'unit_ids', 'unit_id')
    type_reception_ids = _parse_multi_ids(
        get, 'type_reception', 'type_reception_ids', 'type_reception_id',
    )

    order_by = (get.get('order_by') or '').strip()

    return {
        'date_from': date_from,
        'date_to': date_to,
        'unit_ids': unit_ids,
        'type_reception_ids': type_reception_ids,
        'vin': (get.get('vin') or '').strip(),
        'mark': (get.get('mark') or '').strip(),
        'model': (get.get('model') or '').strip(),
        'person': (get.get('person') or '').strip(),
        'type_sale': (get.get('type_sale') or '').strip(),
        'client': (get.get('client') or '').strip(),
        'nomer': (get.get('nomer') or '').strip(),
        'order_by': order_by,
        'page': max(1, int(get.get('page') or 1) if str(get.get('page') or '').isdigit() else 1),
        'saved_filter': (get.get('saved_filter') or '').strip(),
        # совместимость со старым ?name=
        'name': (get.get('name') or '').strip(),
    }


def resolve_get(request, report_key: str) -> QueryDict:
    base = request.GET.copy()
    if not isinstance(base, QueryDict):
        base = QueryDict(mutable=True)
    else:
        base = base.copy()

    raw_id = (base.get('saved_filter') or '').strip()
    if not raw_id.isdigit():
        return base

    preset = get_accessible_saved_filter(request.user, report_key, int(raw_id))
    if preset is None:
        return base

    extras = {'saved_filter': raw_id}
    if base.get('order_by'):
        extras['order_by'] = base.get('order_by')
    if base.get('page'):
        extras['page'] = base.get('page')
    if base.get('export'):
        extras['export'] = base.get('export')
    return filter_data_to_querydict(preset.filter_data, extras=extras)


def annotate_lo(qs: QuerySet) -> QuerySet:
    sub = RefCarsOrganization.objects.filter(lo__id=OuterRef(name='lo__id'))
    qs = qs.annotate(
        lo_date=Subquery(sub.values('lo_link_date')[:1]),
        lo_number=Subquery(sub.values('lo_link_number')[:1]),
        lo_type_reception=Subquery(sub.values('type_reception__name')[:1]),
        lo_status=Subquery(sub.values('status__name')[:1]),
        lo_vin=Subquery(sub.values('vin')[:1]),
        lo_vin2=Subquery(sub.values('vin2')[:1]),
        lo_days_in_stok=Subquery(sub.values('days_in_stok')[:1]),
        lo_type_sale=Subquery(sub.values('type_sale__name')[:1]),
        lo_description_podgotovka=Subquery(sub.values('description_podgotovka')[:1]),
        lo_description_op=Subquery(sub.values('description_op')[:1]),
        lo_evaluation=Subquery(sub.values('evaluation__name')[:1]),
        lo_group_price=Subquery(sub.values('group_price__name')[:1]),
        lo_stageprice=Subquery(sub.values('stage_price__name')[:1]),
        lo_rating=Subquery(sub.values('rating__name')[:1]),
        lo_mark=Subquery(sub.values('modification_autoru__model__mark__name')[:1]),
        lo_model=Subquery(sub.values('modification_autoru__model__name')[:1]),
        lo_modification=Subquery(sub.values('modification_autoru__name')[:1]),
        lo_year=Subquery(sub.values('year')[:1]),
        lo_quantity=Subquery(sub.values('quantity')[:1]),
        lo_run=Subquery(sub.values('run')[:1]),
        lo_color=Subquery(sub.values('color')[:1]),
        lo_days_next_stage=Subquery(sub.values('days_next_stage')[:1]),
        lo_task=Subquery(sub.values('task')[:1]),
        lo_store=Subquery(sub.values('store__name')[:1]),
        lo_unit=Subquery(sub.values('unit__name')[:1]),
        lo_is_new=Subquery(sub.values('is_new')[:1]),
        lo_plate_number=Subquery(sub.values('plate_number')[:1]),
        lo_slug=Subquery(sub.values('slug')[:1]),
    )
    from documents.rlk_estimation import subquery_estimation_id
    return qs.annotate(estimation=subquery_estimation_id('lo__rlk', 'lo__rlk__uin'))


def apply_filters(qs: QuerySet, filters: dict[str, Any]) -> QuerySet:
    if filters.get('date_from'):
        qs = qs.filter(dataTime__date__gte=filters['date_from'])
    if filters.get('date_to'):
        qs = qs.filter(dataTime__date__lte=filters['date_to'])
    if filters.get('unit_ids'):
        qs = qs.filter(unit_id__in=filters['unit_ids'])
    if filters.get('type_reception_ids'):
        qs = qs.filter(lo__type_reception_id__in=filters['type_reception_ids'])
    if filters.get('nomer'):
        qs = qs.filter(nomer__icontains=filters['nomer'])
    if filters.get('person'):
        qs = qs.filter(staff__name__icontains=filters['person'])
    if filters.get('type_sale'):
        qs = qs.filter(typeSale__icontains=filters['type_sale'])
    if filters.get('client'):
        client = filters['client']
        qs = qs.filter(
            Q(clientName__icontains=client)
            | Q(client__name__icontains=client)
            | Q(client__full_name__icontains=client)
        )
    # аннотации уже на qs
    if filters.get('vin'):
        vin = filters['vin']
        qs = qs.filter(
            Q(lo_vin__icontains=vin)
            | Q(lo_vin2__icontains=vin)
            | Q(cars__vin__icontains=vin)
            | Q(cars__vin2__icontains=vin)
        )
    if filters.get('mark'):
        mark = filters['mark']
        qs = qs.filter(Q(lo_mark__icontains=mark) | Q(cars__mark__icontains=mark))
    if filters.get('model'):
        model = filters['model']
        qs = qs.filter(Q(lo_model__icontains=model) | Q(cars__model__icontains=model))
    # старый единый поиск
    name = filters.get('name') or ''
    if name:
        qs = qs.filter(
            Q(lo_vin__icontains=name)
            | Q(lo_mark__icontains=name)
            | Q(lo_model__icontains=name)
            | Q(client__full_name__icontains=name)
            | Q(client__name__icontains=name)
            | Q(nomer__icontains=name)
        )
    return qs


def resolve_order_by(report_key: str, order_by: str | None) -> tuple[str, tuple[str, ...]]:
    cfg = REPORTS[report_key]
    raw = (order_by or cfg['default_order']).strip() or cfg['default_order']
    descending = raw.startswith('-')
    key = raw[1:] if descending else raw
    sort_map = cfg['sort']
    if key not in sort_map:
        raw = cfg['default_order']
        descending = raw.startswith('-')
        key = raw[1:] if descending else raw
    field = sort_map[key]
    orm = (f'-{field}' if descending else field, '-pk')
    ui = f'-{key}' if descending else key
    return ui, orm


def normalize_columns(report_key: str, raw_columns) -> list[str]:
    cfg = REPORTS[report_key]
    defaults = list(cfg['defaults'])
    valid = set(cfg['defs'].keys())
    if not raw_columns:
        return defaults
    seen = set()
    result = []
    for key in raw_columns:
        if key in valid and key not in seen:
            result.append(key)
            seen.add(key)
    return result or defaults


def get_user_columns(request, report_key: str) -> list[str]:
    raw = request.COOKIES.get(cookie_name(report_key))
    text = (raw or '').strip()
    if not text:
        return list(REPORTS[report_key]['defaults'])
    if text.startswith('['):
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return normalize_columns(report_key, data)
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    return normalize_columns(report_key, [p.strip() for p in text.split(',') if p.strip()])


def build_table_columns(report_key: str, visible_keys: list[str]) -> list[dict]:
    defs = REPORTS[report_key]['defs']
    columns = []
    for key in visible_keys:
        defn = defs[key]
        columns.append({
            'key': key,
            'label': defn['label'],
            'sortable': bool(defn.get('sortable')),
            'sort_key': defn.get('sort_key') or key,
            'num': bool(defn.get('num')),
        })
    return columns


def build_columns_settings(report_key: str, visible_keys: list[str]) -> list[dict]:
    defs = REPORTS[report_key]['defs']
    visible_set = set(visible_keys)
    ordered = list(visible_keys)
    for key in defs:
        if key not in visible_set:
            ordered.append(key)
    return [
        {'key': key, 'label': defs[key]['label'], 'visible': key in visible_set}
        for key in ordered
    ]


def has_active_filters(filters: dict[str, Any]) -> bool:
    if filters.get('unit_ids') or filters.get('type_reception_ids'):
        return True
    for key in ('vin', 'mark', 'model', 'person', 'type_sale', 'client', 'nomer', 'name'):
        if filters.get(key):
            return True
    # даты отличаются от дефолтного месяца
    if filters.get('date_from') or filters.get('date_to'):
        return True
    return False


def build_query_string(filters: dict[str, Any], exclude: tuple[str, ...] = ('page',)) -> str:
    exclude_set = set(exclude)
    pairs = []
    if 'date_from' not in exclude_set and filters.get('date_from'):
        df = filters['date_from']
        pairs.append(('date_from', df.isoformat() if hasattr(df, 'isoformat') else df))
    if 'date_to' not in exclude_set and filters.get('date_to'):
        dt = filters['date_to']
        pairs.append(('date_to', dt.isoformat() if hasattr(dt, 'isoformat') else dt))
    if 'unit_ids' not in exclude_set:
        for uid in filters.get('unit_ids') or []:
            pairs.append(('unit', str(uid)))
    if 'type_reception_ids' not in exclude_set:
        for tid in filters.get('type_reception_ids') or []:
            pairs.append(('type_reception', str(tid)))
    for key in ('vin', 'mark', 'model', 'person', 'type_sale', 'client', 'nomer', 'order_by', 'name'):
        if key in exclude_set:
            continue
        val = filters.get(key)
        if val not in (None, '', [], False):
            pairs.append((key, str(val)))
    return urlencode(pairs)


def _client_name(doc) -> str:
    if getattr(doc, 'client_id', None) and doc.client:
        return (doc.client.name or doc.client.full_name or '').strip()
    return (getattr(doc, 'clientName', None) or '').strip()


def _car_label(doc) -> str:
    parts = [
        getattr(doc, 'lo_mark', None) or '',
        getattr(doc, 'lo_model', None) or '',
        getattr(doc, 'lo_modification', None) or '',
    ]
    label = ' '.join(p for p in parts if p).strip()
    year = getattr(doc, 'lo_year', None)
    run = getattr(doc, 'lo_run', None)
    extra = []
    if year:
        extra.append(f'{year} г.в.')
    if run not in (None, ''):
        try:
            extra.append(f'{int(run):,} км'.replace(',', ' '))
        except (TypeError, ValueError):
            extra.append(f'{run} км')
    if extra:
        label = f'{label} / {" ".join(extra)}'.strip(' /')
    return label


def row_from_doc(doc, report_key: str) -> dict[str, Any]:
    vin = (getattr(doc, 'lo_vin', None) or '') or ''
    if not vin and getattr(doc, 'cars_id', None) and doc.cars:
        vin = doc.cars.vin or ''
    base = {
        'id': doc.pk,
        'open': doc.pk,
        'date': doc.dataTime,
        'nomer': doc.nomer or '',
        'unit': doc.unit.name if getattr(doc, 'unit_id', None) and doc.unit else '',
        'client': _client_name(doc),
        'car': _car_label(doc),
        'vin': vin,
        'amount': doc.amount,
        'person': doc.staff.name if getattr(doc, 'staff_id', None) and doc.staff else '',
        'type_sale': getattr(doc, 'typeSale', None) or getattr(doc, 'lo_type_sale', None) or '',
        'type_reception': getattr(doc, 'lo_type_reception', None) or '',
        'mark': getattr(doc, 'lo_mark', None) or '',
        'model': getattr(doc, 'lo_model', None) or '',
        'year': getattr(doc, 'lo_year', None) or '',
        'run': getattr(doc, 'lo_run', None),
    }
    if report_key == AGREEMENT_KEY:
        base.update({
            'check_estimated': bool(getattr(doc, 'check_estimated', False)),
            'check_actual': bool(getattr(doc, 'check_actual', False)),
            'cm_est': getattr(doc, 'cm_est', None),
            'cm_actual': getattr(doc, 'cm_actual', None),
            'detail_url': f'/docs_car_agreement/{doc.pk}/',
        })
    else:
        agr = ''
        if getattr(doc, 'agreement_id', None) and doc.agreement:
            agr = doc.agreement.nomer or ''
        base.update({
            'cost_price': getattr(doc, 'cost_price', None),
            'outlay': getattr(doc, 'outlay', None),
            'agreement': agr,
            'detail_url': f'/docs_car_shipment/{doc.pk}/',
        })
    return base


def cell_export_value(row: dict, key: str):
    if key == 'open':
        return row.get('id')
    if key in ('check_estimated', 'check_actual'):
        return 'Да' if row.get(key) else 'Нет'
    if key == 'date':
        val = row.get('date')
        if val is None:
            return ''
        try:
            return timezone.localtime(val).strftime('%d.%m.%Y %H:%M')
        except (ValueError, TypeError, AttributeError):
            try:
                return val.strftime('%d.%m.%Y %H:%M')
            except Exception:
                return str(val)
    return row.get(key)


def export_xlsx(report_key: str, filters: dict, columns: list[dict], qs: QuerySet) -> HttpResponse:
    cfg = REPORTS[report_key]
    wb = Workbook()
    ws = wb.active
    ws.title = 'Данные'
    # сводка фильтров
    ws.append(['Отчёт', cfg['title']])
    if filters.get('date_from') or filters.get('date_to'):
        ws.append([
            'Период',
            '{} — {}'.format(
                filters['date_from'].isoformat() if filters.get('date_from') else '…',
                filters['date_to'].isoformat() if filters.get('date_to') else '…',
            ),
        ])
    if filters.get('vin'):
        ws.append(['VIN', filters['vin']])
    if filters.get('nomer'):
        ws.append(['Номер', filters['nomer']])
    if filters.get('client'):
        ws.append(['Клиент', filters['client']])
    if filters.get('person'):
        ws.append(['Сотрудник', filters['person']])
    ws.append([])
    ws.append([c['label'] for c in columns])
    for doc in qs[:10000]:
        row = row_from_doc(doc, report_key)
        ws.append([cell_export_value(row, c['key']) for c in columns])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f'{report_key}_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx'
    response = HttpResponse(
        buf.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def build_list_context(request, report_key: str) -> dict[str, Any] | HttpResponse:
    cfg = REPORTS[report_key]
    get = resolve_get(request, report_key)
    filters = parse_filters(get, default_month=True)
    order_ui, orm_order = resolve_order_by(report_key, filters.get('order_by'))
    filters['order_by'] = order_ui

    Model = cfg['model']
    qs = Model.objects.select_related('unit', 'client', 'staff', 'cars')
    if report_key == SHIPMENT_KEY:
        qs = qs.select_related('agreement')
    qs = annotate_lo(qs)
    qs = apply_filters(qs, filters)
    qs = qs.order_by(*orm_order)

    visible = get_user_columns(request, report_key)
    table_columns = build_table_columns(report_key, visible)
    columns_settings = build_columns_settings(report_key, visible)

    if (get.get('export') or '').strip().lower() in ('xlsx', 'excel', '1'):
        return export_xlsx(report_key, filters, table_columns, qs)

    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(filters['page'])
    rows = [row_from_doc(doc, report_key) for doc in page_obj.object_list]

    qs_params = build_query_string(filters)
    export_url = f'?{qs_params}&export=xlsx' if qs_params else '?export=xlsx'

    tpl_filters = filters_for_template(filters)
    tpl_filters['order_by'] = order_ui
    tpl_filters['name'] = filters.get('name') or ''
    tpl_filters['saved_filter'] = filters.get('saved_filter') or ''

    return {
        'type': cfg['list_type'],
        'report_key': report_key,
        'report_title': cfg['title'],
        'report_subtitle': cfg['subtitle'],
        'user': request.user,
        'filtr': tpl_filters,
        'filters': tpl_filters,
        'paginator': page_obj,
        'page_obj': page_obj,
        'rows': rows,
        'table_columns': table_columns,
        'columns_settings': columns_settings,
        'columns_defaults': list(cfg['defaults']),
        'columns_defaults_json': json.dumps(list(cfg['defaults'])),
        'has_filters': has_active_filters(filters),
        'saved_filters': saved_filters_for_template(
            request.user, report_key, filters.get('saved_filter'),
        ),
        'units_qs': docs_units_qs(),
        'type_receptions_qs': asp_type_receptions_qs().only('id', 'name'),
        'export_url': export_url,
        'query_string': qs_params,
        'list_path': request.path,
    }
