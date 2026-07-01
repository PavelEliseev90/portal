# -*- coding: utf-8 -*-
"""Отчёт «Видение сделки» — этап 1: РЛ trade-in + оценка через RegInteractivOcenkaRLK."""
import datetime as DT
from collections import defaultdict

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Exists, OuterRef, Q, Subquery

from documents.models import DocCarAgreement, DocCarShipment, DocRLK
from prices_car.models import CarCalculations, CarCalculationsDetail
from refs.models import RefStaff, RefTypeReceptionCarsOrganization, RefUnit, RefUnitGroup
from register.models import RegInteractivOcenkaRLK


TRADEIN_RLK_Q = Q(
    Q(type__id=2, unit_dc__buauto=True) |
    Q(type__id=7, eco=True) |
    Q(type__id=1, eco=True) |
    Q(type__id=19, eco=True) |
    Q(eco=True)
)

SOGLASOVANIE_LABELS = dict(CarCalculations.SOGLASOVANIE_STATUS_CHOICES)

KP_MAIN_COLUMN_COUNT = 18


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


def _pick_price(*values):
    for value in values:
        if value not in (None, '', 0):
            return value
    return None


def _op_footing_to_dict(op_rlk):
    archive_name, archive_comment = _parse_reason_archive(op_rlk.reasonArchive)
    unit = op_rlk.unit_dc if op_rlk.unit_dc_id else op_rlk.unit
    return {
        'id': op_rlk.id,
        'number': op_rlk.nomer,
        'uin': op_rlk.uin,
        'date': op_rlk.dataTime,
        'staff_name': op_rlk.staff.name if op_rlk.staff_id else '—',
        'unit_name': unit.name if unit else '—',
        'client_name': op_rlk.clientName or '',
        'archive': op_rlk.archive,
        'archive_name': archive_name,
        'archive_comment': archive_comment,
        'comment_manager': (op_rlk.commentManager or '').strip(),
        'comment_administrator': (op_rlk.commentAdministrator or '').strip(),
        'agreement': None,
        'shipment': None,
        'kp': None,
    }


def _agreement_to_dict(agr):
    return {
        'number': agr.nomer,
        'date': agr.dataTime,
        'active': agr.active,
        'amount': agr.amount,
        'cost_price': agr.cost_price,
        'outlay': agr.outlay,
        'discount_amount': agr.discountAmount,
        'discount_torg': agr.discountAmountTorg,
        'discount_tradein': agr.discountAmountTradeIN,
        'type_sale': agr.typeSale or '',
        'staff_name': agr.staff.name if agr.staff_id else '',
        'client_name': agr.clientName or '',
    }


def _shipment_to_dict(sh):
    return {
        'number': sh.nomer,
        'date': sh.dataTime,
        'active': sh.active,
        'amount': sh.amount,
        'cost_price': sh.cost_price,
        'outlay': sh.outlay,
        'discount_amount': sh.discountAmount,
        'discount_torg': sh.discountAmountTorg,
        'discount_tradein': sh.discountAmountTradeIN,
        'type_sale': sh.typeSale or '',
        'staff_name': sh.staff.name if sh.staff_id else '',
        'client_name': sh.clientName or '',
    }


def _detail_to_dict(detail):
    return {
        'type_id': detail.detail_type_id,
        'type_name': detail.detail_type.name if detail.detail_type_id else '',
        'amount': detail.amount,
        'vp': detail.vp,
        'pocazatel': detail.pocazatel,
        'amount_k': detail.amount_k,
        'success': detail.success,
    }


def _collect_kp_detail_columns(all_ops):
    seen = {}
    for op in all_ops:
        kp = op.get('kp')
        if not kp:
            continue
        for detail in kp.get('details_list', []):
            tid = detail.get('type_id')
            if tid:
                seen[tid] = detail.get('type_name') or ''
    return [
        {'id': tid, 'name': seen[tid]}
        for tid in sorted(seen.keys(), key=lambda i: (seen[i] or '', i))
    ]


def _attach_kp_detail_cells(all_ops, detail_columns):
    col_ids = [col['id'] for col in detail_columns]
    for op in all_ops:
        details_map = {}
        kp = op.get('kp')
        if kp:
            details_map = {d['type_id']: d for d in kp.get('details_list', [])}
        op['kp_detail_cells'] = [details_map.get(tid) for tid in col_ids] if col_ids else []


def _calc_to_dict(calc):
    car_label = ''
    if calc.car_id and calc.car:
        car_label = str(calc.car)
    return {
        'id': calc.id,
        'number': calc.number or '',
        'date': calc.date,
        'date_success': calc.date_success,
        'rejection': calc.rejection or '',
        'amount': calc.amount,
        'kvp': calc.kvp,
        'km_raschet': calc.km_raschet,
        'price': calc.price,
        'discount': calc.discount,
        'custom_opfu': calc.custom_opfu,
        'custom_tradein': calc.custom_tradein,
        'custom_wheels': calc.custom_wheels,
        'custom_grz': calc.custom_grz,
        'custom_work': calc.custom_work,
        'custom_product': calc.custom_product,
        'comment': calc.comment or '',
        'soglasovanie': SOGLASOVANIE_LABELS.get(calc.soglasovanie_status, calc.soglasovanie_status or ''),
        'active': calc.active,
        'inactive_reason': calc.inactive_reason or '',
        'author': calc.author.name if calc.author_id else '',
        'staff': calc.staff.name if calc.staff_id else '',
        'car': car_label,
        'details_list': [],
    }


def _enrich_op_footings(op_footings):
    if not op_footings:
        return op_footings
    op_ids = [op['id'] for op in op_footings]
    op_uins = list({(op.get('uin') or '').strip() for op in op_footings if op.get('uin')})
    op_id_set = set(op_ids)

    agreements_by_rlk = {}
    agreement_q = Q(rlk_id__in=op_ids)
    if op_uins:
        agreement_q |= Q(rlk__uin__in=op_uins)
    for agr in DocCarAgreement.objects.filter(
        agreement_q, active=True,
    ).select_related('staff', 'rlk').order_by('-dataTime', '-id'):
        rid = agr.rlk_id
        if rid and rid in op_id_set and rid not in agreements_by_rlk:
            agreements_by_rlk[rid] = _agreement_to_dict(agr)

    shipments_by_rlk = {}
    shipment_q = Q(rlk_id__in=op_ids)
    if op_uins:
        shipment_q |= Q(rlk__uin__in=op_uins)
    for sh in DocCarShipment.objects.filter(
        shipment_q, active=True,
    ).select_related('staff', 'rlk').order_by('-dataTime', '-id'):
        rid = sh.rlk_id
        if rid and rid in op_id_set and rid not in shipments_by_rlk:
            shipments_by_rlk[rid] = _shipment_to_dict(sh)

    calcs_by_rlk = {}
    calc_q = Q(rlk_id__in=op_ids)
    if op_uins:
        calc_q |= Q(rlk__uin__in=op_uins)
    for calc in CarCalculations.objects.filter(
        calc_q,
    ).select_related('author', 'staff', 'car', 'rlk').order_by('-date', '-id'):
        rid = calc.rlk_id
        if rid and rid in op_id_set and rid not in calcs_by_rlk:
            calcs_by_rlk[rid] = _calc_to_dict(calc)

    calc_ids = [c['id'] for c in calcs_by_rlk.values()]
    details_by_calc = defaultdict(dict)
    if calc_ids:
        for detail in CarCalculationsDetail.objects.filter(
            calculation_id__in=calc_ids,
        ).select_related('detail_type').order_by('detail_type__name'):
            if detail.calculation_id and detail.detail_type_id:
                details_by_calc[detail.calculation_id][detail.detail_type_id] = _detail_to_dict(detail)

    for op in op_footings:
        op_id = op['id']
        op['agreement'] = agreements_by_rlk.get(op_id)
        op['shipment'] = shipments_by_rlk.get(op_id)
        kp = calcs_by_rlk.get(op_id)
        if kp:
            details_map = details_by_calc.get(kp['id'], {})
            kp['details_list'] = sorted(
                details_map.values(),
                key=lambda row: (row.get('type_name') or '', row.get('type_id') or 0),
            )
        op['kp'] = kp
    return op_footings


def _is_korsavto_source(doc):
    source = doc.unit_dc if doc.unit_dc_id else doc.unit
    name = (source.name if source else '') or ''
    return 'корсавто' in name.lower()


def _op_matches_ib_alfa(op_rlk, alfa_required):
    """РЛ ОП подходит, если unit или unit_dc имеет ib.alfa == alfa_required."""
    for unit in (op_rlk.unit, op_rlk.unit_dc):
        if unit is None:
            continue
        ib = getattr(unit, 'ib', None)
        if ib is not None and bool(ib.alfa) == alfa_required:
            return True
    return False


def _resolve_op_footings_batch(docs):
    """Уникальные РЛ ОП по footing__uin. КорсАвто → ib.alfa=False, иначе ib.alfa=True."""
    result = {doc.id: [] for doc in docs}
    trade_uins = list({(doc.uin or '').strip() for doc in docs if (doc.uin or '').strip()})
    if not trade_uins:
        return result

    footing_uins_by_trade = defaultdict(set)
    for trade_uin, footing_uin in DocRLK.objects.filter(
        uin__in=trade_uins,
        footing__isnull=False,
    ).values_list('uin', 'footing__uin').distinct():
        trade_uin = (trade_uin or '').strip()
        footing_uin = (footing_uin or '').strip()
        if trade_uin and footing_uin:
            footing_uins_by_trade[trade_uin].add(footing_uin)

    all_footing_uins = set()
    for footing_uins in footing_uins_by_trade.values():
        all_footing_uins.update(footing_uins)

    op_by_uin = {}
    if all_footing_uins:
        for op in DocRLK.objects.filter(
            uin__in=all_footing_uins,
        ).select_related('unit', 'unit_dc', 'unit__ib', 'unit_dc__ib', 'staff').order_by('-dataTime', '-id'):
            uin = (op.uin or '').strip()
            if uin and uin not in op_by_uin:
                op_by_uin[uin] = op

    for doc in docs:
        trade_uin = (doc.uin or '').strip()
        is_kors = _is_korsavto_source(doc)
        alfa_required = False if is_kors else True
        ops = []
        for footing_uin in sorted(footing_uins_by_trade.get(trade_uin, set())):
            op = op_by_uin.get(footing_uin)
            if op and _op_matches_ib_alfa(op, alfa_required):
                ops.append(_op_footing_to_dict(op))
        ops.sort(key=lambda row: row['date'] or DT.datetime.min, reverse=True)
        result[doc.id] = ops
    return result


def _build_row(doc, op_footings=None):
    archive_name, archive_comment = _parse_reason_archive(doc.reasonArchive)
    mark = doc.est_mark or doc.est_mark_manual or ''
    model = doc.est_model or doc.est_model_manual or ''
    modification = doc.est_modification or doc.est_modification_manual or ''
    car_title, car_mod = _car_title(mark, model, modification)
    source_unit = doc.unit_dc if doc.unit_dc_id else doc.unit
    price_reception = _pick_price(doc.inter_price_reception_sog, doc.inter_price_reception_remote)
    price_sale = _pick_price(doc.inter_price_sale_sog, doc.inter_price_sale_remote)
    cost_prep = doc.inter_amount_podgotovka
    cost_ss = doc.inter_amount_ss
    cost_mcu = doc.inter_amount_mcu
    cost_recovery = doc.inter_amount_recovery
    if (not cost_recovery or cost_recovery == 0) and any(v for v in (cost_prep, cost_ss, cost_mcu) if v):
        cost_recovery = sum(v or 0 for v in (cost_prep, cost_ss, cost_mcu))
    return {
        'rlk_id': doc.id,
        'rlk_number': doc.nomer,
        'rlk_uin': doc.uin,
        'rlk_date': doc.dataTime,
        'date_archive': doc.dateArchive,
        'archive_name': archive_name,
        'archive_comment': archive_comment,
        'interactiv_rlk_id': doc.interactiv_rlk_id or None,
        'estimation_id': doc.inter_estimation_id or None,
        'status_name': doc.inter_status_name or '—',
        'start_estimation': doc.inter_start_estimation,
        'end_estimation': doc.inter_end_estimation,
        'staff_name': doc.inter_staff_name or '—',
        'type_reception_name': doc.inter_type_reception_name or '—',
        'unit_name': doc.unit.name if doc.unit_id else '—',
        'unit_source_name': source_unit.name if source_unit else '—',
        'car_title': car_title or '—',
        'car_modification': car_mod,
        'vin': doc.est_vin or doc.vin_trade_in or '—',
        'year': doc.est_year,
        'run': doc.est_run,
        'has_estimation': bool(doc.inter_estimation_id),
        'has_interactiv_rlk': bool(doc.interactiv_rlk_id),
        'price_reception': price_reception,
        'price_sale': price_sale,
        'price_before_kd': doc.inter_price_before_kd or None,
        'price_after_kd': doc.inter_price_after_kd or None,
        'price_auto_1': doc.inter_price_auto_1 or None,
        'price_auto_2': doc.inter_price_auto_2 or None,
        'price_auto_3': doc.inter_price_auto_3 or None,
        'price_auto_remote': doc.inter_price_auto_remote or None,
        'cost_recovery': cost_recovery or None,
        'cost_podgotovka': cost_prep or None,
        'cost_ss': cost_ss or None,
        'cost_mcu': cost_mcu or None,
        'op_footings': op_footings or [],
    }


def _parse_deal_analysis_filters(request):
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

    if unit_group_ids:
        for group in RefUnitGroup.objects.filter(id__in=unit_group_ids).prefetch_related('units'):
            for unit in group.units.all():
                if unit.id not in unit_ids:
                    unit_ids.append(unit.id)

    return {
        'date_start': date_start,
        'date_end': date_end,
        'unit_ids': unit_ids,
        'unit_group_ids': unit_group_ids,
        'source_unit_ids': source_unit_ids,
        'staff_ids': staff_ids,
        'type_reception_ids': type_reception_ids,
        'reason_archive': reason_archive_filter,
        'status': status_filter,
    }


def _deal_analysis_queryset(filters):
    subquery_inter = RegInteractivOcenkaRLK.objects.filter(rlk__id=OuterRef('id'))

    qs = DocRLK.objects.filter(
        dataTime__gte=filters['date_start'],
        dataTime__lte=filters['date_end'],
    ).filter(TRADEIN_RLK_Q).annotate(
        has_interactiv_rlk=Exists(RegInteractivOcenkaRLK.objects.filter(rlk=OuterRef('id'))),
        has_estimation=Exists(
            RegInteractivOcenkaRLK.objects.filter(rlk=OuterRef('id'), estimation__isnull=False),
        ),
        interactiv_rlk_id=Subquery(subquery_inter.values('id')[:1]),
        inter_estimation_id=Subquery(subquery_inter.values('estimation_id')[:1]),
        inter_status_name=Subquery(subquery_inter.values('status__name')[:1]),
        inter_status_id=Subquery(subquery_inter.values('status__id')[:1]),
        inter_start_estimation=Subquery(subquery_inter.values('estimation__start_estimation')[:1]),
        inter_end_estimation=Subquery(subquery_inter.values('estimation__end_estimation')[:1]),
        inter_staff_name=Subquery(subquery_inter.values('staff_rlk__name')[:1]),
        inter_staff_id=Subquery(subquery_inter.values('staff_rlk__id')[:1]),
        inter_type_reception_name=Subquery(subquery_inter.values('type_reception__name')[:1]),
        inter_type_reception_id=Subquery(subquery_inter.values('type_reception__id')[:1]),
        est_vin=Subquery(subquery_inter.values('estimation__vin')[:1]),
        est_year=Subquery(subquery_inter.values('estimation__year')[:1]),
        est_run=Subquery(subquery_inter.values('estimation__page_salon__run')[:1]),
        est_mark=Subquery(subquery_inter.values('estimation__modification__model__mark__name')[:1]),
        est_model=Subquery(subquery_inter.values('estimation__modification__model__name')[:1]),
        est_modification=Subquery(subquery_inter.values('estimation__modification__name')[:1]),
        est_mark_manual=Subquery(subquery_inter.values('estimation__mark_name')[:1]),
        est_model_manual=Subquery(subquery_inter.values('estimation__model_name')[:1]),
        est_modification_manual=Subquery(subquery_inter.values('estimation__modification_name')[:1]),
        inter_price_reception_sog=Subquery(subquery_inter.values('page_soglasovanie__price_reception')[:1]),
        inter_price_sale_sog=Subquery(subquery_inter.values('page_soglasovanie__price_sale')[:1]),
        inter_price_before_kd=Subquery(subquery_inter.values('page_soglasovanie__price_before_kd')[:1]),
        inter_price_after_kd=Subquery(subquery_inter.values('page_soglasovanie__price_after_kd')[:1]),
        inter_price_auto_1=Subquery(subquery_inter.values('page_soglasovanie__price_auto_1')[:1]),
        inter_price_auto_2=Subquery(subquery_inter.values('page_soglasovanie__price_auto_2')[:1]),
        inter_price_auto_3=Subquery(subquery_inter.values('page_soglasovanie__price_auto_3')[:1]),
        inter_price_reception_remote=Subquery(subquery_inter.values('estimation__page_remote__price_reception')[:1]),
        inter_price_sale_remote=Subquery(subquery_inter.values('estimation__page_remote__price_sale')[:1]),
        inter_price_auto_remote=Subquery(subquery_inter.values('estimation__page_remote__price_auto')[:1]),
        inter_amount_recovery=Subquery(subquery_inter.values('page_soglasovanie__amount_recovery')[:1]),
        inter_amount_podgotovka=Subquery(subquery_inter.values('page_soglasovanie__amount_podgotovka')[:1]),
        inter_amount_ss=Subquery(subquery_inter.values('page_soglasovanie__amount_ss')[:1]),
        inter_amount_mcu=Subquery(subquery_inter.values('page_soglasovanie__amount_mcu')[:1]),
    ).select_related('unit', 'unit_dc').order_by('-dataTime', '-id')

    unit_ids = filters['unit_ids']
    if unit_ids:
        qs = qs.filter(Q(unit__id__in=unit_ids) | Q(unit_dc__id__in=unit_ids))
    source_unit_ids = filters['source_unit_ids']
    if source_unit_ids:
        qs = qs.filter(
            Q(unit_dc__id__in=source_unit_ids) |
            Q(unit__id__in=source_unit_ids, unit_dc__isnull=True),
        )
    staff_ids = filters['staff_ids']
    if staff_ids:
        qs = qs.filter(inter_staff_id__in=staff_ids)
    type_reception_ids = filters['type_reception_ids']
    if type_reception_ids:
        qs = qs.filter(inter_type_reception_id__in=type_reception_ids)
    if filters['reason_archive']:
        qs = qs.filter(reasonArchive__istartswith=filters['reason_archive'])
    if filters['status']:
        qs = qs.filter(inter_status_name=filters['status'])
    return qs


def build_deal_analysis_items(docs):
    if not docs:
        return [], []
    op_map = _resolve_op_footings_batch(docs)
    all_ops = []
    for ops in op_map.values():
        all_ops.extend(ops)
    _enrich_op_footings(all_ops)
    kp_detail_columns = _collect_kp_detail_columns(all_ops)
    _attach_kp_detail_cells(all_ops, kp_detail_columns)
    items = [
        _build_row(doc, op_map.get(doc.id, []))
        for doc in docs
    ]
    return items, kp_detail_columns


def get_deal_analysis_export_data(request):
    filters = _parse_deal_analysis_filters(request)
    docs = list(_deal_analysis_queryset(filters))
    items, kp_detail_columns = build_deal_analysis_items(docs)
    return items, kp_detail_columns, filters


def _filters_to_export_dict(filters):
    return {
        'date_start': filters['date_start'].strftime('%Y-%m-%d'),
        'date_end': filters['date_end'].strftime('%Y-%m-%d'),
        'unit_ids': ','.join(map(str, filters['unit_ids'])) if filters['unit_ids'] else '',
        'unit_ids_list': filters['unit_ids'],
        'unit_group_ids': ','.join(map(str, filters['unit_group_ids'])) if filters['unit_group_ids'] else '',
        'unit_group_ids_list': filters['unit_group_ids'],
        'source_unit_ids': ','.join(map(str, filters['source_unit_ids'])) if filters['source_unit_ids'] else '',
        'source_unit_ids_list': filters['source_unit_ids'],
        'staff_ids': ','.join(map(str, filters['staff_ids'])) if filters['staff_ids'] else '',
        'staff_ids_list': filters['staff_ids'],
        'type_reception_ids': ','.join(map(str, filters['type_reception_ids'])) if filters['type_reception_ids'] else '',
        'type_reception_ids_list': filters['type_reception_ids'],
        'reason_archive': filters['reason_archive'],
        'status': filters['status'],
    }


def get_deal_analysis_context(request):
    filters = _parse_deal_analysis_filters(request)
    date_start = filters['date_start']
    date_end = filters['date_end']

    units = RefUnit.objects.filter(buauto=True, active_eco=True).exclude(name='').order_by('name')
    unit_groups = RefUnitGroup.objects.filter(active=True, bu_auto=True).order_by('name')

    qs = _deal_analysis_queryset(filters)

    reason_stats = defaultdict(int)
    status_stats = defaultdict(int)
    for reason_archive, row_status in qs.values_list('reasonArchive', 'inter_status_name'):
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

    items, kp_detail_columns = build_deal_analysis_items(page_obj.object_list)
    kp_col_count = KP_MAIN_COLUMN_COUNT + len(kp_detail_columns)

    filters_export = _filters_to_export_dict(filters)

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
            'kp_detail_columns': kp_detail_columns,
            'kp_col_count': kp_col_count,
        },
    }


def _fmt_excel_dt(value):
    if not value:
        return ''
    if isinstance(value, DT.datetime):
        return value.strftime('%d.%m.%Y %H:%M')
    if isinstance(value, DT.date):
        return value.strftime('%d.%m.%Y')
    return str(value)


def _fmt_excel_money(value):
    if value in (None, '', 0):
        return ''
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def _join_ops(ops, formatter):
    parts = []
    for op in ops or []:
        text = formatter(op)
        if text not in (None, '', '—'):
            parts.append(str(text))
    return '\n'.join(parts)


def _fmt_op_archive(op):
    lines = []
    if op.get('archive_name'):
        lines.append(op['archive_name'])
    elif op.get('archive'):
        lines.append('В архиве')
    comment = (op.get('archive_comment') or '').strip()
    if comment:
        lines.append(comment)
    return '\n'.join(lines)


def _fmt_agreement(agr):
    if not agr:
        return ''
    lines = [
        f'№ {agr.get("number") or ""}'.strip(),
        _fmt_excel_dt(agr.get('date')),
        f'Сумма: {_fmt_excel_money(agr.get("amount"))}' if agr.get('amount') else '',
        f'Себест.: {_fmt_excel_money(agr.get("cost_price"))}' if agr.get('cost_price') else '',
        f'Расходы: {_fmt_excel_money(agr.get("outlay"))}' if agr.get('outlay') else '',
        f'Скидка: {_fmt_excel_money(agr.get("discount_amount"))}' if agr.get('discount_amount') else '',
        f'Торг: {_fmt_excel_money(agr.get("discount_torg"))}' if agr.get('discount_torg') else '',
        f'Trade-in: {_fmt_excel_money(agr.get("discount_tradein"))}' if agr.get('discount_tradein') else '',
    ]
    return '\n'.join(line for line in lines if line)


def _fmt_shipment(sh):
    if not sh:
        return ''
    lines = [
        f'№ {sh.get("number") or ""}'.strip(),
        _fmt_excel_dt(sh.get('date')),
        f'Сумма: {_fmt_excel_money(sh.get("amount"))}' if sh.get('amount') else '',
        f'Себест.: {_fmt_excel_money(sh.get("cost_price"))}' if sh.get('cost_price') else '',
        f'Расходы: {_fmt_excel_money(sh.get("outlay"))}' if sh.get('outlay') else '',
        f'Скидка: {_fmt_excel_money(sh.get("discount_amount"))}' if sh.get('discount_amount') else '',
    ]
    return '\n'.join(line for line in lines if line)


def _fmt_kp_detail_cell(cell):
    if not cell:
        return ''
    lines = [
        f'Сумма: {_fmt_excel_money(cell.get("amount"))}' if cell.get('amount') else 'Сумма: —',
        f'ВП: {_fmt_excel_money(cell.get("vp"))}' if cell.get('vp') else 'ВП: —',
        f'Показ.: {cell.get("pocazatel") or "—"}',
        f'Сумма K: {_fmt_excel_money(cell.get("amount_k"))}' if cell.get('amount_k') else 'Сумма K: —',
        'Применено' if cell.get('success') else 'Не применено',
    ]
    return '\n'.join(lines)


def _deal_analysis_excel_headers(kp_detail_columns):
    headers = [
        'РЛ trade-in', 'Дата РЛ', 'Причина отказа', 'Коммент. отказа', 'Дата архива',
        'Оценка', 'Статус', 'Оценщик', 'Тип приёма', 'Автомобиль', 'Модификация',
        'VIN', 'Год', 'Пробег',
        'Приём оценщик', 'Продажа оценщик', 'До КД', 'После КД', 'Авторасчёт', 'Затраты ВР',
        'РЛ ОП', 'Дата ОП', 'Менеджер ОП', 'Подразделение ОП', 'Архив ОП',
        'Коммент. менеджера', 'Коммент. администратора', 'Соглашение', 'Отгрузка АМ',
        'КП №', 'КП дата', 'КП итого', 'КП цена авто', 'КП скидка', 'КП trade-in',
        'КП ОПФУ', 'КП колёса', 'КП ГРЗ', 'КП работы', 'КП товары', 'КП КВП', 'КП КМ',
        'КП согласование', 'КП отказ', 'КП автор', 'КП авто', 'КП комментарий',
    ]
    for col in kp_detail_columns:
        headers.append(f'КП {col["name"]}')
    headers.extend(['Подразделение', 'Источник'])
    return headers


def _deal_analysis_item_to_row(item, kp_detail_columns):
    ops = item.get('op_footings') or []
    col_count = len(kp_detail_columns)

    if item.get('has_estimation'):
        estimation_cell = f'#{item.get("estimation_id")}'
    elif item.get('has_interactiv_rlk'):
        estimation_cell = 'без оценки'
    else:
        estimation_cell = 'Нет связи'

    car_title = item.get('car_title') or ''
    if car_title == '—':
        car_title = ''

    auto_lines = []
    if item.get('price_auto_remote'):
        auto_lines.append(f'Д: {item["price_auto_remote"]}')
    if item.get('price_auto_1'):
        auto_lines.append(f'1: {item["price_auto_1"]}')
    if item.get('price_auto_2'):
        auto_lines.append(f'2: {item["price_auto_2"]}')
    if item.get('price_auto_3'):
        auto_lines.append(f'3: {item["price_auto_3"]}')

    cost_lines = []
    if item.get('cost_recovery'):
        cost_lines.append(f'Итого: {item["cost_recovery"]}')
    cost_lines.append(f'Подгот.: {item.get("cost_podgotovka") or "—"}')
    cost_lines.append(f'Слесарка: {item.get("cost_ss") or "—"}')
    cost_lines.append(f'Кузов: {item.get("cost_mcu") or "—"}')

    row = [
        item.get('rlk_number') or '',
        _fmt_excel_dt(item.get('rlk_date')),
        item.get('archive_name') or '',
        item.get('archive_comment') or '',
        _fmt_excel_dt(item.get('date_archive')),
        estimation_cell,
        item.get('status_name') or '',
        item.get('staff_name') or '',
        item.get('type_reception_name') or '',
        car_title,
        item.get('car_modification') or '',
        item.get('vin') or '',
        item.get('year') or '',
        item.get('run') or '',
        _fmt_excel_money(item.get('price_reception')),
        _fmt_excel_money(item.get('price_sale')),
        _fmt_excel_money(item.get('price_before_kd')),
        _fmt_excel_money(item.get('price_after_kd')),
        '\n'.join(auto_lines),
        '\n'.join(cost_lines),
        _join_ops(ops, lambda op: f'{op.get("number") or ""}\nid {op.get("id")}'),
        _join_ops(ops, lambda op: _fmt_excel_dt(op.get('date'))),
        _join_ops(ops, lambda op: op.get('staff_name') or ''),
        _join_ops(ops, lambda op: op.get('unit_name') or ''),
        _join_ops(ops, _fmt_op_archive),
        _join_ops(ops, lambda op: op.get('comment_manager') or ''),
        _join_ops(ops, lambda op: op.get('comment_administrator') or ''),
        _join_ops(ops, lambda op: _fmt_agreement(op.get('agreement'))),
        _join_ops(ops, lambda op: _fmt_shipment(op.get('shipment'))),
        _join_ops(ops, lambda op: (
            f'{op["kp"].get("number") or "—"}\nid {op["kp"].get("id")}' if op.get('kp') else ''
        )),
        _join_ops(ops, lambda op: _fmt_excel_dt(op['kp'].get('date')) if op.get('kp') else ''),
        _join_ops(ops, lambda op: _fmt_excel_money(op['kp'].get('amount')) if op.get('kp') else ''),
        _join_ops(ops, lambda op: _fmt_excel_money(op['kp'].get('price')) if op.get('kp') else ''),
        _join_ops(ops, lambda op: _fmt_excel_money(op['kp'].get('discount')) if op.get('kp') else ''),
        _join_ops(ops, lambda op: _fmt_excel_money(op['kp'].get('custom_tradein')) if op.get('kp') else ''),
        _join_ops(ops, lambda op: _fmt_excel_money(op['kp'].get('custom_opfu')) if op.get('kp') else ''),
        _join_ops(ops, lambda op: _fmt_excel_money(op['kp'].get('custom_wheels')) if op.get('kp') else ''),
        _join_ops(ops, lambda op: _fmt_excel_money(op['kp'].get('custom_grz')) if op.get('kp') else ''),
        _join_ops(ops, lambda op: _fmt_excel_money(op['kp'].get('custom_work')) if op.get('kp') else ''),
        _join_ops(ops, lambda op: _fmt_excel_money(op['kp'].get('custom_product')) if op.get('kp') else ''),
        _join_ops(ops, lambda op: op['kp'].get('kvp') if op.get('kp') and op['kp'].get('kvp') is not None else ''),
        _join_ops(ops, lambda op: op['kp'].get('km_raschet') if op.get('kp') and op['kp'].get('km_raschet') is not None else ''),
        _join_ops(ops, lambda op: op['kp'].get('soglasovanie') or '' if op.get('kp') else ''),
        _join_ops(ops, lambda op: op['kp'].get('rejection') or '' if op.get('kp') else ''),
        _join_ops(ops, lambda op: op['kp'].get('author') or '' if op.get('kp') else ''),
        _join_ops(ops, lambda op: op['kp'].get('car') or '' if op.get('kp') else ''),
        _join_ops(ops, lambda op: op['kp'].get('comment') or '' if op.get('kp') else ''),
    ]

    for col_idx in range(col_count):
        row.append(_join_ops(
            ops,
            lambda op, idx=col_idx: _fmt_kp_detail_cell(
                (op.get('kp_detail_cells') or [])[idx]
                if idx < len(op.get('kp_detail_cells') or []) else None
            ),
        ))

    unit_name = item.get('unit_name') or ''
    source_name = item.get('unit_source_name') or ''
    row.extend([
        '' if unit_name == '—' else unit_name,
        '' if source_name == '—' else source_name,
    ])
    return row


def build_deal_analysis_workbook(items, kp_detail_columns):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font

    wb = Workbook()
    ws = wb.active
    ws.title = 'Видение сделки'
    headers = _deal_analysis_excel_headers(kp_detail_columns)
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for item in items:
        ws.append(_deal_analysis_item_to_row(item, kp_detail_columns))

    for row in ws.iter_rows(min_row=2):
        for cell in row:
            if isinstance(cell.value, str) and '\n' in cell.value:
                cell.alignment = Alignment(wrap_text=True, vertical='top')
    return wb
