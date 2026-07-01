# -*- coding: utf-8 -*-
"""Отчёт «видение сделки» на основе витрины TradeInFunnel."""
import datetime as DT
from collections import defaultdict

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q

from analytics.models import TradeInFunnel
from documents.models import DocCarAgreement, DocCarShipment, DocLO, DocRLK
from prices_car.models import CarCalculations
from refs.models import RefStaff, RefTypeReceptionCarsOrganization, RefUnit, RefUnitGroup


DATE_INVALID = DT.datetime(1, 1, 1, 0, 0, 0)

COMPARISON_LABELS = {
    -1: 'Ниже авторасчёта',
    0: 'В коридоре',
    1: 'Выше авторасчёта',
}

SOGLASOVANIE_LABELS = dict(CarCalculations.SOGLASOVANIE_STATUS_CHOICES)


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


def _get_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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


def _fmt_money(value):
    if value is None:
        return '—'
    try:
        return '{:,.0f}'.format(float(value)).replace(',', ' ')
    except (TypeError, ValueError):
        return '—'


def _fmt_dt(value):
    if not value or value == DATE_INVALID:
        return '—'
    try:
        return value.strftime('%d.%m.%Y %H:%M')
    except Exception:
        return '—'


def _loss_stage(row):
    if row.date_reception_success and row.date_reception_success != DATE_INVALID:
        return 'Принят'
    if row.archive_name:
        return row.archive_name
    if row.date_after_success and row.date_after_success != DATE_INVALID:
        return 'После КД — не принят'
    if row.diagostica:
        return 'КД / согласование после КД'
    if row.date_before_success and row.date_before_success != DATE_INVALID:
        return 'До КД'
    if row.remote or (row.date_remote_success and row.date_remote_success != DATE_INVALID):
        return 'Дистанционная оценка'
    if row.date_start_estimation and row.date_start_estimation != DATE_INVALID:
        return 'Старт оценки'
    return row.stage or 'Не определено'


def _tradein_kp_comment(kp_has_tradein, accepted, op_deal):
    if not kp_has_tradein and not accepted:
        return 'В КП trade-in не заложен, авто не принято'
    if kp_has_tradein and accepted:
        return 'Trade-in в КП и приём совпали'
    if kp_has_tradein and not accepted:
        return 'Trade-in в КП, авто не принято'
    if not kp_has_tradein and accepted:
        return 'Принято без trade-in в последнем КП'
    if op_deal and not accepted:
        return 'Сделка ОП есть, trade-in не принят'
    return '—'


def _load_filter_lists(date_start, date_end):
    funnel_period = TradeInFunnel.objects.filter(
        date_start_estimation__gte=date_start,
        date_start_estimation__lte=date_end,
    )
    units = RefUnit.objects.filter(
        buauto=True, active_eco=True,
    ).exclude(name='').order_by('name')
    source_units = RefUnit.objects.filter(
        id__in=funnel_period.exclude(unit_source_id__isnull=True).values_list('unit_source_id', flat=True),
    ).exclude(name='').order_by('name')
    staff_ids = list(
        funnel_period.exclude(staff_id__isnull=True).values_list('staff_id', flat=True).distinct(),
    )
    staffs = RefStaff.objects.filter(id__in=staff_ids).exclude(name='').order_by('name') if staff_ids else RefStaff.objects.none()
    analyst_ids = set()
    for field in ('analyst_remote_id', 'analyst_before_id', 'analyst_after_id'):
        analyst_ids.update(
            funnel_period.exclude(**{field + '__isnull': True}).values_list(field, flat=True),
        )
    analysts = RefStaff.objects.filter(id__in=list(analyst_ids)).exclude(name='').order_by('name') if analyst_ids else RefStaff.objects.none()
    type_reception_ids = list(
        funnel_period.exclude(type_reception_id__isnull=True).values_list('type_reception_id', flat=True).distinct(),
    )
    type_receptions = RefTypeReceptionCarsOrganization.objects.filter(
        id__in=type_reception_ids,
    ).exclude(name='').order_by('name') if type_reception_ids else RefTypeReceptionCarsOrganization.objects.none()
    return units, source_units, staffs, analysts, type_receptions


def _parse_reason_archive(value):
    if not value:
        return '', ''
    parts = str(value).split(':', 1)
    name = parts[0].strip()
    comment = parts[1].strip() if len(parts) > 1 else ''
    return name, comment


def _alfa_unit_ids(unit_ids):
    if not unit_ids:
        return set()
    return set(
        RefUnit.objects.filter(id__in=unit_ids, ib__alfa=True).values_list('id', flat=True),
    )


def _footing_uins_by_trade_uin(trade_uins):
    """trade-in uin -> set(footing uin)."""
    result = defaultdict(set)
    if not trade_uins:
        return result
    for row in DocRLK.objects.filter(uin__in=trade_uins).exclude(footing__isnull=True).select_related('footing'):
        trade_uin = (row.uin or '').strip()
        footing_uin = (row.footing.uin or '').strip() if row.footing else ''
        if trade_uin and footing_uin:
            result[trade_uin].add(footing_uin)
    return result


def _resolve_op_rlks_batch(funnel_list):
    """РЛ ОП: по цепочке footing_uin; для Alfa — eco=False."""
    unit_ids = set()
    for row in funnel_list:
        if row.unit_id:
            unit_ids.add(row.unit_id)
        if row.unit_source_id:
            unit_ids.add(row.unit_source_id)
    alfa_ids = _alfa_unit_ids(unit_ids)

    trade_uins = []
    for row in funnel_list:
        trade_uin = (row.rlk_uin or '').strip()
        if trade_uin:
            trade_uins.append(trade_uin)
    footing_map = _footing_uins_by_trade_uin(trade_uins)

    all_footing_uins = set()
    for row in funnel_list:
        trade_uin = (row.rlk_uin or '').strip()
        footing_uins = footing_map.get(trade_uin, set())
        if row.footing_rlk_uin:
            footing_uins = set(footing_uins)
            footing_uins.add(row.footing_rlk_uin.strip())
        all_footing_uins.update(footing_uins)

    op_by_uin = {}
    op_by_uin_eco_false = {}
    if all_footing_uins:
        for op in DocRLK.objects.filter(uin__in=all_footing_uins).select_related(
            'unit', 'unit_dc', 'staff',
        ).order_by('-dataTime', '-id'):
            uin = (op.uin or '').strip()
            if uin and uin not in op_by_uin:
                op_by_uin[uin] = op
            if uin and not op.eco and uin not in op_by_uin_eco_false:
                op_by_uin_eco_false[uin] = op

    result = {}
    for row in funnel_list:
        trade_uin = (row.rlk_uin or '').strip()
        is_alfa = row.unit_id in alfa_ids or row.unit_source_id in alfa_ids
        footing_uins = list(footing_map.get(trade_uin, set()))
        if row.footing_rlk_uin and row.footing_rlk_uin.strip() not in footing_uins:
            footing_uins.append(row.footing_rlk_uin.strip())

        op_rlk = None
        lookup = op_by_uin_eco_false if is_alfa else op_by_uin
        for fu in footing_uins:
            op_rlk = lookup.get(fu)
            if op_rlk:
                break
        if op_rlk is None and row.footing_rlk_id:
            op_rlk = DocRLK.objects.filter(pk=row.footing_rlk_id).select_related(
                'unit', 'unit_dc', 'staff',
            ).first()
        result[row.rlk_id] = op_rlk
    return result


def _last_calc_map_for_ops(op_rlks):
    """Последнее КП по разрешённому РЛ ОП (rlk_id и rlk__uin)."""
    op_list = [op for op in op_rlks if op]
    if not op_list:
        return {}
    ids = [op.id for op in op_list]
    uins = list({(op.uin or '').strip() for op in op_list if op.uin})
    result = {}
    qs = CarCalculations.objects.filter(
        Q(rlk_id__in=ids) | Q(rlk__uin__in=uins),
    ).select_related('author', 'staff', 'car', 'rlk').order_by('-date', '-id')
    for calc in qs:
        if calc.rlk_id and calc.rlk_id in ids and calc.rlk_id not in result:
            result[calc.rlk_id] = calc
        ruin = (calc.rlk.uin or '').strip() if calc.rlk else ''
        if ruin:
            for op in op_list:
                if (op.uin or '').strip() == ruin and op.id not in result:
                    result[op.id] = calc
    return result


def _op_deal_map(footing_ids):
    agreements = {
        row['rlk_id']: row
        for row in DocCarAgreement.objects.filter(
            rlk_id__in=footing_ids, active=True,
        ).values('rlk_id', 'nomer', 'dataTime')
    }
    shipments = {
        row['rlk_id']: row
        for row in DocCarShipment.objects.filter(
            rlk_id__in=footing_ids, active=True,
        ).values('rlk_id', 'nomer', 'dataTime')
    }
    return agreements, shipments


def _build_row(funnel_row, op_rlk, calc, agreement, shipment, lo_active):
    footing_id = op_rlk.id if op_rlk else (funnel_row.footing_rlk_id or 0)
    footing_number = op_rlk.nomer if op_rlk else funnel_row.footing_rlk_number
    footing_uin = op_rlk.uin if op_rlk else funnel_row.footing_rlk_uin
    op_archive_name, op_archive_comment = _parse_reason_archive(
        op_rlk.reasonArchive if op_rlk else '',
    )
    kp_has_tradein = bool(calc and (calc.custom_tradein or 0) > 0)
    accepted = bool(
        funnel_row.date_reception_success
        and funnel_row.date_reception_success != DATE_INVALID,
    )
    op_deal = bool(agreement or shipment)
    loss_stage = _loss_stage(funnel_row)

    op_deal_text = []
    if agreement:
        op_deal_text.append(
            'Соглашение {} от {}'.format(
                agreement['nomer'],
                agreement['dataTime'].strftime('%d.%m.%Y') if agreement['dataTime'] else '—',
            ),
        )
    if shipment:
        op_deal_text.append(
            'Отгрузка {} от {}'.format(
                shipment['nomer'],
                shipment['dataTime'].strftime('%d.%m.%Y') if shipment['dataTime'] else '—',
            ),
        )

    return {
        'rlk_id': funnel_row.rlk_id,
        'rlk_number': funnel_row.rlk_number,
        'lo_number': funnel_row.lo_number,
        'footing_rlk_id': footing_id,
        'footing_rlk_number': footing_number,
        'footing_rlk_uin': footing_uin,
        'op_archive_name': op_archive_name,
        'op_archive_comment': op_archive_comment,
        'unit_name': funnel_row.unit_name,
        'unit_source_name': funnel_row.unit_source_name,
        'brand': funnel_row.brand,
        'mark_name': funnel_row.mark_name,
        'model_name': funnel_row.model_name,
        'modification_name': funnel_row.modification_name,
        'vin': funnel_row.vin or funnel_row.vin_trade_in,
        'year': funnel_row.year,
        'run': funnel_row.run,
        'stage': funnel_row.stage,
        'loss_stage': loss_stage,
        'archive_name': funnel_row.archive_name,
        'archive_comment': funnel_row.archive_comment,
        'type_reception_name': funnel_row.type_reception_name,
        'staff_name': funnel_row.staff_name,
        'analyst_remote_name': funnel_row.analyst_remote_name,
        'analyst_before_name': funnel_row.analyst_before_name,
        'analyst_after_name': funnel_row.analyst_after_name,
        'date_rlk': funnel_row.date_rlk,
        'date_start_estimation': funnel_row.date_start_estimation,
        'date_remote_success': funnel_row.date_remote_success,
        'date_before_success': funnel_row.date_before_success,
        'date_diagnostic_success': funnel_row.date_diagnostic_success,
        'date_after_success': funnel_row.date_after_success,
        'date_reception_success': funnel_row.date_reception_success,
        'date_archive': funnel_row.date_archive,
        'price_remote': funnel_row.price_remote,
        'price_before': funnel_row.price_before,
        'price_after': funnel_row.price_after,
        'price_auto_remote': funnel_row.price_auto_remote,
        'price_auto_before': funnel_row.price_auto_before,
        'price_auto_after': funnel_row.price_auto_after,
        'price_reception_staff': funnel_row.price_reception_staff,
        'price_sale_staff': funnel_row.price_sale_staff,
        'price_auto_bcp': funnel_row.price_auto_bcp,
        'comparison_remote_type': COMPARISON_LABELS.get(funnel_row.comparison_remote_type, '—'),
        'comparison_before_type': COMPARISON_LABELS.get(funnel_row.comparison_before_type, '—'),
        'comparison_after_type': COMPARISON_LABELS.get(funnel_row.comparison_after_type, '—'),
        'kp_number': calc.number if calc else '',
        'kp_date': calc.date if calc else None,
        'kp_amount': calc.amount if calc else None,
        'kp_tradein': calc.custom_tradein if calc else None,
        'kp_price_car': calc.price if calc else None,
        'kp_discount': calc.discount if calc else None,
        'kp_rejection': calc.rejection if calc else '',
        'kp_soglasovanie': SOGLASOVANIE_LABELS.get(calc.soglasovanie_status, '') if calc else '',
        'kp_active': calc.active if calc else None,
        'kp_author': calc.author.name if calc and calc.author else '',
        'kp_has_tradein': kp_has_tradein,
        'accepted': accepted,
        'lo_active': lo_active,
        'op_deal': op_deal,
        'op_deal_text': '; '.join(op_deal_text) if op_deal_text else '—',
        'tradein_kp_comment': _tradein_kp_comment(kp_has_tradein, accepted, op_deal),
        '_op_deal': op_deal,
        '_kp_has_tradein': kp_has_tradein,
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
    analyst_ids = _parse_multiple_ints(request.GET.get('analyst_ids', ''))
    type_reception_ids = _parse_multiple_ints(request.GET.get('type_reception_ids', ''))

    loss_stage_filter = (request.GET.get('loss_stage') or '').strip()
    op_deal_filter = (request.GET.get('op_deal') or '').strip()
    kp_tradein_filter = (request.GET.get('kp_tradein') or '').strip()
    only_lost = (request.GET.get('only_lost') or '1').strip() != '0'

    units, source_units, staffs, analysts, type_receptions = _load_filter_lists(date_start, date_end)
    unit_groups = RefUnitGroup.objects.filter(active=True, bu_auto=True).order_by('name')

    qs = TradeInFunnel.objects.filter(
        date_start_estimation__isnull=False,
        date_start_estimation__gte=date_start,
        date_start_estimation__lte=date_end,
    ).order_by('-date_start_estimation', '-rlk_id')

    if only_lost:
        qs = qs.filter(
            Q(date_reception_success__isnull=True) | Q(date_reception_success=DATE_INVALID),
        )

    filters = {
        'date_start': date_start.strftime('%Y-%m-%d'),
        'date_end': date_end.strftime('%Y-%m-%d'),
        'unit_ids': unit_ids,
        'unit_group_ids': unit_group_ids,
        'source_unit_ids': source_unit_ids,
        'staff_ids': staff_ids,
        'analyst_ids': analyst_ids,
        'type_reception_ids': type_reception_ids,
        'loss_stage': loss_stage_filter,
        'op_deal': op_deal_filter,
        'kp_tradein': kp_tradein_filter,
        'only_lost': '1' if only_lost else '0',
    }

    if unit_ids:
        qs = qs.filter(unit_id__in=unit_ids)
    if source_unit_ids:
        qs = qs.filter(unit_source_id__in=source_unit_ids)
    if staff_ids:
        qs = qs.filter(staff_id__in=staff_ids)
    if analyst_ids:
        aq = Q()
        for aid in analyst_ids:
            aq |= Q(analyst_remote_id=aid) | Q(analyst_before_id=aid) | Q(analyst_after_id=aid)
        qs = qs.filter(aq)
    if type_reception_ids:
        qs = qs.filter(type_reception_id__in=type_reception_ids)
    if unit_group_ids:
        group_unit_ids = []
        for group in RefUnitGroup.objects.filter(id__in=unit_group_ids).prefetch_related('units'):
            group_unit_ids.extend([u.id for u in group.units.all()])
        if group_unit_ids:
            qs = qs.filter(unit_id__in=group_unit_ids)

    funnel_list = list(qs)
    footing_ids = [r.footing_rlk_id for r in funnel_list if r.footing_rlk_id]
    rlk_ids = [r.rlk_id for r in funnel_list]

    calc_map = _last_calc_map(footing_ids)
    agreements, shipments = _op_deal_map(footing_ids)
    lo_map = {
        row['rlk_id']: row['active']
        for row in DocLO.objects.filter(rlk_id__in=rlk_ids).values('rlk_id', 'active')
    }

    items = []
    loss_stage_stats = defaultdict(int)
    for row in funnel_list:
        op_rlk = op_rlk_map.get(row.rlk_id)
        op_id = op_rlk.id if op_rlk else 0
        item = _build_row(
            row,
            op_rlk,
            calc_map.get(op_id),
            agreements.get(op_id),
            shipments.get(op_id),
            lo_map.get(row.rlk_id),
        )
        if loss_stage_filter and item['loss_stage'] != loss_stage_filter:
            continue
        if op_deal_filter == 'yes' and not item['op_deal']:
            continue
        if op_deal_filter == 'no' and item['op_deal']:
            continue
        if kp_tradein_filter == 'yes' and not item['kp_has_tradein']:
            continue
        if kp_tradein_filter == 'no' and item['kp_has_tradein']:
            continue
        loss_stage_stats[item['loss_stage']] += 1
        items.append(item)

    page_num = request.GET.get('page', 1)
    paginator = Paginator(items, 50)
    try:
        page_obj = paginator.page(page_num)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    loss_stage_options = sorted(loss_stage_stats.keys())
    loss_stage_stats_sorted = sorted(loss_stage_stats.items(), key=lambda x: x[1], reverse=True)

    filters_export = {
        'date_start': filters['date_start'],
        'date_end': filters['date_end'],
        'unit_ids': ','.join(map(str, unit_ids)) if unit_ids else '',
        'unit_ids_list': unit_ids,
        'unit_group_ids': ','.join(map(str, unit_group_ids)) if unit_group_ids else '',
        'unit_group_ids_list': unit_group_ids,
        'source_unit_ids': ','.join(map(str, source_unit_ids)) if source_unit_ids else '',
        'source_unit_ids_list': source_unit_ids,
        'staff_ids': ','.join(map(str, staff_ids)) if staff_ids else '',
        'staff_ids_list': staff_ids,
        'analyst_ids': ','.join(map(str, analyst_ids)) if analyst_ids else '',
        'analyst_ids_list': analyst_ids,
        'type_reception_ids': ','.join(map(str, type_reception_ids)) if type_reception_ids else '',
        'type_reception_ids_list': type_reception_ids,
        'loss_stage': loss_stage_filter,
        'op_deal': op_deal_filter,
        'kp_tradein': kp_tradein_filter,
        'only_lost': filters['only_lost'],
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
            'analysts': analysts,
            'type_receptions': type_receptions,
            'items': page_obj.object_list,
            'total_count': paginator.count,
            'page_obj': page_obj,
            'loss_stage_stats': loss_stage_stats_sorted,
            'loss_stage_options': loss_stage_options,
        },
    }
