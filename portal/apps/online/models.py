from django.db import models
from refs.models import RefUnit, RefCars, RefCustomer
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