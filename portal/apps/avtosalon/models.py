from django.db import models
from django.db.models import Avg, Max, Min, Sum, F
from datetime import datetime
from refs.models import RefUnit, AutoruModification, AutoruComplectation, RefCarsOrganization
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
import uuid
import random
import json
from django.contrib.postgres.fields import ArrayField


class RefreshSpecificationsAutoRU(models.Model):
    date                = models.DateTimeField('Дата обновления', default=datetime.now, blank=False)
    modification        = models.ForeignKey(AutoruModification, null=True, on_delete=models.SET_NULL, verbose_name="Модификация")
    complectation       = models.ForeignKey(AutoruComplectation, null=True, on_delete=models.SET_NULL, verbose_name="Комплектация")
    
    def __str__(self):
        return "{} / {} / {}".format(self.date, self.modification, self.complectation)

    class Meta:
        db_table = 'refreshSpecificationsAutoRU'
        verbose_name = "Обновление технических характеристик модификаций авто ру"
        verbose_name_plural = "Обновления технических характеристик модификаций авто ру"


class RefreshCarsLog(models.Model):
    date                = models.DateTimeField('Дата обновления', default=datetime.now, blank=False)
    unit                = models.ForeignKey(RefUnit, on_delete=models.SET_NULL, null=True, verbose_name="Подразделение ДЦ") 
    count_add           = models.IntegerField('Добавлено', default=0, null=False, blank=False) 
    count_del           = models.IntegerField('Удалено', default=0, null=False, blank=False) 
    count_stock         = models.IntegerField('Автомобилей активно', default=0, null=False, blank=False) 

    def __str__(self):
        return "{} / {} ({} - {})".format(self.date, self.unit, self.count_add, self.count_del)

    class Meta:
        db_table = 'refreshCarsLog'
        verbose_name = 'Лог загрузки данных'
        verbose_name_plural = "Логи загрузок данных"


class AvtohubModifications(models.Model):
    id_avtohub                  = models.IntegerField('id', default=0, null=False, blank=False)
    brandId                     = models.IntegerField('brandId', default=0, null=False, blank=False)
    modelId                     = models.IntegerField('modelId', default=0, null=False, blank=False)
    generationId                = models.IntegerField('generationId', default=0, null=False, blank=False)
    bodyConfigurationId         = models.IntegerField('bodyConfigurationId', default=0, null=False, blank=False)
    name                        = models.CharField('name',  default='', null=True, max_length=250, blank=True)  
    autoruId                    = models.IntegerField('autoruId', default=0, null=False, blank=False)
    yearFrom                    = models.IntegerField('yearFrom', default=0, null=False, blank=False)
    yearTo                      = models.IntegerField('yearTo', default=0, null=False, blank=False)
    bodyType                    = models.CharField('bodyType',  default='', null=True, max_length=250, blank=True)  
    bodyDoorCount               = models.IntegerField('bodyDoorCount', default=0, null=False, blank=False)
    engineType                  = models.CharField('engineType',  default='', null=True, max_length=250, blank=True)  
    engineVolume                = models.IntegerField('engineVolume', default=0, null=False, blank=False)
    enginePower                 = models.IntegerField('enginePower', default=0, null=False, blank=False)
    driveType                   = models.CharField('driveType',  default='', null=True, max_length=250, blank=True)  
    gearboxType                 = models.CharField('gearboxType',  default='', null=True, max_length=250, blank=True)  
    gearboxGearCount            = models.IntegerField('gearboxGearCount', default=0, null=False, blank=False)
    isActive                    = models.BooleanField('isActive', default=False, null=False, blank=False)
    
    def __str__(self):
        return "{} / {} / {}".format(self.id, self.vin, self.dealer_name)

    class Meta:
        indexes = [
            models.Index(fields=['id_avtohub']),
            models.Index(fields=['autoruId'])
        ]
        db_table = 'avtohubModifications'
        verbose_name = 'Автохаб модификации'
        verbose_name_plural = "Автохаб - https://api.maxposter.ru/partners-api/directories/vehicle-modifications"


class AvtohubGroupOptions(models.Model):
    id_avtohub                  = models.IntegerField('id', default=0, null=False, blank=False)
    name                        = models.CharField('name',  default='', null=True, max_length=250, blank=True)  
    sortOrder                   = models.IntegerField('sortOrder', default=0, null=False, blank=False)
    
    def __str__(self):
        return "{} / {}".format(self.id_avtohub, self.name)

    class Meta:
        indexes = [
            models.Index(fields=['id_avtohub'])
        ]
        db_table = 'avtohubGroupOptions'
        verbose_name = 'Автохаб группы опций'
        verbose_name_plural = "Автохаб группа опций- https://api.maxposter.ru/partners-api/directories/vehicle-equipment-groups"


class AvtohubOptions(models.Model):
    id_avtohub                  = models.IntegerField('id', default=0, null=False, blank=False)
    name                        = models.CharField('name',  default='', null=True, max_length=250, blank=True)  
    sortOrder                   = models.IntegerField('sortOrder', default=0, null=False, blank=False)
    groupId                     = models.ForeignKey(AvtohubGroupOptions, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Группа опций")
    keyEquipment                = models.BooleanField("Ключевая опция",  default=False, null=True) 
    include                     = ArrayField(models.IntegerField(null=True, blank=True), null=True, blank=True)
    exclude                     = ArrayField(models.IntegerField(null=True, blank=True), null=True, blank=True)

    def __str__(self):
        return "{} / {}".format(self.id_avtohub, self.name)

    class Meta:
        indexes = [
            models.Index(fields=['id_avtohub'])
        ]
        db_table = 'avtohubOptions'
        verbose_name = 'Автохаб опции'
        verbose_name_plural = "Автохаб опции- https://api.maxposter.ru/partners-api/directories/vehicle-equipment"


class AvtohubComplectations(models.Model):
    id_avtohub                  = models.IntegerField('id', default=0, null=False, blank=False)
    name                        = models.CharField('name',  default='', null=True, max_length=250, blank=True)  
    brandId                     = models.IntegerField('brandId', default=0, null=False, blank=False)
    modelId                     = models.IntegerField('modelId', default=0, null=False, blank=False)
    generationId                = models.IntegerField('generationId', default=0, null=False, blank=False)
    modificationId              = models.IntegerField('modificationId', default=0, null=False, blank=False)
    bodyConfigurationId         = models.IntegerField('bodyConfigurationId', default=0, null=False, blank=False)
    autoruId                    = models.IntegerField('autoruId', default=0, null=True, blank=False)
    isActive                    = models.BooleanField('isActive', default=False, null=False, blank=False)
    equipment                   = models.ManyToManyField(AvtohubOptions, verbose_name='Опции', blank=True)

    def __str__(self):
        return "{} / {}".format(self.id_avtohub, self.name)

    class Meta:
        indexes = [
            models.Index(fields=['id_avtohub']),
            models.Index(fields=['autoruId'])
        ]
        db_table = 'avtohubComplectations'
        verbose_name = 'Автохаб комплектации'
        verbose_name_plural = "Автохаб комплектации - https://api.maxposter.ru/partners-api/directories/vehicle-complectations"


class Avtohub(models.Model):
    date                = models.DateTimeField('date - dateTimeField - Дата запроса', default=datetime.now, blank=False)
    id_vencle           = models.IntegerField('id - integer - ID объявления', default=0, null=False, blank=False) 
    uin                 = models.CharField('uin - string Nullable - Учетный номер в интерфейсе', default='', null=True, max_length=150, blank=False) 
    vin                 = models.CharField('vin - string Nullable - VIN', default='', null=True, max_length=20, blank=False) 
    price               = models.IntegerField("price - integer Nullable - Цена ", default=0, blank=True)
    dealer_name         = models.CharField('companyName - string Nullable - Название автосалона', default='', null=True, max_length=150, blank=True)
    type                = models.CharField("type - Enum: used / new - Новое или подержанное ТС",  default='', null=True, max_length=150, blank=True)    
    year                = models.IntegerField("year - integer Nullable - Год выпуска",  default=0, null=False, blank=True)
    mileage             = models.IntegerField("mileage - integer Nullable - Пробег",  default=0, null=False, blank=True)
    isInSale            = models.BooleanField("isInSale - boolean - Авто /в продаже/",  default=False, null=False, blank=False)
    daysInStock         = models.IntegerField("daysInStock - integer Nullable - Дней на складе",  default=0, null=False, blank=True)
    daysInSale          = models.IntegerField("daysInSale - integer Nullable - Дней в продаже",  default=0, null=False, blank=True)
    maxposterSaleCost   = models.IntegerField("maxposterSaleCost - integer Nullable - Прогнозная цена продажи MaxPoster",  default=0, null=False, blank=True)
    avgMarketPrice      = models.IntegerField("avgMarketPrice - integer Nullable - Среднерыночная цена",  default=0, null=False, blank=True)
    imv                 = models.IntegerField("imv - integer Nullable - Авито оценка",  default=0, null=False, blank=True)
    vRatingPosition     = models.IntegerField("vRatingPosition - integer Nullable - Позиция по привлекательности",  default=0, null=False, blank=True)
    numberOfCompetitors = models.IntegerField("numberOfCompetitors - integer Nullable - Количество конкурентов",  default=0, null=False, blank=True)
    
    actualMarketSales       = models.IntegerField("actualMarketSales - integer - Количество авто на рынке",  default=0, null=False, blank=True)
    averageSalePeriod       = models.IntegerField("averageSalePeriod - integer - Среднее время продажи автомобиля (на данный момент рассчитывается только для сделок)",  default=0, null=False, blank=True)
    averageMarketMileage    = models.IntegerField("averageMarketMileage - integer - Средний пробег аналогичных ТС",  default=0, null=False, blank=True)
    averageDaysInSale       = models.IntegerField("averageDaysInSale - integer - Среднее количество дней в продаже",  default=0, null=False, blank=True)
    totalMarketSales        = models.IntegerField("totalMarketSales - integer - Количество уникальных предложений за 60 дней",  default=0, null=False, blank=True)
    totalMarketSales90      = models.IntegerField("totalMarketSales90 - integer - Количество уникальных предложений за 90 дней",  default=0, null=False, blank=True)

    totalAdvertisingCost    = models.FloatField("totalAdvertisingCost - number <float> Nullable - Реклама итого, ₽", default=0.0, blank=True)
    placementOnAutoru   = models.FloatField("placementOnAutoru - number <float> Nullable - Размещение на auto.ru, ₽", default=0.0, blank=True)
    promotionOnAutoru   = models.FloatField("promotionOnAutoru - number <float> Nullable - Продвижение на auto.ru, ₽", default=0.0, blank=True)
    placementOnAvito    = models.FloatField("placementOnAvito - number <float> Nullable - Размещение на avito.ru, ₽", default=0.0, blank=True)
    promotionOnAvito    = models.FloatField("promotionOnAvito - number <float> Nullable - Продвижение на avito.ru, ₽", default=0.0, blank=True)
    placementOnDrom     = models.FloatField("placementOnDrom - number <float> Nullable - Размещение на drom.ru, ₽", default=0.0, blank=True)
    promotionOnDrom     = models.FloatField("promotionOnDrom - number <float> Nullable - Продвижение на drom.ru, ₽", default=0.0, blank=True)

    callsCounts_uniqueTotal = models.IntegerField("callsCounts / uniqueTotal - integer - Всего уникальных звонков",  default=0, null=False, blank=True)	
    callsCounts_uniqueTotalAutoru = models.IntegerField("callsCounts / uniqueTotalAutoru - integer - Уникальных звонков auto.ru",  default=0, null=False, blank=True)	
    callsCounts_uniqueTotalAvito = models.IntegerField("callsCfounts / uniqueTotalAvito - integer - Уникальных звонков avito.ru",  default=0, null=False, blank=True)	
    callsCounts_uniqueTotalDrom = models.IntegerField("callsCounts / uniqueTotalDrom - integer - Уникальных звонков drom.ru",  default=0, null=False, blank=True)	

    chatsCounts_uniqueTotal = models.IntegerField("chatsCounts / uniqueTotal - integer - Всего актуальных уникальных чатов",  default=0, null=False, blank=True)
    chatsCounts_uniqueTotalAutoru = models.IntegerField("chatsCounts / uniqueTotalAutoru - integer - Уникальных чатов auto.ru",  default=0, null=False, blank=True)
    chatsCounts_uniqueTotalAvito = models.IntegerField("chatsCounts / uniqueTotalAvito - integer - Уникальных чатов avito.ru",  default=0, null=False, blank=True)
    chatsCounts_uniqueTotalDrom = models.IntegerField("chatsCounts / uniqueTotalDrom - integer - Уникальных чатов drom.ru",  default=0, null=False, blank=True)

    avitoViews  = models.IntegerField("viewStatistics / avitoViews - integer - Количество просмотров avito.ru",  default=0, null=False, blank=True)
    autoruViews = models.IntegerField("viewStatistics / autoruViews - integer - Количество просмотров auto.ru",  default=0, null=False, blank=True)
    dromViews   = models.IntegerField("viewStatistics / dromViews - integer - Количество просмотров drom.ru",  default=0, null=False, blank=True)
   
    autotekaReportWeb   = models.CharField("autotekaReportLinks / web - string - Ссылка на веб версию отчета", default='', null=True, max_length=1500, blank=False)
    autotekaReportPdf   = models.CharField("autotekaReportLinks / pdf - string - Ссылка на PDF версию отчета", default='', null=True, max_length=1500, blank=False)
    
    def get_type(self):
        if self.type == None:
            return '-'
        return self.type

    def save(self, *args, **kwargs):
        try:
            if self.price == None:
                    self.price = 0
        except:
            self.price = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return "{} / {} / {}".format(self.date, self.vin, self.dealer_name)

    class Meta:
        indexes = [
            models.Index(fields=['vin']),
            models.Index(fields=['date'])
        ]
        db_table = 'avtohub'
        verbose_name = 'Автохаб'
        verbose_name_plural = "Автохаб - https://api.maxposter.ru/partners-api-docs/docs.html - vehicles"


class AvtohubSite(models.Model):
    id_site     = models.IntegerField('id - integer - Идентификатор сайта', default=0, null=False, blank=False) 
    name        = models.CharField('name - string - Название сайта', default='', null=True, max_length=150, blank=False) 
     
    def __str__(self):
        return "{} / {}".format(self.id_site, self.name)

    class Meta:
        db_table = 'avtohubSite'
        verbose_name = 'Автохаб сайты'
        verbose_name_plural = "Автохаб сайты - https://api.maxposter.ru/partners-api-docs/docs.html - vehicles - Array of objects (VehicleSiteState)"


class AvtohubSiteInfo(models.Model):
    date                = models.DateTimeField('date - dateTimeField - Дата запроса', default=datetime.now, blank=False)
    id_vencle           = models.IntegerField('id - integer - ID объявления', default=0, null=False, blank=False) 
    uin                 = models.CharField('uin - string Nullable - Учетный номер в интерфейсе', default='', null=True, max_length=150, blank=False) 
    vin                 = models.CharField('vin - string Nullable - VIN', default='', null=True, max_length=20, blank=False) 
    site                = models.ForeignKey(AvtohubSite, on_delete=models.SET_NULL, null=True, verbose_name="Автомобиль")  
    externalState       = models.CharField('externalState - string Nullable - Статус', default='', null=True, max_length=150, blank=False) 
    externalURL         = models.CharField('externalURL - string Nullable - URL объявления', default='', null=True, max_length=150, blank=False) 
    firstPublishedAt    = models.CharField('firstPublishedAt - 	string <date-time> Nullable - Дата и время первой публикации', default='', null=True, max_length=150, blank=False) 
    hasProblems         = models.BooleanField("hasProblems - boolean - Имеются проблемы в объявлении",  default=False, null=True)
    
    def __str__(self):
        return "{} / {}".format(self.date, self.vin)

    class Meta:
        indexes = [
            models.Index(fields=['vin']),
            models.Index(fields=['site'])
        ]
        db_table = 'avtohubSiteInfo'
        verbose_name = 'Автохаб- информация по объявлениеям на сайтах'
        verbose_name_plural = "Автохаб информация по объявлениеям на сайтах' - https://api.maxposter.ru/partners-api-docs/docs.html - vehicles"


class Autoteka_signal_last_id(models.Model):
    last_id  = models.IntegerField("ИД региона", default=0, blank=True)
    
    def __str__(self):
        return "{}".format(self.last_id)

    class Meta:
        db_table = 'autoteka_signal_last_id'
        verbose_name = 'Сигнал автотека - последний id'
        verbose_name_plural = "Сигнал автотека последний ид - https://developers.avito.ru/api-catalog/autoteka/documentation#operation/monitoringBucketAdd - get-leads"


class Autoteka_signal_region(models.Model):
    name                 = models.CharField('Наименование', default='', null=True, max_length=512, blank=False) 
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'autoteka_signal_region'
        verbose_name = 'Сигнал автотека - регионы'
        verbose_name_plural = "Сигнал автотека регионы - https://developers.avito.ru/api-catalog/autoteka/documentation#operation/monitoringBucketAdd - get-leads"

    
class Autoteka_signal(models.Model):
    date                = models.DateTimeField('date - dateTimeField - Дата запроса', default=datetime.now, blank=False)
    id_records          = models.IntegerField('id - integer - ID записи', default=0, null=False, blank=False) 
    item_id             = models.IntegerField("Ид объявления", default=0, blank=True)
    vin                 = models.CharField('vin - string Nullable - VIN', default='', null=True, max_length=20, blank=False) 
    price               = models.IntegerField("price - integer Nullable - Цена ", default=0, blank=True)
    year                = models.IntegerField("year - integer Nullable - Год выпуска",  default=0, null=False, blank=True)
    mileage             = models.IntegerField("mileage - integer Nullable - Пробег",  default=0, null=False, blank=True)
    brand               = models.CharField('brand - string Nullable - Марка', default='', null=True, max_length=512, blank=False) 
    model               = models.CharField('model - string Nullable - Модель', default='', null=True, max_length=512, blank=False) 
    description         = models.CharField('description - string Nullable - Описание', default='', null=True, max_length=5120, blank=False) 
    condition           = models.CharField('condition - string Nullable - Состояние', default='', null=True, max_length=200, blank=False) 
    owners              = models.IntegerField("owners - integer Nullable - Владельцев ", default=0, blank=True)
    region_id           = models.IntegerField("ИД региона", default=0, blank=True)
    is_pro_seller       = models.BooleanField("Профессиональный продавец",  default=False, null=True) 
    city_name           = models.CharField('Город', default='', null=True, max_length=200, blank=False) 
    region_name         = models.ForeignKey(Autoteka_signal_region, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Регион") 
    pledge              = models.CharField('Залог', default='', null=True, max_length=200, blank=False) 
    phone_number        = models.CharField('Номер телефона', default='', null=True, max_length=200, blank=False) 
    seller              = models.CharField('Продавец', default='', null=True, max_length=512, blank=False) 
    item_created_at     = models.DateTimeField('Дата создания', default=datetime.now, blank=False)
    item_updated_at     = models.DateTimeField('Дата обновления', default=datetime.now, blank=False)
    average_days_in_sale= models.IntegerField("Дней в продаже", default=0, blank=True)
    estimate_sell_price = models.IntegerField("Ориентировочная цена продажи", default=0, blank=True)
    liquidity_rating    = models.CharField('Ликвидность', default='', null=True, max_length=512, blank=False) 
    seller_price_diff   = models.IntegerField("Разница в цене продавца", default=0, blank=True)
    crashes_badge       = models.BooleanField("Значок сбоя",  default=False, null=True) 
    real_mileage_badge  = models.BooleanField("Значок реального пробега",  default=False, null=True)  
    url                 = models.CharField("Ссылка", default='', null=True, max_length=512, blank=False) 
    
    def save(self, *args, **kwargs):
        try:
            if self.price == None:
                    self.price = 0
        except:
            self.price = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return "{} / {} / {}".format(self.date, self.vin, self.item_id)

    class Meta:
        indexes = [
            models.Index(fields=['vin'])
        ]
        db_table = 'autoteka_signal'
        verbose_name = 'Сигнал автотека'
        verbose_name_plural = "Сигнал автотека - https://developers.avito.ru/api-catalog/autoteka/documentation#operation/monitoringBucketAdd - get-leads"


# Статусы задач по автомобилям
TASK_STATUS_CHOICES = [
    ('new', 'Новый'),
    ('in_progress', 'В работе'),
    ('completed', 'Выполнена'),
]


class RegCarsOrganizationTask(models.Model):
    """Задача по автомобилю"""
    car = models.ForeignKey(RefCarsOrganization, on_delete=models.PROTECT, null=True, verbose_name="Автомобиль", related_name='tasks')
    staff_created = models.ForeignKey(User, related_name="car_task_created", on_delete=models.SET_NULL, null=True, verbose_name="Пользователь создавший")
    staff_assignee = models.ForeignKey(User, related_name="car_task_assignee", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Исполнитель")
    status = models.CharField("Статус", max_length=20, choices=TASK_STATUS_CHOICES, default='new')
    title = models.CharField("Название задачи", max_length=512, default='', null=True, blank=True)
    description = models.TextField("Описание задачи", default='', null=True, blank=True)
    date_created = models.DateTimeField('Дата создания', default=datetime.now, blank=True, null=True)
    date_started = models.DateTimeField('Дата начала работы', blank=True, null=True)
    date_completed = models.DateTimeField('Дата завершения', blank=True, null=True)
    
    def comments_count(self):
        return self.comments.filter(is_deleted=False).count()
    
    def __str__(self):
        return "{} - {} - {} - {}".format(self.car, self.title, self.status, self.staff_assignee)
    
    class Meta:
        db_table = 'regCarsOrganizationTask'
        verbose_name = "Задача по автомобилю"
        verbose_name_plural = "Задачи по автомобилям"
        ordering = ['-date_created']
        indexes = [
            models.Index(fields=['car', 'status']),
            models.Index(fields=['staff_assignee', 'status']),
            models.Index(fields=['date_created']),
        ]


class RegCarsOrganizationTaskComment(models.Model):
    """Комментарий к задаче по автомобилю"""
    task = models.ForeignKey(RegCarsOrganizationTask, on_delete=models.CASCADE, null=True, verbose_name="Задача", related_name='comments')
    staff = models.ForeignKey(User, related_name="car_task_comment", on_delete=models.SET_NULL, null=True, verbose_name="Автор комментария")
    comment = models.TextField("Комментарий", default='', null=True, blank=True)
    date_created = models.DateTimeField('Дата создания', default=datetime.now, blank=True, null=True)
    is_deleted = models.BooleanField("Удален", default=False)
    
    def __str__(self):
        return "{} - {} - {}".format(self.task, self.staff, self.date_created)
    
    class Meta:
        db_table = 'regCarsOrganizationTaskComment'
        verbose_name = "Комментарий к задаче по автомобилю"
        verbose_name_plural = "Комментарии к задачам по автомобилям"
        ordering = ['date_created']
        indexes = [
            models.Index(fields=['task', 'date_created']),
        ]


class RegCarsOrganizationTaskFile(models.Model):
    """Файл, прикрепленный к задаче по автомобилю"""
    task = models.ForeignKey(RegCarsOrganizationTask, on_delete=models.CASCADE, null=True, verbose_name="Задача", related_name='files')
    staff = models.ForeignKey(User, related_name="car_task_file", on_delete=models.SET_NULL, null=True, verbose_name="Загрузил")
    file = models.FileField("Файл", upload_to='car_tasks/%Y/%m/%d/', null=True, blank=True)
    file_name = models.CharField("Имя файла", max_length=512, default='', null=True, blank=True)
    file_size = models.IntegerField("Размер файла (байт)", default=0, null=True, blank=True)
    date_created = models.DateTimeField('Дата загрузки', default=datetime.now, blank=True, null=True)
    is_deleted = models.BooleanField("Удален", default=False)
    
    def __str__(self):
        return "{} - {} - {}".format(self.task, self.file_name, self.date_created)
    
    def get_file_size_display(self):
        """Возвращает размер файла в читаемом формате"""
        if not self.file_size:
            return "0 Б"
        size = self.file_size
        for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} ТБ"
    
    class Meta:
        db_table = 'regCarsOrganizationTaskFile'
        verbose_name = "Файл задачи по автомобилю"
        verbose_name_plural = "Файлы задач по автомобилям"
        ordering = ['-date_created']
        indexes = [
            models.Index(fields=['task', 'date_created']),
            models.Index(fields=['task', 'is_deleted']),
        ]


class CarsWarehouseShowcase(models.Model):
    """Витрина склада - снимок данных для анализа склада"""
    date_created = models.DateTimeField('Дата создания', default=datetime.now, blank=True, null=True)
    unit = models.ForeignKey(RefUnit, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Подразделение ДЦ")
    
    # Статистика
    total_cars = models.IntegerField('Всего автомобилей', default=0)
    total_price = models.DecimalField('Общая стоимость', max_digits=15, decimal_places=2, default=0)
    total_cost = models.DecimalField('Общая себестоимость', max_digits=15, decimal_places=2, default=0)
    
    # Проблемы
    cars_no_photos = models.IntegerField('Авто без фото', default=0)
    cars_old_photos = models.IntegerField('Авто со старыми фото', default=0)
    cars_no_evaluation = models.IntegerField('Авто без оценки', default=0)
    cars_old_evaluation = models.IntegerField('Авто со старой оценкой', default=0)
    cars_long_in_stock = models.IntegerField('Авто долго на складе', default=0)
    
    # Данные в JSON для детального анализа
    data_json = models.TextField("Данные в JSON", default='{}', null=True, blank=True)
    
    def __str__(self):
        return "{} - {} - {}".format(self.date_created, self.unit, self.total_cars)
    
    class Meta:
        db_table = 'carsWarehouseShowcase'
        verbose_name = "Витрина склада"
        verbose_name_plural = "Витрины склада"
        ordering = ['-date_created']
        indexes = [
            models.Index(fields=['unit', 'date_created']),
        ]


