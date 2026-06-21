"""Сборка настроек подразделения для отправки в 1С из истории UnitPriceGroupSettings."""
from refs.price_groups import LEGACY_UNIT_FIELD_MAP, get_active_price_groups, get_latest_settings_map_for_unit
from refs.serializers import RefUnitSerializer


def _serialize_value(value):
    if hasattr(value, 'pk'):
        return value.pk
    return value


def apply_settings_row_to_payload(payload, row, price_group_code):
    """Записать поля истории в плоский dict (имена как у колонок RefUnit для 1С)."""
    from website.autopricing_settings import (
        AUTOPRICING_AUTOHUB_FIELDS,
        AUTOPRICING_BOOL_FIELDS,
        AUTOPRICING_MARKUP_FIELDS,
        AUTOPRICING_NUMERIC_FIELDS,
        mirror_autopricing_legacy_fields_on_row,
    )

    mirror_autopricing_legacy_fields_on_row(row)
    code = str(price_group_code)
    suffix = '_{}'.format(code)

    for settings_field, unit_base in LEGACY_UNIT_FIELD_MAP.items():
        payload['{}_{}'.format(unit_base, code)] = _serialize_value(getattr(row, settings_field))

    for field_code, _label in AUTOPRICING_BOOL_FIELDS:
        payload['{}{}'.format(field_code, suffix)] = getattr(row, field_code)

    for field_code, _label in AUTOPRICING_AUTOHUB_FIELDS:
        payload['{}{}'.format(field_code, suffix)] = getattr(row, field_code) or ''

    for field_code, _label in AUTOPRICING_NUMERIC_FIELDS + AUTOPRICING_MARKUP_FIELDS:
        payload['{}{}'.format(field_code, suffix)] = _serialize_value(getattr(row, field_code))

    payload['eval_type{}'.format(suffix)] = row.eval_type_id

    return payload


def build_unit_settings_dc_payload(unit):
    """
    Настройки ДЦ для 1С: базовые поля RefUnit + актуальные значения по ЦГ из истории.
    Для каждой активной ЦГ берётся последняя запись UnitPriceGroupSettings.
    """
    payload = dict(RefUnitSerializer(unit, many=False).data)
    latest_map = get_latest_settings_map_for_unit(unit)

    for price_group in get_active_price_groups():
        row = latest_map.get(price_group.code)
        if row is not None:
            apply_settings_row_to_payload(payload, row, price_group.code)

    return payload
