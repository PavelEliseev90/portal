from django.db import models
from django.conf import settings
from refs.models import RefUnitGroup, RefTypeItemServiceRepair, RefTypeDocService, RefService, RefReasonArchiveRLK, RefStatusRLK, RefFilial, AutoruModification, AutoruComplectation, RefTypeReceptionCarsOrganization, RefStore, RefTypeItemRepair, RefOrganization, RefUnit, RefCustomer, RefCity, RefCars, RefStaff, RefTypeDocRLK, RefWork, RefProduct, RefTypeRepair, RefStatusDocZN, RefContactType, RefStatusEvent, RefTypeCanceledSMS, RefTypeResourcePlanning, RefTypeCategoryNegative, RefTypeCategoryCustomer, RefSMSStatusBase, RefSMSStatusProvider
from django.db.models import Avg, Max, Min, Sum, F
from datetime import datetime, timedelta
import uuid
import random
import json


from django.contrib.auth.models import User, Group


class DocServiceRequest(models.Model):
    uin            = models.CharField('uin', default='', null=True, max_length=64, blank=False)
    closed         = models.BooleanField("Закрыт",  default=False)
    active         = models.BooleanField("Проведен", default=False)
    nomer          = models.CharField('Номер', default='', null=True, max_length=25, blank=False)
    dataTime       = models.DateTimeField('Дата', default=datetime.now, blank=False)
    dateStart      = models.DateTimeField('Пришла в ремонт', null=True, blank=True)
    dateEnd        = models.DateTimeField('Вышла из ремонта', null=True, blank=True)
    organization   = models.ForeignKey(RefOrganization, on_delete=models.SET_NULL, null=True, verbose_name="Организация")
    unit           = models.ForeignKey(RefUnit, on_delete=models.SET_NULL, null=True, verbose_name="Подразделение")
    master         = models.ForeignKey(RefStaff, related_name="service_request_mastein", on_delete=models.SET_NULL, null=True, verbose_name="Мастер-консультант")
    masterOut      = models.ForeignKey(RefStaff, related_name="service_request_master_out", on_delete=models.SET_NULL, null=True, verbose_name="Выпускающий мастер-консультант")
    carsGRZ        = models.CharField('Гос. номер', default='', null=True, max_length=25, blank=False)
    customer       = models.ForeignKey(RefCustomer, on_delete=models.SET_NULL, null=True, verbose_name="Клиент")
    clientName     = models.CharField('Клиент строкой', default='', null=True, max_length=250, blank=False)
    cars           = models.ForeignKey(RefCars, on_delete=models.SET_NULL, null=True, verbose_name="Автомобиль") 
    typeRemont     = models.ForeignKey(RefTypeRepair, on_delete=models.SET_NULL, null=True, verbose_name="Вид ремонта")
    readyStatus    = models.ForeignKey(RefStatusDocZN, on_delete=models.SET_NULL, null=True, verbose_name="Статус") 
    customerWords  = models.CharField('Заявка со слов клиента', default='', null=True, max_length=12500, blank=False) 
    run            = models.IntegerField("Пробег", default=0, blank=True)
    
    def ready_status_board(self):
        if self.readyStatus != None and len(str(self.readyStatus)) > 0:
            return self.readyStatus
        else:
            return 'В работе'
        
    def cars_grz_board(self):
        grz = str(self.carsGRZ).upper().replace(" ", "")
        return grz[0:1] + ' ' + grz[1:4] + ' ' + grz[4:6] + '   ' + grz[6:10]

    
    def __str__(self):
        return "{} ({} - {}) - {}".format(self.dataTime, self.clientName, self.nomer, self.typeRemont)

    def save(self, *args, **kwargs):
        try:
            if self.readyStatus != None and self.readyStatus.name == "Закрыт":
                    self.closed = True
        except:
            self.closed = False
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['uin'])
        ]
        db_table = 'docServiceRequest'
        verbose_name = "Заявка на ремонт"
        verbose_name_plural = "Заявки на ремонт"


class DocZN(models.Model):
    uin            = models.CharField('uin', default='', null=True, max_length=64, blank=False)
    closed         = models.BooleanField("Закрыт",  default=False)
    active         = models.BooleanField("Проведен", default=False)
    nomer          = models.CharField('Номер', default='', null=True, max_length=25, blank=False)
    dataTime       = models.DateTimeField('Дата', default=datetime.now, blank=False)
    dateStart      = models.DateTimeField('Пришла в ремонт', null=True, blank=True)
    dateEnd        = models.DateTimeField('Вышла из ремонта', null=True, blank=True)
    organization   = models.ForeignKey(RefOrganization, on_delete=models.SET_NULL, null=True, verbose_name="Организация")
    unit           = models.ForeignKey(RefUnit, on_delete=models.SET_NULL, null=True, verbose_name="Подразделение")
    master         = models.ForeignKey(RefStaff, related_name="mastein", on_delete=models.SET_NULL, null=True, verbose_name="Мастер-консультант")
    masterOut      = models.ForeignKey(RefStaff, related_name="masterout", on_delete=models.SET_NULL, null=True, verbose_name="Выпускающий мастер-консультант")
    carsGRZ        = models.CharField('Гос. номер', default='', null=True, max_length=25, blank=True)
    customer       = models.ForeignKey(RefCustomer, on_delete=models.SET_NULL, null=True, verbose_name="Клиент")
    clientName     = models.CharField('Клиент строкой', default='', null=True, max_length=250, blank=False)
    cars           = models.ForeignKey(RefCars, on_delete=models.SET_NULL, null=True, verbose_name="Автомобиль") 
    typeRemont     = models.ForeignKey(RefTypeRepair, on_delete=models.SET_NULL, null=True, verbose_name="Вид ремонта")
    readyStatus    = models.ForeignKey(RefStatusDocZN, on_delete=models.SET_NULL, null=True, verbose_name="Статус") 
    customerWords  = models.CharField('Заявка со слов клиента', default='', null=True, max_length=12500, blank=True) 
    run            = models.IntegerField("Пробег", default=0, blank=True)
    amount         = models.FloatField("Сумма", default=0.0, blank=True)
    video          = models.FileField(upload_to='video_zn/%Y/%m/%d/', verbose_name="Видео", blank=True, null=True)
    need_checklist = models.BooleanField("Нужен чек лист", default = False)
    gross_profit_work       = models.FloatField("Валовая прибыль работы", default=0.0, blank=True)
    gross_profit_product    = models.FloatField("Валовая прибыль запчасти", default=0.0, blank=True)
    typeIB                  = models.CharField('Тип конфигурации', default='', null=True, max_length=64, blank=True)
    serviceRequest          = models.ForeignKey(DocServiceRequest, on_delete=models.SET_NULL, null=True, verbose_name="Заявка на ремонт", blank=True)
    recomendation           = models.CharField('Рекомендация / результат диагностики', default='', null=True, max_length=5024, blank=True)

    def amount_zn(self):
        return self.works_amount() + self.products_amount()

    def rating_customer(self):
        if self.customer == None or self.customer.company:
            return ''
        doc_count = DocOprosZN.objects.filter(zn__customer = self.customer).filter(close = True).filter(canceled = False).count()
        if doc_count == 0:
            return 0
        else:
           rating_qyeryset = DocOprosZN.objects.filter(zn__customer = self.customer).filter(close = True).filter(canceled = False).aggregate(Sum('v1'), Sum('v2'), Sum('v3'), Sum('v4'), Sum('v5'), Sum('v6'))
           rating_sum   = rating_qyeryset['v1__sum'] + rating_qyeryset['v2__sum'] + rating_qyeryset['v3__sum'] + rating_qyeryset['v4__sum'] + rating_qyeryset['v5__sum'] + rating_qyeryset['v6__sum']     
           rating       = round(rating_sum / doc_count / 6, 2)
           return rating
         
    def performers_count(self):
        return DocZNPerformers.objects.filter(zn = self).count()

    def ready_status_board(self):
        if self.readyStatus != None and len(str(self.readyStatus)) > 0:
            return self.readyStatus
        else:
            return 'В работе'

    def cars_grz_board(self):
        grz = str(self.carsGRZ).upper().replace(" ", "")
        return grz[0:1] + ' ' + grz[1:4] + ' ' + grz[4:6] + '   ' + grz[6:10]

    def works(self):
        if DocZNWork.objects.filter(zn = self).count() > 0:  
            works = DocZNWork.objects.filter(zn = self) 
            return works
        else: 
            return list()
    def works_count(self):
        if DocZNWork.objects.filter(zn = self).count() > 0:  
            works = DocZNWork.objects.filter(zn = self).count() 
            return works
        else: 
            return 0
    def works_amount(self):
        if DocZNWork.objects.filter(zn = self).count() > 0:  
            #if self.typeIB == '':
            sum = DocZNWork.objects.filter(zn = self).aggregate(Sum('amount')) 
            return round(sum['amount__sum'], 2)
            #else:
            #    sum = DocZNWork.objects.filter(zn = self).aggregate(Sum('amountResult')) 
            #    return round(sum['amountResult__sum'], 2)
        else: 
            return 0
    
    def products(self):
        if DocZNProduct.objects.filter(zn = self).count() > 0:  
            products = DocZNProduct.objects.filter(zn = self) 
            return products
        else: 
            return list()
    def products_count(self):
        if DocZNProduct.objects.filter(zn = self).count() > 0:  
            products = DocZNProduct.objects.filter(zn = self).count() 
            return products
        else: 
            return 0
    def products_amount(self):
        
        if DocZNProduct.objects.filter(zn = self).count() > 0:  
            #if self.typeIB == '':
            sum = DocZNProduct.objects.filter(zn = self).aggregate(Sum('amount')) 
            return round(sum['amount__sum'], 2)
            #else:
            #    sum = DocZNProduct.objects.filter(zn = self).aggregate(Sum('amountResult')) 
            #    return round(sum['amountResult__sum'], 2)
        else: 
            return 0

    def get_time_end(self):
        date_period = datetime(2000,12,2)
        if self.dateStart != None and self.dateEnd.replace(tzinfo=None) > date_period:
            return self.dateEnd
        else:
            return '---'
    def get_time_start(self):
        date_period = datetime(2000,12,2)
        if self.dateStart != None and self.dateStart.replace(tzinfo=None) > date_period:
            return self.dateStart
        else:
            return '---'
    
    def recomendations_mcu(self):
        return DoсRecomendationMCU.objects.filter(zn = self).order_by('status') 
    def recomendations_mcu_count(self):
        return DoсRecomendationMCU.objects.filter(zn = self).count()

    def recomendations_new_customer(self):
        mcu = self.recomendations_mcu_count_1()
        ser = self.recomendations_customer_1_count()
        return mcu + ser

    def recomendations_mcu_1(self):
        return DoсRecomendationMCU.objects.filter(zn = self).filter(customerStatus = 1).order_by('status') 
    def recomendations_mcu_count_1(self):
        return DoсRecomendationMCU.objects.filter(zn = self).filter(customerStatus = 1).count()

    def recomendationsZN(self):
        return DocZNRecomendation.objects.filter(zn = self) 
    def recomendationsZN_count(self):
        return DocZNRecomendation.objects.filter(zn = self).count()
    
    def recomendationsZNShow(self):
        return DocZNRecomendation.objects.filter(zn = self).filter(show = True) 
    def recomendationsZNShow_count(self):
        return DocZNRecomendation.objects.filter(zn = self).filter(show = True).count()

    def recomendations(self):
        return DoсRecomendation.objects.filter(zn = self).order_by('status') 
    def recomendations_count(self):
        return DoсRecomendation.objects.filter(zn = self).count()

    def recomendations_customer(self):
        return DoсRecomendation.objects.filter(zn = self).filter(customerStatus__gt = 0)
    def recomendations_customer_count(self):
        return DoсRecomendation.objects.filter(zn = self).filter(customerStatus__gt = 0).count()

    def recomendations_customer_0(self):
        return DoсRecomendation.objects.filter(zn = self).filter(customerStatus__gt = 0)
    def recomendations_customer_0_count(self):
        return DoсRecomendation.objects.filter(zn = self).filter(customerStatus = 0).count()

    def recomendations_customer_1(self):
        return DoсRecomendation.objects.filter(zn__id = self.pk).filter(customerStatus = 1)
    def recomendations_customer_1_count(self):
        if not DoсRecomendation.objects.filter(zn__id = self.pk).filter(customerStatus = 1).exists():
            return 0
        return DoсRecomendation.objects.filter(zn__id = self.pk).filter(customerStatus = 1).count()
        

    def recomendations_customer_2(self):
        return DoсRecomendation.objects.filter(zn = self).filter(customerStatus = 2)
    def recomendations_customer_2_count(self):
        return DoсRecomendation.objects.filter(zn = self).filter(customerStatus = 2).count()

    def recomendations_customer_3(self):
        return DoсRecomendation.objects.filter(zn = self).filter(customerStatus = 3)
    def recomendations_customer_3_count(self):
        return DoсRecomendation.objects.filter(zn = self).filter(customerStatus = 3).count()

    def get_opros(self):
        if DocOprosZN.objects.filter(zn = self).count() > 0:  
            opros = DocOprosZN.objects.filter(zn = self)[0] 
            return opros
        else: 
            return None
    
    def get_opros_close(self):
        if DocOprosZN.objects.filter(uin = self.uin).count() > 0:  
            opros = DocOprosZN.objects.filter(uin = self.uin)[0] 
            return opros.close
        else: 
            return False

    def __str__(self):
        return "{} ({} - {}) - {}".format(self.dataTime, self.clientName, self.nomer, self.typeRemont)

    def save(self, *args, **kwargs):
        try:
            if self.typeIB == "ALFA6DC":
                if self.readyStatus != None and self.readyStatus.name == "Закрыт":
                    self.closed = True
                elif self.readyStatus != None and self.dateEnd > self.dataTime:
                    self.closed = True
                else:
                    self.closed = False            
            else:
                self.closed = self.active
        except:
            self.closed = False
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['uin'], name='uin')
        ]
        db_table = 'docZN'
        verbose_name = "Заказ - наряд"
        verbose_name_plural = "Заказ - наряды"


class DocZNWork(models.Model):
    zn                  = models.ForeignKey(DocZN, on_delete=models.SET_NULL, null=True, verbose_name="Заказ наряд")
    uin                 = models.CharField('Уникальный идентификатор', default='', null=True, max_length=100, blank=False) 
    type                = models.ForeignKey(RefTypeItemRepair, on_delete=models.SET_NULL, null=True, verbose_name="Тип в заказ наряде")
    work                = models.ForeignKey(RefWork, on_delete=models.SET_NULL, null=True, verbose_name="Работа")
    quantity            = models.FloatField("Количество", default=0.0, blank=True)
    price               = models.FloatField("Цена", default=0.0, blank=True)
    
    discountPercentage  = models.FloatField("Процент скидки", default=0.0, blank=True)
    discountAmount      = models.FloatField("Сумма скидки", default=0.0, blank=True)
    
    amount              = models.FloatField("Сумма", default=0.0, blank=True)
    amountResult        = models.FloatField("Сумма с учетом скидки", default=0.0, blank=True)
    
    def get_type(self):
        if self.type == None:
            return '-'
        return self.type

    def save(self, *args, **kwargs):
        try:
            if self.discountPercentage > 0:
                self.discountAmount     = self.price * self.quantity * self.discountPercentage / 100
                self.amountResult       = self.price * self.quantity - self.discountAmount
            else:
                self.discountAmount = 0
                self.amountResult   = self.price * self.quantity - self.discountAmount
        except:
            self.discountAmount = 0
            self.amountResult   = self.price * self.quantity

        super().save(*args, **kwargs)

    def __str__(self):
        return "{} / {}".format(self.zn, self.work)

    class Meta:
        indexes = [
            models.Index(fields=['zn'])
        ]
        db_table = 'docZNWork'
        verbose_name = "Работа заказ наряда"
        verbose_name_plural = "Работы заказ наряда"


class DocZNProduct(models.Model):
    zn                  = models.ForeignKey(DocZN, on_delete=models.SET_NULL, null=True, verbose_name="Заказ наряд")
    uin                 = models.CharField('Уникальный идентификатор', default='', null=True, max_length=100, blank=False) 
    type                = models.ForeignKey(RefTypeItemRepair, on_delete=models.SET_NULL, null=True, verbose_name="Тип в заказ наряде")
    product             = models.ForeignKey(RefProduct, on_delete=models.SET_NULL, null=True, verbose_name="Товар")
    quantity            = models.FloatField("Количество", default=0.0, blank=True)
    price               = models.FloatField("Цена", default=0.0, blank=True)
    
    discountPercentage  = models.FloatField("Процент скидки", default=0.0, blank=True)
    discountAmount      = models.FloatField("Сумма скидки", default=0.0, blank=True)
    
    amount              = models.FloatField("Сумма", default=0.0, blank=True)
    amountResult       = models.FloatField("Сумма с учетом скидки", default=0.0, blank=True)

    def get_type(self):
        if self.type == None:
            return '-'
        return self.type

    def save(self, *args, **kwargs):
        try:
            if self.discountPercentage > 0:
                self.discountAmount = self.price * self.quantity * self.discountPercentage / 100
                self.amountResult = self.price * self.quantity - self.discountAmount
            else:
                self.discountAmount = 0
                self.amountResult = self.price * self.quantity
        except:
            self.discountAmount = 0
            self.amountResult   = self.price * self.quantity

        super().save(*args, **kwargs)

    def __str__(self):
        return "{} / {}".format(self.zn, self.product)

    class Meta:
        indexes = [
            models.Index(fields=['zn'])
        ]
        db_table = 'docZNProduct'
        verbose_name = "Товар заказ наряда"
        verbose_name_plural = "Товары заказ наряда"


class DocZNProductCustomer(models.Model):
    zn                  = models.ForeignKey(DocZN, on_delete=models.SET_NULL, null=True, verbose_name="Заказ наряд")
    product             = models.CharField('Товар', default='', null=True, max_length=250, blank=False) 
    quantity            = models.FloatField("Количество", default=0.0, blank=True)
    price               = models.FloatField("Цена", default=0.0, blank=True)
    amount              = models.FloatField("Сумма", default=0.0, blank=True)
    article             = models.CharField("Артикул", default='', null=True, max_length=250, blank=False)
    
    def __str__(self):
        return "{} / {}".format(self.zn, self.product)

    class Meta:
        indexes = [
            models.Index(fields=['zn'])
        ]
        db_table = 'docZNProductCustomer'
        verbose_name = "Товар клиента заказ наряда"
        verbose_name_plural = "Товары клиента заказ наряда"


class DocZNRecomendation(models.Model):
    zn                  = models.ForeignKey(DocZN, on_delete=models.SET_NULL, null=True, verbose_name="Заказ наряд")
    name                = models.CharField('Наименование', default='', null=True, max_length=1000, blank=False) 
    uin                 = models.CharField('Уникальный идентификатор', default='', null=True, max_length=84, blank=False) 
    thisZN              = models.BooleanField("Этот документ", default=False)
    close               = models.BooleanField("Закрыта", default=False)
    date                = models.DateTimeField('Дата напоминания', default=datetime.now, blank=False)
    description         = models.CharField("Примечание", default='', null=True, max_length=2500, blank=False)
    reasonClose         = models.CharField("Причина завершения рекомендаций", default='', null=True, max_length=2500, blank=False)
    show                = models.BooleanField("Показывать", default=False)

    def __str__(self):
        return "{} / {}".format(self.zn, self.name)

    class Meta:
        indexes = [
            models.Index(fields=['zn'])
        ]
        db_table = 'docZNRecomendation'
        verbose_name = "Рекомендация заказ наряда"
        verbose_name_plural = "Рекомендации заказ наряда"

    
class DocZNPerformers(models.Model):
    zn                  = models.ForeignKey(DocZN, on_delete=models.SET_NULL, null=True, verbose_name="Заказ наряд")
    staff               = models.ForeignKey(RefStaff, related_name="staff", on_delete=models.SET_NULL, null=True, verbose_name="Исполнитель")
    uin                 = models.CharField('Уникальный идентификатор', default='', null=True, max_length=84, blank=False) 
    percent             = models.FloatField("Доля", default=0.0, blank=True)

    def __str__(self):
        return "{} / {}".format(self.zn, self.staff)

    class Meta:
        indexes = [
            models.Index(fields=['zn'])
        ]
        db_table = 'docZNPerformers'
        verbose_name = "Исполнитель заказ наряда"
        verbose_name_plural = "Исполнители заказ - наряда"


class DocRLK(models.Model):
    
    dataTime                    = models.DateTimeField('Дата', default=datetime.now, blank=False)    
    type_archive                = models.ForeignKey(RefReasonArchiveRLK, null=True, on_delete=models.SET_NULL, verbose_name="Причина отправки в архив", blank=True) 
    status                      = models.ForeignKey(RefStatusRLK, null=True, on_delete=models.SET_NULL, verbose_name="Статус рабочего листа", blank=True) 
    dataEnd                     = models.DateTimeField('Дата окончания визита', default=datetime.now, blank=False)    
    timeStr                     = models.CharField('Время', default='', null=True, max_length=5, blank=False)  
    uin                         = models.CharField('uin', default='', null=True, max_length=100, blank=False)
    nomer                       = models.CharField('Номер', default='', null=True, max_length=25, blank=False)
    clientName                  = models.CharField("Наименование клиента", default='', null=True, max_length=250, blank=False)    
    unit                        = models.ForeignKey(RefUnit, null=True, on_delete=models.SET_NULL, verbose_name="Подразделение") 
    unit_dc                     = models.ForeignKey(RefUnit, related_name='unit_dc' ,null=True, on_delete=models.SET_NULL, verbose_name="Подразделение ДЦ") 
    staff                       = models.ForeignKey(RefStaff, null=True, on_delete=models.SET_NULL, verbose_name="Менеджер") 
    listened                    = models.BooleanField("Прослушан", default=False)
    no_records                  = models.BooleanField("Нет записи", default=False)
    archiveDayToDay             = models.BooleanField("Закрыт день в день", default=False)
    tradeInModel                = models.CharField('Трейд-ин модель', blank=True, default='', null=True, max_length=250)
    cars                        = models.ForeignKey(RefCars, blank=True, null=True, on_delete=models.SET_NULL, verbose_name="Автомобиль")
    type                        = models.ForeignKey(RefTypeDocRLK, blank=True, null=True, on_delete=models.SET_NULL, verbose_name="Тип рабочего листа")
    #statusOcenka                = models.ForeignKey(RefStatusOcenka, blank=True, null=True, on_delete=models.SET_NULL, verbose_name="Статус интерактивной оценки")
    staffECO1                   = models.ForeignKey(RefStaff, blank=True, related_name="staff_eco_1", null=True, on_delete=models.SET_NULL, verbose_name="Согласователь до диагностики")
    staffECO2                   = models.ForeignKey(RefStaff, blank=True, related_name="staff_eco_2", null=True, on_delete=models.SET_NULL, verbose_name="Согласователь после диагностики") 
    contacType                  = models.ForeignKey(RefContactType, blank=True, null=True, on_delete=models.SET_NULL, verbose_name="Вид контакта")
    phone                       = models.CharField("Телефон", default='', null=True, max_length=2500, blank=False)
    customer                    = models.ForeignKey(RefCustomer, null=True, on_delete=models.SET_NULL, verbose_name="Клиент")  
    commentAdministrator        = models.CharField("Комментарий администратора", default='', null=True, max_length=5112, blank=False)
    commentManager              = models.CharField("Комментарий менеджера", default='', null=True, max_length=5112, blank=False)
    manager_trade_in            = models.CharField("Менеджер TradeIn", default='', null=True, max_length=512, blank=False)
    dataTimeCreate              = models.DateTimeField('Дата создания', null=True, blank=True)    
    is_missed                   = models.IntegerField("Упущенный клиент", default=0, blank=True)
    eco                         = models.BooleanField("Оценка автомобиля", default=False)
    archive                     = models.BooleanField("Архив", default=False)
    dateArchive                 = models.DateTimeField('Дата отправки в архив', null=True, blank=True)    
    reasonArchive               = models.CharField('Причина отправки в архивв', blank=True, default='', null=True, max_length=1024)
    footing                     = models.ForeignKey('self', null=True, on_delete=models.SET_NULL, verbose_name="Основание", blank=True) 
    vin_trade_in                = models.CharField('VIN трейд ин', blank=True, default='', null=True, max_length=17)
    estimation_id               = models.IntegerField('ИД оценки', default=0, blank=True, null=False)

    def rlk_trade_in(self):
        return DocRLK.objects.filter(uin__in = DocRLK.objects.filter(footing = self).values_list('uin', flat=True)).filter(eco = True)

    def opfu_in(self):
        return DocRLK.objects.filter(uin__in = DocRLK.objects.filter(footing = self).values_list('uin', flat=True)).filter(type__id = 4)

    def rating_sms_opros(self):
        count_opros = DocOprosCarShipment.objects.filter(shipment__rlk = self).count()
        if count_opros > 0:
            opros = DocOprosCarShipment.objects.filter(shipment__rlk = self)[0]  
            return opros.get_rating()
        return 0 


    def get_check(self):
        check = self.check_list_kg()
        if check == None:
            check = self.check_list_cvc()
        return check

    def get_opros(self):
        count_opros = DocOprosCarShipment.objects.filter(shipment__rlk = self).count()
        if count_opros > 0:
            opros = DocOprosCarShipment.objects.filter(shipment__rlk = self)[0]  
            return opros
        return None 

    def time_visit(self):
        if self.dataEnd > self.dataTimeCreate:
            return self.dataEnd - self.dataTimeCreate
        else: 
            return '0:00:00'

    def check_list_kg(self):
        if self.unit.buauto:
            from checklists.models import CheckList_op_kors
            checklists = CheckList_op_kors.objects.filter(rlk = self)
            if checklists.count() == 1:
                return CheckList_op_kors.objects.filter(rlk = self)[0]
        else:
            from checklists.models import CheckList
            checklists = CheckList.objects.filter(rlk = self)
            if checklists.count() == 1:
                return CheckList.objects.filter(rlk = self)[0] 
        return None
    
    def check_list_kg_result(self):
        if self.unit.buauto:
            from checklists.models import CheckList_op_kors
            checklists = CheckList_op_kors.objects.filter(rlk = self)
            if checklists.count() == 1:
                return CheckList_op_kors.objects.filter(rlk = self)[0].result 
        else:
            from checklists.models import CheckList
            checklists = CheckList.objects.filter(rlk = self)
            if checklists.count() == 1:
                return CheckList.objects.filter(rlk = self)[0].result 
        return 0

    def check_list_cvc(self):
        from recognition.models import Records_voice_recorder_cvc_checklist
        checklists = Records_voice_recorder_cvc_checklist.objects.filter(rlk = self)
        if checklists.count() == 1:
            return Records_voice_recorder_cvc_checklist.objects.filter(rlk = self)[0] 
        return None   

    def check_list_cvc_result(self):
        from recognition.models import Records_voice_recorder_cvc_checklist
        checklists = Records_voice_recorder_cvc_checklist.objects.filter(rlk = self)
        if checklists.count() == 1:
            return Records_voice_recorder_cvc_checklist.objects.filter(rlk = self)[0].result 
        return 0 

    def events(self):
        return DocRLKEvents.objects.filter(rlk = self).order_by('dataTime')

    def days(self):
        return self.dataTime.strftime("%B-%d-%Y") 

    def sound_count(self):
        count = 0
        if self.staff == None:
            return count
        
        if self.staff.domain_login == '':
            return count
       
        from recognition.models import Records_voice_recorder
        login = self.staff.domain_login
        start   = self.dataTimeCreate.replace(hour=0) 
        end     = self.dataTimeCreate.replace(hour=23)
        count = Records_voice_recorder.objects.filter(user__username = login).filter(date__lt = end).filter(date__gt = start).count()

        return count

    def estimation(self):
        from documents.rlk_estimation import resolve_estimation_for_rlk
        est = resolve_estimation_for_rlk(self)
        return est.id if est is not None else None

    def estimation_source_rlk(self):
        """РЛ, по которому смотреть оценку: свой или twin с тем же UIN."""
        from documents.rlk_estimation import sibling_rlk_with_estimation, resolve_estimation_for_rlk
        est = resolve_estimation_for_rlk(self)
        if est is not None and est.rlk_id:
            if est.rlk_id == self.pk:
                return self
            return est.rlk
        twin = sibling_rlk_with_estimation(self)
        return twin or self
    
    def estimation_staff_uin(self):
        if hasattr(self, 'reginteractivocenkarlk'):
            if self.reginteractivocenkarlk.staff_rlk != None:
                return self.reginteractivocenkarlk.staff_rlk.uin
        return None

    def estimation_vin(self):
        # Сначала пробуем через RLK-обёртку
        try:
            rlk_link = self.reginteractivocenkarlk
            if rlk_link.estimation:
                return rlk_link.estimation.vin
        except Exception:
            pass

        # Фоллбек на прямое отношение оценки
        if hasattr(self, 'reginteractivocenkarlk'):
            return self.reginteractivocenkarlk.estimation.vin

        return None
        
    def estimation_status(self):
        if hasattr(self, 'reginteractivocenkarlk'):
            if self.reginteractivocenkarlk.status == None:
                return None
            return self.reginteractivocenkarlk.status.name 
        return None
    
    def estimation_modification_info(self):
        if hasattr(self, 'reginteractivocenkarlk'):
            if self.reginteractivocenkarlk.estimation.modification == None:
                return None
            return self.reginteractivocenkarlk.estimation.modification.model.mark.name  + ' ' + self.reginteractivocenkarlk.estimation.modification.model.name + ' ' + self.reginteractivocenkarlk.estimation.modification.name  
        return None

    def estimation_start_formated(self):
        if hasattr(self, 'reginteractivocenkarlk'):
            if self.reginteractivocenkarlk.estimation.start_estimation == None:
                return None
            return self.reginteractivocenkarlk.estimation.start_estimation.strftime("%d.%m.%Y %H:%M:%S")   
        return None

    def estimation_end_formated(self):
        if hasattr(self, 'reginteractivocenkarlk'):
            if self.reginteractivocenkarlk.estimation.end_estimation == None:
                return None
            return self.reginteractivocenkarlk.estimation.end_estimation.strftime("%d.%m.%Y %H:%M:%S")   
        return None
    
    def estimation_year(self):
        if hasattr(self, 'reginteractivocenkarlk'):
            return self.reginteractivocenkarlk.estimation.year
        return 0

    @staticmethod
    def resolve_op_footing_by_tradein_uin(uin: str):
        """
        РЛ ОП для trade-in по UIN оценки.

        У одного UIN может быть несколько DocRLK (дубли trade-in); footing
        часто заполнен не на текущей строке, а на «сестре» с тем же UIN.
        Берём все листы с этим UIN, у которых заполнен footing, и возвращаем
        footing с самой свежей датой.
        """
        uin = (uin or '').strip()
        if not uin:
            return None
        sibling = (
            DocRLK.objects.filter(uin=uin)
            .exclude(footing_id__isnull=True)
            .select_related('footing')
            .order_by('-footing__dataTime', '-footing_id', '-id')
            .first()
        )
        return sibling.footing if sibling else None

    @staticmethod
    def resolve_op_footing_map_by_uins(uins):
        """
        Массово: trade-in UIN → dict(id, uin, number, date) по РЛ ОП (footing).
        """
        cleaned = {(u or '').strip() for u in (uins or []) if (u or '').strip()}
        if not cleaned:
            return {}
        rows = (
            DocRLK.objects.filter(uin__in=cleaned)
            .exclude(footing_id__isnull=True)
            .values(
                'uin',
                'footing_id',
                'footing__uin',
                'footing__nomer',
                'footing__dataTime',
            )
            .order_by('uin', '-footing__dataTime', '-footing_id')
        )
        result = {}
        for row in rows:
            key = (row.get('uin') or '').strip()
            if not key or key in result:
                continue
            result[key] = {
                'id': row.get('footing_id') or 0,
                'uin': (row.get('footing__uin') or '').strip(),
                'number': (row.get('footing__nomer') or '').strip(),
                'date': row.get('footing__dataTime'),
            }
        return result

    def save(self, *args, **kwargs):
        
        super().save(*args, **kwargs)

        # Q(
        # Q(type__id=2, unit_dc__buauto=True) |
        # Q(type__id=7, eco=True) |
        # Q(type__id=1, eco=True) |
        # Q(type__id=19, eco=True) |
        # Q(eco=True)

        try:
            from analytics.models import TradeInFunnel
            
            def _get_brand(name, city_name):
                try:
                    if name.find('КорсАвто') > -1:
                        return 'корсавто'
                    if name.find('ваз') > -1:
                        return 'lada'
                    if name.find('энгельса') > -1:
                        return 'lada'
                    name = name.replace('Тула', '').replace('Калуга', '').replace('Обнинск', '').replace('Курск (50 лет Октября)', '').replace('(энгельса 173)', '').replace('Курск', '').replace('Новомосковск', '').replace('Серпухов', '').replace('Коломна', '').replace('Ногинск', '').replace('Орел', '').replace('Ярославль', '')
                    name = name.replace('ОП ', '').replace('ДЦ ', '').replace('Техцентр  ', '').replace(city_name, '').strip()
                    return name.lower()
                except: 
                    return name  
                return ''
            
            def _get_info_unit(unit_source_id):
                group = RefUnitGroup.objects.filter(
                    units__id=unit_source_id,
                    bu_auto=True,
                    active=True
                ).prefetch_related(
                    'units'
                ).first()
                if not group:
                    return None, None
                for unit in group.units.all():
                    if 'КорсАвто' in unit.name:
                        return unit.name, unit.id
                return None, None
                
            saves = False
            if self.eco:
                saves = True
            if saves == False:
                if self.unit_dc != None and self.unit_dc.buauto and self.type.id == 2:
                    saves = True
            if saves:
                
                rlk_number = self.nomer or ""
                footing_rlk_id          = 0
                footing_rlk_uin         = ''
                footing_rlk_number      = ''
                footing_rlk_date        = None
                unit_id                 = 0
                unit_name               = ''
                unit_source_id          = 0
                unit_source_name        = ''
                city_id                 = 0
                city_name               = ''
                brand                   = ''

                # РЛ ОП: не только self.footing, а поиск среди всех DocRLK
                # с тем же UIN, у которых footing заполнен.
                footing_op = DocRLK.resolve_op_footing_by_tradein_uin(self.uin)
                if footing_op is None and self.footing_id:
                    footing_op = self.footing
                if footing_op is not None:
                    footing_rlk_id        = footing_op.id or 0
                    footing_rlk_uin       = footing_op.uin or ""
                    footing_rlk_number    = footing_op.nomer or ""
                    footing_rlk_date      = footing_op.dataTime
                
                if self.unit != None:
                    unit_id   = self.unit.id
                    unit_name = self.unit.name or ""
                    if self.unit.city != None:
                        city_id     = self.unit.city.id 
                        city_name   = self.unit.city.name 

                if self.unit_dc != None:
                    unit_source_id   = self.unit_dc.id or 0
                    unit_source_name = self.unit_dc.name or ""
                    if city_id == 0 and self.unit_dc.city != None:
                        city_id     = self.unit_dc.city.id 
                        city_name   = self.unit_dc.city.name
                elif self.unit != None:
                    unit_source_id   = self.unit.id or 0
                    unit_source_name = self.unit.name or ""

                date_rlk      = self.dataTime
                date_archive  = self.dateArchive
                archive_name      = ''
                archive_comment   = ''
                
                if unit_id == 0 and unit_source_id != 0:
                    info = _get_info_unit(unit_source_id)
                    unit_id     = 0 if info[1] == None else info[1] 
                    unit_name   = '' if info[0] == None else info[0] 
                
                if self.reasonArchive != '':
                    mas_data = self.reasonArchive.split(':')
                    archive_name      = mas_data[0]
                    archive_comment   = mas_data[1]
                vin_trade_in = self.vin_trade_in

                if unit_source_name != '':
                    brand = _get_brand(unit_source_name, city_name)
                elif unit_name != '':
                    brand = _get_brand(unit_name, city_name)

                TradeInFunnel.objects.update_or_create(
                        rlk_id = self.id,
                        defaults={
                            'rlk_uin'           : self.uin,
                            'rlk_number'        : rlk_number,
                            'footing_rlk_id'    : footing_rlk_id,
                            'footing_rlk_uin'   : footing_rlk_uin,
                            'footing_rlk_number': footing_rlk_number,
                            'footing_rlk_date'  : footing_rlk_date,
                            'brand'             : brand,
                            'city_id'           : city_id,
                            'city_name'         : city_name,
                            'unit_id'           : unit_id,
                            'unit_name'         : unit_name,
                            'unit_source_id'    : unit_source_id,
                            'unit_source_name'  : unit_source_name,
                            'unit_source_id'    : unit_source_id,
                            'date_rlk'          : date_rlk,
                            'date_archive'      : date_archive,
                            'archive_name'      : archive_name,
                            'archive_comment'   : archive_comment,
                            'vin_trade_in'      : vin_trade_in,
                        }
                    )

        except Exception as e:
            error_text = ' - ' + str(self.id) + ' ' + str(e)  # Текст исключения
            
        
        
    def __str__(self):
        return "{} ({} - {}) - {}".format(self.dataTime, self.clientName, self.nomer, self.unit)

    class Meta:
        indexes = [
            models.Index(fields=['uin'])
        ]
        db_table = 'docRLK'
        verbose_name = "Рабочий лист"
        verbose_name_plural = "Рабочие - листы"


class DocLO(models.Model):
    uin                     = models.CharField('uin', default='', null=True, max_length=64, blank=False)
    active                  = models.BooleanField("Проведен", default=False)
    nomer                   = models.CharField('Номер', default='', null=True, max_length=25, blank=False)
    dataTime                = models.DateTimeField('Дата', default=datetime.now, blank=False)
    organization            = models.ForeignKey(RefOrganization, on_delete=models.SET_NULL, null=True, verbose_name="Организация")
    filial                  = models.ForeignKey(RefFilial, on_delete=models.SET_NULL, null=True, verbose_name="Филиал")
    unit                    = models.ForeignKey(RefUnit, on_delete=models.SET_NULL, null=True, verbose_name="Подразделение")
    store                   = models.ForeignKey(RefStore, null=True, on_delete=models.SET_NULL, verbose_name='Склад / стоянка')
    type_reception          = models.ForeignKey(RefTypeReceptionCarsOrganization, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Тип приема автомобиля')
    staff                   = models.ForeignKey(RefStaff, related_name="staff_eco", on_delete=models.SET_NULL, null=True, verbose_name="Оценщик")
    carsGRZ                 = models.CharField('Гос. номер', default='', null=True, max_length=25, blank=False)
    customer                = models.ForeignKey(RefCustomer, on_delete=models.SET_NULL, null=True, verbose_name="Клиент")
    clientName              = models.CharField('Клиент строкой', default='', null=True, max_length=250, blank=False)
    cars                    = models.ForeignKey(RefCars, on_delete=models.SET_NULL, null=True, verbose_name="Автомобиль") 
    vin                     = models.CharField("ВИН", max_length=21, default='')
    vin2                    = models.CharField("Дополнительный ВИН", max_length=21, default='', blank=True)
    year                    = models.IntegerField("Год выпуска", blank=True, default=0)
    run                     = models.IntegerField("Пробег", default=0, blank=True)
    owners                  = models.IntegerField("Владельцев", blank=True, default=0)
    keys                    = models.IntegerField("Количество ключей", blank=True, default=0)
    color                   = models.CharField("Цвет", blank=True, max_length=1024, default='')
    cost_price              = models.IntegerField("Себестоимость", blank=True, default=0)
    bcp                     = models.IntegerField("БЦП", blank=True, default=0)
    rlk                     = models.ForeignKey(DocRLK, on_delete=models.SET_NULL, null=True, verbose_name="Рабочий лист")
    recomendation           = models.CharField('Рекомендация / результат диагностики', default='', null=True, max_length=5024, blank=True)
    modification_autoru     = models.ForeignKey(AutoruModification, null=True, on_delete=models.SET_NULL, verbose_name='Модификация')
    complectation_autoru    = models.ForeignKey(AutoruComplectation, null=True, on_delete=models.SET_NULL, verbose_name='Комплектация', blank=True)
    description_podgotovka  = models.CharField("Комментарий для отдела подготовки", max_length=15120, default='')
    description_op          = models.CharField("Комментарий для отдела продаж", max_length=15120, default='')
    vin_new                 = models.CharField("ВИН нового авто", max_length=21, default='')
    name_new_auto           = models.CharField("Марка / модель нового авто", max_length=512, default='')
    agreement_number        = models.CharField("Марка / модель нового авто", max_length=512, default='')
    agreement_unit          = models.ForeignKey(RefUnit, on_delete=models.SET_NULL, null=True, related_name='agreement_unit', verbose_name="Подразделение соглашение")
    agreement_unit_bu       = models.BooleanField("Соглашение БУ", default=False)
    auction                 = models.BooleanField("Аукцион", default=False)
    auction_comment         = models.CharField("Аукцион коментарий", max_length=1024, default='', blank=True)
    kolesa2_reception       = models.BooleanField(
        "Приёмка второго комплекта колёс",
        default=False,
        help_text='Признак, что по листу оценки принят второй комплект колёс',
    )

    def __str__(self):
        return "{} ({} - {}) - {}".format(self.dataTime, self.clientName, self.nomer, self.type_reception)

    def save(self, *args, **kwargs):
        
        try:
            from register.models import RegInteractivOcenkaRLK
            if self.rlk != None:
                ocenka = RegInteractivOcenkaRLK.objects.filter(rlk = self.rlk)
                if ocenka.count() == 1:
                    if self.active and ocenka[0].status.id != 8: 
                        ocenka[0].save()                    
                    elif self.active == False and ocenka[0].status.id == 8: 
                        ocenka[0].save()                    
        except:
            s = 1
        
        super().save(*args, **kwargs)

        try:
            
            from analytics.models import TradeInFunnel
            
            lo_number = self.nomer or ""
            date_reception = None
            if self.active:
                date_reception = self.dataTime
                unit_id                 = self.unit.id
                unit_name               = self.unit.name
                type_reception_id       = self.type_reception.id
                type_reception_name     = self.type_reception.name

                TradeInFunnel.objects.update_or_create(
                        rlk_id = self.rlk.id,
                        defaults={
                            'lo_number'                : lo_number,
                            'date_reception_success'   : date_reception,
                            'unit_id'   : unit_id,
                            'unit_name' : unit_name,
                            'vin'       : self.vin,
                            'type_reception_id'     : type_reception_id,
                            'type_reception_name'   : type_reception_name,
                        }
                    )
            else:
                TradeInFunnel.objects.update_or_create(
                        rlk_id = self.rlk.id,
                        defaults={
                            'lo_number'                : lo_number,
                            'date_reception_success'    : None,
                        }
                    )
        except:
            s = 1
        

    class Meta:
        indexes = [
            models.Index(fields=['uin'])
        ]
        db_table = 'docLO'
        verbose_name = "Лист - оценки"
        verbose_name_plural = "Листы - оценок"


class DocRLKEvents(models.Model):
    uin             = models.CharField('uin', default='', null=True, max_length=100, blank=False)
    rlk             = models.ForeignKey(DocRLK, on_delete=models.SET_NULL, null=True, verbose_name="Рабочий лист")
    dataTime        = models.DateTimeField('Дата', default=datetime.now, blank=False)
    dataTimeEvent   = models.DateTimeField('Дата события',  null=True, blank=True)
    contacType      = models.ForeignKey(RefContactType, blank=True, null=True, on_delete=models.SET_NULL, verbose_name="Вид контакта")
    staff           = models.ForeignKey(RefStaff, null=True, on_delete=models.SET_NULL, verbose_name="Менеджер") 
    comment         = models.CharField("Комментарий менеджера", default='', null=True, max_length=1024, blank=False)
    status          = models.ForeignKey(RefStatusEvent, blank=True, null=True, on_delete=models.SET_NULL, verbose_name="Статус события")

    def __str__(self):
        return "{} {} - {} - {}".format(self.dataTime, self.rlk, self.staff, self.contacType)

    class Meta:
        indexes = [
            models.Index(fields=['uin']),
            models.Index(fields=['rlk']),
        ]
        db_table = 'docRLKEvents'
        verbose_name = "Событие рабочего листа"
        verbose_name_plural = "События рабочих листов"


class DocCarAgreement(models.Model):
    uin             = models.CharField('uin', default='', null=True, max_length=100, blank=False)
    nomer           = models.CharField('Номер', default='', null=True, max_length=25, blank=False)
    dataTime        = models.DateTimeField('Дата', default=datetime.now, blank=False)    
    timeStr         = models.CharField('Время', default='', null=True, max_length=5, blank=False)  
    active          = models.BooleanField("Проведен", default=False)
    organization    = models.ForeignKey(RefOrganization, on_delete=models.SET_NULL, null=True, verbose_name="Организация")
    unit            = models.ForeignKey(RefUnit, null=True, on_delete=models.SET_NULL, verbose_name="Подразделение") 
    clientName      = models.CharField("Наименование клиента", default='', null=True, max_length=250, blank=False)    
    client          = models.ForeignKey(RefCustomer, null=True, on_delete=models.SET_NULL, verbose_name="Клиент")  
    staff           = models.ForeignKey(RefStaff, null=True, on_delete=models.SET_NULL, verbose_name="Менеджер") 
    cars                                    = models.ForeignKey(RefCars, null=True, on_delete=models.SET_NULL, verbose_name="Автомобиль")
    rlk                                     = models.ForeignKey(DocRLK, null=True, on_delete=models.SET_NULL, verbose_name="РЛК")  
    amount                                  = models.FloatField("Сумма продажи", default=0.0, blank=True)
    amountAddDiscountAmountTorg             = models.FloatField("Сумма продажи + скидка торг", default=0.0, blank=True)
    cost_price                              = models.FloatField("Себестоимость", default=0.0, blank=True)
    outlay                                  = models.IntegerField("Расходы на АМ", blank=True, default=0)
    lo                                      = models.ForeignKey(DocLO, null=True, on_delete=models.SET_NULL, verbose_name="Лист оценки ам")
    discountAmount                          = models.FloatField("Скидка итог", default=0.0, blank=True)
    discountAmountTorg                      = models.FloatField("Скидка торг", default=0.0, blank=True)
    discountAmountTradeIN                   = models.FloatField("Скидка трейдин", default=0.0, blank=True)
    discountAmountTorgComment               = models.CharField('Комментарий скидки торг', default='', null=True, max_length=512, blank=True) 
    discountAmountTradeINComment            = models.CharField('Комментарий  скидки трейд ин', default='', null=True, max_length=512, blank=True) 
    run                                     = models.IntegerField("Пробег", blank=True, default=0)
    owners                                  = models.IntegerField("Владельцев", blank=True, default=0)
    typeSale                                = models.CharField('Тип продажи', default='', null=True, max_length=512, blank=True) 
    check_estimated                         = models.BooleanField("Правило расчетное выполнено", default=False)
    check_actual                            = models.BooleanField("Правило фактическое выполнено", default=False)
    check_date_time                         = models.DateTimeField('Дата проверки', default=datetime.now, blank=False)    
    bu_wheels_est                           = models.FloatField("Расчетные данные бу шины", default=0.0, blank=True)
    bu_wheels_actual                        = models.FloatField("Фактические данные бу шины", default=0.0, blank=True)
    kso_est                                 = models.FloatField("Расчетные данные ксо", default=0.0, blank=True)
    kso_actual                              = models.FloatField("Фактические данные ксо", default=0.0, blank=True)
    check_text                              = models.CharField('Правило', default='', null=True, max_length=2048, blank=True)
    cm_est                                  = models.FloatField("КМ расчетный", default=0.0, blank=True)
    cm_min                                  = models.FloatField("КМ минимальный", default=0.0, blank=True)                                                               
    cm_actual                               = models.FloatField("КМ фактический", default=0.0, blank=True)
    cm_goal                                 = models.FloatField("КМ целевой", default=0.0, blank=True)
    date_planed_sale                        = models.DateTimeField('Планируемая дата выдачи', default=datetime.now, blank=False)    

    def car_shipment_count(self):
        from documents.models import DocCarShipment 
        return DocCarShipment.objects.filter(agreement = self).filter(active = True).count()

    def opcion(self):
        return self.cm_actual - (self.amount - (self.cost_price + self.outlay))

    def cum(self):
        return self.amount - (self.cost_price + self.outlay)
    
    def save(self, *args, **kwargs):
        
        try:
            self.amountAddDiscountAmountTorg = self.amount + self.discountAmountTorg
        except:
            self.amountAddDiscountAmountTorg = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return "{} ({} - {}) - {}".format(self.dataTime, self.clientName, self.nomer, self.unit)

    class Meta:
        indexes = [
            models.Index(fields=['uin']),
            models.Index(fields=['rlk'])
        ]
        db_table = 'docCarAgreement'
        verbose_name = "Соглашение о покупке автомобиля"
        verbose_name_plural = "Соглашения о покупке автомобилей"


class DocCarShipment(models.Model):
    uin             = models.CharField('uin', default='', null=True, max_length=100, blank=False)
    nomer           = models.CharField('Номер', default='', null=True, max_length=25, blank=False)
    dataTime        = models.DateTimeField('Дата', default=datetime.now, blank=False)    
    timeStr         = models.CharField('Время', default='', null=True, max_length=5, blank=False)  
    active          = models.BooleanField("Проведен", default=False)
    organization    = models.ForeignKey(RefOrganization, on_delete=models.SET_NULL, null=True, verbose_name="Организация")
    unit            = models.ForeignKey(RefUnit, null=True, on_delete=models.SET_NULL, verbose_name="Подразделение") 
    clientName      = models.CharField("Наименование клиента", default='', null=True, max_length=250, blank=False)    
    client          = models.ForeignKey(RefCustomer, null=True, on_delete=models.SET_NULL, verbose_name="Клиент")  
    staff           = models.ForeignKey(RefStaff, null=True, on_delete=models.SET_NULL, verbose_name="Менеджер") 
    cars            = models.ForeignKey(RefCars, null=True, on_delete=models.SET_NULL, verbose_name="Автомобиль")
    #uid            = models.UUIDField(max_length=100, blank=True, unique=True, default=uuid.uuid4)
    rlk             = models.ForeignKey(DocRLK, null=True, on_delete=models.SET_NULL, verbose_name="РЛК")  
    agreement                               = models.ForeignKey(DocCarAgreement, null=True, on_delete=models.SET_NULL, verbose_name="Соглашение о покупке автомобиля")  
    amount                                  = models.FloatField("Сумма продажи", default=0.0, blank=True)
    amountAddDiscountAmountTorg             = models.FloatField("Сумма продажи + скидка торг", default=0.0, blank=True)
    cost_price                              = models.FloatField("Себестоимость", default=0.0, blank=True)
    outlay                                  = models.IntegerField("Расходы на АМ", blank=True, default=0)
    lo                                      = models.ForeignKey(DocLO, null=True, on_delete=models.SET_NULL, verbose_name="Лист оценки ам")
    discountAmount                          = models.FloatField("Скидка итог", default=0.0, blank=True)
    discountAmountTorg                      = models.FloatField("Скидка торг", default=0.0, blank=True)
    discountAmountTradeIN                   = models.FloatField("Скидка трейдин", default=0.0, blank=True)
    discountAmountTorgComment               = models.CharField('Комментарий скидки торг', default='', null=True, max_length=512, blank=True) 
    discountAmountTradeINComment            = models.CharField('Комментарий  скидки трейд ин', default='', null=True, max_length=512, blank=True) 
    run                                     = models.IntegerField("Пробег", blank=True, default=0)
    owners                                  = models.IntegerField("Владельцев", blank=True, default=0)
    typeSale                                = models.CharField('Тип продажи', default='', null=True, max_length=512, blank=True)
    amount_reward_credit                    = models.FloatField("Сумма вознаграждения кредит", default=0.0, blank=True)
    amount_reward_opfu                      = models.FloatField("Сумма вознаграждения ОПФУ", default=0.0, blank=True)
    amount_kits                             = models.FloatField("Сумма продажи комплектов", default=0.0, blank=True)
    cumulative_margin                       = models.FloatField("Кумулятивная маржа", default=0.0, blank=True)
    
    def cum(self):
        return self.amount - (self.cost_price + self.outlay)
    
    def get_opros(self):
        if DocOprosCarShipment.objects.filter(shipment = self).count() > 0:  
            opros = DocOprosCarShipment.objects.filter(shipment = self)[0] 
            return opros
        else: 
            return None
    
    def get_opros_close(self):
        if DocOprosCarShipment.objects.filter(shipment = self).count() > 0:  
            opros = DocOprosCarShipment.objects.filter(shipment = self)[0] 
            return opros.close
        else: 
            return False

    def save(self, *args, **kwargs):
        
        try:
            self.amountAddDiscountAmountTorg = self.amount + self.discountAmountTorg
        except:
            self.amountAddDiscountAmountTorg = 0
        
        try:
            if self.lo != None:
                from website.views import refresh_balance_unit_car_shipment
                refresh_balance_unit_car_shipment(self.id)

        except:
            s = 1

        super().save(*args, **kwargs)

    def __str__(self):
        return "{} ({} - {}) - {}".format(self.dataTime, self.clientName, self.nomer, self.unit)

    class Meta:
        indexes = [
            models.Index(fields=['uin']),
            models.Index(fields=['rlk']),
            models.Index(fields=['agreement'])
        ]
        db_table = 'docCarShipment'
        verbose_name = "Отгрузка автомобиля"
        verbose_name_plural = "Отгрузки автомобилей"


class DoсRecomendation(models.Model):
    zn                      = models.ForeignKey(DocZN, on_delete=models.SET_NULL, null=True, verbose_name="Заказ наряд")
    dataTime                = models.DateTimeField('Дата', default=datetime.now, blank=True)    
    name                    = models.CharField("Наименование", default='', null=True, max_length=250, blank=False)
    dataTimeCutomerEvent    = models.DateTimeField('Дата', null=True, blank=True)   
    customerStatus          = models.IntegerField('Статус согласования клиента', default=0) # 0 - неактивна - 1 на согласовании - 2 - согласована - 3 отклонена
    status                  = models.IntegerField('Статус рекомендации', default=0)         # 0 - новая - 1 обрабатывается - 2 добавлен в ЗН - 3 добавлено в рекомендации - 4 отменено
    kod_recomendation       = models.IntegerField('Код согласования', default = random.randrange(1000, 9999))

    def recomendation_works(self):
        return DoсRecomendationWork.objects.filter(recomendation = self) 
    def recomendation_works_count(self):
        return DoсRecomendationWork.objects.filter(recomendation = self).count() 
    def recomendation_works_amount(self):
        sum = DoсRecomendationWork.objects.filter(recomendation = self).aggregate(Sum('amount'))
        sum_work = sum['amount__sum']
        if sum_work == None:
            sum_work = 0
        else:
            sum_work = round(sum_work, 2)
        return sum_work

    def recomendation_products(self):
        return DoсRecomendationProduct.objects.filter(recomendation = self) 
    def recomendation_products_count(self):
        return DoсRecomendationProduct.objects.filter(recomendation = self).count() 
    def recomendation_products_amount(self):
        sum = DoсRecomendationProduct.objects.filter(recomendation = self).aggregate(Sum('amount'))
        sum_products = sum['amount__sum']
        if sum_products == None:
            sum_products = 0
        else:
            sum_products = round(sum_products, 2)
        return sum_products 

    def recomendation_files(self):
        return DocRecomendationFiles.objects.filter(recomendation = self) 
    def recomendation_files_count(self):
        return DocRecomendationFiles.objects.filter(recomendation = self).count() 

    def recomendation_amount(self):
        #работы 
        sum = DoсRecomendationWork.objects.filter(recomendation = self).aggregate(Sum('amount'))
        sum_work = sum['amount__sum']
        if sum_work == None:
            sum_work = 0
        else:
            sum_work = round(sum_work, 2)
        #товары
        sum = DoсRecomendationProduct.objects.filter(recomendation = self).aggregate(Sum('amount'))
        sum_products = sum['amount__sum']
        if sum_products == None:
            sum_products = 0
        else:
            sum_products = round(sum_products, 2)
        return sum_work + sum_products

    def __str__(self):
        return "{} {} - {}".format(self.dataTime, self.name, self.zn)

    class Meta:
        db_table = 'doсRecomendation'
        verbose_name = "Рекомендация расширения зн"
        verbose_name_plural = "Рекомендации расширений зн"


class DoсRecomendationWork(models.Model):
    recomendation   = models.ForeignKey(DoсRecomendation, on_delete=models.SET_NULL, null=True, verbose_name="Рекомендация")
    work            = models.ForeignKey(RefWork, on_delete=models.SET_NULL, null=True, verbose_name="Работа")
    quantity        = models.FloatField("Количество", default=0.0, blank=True)
    price           = models.FloatField("Цена", default=0.0, blank=True)
    amount          = models.FloatField("Сумма", default=0.0, blank=True)

    def __str__(self):
        return "{} / {}".format(self.recomendation, self.work)

    class Meta:
        indexes = [
            models.Index(fields=['recomendation'])
        ]
        db_table = 'doсRecomendationWork'
        verbose_name = "Работа заказ наряда"
        verbose_name_plural = "Работы заказ наряда"


class DoсRecomendationProduct(models.Model):
    recomendation   = models.ForeignKey(DoсRecomendation, on_delete=models.SET_NULL, null=True, verbose_name="Рекомендация")
    product         = models.ForeignKey(RefProduct, on_delete=models.SET_NULL, null=True, verbose_name="Товар")
    quantity        = models.FloatField("Количество", default=0.0, blank=True)
    price           = models.FloatField("Цена", default=0.0, blank=True)
    amount          = models.FloatField("Сумма", default=0.0, blank=True)

    def __str__(self):
        return "{} / {}".format(self.recomendation, self.product)

    class Meta:
        indexes = [
            models.Index(fields=['recomendation'])
        ]
        db_table = 'doсRecomendationProduct'
        verbose_name = "Товар рекомендации"
        verbose_name_plural = "Товары рекомендации"


class DocRecomendationFiles(models.Model):
    recomendation   = models.ForeignKey(DoсRecomendation, on_delete=models.SET_NULL, null=True, verbose_name="Рекомендация")
    file            = models.ImageField(upload_to='recomendations/%Y/%m/%d/', max_length=100, verbose_name="Файл", blank=True, null=True)
    
    def is_video(self):
        list_world_name = self.file.name.lower().split('.')
        format = list_world_name[-1]
        if format.find('jpg') > -1 or format.find('jpeg') > -1 or format.find('svg') > -1 or format.find('gif') > -1 or format.find('png') > -1 or format.find('tiff') > -1:
            return False
        return True

    def __str__(self):
        return "{}".format(self.recomendation)

    class Meta:
        indexes = [
            models.Index(fields=['recomendation'])
        ]
        db_table = 'docRecomendationFiles'
        verbose_name = "Файл рекомендации"
        verbose_name_plural = "Файлы рекомендаций"


class DocOprosZN(models.Model):
    uin         = models.CharField('uin', default='', null=True, max_length=64, blank=False)
    zn          = models.ForeignKey(DocZN, on_delete=models.SET_NULL, null=True, verbose_name="Заказ - наряд")
    dataTime    = models.DateTimeField('Дата', default=datetime.now, blank=False) 
    dataClose   = models.DateTimeField('Дата прохождения опроса', null=True, blank=True)
    v1          = models.IntegerField(default=0, verbose_name='Как бы вы оценили общую удовлетворенность обслуживанием в дилерском центре')
    v2          = models.IntegerField(default=0, verbose_name='С какой вероятностью Вы порекомендовали бы нас своим друзьям или знакомым')
    v3          = models.IntegerField(default=0, verbose_name='Скорость обслуживания: работы были выполнены в оговоренное время')
    v4          = models.IntegerField(default=0, verbose_name='Оцените вежливость и внимательность персонала')
    v5          = models.IntegerField(default=0, verbose_name='Доступно ли разъяснили Вам перечень и стоимость работ')
    v6          = models.IntegerField(default=0, verbose_name='Качество оказанной услуги/работ')
    v7          = models.CharField('Откуда вы узнали о нашем сервисном центре', default='', null=True, max_length=250, blank=False)
    v8          = models.CharField('Если у вас есть пожелания/замечания вы можете поделиться с нами', default='', null=True, max_length=2500, blank=False)
    close       = models.BooleanField("Закрыт", default=False)
    canceled            = models.BooleanField("Отменен", default=False)
    canceled_type       = models.ForeignKey(RefTypeCanceledSMS, on_delete=models.SET_NULL, null=True, verbose_name="Причина отмены", blank=True)
    canceled_user       = models.ForeignKey(settings. AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,verbose_name="Ответственный", blank=True)
    canceled_comment    = models.CharField('Комментарий', default='', null=True, max_length=512, blank=True)
    category_negative   = models.ForeignKey(RefTypeCategoryNegative, on_delete=models.SET_NULL, null=True, verbose_name="Категория негатива", blank=True)
    category_customer   = models.ForeignKey(RefTypeCategoryCustomer, on_delete=models.SET_NULL, null=True, verbose_name="Категория клиента", blank=True)
    number_base         = models.CharField('Номер в 1С', default='', null=True, max_length=64, blank=False)
    date_base           = models.DateTimeField('Дата в 1С', null=True, blank=True)
    conclusions         = models.CharField('Выводы', default='', null=True, max_length=1024, blank=True)
    comment_tech_dir    = models.CharField('Комментарий технического директора', default='', null=True, max_length=1024, blank=True)
    info                = models.CharField('Инфо', default='', null=True, max_length=10024, blank=True)
    cookie_key          = models.CharField('Куки key', default='', null=True, max_length=128, blank=True)
    ip_key              = models.CharField('ИП key', default='', null=True, max_length=128, blank=True)
    negative            = models.CharField('Негатив key', default='', null=True, max_length=128, blank=True)

    def get_rating(self):
        rating_sum_common      = self.v1 + self.v2 + self.v3 + self.v4 + self.v5 + self.v6
        rating_common          = round(rating_sum_common / 6, 2)
            
        return rating_common

    def __str__(self):
        return "{}".format(self.zn)

    class Meta:
        indexes = [
            models.Index(fields=['uin']),
            models.Index(fields=['zn'])
        ]
        db_table = 'docOprosZN'
        verbose_name = "Опрос по заказ - наряду"
        verbose_name_plural = "Опросы по заказ - нарядам"


class DocOprosCarShipment(models.Model):
    uin         = models.CharField('uin', default='', null=True, max_length=64, blank=False)
    shipment    = models.ForeignKey(DocCarShipment, on_delete=models.SET_NULL, null=True, verbose_name="Отгрузка АМ")
    dataTime    = models.DateTimeField('Дата', default=datetime.now, blank=False) 
    dataClose   = models.DateTimeField('Дата прохождения опроса',null=True, blank=True)
    v1          = models.IntegerField(default=0, verbose_name='Насколько в целом Вы удовлетворены работой менеджера отдела продаж дилерского центра')
    v2          = models.IntegerField(default=0, verbose_name='С какой вероятностью Вы порекомендовали бы нас своим друзьям или знакомым')
    v3          = models.IntegerField(default=0, verbose_name='Насколько Вы остались довольны процессом покупки автомобиля')
    v4          = models.IntegerField(default=0, verbose_name='Насколько вы удовлетворены процессом выдачи автомобиля')
    v5          = models.IntegerField(default=0, verbose_name='Вы воспользовались услугой трейд ин (принятия старого автомобиля в зачет при покупке нового)? Если Да Насколько Вы остались довольны услугой трейд ин?')
    v6          = models.IntegerField(default=0, verbose_name='-')
    v7          = models.CharField('Где вы подбирали автомобиль перед покупкой?', default='', null=True, max_length=250, blank=False)
    v8          = models.CharField('Если у вас есть пожелания/замечания вы можете поделиться с нами', default='', null=True, max_length=2500, blank=False)
    close       = models.BooleanField("Закрыт", default=False)
    canceled            = models.BooleanField("Отменен", default=False)
    canceled_type       = models.ForeignKey(RefTypeCanceledSMS, on_delete=models.SET_NULL, null=True, verbose_name="Причина отмены", blank=True)
    canceled_user       = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,verbose_name="Ответственный" , blank=True)
    canceled_comment    = models.CharField('Комментарий', default='', null=True, max_length=512, blank=True)
    category_negative   = models.ForeignKey(RefTypeCategoryNegative, on_delete=models.SET_NULL, null=True, verbose_name="Категория негатива", blank=True)
    category_customer   = models.ForeignKey(RefTypeCategoryCustomer, on_delete=models.SET_NULL, null=True, verbose_name="Категория клиента", blank=True)
    number_base         = models.CharField('Номер в 1С', default='', null=True, max_length=64, blank=False)
    date_base           = models.DateTimeField('Дата в 1С', null=True, blank=True)
    conclusions         = models.CharField('Выводы', default='', null=True, max_length=1024, blank=True)
    comment_tech_dir    = models.CharField('Комментарий технического директора', default='', null=True, max_length=1024, blank=True)

    def get_rating(self):
        rating_sum_common      = self.v1 + self.v2 + self.v3 + self.v4
        rating_common          = round(rating_sum_common / 4, 2)
            
        return rating_common

    def get_rating_staff(self):
        query_rating_common_count = DocOprosCarShipment.objects.filter(close = True).filter(canceled = False).filter(shipment__staff = self.shipment.staff).count()
        if query_rating_common_count > 0:
            rating_qyeryset_common = DocOprosCarShipment.objects.filter(close = True).filter(canceled = False).filter(shipment__staff = self.shipment.staff).aggregate(Sum('v1'), Sum('v2'), Sum('v3'), Sum('v4'))
            rating_sum_common      = rating_qyeryset_common['v1__sum'] + rating_qyeryset_common['v2__sum'] + rating_qyeryset_common['v3__sum'] + rating_qyeryset_common['v4__sum']     
            rating_common          = round(rating_sum_common / query_rating_common_count / 4, 2)
            return rating_common
        return 0 
    
    def get_rating_staff_30(self):
        curent_date_mounth        = datetime.today() - timedelta(days=30)
        query_rating_common_count = DocOprosCarShipment.objects.filter(dataTime__gte = curent_date_mounth).filter(close = True).filter(canceled = False).filter(shipment__staff = self.shipment.staff).count()
        if query_rating_common_count > 0:
            rating_qyeryset_common = DocOprosCarShipment.objects.filter(close = True).filter(dataTime__gte = curent_date_mounth).filter(canceled = False).filter(shipment__staff = self.shipment.staff).aggregate(Sum('v1'), Sum('v2'), Sum('v3'), Sum('v4'))
            rating_sum_common      = rating_qyeryset_common['v1__sum'] + rating_qyeryset_common['v2__sum'] + rating_qyeryset_common['v3__sum'] + rating_qyeryset_common['v4__sum']   
            rating_common          = round(rating_sum_common / query_rating_common_count / 4, 2)
            return rating_common
        return 0 
    
    def __str__(self):
        return "{}".format(self.shipment)

    class Meta:
        indexes = [
            models.Index(fields=['uin']),
            models.Index(fields=['shipment'])
        ]
        db_table = 'docOprosCarShipment'
        verbose_name = "Опрос по продаже автомобиля"
        verbose_name_plural = "Опросы по продажам автомобилей"


class DoсRecomendationMCU(models.Model):
    zn                      = models.ForeignKey(DocZN, on_delete=models.SET_NULL, null=True, verbose_name="Заказ наряд")
    dataTime                = models.DateTimeField('Дата', default=datetime.now, blank=True)    
    name                    = models.CharField("Наименование", default='', null=True, max_length=250, blank=False)
    dataTimeCutomerEvent    = models.DateTimeField('Дата', null=True, blank=True)   
    customerStatus          = models.IntegerField('Статус согласования клиента', default=0) # 0 - неактивна - 1 на согласовании - 2 - согласована - 3 отклонена
    status                  = models.IntegerField('Статус рекомендации', default=0)         # 0 - новая - 1 обрабатывается - 2 добавлен в ЗН - 3 добавлено в рекомендации - 4 отменено
    
    def unit(self):
        return self.zn.unit.name
    unit.short_description = 'Подразделение ДЦ'
    unit.allow_tags = True

    def recomendation_mcu_files(self):
        return DocRecomendationFilesMCU.objects.filter(recomendation = self) 
    
    def recomendation_files_mcu_count(self):
        return DocRecomendationFilesMCU.objects.filter(recomendation = self).count() 

    def __str__(self):
        return "{} {} - {}".format(self.dataTime, self.name, self.zn)

    class Meta:
        indexes = [
            models.Index(fields=['zn'])
        ]
        db_table = 'doсRecomendationMCU'
        verbose_name = "Рекомендация расширения зн МКУ"
        verbose_name_plural = "Рекомендации расширений зн МКУ"


class DocRecomendationFilesMCU(models.Model):
    recomendation   = models.ForeignKey(DoсRecomendationMCU, on_delete=models.SET_NULL, null=True, verbose_name="Рекомендация")
    file            = models.ImageField(upload_to='recomendations/%Y/%m/%d/', max_length=100, verbose_name="Файл", blank=True, null=True)
    
    def is_video(self):
        list_world_name = self.file.name.lower().split('.')
        format = list_world_name[-1]
        if format.find('jpg') > -1 or format.find('jpeg') > -1 or format.find('svg') > -1 or format.find('gif') > -1 or format.find('png') > -1 or format.find('tiff') > -1:
            return False
        return True

    def __str__(self):
        return "{}".format(self.recomendation)

    class Meta:
        indexes = [
            models.Index(fields=['recomendation'])
        ]
        db_table = 'docRecomendationFilesMCU'
        verbose_name = "Файл рекомендации МКУ"
        verbose_name_plural = "Файлы рекомендаций МКУ"


class SurveysOP(models.Model):
    dateTime                    = models.DateTimeField('Дата', default=datetime.now, blank=False)    
    uin                         = models.CharField('uin', default='', null=True, max_length=100, blank=False)
    nomer                       = models.CharField('Номер', default='', null=True, max_length=25, blank=False)
    unit                        = models.ForeignKey(RefUnit, null=True, on_delete=models.SET_NULL, verbose_name="Подразделение") 
    staff                       = models.ForeignKey(RefStaff, null=True, on_delete=models.SET_NULL, verbose_name="Менеджер") 
    rlk                         = models.ForeignKey(DocRLK, null=True, on_delete=models.SET_NULL, verbose_name="Рабочий лист") 
    result                      = models.IntegerField("Результат", default=0, blank=True)
    сonclusions                 = models.CharField('Выводы', default='', null=True, max_length=25024, blank=False)

    def conclusions_table(self):
        if len(str(self.сonclusions)) > 0:
            try:
                return json.loads(str(self.сonclusions))
            except:
                return None
        else:
            return None

    def tematics(self):
        return SurveysOP_tematics.objects.filter(surveys = self)
    def tematics_count(self):
        return SurveysOP_tematics.objects.filter(surveys = self).count()

    def questions_success(self):
        return SurveysOP_questions.objects.filter(surveys = self).filter(answer__gt = 0)
    def questions_success_count(self):
        return SurveysOP_questions.objects.filter(surveys = self).filter(answer__gt = 0).count()

    def questions_fail(self):
        return SurveysOP_questions.objects.filter(surveys = self).filter(answer = 0)
    def questions_fail_count(self):
        return SurveysOP_questions.objects.filter(surveys = self).filter(answer = 0).count()
    
    def __str__(self):
        return "{} / {}({})".format(self.dateTime, self.nomer, self.rlk)

    class Meta:
        db_table = 'surveysOP'
        verbose_name = "Опрос отдела продаж"
        verbose_name_plural = "Опросы отдела продаж"


class SurveysOP_tematics(models.Model):
    surveys             = models.ForeignKey(SurveysOP, null=True, on_delete=models.SET_NULL, verbose_name="Опрос") 
    name                = models.CharField('Тематика', default='', null=True, max_length=150, blank=False)
    entry_id            = models.CharField('entry_id', default='', null=True, max_length=20, blank=False, db_index=True)
    record              = models.CharField('record',    default='', null=True, max_length=512, blank=False, db_index=True)
    
    def __str__(self):
        return "{} / {}".format(self.surveys, self.name)

    class Meta:
        db_table = 'surveysOP_tematics'
        verbose_name = "Опрос отдела продаж тематики"
        verbose_name_plural = "Опросы отдела продаж тематики"


class SurveysOP_questions(models.Model):
    surveys             = models.ForeignKey(SurveysOP, null=True, on_delete=models.SET_NULL, verbose_name="Опрос") 
    name                = models.CharField('Вопрос', default='', null=True, max_length=150, blank=False)
    answer              = models.IntegerField("Значение", default=0, blank=True)
    canceled            = models.BooleanField("Отменен", default=False)
    
    def __str__(self):
        return "{} / {}".format(self.surveys, self.name)

    class Meta:
        db_table = 'surveysOP_questions'
        verbose_name = "Опрос отдела продаж вопрос"
        verbose_name_plural = "Опросы отдела продаж вопросы"


class ResourcePlanning(models.Model):
    uin             = models.CharField('uin', default='', null=True, max_length=64, blank=False)
    active          = models.BooleanField("Активна", default=False)
    dateStart       = models.DateTimeField('Начало', null=True, blank=True)
    dateEnd         = models.DateTimeField('Конец', null=True, blank=True)
    serviceRequest  = models.ForeignKey(DocServiceRequest, on_delete=models.SET_NULL, null=True, verbose_name="Заявка на ремонт")
    staff           = models.ForeignKey(RefStaff, on_delete=models.SET_NULL, null=True, verbose_name="Мастер-консультант")
    type            = models.ForeignKey(RefTypeResourcePlanning, on_delete=models.SET_NULL, null=True, verbose_name="Тип")

    def cars_grz_board(self):
        grz = str(self.serviceRequest.carsGRZ).upper().replace(" ", "")
        return grz[0:1] + ' ' + grz[1:4] + ' ' + grz[4:6] + '   ' + grz[6:10]
   
    def __str__(self):
        return "{} ({} - {}) - {}".format(self.staff, self.uin, self.dateStart, self.dateEnd)

   
    class Meta:
        indexes = [
            models.Index(fields=['uin'])
        ]
        db_table = 'resourcePlanning'
        verbose_name = "Планирование ресурса"
        verbose_name_plural = "Планирование ресурсов"


class DocSMS(models.Model):
    uin             = models.CharField('uin', default='', null=True, max_length=64, blank=False)
    active          = models.BooleanField("Проведен", default=False)
    nomer           = models.CharField('Номер', default='', null=True, max_length=25, blank=False)
    dateTime        = models.DateTimeField('Дата', default=datetime.now, blank=False)
    dateSend        = models.DateTimeField('Дата отправки', null=True, blank=True)
    organization    = models.ForeignKey(RefOrganization, on_delete=models.SET_NULL, null=True, verbose_name="Организация")
    unit            = models.ForeignKey(RefUnit, on_delete=models.SET_NULL, null=True, verbose_name="Подразделение")
    staff           = models.ForeignKey(RefStaff, related_name="sms_staff", on_delete=models.SET_NULL, null=True, verbose_name="Автор")
    customer        = models.ForeignKey(RefCustomer, on_delete=models.SET_NULL, null=True, verbose_name="Клиент")
    clientName      = models.CharField('Клиент строкой', default='', null=True, max_length=250, blank=False)
    modelName       = models.CharField('Имя модели', default='', null=True, max_length=250, blank=False)
    modelId         = models.CharField('ИД объекта модели', default='', null=True, max_length=250, blank=False)
    thema           = models.CharField('Тема', default='', null=True, max_length=250, blank=False)
    message         = models.CharField('Сообщение', default='', null=True, max_length=2500, blank=False)
    statusBase      = models.ForeignKey(RefSMSStatusBase, on_delete=models.SET_NULL, null=True, verbose_name="Статус СМС сообщения 1С")
    statusProvider  = models.ForeignKey(RefSMSStatusProvider, on_delete=models.SET_NULL, null=True, verbose_name="Статус СМС сообщения провайдера")
    error           = models.CharField('Ошибка', default='', null=True, max_length=250, blank=False)
    errorProvider   = models.CharField('Ошибка провайдер', default='', null=True, max_length=250, blank=False)
    phone           = models.CharField('Телефон', default='', null=True, max_length=250, blank=False)
    phoneNorm       = models.CharField('Телефон нормализованный', default='', null=True, max_length=250, blank=False)
    messageId       = models.CharField('Идентификатор сообщения', default='', null=True, max_length=250, blank=False)
    model_pk        = models.IntegerField("ИД данных", default=0, blank=True)
    
    def __str__(self):
        return "{} ({} - {})".format(self.dateTime, self.clientName, self.nomer)


    
    def save(self, *args, **kwargs):
        
        try:
            self.model_pk = int(self.modelId)
        except:
            s = 1
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['uin']),
            models.Index(fields=['modelName']),
            models.Index(fields=['model_pk']),
        ]
        db_table = 'docSMS'
        verbose_name = "Сообщение смс"
        verbose_name_plural = "Сообщения смс"


class DocZNKA(models.Model):
    uin            = models.CharField('uin', default='', null=True, max_length=64, blank=False)
    closed         = models.BooleanField("Закрыт",  default=False)
    active         = models.BooleanField("Проведен", default=False)
    nomer          = models.CharField('Номер', default='', null=True, max_length=25, blank=False)
    dataTime       = models.DateTimeField('Дата', default=datetime.now, blank=False)
    nomer_dc       = models.CharField('Номер в дц', default='', null=True, max_length=25, blank=False)
    dataTime_dc    = models.DateTimeField('Дата в дц', default=datetime.now, blank=False)
    dateStart      = models.DateTimeField('Пришла в ремонт', null=True, blank=True)
    dateEnd        = models.DateTimeField('Вышла из ремонта', null=True, blank=True)
    organization   = models.ForeignKey(RefOrganization, on_delete=models.SET_NULL, null=True, verbose_name="Организация")
    unit           = models.ForeignKey(RefUnit, on_delete=models.SET_NULL, null=True, verbose_name="Подразделение")
    master         = models.ForeignKey(RefStaff, related_name="mastein_ka", on_delete=models.SET_NULL, null=True, verbose_name="Мастер-консультант")
    masterOut      = models.ForeignKey(RefStaff, related_name="masterout_ka", on_delete=models.SET_NULL, null=True, verbose_name="Выпускающий мастер-консультант")
    carsGRZ        = models.CharField('Гос. номер', default='', null=True, max_length=25, blank=True)
    customer       = models.ForeignKey(RefCustomer, on_delete=models.SET_NULL, null=True, verbose_name="Клиент")
    clientName     = models.CharField('Клиент строкой', default='', null=True, max_length=250, blank=False)
    cars           = models.ForeignKey(RefCars, on_delete=models.SET_NULL, null=True, verbose_name="Автомобиль") 
    lo             = models.ForeignKey(DocLO, on_delete=models.SET_NULL, null=True, verbose_name="Лист оценки")
    typeRemont     = models.ForeignKey(RefTypeRepair, on_delete=models.SET_NULL, null=True, verbose_name="Вид ремонта")
    readyStatus    = models.ForeignKey(RefStatusDocZN, on_delete=models.SET_NULL, null=True, verbose_name="Статус") 
    customerWords  = models.CharField('Заявка со слов клиента', default='', null=True, max_length=12500, blank=True) 
    run            = models.IntegerField("Пробег", default=0, blank=True)
    amount         = models.FloatField("Сумма", default=0.0, blank=True)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['uin'])
        ]
        db_table = 'docZNKA'
        verbose_name = "Заказ - наряд КорсАвто"
        verbose_name_plural = "Заказ - наряды КорсАвто"


class DocZNWorkKA(models.Model):
    zn                  = models.ForeignKey(DocZNKA, on_delete=models.SET_NULL, null=True, verbose_name="Заказ наряд")
    uin                 = models.CharField('Уникальный идентификатор', default='', null=True, max_length=100, blank=False) 
    type                = models.ForeignKey(RefTypeItemRepair, on_delete=models.SET_NULL, null=True, verbose_name="Тип в заказ наряде")
    work                = models.ForeignKey(RefWork, on_delete=models.SET_NULL, null=True, verbose_name="Работа")
    quantity            = models.FloatField("Количество", default=0.0, blank=True)
    price               = models.FloatField("Цена", default=0.0, blank=True)
    
    discountPercentage  = models.FloatField("Процент скидки", default=0.0, blank=True)
    discountAmount      = models.FloatField("Сумма скидки", default=0.0, blank=True)
    
    amount              = models.FloatField("Сумма", default=0.0, blank=True)
    amountResult        = models.FloatField("Сумма с учетом скидки", default=0.0, blank=True)
    
    def get_type(self):
        if self.type == None:
            return '-'
        return self.type

    def save(self, *args, **kwargs):
        try:
            if self.discountPercentage > 0:
                self.discountAmount     = self.price * self.quantity * self.discountPercentage / 100
                self.amountResult       = self.price * self.quantity - self.discountAmount
            else:
                self.discountAmount = 0
                self.amountResult   = self.price * self.quantity - self.discountAmount
        except:
            self.discountAmount = 0
            self.amountResult   = self.price * self.quantity

        super().save(*args, **kwargs)

    def __str__(self):
        return "{} / {}".format(self.zn, self.work)

    class Meta:
        indexes = [
            models.Index(fields=['zn'])
        ]
        db_table = 'docZNWorkKA'
        verbose_name = "Работа заказ наряда КорсАвто"
        verbose_name_plural = "Работы заказ наряда КорсАвто"


class DocZNProductKA(models.Model):
    zn                  = models.ForeignKey(DocZNKA, on_delete=models.SET_NULL, null=True, verbose_name="Заказ наряд")
    uin                 = models.CharField('Уникальный идентификатор', default='', null=True, max_length=100, blank=False) 
    type                = models.ForeignKey(RefTypeItemRepair, on_delete=models.SET_NULL, null=True, verbose_name="Тип в заказ наряде")
    product             = models.ForeignKey(RefProduct, on_delete=models.SET_NULL, null=True, verbose_name="Товар")
    quantity            = models.FloatField("Количество", default=0.0, blank=True)
    price               = models.FloatField("Цена", default=0.0, blank=True)
    
    discountPercentage  = models.FloatField("Процент скидки", default=0.0, blank=True)
    discountAmount      = models.FloatField("Сумма скидки", default=0.0, blank=True)
    
    amount              = models.FloatField("Сумма", default=0.0, blank=True)
    amountResult       = models.FloatField("Сумма с учетом скидки", default=0.0, blank=True)

    def get_type(self):
        if self.type == None:
            return '-'
        return self.type

    def save(self, *args, **kwargs):
        try:
            if self.discountPercentage > 0:
                self.discountAmount = self.price * self.quantity * self.discountPercentage / 100
                self.amountResult = self.price * self.quantity - self.discountAmount
            else:
                self.discountAmount = 0
                self.amountResult = self.price * self.quantity
        except:
            self.discountAmount = 0
            self.amountResult   = self.price * self.quantity

        super().save(*args, **kwargs)

    def __str__(self):
        return "{} / {}".format(self.zn, self.product)

    class Meta:
        indexes = [
            models.Index(fields=['zn'])
        ]
        db_table = 'docZNProductKA'
        verbose_name = "Товар заказ наряда КорсАвто"
        verbose_name_plural = "Товары заказ наряда КорсАвто"


class DocZNServicesKA(models.Model):
    zn                  = models.ForeignKey(DocZNKA, on_delete=models.SET_NULL, null=True, verbose_name="Заказ наряд")
    uin                 = models.CharField('Уникальный идентификатор', default='', null=True, max_length=100, blank=False) 
    type                = models.ForeignKey(RefTypeItemRepair, on_delete=models.SET_NULL, null=True, verbose_name="Тип в заказ наряде")
    service             = models.ForeignKey(RefService, on_delete=models.SET_NULL, null=True, verbose_name="Услуга")
    quantity            = models.FloatField("Количество", default=0.0, blank=True)
    price               = models.FloatField("Цена", default=0.0, blank=True)
    
    discountPercentage  = models.FloatField("Процент скидки", default=0.0, blank=True)
    discountAmount      = models.FloatField("Сумма скидки", default=0.0, blank=True)
    
    amount              = models.FloatField("Сумма", default=0.0, blank=True)
    amountResult       = models.FloatField("Сумма с учетом скидки", default=0.0, blank=True)

    def get_type(self):
        if self.type == None:
            return '-'
        return self.type

    
    def __str__(self):
        return "{} / {}".format(self.zn, self.service)

    class Meta:
        indexes = [
            models.Index(fields=['zn'])
        ]
        db_table = 'docZNServicesKA'
        verbose_name = "Товар заказ наряда КорсАвто"
        verbose_name_plural = "Товары заказ наряда КорсАвто"


class DocZNPerformersKA(models.Model):
    zn                  = models.ForeignKey(DocZNKA, on_delete=models.SET_NULL, null=True, verbose_name="Заказ наряд")
    uin                 = models.CharField('Уникальный идентификатор', default='', null=True, max_length=100, blank=False) 
    staff               = models.ForeignKey(RefStaff, on_delete=models.SET_NULL, null=True, verbose_name="Сотрудник")
    percent             = models.FloatField("Сумма с учетом скидки", default=0.0, blank=True)

    def __str__(self):
        return "{} / {}".format(self.zn, self.staff)

    class Meta:
        indexes = [
            models.Index(fields=['zn'])
        ]
        db_table = 'docZNPerformersKA'
        verbose_name = "Исполнители заказ наряда КорсАвто"
        verbose_name_plural = "Исполнители заказ наряда КорсАвто"


class DocServices(models.Model):
    uin             = models.CharField('uin', default='', null=True, max_length=64, blank=False)
    active          = models.BooleanField("Проведен", default=False)
    nomer           = models.CharField('Номер', default='', null=True, max_length=25, blank=False)
    date_time       = models.DateTimeField('Дата', default=datetime.now, blank=False)
    nomer_dc        = models.CharField('Номер стороней базы', default='', null=True, max_length=25, blank=False)
    date_time_dc    = models.DateTimeField('Дата стороней базы', default=datetime.now, blank=False)
    organization    = models.ForeignKey(RefOrganization, on_delete=models.SET_NULL, null=True, verbose_name="Организация")
    unit            = models.ForeignKey(RefUnit, on_delete=models.SET_NULL, null=True, verbose_name="Подразделение")
    author          = models.ForeignKey(RefStaff, related_name="author", on_delete=models.SET_NULL, null=True, verbose_name="Автор")
    customer        = models.ForeignKey(RefCustomer, on_delete=models.SET_NULL, null=True, verbose_name="Клиент")
    lo              = models.ForeignKey(DocLO, on_delete=models.SET_NULL, null=True, verbose_name="Лист оценки")
    type_cost       = models.ForeignKey(RefTypeDocService, on_delete=models.SET_NULL, null=True, verbose_name="Вид поступления")
    amount          = models.FloatField("Сумма", default=0.0, blank=True)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['uin']),
            models.Index(fields=['lo'])
        ]
        db_table = 'docServices'
        verbose_name = "Поступление услуг КорсАвто"
        verbose_name_plural = "Поступления услугы КорсАвто"


class DocServiceItem(models.Model):
    doc_service         = models.ForeignKey(DocServices, on_delete=models.SET_NULL, null=True, verbose_name="Постпление услуг")
    type_service        = models.ForeignKey(RefTypeItemServiceRepair, on_delete=models.SET_NULL, null=True, verbose_name="Тип затраты")
    description         = models.CharField('Описание', default='', null=True, max_length=12500, blank=True)
    service             = models.ForeignKey(RefService, on_delete=models.SET_NULL, null=True, verbose_name="Услуга")
    quantity            = models.FloatField("Количество", default=0.0, blank=True)
    price               = models.FloatField("Цена", default=0.0, blank=True)
    amount              = models.FloatField("Сумма", default=0.0, blank=True)
    
    def __str__(self):
        return "{} / {}".format(self.doc_service, self.service)

    class Meta:
        indexes = [
            models.Index(fields=['doc_service'])
        ]
        db_table = 'docServiceItem'
        verbose_name = "Услуги поступления услуг КорсАвто"
        verbose_name_plural = "Услуги поступления услуг КорсАвто"
