"""Визуальный what-if калькулятор выкупа по ЦГ (без записи в БД)."""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Optional

from django.db.models import Q

from refs.price_groups import PRICE_GROUP_RANGES, RANGE_BY_CODE, zg_display_from_price

ZG_CODES = [row['code'] for row in PRICE_GROUP_RANGES]

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
    from refs.price_groups import price_group_code
    code = price_group_code(raw)
    if code:
        return code
    value = str(raw or '').strip()
    if not value:
        return None
    compact = value.replace(' ', '').replace('+', '')
    for row in PRICE_GROUP_RANGES:
        if compact == row['code'] or compact == row['name'].replace(' ', '').replace('+', ''):
            return row['code']
    aliases = {
        '5000+': '5001',
        '5000': '5000',
        '3001': '3000',
    }
    return aliases.get(compact)


def _range_q(field: str, zg_code: str) -> Q:
    rng = RANGE_BY_CODE[zg_code]
    min_p = float(rng['min_price_rub'] or 0)
    max_p = rng['max_price_rub']
    if zg_code == '200':
        return Q(**{f'{field}__gt': 0, f'{field}__lte': max_p})
    if max_p is None:
        return Q(**{f'{field}__gt': min_p})
    return Q(**{f'{field}__gt': min_p, f'{field}__lte': max_p})


def zg_price_q(zg_code: str) -> Q:
    """ЦНА на оценке или (если 0) на remote."""
    on_est = _range_q('estimation__hub_avg', zg_code)
    on_remote = (
        (Q(estimation__hub_avg__isnull=True) | Q(estimation__hub_avg=0))
        & _range_q('estimation__page_remote__hub_avg', zg_code)
    )
    return on_est | on_remote


def _num(value, default=0.0):
    try:
        if value in (None, ''):
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _same_num(a, b, eps=0.05):
    return abs(_num(a) - _num(b)) < eps


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


def load_full_settings():
    """Полный профиль настроек отдельным запросом (одна таблица < лимита PG 1664)."""
    from register.models import RegEstimationsSettings
    return RegEstimationsSettings.objects.order_by('id').last()


def load_unit_for_calculator(unit_id: Optional[int], zg_code: str = '', fallback_unit=None):
    """Загрузка ДЦ отдельным SELECT * (без JOIN с другими широкими таблицами)."""
    from refs.models import RefUnit
    if unit_id:
        unit = RefUnit.objects.filter(pk=unit_id).first()
        if unit is not None:
            return unit
    if fallback_unit is not None and getattr(fallback_unit, 'pk', None):
        return RefUnit.objects.filter(pk=fallback_unit.pk).first() or fallback_unit
    return (
        RefUnit.objects
        .filter(buauto=True, active_eco=True)
        .exclude(name='')
        .order_by('name')
        .first()
    )


def read_baseline_levers(unit, settings_obj, zg_code: str) -> dict:
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


def changed_lever_labels(zg_code: str, baseline: dict, effective: dict) -> list:
    labels = []
    for lever in lever_definitions(zg_code):
        key = lever['key']
        b = baseline.get(key)
        a = effective.get(key)
        if lever['unit'] == 'bool':
            if bool(b) != bool(a):
                labels.append(lever['label'])
        elif not _same_num(a, b):
            labels.append(lever['label'])
    return labels


def _unit_override_fields(zg_code: str, overrides: dict) -> dict:
    code = zg_code
    fields = {}
    if 'kf' in overrides:
        fields[f'correction_txt_{code}'] = overrides['kf']
        fields[f'ratio_avtohub_txt_{code}'] = overrides['kf']
    if 'percent_ss' in overrides:
        fields[f'markup_txt_{code}'] = overrides['percent_ss']
        fields[f'percent_txt_{code}'] = overrides['percent_ss']
    if 'percent_torg' in overrides:
        fields[f'max_discount_bargain_percent_{code}'] = overrides['percent_torg']
        fields[f'percent_torg_txt_{code}'] = overrides['percent_torg']
    return fields


def _settings_override_fields(zg_code: str, overrides: dict) -> dict:
    code = zg_code
    fields = {}
    if 'auction_kf' in overrides:
        fields[f'auction_kf_{code}'] = overrides['auction_kf']
    if 'iznos_with_ss' in overrides:
        fields['iznos_with_ss'] = bool(overrides['iznos_with_ss'])
    if 'financity_all' in overrides:
        fields['all_percent_financity'] = overrides['financity_all']
    if 'days_stok_all' in overrides:
        fields['all_days_stok_financity'] = overrides['days_stok_all']
    if 'financity_zg' in overrides:
        fields[f'percent_financity_{code}'] = overrides['financity_zg']
    if 'days_stok_zg' in overrides:
        fields[f'days_stok_financity_{code}'] = overrides['days_stok_zg']
    if 'izp' in overrides:
        fields[f'izp_{code}'] = overrides['izp']
    if 'izp_v' in overrides:
        fields[f'izp_{code}_v'] = overrides['izp_v']
    for key, _label, _unit in SETTINGS_ZG_AMOUNT_FIELDS:
        ov_key = f'amt_{key}'
        if ov_key in overrides:
            fields[f'{key}_{code}'] = overrides[ov_key]
    for key, _label, _unit in SETTINGS_ZG_DAMAGE_FIELDS:
        ov_key = f'dmg_{key}'
        if ov_key in overrides:
            fields[f'{key}_{code}'] = overrides[ov_key]
    return fields


def _patch_attrs(obj, fields: dict) -> dict:
    """Временный setattr, возвращает старые значения для отката."""
    backup = {}
    for name, value in fields.items():
        backup[name] = getattr(obj, name, None)
        setattr(obj, name, value)
    return backup


def _restore_attrs(obj, backup: dict):
    for name, value in backup.items():
        setattr(obj, name, value)


def _resolve_unit_id(rlk) -> Optional[int]:
    """ID ДЦ без загрузки RefUnit (unit / DocRLK / remote)."""
    uid = getattr(rlk, 'unit_id', None)
    if uid:
        return uid
    doc = getattr(rlk, 'rlk', None)
    if doc is not None:
        uid = getattr(doc, 'unit_id', None) or getattr(doc, 'unit_dc_id', None)
        if uid:
            return uid
    estimation = getattr(rlk, 'estimation', None)
    if estimation is not None:
        remote = getattr(estimation, 'page_remote', None)
        if remote is not None:
            uid = getattr(remote, 'unit_id', None)
            if uid:
                return uid
    return None


def _resolve_unit(rlk, units_map: Optional[dict] = None):
    uid = _resolve_unit_id(rlk)
    if uid and units_map is not None and uid in units_map:
        return units_map[uid]
    if uid:
        return load_unit_for_calculator(uid)
    return None


def _snapshot_from_result(result: Optional[dict]) -> dict:
    if not result or not isinstance(result, dict) or result.get('__error__'):
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


def _snapshot_from_soglasovanie(sog, estimation=None) -> Optional[dict]:
    if sog is None:
        return None
    price = _num(getattr(sog, 'price_auto_2', 0))
    zna = _num(getattr(sog, 'price_zna_2', 0))
    if price <= 0 and zna <= 0:
        return None
    pod = _num(getattr(sog, 'amount_podgotovka', 0))
    ss = _num(getattr(sog, 'amount_ss', 0))
    mcu = _num(getattr(sog, 'amount_mcu', 0))
    recovery = _num(getattr(sog, 'amount_recovery', 0)) or (pod + ss + mcu)
    if zna <= 0 and estimation is not None:
        zna = _num(getattr(estimation, 'hub_avg', 0))
        if zna <= 0:
            remote = getattr(estimation, 'page_remote', None)
            zna = _num(getattr(remote, 'hub_avg', 0)) if remote else 0
    return {
        'ok': True,
        'estimation_price': price,
        'cna_expenses': _num(getattr(sog, 'price_auto_bcp_2', 0)),
        'zna': zna,
        'zg': zg_display_from_price(zna) if zna else '',
        'kf': '',
        'amount_podgotovka': pod,
        'amount_ss': ss,
        'amount_mcu': mcu,
        'amount_recovery': recovery,
        'zachita_ot_ubitka': _num(getattr(sog, 'zachita_ot_ubitka', 0)),
        'discount_torg': _num(getattr(sog, 'discount_torg', 0)),
        'finance_price': _num(getattr(sog, 'finance_price', 0)),
        'iznos_price': 0,
        'source': 'soglasovanie',
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
    from register.models import RegInteractivOcenkaRLK
    from refs.models import RefUnit

    overrides = overrides or {}
    limit = max(1, min(int(limit or 100), 150))

    qs = (
        RegInteractivOcenkaRLK.objects
        .filter(estimation__isnull=False)
        .filter(estimation__start_estimation__gte=date_start)
        .filter(estimation__start_estimation__lte=date_end)
        .filter(zg_price_q(zg_code))
        # Нельзя select_related несколько RefUnit сразу: ~419 колонок × N > лимита PG 1664
        .select_related(
            'estimation',
            'estimation__page_salon',
            'estimation__page_remote',
            'estimation__page_soglasovanie',
            'estimation__modification',
            'estimation__modification__model',
            'estimation__modification__model__mark',
            'page_soglasovanie',
            'rlk',
        )
        .order_by('-estimation__start_estimation', '-estimation_id')
    )
    if unit_id:
        qs = qs.filter(Q(unit_id=unit_id) | Q(rlk__unit_id=unit_id) | Q(rlk__unit_dc_id=unit_id))

    total_found = qs.count()
    items = list(qs[:limit])

    # ДЦ — отдельный SELECT * (одна таблица), не JOIN в основной выборке
    unit_ids = {_resolve_unit_id(rlk) for rlk in items}
    unit_ids.discard(None)
    if unit_id:
        unit_ids.add(unit_id)
    units_map = {
        u.id: u
        for u in RefUnit.objects.filter(id__in=unit_ids)
    } if unit_ids else {}

    ref_unit = None
    if unit_id:
        ref_unit = units_map.get(unit_id) or load_unit_for_calculator(unit_id)
    if ref_unit is None and items:
        ref_unit = _resolve_unit(items[0], units_map)
    if ref_unit is None:
        ref_unit = load_unit_for_calculator(None)

    # Полные settings отдельным запросом (не в JOIN)
    settings_base = load_full_settings()
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
            'sample_errors': [],
        }

    baseline_levers = read_baseline_levers(ref_unit, settings_base, zg_code) if ref_unit else {}
    effective = dict(baseline_levers)
    effective.update(overrides or {})
    levers_changed = changed_lever_labels(zg_code, baseline_levers, effective)
    unit_fields = _unit_override_fields(zg_code, effective)
    settings_fields = _settings_override_fields(zg_code, effective)

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
    error_counter = Counter()
    sample_errors = []

    for rlk in items:
        estimation = rlk.estimation
        if estimation is None:
            err_count += 1
            error_counter['нет estimation'] += 1
            continue

        unit = _resolve_unit(rlk, units_map)
        if unit is None:
            err_count += 1
            error_counter['нет ДЦ (unit)'] += 1
            if len(sample_errors) < 8:
                sample_errors.append(f'id={estimation.pk}: нет ДЦ')
            continue

        sog = getattr(rlk, 'page_soglasovanie', None) or getattr(estimation, 'page_soglasovanie', None)
        before = _snapshot_from_soglasovanie(sog, estimation)

        original_unit_id = rlk.unit_id
        unit_backup = None
        settings_backup = None
        est_settings = None

        try:
            # Подставляем unit на RLK, если он был только на DocRLK / remote
            rlk.unit = unit

            body_info = get_body_estimation_cached(estimation)
            salon_info = get_salon_estimation_cached(estimation)
            est_settings = resolve_estimation_settings(
                interactiv_rlk=rlk,
                estimation=estimation,
                estimation_settings=None,
            ) or settings_base

            # «Было»: с согласования, иначе один прогон текущих настроек
            if before is None:
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
                if before['ok']:
                    before['source'] = 'recalc'

            if not before or not before.get('ok'):
                err_count += 1
                error_counter['нет базовой цены / ЦНА=0'] += 1
                if len(sample_errors) < 8:
                    sample_errors.append(f'id={estimation.pk}: нет базовой цены (ЦНА/авторасчёт)')
                continue

            # Если рычаги не менялись — «стало» = «было» (быстрый путь)
            if not levers_changed:
                after = dict(before)
            else:
                unit_backup = _patch_attrs(unit, unit_fields)
                settings_backup = _patch_attrs(est_settings, settings_fields)
                after_raw = estimations_price_calculation(
                    rlk,
                    estimation,
                    type_calculation='autohub',
                    body_info=body_info,
                    salon_info=salon_info,
                    estimation_settings=est_settings,
                    persist=False,
                    save_history=False,
                    trigger='price_calculator_whatif',
                )
                after = _snapshot_from_result(after_raw)
                if not after.get('ok'):
                    err_count += 1
                    error_counter['what-if вернул пусто'] += 1
                    if len(sample_errors) < 8:
                        sample_errors.append(f'id={estimation.pk}: what-if пустой результат')
                    continue
        except Exception as exc:
            err_count += 1
            msg = f'{type(exc).__name__}: {exc}'
            error_counter[msg.split(':')[0]] += 1
            if len(sample_errors) < 8:
                sample_errors.append(f'id={getattr(estimation, "pk", "?")}: {msg[:180]}')
            continue
        finally:
            if settings_backup is not None and est_settings is not None:
                _restore_attrs(est_settings, settings_backup)
            if unit_backup is not None:
                _restore_attrs(unit, unit_backup)
            rlk.unit_id = original_unit_id

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
                mark_obj = getattr(getattr(mod, 'model', None), 'mark', None)
                mark = getattr(mark_obj, 'name', '') if mark_obj else ''
        except Exception:
            pass

        rows.append({
            'estimation_id': estimation.pk,
            'rlk_id': getattr(rlk, 'rlk_id', None) or rlk.pk,
            'vin': estimation.vin or '',
            'unit_name': getattr(unit, 'name', '') or '—',
            'mark': mark or '',
            'model': model or '',
            'start_estimation': estimation.start_estimation,
            'zna_before': before['zna'],
            'zna_after': after['zna'],
            'zg': after.get('zg') or before.get('zg') or zg_display_from_price(before['zna'] or after['zna']),
            'before': before,
            'after': after,
            'before_source': before.get('source') or '',
            'delta_estimation_price': after['estimation_price'] - before['estimation_price'],
            'delta_amount_recovery': after['amount_recovery'] - before['amount_recovery'],
            'delta_podgotovka': after['amount_podgotovka'] - before['amount_podgotovka'],
            'delta_ss': after['amount_ss'] - before['amount_ss'],
            'delta_mcu': after['amount_mcu'] - before['amount_mcu'],
            'delta_cna': after['cna_expenses'] - before['cna_expenses'],
            'delta_pct_estimation': _pct_delta(before['estimation_price'], after['estimation_price']),
            'delta_pct_recovery': _pct_delta(before['amount_recovery'], after['amount_recovery']),
        })

    badges = [
        _badge('Выкуп', sum_before['estimation_price'], sum_after['estimation_price']),
        _badge('Затраты', sum_before['amount_recovery'], sum_after['amount_recovery']),
        _badge('БЦП', sum_before['cna_expenses'], sum_after['cna_expenses']),
    ]

    zg_name = next((r['name'] for r in PRICE_GROUP_RANGES if r['code'] == zg_code), zg_code)
    top_errors = [f'{name}: {cnt}' for name, cnt in error_counter.most_common(6)]

    return {
        'error': '',
        'rows': rows,
        'badges': badges,
        'baseline_levers': baseline_levers,
        'overrides': effective,
        'levers': lever_definitions(zg_code),
        'changed_levers': levers_changed,
        'total_found': total_found,
        'shown': len(rows),
        'ok_count': ok_count,
        'err_count': err_count,
        'truncated': True,
        'ref_unit': ref_unit,
        'zg_code': zg_code,
        'zg_name': zg_name,
        'sample_errors': sample_errors,
        'top_errors': top_errors,
        'summary': {
            'before': sum_before,
            'after': sum_after,
            'delta_estimation_price': sum_after['estimation_price'] - sum_before['estimation_price'],
            'delta_amount_recovery': sum_after['amount_recovery'] - sum_before['amount_recovery'],
        },
    }
