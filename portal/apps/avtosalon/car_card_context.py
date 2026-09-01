# -*- coding: utf-8 -*-
"""Связанные документы и история статусов для карточки автомобиля на складе."""
from __future__ import annotations

from django.db.models import Q

from documents.models import DocCarAgreement, DocCarShipment


def _pick_label(value):
    if value is None:
        return ''
    if isinstance(value, dict):
        return (value.get('name') or value.get('Name') or '').strip()
    return str(value).strip()


def parse_status_history_from_1c(data) -> list[dict]:
    """История статусов из ответа 1С /car/?uin_lo= (если блок есть в JSON)."""
    if not isinstance(data, dict):
        return []

    for key in (
        'Status_list', 'Statuses', 'Status_history', 'History_status',
        'StatusHistory', 'Status_history_list',
    ):
        block = data.get(key)
        if not block:
            continue
        if isinstance(block, list):
            rows = block
        elif isinstance(block, dict):
            rows = block.get('items') or block.get('Rows') or block.get('rows') or []
        else:
            continue

        result = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            result.append({
                'date': (
                    row.get('Date') or row.get('date') or row.get('Period')
                    or row.get('period') or ''
                ),
                'status': _pick_label(
                    row.get('Status') or row.get('status') or row.get('StatusName')
                ),
                'comment': (row.get('Comment') or row.get('comment') or '').strip(),
            })
        if result:
            return result
    return []


def get_car_interactiv_context(car):
    """Интерактивная оценка и ссылка на ECO."""
    from documents.rlk_estimation import (
        resolve_estimation_for_rlk,
        resolve_interactiv_rlk_for_rlk,
    )

    estimation = None
    interactiv_rlk = None
    eco_url = ''

    lo = getattr(car, 'lo', None)
    rlk = getattr(lo, 'rlk', None) if lo is not None else None
    if rlk is None:
        return {
            'estimation': None,
            'interactiv_rlk': None,
            'eco_url': '',
        }

    vin = (car.vin or '').strip()
    estimation = resolve_estimation_for_rlk(rlk, vin=vin)
    interactiv_rlk = resolve_interactiv_rlk_for_rlk(rlk, vin=vin)

    eco_rlk_id = None
    if interactiv_rlk is not None and interactiv_rlk.rlk_id:
        eco_rlk_id = interactiv_rlk.rlk_id
    elif estimation is not None and estimation.rlk_id:
        eco_rlk_id = estimation.rlk_id
    elif rlk.pk:
        eco_rlk_id = rlk.pk

    if eco_rlk_id:
        eco_url = '/eco/{}/'.format(eco_rlk_id)

    return {
        'estimation': estimation,
        'interactiv_rlk': interactiv_rlk,
        'eco_url': eco_url,
    }


def get_car_agreements(car):
    if not getattr(car, 'lo_id', None):
        return []
    return list(
        DocCarAgreement.objects
        .filter(lo=car.lo, active=True)
        .select_related('unit', 'staff', 'rlk')
        .order_by('-dataTime', '-id')
    )


def get_car_shipments(car, agreements=None):
    if agreements is None:
        agreements = get_car_agreements(car)

    qs = (
        DocCarShipment.objects
        .filter(active=True)
        .select_related('unit', 'staff', 'rlk', 'agreement')
    )
    filters = Q()
    if getattr(car, 'lo_id', None):
        filters |= Q(lo=car.lo)
        filters |= Q(agreement__lo=car.lo)
    agreement_ids = [item.pk for item in agreements]
    if agreement_ids:
        filters |= Q(agreement_id__in=agreement_ids)
    if not filters:
        return []

    return list(qs.filter(filters).order_by('-dataTime', '-id').distinct())


def build_car_related_context(car, base1c=None):
    interactiv_ctx = get_car_interactiv_context(car)
    agreements = get_car_agreements(car)
    shipments = get_car_shipments(car, agreements=agreements)
    status_history = parse_status_history_from_1c(base1c or {})

    return {
        **interactiv_ctx,
        'agreements': agreements,
        'shipments': shipments,
        'status_history': status_history,
        'status_history_from_1c': bool(status_history),
        'status_history_stored_in_portal': False,
    }
