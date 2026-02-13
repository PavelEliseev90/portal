"""
Модели для управления выгрузкой автомобилей на различные площадки
"""
from django.db import models
from django.conf import settings
from datetime import datetime
from refs.models import RefUnit, RefCarsOrganization, RefTypeExchange, RefStatusCarsOrganization, RefTypeBody, RefTypeKpp, RefTypeEngine, RefTypeDrive
from changelog.mixins import ChangeloggableMixin
import json


# ===========================================
# СПРАВОЧНИКИ
# ===========================================

class RefClassifiedsPlatform(models.Model):
    """Площадка для выгрузки (Авито, Авто.ру, Drom и т.д.)"""
    name = models.CharField("Наименование", max_length=250, default='')
    code = models.CharField("Код", max_length=50, default='', unique=True)
    description = models.TextField("Описание", max_length=2000, blank=True, default='')
    is_active = models.BooleanField("Активна", default=True)
    xml_template = models.TextField("Шаблон XML", blank=True, default='')
    api_url = models.CharField("URL API", max_length=1024, blank=True, default='')
    api_key = models.CharField("API ключ", max_length=512, blank=True, default='')
    sort_order = models.IntegerField("Порядок сортировки", default=0)
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'refClassifiedsPlatform'
        verbose_name = "Площадка для выгрузки"
        verbose_name_plural = "Площадки для выгрузки"
        ordering = ['sort_order', 'name']


# ===========================================
# ОСНОВНЫЕ МОДЕЛИ
# ===========================================

class ClassifiedsExportConfig(ChangeloggableMixin, models.Model):
    """Настройка выгрузки автомобилей на площадку"""
    
    STATUS_CHOICES = [
        ('active', 'Активна'),
        ('inactive', 'Неактивна'),
        ('error', 'Ошибка'),
    ]
    
    name = models.CharField("Наименование настройки", max_length=250, default='')
    platform = models.ForeignKey(RefClassifiedsPlatform, null=True, on_delete=models.SET_NULL, 
                                 verbose_name="Площадка", related_name='export_configs')
    unit = models.ForeignKey(RefUnit, null=True, on_delete=models.SET_NULL, verbose_name='Подразделение ДЦ')
    type_exchange = models.ForeignKey(RefTypeExchange, null=True, blank=True, on_delete=models.SET_NULL, 
                                     verbose_name='Назначение выгрузки')
    
    # Статус и активность
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default='active')
    is_active = models.BooleanField("Активна", default=True)
    
    # Настройки файла
    file_name_template = models.CharField("Шаблон имени файла", max_length=300, 
                                         default='export_{platform}_{date}.xml',
                                         help_text="Доступны переменные: {platform}, {date}, {unit}, {count}")
    file_path = models.CharField("Путь для сохранения", max_length=1024, 
                                default='/media/classifieds/exports/',
                                help_text="Путь относительно MEDIA_ROOT")
    
    # Настройки выгрузки
    auto_export = models.BooleanField("Автоматическая выгрузка", default=False,
                                     help_text="Автоматически выгружать при изменении автомобилей")
    schedule_cron = models.CharField("Расписание (cron)", max_length=100, blank=True, default='',
                                     help_text="Формат cron: '0 2 * * *' (каждый день в 2:00)")
    
    # Фильтры для выбора автомобилей
    filter_units = models.ManyToManyField(RefUnit, blank=True, related_name='classifieds_export_configs',
                                          verbose_name="Подразделения (фильтр)")
    filter_statuses = models.ManyToManyField(RefStatusCarsOrganization, blank=True,
                                            verbose_name="Статусы автомобилей (фильтр)")
    filter_is_new = models.BooleanField("Только новые", null=True, blank=True, default=None,
                                       verbose_name="Только новые автомобили")
    filter_min_price = models.IntegerField("Минимальная цена", null=True, blank=True, default=None)
    filter_max_price = models.IntegerField("Максимальная цена", null=True, blank=True, default=None)
    filter_min_year = models.IntegerField("Минимальный год", null=True, blank=True, default=None)
    filter_max_year = models.IntegerField("Максимальный год", null=True, blank=True, default=None)
    filter_marks = models.CharField("Марки (через запятую)", max_length=1000, blank=True, default='')
    filter_exclude_vin = models.TextField("Исключить VIN (по одному на строку)", blank=True, default='')
    
    # Дополнительные настройки
    max_cars_per_export = models.IntegerField("Максимум автомобилей в выгрузке", null=True, blank=True,
                                             default=None, help_text="Ограничение количества")
    include_reserved = models.BooleanField("Включать зарезервированные", default=False)
    include_sold = models.BooleanField("Включать проданные", default=False)
    
    # Настройки XML
    xml_settings = models.TextField("Настройки XML (JSON)", blank=True, default='{}',
                                   help_text="Дополнительные настройки для генерации XML в формате JSON")
    
    # Метаданные
    date_create = models.DateTimeField('Дата создания', default=datetime.now, blank=False)
    date_update = models.DateTimeField('Дата обновления', auto_now=True)
    user_create = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, 
                                   on_delete=models.SET_NULL, related_name='classifieds_configs_created',
                                   verbose_name="Создал")
    user_update = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name='classifieds_configs_updated',
                                   verbose_name="Обновил")
    comment = models.TextField("Комментарий", max_length=2000, blank=True, default='')
    
    def __str__(self):
        return f"{self.name} ({self.platform.name if self.platform else 'Без площадки'})"
    
    def get_xml_settings(self):
        """Получить настройки XML как словарь"""
        try:
            return json.loads(self.xml_settings) if self.xml_settings else {}
        except:
            return {}
    
    def set_xml_settings(self, settings_dict):
        """Установить настройки XML из словаря"""
        self.xml_settings = json.dumps(settings_dict, ensure_ascii=False)
    
    class Meta:
        db_table = 'classifiedsExportConfig'
        verbose_name = "Настройка выгрузки"
        verbose_name_plural = "Настройки выгрузки"
        ordering = ['-date_create']


class ClassifiedsFieldMapping(models.Model):
    """Маппинг полей автомобиля на поля площадки"""
    config = models.ForeignKey(ClassifiedsExportConfig, on_delete=models.CASCADE,
                              related_name='field_mappings', verbose_name="Настройка выгрузки")
    car_field = models.CharField("Поле автомобиля", max_length=250,
                                help_text="Путь к полю в модели RefCarsOrganization, например: 'mark', 'price', 'modification_autoru.name'")
    platform_field = models.CharField("Поле площадки", max_length=250,
                                     help_text="Название поля в XML площадки")
    default_value = models.CharField("Значение по умолчанию", max_length=500, blank=True, default='',
                                     help_text="Используется если поле автомобиля пустое")
    transform_function = models.CharField("Функция преобразования", max_length=250, blank=True, default='',
                                         help_text="Название функции для преобразования значения")
    is_required = models.BooleanField("Обязательное поле", default=False)
    sort_order = models.IntegerField("Порядок сортировки", default=0)
    
    def __str__(self):
        return f"{self.car_field} -> {self.platform_field}"
    
    class Meta:
        db_table = 'classifiedsFieldMapping'
        verbose_name = "Маппинг полей"
        verbose_name_plural = "Маппинги полей"
        ordering = ['sort_order', 'platform_field']


class ClassifiedsExportHistory(models.Model):
    """История выгрузок"""
    
    STATUS_CHOICES = [
        ('pending', 'В очереди'),
        ('processing', 'Обрабатывается'),
        ('success', 'Успешно'),
        ('error', 'Ошибка'),
        ('partial', 'Частично'),
    ]
    
    config = models.ForeignKey(ClassifiedsExportConfig, on_delete=models.CASCADE,
                              related_name='export_history', verbose_name="Настройка выгрузки")
    
    # Статус и результат
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default='pending')
    cars_count = models.IntegerField("Количество автомобилей", default=0)
    cars_exported = models.IntegerField("Выгружено автомобилей", default=0)
    cars_skipped = models.IntegerField("Пропущено автомобилей", default=0)
    cars_errors = models.IntegerField("Ошибок", default=0)
    
    # Файлы
    file_path = models.CharField("Путь к файлу", max_length=1024, blank=True, default='')
    file_name = models.CharField("Имя файла", max_length=300, blank=True, default='')
    file_size = models.BigIntegerField("Размер файла (байт)", null=True, blank=True, default=None)
    
    # Детали
    error_message = models.TextField("Сообщение об ошибке", blank=True, default='')
    export_details = models.TextField("Детали выгрузки (JSON)", blank=True, default='{}',
                                     help_text="Дополнительная информация о выгрузке")
    
    # Метаданные
    date_start = models.DateTimeField('Дата начала', default=datetime.now, blank=False)
    date_end = models.DateTimeField('Дата окончания', null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                           on_delete=models.SET_NULL, related_name='classifieds_exports',
                           verbose_name="Пользователь")
    is_manual = models.BooleanField("Ручная выгрузка", default=False,
                                   help_text="True если запущена вручную, False если автоматически")
    
    def __str__(self):
        return f"{self.config.name} - {self.date_start.strftime('%d.%m.%Y %H:%M')} ({self.status})"
    
    def get_export_details(self):
        """Получить детали выгрузки как словарь"""
        try:
            return json.loads(self.export_details) if self.export_details else {}
        except:
            return {}
    
    def set_export_details(self, details_dict):
        """Установить детали выгрузки из словаря"""
        self.export_details = json.dumps(details_dict, ensure_ascii=False)
    
    class Meta:
        db_table = 'classifiedsExportHistory'
        verbose_name = "История выгрузки"
        verbose_name_plural = "История выгрузок"
        ordering = ['-date_start']


class ClassifiedsExportLog(models.Model):
    """Лог выгрузки конкретного автомобиля"""
    
    STATUS_CHOICES = [
        ('success', 'Успешно'),
        ('error', 'Ошибка'),
        ('skipped', 'Пропущен'),
    ]
    
    export_history = models.ForeignKey(ClassifiedsExportHistory, on_delete=models.CASCADE,
                                     related_name='export_logs', verbose_name="История выгрузки")
    car = models.ForeignKey(RefCarsOrganization, on_delete=models.CASCADE,
                          related_name='classifieds_export_logs', verbose_name="Автомобиль")
    
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default='success')
    error_message = models.TextField("Сообщение об ошибке", blank=True, default='')
    xml_data = models.TextField("XML данные автомобиля", blank=True, default='',
                               help_text="Сгенерированный XML для этого автомобиля")
    
    date_create = models.DateTimeField('Дата создания', default=datetime.now, blank=False)
    
    def __str__(self):
        return f"{self.car.vin} - {self.status}"
    
    class Meta:
        db_table = 'classifiedsExportLog'
        verbose_name = "Лог выгрузки автомобиля"
        verbose_name_plural = "Логи выгрузки автомобилей"
        ordering = ['-date_create']
        indexes = [
            models.Index(fields=['export_history', 'car']),
            models.Index(fields=['status']),
        ]

