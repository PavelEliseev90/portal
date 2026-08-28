"""Страница СБ: оценки и приёмки второго комплекта колёс."""
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, DateTimeField, Exists, IntegerField, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import render

from documents.models import DocLO
from refs.models import RefUnit
from register.models import (
    RegInteractivOcenka,
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


def _kolesa2_estimation_q():
    """Оценки со вторым комплектом колёс."""
    return Q(page_kolesa__kolesa2_estimation=1) | Q(page_kolesa__kolesa2=True)


def _sb_list_queryset(request):
    """
    Список оценок со 2-м комплектом колёс.
    Приёмка опциональна — строка показывается и без документа оприходования.
    """
    reception_sq = RegInteractivOcenkaKolesaReception.objects.filter(
        estimation_id=OuterRef('pk'),
    )
    photos_sq = (
        RegRegInteractivOcenkaFilesKolesaReception.objects
        .filter(kolesa_reception__estimation_id=OuterRef('pk'))
        .order_by()
        .values('kolesa_reception__estimation_id')
        .annotate(c=Count('id'))
        .values('c')
    )
    sort_date = Coalesce(
        Subquery(reception_sq.values('date')[:1]),
        'end_estimation',
        'start_estimation',
        output_field=DateTimeField(),
    )

    qs = (
        RegInteractivOcenka.objects
        .filter(page_kolesa__isnull=False)
        .filter(_kolesa2_estimation_q())
        .select_related(
            'page_kolesa',
            'status',
            'rlk',
            'rlk__unit',
            'modification',
            'modification__model',
            'modification__model__mark',
        )
        .annotate(
            reception_id=Subquery(reception_sq.values('pk')[:1]),
            photos_count=Coalesce(
                Subquery(photos_sq, output_field=IntegerField()),
                0,
            ),
            sort_date=sort_date,
        )
        .order_by('-sort_date', '-id')
    )

    date_from = _parse_date(request.GET.get('date_from', ''))
    date_to = _parse_date(request.GET.get('date_to', ''))
    unit_ids = _sb_unit_ids(request)
    vin = request.GET.get('vin', '').strip()
    wheels_number = request.GET.get('wheels_number', '').strip()
    photos = request.GET.get('photos', '').strip()
    route_sheet = request.GET.get('route_sheet', '').strip()
    sent = request.GET.get('sent', '').strip()
    has_reception = request.GET.get('has_reception', '').strip()

    if date_from:
        qs = qs.filter(sort_date__date__gte=date_from)
    if date_to:
        qs = qs.filter(sort_date__date__lte=date_to)

    if unit_ids:
        qs = qs.filter(rlk__unit_id__in=unit_ids)

    if vin:
        lo_rlk_ids = DocLO.objects.filter(nomer__icontains=vin).values_list('rlk_id', flat=True)
        vin_q = (
            Q(vin__icontains=vin)
            | Q(number_body__icontains=vin)
            | Q(rlk__nomer__icontains=vin)
            | Q(rlk_id__in=lo_rlk_ids)
        )
        if vin.isdigit():
            n = int(vin)
            vin_q = vin_q | Q(pk=n) | Q(reception_id=n)
        qs = qs.filter(vin_q)

    if wheels_number:
        qs = qs.filter(
            Exists(
                reception_sq.filter(send_wheels_ib_number__icontains=wheels_number),
            ),
        )

    if photos == '1':
        qs = qs.filter(photos_count__gt=0)
    elif photos == '0':
        qs = qs.filter(photos_count=0)

    has_route_sq = reception_sq.filter(route_sheet_attached=True).exclude(
        Q(route_sheet_file='') | Q(route_sheet_file__isnull=True),
    )
    if route_sheet == '1':
        qs = qs.filter(Exists(has_route_sq))
    elif route_sheet == '0':
        qs = qs.filter(~Exists(has_route_sq))

    sent_sq = reception_sq.filter(send_wheels_ib=True)
    if sent == '1':
        qs = qs.filter(Exists(sent_sq))
    elif sent == '0':
        qs = qs.filter(~Exists(sent_sq))

    if has_reception == '1':
        qs = qs.filter(reception_id__isnull=False)
    elif has_reception == '0':
        qs = qs.filter(reception_id__isnull=True)

    return qs


def _lo_numbers_map(estimations):
    """rlk_id -> номер листа оценки (DocLO)."""
    rlk_ids = {est.rlk_id for est in estimations if est.rlk_id}
    if not rlk_ids:
        return {}
    mapping = {}
    for lo in DocLO.objects.filter(rlk_id__in=rlk_ids).order_by('-dataTime').only('rlk_id', 'nomer'):
        if lo.rlk_id and lo.rlk_id not in mapping and lo.nomer:
            mapping[lo.rlk_id] = lo.nomer
    return mapping


def _fetch_receptions_map(estimations):
    """estimation_id -> RegInteractivOcenkaKolesaReception."""
    est_ids = [est.pk for est in estimations]
    if not est_ids:
        return {}
    return {
        r.estimation_id: r
        for r in RegInteractivOcenkaKolesaReception.objects.filter(
            estimation_id__in=est_ids,
        ).select_related('user', 'rlk', 'rlk__unit')
    }


def _row_sort_date(estimation, reception):
    if reception and reception.date:
        return reception.date
    return estimation.end_estimation or estimation.start_estimation


def _build_sb_rows(estimations):
    lo_map = _lo_numbers_map(estimations)
    receptions_map = _fetch_receptions_map(estimations)
    rows = []
    for est in estimations:
        reception = receptions_map.get(est.pk)
        rlk_id = est.rlk_id
        unit_name = '—'
        if est.rlk_id and est.rlk and est.rlk.unit_id:
            unit_name = est.rlk.unit.name

        has_route = bool(
            reception
            and reception.route_sheet_attached
            and reception.route_sheet_file,
        )
        rows.append({
            'estimation': est,
            'reception': reception,
            'has_reception': reception is not None,
            'display_id': reception.pk if reception else est.pk,
            'display_id_label': 'приёмка' if reception else 'оценка',
            'sort_date': _row_sort_date(est, reception),
            'car_label': _estimation_car_label(est),
            'vin': est.vin or est.number_body or '—',
            'lo_number': lo_map.get(rlk_id, '') or '—',
            'unit_name': unit_name,
            'author': user_display(reception.user) if reception and reception.user_id else '—',
            'photos_count': getattr(est, 'photos_count', 0) or 0,
            'route_sheet_attached': has_route,
            'sent': bool(reception and reception.send_wheels_ib),
            'wheels_number': (reception.send_wheels_ib_number if reception else '') or '—',
            'estimation_url': f'/eco/{est.rlk_id}/' if est.rlk_id else '',
            'reception_url': f'/estimations/kolesa-reception/{reception.pk}/' if reception else '',
        })
    return rows


@login_required
def kolesa_reception_sb_list(request):
    """Список 2КК для службы безопасности: оценки со 2-м комплектом и приёмки."""
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
            'has_reception': request.GET.get('has_reception', ''),
        },
        'total_count': paginator.count,
    }
    return render(request, 'estimations/kolesa_reception_sb_list.html', {'params': params})


@login_required
def kolesa_reception_sb_export(request):
    """Выгрузка списка 2КК в Excel для СБ."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    qs = _sb_list_queryset(request)[:5000]
    rows = _build_sb_rows(list(qs))

    wb = Workbook()
    ws = wb.active
    ws.title = '2КК СБ'

    headers = [
        'Дата',
        'Автомобиль',
        'VIN / кузов',
        '№ листа оценки',
        'Подразделение',
        'Автор приёмки',
        'Есть приёмка',
        'Фото',
        'Маршрутный лист',
        'Отправлен в БУ',
        '№ док. БУ шин',
        'Дата док. БУ',
        'УИН док. БУ',
        'ID оценки',
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
        est = row['estimation']
        reception = row['reception']
        sort_dt = row['sort_date']
        ws.cell(idx, 1, sort_dt.strftime('%d.%m.%Y %H:%M') if sort_dt else '')
        ws.cell(idx, 2, row['car_label'])
        ws.cell(idx, 3, row['vin'])
        ws.cell(idx, 4, row['lo_number'] if row['lo_number'] != '—' else '')
        ws.cell(idx, 5, row['unit_name'])
        ws.cell(idx, 6, row['author'] if row['author'] != '—' else '')
        ws.cell(idx, 7, 'Да' if row['has_reception'] else 'Нет')
        ws.cell(idx, 8, row['photos_count'])
        ws.cell(idx, 9, 'Да' if row['route_sheet_attached'] else 'Нет')
        ws.cell(idx, 10, 'Да' if row['sent'] else 'Нет')
        ws.cell(idx, 11, reception.send_wheels_ib_number if reception else '')
        ws.cell(
            idx, 12,
            reception.send_wheels_ib_date.strftime('%d.%m.%Y %H:%M')
            if reception and reception.send_wheels_ib_date else '',
        )
        ws.cell(idx, 13, reception.send_wheels_ib_uin if reception else '')
        ws.cell(idx, 14, est.pk)
        ws.cell(idx, 15, reception.pk if reception else '')

    for col in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 18

    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="kolesa_reception_sb_{}.xlsx"'.format(stamp)
    wb.save(response)
    return response
