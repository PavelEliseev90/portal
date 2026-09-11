# -*- coding: utf-8 -*-
"""Общие хелперы отчётов ОП АСП (быстрые агрегаты + ленивые детали)."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Iterable
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Count, F, FloatField, Q, Sum, Value
from django.db.models.functions import Coalesce, Trim
from django.utils import timezone

from refs.models import RefUnit

ASP_DIRECTION_NAME = 'Отдел продаж АСП'
PAGE_SIZE = 100
GROUP_DETAIL_LIMIT = 500

VIEW_MODES = (
    ('main', 'Основной'),
    ('by_unit', 'По подразделениям'),
    ('by_person', 'По оценщикам / продавцам'),
)


def parse_date(raw) -> date | None:
    text = (raw or '').strip()
    if not text:
        return None
    for fmt in ('%Y-%m-%d', '%d.%m.%Y'):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_int_ids(values) -> list[int]:
    result = []
    for raw in values or []:
        text = str(raw).strip()
        if not text:
            continue
        try:
            result.append(int(text))
        except (TypeError, ValueError):
            continue
    return result


def local_today() -> date:
    """Безопасная «сегодня» при USE_TZ=False (localdate/localtime падают на naive)."""
    try:
        return timezone.localdate()
    except ValueError:
        return datetime.now().date()


def local_now() -> datetime:
    try:
        return timezone.localtime(timezone.now())
    except ValueError:
        return datetime.now()


def month_bounds(today: date | None = None) -> tuple[date, date]:
    today = today or local_today()
    start = today.replace(day=1)
    if today.month == 12:
        end = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(today.year, today.month + 1, 1) - timedelta(days=1)
    return start, end


def money(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def sum_money(field: str):
    """Sum по полю модели. Алиас агрегата не должен совпадать с field в том же annotate,
    если другое выражение ссылается на F(field) — см. aggregate_totals / SUM_MAP без sum_diff.
    """
    return Sum(Coalesce(F(field), Value(0)), output_field=FloatField())


def asp_sales_unit_ids() -> list[int]:
    """Подразделения направления «Отдел продаж АСП» для отбора отчётов.

    Без process-lifetime cache: направление у unit меняют в админке,
    а @lru_cache оставлял старый список до рестарта воркеров.
    """
    ids = list(
        RefUnit.objects
        .annotate(_dir_name=Trim('direction__name'), _unit_name=Trim('name'))
        .filter(_dir_name__iexact=ASP_DIRECTION_NAME)
        .exclude(_unit_name='')
        .order_by('name')
        .values_list('pk', flat=True)
    )
    if ids:
        return ids
    return list(
        RefUnit.objects
        .annotate(_unit_name=Trim('name'))
        .filter(buauto=True, active_eco=True)
        .exclude(_unit_name='')
        .order_by('name')
        .values_list('pk', flat=True)
    )


def asp_sales_units_list() -> list[dict]:
    ids = asp_sales_unit_ids()
    if not ids:
        return []
    return list(
        RefUnit.objects.filter(pk__in=ids).order_by('name').values('id', 'name')
    )


def asp_sales_units_qs():
    ids = asp_sales_unit_ids() or [-1]
    return RefUnit.objects.filter(pk__in=ids).select_related('city', 'direction').order_by('name')


def asp_type_receptions_qs():
    from refs.models import RefTypeReceptionCarsOrganization
    return (
        RefTypeReceptionCarsOrganization.objects
        .exclude(name='')
        .order_by('name')
    )


def asp_type_reception_ids() -> list[int]:
    return list(asp_type_receptions_qs().values_list('pk', flat=True))


def _parse_multi_ids(get, *keys: str) -> list[int]:
    getlist = getattr(get, 'getlist', None)
    raw = []
    if callable(getlist):
        for key in keys:
            raw.extend(list(getlist(key)))
            raw.extend(list(getlist(f'{key}[]')))
    else:
        for key in keys:
            for k in (key, f'{key}[]'):
                val = get.get(k)
                if val is None:
                    continue
                if isinstance(val, (list, tuple)):
                    raw.extend(val)
                else:
                    raw.append(val)
    return parse_int_ids(raw)


def parse_common_filters(get, *, default_month: bool = False) -> dict[str, Any]:
    raw_from = get.get('date_from') or get.get('date_start')
    raw_to = get.get('date_to') or get.get('date_end')
    date_from = parse_date(raw_from)
    date_to = parse_date(raw_to)
    # Дефолт месяца только при первом заходе (параметров дат нет в запросе),
    # а не когда пользователь явно очистил поля.
    has_date_params = any(
        key in get for key in ('date_from', 'date_to', 'date_start', 'date_end')
    )
    if default_month and not has_date_params and date_from is None and date_to is None:
        date_from, date_to = month_bounds()

    unit_ids = _parse_multi_ids(get, 'unit', 'unit_ids', 'unit_id')
    allowed_units = set(asp_sales_unit_ids())
    if unit_ids:
        unit_ids = [uid for uid in unit_ids if uid in allowed_units]

    type_reception_ids = _parse_multi_ids(
        get, 'type_reception', 'type_reception_ids', 'type_reception_id',
    )
    allowed_tr = set(asp_type_reception_ids())
    if type_reception_ids:
        type_reception_ids = [tid for tid in type_reception_ids if tid in allowed_tr]

    view_mode = (get.get('view') or 'main').strip()
    if view_mode not in {m[0] for m in VIEW_MODES}:
        view_mode = 'main'

    return {
        'date_from': date_from,
        'date_to': date_to,
        'unit_ids': unit_ids,
        'type_reception_ids': type_reception_ids,
        'vin': (get.get('vin') or '').strip(),
        'mark': (get.get('mark') or '').strip(),
        'model': (get.get('model') or '').strip(),
        'status': (get.get('status') or '').strip(),
        'person': (get.get('person') or '').strip(),
        'type_sale': (get.get('type_sale') or '').strip(),
        'client': (get.get('client') or '').strip(),
        'nomer': (get.get('nomer') or '').strip(),
        'days_from': (get.get('days_from') or '').strip(),
        'days_to': (get.get('days_to') or '').strip(),
        'view': view_mode,
        'page': max(1, int(get.get('page') or 1) if str(get.get('page') or '').isdigit() else 1),
        'group_key': (get.get('group_key') or '').strip(),
        'order_by': (get.get('order_by') or '').strip(),
    }


def allowed_unit_ids(filters: dict[str, Any]) -> list[int]:
    return filters.get('unit_ids') or asp_sales_unit_ids() or [-1]


def allowed_type_reception_ids(filters: dict[str, Any]) -> list[int]:
    """Пустой выбор = без ограничения (все типы приёма)."""
    return list(filters.get('type_reception_ids') or [])


def apply_type_reception_filter(qs, filters: dict[str, Any], *field_names: str):
    """Фильтр по выбранным типам приёма. Несколько field_names — OR по полям."""
    ids = allowed_type_reception_ids(filters)
    if not ids:
        return qs
    if not field_names:
        field_names = ('type_reception_id',)
    if len(field_names) == 1:
        return qs.filter(**{f'{field_names[0]}__in': ids})
    q = Q()
    for field in field_names:
        q |= Q(**{f'{field}__in': ids})
    return qs.filter(q)


def build_query_string(
    filters: dict[str, Any],
    extra_keys: Iterable[str] = (),
    exclude: Iterable[str] = ('page', 'group_key'),
) -> str:
    exclude_set = set(exclude)
    pairs = []
    if 'date_from' not in exclude_set and filters.get('date_from'):
        pairs.append((
            'date_from',
            filters['date_from'].isoformat() if hasattr(filters['date_from'], 'isoformat') else filters['date_from'],
        ))
    if 'date_to' not in exclude_set and filters.get('date_to'):
        pairs.append((
            'date_to',
            filters['date_to'].isoformat() if hasattr(filters['date_to'], 'isoformat') else filters['date_to'],
        ))
    if 'unit_ids' not in exclude_set:
        for uid in filters.get('unit_ids') or []:
            pairs.append(('unit', str(uid)))
    if 'type_reception_ids' not in exclude_set:
        for tid in filters.get('type_reception_ids') or []:
            pairs.append(('type_reception', str(tid)))
    keys = (
        'vin', 'mark', 'model', 'status', 'person', 'type_sale',
        'client', 'nomer', 'days_from', 'days_to', 'view', 'order_by',
    ) + tuple(extra_keys)
    for key in keys:
        if key in exclude_set:
            continue
        val = filters.get(key)
        if val not in (None, '', [], False):
            pairs.append((key, str(val)))
    return urlencode(pairs)


def filters_for_template(filters: dict[str, Any]) -> dict[str, Any]:
    return {
        'date_from': filters['date_from'].isoformat() if filters.get('date_from') else '',
        'date_to': filters['date_to'].isoformat() if filters.get('date_to') else '',
        'unit_ids': filters.get('unit_ids') or [],
        'type_reception_ids': filters.get('type_reception_ids') or [],
        'vin': filters.get('vin') or '',
        'mark': filters.get('mark') or '',
        'model': filters.get('model') or '',
        'status': filters.get('status') or '',
        'person': filters.get('person') or '',
        'type_sale': filters.get('type_sale') or '',
        'client': filters.get('client') or '',
        'nomer': filters.get('nomer') or '',
        'days_from': filters.get('days_from') or '',
        'days_to': filters.get('days_to') or '',
        'view': filters.get('view') or 'main',
        'page': filters.get('page') or 1,
        'order_by': filters.get('order_by') or '',
    }


def zero_sum(fields: Iterable[str]) -> dict[str, float]:
    return {f: 0.0 for f in fields}


def aggregate_totals(qs, field_map: dict[str, Any], *, count_field='id') -> dict[str, Any]:
    """field_map: output_name -> Sum(expr). Имена алиасов = имена полей модели — ок,
    пока выражения не ссылаются на F('то_же_имя') внутри того же aggregate.
    """
    ann = {'count': Count(count_field, distinct=True)}
    for name, expr in field_map.items():
        ann[name] = expr
    row = qs.aggregate(**ann)
    total = {'count': int(row.get('count') or 0)}
    for name in field_map:
        total[name] = money(row.get(name))
    return total


def aggregate_groups(qs, *, group_id_field: str, group_name_field: str, field_map: dict[str, Any]) -> list[dict]:
    # Алиасы с префиксом agg_, чтобы F('outlay') внутри выражений не путался с Sum(outlay)
    # (на случай если в field_map снова появятся составные Sum).
    ann = {'agg_count': Count('id', distinct=True)}
    alias_map = {}
    for name, expr in field_map.items():
        alias = f'agg_{name}'
        alias_map[name] = alias
        ann[alias] = expr
    rows = (
        qs.values(group_id_field, group_name_field)
        .annotate(**ann)
        .order_by('-agg_count', group_name_field)
    )
    result = []
    for row in rows:
        gid = row.get(group_id_field)
        if gid is None:
            gid = 0
        item = {
            'key': gid,
            'label': row.get(group_name_field) or '—',
            'count': int(row.get('agg_count') or 0),
            'rows': [],
            'lazy': True,
        }
        for name, alias in alias_map.items():
            item[name] = money(row.get(alias))
        result.append(item)
    return result


def paginate_rows(rows: list, page: int, page_size: int = PAGE_SIZE):
    paginator = Paginator(rows, page_size)
    page_obj = paginator.get_page(page)
    return page_obj.object_list, page_obj, paginator


def paginate_values_qs(values_qs, page: int, page_size: int = PAGE_SIZE, *, row_mapper=None):
    """Пагинация на уровне SQL (только текущая страница)."""
    paginator = Paginator(values_qs, page_size)
    page_obj = paginator.get_page(page)
    rows = list(page_obj.object_list)
    if row_mapper:
        rows = [row_mapper(r) for r in rows]
    return rows, page_obj, paginator


def json_safe_rows(rows: list[dict]) -> list[dict]:
    """Даты/datetime → ISO-строки для JsonResponse."""
    safe = []
    for row in rows:
        item = dict(row)
        for key, val in list(item.items()):
            if isinstance(val, datetime):
                item[key] = val.isoformat(sep=' ', timespec='seconds')
            elif isinstance(val, date):
                item[key] = val.isoformat()
        safe.append(item)
    return safe


def details_payload(rows: list[dict], *, limit: int = GROUP_DETAIL_LIMIT) -> dict[str, Any]:
    return {
        'ok': True,
        'rows': json_safe_rows(rows),
        'count': len(rows),
        'truncated': len(rows) >= limit,
    }


VIEW_COOKIE = 'asp_report_view'
VIEW_COOKIE_MAX_AGE = 60 * 60 * 24 * 180  # 180 дней


def preferred_view_from_cookie(cookie_value: str | None) -> str:
    view = (cookie_value or '').strip()
    if view in {m[0] for m in VIEW_MODES}:
        return view
    return 'main'


def report_shell(
    *,
    filters: dict,
    totals: dict,
    rows: list,
    groups: list,
    view: str,
    title: str,
    subtitle: str,
    person_label: str,
    extra: dict | None = None,
    page_obj=None,
    paginator=None,
    truncated: bool = False,
) -> dict[str, Any]:
    query_string = build_query_string(filters)
    export_url = f'?{query_string}&export=xlsx' if query_string else '?export=xlsx'
    data = {
        'report_title': title,
        'report_subtitle': subtitle,
        'person_label': person_label,
        'filters': filters_for_template(filters),
        'units': asp_sales_units_list(),
        'units_qs': asp_sales_units_qs(),
        'type_receptions_qs': asp_type_receptions_qs(),
        'view_modes': VIEW_MODES,
        'view': view,
        'totals': totals,
        'rows': rows,
        'groups': groups,
        'page_obj': page_obj,
        'paginator': paginator,
        'query_string': query_string,
        'query_string_base': build_query_string(filters, exclude=('page', 'view', 'group_key')),
        'export_url': export_url,
        'truncated': truncated,
        'lazy_details': view in ('by_unit', 'by_person'),
        'show_dates': False,
        'show_days_filter': False,
        'show_status_filter': False,
    }
    if extra:
        data.update(extra)
    return data
