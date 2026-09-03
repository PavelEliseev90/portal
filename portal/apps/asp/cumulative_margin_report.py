# -*- coding: utf-8 -*-
"""Отчёт кумулятивной маржи ОП АСП — быстрые агрегаты; PowerBI опционально."""
from __future__ import annotations

from typing import Any

from django.core.paginator import Paginator
from django.db.models import Q

from asp.report_common import (
    GROUP_DETAIL_LIMIT,
    PAGE_SIZE,
    aggregate_groups,
    aggregate_totals,
    allowed_unit_ids,
    details_payload,
    money,
    parse_common_filters,
    report_shell,
    sum_diff,
    sum_money,
)
from documents.models import DocCarShipment

SUM_MAP = {
    'amount': sum_money('amount'),
    'cost_price': sum_money('cost_price'),
    'outlay': sum_money('outlay'),
    'doc_margin': sum_diff('amount', 'cost_price', 'outlay'),
    'cm_actual': sum_money('agreement__cm_actual'),
    'cm_est': sum_money('agreement__cm_est'),
}


def filtered_shipments_qs(filters: dict[str, Any]):
    unit_ids = allowed_unit_ids(filters)
    qs = DocCarShipment.objects.filter(active=True, unit_id__in=unit_ids)

    if filters.get('date_from'):
        qs = qs.filter(dataTime__date__gte=filters['date_from'])
    if filters.get('date_to'):
        qs = qs.filter(dataTime__date__lte=filters['date_to'])
    vin = filters.get('vin') or ''
    if vin:
        qs = qs.filter(Q(cars__vin__icontains=vin) | Q(cars__vin2__icontains=vin))
    mark = filters.get('mark') or ''
    if mark:
        qs = qs.filter(cars__mark__icontains=mark)
    model = filters.get('model') or ''
    if model:
        qs = qs.filter(cars__model__icontains=model)
    type_sale = filters.get('type_sale') or ''
    if type_sale:
        qs = qs.filter(typeSale__icontains=type_sale)
    client = filters.get('client') or ''
    if client:
        qs = qs.filter(Q(clientName__icontains=client) | Q(client__name__icontains=client))
    nomer = filters.get('nomer') or ''
    if nomer:
        qs = qs.filter(nomer__icontains=nomer)
    person = filters.get('person') or ''
    if person:
        qs = qs.filter(staff__name__icontains=person)
    return qs


DETAIL_VALUES = (
    'id', 'nomer', 'dataTime', 'unit_id', 'unit__name', 'cars__vin', 'cars__mark',
    'cars__model', 'cars__year', 'clientName', 'staff_id', 'staff__name', 'typeSale',
    'amount', 'cost_price', 'outlay', 'agreement_id', 'agreement__nomer',
    'agreement__cm_actual', 'agreement__cm_est',
)


def _shipment_row_from_values(row: dict, pbi: dict | None = None) -> dict[str, Any]:
    amount = money(row.get('amount'))
    cost = money(row.get('cost_price'))
    outlay = money(row.get('outlay'))
    pbi = pbi or {}
    has_cm = bool(row.get('agreement_id'))
    return {
        'id': row['id'],
        'nomer': row.get('nomer') or '',
        'date': row.get('dataTime'),
        'unit_id': row.get('unit_id'),
        'unit_name': row.get('unit__name') or '—',
        'vin': row.get('cars__vin') or '',
        'mark': row.get('cars__mark') or '',
        'model': row.get('cars__model') or '',
        'year': row.get('cars__year') or '',
        'client': row.get('clientName') or '',
        'person_id': row.get('staff_id') or 0,
        'person_name': row.get('staff__name') or 'Без продавца',
        'type_sale': row.get('typeSale') or '',
        'amount': amount,
        'cost_price': cost,
        'outlay': outlay,
        'doc_margin': amount - cost - outlay,
        'agreement_nomer': row.get('agreement__nomer') or '',
        'cm_actual': money(row.get('agreement__cm_actual')) if has_cm else 0.0,
        'cm_est': money(row.get('agreement__cm_est')) if has_cm else 0.0,
        'has_cm': has_cm,
        'pbi_cum_full': money(pbi.get('cum_full')),
        'pbi_kvp': money(pbi.get('kvp')),
        'pbi_marzhi': money(pbi.get('summa_marzhi_bez_nds')),
        'pbi_vpopfu': money(pbi.get('vpopfu')),
        'has_pbi': bool(pbi),
    }


def _load_powerbi_by_vin(vins: list[str]) -> dict[str, Any]:
    """Быстрый lookup: один IN по уникальным VIN (без OR-цепочки)."""
    clean = sorted({str(v).strip().upper() for v in vins if v and str(v).strip()})
    if not clean:
        return {}
    try:
        from powerbi.models import CumulativeMarginUS
    except Exception:
        return {}

    result = {}
    chunk = 500
    for i in range(0, len(clean), chunk):
        part = clean[i:i + chunk]
        try:
            qs = (
                CumulativeMarginUS.objects
                .filter(VIN__in=part)
                .order_by('-DataProdazhi', '-pk')
                .values(
                    'VIN', 'SummaMarzhiBezNDS', 'VPOPFU', 'SummaTrejdInPoPlanu',
                    'VPDopy', 'VPKredit', 'KVP',
                )
            )
            for row in qs:
                key = (row.get('VIN') or '').strip().upper()
                if not key or key in result:
                    continue
                m = money(row.get('SummaMarzhiBezNDS'))
                vpopfu = money(row.get('VPOPFU'))
                tradein = money(row.get('SummaTrejdInPoPlanu'))
                dopy = money(row.get('VPDopy'))
                kredit = money(row.get('VPKredit'))
                result[key] = {
                    'summa_marzhi_bez_nds': m,
                    'vpopfu': vpopfu,
                    'cum_full': m + vpopfu + tradein + dopy + kredit,
                    'kvp': money(row.get('KVP')),
                }
        except Exception:
            # PowerBI-таблица может быть недоступна — отчёт без неё
            return result
    return result


def iter_detail_rows(qs, include_pbi=False, limit=GROUP_DETAIL_LIMIT):
    values = list(qs.order_by('-dataTime', '-pk').values(*DETAIL_VALUES)[:limit])
    pbi_map = {}
    if include_pbi:
        pbi_map = _load_powerbi_by_vin([v.get('cars__vin') or '' for v in values])
    rows = []
    for v in values:
        vin = (v.get('cars__vin') or '').strip().upper()
        rows.append(_shipment_row_from_values(v, pbi_map.get(vin)))
    return rows


def build_group_details(get) -> dict[str, Any]:
    filters = parse_common_filters(get, default_month=True)
    qs = filtered_shipments_qs(filters)
    key = filters.get('group_key') or ''
    view = filters.get('view') or 'by_unit'
    try:
        key_int = int(key)
    except (TypeError, ValueError):
        key_int = 0
    if view == 'by_person':
        if key_int:
            qs = qs.filter(staff_id=key_int)
        else:
            qs = qs.filter(staff__isnull=True)
    else:
        if key_int:
            qs = qs.filter(unit_id=key_int)
        else:
            qs = qs.filter(unit__isnull=True)
    return details_payload(iter_detail_rows(qs, include_pbi=filters.get('include_pbi')))


def _enrich_totals(totals: dict) -> dict:
    totals['pbi_cum_full'] = 0
    totals['pbi_kvp'] = 0
    totals['pbi_marzhi'] = 0
    totals['pbi_vpopfu'] = 0
    totals['pbi_count'] = 0
    totals['cm_actual_count'] = 0
    if totals['count']:
        totals['avg_doc_margin'] = totals['doc_margin'] / totals['count']
        totals['margin_pct'] = (totals['doc_margin'] / totals['amount'] * 100) if totals['amount'] else 0
    else:
        totals['avg_doc_margin'] = 0
        totals['margin_pct'] = 0
    return totals


def build_cumulative_margin_report(get) -> dict[str, Any]:
    filters = parse_common_filters(get, default_month=True)
    qs = filtered_shipments_qs(filters)
    totals = _enrich_totals(aggregate_totals(qs, SUM_MAP))

    view = filters['view']
    include_pbi = bool(filters.get('include_pbi'))
    rows = []
    groups = []
    page_obj = None
    paginator = None

    if view == 'main':
        values_qs = qs.order_by('-dataTime', '-pk').values(*DETAIL_VALUES)
        paginator = Paginator(values_qs, PAGE_SIZE)
        page_obj = paginator.get_page(filters['page'])
        page_values = list(page_obj.object_list)
        pbi_map = (
            _load_powerbi_by_vin([v.get('cars__vin') or '' for v in page_values])
            if include_pbi else {}
        )
        rows = []
        for v in page_values:
            vin = (v.get('cars__vin') or '').strip().upper()
            rows.append(_shipment_row_from_values(v, pbi_map.get(vin)))
        truncated = False
    elif view == 'by_unit':
        groups = aggregate_groups(
            qs,
            group_id_field='unit_id',
            group_name_field='unit__name',
            field_map=SUM_MAP,
        )
        for g in groups:
            g['avg_doc_margin'] = (g['doc_margin'] / g['count']) if g['count'] else 0
            g['margin_pct'] = (g['doc_margin'] / g['amount'] * 100) if g['amount'] else 0
        truncated = False
    else:
        groups = aggregate_groups(
            qs,
            group_id_field='staff_id',
            group_name_field='staff__name',
            field_map=SUM_MAP,
        )
        for g in groups:
            if not g['label'] or g['label'] == '—':
                g['label'] = 'Без продавца'
            g['avg_doc_margin'] = (g['doc_margin'] / g['count']) if g['count'] else 0
            g['margin_pct'] = (g['doc_margin'] / g['amount'] * 100) if g['amount'] else 0
        truncated = False

    return report_shell(
        filters=filters,
        totals=totals,
        rows=rows,
        groups=groups,
        view=view,
        title='Кумулятивная маржа — ОП АСП',
        subtitle=(
            'По проведённым отгрузкам. Итоги — агрегаты БД. '
            'PowerBI в строках — по галочке (только текущая страница / группа).'
        ),
        person_label='Продавец',
        page_obj=page_obj,
        paginator=paginator,
        truncated=truncated,
        extra={
            'show_dates': True,
            'show_pbi_toggle': True,
            'type_sales': [],
            'details_url': '/asp/reports/cumulative-margin/',
            'formula_hint': (
                'Маржа = продажа − себестоимость − расходы. '
                'КМ факт — из соглашения. PowerBI включается галочкой в фильтрах.'
            ),
        },
    )
