# -*- coding: utf-8 -*-
"""Excel-выгрузка отчётов ОП АСП."""
from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from typing import Any, Iterable

from django.http import HttpResponse

from asp.report_common import local_now

EXCEL_ROW_LIMIT = 10000


def _cell(value):
    if value is None:
        return ''
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, date):
        return value
    if isinstance(value, bool):
        return 'да' if value else 'нет'
    return value


def _style_header(ws):
    from openpyxl.styles import Alignment, Font, PatternFill

    fill = PatternFill(start_color='002A5A', end_color='002A5A', fill_type='solid')
    font = Font(bold=True, color='FFFFFF')
    align = Alignment(horizontal='center', vertical='center', wrap_text=True)
    for cell in ws[1]:
        cell.fill = fill
        cell.font = font
        cell.alignment = align
    ws.freeze_panes = 'A2'


def _autosize(ws, max_width: int = 36):
    from openpyxl.utils import get_column_letter

    for col in range(1, ws.max_column + 1):
        letter = get_column_letter(col)
        width = 10
        for cell in ws[letter]:
            if cell.value is None:
                continue
            width = max(width, min(len(str(cell.value)) + 2, max_width))
        ws.column_dimensions[letter].width = width


def _append_rows(ws, headers: list[str], rows: Iterable[Iterable[Any]]):
    ws.append(headers)
    _style_header(ws)
    for row in rows:
        ws.append([_cell(v) for v in row])
    if ws.max_row >= 1 and ws.max_column >= 1:
        ws.auto_filter.ref = ws.dimensions
    _autosize(ws)


def workbook_response(wb, filename_stem: str) -> HttpResponse:
    stamp = local_now().strftime('%Y%m%d_%H%M')
    filename = f'{filename_stem}_{stamp}.xlsx'
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    response = HttpResponse(
        buf.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _fmt_filter_sheet(ws, title: str, filters: dict, totals: dict, extra_lines: list | None = None):
    ws.append(['Отчёт', title])
    ws.append(['Сформировано', local_now().strftime('%d.%m.%Y %H:%M')])
    ws.append(['Режим', filters.get('view') or 'main'])
    if filters.get('date_from') or filters.get('date_to'):
        ws.append([
            'Период',
            f"{filters.get('date_from') or '…'} — {filters.get('date_to') or '…'}",
        ])
    if filters.get('vin'):
        ws.append(['VIN', filters['vin']])
    if filters.get('mark'):
        ws.append(['Марка', filters['mark']])
    if filters.get('model'):
        ws.append(['Модель', filters['model']])
    if filters.get('person'):
        ws.append(['Сотрудник', filters['person']])
    if filters.get('include_pbi'):
        ws.append(['PowerBI', 'да'])
    ws.append([])
    ws.append(['Показатель', 'Значение'])
    for key, val in (totals or {}).items():
        ws.append([key, _cell(val)])
    if extra_lines:
        ws.append([])
        for line in extra_lines:
            ws.append(list(line))
    _autosize(ws, max_width=48)


def export_stock_xlsx(get, request=None) -> HttpResponse:
    from openpyxl import Workbook

    from asp.report_common import aggregate_groups, aggregate_totals, parse_common_filters
    from asp.report_table import (
        STOCK_DEFAULT_COLUMNS,
        build_table_columns,
        export_row_values,
        get_user_columns,
        resolve_order_by,
    )
    from asp.stock_report import (
        DETAIL_VALUES,
        SUM_MAP,
        _car_row_from_values,
        _enrich_totals,
        filtered_stock_qs,
    )

    filters = parse_common_filters(get, default_month=False)
    qs = filtered_stock_qs(filters)
    totals = _enrich_totals(aggregate_totals(qs, SUM_MAP))
    view = filters['view']

    wb = Workbook()
    ws_info = wb.active
    ws_info.title = 'Сводка'
    _fmt_filter_sheet(
        ws_info,
        'Остатки ОП АСП',
        filters,
        {
            'Автомобилей': totals.get('count'),
            'Цена витрины': totals.get('price'),
            'Себестоимость': totals.get('cost_price'),
            'Расходы': totals.get('outlay'),
            'Маржа': totals.get('margin'),
            'Ср. дней': round(totals.get('avg_days') or 0, 1),
        },
        extra_lines=[('Лимит строк деталей', EXCEL_ROW_LIMIT)],
    )

    if view in ('by_unit', 'by_person'):
        if view == 'by_unit':
            groups = aggregate_groups(qs, group_id_field='unit_id', group_name_field='unit__name', field_map=SUM_MAP)
            group_title = 'По подразделениям'
        else:
            groups = aggregate_groups(qs, group_id_field='lo__staff_id', group_name_field='lo__staff__name', field_map=SUM_MAP)
            for g in groups:
                if not g['label'] or g['label'] == '—':
                    g['label'] = 'Без оценщика'
            group_title = 'По оценщикам'
        ws_g = wb.create_sheet(group_title[:31])
        _append_rows(
            ws_g,
            ['Группа', 'Кол-во', 'Цена', 'Себест.', 'Расходы', 'Маржа', 'Дней (сумма)'],
            (
                [
                    g['label'], g['count'], g['price'], g['cost_price'], g['outlay'],
                    g['price'] - g['cost_price'] - g['outlay'], g['days_in_stok'],
                ]
                for g in groups
            ),
        )

    _ui, orm_order = resolve_order_by('stock', filters.get('order_by'))
    values = list(qs.order_by(*orm_order).values(*DETAIL_VALUES)[:EXCEL_ROW_LIMIT])
    rows = [_car_row_from_values(v) for v in values]
    visible = get_user_columns(request, 'stock') if request else list(STOCK_DEFAULT_COLUMNS)
    cols = build_table_columns('stock', visible)
    ws = wb.create_sheet('Детали')
    _append_rows(
        ws,
        [c['label_export'] for c in cols],
        (export_row_values('stock', r, cols) for r in rows),
    )
    return workbook_response(wb, 'asp_stock')


def export_accepted_xlsx(get, request=None) -> HttpResponse:
    from openpyxl import Workbook

    from asp.accepted_report import (
        DETAIL_VALUES,
        SUM_MAP,
        _lo_row_from_values,
        filtered_accepted_qs,
    )
    from asp.report_common import aggregate_groups, aggregate_totals, parse_common_filters
    from asp.report_table import (
        ACCEPTED_DEFAULT_COLUMNS,
        build_table_columns,
        export_row_values,
        get_user_columns,
        resolve_order_by,
    )

    filters = parse_common_filters(get, default_month=True)
    qs = filtered_accepted_qs(filters)
    totals = aggregate_totals(qs, SUM_MAP)
    view = filters['view']

    wb = Workbook()
    ws_info = wb.active
    ws_info.title = 'Сводка'
    _fmt_filter_sheet(
        ws_info,
        'Принятые ОП АСП',
        filters,
        {
            'Принято': totals.get('count'),
            'Себестоимость': totals.get('cost_price'),
            'БЦП': totals.get('bcp'),
            'Пробег (сумма)': totals.get('run'),
        },
        extra_lines=[('Лимит строк деталей', EXCEL_ROW_LIMIT)],
    )

    if view in ('by_unit', 'by_person'):
        if view == 'by_unit':
            groups = aggregate_groups(qs, group_id_field='unit_id', group_name_field='unit__name', field_map=SUM_MAP)
            group_title = 'По подразделениям'
        else:
            groups = aggregate_groups(qs, group_id_field='staff_id', group_name_field='staff__name', field_map=SUM_MAP)
            for g in groups:
                if not g['label'] or g['label'] == '—':
                    g['label'] = 'Без оценщика'
            group_title = 'По оценщикам'
        ws_g = wb.create_sheet(group_title[:31])
        _append_rows(
            ws_g,
            ['Группа', 'Кол-во', 'Себест.', 'БЦП', 'Пробег'],
            ([g['label'], g['count'], g['cost_price'], g['bcp'], g['run']] for g in groups),
        )

    _ui, orm_order = resolve_order_by('accepted', filters.get('order_by'))
    values = list(qs.order_by(*orm_order).values(*DETAIL_VALUES)[:EXCEL_ROW_LIMIT])
    rows = [_lo_row_from_values(v) for v in values]
    visible = get_user_columns(request, 'accepted') if request else list(ACCEPTED_DEFAULT_COLUMNS)
    cols = build_table_columns('accepted', visible)
    ws = wb.create_sheet('Детали')
    _append_rows(
        ws,
        [c['label_export'] for c in cols],
        (export_row_values('accepted', r, cols) for r in rows),
    )
    return workbook_response(wb, 'asp_accepted')


def export_margin_xlsx(get, request=None) -> HttpResponse:
    from openpyxl import Workbook

    from asp.cumulative_margin_report import (
        DETAIL_VALUES,
        SUM_MAP,
        _enrich_totals,
        _load_powerbi_by_vin,
        _shipment_row_from_values,
        filtered_shipments_qs,
    )
    from asp.report_common import aggregate_groups, aggregate_totals, parse_common_filters
    from asp.report_table import (
        MARGIN_DEFAULT_COLUMNS,
        build_table_columns,
        export_row_values,
        get_user_columns,
        resolve_order_by,
    )

    filters = parse_common_filters(get, default_month=True)
    qs = filtered_shipments_qs(filters)
    totals = _enrich_totals(aggregate_totals(qs, SUM_MAP))
    view = filters['view']
    include_pbi = bool(filters.get('include_pbi'))

    wb = Workbook()
    ws_info = wb.active
    ws_info.title = 'Сводка'
    _fmt_filter_sheet(
        ws_info,
        'Кумулятивная маржа ОП АСП',
        filters,
        {
            'Отгрузок': totals.get('count'),
            'Выручка': totals.get('amount'),
            'Себестоимость': totals.get('cost_price'),
            'Расходы': totals.get('outlay'),
            'Маржа отгрузки': totals.get('doc_margin'),
            'КМ факт': totals.get('cm_actual'),
            'Вознагр. кредит': totals.get('amount_reward_credit'),
            'Вознагр. ОПФУ': totals.get('amount_reward_opfu'),
            'Комплекты': totals.get('amount_kits'),
        },
        extra_lines=[
            ('PowerBI в деталях', 'да' if include_pbi else 'нет'),
            ('Лимит строк деталей', EXCEL_ROW_LIMIT),
        ],
    )

    if view in ('by_unit', 'by_person'):
        if view == 'by_unit':
            groups = aggregate_groups(qs, group_id_field='unit_id', group_name_field='unit__name', field_map=SUM_MAP)
            group_title = 'По подразделениям'
        else:
            groups = aggregate_groups(qs, group_id_field='staff_id', group_name_field='staff__name', field_map=SUM_MAP)
            for g in groups:
                if not g['label'] or g['label'] == '—':
                    g['label'] = 'Без продавца'
            group_title = 'По продавцам'
        ws_g = wb.create_sheet(group_title[:31])
        _append_rows(
            ws_g,
            ['Группа', 'Кол-во', 'Продажа', 'Себест.', 'Расходы', 'Маржа', 'КМ факт',
             'Вознагр. кредит', 'Вознагр. ОПФУ', 'Комплекты'],
            (
                [
                    g['label'], g['count'], g['amount'], g['cost_price'], g['outlay'],
                    g['amount'] - g['cost_price'] - g['outlay'], g['cm_actual'],
                    g.get('amount_reward_credit', 0), g.get('amount_reward_opfu', 0),
                    g.get('amount_kits', 0),
                ]
                for g in groups
            ),
        )

    _ui, orm_order = resolve_order_by('margin', filters.get('order_by'))
    values = list(qs.order_by(*orm_order).values(*DETAIL_VALUES)[:EXCEL_ROW_LIMIT])
    pbi_map = (
        _load_powerbi_by_vin([v.get('cars__vin') or '' for v in values])
        if include_pbi else {}
    )
    rows = []
    for v in values:
        vin = (v.get('cars__vin') or '').strip().upper()
        rows.append(_shipment_row_from_values(v, pbi_map.get(vin)))

    visible = get_user_columns(request, 'margin') if request else list(MARGIN_DEFAULT_COLUMNS)
    cols = build_table_columns('margin', visible)
    ws = wb.create_sheet('Детали')
    _append_rows(
        ws,
        [c['label_export'] for c in cols],
        (export_row_values('margin', r, cols) for r in rows),
    )
    return workbook_response(wb, 'asp_cumulative_margin')
