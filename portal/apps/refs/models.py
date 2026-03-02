from email.policy import default
import uuid
import re
from django.db import models
from django.utils.safestring import mark_safe
from ckeditor_uploader.fields import RichTextUploadingField
from django.db.models import Count, Sum, Max, Avg, F, OuterRef, Subquery, Sum, Q, Func, Value, CharField, IntegerField
from django.contrib.auth.models import User, Group
from datetime import datetime, timedelta
from mptt.models import MPTTModel, TreeForeignKey
from django.utils.text import slugify
from django.urls import reverse
import qrcode
import base64
import io
from django.core.files.base import ContentFile
from transliterate import translit
from itertools import chain

'''
Служебные процедуры и функции
'''
def unique_list(l):
    ulist = []
    [ulist.append(x) for x in l if x not in ulist]
    return ulist

def transliterate(name):
   slovar = {'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e',
      'ж':'zh','з':'z','и':'i','й':'i','к':'k','л':'l','м':'m','н':'n',
      'о':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'h',
      'ц':'c','ч':'cz','ш':'sh','щ':'scz','ъ':'','ы':'y','ь':'','э':'e',
      'ю':'u','я':'ja', 'А':'A','Б':'B','В':'V','Г':'G','Д':'D','Е':'E','Ё':'E',
      'Ж':'ZH','З':'Z','И':'I','Й':'I','К':'K','Л':'L','М':'M','Н':'N',
      'О':'O','П':'P','Р':'R','С':'S','Т':'T','У':'U','Ф':'F','Х':'H',
      'Ц':'C','Ч':'CZ','Ш':'SH','Щ':'SCH','Ъ':'','Ы':'y','Ь':'','Э':'E',
      'Ю':'U','Я':'YA',',':'','?':'',' ':'_','~':'','!':'','@':'','#':'',
      '$':'','%':'','^':'','&':'','*':'','(':'',')':'','-':'','=':'','+':'',
      ':':'',';':'','<':'','>':'','\'':'','"':'','\\':'','/':'','№':'',
      '[':'',']':'','{':'','}':'','ґ':'','ї':'', 'є':'','Ґ':'g','Ї':'i',
      'Є':'e', '—':'', '1':'1', '2':'2', '3':'3', '4':'4', '5':'5', '6':'6', '7':'7', '8':'8', '9':'9', '0':'0'}
        
   # Циклически заменяем все буквы в строке
   for key in slovar:
      name = name.replace(key, slovar[key])
   return name

def transliterate_to_rus(name):
   slovar = {'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e',
      'ж':'zh','з':'z','и':'i','й':'i','к':'k','л':'l','м':'m','н':'n',
      'о':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'h',
      'ц':'c','ч':'cz','ш':'sh','щ':'scz','ъ':'','ы':'y','ь':'','э':'e',
      'ю':'u','я':'ja', 'А':'A','Б':'B','В':'V','Г':'G','Д':'D','Е':'E','Ё':'E',
      'Ж':'ZH','З':'Z','И':'I','Й':'I','К':'K','Л':'L','М':'M','Н':'N',
      'О':'O','П':'P','Р':'R','С':'S','Т':'T','У':'U','Ф':'F','Х':'H',
      'Ц':'C','Ч':'CZ','Ш':'SH','Щ':'SCH','Ъ':'','Ы':'y','Ь':'','Э':'E',
      'Ю':'U','Я':'YA',',':'','?':'',' ':'_','~':'','!':'','@':'','#':'',
      '$':'','%':'','^':'','&':'','*':'','(':'',')':'','-':'','=':'','+':'',
      ':':'',';':'','<':'','>':'','\'':'','"':'','\\':'','/':'','№':'',
      '[':'',']':'','{':'','}':'','ґ':'','ї':'', 'є':'','Ґ':'g','Ї':'i',
      'Є':'e', '—':'', '1':'1', '2':'2', '3':'3', '4':'4', '5':'5', '6':'6', '7':'7', '8':'8', '9':'9', '0':'0'}
        
   # Циклически заменяем все буквы в строке
   for key in slovar:
      name = name.replace(slovar[key], key)
   return name

def get_qrcode(name):
    
    slug = 'https://ah.kors-group.com/cars/' + name + '/'

    qr_code_image   = qrcode.make(slug)
    buffer          = io.BytesIO()
    qr_code_image.save(buffer, format="PNG")
    qr_code_image_data = buffer.getvalue()
    
    return qr_code_image_data


# Информационная база 1С
class RefIb(models.Model):
    name    = models.CharField("Наименование", max_length=200, default='')
    server  = models.CharField("Сервер", max_length=200, default='')
    base    = models.CharField("База", max_length=200, default='')
    active  = models.BooleanField("Активна", default=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'RefIb'
        verbose_name = "Информационная база"
        verbose_name_plural = "Информационные базы"


#Область / регион 
class RefArea(models.Model):
    name = models.CharField("Наименование", max_length=200, default='')
   
    def __str__(self):
        return self.name

    class Meta:
        db_table = 'refArea'
        verbose_name = "Область"
        verbose_name_plural = "Области"


#Города 
class RefCity(models.Model):
    name        = models.CharField("Наименование", max_length=200, default='')
    area        = models.ForeignKey(RefArea, null=True, on_delete=models.SET_NULL, verbose_name='Область')
    latitude    = models.FloatField("Широта", default=0.0, blank=True)
    longitude   = models.FloatField("Долгота", default=0.0, blank=True)
    
    def __str__(self):
        return self.name

    class Meta:
        db_table = 'refCity'
        verbose_name = "Город"
        verbose_name_plural = "Города"


#Организации (Фирмы)
class RefOrganization(models.Model):
    name            = models.CharField("Наименование", max_length=250, default='')
    full_name       = models.CharField("Наименование полное", max_length=250, default='')
    phone           = models.CharField("Телефон", max_length=512, default='')
    email           = models.CharField("Email", max_length=200, default='')
    inn             = models.CharField("ИНН", max_length=20, default='')
    kpp             = models.CharField("КПП", max_length=20, default='')
    actual_adress   = models.CharField("Фактический адрес", max_length=200, default='')
    adress          = models.CharField("Юридический адрес", max_length=200, default='')
    active_eco      = models.BooleanField("Доступен для оценки", default=False)

    def phone_normalize(self):
        return "+" + re.sub('[^0-9]', '', self.phone)

    def __str__(self):
        return "{} - {} / {}".format(self.name, self.inn, self.kpp)

    class Meta:
        db_table = 'refOrganization'
        verbose_name = "Организация / фирма"
        verbose_name_plural = "Организации / фирмы"


# Подразделения ДЦ


AVTOHUB_DATA_USAGE_CHOICES = [
    ('ПЦП', 'ПЦП'),
    ('ЦНА', 'ЦНА'),
    ('АвитоОценка', 'АвитоОценка'),
]


class RefUnit(models.Model):
    uin             = models.CharField("uin", max_length=200)
    name            = models.CharField("Наименование", max_length=200, default='')
    name_dop        = models.CharField("Наименование для отображения", max_length=200, blank=True)
    name_search     = models.CharField("Наименование для поиска и фильтров в верхнем регистре", max_length=200, blank=True)
    name_board      = models.CharField("Наименование для доски приветствия", max_length=200, blank=True)
    city            = models.ForeignKey(RefCity, null=True, on_delete=models.SET_NULL, verbose_name='Город')
    main_photo      = models.ImageField(upload_to='logo_unit/', max_length=100, verbose_name="Логотип", blank=True, null=True)
    main_photo_back = models.ImageField(upload_to='back_unit/', max_length=100, verbose_name="Фоновая картинка монитора", blank=True, null=True)
    buauto          = models.BooleanField("Подразделение Б/У Автомобилей", default=False)
    email_service   = models.CharField("Адрес для оповещения о онлайн записи (через ;)", blank=True, default='', max_length=2500)
    board_name      = models.CharField("Наименование монитора приветсвтвия", default='', max_length=200, blank=True)
    adress          = models.CharField("Адрес", default='', max_length=512, blank=True)
    phone           = models.CharField("Телефон", default='', max_length=512, blank=True)
    email           = models.CharField("Email", default='', max_length=512, blank=True)
    webSite         = models.CharField("Веб - сайт", max_length=250, default='', blank=True)
    socialVK        = models.CharField("Ссылка vk.com", max_length=250, default='', blank=True)
    socialYoutube   = models.CharField("Ссылка Youtube", max_length=250, default='', blank=True)
    latitude        = models.FloatField("Широта", default=0.0, blank=True)
    longitude       = models.FloatField("Долгота", default=0.0, blank=True)
    link_ya_map     = models.CharField("Ссылка яндекс карты", max_length=512, default='', blank=True)
    ib              = models.ForeignKey(RefIb, null=True, on_delete=models.SET_NULL, verbose_name='Информационная база')
    mcc             = models.BooleanField("Расширения МКЦ", default=False)
    active_eco      = models.BooleanField("Доступен для оценки", default=False)
    
    eco_staff               = models.ManyToManyField('RefStaff', verbose_name='Сотрудники для оповещения', blank=True)
    eco_units               = models.ManyToManyField('self', verbose_name='Подразделения', blank=True)
    
    ratio_1с_test_price_200    = models.FloatField("ИРЦ Тест прайс 200", default=0.0, blank=True, null=True)
    ratio_1с_test_price_400    = models.FloatField("ИРЦ Тест прайс 400", default=0.0, blank=True, null=True)
    ratio_1с_test_price_700    = models.FloatField("ИРЦ Тест прайс 700", default=0.0, blank=True, null=True)
    ratio_1с_test_price_1200   = models.FloatField("ИРЦ Тест прайс 1200", default=0.0, blank=True, null=True)
    ratio_1с_test_price_2000   = models.FloatField("ИРЦ Тест прайс 2000", default=0.0, blank=True, null=True)
    ratio_1с_test_price_3000   = models.FloatField("ИРЦ Тест прайс 3000", default=0.0, blank=True, null=True)
    ratio_1с_test_price_5000   = models.FloatField("ИРЦ Тест прайс 5000", default=0.0, blank=True, null=True)
    ratio_1с_test_price_5001   = models.FloatField("ИРЦ Тест прайс 5001", default=0.0, blank=True, null=True)

    ratio_1с_rdo_200   = models.FloatField("ИРЦ РДО 200", default=0.0, blank=True, null=True)
    ratio_1с_rdo_400   = models.FloatField("ИРЦ РДО 400", default=0.0, blank=True, null=True)
    ratio_1с_rdo_700   = models.FloatField("ИРЦ РДО 700", default=0.0, blank=True, null=True)
    ratio_1с_rdo_1200  = models.FloatField("ИРЦ РДО 1200", default=0.0, blank=True, null=True)
    ratio_1с_rdo_2000  = models.FloatField("ИРЦ РДО 2000", default=0.0, blank=True, null=True)
    ratio_1с_rdo_3000  = models.FloatField("ИРЦ РДО 3000", default=0.0, blank=True, null=True)
    ratio_1с_rdo_5000  = models.FloatField("ИРЦ РДО 5000", default=0.0, blank=True, null=True)
    ratio_1с_rdo_5001  = models.FloatField("ИРЦ РДО 5001", default=0.0, blank=True, null=True)
    
    ratio_1с_kor_200   = models.FloatField("ИРЦ коррекция 200", default=0.0, blank=True, null=True)
    ratio_1с_kor_400   = models.FloatField("ИРЦ коррекция 400", default=0.0, blank=True, null=True)
    ratio_1с_kor_700   = models.FloatField("ИРЦ коррекция 700", default=0.0, blank=True, null=True)
    ratio_1с_kor_1200  = models.FloatField("ИРЦ коррекция 1200", default=0.0, blank=True, null=True)
    ratio_1с_kor_2000  = models.FloatField("ИРЦ коррекция 2000", default=0.0, blank=True, null=True)
    ratio_1с_kor_3000  = models.FloatField("ИРЦ коррекция 3000", default=0.0, blank=True, null=True)
    ratio_1с_kor_5000  = models.FloatField("ИРЦ коррекция 5000", default=0.0, blank=True, null=True)
    ratio_1с_kor_5001  = models.FloatField("ИРЦ коррекция 5001", default=0.0, blank=True, null=True)

    ratio_1с_txt_200   = models.FloatField("ИРЦ тхт 200", default=0.0, blank=True, null=True)
    ratio_1с_txt_400   = models.FloatField("ИРЦ тхт 400", default=0.0, blank=True, null=True)
    ratio_1с_txt_700   = models.FloatField("ИРЦ тхт 700", default=0.0, blank=True, null=True)
    ratio_1с_txt_1200  = models.FloatField("ИРЦ тхт 1200", default=0.0, blank=True, null=True)
    ratio_1с_txt_2000  = models.FloatField("ИРЦ тхт 2000", default=0.0, blank=True, null=True)
    ratio_1с_txt_3000  = models.FloatField("ИРЦ тхт 3000", default=0.0, blank=True, null=True)
    ratio_1с_txt_5000  = models.FloatField("ИРЦ тхт 5000", default=0.0, blank=True, null=True)
    ratio_1с_txt_5001  = models.FloatField("ИРЦ тхт 5001", default=0.0, blank=True, null=True)

    ratio_avtohub_test_price_200    = models.FloatField("ИРЦ Автохаб Тест прайс 200", default=0.0, blank=True, null=True)
    ratio_avtohub_test_price_400    = models.FloatField("ИРЦ Автохаб Тест прайс 400", default=0.0, blank=True, null=True)
    ratio_avtohub_test_price_700    = models.FloatField("ИРЦ Автохаб Тест прайс 700", default=0.0, blank=True, null=True)
    ratio_avtohub_test_price_1200   = models.FloatField("ИРЦ Автохаб Тест прайс 1200", default=0.0, blank=True, null=True)
    ratio_avtohub_test_price_2000   = models.FloatField("ИРЦ Автохаб Тест прайс 2000", default=0.0, blank=True, null=True)
    ratio_avtohub_test_price_3000   = models.FloatField("ИРЦ Автохаб Тест прайс 3000", default=0.0, blank=True, null=True)
    ratio_avtohub_test_price_5000   = models.FloatField("ИРЦ Автохаб Тест прайс 5000", default=0.0, blank=True, null=True)
    ratio_avtohub_test_price_5001   = models.FloatField("ИРЦ Автохаб Тест прайс 5001", default=0.0, blank=True, null=True)

    ratio_avtohub_rdo_200   = models.FloatField("ИРЦ Автохаб РДО 200", default=0.0, blank=True, null=True)
    ratio_avtohub_rdo_400   = models.FloatField("ИРЦ Автохаб РДО 400", default=0.0, blank=True, null=True)
    ratio_avtohub_rdo_700   = models.FloatField("ИРЦ Автохаб РДО 700", default=0.0, blank=True, null=True)
    ratio_avtohub_rdo_1200  = models.FloatField("ИРЦ Автохаб РДО 1200", default=0.0, blank=True, null=True)
    ratio_avtohub_rdo_2000  = models.FloatField("ИРЦ Автохаб РДО 2000", default=0.0, blank=True, null=True)
    ratio_avtohub_rdo_3000  = models.FloatField("ИРЦ Автохаб РДО 3000", default=0.0, blank=True, null=True)
    ratio_avtohub_rdo_5000  = models.FloatField("ИРЦ Автохаб РДО 5000", default=0.0, blank=True, null=True)
    ratio_avtohub_rdo_5001  = models.FloatField("ИРЦ Автохаб РДО 5001", default=0.0, blank=True, null=True)

    ratio_avtohub_kor_200   = models.FloatField("ИРЦ Автохаб коррекция 200", default=0.0, blank=True, null=True)
    ratio_avtohub_kor_400   = models.FloatField("ИРЦ Автохаб коррекция 400", default=0.0, blank=True, null=True)
    ratio_avtohub_kor_700   = models.FloatField("ИРЦ Автохаб коррекция 700", default=0.0, blank=True, null=True)
    ratio_avtohub_kor_1200  = models.FloatField("ИРЦ Автохаб коррекция 1200", default=0.0, blank=True, null=True)
    ratio_avtohub_kor_2000  = models.FloatField("ИРЦ Автохаб коррекция 2000", default=0.0, blank=True, null=True)
    ratio_avtohub_kor_3000  = models.FloatField("ИРЦ Автохаб коррекция 3000", default=0.0, blank=True, null=True)
    ratio_avtohub_kor_5000  = models.FloatField("ИРЦ Автохаб коррекция 3001", default=0.0, blank=True, null=True)
    ratio_avtohub_kor_5001  = models.FloatField("ИРЦ Автохаб коррекция 3001", default=0.0, blank=True, null=True)

    ratio_avtohub_txt_200   = models.FloatField("ИРЦ Автохаб тхт 200", default=0.0, blank=True, null=True)
    ratio_avtohub_txt_400   = models.FloatField("ИРЦ Автохаб тхт 400", default=0.0, blank=True, null=True)
    ratio_avtohub_txt_700   = models.FloatField("ИРЦ Автохаб тхт 700", default=0.0, blank=True, null=True)
    ratio_avtohub_txt_1200  = models.FloatField("ИРЦ Автохаб тхт 1200", default=0.0, blank=True, null=True)
    ratio_avtohub_txt_2000  = models.FloatField("ИРЦ Автохаб тхт 2000", default=0.0, blank=True, null=True)
    ratio_avtohub_txt_3000  = models.FloatField("ИРЦ Автохаб тхт 3000", default=0.0, blank=True, null=True)
    ratio_avtohub_txt_5000  = models.FloatField("ИРЦ Автохаб тхт 3001", default=0.0, blank=True, null=True)
    ratio_avtohub_txt_5001  = models.FloatField("ИРЦ Автохаб тхт 3001", default=0.0, blank=True, null=True)

    ratio_avtohub_txt_200   = models.FloatField("ИРЦ Автохаб тхт 200", default=0.0, blank=True, null=True)
    ratio_avtohub_txt_400   = models.FloatField("ИРЦ Автохаб тхт 400", default=0.0, blank=True, null=True)
    ratio_avtohub_txt_700   = models.FloatField("ИРЦ Автохаб тхт 700", default=0.0, blank=True, null=True)
    ratio_avtohub_txt_1200  = models.FloatField("ИРЦ Автохаб тхт 1200", default=0.0, blank=True, null=True)
    ratio_avtohub_txt_2000  = models.FloatField("ИРЦ Автохаб тхт 2000", default=0.0, blank=True, null=True)
    ratio_avtohub_txt_3000  = models.FloatField("ИРЦ Автохаб тхт 3000", default=0.0, blank=True, null=True)
    ratio_avtohub_txt_5000  = models.FloatField("ИРЦ Автохаб тхт 3001", default=0.0, blank=True, null=True)
    ratio_avtohub_txt_5001  = models.FloatField("ИРЦ Автохаб тхт 3001", default=0.0, blank=True, null=True)

    percent_txt_200   = models.FloatField("Процент наценки к СС тхт 200", default=0.0, blank=True, null=True)
    percent_txt_400   = models.FloatField("Процент наценки к СС тхт 400", default=0.0, blank=True, null=True)
    percent_txt_700   = models.FloatField("Процент наценки к СС тхт 700", default=0.0, blank=True, null=True)
    percent_txt_1200  = models.FloatField("Процент наценки к СС тхт 1200", default=0.0, blank=True, null=True)
    percent_txt_2000  = models.FloatField("Процент наценки к СС тхт 2000", default=0.0, blank=True, null=True)
    percent_txt_3000  = models.FloatField("Процент наценки к СС тхт 3000", default=0.0, blank=True, null=True)
    percent_txt_5000  = models.FloatField("Процент наценки к СС тхт 3001", default=0.0, blank=True, null=True)
    percent_txt_5001  = models.FloatField("Процент наценки к СС тхт 3001", default=0.0, blank=True, null=True)

    percent_torg_txt_200   = models.FloatField("Процент наценки торг к СС тхт 200", default=0.0, blank=True, null=True)
    percent_torg_txt_400   = models.FloatField("Процент наценки торг к СС тхт 400", default=0.0, blank=True, null=True)
    percent_torg_txt_700   = models.FloatField("Процент наценки торг к СС тхт 700", default=0.0, blank=True, null=True)
    percent_torg_txt_1200  = models.FloatField("Процент наценки торг к СС тхт 1200", default=0.0, blank=True, null=True)
    percent_torg_txt_2000  = models.FloatField("Процент наценки торг к СС тхт 2000", default=0.0, blank=True, null=True)
    percent_torg_txt_3000  = models.FloatField("Процент наценки торг к СС тхт 3000", default=0.0, blank=True, null=True)
    percent_torg_txt_5000  = models.FloatField("Процент наценки торг к СС тхт 3001", default=0.0, blank=True, null=True)
    percent_torg_txt_5001  = models.FloatField("Процент наценки торг к СС тхт 3001", default=0.0, blank=True, null=True)

    discount_tt_200   = models.FloatField("Скидка трейд ин 200", default=0.0, blank=True, null=True)
    discount_tt_400   = models.FloatField("Скидка трейд ин 400", default=0.0, blank=True, null=True)
    discount_tt_700   = models.FloatField("Скидка трейд ин 700", default=0.0, blank=True, null=True)
    discount_tt_1200  = models.FloatField("Скидка трейд ин 1200", default=0.0, blank=True, null=True)
    discount_tt_2000  = models.FloatField("Скидка трейд ин 2000", default=0.0, blank=True, null=True)
    discount_tt_3000  = models.FloatField("Скидка трейд ин 3000", default=0.0, blank=True, null=True)
    discount_tt_5000  = models.FloatField("Скидка трейд ин 3001", default=0.0, blank=True, null=True)
    discount_tt_5001  = models.FloatField("Скидка трейд ин 3001", default=0.0, blank=True, null=True)

    discount_torg_200   = models.FloatField("Скидка торг 200", default=0.0, blank=True, null=True)
    discount_torg_400   = models.FloatField("Скидка торг 400", default=0.0, blank=True, null=True)
    discount_torg_700   = models.FloatField("Скидка торг 700", default=0.0, blank=True, null=True)
    discount_torg_1200  = models.FloatField("Скидка торг 1200", default=0.0, blank=True, null=True)
    discount_torg_2000  = models.FloatField("Скидка торг 2000", default=0.0, blank=True, null=True)
    discount_torg_3000  = models.FloatField("Скидка торг 3000", default=0.0, blank=True, null=True)
    discount_torg_5000  = models.FloatField("Скидка торг 3001", default=0.0, blank=True, null=True)
    discount_torg_5001  = models.FloatField("Скидка торг 3001", default=0.0, blank=True, null=True)

    # -------------------------
    # Настройки автопереоценки КорсАвто по ценовым диапазонам
    # Диапазоны: 200, 400, 700, 1200, 2000, 3000, 5000, 5001
    # -------------------------

    # 200
    auto_strategy_200                       = models.BooleanField("Автостратегия цены 200", default=False)
    auto_active_200                         = models.BooleanField("Активна 200", default=False)
    autohub_mode_kor_200                    = models.CharField("Вариант использования Автохаб Коррекция 200", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    autohub_mode_rdo_200                    = models.CharField("Вариант использования Автохаб РДО 200", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    autohub_mode_test_200                   = models.CharField("Вариант использования Автохаб Тест прайс 200", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    autohub_mode_txt_200                    = models.CharField("Вариант использования Автохаб ТХТ 200", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    eval_type_200                           = models.ForeignKey('RefTypeEvaluationCarsOrganization', null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Выводить в продажу по правилу 200", related_name='+')
    lock_eval_change_after_stage_200        = models.BooleanField("Запрет изменения варианта управления ценой после перехода на новый этап 200", default=False)
    deny_manual_price_200                   = models.BooleanField("Запрет на ручной ввод 200", default=False)
    deny_discount_200                       = models.BooleanField("Запрет скидки 200", default=False)
    correction_kor_200                      = models.FloatField("Корректировка Коррекция 200", default=0.0, blank=True, null=True)
    correction_kor_1c_200                   = models.FloatField("Корректировка Коррекция 1С 200", default=0.0, blank=True, null=True)
    correction_kor_express_200              = models.FloatField("Корректировка Коррекция Экспресс 200", default=0.0, blank=True, null=True)
    correction_rdo_200                      = models.FloatField("Корректировка РДО 200", default=0.0, blank=True, null=True)
    correction_rdo_1c_200                   = models.FloatField("Корректировка РДО 1С 200", default=0.0, blank=True, null=True)
    correction_rdo_express_200              = models.FloatField("Корректировка РДО Экспресс 200", default=0.0, blank=True, null=True)
    correction_test_200                     = models.FloatField("Корректировка Тест прайс 200", default=0.0, blank=True, null=True)
    correction_test_1c_200                  = models.FloatField("Корректировка Тест прайс 1С 200", default=0.0, blank=True, null=True)
    correction_test_express_200             = models.FloatField("Корректировка Тест прайс Экспресс 200", default=0.0, blank=True, null=True)
    correction_txt_200                      = models.FloatField("Корректировка ТХТ 200", default=0.0, blank=True, null=True)
    correction_txt_1c_200                   = models.FloatField("Корректировка ТХТ 1С 200", default=0.0, blank=True, null=True)
    correction_txt_express_200              = models.FloatField("Корректировка ТХТ Экспресс 200", default=0.0, blank=True, null=True)
    max_discount_tradein_200                = models.FloatField("Максимальная скидка за TradeIn 200", default=0.0, blank=True, null=True)
    max_discount_bargain_percent_200        = models.FloatField("Максимальная скидка торг в процентах 200", default=0.0, blank=True, null=True)
    marketing_200                           = models.FloatField("Маркетинг 200", default=0.0, blank=True, null=True)
    no_limit_max_manual_200                 = models.BooleanField("Не ограничивать максимальную ручную цену стратегией 200", default=False)
    reset_manual_prices_200                 = models.BooleanField("Обнуление ручных цен 200", default=False)
    delay_repricing_new_stage_200           = models.BooleanField("Отсрочка переоценки в новом этапе 200", default=False)
    check_price_rule_before_sale_200        = models.BooleanField("Проверка выполнения ценового правила при продаже 200", default=False)
    check_open_tasks_200                    = models.BooleanField("Проверка не закрытых задач 200", default=False)
    markup_base_200                         = models.FloatField("Процент наценки 200", default=0.0, blank=True, null=True)
    markup_kor_200                          = models.FloatField("Процент наценки Коррекция 200", default=0.0, blank=True, null=True)
    markup_rdo_200                          = models.FloatField("Процент наценки РДО 200", default=0.0, blank=True, null=True)
    markup_test_200                         = models.FloatField("Процент наценки Тест прайс 200", default=0.0, blank=True, null=True)
    markup_txt_200                          = models.FloatField("Процент наценки ТХТ 200", default=0.0, blank=True, null=True)
    calc_by_days_in_sale_200                = models.BooleanField("Расчет по дням в продаже 200", default=False)

    # 400
    auto_strategy_400                       = models.BooleanField("Автостратегия цены 400", default=False)
    auto_active_400                         = models.BooleanField("Активна 400", default=False)
    autohub_mode_kor_400                    = models.CharField("Вариант использования Автохаб Коррекция 400", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    autohub_mode_rdo_400                    = models.CharField("Вариант использования Автохаб РДО 400", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    autohub_mode_test_400                   = models.CharField("Вариант использования Автохаб Тест прайс 400", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    autohub_mode_txt_400                    = models.CharField("Вариант использования Автохаб ТХТ 400", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    eval_type_400                           = models.ForeignKey('RefTypeEvaluationCarsOrganization', null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Выводить в продажу по правилу 400", related_name='+')
    lock_eval_change_after_stage_400        = models.BooleanField("Запрет изменения варианта управления ценой после перехода на новый этап 400", default=False)
    deny_manual_price_400                   = models.BooleanField("Запрет на ручной ввод 400", default=False)
    deny_discount_400                       = models.BooleanField("Запрет скидки 400", default=False)
    correction_kor_400                      = models.FloatField("Корректировка Коррекция 400", default=0.0, blank=True, null=True)
    correction_kor_1c_400                   = models.FloatField("Корректировка Коррекция 1С 400", default=0.0, blank=True, null=True)
    correction_kor_express_400              = models.FloatField("Корректировка Коррекция Экспресс 400", default=0.0, blank=True, null=True)
    correction_rdo_400                      = models.FloatField("Корректировка РДО 400", default=0.0, blank=True, null=True)
    correction_rdo_1c_400                   = models.FloatField("Корректировка РДО 1С 400", default=0.0, blank=True, null=True)
    correction_rdo_express_400              = models.FloatField("Корректировка РДО Экспресс 400", default=0.0, blank=True, null=True)
    correction_test_400                     = models.FloatField("Корректировка Тест прайс 400", default=0.0, blank=True, null=True)
    correction_test_1c_400                  = models.FloatField("Корректировка Тест прайс 1С 400", default=0.0, blank=True, null=True)
    correction_test_express_400             = models.FloatField("Корректировка Тест прайс Экспресс 400", default=0.0, blank=True, null=True)
    correction_txt_400                      = models.FloatField("Корректировка ТХТ 400", default=0.0, blank=True, null=True)
    correction_txt_1c_400                   = models.FloatField("Корректировка ТХТ 1С 400", default=0.0, blank=True, null=True)
    correction_txt_express_400              = models.FloatField("Корректировка ТХТ Экспресс 400", default=0.0, blank=True, null=True)
    max_discount_tradein_400                = models.FloatField("Максимальная скидка за TradeIn 400", default=0.0, blank=True, null=True)
    max_discount_bargain_percent_400        = models.FloatField("Максимальная скидка торг в процентах 400", default=0.0, blank=True, null=True)
    marketing_400                           = models.FloatField("Маркетинг 400", default=0.0, blank=True, null=True)
    no_limit_max_manual_400                 = models.BooleanField("Не ограничивать максимальную ручную цену стратегией 400", default=False)
    reset_manual_prices_400                 = models.BooleanField("Обнуление ручных цен 400", default=False)
    delay_repricing_new_stage_400           = models.BooleanField("Отсрочка переоценки в новом этапе 400", default=False)
    check_price_rule_before_sale_400        = models.BooleanField("Проверка выполнения ценового правила при продаже 400", default=False)
    check_open_tasks_400                    = models.BooleanField("Проверка не закрытых задач 400", default=False)
    markup_base_400                         = models.FloatField("Процент наценки 400", default=0.0, blank=True, null=True)
    markup_kor_400                          = models.FloatField("Процент наценки Коррекция 400", default=0.0, blank=True, null=True)
    markup_rdo_400                          = models.FloatField("Процент наценки РДО 400", default=0.0, blank=True, null=True)
    markup_test_400                         = models.FloatField("Процент наценки Тест прайс 400", default=0.0, blank=True, null=True)
    markup_txt_400                          = models.FloatField("Процент наценки ТХТ 400", default=0.0, blank=True, null=True)
    calc_by_days_in_sale_400                = models.BooleanField("Расчет по дням в продаже 400", default=False)

    # 700
    auto_strategy_700                       = models.BooleanField("Автостратегия цены 700", default=False)
    auto_active_700                         = models.BooleanField("Активна 700", default=False)
    autohub_mode_kor_700                    = models.CharField("Вариант использования Автохаб Коррекция 700", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    autohub_mode_rdo_700                    = models.CharField("Вариант использования Автохаб РДО 700", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    autohub_mode_test_700                   = models.CharField("Вариант использования Автохаб Тест прайс 700", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    autohub_mode_txt_700                    = models.CharField("Вариант использования Автохаб ТХТ 700", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    eval_type_700                           = models.ForeignKey('RefTypeEvaluationCarsOrganization', null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Выводить в продажу по правилу 700", related_name='+')
    lock_eval_change_after_stage_700        = models.BooleanField("Запрет изменения варианта управления ценой после перехода на новый этап 700", default=False)
    deny_manual_price_700                   = models.BooleanField("Запрет на ручной ввод 700", default=False)
    deny_discount_700                       = models.BooleanField("Запрет скидки 700", default=False)
    correction_kor_700                      = models.FloatField("Корректировка Коррекция 700", default=0.0, blank=True, null=True)
    correction_kor_1c_700                   = models.FloatField("Корректировка Коррекция 1С 700", default=0.0, blank=True, null=True)
    correction_kor_express_700              = models.FloatField("Корректировка Коррекция Экспресс 700", default=0.0, blank=True, null=True)
    correction_rdo_700                      = models.FloatField("Корректировка РДО 700", default=0.0, blank=True, null=True)
    correction_rdo_1c_700                   = models.FloatField("Корректировка РДО 1С 700", default=0.0, blank=True, null=True)
    correction_rdo_express_700              = models.FloatField("Корректировка РДО Экспресс 700", default=0.0, blank=True, null=True)
    correction_test_700                     = models.FloatField("Корректировка Тест прайс 700", default=0.0, blank=True, null=True)
    correction_test_1c_700                  = models.FloatField("Корректировка Тест прайс 1С 700", default=0.0, blank=True, null=True)
    correction_test_express_700             = models.FloatField("Корректировка Тест прайс Экспресс 700", default=0.0, blank=True, null=True)
    correction_txt_700                      = models.FloatField("Корректировка ТХТ 700", default=0.0, blank=True, null=True)
    correction_txt_1c_700                   = models.FloatField("Корректировка ТХТ 1С 700", default=0.0, blank=True, null=True)
    correction_txt_express_700              = models.FloatField("Корректировка ТХТ Экспресс 700", default=0.0, blank=True, null=True)
    max_discount_tradein_700                = models.FloatField("Максимальная скидка за TradeIn 700", default=0.0, blank=True, null=True)
    max_discount_bargain_percent_700        = models.FloatField("Максимальная скидка торг в процентах 700", default=0.0, blank=True, null=True)
    marketing_700                           = models.FloatField("Маркетинг 700", default=0.0, blank=True, null=True)
    no_limit_max_manual_700                 = models.BooleanField("Не ограничивать максимальную ручную цену стратегией 700", default=False)
    reset_manual_prices_700                 = models.BooleanField("Обнуление ручных цен 700", default=False)
    delay_repricing_new_stage_700           = models.BooleanField("Отсрочка переоценки в новом этапе 700", default=False)
    check_price_rule_before_sale_700        = models.BooleanField("Проверка выполнения ценового правила при продаже 700", default=False)
    check_open_tasks_700                    = models.BooleanField("Проверка не закрытых задач 700", default=False)
    markup_base_700                         = models.FloatField("Процент наценки 700", default=0.0, blank=True, null=True)
    markup_kor_700                          = models.FloatField("Процент наценки Коррекция 700", default=0.0, blank=True, null=True)
    markup_rdo_700                          = models.FloatField("Процент наценки РДО 700", default=0.0, blank=True, null=True)
    markup_test_700                         = models.FloatField("Процент наценки Тест прайс 700", default=0.0, blank=True, null=True)
    markup_txt_700                          = models.FloatField("Процент наценки ТХТ 700", default=0.0, blank=True, null=True)
    calc_by_days_in_sale_700                = models.BooleanField("Расчет по дням в продаже 700", default=False)

    # 1200
    auto_strategy_1200                      = models.BooleanField("Автостратегия цены 1200", default=False)
    auto_active_1200                        = models.BooleanField("Активна 1200", default=False)
    autohub_mode_kor_1200                   = models.CharField("Вариант использования Автохаб Коррекция 1200", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    autohub_mode_rdo_1200                   = models.CharField("Вариант использования Автохаб РДО 1200", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    autohub_mode_test_1200                  = models.CharField("Вариант использования Автохаб Тест прайс 1200", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    autohub_mode_txt_1200                   = models.CharField("Вариант использования Автохаб ТХТ 1200", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    eval_type_1200                          = models.ForeignKey('RefTypeEvaluationCarsOrganization', null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Выводить в продажу по правилу 1200", related_name='+')
    lock_eval_change_after_stage_1200       = models.BooleanField("Запрет изменения варианта управления ценой после перехода на новый этап 1200", default=False)
    deny_manual_price_1200                  = models.BooleanField("Запрет на ручной ввод 1200", default=False)
    deny_discount_1200                      = models.BooleanField("Запрет скидки 1200", default=False)
    correction_kor_1200                     = models.FloatField("Корректировка Коррекция 1200", default=0.0, blank=True, null=True)
    correction_kor_1c_1200                  = models.FloatField("Корректировка Коррекция 1С 1200", default=0.0, blank=True, null=True)
    correction_kor_express_1200             = models.FloatField("Корректировка Коррекция Экспресс 1200", default=0.0, blank=True, null=True)
    correction_rdo_1200                     = models.FloatField("Корректировка РДО 1200", default=0.0, blank=True, null=True)
    correction_rdo_1c_1200                  = models.FloatField("Корректировка РДО 1С 1200", default=0.0, blank=True, null=True)
    correction_rdo_express_1200             = models.FloatField("Корректировка РДО Экспресс 1200", default=0.0, blank=True, null=True)
    correction_test_1200                    = models.FloatField("Корректировка Тест прайс 1200", default=0.0, blank=True, null=True)
    correction_test_1c_1200                 = models.FloatField("Корректировка Тест прайс 1С 1200", default=0.0, blank=True, null=True)
    correction_test_express_1200            = models.FloatField("Корректировка Тест прайс Экспресс 1200", default=0.0, blank=True, null=True)
    correction_txt_1200                     = models.FloatField("Корректировка ТХТ 1200", default=0.0, blank=True, null=True)
    correction_txt_1c_1200                  = models.FloatField("Корректировка ТХТ 1С 1200", default=0.0, blank=True, null=True)
    correction_txt_express_1200             = models.FloatField("Корректировка ТХТ Экспресс 1200", default=0.0, blank=True, null=True)
    max_discount_tradein_1200               = models.FloatField("Максимальная скидка за TradeIn 1200", default=0.0, blank=True, null=True)
    max_discount_bargain_percent_1200       = models.FloatField("Максимальная скидка торг в процентах 1200", default=0.0, blank=True, null=True)
    marketing_1200                          = models.FloatField("Маркетинг 1200", default=0.0, blank=True, null=True)
    no_limit_max_manual_1200                = models.BooleanField("Не ограничивать максимальную ручную цену стратегией 1200", default=False)
    reset_manual_prices_1200                = models.BooleanField("Обнуление ручных цен 1200", default=False)
    delay_repricing_new_stage_1200          = models.BooleanField("Отсрочка переоценки в новом этапе 1200", default=False)
    check_price_rule_before_sale_1200       = models.BooleanField("Проверка выполнения ценового правила при продаже 1200", default=False)
    check_open_tasks_1200                   = models.BooleanField("Проверка не закрытых задач 1200", default=False)
    markup_base_1200                        = models.FloatField("Процент наценки 1200", default=0.0, blank=True, null=True)
    markup_kor_1200                         = models.FloatField("Процент наценки Коррекция 1200", default=0.0, blank=True, null=True)
    markup_rdo_1200                         = models.FloatField("Процент наценки РДО 1200", default=0.0, blank=True, null=True)
    markup_test_1200                        = models.FloatField("Процент наценки Тест прайс 1200", default=0.0, blank=True, null=True)
    markup_txt_1200                         = models.FloatField("Процент наценки ТХТ 1200", default=0.0, blank=True, null=True)
    calc_by_days_in_sale_1200               = models.BooleanField("Расчет по дням в продаже 1200", default=False)

    # 2000
    auto_strategy_2000                      = models.BooleanField("Автостратегия цены 2000", default=False)
    auto_active_2000                        = models.BooleanField("Активна 2000", default=False)
    autohub_mode_kor_2000                   = models.CharField("Вариант использования Автохаб Коррекция 2000", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    autohub_mode_rdo_2000                   = models.CharField("Вариант использования Автохаб РДО 2000", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    autohub_mode_test_2000                  = models.CharField("Вариант использования Автохаб Тест прайс 2000", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    autohub_mode_txt_2000                   = models.CharField("Вариант использования Автохаб ТХТ 2000", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    eval_type_2000                          = models.ForeignKey('RefTypeEvaluationCarsOrganization', null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Выводить в продажу по правилу 2000", related_name='+')
    lock_eval_change_after_stage_2000       = models.BooleanField("Запрет изменения варианта управления ценой после перехода на новый этап 2000", default=False)
    deny_manual_price_2000                  = models.BooleanField("Запрет на ручной ввод 2000", default=False)
    deny_discount_2000                      = models.BooleanField("Запрет скидки 2000", default=False)
    correction_kor_2000                     = models.FloatField("Корректировка Коррекция 2000", default=0.0, blank=True, null=True)
    correction_kor_1c_2000                  = models.FloatField("Корректировка Коррекция 1С 2000", default=0.0, blank=True, null=True)
    correction_kor_express_2000             = models.FloatField("Корректировка Коррекция Экспресс 2000", default=0.0, blank=True, null=True)
    correction_rdo_2000                     = models.FloatField("Корректировка РДО 2000", default=0.0, blank=True, null=True)
    correction_rdo_1c_2000                  = models.FloatField("Корректировка РДО 1С 2000", default=0.0, blank=True, null=True)
    correction_rdo_express_2000             = models.FloatField("Корректировка РДО Экспресс 2000", default=0.0, blank=True, null=True)
    correction_test_2000                    = models.FloatField("Корректировка Тест прайс 2000", default=0.0, blank=True, null=True)
    correction_test_1c_2000                 = models.FloatField("Корректировка Тест прайс 1С 2000", default=0.0, blank=True, null=True)
    correction_test_express_2000            = models.FloatField("Корректировка Тест прайс Экспресс 2000", default=0.0, blank=True, null=True)
    correction_txt_2000                     = models.FloatField("Корректировка ТХТ 2000", default=0.0, blank=True, null=True)
    correction_txt_1c_2000                  = models.FloatField("Корректировка ТХТ 1С 2000", default=0.0, blank=True, null=True)
    correction_txt_express_2000             = models.FloatField("Корректировка ТХТ Экспресс 2000", default=0.0, blank=True, null=True)
    max_discount_tradein_2000               = models.FloatField("Максимальная скидка за TradeIn 2000", default=0.0, blank=True, null=True)
    max_discount_bargain_percent_2000       = models.FloatField("Максимальная скидка торг в процентах 2000", default=0.0, blank=True, null=True)
    marketing_2000                          = models.FloatField("Маркетинг 2000", default=0.0, blank=True, null=True)
    no_limit_max_manual_2000                = models.BooleanField("Не ограничивать максимальную ручную цену стратегией 2000", default=False)
    reset_manual_prices_2000                = models.BooleanField("Обнуление ручных цен 2000", default=False)
    delay_repricing_new_stage_2000          = models.BooleanField("Отсрочка переоценки в новом этапе 2000", default=False)
    check_price_rule_before_sale_2000       = models.BooleanField("Проверка выполнения ценового правила при продаже 2000", default=False)
    check_open_tasks_2000                   = models.BooleanField("Проверка не закрытых задач 2000", default=False)
    markup_base_2000                        = models.FloatField("Процент наценки 2000", default=0.0, blank=True, null=True)
    markup_kor_2000                         = models.FloatField("Процент наценки Коррекция 2000", default=0.0, blank=True, null=True)
    markup_rdo_2000                         = models.FloatField("Процент наценки РДО 2000", default=0.0, blank=True, null=True)
    markup_test_2000                        = models.FloatField("Процент наценки Тест прайс 2000", default=0.0, blank=True, null=True)
    markup_txt_2000                         = models.FloatField("Процент наценки ТХТ 2000", default=0.0, blank=True, null=True)
    calc_by_days_in_sale_2000               = models.BooleanField("Расчет по дням в продаже 2000", default=False)

    # 3000
    auto_strategy_3000                      = models.BooleanField("Автостратегия цены 3000", default=False)
    auto_active_3000                        = models.BooleanField("Активна 3000", default=False)
    autohub_mode_kor_3000                   = models.CharField("Вариант использования Автохаб Коррекция 3000", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    autohub_mode_rdo_3000                   = models.CharField("Вариант использования Автохаб РДО 3000", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    autohub_mode_test_3000                  = models.CharField("Вариант использования Автохаб Тест прайс 3000", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    autohub_mode_txt_3000                   = models.CharField("Вариант использования Автохаб ТХТ 3000", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    eval_type_3000                          = models.ForeignKey('RefTypeEvaluationCarsOrganization', null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Выводить в продажу по правилу 3000", related_name='+')
    lock_eval_change_after_stage_3000       = models.BooleanField("Запрет изменения варианта управления ценой после перехода на новый этап 3000", default=False)
    deny_manual_price_3000                  = models.BooleanField("Запрет на ручной ввод 3000", default=False)
    deny_discount_3000                      = models.BooleanField("Запрет скидки 3000", default=False)
    correction_kor_3000                     = models.FloatField("Корректировка Коррекция 3000", default=0.0, blank=True, null=True)
    correction_kor_1c_3000                  = models.FloatField("Корректировка Коррекция 1С 3000", default=0.0, blank=True, null=True)
    correction_kor_express_3000             = models.FloatField("Корректировка Коррекция Экспресс 3000", default=0.0, blank=True, null=True)
    correction_rdo_3000                     = models.FloatField("Корректировка РДО 3000", default=0.0, blank=True, null=True)
    correction_rdo_1c_3000                  = models.FloatField("Корректировка РДО 1С 3000", default=0.0, blank=True, null=True)
    correction_rdo_express_3000             = models.FloatField("Корректировка РДО Экспресс 3000", default=0.0, blank=True, null=True)
    correction_test_3000                    = models.FloatField("Корректировка Тест прайс 3000", default=0.0, blank=True, null=True)
    correction_test_1c_3000                 = models.FloatField("Корректировка Тест прайс 1С 3000", default=0.0, blank=True, null=True)
    correction_test_express_3000            = models.FloatField("Корректировка Тест прайс Экспресс 3000", default=0.0, blank=True, null=True)
    correction_txt_3000                     = models.FloatField("Корректировка ТХТ 3000", default=0.0, blank=True, null=True)
    correction_txt_1c_3000                  = models.FloatField("Корректировка ТХТ 1С 3000", default=0.0, blank=True, null=True)
    correction_txt_express_3000             = models.FloatField("Корректировка ТХТ Экспресс 3000", default=0.0, blank=True, null=True)
    max_discount_tradein_3000               = models.FloatField("Максимальная скидка за TradeIn 3000", default=0.0, blank=True, null=True)
    max_discount_bargain_percent_3000       = models.FloatField("Максимальная скидка торг в процентах 3000", default=0.0, blank=True, null=True)
    marketing_3000                          = models.FloatField("Маркетинг 3000", default=0.0, blank=True, null=True)
    no_limit_max_manual_3000                = models.BooleanField("Не ограничивать максимальную ручную цену стратегией 3000", default=False)
    reset_manual_prices_3000                = models.BooleanField("Обнуление ручных цен 3000", default=False)
    delay_repricing_new_stage_3000          = models.BooleanField("Отсрочка переоценки в новом этапе 3000", default=False)
    check_price_rule_before_sale_3000       = models.BooleanField("Проверка выполнения ценового правила при продаже 3000", default=False)
    check_open_tasks_3000                   = models.BooleanField("Проверка не закрытых задач 3000", default=False)
    markup_base_3000                        = models.FloatField("Процент наценки 3000", default=0.0, blank=True, null=True)
    markup_kor_3000                         = models.FloatField("Процент наценки Коррекция 3000", default=0.0, blank=True, null=True)
    markup_rdo_3000                         = models.FloatField("Процент наценки РДО 3000", default=0.0, blank=True, null=True)
    markup_test_3000                        = models.FloatField("Процент наценки Тест прайс 3000", default=0.0, blank=True, null=True)
    markup_txt_3000                         = models.FloatField("Процент наценки ТХТ 3000", default=0.0, blank=True, null=True)
    calc_by_days_in_sale_3000               = models.BooleanField("Расчет по дням в продаже 3000", default=False)

    # 5000
    auto_strategy_5000                      = models.BooleanField("Автостратегия цены 5000", default=False)
    auto_active_5000                        = models.BooleanField("Активна 5000", default=False)
    autohub_mode_kor_5000                   = models.CharField("Вариант использования Автохаб Коррекция 5000", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    autohub_mode_rdo_5000                   = models.CharField("Вариант использования Автохаб РДО 5000", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    autohub_mode_test_5000                  = models.CharField("Вариант использования Автохаб Тест прайс 5000", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    autohub_mode_txt_5000                   = models.CharField("Вариант использования Автохаб ТХТ 5000", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    eval_type_5000                          = models.ForeignKey('RefTypeEvaluationCarsOrganization', null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Выводить в продажу по правилу 5000", related_name='+')
    lock_eval_change_after_stage_5000       = models.BooleanField("Запрет изменения варианта управления ценой после перехода на новый этап 5000", default=False)
    deny_manual_price_5000                  = models.BooleanField("Запрет на ручной ввод 5000", default=False)
    deny_discount_5000                      = models.BooleanField("Запрет скидки 5000", default=False)
    correction_kor_5000                     = models.FloatField("Корректировка Коррекция 5000", default=0.0, blank=True, null=True)
    correction_kor_1c_5000                  = models.FloatField("Корректировка Коррекция 1С 5000", default=0.0, blank=True, null=True)
    correction_kor_express_5000             = models.FloatField("Корректировка Коррекция Экспресс 5000", default=0.0, blank=True, null=True)
    correction_rdo_5000                     = models.FloatField("Корректировка РДО 5000", default=0.0, blank=True, null=True)
    correction_rdo_1c_5000                  = models.FloatField("Корректировка РДО 1С 5000", default=0.0, blank=True, null=True)
    correction_rdo_express_5000             = models.FloatField("Корректировка РДО Экспресс 5000", default=0.0, blank=True, null=True)
    correction_test_5000                    = models.FloatField("Корректировка Тест прайс 5000", default=0.0, blank=True, null=True)
    correction_test_1c_5000                 = models.FloatField("Корректировка Тест прайс 1С 5000", default=0.0, blank=True, null=True)
    correction_test_express_5000            = models.FloatField("Корректировка Тест прайс Экспресс 5000", default=0.0, blank=True, null=True)
    correction_txt_5000                     = models.FloatField("Корректировка ТХТ 5000", default=0.0, blank=True, null=True)
    correction_txt_1c_5000                  = models.FloatField("Корректировка ТХТ 1С 5000", default=0.0, blank=True, null=True)
    correction_txt_express_5000             = models.FloatField("Корректировка ТХТ Экспресс 5000", default=0.0, blank=True, null=True)
    max_discount_tradein_5000               = models.FloatField("Максимальная скидка за TradeIn 5000", default=0.0, blank=True, null=True)
    max_discount_bargain_percent_5000       = models.FloatField("Максимальная скидка торг в процентах 5000", default=0.0, blank=True, null=True)
    marketing_5000                          = models.FloatField("Маркетинг 5000", default=0.0, blank=True, null=True)
    no_limit_max_manual_5000                = models.BooleanField("Не ограничивать максимальную ручную цену стратегией 5000", default=False)
    reset_manual_prices_5000                = models.BooleanField("Обнуление ручных цен 5000", default=False)
    delay_repricing_new_stage_5000          = models.BooleanField("Отсрочка переоценки в новом этапе 5000", default=False)
    check_price_rule_before_sale_5000       = models.BooleanField("Проверка выполнения ценового правила при продаже 5000", default=False)
    check_open_tasks_5000                   = models.BooleanField("Проверка не закрытых задач 5000", default=False)
    markup_base_5000                        = models.FloatField("Процент наценки 5000", default=0.0, blank=True, null=True)
    markup_kor_5000                         = models.FloatField("Процент наценки Коррекция 5000", default=0.0, blank=True, null=True)
    markup_rdo_5000                         = models.FloatField("Процент наценки РДО 5000", default=0.0, blank=True, null=True)
    markup_test_5000                        = models.FloatField("Процент наценки Тест прайс 5000", default=0.0, blank=True, null=True)
    markup_txt_5000                         = models.FloatField("Процент наценки ТХТ 5000", default=0.0, blank=True, null=True)
    calc_by_days_in_sale_5000               = models.BooleanField("Расчет по дням в продаже 5000", default=False)

    # 5001+
    auto_strategy_5001                      = models.BooleanField("Автостратегия цены 5001+", default=False)
    auto_active_5001                        = models.BooleanField("Активна 5001+", default=False)
    autohub_mode_kor_5001                   = models.CharField("Вариант использования Автохаб Коррекция 5001+", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    autohub_mode_rdo_5001                   = models.CharField("Вариант использования Автохаб РДО 5001+", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    autohub_mode_test_5001                  = models.CharField("Вариант использования Автохаб Тест прайс 5001+", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    autohub_mode_txt_5001                   = models.CharField("Вариант использования Автохаб ТХТ 5001+", max_length=20, choices=AVTOHUB_DATA_USAGE_CHOICES, blank=True, default='')
    eval_type_5001                          = models.ForeignKey('RefTypeEvaluationCarsOrganization', null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Выводить в продажу по правилу 5001+", related_name='+')
    lock_eval_change_after_stage_5001       = models.BooleanField("Запрет изменения варианта управления ценой после перехода на новый этап 5001+", default=False)
    deny_manual_price_5001                  = models.BooleanField("Запрет на ручной ввод 5001+", default=False)
    deny_discount_5001                      = models.BooleanField("Запрет скидки 5001+", default=False)
    correction_kor_5001                     = models.FloatField("Корректировка Коррекция 5001+", default=0.0, blank=True, null=True)
    correction_kor_1c_5001                  = models.FloatField("Корректировка Коррекция 1С 5001+", default=0.0, blank=True, null=True)
    correction_kor_express_5001             = models.FloatField("Корректировка Коррекция Экспресс 5001+", default=0.0, blank=True, null=True)
    correction_rdo_5001                     = models.FloatField("Корректировка РДО 5001+", default=0.0, blank=True, null=True)
    correction_rdo_1c_5001                  = models.FloatField("Корректировка РДО 1С 5001+", default=0.0, blank=True, null=True)
    correction_rdo_express_5001             = models.FloatField("Корректировка РДО Экспресс 5001+", default=0.0, blank=True, null=True)
    correction_test_5001                    = models.FloatField("Корректировка Тест прайс 5001+", default=0.0, blank=True, null=True)
    correction_test_1c_5001                 = models.FloatField("Корректировка Тест прайс 1С 5001+", default=0.0, blank=True, null=True)
    correction_test_express_5001            = models.FloatField("Корректировка Тест прайс Экспресс 5001+", default=0.0, blank=True, null=True)
    correction_txt_5001                     = models.FloatField("Корректировка ТХТ 5001+", default=0.0, blank=True, null=True)
    correction_txt_1c_5001                  = models.FloatField("Корректировка ТХТ 1С 5001+", default=0.0, blank=True, null=True)
    correction_txt_express_5001             = models.FloatField("Корректировка ТХТ Экспресс 5001+", default=0.0, blank=True, null=True)
    max_discount_tradein_5001               = models.FloatField("Максимальная скидка за TradeIn 5001+", default=0.0, blank=True, null=True)
    max_discount_bargain_percent_5001       = models.FloatField("Максимальная скидка торг в процентах 5001+", default=0.0, blank=True, null=True)
    marketing_5001                          = models.FloatField("Маркетинг 5001+", default=0.0, blank=True, null=True)
    no_limit_max_manual_5001                = models.BooleanField("Не ограничивать максимальную ручную цену стратегией 5001+", default=False)
    reset_manual_prices_5001                = models.BooleanField("Обнуление ручных цен 5001+", default=False)
    delay_repricing_new_stage_5001          = models.BooleanField("Отсрочка переоценки в новом этапе 5001+", default=False)
    check_price_rule_before_sale_5001       = models.BooleanField("Проверка выполнения ценового правила при продаже 5001+", default=False)
    check_open_tasks_5001                   = models.BooleanField("Проверка не закрытых задач 5001+", default=False)
    markup_base_5001                        = models.FloatField("Процент наценки 5001+", default=0.0, blank=True, null=True)
    markup_kor_5001                         = models.FloatField("Процент наценки Коррекция 5001+", default=0.0, blank=True, null=True)
    markup_rdo_5001                         = models.FloatField("Процент наценки РДО 5001+", default=0.0, blank=True, null=True)
    markup_test_5001                        = models.FloatField("Процент наценки Тест прайс 5001+", default=0.0, blank=True, null=True)
    markup_txt_5001                         = models.FloatField("Процент наценки ТХТ 5001+", default=0.0, blank=True, null=True)
    calc_by_days_in_sale_5001               = models.BooleanField("Расчет по дням в продаже 5001+", default=False)

    def name_web(self):
        return mark_safe(self.name.replace('КорсАвто','КорсАвто<br>'))

    def image_img(self):
        if self.main_photo:
            return mark_safe('<div style=" width:240px; height:120px;text-align:center;" ><img style="object-fit: scale-down;min-width:240px;max-width:240px;max-height: 120px;" src="{0}"/></div>'.format(self.main_photo.url))
        else: 
            return mark_safe('<div style=" width:240px; height:120px;text-align:center;" ><img style="max-width:100%;max-height: 100%;" src="/static/media/kg.jpg"/></div>')
    image_img.short_description = 'Логотип'
    image_img.allow_tags = True

    def phone_normalize(self):
        return "+" + re.sub('[^0-9]', '', self.phone)

    def balance_detail(self):
        from register.models import RegEstimationBalanceUnit
        request = RegEstimationBalanceUnit.objects.filter(unit = self).order_by('-date')
        return request

    def balance(self):
        from register.models import RegEstimationBalanceUnit
        request = RegEstimationBalanceUnit.objects.filter(unit = self).aggregate(Sum('amount'))
        if request['amount__sum'] == None:
             return 0
        return request['amount__sum']
    
    def balance_top_unit(self):
        from register.models import RegEstimationBalanceUnit
        
        request = RegEstimationBalanceUnit.objects.values('unit').order_by('unit').distinct().annotate(sum = Sum('amount')).values('unit','sum' , ).order_by('-sum')
        
        all_count = RegEstimationBalanceUnit.objects.all().order_by('unit').distinct('unit').count()
        
        position = 0
        for uni in request:
            position = position + 1
            if self.pk == uni['unit']:
                break
             
        info = {
            'position'  : position,
            'all'       : all_count,
            'name'      : '' + str(position) + ' / ' + str(all_count)
        }
        return info

    def save(self, *args, **kwargs):
        self.name_search = self.name.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        bu = 'Новые - '
        if self.buauto:
            bu = 'Б/У - '    
        return "{} {} - {} - {}".format(bu, self.name, self.city, self.ib)

    class Meta:
        indexes = [
            models.Index(fields=['uin'])
        ]
        db_table = 'refUnit'
        verbose_name = "Подразделение"
        verbose_name_plural = "Подразделения"


#Организации (Фирмы)
class RefFilial(models.Model):
    uin             = models.CharField("uin", max_length=200, default='')
    name            = models.CharField("Наименование", max_length=250, default='')
    organization    = models.ForeignKey(RefOrganization, null=True, on_delete=models.SET_NULL, verbose_name='Организация')
    active_eco      = models.BooleanField("Доступен для оценки", default=False)
    unit            = models.ForeignKey(RefUnit, null=True, on_delete=models.SET_NULL, verbose_name='Подразделение')

    def __str__(self):
        return "{} - {} / {}".format(self.name, self.active_eco, self.organization)

    class Meta:
        db_table = 'refFilial'
        verbose_name = "Филиал"
        verbose_name_plural = "Филиалы"


# Группы подразделений
class RefUnitGroup(models.Model):
    name        = models.CharField("Наименование", default='', max_length=300, blank=True)
    name_bi     = models.CharField("Наименование bi", default='', max_length=300, blank=True)
    units       = models.ManyToManyField(RefUnit, verbose_name='Подразделения', blank=True)
    comment     = models.CharField("Комментарий", default='', max_length=300, blank=True)
    active      = models.BooleanField("Активно", default=False)
    bu_auto     = models.BooleanField("Б/У Автомобили", default=False)
    city        = models.ForeignKey(RefCity, null=True, on_delete=models.SET_NULL, verbose_name='Город')

    def get_info_units(self):
        units_names = ''
        units = self.units.all().order_by('name')
        for unit in units:
            name = unit.name
            if units_names.find(name) < 0:
                units_names = units_names + ' | ' + name
        return units_names   

    def __str__(self):
        return "{} ({})".format(self.name, self.name_bi)

    class Meta:
        db_table = 'refUnitGroup'
        verbose_name = "Группa подразделений"
        verbose_name_plural = "Группы подразделений"


# Сотрудники
class RefStaff(models.Model):
    uin             = models.CharField("uin", max_length=200, default='')
    name            = models.CharField("Наименование", max_length=300, default='')
    main_photo      = models.ImageField(upload_to='logo/', max_length=100, verbose_name="Фотография", blank=True, null=True)
    units           = models.ManyToManyField(RefUnit, verbose_name='Подразделения', related_name='units', blank=True)
    domain_login    = models.CharField('Доменный логин', default='', null=True, max_length=150, blank=True) 
    status          = models.CharField("Статус", max_length=200, default='', blank=True)
    phone           = models.CharField("Номер телефона", max_length=200, default='', blank=True)
    post            = models.CharField("Должность", max_length=200, default='', blank=True)
    no_monitors     = models.BooleanField("Не выводить на монитор", default=False)
    buauto          = models.BooleanField("База бу автомобилей", default=False)
    
    def image_img(self):
        if self.main_photo:
            return mark_safe('<img style="object-fit: scale-down;min-width:240px;max-width:240px;max-height: 120px;" src="{0}"/>'.format(self.main_photo.url))
        else: 
            return mark_safe('<div style="width:240px; height:120px;text-align:center;" ><img style="max-width:100%;max-height: 100%;" src="/static/media/no_image.png"/></div>')
    image_img.short_description = 'Фотография'
    image_img.allow_tags = True
    
    def image_img_url(self):
        if self.main_photo:
            return self.main_photo.url
        else: 
            return "/static/media/no_image.png"
    image_img_url.short_description = 'Фотография урл'
    image_img_url.allow_tags = True

    def image_img_haval(self):
        if self.main_photo:
            return mark_safe('<img style=" height: 225px;" src="{0}"/>'.format(self.main_photo.url))
        else: 
            return mark_safe('<img style="object-fit: cover;  height: 225px;" src="/static/media/no_image.png"/>')
    image_img_haval.short_description = 'Фотография'
    image_img_haval.allow_tags = True

    def name_lines(self):
        return self.name.replace(' ', '<br>')
    name_lines.short_description = 'Наименование с переносами'
    name_lines.allow_tags = True

    def photo(self):
        if self.main_photo:
            return self.main_photo.url
        else:
            return '/media/no_image.png'


    def save(self, *args, **kwargs):
        if self.name == '':
            raise ValueError("Updating the value of creator isn't allowed")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=['uin'])
        ]
        db_table = 'refStaff'
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"


# Клиенты
class RefCustomer(models.Model):
    uin                 = models.CharField("uin", max_length=64, default='')
    name                = models.CharField("Наименование", max_length=250, default='')
    full_name           = models.CharField("Наименование полное", max_length=512, default='')
    phoneNorm           = models.CharField("Телефон", max_length=512, default='')
    email               = models.CharField("Email", max_length=512, default='')
    inn                 = models.CharField("ИНН", max_length=20, default='')
    kpp                 = models.CharField("КПП", max_length=20, default='')
    actual_addres       = models.CharField("Фактический адрес", max_length=512, default='')
    addres              = models.CharField("Юридический адрес", max_length=512, default='')
    description         = models.CharField("Описание", max_length=2500, default='')
    comment             = models.CharField("Комментарий", max_length=2500, default='')
    company             = models.BooleanField("Юридическое лицо", default=False)

    def __str__(self):
        return "{} {} - {}".format(self.name, self.phoneNorm, self.email)

    class Meta:
        indexes = [
            models.Index(fields=['uin']),
            models.Index(fields=['inn']),
            models.Index(fields=['kpp'])
        ]
        db_table = 'refCustomer'
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"


# Вид рабочего листа
class RefTypeDocRLK(models.Model):
    name    = models.CharField("Наименование", max_length=150, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refTypeDocRLK'
        verbose_name = "Вид рабочего листа"
        verbose_name_plural = "Виды рабочих листов"


# Работы заказ - наряда / Работы СЦ
class RefWork(models.Model):
    uin     = models.CharField("uin", max_length=200, default='')
    name    = models.CharField("Наименование", max_length=300, default='')
    article = models.CharField("Артикул", max_length=150, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        indexes = [
            models.Index(fields=['uin'])
        ]
        db_table = 'refWork'
        verbose_name = "Работа"
        verbose_name_plural = "Работы"


# Статусы оценки 
class RefStatusEstimation(models.Model):
    name    = models.CharField("Наименование", max_length=300, default='')
    order   = models.IntegerField("Сортировка", null=True, default=0, blank=True)
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refStatusEstimation'
        verbose_name = "Статус оценки"
        verbose_name_plural = "Статусы оценки"

# Тип документа поступления 
class RefTypeDocService(models.Model):
    name    = models.CharField("Наименование", max_length=150, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refTypeDocService'
        verbose_name = "Тип документа поступления"
        verbose_name_plural = "Типы документов поступления"

# Тип документа поступления 
class RefTypeItemServiceRepair(models.Model):
    name    = models.CharField("Наименование ", max_length=150, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refTypeItemServiceRepair'
        verbose_name = "Тип затраты поля поступления"
        verbose_name_plural = "Типы затраты поля поступления"

# Услуги
class RefService(models.Model):
    uin             = models.CharField("uin", max_length=200, default='')
    name            = models.CharField("Наименование", max_length=300, default='')
    article         = models.CharField("Артикул", max_length=150, default='')
   
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        indexes = [
            models.Index(fields=['uin'])
        ]
        db_table = 'refService'
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"
        
        
# Товары
class RefProduct(models.Model):
    uin             = models.CharField("uin", max_length=200, default='')
    name            = models.CharField("Наименование", max_length=300, default='')
    article         = models.CharField("Артикул", max_length=150, default='')
    article_dop     = models.CharField("Артикул дополнительный", max_length=150, default='')
    manufacturer    = models.CharField("Производитель", max_length=150, default='')

    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        indexes = [
            models.Index(fields=['uin'])
        ]
        db_table = 'refProduct'
        verbose_name = "Товар"
        verbose_name_plural = "Товары"


# Вид ремонта заказ - наряда
class RefTypeRepair(models.Model):
    name            = models.CharField("Наименование", max_length=300, default='')
    tizer           = models.BooleanField("Тизер", default=False)
    сhecklist       = models.BooleanField("Учавствует в чек листах", default=False)
    opros           = models.BooleanField("Учавствует в опросах клиента", default=False)
    warranty        = models.BooleanField("Гарантия", default=False)

    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refTypeRepair'
        verbose_name = "Вид ремонта заказ - наряда"
        verbose_name_plural = "Виды ремонта заказ - нарядов"


# Вид работы в заказ - наряде
class RefTypeItemRepair(models.Model):
    name            = models.CharField("Наименование", max_length=300, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refTypeItemRepair'
        verbose_name = "Вид в заказ - наряде"
        verbose_name_plural = "Виды в заказ - нарядах"


# Статус заказ - наряда / статус готовности ЗН
class RefStatusDocZN(models.Model):
    name    = models.CharField("Наименование", max_length=300, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refStatusDocZN'
        verbose_name = "Статус заказ - наряда / статус готовности ЗН"
        verbose_name_plural = "Статусы заказ - наряда / статус готовности ЗН"


# Вид контакта
class RefContactType(models.Model):
    name    = models.CharField("Наименование", max_length=300, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refContactType'
        verbose_name = "Вид контакта"
        verbose_name_plural = "Виды контактов"


# Статус события
class RefStatusEvent(models.Model):
    name    = models.CharField("Наименование", max_length=300, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refStatusEvent'
        verbose_name = "Статус события"
        verbose_name_plural = "Статусы события"


# Тип Аналитики автомобиля
class RefEventCarsOrganization(models.Model):
    name    = models.CharField("Наименование", max_length=300, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refEventCarsOrganization'
        verbose_name = "Тип события автомобиля"
        verbose_name_plural = "Типы событий по автомобилям"

# Тип привода
class RefTypeDrive(models.Model):
    name    = models.CharField("Наименование", max_length=300, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refTypeDrive'
        verbose_name = "Тип привода"
        verbose_name_plural = "Типы привода"


# Тип кузова
class RefTypeBody(models.Model):
    name            = models.CharField("Наименование", max_length=300, default='')
    name_autohub    = models.CharField("Наименование автохаб", max_length=300, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refTypeBody'
        verbose_name = "Тип кузова"
        verbose_name_plural = "Типы кузова"


# Тип двигателя
class RefTypeEngine(models.Model):
    name    = models.CharField("Наименование", max_length=300, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refTypeEngine'
        verbose_name = "Тип двигателя"
        verbose_name_plural = "Типы двигателей"


# Тип коробки передач
class RefTypeKpp(models.Model):
    name    = models.CharField("Наименование", max_length=300, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refTypeKpp'
        verbose_name = "Тип коробки передач"
        verbose_name_plural = "Типы коробок передач"


# Марка автору
class AutoruMark(models.Model):
	name    = models.CharField("Наименование", max_length=200)
	nameEn  = models.CharField("Наименование дополнительное", max_length=200)
	idSite  = models.IntegerField("ИД", null=True, default=0, blank=True)
	file    = models.ImageField(upload_to='autoru_images/', max_length=100, verbose_name="Файл", blank=True, null=True)

	def logo(self):
		try:
			return self.file.url
		except:
			return '/media/images/kg.png'
	
	def __str__(self):
		
		return self.name

	class Meta:
		indexes = [
			models.Index(fields=['idSite'])
		]
		db_table = 'autoruMark'
		verbose_name = "Марка"
		verbose_name_plural = "Марки"
		ordering = ['name',]


# Модель автору
class AutoruModel(models.Model):
	mark                = models.ForeignKey(AutoruMark, null=True, on_delete=models.CASCADE, verbose_name='Марка')
	name                = models.CharField("Наименование", max_length=200)
	nameEn              = models.CharField("Наименование дополнительное", max_length=200)
	nameHuman           = models.CharField("Наименование общее", max_length=200, default='')
	idSite              = models.IntegerField("ИД", null=True, default=0, blank=True)
	idSiteGeneration    = models.IntegerField("ИДГенерации", default=0, null=True, blank=True)
	file                = models.ImageField(upload_to='autoru_images/', max_length=100, verbose_name="Файл", blank=True, null=True)

	def save(self, *args, **kwargs):
		try:
			if self.name.find(',') > 0:
				name = self.name.split(',')[0]
				self.nameHuman = name
			else:
				self.nameHuman = self.name
		except:
			self.nameHuman = self.name
			s = 1 
		
		super().save(*args, **kwargs)

	def __str__(self):
		return self.name

	class Meta:
		indexes = [
			models.Index(fields=['idSite'])
		]
		db_table = 'autoruModel'
		verbose_name = "Модель"
		verbose_name_plural = "Модели"
		ordering = ['name',]


# Модификация автору
class AutoruModification(models.Model):
	model               = models.ForeignKey(AutoruModel, null=True, on_delete=models.CASCADE, verbose_name='Модель')
	name                = models.CharField("Наименование", max_length=200)
	nameEn              = models.CharField("Наименование дополнительное", max_length=200)
	idSite              = models.IntegerField("ИД", null=True, default=0, blank=True)
	idSiteGeneration    = models.IntegerField("ИД генерации", null=True, default=0, blank=True)
	idSiteKonf          = models.IntegerField("ИД конфигурации", null=True, default=0, blank=True)
	idSiteTech          = models.IntegerField("ИД тех параметров", null=True, default=0, blank=True)
	typeBody            = models.ForeignKey(RefTypeBody, null=True, on_delete=models.SET_NULL, verbose_name='Вид кузова')
	typeEngine          = models.ForeignKey(RefTypeEngine, null=True, on_delete=models.SET_NULL, verbose_name='Вид двигателя')
	typeGear            = models.ForeignKey(RefTypeKpp, null=True, on_delete=models.SET_NULL, verbose_name='Вид коробки передач')
	engineVolume        = models.FloatField("Объем двигателя", blank=True, default=0.0)
	enginePower         = models.FloatField("Мощность двигателя", blank=True, default=0.0)
	ProductionStartYear = models.PositiveSmallIntegerField('Год начала выпуска', default=0, blank=True)
	ProductionEndYear   = models.PositiveSmallIntegerField('Год окончания выпуска', default=0, blank=True)
	file    = models.ImageField(upload_to='autoru_images/', max_length=100, verbose_name="Файл", blank=True, null=True)

	def engine_volume(self):
		return str(self.engineVolume).replace(',','.')


	def __str__(self):
		return self.name

	class Meta:
		indexes = [
			models.Index(fields=['idSite'])
		]
		db_table = 'autoruModification'
		verbose_name = "Модификация"
		verbose_name_plural = "Модификации"
		ordering = ['name',]


# Комплектация автору
class AutoruComplectation(models.Model):
	modification    = models.ForeignKey(AutoruModification, null=True, on_delete=models.CASCADE, verbose_name='Модификация')
	name            = models.CharField("Наименование", max_length=200)
	idSite          = models.IntegerField("ИД", null=True, default=0, blank=True)

	def __str__(self):
		return self.name

	class Meta:
		indexes = [
			models.Index(fields=['idSite'])
		]
		db_table = 'autoruComplectation'
		verbose_name = "Комплектация"
		verbose_name_plural = "Комплектации"
		ordering = ['name',]

# Опции модификации автору
class AutoruModificationOptions(models.Model):
    modification        = models.ForeignKey(AutoruModification, null=True, on_delete=models.CASCADE, verbose_name='Модификация')
    complectation       = models.ForeignKey(AutoruComplectation, null=True, on_delete=models.CASCADE, verbose_name='Комплектация')
    name                = models.CharField("Наименование", max_length=1750, default='')
    link                = models.CharField("Ссылка", max_length=1750, default='')

    def __str__(self):
        return "{}".format(self.modification)

    class Meta:
        db_table = 'autoruModificationOptions'
        verbose_name = "Опции модификации"
        verbose_name_plural = "Опции модификаций"

class RefModificationsOptionGroup(models.Model):
    name    = models.CharField("Наименование", max_length=512, default='')
    
    def __str__(self):
        return self.name

    class Meta:
        db_table = 'refModificationsOptionGroup'
        verbose_name = "Группа опции"
        verbose_name_plural = "Группа опций"

class RefModificationsOption(models.Model):
    name    = models.CharField("Наименование", max_length=512, default='')
    group   = models.ForeignKey(RefModificationsOptionGroup, null=True, on_delete=models.CASCADE, verbose_name='Группа опций')
    
    def __str__(self):
        return self.name

    class Meta:
        db_table = 'refModificationsOption'
        verbose_name = "Группа опции"
        verbose_name_plural = "Группа опций"

class AutoruModificationOptionsDetail(models.Model):
    modification        = models.ForeignKey(AutoruModification, null=True, on_delete=models.CASCADE, verbose_name='Модификация')
    complectation       = models.ForeignKey(AutoruComplectation, null=True, on_delete=models.CASCADE, verbose_name='Комплектация')
    option              = models.ForeignKey(RefModificationsOption, null=True, on_delete=models.CASCADE, verbose_name='Опция')
    
    def __str__(self):
        return "{}".format(self.modification)

    class Meta:
        db_table = 'autoruModificationOptionsDetail'
        verbose_name = "Опции модификации детально"
        verbose_name_plural = "Опции модификации детально"

# Технические характеристики модификации автору
class AutoruModificationSpecifications(models.Model):
    modification        = models.ForeignKey(AutoruModification, null=True, on_delete=models.CASCADE, verbose_name='Модификация')
    complectation       = models.ForeignKey(AutoruComplectation, null=True, on_delete=models.CASCADE, verbose_name='Комплектация')
    name                = models.CharField("Наименование", max_length=1750, default='')
    link                = models.CharField("Ссылка", max_length=1750, default='')

    def __str__(self):
        return "{}".format(self.modification)

    class Meta:
        db_table = 'autoruModificationSpecifications'
        verbose_name = "Спецификация модификации тех характеристики"
        verbose_name_plural = "Спецификации модификаций тех характеристики"

class RefSpecification(models.Model):
    name    = models.CharField("Наименование", max_length=512, default='')
    group   = models.CharField("Группа", max_length=512, default='')
    
    def __str__(self):
        return self.name

    class Meta:
        db_table = 'refSpecification'
        verbose_name = "Спецификация"
        verbose_name_plural = "Спецификации"

class RefSpecificationData(models.Model):
    modification_specifications = models.ForeignKey(AutoruModificationSpecifications, null=True, on_delete=models.CASCADE, verbose_name='Модификация спецификация')
    specification               = models.ForeignKey(RefSpecification, null=True, on_delete=models.CASCADE, verbose_name='Спецификация')
    value                       = models.CharField("Ссылка", max_length=1750, default='')

    def __str__(self):
        return "{}".format(self.modification_specifications)

    class Meta:
        db_table = 'refSpecificationData'
        verbose_name = "Спецификации модификаций"
        verbose_name_plural = "Спецификация модификации"


# Автомобили
class RefCars(models.Model):
    vin                     = models.CharField("ВИН", max_length=18, default='')
    vin2                    = models.CharField("Дополнительный ВИН", max_length=18, default='')
    name                    = models.CharField("Наименование", max_length=512, default='')
    year                    = models.CharField("Год выпуска", max_length=4, default='')
    mark                    = models.CharField("Марка", max_length=512, default='')
    model                   = models.CharField("Модель", max_length=512, default='')
    modification            = models.CharField("Модификация", max_length=512, default='')
    modification_autoru     = models.ForeignKey(AutoruModification, null=True, on_delete=models.SET_NULL, verbose_name='Модификация')
    complectation_autoru    = models.ForeignKey(AutoruComplectation, null=True, on_delete=models.SET_NULL, verbose_name='Комплектация')

    def __str__(self):
        return "{} - {}({})".format(self.name, self.vin, self.vin2)

    class Meta:
        indexes = [
            models.Index(fields=['vin']),
            models.Index(fields=['name'])
        ]
        db_table = 'refCars'
        verbose_name = "Автомобиль"
        verbose_name_plural = "Автомобили"


# Назначения выгрузок
class RefTypeExchange(models.Model):
    name       = models.CharField("Наименование", max_length=300)
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refTypeExchange'
        verbose_name = "Назначение выгрузки"
        verbose_name_plural = "Назначения выгрузок"


# Выгрузки автомобилей
class RefExchangeCars(models.Model):
    unit            = models.ForeignKey(RefUnit, null=True, on_delete=models.SET_NULL, verbose_name='Подразделение ДЦ')
    type_exchange   = models.ForeignKey(RefTypeExchange, null=True, on_delete=models.SET_NULL, verbose_name='Назначение выгрузки')
    mark_filter     = models.CharField("Марка автомобиля", max_length=300)
    adress          = models.CharField("Адрес", max_length=300)
    file_name       = models.CharField("Имя файла", max_length=300)
    city_name       = models.CharField("Город", max_length=300)
    link            = models.CharField("Ссылка", max_length=1024)

    def __str__(self):
        return "{}".format(self.unit)

    class Meta:
        db_table = 'refExchangeCars'
        verbose_name = "Выгрузка автомобилей ДЦ"
        verbose_name_plural = "Выгрузки автомобилей ДЦ"


# Причина отмены чек листа
class RefTypeCanceledCheckList(models.Model):
    name            = models.CharField("Наименование", max_length=300, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refTypeCanceledCheckList'
        verbose_name = "Причина отмены чек листа"
        verbose_name_plural = "Причины отмены чек листа"


# Причина отмены смс опроса
class RefTypeCanceledSMS(models.Model):
    name            = models.CharField("Наименование", max_length=300, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refTypeCanceledSMS'
        verbose_name = "Причина отмены смс опроса"
        verbose_name_plural = "Причины отмены смс опросов"


# NPS категория негатива 
class RefTypeCategoryNegative(models.Model):
    name            = models.CharField("Наименование", max_length=300, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refTypeCategoryNegative'
        verbose_name = "Категория негатива"
        verbose_name_plural = "Категории негатива"


# NPS категория клиента
class RefTypeCategoryCustomer(models.Model):
    name            = models.CharField("Наименование", max_length=300, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refTypeCategoryCustomer'
        verbose_name = "Категория клиента"
        verbose_name_plural = "Категории клиентов"


# Производители
class RefManufacturer(models.Model):
    name                = models.CharField("Наименование", max_length=300, default='')
    alias               = models.CharField("Алиас", max_length=2048, default='', blank=True)
    group_name          = models.CharField("Группа", max_length=2048, default='', blank=True)    
    search_fields       = models.CharField("Строка поиска", blank=True, max_length=5120, default='')
    name_rus            = models.CharField("Наименование на русском", blank=True, max_length=5120, default='')
    slug                = models.SlugField(max_length=512, null=True, blank=True)
    name_upper          = models.CharField("Наименование в верхнем регистре ", max_length=300, default='')

    def __str__(self):
        return "{}".format(self.name)

    def save(self, *args, **kwargs):
        self.name_rus       = translit(self.name, 'ru')
        self.name_upper     = self.name.upper()
        
        text_search     = re.sub("[^A-Za-z А-Яа-я 0-9]", " ", self.name.lower()).rstrip() + ' ' + re.sub("[^A-Za-z А-Яа-я 0-9]", " ", self.alias.lower()).rstrip() + ' ' + self.group_name.lower()
        text_search     = re.sub(" +", " ", text_search)

        text_search_rus = translit(text_search, 'ru') 
        
        text_search_new = text_search + ' ' + text_search_rus
        self.search_fields  = ' '.join(unique_list(text_search_new.split()))

        super().save(*args, **kwargs)

    class Meta:
        db_table = 'refManufacturer'
        verbose_name = "Производитель"
        verbose_name_plural = "Производители"

# Группы деталей / пока точно использую в прайслистах
class RefGroupProduct(models.Model):
    name                = models.CharField("Наименование", max_length=300, default='')
    slug                = models.SlugField(max_length=512, null=True, blank=True)

    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refGroupProduct'
        verbose_name = "Группа товаров"
        verbose_name_plural = "Группа товара"

# Категории товаров
class RefCategoryProduct(models.Model):
    name                = models.CharField("Наименование", max_length=300, default='')
    slug                = models.SlugField(max_length=512, null=True, blank=True)

    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refCategoryProduct'
        verbose_name = "Категории товаров"
        verbose_name_plural = "Категории товара"


# Производители
class RefCatalogProduct(models.Model):
    name            = models.CharField("Наименование", max_length=300, default='')
    manufacturer    = models.ForeignKey(RefManufacturer, null=True, on_delete=models.SET_NULL, verbose_name='Производитель')
    article         = models.CharField("Артикул", max_length=150, default='')
    main_photo      = models.ImageField(upload_to='catalog_product/', max_length=250, verbose_name="Фото", blank=True, null=True)
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refCatalogProduct'
        verbose_name = "Каталог товаров"
        verbose_name_plural = "Каталог товаров"


# Тип планирования ресурса
class RefTypeResourcePlanning(models.Model):
    name                = models.CharField("Наименование", max_length=300, default='')
    in_service          = models.BooleanField("Прием", default = False, null=True, blank=True)
    out_service         = models.BooleanField("Выдача", default = False, null=True, blank=True)
    work_service        = models.BooleanField("Ремонт", default = False, null=True, blank=True)
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refTypeResourcePlanning'
        verbose_name = "Тип планирования ресурса"
        verbose_name_plural = "Типы планирования ресурса"


class RefBoards(models.Model):
    name                        = models.CharField("Наименование", max_length=300, default='')
    name_title                  = models.CharField("Заголовок", max_length=300, default='')
    main_photo                  = models.ImageField(upload_to='logo/', max_length=100, verbose_name="Фотография", blank=True, null=True)
    one_staff                   = models.BooleanField("Выводить по одному мастеру консультанту", default = False, null=True, blank=True)
    units                       = models.ManyToManyField(RefUnit, related_name='boards_units', verbose_name='Подразделения', blank=True)
    board_name                  = models.CharField("Наименование шаблона", default='', max_length=200, blank=True)
    table_view_customer         = models.BooleanField("Выводить ФИО клиента", default = False, null=True, blank=True)
    table_view_staff            = models.BooleanField("Выводить мастера консультанта", default = False, null=True, blank=True)
    table_view_plate_number     = models.BooleanField("Выводить номер автомобиля", default = False, null=True, blank=True)
    table_view_status           = models.BooleanField("Выводить заказ-наряда", default = False, null=True, blank=True)
    table_view_vin              = models.BooleanField("Выводить VIN автомобиля", default = False, null=True, blank=True)
    table_view_mark             = models.BooleanField("Выводить марку автомобиля", default = False, null=True, blank=True)
    table_view_model            = models.BooleanField("Выводить модель автомобиля", default = False, null=True, blank=True)
    adress                      = models.CharField("Адрес", default='', max_length=512, blank=True)
    filter_mark                 = models.CharField("Фильтр марки", default='', max_length=512, blank=True)
    max_count_records_page      = models.IntegerField("Максимум записей для одной страницы", default=60, null=True, blank=True)
    phone                       = models.CharField("Телефон", default='', max_length=512, blank=True)
    email                       = models.CharField("Email", default='', max_length=512, blank=True)
    webSite                     = models.CharField("Веб - сайт", max_length=250, default='', blank=True)
    time_refresh                = models.IntegerField("Секунд обновления", default=60, null=True, blank=True)
    customer_name_default       = models.CharField("Наименование клиента по умолчанию (в случае пустого наименования)", max_length=250, default='', blank=True)

    def image_img(self):
        if self.main_photo:
            return mark_safe('<img style="object-fit: scale-down;min-width:240px;max-width:240px;max-height: 120px;" src="{0}"/>'.format(self.main_photo.url))
        else: 
            return mark_safe('<div style="width:240px; height:120px;text-align:center;" ><img style="max-width:100%;max-height: 100%;" src="/static/media/no_image.png"/></div>')
    image_img.short_description = 'Фотография'
    image_img.allow_tags = True
    
    def photo(self):
        if self.main_photo:
            return self.main_photo.url
        else:
            return '/media/no_image.png'

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'refBoards'
        verbose_name = "Доски приветствия"
        verbose_name_plural = "Доски приветствия"


# Доски страницы рекламы и прочего
class RefBoardsPage(models.Model):
    board       = models.ManyToManyField(RefBoards, verbose_name='Монитор приветствия', blank=True)
    title       = models.CharField("Наименование", max_length=300)
    activated   = models.BooleanField("Активна", default = False, null=True, blank=True)
    html        = RichTextUploadingField(null=True, blank=True)
    time        = models.IntegerField("Время отображения", default=60, null=True, blank=True)
    
    def __str__(self):
        return "{} / {}".format(self.board, self.title)

    class Meta:
        db_table = 'refBoardsPage'
        verbose_name = "Страница монитора приветствия"
        verbose_name_plural = "Страницы монитора приветствия"



# Статус сообщения 1С
class RefSMSStatusBase(models.Model):
    name            = models.CharField("Наименование", max_length=300, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refSMSStatusBase'
        verbose_name = "Статус сообщения СМС 1C"
        verbose_name_plural = "Статусы сообщения СМС 1C"


# Статус сообщения Пройвайдера
class RefSMSStatusProvider(models.Model):
    name            = models.CharField("Наименование", max_length=300, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refSMSStatusProvider'
        verbose_name = "Статус сообщения СМС провайдера"
        verbose_name_plural = "Статусы сообщения СМС провайдера"


# Пользовательские фильтры
class RefCustomerFiltr(models.Model):

    name                = models.CharField("Наименование", max_length=512, default='')
    user                = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, verbose_name='Пользователь')
    path                = models.CharField("Параметры", max_length=5112, default='')
    page                = models.CharField("Раздел, страница", max_length=2048, default='')
    date                = models.DateTimeField('Дата', default=datetime.now, blank=False)

    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refCustomerFiltr'
        verbose_name = "Пользовательский фильтр"
        verbose_name_plural = "Пользовательские фильтры"


class RefPageOcenka(models.Model):
    name = models.CharField("Наименование", max_length=300)
   
    def __str__(self):
        return self.name

    class Meta:
        db_table = 'refPageOcenka'
        verbose_name = "Страница интерактивной оценки"
        verbose_name_plural = "Страницы интерактивной оценки"


class RefStatusOcenka(models.Model):
    name = models.CharField("Наименование", max_length=200)
   
    def __str__(self):
        return self.name

    class Meta:
        db_table = 'refStatusOcenka'
        verbose_name = "Статус интерактивной оценки"
        verbose_name_plural = "Статусы интерактивных оценок"


# Статус диспозиции
class RefStatusCars(models.Model):
    name = models.CharField("Наименование", max_length=200)
   
    def __str__(self):
        return self.name

    class Meta:
        db_table = 'refStatusCars'
        verbose_name = "Статус автомобиля"
        verbose_name_plural = "Статусы автомобиля"


# Склад / Стоянка
class RefStore(models.Model):
    uin             = models.CharField("uin", max_length=200)
    unit            = models.ForeignKey(RefUnit, null=True, on_delete=models.SET_NULL, verbose_name='Подразделение ДЦ')
    name            = models.CharField("Наименование", max_length=200, default='')
    name_dop        = models.CharField("Наименование для отображения", max_length=200, blank=True)
    city            = models.ForeignKey(RefCity, null=True, on_delete=models.SET_NULL, verbose_name='Город')
    main_photo      = models.ImageField(upload_to='logo_unit/', max_length=100, verbose_name="Логотип", blank=True, null=True)
    adress          = models.CharField("Адрес", default='', max_length=512, blank=True)
    phone           = models.CharField("Телефон", default='', max_length=512, blank=True)
    email           = models.CharField("Email", default='', max_length=512, blank=True)
    latitude        = models.FloatField("Широта", default=0.0, blank=True)
    longitude       = models.FloatField("Долгота", default=0.0, blank=True)
    link_ya_map     = models.CharField("Ссылка яндекс карты", max_length=512, default='', blank=True)
    name_site       = models.CharField("Наименование для сайта", max_length=512, default='', blank=True)
    view_site       = models.BooleanField("Показывать на сайте", default=False, blank=True)
    link_site_map   = models.CharField("Ссылка на карту", max_length=512, default='', blank=True)
    active_eco      = models.BooleanField("Доступен для оценки", default=False)

    def image_img(self):
        if self.main_photo:
            return mark_safe('<div style=" width:240px; height:120px;text-align:center;" ><img style="object-fit: scale-down;min-width:240px;max-width:240px;max-height: 120px;" src="{0}"/></div>'.format(self.main_photo.url))
        else: 
            return mark_safe('<div style=" width:240px; height:120px;text-align:center;" ><img style="max-width:100%;max-height: 100%;" src="/static/media/kg.jpg"/></div>')
    image_img.short_description = 'Логотип'
    image_img.allow_tags = True

    def phone_normalize(self):
        return "+" + re.sub('[^0-9]', '', self.phone)

    def cars_count(self):
        return RefCarsOrganization.objects.filter(store = self).filter(reserve = 0).exclude(quantity = 0).count()

    def __str__(self):
        return "{} - {}".format(self.name, self.city)

    class Meta:
        indexes = [
            models.Index(fields=['uin'])
        ]
        db_table = 'refStore'
        verbose_name = "Склад / Стоянки"
        verbose_name_plural = "Склады / Стоянки"


# Ценовые группы автомобилей
class RefGroupPrice(models.Model):
    name            = models.CharField("Наименование", max_length=200, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refGroupPrice'
        verbose_name = "Ценовая категория"
        verbose_name_plural = "Ценовые категории"


# Этапы переоценки автомобилей
class RefStagePrice(models.Model):
    name            = models.CharField("Наименование", max_length=200, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refStagePrice'
        verbose_name = "Этап установки цены"
        verbose_name_plural = "Этапы установки цен"


class RefStatusCarsOrganization(models.Model):
    name            = models.CharField("Наименование", max_length=200, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refStatusCarsOrganization'
        verbose_name = "Статус автомобиля"
        verbose_name_plural = "Статусы автомобилей"


class RefTypeEvaluationCarsOrganization(models.Model):
    name            = models.CharField("Наименование", max_length=200, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        indexes = [
            models.Index(fields=['name'])
        ]
        db_table = 'refTypeEvaluationCarsOrganization'
        verbose_name = "Статус автомобиля"
        verbose_name_plural = "Статусы автомобилей"


class RefRatingCarsOrganization(models.Model):
    name            = models.CharField("Наименование", max_length=200, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refRatingCarsOrganization'
        verbose_name = "Привлекательность автомобиля"
        verbose_name_plural = "Привлекательности автомобиля"


class RefTypeSaleCarsOrganization(models.Model):
    name            = models.CharField("Наименование", max_length=200, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refTypeSaleCarsOrganization'
        verbose_name = "Тип продажи автомобиля"
        verbose_name_plural = "Типы продажи автомобиля"


class RefTypeReceptionCarsOrganization(models.Model):
    name            = models.CharField("Наименование", max_length=200, default='')
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refTypeReceptionCarsOrganization'
        verbose_name = "Тип приема автомобиля"
        verbose_name_plural = "Типы приема автомобиля"


class RefTypeKPPAvito(models.Model):
    name        = models.CharField("Наименование", max_length=200, default='')
    
    def __str__(self):
        return self.name

    class Meta:
        db_table = 'refTypeKPPAvito'
        verbose_name = "Тип коробки передач"
        verbose_name_plural = "Типы коробки передач"


class RefTypeEngineAvito(models.Model):
    name        = models.CharField("Наименование", max_length=200, default='')
    
    def __str__(self):
        return self.name

    class Meta:
        db_table = 'refTypeEngineAvito'
        verbose_name = "Тип двигателя"
        verbose_name_plural = "Типы двигателей"


class RefTypeDriveAvito(models.Model):
    name        = models.CharField("Наименование", max_length=200, default='')
    
    def __str__(self):
        return self.name

    class Meta:
        db_table = 'refTypeDriveAvito'
        verbose_name = "Тип привода"
        verbose_name_plural = "Типы приводов"


class RefTypeBodyAvito(models.Model):
    name        = models.CharField("Наименование", max_length=200, default='')
    
    def __str__(self):
        return self.name

    class Meta:
        db_table = 'refTypeBodyAvito'
        verbose_name = "Тип кузова"
        verbose_name_plural = "Типы кузовов"


# Причины отправки в архив
class RefReasonArchiveRLK(models.Model):
	name                = models.CharField("Наименование", max_length=200)
	
	def __str__(self):
		return self.name

	class Meta:
		db_table = 'refReasonArchiveRLK'
		verbose_name = "Причина отправки в архив рабочих листов"
		verbose_name_plural = "Причины отправки в архив рабочих листов"
		ordering = ['name',]


# Причины отправки в архив
class RefStatusRLK(models.Model):
	name                = models.CharField("Наименование", max_length=200)
	
	def __str__(self):
		return self.name

	class Meta:
		db_table = 'refStatusRLK'
		verbose_name = "Статус рабочего листа"
		verbose_name_plural = "Статус рабочего листа"
		ordering = ['name',]


class RefAvito(MPTTModel):
    name            = models.CharField("Наименование", max_length=250, default='', null=True, blank=True,)
    slug            = models.SlugField(max_length=512)
    parent          = TreeForeignKey('self', on_delete=models.PROTECT, default=0,  null=True, blank=True, related_name='children',
                            db_index=True, verbose_name='Родитель')
    group           = models.BooleanField("Это группа", default=False)
    avito_id        = models.IntegerField("ИД", default=0, blank=True)  
    engine_volume   = models.FloatField("Объем двигателя", default=0.0, blank=True)  
    engine_power    = models.IntegerField("Мощность двигателя", default=0, blank=True)  
    year_star       = models.IntegerField("Год начала выпуска", default=0, blank=True)  
    year_end        = models.IntegerField("Год окончания выпуска", default=0, blank=True)  
    doors           = models.IntegerField("Количество дверей", default=0, blank=True)  
    kpp             = models.ForeignKey(RefTypeKPPAvito, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Тип коробки передач")
    engine          = models.ForeignKey(RefTypeEngineAvito, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Тип двигателя")
    drive           = models.ForeignKey(RefTypeDriveAvito, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Тип привода")
    body            = models.ForeignKey(RefTypeBodyAvito, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Тип кузова")
    image_url       = models.CharField("УРЛ", max_length=512, default='', blank=True)
    file            = models.ImageField(upload_to='avito_images/', max_length=100, verbose_name="Файл", blank=True, null=True)
    
    

    def __str__(self):
        return "{}".format(self.name)
    
    def get_photo(self):
        try:
            return self.file.url
        except:
            if len(self.image_url) != 0:
                return self.image_url
            return '' #'/media/no_foto.jpg'

    def get_photo_mini(self):
        try:
            return self.file.url
        except:
            if len(self.image_url) != 0:
                return self.image_url
            return '' #'/media/no_foto.jpg'
        
    def save(self, *args, **kwargs):
        parent_name = ''
        if self.parent != None:
            parent_name = self.parent.slug
        if not self.slug:
            name_slug = transliterate(self.name) + '_' + str(self.avito_id)
            self.slug = slugify(name_slug.lower())
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('', args=[str(self.slug)])
    
    class Meta:
        indexes = [
            models.Index(fields=['avito_id'])
        ]
        unique_together = [['parent', 'slug']]
        db_table = 'refAvito'
        verbose_name = "Каталог авито"
        verbose_name_plural = "Каталог авито"


# Комплектация автору
class RefAvitoComplectation(models.Model):
	avito_ref       = models.ForeignKey(RefAvito, null=True, on_delete=models.CASCADE, verbose_name='Модификация')
	name            = models.CharField("Наименование", max_length=200)
	avito_id        = models.IntegerField("ИД", default=0, blank=True)

	def __str__(self):
		return self.name

	class Meta:
		indexes = [
            models.Index(fields=['avito_id'])
        ]
		db_table = 'refAvitoComplectation'
		verbose_name = "Комплектация авито"
		verbose_name_plural = "Комплектации авито"
		ordering = ['name',]

# Марки резины
class RefMarkTyres(models.Model):
	name            = models.CharField("Наименование", max_length=512)
	
	def __str__(self):
		return self.name

	class Meta:
		db_table = 'refMarkTyres'
		verbose_name = "Марка резины"
		verbose_name_plural = "Марки резины"
		ordering = ['name',]

# Ширина резины
class RefWidthTyres(models.Model):
	name            = models.CharField("Наименование", max_length=100)
	value           = models.FloatField("Значение", default=0.0, blank=True) 

	def __str__(self):
		return self.name

	class Meta:
		db_table = 'refWidthTyres'
		verbose_name = "Ширина резины"
		verbose_name_plural = "Ширина резины"
		ordering = ['value',]

# Профиль резины
class RefProfileTyres(models.Model):
	name            = models.CharField("Наименование", max_length=100)
	value           = models.FloatField("Значение", default=0.0, blank=True) 

	def __str__(self):
		return self.name

	class Meta:
		db_table = 'refProfileTyres'
		verbose_name = "Профиль резины"
		verbose_name_plural = "Профиль резины"
		ordering = ['value',]

# Радиус
class RefRadius(models.Model):
	name            = models.CharField("Наименование", max_length=100)
	value           = models.FloatField("Значение", default=0.0, blank=True) 

	def __str__(self):
		return self.name

	class Meta:
		db_table = 'refRadius'
		verbose_name = "Радиус резины"
		verbose_name_plural = "Радиус резины"
		ordering = ['value',]

# Сезон резины
class RefSezonTyres(models.Model):
	name            = models.CharField("Наименование", max_length=100)

	def __str__(self):
		return self.name

	class Meta:
		db_table = 'refSezonTyres'
		verbose_name = "Сезон резины"
		verbose_name_plural = "Сезон резины"
		ordering = ['name',]

# Типы дисков
class RefTypeDisk(models.Model):
	name            = models.CharField("Наименование", max_length=100)

	def __str__(self):
		return self.name

	class Meta:
		db_table = 'refTypeDisk'
		verbose_name = "Тип дисска"
		verbose_name_plural = "Типы дисков"
		ordering = ['name',]

# DIA диск
class RefDiaDisk(models.Model):
	name            = models.CharField("Наименование", max_length=100)
	value           = models.FloatField("Значение", default=0.0, blank=True) 

	def __str__(self):
		return self.name

	class Meta:
		db_table = 'refDiaDisk'
		verbose_name = "DIA диска"
		verbose_name_plural = "DIA дисков"
		ordering = ['value',]

# ET диск
class RefEtDisk(models.Model):
	name            = models.CharField("Наименование", max_length=100)
	value           = models.FloatField("Значение", default=0.0, blank=True) 

	def __str__(self):
		return self.name

	class Meta:
		db_table = 'refEtDisk'
		verbose_name = "ET диска"
		verbose_name_plural = "ET дисков"
		ordering = ['value',]

# PSD диск
class RefPsdDisk(models.Model):
	name            = models.CharField("Наименование", max_length=100)
	value           = models.FloatField("Значение", default=0.0, blank=True) 

	def __str__(self):
		return self.name

	class Meta:
		db_table = 'refPsdDisk'
		verbose_name = "PSD диска"
		verbose_name_plural = "PSD дисков"
		ordering = ['value',]


from documents.models import DocLO
# Автомобили организации
class RefCarsOrganization(models.Model):
    organization            = models.ForeignKey(RefOrganization, null=True, on_delete=models.SET_NULL, verbose_name='Организация')
    unit                    = models.ForeignKey(RefUnit, null=True, on_delete=models.SET_NULL, verbose_name='Подразделение ДЦ')
    store                   = models.ForeignKey(RefStore, null=True, on_delete=models.SET_NULL, verbose_name='Склад / стоянка')
    is_new                  = models.BooleanField('Новый', default=False)
    vin                     = models.CharField("ВИН", max_length=18, default='')
    vin2                    = models.CharField("Дополнительный ВИН", max_length=18, default='')
    name                    = models.CharField("Наименование", max_length=512, default='')
    year                    = models.IntegerField("Год выпуска", blank=True, default=0)
    owners                  = models.IntegerField("Владельцев", blank=True, default=0)
    keys                    = models.IntegerField("Количество ключей", blank=True, default=0)
    reserve                 = models.IntegerField("Резерв", blank=True, default=0)
    mark                    = models.CharField("Марка", max_length=512, default='')
    model                   = models.CharField("Модель", max_length=512, default='')
    modification            = models.CharField("Модификация", max_length=512, default='')
    color                   = models.CharField("Цвет", blank=True, max_length=1024, default='')

    status                  = models.ForeignKey(RefStatusCarsOrganization, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Статус автомобиля')
    type_sale               = models.ForeignKey(RefTypeSaleCarsOrganization, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Тип продажи автомобиля')
    type_reception          = models.ForeignKey(RefTypeReceptionCarsOrganization, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Тип приема автомобиля')
    evaluation              = models.ForeignKey(RefTypeEvaluationCarsOrganization, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Вариант управления ценообразованием')
    
    modification_avito      = models.ForeignKey(RefAvito, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Авито модификация')
    complectation_avito     = models.ForeignKey(RefAvitoComplectation, null=True, on_delete=models.SET_NULL, verbose_name='Авито комплектация')

    modification_autoru     = models.ForeignKey(AutoruModification, null=True, on_delete=models.SET_NULL, verbose_name='Модификация')
    complectation_autoru    = models.ForeignKey(AutoruComplectation, null=True, on_delete=models.SET_NULL, verbose_name='Комплектация')
    
    type_body               = models.ForeignKey(RefTypeBody, null=True, on_delete=models.SET_NULL, verbose_name='Вид кузова')
    type_engine             = models.ForeignKey(RefTypeEngine, null=True, on_delete=models.SET_NULL, verbose_name='Вид двигателя')
    type_gear               = models.ForeignKey(RefTypeKpp, null=True, on_delete=models.SET_NULL, verbose_name='Вид коробки передач')
    type_drive              = models.ForeignKey(RefTypeDrive, null=True, on_delete=models.SET_NULL, verbose_name='Вид привода')
    
    engine_volume           = models.FloatField("Объем двигателя", blank=True, default=0.0)
    engine_power            = models.FloatField("Мощность двигателя", blank=True, default=0.0)
    
    plate_number            = models.CharField("Номерной знак", max_length=30, default='')

    description_podgotovka  = models.CharField("Комментарий для отдела подготовки", max_length=5120, default='')
    description_op          = models.CharField("Комментарий для отдела продаж", max_length=5120, default='')
    run                     = models.IntegerField("Пробег", null=True, default=0, blank=True)
    
    quantity                = models.IntegerField("Остаток", blank=True, default=0)
    bcp                     = models.IntegerField("БЦП", blank=True, default=0)
    price                   = models.IntegerField("Цена", blank=True, default=0)
    cost_price              = models.IntegerField("Себестоимость", blank=True, default=0)
    outlay                  = models.IntegerField("Расходы на АМ", blank=True, default=0)
    days_in_stok            = models.IntegerField("Дней на складе", blank=True, default=0)
    
    slug                    = models.SlugField(max_length=512, null=True, blank=True)
    date_refresh            = models.DateTimeField('Дата обновления', default=datetime.now, blank=False)
    date_create             = models.DateTimeField('Дата добавления', default=datetime.now, blank=False)
    search_worlds           = models.CharField("Поисковвые фразы", blank=True, max_length=5120, default='')
    search_fields           = models.CharField("Строка поиска", blank=True, max_length=5120, default='')
    
    lo_link                 = models.CharField("Лист - оценки", blank=True, max_length=1024, default='')
    lo_link_number          = models.CharField("Лист - оценки номер", blank=True, max_length=20, default='')
    lo_link_date            = models.DateTimeField("Лист - оценки дата", default=datetime.now, blank=False)
    lo_uin                  = models.CharField("УИН листа оценки", blank=True, max_length=36, default='')
    lo                      = models.ForeignKey(DocLO, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='ЛистОценки')

    qr                      = models.ImageField(upload_to='qr_cars_organization/', max_length=100, verbose_name="QR - code", blank=True, null=True)
    prev_photo              = models.ImageField(upload_to='prev_cars_organization/', max_length=100, verbose_name="Превью", blank=True, null=True)
    
    stage_price             = models.ForeignKey(RefStagePrice, null=True, on_delete=models.SET_NULL, verbose_name='Этап УС')
    group_price             = models.ForeignKey(RefGroupPrice, null=True, on_delete=models.SET_NULL, verbose_name='Ценовая категория')

    task                    = models.IntegerField("Задач по автомобилю", null=True, default=0, blank=True)
    rating                  = models.ForeignKey(RefRatingCarsOrganization, null=True, on_delete=models.SET_NULL, verbose_name='Рейтинг привлекательности')

    link_avtoteka_web       = models.CharField("Ссылка на автотеку веб", blank=True, max_length=1024, default='')
    link_avtoteka_pdf       = models.CharField("Ссылка на автотеку пдф", blank=True, max_length=1024, default='')

    days_next_stage         = models.IntegerField("Дней до следующего этапа", blank=True, default=0)

    def estimations_car_organizaton(self):
        from register.models import RegEstimationRefCarsOrganizations
        return RegEstimationRefCarsOrganizations.objects.filter(car = self).order_by('-date')    

    def get_link_autoru(self):
        from avtosalon.models import AvtohubSiteInfo
        infos = AvtohubSiteInfo.objects.filter(vin = self.vin).filter(date__range = [self.lo_link_date, self.date_refresh]).filter(site__id = 9).order_by('-date')   
        if infos.count() > 0:
            url = infos[0].externalURL
            if url != None:
                return url
        return ''

    def get_link_avitoru(self):
        from avtosalon.models import AvtohubSiteInfo
        infos = AvtohubSiteInfo.objects.filter(vin = self.vin).filter(date__range = [self.lo_link_date, self.date_refresh]).filter(site__id = 1).order_by('-date')   
        if infos.count() > 0:
            url = infos[0].externalURL
            if url != None:
                return url
        return ''

    def get_link_dromru(self):
        from avtosalon.models import AvtohubSiteInfo
        infos = AvtohubSiteInfo.objects.filter(vin = self.vin).filter(date__range = [self.lo_link_date, self.date_refresh]).filter(site__id = 3).order_by('-date')   
        if infos.count() > 0:
            url = infos[0].externalURL
            if url != None:
                return url
        return ''

    def avtohub_car_organizaton(self):
        from avtosalon.models import Avtohub
        return Avtohub.objects.filter(vin = self.vin).filter(date__range = [self.lo_link_date, self.date_refresh]).order_by('-date')    

    def price_car_organizaton_info(self):
        from register.models import RegRefCarsOrganizationsPrice
        return RegRefCarsOrganizationsPrice.objects.filter(car = self).order_by('-date') 
    
    def price_car_organizaton_calculation(self):
        from register.models import RegRefCarsOrganizationsCalculationPrice
        return RegRefCarsOrganizationsCalculationPrice.objects.filter(car = self).order_by('-date') 
    
    def price_car_organizaton_estimations(self):
        from register.models import RegEstimationRefCarsOrganizations
        return RegEstimationRefCarsOrganizations.objects.filter(car = self).order_by('-date') 

    def dop_cars(self, limit=12):
        """
        Расширенный метод подбора похожих автомобилей с приоритетами и системой релевантности.
        
        Приоритеты поиска:
        1. Та же модель (самый высокий приоритет)
        2. Та же марка + похожая цена (±15%)
        3. Та же марка + похожий год (±2 года) + похожий пробег (±30%)
        4. Та же марка + тот же объем двигателя
        5. Та же марка + та же КПП
        6. Та же марка + тот же кузов
        7. Похожая цена (±15%) из других подразделений
        8. Та же марка, любой вариант
        
        Результаты сортируются по системе баллов релевантности.
        """
        if not self.modification_autoru:
            return []
        
        try:
            base_filter = Q(
                modification_autoru__isnull=False,
                quantity__gt=0,
                reserve=0
            ) & ~Q(pk=self.pk)
            
            # Базовые фильтры - только активные автомобили
            all_cars = RefCarsOrganization.objects.filter(base_filter)
        
            # Приоритет 1: Та же модель (самый высокий приоритет)
            if self.unit:
                cars_same_model = all_cars.filter(
                    modification_autoru__model__id=self.modification_autoru.model.id,
                    unit=self.unit
                ).order_by('-date_create')[:limit]
            else:
                cars_same_model = all_cars.filter(
                    modification_autoru__model__id=self.modification_autoru.model.id
                ).order_by('-date_create')[:limit]
        
            # Приоритет 2: Та же марка, похожая цена (±15%)
            if self.price > 0:
                min_price = max(0, int(self.price - (self.price * 15 / 100)))
                max_price = int(self.price + (self.price * 15 / 100))
                query = all_cars.filter(
                    modification_autoru__model__mark__id=self.modification_autoru.model.mark.id
                ).exclude(
                    modification_autoru__model__id=self.modification_autoru.model.id
                ).filter(
                    price__range=[min_price, max_price]
                )
                if self.unit:
                    query = query.filter(unit=self.unit)
                cars_same_mark_price = query.order_by('-date_create')[:limit]
            else:
                cars_same_mark_price = []
        
            # Приоритет 3: Та же марка, похожий год (±2 года), похожий пробег (±30%)
            if self.year > 0 and self.run and self.run > 0:
                year_min = max(1950, self.year - 2)
                year_max = min(2030, self.year + 2)
                run_min = max(0, int(self.run * 0.7))
                run_max = int(self.run * 1.3)
                
                query = all_cars.filter(
                    modification_autoru__model__mark__id=self.modification_autoru.model.mark.id
                ).exclude(
                    modification_autoru__model__id=self.modification_autoru.model.id
                ).filter(
                    year__range=[year_min, year_max],
                    run__range=[run_min, run_max]
                )
                if self.unit:
                    query = query.filter(unit=self.unit)
                cars_same_mark_similar = query.order_by('-date_create')[:limit]
            else:
                cars_same_mark_similar = []
        
            # Приоритет 4: Та же марка, тот же объем двигателя
            try:
                engine_volume = None
                # Пробуем получить значение из поля engineVolume
                if hasattr(self.modification_autoru, 'engineVolume'):
                    engine_volume = getattr(self.modification_autoru, 'engineVolume', None)
                    # Если это callable (метод), вызываем его
                    if callable(engine_volume):
                        engine_volume = engine_volume()
                # Если не получилось, пробуем engine_volume
                if not engine_volume and hasattr(self.modification_autoru, 'engine_volume'):
                    engine_volume = getattr(self.modification_autoru, 'engine_volume', None)
                    if callable(engine_volume):
                        engine_volume = engine_volume()
                
                if engine_volume and isinstance(engine_volume, (int, float)) and engine_volume > 0:
                    query = all_cars.filter(
                        modification_autoru__model__mark__id=self.modification_autoru.model.mark.id
                    ).exclude(
                        modification_autoru__model__id=self.modification_autoru.model.id
                    ).filter(
                        modification_autoru__engineVolume=engine_volume
                    )
                    if self.unit:
                        query = query.filter(unit=self.unit)
                    cars_same_mark_engine = query.order_by('-date_create')[:limit]
                else:
                    cars_same_mark_engine = []
            except (AttributeError, TypeError, ValueError):
                cars_same_mark_engine = []
            
            # Приоритет 5: Та же марка, та же КПП
            if hasattr(self.modification_autoru, 'typeGear') and self.modification_autoru.typeGear:
                query = all_cars.filter(
                    modification_autoru__model__mark__id=self.modification_autoru.model.mark.id
                ).exclude(
                    modification_autoru__model__id=self.modification_autoru.model.id
                ).filter(
                    modification_autoru__typeGear__id=self.modification_autoru.typeGear.id
                )
                if self.unit:
                    query = query.filter(unit=self.unit)
                cars_same_mark_gear = query.order_by('-date_create')[:limit]
            else:
                cars_same_mark_gear = []
            
            # Приоритет 6: Та же марка, тот же кузов
            if hasattr(self.modification_autoru, 'typeBody') and self.modification_autoru.typeBody:
                query = all_cars.filter(
                    modification_autoru__model__mark__id=self.modification_autoru.model.mark.id
                ).exclude(
                    modification_autoru__model__id=self.modification_autoru.model.id
                ).filter(
                    modification_autoru__typeBody__id=self.modification_autoru.typeBody.id
                )
                if self.unit:
                    query = query.filter(unit=self.unit)
                cars_same_mark_body = query.order_by('-date_create')[:limit]
            else:
                cars_same_mark_body = []
        
            # Приоритет 7: Похожая цена (±15%), другой подразделение (если в текущем подразделении мало вариантов)
            if self.price > 0 and self.unit:
                min_price = max(0, int(self.price - (self.price * 15 / 100)))
                max_price = int(self.price + (self.price * 15 / 100))
                cars_similar_price_other_unit = all_cars.filter(
                    price__range=[min_price, max_price]
                ).exclude(
                    modification_autoru__model__id=self.modification_autoru.model.id
                ).exclude(
                    unit=self.unit
                ).order_by('-date_create')[:limit]
            else:
                cars_similar_price_other_unit = []
            
            # Приоритет 8: Та же марка, любой вариант (если еще не набрали достаточно)
            query = all_cars.filter(
                modification_autoru__model__mark__id=self.modification_autoru.model.mark.id
            ).exclude(
                modification_autoru__model__id=self.modification_autoru.model.id
            )
            if self.unit:
                query = query.filter(unit=self.unit)
            cars_same_mark_any = query.order_by('-date_create')[:limit]
        
            # Объединяем все результаты с приоритетами
            result_cars = []
            seen_ids = {self.pk}  # Исключаем текущий автомобиль
            
            # Добавляем автомобили по приоритетам
            priority_lists = [
                cars_same_model,
                cars_same_mark_price,
                cars_same_mark_similar,
                cars_same_mark_engine,
                cars_same_mark_gear,
                cars_same_mark_body,
                cars_similar_price_other_unit,
                cars_same_mark_any
            ]
            
            for car_list in priority_lists:
                for car in car_list:
                    if car.pk not in seen_ids and len(result_cars) < limit * 2:  # Берем больше для сортировки
                        result_cars.append(car)
                        seen_ids.add(car.pk)
                    if len(result_cars) >= limit * 2:
                        break
                if len(result_cars) >= limit * 2:
                    break
            
            # Сортируем результаты по релевантности (вычисляем "балл похожести")
            def calculate_relevance_score(car):
                score = 0
                
                try:
                    # Та же модель = +100 баллов
                    if (car.modification_autoru and self.modification_autoru and 
                        car.modification_autoru.model.id == self.modification_autoru.model.id):
                        score += 100
                    
                    # Та же марка = +50 баллов
                    if (car.modification_autoru and self.modification_autoru and 
                        car.modification_autoru.model.mark.id == self.modification_autoru.model.mark.id):
                        score += 50
                    
                    # Похожая цена (±10%) = +30 баллов, (±15%) = +20 баллов
                    if self.price > 0 and car.price and car.price > 0:
                        price_diff_percent = abs(car.price - self.price) / self.price * 100
                        if price_diff_percent <= 10:
                            score += 30
                        elif price_diff_percent <= 15:
                            score += 20
                    
                    # Похожий год (±1 год = +20, ±2 года = +10)
                    if self.year > 0 and car.year and car.year > 0:
                        year_diff = abs(car.year - self.year)
                        if year_diff <= 1:
                            score += 20
                        elif year_diff <= 2:
                            score += 10
                    
                    # Похожий пробег (±20% = +20, ±30% = +10)
                    if self.run and self.run > 0 and car.run and car.run > 0:
                        run_diff_percent = abs(car.run - self.run) / self.run * 100
                        if run_diff_percent <= 20:
                            score += 20
                        elif run_diff_percent <= 30:
                            score += 10
                    
                    # Тот же объем двигателя = +15 баллов
                    if car.modification_autoru and self.modification_autoru:
                        car_engine_volume = None
                        self_engine_volume = None
                        
                        # Получаем объем двигателя для car
                        if hasattr(car.modification_autoru, 'engineVolume'):
                            car_engine_volume = getattr(car.modification_autoru, 'engineVolume', None)
                            if callable(car_engine_volume):
                                car_engine_volume = car_engine_volume()
                        if not car_engine_volume and hasattr(car.modification_autoru, 'engine_volume'):
                            car_engine_volume = getattr(car.modification_autoru, 'engine_volume', None)
                            if callable(car_engine_volume):
                                car_engine_volume = car_engine_volume()
                        
                        # Получаем объем двигателя для self
                        if hasattr(self.modification_autoru, 'engineVolume'):
                            self_engine_volume = getattr(self.modification_autoru, 'engineVolume', None)
                            if callable(self_engine_volume):
                                self_engine_volume = self_engine_volume()
                        if not self_engine_volume and hasattr(self.modification_autoru, 'engine_volume'):
                            self_engine_volume = getattr(self.modification_autoru, 'engine_volume', None)
                            if callable(self_engine_volume):
                                self_engine_volume = self_engine_volume()
                        
                        if (car_engine_volume and self_engine_volume and 
                            isinstance(car_engine_volume, (int, float)) and 
                            isinstance(self_engine_volume, (int, float)) and
                            car_engine_volume == self_engine_volume):
                            score += 15
                    
                    # Та же КПП = +10 баллов
                    if (car.modification_autoru and self.modification_autoru and 
                        hasattr(car.modification_autoru, 'typeGear') and 
                        hasattr(self.modification_autoru, 'typeGear') and
                        car.modification_autoru.typeGear and self.modification_autoru.typeGear and
                        car.modification_autoru.typeGear.id == self.modification_autoru.typeGear.id):
                        score += 10
                    
                    # Тот же кузов = +10 баллов
                    if (car.modification_autoru and self.modification_autoru and 
                        hasattr(car.modification_autoru, 'typeBody') and 
                        hasattr(self.modification_autoru, 'typeBody') and
                        car.modification_autoru.typeBody and self.modification_autoru.typeBody and
                        car.modification_autoru.typeBody.id == self.modification_autoru.typeBody.id):
                        score += 10
                    
                    # Тот же привод = +5 баллов
                    if car.type_drive and self.type_drive and car.type_drive.id == self.type_drive.id:
                        score += 5
                    
                    # Тот же цвет = +5 баллов
                    if car.color and self.color and car.color.lower().strip() == self.color.lower().strip():
                        score += 5
                    
                    # Бонус за новинку (на складе менее 30 дней) = +5 баллов
                    if hasattr(car, 'days_in_stok') and car.days_in_stok and car.days_in_stok <= 30:
                        score += 5
                    
                    # Бонус за популярность (много просмотров) = +3 балла
                    if hasattr(car, 'view_card_cars') and car.view_card_cars and car.view_card_cars > 30:
                        score += 3
                    
                    # Бонус за то же подразделение = +2 балла
                    if car.unit and self.unit and car.unit.id == self.unit.id:
                        score += 2
                        
                except (AttributeError, TypeError, ZeroDivisionError):
                    pass  # Игнорируем ошибки при вычислении
                
                return score
            
            # Сортируем по релевантности (от большего к меньшему)
            result_cars.sort(key=calculate_relevance_score, reverse=True)
            
            return result_cars[:limit]
            
        except Exception as e:
            # В случае ошибки возвращаем пустой список или базовый результат
            return []

    def wear(self):
        year = datetime.now().year - self.year
        if year == 0:
             year = 1

        calc = self.run / year 
        if calc > 35000:
             return 1
        
        return 0

    def history_success(self):
        from documents.models import DocZN
        return DocZN.objects.filter(cars__vin = self.vin).count()
    
    def view_card_cars(self):
        from register.models import RegViewsCarsOrganization
        return RegViewsCarsOrganization.objects.filter(cars = self).filter(store = self.store).count()
    
    def get_files_count(self):
        return RefCarsOrganizationFiles.objects.filter(сars_organization = self).count()
        
    def get_files(self):
        list_files = list()
        photos_count = RefCarsOrganizationFiles.objects.filter(сars_organization = self).count()
        if photos_count > 0:
            return RefCarsOrganizationFiles.objects.filter(сars_organization = self).order_by('-main')
            for file in files:
                list_files.append(file)  
        else:
            list_files.append('/media/nophoto.png')
        return list_files

    def get_photo_mini(self):
        photos_count = RefCarsOrganizationFiles.objects.filter(сars_organization = self).filter(main = True).count()
        try:
            if photos_count > 0:
                return RefCarsOrganizationFiles.objects.filter(сars_organization = self).filter(main = True)[0].file_mini.url
            else:
                photos_count = RefCarsOrganizationFiles.objects.filter(сars_organization = self).count()
                if photos_count > 0:
                    return RefCarsOrganizationFiles.objects.filter(сars_organization = self)[0].file_bak.url
        except:
            return '/media/nophoto.png'
        return '/media/nophoto.png'
    
    def get_photo(self):
        photos_count = RefCarsOrganizationFiles.objects.filter(сars_organization = self).filter(car = True).filter(main = True).count()
        if photos_count > 0:
            return RefCarsOrganizationFiles.objects.filter(сars_organization = self).filter(main = True).filter(car = True)[0].file_bak.url
        else:
            photos_count = RefCarsOrganizationFiles.objects.filter(сars_organization = self).filter(main = True).count()
            if photos_count > 0:
                return RefCarsOrganizationFiles.objects.filter(сars_organization = self).filter(main = True)[0].file.url
        return '/media/nophoto.png'

    def logo(self):
        try:
            if self.modification_autoru != None: 
                return self.modification_autoru.model.mark.file.url
            else:
                count_avito = RefAvito.objects.filter(name = self.mark).filter(parent = None).count()
                if count_avito > 0:
                    ref_avito = RefAvito.objects.filter(name = self.mark).filter(parent = None)[0]
                    return ref_avito.get_photo()
        except:
            s = 1
        return '/media/images/kg.png'
    

    def save(self, *args, **kwargs):
        
        self.vin = self.vin.upper()
        
        if self.lo == None:
            if len(self.lo_uin) > 0:
                lo = DocLO.objects.filter(uin__icontains = self.lo_uin).first()
                if lo != None:
                    self.lo = lo

        if not self.slug:
            name_slug = transliterate(self.name) + '_' + str(self.vin[0:5]) + self.vin[15:18] + '_' + str(self.lo_link_number.replace('ПО-', ''))
            self.slug = slugify(name_slug.lower())
        
        try:
            text_search = ''
            if len(self.vin) > 4:
                text_search = text_search + self.vin + ' '
            if len(self.plate_number) > 4:
                text_search = text_search + self.plate_number + ' '
            if self.status != None:
                text_search = text_search + self.status.name + ' '
            if self.type_sale != None:
                text_search = text_search + self.type_sale.name + ' '
            if self.type_reception != None:
                text_search = text_search + self.type_reception.name + ' '
            
            if self.modification_autoru != None:
                text_search = text_search + self.modification_autoru.model.mark.name + ' '
                text_search = text_search + self.modification_autoru.model.name + ' '
                text_search = text_search + self.modification_autoru.name + ' ' 
            else:
                text_search = text_search + self.mark + ' '
                text_search = text_search + self.model + ' '
                text_search = text_search + self.modification + ' '            

            if len(self.lo_link_number) > 4:
                text_search = text_search + self.lo_link_number + ' '
            
            if len(self.color) > 4:
                text_search = text_search + self.color + ' ' 

            self.search_fields  = text_search

        except:
            s = 1

        if not self.qr:
            self.qr = ContentFile(get_qrcode(self.slug), name=self.slug)

        super().save(*args, **kwargs)
    
    def __str__(self):
        return "{} - {}({})".format(self.name, self.vin, self.vin2)

    class Meta:
        indexes = [
            models.Index(fields=['unit']),
            models.Index(fields=['slug']),
            models.Index(fields=['vin']),
            models.Index(fields=['lo_uin']),
            models.Index(fields=['lo_link_number'])
        ]
        db_table = 'refCarsOrganization'
        verbose_name = "Автомобиль организации"
        verbose_name_plural = "Автомобили организации"
        unique_together = ('vin', 'lo_uin', 'lo_link_number',)


class RefCarsOrganizationFiles(models.Model):
    сars_organization     = models.ForeignKey(RefCarsOrganization, on_delete=models.PROTECT, null=True, verbose_name="Автомобиль")
    file        = models.ImageField(upload_to='cars_images/%Y/%m/%d/', max_length=100, verbose_name="Файл", blank=True, null=True)
    file_mini   = models.ImageField(upload_to='cars_images/%Y/%m/%d/', max_length=100, verbose_name="Файл маленький", blank=True, null=True)
    file_bak    = models.ImageField(upload_to='cars_images/%Y/%m/%d/', max_length=100, verbose_name="Файл без фона", blank=True, null=True)
    main        = models.BooleanField('Главный', default=False) 
    url         = models.CharField("УРЛ", max_length=512, default='', blank=True)
    url_mini    = models.CharField("УРЛ мини", max_length=512, default='', blank=True)
    name        = models.CharField("Наименование", max_length=512, default='', blank=True)
    car         = models.BooleanField('Автомобиль', default=False) 
    processed   = models.BooleanField('Обработан', default=False) 
    date        = models.DateTimeField('Дата', default=datetime.now, blank=False, null=True)

    def is_video(self):
        list_world_name = self.file.name.lower().split('.')
        format = list_world_name[-1]
        if format.find('jpg') > -1 or format.find('jpeg') > -1 or format.find('svg') > -1 or format.find('gif') > -1 or format.find('png') > -1 or format.find('tiff') > -1:
            return False
        return True

    def __str__(self):
        return "{}".format(self.сars_organization)

    class Meta:
        indexes = [
            models.Index(fields=['сars_organization'])
        ]
        db_table = 'refCarsOrganizationFiles'
        verbose_name = "Фото автомобиля"
        verbose_name_plural = "Фотографии автомобилей"


class RefCarsOrganizationAuctionStatus(models.Model):
    name                    = models.CharField("Наименование", max_length=512, default='', blank=True)
    name_auction            = models.CharField("Наименование на сайте аукциона", max_length=512, default='', blank=True)
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'refCarsOrganizationAuctionStatus'
        verbose_name = "Автомобили для аукциона статус"
        verbose_name_plural = "Автомобили для аукциона статус"


class Auction(models.Model):
    uid                 = models.UUIDField(max_length=100, blank=True, unique=True, default=uuid.uuid4)
    status              = models.ForeignKey(RefCarsOrganizationAuctionStatus, on_delete=models.PROTECT, null=True, verbose_name="Статус")  
    number              = models.CharField('Номер', default='', null=True, max_length=25, blank=False)
    dataTime            = models.DateTimeField('Дата', default=datetime.now, blank=False)
    dateStart           = models.DateTimeField('Желаемая дата аукциона', null=True, blank=True)
    dateEnd             = models.DateTimeField('Дата завершения аукциона', null=True, blank=True)
    store               = models.ForeignKey(RefStore, on_delete=models.SET_NULL, null=True, verbose_name="Стоянка")
    user                = models.ForeignKey(User, null=True, on_delete=models.SET_NULL,verbose_name="Ответственный", blank=True)
    description         = models.CharField('Описание', default='', null=True, max_length=12500, blank=False)
    start_price         = models.IntegerField("Стартовая цена", default=0, blank=True)
    rejection_reason    = models.TextField('Причина отклонения', blank=True, null=True, max_length=1000, default='')
    winner_name         = models.TextField('Победитель наименование', blank=True, null=True, max_length=1000, default='')
    winner_phone        = models.TextField('Победитель телефон', blank=True, null=True, max_length=1000, default='')
    winner_email        = models.TextField('Победитель email', blank=True, null=True, max_length=1000, default='')
    winner_price        = models.IntegerField("Выигрышная цена", default=0, blank=True)
    pk_auction          = models.CharField('№ лота', default='', null=True, max_length=12, blank=False)

    def count_cars(self):
        return AuctionStructure.objects.filter(auction = self).count()
    
    def cars(self):
        return AuctionStructure.objects.filter(auction = self)
    
    def __str__(self):
        return "{} ({} - {}) - {}".format(self.dataTime, self.store, self.user, self.start_price)

    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['store'])
        ]
        db_table = 'auction'
        verbose_name = "Аукцион"
        verbose_name_plural = "Аукцион"


class AuctionStructure(models.Model):
    auction         = models.ForeignKey(Auction, on_delete=models.SET_NULL, null=True, verbose_name="Документ аукциона") 
    car             = models.ForeignKey(RefCarsOrganization, on_delete=models.SET_NULL, null=True, verbose_name="Автомобиль") 
    description     = models.CharField('Описание', default='', null=True, max_length=12500, blank=False)
    diagnostic      = models.CharField('Диагностика', default='', null=True, max_length=12500, blank=False)
    works           = models.CharField('Запланированные работы', default='', null=True, max_length=12500, blank=False)
    op              = models.CharField('Комментарий для ОП', default='', null=True, max_length=12500, blank=False)
    podgotovka      = models.CharField('Комментарий для подготовки', default='', null=True, max_length=12500, blank=False)
    autoteka_prev   = models.BooleanField('Показывать автотеку', default = False)
    success         = models.BooleanField('Проверено',  default = False)
    
    files_glav      = models.CharField('Главная',       default='', null=True, max_length=1000,     blank=False)
    files_car       = models.CharField('Внешний вид',   default='', null=True, max_length=12500,    blank=False)
    files_salon     = models.CharField('Салон',         default='', null=True, max_length=12500,    blank=False)
    files_shema     = models.CharField('Схема',         default='', null=True, max_length=12500,    blank=False)
    files_damages   = models.CharField('Повреждения',   default='', null=True, max_length=12500,    blank=False)
    files_kolesa    = models.CharField('Колеса',        default='', null=True, max_length=12500,    blank=False)
    files_diagnostic= models.CharField('Диагностика',   default='', null=True, max_length=12500,    blank=False)

    def info_car_vnesh(self):
        list_links = list()
        list_qyeryset = AuctionStructureFiles.objects.filter(auction_structure = self).filter(auction_structure = self).filter(type_file = 'vnesh')
        for list_qyery in list_qyeryset:
            list_links.append(list_qyery.file.url)
        return list_links
    
    def info_car_salon(self):
        list_links = list()
        list_qyeryset = AuctionStructureFiles.objects.filter(auction_structure = self).filter(type_file = 'salon')
        for list_qyery in list_qyeryset:
            list_links.append(list_qyery.file.url)
        return list_links
    
    def info_car_shema(self):
        list_links = list()
        list_qyeryset = AuctionStructureFiles.objects.filter(auction_structure = self).filter(type_file = 'shema')
        for list_qyery in list_qyeryset:
            list_links.append(list_qyery.file.url)
        return list_links
    
    def info_car_wheels(self):
        list_links = list()
        list_qyeryset = AuctionStructureFiles.objects.filter(auction_structure = self).filter(type_file = 'kolesa')
        for list_qyery in list_qyeryset:
            list_links.append(list_qyery.file.url)
        return list_links
    
    def info_car_damages(self):
        list_links = list()
        list_qyeryset = AuctionStructureFiles.objects.filter(auction_structure = self).filter(type_file = 'damage')
        for list_qyery in list_qyeryset:
            list_links.append(list_qyery.file.url)
        return list_links

    def info_car_auction_data(self):
        from task_manager.views import info_car_auction
        return info_car_auction(self.car.slug)

    def __str__(self):
        return "{} ({} - {})".format(self.auction, self.car, self.description)

    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['auction'])
        ]
        db_table = 'auctionStructure'
        verbose_name = "Аукцион состав"
        verbose_name_plural = "Аукцион состав"


class AuctionStructureFiles(models.Model):
    auction_structure     = models.ForeignKey(AuctionStructure, on_delete=models.PROTECT, null=True, verbose_name="Автомобиль аукциона")
    file        = models.ImageField(upload_to='cars_images_auction/%Y/%m/%d/', max_length=100, verbose_name="Файл", blank=True, null=True)
    file_mini   = models.ImageField(upload_to='cars_images_auction/%Y/%m/%d/', max_length=100, verbose_name="Файл маленький", blank=True, null=True)
    file_bak    = models.ImageField(upload_to='cars_images_auction/%Y/%m/%d/', max_length=100, verbose_name="Файл без фона", blank=True, null=True)
    main        = models.BooleanField('Главный', default=False) 
    url         = models.CharField("УРЛ", max_length=512, default='', blank=True)
    url_mini    = models.CharField("УРЛ мини", max_length=512, default='', blank=True)
    name        = models.CharField("Наименование", max_length=512, default='', blank=True)
    car         = models.BooleanField('Автомобиль', default=False) 
    type_file   = models.CharField("тип файла", max_length=512, default='', blank=True)
    
    def is_video(self):
        list_world_name = self.file.name.lower().split('.')
        format = list_world_name[-1]
        if format.find('jpg') > -1 or format.find('jpeg') > -1 or format.find('svg') > -1 or format.find('gif') > -1 or format.find('png') > -1 or format.find('tiff') > -1:
            return False
        return True

    def __str__(self):
        return "{}".format(self.auction_structure)

    class Meta:
        indexes = [
            models.Index(fields=['auction_structure'])
        ]
        db_table = 'auctionStructureFiles'
        verbose_name = "Фото автомобиля для аукциона"
        verbose_name_plural = "Фотографии автомобиля для аукциона"


# Настройки новых автомобилей
class RefRulesCars(models.Model):
    brand           = models.ForeignKey(AutoruMark, null=True, on_delete=models.CASCADE, verbose_name='Марка / бренд')
    stage           = models.ForeignKey(RefStagePrice, null=True, on_delete=models.CASCADE, verbose_name='Этап УС')
    km_index        = models.FloatField("Индекс КМ", default=0.0, blank=True)
    km_percent      = models.FloatField("Правило КМ", default=0.0, blank=True)

    def __str__(self):
        return "{} / {} ({} - {})".format(self.brand.name, self.stage.name, self.km_index, self.km_percent) 

    class Meta:
        db_table = 'RefRulesCars'
        verbose_name = "Настройка правил новых ам"
        verbose_name_plural = "Настройки правил новых ам"