# -*- coding: utf-8 -*-
"""Excel-выгрузка отчётов ОП АСП."""
from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from typing import Any, Iterable

from django.http import HttpResponse
from django.utils import timezone

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
    stamp = timezone.localtime().strftime('%Y%m%d_%H%M')
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
    ws.append(['Сформировано', timezone.localtime().strftime('%d.%m.%Y %H:%M')])
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


def export_stock_xlsx(get) -> HttpResponse:
    from openpyxl import Workbook

    from asp.report_common import aggregate_groups, aggregate_totals, parse_common_filters
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
                [g['label'], g['count'], g['price'], g['cost_price'], g['outlay'], g['margin'], g['days_in_stok']]
                for g in groups
            ),
        )

    values = list(
        qs.order_by('unit__name', '-days_in_stok', 'mark', 'model')
        .values(*DETAIL_VALUES)[:EXCEL_ROW_LIMIT]
    )
    rows = [_car_row_from_values(v) for v in values]
    ws = wb.create_sheet('Детали')
    _append_rows(
        ws,
        [
            'Подразделение', 'Марка', 'Модель', 'Год', 'VIN', 'Пробег', 'Статус',
            'Дней', 'Оценщик', 'Цена', 'Себест.', 'Расходы', 'Маржа', 'БЦП',
            'Тип приёма', 'Тип продажи', 'Склад', 'Этап', 'Категория',
        ],
        (
            [
                r['unit_name'], r['mark'], r['model'], r['year'], r['vin'], r['run'],
                r['status_name'], r['days_in_stok'], r['person_name'], r['price'],
                r['cost_price'], r['outlay'], r['margin'], r['bcp'], r['type_reception'],
                r['type_sale'], r['store_name'], r['stage_price'], r['group_price'],
            ]
            for r in rows
        ),
    )
    return workbook_response(wb, 'asp_stock')


def export_accepted_xlsx(get) -> HttpResponse:
    from openpyxl import Workbook

    from asp.accepted_report import (
        DETAIL_VALUES,
        SUM_MAP,
        _lo_row_from_values,
        filtered_accepted_qs,
    )
    from asp.report_common import aggregate_groups, aggregate_totals, parse_common_filters

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

    values = list(qs.order_by('-dataTime', '-pk').values(*DETAIL_VALUES)[:EXCEL_ROW_LIMIT])
    rows = [_lo_row_from_values(v) for v in values]
    ws = wb.create_sheet('Детали')
    _append_rows(
        ws,
        [
            'Дата', '№ ЛО', 'РЛ', 'Подразделение', 'Марка', 'Модель', 'Год', 'VIN',
            'Госномер', 'Клиент', 'Оценщик', 'Тип приёма', 'Себест.', 'БЦП',
            'Пробег', 'Владельцев', 'Ключей', 'Аукцион',
        ],
        (
            [
                r['date'], r['nomer'], r['rlk_nomer'], r['unit_name'], r['mark'], r['model'],
                r['year'], r['vin'], r['plate'], r['client'], r['person_name'],
                r['type_reception'], r['cost_price'], r['bcp'], r['run'], r['owners'],
                r['keys'], r['auction'],
            ]
            for r in rows
        ),
    )
    return workbook_response(wb, 'asp_accepted')


def export_margin_xlsx(get) -> HttpResponse:
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
            ['Группа', 'Кол-во', 'Продажа', 'Себест.', 'Расходы', 'Маржа', 'КМ факт'],
            (
                [g['label'], g['count'], g['amount'], g['cost_price'], g['outlay'], g['doc_margin'], g['cm_actual']]
                for g in groups
            ),
        )

    values = list(qs.order_by('-dataTime', '-pk').values(*DETAIL_VALUES)[:EXCEL_ROW_LIMIT])
    pbi_map = (
        _load_powerbi_by_vin([v.get('cars__vin') or '' for v in values])
        if include_pbi else {}
    )
    rows = []
    for v in values:
        vin = (v.get('cars__vin') or '').strip().upper()
        rows.append(_shipment_row_from_values(v, pbi_map.get(vin)))

    headers = [
        'Дата', '№ отгрузки', 'Подразделение', 'Марка', 'Модель', 'Год', 'VIN',
        'Клиент', 'Продавец', 'Тип', 'Продажа', 'Себест.', 'Расходы', 'Маржа',
        '№ соглашения', 'КМ факт', 'КМ расчёт',
    ]
    if include_pbi:
        headers += ['БУ кумул.', 'КВП', 'Маржа БУ', 'ВПОПФУ']

    def row_values(r):
        base = [
            r['date'], r['nomer'], r['unit_name'], r['mark'], r['model'], r['year'],
            r['vin'], r['client'], r['person_name'], r['type_sale'], r['amount'],
            r['cost_price'], r['outlay'], r['doc_margin'], r['agreement_nomer'],
            r['cm_actual'] if r['has_cm'] else '', r['cm_est'] if r['has_cm'] else '',
        ]
        if include_pbi:
            base += [
                r['pbi_cum_full'] if r['has_pbi'] else '',
                r['pbi_kvp'] if r['has_pbi'] else '',
                r['pbi_marzhi'] if r['has_pbi'] else '',
                r['pbi_vpopfu'] if r['has_pbi'] else '',
            ]
        return base

    ws = wb.create_sheet('Детали')
    _append_rows(ws, headers, (row_values(r) for r in rows))
    return workbook_response(wb, 'asp_cumulative_margin')
