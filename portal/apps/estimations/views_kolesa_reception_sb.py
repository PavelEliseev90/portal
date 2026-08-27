"""Страница СБ: список приёмок второго комплекта колёс."""
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, IntegerField, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import render

from documents.models import DocLO
from refs.models import RefUnit
from register.models import (
    RegInteractivOcenkaKolesaReception,
    RegRegInteractivOcenkaFilesKolesaReception,
)

from estimations.views_kolesa_reception import (
    _estimation_car_label,
    _parse_date,
)
from estimations.kolesa_reception_events import user_display


def _sb_unit_ids(request):
    """ID подразделений из GET (unit / unit_ids / unit[])."""
    raw = []
    raw.extend(request.GET.getlist('unit'))
    raw.extend(request.GET.getlist('unit_ids'))
    raw.extend(request.GET.getlist('unit[]'))
    ids = []
    seen = set()
    for v in raw:
        s = str(v).strip()
        if not s.isdigit():
            continue
        n = int(s)
        if n in seen:
            continue
        seen.add(n)
        ids.append(n)
    return ids


def _sb_list_queryset(request):
    """Список существующих приёмок 2КК с аннотацией числа фото."""
    photos_sq = (
        RegRegInteractivOcenkaFilesKolesaReception.objects
        .filter(kolesa_reception_id=OuterRef('pk'))
        .order_by()
        .values('kolesa_reception_id')
        .annotate(c=Count('id'))
        .values('c')
    )
    qs = (
        RegInteractivOcenkaKolesaReception.objects
        .select_related(
            'estimation',
            'estimation__status',
            'estimation__rlk',
            'estimation__rlk__unit',
            'estimation__modification',
            'estimation__modification__model',
            'estimation__modification__model__mark',
            'rlk',
            'rlk__unit',
            'user',
            'route_sheet_attached_by',
        )
        .annotate(
            photos_count=Coalesce(
                Subquery(photos_sq, output_field=IntegerField()),
                0,
            )
        )
        .order_by('-date', '-id')
    )

    date_from = _parse_date(request.GET.get('date_from', ''))
    date_to = _parse_date(request.GET.get('date_to', ''))
    unit_ids = _sb_unit_ids(request)
    vin = request.GET.get('vin', '').strip()
    wheels_number = request.GET.get('wheels_number', '').strip()
    photos = request.GET.get('photos', '').strip()
    route_sheet = request.GET.get('route_sheet', '').strip()
    sent = request.GET.get('sent', '').strip()

    if date_from:
        qs = qs.filter(date__date__gte=date_from)
    if date_to:
        qs = qs.filter(date__date__lte=date_to)

    if unit_ids:
        qs = qs.filter(
            Q(rlk__unit_id__in=unit_ids)
            | Q(estimation__rlk__unit_id__in=unit_ids)
        )

    if vin:
        lo_rlk_ids = DocLO.objects.filter(nomer__icontains=vin).values_list('rlk_id', flat=True)
        vin_q = (
            Q(estimation__vin__icontains=vin)
            | Q(estimation__number_body__icontains=vin)
            | Q(rlk__nomer__icontains=vin)
            | Q(estimation__rlk__nomer__icontains=vin)
            | Q(rlk_id__in=lo_rlk_ids)
            | Q(estimation__rlk_id__in=lo_rlk_ids)
        )
        if vin.isdigit():
            vin_q = vin_q | Q(pk=int(vin))
        qs = qs.filter(vin_q)

    if wheels_number:
        qs = qs.filter(send_wheels_ib_number__icontains=wheels_number)

    if photos == '1':
        qs = qs.filter(photos_count__gt=0)
    elif photos == '0':
        qs = qs.filter(photos_count=0)

    if route_sheet == '1':
        qs = qs.filter(route_sheet_attached=True).exclude(route_sheet_file='')
    elif route_sheet == '0':
        qs = qs.filter(Q(route_sheet_attached=False) | Q(route_sheet_file='') | Q(route_sheet_file__isnull=True))

    if sent == '1':
        qs = qs.filter(send_wheels_ib=True)
    elif sent == '0':
        qs = qs.filter(Q(send_wheels_ib=False) | Q(send_wheels_ib__isnull=True))

    return qs


def _lo_numbers_map(receptions):
    """rlk_id -> номер листа оценки (DocLO)."""
    rlk_ids = set()
    for r in receptions:
        if r.rlk_id:
            rlk_ids.add(r.rlk_id)
        if r.estimation_id and r.estimation and r.estimation.rlk_id:
            rlk_ids.add(r.estimation.rlk_id)
    if not rlk_ids:
        return {}
    mapping = {}
    for lo in DocLO.objects.filter(rlk_id__in=rlk_ids).order_by('-dataTime').only('rlk_id', 'nomer'):
        if lo.rlk_id and lo.rlk_id not in mapping and lo.nomer:
            mapping[lo.rlk_id] = lo.nomer
    return mapping


def _build_sb_rows(receptions):
    lo_map = _lo_numbers_map(receptions)
    rows = []
    for r in receptions:
        est = r.estimation
        rlk_id = r.rlk_id or (est.rlk_id if est else None)
        unit_name = '—'
        if r.rlk_id and r.rlk and r.rlk.unit_id:
            unit_name = r.rlk.unit.name
        elif est and est.rlk_id and est.rlk and est.rlk.unit_id:
            unit_name = est.rlk.unit.name

        has_route = bool(r.route_sheet_attached and r.route_sheet_file)
        rows.append({
            'reception': r,
            'car_label': _estimation_car_label(est) if est else '—',
            'vin': (est.vin or est.number_body) if est else '—',
            'lo_number': lo_map.get(rlk_id, '') or '—',
            'unit_name': unit_name,
            'author': user_display(r.user),
            'photos_count': getattr(r, 'photos_count', 0) or 0,
            'route_sheet_attached': has_route,
            'sent': bool(r.send_wheels_ib),
            'wheels_number': r.send_wheels_ib_number or '—',
        })
    return rows


@login_required
def kolesa_reception_sb_list(request):
    """Список приёмок 2КК для службы безопасности (без кнопки «Создать»)."""
    if request.GET.get('export') == 'xlsx':
        return kolesa_reception_sb_export(request)

    qs = _sb_list_queryset(request)
    paginator = Paginator(qs, 40)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    rows = _build_sb_rows(list(page_obj.object_list))
    unit_ids_list = _sb_unit_ids(request)

    params = {
        'page_obj': page_obj,
        'rows': rows,
        'units': RefUnit.objects.filter(name__icontains='КорсАвто').order_by('name'),
        'filters': {
            'date_from': request.GET.get('date_from', ''),
            'date_to': request.GET.get('date_to', ''),
            'unit': [str(v) for v in unit_ids_list],
            'unit_ids_list': unit_ids_list,
            'vin': request.GET.get('vin', ''),
            'wheels_number': request.GET.get('wheels_number', ''),
            'photos': request.GET.get('photos', ''),
            'route_sheet': request.GET.get('route_sheet', ''),
            'sent': request.GET.get('sent', ''),
        },
        'total_count': paginator.count,
    }
    return render(request, 'estimations/kolesa_reception_sb_list.html', {'params': params})


@login_required
def kolesa_reception_sb_export(request):
    """Выгрузка списка приёмок 2КК в Excel для СБ."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    qs = _sb_list_queryset(request)[:5000]
    rows = _build_sb_rows(list(qs))

    wb = Workbook()
    ws = wb.active
    ws.title = '2КК СБ'

    headers = [
        'Дата приёмки',
        'Автомобиль',
        'VIN / кузов',
        '№ листа оценки',
        'Подразделение',
        'Автор',
        'Фото',
        'Маршрутный лист',
        'Отправлен в БУ',
        '№ док. БУ шин',
        'Дата док. БУ',
        'УИН док. БУ',
        'ID приёмки',
    ]
    header_fill = PatternFill('solid', fgColor='002A5A')
    header_font = Font(color='FFFFFF', bold=True)
    for col, title in enumerate(headers, 1):
        cell = ws.cell(1, col, title)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', wrap_text=True)

    for idx, row in enumerate(rows, 2):
        r = row['reception']
        ws.cell(idx, 1, r.date.strftime('%d.%m.%Y %H:%M') if r.date else '')
        ws.cell(idx, 2, row['car_label'])
        ws.cell(idx, 3, row['vin'])
        ws.cell(idx, 4, row['lo_number'] if row['lo_number'] != '—' else '')
        ws.cell(idx, 5, row['unit_name'])
        ws.cell(idx, 6, row['author'])
        ws.cell(idx, 7, row['photos_count'])
        ws.cell(idx, 8, 'Да' if row['route_sheet_attached'] else 'Нет')
        ws.cell(idx, 9, 'Да' if row['sent'] else 'Нет')
        ws.cell(idx, 10, r.send_wheels_ib_number or '')
        ws.cell(idx, 11, r.send_wheels_ib_date.strftime('%d.%m.%Y %H:%M') if r.send_wheels_ib_date else '')
        ws.cell(idx, 12, r.send_wheels_ib_uin or '')
        ws.cell(idx, 13, r.pk)

    for col in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 18

    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="kolesa_reception_sb_{}.xlsx"'.format(stamp)
    wb.save(response)
    return response
