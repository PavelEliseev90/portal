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


class CarCalculations(models.Model):
    
    uin                     = models.CharField("UIN", max_length=64, default='', null=True, blank=True)
    date                    = models.DateTimeField('Дата', default=datetime.now, blank=False)
    date_success            = models.DateTimeField('Дата согласования', default=datetime.now, blank=False)
    date_refresh            = models.DateTimeField('Дата обновления', default=datetime.now, blank=False)
    date_start_soglasovanie = models.DateTimeField('Дата начала согласования', default=datetime.now, blank=False)
    rejection               = models.CharField("Причина отказа", max_length=1024, null=True, blank=True)
    number              = models.CharField("Номер", max_length=15, null=True, blank=True)
    amount              = models.IntegerField("Сумма итого", default=0, null=True, blank=True)
    kvp                 = models.IntegerField("КВП", default=0, null=True, blank=True)
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


class CarCalculationsTypeDetail(models.Model):
    name =  models.CharField("Наименование", max_length=150, null=True, blank=True)

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


class KMCar(models.Model):
    date                = models.DateTimeField('Дата создания', default=datetime.now, blank=False)
    car                 = models.ForeignKey(RefCarsOrganization, on_delete=models.CASCADE, verbose_name='Автомобиль')
    km                  = models.IntegerField("КМ автомобиля", default=0, null=True, blank=True)
    km_auto_1           = models.IntegerField("КМ автомобиля авто 1", default=0, null=True, blank=True)
    km_auto_2           = models.IntegerField("КМ автомобиля авто 2", default=0, null=True, blank=True)

    def __str__(self):
        return "{} / {}".format(self.date, self.car)

    def save(self, *args, **kwargs):
        self.km = max(self.km_auto_1, self.km_auto_2)
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'km_car'
        verbose_name = "Расчетный км для автомобиля"
        verbose_name_plural = "Расчетные км для автомобилей"


