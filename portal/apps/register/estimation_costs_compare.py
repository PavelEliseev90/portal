# -*- coding: utf-8 -*-
"""
Сравнение показателей расчёта оценки: ДО / ПОСЛЕ.

Алгоритм (одинаковые входные данные оценки, два прогона одной функции расчёта):

  ДО:
    - коэффициенты ДЦ+ЦГ из UnitPriceGroupSettings на дату оценки
    - суммы диагностик / настройки из RegEstimationsSettings id=12
    - estimations_price_calculation(..., persist=False)

  ПОСЛЕ:
    - коэффициенты ДЦ+ЦГ из UnitPriceGroupSettings на дату отчёта (сейчас)
    - суммы диагностик / настройки из RegEstimationsSettings id=13
    - та же estimations_price_calculation(..., persist=False)

Результаты показателей → колонки «до» / «после».
"""
from __future__ import annotations

import copy
import logging
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.db.models import Q

logger = logging.getLogger(__name__)

SECTION_PODGOTOVKA = 'podgotovka'
SECTION_SS = 'ss'
SECTION_MCU = 'mcu'
SECTION_OTHER = 'other'
SECTION_PRICE_FLOW = 'price_flow'
SECTION_DIAG_SETTINGS = 'diag_settings'

SECTION_TITLES = {
    SECTION_PODGOTOVKA: 'Подготовка',
    SECTION_SS: 'Слесарка',
    SECTION_MCU: 'Кузовной участок',
    SECTION_OTHER: 'Прочее / показатели',
    SECTION_PRICE_FLOW: 'Цепочка ЦНА',
    SECTION_DIAG_SETTINGS: 'Диагностика',
}

INDICATOR_IZNOS_SS = 'Возврат за слесарный ремонт (повышенный износ)'
INDICATOR_TOTAL_POD = 'Итого: подготовка'
INDICATOR_TOTAL_SS = 'Итого: слесарка'
INDICATOR_TOTAL_MCU = 'Итого: кузовной'
INDICATOR_TOTAL_RECOVERY = 'Итого: восстановительный ремонт'
INDICATOR_IZNOS_PRICE = 'Коррекция повышенного износа'
INDICATOR_CNA = 'ЦНА (base)'
INDICATOR_KF_TXT = 'ИРЦ ТХТ'
INDICATOR_TORG_PROTECT = 'Скидка торг (защита)'
INDICATOR_LOSS_PROTECT = 'Защита от убытка СС'
INDICATOR_FINANCE = 'Финансирование'

BEFORE_SETTINGS_ID = 12
AFTER_SETTINGS_ID = 13


@dataclass
class CompareProfile:
    before_settings_id: int = BEFORE_SETTINGS_ID
    after_settings_id: int = AFTER_SETTINGS_ID


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


def _strip_trailing_amount_from_label(text: str) -> str:
    """Убираем хвостовые суммы/проценты из комментария шага ЦНА."""
    import re

    value = (text or '').strip()
    value = re.sub(r'\s+\d[\d\s.,]*\s*₽\s*$', '', value)
    value = re.sub(r'\s+\d[\d.,]*\s*%\s*$', '', value)
    return ' '.join(value.split())


def _price_step_indicator(item: dict, idx: int) -> str:
    name = (item.get('name') or '').strip().lower()
    comment = (item.get('comment') or '').strip().lower()
    text = f'{name} {comment}'
    if 'повышенного износа' in text or 'использования в такси' in text:
        return 'Цена с учетом повышенного износа'
    if 'токсичном стоке' in text or 'ирц тхт' in text:
        return 'Цена в токсичной продаже'
    if 'защиты от убытка' in text:
        return 'Цена с учетом защиты от убытка'
    if 'защиты скидки торг' in text or 'скидка торг' in text:
        return 'Цена с учетом защиты скидки торг'
    if 'слесарного ремонта на износ' in text or 'влиялия слесарного ремонта' in text:
        return 'Цена скоректирована с учетом затрат влиялия слесарного ремонта на износ'
    if 'затрат на слесарный ремонт' in text:
        return 'Цена с учетом затрат на слесарный ремонт'
    if 'затрат на подготовку' in text:
        return 'Цена с учетом затрат на подготовку'
    if 'затрат на кузовной ремонт' in text:
        return 'Цена с учетом затрат на кузовной ремонт'
    if 'финансирование' in text:
        return 'Финансирование'
    if comment:
        return _strip_trailing_amount_from_label(item.get('comment') or '').capitalize()
    if name:
        return name.capitalize()
    return 'Шаг расчета'


def _clean_indicator_name(name: str) -> str:
    """Убираем суффиксы вида 'сумма 200/400/.../5001'."""
    import re

    value = (name or '').strip()
    value = re.sub(r'\s+сумма\s+\d{3,4}\b', '', value, flags=re.IGNORECASE)
    return ' '.join(value.split())


def _diag_indicator_from_work_name(name: str) -> str:
    text = (name or '').strip().lower()
    if not text:
        return ''
    if 'двигатель' in text and 'замеч' in text:
        return 'Двигатель устранение замечаний'
    if 'двигатель' in text:
        return 'Двигатель ремонт'
    if 'автомат' in text and 'замеч' in text:
        return 'АКПП устранение замечаний'
    if 'автомат' in text:
        return 'АКПП ремонт'
    if 'вариатор' in text and 'замеч' in text:
        return 'CVT устранение замечаний'
    if 'вариатор' in text:
        return 'CVT ремонт'
    if 'робот' in text and 'замеч' in text:
        return 'АМТ устранение замечаний'
    if 'робот' in text:
        return 'АМТ ремонт'
    if 'механика' in text and 'замеч' in text:
        return 'МКПП устранение замечаний'
    if 'механика' in text:
        return 'МКПП ремонт'
    if 'подвеска' in text and 'замеч' in text:
        return 'Подвеска устранение замечаний'
    if 'подвеска' in text:
        return 'Подвеска ремонт'
    if 'система выпуска ог' in text and 'замеч' in text:
        return 'Система выпуска ОГ устранение замечаний'
    if 'система выпуска ог' in text:
        return 'Система выпуска ОГ ремонт'
    if 'кондиционер' in text and 'замеч' in text:
        return 'Кондиционер устранение замечаний'
    if 'кондиционер' in text:
        return 'Кондиционер ремонт'
    if 'турбокомпрессор' in text and 'замеч' in text:
        return 'Турбокомпрессор устранение замечаний'
    if 'турбокомпрессор' in text:
        return 'Турбокомпрессор ремонт'
    if 'рулевое управление' in text and 'замеч' in text:
        return 'Рулевое управление устранение замечаний'
    if 'рулевое управление' in text:
        return 'Рулевое управление ремонт'
    if 'привод' in text and 'замеч' in text:
        return 'Привод устранение замечаний'
    if 'привод' in text:
        return 'Привод ремонт'
    if 'тормозная система' in text and 'замеч' in text:
        return 'Тормозная система устранение замечаний'
    if 'тормозная система' in text:
        return 'Тормозная система ремонт'
    if 'подрамник' in text and 'замеч' in text:
        return 'Подрамник устранение замечаний'
    if 'подрамник' in text:
        return 'Подрамник ремонт'
    if text.startswith('то ') or text.startswith('то-') or text.startswith('то'):
        return 'ТО'
    return ''


def _diag_actual_lines(price_result: dict | None) -> list[dict]:
    price_result = price_result or {}
    totals = OrderedDict()
    for item in (price_result.get('list_work_service') or []):
        label = _diag_indicator_from_work_name(_work_name(item))
        if not label:
            continue
        totals[label] = totals.get(label, 0.0) + _work_amount(item)

    lines = []
    for label, amount in totals.items():
        lines.append({
            'section': SECTION_DIAG_SETTINGS,
            'section_title': SECTION_TITLES[SECTION_DIAG_SETTINGS],
            'indicator': label,
            'amount': amount,
            'kind': 'diag_setting',
        })
    return lines


def _context_indicator_lines(price_result: dict | None) -> list[dict]:
    price_result = price_result or {}
    return [
        {
            'section': SECTION_OTHER,
            'section_title': SECTION_TITLES[SECTION_OTHER],
            'indicator': INDICATOR_KF_TXT,
            'amount': _as_float(price_result.get('kf')),
            'kind': 'context',
        },
        {
            'section': SECTION_OTHER,
            'section_title': SECTION_TITLES[SECTION_OTHER],
            'indicator': INDICATOR_TORG_PROTECT,
            'amount': _as_float(price_result.get('discount_torg')),
            'kind': 'context',
        },
        {
            'section': SECTION_OTHER,
            'section_title': SECTION_TITLES[SECTION_OTHER],
            'indicator': INDICATOR_LOSS_PROTECT,
            'amount': _as_float(price_result.get('zachita_ot_ubitka')),
            'kind': 'context',
        },
        {
            'section': SECTION_OTHER,
            'section_title': SECTION_TITLES[SECTION_OTHER],
            'indicator': INDICATOR_FINANCE,
            'amount': _as_float(price_result.get('finance_price')),
            'kind': 'context',
        },
    ]


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
            name = _clean_indicator_name(_work_name(item))
            if not name:
                continue
            lines.append({
                'section': section,
                'section_title': SECTION_TITLES[section],
                'indicator': name,
                'amount': _work_amount(item),
                'kind': 'work',
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

    # База и цепочка шагов цены (как в list_info_price на карточке)
    lines.append({
        'section': SECTION_PRICE_FLOW,
        'section_title': SECTION_TITLES[SECTION_PRICE_FLOW],
        'indicator': INDICATOR_CNA,
        'amount': _as_float(price_result.get('zna')),
        'kind': 'price_base',
    })
    for idx, step in enumerate(price_result.get('list_info_price') or [], start=1):
        if not isinstance(step, dict):
            continue
        lines.append({
            'section': SECTION_PRICE_FLOW,
            'section_title': SECTION_TITLES[SECTION_PRICE_FLOW],
            'indicator': _price_step_indicator(step, idx),
            'amount': _as_float(step.get('dif')),
            'kind': 'price_step',
        })

    lines.extend(_context_indicator_lines(price_result))
    lines.extend(_diag_actual_lines(price_result))

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

    # Если в JSON нет списков работ/шагов цены — соберём хотя бы итоги из полей записи
    has_works = any(
        raw.get(k)
        for k in ('list_work_podgotovka', 'list_work_service', 'list_work_mcu', 'list_info_price')
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
        'zna': getattr(record, 'zna', 0) or 0,
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


def _resolve_estimation_zna(estimation, calc_type: str = 'autohub') -> float:
    """Базовая ЦНА — как в estimations_price_calculation."""
    zna = 0.0
    if calc_type == 'kors':
        zna = getattr(estimation, 'kors_price', 0) or 0
    elif calc_type == 'autohub_k':
        zna = getattr(estimation, 'hub_avg_k', 0) or 0
        if not zna and getattr(estimation, 'page_remote', None) is not None:
            zna = estimation.page_remote.hub_avg_k or 0
    elif calc_type == 'autohub':
        zna = getattr(estimation, 'hub_avg', 0) or 0
        if not zna and getattr(estimation, 'page_remote', None) is not None:
            zna = estimation.page_remote.hub_avg or 0
    elif calc_type == 'avito':
        zna = getattr(estimation, 'avito_price_avg_market_price', 0) or 0
    elif calc_type == 'custom':
        zna = getattr(estimation, 'custom_zna', 0) or 0
    return _as_float(zna)


def _resolve_calc_context(interactiv_rlk, estimation, calc_type: str = 'autohub'):
    """ДЦ оценки + ЦГ по ЦНА + свежий RefUnit из БД."""
    from refs.models import RefUnit
    from refs.price_groups import resolve_price_group_by_amount

    rlk = getattr(interactiv_rlk, 'rlk', None)
    unit = getattr(interactiv_rlk, 'unit', None) or getattr(rlk, 'unit_dc', None) or getattr(rlk, 'unit', None)
    if unit is not None and getattr(unit, 'pk', None):
        unit = RefUnit.objects.filter(pk=unit.pk).first() or unit
    zna = _resolve_estimation_zna(estimation, calc_type=calc_type)
    price_group = resolve_price_group_by_amount(zna)
    return unit, price_group, zna


def _get_unit_settings_as_of(unit, price_group, as_of):
    """
    Коэффициенты ДЦ+ЦГ на дату as_of:
    последняя запись UnitPriceGroupSettings с created_at <= as_of.
    """
    from refs.unit_price_group_settings import UnitPriceGroupSettings

    if not unit or not price_group or as_of is None:
        return None

    row = (
        UnitPriceGroupSettings.objects
        .filter(
            unit_id=unit.pk,
            price_group_id=price_group.pk,
            created_at__lte=as_of,
        )
        .order_by('-created_at', '-id')
        .first()
    )
    if row is not None:
        return row

    code = str(getattr(price_group, 'code', '') or '').strip()
    if not code:
        return None
    return (
        UnitPriceGroupSettings.objects
        .filter(
            unit_id=unit.pk,
            price_group__code=code,
            created_at__lte=as_of,
        )
        .order_by('-created_at', '-id')
        .first()
    )


def _build_dc_for_calc(unit, price_group, settings_row):
    """
    Копия ДЦ с коэффициентами из снимка settings_row.
    Расчёт цены читает поля вида correction_txt_{code} / ratio_avtohub_txt_{code}.
    """
    from refs.unit_price_group_settings import sync_settings_row_to_unit

    dc = copy.copy(unit)
    if settings_row is None or price_group is None:
        return dc

    code = str(getattr(price_group, 'code', '') or '')
    if not code:
        return dc

    sync_settings_row_to_unit(dc, settings_row, code)

    # Явно фиксируем ИРЦ ТХТ так же, как ветка расчёта:
    # correction_txt, иначе ratio_avtohub_txt
    corr = getattr(settings_row, 'correction_txt', None)
    ratio = getattr(settings_row, 'ratio_avtohub_txt', None)
    kf = corr if corr not in (None, 0) else ratio
    if kf not in (None,):
        if hasattr(dc, f'correction_txt_{code}'):
            setattr(dc, f'correction_txt_{code}', kf)
        if hasattr(dc, f'ratio_avtohub_txt_{code}'):
            setattr(dc, f'ratio_avtohub_txt_{code}', kf)

    markup = getattr(settings_row, 'markup_txt', None)
    if markup in (None, 0):
        markup = getattr(settings_row, 'percent_txt', None)
    if markup not in (None,):
        if hasattr(dc, f'markup_txt_{code}'):
            setattr(dc, f'markup_txt_{code}', markup)
        if hasattr(dc, f'percent_txt_{code}'):
            setattr(dc, f'percent_txt_{code}', markup)

    torg = getattr(settings_row, 'max_discount_bargain_percent', None)
    if torg in (None, 0):
        torg = getattr(settings_row, 'percent_torg_txt', None)
    if torg not in (None,):
        if hasattr(dc, f'max_discount_bargain_percent_{code}'):
            setattr(dc, f'max_discount_bargain_percent_{code}', torg)
        if hasattr(dc, f'percent_torg_txt_{code}'):
            setattr(dc, f'percent_torg_txt_{code}', torg)

    return dc


def calculate_compare_before_after(
    interactiv_rlk,
    estimation,
    *,
    calc_type: str = 'autohub',
    profile: CompareProfile | None = None,
) -> dict[str, Any] | None:
    """
    Два прогона estimations_price_calculation на одних входных данных оценки.

    ДО   = коэф. ДЦ/ЦГ на дату оценки + RegEstimationsSettings(12)
    ПОСЛЕ = коэф. ДЦ/ЦГ на дату отчёта (сейчас) + RegEstimationsSettings(13)
    """
    from eco.views import (
        estimations_price_calculation,
        get_body_estimation_cached,
        get_salon_estimation_cached,
    )
    from register.models import RegEstimationsSettings

    profile = profile or CompareProfile()
    unit, price_group, zna = _resolve_calc_context(interactiv_rlk, estimation, calc_type=calc_type)
    if unit is None or price_group is None:
        return None
    if not zna:
        return None

    report_at = datetime.now()
    price_group_code = str(getattr(price_group, 'code', '') or '')

    # 1) Коэффициенты на дату оценки
    row_before = _get_unit_settings_as_of(unit, price_group, estimation.start_estimation)
    if row_before is None:
        return {
            'status': 'no_history',
            'history_row_id': None,
            'history_row_date': None,
            'price_group_code': price_group_code,
            'price_group_name': getattr(price_group, 'name', '') or '',
            'unit_id': unit.pk,
            'zna': zna,
        }

    # 2) Коэффициенты на дату формирования отчёта (текущая дата)
    row_after = _get_unit_settings_as_of(unit, price_group, report_at)
    if row_after is None:
        return {
            'status': 'no_history',
            'history_row_id': row_before.pk,
            'history_row_date': row_before.created_at,
            'price_group_code': price_group_code,
            'price_group_name': getattr(price_group, 'name', '') or '',
            'unit_id': unit.pk,
            'zna': zna,
        }

    dc_before = _build_dc_for_calc(unit, price_group, row_before)
    dc_after = _build_dc_for_calc(unit, price_group, row_after)

    # Одинаковые входы оценки (кузов/салон/тест-драйв и т.д.)
    body_info = get_body_estimation_cached(estimation)
    salon_info = get_salon_estimation_cached(estimation)
    settings_before = RegEstimationsSettings.objects.get(pk=profile.before_settings_id)
    settings_after = RegEstimationsSettings.objects.get(pk=profile.after_settings_id)

    def _run(settings_obj, dc_unit):
        interactiv_for_calc = copy.copy(interactiv_rlk)
        interactiv_for_calc.unit = dc_unit
        return estimations_price_calculation(
            interactiv_for_calc,
            estimation,
            type_calculation=calc_type,
            body_info=body_info,
            salon_info=salon_info,
            estimation_settings=settings_obj,
            persist=False,
            save_history=False,
        )

    before_result = _run(settings_before, dc_before)
    after_result = _run(settings_after, dc_after)
    if not before_result or not after_result:
        return None

    return {
        'status': 'ok',
        'before_result': before_result,
        'after_result': after_result,
        'history_row_id': row_before.pk,
        'history_row_date': row_before.created_at,
        'after_history_row_id': row_after.pk,
        'after_history_row_date': row_after.created_at,
        'report_at': report_at,
        'before_coefficients_source': 'dc_cg_on_estimation_date',
        'after_coefficients_source': 'dc_cg_on_report_date',
        'price_group_code': price_group_code,
        'price_group_name': getattr(price_group, 'name', '') or '',
        'unit_id': unit.pk,
        'zna': zna,
        'profile': profile,
    }


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
    try:
        compare_data = calculate_compare_before_after(
            interactiv_rlk,
            estimation,
            calc_type=calc_type,
        )
    except Exception:
        logger.exception('compare_estimation_costs: recalc failed estimation=%s', estimation.pk)
        return None

    if not compare_data:
        return None

    if compare_data.get('status') == 'no_history':
        return {
            'estimation_id': estimation.pk,
            'vin': (estimation.vin or '').strip(),
            'start_estimation': estimation.start_estimation,
            'before_source': 'no_history',
            'history_missing': True,
            'rows': [],
            'price_group_code': compare_data.get('price_group_code') or '',
            'price_group_name': compare_data.get('price_group_name') or '',
        }

    before_result = compare_data['before_result']
    after_result = compare_data['after_result']
    before_lines = extract_lines_from_price_result(before_result)
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
        'before_source': 'settings_12_coeffs_on_estimation_date',
        'before_history_id': compare_data.get('history_row_id'),
        'before_date': compare_data.get('history_row_date'),
        'after_history_id': compare_data.get('after_history_row_id'),
        'after_date': compare_data.get('after_history_row_date'),
        'before_coefficients_source': compare_data.get('before_coefficients_source') or 'dc_cg_on_estimation_date',
        'after_coefficients_source': compare_data.get('after_coefficients_source') or 'dc_cg_on_report_date',
        'before_zna': before_result.get('zna') or 0,
        'before_kf': before_result.get('kf') or '',
        'after_zna': after_result.get('zna') or 0,
        'after_kf': after_result.get('kf') or '',
        'after_estimation_price': after_result.get('estimation_price') or 0,
        'before_estimation_price': before_result.get('estimation_price') or 0,
        'settings_before_id': compare_data.get('profile').before_settings_id,
        'settings_after_id': compare_data.get('profile').after_settings_id,
        'price_group_code': compare_data.get('price_group_code') or '',
        'price_group_name': compare_data.get('price_group_name') or '',
        'history_missing': False,
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
    """Длинный формат: одна строка = один показатель (для экрана и Excel)."""
    out = []
    for row in comparison.get('rows') or []:
        out.append({
            'date': comparison.get('start_estimation'),
            'rlk_number': comparison.get('rlk_number') or comparison.get('rlk_id') or '',
            'vin': comparison.get('vin') or '',
            'unit_name': comparison.get('unit_name') or '',
            'section': row.get('section_title') or row.get('section') or '',
            'indicator': row.get('indicator') or '',
            'amount_before': row.get('amount_before') or 0,
            'amount_after': row.get('amount_after') or 0,
            'delta': row.get('delta') or 0,
        })
    return out


def export_comparisons_to_xlsx(comparisons, filepath: str | None = None) -> tuple[int, Any]:
    """Пишет Excel в файл или file-like. Возвращает (число строк, workbook)."""
    from openpyxl import Workbook
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = 'Затраты до-после'

    headers = [
        'Дата',
        'РЛ',
        'VIN',
        'ДЦ',
        'Раздел',
        'Показатель',
        'До',
        'После',
        'Дельта',
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    count = 0
    for comparison in comparisons:
        for row in flatten_comparison_rows(comparison):
            date_est = row['date']
            ws.append([
                date_est.strftime('%d.%m.%Y') if date_est else '',
                row['rlk_number'],
                row['vin'],
                row['unit_name'],
                row['section'],
                row['indicator'],
                row['amount_before'],
                row['amount_after'],
                row['delta'],
            ])
            count += 1

    for idx, _ in enumerate(headers, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = 16
    ws.column_dimensions['C'].width = 20
    ws.column_dimensions['F'].width = 45

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
