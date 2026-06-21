"""Настройки подразделения по ценовой группе (история: каждое сохранение — новая запись)."""
from types import SimpleNamespace

from django.db import models

from refs.price_groups import LEGACY_UNIT_FIELD_MAP, get_active_price_groups

AVTOHUB_DATA_USAGE_CHOICES = [
    ('ПЦП', 'ПЦП'),
    ('ЦНА', 'ЦНА'),
    ('АвитоОценка', 'АвитоОценка'),
]


class UnitPriceGroupSettings(models.Model):
    unit = models.ForeignKey(
        'RefUnit',
        on_delete=models.CASCADE,
        related_name='price_group_settings',
        verbose_name='Подразделение',
    )
    price_group = models.ForeignKey(
        'RefGroupPrice',
        on_delete=models.PROTECT,
        related_name='unit_settings',
        verbose_name='Ценовая группа',
    )
    created_at = models.DateTimeField('Дата создания', auto_now_add=True, db_index=True)

    # Legacy / ИРЦ
    ratio_1c_test_price = models.FloatField('ИРЦ Тест прайс 1С', default=0.0, blank=True, null=True)
    ratio_1c_rdo = models.FloatField('ИРЦ РДО 1С', default=0.0, blank=True, null=True)
    ratio_1c_kor = models.FloatField('ИРЦ коррекция 1С', default=0.0, blank=True, null=True)
    ratio_1c_txt = models.FloatField('ИРЦ ТХТ 1С', default=0.0, blank=True, null=True)
    ratio_avtohub_test_price = models.FloatField('ИРЦ Автохаб Тест прайс', default=0.0, blank=True, null=True)
    ratio_avtohub_rdo = models.FloatField('ИРЦ Автохаб РДО', default=0.0, blank=True, null=True)
    ratio_avtohub_kor = models.FloatField('ИРЦ Автохаб коррекция', default=0.0, blank=True, null=True)
    ratio_avtohub_txt = models.FloatField('ИРЦ Автохаб ТХТ', default=0.0, blank=True, null=True)
    percent_txt = models.FloatField('Процент наценки к СС ТХТ', default=0.0, blank=True, null=True)
    percent_torg_txt = models.FloatField('Процент наценки торг к СС ТХТ', default=0.0, blank=True, null=True)
    discount_tt = models.FloatField('Скидка Trade-In', default=0.0, blank=True, null=True)
    discount_torg = models.FloatField('Скидка торг', default=0.0, blank=True, null=True)

    # Автопереоценка / управление ценой
    auto_strategy = models.BooleanField('Автостратегия цены', default=False)
    auto_active = models.BooleanField('Активна', default=False)
    autohub_mode_kor = models.CharField(
        'Вариант использования Автохаб Коррекция',
        max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='',
    )
    autohub_mode_rdo = models.CharField(
        'Вариант использования Автохаб РДО',
        max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='',
    )
    autohub_mode_test = models.CharField(
        'Вариант использования Автохаб Тест прайс',
        max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='',
    )
    autohub_mode_txt = models.CharField(
        'Вариант использования Автохаб ТХТ',
        max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='',
    )
    eval_type = models.ForeignKey(
        'RefTypeEvaluationCarsOrganization',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name='Выводить в продажу по правилу',
        related_name='+',
    )
    lock_eval_change_after_stage = models.BooleanField(
        'Запрет изменения варианта управления ценой после перехода на новый этап',
        default=False,
    )
    deny_manual_price = models.BooleanField('Запрет на ручной ввод', default=False)
    deny_discount = models.BooleanField('Запрет скидки', default=False)
    correction_kor = models.FloatField('Корректировка Коррекция', default=0.0, blank=True, null=True)
    correction_kor_1c = models.FloatField('Корректировка Коррекция 1С', default=0.0, blank=True, null=True)
    correction_kor_express = models.FloatField('Корректировка Коррекция Экспресс', default=0.0, blank=True, null=True)
    correction_rdo = models.FloatField('Корректировка РДО', default=0.0, blank=True, null=True)
    correction_rdo_1c = models.FloatField('Корректировка РДО 1С', default=0.0, blank=True, null=True)
    correction_rdo_express = models.FloatField('Корректировка РДО Экспресс', default=0.0, blank=True, null=True)
    correction_test = models.FloatField('Корректировка Тест прайс', default=0.0, blank=True, null=True)
    correction_test_1c = models.FloatField('Корректировка Тест прайс 1С', default=0.0, blank=True, null=True)
    correction_test_express = models.FloatField('Корректировка Тест прайс Экспресс', default=0.0, blank=True, null=True)
    correction_txt = models.FloatField('Корректировка ТХТ', default=0.0, blank=True, null=True)
    correction_txt_1c = models.FloatField('Корректировка ТХТ 1С', default=0.0, blank=True, null=True)
    correction_txt_express = models.FloatField('Корректировка ТХТ Экспресс', default=0.0, blank=True, null=True)
    max_discount_tradein = models.FloatField('Максимальная скидка за TradeIn', default=0.0, blank=True, null=True)
    max_discount_bargain_percent = models.FloatField('Максимальная скидка торг в процентах', default=0.0, blank=True, null=True)
    marketing = models.FloatField('Маркетинг', default=0.0, blank=True, null=True)
    no_limit_max_manual = models.BooleanField('Не ограничивать максимальную ручную цену стратегией', default=False)
    reset_manual_prices = models.BooleanField('Обнуление ручных цен', default=False)
    delay_repricing_new_stage = models.BooleanField('Отсрочка переоценки в новом этапе', default=False)
    check_price_rule_before_sale = models.BooleanField('Проверка выполнения ценового правила при продаже', default=False)
    check_open_tasks = models.BooleanField('Проверка не закрытых задач', default=False)
    markup_base = models.FloatField('Процент наценки', default=0.0, blank=True, null=True)
    markup_kor = models.FloatField('Процент наценки Коррекция', default=0.0, blank=True, null=True)
    markup_rdo = models.FloatField('Процент наценки РДО', default=0.0, blank=True, null=True)
    markup_test = models.FloatField('Процент наценки Тест прайс', default=0.0, blank=True, null=True)
    markup_txt = models.FloatField('Процент наценки ТХТ', default=0.0, blank=True, null=True)
    calc_by_days_in_sale = models.BooleanField('Расчет по дням в продаже', default=False)

    class Meta:
        db_table = 'unitPriceGroupSettings'
        verbose_name = 'Настройки ДЦ по ценовой группе'
        verbose_name_plural = 'Настройки ДЦ по ценовым группам'
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['unit', 'price_group', '-created_at']),
        ]

    def __str__(self):
        return '{} / {} ({})'.format(self.unit_id, self.price_group_id, self.created_at)


def copy_unit_price_range_to_settings(unit, price_group, target=None):
    """Скопировать поля RefUnit_*_{code} в объект настроек (без save)."""
    from website.autopricing_settings import (
        AUTOPRICING_AUTOHUB_FIELDS,
        AUTOPRICING_BOOL_FIELDS,
        AUTOPRICING_MARKUP_FIELDS,
        AUTOPRICING_NUMERIC_FIELDS,
    )

    code = price_group.code
    if target is None:
        row = SimpleNamespace()
    else:
        row = target
        row.unit = unit
        row.price_group = price_group

    for settings_field, unit_base in LEGACY_UNIT_FIELD_MAP.items():
        unit_field = '{}_{}'.format(unit_base, code)
        if hasattr(unit, unit_field):
            setattr(row, settings_field, getattr(unit, unit_field))

    suffix = '_{}'.format(code)
    for field_code, _label in AUTOPRICING_BOOL_FIELDS:
        unit_field = '{}{}'.format(field_code, suffix)
        if hasattr(unit, unit_field):
            setattr(row, field_code, getattr(unit, unit_field, False))
    for field_code, _label in AUTOPRICING_AUTOHUB_FIELDS:
        unit_field = '{}{}'.format(field_code, suffix)
        if hasattr(unit, unit_field):
            setattr(row, field_code, getattr(unit, unit_field, '') or '')
    for field_code, _label in AUTOPRICING_NUMERIC_FIELDS + AUTOPRICING_MARKUP_FIELDS:
        unit_field = '{}{}'.format(field_code, suffix)
        if hasattr(unit, unit_field):
            setattr(row, field_code, getattr(unit, unit_field, None))
    eval_attr = 'eval_type{}'.format(suffix)
    if hasattr(unit, eval_attr):
        eval_val = getattr(unit, eval_attr, None)
        row.eval_type = eval_val
        row.eval_type_id = getattr(eval_val, 'pk', None)

    return row


def sync_settings_row_to_unit(unit, row, price_group_code):
    """Зеркало в плоские колонки RefUnit (для 1С), только если колонка существует."""
    from website.autopricing_settings import (
        AUTOPRICING_AUTOHUB_FIELDS,
        AUTOPRICING_BOOL_FIELDS,
        AUTOPRICING_MARKUP_FIELDS,
        AUTOPRICING_NUMERIC_FIELDS,
        mirror_autopricing_legacy_fields,
    )

    code = str(price_group_code)
    suffix = '_{}'.format(code)
    for settings_field, unit_base in LEGACY_UNIT_FIELD_MAP.items():
        unit_field = '{}_{}'.format(unit_base, code)
        if hasattr(unit, unit_field):
            setattr(unit, unit_field, getattr(row, settings_field))

    for field_code, _label in AUTOPRICING_BOOL_FIELDS:
        unit_field = '{}{}'.format(field_code, suffix)
        if hasattr(unit, unit_field):
            setattr(unit, unit_field, getattr(row, field_code))
    for field_code, _label in AUTOPRICING_AUTOHUB_FIELDS:
        unit_field = '{}{}'.format(field_code, suffix)
        if hasattr(unit, unit_field):
            setattr(unit, unit_field, getattr(row, field_code) or '')
    for field_code, _label in AUTOPRICING_NUMERIC_FIELDS + AUTOPRICING_MARKUP_FIELDS:
        unit_field = '{}{}'.format(field_code, suffix)
        if hasattr(unit, unit_field):
            setattr(unit, unit_field, getattr(row, field_code))
    eval_attr = 'eval_type{}'.format(suffix)
    if hasattr(unit, eval_attr):
        setattr(unit, eval_attr, row.eval_type)

    class _PriceGroupStub:
        def __init__(self, code_value):
            self.code = code_value

    mirror_autopricing_legacy_fields(unit, _PriceGroupStub(code))
    return unit


def create_settings_snapshot_from_unit(unit, price_group):
    """Создать новую запись истории из текущих колонок RefUnit."""
    row = copy_unit_price_range_to_settings(
        unit,
        price_group,
        target=UnitPriceGroupSettings(unit=unit, price_group=price_group),
    )
    row.save()
    return row


def create_settings_snapshots_from_unit(unit, price_groups=None):
    """Создать снимок настроек по всем (или указанным) ценовым группам."""
    groups = price_groups or get_active_price_groups()
    rows = []
    for price_group in groups:
        row = create_settings_snapshot_from_unit(unit, price_group)
        if row:
            rows.append(row)
    return rows


def copy_settings_row_to_new_record(source_row, target_unit):
    """Скопировать последнюю настройку в новую запись истории для другого ДЦ."""
    row = UnitPriceGroupSettings(
        unit=target_unit,
        price_group=source_row.price_group,
    )
    for field in source_row._meta.fields:
        name = field.name
        if name in ('id', 'unit', 'price_group', 'created_at'):
            continue
        setattr(row, name, getattr(source_row, name))
    row.save()
    return row
