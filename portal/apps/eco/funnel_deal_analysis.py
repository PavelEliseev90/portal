# -*- coding: utf-8 -*-
"""Отчёт «Видение сделки» — этап 1: РЛ trade-in + оценка через RegInteractivOcenkaRLK."""
import datetime as DT
from collections import defaultdict

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Exists, OuterRef, Q, Subquery

from documents.models import DocRLK
from refs.models import RefStaff, RefTypeReceptionCarsOrganization, RefUnit, RefUnitGroup
from register.models import RegInteractivOcenkaRLK


TRADEIN_RLK_Q = Q(
    Q(type__id=2, unit_dc__buauto=True) |
    Q(type__id=7, eco=True) |
    Q(type__id=1, eco=True) |
    Q(type__id=19, eco=True) |
    Q(eco=True)
)


def _parse_date(value, default, is_end=False):
    if not value:
        return default
    try:
        year, month, day = [int(part) for part in value.split('-')]
        parsed = default.replace(year=year, month=month, day=day)
        if is_end:
            parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=0)
        else:
            parsed = parsed.replace(hour=0, minute=0, second=0, microsecond=0)
        return parsed
    except Exception:
        return default


def _parse_multiple_ints(value):
    if not value:
        return []
    result = []
    for part in str(value).split(','):
        part = part.strip()
        if not part:
            continue
        try:
            result.append(int(part))
        except ValueError:
            continue
    return result


def _parse_reason_archive(value):
    if not value:
        return '', ''
    parts = str(value).split(':', 1)
    name = parts[0].strip()
    comment = parts[1].strip() if len(parts) > 1 else ''
    return name, comment


def _car_title(mark, model, modification):
    parts = [p for p in (mark, model) if p]
    title = ' '.join(parts)
    if modification:
        return title, modification
    return title, ''


def _build_row(doc):
    archive_name, archive_comment = _parse_reason_archive(doc.reasonArchive)
    mark = doc.est_mark or doc.est_mark_manual or ''
    model = doc.est_model or doc.est_model_manual or ''
    modification = doc.est_modification or doc.est_modification_manual or ''
    car_title, car_mod = _car_title(mark, model, modification)
    source_unit = doc.unit_dc if doc.unit_dc_id else doc.unit
    return {
        'rlk_id': doc.id,
        'rlk_number': doc.nomer,
        'rlk_uin': doc.uin,
        'rlk_date': doc.dataTime,
        'date_archive': doc.dateArchive,
        'archive_name': archive_name,
        'archive_comment': archive_comment,
        'interactiv_rlk_id': doc.interactiv_rlk_id or None,
        'estimation_id': doc.estimation_id or None,
        'status_name': doc.status_name or '—',
        'start_estimation': doc.start_estimation,
        'end_estimation': doc.end_estimation,
        'staff_name': doc.staff_name or '—',
        'type_reception_name': doc.type_reception_name or '—',
        'unit_name': doc.unit.name if doc.unit_id else '—',
        'unit_source_name': source_unit.name if source_unit else '—',
        'car_title': car_title or '—',
        'car_modification': car_mod,
        'vin': doc.est_vin or doc.vin_trade_in or '—',
        'year': doc.est_year,
        'run': doc.est_run,
        'has_estimation': bool(doc.estimation_id),
        'has_interactiv_rlk': bool(doc.interactiv_rlk_id),
    }


def get_deal_analysis_context(request):
    now = DT.datetime.now()
    default_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    default_start = default_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    date_start = _parse_date(request.GET.get('date_start', ''), default_start, is_end=False)
    date_end = _parse_date(request.GET.get('date_end', ''), default_end, is_end=True)

    unit_ids = _parse_multiple_ints(request.GET.get('unit_ids', ''))
    unit_group_ids = _parse_multiple_ints(request.GET.get('unit_group_ids', ''))
    source_unit_ids = _parse_multiple_ints(request.GET.get('source_unit_ids', ''))
    staff_ids = _parse_multiple_ints(request.GET.get('staff_ids', ''))
    type_reception_ids = _parse_multiple_ints(request.GET.get('type_reception_ids', ''))
    reason_archive_filter = (request.GET.get('reason_archive') or '').strip()
    status_filter = (request.GET.get('status') or '').strip()

    units = RefUnit.objects.filter(buauto=True, active_eco=True).exclude(name='').order_by('name')
    unit_groups = RefUnitGroup.objects.filter(active=True, bu_auto=True).order_by('name')

    if unit_group_ids:
        for group in RefUnitGroup.objects.filter(id__in=unit_group_ids).prefetch_related('units'):
            for unit in group.units.all():
                if unit.id not in unit_ids:
                    unit_ids.append(unit.id)

    subquery_inter = RegInteractivOcenkaRLK.objects.filter(rlk__id=OuterRef('id'))

    qs = DocRLK.objects.filter(
        dataTime__gte=date_start,
        dataTime__lte=date_end,
    ).filter(TRADEIN_RLK_Q).annotate(
        has_interactiv_rlk=Exists(RegInteractivOcenkaRLK.objects.filter(rlk=OuterRef('id'))),
        has_estimation=Exists(
            RegInteractivOcenkaRLK.objects.filter(rlk=OuterRef('id'), estimation__isnull=False),
        ),
        interactiv_rlk_id=Subquery(subquery_inter.values('id')[:1]),
        estimation_id=Subquery(subquery_inter.values('estimation_id')[:1]),
        status_name=Subquery(subquery_inter.values('status__name')[:1]),
        status_id=Subquery(subquery_inter.values('status__id')[:1]),
        start_estimation=Subquery(subquery_inter.values('estimation__start_estimation')[:1]),
        end_estimation=Subquery(subquery_inter.values('estimation__end_estimation')[:1]),
        staff_name=Subquery(subquery_inter.values('staff_rlk__name')[:1]),
        inter_staff_id=Subquery(subquery_inter.values('staff_rlk__id')[:1]),
        type_reception_name=Subquery(subquery_inter.values('type_reception__name')[:1]),
        type_reception_id=Subquery(subquery_inter.values('type_reception__id')[:1]),
        est_vin=Subquery(subquery_inter.values('estimation__vin')[:1]),
        est_year=Subquery(subquery_inter.values('estimation__year')[:1]),
        est_run=Subquery(subquery_inter.values('estimation__page_salon__run')[:1]),
        est_mark=Subquery(subquery_inter.values('estimation__modification__model__mark__name')[:1]),
        est_model=Subquery(subquery_inter.values('estimation__modification__model__name')[:1]),
        est_modification=Subquery(subquery_inter.values('estimation__modification__name')[:1]),
        est_mark_manual=Subquery(subquery_inter.values('estimation__mark_name')[:1]),
        est_model_manual=Subquery(subquery_inter.values('estimation__model_name')[:1]),
        est_modification_manual=Subquery(subquery_inter.values('estimation__modification_name')[:1]),
    ).select_related('unit', 'unit_dc').order_by('-dataTime', '-id')

    if unit_ids:
        qs = qs.filter(Q(unit__id__in=unit_ids) | Q(unit_dc__id__in=unit_ids))
    if source_unit_ids:
        qs = qs.filter(
            Q(unit_dc__id__in=source_unit_ids) |
            Q(unit__id__in=source_unit_ids, unit_dc__isnull=True),
        )
    if staff_ids:
        qs = qs.filter(inter_staff_id__in=staff_ids)
    if type_reception_ids:
        qs = qs.filter(type_reception_id__in=type_reception_ids)
    if reason_archive_filter:
        qs = qs.filter(reasonArchive__istartswith=reason_archive_filter)
    if status_filter:
        qs = qs.filter(status_name=status_filter)

    reason_stats = defaultdict(int)
    status_stats = defaultdict(int)
    for reason_archive, row_status in qs.values_list('reasonArchive', 'status_name'):
        name, _ = _parse_reason_archive(reason_archive)
        if name:
            reason_stats[name] += 1
        if row_status:
            status_stats[row_status] += 1

    base_docs = DocRLK.objects.filter(
        dataTime__gte=date_start,
        dataTime__lte=date_end,
    ).filter(TRADEIN_RLK_Q)

    inter_base = RegInteractivOcenkaRLK.objects.filter(
        rlk__in=base_docs.values_list('id', flat=True),
    )
    staff_ids_from = list(
        inter_base.exclude(staff_rlk__isnull=True).values_list('staff_rlk_id', flat=True).distinct(),
    )
    staffs = RefStaff.objects.filter(id__in=staff_ids_from).exclude(name='').order_by('name') if staff_ids_from else RefStaff.objects.none()

    type_reception_ids_from = list(
        inter_base.exclude(type_reception__isnull=True).values_list('type_reception_id', flat=True).distinct(),
    )
    type_receptions = RefTypeReceptionCarsOrganization.objects.filter(
        id__in=type_reception_ids_from,
    ).exclude(name='').order_by('name') if type_reception_ids_from else RefTypeReceptionCarsOrganization.objects.none()

    source_unit_ids_from = set()
    source_unit_ids_from.update(
        base_docs.exclude(unit_dc__isnull=True).values_list('unit_dc_id', flat=True),
    )
    source_unit_ids_from.update(
        base_docs.filter(unit_dc__isnull=True).exclude(unit__isnull=True).values_list('unit_id', flat=True),
    )
    source_units = RefUnit.objects.filter(id__in=source_unit_ids_from).exclude(name='').order_by('name')

    reason_options = sorted(reason_stats.keys())
    status_options = sorted(status_stats.keys())
    reason_stats_sorted = sorted(reason_stats.items(), key=lambda x: x[1], reverse=True)
    status_stats_sorted = sorted(status_stats.items(), key=lambda x: x[1], reverse=True)

    page_num = request.GET.get('page', 1)
    paginator = Paginator(qs, 50)
    try:
        page_obj = paginator.page(page_num)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    items = [_build_row(doc) for doc in page_obj.object_list]

    filters_export = {
        'date_start': date_start.strftime('%Y-%m-%d'),
        'date_end': date_end.strftime('%Y-%m-%d'),
        'unit_ids': ','.join(map(str, unit_ids)) if unit_ids else '',
        'unit_ids_list': unit_ids,
        'unit_group_ids': ','.join(map(str, unit_group_ids)) if unit_group_ids else '',
        'unit_group_ids_list': unit_group_ids,
        'source_unit_ids': ','.join(map(str, source_unit_ids)) if source_unit_ids else '',
        'source_unit_ids_list': source_unit_ids,
        'staff_ids': ','.join(map(str, staff_ids)) if staff_ids else '',
        'staff_ids_list': staff_ids,
        'type_reception_ids': ','.join(map(str, type_reception_ids)) if type_reception_ids else '',
        'type_reception_ids_list': type_reception_ids,
        'reason_archive': reason_archive_filter,
        'status': status_filter,
    }

    return {
        'params': {
            'type': 'eco_funnel',
            'nav_selected': 4,
            'filters': filters_export,
            'units': units,
            'unit_groups': unit_groups,
            'source_units': source_units,
            'staffs': staffs,
            'type_receptions': type_receptions,
            'items': items,
            'total_count': paginator.count,
            'page_obj': page_obj,
            'reason_stats': reason_stats_sorted,
            'reason_options': reason_options,
            'status_stats': status_stats_sorted,
            'status_options': status_options,
        },
    }
