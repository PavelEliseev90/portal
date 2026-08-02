"""Визуальный what-if калькулятор выкупа по ЦГ (без записи в БД)."""
from __future__ import annotations

from copy import copy
from datetime import datetime
from typing import Any, Optional

from django.db.models import Q

from refs.price_groups import PRICE_GROUP_RANGES, RANGE_BY_CODE, zg_display_from_price

# Код ЦГ в полях RefUnit / RegEstimationsSettings
ZG_CODES = [row['code'] for row in PRICE_GROUP_RANGES]

# Суффиксы настроек повреждений / доплат для выбранной ЦГ
SETTINGS_ZG_AMOUNT_FIELDS = [
    ('windshield', 'Лобовое стекло', '₽'),
    ('windshield_heat', 'Лобовое с подогревом', '₽'),
    ('light_pered', 'Передняя оптика (сумма)', '₽'),
    ('light_pered_kf', 'Передняя оптика (КФ)', '%'),
    ('light_zad', 'Задняя оптика (сумма)', '₽'),
    ('light_zad_kf', 'Задняя оптика (КФ)', '%'),
    ('battery', 'АКБ', '₽'),
    ('to_1', 'ТО 1', '₽'),
    ('to_2', 'ТО 2', '₽'),
    ('to_3', 'ТО 3', '₽'),
]

_DAMAGE_PARTS = [
    ('engine', 'Двигатель'),
    ('engine_dt', 'Двигатель ДТ'),
    ('gear_at', 'АКПП'),
    ('gear_amt', 'АМТ'),
    ('gear_cvt', 'Вариатор'),
    ('gear_mt', 'МКПП'),
    ('suspension', 'Подвеска'),
    ('system_og', 'Система ОГ'),
    ('conditioner', 'Кондиционер'),
    ('turbo', 'Турбина'),
    ('wheel', 'Колёса'),
    ('brake', 'Тормоза'),
    ('subframe', 'Подрамник'),
    ('drive', 'Привод'),
]

SETTINGS_ZG_DAMAGE_FIELDS = []
for prefix, title in _DAMAGE_PARTS:
    SETTINGS_ZG_DAMAGE_FIELDS.extend([
        (f'{prefix}_danger_kf', f'{title}: опасный КФ', '%'),
        (f'{prefix}_danger_amount_min', f'{title}: опасный мин.', '₽'),
        (f'{prefix}_warning_kf', f'{title}: предупреждение КФ', '%'),
        (f'{prefix}_warning_amount_min', f'{title}: предупреждение мин.', '₽'),
    ])


def zg_code_from_param(raw) -> Optional[str]:
    value = str(raw or '').strip()
    if not value:
        return None
    compact = value.replace(' ', '')
    for row in PRICE_GROUP_RANGES:
        if value == row['code'] or value == row['name'] or compact == row['code'] or compact == row['name'].replace(' ', ''):
            return row['code']
    aliases = {
        '5000+': '5001',
        '5 000+': '5001',
        '3001+': '3000',
        '3 001+': '3000',
    }
    return aliases.get(value) or aliases.get(compact)


def zg_price_q(zg_code: str, field: str = 'estimation__hub_avg') -> Q:
    rng = RANGE_BY_CODE[zg_code]
    min_p = float(rng['min_price_rub'] or 0)
    max_p = rng['max_price_rub']
    if zg_code == '200':
        return Q(**{f'{field}__gt': 0, f'{field}__lte': max_p})
    if max_p is None:
        return Q(**{f'{field}__gt': min_p})
    return Q(**{f'{field}__gt': min_p, f'{field}__lte': max_p})


def _num(value, default=0.0):
    try:
        if value in (None, ''):
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _pct_delta(before, after):
    before = _num(before)
    after = _num(after)
    if abs(before) < 1e-9:
        return None
    return round(100.0 * (after - before) / before, 1)


def _badge(label, before, after, *, unit='₽'):
    before = _num(before)
    after = _num(after)
    delta = after - before
    return {
        'label': label,
        'before': before,
        'after': after,
        'delta': delta,
        'delta_pct': _pct_delta(before, after),
        'unit': unit,
        'changed': abs(delta) >= 0.5,
    }


def lever_definitions(zg_code: str) -> list[dict]:
    """Список рычагов UI: key, label, unit, group, source."""
    code = zg_code
    levers = [
        {'key': 'kf', 'label': 'ИРЦ ТХТ (КФ)', 'unit': '%', 'group': 'buyout', 'source': 'dc'},
        {'key': 'percent_ss', 'label': 'Защита от убытка СС', 'unit': '%', 'group': 'buyout', 'source': 'dc'},
        {'key': 'percent_torg', 'label': 'Защита скидки торг', 'unit': '%', 'group': 'buyout', 'source': 'dc'},
        {'key': 'auction_kf', 'label': 'КФ аукциона / такси', 'unit': '%', 'group': 'buyout', 'source': 'settings'},
        {'key': 'iznos_with_ss', 'label': 'Износ с учётом слесарки', 'unit': 'bool', 'group': 'iznos', 'source': 'settings'},
        {'key': 'financity_all', 'label': 'Финансирование % (общее)', 'unit': '%', 'group': 'finance', 'source': 'settings'},
        {'key': 'days_stok_all', 'label': 'Дни стока (общие)', 'unit': 'дн', 'group': 'finance', 'source': 'settings'},
        {'key': 'financity_zg', 'label': f'Финансирование % (ЦГ {code})', 'unit': '%', 'group': 'finance', 'source': 'settings'},
        {'key': 'days_stok_zg', 'label': f'Дни стока (ЦГ {code})', 'unit': 'дн', 'group': 'finance', 'source': 'settings'},
        {'key': 'izp', 'label': 'ИЗП % (сейчас почти не режет цену)', 'unit': '%', 'group': 'finance', 'source': 'settings'},
        {'key': 'izp_v', 'label': 'ИЗП вариант (≥0 включает финансирование)', 'unit': '', 'group': 'finance', 'source': 'settings'},
    ]
    for key, label, unit in SETTINGS_ZG_AMOUNT_FIELDS:
        levers.append({
            'key': f'amt_{key}',
            'label': label,
            'unit': unit,
            'group': 'amounts',
            'source': 'settings',
            'field': key,
        })
    for key, label, unit in SETTINGS_ZG_DAMAGE_FIELDS:
        levers.append({
            'key': f'dmg_{key}',
            'label': label,
            'unit': unit,
            'group': 'damage',
            'source': 'settings',
            'field': key,
        })
    return levers


def read_baseline_levers(unit, settings_obj, zg_code: str) -> dict:
    """Текущие значения рычагов с ДЦ + профиля настроек."""
    code = zg_code
    kf = getattr(unit, f'correction_txt_{code}', None)
    if kf in (None, 0):
        kf = getattr(unit, f'ratio_avtohub_txt_{code}', 100) or 100
    percent_ss = getattr(unit, f'markup_txt_{code}', None)
    if percent_ss in (None, 0):
        percent_ss = getattr(unit, f'percent_txt_{code}', 0) or 0
    percent_torg = getattr(unit, f'max_discount_bargain_percent_{code}', None)
    if percent_torg in (None, 0):
        percent_torg = getattr(unit, f'percent_torg_txt_{code}', 0) or 0

    values = {
        'kf': _num(kf, 100),
        'percent_ss': abs(_num(percent_ss)),
        'percent_torg': abs(_num(percent_torg)),
        'auction_kf': _num(getattr(settings_obj, f'auction_kf_{code}', 75), 75),
        'iznos_with_ss': bool(getattr(settings_obj, 'iznos_with_ss', False)),
        'financity_all': _num(getattr(settings_obj, 'all_percent_financity', 0)),
        'days_stok_all': _num(getattr(settings_obj, 'all_days_stok_financity', 0)),
        'financity_zg': _num(getattr(settings_obj, f'percent_financity_{code}', 0)),
        'days_stok_zg': _num(getattr(settings_obj, f'days_stok_financity_{code}', 0)),
        'izp': _num(getattr(settings_obj, f'izp_{code}', 0)),
        'izp_v': _num(getattr(settings_obj, f'izp_{code}_v', 0)),
    }
    for key, _label, _unit in SETTINGS_ZG_AMOUNT_FIELDS:
        values[f'amt_{key}'] = _num(getattr(settings_obj, f'{key}_{code}', 0))
    for key, _label, _unit in SETTINGS_ZG_DAMAGE_FIELDS:
        values[f'dmg_{key}'] = _num(getattr(settings_obj, f'{key}_{code}', 0))
    return values


def parse_overrides_from_request(get, zg_code: str, baseline: dict) -> dict:
    """Разбор POST/GET overrides; пустые → baseline."""
    out = dict(baseline)
    for lever in lever_definitions(zg_code):
        key = lever['key']
        raw = get.get(f'ov_{key}')
        if raw is None or str(raw).strip() == '':
            continue
        if lever['unit'] == 'bool':
            out[key] = str(raw).lower() in ('1', 'true', 'yes', 'on', 'да')
        else:
            out[key] = _num(raw, baseline.get(key, 0))
    return out


def apply_overrides_to_unit(unit, zg_code: str, overrides: dict):
    """Копия ДЦ с подменёнными ИРЦ/защитами для ЦГ."""
    dc = copy(unit)
    code = zg_code
    kf = overrides.get('kf')
    ss = overrides.get('percent_ss')
    torg = overrides.get('percent_torg')
    if kf is not None:
        setattr(dc, f'correction_txt_{code}', kf)
        setattr(dc, f'ratio_avtohub_txt_{code}', kf)
    if ss is not None:
        setattr(dc, f'markup_txt_{code}', ss)
        setattr(dc, f'percent_txt_{code}', ss)
    if torg is not None:
        setattr(dc, f'max_discount_bargain_percent_{code}', torg)
        setattr(dc, f'percent_torg_txt_{code}', torg)
    return dc


def apply_overrides_to_settings(settings_obj, zg_code: str, overrides: dict):
    """Копия профиля настроек с подменой полей ЦГ."""
    st = copy(settings_obj)
    code = zg_code
    if 'auction_kf' in overrides:
        setattr(st, f'auction_kf_{code}', overrides['auction_kf'])
    if 'iznos_with_ss' in overrides:
        st.iznos_with_ss = bool(overrides['iznos_with_ss'])
    if 'financity_all' in overrides:
        st.all_percent_financity = overrides['financity_all']
    if 'days_stok_all' in overrides:
        st.all_days_stok_financity = overrides['days_stok_all']
    if 'financity_zg' in overrides:
        setattr(st, f'percent_financity_{code}', overrides['financity_zg'])
    if 'days_stok_zg' in overrides:
        setattr(st, f'days_stok_financity_{code}', overrides['days_stok_zg'])
    if 'izp' in overrides:
        setattr(st, f'izp_{code}', overrides['izp'])
    if 'izp_v' in overrides:
        setattr(st, f'izp_{code}_v', overrides['izp_v'])
    for key, _label, _unit in SETTINGS_ZG_AMOUNT_FIELDS:
        ov_key = f'amt_{key}'
        if ov_key in overrides:
            setattr(st, f'{key}_{code}', overrides[ov_key])
    for key, _label, _unit in SETTINGS_ZG_DAMAGE_FIELDS:
        ov_key = f'dmg_{key}'
        if ov_key in overrides:
            setattr(st, f'{key}_{code}', overrides[ov_key])
    return st


def _snapshot_from_result(result: Optional[dict]) -> dict:
    if not result:
        return {
            'ok': False,
            'estimation_price': 0,
            'cna_expenses': 0,
            'zna': 0,
            'zg': '',
            'kf': '',
            'amount_podgotovka': 0,
            'amount_ss': 0,
            'amount_mcu': 0,
            'amount_recovery': 0,
            'zachita_ot_ubitka': 0,
            'discount_torg': 0,
            'finance_price': 0,
            'iznos_price': 0,
        }
    pod = _num(result.get('amount_podgotovka'))
    ss = _num(result.get('amount_ss'))
    mcu = _num(result.get('amount_mcu'))
    return {
        'ok': True,
        'estimation_price': _num(result.get('estimation_price')),
        'cna_expenses': _num(result.get('cna_expenses')),
        'zna': _num(result.get('zna')),
        'zg': str(result.get('zg') or ''),
        'kf': str(result.get('kf') or ''),
        'amount_podgotovka': pod,
        'amount_ss': ss,
        'amount_mcu': mcu,
        'amount_recovery': pod + ss + mcu,
        'zachita_ot_ubitka': _num(result.get('zachita_ot_ubitka')),
        'discount_torg': _num(result.get('discount_torg')),
        'finance_price': _num(result.get('finance_price')),
        'iznos_price': _num(result.get('iznos_price')),
    }


def run_price_calculator(
    *,
    date_start: datetime,
    date_end: datetime,
    zg_code: str,
    unit_id: Optional[int] = None,
    overrides: Optional[dict] = None,
    limit: int = 100,
) -> dict:
    from eco.views import (
        estimations_price_calculation,
        get_body_estimation_cached,
        get_salon_estimation_cached,
        resolve_estimation_settings,
    )
    from register.models import RegEstimationsSettings, RegInteractivOcenkaRLK
    from refs.models import RefUnit

    overrides = overrides or {}
    limit = max(1, min(int(limit or 100), 300))

    qs = (
        RegInteractivOcenkaRLK.objects
        .filter(estimation__isnull=False)
        .filter(estimation__start_estimation__gte=date_start)
        .filter(estimation__start_estimation__lte=date_end)
        .filter(zg_price_q(zg_code))
        .select_related(
            'estimation',
            'estimation__page_salon',
            'estimation__page_remote',
            'estimation__page_soglasovanie',
            'estimation__modification',
            'page_soglasovanie',
            'unit',
            'rlk',
        )
        .order_by('-estimation__start_estimation', '-estimation_id')
    )
    if unit_id:
        qs = qs.filter(Q(unit_id=unit_id) | Q(rlk__unit_id=unit_id) | Q(rlk__unit_dc_id=unit_id))

    total_found = qs.count()
    items = list(qs[:limit])

    # ДЦ для дефолтных рычагов
    ref_unit = None
    if unit_id:
        ref_unit = RefUnit.objects.filter(pk=unit_id).first()
    if ref_unit is None and items:
        ref_unit = items[0].unit
    if ref_unit is None:
        ref_unit = RefUnit.objects.filter(buauto=True, active_eco=True).order_by('name').first()

    settings_base = RegEstimationsSettings.objects.order_by('id').last()
    if settings_base is None:
        return {
            'error': 'Не найден профиль RegEstimationsSettings',
            'rows': [],
            'summary': {},
            'badges': [],
            'baseline_levers': {},
            'overrides': {},
            'levers': lever_definitions(zg_code),
            'total_found': 0,
            'shown': 0,
            'ref_unit': ref_unit,
        }

    baseline_levers = read_baseline_levers(ref_unit, settings_base, zg_code) if ref_unit else {}
    # overrides уже должны быть полными; если нет — baseline
    effective = dict(baseline_levers)
    effective.update({k: v for k, v in (overrides or {}).items() if k in baseline_levers or k in overrides})

    rows = []
    sum_before = {
        'estimation_price': 0.0,
        'amount_recovery': 0.0,
        'amount_podgotovka': 0.0,
        'amount_ss': 0.0,
        'amount_mcu': 0.0,
        'cna_expenses': 0.0,
        'finance_price': 0.0,
    }
    sum_after = {k: 0.0 for k in sum_before}
    ok_count = 0
    err_count = 0

    for rlk in items:
        estimation = rlk.estimation
        if estimation is None or rlk.unit is None:
            err_count += 1
            continue

        body_info = get_body_estimation_cached(estimation)
        salon_info = get_salon_estimation_cached(estimation)
        est_settings = resolve_estimation_settings(
            interactiv_rlk=rlk,
            estimation=estimation,
            estimation_settings=None,
        ) or settings_base

        original_unit = rlk.unit
        try:
            before_raw = estimations_price_calculation(
                rlk,
                estimation,
                type_calculation='autohub',
                body_info=body_info,
                salon_info=salon_info,
                estimation_settings=est_settings,
                persist=False,
                save_history=False,
                trigger='price_calculator_base',
            )
            before = _snapshot_from_result(before_raw)

            patched_unit = apply_overrides_to_unit(original_unit, zg_code, effective)
            patched_settings = apply_overrides_to_settings(est_settings, zg_code, effective)
            rlk.unit = patched_unit
            after_raw = estimations_price_calculation(
                rlk,
                estimation,
                type_calculation='autohub',
                body_info=body_info,
                salon_info=salon_info,
                estimation_settings=patched_settings,
                persist=False,
                save_history=False,
                trigger='price_calculator_whatif',
            )
            after = _snapshot_from_result(after_raw)
        except Exception:
            err_count += 1
            continue
        finally:
            rlk.unit = original_unit

        if not before['ok'] and not after['ok']:
            err_count += 1
            continue

        ok_count += 1
        for key in sum_before:
            sum_before[key] += before.get(key) or 0
            sum_after[key] += after.get(key) or 0

        mark = ''
        model = ''
        try:
            mod = estimation.modification
            if mod is not None:
                model = getattr(mod, 'name', '') or ''
                mark = getattr(getattr(mod, 'model', None), 'mark', None)
                mark = getattr(mark, 'name', '') if mark else ''
        except Exception:
            pass

        row = {
            'estimation_id': estimation.pk,
            'rlk_id': getattr(rlk, 'rlk_id', None) or rlk.pk,
            'vin': estimation.vin or '',
            'unit_name': getattr(original_unit, 'name', '') or '—',
            'mark': mark or '',
            'model': model or '',
            'start_estimation': estimation.start_estimation,
            'zna_before': before['zna'],
            'zna_after': after['zna'],
            'zg': after['zg'] or before['zg'] or zg_display_from_price(before['zna'] or after['zna']),
            'before': before,
            'after': after,
            'delta_estimation_price': after['estimation_price'] - before['estimation_price'],
            'delta_amount_recovery': after['amount_recovery'] - before['amount_recovery'],
            'delta_podgotovka': after['amount_podgotovka'] - before['amount_podgotovka'],
            'delta_ss': after['amount_ss'] - before['amount_ss'],
            'delta_mcu': after['amount_mcu'] - before['amount_mcu'],
            'delta_cna': after['cna_expenses'] - before['cna_expenses'],
            'delta_pct_estimation': _pct_delta(before['estimation_price'], after['estimation_price']),
            'delta_pct_recovery': _pct_delta(before['amount_recovery'], after['amount_recovery']),
        }
        rows.append(row)

    badges = [
        _badge('Выкуп (сумма)', sum_before['estimation_price'], sum_after['estimation_price']),
        _badge('Затраты всего', sum_before['amount_recovery'], sum_after['amount_recovery']),
        _badge('Подготовка', sum_before['amount_podgotovka'], sum_after['amount_podgotovka']),
        _badge('Слесарка (СС)', sum_before['amount_ss'], sum_after['amount_ss']),
        _badge('Кузовной (МКУ)', sum_before['amount_mcu'], sum_after['amount_mcu']),
        _badge('БЦП', sum_before['cna_expenses'], sum_after['cna_expenses']),
        _badge('Финансирование', sum_before['finance_price'], sum_after['finance_price']),
    ]

    changed_levers = []
    for lever in lever_definitions(zg_code):
        key = lever['key']
        b = baseline_levers.get(key)
        a = effective.get(key)
        if lever['unit'] == 'bool':
            if bool(b) != bool(a):
                changed_levers.append(lever['label'])
        elif abs(_num(a) - _num(b)) >= 1e-6:
            changed_levers.append(lever['label'])

    zg_name = next((r['name'] for r in PRICE_GROUP_RANGES if r['code'] == zg_code), zg_code)

    return {
        'error': '',
        'rows': rows,
        'badges': badges,
        'baseline_levers': baseline_levers,
        'overrides': effective,
        'levers': lever_definitions(zg_code),
        'changed_levers': changed_levers,
        'total_found': total_found,
        'shown': len(rows),
        'ok_count': ok_count,
        'err_count': err_count,
        'truncated': True,
        'ref_unit': ref_unit,
        'zg_code': zg_code,
        'zg_name': zg_name,
        'summary': {
            'before': sum_before,
            'after': sum_after,
            'delta_estimation_price': sum_after['estimation_price'] - sum_before['estimation_price'],
            'delta_amount_recovery': sum_after['amount_recovery'] - sum_before['amount_recovery'],
        },
    }
