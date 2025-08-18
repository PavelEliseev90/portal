from django.db import models
import datetime as DT
from django.conf import settings
from documents.models import DocRLK
from django.db.models import OuterRef, Subquery, Sum

cancel_limit = 20


class Check_settings_cvc(models.Model):
    name        = models.CharField("Наименование", max_length=200)
    id_cvc      = models.IntegerField('id CVC', default=0, null=True, blank=True)
   
    def __str__(self):
        return "{} - {}".format(self.name, self.id_cvc) 

    class Meta:
        db_table = 'check_settings_cvc'
        verbose_name = "Настройка чек листа cvc"
        verbose_name_plural = "Настройки чек листа cvc"

class Check_settings(models.Model):
    name                = models.CharField("Наименование", max_length=200)
    direction           = models.IntegerField('Направление', default=0, null=True, blank=True) # 1 - ОП Новые автомобили 2 - Сервис прием авто 3 - Сервис выдача автомобиля 
    check_settings_cvc  = models.ForeignKey(Check_settings_cvc, null=True, on_delete=models.SET_NULL, verbose_name="Настройки чек листа cvc")

    def questions_count(self):
        return Records_questions.objects.filter(сheck_settings = self).count()
    
    def __str__(self):
        return "{} - {} - {}".format(self.name, self.direction, self.check_settings_cvc) 

    class Meta:
        db_table = 'check_settings'
        verbose_name = "Настройка чек листа"
        verbose_name_plural = "Настройки чек листа"


class Settings_check_records(models.Model):
    name                = models.CharField("Наименование", max_length=200)
    check_settings      = models.ForeignKey(Check_settings, related_name="settings_check_records_сheck_settings", null=True, on_delete=models.SET_NULL, verbose_name="Настройки чек листа")
    direction           = models.IntegerField('Направление', default=0, null=True, blank=True) # 1 - ОП Новые автомобили 2 - Сервис прием авто 3 - Сервис выдача автомобиля 

    def __str__(self):
        return "{} - {} - {}".format(self.name, self.direction, self.direction) 

    class Meta:
        db_table = 'settings_check_records'
        verbose_name = "Настройка чек листа диктофона"
        verbose_name_plural = "Настройка чек листа диктофона"


class Recognition_Anketa_Type(models.Model):
    name        = models.CharField("Наименование", max_length=200)
    
    def __str__(self):
        return self.name

    class Meta:
        db_table            = 'recognition_Anketa_Type'
        verbose_name        = "Тип анкеты"
        verbose_name_plural = "Типы анкет"


class Recognition_Anketa(models.Model):
    name        = models.CharField("Наименование", max_length=200)
    direction   = models.CharField("Направление", max_length=200)
    type        = models.ForeignKey(Recognition_Anketa_Type, null=True, on_delete=models.SET_NULL, verbose_name='Тип анкеты')

    def __str__(self):
        return self.name

    class Meta:
        db_table            = 'recognition_Anketa'
        verbose_name        = "Анкета"
        verbose_name_plural = "Анкеты"


class Recognition_Dictonary(models.Model):
    date        = models.DateTimeField("Дата", default=DT.datetime.now, blank=False)
    name        = models.CharField("Слово или фраза", max_length=512)
    added       = models.BooleanField("Добавлено в словарь", default=False)

    def __str__(self):
        return self.name

    class Meta:
        db_table            = 'recognition_Dictonary'
        verbose_name        = "Слово"
        verbose_name_plural = "Слова"


class Recognition_Tematika(models.Model):
    name        = models.CharField("Наименование", max_length=200)
    anketa      = models.ForeignKey(Recognition_Anketa, null=True, on_delete=models.SET_NULL, verbose_name='Анкета') 
    rating      = models.IntegerField("Значимость", default=0)
    field       = models.CharField("Пункт чек листа", max_length=200)
    enabled     = models.BooleanField("Включена", default=False, null=True) 

    def worlds_count(self):
        return Recognition_Tematika_fraza.objects.filter(tematika = self.pk).count()

    def __str__(self):
        return self.name

    class Meta:
        db_table            = 'recognition_Tematika'
        verbose_name        = "Тематика"
        verbose_name_plural = "Тематики"


class Recognition_Tematika_fraza(models.Model):
    name        = models.CharField("Фраза", max_length=200)
    tematika    = models.ForeignKey(Recognition_Tematika, null=True, on_delete=models.SET_NULL, verbose_name='Тематика') 
    type_search = models.CharField("Тип поиска", max_length=200)
    works       = models.CharField("Срабатывает когда найдено", max_length=200)
    doorstep    = models.IntegerField("Порог срабатывания", default=0)

    def __str__(self):
        return self.name

    class Meta:
        db_table            = 'recognition_Tematika_Fraza'
        verbose_name        = "Слова тематик"
        verbose_name_plural = "Слова тематик"


class Recognition_call(models.Model):
    date            = models.DateTimeField('Дата', default=DT.datetime.now, null=True, blank=False)
    time            = models.IntegerField('Длительность', default=0, null=True, blank=True)
    user            = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, verbose_name="Автор")
    name            = models.CharField("Наименование", default='', max_length=512, null=True, blank=True)
    comment         = models.CharField("Комментарий", default='', max_length=2500, null=True, blank=True) 
    data_json       = models.TextField("Данные", default='', null=True, blank=True)
    recognition     = models.BooleanField("Распознан", default=False, null=True)
    audio           = models.FileField(upload_to='recognition_call/%Y/%m/%d/', verbose_name="Запись", blank=True, null=True)

    def __str__(self):
        return "{} - {} - {}".format(self.date, self.name, self.user) 

    class Meta:
        db_table = 'recognition_call'
        verbose_name = "Распознанный звонок"
        verbose_name_plural = "Распознанные звонки"


class Records_voice_recorder(models.Model):
    date                = models.DateTimeField('Дата', default=DT.datetime.now, null=True, blank=False)
    time                = models.IntegerField('Длительность', default=0, null=True, blank=True)
    user                = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, verbose_name="Автор")
    name                = models.CharField("Наименование", default='', max_length=512, null=True, blank=True)
    comment             = models.CharField("Комментарий", default='', max_length=2500)
    data_json           = models.TextField("Данные", default='', null=True, blank=True)
    dateRecognitions    = models.DateTimeField('Дата распознования /', default=DT.datetime.now, null=True, blank=False)
    recognition         = models.BooleanField("Распознан", default=False, null=True)
    audio               = models.FileField(upload_to='records_voice_recorder/%Y/%m/%d/', verbose_name="Запись", blank=True, null=True)
    image               = models.ImageField(upload_to='records_voice_recorder_img/%Y/%m/%d/', max_length=100, verbose_name="Картинка", blank=True, null=True)
    date_create         = models.DateTimeField('Дата загрузки', default=DT.datetime.now, null=True, blank=False)
    version_programm    = models.IntegerField('Версия программы загрузки', default=0, null=True, blank=True)
    error               = models.BooleanField("Ошибочен", default=False, null=True)

    def date_end(self):
        sec = self.time
        if sec > 0:
            return self.date + DT.timedelta(seconds=sec)
        return self.date
    
    def time_human(self):
        sec = self.time
        if sec > 0:
            sec     = sec % (24 * 3600) 
            hour    = sec // 3600 
            sec     %= 3600 
            min     = sec // 60 
            sec     %= 60 
            if hour > 0:
                return "%02d:%02d:%02d" % (hour, min, sec)
            else:
                return "%02d:%02d" % (min, sec)
        else:
            return "00:00"

    def __str__(self):
        return "{} - {} - {}".format(self.date, self.name, self.user) 

    class Meta:
        db_table = 'records_voice_recorder'
        verbose_name = "Запись диктофона"
        verbose_name_plural = "Записи диктофона"


class Records_voice_recorder_queue(models.Model):
    date                    = models.DateTimeField('Дата', default=DT.datetime.now, null=True, blank=False)
    doc_id                  = models.IntegerField('Ид документа', default=0, null=True, blank=True)
    direction               = models.IntegerField('Направление', default=0, null=True, blank=True) # 1 - ОП Новые автомобили 2 - Сервис прием авто 3 - Сервис выдача автомобиля 
    time_start              = models.DateTimeField('Дата начала', default=DT.datetime.now, null=True, blank=False)
    time_end                = models.DateTimeField('Дата окончания', default=DT.datetime.now, null=True, blank=False)
    records                 = models.ForeignKey(Records_voice_recorder, null=True, on_delete=models.SET_NULL, verbose_name="Запись")
    data_json               = models.TextField("Данные", default='', null=True, blank=True)
    duration                = models.IntegerField('Продолжительность', default=0, null=True, blank=True)
    rlk                     = models.ForeignKey(DocRLK, on_delete=models.SET_NULL, null=True, verbose_name="Рабочий лист")
    error                   = models.BooleanField("Ошибочен", default=False, null=True)

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
        return "{} - {} - {}".format(self.date, self.doc_id, self.direction) 

    def save(self, *args, **kwargs):
        
        try:
            self.rlk      = DocRLK.objects.get(pk = self.doc_id)
        except:
            s = 1

        try:
            self.duration = (self.time_end - self.time_start).seconds
        except:
            self.duration = 0
        
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'records_voice_recorder_queue'
        verbose_name = "Очередь распознования"
        verbose_name_plural = "Очередь распознования"
        ordering = ["rlk__dataTime"]


class Records_voice_recorder_cvc(models.Model):
    records             = models.ForeignKey(Records_voice_recorder, null=True, on_delete=models.SET_NULL, verbose_name="Запись диктофона")
    date                = models.DateTimeField('Дата', default=DT.datetime.now, null=True, blank=False)
    comment             = models.CharField("Комментарий", default='', max_length=2500)
    data_json           = models.TextField("Данные", default='', null=True, blank=True)
    
    def __str__(self):
        return "{} - {}".format(self.date, self.records) 

    class Meta:
        db_table = 'records_voice_recorder_cvc'
        verbose_name = "Запись диктофона отправка в CVC"
        verbose_name_plural = "Записи диктофона отправленные в CVC"


class Records_voice_recorder_cvc_checklist(models.Model):
    rlk                 = models.ForeignKey(DocRLK, related_name="rlk", null=True, on_delete=models.SET_NULL, verbose_name="Рабочий лист")
    direction           = models.IntegerField('Направление', default=1, null=True, blank=True) # 1 - ОП Новые автомобили 2 - Сервис прием авто 3 - Сервис выдача автомобиля 
    records             = models.ForeignKey(Records_voice_recorder, null=True, on_delete=models.SET_NULL, verbose_name="Запись диктофона")
    date                = models.DateTimeField('Дата', default=DT.datetime.now, null=True, blank=False)
    time_start          = models.DateTimeField('Дата начала', default=DT.datetime.now, null=True, blank=False)
    time_end            = models.DateTimeField('Дата окончания', default=DT.datetime.now, null=True, blank=False)
    duration            = models.IntegerField('Продолжительность', default=0, null=True, blank=True)
    comment             = models.CharField("Комментарий", default='', max_length=2500)
    company             = models.BooleanField("Юрлицо", default=False, null=True)
    success             = models.BooleanField("Обработан", default=False, null=True)
    canceled            = models.BooleanField("Отменен", default=False, null=True)
    result              = models.IntegerField('Результат', default=0, null=True, blank=True)
    сheck_settings      = models.ForeignKey(Check_settings, related_name="records_voice_recorder_cvc_checklist_сheck_settings", null=True, on_delete=models.SET_NULL, verbose_name="Настройки чек листа")

    def detail_chelist(self):
        infos = Records_voice_recorder_cvc_checklist_kg.objects.filter(checklist_cvc = self)
        dict_info = dict()
        for info in infos:
            field_name = 'cvc_v' + str(info.questions_kg.field)[0:3].replace('.', '_')
            dict_info[field_name] = info.value
        questions = Records_questions.objects.all()
        for question in questions:
            field_name = 'cvc_v' + str(question.field)[0:3].replace('.', '_')
            if not field_name in dict_info:
                dict_info[field_name] = 0
        return dict_info
    
    def detail_chelist_human(self):
        infos = Records_voice_recorder_cvc_checklist_tematics.objects.filter(checklist = self).order_by('tematic__field')
        dict_info = dict()
        for info in infos:
            field_name = info.tematic.field
            dict_info[field_name] = info.value
        return dict_info
    
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

    def save(self, *args, **kwargs):
        
        try:
            if self.сheck_settings == None:
                count_settings = Settings_check_records.objects.filter(direction = self.direction).count()
                if count_settings > 0:
                    self.сheck_settings = Settings_check_records.objects.filter(direction = self.direction)[0].check_settings
        except:
            s = 1

        try:
            self.result     = Records_voice_recorder_cvc_checklist_kg.objects.filter(checklist_cvc = self).aggregate(Sum('value'))['value__sum']
            if self.result == None:
                self.result     = 0
            self.canceled   = Records_voice_recorder_cvc_checklist_tematics.objects.filter(checklist = self).filter(tematic__canceled = True).filter(confirmed = True).count() > 0
            
            if self.result < cancel_limit:
                self.canceled = True 

        except:
            s = 1
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return "{} - {}".format(self.date, self.records) 

    class Meta:
        db_table = 'records_voice_recorder_cvc_checklist'
        verbose_name = "Чек лист ОП"
        verbose_name_plural = "Чек листы ОП"


class Records_voice_recorder_cvc_tematics(models.Model):
    name                = models.CharField("Наименование", default='', max_length=2500)
    id_cvc              = models.CharField("ИД cvc", default='', max_length=2500)
    activated           = models.BooleanField("Активна", default=False, null=True)
    company             = models.BooleanField("Юрлицо", default=False, null=True)
    canceled            = models.BooleanField("Не создвать чек лист", default=False, null=True)
    field               = models.CharField("Пункт чек листа", max_length=200)

    def get_tematics_fields_count(self):
        return Records_voice_recorder_cvc_tematics_fields.objects.filter(tematics_cvc = self).count()
    
    def __str__(self):
        return "{} - {} - {}".format(self.name, self.id_cvc, self.activated) 

    class Meta:
        db_table = 'records_voice_recorder_cvc_tematics'
        verbose_name = "Тематика CVC"
        verbose_name_plural = "Тематики CVC"


class Records_questions(models.Model):
    name                = models.CharField("Наименование", max_length=200)
    сheck_settings      = models.ForeignKey(Check_settings, related_name="records_questions_сheck_settings", null=True, on_delete=models.SET_NULL, verbose_name="Настройки чек листа")
    direction           = models.IntegerField('Направление', default=0, null=True, blank=True) # 1 - ОП Новые автомобили 2 - Сервис прием авто 3 - Сервис выдача автомобиля 
    canceled            = models.BooleanField("Не подлежит оценке", default=False, null=True)
    estimation          = models.IntegerField('Оценка', default=0, null=True, blank=True) 
    tematics            = models.ManyToManyField(Records_voice_recorder_cvc_tematics, verbose_name='Тематики', blank=True)
    field               = models.CharField("Пункт чек листа", max_length=200)
    chapter             = models.CharField("Раздел", default='', max_length=200)
    priority_chapter    = models.IntegerField('Приоритет в разделе', default=0, null=True, blank=True)
    chapter_name        = models.CharField("Раздел наименование", default='', max_length=200)
    event_sale          = models.BooleanField("Есть соглашение день в день", default=False, null=True)
    event_trade_in      = models.BooleanField("Есть подвод тррейд ин день в день", default=False, null=True)

    def __str__(self):
        return "{} - {} - {}".format(self.name, self.direction, self.direction) 

    class Meta:
        db_table = 'records_questions'
        verbose_name = "Вопрос чек листа диктофона"
        verbose_name_plural = "Вопросы чек листа диктофона"    


class Records_voice_recorder_cvc_tematics_fields(models.Model):
    tematics_cvc        = models.ForeignKey(Records_voice_recorder_cvc_tematics, null=True, on_delete=models.SET_NULL, verbose_name="Тематика")
    field               = models.CharField("Пункт чек листа", max_length=200)
    value               = models.IntegerField('Значение', default=0, null=True, blank=True)
    
    def __str__(self):
        return "{} - {} - {}".format(self.tematics_cvc, self.field, self.value) 

    class Meta:
        db_table = 'records_voice_recorder_cvc_tematics_fields'
        verbose_name = "Тематика CVC c нашими полями"
        verbose_name_plural = "Тематики CVC c нашими полями"


class Records_voice_recorder_cvc_checklist_tematics(models.Model):
    checklist           = models.ForeignKey(Records_voice_recorder_cvc_checklist, null=True, on_delete=models.SET_NULL, verbose_name="Чек лист")
    tematic             = models.ForeignKey(Records_voice_recorder_cvc_tematics, null=True, on_delete=models.SET_NULL, verbose_name="Тематика")
    value               = models.IntegerField('Значение', default=0, null=True, blank=True)
    confirmed           = models.BooleanField("Сработала", default=False, null=True) 

    def __str__(self):
        return "{} - {}".format(self.checklist, self.tematic) 

    class Meta:
        db_table = 'records_voice_recorder_cvc_checklist_tematics'
        verbose_name = "Чек лист отдела продаж новых автомобилей CVC"
        verbose_name_plural = "Чек лист отдела продаж новых автомобилей CVC"


class Records_voice_recorder_cvc_checklist_kg(models.Model):
    checklist_cvc   = models.ForeignKey(Records_voice_recorder_cvc_checklist, null=True, on_delete=models.SET_NULL, verbose_name="Чек лист") 
    questions_kg    = models.ForeignKey(Records_questions, null=True, on_delete=models.SET_NULL, verbose_name="Вопрос")
    value           = models.IntegerField('Значение', default=0, null=True, blank=True)

    def __str__(self):
        return "{} - {}".format(self.checklist_cvc, self.questions_kg) 

    class Meta:
        db_table = 'records_voice_recorder_cvc_checklist_kg'
        verbose_name = "Чек лист отдела продаж новых автомобилей CVC с нашими вопросами"
        verbose_name_plural = "Чек лист отдела продаж новых автомобилей CVC с нашими вопросами"