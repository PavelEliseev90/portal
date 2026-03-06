from django.db import models
from refs.models import (
    AutoruMark, AutoruModel,
    RefTypeEngine, RefTypeKpp, RefTypeBody, RefTypeEvaluationCarsOrganization,
    RefAvito, RefAvitoComplectation, RefStatusEstimation, RefMarkTyres, RefWidthTyres,
    RefProfileTyres, RefRadius, RefSezonTyres, RefTypeDisk, RefDiaDisk, RefEtDisk, RefPsdDisk,
    RefOrganization, RefFilial, RefTypeReceptionCarsOrganization, AutoruModification,
    RefGroupProduct, RefStaff, RefCategoryProduct, RefPageOcenka, RefUnit, RefCarsOrganization,
    RefEventCarsOrganization, RefStore, RefManufacturer, AutoruComplectation,
    RefStagePrice,
)


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
    km_index_rdo = models.DecimalField(
        'Индекс Км для РДО',
        max_digits=12,
        decimal_places=2,
        default=0,
        null=True,
        blank=True,
        help_text='Индекс км для РДО (число с 2 знаками после запятой)',
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
        help_text='Процент, на который изменяется минимальный Км (кумулятивная маржа)',
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
        return '{}: {}% ({} — {})'.format(' / '.join(parts), self.discount_percent, self.date_from, self.date_to)

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

