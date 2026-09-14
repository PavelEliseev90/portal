# -*- coding: utf-8 -*-
"""Список рабочих листов ОП (/docs_rlk/): фильтры, столбцы, сортировка, Excel, сохранённые пресеты."""
from __future__ import annotations

import json
from io import BytesIO
from typing import Any
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Count, Q, QuerySet
from django.http import HttpResponse, QueryDict
from django.utils import timezone
from openpyxl import Workbook

from asp.models import ReportSavedFilter
from asp.report_common import (
    filters_for_template,
    month_bounds,
    parse_date,
    parse_int_ids,
)
from asp.saved_filters import (
    filter_data_to_querydict,
    get_accessible_saved_filter,
    saved_filters_for_template,
)
from documents.models import DocRLK
from refs.models import RefContactType, RefStatusRLK, RefTypeDocRLK, RefUnit

RLK_KEY = 'docs_rlk'
PAGE_SIZE = 50
COLUMNS_COOKIE_PREFIX = 'docs_cols_'
COLUMNS_COOKIE_MAX_AGE = 60 * 60 * 24 * 365
COLUMNS_COOKIE_VERSION = 'v1'

RLK_DEFAULT_COLUMNS = [
    'open',
    'date',
    'nomer',
    'unit',
    'staff',
    'client',
    'phone',
    'car',
    'vin',
    'status',
    'contact_type',
    'archive',
]

RLK_COLUMN_DEFS = {
    'open': {'label': '#', 'sortable': False, 'num': False},
    'date': {'label': 'Дата', 'sortable': True, 'sort_key': 'date', 'num': False},
    'nomer': {'label': 'Номер', 'sortable': True, 'sort_key': 'nomer', 'num': False},
    'unit': {'label': 'Подразделение', 'sortable': True, 'sort_key': 'unit', 'num': False},
    'staff': {'label': 'Менеджер', 'sortable': True, 'sort_key': 'staff', 'num': False},
    'client': {'label': 'Клиент', 'sortable': True, 'sort_key': 'client', 'num': False},
    'phone': {'label': 'Телефон', 'sortable': False, 'num': False},
    'car': {'label': 'Автомобиль', 'sortable': True, 'sort_key': 'car', 'num': False},
    'vin': {'label': 'VIN', 'sortable': True, 'sort_key': 'vin', 'num': False},
    'status': {'label': 'Статус', 'sortable': True, 'sort_key': 'status', 'num': False},
    'contact_type': {'label': 'Вид контакта', 'sortable': True, 'sort_key': 'contact_type', 'num': False},
    'type': {'label': 'Тип РЛ', 'sortable': True, 'sort_key': 'type', 'num': False},
    'trade_in': {'label': 'Трейд-ин', 'sortable': False, 'num': False},
    'archive': {'label': 'Архив', 'sortable': True, 'sort_key': 'archive', 'num': False},
    'type_archive': {'label': 'Причина архива', 'sortable': True, 'sort_key': 'type_archive', 'num': False},
    'is_missed': {'label': 'Упущенный', 'sortable': True, 'sort_key': 'is_missed', 'num': False},
    'eco': {'label': 'Оценка / Trade-in', 'sortable': True, 'sort_key': 'eco', 'num': False},
    'duration': {'label': 'Время визита', 'sortable': False, 'num': False},
}

RLK_SORT = {
    'date': 'dataTime',
    'nomer': 'nomer',
    'unit': 'unit__name',
    'staff': 'staff__name',
    'client': 'clientName',
    'car': 'cars__mark',
    'vin': 'cars__vin',
    'status': 'status__name',
    'contact_type': 'contacType__name',
    'type': 'type__name',
    'archive': 'archive',
    'type_archive': 'type_archive__name',
    'is_missed': 'is_missed',
    'eco': 'eco',
}

REPORT_CONFIG = {
    'defs': RLK_COLUMN_DEFS,
    'defaults': RLK_DEFAULT_COLUMNS,
    'sort': RLK_SORT,
    'default_order': '-date',
    'title': 'Рабочие листы ОП',
    'subtitle': 'Список рабочих листов отдела продаж',
    'list_type': 'docs_rlk',
    'model': DocRLK,
}


def cookie_name(report_key: str = RLK_KEY) -> str:
    return f'{COLUMNS_COOKIE_PREFIX}{report_key}_{COLUMNS_COOKIE_VERSION}'


def rlk_units_qs():
    return (
        RefUnit.objects.exclude(name='ЕЦО ГК')
        .exclude(name='Основное подразделение')
        .only('id', 'name', 'city')
        .order_by('name')
    )


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
        key in get for key in ('date_from', 'date_to', 'date_start', 'date_end', 'date')
    )

    # Совместимость со старым ?date=YYYY-MM
    legacy_date = (get.get('date') or '').strip()
    if not date_from and not date_to and legacy_date:
        parts = legacy_date.split('-')
        if len(parts) == 2:
            try:
                y, m = int(parts[0]), int(parts[1])
                import datetime as dt
                cur = dt.date(y, m, 1)
                date_from, date_to = month_bounds(cur)
            except Exception:
                pass

    if default_month and not has_date_params and date_from is None and date_to is None:
        date_from, date_to = month_bounds()

    unit_ids = _parse_multi_ids(get, 'unit', 'unit_ids', 'unit_id')
    status_id = (get.get('status_id') or get.get('status') or '').strip()
    contact_type_id = (get.get('contact_type_id') or get.get('contact_type') or '').strip()
    type_id = (get.get('type_id') or '').strip()
    archive = (get.get('archive') or get.get('closed') or '').strip()
    eco = (get.get('eco') or '').strip()
    is_missed = (get.get('is_missed') or '').strip()
    order_by = (get.get('order_by') or '').strip()

    return {
        'date_from': date_from,
        'date_to': date_to,
        'unit_ids': unit_ids,
        'vin': (get.get('vin') or '').strip(),
        'nomer': (get.get('nomer') or get.get('number_doc') or '').strip(),
        'mark': (get.get('mark') or '').strip(),
        'model': (get.get('model') or '').strip(),
        'person': (get.get('person') or get.get('staff') or '').strip(),
        'client': (get.get('client') or get.get('customer') or '').strip(),
        'phone': (get.get('phone') or '').strip(),
        'status_id': int(status_id) if status_id.isdigit() else None,
        'contact_type_id': int(contact_type_id) if contact_type_id.isdigit() else None,
        'type_id': int(type_id) if type_id.isdigit() else None,
        'archive': archive,
        'eco': eco,
        'is_missed': is_missed,
        'order_by': order_by,
        'page': max(1, int(get.get('page') or 1) if str(get.get('page') or '').isdigit() else 1),
        'saved_filter': (get.get('saved_filter') or '').strip(),
        'name': (get.get('name') or '').strip(),
    }


def resolve_get(request, report_key: str = RLK_KEY) -> QueryDict:
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


def apply_filters(qs: QuerySet, filters: dict[str, Any]) -> QuerySet:
    if filters.get('date_from'):
        qs = qs.filter(dataTime__date__gte=filters['date_from'])
    if filters.get('date_to'):
        qs = qs.filter(dataTime__date__lte=filters['date_to'])
    if filters.get('unit_ids'):
        qs = qs.filter(Q(unit_id__in=filters['unit_ids']) | Q(unit_dc_id__in=filters['unit_ids']))
    if filters.get('nomer'):
        qs = qs.filter(nomer__icontains=filters['nomer'])
    if filters.get('person'):
        qs = qs.filter(staff__name__icontains=filters['person'])
    if filters.get('phone'):
        qs = qs.filter(phone__icontains=filters['phone'])
    if filters.get('client'):
        c = filters['client']
        qs = qs.filter(
            Q(clientName__icontains=c)
            | Q(customer__name__icontains=c)
            | Q(customer__full_name__icontains=c)
        )
    if filters.get('vin'):
        v = filters['vin']
        qs = qs.filter(
            Q(cars__vin__icontains=v)
            | Q(cars__vin2__icontains=v)
            | Q(vin_trade_in__icontains=v)
        )
    if filters.get('mark'):
        m = filters['mark']
        qs = qs.filter(Q(cars__mark__icontains=m) | Q(tradeInModel__icontains=m))
    if filters.get('model'):
        m = filters['model']
        qs = qs.filter(Q(cars__model__icontains=m) | Q(tradeInModel__icontains=m))
    if filters.get('status_id'):
        qs = qs.filter(status_id=filters['status_id'])
    if filters.get('contact_type_id'):
        qs = qs.filter(contacType_id=filters['contact_type_id'])
    if filters.get('type_id'):
        qs = qs.filter(type_id=filters['type_id'])

    archive_val = str(filters.get('archive') or '').lower()
    if archive_val in ('true', '1', 'yes', 'archived'):
        qs = qs.filter(archive=True)
    elif archive_val in ('false', '0', 'no', 'active'):
        qs = qs.filter(archive=False)

    eco_val = str(filters.get('eco') or '').lower()
    if eco_val in ('true', '1', 'yes', 'eco'):
        qs = qs.filter(eco=True)
    elif eco_val in ('false', '0', 'no', 'op'):
        qs = qs.filter(eco=False)

    missed_val = str(filters.get('is_missed') or '').lower()
    if missed_val in ('true', '1', 'yes', 'missed'):
        qs = qs.filter(is_missed__gt=0)
    elif missed_val in ('false', '0', 'no'):
        qs = qs.filter(is_missed=0)

    # Общий текстовый поиск name (совместимость)
    name = filters.get('name') or ''
    if name:
        qs = qs.filter(
            Q(nomer__icontains=name)
            | Q(clientName__icontains=name)
            | Q(customer__name__icontains=name)
            | Q(cars__vin__icontains=name)
            | Q(vin_trade_in__icontains=name)
            | Q(cars__mark__icontains=name)
            | Q(cars__model__icontains=name)
            | Q(phone__icontains=name)
        )
    return qs


def resolve_order_by(order_by: str | None) -> tuple[str, tuple[str, ...]]:
    default_order = REPORT_CONFIG['default_order']
    raw = (order_by or default_order).strip() or default_order
    descending = raw.startswith('-')
    key = raw[1:] if descending else raw
    sort_map = REPORT_CONFIG['sort']
    if key not in sort_map:
        raw = default_order
        descending = raw.startswith('-')
        key = raw[1:] if descending else raw
    field = sort_map[key]
    orm = (f'-{field}' if descending else field, '-pk')
    ui = f'-{key}' if descending else key
    return ui, orm


def normalize_columns(raw_columns) -> list[str]:
    defaults = list(RLK_DEFAULT_COLUMNS)
    valid = set(RLK_COLUMN_DEFS.keys())
    if not raw_columns:
        return defaults
    seen = set()
    result = []
    for key in raw_columns:
        if key in valid and key not in seen:
            result.append(key)
            seen.add(key)
    return result or defaults


def get_user_columns(request) -> list[str]:
    raw = request.COOKIES.get(cookie_name())
    text = (raw or '').strip()
    if not text:
        return list(RLK_DEFAULT_COLUMNS)
    if text.startswith('['):
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return normalize_columns(data)
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    return normalize_columns([p.strip() for p in text.split(',') if p.strip()])


def build_table_columns(visible_keys: list[str]) -> list[dict]:
    defs = RLK_COLUMN_DEFS
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


def build_columns_settings(visible_keys: list[str]) -> list[dict]:
    defs = RLK_COLUMN_DEFS
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
    if filters.get('unit_ids'):
        return True
    for key in (
        'vin', 'nomer', 'mark', 'model', 'person', 'client', 'phone',
        'status_id', 'contact_type_id', 'type_id', 'archive', 'eco', 'is_missed', 'name',
    ):
        if filters.get(key) not in (None, '', [], False):
            return True
    if filters.get('date_from') or filters.get('date_to'):
        return True
    return False


def build_query_string(filters: dict[str, Any], exclude: tuple[str, ...] = ('page',)) -> str:
    exclude_set = set(exclude)
    pairs = []
    if 'date_from' not in exclude_set and filters.get('date_from'):
        df = filters['date_from']
        pairs.append(('date_from', df.isoformat() if hasattr(df, 'isoformat') else str(df)))
    if 'date_to' not in exclude_set and filters.get('date_to'):
        dt = filters['date_to']
        pairs.append(('date_to', dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)))
    if 'unit_ids' not in exclude_set:
        for uid in filters.get('unit_ids') or []:
            pairs.append(('unit', str(uid)))
    for key in (
        'vin', 'nomer', 'mark', 'model', 'person', 'client', 'phone',
        'status_id', 'contact_type_id', 'type_id', 'archive', 'eco', 'is_missed',
        'order_by', 'name',
    ):
        if key in exclude_set:
            continue
        val = filters.get(key)
        if val not in (None, '', [], False):
            pairs.append((key, str(val)))
    return urlencode(pairs)


def _client_name(doc: DocRLK) -> str:
    if doc.customer_id and doc.customer:
        return (doc.customer.name or doc.customer.full_name or '').strip()
    return (doc.clientName or '').strip()


def _car_label(doc: DocRLK) -> str:
    if doc.cars_id and doc.cars:
        parts = [doc.cars.mark or '', doc.cars.model or '']
        label = ' '.join(p for p in parts if p).strip()
        if doc.cars.year:
            label += f' ({doc.cars.year} г.)'
        return label
    if doc.tradeInModel:
        return doc.tradeInModel.strip()
    return '—'


def _car_slug(doc: DocRLK) -> str:
    if doc.cars_id and doc.cars and doc.cars.slug:
        return doc.cars.slug
    return ''


def row_from_doc(doc: DocRLK) -> dict[str, Any]:
    vin = ''
    if doc.cars_id and doc.cars and doc.cars.vin:
        vin = doc.cars.vin.strip()
    elif doc.vin_trade_in:
        vin = doc.vin_trade_in.strip()

    duration = ''
    if doc.dataTimeCreate and doc.dataEnd and doc.dataEnd > doc.dataTimeCreate:
        try:
            delta = doc.dataEnd - doc.dataTimeCreate
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            duration = f'{hours}ч {minutes}м' if hours else f'{minutes} мин'
        except Exception:
            duration = ''

    return {
        'id': doc.pk,
        'open': doc.pk,
        'detail_url': f'/docs_rlk/{doc.pk}/',
        'date': doc.dataTime,
        'nomer': (doc.nomer or '').strip(),
        'unit': doc.unit.name if doc.unit else (doc.unit_dc.name if doc.unit_dc else ''),
        'staff': doc.staff.name if doc.staff else '',
        'client': _client_name(doc),
        'phone': (doc.phone or '').strip(),
        'car': _car_label(doc),
        'car_slug': _car_slug(doc),
        'vin': vin,
        'status': doc.status.name if doc.status else '',
        'status_id': doc.status_id,
        'contact_type': doc.contacType.name if doc.contacType else '',
        'type': doc.type.name if doc.type else '',
        'trade_in': (doc.tradeInModel or doc.vin_trade_in or '').strip(),
        'archive': bool(doc.archive),
        'type_archive': doc.type_archive.name if doc.type_archive else '',
        'is_missed': bool(doc.is_missed),
        'eco': bool(doc.eco),
        'duration': duration,
    }


def cell_export_value(row: dict, key: str):
    if key == 'open':
        return row.get('id')
    if key in ('archive', 'is_missed', 'eco'):
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
    return row.get(key) or ''


def export_xlsx(filters: dict, columns: list[dict], qs: QuerySet) -> HttpResponse:
    wb = Workbook()
    ws = wb.active
    ws.title = 'Рабочие листы'
    ws.append(['Отчёт', REPORT_CONFIG['title']])
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
        ws.append(['Менеджер', filters['person']])
    ws.append([])
    ws.append([c['label'] for c in columns])
    for doc in qs[:10000]:
        row = row_from_doc(doc)
        ws.append([cell_export_value(row, c['key']) for c in columns])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f'docs_rlk_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx'
    response = HttpResponse(
        buf.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def build_rlk_list_context(request) -> dict[str, Any] | HttpResponse:
    get = resolve_get(request, RLK_KEY)
    filters = parse_filters(get, default_month=True)
    order_ui, orm_order = resolve_order_by(filters.get('order_by'))
    filters['order_by'] = order_ui

    qs = (
        DocRLK.objects.select_related(
            'unit', 'unit_dc', 'staff', 'customer', 'cars',
            'status', 'contacType', 'type', 'type_archive',
        )
    )
    qs = apply_filters(qs, filters)

    # Агрегаты метрик быстрого обзора
    totals = qs.aggregate(
        count=Count('pk'),
        active=Count('pk', filter=Q(archive=False)),
        archive=Count('pk', filter=Q(archive=True)),
        eco=Count('pk', filter=Q(eco=True)),
        missed=Count('pk', filter=Q(is_missed__gt=0)),
    )

    qs = qs.order_by(*orm_order)

    visible = get_user_columns(request)
    table_columns = build_table_columns(visible)
    columns_settings = build_columns_settings(visible)

    if (get.get('export') or '').strip().lower() in ('xlsx', 'excel', '1'):
        return export_xlsx(filters, table_columns, qs)

    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(filters['page'])
    rows = [row_from_doc(doc) for doc in page_obj.object_list]

    qs_params = build_query_string(filters)
    export_url = f'?{qs_params}&export=xlsx' if qs_params else '?export=xlsx'

    tpl_filters = filters_for_template(filters)
    tpl_filters['order_by'] = order_ui
    tpl_filters['name'] = filters.get('name') or ''
    tpl_filters['saved_filter'] = filters.get('saved_filter') or ''
    tpl_filters['phone'] = filters.get('phone') or ''
    tpl_filters['status_id'] = filters.get('status_id')
    tpl_filters['contact_type_id'] = filters.get('contact_type_id')
    tpl_filters['type_id'] = filters.get('type_id')
    tpl_filters['archive'] = filters.get('archive') or ''
    tpl_filters['eco'] = filters.get('eco') or ''
    tpl_filters['is_missed'] = filters.get('is_missed') or ''

    return {
        'type': REPORT_CONFIG['list_type'],
        'report_key': RLK_KEY,
        'report_title': REPORT_CONFIG['title'],
        'report_subtitle': REPORT_CONFIG['subtitle'],
        'user': request.user,
        'filtr': tpl_filters,
        'filters': tpl_filters,
        'totals': totals,
        'paginator': page_obj,
        'page_obj': page_obj,
        'rows': rows,
        'table_columns': table_columns,
        'columns_settings': columns_settings,
        'columns_defaults': list(RLK_DEFAULT_COLUMNS),
        'columns_defaults_json': json.dumps(list(RLK_DEFAULT_COLUMNS)),
        'has_filters': has_active_filters(filters),
        'saved_filters': saved_filters_for_template(
            request.user, RLK_KEY, filters.get('saved_filter'),
        ),
        'units_qs': rlk_units_qs(),
        'statuses_qs': RefStatusRLK.objects.only('id', 'name').order_by('name'),
        'contact_types_qs': RefContactType.objects.only('id', 'name').order_by('name'),
        'types_qs': RefTypeDocRLK.objects.only('id', 'name').order_by('name'),
        'export_url': export_url,
        'query_string': qs_params,
        'list_path': request.path,
    }
