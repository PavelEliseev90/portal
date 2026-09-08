# -*- coding: utf-8 -*-
"""Настраиваемые столбцы и сортировка отчётов ОП АСП (как calculations_list)."""
from __future__ import annotations

import json
from typing import Any

COLUMNS_COOKIE_PREFIX = 'asp_cols_'
COLUMNS_COOKIE_MAX_AGE = 60 * 60 * 24 * 365
# Смена версии сбрасывает сохранённый набор столбцов (новые колонки по умолчанию).
COLUMNS_COOKIE_VERSION = {
    'margin': 'v4',
    'stock': 'v3',
    'accepted': 'v3',
}

# --- Кумулятивная маржа (отгрузки) ---
MARGIN_DEFAULT_COLUMNS = [
    'date', 'reception_date', 'unit', 'unit_source', 'car', 'vin', 'vin_new',
    'client', 'person', 'appraiser',
    'type_reception', 'vtd', 'group_price', 'stage_price', 'iznos', 'type_sale',
    'amount', 'cost_price', 'outlay', 'doc_margin', 'cm_actual',
    'amount_reward_credit', 'amount_reward_opfu', 'amount_kits',
]
MARGIN_COLUMN_DEFS = {
    'date': {'label': 'Дата / №', 'sortable': True, 'sort_key': 'date', 'num': False},
    'reception_date': {'label': 'Дата приёма', 'sortable': True, 'sort_key': 'reception_date', 'num': False},
    'unit': {'label': 'Подразделение', 'sortable': True, 'sort_key': 'unit', 'num': False},
    'unit_source': {'label': 'ДЦ источник', 'sortable': True, 'sort_key': 'unit_source', 'num': False},
    'car': {'label': 'Авто', 'sortable': True, 'sort_key': 'car', 'num': False},
    'vin': {'label': 'VIN', 'sortable': True, 'sort_key': 'vin', 'num': False},
    'vin_new': {'label': 'VIN нового', 'sortable': True, 'sort_key': 'vin_new', 'num': False},
    'client': {'label': 'Клиент', 'sortable': True, 'sort_key': 'client', 'num': False},
    'person': {'label': 'Продавец', 'sortable': True, 'sort_key': 'person', 'num': False},
    'appraiser': {'label': 'Оценщик', 'sortable': True, 'sort_key': 'appraiser', 'num': False},
    'type_reception': {'label': 'Тип приёма', 'sortable': True, 'sort_key': 'type_reception', 'num': False},
    'vtd': {'label': 'ВТД', 'sortable': True, 'sort_key': 'vtd', 'num': False},
    'group_price': {'label': 'Ценовая группа', 'sortable': False, 'num': False},
    'stage_price': {'label': 'Этап цены', 'sortable': False, 'num': False},
    'iznos': {'label': 'Износ', 'sortable': True, 'sort_key': 'iznos', 'num': False},
    'type_sale': {'label': 'Тип продажи', 'sortable': True, 'sort_key': 'type_sale', 'num': False},
    'amount': {'label': 'Продажа', 'sortable': True, 'sort_key': 'amount', 'num': True},
    'cost_price': {'label': 'Себест.', 'sortable': True, 'sort_key': 'cost_price', 'num': True},
    'outlay': {'label': 'Расходы', 'sortable': True, 'sort_key': 'outlay', 'num': True},
    'doc_margin': {'label': 'Маржа', 'sortable': True, 'sort_key': 'doc_margin', 'num': True, 'signed': True},
    'cm_actual': {'label': 'КМ факт', 'sortable': True, 'sort_key': 'cm_actual', 'num': True},
    'amount_reward_credit': {'label': 'Вознагр. кредит', 'sortable': True, 'sort_key': 'amount_reward_credit', 'num': True},
    'amount_reward_opfu': {'label': 'Вознагр. ОПФУ', 'sortable': True, 'sort_key': 'amount_reward_opfu', 'num': True},
    'amount_kits': {'label': 'Комплекты', 'sortable': True, 'sort_key': 'amount_kits', 'num': True},
    'kolesa2_reception': {'label': 'Приёмка 2КК', 'sortable': True, 'sort_key': 'kolesa2_reception', 'num': False},
    'pbi_cum': {'label': 'БУ кумул.', 'sortable': False, 'num': True},
    'pbi_kvp': {'label': 'КВП', 'sortable': False, 'num': True},
    'agreement': {'label': 'Соглашение', 'sortable': True, 'sort_key': 'agreement', 'num': False},
}
MARGIN_SORT_FIELDS = {
    'date': 'dataTime',
    'reception_date': 'lo__dataTime',
    'unit': 'unit__name',
    'unit_source': 'rlk__unit_dc__name',
    'car': 'cars__mark',
    'vin': 'cars__vin',
    'vin_new': 'lo__vin_new',
    'client': 'clientName',
    'person': 'staff__name',
    'appraiser': 'lo__staff__name',
    'type_reception': 'lo__type_reception__name',
    'vtd': 'lo__type_reception__is_vtd',
    'iznos': 'lo__rlk__reginteractivocenka__iznos',
    'type_sale': 'typeSale',
    'amount': 'amount',
    'cost_price': 'cost_price',
    'outlay': 'outlay',
    'doc_margin': 'amount',  # приближение; точная маржа = amount-cost-outlay
    'cm_actual': 'agreement__cm_actual',
    'amount_reward_credit': 'amount_reward_credit',
    'amount_reward_opfu': 'amount_reward_opfu',
    'amount_kits': 'amount_kits',
    'kolesa2_reception': 'lo__kolesa2_reception',
    'agreement': 'agreement__nomer',
}

# --- Склад ---
STOCK_DEFAULT_COLUMNS = [
    'car', 'vin', 'unit', 'unit_source', 'status', 'type_reception',
    'group_price', 'stage_price', 'iznos',
    'days', 'person', 'price', 'cost_price', 'outlay', 'margin', 'store',
]
STOCK_COLUMN_DEFS = {
    'car': {'label': 'Авто', 'sortable': True, 'sort_key': 'car', 'num': False},
    'vin': {'label': 'VIN', 'sortable': True, 'sort_key': 'vin', 'num': False},
    'year': {'label': 'Год', 'sortable': True, 'sort_key': 'year', 'num': False},
    'unit': {'label': 'Подразделение', 'sortable': True, 'sort_key': 'unit', 'num': False},
    'unit_source': {'label': 'ДЦ источник', 'sortable': True, 'sort_key': 'unit_source', 'num': False},
    'status': {'label': 'Статус', 'sortable': True, 'sort_key': 'status', 'num': False},
    'type_reception': {'label': 'Тип приёма', 'sortable': True, 'sort_key': 'type_reception', 'num': False},
    'group_price': {'label': 'Ценовая группа', 'sortable': True, 'sort_key': 'group_price', 'num': False},
    'stage_price': {'label': 'Этап УС', 'sortable': True, 'sort_key': 'stage_price', 'num': False},
    'iznos': {'label': 'Износ', 'sortable': True, 'sort_key': 'iznos', 'num': False},
    'days': {'label': 'Дней', 'sortable': True, 'sort_key': 'days', 'num': True},
    'person': {'label': 'Оценщик', 'sortable': True, 'sort_key': 'person', 'num': False},
    'price': {'label': 'Цена', 'sortable': True, 'sort_key': 'price', 'num': True},
    'cost_price': {'label': 'Себест.', 'sortable': True, 'sort_key': 'cost_price', 'num': True},
    'outlay': {'label': 'Расходы', 'sortable': True, 'sort_key': 'outlay', 'num': True},
    'margin': {'label': 'Маржа', 'sortable': True, 'sort_key': 'margin', 'num': True, 'signed': True},
    'store': {'label': 'Склад / этап', 'sortable': True, 'sort_key': 'store', 'num': False},
    'run': {'label': 'Пробег', 'sortable': True, 'sort_key': 'run', 'num': True},
    'kolesa2_reception': {'label': 'Приёмка 2КК', 'sortable': True, 'sort_key': 'kolesa2_reception', 'num': False},
}
STOCK_SORT_FIELDS = {
    'car': 'mark',
    'vin': 'vin',
    'year': 'year',
    'unit': 'unit__name',
    'unit_source': 'lo__rlk__unit_dc__name',
    'status': 'status__name',
    'type_reception': 'type_reception__name',
    'group_price': 'group_price__name',
    'stage_price': 'stage_price__name',
    'iznos': 'lo__rlk__reginteractivocenka__iznos',
    'days': 'days_in_stok',
    'person': 'lo__staff__name',
    'price': 'price',
    'cost_price': 'cost_price',
    'outlay': 'outlay',
    'margin': 'price',
    'store': 'store__name',
    'run': 'run',
    'kolesa2_reception': 'lo__kolesa2_reception',
}

# --- Принятые ---
ACCEPTED_DEFAULT_COLUMNS = [
    'date', 'car', 'vin', 'client', 'person', 'type_reception',
    'group_price', 'stage_price', 'iznos', 'kolesa2_reception',
    'cost_price', 'bcp', 'run', 'unit', 'unit_source',
]
ACCEPTED_COLUMN_DEFS = {
    'date': {'label': 'Дата / №', 'sortable': True, 'sort_key': 'date', 'num': False},
    'car': {'label': 'Авто', 'sortable': True, 'sort_key': 'car', 'num': False},
    'vin': {'label': 'VIN', 'sortable': True, 'sort_key': 'vin', 'num': False},
    'client': {'label': 'Клиент', 'sortable': True, 'sort_key': 'client', 'num': False},
    'person': {'label': 'Оценщик', 'sortable': True, 'sort_key': 'person', 'num': False},
    'type_reception': {'label': 'Тип приёма', 'sortable': True, 'sort_key': 'type_reception', 'num': False},
    'group_price': {'label': 'Ценовая группа', 'sortable': False, 'num': False},
    'stage_price': {'label': 'Этап УС', 'sortable': False, 'num': False},
    'iznos': {'label': 'Износ', 'sortable': True, 'sort_key': 'iznos', 'num': False},
    'kolesa2_reception': {'label': 'Приёмка 2КК', 'sortable': True, 'sort_key': 'kolesa2_reception', 'num': False},
    'cost_price': {'label': 'Себест.', 'sortable': True, 'sort_key': 'cost_price', 'num': True},
    'bcp': {'label': 'БЦП', 'sortable': True, 'sort_key': 'bcp', 'num': True},
    'run': {'label': 'Пробег', 'sortable': True, 'sort_key': 'run', 'num': True},
    'unit': {'label': 'Подразделение', 'sortable': True, 'sort_key': 'unit', 'num': False},
    'unit_source': {'label': 'ДЦ источник', 'sortable': True, 'sort_key': 'unit_source', 'num': False},
    'store': {'label': 'Склад', 'sortable': True, 'sort_key': 'store', 'num': False},
    'year': {'label': 'Год', 'sortable': True, 'sort_key': 'year', 'num': False},
    'plate': {'label': 'Госномер', 'sortable': False, 'num': False},
}
ACCEPTED_SORT_FIELDS = {
    'date': 'dataTime',
    'car': 'cars__mark',
    'vin': 'vin',
    'client': 'clientName',
    'person': 'staff__name',
    'type_reception': 'type_reception__name',
    'iznos': 'rlk__reginteractivocenka__iznos',
    'kolesa2_reception': 'kolesa2_reception',
    'cost_price': 'cost_price',
    'bcp': 'bcp',
    'run': 'run',
    'unit': 'unit__name',
    'unit_source': 'rlk__unit_dc__name',
    'store': 'store__name',
    'year': 'year',
}

REPORTS = {
    'margin': {
        'defs': MARGIN_COLUMN_DEFS,
        'defaults': MARGIN_DEFAULT_COLUMNS,
        'sort': MARGIN_SORT_FIELDS,
        'default_order': '-date',
    },
    'stock': {
        'defs': STOCK_COLUMN_DEFS,
        'defaults': STOCK_DEFAULT_COLUMNS,
        'sort': STOCK_SORT_FIELDS,
        'default_order': '-days',
    },
    'accepted': {
        'defs': ACCEPTED_COLUMN_DEFS,
        'defaults': ACCEPTED_DEFAULT_COLUMNS,
        'sort': ACCEPTED_SORT_FIELDS,
        'default_order': '-date',
    },
}


def cookie_name(report_key: str) -> str:
    ver = COLUMNS_COOKIE_VERSION.get(report_key)
    if ver:
        return f'{COLUMNS_COOKIE_PREFIX}{report_key}_{ver}'
    return f'{COLUMNS_COOKIE_PREFIX}{report_key}'


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


def parse_columns_cookie(raw: str | None, report_key: str) -> list[str]:
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


def columns_cookie_value(columns: list[str]) -> str:
    return ','.join(columns)


def get_user_columns(request, report_key: str) -> list[str]:
    return parse_columns_cookie(request.COOKIES.get(cookie_name(report_key)), report_key)


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


def build_table_columns(report_key: str, visible_keys: list[str]) -> list[dict]:
    defs = REPORTS[report_key]['defs']
    columns = []
    for key in visible_keys:
        defn = defs[key]
        columns.append({
            'key': key,
            'label': defn['label'],
            'label_export': defn.get('label_export') or defn['label'],
            'sortable': bool(defn.get('sortable')),
            'sort_key': defn.get('sort_key') or key,
            'num': bool(defn.get('num')),
            'signed': bool(defn.get('signed')),
        })
    return columns


def resolve_order_by(report_key: str, order_by: str | None) -> tuple[str, tuple[str, ...]]:
    """Возвращает (order_by для UI, кортеж ORM order_by)."""
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
    orm = (f'-{field}' if descending else field, '-pk' if not field.endswith('pk') else 'pk')
    # стабильный вторичный ключ
    if orm[1] == '-pk' or orm[0].endswith('pk'):
        pass
    ui = f'-{key}' if descending else key
    return ui, orm


def attach_table_ui(report: dict[str, Any], request, report_key: str) -> dict[str, Any]:
    visible = get_user_columns(request, report_key)
    order_ui = report.get('filters', {}).get('order_by') or REPORTS[report_key]['default_order']
    # Нормализуем order_by в filters для шаблона стрелок
    order_ui, _orm = resolve_order_by(report_key, order_ui)
    if isinstance(report.get('filters'), dict):
        report['filters']['order_by'] = order_ui
    report['report_key'] = report_key
    report['table_columns'] = build_table_columns(report_key, visible)
    report['columns_settings'] = build_columns_settings(report_key, visible)
    report['columns_defaults'] = list(REPORTS[report_key]['defaults'])
    report['columns_defaults_json'] = json.dumps(report['columns_defaults'])
    report['table_columns_json'] = json.dumps([
        {'key': c['key'], 'num': c['num'], 'signed': c['signed']}
        for c in report['table_columns']
    ])
    return report


def export_headers(report_key: str, request) -> list[str]:
    cols = build_table_columns(report_key, get_user_columns(request, report_key))
    return [c['label_export'] for c in cols]


def export_row_values(report_key: str, row: dict, columns: list[dict]) -> list[Any]:
    return [cell_export_value(report_key, row, c['key']) for c in columns]


def cell_export_value(report_key: str, row: dict, key: str):
    if report_key == 'margin':
        mapping = {
            'date': row.get('date'),
            'reception_date': row.get('reception_date'),
            'unit': row.get('unit_name'),
            'unit_source': row.get('unit_source_name'),
            'car': f"{row.get('mark') or ''} {row.get('model') or ''}".strip(),
            'vin': row.get('vin'),
            'vin_new': row.get('vin_new'),
            'client': row.get('client'),
            'person': row.get('person_name'),
            'appraiser': row.get('appraiser_name'),
            'type_reception': row.get('type_reception'),
            'vtd': (
                'Да' if row.get('has_vtd') and row.get('vtd')
                else ('Нет' if row.get('has_vtd') else '')
            ),
            'group_price': row.get('group_price'),
            'stage_price': row.get('stage_price'),
            'iznos': (
                'Да' if row.get('has_iznos') and row.get('iznos')
                else ('Нет' if row.get('has_iznos') else '')
            ),
            'type_sale': row.get('type_sale'),
            'amount': row.get('amount'),
            'cost_price': row.get('cost_price'),
            'outlay': row.get('outlay'),
            'doc_margin': row.get('doc_margin'),
            'cm_actual': row.get('cm_actual') if row.get('has_cm') else '',
            'amount_reward_credit': row.get('amount_reward_credit'),
            'amount_reward_opfu': row.get('amount_reward_opfu'),
            'amount_kits': row.get('amount_kits'),
            'kolesa2_reception': 'Да' if row.get('kolesa2_reception') else 'Нет',
            'pbi_cum': row.get('pbi_cum_full') if row.get('has_pbi') else '',
            'pbi_kvp': row.get('pbi_kvp') if row.get('has_pbi') else '',
            'agreement': row.get('agreement_nomer'),
        }
        if key == 'date':
            d = row.get('date')
            n = row.get('nomer') or ''
            return f"{d} {n}".strip() if d else n
        return mapping.get(key, '')
    if report_key == 'stock':
        mapping = {
            'car': f"{row.get('mark') or ''} {row.get('model') or ''}".strip(),
            'vin': row.get('vin'),
            'year': row.get('year'),
            'unit': row.get('unit_name'),
            'unit_source': row.get('unit_source_name'),
            'status': row.get('status_name'),
            'type_reception': row.get('type_reception'),
            'group_price': row.get('group_price'),
            'stage_price': row.get('stage_price'),
            'iznos': (
                'Да' if row.get('has_iznos') and row.get('iznos')
                else ('Нет' if row.get('has_iznos') else '')
            ),
            'days': row.get('days_in_stok'),
            'person': row.get('person_name'),
            'price': row.get('price'),
            'cost_price': row.get('cost_price'),
            'outlay': row.get('outlay'),
            'margin': row.get('margin'),
            'store': f"{row.get('store_name') or ''} {row.get('stage_price') or ''}".strip(),
            'run': row.get('run'),
            'kolesa2_reception': 'Да' if row.get('kolesa2_reception') else 'Нет',
        }
        return mapping.get(key, '')
    # accepted
    mapping = {
        'date': row.get('date'),
        'car': f"{row.get('mark') or ''} {row.get('model') or ''}".strip(),
        'vin': row.get('vin'),
        'client': row.get('client'),
        'person': row.get('person_name'),
        'type_reception': row.get('type_reception'),
        'group_price': row.get('group_price'),
        'stage_price': row.get('stage_price'),
        'iznos': (
            'Да' if row.get('has_iznos') and row.get('iznos')
            else ('Нет' if row.get('has_iznos') else '')
        ),
        'kolesa2_reception': 'Да' if row.get('kolesa2_reception') else 'Нет',
        'cost_price': row.get('cost_price'),
        'bcp': row.get('bcp'),
        'run': row.get('run'),
        'unit': row.get('unit_name'),
        'unit_source': row.get('unit_source_name'),
        'store': row.get('store_name'),
        'year': row.get('year'),
        'plate': row.get('plate'),
    }
    if key == 'date':
        d = row.get('date')
        n = row.get('nomer') or ''
        return f"{d} {n}".strip() if d else n
    return mapping.get(key, '')
