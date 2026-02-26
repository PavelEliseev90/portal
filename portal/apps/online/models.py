from django.db import models
from refs.models import RefUnit, RefCars, RefCustomer
from documents.models import DocRLK
from datetime import datetime
import uuid
import random
from django.conf import settings


class Online_doc(models.Model):
    dataTimeCreate      = models.DateTimeField('Дата и время создания', default=datetime.now, blank=False)    
    dataTimeOpen        = models.DateTimeField('Дата и время открытия ссылки', null=True, blank=True)    
    dataTimeRecord      = models.DateTimeField('Дата и время записи на сервис', null=True, blank=True) 
    uin                 = models.CharField('uin', default='', null=True, max_length=100, blank=False)
    clientName          = models.CharField("Клиент", default='', null=True, max_length=250, blank=False)    
    clientPhone         = models.CharField("Номер телефона клиента", default='', null=True, max_length=250, blank=False)    
    customer            = models.ForeignKey(RefCustomer, null=True, on_delete=models.SET_NULL, verbose_name="Клиент")
    unit                = models.ForeignKey(RefUnit, null=True, on_delete=models.SET_NULL, verbose_name="Подразделение создания") 
    cars                = models.ForeignKey(RefCars, blank=True, null=True, on_delete=models.SET_NULL, verbose_name="Автомобиль")
    uid                 = models.CharField(max_length=100, blank=True, unique=True, default=uuid.uuid4)
    call                = models.BooleanField("Заказан обратный звонок", default = False)
    unitRecord          = models.ForeignKey(RefUnit, related_name='unitRecord', null=True, on_delete=models.SET_NULL, verbose_name="Подразделение записи", blank=True)
    
    def __str__(self):
        return "{} ({}) - {}".format(self.dataTimeCreate, self.clientName, self.unit)

    class Meta:
        db_table = 'online_doc'
        verbose_name = "Онлайн запись сервис"
        verbose_name_plural = "Онлайн записи на сервис"


class Records_online_doc(models.Model):
    dataTimeCreate      = models.DateTimeField('Дата и время создания', default=datetime.now, blank=False)    
    dataTimeRecord      = models.DateTimeField('Дата и время записи на сервис', default=datetime.now, blank=False)    
    dataTimeOpen        = models.DateTimeField('Дата и время открытия ссылки', null=True, blank=True)    
    uin                 = models.CharField('uin', default='', null=True, max_length=100, blank=False)
    clientName          = models.CharField("Клиент", default='', null=True, max_length=250, blank=False)    
    clientPhone         = models.CharField("Номер телефона клиента", default='', null=True, max_length=250, blank=False)    
    customer            = models.ForeignKey(RefCustomer, null=True, on_delete=models.SET_NULL, verbose_name="Клиент")
    unit                = models.ForeignKey(RefUnit, null=True, on_delete=models.SET_NULL, verbose_name="Подразделение создания") 
    cars                = models.ForeignKey(RefCars, blank=True, null=True, on_delete=models.SET_NULL, verbose_name="Автомобиль")
    short_url           = models.CharField("Короткая ссылка", unique=True, max_length=20, blank=True, db_index=True) 
    confirmed           = models.BooleanField("Подтвержденно", default = False)
    
    def save(self, *args, **kwargs):
        if not self.short_url:
            while True:  # цикл будет повторять до тех пор пока не сгенерирует уникальную ссылку
                self.short_url = ''.join(
                    random.choices(
                        settings.CHARACTERS,  # алфавит для генерации короткой ссылки мы будем хранить в файле настроек
                        k=settings.TOKEN_LENGTH  # длину короткой ссылки тоже
                    )
                )
                if not Records_online_doc.objects.filter(  # проверка на уникальность
                    short_url=self.short_url
                ).exists():
                    break
        super().save(*args, **kwargs)
        
    def __str__(self):
        return "{} ({}) - {}".format(self.dataTimeCreate, self.clientName, self.unit)

    class Meta:
        db_table = 'records_online_doc'
        verbose_name = "Подтверждение записи на сервис"
        verbose_name_plural = "Подтверждения записи на сервис"


class PersonalDataConsent(models.Model):
    """
    Модель для хранения согласий на обработку персональных данных клиентов
    """
    # Уникальный токен для ссылки подтверждения
    token = models.CharField("Уникальный токен", max_length=64, unique=True, db_index=True, blank=True)
    
    # Данные клиента
    last_name = models.CharField("Фамилия", max_length=100, default='', blank=False)
    first_name = models.CharField("Имя", max_length=100, default='', blank=False)
    middle_name = models.CharField("Отчество", max_length=100, default='', blank=True)
    phone = models.CharField("Номер телефона", max_length=20, default='', blank=False)
    email = models.EmailField("Email", max_length=254, default='', blank=True)
    
    # Связи 
    rlk         = models.ForeignKey(DocRLK, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Рабочий лист")
    customer    = models.ForeignKey(RefCustomer, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Клиент")
    unit        = models.ForeignKey(RefUnit, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Подразделение")
    
    # Даты и время
    date_created = models.DateTimeField("Дата и время создания ссылки", default=datetime.now, blank=False)
    date_opened = models.DateTimeField("Дата и время открытия ссылки", null=True, blank=True)
    date_confirmed = models.DateTimeField("Дата и время подтверждения", null=True, blank=True)
    
    # Техническая информация
    ip_address = models.GenericIPAddressField("IP адрес", null=True, blank=True)
    user_agent = models.TextField("User Agent", default='', blank=True)
    
    # Статус
    confirmed = models.BooleanField("Подтверждено", default=False)
    revoked = models.BooleanField("Отозвано", default=False)
    date_revoked = models.DateTimeField("Дата и время отзыва", null=True, blank=True)
    
    # Юридический текст согласия (для хранения версии на момент подтверждения)
    consent_text = models.TextField("Текст согласия", default='', blank=True)
    
    # Дополнительная информация
    comment = models.TextField("Комментарий", default='', blank=True)
    
    def get_full_name(self):
        """Получить полное ФИО"""
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return ' '.join(parts).strip()
    
    def save(self, *args, **kwargs):
        """Автоматическая генерация токена при создании"""
        if not self.token:
            while True:
                # Генерируем токен из безопасных символов
                chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
                self.token = ''.join(random.choices(chars, k=32))
                if not PersonalDataConsent.objects.filter(token=self.token).exists():
                    break
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.phone}) - {'Подтверждено' if self.confirmed else 'Не подтверждено'}"
    
    class Meta:
        db_table = 'personal_data_consent'
        verbose_name = "Согласие на обработку персональных данных"
        verbose_name_plural = "Согласия на обработку персональных данных"
        ordering = ['-date_created']