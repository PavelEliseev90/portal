from django.db import models
from datetime import datetime
from documents.models import DocRLK, DocZN
from refs.models import RefTypeCanceledCheckList
from django.conf import settings
from recognition.models import Records_voice_recorder

from django.db.models.signals import post_delete, post_save

from changelog.mixins import ChangeloggableMixin
from changelog.signals import journal_save_handler, journal_delete_handler


class CheckList(ChangeloggableMixin, models.Model):
    dataTimeCreate      = models.DateTimeField('Дата создания', default=datetime.now, blank=False)
    dataTime            = models.DateTimeField('Дата', default=datetime.now, blank=False)
    user                = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,verbose_name="Автор")
    rlk                 = models.ForeignKey(DocRLK, related_name="DocRLK", null=True, on_delete=models.SET_NULL, verbose_name="Рабочий лист")
    comment             = models.CharField("Комментарий", default='', max_length=2500) 
    
    v1_1 = models.IntegerField("МОП спросил имя клиента первым", default=0)
    v1_2 = models.IntegerField("Обращался к клиенту по имени не менее 3-х раз", default=0)
    v1_3 = models.IntegerField("Small talk", default=0)
    v1_4 = models.IntegerField("МОП управляет процессом беседы", default=0)

    v2_1 = models.IntegerField("Сроки приобретения", default=0)
    v2_2 = models.IntegerField("Сравнение с конкурентами/отработка возражений", default=0)
    v2_3 = models.IntegerField("Уточнил ключевые потребности у клиента /динамика/комфорт/цена/безопастность/экономичность", default=0)
    v2_4 = models.IntegerField("Получил ли подтверждение от клиента / Резюмирование", default=0)
    v2_5 = models.IntegerField("Финансовые условия прибретения / наличные/кредит/трейд-ин", default=0)
    v2_6 = models.IntegerField("Пожелания к модификации/ комплектация/цвет/функционал/модель/коробка", default=0)
    
    v3_1 = models.IntegerField("Презентации автомобиля в шоурум / без 6 точек в шоу рум", default=0)
    v3_2 = models.IntegerField("В презентации менеджер ведет клиента/ уверенность", default=0)
    v3_3 = models.IntegerField("Презентация на основе потребностей клиента / отталкиваясь от того что говорил клиент ранее (логика)", default=0)
    v3_4 = models.IntegerField("Проведение Тест-драйва", default=0)
    v3_5 = models.IntegerField("Предложение альтернативных вариантов/из наличия/транзит /заказ/ модель", default=0)

    v4_1 = models.IntegerField("Грамотность речи", default=0)
    v4_2 = models.IntegerField("Получение обратной связи от клиента/ согласие клиента с мнением менеджера/мнение клиента", default=0)
    v4_3 = models.IntegerField("Менеджер не перебивает клиента", default=0)
    v4_4 = models.IntegerField("Преобладают открытые вопросы", default=0)

    v5_1 = models.IntegerField("Презентация дополнительного оборудования", default=0)
    v5_2 = models.IntegerField("Презентация кредитного продукта", default=0)
    v5_3 = models.IntegerField("Презентация страховых услуг (ОСАГО, КАСКО)", default=0)
    v5_4 = models.IntegerField("Презентация Госрегистрация", default=0)
    v5_5 = models.IntegerField("Предложение услуги Traid-in", default=0)

    v6_1 = models.IntegerField("Присутствует отработка возражений по кредиту (согласие на кредит)", default=0)
    v6_2 = models.IntegerField("Присутствует отработка возражений по Trade-In (согласие на Trade-In)", default=0)
    v6_3 = models.IntegerField("Отработка возражений / не спорит с клиентом/ не уходит от ответа на возражение", default=0)
    
    v7_1 = models.IntegerField("Предложение заключения сделки", default=0)
    v7_2 = models.IntegerField("Выяснение причины отказа", default=0)
    v7_3 = models.IntegerField("Предложение решения (случае сомнения клиента)", default=0)
    v7_4 = models.IntegerField("Получение контактов клиента", default=0)

    v8_1 = models.IntegerField("Договоренность ДСК на звонок с точной датой в течение недели", default=0)
    v8_2 = models.IntegerField("ДСК на визит с точной датой в течение недели", default=0)
    v8_3 = models.IntegerField("Сделка состоялась", default=0)

    audio = models.FileField(upload_to='audio/%Y/%m/%d/', verbose_name="Запись", blank=True, null=True)

    audio_voice_recorder = models.ForeignKey(Records_voice_recorder, null=True, on_delete=models.SET_NULL, verbose_name="Запись диктофона")

    canceled    = models.BooleanField("Не подлежит оценке", default=False, null=True)

    result      = models.IntegerField("Итог", default=0)

    canceledType            = models.ForeignKey(RefTypeCanceledCheckList, null=True, on_delete=models.SET_NULL, verbose_name="Причина отмены")
    comment_canceled        = models.CharField("Комментарий отмены", default='', max_length=2500) 

    version_checklist       = models.IntegerField("Версия чеклиста", default=0)

    cheked                  = models.BooleanField("Проверен", default=False, null=True)
    cheked_user             = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="cheked_user", null=True, on_delete=models.SET_NULL,verbose_name="Проверил")
    
    def checkItog(self):
        return self.v1_1 + self.v1_2 + self.v1_3 + self.v1_4 + self.v2_1 + self.v2_2 + self.v2_3 + self.v2_4 + self.v2_5 + self.v2_6 + self.v3_1 + self.v3_2 + self.v3_3 + self.v3_4 + self.v3_5 + self.v4_1 + self.v4_2 + self.v4_3 + self.v4_4 + self.v5_1 + self.v5_2 + self.v5_3 + self.v5_4 + self.v5_5 + self.v6_1 + self.v6_2 + self.v6_3 + self.v7_1 + self.v7_2 + self.v7_3 + self.v7_4 + self.v8_1 + self.v8_2 + self.v8_3
    checkItog.short_description = 'Итог'
    checkItog.allow_tags = True

    def checkItog_v1(self):
        return self.v1_1 + self.v1_2 + self.v1_3 + self.v1_4
    checkItog_v1.short_description = 'Итог раздела 1'
    checkItog_v1.allow_tags = True

    def checkItog_v1_P(self):
        return int((self.v1_1 + self.v1_2 + self.v1_3 + self.v1_4) / 10 * 100)
    checkItog_v1_P.short_description = 'Итог раздела 1 %'
    checkItog_v1_P.allow_tags = True

    def checkItog_v2(self):
        return self.v2_1 + self.v2_2 + self.v2_3 + self.v2_4 + self.v2_5 + self.v2_6
    checkItog_v2.short_description = 'Итог раздела 2'
    checkItog_v2.allow_tags = True

    def checkItog_v2_P(self):
        return int((self.v2_1 + self.v2_2 + self.v2_3 + self.v2_4 + self.v2_5 + self.v2_6) / 15 * 100)
    checkItog_v2_P.short_description = 'Итог раздела 2 %'
    checkItog_v2_P.allow_tags = True

    def checkItog_v3(self):
        return self.v3_1 + self.v3_2 + self.v3_3 + self.v3_4 + self.v3_5
    checkItog_v3.short_description = 'Итог раздела 3'
    checkItog_v3.allow_tags = True

    def checkItog_v3_P(self):
        return int((self.v3_1 + self.v3_2 + self.v3_3 + self.v3_4 + self.v3_5) / 14 * 100)
    checkItog_v3_P.short_description = 'Итог раздела 3 %'
    checkItog_v3_P.allow_tags = True

    def checkItog_v4(self):
        return self.v4_1 + self.v4_2 + self.v4_3 + self.v4_4
    checkItog_v4.short_description = 'Итог раздела 4'
    checkItog_v4.allow_tags = True

    def checkItog_v4_P(self):
        return int((self.v4_1 + self.v4_2 + self.v4_3 + self.v4_4) / 8 * 100)
    checkItog_v4_P.short_description = 'Итог раздела 4 %'
    checkItog_v4_P.allow_tags = True

    def checkItog_v5(self):
        return self.v5_1 + self.v5_2 + self.v5_3 + self.v5_4 + self.v5_5
    checkItog_v5.short_description = 'Итог раздела 5'
    checkItog_v5.allow_tags = True

    def checkItog_v5_P(self):
        return int((self.v5_1 + self.v5_2 + self.v5_3 + self.v5_4 + self.v5_5) / 16 * 100)
    checkItog_v5_P.short_description = 'Итог раздела 5 %'
    checkItog_v5_P.allow_tags = True

    def checkItog_v6(self):
        return self.v6_1 + self.v6_2 + self.v6_3
    checkItog_v6.short_description = 'Итог раздела 6'
    checkItog_v6.allow_tags = True

    def checkItog_v6_P(self):
        return int((self.v6_1 + self.v6_2 + self.v6_3) / 7 * 100)
    checkItog_v6_P.short_description = 'Итог раздела 6 %'
    checkItog_v6_P.allow_tags = True

    def checkItog_v7(self):
        return self.v7_1 + self.v7_2 + self.v7_3 + self.v7_4
    checkItog_v7.short_description = 'Итог раздела 7'
    checkItog_v7.allow_tags = True

    def checkItog_v7_P(self):
        return int((self.v7_1 + self.v7_2 + self.v7_3 + self.v7_4) / 15 * 100)
    checkItog_v7_P.short_description = 'Итог раздела 7 %'
    checkItog_v7_P.allow_tags = True

    def checkItog_v8(self):
        return self.v8_1 + self.v8_2 + self.v8_3
    checkItog_v8.short_description = 'Итог раздела 8'
    checkItog_v8.allow_tags = True

    def checkItog_v8_P(self):
        return int((self.v8_1 + self.v8_2 + self.v8_3) / 15 * 100)
    checkItog_v8_P.short_description = 'Итог раздела 8 %'
    checkItog_v8_P.allow_tags = True

    def save(self, *args, **kwargs):
        try:
            self.result = self.checkItog()
        except:
            self.result = 0
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'checkList'
        verbose_name = "Чек лист"
        verbose_name_plural = "Чек листы"

post_save.connect(journal_save_handler, sender=CheckList)
post_delete.connect(journal_delete_handler, sender=CheckList)


class CheckListServiceIn(ChangeloggableMixin, models.Model):
    dataTimeCreate  = models.DateTimeField('Дата создания', default=datetime.now, blank=False)
    dataTime        = models.DateTimeField('Дата', default=datetime.now, blank=False)
    user            = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,verbose_name="Автор")
    zn              = models.ForeignKey(DocZN, related_name="DocZN", null=True, on_delete=models.SET_NULL, verbose_name="Заказ наряд")
    comment         = models.CharField("Комментарий", default='', max_length=2500) 
    
    v1_1 = models.IntegerField("Заранее создана калькуляция, исходя из причины обращения клиента и истории обслуживания автомобиля", default=0)
    v1_2 = models.IntegerField("Произнес свою должность и представился сам. Поблагодарил за пунктуальность (если клиент не опоздал).", default=0)
    v1_3 = models.IntegerField("Консультант вежливо выяснил имя клиента либо сразу обратился по имени", default=0)
    v1_4 = models.IntegerField("Консультант уточнил у клиента: ФИО собственника автомобиля / личный контактный номер телефона / адрес эл. почты (в т.ч. актуальность внесенного адреса ранее)", default=0)
    v1_5 = models.IntegerField("Консультант выяснил объем работ, интересующих клиента с обязательным уточнением пожеланий о дополнительных работах/жалобах. Вся информация полученная от клиента зафиксирована в ЗН", default=0)
    v1_6 = models.IntegerField("МК напомнил клиенту, что центр не несет ответственности за денежные средства и вещи оставленные в автомобиле, а так же уточнил, куда положить замененные з/ч (при их наличии).", default=0)
    
    v2_1 = models.IntegerField("Не отвлекается во время общения с клиентом на посторонние дела и разговоры", default=0)
    v2_2 = models.IntegerField("В презентации работ и услуг консультант ведет клиента/ уверен в себе", default=0)
    v2_3 = models.IntegerField("Презентация на основе потребностей клиента / отталкиваясь от того что было озвучено клиентом ранее", default=0)
    v2_4 = models.IntegerField("Грамотность речи", default=0)
    v2_5 = models.IntegerField("Получение обратной связи от клиента/ согласие клиента с мнением консультанта/мнение клиента", default=0)
    v2_6 = models.IntegerField("Консультант не перебивает клиента", default=0)
    v2_7 = models.IntegerField("Преобладают открытые вопросы", default=0)

    v3_1 = models.IntegerField("Предложение проведения услуги Интерактивная приемка/ Диалоговая приемка ", default=0)
    v3_2 = models.IntegerField("Проведен осмотр автомобиля совместо с клиентом", default=0)
    v3_3 = models.IntegerField("МК предложил не менее 2х дополнительных услуг сервиса к основной причине обращения клиента (доп.оборудование; слесарные работы и или аксессуары). ", default=0)
    v3_4 = models.CharField("Предлагает с ХПВ дополнительное оборудование: установку сетки в решетку переднего бампера, установку секретных гаек (болтов), установку подкрылков и брызговиков. Не менее 2-х предложений по ДОП или профилактик.", default='', max_length=2500)
    v3_5 = models.CharField("Поднимает капот и проводит осмотр моторного отсека. Проверяет утечку и комментирует: уровни моторного масла, тормозной и охлаждающей жидкостей, рабочей жидкости рулевого управления, а также наличие подтеков на двигателе и патрубках.", default='', max_length=2500)
    v3_6 = models.CharField("Предлагает : 1л масла с собой, долить жидкость омывателя (при отсутствии у клиента - купить нашу и на запас), мойку подкапотного пространства, газовые упоры капота, чистку дроселя, регулировку света фар, промывку инжектора, чистку форсунок стеклоомывателя, промывку ДВС перед сменой масла. Не менее 2-х предложений по ДОП или профилактик.", default='', max_length=2500)
    v3_7 = models.CharField("Консультант продает: детали экстерьера, защитная накладка порога заднего бампера, нанесение антидождя, проведение антибактериальной обработки - озонирования, покрытие керамика, тонировку, бронировку, дефлектора окон, легкосплавные диски. Минимум 1 предложение.", default='', max_length=2500)
    v3_8 = models.CharField("Предлагает: набор автомобилиста (или комплектующие), ковер в багажник, уборку в багажнике, компрессор, органайзер в багажник (сетка). Минимум 1 предложение.", default='', max_length=2500)
    v3_9 = models.IntegerField("Предложено купить сертификат 'Продленная гарантия на автомобиль от Корс Групп'", default=0)
    
    v4_1 = models.IntegerField("Принятие стороны клиента (важности, уместностии…., я раньше тоже так думал)", default=0)
    v4_2 = models.IntegerField("Уточнение (В сравнении с чем? Откуда такая информация? Не могли бы Вы объяснить…? Что именно Вы имеете ввиду говоря о …? Правильно ли я Вас понимаю…?)", default=0)
    v4_3 = models.IntegerField("Убедительность аргументации на основании мнения клиента", default=0)
    v4_4 = models.IntegerField("Была работа с возражением при отказе от покупки сертификата 'Продленная гарантия на автомобиль от Корс Групп'", default=0)

    v5_1 = models.IntegerField("Согласовывает с клиентом итоговый заказ-наряд. Разъясняет, какие работы будут проводиться на автомобиле, что будет меняться. Получает согласие клиента на сумму. Подписывают документы.", default=0)
    v5_2 = models.IntegerField("Ориентирует о точном времени ремонта и выдачи ам.", default=0)
    v5_3 = models.IntegerField("Уточнение способа получения согласования (например: в ДЦ, телефон, ВотсАпп)", default=0)
    
    audio = models.FileField(upload_to='audio/%Y/%m/%d/', verbose_name="Запись", blank=True, null=True)

    audio_voice_recorder = models.ForeignKey(Records_voice_recorder, null=True, on_delete=models.SET_NULL, verbose_name="Запись диктофона")

    canceled            = models.BooleanField("Не подлежит оценке", default=False, null=True)

    result              = models.IntegerField("Итог", default=0)

    canceledType        = models.ForeignKey(RefTypeCanceledCheckList, null=True, on_delete=models.SET_NULL, verbose_name="Причина отмены")

    def checkItog(self):
        return self.v1_1 + self.v1_2 + self.v1_3 + self.v1_4 + self.v1_5 + self.v1_6 + self.v2_1 + self.v2_2 + self.v2_3 + self.v2_4 + self.v2_5 + self.v2_6 + self.v2_7 + self.v3_1 + self.v3_2 + self.v3_3 + self.v4_1 + self.v4_2 + self.v4_3 + self.v5_1 + self.v5_2 + self.v5_3
    checkItog.short_description = 'Итог'
    checkItog.allow_tags = True

    def checkItog_v1(self):
        return self.v1_1 + self.v1_2 + self.v1_3 + self.v1_4 + self.v1_5 + self.v1_6
    checkItog_v1.short_description = 'Итог раздела 1'
    checkItog_v1.allow_tags = True

    def checkItog_v1_P(self):
        return int((self.v1_1 + self.v1_2 + self.v1_3 + self.v1_4 + self.v1_5 + self.v1_6) / 32 * 100)
    checkItog_v1_P.short_description = 'Итог раздела 1 %'
    checkItog_v1_P.allow_tags = True

    def checkItog_v2(self):
        return self.v2_1 + self.v2_2 + self.v2_3 + self.v2_4 + self.v2_5 + self.v2_6 + self.v2_7
    checkItog_v2.short_description = 'Итог раздела 2'
    checkItog_v2.allow_tags = True

    def checkItog_v2_P(self):
        return int((self.v2_1 + self.v2_2 + self.v2_3 + self.v2_4 + self.v2_5 + self.v2_6 + self.v2_7) / 14 * 100)
    checkItog_v2_P.short_description = 'Итог раздела 2 %'
    checkItog_v2_P.allow_tags = True

    def checkItog_v3(self):
        return self.v3_1 + self.v3_2 + self.v3_3
    checkItog_v3.short_description = 'Итог раздела 3'
    checkItog_v3.allow_tags = True

    def checkItog_v3_P(self):
        return int((self.v3_1 + self.v3_2 + self.v3_3) / 24 * 100) 
    checkItog_v3_P.short_description = 'Итог раздела 3 %'
    checkItog_v3_P.allow_tags = True

    def checkItog_v4(self):
        return self.v4_1 + self.v4_2 + self.v4_3
    checkItog_v4.short_description = 'Итог раздела 4'
    checkItog_v4.allow_tags = True

    def checkItog_v4_P(self):
        return int((self.v4_1 + self.v4_2 + self.v4_3) / 8 * 100)
    checkItog_v4_P.short_description = 'Итог раздела 4 %'
    checkItog_v4_P.allow_tags = True

    def checkItog_v5(self):
        return self.v5_1 + self.v5_2 + self.v5_3
    checkItog_v5.short_description = 'Итог раздела 5'
    checkItog_v5.allow_tags = True

    def checkItog_v5_P(self):
        return int((self.v5_1 + self.v5_2 + self.v5_3) / 22 * 100) 
    checkItog_v5_P.short_description = 'Итог раздела 5 %'
    checkItog_v5_P.allow_tags = True

    def save(self, *args, **kwargs):
        try:
            self.result = self.checkItog()
        except:
            self.result = 0
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'checkListServiceIn'
        verbose_name = "Чек лист сервиса (приемка)"
        verbose_name_plural = "Чек листы сервиса (приемка)"

post_save.connect(journal_save_handler, sender=CheckListServiceIn)
post_delete.connect(journal_delete_handler, sender=CheckListServiceIn)


class CheckListServiceOut(ChangeloggableMixin, models.Model):
    dataTimeCreate  = models.DateTimeField('Дата создания', default=datetime.now, blank=False)
    dataTime        = models.DateTimeField('Дата', default=datetime.now, blank=False)
    user            = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,verbose_name="Автор")
    zn              = models.ForeignKey(DocZN, related_name="DocZN_out", null=True, on_delete=models.SET_NULL, verbose_name="Заказ наряд")
    comment         = models.CharField("Комментарий", default='', max_length=2500) 
    
    v1_1 = models.IntegerField("Разъясняет клиенту каждую позицию в счете.", default=0)
    v1_2 = models.IntegerField("Подводит клиента к автомобилю для демонстрации выполненных работ. Демонстрирует клиенту проведенные работы, показывает и комментирует выполнение по каждому виду работ. Если была неисправность, показывает, что она устранена.  Развеивает опасения.", default=0)
    v1_3 = models.IntegerField("Демонстрирует заменённые запчасти в пакете, открывая багажник.", default=0)
    v1_4 = models.IntegerField("Получает подтверждение от клиента о том, что все заявленные работы выполнены, и в случае возникновения вопросов, просит звонить именно ему (в т.ч. передает свою визитку). ", default=0)
    
    v2_1 = models.CharField("МК приветствует клиента и благодарит за пунктуальность (если клиент уезжал из ДЦ).", default='', max_length=2500)
    v2_2 = models.IntegerField("МК обращается к клиенту по имени.", default=0)
    v2_3 = models.IntegerField("МК улыбается, приветлив и доброжелателен, позитивный голос.", default=0)
    v2_4 = models.IntegerField("При формулировке вопросов и просьб использует различные вежливые фразы. В речи МК отсутствуют негативные слова, уменьшительно-ласкательные, слова-паразиты.", default=0)
    
    v3_1 = models.IntegerField("Дает развернутые рекомендации по дальнейшему обслуживанию и эксплуатации автомобиля.", default=0)
    v3_2 = models.IntegerField("Предложено установить мобильное приложение АХ Корс Групп (в соответствии со скриптом предложения) и мобильное приложение импортера (при наличии такового требования).", default=0)
    
    v4_1 = models.IntegerField("Рекомендованные работы занесены в программу корректно (соответствует ориентировочно-приближенной дате согласованной с клиентом).", default=0)
    v4_2 = models.IntegerField("Договоренность о следующем визите на ТО/МС занесена в программу корректно (соответствует ориентировочно-приближенной дате согласованной с клиентом).", default=0)
    v4_3 = models.IntegerField("Клиенту озвучено, что после визита на обслуживание будет отправлено смс-сообщение с просьбой оценить качество обслуживания.", default=0)
    v4_4 = models.IntegerField("Благодарность за визит", default=0)
    v4_5 = models.IntegerField("Клиенту сообщено, что после посещения СЦ будет звонок с предложением обмена шин и дисков.", default=0)

    audio                   = models.FileField(upload_to='audio/%Y/%m/%d/', verbose_name="Запись", blank=True, null=True)

    audio_voice_recorder    = models.ForeignKey(Records_voice_recorder, null=True, on_delete=models.SET_NULL, verbose_name="Запись диктофона")

    canceled                = models.BooleanField("Не подлежит оценке", default=False, null=True)

    result                  = models.IntegerField("Итог", default=0)

    canceledType            = models.ForeignKey(RefTypeCanceledCheckList, null=True, on_delete=models.SET_NULL, verbose_name="Причина отмены")

    def checkItog(self):
        return self.v1_1 + self.v1_2 + self.v1_3 + + self.v1_4 + self.v2_2 + self.v2_3 + self.v2_4 + self.v3_1 + self.v3_2 + self.v4_1 + self.v4_2 + self.v4_3 + self.v4_4
    checkItog.short_description = 'Итог'
    checkItog.allow_tags = True

    def checkItog_v1(self):
        return self.v1_1 + self.v1_2 + self.v1_3 + + self.v1_4
    checkItog_v1.short_description = 'Итог раздела 1'
    checkItog_v1.allow_tags = True

    def checkItog_v1_P(self):
        return int((self.v1_1 + self.v1_2 + self.v1_3 + + self.v1_4) / 37 * 100)
    checkItog_v1_P.short_description = 'Итог раздела 1 %'
    checkItog_v1_P.allow_tags = True

    def checkItog_v2(self):
        return self.v2_2 + self.v2_3 + self.v2_4
    checkItog_v2.short_description = 'Итог раздела 2'
    checkItog_v2.allow_tags = True

    def checkItog_v2_P(self):
        return int((self.v2_2 + self.v2_3 + self.v2_4) / 11 * 100)
    checkItog_v2_P.short_description = 'Итог раздела 2 %'
    checkItog_v2_P.allow_tags = True

    def checkItog_v3(self):
        return self.v3_1 + self.v3_2
    checkItog_v3.short_description = 'Итог раздела 3'
    checkItog_v3.allow_tags = True

    def checkItog_v3_P(self):
        return int((self.v3_1 + self.v3_2) / 15 * 100) 
    checkItog_v3_P.short_description = 'Итог раздела 3 %'
    checkItog_v3_P.allow_tags = True

    def checkItog_v4(self):
        return self.v4_1 + self.v4_2 + self.v4_3 + self.v4_4
    checkItog_v4.short_description = 'Итог раздела 4'
    checkItog_v4.allow_tags = True

    def checkItog_v4_P(self):
        return int((self.v4_1 + self.v4_2 + self.v4_3 + self.v4_4) / 37 * 100)
    checkItog_v4_P.short_description = 'Итог раздела 4 %'
    checkItog_v4_P.allow_tags = True

    def save(self, *args, **kwargs):
        try:
            self.result = self.checkItog()
        except:
            self.result = 0
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'checkListServiceOut'
        verbose_name = "Чек лист сервиса (выдача)"
        verbose_name_plural = "Чек листы сервиса (выдача)"

post_save.connect(journal_save_handler, sender=CheckListServiceOut)
post_delete.connect(journal_delete_handler, sender=CheckListServiceOut)


class CheckListTradeIn(ChangeloggableMixin, models.Model):
    dataTimeCreate  = models.DateTimeField('Дата создания', default=datetime.now, blank=False)
    dataTime        = models.DateTimeField('Дата', default=datetime.now, blank=False)
    user            = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,verbose_name="Автор")
    rlk             = models.ForeignKey(DocRLK, related_name="rlkCheckTradeIn", null=True, on_delete=models.SET_NULL, verbose_name="Рабочий лист")
    comment         = models.CharField("Комментарий", default='', max_length=2500) 
    
    v1_1 = models.IntegerField("Поздоровался и представился по стандарту", default=0)
    v1_2 = models.IntegerField("Спросил, как можно обращаться к клиенту", default=0)
    v1_3 = models.IntegerField("Сказал приятно познакомиться", default=0)
    v1_4 = models.IntegerField("Передал свою визитку клиенту", default=0)
    
    v2_1 = models.IntegerField("Рассказал клиенту что и зачем сейчас будет происходить", default=0)
    v2_2 = models.IntegerField("Рассказал клиенту о необходимом времени на оценку", default=0)
    
    v3_1 = models.IntegerField("Выяснил какой тип сделки (трейд ин/выкуп/комиссия)", default=0)
    v3_2 = models.IntegerField("Выяснил причину продажи (при отсутствии планов на покупку другого автомобиля)", default=0)
    v3_3 = models.IntegerField("Узнал оценивался ли клиент у нас и где то еще", default=0)
    v3_4 = models.IntegerField("Узнал продает ли клиент свой а/м самостоятельно", default=0)
    v3_5 = models.IntegerField("Установил ЛПР.", default=0)
    v3_6 = models.IntegerField("Узнал в какие сроки клиент примет решение.", default=0)
    v3_7 = models.IntegerField("Презентовал услугу на основе выявленных потребностей.", default=0)
    
    v4_1 = models.IntegerField("Рассказал клиенту про этап осмотра. Зачем и сколько по времени это займет?", default=0)
    v4_2 = models.IntegerField("Взял с собой на осмотр клиента", default=0)
    v4_3 = models.IntegerField("Попросил клиента самостоятельно рассказать о совем автомобиле", default=0)
    v4_4 = models.IntegerField("__о недостатках", default=0)
    v4_5 = models.IntegerField("__истории эксплуатации", default=0)
    v4_6 = models.IntegerField("Использовал вопрос 'а что еще'", default=0)
    v4_7 = models.IntegerField("Попросил клиента выполнить простые поручения (открыть капот, багажник, бардачок и тд)", default=0)
    
    v5_1 = models.IntegerField("Рассказал клиенту о времени ожидания и что сейчас будет происходить", default=0)
    
    v6_1 = models.IntegerField("Назвал цену по принципу: преимущества - цена - призыв к действию (запись на диагностику)", default=0)
    v6_2 = models.IntegerField("Отработка возражения. Возражение клиента - наше присоединение - ответ - аргументация", default=0)
    v6_3 = models.IntegerField("Рассказал клиенту про условия проведения диагностики", default=0)
    v6_4 = models.IntegerField("Отработал возражение клиента 'зачем мне Ваша диагностика, Вы специально занизите цену'", default=0)
    v6_5 = models.IntegerField("Записал на диагностику", default=0)
    v6_6 = models.IntegerField("Выяснил причину отказа", default=0)
    v6_7 = models.IntegerField("Предложил варианты решения (в случае отказа клиента)", default=0)
    v6_8 = models.IntegerField("Согласовал дату следующего контакта, не позднее 2 дня с момента обращения.", default=0)

    audio                   = models.FileField(upload_to='audio/%Y/%m/%d/', verbose_name="Запись", blank=True, null=True)

    audio_voice_recorder    = models.ForeignKey(Records_voice_recorder, null=True, on_delete=models.SET_NULL, verbose_name="Запись диктофона")

    canceled                =  models.BooleanField("Не подлежит оценке", default=False, null=True)

    result                  = models.IntegerField("Итог", default=0)

    canceledType            = models.ForeignKey(RefTypeCanceledCheckList, null=True, on_delete=models.SET_NULL, verbose_name="Причина отмены")

    def checkItog(self):
        return self.v1_1 + self.v1_2 + self.v1_3 + + self.v1_4 + self.v2_1 + self.v2_2 + self.v3_1 + self.v3_2 + self.v3_3 + self.v3_4 + self.v3_5 + self.v3_6 + self.v3_7 + self.v4_1 + self.v4_2 + self.v4_3 + self.v4_4 + self.v4_5 + self.v4_6 + self.v4_7 + self.v5_1 + self.v6_1 + self.v6_2 + self.v6_3 + self.v6_4 + self.v6_5 + self.v6_6 + self.v6_7 + self.v6_8

    checkItog.short_description = 'Итог'
    checkItog.allow_tags = True

    def checkItog_v1(self):
        return self.v1_1 + self.v1_2 + self.v1_3 + + self.v1_4
    checkItog_v1.short_description = 'Итог раздела 1'
    checkItog_v1.allow_tags = True

    def checkItog_v1_P(self):
        return int((self.v1_1 + self.v1_2 + self.v1_3 + + self.v1_4) / 12 * 100)
    checkItog_v1_P.short_description = 'Итог раздела 1 %'
    checkItog_v1_P.allow_tags = True

    def checkItog_v2(self):
        return self.v2_1 + self.v2_2
    checkItog_v2.short_description = 'Итог раздела 2'
    checkItog_v2.allow_tags = True

    def checkItog_v2_P(self):
        return int((self.v2_1 + self.v2_2) / 6 * 100)
    checkItog_v2_P.short_description = 'Итог раздела 2 %'
    checkItog_v2_P.allow_tags = True

    def checkItog_v3(self):
        return self.v3_1 + self.v3_2 + self.v3_3 + self.v3_4 + self.v3_5 + self.v3_6 + self.v3_7
    checkItog_v3.short_description = 'Итог раздела 3'
    checkItog_v3.allow_tags = True

    def checkItog_v3_P(self):
        return int((self.v3_1 + self.v3_2 + self.v3_3 + self.v3_4 + self.v3_5 + self.v3_6 + self.v3_7) / 16 * 100)
    checkItog_v3_P.short_description = 'Итог раздела 3 %'
    checkItog_v3_P.allow_tags = True

    def checkItog_v4(self):
        return self.v4_1 + self.v4_2 + self.v4_3 + self.v4_4 + self.v4_5 + self.v4_6 + self.v4_7
    checkItog_v4.short_description = 'Итог раздела 4'
    checkItog_v4.allow_tags = True

    def checkItog_v4_P(self):
        return int((self.v4_1 + self.v4_2 + self.v4_3 + self.v4_4 + self.v4_5 + self.v4_6 + self.v4_7) / 23 * 100)
    checkItog_v4_P.short_description = 'Итог раздела 4 %'
    checkItog_v4_P.allow_tags = True

    def checkItog_v5(self):
        return self.v5_1
    checkItog_v5.short_description = 'Итог раздела 5'
    checkItog_v5.allow_tags = True

    def checkItog_v5_P(self):
        return int(self.v5_1 / 3 * 100)
    checkItog_v5_P.short_description = 'Итог раздела 5 %'
    checkItog_v5_P.allow_tags = True

    def checkItog_v6(self):
        return self.v6_1 + self.v6_2 + self.v6_3 + self.v6_4 + self.v6_5 + self.v6_6 + self.v6_7 + self.v6_8
    checkItog_v6.short_description = 'Итог раздела 6'
    checkItog_v6.allow_tags = True

    def checkItog_v6_P(self):
        return int((self.v6_1 + self.v6_2 + self.v6_3 + self.v6_4 + self.v6_5 + self.v6_6 + self.v6_7 + self.v6_8) / 40 * 100)
    checkItog_v6_P.short_description = 'Итог раздела 6 %'
    checkItog_v6_P.allow_tags = True

    def save(self, *args, **kwargs):
        try:
            self.result = self.checkItog()
        except:
            self.result = 0
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'checkListTradeIn'
        verbose_name = "Чек лист трейд-ин (оценка)"
        verbose_name_plural = "Чек листы трейд-ин (оценка)"

post_save.connect(journal_save_handler, sender=CheckListTradeIn)
post_delete.connect(journal_delete_handler, sender=CheckListTradeIn)


class CheckList_op_kors(ChangeloggableMixin, models.Model):
    dataTimeCreate  = models.DateTimeField('Дата создания', default=datetime.now, blank=False)
    dataTime        = models.DateTimeField('Дата', default=datetime.now, blank=False)
    user            = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,verbose_name="Автор")
    rlk             = models.ForeignKey(DocRLK, related_name="doc_rlk_op_kors", null=True, on_delete=models.SET_NULL, verbose_name="Рабочий лист")
    comment         = models.CharField("Комментарий", default='', max_length=2500) 
    
    v1_1 = models.IntegerField("МОП спросил имя клиента первым", default=0)
    v1_2 = models.IntegerField("Обращался к клиенту по имени не менее 3-х раз", default=0)
    v1_3 = models.IntegerField("Small talk", default=0)
    v1_4 = models.IntegerField("МОП управляет процессом беседы", default=0)

    v2_1 = models.IntegerField("Сроки приобретения", default=0)
    v2_2 = models.IntegerField("Сравнение с конкурентами/отработка возражений", default=0)
    v2_3 = models.IntegerField("Уточнил ключевые потребности у клиента /динамика/комфорт/цена/безопастность/экономичность", default=0)
    v2_4 = models.IntegerField("Получил ли подтверждение от клиента / Резюмирование", default=0)
    v2_5 = models.IntegerField("Финансовые условия прибретения / наличные/кредит/трейд-ин", default=0)
    v2_6 = models.IntegerField("Пожелания к модификации/ комплектация/цвет/функционал/модель/коробка", default=0)
    
    v3_1 = models.IntegerField("Презентации автомобиля в шоурум / без 6 точек в шоу рум", default=0)
    v3_2 = models.IntegerField("В презентации менеджер ведет клиента/ уверенность", default=0)
    v3_3 = models.IntegerField("Презентация на основе потребностей клиента / отталкиваясь от того что говорил клиент ранее (логика)", default=0)
    v3_4 = models.IntegerField("Предложение альтернативных вариантов/из наличия/транзит /заказ/ модель", default=0)

    v4_1 = models.IntegerField("Грамотность речи", default=0)
    v4_2 = models.IntegerField("Получение обратной связи от клиента/ согласие клиента с мнением менеджера/мнение клиента", default=0)
    v4_3 = models.IntegerField("Менеджер не перебивает клиента", default=0)
    v4_4 = models.IntegerField("Преобладают открытые вопросы", default=0)

    v5_1 = models.IntegerField("Презентация дополнительного оборудования, шины", default=0)
    v5_2 = models.IntegerField("Презентация кредитного продукта", default=0)
    v5_3 = models.IntegerField("Презентация страховых услуг (ОСАГО, КАСКО)", default=0)
    v5_4 = models.IntegerField("Предложение услуги Traid-in", default=0)

    v6_1 = models.IntegerField("Присутствует отработка возражений по кредиту (согласие на кредит)", default=0)
    v6_2 = models.IntegerField("Присутствует отработка возражений по Trade-In (согласие на Trade-In)", default=0)
    v6_3 = models.IntegerField("Отработка возражений / не спорит с клиентом/ не уходит от ответа на возражение", default=0)
    
    v7_1 = models.IntegerField("Предложение заключения сделки", default=0)
    v7_2 = models.IntegerField("Выяснение причины отказа", default=0)
    v7_3 = models.IntegerField("Предложение решения (случае сомнения клиента)", default=0)
    v7_4 = models.IntegerField("Получение контактов клиента", default=0)

    v8_1 = models.IntegerField("Договоренность ДСК на звонок с точной датой в течение недели", default=0)
    v8_2 = models.IntegerField("ДСК на визит с точной датой в течение недели", default=0)
    v8_3 = models.IntegerField("Сделка состоялась", default=0)

    audio                   = models.FileField(upload_to='audio/%Y/%m/%d/', verbose_name="Запись", blank=True, null=True)

    audio_voice_recorder    = models.ForeignKey(Records_voice_recorder, null=True, on_delete=models.SET_NULL, verbose_name="Запись диктофона")

    canceled                = models.BooleanField("Не подлежит оценке", default=False, null=True)

    result                  = models.IntegerField("Итог", default=0)

    canceledType            = models.ForeignKey(RefTypeCanceledCheckList, null=True, on_delete=models.SET_NULL, verbose_name="Причина отмены")
    comment_canceled        = models.CharField("Комментарий отмены", default='', max_length=2500) 

    version_checklist       = models.IntegerField("Версия чеклиста", default=0)

    cheked                  = models.BooleanField("Проверен", default=False, null=True)
    cheked_user             = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="op_kors_cheked_user", null=True, on_delete=models.SET_NULL,verbose_name="Проверил")

    def checkItog(self):
        return self.v1_1 + self.v1_2 + self.v1_3 + self.v1_4 + self.v2_1 + self.v2_2 + self.v2_3 + self.v2_4 + self.v2_5 + self.v2_6 + self.v3_1 + self.v3_2 + self.v3_3 + self.v3_4 + self.v4_1 + self.v4_2 + self.v4_3 + self.v4_4 + self.v5_1 + self.v5_2 + self.v5_3 + self.v5_4 + self.v6_1 + self.v6_2 + self.v6_3 + self.v7_1 + self.v7_2 + self.v7_3 + self.v7_4 + self.v8_1 + self.v8_2 + self.v8_3
    checkItog.short_description = 'Итог'
    checkItog.allow_tags = True

    def checkItog_v1(self):
        return self.v1_1 + self.v1_2 + self.v1_3 + self.v1_4
    checkItog_v1.short_description = 'Итог раздела 1'
    checkItog_v1.allow_tags = True

    def checkItog_v1_P(self):
        return int((self.v1_1 + self.v1_2 + self.v1_3 + self.v1_4) / 10 * 100)
    checkItog_v1_P.short_description = 'Итог раздела 1 %'
    checkItog_v1_P.allow_tags = True

    def checkItog_v2(self):
        return self.v2_1 + self.v2_2 + self.v2_3 + self.v2_4 + self.v2_5 + self.v2_6
    checkItog_v2.short_description = 'Итог раздела 2'
    checkItog_v2.allow_tags = True

    def checkItog_v2_P(self):
        return int((self.v2_1 + self.v2_2 + self.v2_3 + self.v2_4 + self.v2_5 + self.v2_6) / 15 * 100)
    checkItog_v2_P.short_description = 'Итог раздела 2 %'
    checkItog_v2_P.allow_tags = True

    def checkItog_v3(self):
        return self.v3_1 + self.v3_2 + self.v3_3 + self.v3_4
    checkItog_v3.short_description = 'Итог раздела 3'
    checkItog_v3.allow_tags = True

    def checkItog_v3_P(self):
        return int((self.v3_1 + self.v3_2 + self.v3_3 + self.v3_4) / 14 * 100)
    checkItog_v3_P.short_description = 'Итог раздела 3 %'
    checkItog_v3_P.allow_tags = True

    def checkItog_v4(self):
        return self.v4_1 + self.v4_2 + self.v4_3 + self.v4_4
    checkItog_v4.short_description = 'Итог раздела 4'
    checkItog_v4.allow_tags = True

    def checkItog_v4_P(self):
        return int((self.v4_1 + self.v4_2 + self.v4_3 + self.v4_4) / 8 * 100)
    checkItog_v4_P.short_description = 'Итог раздела 4 %'
    checkItog_v4_P.allow_tags = True

    def checkItog_v5(self):
        return self.v5_1 + self.v5_2 + self.v5_3 + self.v5_4
    checkItog_v5.short_description = 'Итог раздела 5'
    checkItog_v5.allow_tags = True

    def checkItog_v5_P(self):
        return int((self.v5_1 + self.v5_2 + self.v5_3 + self.v5_4) / 16 * 100)
    checkItog_v5_P.short_description = 'Итог раздела 5 %'
    checkItog_v5_P.allow_tags = True

    def checkItog_v6(self):
        return self.v6_1 + self.v6_2 + self.v6_3
    checkItog_v6.short_description = 'Итог раздела 6'
    checkItog_v6.allow_tags = True

    def checkItog_v6_P(self):
        return int((self.v6_1 + self.v6_2 + self.v6_3) / 7 * 100)
    checkItog_v6_P.short_description = 'Итог раздела 6 %'
    checkItog_v6_P.allow_tags = True

    def checkItog_v7(self):
        return self.v7_1 + self.v7_2 + self.v7_3 + self.v7_4
    checkItog_v7.short_description = 'Итог раздела 7'
    checkItog_v7.allow_tags = True

    def checkItog_v7_P(self):
        return int((self.v7_1 + self.v7_2 + self.v7_3 + self.v7_4) / 15 * 100)
    checkItog_v7_P.short_description = 'Итог раздела 7 %'
    checkItog_v7_P.allow_tags = True

    def checkItog_v8(self):
        return self.v8_1 + self.v8_2 + self.v8_3
    checkItog_v8.short_description = 'Итог раздела 8'
    checkItog_v8.allow_tags = True

    def checkItog_v8_P(self):
        return int((self.v8_1 + self.v8_2 + self.v8_3) / 15 * 100)
    checkItog_v8_P.short_description = 'Итог раздела 8 %'
    checkItog_v8_P.allow_tags = True

    def save(self, *args, **kwargs):
        try:
            self.result = self.checkItog()
        except:
            self.result = 0
        super().save(*args, **kwargs)
        
    class Meta:
        db_table = 'checkList_op_kors'
        verbose_name = "Чек лист ОП КорсАвто"
        verbose_name_plural = "Чек листы ОП КорсАвто"

post_save.connect(journal_save_handler, sender=CheckList_op_kors)
post_delete.connect(journal_delete_handler, sender=CheckList_op_kors)