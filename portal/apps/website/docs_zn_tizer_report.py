# -*- coding: utf-8 -*-
from __future__ import annotations

import datetime
from typing import Any

from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from portal.apps.documents.models import DocZN, DoсRecomendation
from portal.apps.refs.models import RefUnit, RefUnitGroup


def parse_report_dates(date_start_str: str, date_end_str: str):
    """
    Разбирает даты периода фильтрации.
    По умолчанию: date_start — 1 число текущего месяца,
                  date_end   — текущий день (или последний день месяца).
    Для фильтрации date_end_dt берётся до конца суток 23:59:59.
    """
    now = datetime.datetime.now()
    today = now.date()

    if date_start_str:
        try:
            date_start_d = datetime.datetime.strptime(date_start_str.strip(), '%Y-%m-%d').date()
        except ValueError:
            date_start_d = today.replace(day=1)
    else:
        date_start_d = today.replace(day=1)

    if date_end_str:
        try:
            date_end_d = datetime.datetime.strptime(date_end_str.strip(), '%Y-%m-%d').date()
        except ValueError:
            date_end_d = today
    else:
        date_end_d = today

    date_start_dt = datetime.datetime.combine(date_start_d, datetime.time.min)
    date_end_dt = datetime.datetime.combine(date_end_d, datetime.time.max)

    return date_start_d, date_end_d, date_start_dt, date_end_dt


def get_tizer_report_data(
    date_start_dt: datetime.datetime,
    date_end_dt: datetime.datetime,
    unit_group: str = 'yes',
    select_unit_id: str = '',
    select_unit_group_id: str = '',
):
    """
    Выполняет быстрый подсчёт статистики за 2 SQL-запроса с агрегацией.
    """
    filter_unit_id = int(select_unit_id) if select_unit_id and select_unit_id.isdigit() else None
    filter_group_id = int(select_unit_group_id) if select_unit_group_id and select_unit_group_id.isdigit() else None

    # Базовые запросы
    zn_qs = DocZN.objects.filter(
        closed=True,
        typeRemont__tizer=True,
        dataTime__gte=date_start_dt,
        dataTime__lte=date_end_dt,
    )

    rec_qs = DoсRecomendation.objects.filter(
        zn__closed=True,
        zn__dataTime__gte=date_start_dt,
        zn__dataTime__lte=date_end_dt,
    )

    # 1. Агрегация заказ-нарядов по unit_id
    if filter_unit_id and unit_group == 'no':
        zn_qs = zn_qs.filter(unit_id=filter_unit_id)
        rec_qs = rec_qs.filter(zn__unit_id=filter_unit_id)
    elif filter_group_id and unit_group == 'yes':
        group_obj = RefUnitGroup.objects.filter(pk=filter_group_id).prefetch_related('units').first()
        if group_obj:
            g_unit_ids = list(group_obj.units.values_list('id', flat=True))
            zn_qs = zn_qs.filter(unit_id__in=g_unit_ids)
            rec_qs = rec_qs.filter(zn__unit_id__in=g_unit_ids)
        else:
            zn_qs = zn_qs.none()
            rec_qs = rec_qs.none()

    zn_agg = (
        zn_qs.values('unit_id', 'unit__name')
        .annotate(total_zn=Count('id', distinct=True))
    )
    zn_by_unit = {}
    for r in zn_agg:
        u_id = r['unit_id']
        if u_id:
            zn_by_unit[u_id] = {
                'unit_id': u_id,
                'unit_name': r['unit__name'] or f'Подразделение #{u_id}',
                'zn_count_all': r['total_zn'],
            }

    # 2. Агрегация рекомендаций по unit_id
    rec_agg = (
        rec_qs.values('zn__unit_id', 'zn__unit__name')
        .annotate(
            zn_count=Count('zn_id', distinct=True),
            zn_send_count=Count('zn_id', filter=~Q(customerStatus=0), distinct=True),
            zn_success_count=Count('zn_id', filter=Q(customerStatus=2), distinct=True),
            rec_total=Count('id'),
            rec_0=Count('id', filter=Q(customerStatus=0)),
            rec_1=Count('id', filter=Q(customerStatus=1)),
            rec_2=Count('id', filter=Q(customerStatus=2)),
            rec_3=Count('id', filter=Q(customerStatus=3)),
        )
    )
    rec_by_unit = {}
    for r in rec_agg:
        u_id = r['zn__unit_id']
        if u_id:
            rec_by_unit[u_id] = r

    table_data = []

    if unit_group == 'no':
        # Группировка по отдельным подразделениям
        all_unit_ids = set(zn_by_unit.keys()) | set(rec_by_unit.keys())
        for u_id in all_unit_ids:
            zn_info = zn_by_unit.get(u_id, {})
            rec_info = rec_by_unit.get(u_id, {})
            u_name = zn_info.get('unit_name') or rec_info.get('zn__unit__name') or f'Подразделение #{u_id}'

            # Исключаем служебное подразделение
            if not u_name or u_name.strip() == 'ЕЦО ГК':
                continue

            zn_all = zn_info.get('zn_count_all', 0)
            zn_with_rec = rec_info.get('zn_count', 0)
            zn_pct = round(zn_with_rec * 100 / zn_all, 1) if zn_all > 0 else 0

            zn_send = rec_info.get('zn_send_count', 0)
            zn_send_pct = round(zn_send * 100 / zn_all, 1) if zn_all > 0 else 0

            zn_succ = rec_info.get('zn_success_count', 0)
            zn_succ_pct = round(zn_succ * 100 / zn_send, 1) if zn_send > 0 else 0

            rec_total = rec_info.get('rec_total', 0)
            rec_0 = rec_info.get('rec_0', 0)
            rec_1 = rec_info.get('rec_1', 0)
            rec_2 = rec_info.get('rec_2', 0)
            rec_3 = rec_info.get('rec_3', 0)

            table_data.append({
                'unit_id': u_id,
                'unit_name': u_name,
                'unit_info': '',
                'zn_count_all': zn_all,
                'zn_count': zn_with_rec,
                'zn_percent': zn_pct,
                'zn_send_count': zn_send,
                'zn_send_count_sr': zn_send_pct,
                'zn_success_count': zn_succ,
                'zn_success_count_sr': zn_succ_pct,
                'recomendations_total': rec_total,
                'recomendations_0': rec_0,
                'recomendations_1': rec_1,
                'recomendations_2': rec_2,
                'recomendations_3': rec_3,
            })

        table_data.sort(key=lambda x: x['unit_name'])

    else:
        # Группировка по группам подразделений (RefUnitGroup)
        groups_qs = RefUnitGroup.objects.filter(active=True, bu_auto=False).prefetch_related('units')
        if filter_group_id:
            groups_qs = groups_qs.filter(pk=filter_group_id)
        groups_qs = groups_qs.order_by('name_bi')

        for g in groups_qs:
            group_unit_ids = list(g.units.values_list('id', flat=True))
            g_name = g.name_bi or g.name
            if not g_name or g_name.strip() == 'ЕЦО ГК':
                continue

            # Суммируем агрегированные данные по всем подразделениям группы
            zn_all = sum(zn_by_unit.get(uid, {}).get('zn_count_all', 0) for uid in group_unit_ids)
            zn_with_rec = sum(rec_by_unit.get(uid, {}).get('zn_count', 0) for uid in group_unit_ids)
            zn_pct = round(zn_with_rec * 100 / zn_all, 1) if zn_all > 0 else 0

            zn_send = sum(rec_by_unit.get(uid, {}).get('zn_send_count', 0) for uid in group_unit_ids)
            zn_send_pct = round(zn_send * 100 / zn_all, 1) if zn_all > 0 else 0

            zn_succ = sum(rec_by_unit.get(uid, {}).get('zn_success_count', 0) for uid in group_unit_ids)
            zn_succ_pct = round(zn_succ * 100 / zn_send, 1) if zn_send > 0 else 0

            rec_total = sum(rec_by_unit.get(uid, {}).get('rec_total', 0) for uid in group_unit_ids)
            rec_0 = sum(rec_by_unit.get(uid, {}).get('rec_0', 0) for uid in group_unit_ids)
            rec_1 = sum(rec_by_unit.get(uid, {}).get('rec_1', 0) for uid in group_unit_ids)
            rec_2 = sum(rec_by_unit.get(uid, {}).get('rec_2', 0) for uid in group_unit_ids)
            rec_3 = sum(rec_by_unit.get(uid, {}).get('rec_3', 0) for uid in group_unit_ids)

            # Если в группе нет ЗН и нет рекомендаций и был выбран фильтр по группе, всё равно показываем
            if zn_all == 0 and rec_total == 0 and not filter_group_id:
                continue

            table_data.append({
                'unit_id': g.id,
                'unit_name': g_name,
                'unit_info': g.get_info_units(),
                'zn_count_all': zn_all,
                'zn_count': zn_with_rec,
                'zn_percent': zn_pct,
                'zn_send_count': zn_send,
                'zn_send_count_sr': zn_send_pct,
                'zn_success_count': zn_succ,
                'zn_success_count_sr': zn_succ_pct,
                'recomendations_total': rec_total,
                'recomendations_0': rec_0,
                'recomendations_1': rec_1,
                'recomendations_2': rec_2,
                'recomendations_3': rec_3,
            })

    # Общие итоги для KPI метрик
    tot_zn_all = sum(r['zn_count_all'] for r in table_data)
    tot_zn_rec = sum(r['zn_count'] for r in table_data)
    tot_zn_pct = round(tot_zn_rec * 100 / tot_zn_all, 1) if tot_zn_all > 0 else 0

    tot_zn_send = sum(r['zn_send_count'] for r in table_data)
    tot_zn_send_pct = round(tot_zn_send * 100 / tot_zn_all, 1) if tot_zn_all > 0 else 0

    tot_zn_succ = sum(r['zn_success_count'] for r in table_data)
    tot_zn_succ_pct = round(tot_zn_succ * 100 / tot_zn_send, 1) if tot_zn_send > 0 else 0

    tot_rec_total = sum(r['recomendations_total'] for r in table_data)
    tot_rec_0 = sum(r['recomendations_0'] for r in table_data)
    tot_rec_1 = sum(r['recomendations_1'] for r in table_data)
    tot_rec_2 = sum(r['recomendations_2'] for r in table_data)
    tot_rec_3 = sum(r['recomendations_3'] for r in table_data)
    tot_rec_succ_pct = round(tot_rec_2 * 100 / tot_rec_total, 1) if tot_rec_total > 0 else 0

    totals = {
        'zn_count_all': tot_zn_all,
        'zn_count': tot_zn_rec,
        'zn_percent': tot_zn_pct,
        'zn_send_count': tot_zn_send,
        'zn_send_count_sr': tot_zn_send_pct,
        'zn_success_count': tot_zn_succ,
        'zn_success_count_sr': tot_zn_succ_pct,
        'rec_total': tot_rec_total,
        'rec_0': tot_rec_0,
        'rec_1': tot_rec_1,
        'rec_2': tot_rec_2,
        'rec_3': tot_rec_3,
        'rec_succ_pct': tot_rec_succ_pct,
    }

    return table_data, totals


def get_ajax_tizer_details(request):
    """
    Возвращает список рекомендаций для раскрывающейся строки подразделения или группы.
    """
    item_id = request.GET.get('id') or request.GET.get('unit_id') or request.GET.get('unit_group_id')
    group_type = request.GET.get('group_type', 'yes')
    date_start_str = request.GET.get('date_start', '')
    date_end_str = request.GET.get('date_end', '')

    if not item_id:
        return JsonResponse({'ok': False, 'error': 'ID не указан', 'rows': []})

    _, _, date_start_dt, date_end_dt = parse_report_dates(date_start_str, date_end_str)

    recs_qs = DoсRecomendation.objects.filter(
        zn__closed=True,
        zn__dataTime__gte=date_start_dt,
        zn__dataTime__lte=date_end_dt,
    )

    if group_type == 'no':
        recs_qs = recs_qs.filter(zn__unit_id=int(item_id))
    else:
        group = RefUnitGroup.objects.filter(pk=int(item_id)).prefetch_related('units').first()
        if group:
            unit_ids = list(group.units.values_list('id', flat=True))
            recs_qs = recs_qs.filter(zn__unit_id__in=unit_ids)
        else:
            recs_qs = recs_qs.none()

    recs = recs_qs.select_related('zn', 'zn__unit').order_by('dataTime')[:1000]

    rows = []
    for r in recs:
        zn_nomer = r.zn.nomer if r.zn else '—'
        dt_str = r.dataTime.strftime('%d.%m.%Y %H:%M') if r.dataTime else ''
        unit_name = r.zn.unit.name if (r.zn and r.zn.unit) else ''

        rows.append({
            'id': r.id,
            'nomer': zn_nomer,
            'date': dt_str,
            'name': r.name or '',
            'unit_name': unit_name,
            'status': r.customerStatus,
        })

    return JsonResponse({'ok': True, 'rows': rows, 'total': len(rows)})


def export_tizer_report_xlsx(table_data: list, totals: dict, filtr: dict):
    """
    Генерирует Excel-файл выгрузки отчёта по расширениям.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = 'Отчёт по расширениям'

    title_font = Font(name='Calibri', size=14, bold=True, color='002A5A')
    header_font = Font(name='Calibri', size=10, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='002A5A', end_color='002A5A', fill_type='solid')
    total_fill = PatternFill(start_color='E2E8F0', end_color='E2E8F0', fill_type='solid')
    bold_font = Font(name='Calibri', size=10, bold=True)
    regular_font = Font(name='Calibri', size=10)
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1'),
    )

    # Заголовок
    ws.append(['Заказ-наряды: отчёт по расширениям (тизер)'])
    ws['A1'].font = title_font

    period_str = f"Период: с {filtr['date_start']} по {filtr['date_end']} | Группировка: {'Подразделения' if filtr['unit_group'] == 'no' else 'Группы подразделений'}"
    ws.append([period_str])
    ws['A2'].font = Font(name='Calibri', size=10, italic=True, color='64748B')
    ws.append([])

    headers = [
        'Подразделение / Группа',
        'Всего ЗН',
        'Всего ЗН с реком.',
        '% ЗН с реком.',
        'ЗН с отправленными',
        '% отправлено',
        'ЗН с согласованными',
        '% согласовано',
        'Всего рекомендаций',
        'Не активных',
        'На согласовании',
        'Согласовано',
        'Отклонено',
    ]
    ws.append(headers)
    header_row_idx = 4

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=header_row_idx, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = thin_border

    ws.row_dimensions[header_row_idx].height = 28

    # Данные
    for r in table_data:
        row_vals = [
            r['unit_name'],
            r['zn_count_all'],
            r['zn_count'],
            f"{r['zn_percent']}%",
            r['zn_send_count'],
            f"{r['zn_send_count_sr']}%",
            r['zn_success_count'],
            f"{r['zn_success_count_sr']}%",
            r['recomendations_total'],
            r['recomendations_0'],
            r['recomendations_1'],
            r['recomendations_2'],
            r['recomendations_3'],
        ]
        ws.append(row_vals)
        cur_row = ws.max_row
        for col_idx in range(1, len(row_vals) + 1):
            cell = ws.cell(row=cur_row, column=col_idx)
            cell.font = regular_font
            cell.border = thin_border
            if col_idx > 1:
                cell.alignment = Alignment(horizontal='right')

    # Итоговая строка
    total_vals = [
        'ИТОГО',
        totals['zn_count_all'],
        totals['zn_count'],
        f"{totals['zn_percent']}%",
        totals['zn_send_count'],
        f"{totals['zn_send_count_sr']}%",
        totals['zn_success_count'],
        f"{totals['zn_success_count_sr']}%",
        totals['rec_total'],
        totals['rec_0'],
        totals['rec_1'],
        totals['rec_2'],
        totals['rec_3'],
    ]
    ws.append(total_vals)
    tot_row_idx = ws.max_row
    for col_idx in range(1, len(total_vals) + 1):
        cell = ws.cell(row=tot_row_idx, column=col_idx)
        cell.font = bold_font
        cell.fill = total_fill
        cell.border = thin_border
        if col_idx > 1:
            cell.alignment = Alignment(horizontal='right')

    # Автоподбор ширины колонок
    for col_idx in range(1, len(headers) + 1):
        col_letter = get_column_letter(col_idx)
        max_len = 0
        for cell in ws[col_letter]:
            val_str = str(cell.value or '')
            if len(val_str) > max_len and cell.row > 2:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="docs_zn_report_tizer.xlsx"'
    wb.save(response)
    return response
