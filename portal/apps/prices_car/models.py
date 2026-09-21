from django.db import models
from refs.models import (
    AutoruMark, AutoruModel,
    RefTypeEngine, RefTypeKpp, RefTypeBody, RefTypeEvaluationCarsOrganization,
    RefAvito, RefAvitoComplectation, RefStatusEstimation, RefMarkTyres, RefWidthTyres,
    RefProfileTyres, RefRadius, RefSezonTyres, RefTypeDisk, RefDiaDisk, RefEtDisk, RefPsdDisk,
    RefOrganization, RefFilial, RefTypeReceptionCarsOrganization, AutoruModification,
    RefGroupProduct, RefStaff, RefCategoryProduct, RefPageOcenka, RefUnit, RefCarsOrganization,
    RefEventCarsOrganization, RefStore, RefManufacturer, AutoruComplectation,
    RefStagePrice, RefTypeSaleCarsOrganization,
)
from datetime import datetime, timedelta
from django.contrib.auth.models import User, Group
from documents.models import DocRLK


class PriceCarBrand(models.Model):
    """Бренд для ценообразования: объединяет марки Автору и опционально список моделей."""
    name = models.CharField('Название бренда', max_length=200)
    marks = models.ManyToManyField(
        AutoruMark,
        blank=True,
        related_name='price_car_brands',
        verbose_name='Марки Автору',
        help_text='Марки, входящие в этот бренд',
    )
    models_included = models.ManyToManyField(
        AutoruModel,
        blank=True,
        related_name='price_car_brands',
        verbose_name='Модели в бренде',
        help_text='Конкретные модели (если пусто — учитываются все модели выбранных марок)',
    )
    free_consignment_days = models.PositiveIntegerField(
        'Бесплатный срок консигнации (дней)',
        default=90,
        help_text='Срок бесплатного хранения/консигнации от импортера (в днях)',
    )
    analysis_period_days = models.PositiveIntegerField(
        'Период анализа статистики продаж (дней)',
        null=True,
        blank=True,
        help_text='Глубина выборки сделок аналогов для АвтоК в днях (если не задано — берётся общее значение)',
    )

    class Meta:
        db_table = 'prices_car_brand'
        verbose_name = 'Бренд (ценообразование)'
        verbose_name_plural = 'Бренды (ценообразование)'
        ordering = ['name']

    def __str__(self):
        return self.name


class BrandKM(models.Model):
    """Значение км по бренду на месяц."""
    brand = models.ForeignKey(
        PriceCarBrand,
        on_delete=models.CASCADE,
        related_name='km_values',
        verbose_name='Бренд',
    )
    km = models.PositiveIntegerField('Км', default=0, help_text='Значение кумулятивной маржи')
    km_min_dc = models.PositiveIntegerField(
        'Минимальное значение кумулятивной маржи ДЦ',
        default=0,
        help_text='Минимальное значение кумулятивной маржи ДЦ',
    )
    allow_dc_transfers = models.BooleanField(
        'Могут быть перемещения между ДЦ',
        default=False,
        help_text='Если включено — при подборе альтернатив с более низким КМ учитываются автомобили всех ДЦ бренда',
    )
    month = models.DateField(
        'Месяц (период)',
        help_text='Месяц, на который устанавливается значение (обычно первый день месяца, напр. 2025-02-01)',
    )

    class Meta:
        db_table = 'prices_car_brand_km'
        verbose_name = 'Км по марке на месяц'
        verbose_name_plural = 'Км по маркам на месяц'
        ordering = ['brand', '-month']
        constraints = [
            models.UniqueConstraint(fields=['brand', 'month'], name='prices_car_brand_km_brand_month_uniq'),
        ]

    def __str__(self):
        return f'{self.brand} — {self.month:%Y-%m}: {self.km} км'


class PriceCarStageKM(models.Model):
    """Индекс Км по этапу УС на месяц (этап установки цены + период + значение индекса)."""
    stage = models.ForeignKey(
        RefStagePrice,
        on_delete=models.CASCADE,
        related_name='price_car_km_indices',
        verbose_name='Этап УС',
    )
    month = models.DateField(
        'Месяц (период)',
        help_text='Месяц, на который устанавливается индекс (например, первый день месяца 2025-02-01)',
    )
    km_index = models.DecimalField(
        'Индекс Км',
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Индекс км (число с 2 знаками после запятой)',
    )

    class Meta:
        db_table = 'prices_car_stage_km'
        verbose_name = 'Индекс Км по этапу УС'
        verbose_name_plural = 'Индексы Км по этапам УС'
        ordering = ['stage', '-month']
        constraints = [
            models.UniqueConstraint(fields=['stage', 'month'], name='prices_car_stage_km_stage_month_uniq'),
        ]

    def __str__(self):
        return f'{self.stage.name} — {self.month:%Y-%m}: {self.km_index}'


class PriceCarKmDiscount(models.Model):
    """
    Дисконт Км (кумулятивная маржа): процент, на который изменяется минимальный Км.
    Привязка к бренду, модели, модификации, комплектации, году. Срок действия — от и до в рамках одного месяца.
    """
    brand = models.ForeignKey(
        PriceCarBrand,
        on_delete=models.CASCADE,
        related_name='km_discounts',
        verbose_name='Бренд',
    )
    model = models.ForeignKey(
        AutoruModel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='price_car_km_discounts',
        verbose_name='Модель',
    )
    modification = models.ForeignKey(
        AutoruModification,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='price_car_km_discounts',
        verbose_name='Модификация',
    )
    complectation = models.ForeignKey(
        AutoruComplectation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='price_car_km_discounts',
        verbose_name='Комплектация',
    )
    year = models.PositiveSmallIntegerField(
        'Год выпуска',
        null=True,
        blank=True,
        help_text='Год выпуска автомобиля (опционально)',
    )
    discount_percent = models.FloatField(
        'Процент изменения мин. Км',
        default=0.0,
        help_text='Процент, на который изменяется минимальный Км (кумулятивная маржа)',
    )
    discount_rub = models.IntegerField(
        'Скидка к Км (в рублях)',
        default=0,
        null=True,
        blank=True,
        help_text='Фиксированная сумма скидки к целевому КМ в рублях (напр. 50 000, 100 000). Можно комбинировать с процентом.',
    )
    days_consignment_left_lte = models.IntegerField(
        'Дней бесплатной консигнации осталось (<=)',
        default=None,
        null=True,
        blank=True,
        help_text='Применять дисконт только если до платной консигнации осталось не более X дней (напр. 15, 10, 0).',
    )
    is_autopilot = models.BooleanField(
        'Создано автопилотом',
        default=False,
        help_text='Создано автоматически интеллектуальным помощником Центра управления',
    )
    unit = models.ForeignKey(
        RefUnit,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='price_car_km_discounts',
        verbose_name='Подразделение ДЦ',
        help_text='Если пусто — действует для всех ДЦ бренда',
    )
    type_sale = models.ForeignKey(
        RefTypeSaleCarsOrganization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='price_car_km_discounts',
        verbose_name='Канал продажи',
        help_text='Если пусто — действует для всех каналов продаж',
    )
    is_yellow_car = models.BooleanField(
        'Только для желтых авто',
        default=False,
        help_text='Применять только к автомобилям со сданным рапортом / признаком желтого',
    )
    is_key_model = models.BooleanField(
        'Только для ключевых моделей',
        default=False,
        help_text='Применять только к ключевым моделям ДЦ на текущий месяц',
    )
    comment = models.CharField(
        'Комментарий / Обоснование',
        max_length=512,
        blank=True,
        default='',
    )
    date_from = models.DateField('Действует с')
    date_to = models.DateField('Действует по')

    class Meta:
        db_table = 'prices_car_km_discount'
        verbose_name = 'Дисконт Км'
        verbose_name_plural = 'Дисконты Км'
        ordering = ['-date_from', 'brand']

    def __str__(self):
        parts = [self.brand.name]
        if self.model:
            parts.append(self.model.name)
        if self.modification:
            parts.append(self.modification.name)
        if self.complectation:
            parts.append(self.complectation.name)
        if self.year:
            parts.append(str(self.year))
        desc = []
        if self.discount_percent:
            desc.append(f'{self.discount_percent}%')
        if self.discount_rub:
            desc.append(f'{self.discount_rub:,} ₽'.replace(',', ' '))
        disc_text = ' + '.join(desc) if desc else '0%'
        return '{}: {} ({} — {})'.format(' / '.join(parts), disc_text, self.date_from, self.date_to)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise ValidationError({'date_to': 'Дата «по» не может быть раньше даты «с».'})
            if self.date_from.month != self.date_to.month or self.date_from.year != self.date_to.year:
                raise ValidationError({'date_to': 'Срок действия должен быть в рамках одного месяца.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class DcMonthlyPlan(models.Model):
    """Планы по ДЦ и импортеру на месяц и выбранная тактика ценообразования."""
    TACTIC_MAX_MARGIN = 'max_margin'
    TACTIC_BALANCED = 'balanced'
    TACTIC_MAX_VOLUME = 'max_volume'
    TACTIC_CHOICES = (
        (TACTIC_MAX_MARGIN, 'Максимальная маржа'),
        (TACTIC_BALANCED, 'Умеренный (баланс)'),
        (TACTIC_MAX_VOLUME, 'Максимальные штуки'),
    )

    unit = models.ForeignKey(
        RefUnit,
        on_delete=models.CASCADE,
        related_name='dc_pricing_monthly_plans',
        verbose_name='Подразделение ДЦ',
    )
    month = models.DateField(
        'Месяц (период)',
        help_text='Первое число месяца, напр. 2025-09-01',
    )
    plan_dc_qty = models.PositiveIntegerField('План ДЦ, шт.', default=0)
    plan_importer_qty = models.PositiveIntegerField('План импортера, шт.', default=0)
    plan_km_rub = models.BigIntegerField(
        'План по КМ (марже), ₽',
        default=0,
        help_text='Целевой кумулятивный маржинальный доход ДЦ на месяц в рублях',
    )
    plan_revenue_rub = models.BigIntegerField(
        'План по выручке, ₽',
        default=0,
        null=True,
        blank=True,
        help_text='Целевой оборот (выручка) ДЦ на месяц в рублях',
    )
    tactic = models.CharField(
        'Тактика ДЦ',
        max_length=32,
        choices=TACTIC_CHOICES,
        default=TACTIC_BALANCED,
    )
    is_autopilot = models.BooleanField(
        'Автопилот дисконтов',
        default=False,
        help_text='Автоматически активировать и синхронизировать рекомендованные правила дисконта при отставании от темпа или рисках консигнации',
    )
    author = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name='Автор изменений',
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        db_table = 'prices_car_dc_monthly_plan'
        verbose_name = 'План ДЦ на месяц'
        verbose_name_plural = 'Планы ДЦ на месяц'
        ordering = ['-month', 'unit']
        constraints = [
            models.UniqueConstraint(fields=['unit', 'month'], name='prices_car_dc_monthly_plan_unit_month_uniq'),
        ]

    def __str__(self):
        return f'{self.unit} — {self.month:%Y-%m} (ДЦ: {self.plan_dc_qty}, Имп: {self.plan_importer_qty})'


class DcKeyModel(models.Model):
    """Ключевая / фокусная модель ДЦ на месяц."""
    plan = models.ForeignKey(
        DcMonthlyPlan,
        on_delete=models.CASCADE,
        related_name='key_models',
        verbose_name='План ДЦ',
    )
    model = models.ForeignKey(
        AutoruModel,
        on_delete=models.CASCADE,
        related_name='dc_key_models',
        verbose_name='Модель',
    )
    target_qty = models.PositiveIntegerField('Целевой объем, шт.', default=0, blank=True)
    comment = models.CharField('Комментарий', max_length=512, blank=True, default='')

    class Meta:
        db_table = 'prices_car_dc_key_model'
        verbose_name = 'Ключевая модель ДЦ на месяц'
        verbose_name_plural = 'Ключевые модели ДЦ на месяц'
        ordering = ['plan', 'model']
        constraints = [
            models.UniqueConstraint(fields=['plan', 'model'], name='prices_car_dc_key_model_plan_model_uniq'),
        ]

    def __str__(self):
        return f'{self.plan.unit} — {self.model.name} ({self.target_qty} шт.)'


class DcCommandCenterShowcase(models.Model):
    """
    Витрина данных Центра управления ДЦ (материализованный срез на месяц).
    Обеспечивает мгновенный отклик экрана мониторинга сети без повторного выполнения
    десятков тяжёлых запросов к PowerBI Cumulative, складу и движку рекомендаций.
    """
    unit = models.ForeignKey(
        RefUnit,
        on_delete=models.CASCADE,
        related_name='command_center_showcases',
        verbose_name='Подразделение ДЦ',
    )
    month = models.DateField(
        'Месяц (период)',
        help_text='Первое число месяца, напр. 2026-09-01',
        db_index=True,
    )
    updated_at = models.DateTimeField('Время обновления витрины', auto_now=True)

    # Показатели планов и штук
    plan_dc_qty = models.PositiveIntegerField('План ДЦ, шт.', default=0)
    plan_importer_qty = models.PositiveIntegerField('План импортера, шт.', default=0)
    target_plan = models.PositiveIntegerField('Целевой план (макс), шт.', default=0)
    contracts_count = models.PositiveIntegerField('Фактически законтрактовано, шт.', default=0)
    run_rate = models.FloatField('Прогноз выполнения (Run-rate), шт.', default=0.0)
    pace_pct = models.FloatField('Темп выполнения плана, %', default=0.0)
    pace_status = models.CharField('Статус темпа', max_length=32, default='no_plan')
    pace_label = models.CharField('Подпись темпа', max_length=64, default='План не задан')
    pace_class = models.CharField('CSS класс темпа', max_length=32, default='secondary')
    pace_delta_label = models.CharField('Дельта темпа', max_length=32, default='нет плана')
    gap = models.PositiveIntegerField('Отставание до плана, шт.', default=0)

    # Показатели финансов и кумулятивной маржи (КМ в рублях)
    plan_km_rub = models.BigIntegerField('План по КМ, ₽', default=0)
    plan_revenue_rub = models.BigIntegerField('План по выручке, ₽', default=0)
    fact_km = models.BigIntegerField('Факт КМ, ₽', default=0)
    fact_revenue = models.BigIntegerField('Факт выручки, ₽', default=0)
    km_run_rate = models.BigIntegerField('Прогноз КМ (Run-rate), ₽', default=0)
    km_pace_pct = models.FloatField('Темп выполнения КМ, %', default=0.0)
    quadrant_key = models.CharField('Ключ квадранта', max_length=32, default='no_money_plan')
    quadrant_label = models.CharField('Название квадранта', max_length=64, default='План КМ не задан')
    quadrant_badge_class = models.CharField('CSS класс квадранта', max_length=32, default='secondary')
    quadrant_desc = models.CharField('Описание квадранта', max_length=255, blank=True, default='')

    # Склад и риски
    stock_total = models.PositiveIntegerField('Всего новых авто на складе', default=0)
    yellow_count = models.PositiveIntegerField('Желтые авто (>45 дн)', default=0)
    consignment_overdue = models.PositiveIntegerField('Просроченная консигнация (>90 дн)', default=0)
    consignment_warning = models.PositiveIntegerField('Подходит срок консигнации (75-90 дн)', default=0)
    missed_count = models.PositiveIntegerField('Упущенные сделки (РЛК/отказы)', default=0)

    # Тактика ценообразования и автопилот
    is_autopilot = models.BooleanField('Автопилот дисконтов', default=False)
    autopilot_rules_count = models.PositiveIntegerField('Активных правил автопилота', default=0)
    tactic = models.CharField('Тактика ДЦ', max_length=32, default='balanced')
    tactic_label = models.CharField('Название тактики', max_length=64, default='Сбалансированная')

    # Рекомендации Smart Advisor
    recs_count = models.PositiveIntegerField('Количество рекомендаций', default=0)
    has_recs = models.BooleanField('Есть рекомендации', default=False)
    needs_attention = models.BooleanField('Требует внимания', default=False)
    top_rec_title = models.CharField('Заголовок главной рекомендации', max_length=255, blank=True, default='')
    top_rec_badge = models.CharField('Бейдж главной рекомендации', max_length=64, blank=True, default='')
    top_rec_badge_class = models.CharField('CSS класс главной рекомендации', max_length=32, blank=True, default='')
    recommendations_json = models.JSONField('Рекомендации (JSON)', default=list, blank=True)

    class Meta:
        db_table = 'prices_car_dc_command_center_showcase'
        verbose_name = 'Витрина Центра управления ДЦ'
        verbose_name_plural = 'Витрины Центра управления ДЦ'
        ordering = ['unit__city__name', 'unit__name']
        constraints = [
            models.UniqueConstraint(fields=['unit', 'month'], name='prices_car_dc_showcase_unit_month_uniq'),
        ]

    def __str__(self):
        return f'Витрина {self.unit} — {self.month:%Y-%m} (Шт: {self.contracts_count}/{self.target_plan}, КМ: {self.fact_km}/{self.plan_km_rub})'


class CarCalculations(models.Model):
    
    uin                     = models.CharField("UIN", max_length=64, default='', null=True, blank=True)
    date                    = models.DateTimeField('Дата', default=datetime.now, blank=False)
    date_success            = models.DateTimeField('Дата согласования', default=datetime.now, blank=False)
    date_refresh            = models.DateTimeField('Дата обновления', default=datetime.now, blank=False)
    date_start_soglasovanie = models.DateTimeField(
        'Дата начала согласования',
        null=True,
        blank=True,
        default=None,
        help_text='Заполняется при подтверждении отправки на согласование из 1С.',
    )
    rejection               = models.CharField("Причина отказа", max_length=1024, null=True, blank=True)
    number              = models.CharField("Номер", max_length=15, null=True, blank=True)
    amount              = models.IntegerField("Сумма итого", default=0, null=True, blank=True)
    kvp                 = models.IntegerField("КВП", default=0, null=True, blank=True)
    km_raschet          = models.IntegerField("Расчетный КМ", null=True, blank=True)
    author              = models.ForeignKey(RefStaff, null=True, related_name='car_calculation_author', on_delete=models.SET_NULL, verbose_name='Пользователь')
    staff               = models.ForeignKey(RefStaff, null=True, related_name='car_calculation_staff', on_delete=models.SET_NULL, verbose_name='Пользователь')
    
    rlk                 = models.ForeignKey(DocRLK, on_delete=models.CASCADE, verbose_name='Рабочий лист', null=True, blank=True)
    unit                = models.ForeignKey(RefUnit, on_delete=models.CASCADE, verbose_name='Подразделение', null=True, blank=True)    
    
    car = models.ForeignKey(
        RefCarsOrganization,
        on_delete=models.CASCADE,
        related_name='car',
        verbose_name='Автомобиль',
        null=True, 
        blank=True
    )
    
    user            = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, verbose_name='Пользователь')
    discount        = models.IntegerField("Скидка", default=0, null=True, blank=True) 
    price           = models.IntegerField("Цена автомобиля", default=0, null=True, blank=True)
    
    custom_opfu     = models.IntegerField("ОПФУ", default=0, null=True, blank=True)
    custom_tradein  = models.IntegerField("ТрейдИн", default=0, null=True, blank=True)
    custom_wheels   = models.IntegerField("Колеса", default=0, null=True, blank=True)
    custom_grz      = models.IntegerField("Гос. регистрация", default=0, null=True, blank=True)
    custom_work     = models.IntegerField("Работы", default=0, null=True, blank=True)
    custom_product  = models.IntegerField("Товары", default=0, null=True, blank=True)

    comment    = models.CharField("Текст", max_length=2048, default='', null=True, blank=True)

    SOGLASOVANIE_PENDING = 'pending'
    SOGLASOVANIE_AWAITING_1C = 'awaiting_1c'
    SOGLASOVANIE_DIRECTOR_APPROVED = 'director_approved'
    SOGLASOVANIE_PENDING_UK = 'pending_uk'
    SOGLASOVANIE_UK_APPROVED = 'uk_approved'
    SOGLASOVANIE_DIRECTOR_REJECTED = 'director_rejected'
    SOGLASOVANIE_UK_REJECTED = 'uk_rejected'
    UK_APPROVAL_BASIS_MANUAL = 'manual'
    UK_APPROVAL_BASIS_PRIOR_THRESHOLD = 'prior_threshold'
    UK_APPROVAL_BASIS_CHOICES = (
        (UK_APPROVAL_BASIS_MANUAL, 'Ручное согласование УК'),
        (UK_APPROVAL_BASIS_PRIOR_THRESHOLD, 'Ранее согласованный минимальный КВП УК'),
    )
    SOGLASOVANIE_STATUS_CHOICES = (
        (SOGLASOVANIE_AWAITING_1C, 'Ожидает подтверждения из 1С'),
        (SOGLASOVANIE_PENDING, 'Ожидает директора ДЦ'),
        (SOGLASOVANIE_DIRECTOR_APPROVED, 'Согласовано директором ДЦ'),
        (SOGLASOVANIE_PENDING_UK, 'На согласовании УК'),
        (SOGLASOVANIE_UK_APPROVED, 'Согласовано УК'),
        (SOGLASOVANIE_DIRECTOR_REJECTED, 'Отказ директора ДЦ'),
        (SOGLASOVANIE_UK_REJECTED, 'Отказ УК'),
    )
    soglasovanie_status = models.CharField(
        "Статус согласования",
        max_length=32,
        choices=SOGLASOVANIE_STATUS_CHOICES,
        default=SOGLASOVANIE_PENDING,
        blank=True,
    )
    director_approve_user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='calc_director_approvals',
        verbose_name='Согласовал директор',
    )
    director_approve_date = models.DateTimeField(
        'Дата согласования директором',
        null=True,
        blank=True,
    )
    director_approve_comment = models.CharField(
        "Комментарий директора",
        max_length=2048,
        default='',
        null=True,
        blank=True,
    )
    uk_approve_user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='calc_uk_approvals',
        verbose_name='Согласовал УК',
    )
    uk_approve_date = models.DateTimeField(
        'Дата согласования УК',
        null=True,
        blank=True,
    )
    uk_approve_comment = models.CharField(
        "Комментарий УК",
        max_length=2048,
        default='',
        null=True,
        blank=True,
    )
    uk_approval_basis = models.CharField(
        'Основание согласования УК',
        max_length=32,
        choices=UK_APPROVAL_BASIS_CHOICES,
        default='',
        blank=True,
    )
    uk_approval_threshold_kvp = models.IntegerField(
        'Применённый минимальный КВП УК',
        null=True,
        blank=True,
    )
    uk_approval_reference = models.ForeignKey(
        'CarCalculationUkApproval',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='derived_calculations',
        verbose_name='Основание из истории согласований УК',
    )

    active = models.BooleanField(
        'Активное КП по рабочему листу',
        default=True,
    )
    inactive_reason = models.CharField(
        'Причина неактивности',
        max_length=512,
        default='',
        blank=True,
    )

    def detail(self):
        from prices_car.models import CarCalculationsDetail
        return CarCalculationsDetail.objects.filter(calculation = self).order_by('-detail_type__name')
    
    class Meta:
        db_table = 'carCalculations'
        verbose_name = 'Калькуляции автомобиля'
        verbose_name_plural = 'Калькуляции автомобилей'
        ordering = ['-date', 'car']

    def __str__(self):
        return "{} {}".format(self.car, self.date)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class CarCalculationUkApproval(models.Model):
    """Неизменяемый снимок ручного согласования УК для повторных КП."""

    calculation = models.OneToOneField(
        CarCalculations,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='manual_uk_approval_snapshot',
        verbose_name='Исходное коммерческое предложение',
    )
    rlk = models.ForeignKey(
        DocRLK,
        on_delete=models.CASCADE,
        related_name='car_calculation_uk_approvals',
        verbose_name='Рабочий лист',
    )
    car = models.ForeignKey(
        RefCarsOrganization,
        on_delete=models.CASCADE,
        related_name='calculation_uk_approvals',
        verbose_name='Автомобиль',
    )
    approved_kvp = models.IntegerField('Согласованный КВП')
    approved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='manual_car_calculation_uk_approvals',
        verbose_name='Согласовал УК',
    )
    approved_at = models.DateTimeField('Дата ручного согласования УК')
    comment = models.CharField(
        'Комментарий УК',
        max_length=2048,
        default='',
        blank=True,
    )
    created_at = models.DateTimeField('Дата фиксации', auto_now_add=True)

    class Meta:
        db_table = 'carCalculationUkApproval'
        verbose_name = 'Ручное согласование КВП управляющей компанией'
        verbose_name_plural = 'Ручные согласования КВП управляющей компанией'
        ordering = ['approved_kvp', '-approved_at', 'pk']
        indexes = [
            models.Index(
                fields=['rlk', 'car', 'approved_kvp'],
                name='calc_uk_rlk_car_kvp_idx',
            ),
        ]

    def __str__(self):
        return '{} / {} / КВП {}'.format(self.rlk, self.car, self.approved_kvp)


class CarCalculationsTypeDetail(models.Model):
    name = models.CharField("Наименование", max_length=150, null=True, blank=True)
    is_trade_in = models.BooleanField(
        "Показатель трейд-ин",
        default=False,
        help_text='Если включено — применение этого показателя в КП влияет на выбор расчётного КМ (АвтоК с trade-in)',
    )

    class Meta:
        db_table = 'сarCalculationsTypeDetail'
        verbose_name = 'Калькуляции автомобиля детально типы'
        verbose_name_plural = 'Калькуляции автомобилей детально типы' 
        ordering = ['name']

    def __str__(self):
        return "{}".format(self.name)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class CarCalculationsDetail(models.Model):
    
    calculation     = models.ForeignKey(CarCalculations, null=True, on_delete=models.SET_NULL, verbose_name='Калькуляция')
    detail_type     = models.ForeignKey(CarCalculationsTypeDetail, null=True, on_delete=models.SET_NULL, verbose_name='Показатель')
    success         = models.BooleanField("Применено", default = False, null=True, blank=True)
    amount          = models.IntegerField("Сумма", default=0, null=True, blank=True)
    vp              = models.IntegerField("Валовая прибыль", default=0, null=True, blank=True)
    pocazatel       = models.IntegerField("Показатель", default=0, null=True, blank=True)
    amount_k        = models.IntegerField("Сумма с коэфицентом", default=0, null=True, blank=True)

    class Meta:
        db_table = 'carCalculationsDetail'
        verbose_name = 'Калькуляции автомобиля детально'
        verbose_name_plural = 'Калькуляции автомобилей детально'
        ordering = ['calculation']

    def __str__(self):
        return "{} {}".format(self.calculation, self.detail_type)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        
class CarCalculationsListSettings(models.Model):
    """Персональные настройки столбцов списка калькуляций."""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='car_calculations_list_settings',
        verbose_name='Пользователь',
    )
    columns = models.JSONField(
        'Столбцы',
        default=list,
        blank=True,
        help_text='Упорядоченный список ключей видимых столбцов',
    )
    compare_km_kvp = models.BooleanField(
        'Сравнивать расчетный КМ с КВ',
        default=True,
    )
    highlight_km_below_kvp = models.BooleanField(
        'Подсвечивать строки, где расчетный КМ ниже КВ',
        default=True,
    )

    class Meta:
        db_table = 'prices_car_calc_list_settings'
        verbose_name = 'Настройки таблицы калькуляций'
        verbose_name_plural = 'Настройки таблиц калькуляций'

    def __str__(self):
        return 'Таблица калькуляций — %s' % self.user


class EmailPushCar(models.Model):
    date                = models.DateTimeField('Дата создания', default=datetime.now, blank=False)
    car                 = models.ForeignKey(RefCarsOrganization, on_delete=models.CASCADE, related_name='email_push_car', verbose_name='Автомобиль')
    user                = models.ForeignKey(User, related_name="emailpushcar_user", on_delete=models.SET_NULL, null=True, verbose_name="Пользователь")
    email               = models.CharField("Email", max_length=2048, default='', null=True, blank=True)
    comment             = models.CharField("Текст", max_length=2048, default='', null=True, blank=True) 
    send                = models.BooleanField("Отправлено", default = False, null=True, blank=True)
    price               = models.BooleanField("Ценообразование", default = False, null=True, blank=True)
    calc                = models.ForeignKey(CarCalculations, on_delete=models.CASCADE, related_name='calc', verbose_name='Калькуляция', null=True, blank=True)
    
    def __str__(self):
        return "{} / {}".format(self.car, self.user)

    class Meta:
        db_table = 'emailPushCar'
        verbose_name = "Оповещения по автомобилям"
        verbose_name_plural = "Оповещения по автомобилям"


class DealCalcTelegramSettings(models.Model):
    """
    Настройки Telegram-уведомлений по согласованию КП.
    Singleton: в админке должна быть одна запись. По умолчанию выключено.
    """
    enabled = models.BooleanField(
        'Включить Telegram по КП',
        default=False,
        help_text='Параллельно email. Ошибки Telegram не влияют на почту и согласование.',
    )
    bot_token = models.CharField(
        'Токен бота',
        max_length=256,
        blank=True,
        default='',
        help_text='Если пусто — берётся DEAL_CALC_TELEGRAM_BOT_TOKEN из окружения.',
    )
    chat_ids = models.CharField(
        'Общие chat ID (через запятую)',
        max_length=512,
        blank=True,
        default='',
        help_text='Опциональный тестовый/общий канал. Личные уведомления — '
                  'через telegram_chat_id в профиле пользователя. '
                  'Если пусто — DEAL_CALC_TELEGRAM_CHAT_IDS из окружения.',
    )
    bot_username = models.CharField(
        'Username бота (без @)',
        max_length=128,
        blank=True,
        default='',
        help_text='Для подсказки в профиле: ссылка t.me/…',
    )
    webhook_secret = models.CharField(
        'Секрет webhook',
        max_length=128,
        blank=True,
        default='',
        help_text='Заголовок X-Telegram-Bot-Api-Secret-Token. '
                  'Сгенерируется при сохранении, если пусто.',
    )
    api_proxy = models.CharField(
        'Прокси для api.telegram.org',
        max_length=512,
        blank=True,
        default='',
        help_text='Если с сервера нет доступа к Telegram: '
                  'http://host:port или http://user:pass@host:port. '
                  'Пусто — DEAL_CALC_TELEGRAM_PROXY из окружения.',
    )
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        db_table = 'prices_car_deal_calc_telegram_settings'
        verbose_name = 'Telegram: согласование КП'
        verbose_name_plural = 'Telegram: согласование КП'

    def __str__(self):
        return 'Telegram КП: {}'.format('вкл' if self.enabled else 'выкл')

    def save(self, *args, **kwargs):
        self.pk = 1
        if not (self.webhook_secret or '').strip():
            import secrets
            self.webhook_secret = secrets.token_urlsafe(24)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class DealCalcTelegramPendingAction(models.Model):
    """Ожидание комментария от пользователя в Telegram после нажатия кнопки."""
    chat_id = models.CharField('Chat ID', max_length=64, db_index=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='deal_calc_telegram_pending',
        verbose_name='Пользователь',
    )
    calc = models.ForeignKey(
        CarCalculations,
        on_delete=models.CASCADE,
        related_name='telegram_pending_actions',
        verbose_name='КП',
    )
    action = models.CharField('Действие', max_length=64)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        db_table = 'prices_car_deal_calc_telegram_pending'
        verbose_name = 'Telegram: ожидание комментария КП'
        verbose_name_plural = 'Telegram: ожидания комментария КП'

    def __str__(self):
        return '{} {} calc={}'.format(self.chat_id, self.action, self.calc_id)


class KMCar(models.Model):
    date                = models.DateTimeField('Дата создания', default=datetime.now, blank=False)
    car                 = models.ForeignKey(RefCarsOrganization, on_delete=models.CASCADE, verbose_name='Автомобиль')
    km                  = models.IntegerField("КМ автомобиля", default=0, null=True, blank=True)
    km_auto_1           = models.IntegerField("КМ автомобиля авто 1", default=0, null=True, blank=True)
    km_auto_2           = models.IntegerField("КМ автомобиля авто 2", default=0, null=True, blank=True)
    km_auto_3           = models.IntegerField("КМ автомобиля спец. условие", default=0, null=True, blank=True)
    km_auto_k           = models.IntegerField("КМ АвтоК без trade-in", default=0, null=True, blank=True)
    km_auto_k_tradein   = models.IntegerField("КМ АвтоК с trade-in", default=0, null=True, blank=True)
    km_auto_6           = models.IntegerField("КМ Вариант 6 (Smart АвтоК)", default=0, null=True, blank=True)
    km_manual           = models.IntegerField("КМ ручной (min_km)", default=0, null=True, blank=True)
    type_km             = models.SmallIntegerField("Тип итогового КМ", default=0, null=True, blank=True)

    def __str__(self):
        return "{} / {}".format(self.date, self.car)

    def save(self, *args, **kwargs):
        from prices_car.km_car import resolve_km_car_total

        total, type_km = resolve_km_car_total(
            self.km_manual, self.km_auto_1, self.km_auto_2, self.km_auto_3,
            self.km_auto_k, self.km_auto_k_tradein, km_auto_6=self.km_auto_6,
        )
        self.km = total
        self.type_km = type_km
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'km_car'
        verbose_name = "Расчетный км для автомобиля"
        verbose_name_plural = "Расчетные км для автомобилей"


class PriceCarAlgorithmSettings(models.Model):
    """Глобальные параметры алгоритма ценообразования и расчёта АвтоК."""
    analysis_period_days = models.PositiveIntegerField(
        'Период анализа статистики продаж по умолчанию (дней)',
        default=60,
        help_text='Глубина выборки розничных продаж аналогов (в днях) для алгоритма АвтоК',
    )
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        db_table = 'prices_car_algorithm_settings'
        verbose_name = 'Настройки алгоритма ценообразования'
        verbose_name_plural = 'Настройки алгоритма ценообразования'

    def __str__(self):
        return f'Настройки алгоритма (анализ: {self.analysis_period_days} дн.)'

    @classmethod
    def get_settings(cls):
        obj = cls.objects.first()
        if not obj:
            obj, _ = cls.objects.get_or_create(pk=1, defaults={'analysis_period_days': 60})
        return obj

    @classmethod
    def get_default_analysis_days(cls) -> int:
        try:
            settings_obj = cls.get_settings()
            return int(settings_obj.analysis_period_days or 60)
        except Exception:
            return 60



