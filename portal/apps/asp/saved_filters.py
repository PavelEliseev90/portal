# -*- coding: utf-8 -*-
"""Сохранённые фильтры отчётов ОП АСП."""
from __future__ import annotations

from typing import Any

from django.db.models import Q
from django.http import QueryDict

from asp.models import ReportSavedFilter
from asp.report_table import REPORTS

# Ключи пресетов вне ASP-отчётов (диспозиция и др.).
EXTRA_SAVED_FILTER_KEYS = frozenset({'disposition'})

ALLOWED_SAVED_FILTER_KEYS = frozenset(REPORTS.keys()) | EXTRA_SAVED_FILTER_KEYS

# Служебные ключи, которые не кладём в пресет и не восстанавливаем из него.
SKIP_KEYS = frozenset({
    'page', 'ajax', 'export', 'group_key', 'saved_filter',
})

# Поля с несколькими значениями (getlist).
MULTI_KEYS = frozenset({
    'unit', 'unit[]', 'unit_ids', 'unit_id',
    'type_reception', 'type_reception[]', 'type_reception_ids', 'type_reception_id',
    'mark', 'mark[]', 'model', 'model[]',
    'body_type', 'body_type[]', 'gear_type', 'gear_type[]',
    'drive_type', 'drive_type[]', 'evaluation_type', 'evaluation_type[]',
    'store', 'store[]',
})


def snapshot_filter_data(get) -> dict[str, Any]:
    """Сериализовать текущий GET в JSON для сохранения."""
    data: dict[str, Any] = {}
    getlist = getattr(get, 'getlist', None)

    # Мультивыбор — канонические ключи unit / type_reception
    if callable(getlist):
        units = []
        for key in ('unit', 'unit[]', 'unit_ids', 'unit_id'):
            units.extend(getlist(key) or [])
        units = [str(v).strip() for v in units if str(v).strip()]
        if units:
            data['unit'] = list(dict.fromkeys(units))

        types = []
        for key in ('type_reception', 'type_reception[]', 'type_reception_ids', 'type_reception_id'):
            types.extend(getlist(key) or [])
        types = [str(v).strip() for v in types if str(v).strip()]
        if types:
            data['type_reception'] = list(dict.fromkeys(types))

    for key in get.keys():
        if key in SKIP_KEYS or key in MULTI_KEYS:
            continue
        val = get.get(key)
        if val in (None, ''):
            continue
        data[key] = str(val).strip()
    return data


def filter_data_to_querydict(filter_data: dict | None, *, extras: dict | None = None) -> QueryDict:
    """JSON пресета → QueryDict."""
    q = QueryDict(mutable=True)
    for key, value in (filter_data or {}).items():
        if key in SKIP_KEYS:
            continue
        if isinstance(value, (list, tuple)):
            for item in value:
                if item not in (None, ''):
                    q.appendlist(key, str(item))
        elif value not in (None, ''):
            q[key] = str(value)
    for key, value in (extras or {}).items():
        if value in (None, ''):
            continue
        if isinstance(value, (list, tuple)):
            for item in value:
                q.appendlist(key, str(item))
        else:
            q[key] = str(value)
    return q


def accessible_saved_filters_qs(user, report_key: str):
    if report_key not in ALLOWED_SAVED_FILTER_KEYS:
        return ReportSavedFilter.objects.none()
    return (
        ReportSavedFilter.objects
        .filter(report_key=report_key)
        .filter(Q(user=user) | Q(is_shared=True))
        .select_related('user')
        .order_by('order', 'name', 'id')
    )


def get_accessible_saved_filter(user, report_key: str, filter_id: int):
    return accessible_saved_filters_qs(user, report_key).filter(pk=filter_id).first()


def resolve_report_get(request, report_key: str) -> QueryDict:
    """GET отчёта с раскрытием ?saved_filter=id (если пресет доступен)."""
    base = request.GET.copy()
    if isinstance(base, QueryDict):
        base = base.copy()
    else:
        base = QueryDict(mutable=True)

    raw_id = (base.get('saved_filter') or '').strip()
    if not raw_id.isdigit():
        return base

    preset = get_accessible_saved_filter(request.user, report_key, int(raw_id))
    if preset is None:
        return base

    extras = {'saved_filter': raw_id}
    # Текущий view / order_by из URL имеют приоритет над пресетом (удобно шарить режим).
    if base.get('view'):
        extras['view'] = base.get('view')
    if base.get('order_by'):
        extras['order_by'] = base.get('order_by')

    q = filter_data_to_querydict(preset.filter_data, extras=extras)
    if not q.get('view') and base.get('view'):
        q['view'] = base.get('view')
    return q


def saved_filters_for_template(user, report_key: str, active_id: str | None = None) -> list[dict]:
    rows = []
    active = (active_id or '').strip()
    for item in accessible_saved_filters_qs(user, report_key):
        rows.append({
            'id': item.pk,
            'name': item.name,
            'is_shared': bool(item.is_shared),
            'is_owner': item.user_id == getattr(user, 'pk', None),
            'is_active': active.isdigit() and int(active) == item.pk,
        })
    return rows
