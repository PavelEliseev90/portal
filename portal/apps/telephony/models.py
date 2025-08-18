from django.db import models
from datetime import datetime
from django.dispatch import receiver
from django.db.models.signals import post_save
import datetime as DT
from documents.models import DocRLK 


class MangoGroup(models.Model):
    name                = models.CharField('Наименование', default='', null=True, max_length=250, blank=False)
    mango_id            = models.IntegerField('ИД Манго', default=0, blank=True)
    direction_op        = models.BooleanField("Отдел продаж", default=False)
    direction_service   = models.BooleanField("Отдел сервиса", default=False)
    def __str__(self):
        return "{} ({}) - op {} - service {}".format(self.name, self.mango_id, self.direction_op, self.direction_service)

    class Meta:
        db_table = 'mangoGroup'
        verbose_name = "Манго группа"
        verbose_name_plural = "Манго группы"


class MangoNumberSip(models.Model):
    name                = models.CharField('Наименование', default='', null=True, max_length=250, blank=False)
    mango_id            = models.IntegerField('ИД Манго', default=0, blank=True)
    sip                 = models.CharField('SIP', default='', null=True, max_length=250, blank=False)
    description         = models.CharField('Описание', default='', null=True, max_length=250, blank=False)
    
    def __str__(self):
        return "{} / {}".format(self.name, self.description)

    class Meta:
        db_table = 'mangoNumberSip'
        verbose_name = "Манго номер"
        verbose_name_plural = "Манго номера"


class MangoNumberSipGroup(models.Model):
    group               = models.ForeignKey(MangoGroup, on_delete=models.SET_NULL, null=True, verbose_name="Манго группа")
    number              = models.ForeignKey(MangoNumberSip, on_delete=models.SET_NULL, null=True, verbose_name="Манго номер")
    
    def __str__(self):
        return "{} / {}".format(self.number, self.group)

    class Meta:
        db_table = 'mangoNumberSipGroup'
        verbose_name = "Манго номер группа"
        verbose_name_plural = "Манго номер группы"


class MangoHystoryCalls(models.Model):
    
    class DirectionCall(models.TextChoices):
        INBOUND     = 'INBOUND', 'Входящий'
        OUTBOUND    = 'OUTBOUND', 'Исходящий'
        INTERNAL    = 'INTERNAL', 'Внутренний'

    entry_id                = models.CharField('entry_id', default='', null=True, max_length=20, blank=False, db_index=True)
    from_number             = models.CharField('from_number', default='', null=True, max_length=100, blank=False, db_index=True)
    to_number               = models.CharField('to_number', default='', null=True, max_length=100, blank=False, db_index=True)
    start                   = models.DateTimeField('start', default=datetime.now, blank=False, db_index=True)
    finish                  = models.DateTimeField('finish', default=datetime.now, blank=False, db_index=True)
    time                    = models.IntegerField('time', default=0, blank=True)
    records                 = models.CharField('records', default='', null=True, max_length=1024, blank=False)
    answer                  = models.BooleanField("answer", default=False)
    duration                = models.CharField('duration', default='', null=True, max_length=25, blank=False)
    direction               = models.CharField(max_length=10, choices=DirectionCall.choices, default=DirectionCall.INBOUND)
    sip_from                = models.ForeignKey(MangoNumberSip, related_name="sip_from", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Манго номер c") 
    sip_to                  = models.ForeignKey(MangoNumberSip, related_name="sip_to", on_delete=models.SET_NULL, null=True,  blank=True, verbose_name="Манго номер на") 

    def __str__(self):
        return "{} / {} --> {} ({})".format(self.entry_id, self.from_number, self.to_number, self.duration)
    
    def save(self, *args, **kwargs):
        try:
            if len(self.records) > 0:
                records_str  = str(self.records)
                records      = records_str.replace('[', '').replace(']', '').split(',')
                for record in records:
                    if len(record) > 3:
                        count_record = MangoHystoryCallsRecords.objects.filter(record = record).filter(entry_id = self.entry_id).count()
                        if count_record == 0:
                            hystory_records                  = MangoHystoryCallsRecords()
                            hystory_records.entry_id         = self.entry_id
                            hystory_records.record           = record
                            hystory_records.save() 
        except:
            s = 13
        try:
            if self.answer == False:
                count_record_answer = MangoHystoryCalls.objects.filter(entry_id = self.entry_id).filter(answer = True).count()
                if count_record_answer > 0:
                    self.answer = True
            if self.answer == True:
                count_record_answer = MangoHystoryCalls.objects.filter(entry_id = self.entry_id).filter(answer = False).exclude(id = self.id).count()
                if count_record_answer > 0:
                    hystorys  = MangoHystoryCalls.objects.filter(entry_id = self.entry_id).filter(answer = False) 
                    for hystory in hystorys:
                        hystory.answer = True
                        hystory.save()    
        except:
            s = 1
        
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'mangoHystoryCalls'
        verbose_name = "Манго история звонка"
        verbose_name_plural = "Манго история звонков"


class MangoHystoryCallsRecords(models.Model):

    entry_id                = models.CharField('entry_id',  default='', null=True, max_length=20, blank=False, db_index=True)
    record                  = models.CharField('record',    default='', null=True, max_length=512, blank=False, db_index=True)
    image                   = models.ImageField(upload_to='records_hystory_calls_img/%Y/%m/%d/', max_length=100, verbose_name="Картинка", blank=True, null=True)

    def __str__(self):
        return "{} / {}".format(self.entry_id, self.record)

    class Meta:
        db_table = 'mangoHystoryCallsRecords'
        verbose_name = "Манго история звонка записи"
        verbose_name_plural = "Манго история записи"


###
##
#
class Telephony_Recognition_Dictonary(models.Model):
    date        = models.DateTimeField("Дата", default=DT.datetime.now, blank=False)
    name_s      = models.CharField("Слово или фраза с", max_length=512)
    name_n      = models.CharField("Слово или фраза на", max_length=512)
    added       = models.BooleanField("Добавлено в словарь", default=False)

    def __str__(self):
        return self.name_s

    class Meta:
        db_table            = 'telephony_recognition_Dictonary'
        verbose_name        = "Слово"
        verbose_name_plural = "Слова"


class Telephony_Recognition_Dictonary_Model(models.Model):
    date        = models.DateTimeField("Дата", default=DT.datetime.now, blank=False)
    name        = models.CharField("Слово или фраза", max_length=512)
    added       = models.BooleanField("Добавлено в словарь", default=False)

    def __str__(self):
        return self.name

    class Meta:
        db_table            = 'telephony_recognition_Dictonary_model'
        verbose_name        = "Слово"
        verbose_name_plural = "Слова"


class Telephony_Recognition_Tematika(models.Model):
    name        = models.CharField("Наименование", max_length=200)
    direction   = models.IntegerField("Направление", default=0) 
    rating      = models.IntegerField("Значимость", default=0)
    field       = models.CharField("Пункт чек листа", max_length=200)
    enabled     = models.BooleanField("Включена", default=False, null=True) 

    def worlds_count(self):
        return Telephony_Recognition_Tematika_fraza.objects.filter(tematika = self.pk).count()

    def __str__(self):
        return self.name

    class Meta:
        db_table            = 'telephony_recognition_Tematika'
        verbose_name        = "Тематика звонка"
        verbose_name_plural = "Тематики звонков"


class Telephony_Recognition_Tematika_fraza(models.Model):
    name        = models.CharField("Фраза", max_length=200)
    tematika    = models.ForeignKey(Telephony_Recognition_Tematika, null=True, on_delete=models.SET_NULL, verbose_name='Тематика') 
    type_search = models.CharField("Тип поиска", max_length=200)
    works       = models.CharField("Срабатывает когда найдено", max_length=200)
    doorstep    = models.IntegerField("Порог срабатывания", default=0)

    def __str__(self):
        return self.name

    class Meta:
        db_table            = 'telephony_recognition_Tematika_Fraza'
        verbose_name        = "Слова тематик"
        verbose_name_plural = "Слова тематик"


class Telephony_records_queue(models.Model):
    date                    = models.DateTimeField('Дата', default=DT.datetime.now, null=True, blank=False)
    direction               = models.IntegerField('Направление', default=0, null=True, blank=True) # 1 - ОП Новые автомобили 2 - Сервис прием авто 3 - Сервис выдача автомобиля 
    record                  = models.CharField("Запись", max_length=512)
    data_json               = models.TextField("Данные", default='', null=True, blank=True)
    duration                = models.IntegerField('Продолжительность', default=0, null=True, blank=True)
    rlk                     = models.ForeignKey(DocRLK, on_delete=models.SET_NULL, null=True, verbose_name="Рабочий лист")
    error                   = models.BooleanField("Ошибочен", default=False, null=True)
    img_chanel_1            = models.ImageField(upload_to='calls/%Y/%m/%d/', max_length=100, verbose_name="Первый канал", blank=True, null=True)
    img_chanel_2            = models.ImageField(upload_to='calls/%Y/%m/%d/', max_length=100, verbose_name="Второй канал", blank=True, null=True)


    def duration_human(self):
        sec             = self.duration
        time_seconds    = sec
        if sec > 0:
            sec     = sec % (24 * 3600) 
            hour    = time_seconds // 3600 
            sec     %= 3600 
            min     = sec // 60 
            sec     %= 60 
            if hour > 0:
                return "%02d:%02d:%02d" % (hour, min, sec)
            else:
                return "%02d:%02d:%02d" % (0, min, sec)
        else:
            return "00:00"
        

    def __str__(self):
        return "{} - {}".format(self.date, self.direction) 

    class Meta:
        db_table = 'telephony_records_queue'
        verbose_name = "Очередь распознования звонков"
        verbose_name_plural = "Очередь распознования звонков"
        ordering = ["rlk__dataTime"]


class Telephony_question(models.Model):
    name         = models.CharField("Наименование", max_length=200)
    direction    = models.IntegerField('Направление', default=0, null=True, blank=True) # 1 - ОП Новые автомобили 2 - Сервис прием авто 3 - Сервис выдача автомобиля 
    canceled     = models.BooleanField("Не подлежит оценке", default=False, null=True)
    estimation   = models.IntegerField('Оценка', default=0, null=True, blank=True) 
    tematics     = models.ManyToManyField(Telephony_Recognition_Tematika, verbose_name='Тематики', blank=True)

    def __str__(self):
        return "{} - {} - {}".format(self.name, self.direction, self.direction) 

    class Meta:
        db_table = 'telephony_question'
        verbose_name = "Вопрос для опроса"
        verbose_name_plural = "Вопросы для опроса"



class Telephony_survey(models.Model):
    date                    = models.DateTimeField('Дата', default=DT.datetime.now, null=True, blank=False)
    direction               = models.IntegerField('Направление', default=0, null=True, blank=True) # 1 - ОП Новые автомобили 2 - Сервис прием авто 3 - Сервис выдача автомобиля 
    data_json               = models.TextField("Данные", default='', null=True, blank=True)
    rlk                     = models.ForeignKey(DocRLK, on_delete=models.SET_NULL, null=True, verbose_name="Рабочий лист")
    canceled                = models.BooleanField("Не подлежит оценке", default=False, null=True)
    result                  = models.IntegerField("Результат", default=0, blank=True)

    def __str__(self):
        return "{} - {} - {}".format(self.date, self.direction, self.rlk) 

    class Meta:
        db_table = 'telephony_survey'
        verbose_name = "Опрос по рабочему листу"
        verbose_name_plural = "Опросы по рабочим листам"
        ordering = ["rlk__dataTime"]