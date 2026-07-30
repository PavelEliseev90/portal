"""Настройки формулы расчёта выкупа для аукциона Авито."""
from __future__ import annotations

from typing import Optional

# Ключи ЦГ как в calculate_car (zg)
TXT_COEFF_FIELDS = {
    '200': 'txt_coeff_200',
    '400': 'txt_coeff_400',
    '700': 'txt_coeff_700',
    '1 200': 'txt_coeff_1200',
    '2 000': 'txt_coeff_2000',
    '3 000': 'txt_coeff_3000',
    '5 000': 'txt_coeff_5000',
    '5 000+': 'txt_coeff_5001',
}

# Fallback на поля RefUnit (ДЦ), если в настройках аукциона пусто.
_DC_TXT_FALLBACK = {
    '200': ('correction_txt_200', 'ratio_avtohub_txt_200'),
    '400': ('correction_txt_400', 'ratio_avtohub_txt_400'),
    '700': ('correction_txt_700', 'ratio_avtohub_txt_700'),
    '1 200': ('correction_txt_1200', 'ratio_avtohub_txt_1200'),
    '2 000': ('correction_txt_2000', 'ratio_avtohub_txt_2000'),
    '3 000': ('correction_txt_3000', 'ratio_avtohub_txt_3000'),
    '5 000': ('correction_txt_5000', 'ratio_avtohub_txt_5000'),
    '5 000+': ('correction_txt_5001', 'ratio_avtohub_txt_5001'),
}


def zg_from_zna(zna: float) -> str:
    """Ценовая группа по ЦНА (пороги как в calculate_car)."""
    try:
        value = float(zna or 0)
    except (TypeError, ValueError):
        value = 0
    if value <= 0:
        return 'Неопределена'
    if value < 200_000:
        return '200'
    if value < 400_000:
        return '400'
    if value < 700_000:
        return '700'
    if value < 1_200_000:
        return '1 200'
    if value < 2_000_000:
        return '2 000'
    if value < 3_000_000:
        return '3 000'
    if value < 5_000_000:
        return '5 000'
    return '5 000+'


def _float_or_none(val):
    if val in (None, ''):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def resolve_txt_kf(zg: str, settings_obj=None, *, dc=None) -> float:
    """
    Коэффициент ТХТ (ИРЦ) для ценовой группы.
    Приоритет: настройки аукциона Авито → поля ДЦ → 100.
    """
    field = TXT_COEFF_FIELDS.get(zg)
    if settings_obj is not None and field:
        val = _float_or_none(getattr(settings_obj, field, None))
        if val is not None and val != 0:
            return val

    if dc is not None:
        primary, fallback = _DC_TXT_FALLBACK.get(zg, (None, None))
        for attr in (primary, fallback):
            if not attr:
                continue
            val = _float_or_none(getattr(dc, attr, None))
            if val is not None and val != 0:
                return val

    return 100.0


def get_avito_commission(settings_obj=None) -> int:
    """Сумма комиссии Авито, ₽ (вычитается после финансирования)."""
    if settings_obj is None:
        from auction_avito.models import AvitoAuctionSettings
        settings_obj = AvitoAuctionSettings.get_solo()
    try:
        return max(0, int(settings_obj.avito_commission or 0))
    except (TypeError, ValueError):
        return 0


def txt_coefficients_dict(settings_obj) -> dict:
    """Все коэффициенты ТХТ для API/UI."""
    out = {}
    for zg, field in TXT_COEFF_FIELDS.items():
        val = _float_or_none(getattr(settings_obj, field, None))
        out[zg] = val
    return out
