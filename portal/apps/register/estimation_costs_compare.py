# -*- coding: utf-8 -*-
"""
Сравнение затрат оценки: снимок из истории (ДО) vs пересчёт на текущих настройках (ПОСЛЕ).

Тип расчёта по умолчанию — autohub.
«ДО» = первый успешный пересчёт; если позже добавлялись работы (затраты выросли /
появились строки) — берём последний снимок с той же ЦНА.
"""
from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Any

from django.db.models import Q

logger = logging.getLogger(__name__)

SECTION_PODGOTOVKA = 'podgotovka'
SECTION_SS = 'ss'
SECTION_MCU = 'mcu'
SECTION_OTHER = 'other'

SECTION_TITLES = {
    SECTION_PODGOTOVKA: 'Подготовка',
    SECTION_SS: 'Слесарка',
    SECTION_MCU: 'Кузовной участок',
    SECTION_OTHER: 'Прочее / показатели',
}

INDICATOR_IZNOS_SS = 'Возврат за слесарный ремонт (повышенный износ)'
INDICATOR_TOTAL_POD = 'Итого: подготовка'
INDICATOR_TOTAL_SS = 'Итого: слесарка'
INDICATOR_TOTAL_MCU = 'Итого: кузовной'
INDICATOR_TOTAL_RECOVERY = 'Итого: восстановительный ремонт'
INDICATOR_IZNOS_PRICE = 'Коррекция повышенного износа'


def _as_float(value, default=0.0) -> float:
    if value in (None, ''):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _norm_name(name: str) -> str:
    return ' '.join((name or '').strip().lower().split())


def _zna_key(value) -> float:
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _work_amount(item: dict) -> float:
    if not isinstance(item, dict):
        return 0.0
    for key in ('amount', 'price_kors', 'amount_kors'):
        if item.get(key) not in (None, ''):
            return _as_float(item.get(key))
    return 0.0


def _work_name(item: dict) -> str:
    if not isinstance(item, dict):
        return ''
    return (item.get('name') or item.get('title') or '').strip()


def extract_lines_from_price_result(price_result: dict | None) -> list[dict]:
    """Строки работ + служебные показатели из ответа estimations_price_calculation."""
    price_result = price_result or {}
    lines = []

    mapping = (
        (SECTION_PODGOTOVKA, price_result.get('list_work_podgotovka') or []),
        (SECTION_SS, price_result.get('list_work_service') or []),
        (SECTION_MCU, price_result.get('list_work_mcu') or []),
    )
    for section, items in mapping:
        for item in items:
            name = _work_name(item)
            if not name:
                continue
            lines.append({
                'section': section,
                'section_title': SECTION_TITLES[section],
                'indicator': name,
                'amount': _work_amount(item),
                'kind': 'work',
            })

    # Итоги разделов
    lines.append({
        'section': SECTION_PODGOTOVKA,
        'section_title': SECTION_TITLES[SECTION_PODGOTOVKA],
        'indicator': INDICATOR_TOTAL_POD,
        'amount': _as_float(price_result.get('amount_podgotovka')),
        'kind': 'total',
    })
    lines.append({
        'section': SECTION_SS,
        'section_title': SECTION_TITLES[SECTION_SS],
        'indicator': INDICATOR_TOTAL_SS,
        'amount': _as_float(price_result.get('amount_ss')),
        'kind': 'total',
    })
    lines.append({
        'section': SECTION_MCU,
        'section_title': SECTION_TITLES[SECTION_MCU],
        'indicator': INDICATOR_TOTAL_MCU,
        'amount': _as_float(price_result.get('amount_mcu')),
        'kind': 'total',
    })
    recovery = price_result.get('amount_sum') or price_result.get('amount_recovery')
    if recovery in (None, ''):
        recovery = (
            _as_float(price_result.get('amount_podgotovka'))
            + _as_float(price_result.get('amount_ss'))
            + _as_float(price_result.get('amount_mcu'))
        )
    lines.append({
        'section': SECTION_OTHER,
        'section_title': SECTION_TITLES[SECTION_OTHER],
        'indicator': INDICATOR_TOTAL_RECOVERY,
        'amount': _as_float(recovery),
        'kind': 'total',
    })

    # Повышенный износ / возврат слесарки
    lines.append({
        'section': SECTION_OTHER,
        'section_title': SECTION_TITLES[SECTION_OTHER],
        'indicator': INDICATOR_IZNOS_PRICE,
        'amount': _as_float(price_result.get('iznos_price')),
        'kind': 'indicator',
    })
    lines.append({
        'section': SECTION_OTHER,
        'section_title': SECTION_TITLES[SECTION_OTHER],
        'indicator': INDICATOR_IZNOS_SS,
        'amount': _as_float(price_result.get('iznos_ss_compensation')),
        'kind': 'indicator',
    })

    return lines


def extract_lines_from_history_record(record) -> list[dict]:
    """Строки из RegInteractivOcenkaPrice (raw JSON или поля итогов)."""
    raw = getattr(record, 'raw_calculation_json', None) or {}
    if isinstance(raw, str):
        import json
        try:
            raw = json.loads(raw)
        except (TypeError, ValueError):
            raw = {}
    if not isinstance(raw, dict):
        raw = {}

    # Если в JSON нет списков работ — соберём хотя бы итоги из полей записи
    has_works = any(
        raw.get(k)
        for k in ('list_work_podgotovka', 'list_work_service', 'list_work_mcu')
    )
    if has_works:
        # Подмешиваем поля записи, если в JSON нет компенсации износа
        if raw.get('iznos_ss_compensation') in (None, '') and getattr(record, 'iznos_ss_compensation', None):
            raw = dict(raw)
            raw['iznos_ss_compensation'] = record.iznos_ss_compensation
        if raw.get('iznos_price') in (None, '') and getattr(record, 'iznos_price', None):
            raw = dict(raw)
            raw['iznos_price'] = record.iznos_price
        if raw.get('amount_podgotovka') in (None, ''):
            raw = dict(raw)
            raw['amount_podgotovka'] = getattr(record, 'amount_podgotovka', 0) or 0
            raw['amount_ss'] = getattr(record, 'amount_ss', 0) or 0
            raw['amount_mcu'] = getattr(record, 'amount_mcu', 0) or 0
            raw['amount_recovery'] = getattr(record, 'amount_recovery', 0) or 0
        return extract_lines_from_price_result(raw)

    # Fallback: только агрегаты с записи
    return extract_lines_from_price_result({
        'amount_podgotovka': getattr(record, 'amount_podgotovka', 0) or 0,
        'amount_ss': getattr(record, 'amount_ss', 0) or 0,
        'amount_mcu': getattr(record, 'amount_mcu', 0) or 0,
        'amount_recovery': getattr(record, 'amount_recovery', 0) or 0,
        'iznos_price': getattr(record, 'iznos_price', 0) or 0,
        'iznos_ss_compensation': getattr(record, 'iznos_ss_compensation', 0) or 0,
        'list_work_podgotovka': [],
        'list_work_service': [],
        'list_work_mcu': [],
    })


def extract_lines_from_saved_tables(estimation) -> list[dict]:
    """Fallback «ДО» из RegEstimationPodgotovka / SS / MCU."""
    from register.models import RegEstimationMCU, RegEstimationPodgotovka, RegEstimationSS

    result = {
        'list_work_podgotovka': [
            {'name': r.name, 'amount': r.price_kors or 0, 'quantity': r.normo or 0}
            for r in RegEstimationPodgotovka.objects.filter(estimation=estimation).order_by('id')
        ],
        'list_work_service': [
            {'name': r.name, 'amount': r.price_kors or 0, 'quantity': r.normo or 0}
            for r in RegEstimationSS.objects.filter(estimation=estimation).order_by('id')
        ],
        'list_work_mcu': [
            {'name': r.name, 'amount': r.price_kors or 0, 'quantity': r.normo or 0}
            for r in RegEstimationMCU.objects.filter(estimation=estimation).order_by('id')
        ],
    }
    result['amount_podgotovka'] = sum(_work_amount(i) for i in result['list_work_podgotovka'])
    result['amount_ss'] = sum(_work_amount(i) for i in result['list_work_service'])
    result['amount_mcu'] = sum(_work_amount(i) for i in result['list_work_mcu'])
    sog = getattr(estimation, 'page_soglasovanie', None)
    if sog is not None:
        result['iznos_ss_compensation'] = 0
        # компенсации в таблицах работ нет — только на истории/пересчёте
    return extract_lines_from_price_result(result)


def _recovery_sum(lines: list[dict]) -> float:
    for line in lines:
        if line.get('indicator') == INDICATOR_TOTAL_RECOVERY:
            return _as_float(line.get('amount'))
    return sum(
        _as_float(l.get('amount'))
        for l in lines
        if l.get('kind') == 'work'
    )


def _work_count(lines: list[dict]) -> int:
    return sum(1 for l in lines if l.get('kind') == 'work')


def pick_before_history_record(estimation, calc_type: str = 'autohub'):
    """
    Выбор снимка «ДО»:
    - берём успешные записи истории типа calc_type;
    - базово — первая;
    - если позже с той же ЦНА затраты/число работ выросли — берём последнюю с той же ЦНА.
    """
    from register.models import RegInteractivOcenkaPrice

    qs = (
        RegInteractivOcenkaPrice.objects
        .filter(
            estimation=estimation,
            price_calculation=calc_type,
            is_success=True,
        )
        .order_by('date', 'id')
    )
    hist = list(qs)
    if not hist:
        return None, 'no_history'

    first = hist[0]
    if len(hist) == 1:
        return first, 'single'

    first_zna = _zna_key(first.zna)
    same = [h for h in hist if _zna_key(h.zna) == first_zna] if first_zna > 0 else hist
    if len(same) < 2:
        same = hist

    first_same = same[0]
    last_same = same[-1]

    first_lines = extract_lines_from_history_record(first_same)
    last_lines = extract_lines_from_history_record(last_same)
    first_rec = _recovery_sum(first_lines)
    last_rec = _recovery_sum(last_lines)
    first_n = _work_count(first_lines)
    last_n = _work_count(last_lines)

    # Добавляли работы позже → берём поздний снимок
    if last_rec > first_rec + 0.5 or last_n > first_n:
        return last_same, 'last_with_additions'
    return first_same, 'first'


def merge_before_after_lines(before_lines: list[dict], after_lines: list[dict]) -> list[dict]:
    """Сопоставление по (section, indicator) → строки с суммой до/после/Δ."""
    key_order = OrderedDict()

    def add_side(lines, side):
        for line in lines:
            key = (line['section'], _norm_name(line['indicator']), line.get('kind') or 'work')
            # для отображения сохраняем оригинальное имя с первой встречи
            if key not in key_order:
                key_order[key] = {
                    'section': line['section'],
                    'section_title': line['section_title'],
                    'indicator': line['indicator'],
                    'kind': line.get('kind') or 'work',
                    'amount_before': 0.0,
                    'amount_after': 0.0,
                }
            key_order[key][f'amount_{side}'] = _as_float(line.get('amount'))

    add_side(before_lines, 'before')
    add_side(after_lines, 'after')

    rows = []
    for item in key_order.values():
        before = item['amount_before']
        after = item['amount_after']
        rows.append({
            **item,
            'delta': after - before,
        })
    return rows


def compare_estimation_costs(
    interactiv_rlk,
    estimation,
    *,
    calc_type: str = 'autohub',
    only_changed: bool = False,
) -> dict[str, Any] | None:
    """
    Сравнение одной оценки.
    Возвращает dict с meta + rows или None, если пересчёт невозможен (нет ЦНА).
    """
    from eco.views import (
        estimations_price_calculation,
        get_body_estimation_cached,
        get_salon_estimation_cached,
        get_estimation_settings,
    )

    before_record, before_source = pick_before_history_record(estimation, calc_type=calc_type)
    if before_record is not None:
        before_lines = extract_lines_from_history_record(before_record)
        before_date = before_record.date
        before_history_id = before_record.pk
        before_zna = before_record.zna or 0
        before_kf = before_record.kf or ''
    else:
        before_lines = extract_lines_from_saved_tables(estimation)
        before_date = None
        before_history_id = None
        before_zna = estimation.hub_avg or 0
        before_kf = ''
        before_source = 'saved_tables'

    try:
        after_result = estimations_price_calculation(
            interactiv_rlk,
            estimation,
            type_calculation=calc_type,
            body_info=get_body_estimation_cached(estimation),
            salon_info=get_salon_estimation_cached(estimation),
            estimation_settings=get_estimation_settings(),
            persist=False,
            save_history=False,
        )
    except Exception:
        logger.exception('compare_estimation_costs: recalc failed estimation=%s', estimation.pk)
        return None

    if not after_result:
        return None

    after_lines = extract_lines_from_price_result(after_result)
    merged = merge_before_after_lines(before_lines, after_lines)
    if only_changed:
        merged = [r for r in merged if abs(r['delta']) > 0.5]

    rlk = getattr(interactiv_rlk, 'rlk', None)
    unit = getattr(interactiv_rlk, 'unit', None) or getattr(rlk, 'unit_dc', None) or getattr(rlk, 'unit', None)

    return {
        'estimation_id': estimation.pk,
        'rlk_id': getattr(rlk, 'pk', None),
        'rlk_number': getattr(rlk, 'nomer', None) or getattr(rlk, 'number', None) or '',
        'vin': (estimation.vin or '').strip(),
        'start_estimation': estimation.start_estimation,
        'unit_name': getattr(unit, 'name', '') or '',
        'calc_type': calc_type,
        'before_source': before_source,
        'before_history_id': before_history_id,
        'before_date': before_date,
        'before_zna': before_zna,
        'before_kf': before_kf,
        'after_zna': after_result.get('zna') or 0,
        'after_kf': after_result.get('kf') or '',
        'after_estimation_price': after_result.get('estimation_price') or 0,
        'before_estimation_price': (
            (getattr(before_record, 'estimation_price', 0) or 0) if before_record else 0
        ),
        'rows': merged,
    }


def iter_july_comparisons(
    *,
    date_from,
    date_to,
    calc_type: str = 'autohub',
    unit_id: int | None = None,
    limit: int = 0,
    only_changed: bool = False,
    estimation_ids: list[int] | None = None,
    vin: str = '',
    car_query: str = '',
    rlk_ids: list[int] | None = None,
):
    """Генератор результатов сравнения по выборке оценок."""
    from register.models import RegInteractivOcenkaRLK

    qs = build_comparisons_queryset(
        date_from=date_from,
        date_to=date_to,
        calc_type=calc_type,
        unit_id=unit_id,
        vin=vin,
        car_query=car_query,
        estimation_ids=estimation_ids,
    )
    if rlk_ids:
        qs = qs.filter(id__in=rlk_ids)
    qs = qs.select_related(
        'estimation',
        'estimation__page_soglasovanie',
        'estimation__page_salon',
        'estimation__page_remote',
        'estimation__page_test_drive',
        'page_soglasovanie',
        'rlk',
        'unit',
    )

    if limit:
        qs = qs[:limit]

    for interactiv_rlk in qs.iterator(chunk_size=20):
        estimation = interactiv_rlk.estimation
        if not estimation:
            continue
        result = compare_estimation_costs(
            interactiv_rlk,
            estimation,
            calc_type=calc_type,
            only_changed=only_changed,
        )
        if result is None:
            continue
        yield result


def flatten_comparison_rows(comparison: dict) -> list[dict]:
    """Длинный формат для Excel: одна строка = один показатель."""
    base = {
        'date': comparison.get('start_estimation'),
        'rlk_number': comparison.get('rlk_number') or '',
        'rlk_id': comparison.get('rlk_id'),
        'vin': comparison.get('vin') or '',
        'unit_name': comparison.get('unit_name') or '',
        'estimation_id': comparison.get('estimation_id'),
        'before_source': comparison.get('before_source') or '',
        'before_date': comparison.get('before_date'),
        'before_zna': comparison.get('before_zna') or 0,
        'after_zna': comparison.get('after_zna') or 0,
        'before_kf': comparison.get('before_kf') or '',
        'after_kf': comparison.get('after_kf') or '',
        'before_estimation_price': comparison.get('before_estimation_price') or 0,
        'after_estimation_price': comparison.get('after_estimation_price') or 0,
    }
    out = []
    for row in comparison.get('rows') or []:
        out.append({
            **base,
            'section': row.get('section_title') or row.get('section') or '',
            'indicator': row.get('indicator') or '',
            'kind': row.get('kind') or '',
            'amount_before': row.get('amount_before') or 0,
            'amount_after': row.get('amount_after') or 0,
            'delta': row.get('delta') or 0,
        })
    return out


def export_comparisons_to_xlsx(comparisons, filepath: str | None = None) -> int:
    """Пишет Excel в файл или file-like. Возвращает число строк данных."""
    from io import BytesIO

    from openpyxl import Workbook
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = 'Затраты до-после'

    headers = [
        'Дата оценки',
        'РЛ номер',
        'РЛ id',
        'VIN',
        'ДЦ',
        'ID оценки',
        'Источник ДО',
        'Дата снимка ДО',
        'ЦНА до',
        'ЦНА после',
        'КФ до',
        'КФ после',
        'Выкуп до',
        'Выкуп после',
        'Раздел',
        'Показатель',
        'Тип строки',
        'Сумма до',
        'Сумма после',
        'Δ',
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    count = 0
    for comparison in comparisons:
        for row in flatten_comparison_rows(comparison):
            date_est = row['date']
            date_before = row['before_date']
            ws.append([
                date_est.strftime('%d.%m.%Y %H:%M') if date_est else '',
                row['rlk_number'],
                row['rlk_id'] or '',
                row['vin'],
                row['unit_name'],
                row['estimation_id'],
                row['before_source'],
                date_before.strftime('%d.%m.%Y %H:%M') if date_before else '',
                row['before_zna'],
                row['after_zna'],
                row['before_kf'],
                row['after_kf'],
                row['before_estimation_price'],
                row['after_estimation_price'],
                row['section'],
                row['indicator'],
                row['kind'],
                row['amount_before'],
                row['amount_after'],
                row['delta'],
            ])
            count += 1

    for idx, _ in enumerate(headers, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = 16
    ws.column_dimensions['P'].width = 40
    ws.column_dimensions['D'].width = 20

    if filepath is not None:
        wb.save(filepath)
    return count, wb


def export_comparisons_http_response(comparisons, filename='estimation_costs_compare.xlsx'):
    """HttpResponse с Excel-файлом."""
    from io import BytesIO

    from django.http import HttpResponse

    buf = BytesIO()
    export_comparisons_to_xlsx(comparisons, buf)
    buf.seek(0)
    response = HttpResponse(
        buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def build_comparisons_queryset(
    *,
    date_from=None,
    date_to=None,
    calc_type: str = 'autohub',
    unit_id: int | None = None,
    vin: str = '',
    car_query: str = '',
    estimation_ids: list[int] | None = None,
):
    """Базовая выборка RegInteractivOcenkaRLK для отчёта (без пересчёта)."""
    from register.models import RegInteractivOcenkaRLK

    qs = (
        RegInteractivOcenkaRLK.objects
        .filter(estimation__isnull=False)
        .select_related('estimation', 'rlk', 'unit')
        .order_by('-estimation__start_estimation', 'estimation_id')
    )
    if estimation_ids:
        qs = qs.filter(estimation_id__in=estimation_ids)
    else:
        if date_from is not None:
            qs = qs.filter(estimation__start_estimation__gte=date_from)
        if date_to is not None:
            qs = qs.filter(estimation__start_estimation__lte=date_to)
    if unit_id:
        qs = qs.filter(
            Q(unit_id=unit_id)
            | Q(rlk__unit_id=unit_id)
            | Q(rlk__unit_dc_id=unit_id)
        )
    vin = (vin or '').strip().upper()
    car_query = (car_query or '').strip()
    if vin:
        qs = qs.filter(estimation__vin__icontains=vin)
    elif car_query:
        qs = qs.filter(
            Q(estimation__vin__icontains=car_query)
            | Q(estimation__name__icontains=car_query)
        )
        if car_query.isdigit():
            cid = int(car_query)
            qs = qs.filter(
                Q(rlk_id=cid)
                | Q(estimation_id=cid)
                | Q(estimation__rlk_id=cid)
            )
    qs = qs.filter(
        Q(estimation__hub_avg__gt=0)
        | Q(estimation__page_remote__hub_avg__gt=0)
    )
    return qs
