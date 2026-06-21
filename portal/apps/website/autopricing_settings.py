"""Настройки автопереоценки КорсАвто: применение к подразделениям."""
from refs.models import RefTypeEvaluationCarsOrganization, RefUnit
from refs.price_groups import (
    get_active_price_group_codes,
    get_active_price_groups,
    get_latest_settings_map_for_unit,
)
from refs.unit_price_group_settings import (
    UnitPriceGroupSettings,
    copy_settings_row_to_new_record,
    copy_unit_price_range_to_settings,
    sync_settings_row_to_unit,
)

# Fallback, если в справочнике ещё нет code (до migrate/seed).
AUTOPRICING_PRICE_RANGES = [200, 400, 700, 1200, 2000, 3000, 5000, 5001]

AUTOPRICING_BOOL_FIELDS = [
    ('auto_strategy', "Автостратегия цены"),
    ('auto_active', "Активна"),
    ('lock_eval_change_after_stage', "Запрет изменения варианта управления ценой после перехода на новый этап"),
    ('deny_manual_price', "Запрет на ручной ввод"),
    ('deny_discount', "Запрет скидки"),
    ('no_limit_max_manual', "Не ограничивать максимальную ручную цену стратегией"),
    ('reset_manual_prices', "Обнуление ручных цен"),
    ('delay_repricing_new_stage', "Отсрочка переоценки в новом этапе"),
    ('check_price_rule_before_sale', "Проверка выполнения ценового правила при продаже"),
    ('check_open_tasks', "Проверка не закрытых задач"),
    ('calc_by_days_in_sale', "Расчет по дням в продаже"),
]

AUTOPRICING_AUTOHUB_FIELDS = [
    ('autohub_mode_kor', "Вариант использования данных Автохаб Коррекция"),
    ('autohub_mode_rdo', "Вариант использования данных Автохаб РДО"),
    ('autohub_mode_test', "Вариант использования данных Автохаб Тест прайс"),
    ('autohub_mode_txt', "Вариант использования данных Автохаб ТХТ"),
]

AUTOPRICING_NUMERIC_FIELDS = [
    ('correction_kor', "Корректировка Коррекция"),
    ('correction_kor_1c', "Корректировка Коррекция 1С"),
    ('correction_kor_express', "Корректировка Коррекция Экспресс"),
    ('correction_rdo', "Корректировка РДО"),
    ('correction_rdo_1c', "Корректировка РДО 1С"),
    ('correction_rdo_express', "Корректировка РДО Экспресс"),
    ('correction_test', "Корректировка Тест прайс"),
    ('correction_test_1c', "Корректировка Тест прайс 1С"),
    ('correction_test_express', "Корректировка Тест прайс Экспресс"),
    ('correction_txt', "Корректировка ТХТ"),
    ('correction_txt_1c', "Корректировка ТХТ 1С"),
    ('correction_txt_express', "Корректировка ТХТ Экспресс"),
    ('max_discount_tradein', "Максимальная скидка за TradeIn"),
    ('max_discount_bargain_percent', "Максимальная скидка торг в процентах"),
    ('marketing', "Маркетинг"),
]

AUTOPRICING_MARKUP_FIELDS = [
    ('markup_base', "Процент наценки"),
    ('markup_kor', "Процент наценки Коррекция"),
    ('markup_rdo', "Процент наценки РДО"),
    ('markup_test', "Процент наценки Тест прайс"),
    ('markup_txt', "Процент наценки ТХТ"),
]

AUTOPRICING_LEGACY_FIELD_NAMES = [
    'ratio_avtohub_test_price',
    'ratio_1с_test_price',
    'ratio_avtohub_rdo',
    'ratio_1с_rdo',
    'ratio_avtohub_kor',
    'ratio_1с_kor',
    'ratio_avtohub_txt',
    'ratio_1с_txt',
    'percent_txt',
    'percent_torg_txt',
    'discount_tt',
]


def get_korsavto_units_qs():
    return RefUnit.objects.filter(
        buauto=True,
        name__icontains='КорсАвто',
    ).select_related('city', 'ib').order_by('name')


def price_group_form_suffix(price_group):
    code = price_group.code if hasattr(price_group, 'code') else str(price_group)
    return '_{}'.format(code)


def _legacy_unit_suffix(price_group):
    return price_group_form_suffix(price_group)


def mirror_autopricing_legacy_fields_on_row(row):
    """Зеркалим поля коррекции в legacy-поля записи настроек."""
    if row.correction_test is not None:
        row.ratio_avtohub_test_price = row.correction_test
    if row.correction_test_1c is not None:
        row.ratio_1c_test_price = row.correction_test_1c
    if row.correction_rdo is not None:
        row.ratio_avtohub_rdo = row.correction_rdo
    if row.correction_rdo_1c is not None:
        row.ratio_1c_rdo = row.correction_rdo_1c
    if row.correction_kor is not None:
        row.ratio_avtohub_kor = row.correction_kor
    if row.correction_kor_1c is not None:
        row.ratio_1c_kor = row.correction_kor_1c
    if row.correction_txt is not None:
        row.ratio_avtohub_txt = row.correction_txt
    if row.correction_txt_1c is not None:
        row.ratio_1c_txt = row.correction_txt_1c
    if row.markup_txt is not None:
        row.percent_txt = row.markup_txt
    if row.max_discount_bargain_percent is not None:
        row.percent_torg_txt = row.max_discount_bargain_percent
    if row.max_discount_tradein is not None:
        row.discount_tt = row.max_discount_tradein
    return row


def mirror_autopricing_legacy_fields(unit, price_group):
    """Зеркалим новые поля в старые колонки RefUnit (для 1С)."""
    suffix = _legacy_unit_suffix(price_group)

    val = getattr(unit, "correction_test{}".format(suffix), None)
    if val is not None and hasattr(unit, "ratio_avtohub_test_price{}".format(suffix)):
        setattr(unit, "ratio_avtohub_test_price{}".format(suffix), val)
    val = getattr(unit, "correction_test_1c{}".format(suffix), None)
    if val is not None and hasattr(unit, "ratio_1с_test_price{}".format(suffix)):
        setattr(unit, "ratio_1с_test_price{}".format(suffix), val)

    val = getattr(unit, "correction_rdo{}".format(suffix), None)
    if val is not None and hasattr(unit, "ratio_avtohub_rdo{}".format(suffix)):
        setattr(unit, "ratio_avtohub_rdo{}".format(suffix), val)
    val = getattr(unit, "correction_rdo_1c{}".format(suffix), None)
    if val is not None and hasattr(unit, "ratio_1с_rdo{}".format(suffix)):
        setattr(unit, "ratio_1с_rdo{}".format(suffix), val)

    val = getattr(unit, "correction_kor{}".format(suffix), None)
    if val is not None and hasattr(unit, "ratio_avtohub_kor{}".format(suffix)):
        setattr(unit, "ratio_avtohub_kor{}".format(suffix), val)
    val = getattr(unit, "correction_kor_1c{}".format(suffix), None)
    if val is not None and hasattr(unit, "ratio_1с_kor{}".format(suffix)):
        setattr(unit, "ratio_1с_kor{}".format(suffix), val)

    val = getattr(unit, "correction_txt{}".format(suffix), None)
    if val is not None and hasattr(unit, "ratio_avtohub_txt{}".format(suffix)):
        setattr(unit, "ratio_avtohub_txt{}".format(suffix), val)
    val = getattr(unit, "correction_txt_1c{}".format(suffix), None)
    if val is not None and hasattr(unit, "ratio_1с_txt{}".format(suffix)):
        setattr(unit, "ratio_1с_txt{}".format(suffix), val)

    val = getattr(unit, "markup_txt{}".format(suffix), None)
    if val is not None and hasattr(unit, "percent_txt{}".format(suffix)):
        setattr(unit, "percent_txt{}".format(suffix), val)

    val = getattr(unit, "max_discount_bargain_percent{}".format(suffix), None)
    if val is not None and hasattr(unit, "percent_torg_txt{}".format(suffix)):
        setattr(unit, "percent_torg_txt{}".format(suffix), val)

    val = getattr(unit, "max_discount_tradein{}".format(suffix), None)
    if val is not None and hasattr(unit, "discount_tt{}".format(suffix)):
        setattr(unit, "discount_tt{}".format(suffix), val)


def apply_autopricing_post_to_row(row, post_data, price_group):
    """Применить POST формы к объекту UnitPriceGroupSettings (без save)."""
    suffix = price_group_form_suffix(price_group)

    for code, _label in AUTOPRICING_BOOL_FIELDS:
        field_name = '{}{}'.format(code, suffix)
        setattr(row, code, field_name in post_data)

    for code, _label in AUTOPRICING_AUTOHUB_FIELDS:
        field_name = '{}{}'.format(code, suffix)
        value = post_data.get(field_name, '')
        setattr(row, code, value or '')

    for code, _label in AUTOPRICING_NUMERIC_FIELDS + AUTOPRICING_MARKUP_FIELDS:
        field_name = '{}{}'.format(code, suffix)
        raw = post_data.get(field_name, '').strip()
        if raw == '':
            setattr(row, code, None)
        else:
            try:
                raw_normalized = raw.replace(',', '.')
                setattr(row, code, float(raw_normalized))
            except (ValueError, TypeError):
                pass

    eval_field_name = 'eval_type_{}'.format(price_group.code)
    eval_id = post_data.get(eval_field_name, '').strip()
    if eval_id:
        try:
            row.eval_type = RefTypeEvaluationCarsOrganization.objects.get(pk=int(eval_id))
        except (ValueError, RefTypeEvaluationCarsOrganization.DoesNotExist):
            row.eval_type = None
    else:
        row.eval_type = None

    mirror_autopricing_legacy_fields_on_row(row)
    return row


def apply_autopricing_post_to_unit(unit, post_data, price_groups=None):
    """Применить POST к плоским колонкам RefUnit, если они есть (для 1С)."""
    price_groups = price_groups or get_active_price_groups()
    for price_group in price_groups:
        suffix = price_group_form_suffix(price_group)
        for code, _label in AUTOPRICING_BOOL_FIELDS:
            field_name = '{}{}'.format(code, suffix)
            if hasattr(unit, field_name):
                setattr(unit, field_name, field_name in post_data)
        for code, _label in AUTOPRICING_AUTOHUB_FIELDS:
            field_name = '{}{}'.format(code, suffix)
            if hasattr(unit, field_name):
                setattr(unit, field_name, post_data.get(field_name, '') or '')
        for code, _label in AUTOPRICING_NUMERIC_FIELDS + AUTOPRICING_MARKUP_FIELDS:
            field_name = '{}{}'.format(code, suffix)
            if not hasattr(unit, field_name):
                continue
            raw = post_data.get(field_name, '').strip()
            if raw == '':
                setattr(unit, field_name, None)
            else:
                try:
                    setattr(unit, field_name, float(raw.replace(',', '.')))
                except (ValueError, TypeError):
                    pass
        eval_field_name = 'eval_type_{}'.format(price_group.code)
        eval_attr = 'eval_type{}'.format(suffix)
        if hasattr(unit, eval_attr):
            eval_id = post_data.get(eval_field_name, '').strip()
            if eval_id:
                try:
                    setattr(unit, eval_attr, RefTypeEvaluationCarsOrganization.objects.get(pk=int(eval_id)))
                except (ValueError, RefTypeEvaluationCarsOrganization.DoesNotExist):
                    setattr(unit, eval_attr, None)
            else:
                setattr(unit, eval_attr, None)
        mirror_autopricing_legacy_fields(unit, price_group)
    return unit


def get_autopricing_field_value(unit, price_group, field_code, latest_map=None):
    """Значение поля: последняя запись истории или колонка RefUnit (fallback)."""
    if latest_map is None:
        latest_map = get_latest_settings_map_for_unit(unit)
    group_code = price_group.code if hasattr(price_group, 'code') else str(price_group)
    row = latest_map.get(group_code)
    if row is not None and hasattr(row, field_code):
        return getattr(row, field_code)
    suffix = price_group_form_suffix(price_group)
    field_name = '{}{}'.format(field_code, suffix)
    if hasattr(unit, field_name):
        return getattr(unit, field_name)
    return None


def _legacy_fallback_value(unit, price_group, code, value):
    if value not in (None, 0, ''):
        return value
    suffix = _legacy_unit_suffix(price_group)
    legacy_map = {
        'correction_kor': 'ratio_avtohub_kor',
        'correction_kor_1c': 'ratio_1с_kor',
        'correction_rdo': 'ratio_avtohub_rdo',
        'correction_rdo_1c': 'ratio_1с_rdo',
        'correction_test': 'ratio_avtohub_test_price',
        'correction_test_1c': 'ratio_1с_test_price',
        'correction_txt': 'ratio_avtohub_txt',
        'correction_txt_1c': 'ratio_1с_txt',
        'max_discount_tradein': 'discount_tt',
        'max_discount_bargain_percent': 'percent_torg_txt',
        'markup_txt': 'percent_txt',
    }
    legacy_base = legacy_map.get(code)
    if not legacy_base:
        return value
    legacy_field = '{}{}'.format(legacy_base, suffix)
    if hasattr(unit, legacy_field):
        legacy_value = getattr(unit, legacy_field, None)
        if legacy_value not in (None, 0, ''):
            return legacy_value
    return value


def build_autopricing_ranges_for_unit(unit, latest_map=None):
    """Структура для шаблона редактирования настроек по активным ЦГ."""
    latest_map = latest_map or get_latest_settings_map_for_unit(unit)
    ranges = []
    for price_group in get_active_price_groups():
        code = price_group.code
        suffix = price_group_form_suffix(price_group)
        range_data = {
            'price': code,
            'title': price_group.name or code,
            'price_group': price_group,
            'bool_fields': [],
            'autohub_fields': [],
            'numeric_fields': [],
            'markup_fields': [],
            'eval_field': {},
            'numeric': {},
            'markup': {},
            'autohub': {},
        }

        for field_code, label in AUTOPRICING_BOOL_FIELDS:
            field_name = '{}{}'.format(field_code, suffix)
            range_data['bool_fields'].append({
                'name': field_name,
                'label': label,
                'value': get_autopricing_field_value(unit, price_group, field_code, latest_map) or False,
            })

        for field_code, label in AUTOPRICING_AUTOHUB_FIELDS:
            field_name = '{}{}'.format(field_code, suffix)
            value = get_autopricing_field_value(unit, price_group, field_code, latest_map) or ''
            range_data['autohub_fields'].append({
                'name': field_name,
                'label': label,
                'value': value,
            })
            range_data['autohub'][field_code] = {
                'name': field_name,
                'label': label,
                'value': value,
            }

        for field_code, label in AUTOPRICING_NUMERIC_FIELDS:
            field_name = '{}{}'.format(field_code, suffix)
            value = _legacy_fallback_value(
                unit,
                price_group,
                field_code,
                get_autopricing_field_value(unit, price_group, field_code, latest_map),
            )
            field_info = {'name': field_name, 'label': label, 'value': value}
            range_data['numeric_fields'].append(field_info)
            range_data['numeric'][field_code] = field_info

        for field_code, label in AUTOPRICING_MARKUP_FIELDS:
            field_name = '{}{}'.format(field_code, suffix)
            value = _legacy_fallback_value(
                unit,
                price_group,
                field_code,
                get_autopricing_field_value(unit, price_group, field_code, latest_map),
            )
            field_info = {'name': field_name, 'label': label, 'value': value}
            range_data['markup_fields'].append(field_info)
            range_data['markup'][field_code] = field_info

        eval_field_name = 'eval_type_{}'.format(code)
        eval_obj = get_autopricing_field_value(unit, price_group, 'eval_type', latest_map)
        eval_value_id = eval_obj.pk if eval_obj else None
        if eval_value_id is None:
            eval_attr = 'eval_type{}'.format(suffix)
            if hasattr(unit, eval_attr):
                eval_value_id = getattr(unit, '{}_id'.format(eval_attr), None)
        range_data['eval_field'] = {
            'name': eval_field_name,
            'label': 'Выводить в продажу по правилу',
            'value_id': eval_value_id,
        }
        ranges.append(range_data)
    return ranges


def build_autopricing_table_cells(unit, latest_map=None):
    """Плоские ячейки табличного вида: column_id -> {type, value, ...}."""
    from refs.models import AVTOHUB_DATA_USAGE_CHOICES

    latest_map = latest_map or get_latest_settings_map_for_unit(unit)
    cells = {}
    for price_group in get_active_price_groups():
        code = price_group.code
        suffix = price_group_form_suffix(price_group)

        for field_code, _label in AUTOPRICING_BOOL_FIELDS:
            column_id = '{}_{}'.format(field_code, code)
            cells[column_id] = {
                'type': 'bool',
                'value': get_autopricing_field_value(unit, price_group, field_code, latest_map) or False,
            }

        for field_code, _label in AUTOPRICING_NUMERIC_FIELDS:
            column_id = '{}_{}'.format(field_code, code)
            value = _legacy_fallback_value(
                unit,
                price_group,
                field_code,
                get_autopricing_field_value(unit, price_group, field_code, latest_map),
            )
            cells[column_id] = {'type': 'numeric', 'value': value}

        for field_code, _label in AUTOPRICING_MARKUP_FIELDS:
            column_id = '{}_{}'.format(field_code, code)
            value = _legacy_fallback_value(
                unit,
                price_group,
                field_code,
                get_autopricing_field_value(unit, price_group, field_code, latest_map),
            )
            cells[column_id] = {'type': 'markup', 'value': value}

        for field_code, _label in AUTOPRICING_AUTOHUB_FIELDS:
            column_id = '{}_{}'.format(field_code, code)
            value = get_autopricing_field_value(unit, price_group, field_code, latest_map) or ''
            autohub_label = ''
            if value:
                for choice_code, choice_title in AVTOHUB_DATA_USAGE_CHOICES:
                    if choice_code == value:
                        autohub_label = choice_title
                        break
            cells[column_id] = {'type': 'autohub', 'value': value, 'label': autohub_label}

        column_id = 'eval_type_{}'.format(code)
        eval_obj = get_autopricing_field_value(unit, price_group, 'eval_type', latest_map)
        eval_value_id = eval_obj.pk if eval_obj else None
        eval_name = eval_obj.name if eval_obj else ''
        if eval_value_id is None:
            eval_attr = 'eval_type{}'.format(suffix)
            if hasattr(unit, eval_attr):
                eval_value_id = getattr(unit, '{}_id'.format(eval_attr), None)
                if eval_value_id:
                    try:
                        eval_name = RefTypeEvaluationCarsOrganization.objects.get(pk=eval_value_id).name
                    except RefTypeEvaluationCarsOrganization.DoesNotExist:
                        eval_name = ''
        cells[column_id] = {'type': 'eval', 'value': eval_value_id, 'label': eval_name}
    return cells


def build_autopricing_table_columns():
    """Список столбцов табличного вида по активным ЦГ."""
    all_columns = [
        {'id': 'unit_id', 'label': 'ID', 'type': 'base', 'always_visible': True},
        {'id': 'unit_name', 'label': 'Подразделение', 'type': 'base', 'always_visible': True},
        {'id': 'unit_city', 'label': 'Город', 'type': 'base', 'always_visible': True},
    ]
    for price_group in get_active_price_groups():
        code = price_group.code
        title = price_group.name or code
        for field_code, label in AUTOPRICING_BOOL_FIELDS:
            all_columns.append({
                'id': '{}_{}'.format(field_code, code),
                'label': '{} {}'.format(label, title),
                'type': 'bool',
                'price': code,
                'field': field_code,
                'always_visible': False,
            })
        for field_code, label in AUTOPRICING_NUMERIC_FIELDS:
            all_columns.append({
                'id': '{}_{}'.format(field_code, code),
                'label': '{} {}'.format(label, title),
                'type': 'numeric',
                'price': code,
                'field': field_code,
                'always_visible': False,
            })
        for field_code, label in AUTOPRICING_MARKUP_FIELDS:
            all_columns.append({
                'id': '{}_{}'.format(field_code, code),
                'label': '{} {}'.format(label, title),
                'type': 'markup',
                'price': code,
                'field': field_code,
                'always_visible': False,
            })
        for field_code, label in AUTOPRICING_AUTOHUB_FIELDS:
            all_columns.append({
                'id': '{}_{}'.format(field_code, code),
                'label': '{} {}'.format(label, title),
                'type': 'autohub',
                'price': code,
                'field': field_code,
                'always_visible': False,
            })
        all_columns.append({
            'id': 'eval_type_{}'.format(code),
            'label': 'Выводить в продажу по правилу {}'.format(title),
            'type': 'eval',
            'price': code,
            'field': 'eval_type',
            'always_visible': False,
        })
    return all_columns


def save_autopricing_unit_settings(unit, post_data, price_groups=None):
    """
    Сохранить настройки: POST → UnitPriceGroupSettings (история) + RefUnit (1С, если есть колонки).
    """
    price_groups = price_groups or get_active_price_groups()
    for price_group in price_groups:
        row = UnitPriceGroupSettings(unit=unit, price_group=price_group)
        apply_autopricing_post_to_row(row, post_data, price_group)
        row.save()
        sync_settings_row_to_unit(unit, row, price_group.code)
    apply_autopricing_post_to_unit(unit, post_data, price_groups=price_groups)
    unit.save()
    return unit


def copy_autopricing_settings(source_unit, target_unit):
    """Скопировать актуальные настройки с одного ДЦ на другой (новые записи истории)."""
    latest_map = get_latest_settings_map_for_unit(source_unit)
    if not latest_map:
        for price_group in get_active_price_groups():
            row = copy_unit_price_range_to_settings(
                source_unit,
                price_group,
                target=UnitPriceGroupSettings(unit=source_unit, price_group=price_group),
            )
            row.save()
        latest_map = get_latest_settings_map_for_unit(source_unit)

    for source_row in latest_map.values():
        new_row = copy_settings_row_to_new_record(source_row, target_unit)
        sync_settings_row_to_unit(target_unit, new_row, source_row.price_group.code)

    apply_autopricing_post_to_unit(target_unit, _rows_to_post_data(latest_map), price_groups=get_active_price_groups())
    return target_unit


def _rows_to_post_data(latest_map):
    """Собрать pseudo-POST из последних записей (для копирования на RefUnit)."""
    post_data = {}
    for source_row in latest_map.values():
        suffix = price_group_form_suffix(source_row.price_group)
        for code, _label in AUTOPRICING_BOOL_FIELDS:
            if getattr(source_row, code):
                post_data['{}{}'.format(code, suffix)] = 'on'
        for code, _label in AUTOPRICING_AUTOHUB_FIELDS:
            val = getattr(source_row, code) or ''
            if val:
                post_data['{}{}'.format(code, suffix)] = val
        for code, _label in AUTOPRICING_NUMERIC_FIELDS + AUTOPRICING_MARKUP_FIELDS:
            val = getattr(source_row, code)
            if val is not None:
                post_data['{}{}'.format(code, suffix)] = str(val)
        if source_row.eval_type_id:
            post_data['eval_type_{}'.format(source_row.price_group.code)] = str(source_row.eval_type_id)
    return post_data


def apply_autopricing_to_units(source_unit, target_units, send_settings_callback=None):
    """Скопировать настройки и сохранить для списка подразделений."""
    count = 0
    failed_1c = []
    for target in target_units:
        if target.pk == source_unit.pk:
            continue
        copy_autopricing_settings(source_unit, target)
        target.save()
        if send_settings_callback:
            send_result = send_settings_callback(target)
            if isinstance(send_result, dict) and not send_result.get('ok'):
                failed_1c.append(send_result)
        count += 1
    return count, failed_1c


def push_units_settings_to_1c(units):
    """Отправить текущие настройки подразделений в 1С без изменения в портале."""
    from task_manager.views import send_settings_unit

    units = list(units)
    ok_count = 0
    failed = []
    for unit in units:
        result = send_settings_unit(unit)
        if result.get('ok'):
            ok_count += 1
        else:
            failed.append(result)
    return {
        'ok_count': ok_count,
        'failed': failed,
        'total': len(units),
    }


def format_1c_failed_units(failed_results, limit=5):
    if not failed_results:
        return ''
    names = [item.get('unit_name') or str(item.get('unit_id', '')) for item in failed_results[:limit]]
    text = ', '.join(names)
    if len(failed_results) > limit:
        text += ' и ещё {}'.format(len(failed_results) - limit)
    return text


def add_autopricing_portal_1c_messages(request, failed_1c, portal_message, all_1c_ok_suffix=''):
    """Сообщения пользователю: портал сохранён, 1С — успех или ошибка."""
    from django.contrib import messages

    failed_1c = failed_1c or []
    if not failed_1c:
        messages.success(request, portal_message + all_1c_ok_suffix)
        return

    failed_text = format_1c_failed_units(failed_1c)
    messages.warning(
        request,
        '{} Но не отправлено в 1С: {}.'.format(portal_message, failed_text),
    )
