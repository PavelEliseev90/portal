"""Настройки автопереоценки КорсАвто: применение к подразделениям."""
from refs.models import RefTypeEvaluationCarsOrganization, RefUnit

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


def _autopricing_field_names_for_price(price):
    suffix = "_{}".format(price)
    names = []
    for code, _ in AUTOPRICING_BOOL_FIELDS:
        names.append("{}{}".format(code, suffix))
    for code, _ in AUTOPRICING_AUTOHUB_FIELDS:
        names.append("{}{}".format(code, suffix))
    for code, _ in AUTOPRICING_NUMERIC_FIELDS + AUTOPRICING_MARKUP_FIELDS:
        names.append("{}{}".format(code, suffix))
    names.append("eval_type_{}".format(price))
    legacy_suffix = "_{}".format(price)
    for code in AUTOPRICING_LEGACY_FIELD_NAMES:
        names.append("{}{}".format(code, legacy_suffix))
    return names


def mirror_autopricing_legacy_fields(unit, price):
    """Зеркалим новые поля в старые (для 1С)."""
    suffix = "_{}".format(price)
    legacy_suffix = "_{}".format(price)

    val = getattr(unit, "correction_test{}".format(suffix), None)
    if val is not None:
        setattr(unit, "ratio_avtohub_test_price{}".format(legacy_suffix), val)
    val = getattr(unit, "correction_test_1c{}".format(suffix), None)
    if val is not None:
        setattr(unit, "ratio_1с_test_price{}".format(legacy_suffix), val)

    val = getattr(unit, "correction_rdo{}".format(suffix), None)
    if val is not None:
        setattr(unit, "ratio_avtohub_rdo{}".format(legacy_suffix), val)
    val = getattr(unit, "correction_rdo_1c{}".format(suffix), None)
    if val is not None:
        setattr(unit, "ratio_1с_rdo{}".format(legacy_suffix), val)

    val = getattr(unit, "correction_kor{}".format(suffix), None)
    if val is not None:
        setattr(unit, "ratio_avtohub_kor{}".format(legacy_suffix), val)
    val = getattr(unit, "correction_kor_1c{}".format(suffix), None)
    if val is not None:
        setattr(unit, "ratio_1с_kor{}".format(legacy_suffix), val)

    val = getattr(unit, "correction_txt{}".format(suffix), None)
    if val is not None:
        setattr(unit, "ratio_avtohub_txt{}".format(legacy_suffix), val)
    val = getattr(unit, "correction_txt_1c{}".format(suffix), None)
    if val is not None:
        setattr(unit, "ratio_1с_txt{}".format(legacy_suffix), val)

    val = getattr(unit, "markup_txt{}".format(suffix), None)
    if val is not None:
        setattr(unit, "percent_txt{}".format(legacy_suffix), val)

    val = getattr(unit, "max_discount_bargain_percent{}".format(suffix), None)
    if val is not None:
        setattr(unit, "percent_torg_txt{}".format(legacy_suffix), val)

    val = getattr(unit, "max_discount_tradein{}".format(suffix), None)
    if val is not None:
        setattr(unit, "discount_tt{}".format(legacy_suffix), val)


def apply_autopricing_post_to_unit(unit, post_data):
    """Применить данные формы к подразделению (без save)."""
    for price in AUTOPRICING_PRICE_RANGES:
        suffix = "_{}".format(price)

        for code, _label in AUTOPRICING_BOOL_FIELDS:
            field_name = "{}{}".format(code, suffix)
            setattr(unit, field_name, field_name in post_data)

        for code, _label in AUTOPRICING_AUTOHUB_FIELDS:
            field_name = "{}{}".format(code, suffix)
            value = post_data.get(field_name, '')
            setattr(unit, field_name, value or '')

        for code, _label in AUTOPRICING_NUMERIC_FIELDS + AUTOPRICING_MARKUP_FIELDS:
            field_name = "{}{}".format(code, suffix)
            raw = post_data.get(field_name, '').strip()
            if raw == '':
                setattr(unit, field_name, None)
            else:
                try:
                    raw_normalized = raw.replace(',', '.')
                    setattr(unit, field_name, float(raw_normalized))
                except (ValueError, TypeError):
                    pass

        eval_field_name = "eval_type_{}".format(price)
        eval_id = post_data.get(eval_field_name, '').strip()
        if eval_id:
            try:
                eval_obj = RefTypeEvaluationCarsOrganization.objects.get(pk=int(eval_id))
                setattr(unit, eval_field_name, eval_obj)
            except (ValueError, RefTypeEvaluationCarsOrganization.DoesNotExist):
                pass
        else:
            setattr(unit, eval_field_name, None)

        mirror_autopricing_legacy_fields(unit, price)

    return unit


def copy_autopricing_settings(source_unit, target_unit):
    """Скопировать все настройки автопереоценки с одного ДЦ на другой."""
    for price in AUTOPRICING_PRICE_RANGES:
        for field_name in _autopricing_field_names_for_price(price):
            setattr(target_unit, field_name, getattr(source_unit, field_name))
    return target_unit


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
