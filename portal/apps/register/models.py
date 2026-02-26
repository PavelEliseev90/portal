from time import time
from django.db import models
from django.utils.safestring import mark_safe
from documents.models import DocRLK, DocLO, DocCarShipment
from refs.models import RefTypeEngine, RefTypeKpp, RefTypeBody, RefTypeEvaluationCarsOrganization, RefAvito, RefAvitoComplectation, RefStatusEstimation, RefMarkTyres, RefWidthTyres, RefProfileTyres, RefRadius, RefSezonTyres, RefTypeDisk, RefDiaDisk, RefEtDisk, RefPsdDisk, RefOrganization, RefFilial, RefTypeReceptionCarsOrganization, AutoruModification, RefGroupProduct, RefStaff, RefCategoryProduct, RefPageOcenka, RefUnit, RefCarsOrganization, RefEventCarsOrganization, RefStore, RefManufacturer, AutoruComplectation
from ckeditor_uploader.fields import RichTextUploadingField
from datetime import datetime, timedelta
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from itertools import chain
from django.contrib.auth.models import User, Group
import uuid
from transliterate import translit
from django.utils.text import slugify
import qrcode
import base64
import io
from django.core.files.base import ContentFile
import random
from django.db.models import Count, Sum, Max, Avg, F, OuterRef, Subquery, Sum, Q, Min
import json
from avtosalon.models import Avtohub

from django.db.models.signals import post_delete, post_save

from changelog.mixins import ChangeloggableMixin
from changelog.signals import journal_save_handler, journal_delete_handler


def random_slug():
    return ''.join([random.choice(list('123456789qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM')) for x in range(8)])


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
    
    slug = 'https://ah.kors-group.com/es/' + name + '/'

    qr_code_image   = qrcode.make(slug)
    buffer          = io.BytesIO()
    qr_code_image.save(buffer, format="PNG")
    qr_code_image_data = buffer.getvalue()
    
    return qr_code_image_data


def add_swap(estimation):
    try:
        
        if estimation.end_estimation != None:
            swap = RegSwapKors()
            swap.estimation = estimation
            swap.save()
        else:
            if estimation.page_soglasovanie != None:
                swap = RegSwapKors()
                swap.estimation = estimation
                swap.save()

    except:
        s = 1


def save_directory():
    path = settings.MEDIA_ROOT_DOP
    return FileSystemStorage(location=path)


class SettingsMatrixAuction(models.Model):
    charge_bcp_200              = models.IntegerField('Базовая наценка для определения БЦП ЦГ200', default=0, null=False, blank=True)       #'// 
    min_km_200                  = models.IntegerField('Минимальный КМ ЦГ200', default=0, null=False, blank=True)
    charge_km_stage_1_200       = models.IntegerField('Умеренное снижение ЦГ200', default=0, null=False, blank=True)
    charge_km_stage_2_200       = models.IntegerField('Среднее снижение ЦГ200', default=0, null=False, blank=True)
    charge_km_stage_3_200       = models.IntegerField('Значительное снижение КМ ЦГ200', default=0, null=False, blank=True)

    charge_bcp_400              = models.IntegerField('Базовая наценка для определения БЦП ЦГ400', default=0, null=False, blank=True)       #'// 
    min_km_400                  = models.IntegerField('Минимальный КМ ЦГ400', default=0, null=False, blank=True)
    charge_km_stage_1_400       = models.IntegerField('Умеренное снижение ЦГ400', default=0, null=False, blank=True)
    charge_km_stage_2_400       = models.IntegerField('Среднее снижение ЦГ400', default=0, null=False, blank=True)
    charge_km_stage_3_400       = models.IntegerField('Значительное снижение КМ ЦГ400', default=0, null=False, blank=True)

    charge_bcp_700              = models.IntegerField('Базовая наценка для определения БЦП ЦГ700', default=0, null=False, blank=True)       #'// 
    min_km_700                  = models.IntegerField('Минимальный КМ ЦГ700', default=0, null=False, blank=True)
    charge_km_stage_1_700       = models.IntegerField('Умеренное снижение ЦГ700', default=0, null=False, blank=True)
    charge_km_stage_2_700       = models.IntegerField('Среднее снижение ЦГ700', default=0, null=False, blank=True)
    charge_km_stage_3_700       = models.IntegerField('Значительное снижение КМ ЦГ700', default=0, null=False, blank=True)

    charge_bcp_1200              = models.IntegerField('Базовая наценка для определения БЦП ЦГ1200', default=0, null=False, blank=True)       #'// 
    min_km_1200                  = models.IntegerField('Минимальный КМ ЦГ1200', default=0, null=False, blank=True)
    charge_km_stage_1_1200       = models.IntegerField('Умеренное снижение ЦГ1200', default=0, null=False, blank=True)
    charge_km_stage_2_1200       = models.IntegerField('Среднее снижение ЦГ1200', default=0, null=False, blank=True)
    charge_km_stage_3_1200       = models.IntegerField('Значительное снижение КМ ЦГ1200', default=0, null=False, blank=True)

    charge_bcp_2000              = models.IntegerField('Базовая наценка для определения БЦП ЦГ1200', default=0, null=False, blank=True)       #'// 
    min_km_2000                  = models.IntegerField('Минимальный КМ ЦГ2000', default=0, null=False, blank=True)
    charge_km_stage_1_2000       = models.IntegerField('Умеренное снижение ЦГ2000', default=0, null=False, blank=True)
    charge_km_stage_2_2000       = models.IntegerField('Среднее снижение ЦГ2000', default=0, null=False, blank=True)
    charge_km_stage_3_2000       = models.IntegerField('Значительное снижение КМ ЦГ2000', default=0, null=False, blank=True)

    charge_bcp_3000              = models.IntegerField('Базовая наценка для определения БЦП ЦГ3000', default=0, null=False, blank=True)       #'// 
    min_km_3000                  = models.IntegerField('Минимальный КМ ЦГ3000', default=0, null=False, blank=True)
    charge_km_stage_1_3000       = models.IntegerField('Умеренное снижение ЦГ3000', default=0, null=False, blank=True)
    charge_km_stage_2_3000       = models.IntegerField('Среднее снижение ЦГ3000', default=0, null=False, blank=True)
    charge_km_stage_3_3000       = models.IntegerField('Значительное снижение КМ ЦГ3000', default=0, null=False, blank=True)

    charge_bcp_5000              = models.IntegerField('Базовая наценка для определения БЦП ЦГ5000', default=0, null=False, blank=True)       #'// 
    min_km_5000                  = models.IntegerField('Минимальный КМ ЦГ5000', default=0, null=False, blank=True)
    charge_km_stage_1_5000       = models.IntegerField('Умеренное снижение ЦГ5000', default=0, null=False, blank=True)
    charge_km_stage_2_5000       = models.IntegerField('Среднее снижение ЦГ5000', default=0, null=False, blank=True)
    charge_km_stage_3_5000       = models.IntegerField('Значительное снижение КМ ЦГ5000', default=0, null=False, blank=True)

    charge_bcp_5001              = models.IntegerField('Базовая наценка для определения БЦП ЦГ5001', default=0, null=False, blank=True)       #'// 
    min_km_5001                  = models.IntegerField('Минимальный КМ ЦГ5001', default=0, null=False, blank=True)
    charge_km_stage_1_5001       = models.IntegerField('Умеренное снижение ЦГ5001', default=0, null=False, blank=True)
    charge_km_stage_2_5001       = models.IntegerField('Среднее снижение ЦГ5001', default=0, null=False, blank=True)
    charge_km_stage_3_5001       = models.IntegerField('Значительное снижение КМ ЦГ5001', default=0, null=False, blank=True)

    def __str__(self):
        return "{}".format(self.pk)

    class Meta:
        db_table = 'settingsMatrixAuction'
        verbose_name = "Матрица расчета БЦП аукцион"
        verbose_name_plural = "Матрица расчета БЦП аукцион"


class RegEstimationsSettings(models.Model):
    name                    = models.CharField("Наименование", null=True, blank=True, max_length=512)
    
    cleaning_int            = models.IntegerField('Требуеться химчистка',                   default=0, null=True, blank=True)       #'// 
    damage_kpp_int          = models.IntegerField('Повреждения рычага кпп',                 default=0, null=True, blank=True)       #'// 
    damage_wheel_int        = models.IntegerField('Повреждения / затертый руль',            default=0, null=True, blank=True)       #'// 
    damage_pedal_int        = models.IntegerField('Повреждения / затертые педали',          default=0, null=True, blank=True)       #'// 
    damage_door_int         = models.IntegerField('Повреждения / затертые карты дверей',    default=0, null=True, blank=True)       #'// 
    damage_seat_int         = models.IntegerField('Повреждения / затертые сиденья',         default=0, null=True, blank=True)       #'// 
    
    hand_brake              = models.IntegerField('работоспособность ручного тормоза',      default=0, null=True, blank=True)       #'// 
    conductor               = models.IntegerField('работоспособность кондиционера',         default=0, null=True, blank=True)       #'// 
    wiper                   = models.IntegerField('работоспособность стеклоочистителя',     default=0, null=True, blank=True)       #'// 
    signal                  = models.IntegerField('работоспособность сигнала',              default=0, null=True, blank=True)       #'// 
    power_windows           = models.IntegerField('работоспособность стеклоподьемников',    default=0, null=True, blank=True)       #'// 
    seat_belt               = models.IntegerField('работоспособность ремней безопастности', default=0, null=True, blank=True)       #'// 

    carap                   = models.IntegerField('Многочисленые царапины',             default=0, null=True, blank=True)       #'// 
    vmyat                   = models.IntegerField('Многочисленые вмятины',              default=0, null=True, blank=True)       #'// 
    skol                    = models.IntegerField('Многочисленные сколы',               default=0, null=True, blank=True)       #'// 
    rzav                    = models.IntegerField('Многочисленные очаги ржавчины',      default=0, null=True, blank=True)       #'// 

    windshield_error_int    = models.IntegerField('Лобовое стекло с повреждениями',     default=0, null=True, blank=True)       #'// 
    light_error_int         = models.IntegerField('Световые приборы есть проблемы',     default=0, null=True, blank=True)       #'// 

    engine_danger_amount        = models.IntegerField('Двигатель не исправен сумма',      default=0, null=True, blank=True)       #'// 
    engine_danger_kf            = models.IntegerField('Двигатель не исправен коэфицент',      default=0, null=True, blank=True)       #'// 
    engine_danger_amount_min    = models.IntegerField('Двигатель не исправен мин сумма',      default=0, null=True, blank=True)       #'// 

    engine_warning_amount        = models.IntegerField('Двигатель есть замечания сумма',      default=0, null=True, blank=True)       #'// 
    engine_warning_kf            = models.IntegerField('Двигатель есть замечания коэфицент',      default=0, null=True, blank=True)       #'// 
    engine_warning_amount_min    = models.IntegerField('Двигатель есть замечания мин сумма',      default=0, null=True, blank=True)       #'// 


    engine_dt_danger_amount        = models.IntegerField('Двигатель дизель не исправен сумма',      default=0, null=True, blank=True)       #'// 
    engine_dt_danger_kf            = models.IntegerField('Двигатель дизель не исправен коэфицент',      default=0, null=True, blank=True)       #'// 
    engine_dt_danger_amount_min    = models.IntegerField('Двигатель дизель не исправен мин сумма',      default=0, null=True, blank=True)       #'// 

    engine_dt_warning_amount        = models.IntegerField('Двигатель дизель есть замечания сумма',      default=0, null=True, blank=True)       #'// 
    engine_dt_warning_kf            = models.IntegerField('Двигатель дизель есть замечания коэфицент',      default=0, null=True, blank=True)       #'// 
    engine_dt_warning_amount_min    = models.IntegerField('Двигатель дизель есть замечания мин сумма',      default=0, null=True, blank=True)       #'// 

    gear_at_danger_amount        = models.IntegerField('КПП автомат не исправен сумма',      default=0, null=True, blank=True)       #'// 
    gear_at_danger_kf            = models.IntegerField('КПП автомат не исправен коэфицент',      default=0, null=True, blank=True)       #'// 
    gear_at_danger_amount_min    = models.IntegerField('КПП автомат не исправен мин сумма',      default=0, null=True, blank=True)       #'// 

    gear_at_warning_amount        = models.IntegerField('КПП автомат есть замечания сумма',      default=0, null=True, blank=True)       #'// 
    gear_at_warning_kf            = models.IntegerField('КПП автомат есть замечания коэфицент',      default=0, null=True, blank=True)       #'// 
    gear_at_warning_amount_min    = models.IntegerField('КПП автомат есть замечания мин сумма',      default=0, null=True, blank=True)       #'// 

    gear_amt_danger_amount        = models.IntegerField('КПП робот не исправен сумма',      default=0, null=True, blank=True)       #'// 
    gear_amt_danger_kf            = models.IntegerField('КПП робот не исправен коэфицент',      default=0, null=True, blank=True)       #'// 
    gear_amt_danger_amount_min    = models.IntegerField('КПП робот не исправен мин сумма',      default=0, null=True, blank=True)       #'// 

    gear_amt_warning_amount        = models.IntegerField('КПП робот есть замечания сумма',      default=0, null=True, blank=True)       #'// 
    gear_amt_warning_kf            = models.IntegerField('КПП робот есть замечания коэфицент',      default=0, null=True, blank=True)       #'// 
    gear_amt_warning_amount_min    = models.IntegerField('КПП робот есть замечания мин сумма',      default=0, null=True, blank=True)       #'// 

    gear_cvt_danger_amount        = models.IntegerField('КПП вариатор не исправен сумма',      default=0, null=True, blank=True)       #'// 
    gear_cvt_danger_kf            = models.IntegerField('КПП вариатор не исправен коэфицент',      default=0, null=True, blank=True)       #'// 
    gear_cvt_danger_amount_min    = models.IntegerField('КПП вариатор не исправен мин сумма',      default=0, null=True, blank=True)       #'// 

    gear_cvt_warning_amount        = models.IntegerField('КПП вариатор есть замечания сумма',      default=0, null=True, blank=True)       #'// 
    gear_cvt_warning_kf            = models.IntegerField('КПП вариатор есть замечания коэфицент',      default=0, null=True, blank=True)       #'// 
    gear_cvt_warning_amount_min    = models.IntegerField('КПП вариатор есть замечания мин сумма',      default=0, null=True, blank=True)       #'// 

    gear_mt_danger_amount        = models.IntegerField('КПП механика не исправен сумма',      default=0, null=True, blank=True)       #'// 
    gear_mt_danger_kf            = models.IntegerField('КПП механика не исправен коэфицент',      default=0, null=True, blank=True)       #'// 
    gear_mt_danger_amount_min    = models.IntegerField('КПП механика не исправен мин сумма',      default=0, null=True, blank=True)       #'// 

    gear_mt_warning_amount        = models.IntegerField('КПП механика есть замечания сумма',      default=0, null=True, blank=True)       #'// 
    gear_mt_warning_kf            = models.IntegerField('КПП механика есть замечания коэфицент',      default=0, null=True, blank=True)       #'// 
    gear_mt_warning_amount_min    = models.IntegerField('КПП механика есть замечания мин сумма',      default=0, null=True, blank=True)       #'// 

    suspension_danger_amount        = models.IntegerField('Подвеска не исправен сумма',      default=0, null=True, blank=True)       #'// 
    suspension_danger_kf            = models.IntegerField('Подвеска не исправен коэфицент',      default=0, null=True, blank=True)       #'// 
    suspension_danger_amount_min    = models.IntegerField('Подвеска не исправен мин сумма',      default=0, null=True, blank=True)       #'// 

    suspension_warning_amount        = models.IntegerField('Подвеска есть замечания сумма',      default=0, null=True, blank=True)       #'// 
    suspension_warning_kf            = models.IntegerField('Подвеска есть замечания коэфицент',      default=0, null=True, blank=True)       #'// 
    suspension_warning_amount_min    = models.IntegerField('Подвеска есть замечания мин сумма',      default=0, null=True, blank=True)       #'// 
 
    system_og_danger_amount        = models.IntegerField('Подвеска не исправен сумма',      default=0, null=True, blank=True)       #'// 
    system_og_danger_kf            = models.IntegerField('Подвеска не исправен коэфицент',      default=0, null=True, blank=True)       #'// 
    system_og_danger_amount_min    = models.IntegerField('Подвеска не исправен мин сумма',      default=0, null=True, blank=True)       #'// 

    system_og_warning_amount        = models.IntegerField('Подвеска есть замечания сумма',      default=0, null=True, blank=True)       #'// 
    system_og_warning_kf            = models.IntegerField('Подвеска есть замечания коэфицент',      default=0, null=True, blank=True)       #'// 
    system_og_warning_amount_min    = models.IntegerField('Подвеска есть замечания мин сумма',      default=0, null=True, blank=True)       #'// 

    all_percent_financity           = models.FloatField("Процент финансирования", default=0.0, blank=True, null=True)
    all_days_stok_financity         = models.FloatField("Дней на складе для расчета финансирования", default=0.0, blank=True, null=True)
    
    percent_financity_200           = models.FloatField("Процент финансирования 200", default=0.0, blank=True, null=True)
    days_stok_financity_200         = models.FloatField("Дней на складе для расчета финансирования 200", default=0.0, blank=True, null=True)
    
    percent_financity_400           = models.FloatField("Процент финансирования 400", default=0.0, blank=True, null=True)
    days_stok_financity_400         = models.FloatField("Дней на складе для расчета финансирования 400", default=0.0, blank=True, null=True)

    percent_financity_700           = models.FloatField("Процент финансирования 700", default=0.0, blank=True, null=True)
    days_stok_financity_700         = models.FloatField("Дней на складе для расчета финансирования 700", default=0.0, blank=True, null=True)

    percent_financity_1200           = models.FloatField("Процент финансирования 1200", default=0.0, blank=True, null=True)
    days_stok_financity_1200         = models.FloatField("Дней на складе для расчета финансирования 1200", default=0.0, blank=True, null=True)

    percent_financity_2000           = models.FloatField("Процент финансирования 2000", default=0.0, blank=True, null=True)
    days_stok_financity_2000         = models.FloatField("Дней на складе для расчета финансирования 2000", default=0.0, blank=True, null=True)

    percent_financity_3000           = models.FloatField("Процент финансирования 3000", default=0.0, blank=True, null=True)
    days_stok_financity_3000         = models.FloatField("Дней на складе для расчета финансирования 3000", default=0.0, blank=True, null=True)

    percent_financity_5000           = models.FloatField("Процент финансирования 5000", default=0.0, blank=True, null=True)
    days_stok_financity_5000         = models.FloatField("Дней на складе для расчета финансирования 5000", default=0.0, blank=True, null=True)

    percent_financity_5001           = models.FloatField("Процент финансирования 5001", default=0.0, blank=True, null=True)
    days_stok_financity_5001         = models.FloatField("Дней на складе для расчета финансирования 5001", default=0.0, blank=True, null=True)

    battery_200         = models.FloatField("Процент коррекции цна battery_200", default=0.0, blank=True, null=True)
    battery_400         = models.FloatField("Процент коррекции цна battery_400", default=0.0, blank=True, null=True)
    battery_700         = models.FloatField("Процент коррекции цна battery_700", default=0.0, blank=True, null=True)
    battery_1200         = models.FloatField("Процент коррекции цна battery_1200", default=0.0, blank=True, null=True)
    battery_2000         = models.FloatField("Процент коррекции цна battery_2000", default=0.0, blank=True, null=True)
    battery_3000         = models.FloatField("Процент коррекции цна battery_3000", default=0.0, blank=True, null=True)
    battery_5000         = models.FloatField("Процент коррекции цна battery_5000", default=0.0, blank=True, null=True)
    battery_5001         = models.FloatField("Процент коррекции цна battery_5001", default=0.0, blank=True, null=True)
    
    izp_200         = models.FloatField("Процент коррекции цна 200", default=0.0, blank=True, null=True)
    izp_200_v       = models.IntegerField('Коррекция цна 200 вариант',      default=0, null=True, blank=True)       #'// 
    auction_kf_200  = models.FloatField('% от расчитанной цены аукцион цг 200',      default=0.0, blank=True, null=True)

    izp_400         = models.FloatField("Процент коррекции цна 400", default=0.0, blank=True, null=True)
    izp_400_v       = models.IntegerField('Коррекция цна 400 вариант',      default=0, null=True, blank=True)       #'// 
    auction_kf_400  = models.FloatField('% от расчитанной цены аукцион цг 400',      default=0.0, blank=True, null=True)

    izp_700             = models.FloatField("Процент коррекции цна 700", default=0.0, blank=True, null=True)
    izp_700_v           = models.IntegerField('Коррекция цна 700 вариант',      default=0, null=True, blank=True)       #'// 
    auction_kf_700      = models.FloatField('% от расчитанной цены аукцион цг 700',      default=0.0, blank=True, null=True)

    izp_1200            = models.FloatField("Процент коррекции цна 1200", default=0.0, blank=True, null=True)
    izp_1200_v          = models.IntegerField('Коррекция цна 1200 вариант',      default=0, null=True, blank=True)       #'// 
    auction_kf_1200     = models.FloatField('% от расчитанной цены аукцион цг 1200',      default=0.0, blank=True, null=True)
    
    izp_2000     = models.FloatField("Процент коррекции цна 2 000", default=0.0, blank=True, null=True)
    izp_2000_v   = models.IntegerField('Коррекция цна 2 000 вариант',      default=0, null=True, blank=True)       #'// 
    auction_kf_2000     = models.FloatField('% от расчитанной цены аукцион цг 2 000',      default=0.0, blank=True, null=True)

    izp_3000     = models.FloatField("Процент коррекции цна 3000", default=0.0, blank=True, null=True)
    izp_3000_v   = models.IntegerField('Коррекция цна 3000 вариант',      default=0, null=True, blank=True)       #'//
    auction_kf_3000     = models.FloatField('% от расчитанной цены аукцион цг 3 000',      default=0.0, blank=True, null=True)

    izp_5000     = models.FloatField("Процент коррекции цна 5000", default=0.0, blank=True, null=True)
    izp_5000_v   = models.IntegerField('Коррекция цна 5000 вариант',      default=0, null=True, blank=True)       #'//
    auction_kf_5000     = models.FloatField('% от расчитанной цены аукцион цг 5 000',      default=0.0, blank=True, null=True)

    izp_5001     = models.FloatField("Процент коррекции цна 5001", default=0.0, blank=True, null=True)
    izp_5001_v   = models.IntegerField('Коррекция цна 5001 вариант',      default=0, null=True, blank=True)       #'//
    auction_kf_5001     = models.FloatField('% от расчитанной цены аукцион цг 5 000 +',      default=0.0, blank=True, null=True)

    max_kf_iznos = models.FloatField("Максимальный % разницы коэфицента износа", default=0.0, blank=True, null=True)

    wheel_danger_amount_200             = models.IntegerField('Рулевая рейка не исправен сумма 200',      default=0, null=True, blank=True)       #'// 
    wheel_danger_kf_200                 = models.IntegerField('Рулевая рейка не исправен коэфицент 200',      default=0, null=True, blank=True)       #'// 
    wheel_danger_amount_min_200         = models.IntegerField('Рулевая рейка не исправен мин сумма 200',      default=0, null=True, blank=True)       #'// 

    wheel_warning_amount_200        	= models.IntegerField('Рулевая рейка есть замечания сумма 200',      default=0, null=True, blank=True)       #'// 
    wheel_warning_kf_200            	= models.IntegerField('Рулевая рейка есть замечания коэфицент 200',      default=0, null=True, blank=True)       #'// 
    wheel_warning_amount_min_200    	= models.IntegerField('Рулевая рейка есть замечания мин сумма 200',      default=0, null=True, blank=True)       #'// 
    
    brake_danger_amount_200              = models.IntegerField('Тормозная система не исправна сумма 200',      default=0, null=True, blank=True)
    brake_danger_kf_200                  = models.IntegerField('Тормозная система не исправна коэффициент 200', default=0, null=True, blank=True)
    brake_danger_amount_min_200          = models.IntegerField('Тормозная система не исправна мин сумма 200',   default=0, null=True, blank=True)
    brake_warning_amount_200             = models.IntegerField('Тормозная система есть замечания сумма 200',    default=0, null=True, blank=True)
    brake_warning_kf_200                 = models.IntegerField('Тормозная система есть замечания коэффициент 200', default=0, null=True, blank=True)
    brake_warning_amount_min_200         = models.IntegerField('Тормозная система есть замечания мин сумма 200', default=0, null=True, blank=True)
    
    subframe_danger_amount_200              = models.IntegerField('Подрамник не исправен сумма 200',      default=0, null=True, blank=True)
    subframe_danger_kf_200                  = models.IntegerField('Подрамник не исправен коэффициент 200', default=0, null=True, blank=True)
    subframe_danger_amount_min_200          = models.IntegerField('Подрамник не исправен мин сумма 200',   default=0, null=True, blank=True)
    subframe_warning_amount_200             = models.IntegerField('Подрамник есть замечания сумма 200',    default=0, null=True, blank=True)
    subframe_warning_kf_200                 = models.IntegerField('Подрамник есть замечания коэффициент 200', default=0, null=True, blank=True)
    subframe_warning_amount_min_200         = models.IntegerField('Подрамник есть замечания мин сумма 200', default=0, null=True, blank=True)
    
    conditioner_danger_amount_200        = models.IntegerField('Кондиционер не исправен сумма 200',      default=0, null=True, blank=True)       #'// 
    conditioner_danger_kf_200            = models.IntegerField('Кондиционер не исправен коэфицент 200',      default=0, null=True, blank=True)       #'// 
    conditioner_danger_amount_min_200    = models.IntegerField('Кондиционер не исправен мин сумма 200',      default=0, null=True, blank=True)       #'// 

    conditioner_warning_amount_200          = models.IntegerField('Кондиционер есть замечания сумма 200',      default=0, null=True, blank=True)       #'// 
    conditioner_warning_kf_200            	= models.IntegerField('Кондиционер есть замечания коэфицент 200',      default=0, null=True, blank=True)       #'// 
    conditioner_warning_amount_min_200    	= models.IntegerField('Кондиционер есть замечания мин сумма 200',      default=0, null=True, blank=True)       #'// 

    turbo_danger_amount_200                 = models.IntegerField('Турбо не исправен сумма 200',      default=0, null=True, blank=True)       #'// 
    turbo_danger_kf_200                     = models.IntegerField('Турбо не исправен коэфицент 200',      default=0, null=True, blank=True)       #'// 
    turbo_danger_amount_min_200             = models.IntegerField('Турбо не исправен мин сумма 200',      default=0, null=True, blank=True)       #'// 

    turbo_warning_amount_200            = models.IntegerField('Турбо есть замечания сумма 200',      default=0, null=True, blank=True)       #'// 
    turbo_warning_kf_200            	= models.IntegerField('Турбо есть замечания коэфицент 200',      default=0, null=True, blank=True)       #'// 
    turbo_warning_amount_min_200    	= models.IntegerField('Турбо есть замечания мин сумма 200',      default=0, null=True, blank=True)       #'// 

    engine_danger_amount_200        = models.IntegerField('Двигатель не исправен сумма 200',      default=0, null=True, blank=True)       #'// 
    engine_danger_kf_200            = models.IntegerField('Двигатель не исправен коэфицент 200',      default=0, null=True, blank=True)       #'// 
    engine_danger_amount_min_200    = models.IntegerField('Двигатель не исправен мин сумма 200',      default=0, null=True, blank=True)       #'// 

    engine_warning_amount_200        	= models.IntegerField('Двигатель есть замечания сумма 200',      default=0, null=True, blank=True)       #'// 
    engine_warning_kf_200            	= models.IntegerField('Двигатель есть замечания коэфицент 200',      default=0, null=True, blank=True)       #'// 
    engine_warning_amount_min_200    	= models.IntegerField('Двигатель есть замечания мин сумма 200',      default=0, null=True, blank=True)       #'// 

    engine_dt_danger_amount_200        = models.IntegerField('Двигатель дизель не исправен сумма 200',      default=0, null=True, blank=True)       #'// 
    engine_dt_danger_kf_200            = models.IntegerField('Двигатель дизель не исправен коэфицент 200',      default=0, null=True, blank=True)       #'// 
    engine_dt_danger_amount_min_200    = models.IntegerField('Двигатель дизель не исправен мин сумма 200',      default=0, null=True, blank=True)       #'// 

    engine_dt_warning_amount_200        = models.IntegerField('Двигатель дизель есть замечания сумма 200',      default=0, null=True, blank=True)       #'// 
    engine_dt_warning_kf_200            = models.IntegerField('Двигатель дизель есть замечания коэфицент 200',      default=0, null=True, blank=True)       #'// 
    engine_dt_warning_amount_min_200    = models.IntegerField('Двигатель дизель есть замечания мин сумма 200',      default=0, null=True, blank=True)       #'// 

    gear_at_danger_amount_200        = models.IntegerField('КПП автомат не исправен сумма 200',      default=0, null=True, blank=True)       #'// 
    gear_at_danger_kf_200            = models.IntegerField('КПП автомат не исправен коэфицент 200',      default=0, null=True, blank=True)       #'// 
    gear_at_danger_amount_min_200    = models.IntegerField('КПП автомат не исправен мин сумма 200',      default=0, null=True, blank=True)       #'// 

    gear_at_warning_amount_200        = models.IntegerField('КПП автомат есть замечания сумма',      default=0, null=True, blank=True)       #'// 
    gear_at_warning_kf_200            = models.IntegerField('КПП автомат есть замечания коэфицент 200',      default=0, null=True, blank=True)       #'// 
    gear_at_warning_amount_min_200    = models.IntegerField('КПП автомат есть замечания мин сумма 200',      default=0, null=True, blank=True)       #'// 

    gear_amt_danger_amount_200        = models.IntegerField('КПП робот не исправен сумма 200',      default=0, null=True, blank=True)       #'// 
    gear_amt_danger_kf_200            = models.IntegerField('КПП робот не исправен коэфицент 200',      default=0, null=True, blank=True)       #'// 
    gear_amt_danger_amount_min_200    = models.IntegerField('КПП робот не исправен мин сумма 200',      default=0, null=True, blank=True)       #'// 

    gear_amt_warning_amount_200        = models.IntegerField('КПП робот есть замечания сумма 200',      default=0, null=True, blank=True)       #'// 
    gear_amt_warning_kf_200            = models.IntegerField('КПП робот есть замечания коэфицент 200',      default=0, null=True, blank=True)       #'// 
    gear_amt_warning_amount_min_200    = models.IntegerField('КПП робот есть замечания мин сумма 200',      default=0, null=True, blank=True)       #'// 

    gear_cvt_danger_amount_200        = models.IntegerField('КПП вариатор не исправен сумма 200',      default=0, null=True, blank=True)       #'// 
    gear_cvt_danger_kf_200            = models.IntegerField('КПП вариатор не исправен коэфицент 200',      default=0, null=True, blank=True)       #'// 
    gear_cvt_danger_amount_min_200    = models.IntegerField('КПП вариатор не исправен мин сумма 200',      default=0, null=True, blank=True)       #'// 

    gear_cvt_warning_amount_200        = models.IntegerField('КПП вариатор есть замечания сумма 200',      default=0, null=True, blank=True)       #'// 
    gear_cvt_warning_kf_200            = models.IntegerField('КПП вариатор есть замечания коэфицент 200',      default=0, null=True, blank=True)       #'// 
    gear_cvt_warning_amount_min_200    = models.IntegerField('КПП вариатор есть замечания мин сумма 200',      default=0, null=True, blank=True)       #'// 

    gear_mt_danger_amount_200        = models.IntegerField('КПП механика не исправен сумма 200',      default=0, null=True, blank=True)       #'// 
    gear_mt_danger_kf_200            = models.IntegerField('КПП механика не исправен коэфицент 200',      default=0, null=True, blank=True)       #'// 
    gear_mt_danger_amount_min_200    = models.IntegerField('КПП механика не исправен мин сумма 200',      default=0, null=True, blank=True)       #'// 

    gear_mt_warning_amount_200        = models.IntegerField('КПП механика есть замечания сумма 200',      default=0, null=True, blank=True)       #'// 
    gear_mt_warning_kf_200            = models.IntegerField('КПП механика есть замечания коэфицент 200',      default=0, null=True, blank=True)       #'// 
    gear_mt_warning_amount_min_200    = models.IntegerField('КПП механика есть замечания мин сумма 200',      default=0, null=True, blank=True)       #'// 

    suspension_danger_amount_200        = models.IntegerField('Подвеска не исправен сумма 200',      default=0, null=True, blank=True)       #'// 
    suspension_danger_kf_200            = models.IntegerField('Подвеска не исправен коэфицент 200',      default=0, null=True, blank=True)       #'// 
    suspension_danger_amount_min_200    = models.IntegerField('Подвеска не исправен мин сумма 200',      default=0, null=True, blank=True)       #'// 

    suspension_warning_amount_200        = models.IntegerField('Подвеска есть замечания сумма 200',      default=0, null=True, blank=True)       #'// 
    suspension_warning_kf_200            = models.IntegerField('Подвеска есть замечания коэфицент 200',      default=0, null=True, blank=True)       #'// 
    suspension_warning_amount_min_200    = models.IntegerField('Подвеска есть замечания мин сумма 200',      default=0, null=True, blank=True)       #'// 
    
    system_og_danger_amount_200        = models.IntegerField('Подвеска не исправен сумма 200',      default=0, null=True, blank=True)       #'// 
    system_og_danger_kf_200            = models.IntegerField('Подвеска не исправен коэфицент 200',      default=0, null=True, blank=True)       #'// 
    system_og_danger_amount_min_200    = models.IntegerField('Подвеска не исправен мин сумма 200',      default=0, null=True, blank=True)       #'// 

    system_og_warning_amount_200        = models.IntegerField('Подвеска есть замечания сумма 200',      default=0, null=True, blank=True)       #'// 
    system_og_warning_kf_200            = models.IntegerField('Подвеска есть замечания коэфицент 200',      default=0, null=True, blank=True)       #'// 
    system_og_warning_amount_min_200    = models.IntegerField('Подвеска есть замечания мин сумма 200',      default=0, null=True, blank=True)       #'// 
    

    wheel_danger_amount_400             = models.IntegerField('Рулевая рейка не исправен сумма 400',      default=0, null=True, blank=True)       #'// 
    wheel_danger_kf_400                 = models.IntegerField('Рулевая рейка не исправен коэфицент 400',      default=0, null=True, blank=True)       #'// 
    wheel_danger_amount_min_400         = models.IntegerField('Рулевая рейка не исправен мин сумма 400',      default=0, null=True, blank=True)       #'// 

    wheel_warning_amount_400        	= models.IntegerField('Рулевая рейка есть замечания сумма 400',      default=0, null=True, blank=True)       #'// 
    wheel_warning_kf_400            	= models.IntegerField('Рулевая рейка есть замечания коэфицент 400',      default=0, null=True, blank=True)       #'// 
    wheel_warning_amount_min_400    	= models.IntegerField('Рулевая рейка есть замечания мин сумма 400',      default=0, null=True, blank=True)       #'// 
    
    brake_danger_amount_400              = models.IntegerField('Тормозная система не исправна сумма 400',      default=0, null=True, blank=True)
    brake_danger_kf_400                  = models.IntegerField('Тормозная система не исправна коэффициент 400', default=0, null=True, blank=True)
    brake_danger_amount_min_400          = models.IntegerField('Тормозная система не исправна мин сумма 400',   default=0, null=True, blank=True)
    brake_warning_amount_400             = models.IntegerField('Тормозная система есть замечания сумма 400',    default=0, null=True, blank=True)
    brake_warning_kf_400                 = models.IntegerField('Тормозная система есть замечания коэффициент 400', default=0, null=True, blank=True)
    brake_warning_amount_min_400         = models.IntegerField('Тормозная система есть замечания мин сумма 400', default=0, null=True, blank=True)
    
    subframe_danger_amount_400              = models.IntegerField('Подрамник не исправен сумма 400',      default=0, null=True, blank=True)
    subframe_danger_kf_400                  = models.IntegerField('Подрамник не исправен коэффициент 400', default=0, null=True, blank=True)
    subframe_danger_amount_min_400          = models.IntegerField('Подрамник не исправен мин сумма 400',   default=0, null=True, blank=True)
    subframe_warning_amount_400             = models.IntegerField('Подрамник есть замечания сумма 400',    default=0, null=True, blank=True)
    subframe_warning_kf_400                 = models.IntegerField('Подрамник есть замечания коэффициент 400', default=0, null=True, blank=True)
    subframe_warning_amount_min_400         = models.IntegerField('Подрамник есть замечания мин сумма 400', default=0, null=True, blank=True)
    
    conditioner_danger_amount_400        = models.IntegerField('Кондиционер не исправен сумма 400',      default=0, null=True, blank=True)       #'// 
    conditioner_danger_kf_400            = models.IntegerField('Кондиционер не исправен коэфицент 400',      default=0, null=True, blank=True)       #'// 
    conditioner_danger_amount_min_400    = models.IntegerField('Кондиционер не исправен мин сумма 400',      default=0, null=True, blank=True)       #'// 

    conditioner_warning_amount_400          = models.IntegerField('Кондиционер есть замечания сумма 400',      default=0, null=True, blank=True)       #'// 
    conditioner_warning_kf_400            	= models.IntegerField('Кондиционер есть замечания коэфицент 400',      default=0, null=True, blank=True)       #'// 
    conditioner_warning_amount_min_400    	= models.IntegerField('Кондиционер есть замечания мин сумма 400',      default=0, null=True, blank=True)       #'// 

    turbo_danger_amount_400                 = models.IntegerField('Турбо не исправен сумма 400',      default=0, null=True, blank=True)       #'// 
    turbo_danger_kf_400                     = models.IntegerField('Турбо не исправен коэфицент 400',      default=0, null=True, blank=True)       #'// 
    turbo_danger_amount_min_400             = models.IntegerField('Турбо не исправен мин сумма 400',      default=0, null=True, blank=True)       #'// 

    turbo_warning_amount_400            = models.IntegerField('Турбо есть замечания сумма 400',      default=0, null=True, blank=True)       #'// 
    turbo_warning_kf_400            	= models.IntegerField('Турбо есть замечания коэфицент 400',      default=0, null=True, blank=True)       #'// 
    turbo_warning_amount_min_400    	= models.IntegerField('Турбо есть замечания мин сумма 400',      default=0, null=True, blank=True)       #'// 

    engine_danger_amount_400        = models.IntegerField('Двигатель не исправен сумма 400',      default=0, null=True, blank=True)       #'// 
    engine_danger_kf_400            = models.IntegerField('Двигатель не исправен коэфицент 400',      default=0, null=True, blank=True)       #'// 
    engine_danger_amount_min_400    = models.IntegerField('Двигатель не исправен мин сумма 400',      default=0, null=True, blank=True)       #'// 

    engine_warning_amount_400        	= models.IntegerField('Двигатель есть замечания сумма 400',      default=0, null=True, blank=True)       #'// 
    engine_warning_kf_400            	= models.IntegerField('Двигатель есть замечания коэфицент 400',      default=0, null=True, blank=True)       #'// 
    engine_warning_amount_min_400    	= models.IntegerField('Двигатель есть замечания мин сумма 400',      default=0, null=True, blank=True)       #'// 

    engine_dt_danger_amount_400        = models.IntegerField('Двигатель дизель не исправен сумма 400',      default=0, null=True, blank=True)       #'// 
    engine_dt_danger_kf_400            = models.IntegerField('Двигатель дизель не исправен коэфицент 400',      default=0, null=True, blank=True)       #'// 
    engine_dt_danger_amount_min_400    = models.IntegerField('Двигатель дизель не исправен мин сумма 400',      default=0, null=True, blank=True)       #'// 

    engine_dt_warning_amount_400        = models.IntegerField('Двигатель дизель есть замечания сумма 400',      default=0, null=True, blank=True)       #'// 
    engine_dt_warning_kf_400            = models.IntegerField('Двигатель дизель есть замечания коэфицент 400',      default=0, null=True, blank=True)       #'// 
    engine_dt_warning_amount_min_400    = models.IntegerField('Двигатель дизель есть замечания мин сумма 400',      default=0, null=True, blank=True)       #'// 

    gear_at_danger_amount_400        = models.IntegerField('КПП автомат не исправен сумма 400',      default=0, null=True, blank=True)       #'// 
    gear_at_danger_kf_400            = models.IntegerField('КПП автомат не исправен коэфицент 400',      default=0, null=True, blank=True)       #'// 
    gear_at_danger_amount_min_400    = models.IntegerField('КПП автомат не исправен мин сумма 400',      default=0, null=True, blank=True)       #'// 

    gear_at_warning_amount_400        = models.IntegerField('КПП автомат есть замечания сумма',      default=0, null=True, blank=True)       #'// 
    gear_at_warning_kf_400            = models.IntegerField('КПП автомат есть замечания коэфицент 400',      default=0, null=True, blank=True)       #'// 
    gear_at_warning_amount_min_400    = models.IntegerField('КПП автомат есть замечания мин сумма 400',      default=0, null=True, blank=True)       #'// 

    gear_amt_danger_amount_400        = models.IntegerField('КПП робот не исправен сумма 400',      default=0, null=True, blank=True)       #'// 
    gear_amt_danger_kf_400            = models.IntegerField('КПП робот не исправен коэфицент 400',      default=0, null=True, blank=True)       #'// 
    gear_amt_danger_amount_min_400    = models.IntegerField('КПП робот не исправен мин сумма 400',      default=0, null=True, blank=True)       #'// 

    gear_amt_warning_amount_400        = models.IntegerField('КПП робот есть замечания сумма 400',      default=0, null=True, blank=True)       #'// 
    gear_amt_warning_kf_400            = models.IntegerField('КПП робот есть замечания коэфицент 400',      default=0, null=True, blank=True)       #'// 
    gear_amt_warning_amount_min_400    = models.IntegerField('КПП робот есть замечания мин сумма 400',      default=0, null=True, blank=True)       #'// 

    gear_cvt_danger_amount_400        = models.IntegerField('КПП вариатор не исправен сумма 400',      default=0, null=True, blank=True)       #'// 
    gear_cvt_danger_kf_400            = models.IntegerField('КПП вариатор не исправен коэфицент 400',      default=0, null=True, blank=True)       #'// 
    gear_cvt_danger_amount_min_400    = models.IntegerField('КПП вариатор не исправен мин сумма 400',      default=0, null=True, blank=True)       #'// 

    gear_cvt_warning_amount_400        = models.IntegerField('КПП вариатор есть замечания сумма 400',      default=0, null=True, blank=True)       #'// 
    gear_cvt_warning_kf_400            = models.IntegerField('КПП вариатор есть замечания коэфицент 400',      default=0, null=True, blank=True)       #'// 
    gear_cvt_warning_amount_min_400    = models.IntegerField('КПП вариатор есть замечания мин сумма 400',      default=0, null=True, blank=True)       #'// 

    gear_mt_danger_amount_400        = models.IntegerField('КПП механика не исправен сумма 400',      default=0, null=True, blank=True)       #'// 
    gear_mt_danger_kf_400            = models.IntegerField('КПП механика не исправен коэфицент 400',      default=0, null=True, blank=True)       #'// 
    gear_mt_danger_amount_min_400    = models.IntegerField('КПП механика не исправен мин сумма 400',      default=0, null=True, blank=True)       #'// 

    gear_mt_warning_amount_400        = models.IntegerField('КПП механика есть замечания сумма 400',      default=0, null=True, blank=True)       #'// 
    gear_mt_warning_kf_400            = models.IntegerField('КПП механика есть замечания коэфицент 400',      default=0, null=True, blank=True)       #'// 
    gear_mt_warning_amount_min_400    = models.IntegerField('КПП механика есть замечания мин сумма 400',      default=0, null=True, blank=True)       #'// 

    suspension_danger_amount_400        = models.IntegerField('Подвеска не исправен сумма 400',      default=0, null=True, blank=True)       #'// 
    suspension_danger_kf_400            = models.IntegerField('Подвеска не исправен коэфицент 400',      default=0, null=True, blank=True)       #'// 
    suspension_danger_amount_min_400    = models.IntegerField('Подвеска не исправен мин сумма 400',      default=0, null=True, blank=True)       #'// 

    suspension_warning_amount_400        = models.IntegerField('Подвеска есть замечания сумма 400',      default=0, null=True, blank=True)       #'// 
    suspension_warning_kf_400            = models.IntegerField('Подвеска есть замечания коэфицент 400',      default=0, null=True, blank=True)       #'// 
    suspension_warning_amount_min_400    = models.IntegerField('Подвеска есть замечания мин сумма 400',      default=0, null=True, blank=True)       #'// 
    
    system_og_danger_amount_400        = models.IntegerField('Подвеска не исправен сумма 400',      default=0, null=True, blank=True)       #'// 
    system_og_danger_kf_400            = models.IntegerField('Подвеска не исправен коэфицент 400',      default=0, null=True, blank=True)       #'// 
    system_og_danger_amount_min_400    = models.IntegerField('Подвеска не исправен мин сумма 400',      default=0, null=True, blank=True)       #'// 

    system_og_warning_amount_400        = models.IntegerField('Подвеска есть замечания сумма 400',      default=0, null=True, blank=True)       #'// 
    system_og_warning_kf_400            = models.IntegerField('Подвеска есть замечания коэфицент 400',      default=0, null=True, blank=True)       #'// 
    system_og_warning_amount_min_400    = models.IntegerField('Подвеска есть замечания мин сумма 400',      default=0, null=True, blank=True)       #'// 
    

    wheel_danger_amount_700             = models.IntegerField('Рулевая рейка не исправен сумма 700',      default=0, null=True, blank=True)       #'// 
    wheel_danger_kf_700                 = models.IntegerField('Рулевая рейка не исправен коэфицент 700',      default=0, null=True, blank=True)       #'// 
    wheel_danger_amount_min_700         = models.IntegerField('Рулевая рейка не исправен мин сумма 700',      default=0, null=True, blank=True)       #'// 

    wheel_warning_amount_700        	= models.IntegerField('Рулевая рейка есть замечания сумма 700',      default=0, null=True, blank=True)       #'// 
    wheel_warning_kf_700            	= models.IntegerField('Рулевая рейка есть замечания коэфицент 700',      default=0, null=True, blank=True)       #'// 
    wheel_warning_amount_min_700    	= models.IntegerField('Рулевая рейка есть замечания мин сумма 700',      default=0, null=True, blank=True)       #'// 

    brake_danger_amount_700              = models.IntegerField('Тормозная система не исправна сумма 700',      default=0, null=True, blank=True)
    brake_danger_kf_700                  = models.IntegerField('Тормозная система не исправна коэффициент 700', default=0, null=True, blank=True)
    brake_danger_amount_min_700          = models.IntegerField('Тормозная система не исправна мин сумма 700',   default=0, null=True, blank=True)
    brake_warning_amount_700             = models.IntegerField('Тормозная система есть замечания сумма 700',    default=0, null=True, blank=True)
    brake_warning_kf_700                 = models.IntegerField('Тормозная система есть замечания коэффициент 700', default=0, null=True, blank=True)
    brake_warning_amount_min_700         = models.IntegerField('Тормозная система есть замечания мин сумма 700', default=0, null=True, blank=True)
    
    subframe_danger_amount_700              = models.IntegerField('Подрамник не исправен сумма 700',      default=0, null=True, blank=True)
    subframe_danger_kf_700                  = models.IntegerField('Подрамник не исправен коэффициент 700', default=0, null=True, blank=True)
    subframe_danger_amount_min_700          = models.IntegerField('Подрамник не исправен мин сумма 700',   default=0, null=True, blank=True)
    subframe_warning_amount_700             = models.IntegerField('Подрамник есть замечания сумма 700',    default=0, null=True, blank=True)
    subframe_warning_kf_700                 = models.IntegerField('Подрамник есть замечания коэффициент 700', default=0, null=True, blank=True)
    subframe_warning_amount_min_700         = models.IntegerField('Подрамник есть замечания мин сумма 700', default=0, null=True, blank=True)
    
    conditioner_danger_amount_700        = models.IntegerField('Кондиционер не исправен сумма 700',      default=0, null=True, blank=True)       #'// 
    conditioner_danger_kf_700            = models.IntegerField('Кондиционер не исправен коэфицент 700',      default=0, null=True, blank=True)       #'// 
    conditioner_danger_amount_min_700    = models.IntegerField('Кондиционер не исправен мин сумма 700',      default=0, null=True, blank=True)       #'// 

    conditioner_warning_amount_700          = models.IntegerField('Кондиционер есть замечания сумма 700',      default=0, null=True, blank=True)       #'// 
    conditioner_warning_kf_700            	= models.IntegerField('Кондиционер есть замечания коэфицент 700',      default=0, null=True, blank=True)       #'// 
    conditioner_warning_amount_min_700    	= models.IntegerField('Кондиционер есть замечания мин сумма 700',      default=0, null=True, blank=True)       #'// 

    turbo_danger_amount_700                 = models.IntegerField('Турбо не исправен сумма 700',      default=0, null=True, blank=True)       #'// 
    turbo_danger_kf_700                     = models.IntegerField('Турбо не исправен коэфицент 700',      default=0, null=True, blank=True)       #'// 
    turbo_danger_amount_min_700             = models.IntegerField('Турбо не исправен мин сумма 700',      default=0, null=True, blank=True)       #'// 

    turbo_warning_amount_700            = models.IntegerField('Турбо есть замечания сумма 700',      default=0, null=True, blank=True)       #'// 
    turbo_warning_kf_700            	= models.IntegerField('Турбо есть замечания коэфицент 700',      default=0, null=True, blank=True)       #'// 
    turbo_warning_amount_min_700    	= models.IntegerField('Турбо есть замечания мин сумма 700',      default=0, null=True, blank=True)       #'// 

    engine_danger_amount_700        = models.IntegerField('Двигатель не исправен сумма 700',      default=0, null=True, blank=True)       #'// 
    engine_danger_kf_700            = models.IntegerField('Двигатель не исправен коэфицент 700',      default=0, null=True, blank=True)       #'// 
    engine_danger_amount_min_700    = models.IntegerField('Двигатель не исправен мин сумма 700',      default=0, null=True, blank=True)       #'// 

    engine_warning_amount_700        	= models.IntegerField('Двигатель есть замечания сумма 700',      default=0, null=True, blank=True)       #'// 
    engine_warning_kf_700            	= models.IntegerField('Двигатель есть замечания коэфицент 700',      default=0, null=True, blank=True)       #'// 
    engine_warning_amount_min_700    	= models.IntegerField('Двигатель есть замечания мин сумма 700',      default=0, null=True, blank=True)       #'// 

    engine_dt_danger_amount_700        = models.IntegerField('Двигатель дизель не исправен сумма 700',      default=0, null=True, blank=True)       #'// 
    engine_dt_danger_kf_700            = models.IntegerField('Двигатель дизель не исправен коэфицент 700',      default=0, null=True, blank=True)       #'// 
    engine_dt_danger_amount_min_700    = models.IntegerField('Двигатель дизель не исправен мин сумма 700',      default=0, null=True, blank=True)       #'// 

    engine_dt_warning_amount_700        = models.IntegerField('Двигатель дизель есть замечания сумма 700',      default=0, null=True, blank=True)       #'// 
    engine_dt_warning_kf_700            = models.IntegerField('Двигатель дизель есть замечания коэфицент 700',      default=0, null=True, blank=True)       #'// 
    engine_dt_warning_amount_min_700    = models.IntegerField('Двигатель дизель есть замечания мин сумма 700',      default=0, null=True, blank=True)       #'// 

    gear_at_danger_amount_700        = models.IntegerField('КПП автомат не исправен сумма 700',      default=0, null=True, blank=True)       #'// 
    gear_at_danger_kf_700            = models.IntegerField('КПП автомат не исправен коэфицент 700',      default=0, null=True, blank=True)       #'// 
    gear_at_danger_amount_min_700    = models.IntegerField('КПП автомат не исправен мин сумма 700',      default=0, null=True, blank=True)       #'// 

    gear_at_warning_amount_700        = models.IntegerField('КПП автомат есть замечания сумма',      default=0, null=True, blank=True)       #'// 
    gear_at_warning_kf_700            = models.IntegerField('КПП автомат есть замечания коэфицент 700',      default=0, null=True, blank=True)       #'// 
    gear_at_warning_amount_min_700    = models.IntegerField('КПП автомат есть замечания мин сумма 700',      default=0, null=True, blank=True)       #'// 

    gear_amt_danger_amount_700        = models.IntegerField('КПП робот не исправен сумма 700',      default=0, null=True, blank=True)       #'// 
    gear_amt_danger_kf_700            = models.IntegerField('КПП робот не исправен коэфицент 700',      default=0, null=True, blank=True)       #'// 
    gear_amt_danger_amount_min_700    = models.IntegerField('КПП робот не исправен мин сумма 700',      default=0, null=True, blank=True)       #'// 

    gear_amt_warning_amount_700        = models.IntegerField('КПП робот есть замечания сумма 700',      default=0, null=True, blank=True)       #'// 
    gear_amt_warning_kf_700            = models.IntegerField('КПП робот есть замечания коэфицент 700',      default=0, null=True, blank=True)       #'// 
    gear_amt_warning_amount_min_700    = models.IntegerField('КПП робот есть замечания мин сумма 700',      default=0, null=True, blank=True)       #'// 

    gear_cvt_danger_amount_700        = models.IntegerField('КПП вариатор не исправен сумма 700',      default=0, null=True, blank=True)       #'// 
    gear_cvt_danger_kf_700            = models.IntegerField('КПП вариатор не исправен коэфицент 700',      default=0, null=True, blank=True)       #'// 
    gear_cvt_danger_amount_min_700    = models.IntegerField('КПП вариатор не исправен мин сумма 700',      default=0, null=True, blank=True)       #'// 

    gear_cvt_warning_amount_700        = models.IntegerField('КПП вариатор есть замечания сумма 700',      default=0, null=True, blank=True)       #'// 
    gear_cvt_warning_kf_700            = models.IntegerField('КПП вариатор есть замечания коэфицент 700',      default=0, null=True, blank=True)       #'// 
    gear_cvt_warning_amount_min_700    = models.IntegerField('КПП вариатор есть замечания мин сумма 700',      default=0, null=True, blank=True)       #'// 

    gear_mt_danger_amount_700        = models.IntegerField('КПП механика не исправен сумма 700',      default=0, null=True, blank=True)       #'// 
    gear_mt_danger_kf_700            = models.IntegerField('КПП механика не исправен коэфицент 700',      default=0, null=True, blank=True)       #'// 
    gear_mt_danger_amount_min_700    = models.IntegerField('КПП механика не исправен мин сумма 700',      default=0, null=True, blank=True)       #'// 

    gear_mt_warning_amount_700        = models.IntegerField('КПП механика есть замечания сумма 700',      default=0, null=True, blank=True)       #'// 
    gear_mt_warning_kf_700            = models.IntegerField('КПП механика есть замечания коэфицент 700',      default=0, null=True, blank=True)       #'// 
    gear_mt_warning_amount_min_700    = models.IntegerField('КПП механика есть замечания мин сумма 700',      default=0, null=True, blank=True)       #'// 

    suspension_danger_amount_700        = models.IntegerField('Подвеска не исправен сумма 700',      default=0, null=True, blank=True)       #'// 
    suspension_danger_kf_700            = models.IntegerField('Подвеска не исправен коэфицент 700',      default=0, null=True, blank=True)       #'// 
    suspension_danger_amount_min_700    = models.IntegerField('Подвеска не исправен мин сумма 700',      default=0, null=True, blank=True)       #'// 

    suspension_warning_amount_700        = models.IntegerField('Подвеска есть замечания сумма 700',      default=0, null=True, blank=True)       #'// 
    suspension_warning_kf_700            = models.IntegerField('Подвеска есть замечания коэфицент 700',      default=0, null=True, blank=True)       #'// 
    suspension_warning_amount_min_700    = models.IntegerField('Подвеска есть замечания мин сумма 700',      default=0, null=True, blank=True)       #'// 
    
    system_og_danger_amount_700        = models.IntegerField('Подвеска не исправен сумма 700',      default=0, null=True, blank=True)       #'// 
    system_og_danger_kf_700            = models.IntegerField('Подвеска не исправен коэфицент 700',      default=0, null=True, blank=True)       #'// 
    system_og_danger_amount_min_700    = models.IntegerField('Подвеска не исправен мин сумма 700',      default=0, null=True, blank=True)       #'// 

    system_og_warning_amount_700        = models.IntegerField('Подвеска есть замечания сумма 700',      default=0, null=True, blank=True)       #'// 
    system_og_warning_kf_700            = models.IntegerField('Подвеска есть замечания коэфицент 700',      default=0, null=True, blank=True)       #'// 
    system_og_warning_amount_min_700    = models.IntegerField('Подвеска есть замечания мин сумма 700',      default=0, null=True, blank=True)       #'// 


    wheel_danger_amount_1200             = models.IntegerField('Рулевая рейка не исправен сумма 1200',      default=0, null=True, blank=True)       #'// 
    wheel_danger_kf_1200                 = models.IntegerField('Рулевая рейка не исправен коэфицент 1200',      default=0, null=True, blank=True)       #'// 
    wheel_danger_amount_min_1200         = models.IntegerField('Рулевая рейка не исправен мин сумма 1200',      default=0, null=True, blank=True)       #'// 

    wheel_warning_amount_1200        	= models.IntegerField('Рулевая рейка есть замечания сумма 1200',      default=0, null=True, blank=True)       #'// 
    wheel_warning_kf_1200            	= models.IntegerField('Рулевая рейка есть замечания коэфицент 1200',      default=0, null=True, blank=True)       #'// 
    wheel_warning_amount_min_1200    	= models.IntegerField('Рулевая рейка есть замечания мин сумма 1200',      default=0, null=True, blank=True)       #'// 

    brake_danger_amount_1200              = models.IntegerField('Тормозная система не исправна сумма 1200',      default=0, null=True, blank=True)
    brake_danger_kf_1200                  = models.IntegerField('Тормозная система не исправна коэффициент 1200', default=0, null=True, blank=True)
    brake_danger_amount_min_1200          = models.IntegerField('Тормозная система не исправна мин сумма 1200',   default=0, null=True, blank=True)
    brake_warning_amount_1200             = models.IntegerField('Тормозная система есть замечания сумма 1200',    default=0, null=True, blank=True)
    brake_warning_kf_1200                 = models.IntegerField('Тормозная система есть замечания коэффициент 1200', default=0, null=True, blank=True)
    brake_warning_amount_min_1200         = models.IntegerField('Тормозная система есть замечания мин сумма 1200', default=0, null=True, blank=True)
    
    subframe_danger_amount_1200              = models.IntegerField('Подрамник не исправен сумма 1200',      default=0, null=True, blank=True)
    subframe_danger_kf_1200                  = models.IntegerField('Подрамник не исправен коэффициент 1200', default=0, null=True, blank=True)
    subframe_danger_amount_min_1200          = models.IntegerField('Подрамник не исправен мин сумма 1200',   default=0, null=True, blank=True)
    subframe_warning_amount_1200             = models.IntegerField('Подрамник есть замечания сумма 1200',    default=0, null=True, blank=True)
    subframe_warning_kf_1200                 = models.IntegerField('Подрамник есть замечания коэффициент 1200', default=0, null=True, blank=True)
    subframe_warning_amount_min_1200         = models.IntegerField('Подрамник есть замечания мин сумма 1200', default=0, null=True, blank=True)
    
    conditioner_danger_amount_1200        = models.IntegerField('Кондиционер не исправен сумма 1200',      default=0, null=True, blank=True)       #'// 
    conditioner_danger_kf_1200            = models.IntegerField('Кондиционер не исправен коэфицент 1200',      default=0, null=True, blank=True)       #'// 
    conditioner_danger_amount_min_1200    = models.IntegerField('Кондиционер не исправен мин сумма 1200',      default=0, null=True, blank=True)       #'// 

    conditioner_warning_amount_1200          = models.IntegerField('Кондиционер есть замечания сумма 1200',      default=0, null=True, blank=True)       #'// 
    conditioner_warning_kf_1200            	= models.IntegerField('Кондиционер есть замечания коэфицент 1200',      default=0, null=True, blank=True)       #'// 
    conditioner_warning_amount_min_1200    	= models.IntegerField('Кондиционер есть замечания мин сумма 1200',      default=0, null=True, blank=True)       #'// 

    turbo_danger_amount_1200                 = models.IntegerField('Турбо не исправен сумма 1200',      default=0, null=True, blank=True)       #'// 
    turbo_danger_kf_1200                     = models.IntegerField('Турбо не исправен коэфицент 1200',      default=0, null=True, blank=True)       #'// 
    turbo_danger_amount_min_1200             = models.IntegerField('Турбо не исправен мин сумма 1200',      default=0, null=True, blank=True)       #'// 

    turbo_warning_amount_1200            = models.IntegerField('Турбо есть замечания сумма 1200',      default=0, null=True, blank=True)       #'// 
    turbo_warning_kf_1200            	= models.IntegerField('Турбо есть замечания коэфицент 1200',      default=0, null=True, blank=True)       #'// 
    turbo_warning_amount_min_1200    	= models.IntegerField('Турбо есть замечания мин сумма 1200',      default=0, null=True, blank=True)       #'// 

    drive_danger_amount_200                 = models.IntegerField('Привод не исправен сумма 200',      default=0, null=True, blank=True)       #'// 
    drive_danger_kf_200                     = models.IntegerField('Привод не исправен коэфицент 200',      default=0, null=True, blank=True)       #'// 
    drive_danger_amount_min_200             = models.IntegerField('Привод не исправен мин сумма 200',      default=0, null=True, blank=True)       #'// 
    drive_warning_amount_200            = models.IntegerField('Привод есть замечания сумма 200',      default=0, null=True, blank=True)       #'// 
    drive_warning_kf_200            	= models.IntegerField('Привод есть замечания коэфицент 200',      default=0, null=True, blank=True)       #'// 
    drive_warning_amount_min_200    	= models.IntegerField('Привод есть замечания мин сумма 200',      default=0, null=True, blank=True)       #'// 

    drive_danger_amount_400                 = models.IntegerField('Привод не исправен сумма 400',      default=0, null=True, blank=True)       #'// 
    drive_danger_kf_400                     = models.IntegerField('Привод не исправен коэфицент 400',      default=0, null=True, blank=True)       #'// 
    drive_danger_amount_min_400             = models.IntegerField('Привод не исправен мин сумма 400',      default=0, null=True, blank=True)       #'// 
    drive_warning_amount_400            = models.IntegerField('Привод есть замечания сумма 400',      default=0, null=True, blank=True)       #'// 
    drive_warning_kf_400            	= models.IntegerField('Привод есть замечания коэфицент 400',      default=0, null=True, blank=True)       #'// 
    drive_warning_amount_min_400    	= models.IntegerField('Привод есть замечания мин сумма 400',      default=0, null=True, blank=True)       #'// 

    drive_danger_amount_700                 = models.IntegerField('Привод не исправен сумма 700',      default=0, null=True, blank=True)       #'// 
    drive_danger_kf_700                     = models.IntegerField('Привод не исправен коэфицент 700',      default=0, null=True, blank=True)       #'// 
    drive_danger_amount_min_700             = models.IntegerField('Привод не исправен мин сумма 700',      default=0, null=True, blank=True)       #'// 
    drive_warning_amount_700            = models.IntegerField('Привод есть замечания сумма 700',      default=0, null=True, blank=True)       #'// 
    drive_warning_kf_700            	= models.IntegerField('Привод есть замечания коэфицент 700',      default=0, null=True, blank=True)       #'// 
    drive_warning_amount_min_700    	= models.IntegerField('Привод есть замечания мин сумма 700',      default=0, null=True, blank=True)       #'// 

    drive_danger_amount_1200                 = models.IntegerField('Привод не исправен сумма 1200',      default=0, null=True, blank=True)       #'// 
    drive_danger_kf_1200                     = models.IntegerField('Привод не исправен коэфицент 1200',      default=0, null=True, blank=True)       #'// 
    drive_danger_amount_min_1200             = models.IntegerField('Привод не исправен мин сумма 1200',      default=0, null=True, blank=True)       #'// 

    drive_warning_amount_1200            = models.IntegerField('Привод есть замечания сумма 1200',      default=0, null=True, blank=True)       #'// 
    drive_warning_kf_1200            	= models.IntegerField('Привод есть замечания коэфицент 1200',      default=0, null=True, blank=True)       #'// 
    drive_warning_amount_min_1200    	= models.IntegerField('Привод есть замечания мин сумма 1200',      default=0, null=True, blank=True)       #'// 
    
    drive_danger_amount_2000                 = models.IntegerField('Привод не исправен сумма 2000',      default=0, null=True, blank=True)       #'// 
    drive_danger_kf_2000                     = models.IntegerField('Привод не исправен коэфицент 2000',      default=0, null=True, blank=True)       #'// 
    drive_danger_amount_min_2000             = models.IntegerField('Привод не исправен мин сумма 2000',      default=0, null=True, blank=True)       #'// 
    drive_warning_amount_2000            = models.IntegerField('Привод есть замечания сумма 2000',      default=0, null=True, blank=True)       #'// 
    drive_warning_kf_2000            	= models.IntegerField('Привод есть замечания коэфицент 2000',      default=0, null=True, blank=True)       #'// 
    drive_warning_amount_min_2000    	= models.IntegerField('Привод есть замечания мин сумма 2000',      default=0, null=True, blank=True)       #'// 

    drive_danger_amount_3000                 = models.IntegerField('Привод не исправен сумма 3000',      default=0, null=True, blank=True)       #'// 
    drive_danger_kf_3000                     = models.IntegerField('Привод не исправен коэфицент 3000',      default=0, null=True, blank=True)       #'// 
    drive_danger_amount_min_3000             = models.IntegerField('Привод не исправен мин сумма 3000',      default=0, null=True, blank=True)       #'// 
    drive_warning_amount_3000            = models.IntegerField('Привод есть замечания сумма 3000',      default=0, null=True, blank=True)       #'// 
    drive_warning_kf_3000            	= models.IntegerField('Привод есть замечания коэфицент 3000',      default=0, null=True, blank=True)       #'// 
    drive_warning_amount_min_3000    	= models.IntegerField('Привод есть замечания мин сумма 3000',      default=0, null=True, blank=True)       #'// 

    drive_danger_amount_5000                 = models.IntegerField('Привод не исправен сумма 5000',      default=0, null=True, blank=True)       #'// 
    drive_danger_kf_5000                     = models.IntegerField('Привод не исправен коэфицент 5000',      default=0, null=True, blank=True)       #'// 
    drive_danger_amount_min_5000             = models.IntegerField('Привод не исправен мин сумма 5000',      default=0, null=True, blank=True)       #'// 
    drive_warning_amount_5000            = models.IntegerField('Привод есть замечания сумма 5000',      default=0, null=True, blank=True)       #'// 
    drive_warning_kf_5000            	= models.IntegerField('Привод есть замечания коэфицент 5000',      default=0, null=True, blank=True)       #'// 
    drive_warning_amount_min_5000    	= models.IntegerField('Привод есть замечания мин сумма 5000',      default=0, null=True, blank=True)       #'// 

    drive_danger_amount_5001                 = models.IntegerField('Привод не исправен сумма 5001',      default=0, null=True, blank=True)       #'// 
    drive_danger_kf_5001                     = models.IntegerField('Привод не исправен коэфицент 5001',      default=0, null=True, blank=True)       #'// 
    drive_danger_amount_min_5001             = models.IntegerField('Привод не исправен мин сумма 5001',      default=0, null=True, blank=True)       #'// 
    drive_warning_amount_5001            = models.IntegerField('Привод есть замечания сумма 5001',      default=0, null=True, blank=True)       #'// 
    drive_warning_kf_5001            	= models.IntegerField('Привод есть замечания коэфицент 5001',      default=0, null=True, blank=True)       #'// 
    drive_warning_amount_min_5001    	= models.IntegerField('Привод есть замечания мин сумма 5001',      default=0, null=True, blank=True)       #'// 

    engine_danger_amount_1200        = models.IntegerField('Двигатель не исправен сумма 1200',      default=0, null=True, blank=True)       #'// 
    engine_danger_kf_1200            = models.IntegerField('Двигатель не исправен коэфицент 1200',      default=0, null=True, blank=True)       #'// 
    engine_danger_amount_min_1200    = models.IntegerField('Двигатель не исправен мин сумма 1200',      default=0, null=True, blank=True)       #'// 

    engine_warning_amount_1200        	= models.IntegerField('Двигатель есть замечания сумма 1200',      default=0, null=True, blank=True)       #'// 
    engine_warning_kf_1200            	= models.IntegerField('Двигатель есть замечания коэфицент 1200',      default=0, null=True, blank=True)       #'// 
    engine_warning_amount_min_1200    	= models.IntegerField('Двигатель есть замечания мин сумма 1200',      default=0, null=True, blank=True)       #'// 

    engine_dt_danger_amount_1200        = models.IntegerField('Двигатель дизель не исправен сумма 1200',      default=0, null=True, blank=True)       #'// 
    engine_dt_danger_kf_1200            = models.IntegerField('Двигатель дизель не исправен коэфицент 1200',      default=0, null=True, blank=True)       #'// 
    engine_dt_danger_amount_min_1200    = models.IntegerField('Двигатель дизель не исправен мин сумма 1200',      default=0, null=True, blank=True)       #'// 

    engine_dt_warning_amount_1200        = models.IntegerField('Двигатель дизель есть замечания сумма 1200',      default=0, null=True, blank=True)       #'// 
    engine_dt_warning_kf_1200            = models.IntegerField('Двигатель дизель есть замечания коэфицент 1200',      default=0, null=True, blank=True)       #'// 
    engine_dt_warning_amount_min_1200    = models.IntegerField('Двигатель дизель есть замечания мин сумма 1200',      default=0, null=True, blank=True)       #'// 

    gear_at_danger_amount_1200        = models.IntegerField('КПП автомат не исправен сумма 1200',      default=0, null=True, blank=True)       #'// 
    gear_at_danger_kf_1200            = models.IntegerField('КПП автомат не исправен коэфицент 1200',      default=0, null=True, blank=True)       #'// 
    gear_at_danger_amount_min_1200    = models.IntegerField('КПП автомат не исправен мин сумма 1200',      default=0, null=True, blank=True)       #'// 

    gear_at_warning_amount_1200        = models.IntegerField('КПП автомат есть замечания сумма',      default=0, null=True, blank=True)       #'// 
    gear_at_warning_kf_1200            = models.IntegerField('КПП автомат есть замечания коэфицент 1200',      default=0, null=True, blank=True)       #'// 
    gear_at_warning_amount_min_1200    = models.IntegerField('КПП автомат есть замечания мин сумма 1200',      default=0, null=True, blank=True)       #'// 

    gear_amt_danger_amount_1200        = models.IntegerField('КПП робот не исправен сумма 1200',      default=0, null=True, blank=True)       #'// 
    gear_amt_danger_kf_1200            = models.IntegerField('КПП робот не исправен коэфицент 1200',      default=0, null=True, blank=True)       #'// 
    gear_amt_danger_amount_min_1200    = models.IntegerField('КПП робот не исправен мин сумма 1200',      default=0, null=True, blank=True)       #'// 

    gear_amt_warning_amount_1200        = models.IntegerField('КПП робот есть замечания сумма 1200',      default=0, null=True, blank=True)       #'// 
    gear_amt_warning_kf_1200            = models.IntegerField('КПП робот есть замечания коэфицент 1200',      default=0, null=True, blank=True)       #'// 
    gear_amt_warning_amount_min_1200    = models.IntegerField('КПП робот есть замечания мин сумма 1200',      default=0, null=True, blank=True)       #'// 

    gear_cvt_danger_amount_1200        = models.IntegerField('КПП вариатор не исправен сумма 1200',      default=0, null=True, blank=True)       #'// 
    gear_cvt_danger_kf_1200            = models.IntegerField('КПП вариатор не исправен коэфицент 1200',      default=0, null=True, blank=True)       #'// 
    gear_cvt_danger_amount_min_1200    = models.IntegerField('КПП вариатор не исправен мин сумма 1200',      default=0, null=True, blank=True)       #'// 

    gear_cvt_warning_amount_1200        = models.IntegerField('КПП вариатор есть замечания сумма 1200',      default=0, null=True, blank=True)       #'// 
    gear_cvt_warning_kf_1200            = models.IntegerField('КПП вариатор есть замечания коэфицент 1200',      default=0, null=True, blank=True)       #'// 
    gear_cvt_warning_amount_min_1200    = models.IntegerField('КПП вариатор есть замечания мин сумма 1200',      default=0, null=True, blank=True)       #'// 

    gear_mt_danger_amount_1200        = models.IntegerField('КПП механика не исправен сумма 1200',      default=0, null=True, blank=True)       #'// 
    gear_mt_danger_kf_1200            = models.IntegerField('КПП механика не исправен коэфицент 1200',      default=0, null=True, blank=True)       #'// 
    gear_mt_danger_amount_min_1200    = models.IntegerField('КПП механика не исправен мин сумма 1200',      default=0, null=True, blank=True)       #'// 

    gear_mt_warning_amount_1200        = models.IntegerField('КПП механика есть замечания сумма 1200',      default=0, null=True, blank=True)       #'// 
    gear_mt_warning_kf_1200            = models.IntegerField('КПП механика есть замечания коэфицент 1200',      default=0, null=True, blank=True)       #'// 
    gear_mt_warning_amount_min_1200    = models.IntegerField('КПП механика есть замечания мин сумма 1200',      default=0, null=True, blank=True)       #'// 

    suspension_danger_amount_1200        = models.IntegerField('Подвеска не исправен сумма 1200',      default=0, null=True, blank=True)       #'// 
    suspension_danger_kf_1200            = models.IntegerField('Подвеска не исправен коэфицент 1200',      default=0, null=True, blank=True)       #'// 
    suspension_danger_amount_min_1200    = models.IntegerField('Подвеска не исправен мин сумма 1200',      default=0, null=True, blank=True)       #'// 

    suspension_warning_amount_1200        = models.IntegerField('Подвеска есть замечания сумма 1200',      default=0, null=True, blank=True)       #'// 
    suspension_warning_kf_1200            = models.IntegerField('Подвеска есть замечания коэфицент 1200',      default=0, null=True, blank=True)       #'// 
    suspension_warning_amount_min_1200    = models.IntegerField('Подвеска есть замечания мин сумма 1200',      default=0, null=True, blank=True)       #'// 
    
    system_og_danger_amount_1200        = models.IntegerField('Подвеска не исправен сумма 1200',      default=0, null=True, blank=True)       #'// 
    system_og_danger_kf_1200            = models.IntegerField('Подвеска не исправен коэфицент 1200',      default=0, null=True, blank=True)       #'// 
    system_og_danger_amount_min_1200    = models.IntegerField('Подвеска не исправен мин сумма 1200',      default=0, null=True, blank=True)       #'// 

    system_og_warning_amount_1200        = models.IntegerField('Подвеска есть замечания сумма 1200',      default=0, null=True, blank=True)       #'// 
    system_og_warning_kf_1200            = models.IntegerField('Подвеска есть замечания коэфицент 1200',      default=0, null=True, blank=True)       #'// 
    system_og_warning_amount_min_1200    = models.IntegerField('Подвеска есть замечания мин сумма 1200',      default=0, null=True, blank=True)       #'// 


    wheel_danger_amount_2000             = models.IntegerField('Рулевая рейка не исправен сумма 2000',      default=0, null=True, blank=True)       #'// 
    wheel_danger_kf_2000                 = models.IntegerField('Рулевая рейка не исправен коэфицент 2000',      default=0, null=True, blank=True)       #'// 
    wheel_danger_amount_min_2000         = models.IntegerField('Рулевая рейка не исправен мин сумма 2000',      default=0, null=True, blank=True)       #'// 

    wheel_warning_amount_2000        	= models.IntegerField('Рулевая рейка есть замечания сумма 2000',      default=0, null=True, blank=True)       #'// 
    wheel_warning_kf_2000            	= models.IntegerField('Рулевая рейка есть замечания коэфицент 2000',      default=0, null=True, blank=True)       #'// 
    wheel_warning_amount_min_2000    	= models.IntegerField('Рулевая рейка есть замечания мин сумма 2000',      default=0, null=True, blank=True)       #'// 

    brake_danger_amount_2000              = models.IntegerField('Тормозная система не исправна сумма 2000',      default=0, null=True, blank=True)
    brake_danger_kf_2000                  = models.IntegerField('Тормозная система не исправна коэффициент 2000', default=0, null=True, blank=True)
    brake_danger_amount_min_2000          = models.IntegerField('Тормозная система не исправна мин сумма 2000',   default=0, null=True, blank=True)
    brake_warning_amount_2000             = models.IntegerField('Тормозная система есть замечания сумма 2000',    default=0, null=True, blank=True)
    brake_warning_kf_2000                 = models.IntegerField('Тормозная система есть замечания коэффициент 2000', default=0, null=True, blank=True)
    brake_warning_amount_min_2000         = models.IntegerField('Тормозная система есть замечания мин сумма 2000', default=0, null=True, blank=True)
    
    conditioner_danger_amount_2000        = models.IntegerField('Кондиционер не исправен сумма 2000',      default=0, null=True, blank=True)       #'// 
    conditioner_danger_kf_2000            = models.IntegerField('Кондиционер не исправен коэфицент 2000',      default=0, null=True, blank=True)       #'// 
    conditioner_danger_amount_min_2000    = models.IntegerField('Кондиционер не исправен мин сумма 2000',      default=0, null=True, blank=True)       #'// 

    conditioner_warning_amount_2000          = models.IntegerField('Кондиционер есть замечания сумма 2000',      default=0, null=True, blank=True)       #'// 
    conditioner_warning_kf_2000            	= models.IntegerField('Кондиционер есть замечания коэфицент 2000',      default=0, null=True, blank=True)       #'// 
    conditioner_warning_amount_min_2000    	= models.IntegerField('Кондиционер есть замечания мин сумма 2000',      default=0, null=True, blank=True)       #'// 

    turbo_danger_amount_2000                 = models.IntegerField('Турбо не исправен сумма 2000',      default=0, null=True, blank=True)       #'// 
    turbo_danger_kf_2000                     = models.IntegerField('Турбо не исправен коэфицент 2000',      default=0, null=True, blank=True)       #'// 
    turbo_danger_amount_min_2000             = models.IntegerField('Турбо не исправен мин сумма 2000',      default=0, null=True, blank=True)       #'// 

    turbo_warning_amount_2000            = models.IntegerField('Турбо есть замечания сумма 2000',      default=0, null=True, blank=True)       #'// 
    turbo_warning_kf_2000            	= models.IntegerField('Турбо есть замечания коэфицент 2000',      default=0, null=True, blank=True)       #'// 
    turbo_warning_amount_min_2000    	= models.IntegerField('Турбо есть замечания мин сумма 2000',      default=0, null=True, blank=True)       #'// 

    engine_danger_amount_2000        = models.IntegerField('Двигатель не исправен сумма 2000',      default=0, null=True, blank=True)       #'// 
    engine_danger_kf_2000            = models.IntegerField('Двигатель не исправен коэфицент 2000',      default=0, null=True, blank=True)       #'// 
    engine_danger_amount_min_2000    = models.IntegerField('Двигатель не исправен мин сумма 2000',      default=0, null=True, blank=True)       #'// 

    engine_warning_amount_2000        	= models.IntegerField('Двигатель есть замечания сумма 2000',      default=0, null=True, blank=True)       #'// 
    engine_warning_kf_2000            	= models.IntegerField('Двигатель есть замечания коэфицент 2000',      default=0, null=True, blank=True)       #'// 
    engine_warning_amount_min_2000    	= models.IntegerField('Двигатель есть замечания мин сумма 2000',      default=0, null=True, blank=True)       #'// 

    engine_dt_danger_amount_2000        = models.IntegerField('Двигатель дизель не исправен сумма 2000',      default=0, null=True, blank=True)       #'// 
    engine_dt_danger_kf_2000            = models.IntegerField('Двигатель дизель не исправен коэфицент 2000',      default=0, null=True, blank=True)       #'// 
    engine_dt_danger_amount_min_2000    = models.IntegerField('Двигатель дизель не исправен мин сумма 2000',      default=0, null=True, blank=True)       #'// 

    engine_dt_warning_amount_2000        = models.IntegerField('Двигатель дизель есть замечания сумма 2000',      default=0, null=True, blank=True)       #'// 
    engine_dt_warning_kf_2000            = models.IntegerField('Двигатель дизель есть замечания коэфицент 2000',      default=0, null=True, blank=True)       #'// 
    engine_dt_warning_amount_min_2000    = models.IntegerField('Двигатель дизель есть замечания мин сумма 2000',      default=0, null=True, blank=True)       #'// 

    gear_at_danger_amount_2000        = models.IntegerField('КПП автомат не исправен сумма 2000',      default=0, null=True, blank=True)       #'// 
    gear_at_danger_kf_2000            = models.IntegerField('КПП автомат не исправен коэфицент 2000',      default=0, null=True, blank=True)       #'// 
    gear_at_danger_amount_min_2000    = models.IntegerField('КПП автомат не исправен мин сумма 2000',      default=0, null=True, blank=True)       #'// 

    gear_at_warning_amount_2000        = models.IntegerField('КПП автомат есть замечания сумма',      default=0, null=True, blank=True)       #'// 
    gear_at_warning_kf_2000            = models.IntegerField('КПП автомат есть замечания коэфицент 2000',      default=0, null=True, blank=True)       #'// 
    gear_at_warning_amount_min_2000    = models.IntegerField('КПП автомат есть замечания мин сумма 2000',      default=0, null=True, blank=True)       #'// 

    gear_amt_danger_amount_2000        = models.IntegerField('КПП робот не исправен сумма 2000',      default=0, null=True, blank=True)       #'// 
    gear_amt_danger_kf_2000            = models.IntegerField('КПП робот не исправен коэфицент 2000',      default=0, null=True, blank=True)       #'// 
    gear_amt_danger_amount_min_2000    = models.IntegerField('КПП робот не исправен мин сумма 2000',      default=0, null=True, blank=True)       #'// 

    gear_amt_warning_amount_2000        = models.IntegerField('КПП робот есть замечания сумма 2000',      default=0, null=True, blank=True)       #'// 
    gear_amt_warning_kf_2000            = models.IntegerField('КПП робот есть замечания коэфицент 2000',      default=0, null=True, blank=True)       #'// 
    gear_amt_warning_amount_min_2000    = models.IntegerField('КПП робот есть замечания мин сумма 2000',      default=0, null=True, blank=True)       #'// 

    gear_cvt_danger_amount_2000        = models.IntegerField('КПП вариатор не исправен сумма 2000',      default=0, null=True, blank=True)       #'// 
    gear_cvt_danger_kf_2000            = models.IntegerField('КПП вариатор не исправен коэфицент 2000',      default=0, null=True, blank=True)       #'// 
    gear_cvt_danger_amount_min_2000    = models.IntegerField('КПП вариатор не исправен мин сумма 2000',      default=0, null=True, blank=True)       #'// 

    gear_cvt_warning_amount_2000        = models.IntegerField('КПП вариатор есть замечания сумма 2000',      default=0, null=True, blank=True)       #'// 
    gear_cvt_warning_kf_2000            = models.IntegerField('КПП вариатор есть замечания коэфицент 2000',      default=0, null=True, blank=True)       #'// 
    gear_cvt_warning_amount_min_2000    = models.IntegerField('КПП вариатор есть замечания мин сумма 2000',      default=0, null=True, blank=True)       #'// 

    gear_mt_danger_amount_2000        = models.IntegerField('КПП механика не исправен сумма 2000',      default=0, null=True, blank=True)       #'// 
    gear_mt_danger_kf_2000            = models.IntegerField('КПП механика не исправен коэфицент 2000',      default=0, null=True, blank=True)       #'// 
    gear_mt_danger_amount_min_2000    = models.IntegerField('КПП механика не исправен мин сумма 2000',      default=0, null=True, blank=True)       #'// 

    gear_mt_warning_amount_2000        = models.IntegerField('КПП механика есть замечания сумма 2000',      default=0, null=True, blank=True)       #'// 
    gear_mt_warning_kf_2000            = models.IntegerField('КПП механика есть замечания коэфицент 2000',      default=0, null=True, blank=True)       #'// 
    gear_mt_warning_amount_min_2000    = models.IntegerField('КПП механика есть замечания мин сумма 2000',      default=0, null=True, blank=True)       #'// 

    suspension_danger_amount_2000        = models.IntegerField('Подвеска не исправен сумма 2000',      default=0, null=True, blank=True)       #'// 
    suspension_danger_kf_2000            = models.IntegerField('Подвеска не исправен коэфицент 2000',      default=0, null=True, blank=True)       #'// 
    suspension_danger_amount_min_2000    = models.IntegerField('Подвеска не исправен мин сумма 2000',      default=0, null=True, blank=True)       #'// 

    suspension_warning_amount_2000        = models.IntegerField('Подвеска есть замечания сумма 2000',      default=0, null=True, blank=True)       #'// 
    suspension_warning_kf_2000            = models.IntegerField('Подвеска есть замечания коэфицент 2000',      default=0, null=True, blank=True)       #'// 
    suspension_warning_amount_min_2000    = models.IntegerField('Подвеска есть замечания мин сумма 2000',      default=0, null=True, blank=True)       #'// 
    
    system_og_danger_amount_2000        = models.IntegerField('Подвеска не исправен сумма 2000',      default=0, null=True, blank=True)       #'// 
    system_og_danger_kf_2000            = models.IntegerField('Подвеска не исправен коэфицент 2000',      default=0, null=True, blank=True)       #'// 
    system_og_danger_amount_min_2000    = models.IntegerField('Подвеска не исправен мин сумма 2000',      default=0, null=True, blank=True)       #'// 

    system_og_warning_amount_2000        = models.IntegerField('Подвеска есть замечания сумма 2000',      default=0, null=True, blank=True)       #'// 
    system_og_warning_kf_2000            = models.IntegerField('Подвеска есть замечания коэфицент 2000',      default=0, null=True, blank=True)       #'// 
    system_og_warning_amount_min_2000    = models.IntegerField('Подвеска есть замечания мин сумма 2000',      default=0, null=True, blank=True)       #'// 

    subframe_danger_amount_2000              = models.IntegerField('Подрамник не исправен сумма 2000',      default=0, null=True, blank=True)
    subframe_danger_kf_2000                  = models.IntegerField('Подрамник не исправен коэффициент 2000', default=0, null=True, blank=True)
    subframe_danger_amount_min_2000          = models.IntegerField('Подрамник не исправен мин сумма 2000',   default=0, null=True, blank=True)
    subframe_warning_amount_2000             = models.IntegerField('Подрамник есть замечания сумма 2000',    default=0, null=True, blank=True)
    subframe_warning_kf_2000                 = models.IntegerField('Подрамник есть замечания коэффициент 2000', default=0, null=True, blank=True)
    subframe_warning_amount_min_2000         = models.IntegerField('Подрамник есть замечания мин сумма 2000', default=0, null=True, blank=True)


    wheel_danger_amount_3000             = models.IntegerField('Рулевая рейка не исправен сумма 3000',      default=0, null=True, blank=True)       #'// 
    wheel_danger_kf_3000                 = models.IntegerField('Рулевая рейка не исправен коэфицент 3000',      default=0, null=True, blank=True)       #'// 
    wheel_danger_amount_min_3000         = models.IntegerField('Рулевая рейка не исправен мин сумма 3000',      default=0, null=True, blank=True)       #'// 

    wheel_warning_amount_3000        	= models.IntegerField('Рулевая рейка есть замечания сумма 3000',      default=0, null=True, blank=True)       #'// 
    wheel_warning_kf_3000            	= models.IntegerField('Рулевая рейка есть замечания коэфицент 3000',      default=0, null=True, blank=True)       #'// 
    wheel_warning_amount_min_3000    	= models.IntegerField('Рулевая рейка есть замечания мин сумма 3000',      default=0, null=True, blank=True)       #'// 

    brake_danger_amount_3000              = models.IntegerField('Тормозная система не исправна сумма 3000',      default=0, null=True, blank=True)
    brake_danger_kf_3000                  = models.IntegerField('Тормозная система не исправна коэффициент 3000', default=0, null=True, blank=True)
    brake_danger_amount_min_3000          = models.IntegerField('Тормозная система не исправна мин сумма 3000',   default=0, null=True, blank=True)
    brake_warning_amount_3000             = models.IntegerField('Тормозная система есть замечания сумма 3000',    default=0, null=True, blank=True)
    brake_warning_kf_3000                 = models.IntegerField('Тормозная система есть замечания коэффициент 3000', default=0, null=True, blank=True)
    brake_warning_amount_min_3000         = models.IntegerField('Тормозная система есть замечания мин сумма 3000', default=0, null=True, blank=True)
    
    subframe_danger_amount_3000              = models.IntegerField('Подрамник не исправен сумма 3000',      default=0, null=True, blank=True)
    subframe_danger_kf_3000                  = models.IntegerField('Подрамник не исправен коэффициент 3000', default=0, null=True, blank=True)
    subframe_danger_amount_min_3000          = models.IntegerField('Подрамник не исправен мин сумма 3000',   default=0, null=True, blank=True)
    subframe_warning_amount_3000             = models.IntegerField('Подрамник есть замечания сумма 3000',    default=0, null=True, blank=True)
    subframe_warning_kf_3000                 = models.IntegerField('Подрамник есть замечания коэффициент 3000', default=0, null=True, blank=True)
    subframe_warning_amount_min_3000         = models.IntegerField('Подрамник есть замечания мин сумма 3000', default=0, null=True, blank=True)
    
    conditioner_danger_amount_3000        = models.IntegerField('Кондиционер не исправен сумма 3000',      default=0, null=True, blank=True)       #'// 
    conditioner_danger_kf_3000            = models.IntegerField('Кондиционер не исправен коэфицент 3000',      default=0, null=True, blank=True)       #'// 
    conditioner_danger_amount_min_3000    = models.IntegerField('Кондиционер не исправен мин сумма 3000',      default=0, null=True, blank=True)       #'// 

    conditioner_warning_amount_3000          = models.IntegerField('Кондиционер есть замечания сумма 3000',      default=0, null=True, blank=True)       #'// 
    conditioner_warning_kf_3000            	= models.IntegerField('Кондиционер есть замечания коэфицент 3000',      default=0, null=True, blank=True)       #'// 
    conditioner_warning_amount_min_3000    	= models.IntegerField('Кондиционер есть замечания мин сумма 3000',      default=0, null=True, blank=True)       #'// 

    turbo_danger_amount_3000                 = models.IntegerField('Турбо не исправен сумма 3000',      default=0, null=True, blank=True)       #'// 
    turbo_danger_kf_3000                     = models.IntegerField('Турбо не исправен коэфицент 3000',      default=0, null=True, blank=True)       #'// 
    turbo_danger_amount_min_3000             = models.IntegerField('Турбо не исправен мин сумма 3000',      default=0, null=True, blank=True)       #'// 

    turbo_warning_amount_3000            = models.IntegerField('Турбо есть замечания сумма 3000',      default=0, null=True, blank=True)       #'// 
    turbo_warning_kf_3000            	= models.IntegerField('Турбо есть замечания коэфицент 3000',      default=0, null=True, blank=True)       #'// 
    turbo_warning_amount_min_3000    	= models.IntegerField('Турбо есть замечания мин сумма 3000',      default=0, null=True, blank=True)       #'// 

    engine_danger_amount_3000        = models.IntegerField('Двигатель не исправен сумма 3000',      default=0, null=True, blank=True)       #'// 
    engine_danger_kf_3000            = models.IntegerField('Двигатель не исправен коэфицент 3000',      default=0, null=True, blank=True)       #'// 
    engine_danger_amount_min_3000    = models.IntegerField('Двигатель не исправен мин сумма 3000',      default=0, null=True, blank=True)       #'// 

    engine_warning_amount_3000        	= models.IntegerField('Двигатель есть замечания сумма 3000',      default=0, null=True, blank=True)       #'// 
    engine_warning_kf_3000            	= models.IntegerField('Двигатель есть замечания коэфицент 3000',      default=0, null=True, blank=True)       #'// 
    engine_warning_amount_min_3000    	= models.IntegerField('Двигатель есть замечания мин сумма 3000',      default=0, null=True, blank=True)       #'// 

    engine_dt_danger_amount_3000        = models.IntegerField('Двигатель дизель не исправен сумма 3000',      default=0, null=True, blank=True)       #'// 
    engine_dt_danger_kf_3000            = models.IntegerField('Двигатель дизель не исправен коэфицент 3000',      default=0, null=True, blank=True)       #'// 
    engine_dt_danger_amount_min_3000    = models.IntegerField('Двигатель дизель не исправен мин сумма 3000',      default=0, null=True, blank=True)       #'// 

    engine_dt_warning_amount_3000        = models.IntegerField('Двигатель дизель есть замечания сумма 3000',      default=0, null=True, blank=True)       #'// 
    engine_dt_warning_kf_3000            = models.IntegerField('Двигатель дизель есть замечания коэфицент 3000',      default=0, null=True, blank=True)       #'// 
    engine_dt_warning_amount_min_3000    = models.IntegerField('Двигатель дизель есть замечания мин сумма 3000',      default=0, null=True, blank=True)       #'// 

    gear_at_danger_amount_3000        = models.IntegerField('КПП автомат не исправен сумма 3000',      default=0, null=True, blank=True)       #'// 
    gear_at_danger_kf_3000            = models.IntegerField('КПП автомат не исправен коэфицент 3000',      default=0, null=True, blank=True)       #'// 
    gear_at_danger_amount_min_3000    = models.IntegerField('КПП автомат не исправен мин сумма 3000',      default=0, null=True, blank=True)       #'// 

    gear_at_warning_amount_3000        = models.IntegerField('КПП автомат есть замечания сумма',      default=0, null=True, blank=True)       #'// 
    gear_at_warning_kf_3000            = models.IntegerField('КПП автомат есть замечания коэфицент 3000',      default=0, null=True, blank=True)       #'// 
    gear_at_warning_amount_min_3000    = models.IntegerField('КПП автомат есть замечания мин сумма 3000',      default=0, null=True, blank=True)       #'// 

    gear_amt_danger_amount_3000        = models.IntegerField('КПП робот не исправен сумма 3000',      default=0, null=True, blank=True)       #'// 
    gear_amt_danger_kf_3000            = models.IntegerField('КПП робот не исправен коэфицент 3000',      default=0, null=True, blank=True)       #'// 
    gear_amt_danger_amount_min_3000    = models.IntegerField('КПП робот не исправен мин сумма 3000',      default=0, null=True, blank=True)       #'// 

    gear_amt_warning_amount_3000        = models.IntegerField('КПП робот есть замечания сумма 3000',      default=0, null=True, blank=True)       #'// 
    gear_amt_warning_kf_3000            = models.IntegerField('КПП робот есть замечания коэфицент 3000',      default=0, null=True, blank=True)       #'// 
    gear_amt_warning_amount_min_3000    = models.IntegerField('КПП робот есть замечания мин сумма 3000',      default=0, null=True, blank=True)       #'// 

    gear_cvt_danger_amount_3000        = models.IntegerField('КПП вариатор не исправен сумма 3000',      default=0, null=True, blank=True)       #'// 
    gear_cvt_danger_kf_3000            = models.IntegerField('КПП вариатор не исправен коэфицент 3000',      default=0, null=True, blank=True)       #'// 
    gear_cvt_danger_amount_min_3000    = models.IntegerField('КПП вариатор не исправен мин сумма 3000',      default=0, null=True, blank=True)       #'// 

    gear_cvt_warning_amount_3000        = models.IntegerField('КПП вариатор есть замечания сумма 3000',      default=0, null=True, blank=True)       #'// 
    gear_cvt_warning_kf_3000            = models.IntegerField('КПП вариатор есть замечания коэфицент 3000',      default=0, null=True, blank=True)       #'// 
    gear_cvt_warning_amount_min_3000    = models.IntegerField('КПП вариатор есть замечания мин сумма 3000',      default=0, null=True, blank=True)       #'// 

    gear_mt_danger_amount_3000        = models.IntegerField('КПП механика не исправен сумма 3000',      default=0, null=True, blank=True)       #'// 
    gear_mt_danger_kf_3000            = models.IntegerField('КПП механика не исправен коэфицент 3000',      default=0, null=True, blank=True)       #'// 
    gear_mt_danger_amount_min_3000    = models.IntegerField('КПП механика не исправен мин сумма 3000',      default=0, null=True, blank=True)       #'// 

    gear_mt_warning_amount_3000        = models.IntegerField('КПП механика есть замечания сумма 3000',      default=0, null=True, blank=True)       #'// 
    gear_mt_warning_kf_3000            = models.IntegerField('КПП механика есть замечания коэфицент 3000',      default=0, null=True, blank=True)       #'// 
    gear_mt_warning_amount_min_3000    = models.IntegerField('КПП механика есть замечания мин сумма 3000',      default=0, null=True, blank=True)       #'// 

    suspension_danger_amount_3000        = models.IntegerField('Подвеска не исправен сумма 3000',      default=0, null=True, blank=True)       #'// 
    suspension_danger_kf_3000            = models.IntegerField('Подвеска не исправен коэфицент 3000',      default=0, null=True, blank=True)       #'// 
    suspension_danger_amount_min_3000    = models.IntegerField('Подвеска не исправен мин сумма 3000',      default=0, null=True, blank=True)       #'// 

    suspension_warning_amount_3000        = models.IntegerField('Подвеска есть замечания сумма 3000',      default=0, null=True, blank=True)       #'// 
    suspension_warning_kf_3000            = models.IntegerField('Подвеска есть замечания коэфицент 3000',      default=0, null=True, blank=True)       #'// 
    suspension_warning_amount_min_3000    = models.IntegerField('Подвеска есть замечания мин сумма 3000',      default=0, null=True, blank=True)       #'// 
    
    system_og_danger_amount_3000        = models.IntegerField('Подвеска не исправен сумма 3000',      default=0, null=True, blank=True)       #'// 
    system_og_danger_kf_3000            = models.IntegerField('Подвеска не исправен коэфицент 3000',      default=0, null=True, blank=True)       #'// 
    system_og_danger_amount_min_3000    = models.IntegerField('Подвеска не исправен мин сумма 3000',      default=0, null=True, blank=True)       #'// 

    system_og_warning_amount_3000        = models.IntegerField('Подвеска есть замечания сумма 3000',      default=0, null=True, blank=True)       #'// 
    system_og_warning_kf_3000            = models.IntegerField('Подвеска есть замечания коэфицент 3000',      default=0, null=True, blank=True)       #'// 
    system_og_warning_amount_min_3000    = models.IntegerField('Подвеска есть замечания мин сумма 3000',      default=0, null=True, blank=True)       #'// 

    wheel_danger_amount_5000             = models.IntegerField('Рулевая рейка не исправен сумма 5000',      default=0, null=True, blank=True)       #'// 
    wheel_danger_kf_5000                 = models.IntegerField('Рулевая рейка не исправен коэфицент 5000',      default=0, null=True, blank=True)       #'// 
    wheel_danger_amount_min_5000         = models.IntegerField('Рулевая рейка не исправен мин сумма 5000',      default=0, null=True, blank=True)       #'// 

    wheel_warning_amount_5000        	= models.IntegerField('Рулевая рейка есть замечания сумма 5000',      default=0, null=True, blank=True)       #'// 
    wheel_warning_kf_5000            	= models.IntegerField('Рулевая рейка есть замечания коэфицент 5000',      default=0, null=True, blank=True)       #'// 
    wheel_warning_amount_min_5000    	= models.IntegerField('Рулевая рейка есть замечания мин сумма 5000',      default=0, null=True, blank=True)       #'// 

    brake_danger_amount_5000              = models.IntegerField('Тормозная система не исправна сумма 5000',      default=0, null=True, blank=True)
    brake_danger_kf_5000                  = models.IntegerField('Тормозная система не исправна коэффициент 5000', default=0, null=True, blank=True)
    brake_danger_amount_min_5000          = models.IntegerField('Тормозная система не исправна мин сумма 5000',   default=0, null=True, blank=True)
    brake_warning_amount_5000             = models.IntegerField('Тормозная система есть замечания сумма 5000',    default=0, null=True, blank=True)
    brake_warning_kf_5000                 = models.IntegerField('Тормозная система есть замечания коэффициент 5000', default=0, null=True, blank=True)
    brake_warning_amount_min_5000         = models.IntegerField('Тормозная система есть замечания мин сумма 5000', default=0, null=True, blank=True)
    
    subframe_danger_amount_5000              = models.IntegerField('Подрамник не исправен сумма 5000',      default=0, null=True, blank=True)
    subframe_danger_kf_5000                  = models.IntegerField('Подрамник не исправен коэффициент 5000', default=0, null=True, blank=True)
    subframe_danger_amount_min_5000          = models.IntegerField('Подрамник не исправен мин сумма 5000',   default=0, null=True, blank=True)
    subframe_warning_amount_5000             = models.IntegerField('Подрамник есть замечания сумма 5000',    default=0, null=True, blank=True)
    subframe_warning_kf_5000                 = models.IntegerField('Подрамник есть замечания коэффициент 5000', default=0, null=True, blank=True)
    subframe_warning_amount_min_5000         = models.IntegerField('Подрамник есть замечания мин сумма 5000', default=0, null=True, blank=True)
    
    conditioner_danger_amount_5000        = models.IntegerField('Кондиционер не исправен сумма 5000',      default=0, null=True, blank=True)       #'// 
    conditioner_danger_kf_5000            = models.IntegerField('Кондиционер не исправен коэфицент 5000',      default=0, null=True, blank=True)       #'// 
    conditioner_danger_amount_min_5000    = models.IntegerField('Кондиционер не исправен мин сумма 5000',      default=0, null=True, blank=True)       #'// 

    conditioner_warning_amount_5000          = models.IntegerField('Кондиционер есть замечания сумма 5000',      default=0, null=True, blank=True)       #'// 
    conditioner_warning_kf_5000            	= models.IntegerField('Кондиционер есть замечания коэфицент 5000',      default=0, null=True, blank=True)       #'// 
    conditioner_warning_amount_min_5000    	= models.IntegerField('Кондиционер есть замечания мин сумма 5000',      default=0, null=True, blank=True)       #'// 

    turbo_danger_amount_5000                 = models.IntegerField('Турбо не исправен сумма 5000',      default=0, null=True, blank=True)       #'// 
    turbo_danger_kf_5000                     = models.IntegerField('Турбо не исправен коэфицент 5000',      default=0, null=True, blank=True)       #'// 
    turbo_danger_amount_min_5000             = models.IntegerField('Турбо не исправен мин сумма 5000',      default=0, null=True, blank=True)       #'// 

    turbo_warning_amount_5000            = models.IntegerField('Турбо есть замечания сумма 5000',      default=0, null=True, blank=True)       #'// 
    turbo_warning_kf_5000            	= models.IntegerField('Турбо есть замечания коэфицент 5000',      default=0, null=True, blank=True)       #'// 
    turbo_warning_amount_min_5000    	= models.IntegerField('Турбо есть замечания мин сумма 5000',      default=0, null=True, blank=True)       #'// 

    engine_danger_amount_5000        = models.IntegerField('Двигатель не исправен сумма 5000',      default=0, null=True, blank=True)       #'// 
    engine_danger_kf_5000            = models.IntegerField('Двигатель не исправен коэфицент 5000',      default=0, null=True, blank=True)       #'// 
    engine_danger_amount_min_5000    = models.IntegerField('Двигатель не исправен мин сумма 5000',      default=0, null=True, blank=True)       #'// 

    engine_warning_amount_5000        	= models.IntegerField('Двигатель есть замечания сумма 5000',      default=0, null=True, blank=True)       #'// 
    engine_warning_kf_5000            	= models.IntegerField('Двигатель есть замечания коэфицент 5000',      default=0, null=True, blank=True)       #'// 
    engine_warning_amount_min_5000    	= models.IntegerField('Двигатель есть замечания мин сумма 5000',      default=0, null=True, blank=True)       #'// 

    engine_dt_danger_amount_5000        = models.IntegerField('Двигатель дизель не исправен сумма 5000',      default=0, null=True, blank=True)       #'// 
    engine_dt_danger_kf_5000            = models.IntegerField('Двигатель дизель не исправен коэфицент 5000',      default=0, null=True, blank=True)       #'// 
    engine_dt_danger_amount_min_5000    = models.IntegerField('Двигатель дизель не исправен мин сумма 5000',      default=0, null=True, blank=True)       #'// 

    engine_dt_warning_amount_5000        = models.IntegerField('Двигатель дизель есть замечания сумма 5000',      default=0, null=True, blank=True)       #'// 
    engine_dt_warning_kf_5000            = models.IntegerField('Двигатель дизель есть замечания коэфицент 5000',      default=0, null=True, blank=True)       #'// 
    engine_dt_warning_amount_min_5000    = models.IntegerField('Двигатель дизель есть замечания мин сумма 5000',      default=0, null=True, blank=True)       #'// 

    gear_at_danger_amount_5000        = models.IntegerField('КПП автомат не исправен сумма 5000',      default=0, null=True, blank=True)       #'// 
    gear_at_danger_kf_5000            = models.IntegerField('КПП автомат не исправен коэфицент 5000',      default=0, null=True, blank=True)       #'// 
    gear_at_danger_amount_min_5000    = models.IntegerField('КПП автомат не исправен мин сумма 5000',      default=0, null=True, blank=True)       #'// 

    gear_at_warning_amount_5000        = models.IntegerField('КПП автомат есть замечания сумма',      default=0, null=True, blank=True)       #'// 
    gear_at_warning_kf_5000            = models.IntegerField('КПП автомат есть замечания коэфицент 5000',      default=0, null=True, blank=True)       #'// 
    gear_at_warning_amount_min_5000    = models.IntegerField('КПП автомат есть замечания мин сумма 5000',      default=0, null=True, blank=True)       #'// 

    gear_amt_danger_amount_5000        = models.IntegerField('КПП робот не исправен сумма 5000',      default=0, null=True, blank=True)       #'// 
    gear_amt_danger_kf_5000            = models.IntegerField('КПП робот не исправен коэфицент 5000',      default=0, null=True, blank=True)       #'// 
    gear_amt_danger_amount_min_5000    = models.IntegerField('КПП робот не исправен мин сумма 5000',      default=0, null=True, blank=True)       #'// 

    gear_amt_warning_amount_5000        = models.IntegerField('КПП робот есть замечания сумма 5000',      default=0, null=True, blank=True)       #'// 
    gear_amt_warning_kf_5000            = models.IntegerField('КПП робот есть замечания коэфицент 5000',      default=0, null=True, blank=True)       #'// 
    gear_amt_warning_amount_min_5000    = models.IntegerField('КПП робот есть замечания мин сумма 5000',      default=0, null=True, blank=True)       #'// 

    gear_cvt_danger_amount_5000        = models.IntegerField('КПП вариатор не исправен сумма 5000',      default=0, null=True, blank=True)       #'// 
    gear_cvt_danger_kf_5000            = models.IntegerField('КПП вариатор не исправен коэфицент 5000',      default=0, null=True, blank=True)       #'// 
    gear_cvt_danger_amount_min_5000    = models.IntegerField('КПП вариатор не исправен мин сумма 5000',      default=0, null=True, blank=True)       #'// 

    gear_cvt_warning_amount_5000        = models.IntegerField('КПП вариатор есть замечания сумма 5000',      default=0, null=True, blank=True)       #'// 
    gear_cvt_warning_kf_5000            = models.IntegerField('КПП вариатор есть замечания коэфицент 5000',      default=0, null=True, blank=True)       #'// 
    gear_cvt_warning_amount_min_5000    = models.IntegerField('КПП вариатор есть замечания мин сумма 5000',      default=0, null=True, blank=True)       #'// 

    gear_mt_danger_amount_5000        = models.IntegerField('КПП механика не исправен сумма 5000',      default=0, null=True, blank=True)       #'// 
    gear_mt_danger_kf_5000            = models.IntegerField('КПП механика не исправен коэфицент 5000',      default=0, null=True, blank=True)       #'// 
    gear_mt_danger_amount_min_5000    = models.IntegerField('КПП механика не исправен мин сумма 5000',      default=0, null=True, blank=True)       #'// 

    gear_mt_warning_amount_5000        = models.IntegerField('КПП механика есть замечания сумма 5000',      default=0, null=True, blank=True)       #'// 
    gear_mt_warning_kf_5000            = models.IntegerField('КПП механика есть замечания коэфицент 5000',      default=0, null=True, blank=True)       #'// 
    gear_mt_warning_amount_min_5000    = models.IntegerField('КПП механика есть замечания мин сумма 5000',      default=0, null=True, blank=True)       #'// 

    suspension_danger_amount_5000        = models.IntegerField('Подвеска не исправен сумма 5000',      default=0, null=True, blank=True)       #'// 
    suspension_danger_kf_5000            = models.IntegerField('Подвеска не исправен коэфицент 5000',      default=0, null=True, blank=True)       #'// 
    suspension_danger_amount_min_5000    = models.IntegerField('Подвеска не исправен мин сумма 5000',      default=0, null=True, blank=True)       #'// 

    suspension_warning_amount_5000        = models.IntegerField('Подвеска есть замечания сумма 5000',      default=0, null=True, blank=True)       #'// 
    suspension_warning_kf_5000            = models.IntegerField('Подвеска есть замечания коэфицент 5000',      default=0, null=True, blank=True)       #'// 
    suspension_warning_amount_min_5000    = models.IntegerField('Подвеска есть замечания мин сумма 5000',      default=0, null=True, blank=True)       #'// 
    
    system_og_danger_amount_5000        = models.IntegerField('Подвеска не исправен сумма 5000',      default=0, null=True, blank=True)       #'// 
    system_og_danger_kf_5000            = models.IntegerField('Подвеска не исправен коэфицент 5000',      default=0, null=True, blank=True)       #'// 
    system_og_danger_amount_min_5000    = models.IntegerField('Подвеска не исправен мин сумма 5000',      default=0, null=True, blank=True)       #'// 

    system_og_warning_amount_5000        = models.IntegerField('Подвеска есть замечания сумма 5000',      default=0, null=True, blank=True)       #'// 
    system_og_warning_kf_5000            = models.IntegerField('Подвеска есть замечания коэфицент 5000',      default=0, null=True, blank=True)       #'// 
    system_og_warning_amount_min_5000    = models.IntegerField('Подвеска есть замечания мин сумма 5000',      default=0, null=True, blank=True)       #'// 


    wheel_danger_amount_5001             = models.IntegerField('Рулевая рейка не исправен сумма 5001',      default=0, null=True, blank=True)       #'// 
    wheel_danger_kf_5001                 = models.IntegerField('Рулевая рейка не исправен коэфицент 5001',      default=0, null=True, blank=True)       #'// 
    wheel_danger_amount_min_5001         = models.IntegerField('Рулевая рейка не исправен мин сумма 5001',      default=0, null=True, blank=True)       #'// 

    wheel_warning_amount_5001        	= models.IntegerField('Рулевая рейка есть замечания сумма 5001',      default=0, null=True, blank=True)       #'// 
    wheel_warning_kf_5001            	= models.IntegerField('Рулевая рейка есть замечания коэфицент 5001',      default=0, null=True, blank=True)       #'// 
    wheel_warning_amount_min_5001    	= models.IntegerField('Рулевая рейка есть замечания мин сумма 5001',      default=0, null=True, blank=True)       #'// 

    brake_danger_amount_5001              = models.IntegerField('Тормозная система не исправна сумма 5001',      default=0, null=True, blank=True)
    brake_danger_kf_5001                  = models.IntegerField('Тормозная система не исправна коэффициент 5001', default=0, null=True, blank=True)
    brake_danger_amount_min_5001          = models.IntegerField('Тормозная система не исправна мин сумма 5001',   default=0, null=True, blank=True)
    brake_warning_amount_5001             = models.IntegerField('Тормозная система есть замечания сумма 5001',    default=0, null=True, blank=True)
    brake_warning_kf_5001                 = models.IntegerField('Тормозная система есть замечания коэффициент 5001', default=0, null=True, blank=True)
    brake_warning_amount_min_5001         = models.IntegerField('Тормозная система есть замечания мин сумма 5001', default=0, null=True, blank=True)
    
    subframe_danger_amount_5001              = models.IntegerField('Подрамник не исправен сумма 5001',      default=0, null=True, blank=True)
    subframe_danger_kf_5001                  = models.IntegerField('Подрамник не исправен коэффициент 5001', default=0, null=True, blank=True)
    subframe_danger_amount_min_5001          = models.IntegerField('Подрамник не исправен мин сумма 5001',   default=0, null=True, blank=True)
    subframe_warning_amount_5001             = models.IntegerField('Подрамник есть замечания сумма 5001',    default=0, null=True, blank=True)
    subframe_warning_kf_5001                 = models.IntegerField('Подрамник есть замечания коэффициент 5001', default=0, null=True, blank=True)
    subframe_warning_amount_min_5001         = models.IntegerField('Подрамник есть замечания мин сумма 5001', default=0, null=True, blank=True)
    
    conditioner_danger_amount_5001        = models.IntegerField('Кондиционер не исправен сумма 5001',      default=0, null=True, blank=True)       #'// 
    conditioner_danger_kf_5001            = models.IntegerField('Кондиционер не исправен коэфицент 5001',      default=0, null=True, blank=True)       #'// 
    conditioner_danger_amount_min_5001    = models.IntegerField('Кондиционер не исправен мин сумма 5001',      default=0, null=True, blank=True)       #'// 

    conditioner_warning_amount_5001          = models.IntegerField('Кондиционер есть замечания сумма 5001',      default=0, null=True, blank=True)       #'// 
    conditioner_warning_kf_5001            	= models.IntegerField('Кондиционер есть замечания коэфицент 5001',      default=0, null=True, blank=True)       #'// 
    conditioner_warning_amount_min_5001    	= models.IntegerField('Кондиционер есть замечания мин сумма 5001',      default=0, null=True, blank=True)       #'// 

    turbo_danger_amount_5001                 = models.IntegerField('Турбо не исправен сумма 5001',      default=0, null=True, blank=True)       #'// 
    turbo_danger_kf_5001                     = models.IntegerField('Турбо не исправен коэфицент 5001',      default=0, null=True, blank=True)       #'// 
    turbo_danger_amount_min_5001             = models.IntegerField('Турбо не исправен мин сумма 5001',      default=0, null=True, blank=True)       #'// 

    turbo_warning_amount_5001            = models.IntegerField('Турбо есть замечания сумма 5001',      default=0, null=True, blank=True)       #'// 
    turbo_warning_kf_5001            	= models.IntegerField('Турбо есть замечания коэфицент 5001',      default=0, null=True, blank=True)       #'// 
    turbo_warning_amount_min_5001    	= models.IntegerField('Турбо есть замечания мин сумма 5001',      default=0, null=True, blank=True)       #'// 

    engine_danger_amount_5001        = models.IntegerField('Двигатель не исправен сумма 5001',      default=0, null=True, blank=True)       #'// 
    engine_danger_kf_5001            = models.IntegerField('Двигатель не исправен коэфицент 5001',      default=0, null=True, blank=True)       #'// 
    engine_danger_amount_min_5001    = models.IntegerField('Двигатель не исправен мин сумма 5001',      default=0, null=True, blank=True)       #'// 

    engine_warning_amount_5001        	= models.IntegerField('Двигатель есть замечания сумма 5001',      default=0, null=True, blank=True)       #'// 
    engine_warning_kf_5001            	= models.IntegerField('Двигатель есть замечания коэфицент 5001',      default=0, null=True, blank=True)       #'// 
    engine_warning_amount_min_5001    	= models.IntegerField('Двигатель есть замечания мин сумма 5001',      default=0, null=True, blank=True)       #'// 

    engine_dt_danger_amount_5001        = models.IntegerField('Двигатель дизель не исправен сумма 5001',      default=0, null=True, blank=True)       #'// 
    engine_dt_danger_kf_5001            = models.IntegerField('Двигатель дизель не исправен коэфицент 5001',      default=0, null=True, blank=True)       #'// 
    engine_dt_danger_amount_min_5001    = models.IntegerField('Двигатель дизель не исправен мин сумма 5001',      default=0, null=True, blank=True)       #'// 

    engine_dt_warning_amount_5001        = models.IntegerField('Двигатель дизель есть замечания сумма 5001',      default=0, null=True, blank=True)       #'// 
    engine_dt_warning_kf_5001            = models.IntegerField('Двигатель дизель есть замечания коэфицент 5001',      default=0, null=True, blank=True)       #'// 
    engine_dt_warning_amount_min_5001    = models.IntegerField('Двигатель дизель есть замечания мин сумма 5001',      default=0, null=True, blank=True)       #'// 

    gear_at_danger_amount_5001        = models.IntegerField('КПП автомат не исправен сумма 5001',      default=0, null=True, blank=True)       #'// 
    gear_at_danger_kf_5001            = models.IntegerField('КПП автомат не исправен коэфицент 5001',      default=0, null=True, blank=True)       #'// 
    gear_at_danger_amount_min_5001    = models.IntegerField('КПП автомат не исправен мин сумма 5001',      default=0, null=True, blank=True)       #'// 

    gear_at_warning_amount_5001        = models.IntegerField('КПП автомат есть замечания сумма',      default=0, null=True, blank=True)       #'// 
    gear_at_warning_kf_5001            = models.IntegerField('КПП автомат есть замечания коэфицент 5001',      default=0, null=True, blank=True)       #'// 
    gear_at_warning_amount_min_5001    = models.IntegerField('КПП автомат есть замечания мин сумма 5001',      default=0, null=True, blank=True)       #'// 

    gear_amt_danger_amount_5001        = models.IntegerField('КПП робот не исправен сумма 5001',      default=0, null=True, blank=True)       #'// 
    gear_amt_danger_kf_5001            = models.IntegerField('КПП робот не исправен коэфицент 5001',      default=0, null=True, blank=True)       #'// 
    gear_amt_danger_amount_min_5001    = models.IntegerField('КПП робот не исправен мин сумма 5001',      default=0, null=True, blank=True)       #'// 

    gear_amt_warning_amount_5001        = models.IntegerField('КПП робот есть замечания сумма 5001',      default=0, null=True, blank=True)       #'// 
    gear_amt_warning_kf_5001            = models.IntegerField('КПП робот есть замечания коэфицент 5001',      default=0, null=True, blank=True)       #'// 
    gear_amt_warning_amount_min_5001    = models.IntegerField('КПП робот есть замечания мин сумма 5001',      default=0, null=True, blank=True)       #'// 

    gear_cvt_danger_amount_5001        = models.IntegerField('КПП вариатор не исправен сумма 5001',      default=0, null=True, blank=True)       #'// 
    gear_cvt_danger_kf_5001            = models.IntegerField('КПП вариатор не исправен коэфицент 5001',      default=0, null=True, blank=True)       #'// 
    gear_cvt_danger_amount_min_5001    = models.IntegerField('КПП вариатор не исправен мин сумма 5001',      default=0, null=True, blank=True)       #'// 

    gear_cvt_warning_amount_5001        = models.IntegerField('КПП вариатор есть замечания сумма 5001',      default=0, null=True, blank=True)       #'// 
    gear_cvt_warning_kf_5001            = models.IntegerField('КПП вариатор есть замечания коэфицент 5001',      default=0, null=True, blank=True)       #'// 
    gear_cvt_warning_amount_min_5001    = models.IntegerField('КПП вариатор есть замечания мин сумма 5001',      default=0, null=True, blank=True)       #'// 

    gear_mt_danger_amount_5001        = models.IntegerField('КПП механика не исправен сумма 5001',      default=0, null=True, blank=True)       #'// 
    gear_mt_danger_kf_5001            = models.IntegerField('КПП механика не исправен коэфицент 5001',      default=0, null=True, blank=True)       #'// 
    gear_mt_danger_amount_min_5001    = models.IntegerField('КПП механика не исправен мин сумма 5001',      default=0, null=True, blank=True)       #'// 

    gear_mt_warning_amount_5001        = models.IntegerField('КПП механика есть замечания сумма 5001',      default=0, null=True, blank=True)       #'// 
    gear_mt_warning_kf_5001            = models.IntegerField('КПП механика есть замечания коэфицент 5001',      default=0, null=True, blank=True)       #'// 
    gear_mt_warning_amount_min_5001    = models.IntegerField('КПП механика есть замечания мин сумма 5001',      default=0, null=True, blank=True)       #'// 

    suspension_danger_amount_5001        = models.IntegerField('Подвеска не исправен сумма 5001',      default=0, null=True, blank=True)       #'// 
    suspension_danger_kf_5001            = models.IntegerField('Подвеска не исправен коэфицент 5001',      default=0, null=True, blank=True)       #'// 
    suspension_danger_amount_min_5001    = models.IntegerField('Подвеска не исправен мин сумма 5001',      default=0, null=True, blank=True)       #'// 

    suspension_warning_amount_5001        = models.IntegerField('Подвеска есть замечания сумма 5001',      default=0, null=True, blank=True)       #'// 
    suspension_warning_kf_5001            = models.IntegerField('Подвеска есть замечания коэфицент 5001',      default=0, null=True, blank=True)       #'// 
    suspension_warning_amount_min_5001    = models.IntegerField('Подвеска есть замечания мин сумма 5001',      default=0, null=True, blank=True)       #'// 
    
    system_og_danger_amount_5001        = models.IntegerField('Подвеска не исправен сумма 5001',      default=0, null=True, blank=True)       #'// 
    system_og_danger_kf_5001            = models.IntegerField('Подвеска не исправен коэфицент 5001',      default=0, null=True, blank=True)       #'// 
    system_og_danger_amount_min_5001    = models.IntegerField('Подвеска не исправен мин сумма 5001',      default=0, null=True, blank=True)       #'// 

    system_og_warning_amount_5001        = models.IntegerField('Подвеска есть замечания сумма 5001',      default=0, null=True, blank=True)       #'// 
    system_og_warning_kf_5001            = models.IntegerField('Подвеска есть замечания коэфицент 5001',      default=0, null=True, blank=True)       #'// 
    system_og_warning_amount_min_5001    = models.IntegerField('Подвеска есть замечания мин сумма 5001',      default=0, null=True, blank=True)       #'// 


    windshield_200                      = models.IntegerField('Ветровое стекло 200 без подогрева',      default=0, null=False, blank=True)       #'// 
    windshield_heat_200                 = models.IntegerField('Ветровое стекло 200 с подогревом',      default=0, null=False, blank=True)
    
    windshield_400                      = models.IntegerField('Ветровое стекло 400 без подогрева',      default=0, null=False, blank=True)       #'// 
    windshield_heat_400                 = models.IntegerField('Ветровое стекло 400 с подогревом',      default=0, null=False, blank=True)

    windshield_700                      = models.IntegerField('Ветровое стекло 700 без подогрева',      default=0, null=False, blank=True)       #'// 
    windshield_heat_700                 = models.IntegerField('Ветровое стекло 700 с подогревом',      default=0, null=False, blank=True)

    windshield_1200                      = models.IntegerField('Ветровое стекло 1200 без подогрева',      default=0, null=False, blank=True)       #'// 
    windshield_heat_1200                 = models.IntegerField('Ветровое стекло 1200 с подогревом',      default=0, null=False, blank=True)

    windshield_2000                      = models.IntegerField('Ветровое стекло 2000 без подогрева',      default=0, null=False, blank=True)       #'// 
    windshield_heat_2000                 = models.IntegerField('Ветровое стекло 2000 с подогревом',      default=0, null=False, blank=True)

    windshield_3000                      = models.IntegerField('Ветровое стекло 3000 без подогрева',      default=0, null=False, blank=True)       #'// 
    windshield_heat_3000                 = models.IntegerField('Ветровое стекло 3000 с подогревом',      default=0, null=False, blank=True)

    windshield_5000                      = models.IntegerField('Ветровое стекло 5000 без подогрева',      default=0, null=False, blank=True)       #'// 
    windshield_heat_5000                 = models.IntegerField('Ветровое стекло 5000 с подогревом',      default=0, null=False, blank=True)

    windshield_5001                      = models.IntegerField('Ветровое стекло 5001 без подогрева',      default=0, null=False, blank=True)       #'// 
    windshield_heat_5001                 = models.IntegerField('Ветровое стекло 5001 с подогревом',      default=0, null=False, blank=True)

    light_pered_200                 = models.IntegerField('Фара 200 ',      default=0, null=False, blank=True)       #'// 
    light_zad_200                   = models.IntegerField('Фонарь 200 зад',      default=0, null=False, blank=True)
    
    light_pered_400                 = models.IntegerField('Фара 400 ',      default=0, null=False, blank=True)       #'// 
    light_zad_400                   = models.IntegerField('Фонарь 400 зад',      default=0, null=False, blank=True)

    light_pered_700                      = models.IntegerField('Фара 700 ',      default=0, null=False, blank=True)       #'// 
    light_zad_700                 = models.IntegerField('Фонарь 700 зад',      default=0, null=False, blank=True)

    light_pered_1200                      = models.IntegerField('Фара 1200 ',      default=0, null=False, blank=True)       #'// 
    light_zad_1200                 = models.IntegerField('Фонарь 1200 зад',      default=0, null=False, blank=True)

    light_pered_2000                      = models.IntegerField('Фара 2000 ',      default=0, null=False, blank=True)       #'// 
    light_zad_2000                 = models.IntegerField('Фонарь 2000 зад',      default=0, null=False, blank=True)

    light_pered_3000                      = models.IntegerField('Фара 3000 ',      default=0, null=False, blank=True)       #'// 
    light_zad_3000                 = models.IntegerField('Фонарь 3000 зад',      default=0, null=False, blank=True)

    light_pered_5000                      = models.IntegerField('Фара 5000 ',      default=0, null=False, blank=True)       #'// 
    light_zad_5000                = models.IntegerField('Фонарь 5000 зад',      default=0, null=False, blank=True)
    
    light_pered_5001                      = models.IntegerField('Фара 5001 ',      default=0, null=False, blank=True)       #'// 
    light_zad_5001                 = models.IntegerField('Фонарь 5001 зад',      default=0, null=False, blank=True)

    light_pered_kf_200                      = models.IntegerField('Фара коэфицент 200 ',      default=0, null=False, blank=True)       #'// 
    light_zad_kf_200                       = models.IntegerField('Фонарь коэфицент 200 зад',      default=0, null=False, blank=True)
    
    light_pered_kf_400                      = models.IntegerField('Фара коэфицент 400 ',      default=0, null=False, blank=True)       #'// 
    light_zad_kf_400                       = models.IntegerField('Фонарь коэфицент 400 зад',      default=0, null=False, blank=True)

    light_pered_kf_700                      = models.IntegerField('Фара коэфицент 700 ',      default=0, null=False, blank=True)       #'// 
    light_zad_kf_700                 = models.IntegerField('Фонарь коэфицент 700 зад',      default=0, null=False, blank=True)

    light_pered_kf_1200                      = models.IntegerField('Фара коэфицент 1200 ',      default=0, null=False, blank=True)       #'// 
    light_zad_kf_1200                 = models.IntegerField('Фонарь коэфицент 1200 зад',      default=0, null=False, blank=True)

    light_pered_kf_2000                      = models.IntegerField('Фара коэфицент 2000 ',      default=0, null=False, blank=True)       #'// 
    light_zad_kf_2000                 = models.IntegerField('Фонарь коэфицент 2000 зад',      default=0, null=False, blank=True)

    light_pered_kf_3000                      = models.IntegerField('Фара коэфицент 3000 ',      default=0, null=False, blank=True)       #'// 
    light_zad_kf_3000                 = models.IntegerField('Фонарь коэфицент 3000 зад',      default=0, null=False, blank=True)

    light_pered_kf_5000                      = models.IntegerField('Фара коэфицент 5000 ',      default=0, null=False, blank=True)       #'// 
    light_zad_kf_5000                 = models.IntegerField('Фонарь коэфицент 5000 зад',      default=0, null=False, blank=True)

    light_pered_kf_5001                      = models.IntegerField('Фара коэфицент 5001 ',      default=0, null=False, blank=True)       #'// 
    light_zad_kf_5001                 = models.IntegerField('Фонарь коэфицент 5001 зад',      default=0, null=False, blank=True)

    bumper_pered_200                 = models.IntegerField('Бампер 200 ',      default=0, null=False, blank=True)       
    bumper_zad_200                   = models.IntegerField('Бампер 200 зад',      default=0, null=False, blank=True)
    bumper_pered_replace_200                 = models.IntegerField('Бампер 200 ',      default=0, null=False, blank=True)       
    bumper_zad_replace_200                  = models.IntegerField('Бампер 200 зад',      default=0, null=False, blank=True)

    bumper_pered_400                 = models.IntegerField('Бампер 400 ',      default=0, null=False, blank=True)       
    bumper_zad_400                   = models.IntegerField('Бампер 400 зад',      default=0, null=False, blank=True)
    bumper_pered_replace_400                 = models.IntegerField('Бампер 400 ',      default=0, null=False, blank=True)       
    bumper_zad_replace_400                   = models.IntegerField('Бампер 400 зад',      default=0, null=False, blank=True)

    bumper_pered_700                 = models.IntegerField('Бампер 700 ',      default=0, null=False, blank=True)       
    bumper_zad_700                   = models.IntegerField('Бампер 700 зад',      default=0, null=False, blank=True)
    bumper_pered_replace_700                 = models.IntegerField('Бампер 700 ',      default=0, null=False, blank=True)       
    bumper_zad_replace_700                   = models.IntegerField('Бампер 700 зад',      default=0, null=False, blank=True)

    bumper_pered_1200                 = models.IntegerField('Бампер 1200 ',      default=0, null=False, blank=True)       
    bumper_zad_1200                   = models.IntegerField('Бампер 1200 зад',      default=0, null=False, blank=True)
    bumper_pered_replace_1200                 = models.IntegerField('Бампер 1200 ',      default=0, null=False, blank=True)       
    bumper_zad_replace_1200                   = models.IntegerField('Бампер 1200 зад',      default=0, null=False, blank=True)

    bumper_pered_2000                 = models.IntegerField('Бампер 2000 ',      default=0, null=False, blank=True)       
    bumper_zad_2000                   = models.IntegerField('Бампер 2000 зад',      default=0, null=False, blank=True)
    bumper_pered_replace_2000                 = models.IntegerField('Бампер 2000 ',      default=0, null=False, blank=True)       
    bumper_zad_replace_2000                   = models.IntegerField('Бампер 2000 зад',      default=0, null=False, blank=True)

    bumper_pered_3000                 = models.IntegerField('Бампер 3000 ',      default=0, null=False, blank=True)       
    bumper_zad_3000                   = models.IntegerField('Бампер 3000 зад',      default=0, null=False, blank=True)
    bumper_pered_replace_3000                 = models.IntegerField('Бампер 3000 ',      default=0, null=False, blank=True)       
    bumper_zad_replace_3000                   = models.IntegerField('Бампер 3000 зад',      default=0, null=False, blank=True)

    bumper_pered_5000                 = models.IntegerField('Бампер 5000 ',      default=0, null=False, blank=True)       
    bumper_zad_5000                   = models.IntegerField('Бампер 5000 зад',      default=0, null=False, blank=True)
    bumper_pered_replace_5000                 = models.IntegerField('Бампер 5000 ',      default=0, null=False, blank=True)       
    bumper_zad_replace_5000                   = models.IntegerField('Бампер 5000 зад',      default=0, null=False, blank=True)

    bumper_pered_5001                 = models.IntegerField('Бампер 5001 ',      default=0, null=False, blank=True)       
    bumper_zad_5001                   = models.IntegerField('Бампер 5001 зад',      default=0, null=False, blank=True)
    bumper_pered_replace_5001                 = models.IntegerField('Бампер 5001 ',      default=0, null=False, blank=True)       
    bumper_zad_replace_5001                   = models.IntegerField('Бампер 5001 зад',      default=0, null=False, blank=True)


    bumper_pered_kf_200                 = models.IntegerField('Бампер 200 ',      default=0, null=False, blank=True)       
    bumper_zad_kf_200                   = models.IntegerField('Бампер 200 зад',      default=0, null=False, blank=True)
    bumper_pered_replace_kf_200                 = models.IntegerField('Бампер замена 200 ',      default=0, null=False, blank=True)       
    bumper_zad_replace_kf_200                   = models.IntegerField('Бампер замена 200 зад',      default=0, null=False, blank=True)

    bumper_pered_kf_400                 = models.IntegerField('Бампер 400 ',      default=0, null=False, blank=True)       
    bumper_zad_kf_400                   = models.IntegerField('Бампер 400 зад',      default=0, null=False, blank=True)
    bumper_pered_replace_kf_400                 = models.IntegerField('Бампер замена 400 ',      default=0, null=False, blank=True)       
    bumper_zad_replace_kf_400                   = models.IntegerField('Бампер замена 400 зад',      default=0, null=False, blank=True)

    bumper_pered_kf_700                 = models.IntegerField('Бампер 700 ',      default=0, null=False, blank=True)       
    bumper_zad_kf_700                   = models.IntegerField('Бампер 700 зад',      default=0, null=False, blank=True)
    bumper_pered_replace_kf_700                 = models.IntegerField('Бампер замена 700 ',      default=0, null=False, blank=True)       
    bumper_zad_replace_kf_700                   = models.IntegerField('Бампер замена 700 зад',      default=0, null=False, blank=True)

    bumper_pered_kf_1200                 = models.IntegerField('Бампер 1200 ',      default=0, null=False, blank=True)       
    bumper_zad_kf_1200                   = models.IntegerField('Бампер 1200 зад',      default=0, null=False, blank=True)
    bumper_pered_replace_kf_1200                 = models.IntegerField('Бампер замена 1200 ',      default=0, null=False, blank=True)       
    bumper_zad_replace_kf_1200                   = models.IntegerField('Бампер замена 1200 зад',      default=0, null=False, blank=True)

    bumper_pered_kf_2000                 = models.IntegerField('Бампер 2000 ',      default=0, null=False, blank=True)       
    bumper_zad_kf_2000                   = models.IntegerField('Бампер 2000 зад',      default=0, null=False, blank=True)
    bumper_pered_replace_kf_2000                 = models.IntegerField('Бампер замена 2000 ',      default=0, null=False, blank=True)       
    bumper_zad_replace_kf_2000                   = models.IntegerField('Бампер замена 2000 зад',      default=0, null=False, blank=True)

    bumper_pered_kf_3000                 = models.IntegerField('Бампер 3000 ',      default=0, null=False, blank=True)       
    bumper_zad_kf_3000                   = models.IntegerField('Бампер 3000 зад',      default=0, null=False, blank=True)
    bumper_pered_replace_kf_3000                 = models.IntegerField('Бампер 3000 ',      default=0, null=False, blank=True)       
    bumper_zad_replace_kf_3000                   = models.IntegerField('Бампер 3000 зад',      default=0, null=False, blank=True)

    bumper_pered_kf_5000                 = models.IntegerField('Бампер 5000 ',      default=0, null=False, blank=True)       
    bumper_zad_kf_5000                   = models.IntegerField('Бампер 5000 зад',      default=0, null=False, blank=True)
    bumper_pered_replace_kf_5000        = models.IntegerField('Бампер замена 5000 ',      default=0, null=False, blank=True)       
    bumper_zad_replace_kf_5000          = models.IntegerField('Бампер замена 5000 зад',      default=0, null=False, blank=True)
    
    bumper_pered_kf_5001                 = models.IntegerField('Бампер 5001 ',      default=0, null=False, blank=True)       
    bumper_zad_kf_5001                   = models.IntegerField('Бампер 5001 зад',      default=0, null=False, blank=True)
    bumper_pered_replace_kf_5001        = models.IntegerField('Бампер замена 5001 ',      default=0, null=False, blank=True)       
    bumper_zad_replace_kf_5001          = models.IntegerField('Бампер замена 5001 зад',      default=0, null=False, blank=True)
    
    to_1_200    = models.IntegerField('ТО 1 200',      default=0, null=False, blank=True)
    to_2_200    = models.IntegerField('ТО 2 200',      default=0, null=False, blank=True)
    to_3_200    = models.IntegerField('ТО 3 200',      default=0, null=False, blank=True)
    
    to_1_400    = models.IntegerField('ТО 1 400',      default=0, null=False, blank=True)
    to_2_400    = models.IntegerField('ТО 2 400',      default=0, null=False, blank=True)
    to_3_400    = models.IntegerField('ТО 3 400',      default=0, null=False, blank=True)
    
    to_1_700    = models.IntegerField('ТО 1 700',      default=0, null=False, blank=True)
    to_2_700    = models.IntegerField('ТО 2 700',      default=0, null=False, blank=True)
    to_3_700    = models.IntegerField('ТО 3 700',      default=0, null=False, blank=True)
    
    to_1_1200    = models.IntegerField('ТО 1 1200',      default=0, null=False, blank=True)
    to_2_1200    = models.IntegerField('ТО 2 1200',      default=0, null=False, blank=True)
    to_3_1200    = models.IntegerField('ТО 3 1200',      default=0, null=False, blank=True)
    
    to_1_2000    = models.IntegerField('ТО 1 2000',      default=0, null=False, blank=True)
    to_2_2000    = models.IntegerField('ТО 2 2000',      default=0, null=False, blank=True)
    to_3_2000    = models.IntegerField('ТО 3 2000',      default=0, null=False, blank=True)
    
    to_1_3000    = models.IntegerField('ТО 1 3000',      default=0, null=False, blank=True)
    to_2_3000    = models.IntegerField('ТО 2 3000',      default=0, null=False, blank=True)
    to_3_3000    = models.IntegerField('ТО 3 3000',      default=0, null=False, blank=True)
    
    # Безопасность - Подушка водителя
    airbag_driver_danger_amount_200 = models.IntegerField('Подушка водителя не исправна сумма 200', default=0, null=True, blank=True)
    airbag_driver_danger_kf_200 = models.IntegerField('Подушка водителя не исправна коэффициент 200', default=0, null=True, blank=True)
    airbag_driver_danger_amount_min_200 = models.IntegerField('Подушка водителя не исправна мин сумма 200', default=0, null=True, blank=True)
    airbag_driver_warning_amount_200 = models.IntegerField('Подушка водителя есть замечания сумма 200', default=0, null=True, blank=True)
    airbag_driver_warning_kf_200 = models.IntegerField('Подушка водителя есть замечания коэффициент 200', default=0, null=True, blank=True)
    airbag_driver_warning_amount_min_200 = models.IntegerField('Подушка водителя есть замечания мин сумма 200', default=0, null=True, blank=True)
    
    airbag_driver_danger_amount_400 = models.IntegerField('Подушка водителя не исправна сумма 400', default=0, null=True, blank=True)
    airbag_driver_danger_kf_400 = models.IntegerField('Подушка водителя не исправна коэффициент 400', default=0, null=True, blank=True)
    airbag_driver_danger_amount_min_400 = models.IntegerField('Подушка водителя не исправна мин сумма 400', default=0, null=True, blank=True)
    airbag_driver_warning_amount_400 = models.IntegerField('Подушка водителя есть замечания сумма 400', default=0, null=True, blank=True)
    airbag_driver_warning_kf_400 = models.IntegerField('Подушка водителя есть замечания коэффициент 400', default=0, null=True, blank=True)
    airbag_driver_warning_amount_min_400 = models.IntegerField('Подушка водителя есть замечания мин сумма 400', default=0, null=True, blank=True)
    
    airbag_driver_danger_amount_700 = models.IntegerField('Подушка водителя не исправна сумма 700', default=0, null=True, blank=True)
    airbag_driver_danger_kf_700 = models.IntegerField('Подушка водителя не исправна коэффициент 700', default=0, null=True, blank=True)
    airbag_driver_danger_amount_min_700 = models.IntegerField('Подушка водителя не исправна мин сумма 700', default=0, null=True, blank=True)
    airbag_driver_warning_amount_700 = models.IntegerField('Подушка водителя есть замечания сумма 700', default=0, null=True, blank=True)
    airbag_driver_warning_kf_700 = models.IntegerField('Подушка водителя есть замечания коэффициент 700', default=0, null=True, blank=True)
    airbag_driver_warning_amount_min_700 = models.IntegerField('Подушка водителя есть замечания мин сумма 700', default=0, null=True, blank=True)
    
    airbag_driver_danger_amount_1200 = models.IntegerField('Подушка водителя не исправна сумма 1200', default=0, null=True, blank=True)
    airbag_driver_danger_kf_1200 = models.IntegerField('Подушка водителя не исправна коэффициент 1200', default=0, null=True, blank=True)
    airbag_driver_danger_amount_min_1200 = models.IntegerField('Подушка водителя не исправна мин сумма 1200', default=0, null=True, blank=True)
    airbag_driver_warning_amount_1200 = models.IntegerField('Подушка водителя есть замечания сумма 1200', default=0, null=True, blank=True)
    airbag_driver_warning_kf_1200 = models.IntegerField('Подушка водителя есть замечания коэффициент 1200', default=0, null=True, blank=True)
    airbag_driver_warning_amount_min_1200 = models.IntegerField('Подушка водителя есть замечания мин сумма 1200', default=0, null=True, blank=True)
    
    airbag_driver_danger_amount_2000 = models.IntegerField('Подушка водителя не исправна сумма 2000', default=0, null=True, blank=True)
    airbag_driver_danger_kf_2000 = models.IntegerField('Подушка водителя не исправна коэффициент 2000', default=0, null=True, blank=True)
    airbag_driver_danger_amount_min_2000 = models.IntegerField('Подушка водителя не исправна мин сумма 2000', default=0, null=True, blank=True)
    airbag_driver_warning_amount_2000 = models.IntegerField('Подушка водителя есть замечания сумма 2000', default=0, null=True, blank=True)
    airbag_driver_warning_kf_2000 = models.IntegerField('Подушка водителя есть замечания коэффициент 2000', default=0, null=True, blank=True)
    airbag_driver_warning_amount_min_2000 = models.IntegerField('Подушка водителя есть замечания мин сумма 2000', default=0, null=True, blank=True)
    
    airbag_driver_danger_amount_3000 = models.IntegerField('Подушка водителя не исправна сумма 3000', default=0, null=True, blank=True)
    airbag_driver_danger_kf_3000 = models.IntegerField('Подушка водителя не исправна коэффициент 3000', default=0, null=True, blank=True)
    airbag_driver_danger_amount_min_3000 = models.IntegerField('Подушка водителя не исправна мин сумма 3000', default=0, null=True, blank=True)
    airbag_driver_warning_amount_3000 = models.IntegerField('Подушка водителя есть замечания сумма 3000', default=0, null=True, blank=True)
    airbag_driver_warning_kf_3000 = models.IntegerField('Подушка водителя есть замечания коэффициент 3000', default=0, null=True, blank=True)
    airbag_driver_warning_amount_min_3000 = models.IntegerField('Подушка водителя есть замечания мин сумма 3000', default=0, null=True, blank=True)
    
    airbag_driver_danger_amount_5000 = models.IntegerField('Подушка водителя не исправна сумма 5000', default=0, null=True, blank=True)
    airbag_driver_danger_kf_5000 = models.IntegerField('Подушка водителя не исправна коэффициент 5000', default=0, null=True, blank=True)
    airbag_driver_danger_amount_min_5000 = models.IntegerField('Подушка водителя не исправна мин сумма 5000', default=0, null=True, blank=True)
    airbag_driver_warning_amount_5000 = models.IntegerField('Подушка водителя есть замечания сумма 5000', default=0, null=True, blank=True)
    airbag_driver_warning_kf_5000 = models.IntegerField('Подушка водителя есть замечания коэффициент 5000', default=0, null=True, blank=True)
    airbag_driver_warning_amount_min_5000 = models.IntegerField('Подушка водителя есть замечания мин сумма 5000', default=0, null=True, blank=True)
    
    airbag_driver_danger_amount_5001 = models.IntegerField('Подушка водителя не исправна сумма 5001', default=0, null=True, blank=True)
    airbag_driver_danger_kf_5001 = models.IntegerField('Подушка водителя не исправна коэффициент 5001', default=0, null=True, blank=True)
    airbag_driver_danger_amount_min_5001 = models.IntegerField('Подушка водителя не исправна мин сумма 5001', default=0, null=True, blank=True)
    airbag_driver_warning_amount_5001 = models.IntegerField('Подушка водителя есть замечания сумма 5001', default=0, null=True, blank=True)
    airbag_driver_warning_kf_5001 = models.IntegerField('Подушка водителя есть замечания коэффициент 5001', default=0, null=True, blank=True)
    airbag_driver_warning_amount_min_5001 = models.IntegerField('Подушка водителя есть замечания мин сумма 5001', default=0, null=True, blank=True)
    
    # Безопасность - Подушка пассажира + перешив торпеды
    airbag_passenger_danger_amount_200 = models.IntegerField('Подушка пассажира + перешив торпеды не исправна сумма 200', default=0, null=True, blank=True)
    airbag_passenger_danger_kf_200 = models.IntegerField('Подушка пассажира + перешив торпеды не исправна коэффициент 200', default=0, null=True, blank=True)
    airbag_passenger_danger_amount_min_200 = models.IntegerField('Подушка пассажира + перешив торпеды не исправна мин сумма 200', default=0, null=True, blank=True)
    airbag_passenger_warning_amount_200 = models.IntegerField('Подушка пассажира + перешив торпеды есть замечания сумма 200', default=0, null=True, blank=True)
    airbag_passenger_warning_kf_200 = models.IntegerField('Подушка пассажира + перешив торпеды есть замечания коэффициент 200', default=0, null=True, blank=True)
    airbag_passenger_warning_amount_min_200 = models.IntegerField('Подушка пассажира + перешив торпеды есть замечания мин сумма 200', default=0, null=True, blank=True)
    
    airbag_passenger_danger_amount_400 = models.IntegerField('Подушка пассажира + перешив торпеды не исправна сумма 400', default=0, null=True, blank=True)
    airbag_passenger_danger_kf_400 = models.IntegerField('Подушка пассажира + перешив торпеды не исправна коэффициент 400', default=0, null=True, blank=True)
    airbag_passenger_danger_amount_min_400 = models.IntegerField('Подушка пассажира + перешив торпеды не исправна мин сумма 400', default=0, null=True, blank=True)
    airbag_passenger_warning_amount_400 = models.IntegerField('Подушка пассажира + перешив торпеды есть замечания сумма 400', default=0, null=True, blank=True)
    airbag_passenger_warning_kf_400 = models.IntegerField('Подушка пассажира + перешив торпеды есть замечания коэффициент 400', default=0, null=True, blank=True)
    airbag_passenger_warning_amount_min_400 = models.IntegerField('Подушка пассажира + перешив торпеды есть замечания мин сумма 400', default=0, null=True, blank=True)
    
    airbag_passenger_danger_amount_700 = models.IntegerField('Подушка пассажира + перешив торпеды не исправна сумма 700', default=0, null=True, blank=True)
    airbag_passenger_danger_kf_700 = models.IntegerField('Подушка пассажира + перешив торпеды не исправна коэффициент 700', default=0, null=True, blank=True)
    airbag_passenger_danger_amount_min_700 = models.IntegerField('Подушка пассажира + перешив торпеды не исправна мин сумма 700', default=0, null=True, blank=True)
    airbag_passenger_warning_amount_700 = models.IntegerField('Подушка пассажира + перешив торпеды есть замечания сумма 700', default=0, null=True, blank=True)
    airbag_passenger_warning_kf_700 = models.IntegerField('Подушка пассажира + перешив торпеды есть замечания коэффициент 700', default=0, null=True, blank=True)
    airbag_passenger_warning_amount_min_700 = models.IntegerField('Подушка пассажира + перешив торпеды есть замечания мин сумма 700', default=0, null=True, blank=True)
    
    airbag_passenger_danger_amount_1200 = models.IntegerField('Подушка пассажира + перешив торпеды не исправна сумма 1200', default=0, null=True, blank=True)
    airbag_passenger_danger_kf_1200 = models.IntegerField('Подушка пассажира + перешив торпеды не исправна коэффициент 1200', default=0, null=True, blank=True)
    airbag_passenger_danger_amount_min_1200 = models.IntegerField('Подушка пассажира + перешив торпеды не исправна мин сумма 1200', default=0, null=True, blank=True)
    airbag_passenger_warning_amount_1200 = models.IntegerField('Подушка пассажира + перешив торпеды есть замечания сумма 1200', default=0, null=True, blank=True)
    airbag_passenger_warning_kf_1200 = models.IntegerField('Подушка пассажира + перешив торпеды есть замечания коэффициент 1200', default=0, null=True, blank=True)
    airbag_passenger_warning_amount_min_1200 = models.IntegerField('Подушка пассажира + перешив торпеды есть замечания мин сумма 1200', default=0, null=True, blank=True)
    
    airbag_passenger_danger_amount_2000 = models.IntegerField('Подушка пассажира + перешив торпеды не исправна сумма 2000', default=0, null=True, blank=True)
    airbag_passenger_danger_kf_2000 = models.IntegerField('Подушка пассажира + перешив торпеды не исправна коэффициент 2000', default=0, null=True, blank=True)
    airbag_passenger_danger_amount_min_2000 = models.IntegerField('Подушка пассажира + перешив торпеды не исправна мин сумма 2000', default=0, null=True, blank=True)
    airbag_passenger_warning_amount_2000 = models.IntegerField('Подушка пассажира + перешив торпеды есть замечания сумма 2000', default=0, null=True, blank=True)
    airbag_passenger_warning_kf_2000 = models.IntegerField('Подушка пассажира + перешив торпеды есть замечания коэффициент 2000', default=0, null=True, blank=True)
    airbag_passenger_warning_amount_min_2000 = models.IntegerField('Подушка пассажира + перешив торпеды есть замечания мин сумма 2000', default=0, null=True, blank=True)
    
    airbag_passenger_danger_amount_3000 = models.IntegerField('Подушка пассажира + перешив торпеды не исправна сумма 3000', default=0, null=True, blank=True)
    airbag_passenger_danger_kf_3000 = models.IntegerField('Подушка пассажира + перешив торпеды не исправна коэффициент 3000', default=0, null=True, blank=True)
    airbag_passenger_danger_amount_min_3000 = models.IntegerField('Подушка пассажира + перешив торпеды не исправна мин сумма 3000', default=0, null=True, blank=True)
    airbag_passenger_warning_amount_3000 = models.IntegerField('Подушка пассажира + перешив торпеды есть замечания сумма 3000', default=0, null=True, blank=True)
    airbag_passenger_warning_kf_3000 = models.IntegerField('Подушка пассажира + перешив торпеды есть замечания коэффициент 3000', default=0, null=True, blank=True)
    airbag_passenger_warning_amount_min_3000 = models.IntegerField('Подушка пассажира + перешив торпеды есть замечания мин сумма 3000', default=0, null=True, blank=True)
    
    airbag_passenger_danger_amount_5000 = models.IntegerField('Подушка пассажира + перешив торпеды не исправна сумма 5000', default=0, null=True, blank=True)
    airbag_passenger_danger_kf_5000 = models.IntegerField('Подушка пассажира + перешив торпеды не исправна коэффициент 5000', default=0, null=True, blank=True)
    airbag_passenger_danger_amount_min_5000 = models.IntegerField('Подушка пассажира + перешив торпеды не исправна мин сумма 5000', default=0, null=True, blank=True)
    airbag_passenger_warning_amount_5000 = models.IntegerField('Подушка пассажира + перешив торпеды есть замечания сумма 5000', default=0, null=True, blank=True)
    airbag_passenger_warning_kf_5000 = models.IntegerField('Подушка пассажира + перешив торпеды есть замечания коэффициент 5000', default=0, null=True, blank=True)
    airbag_passenger_warning_amount_min_5000 = models.IntegerField('Подушка пассажира + перешив торпеды есть замечания мин сумма 5000', default=0, null=True, blank=True)
    
    airbag_passenger_danger_amount_5001 = models.IntegerField('Подушка пассажира + перешив торпеды не исправна сумма 5001', default=0, null=True, blank=True)
    airbag_passenger_danger_kf_5001 = models.IntegerField('Подушка пассажира + перешив торпеды не исправна коэффициент 5001', default=0, null=True, blank=True)
    airbag_passenger_danger_amount_min_5001 = models.IntegerField('Подушка пассажира + перешив торпеды не исправна мин сумма 5001', default=0, null=True, blank=True)
    airbag_passenger_warning_amount_5001 = models.IntegerField('Подушка пассажира + перешив торпеды есть замечания сумма 5001', default=0, null=True, blank=True)
    airbag_passenger_warning_kf_5001 = models.IntegerField('Подушка пассажира + перешив торпеды есть замечания коэффициент 5001', default=0, null=True, blank=True)
    airbag_passenger_warning_amount_min_5001 = models.IntegerField('Подушка пассажира + перешив торпеды есть замечания мин сумма 5001', default=0, null=True, blank=True)
    
    # Безопасность - Боковые подушки
    airbag_side_danger_amount_200 = models.IntegerField('Боковые подушки не исправны сумма 200', default=0, null=True, blank=True)
    airbag_side_danger_kf_200 = models.IntegerField('Боковые подушки не исправны коэффициент 200', default=0, null=True, blank=True)
    airbag_side_danger_amount_min_200 = models.IntegerField('Боковые подушки не исправны мин сумма 200', default=0, null=True, blank=True)
    airbag_side_warning_amount_200 = models.IntegerField('Боковые подушки есть замечания сумма 200', default=0, null=True, blank=True)
    airbag_side_warning_kf_200 = models.IntegerField('Боковые подушки есть замечания коэффициент 200', default=0, null=True, blank=True)
    airbag_side_warning_amount_min_200 = models.IntegerField('Боковые подушки есть замечания мин сумма 200', default=0, null=True, blank=True)
    
    airbag_side_danger_amount_400 = models.IntegerField('Боковые подушки не исправны сумма 400', default=0, null=True, blank=True)
    airbag_side_danger_kf_400 = models.IntegerField('Боковые подушки не исправны коэффициент 400', default=0, null=True, blank=True)
    airbag_side_danger_amount_min_400 = models.IntegerField('Боковые подушки не исправны мин сумма 400', default=0, null=True, blank=True)
    airbag_side_warning_amount_400 = models.IntegerField('Боковые подушки есть замечания сумма 400', default=0, null=True, blank=True)
    airbag_side_warning_kf_400 = models.IntegerField('Боковые подушки есть замечания коэффициент 400', default=0, null=True, blank=True)
    airbag_side_warning_amount_min_400 = models.IntegerField('Боковые подушки есть замечания мин сумма 400', default=0, null=True, blank=True)
    
    airbag_side_danger_amount_700 = models.IntegerField('Боковые подушки не исправны сумма 700', default=0, null=True, blank=True)
    airbag_side_danger_kf_700 = models.IntegerField('Боковые подушки не исправны коэффициент 700', default=0, null=True, blank=True)
    airbag_side_danger_amount_min_700 = models.IntegerField('Боковые подушки не исправны мин сумма 700', default=0, null=True, blank=True)
    airbag_side_warning_amount_700 = models.IntegerField('Боковые подушки есть замечания сумма 700', default=0, null=True, blank=True)
    airbag_side_warning_kf_700 = models.IntegerField('Боковые подушки есть замечания коэффициент 700', default=0, null=True, blank=True)
    airbag_side_warning_amount_min_700 = models.IntegerField('Боковые подушки есть замечания мин сумма 700', default=0, null=True, blank=True)
    
    airbag_side_danger_amount_1200 = models.IntegerField('Боковые подушки не исправны сумма 1200', default=0, null=True, blank=True)
    airbag_side_danger_kf_1200 = models.IntegerField('Боковые подушки не исправны коэффициент 1200', default=0, null=True, blank=True)
    airbag_side_danger_amount_min_1200 = models.IntegerField('Боковые подушки не исправны мин сумма 1200', default=0, null=True, blank=True)
    airbag_side_warning_amount_1200 = models.IntegerField('Боковые подушки есть замечания сумма 1200', default=0, null=True, blank=True)
    airbag_side_warning_kf_1200 = models.IntegerField('Боковые подушки есть замечания коэффициент 1200', default=0, null=True, blank=True)
    airbag_side_warning_amount_min_1200 = models.IntegerField('Боковые подушки есть замечания мин сумма 1200', default=0, null=True, blank=True)
    
    airbag_side_danger_amount_2000 = models.IntegerField('Боковые подушки не исправны сумма 2000', default=0, null=True, blank=True)
    airbag_side_danger_kf_2000 = models.IntegerField('Боковые подушки не исправны коэффициент 2000', default=0, null=True, blank=True)
    airbag_side_danger_amount_min_2000 = models.IntegerField('Боковые подушки не исправны мин сумма 2000', default=0, null=True, blank=True)
    airbag_side_warning_amount_2000 = models.IntegerField('Боковые подушки есть замечания сумма 2000', default=0, null=True, blank=True)
    airbag_side_warning_kf_2000 = models.IntegerField('Боковые подушки есть замечания коэффициент 2000', default=0, null=True, blank=True)
    airbag_side_warning_amount_min_2000 = models.IntegerField('Боковые подушки есть замечания мин сумма 2000', default=0, null=True, blank=True)
    
    airbag_side_danger_amount_3000 = models.IntegerField('Боковые подушки не исправны сумма 3000', default=0, null=True, blank=True)
    airbag_side_danger_kf_3000 = models.IntegerField('Боковые подушки не исправны коэффициент 3000', default=0, null=True, blank=True)
    airbag_side_danger_amount_min_3000 = models.IntegerField('Боковые подушки не исправны мин сумма 3000', default=0, null=True, blank=True)
    airbag_side_warning_amount_3000 = models.IntegerField('Боковые подушки есть замечания сумма 3000', default=0, null=True, blank=True)
    airbag_side_warning_kf_3000 = models.IntegerField('Боковые подушки есть замечания коэффициент 3000', default=0, null=True, blank=True)
    airbag_side_warning_amount_min_3000 = models.IntegerField('Боковые подушки есть замечания мин сумма 3000', default=0, null=True, blank=True)
    
    airbag_side_danger_amount_5000 = models.IntegerField('Боковые подушки не исправны сумма 5000', default=0, null=True, blank=True)
    airbag_side_danger_kf_5000 = models.IntegerField('Боковые подушки не исправны коэффициент 5000', default=0, null=True, blank=True)
    airbag_side_danger_amount_min_5000 = models.IntegerField('Боковые подушки не исправны мин сумма 5000', default=0, null=True, blank=True)
    airbag_side_warning_amount_5000 = models.IntegerField('Боковые подушки есть замечания сумма 5000', default=0, null=True, blank=True)
    airbag_side_warning_kf_5000 = models.IntegerField('Боковые подушки есть замечания коэффициент 5000', default=0, null=True, blank=True)
    airbag_side_warning_amount_min_5000 = models.IntegerField('Боковые подушки есть замечания мин сумма 5000', default=0, null=True, blank=True)
    
    airbag_side_danger_amount_5001 = models.IntegerField('Боковые подушки не исправны сумма 5001', default=0, null=True, blank=True)
    airbag_side_danger_kf_5001 = models.IntegerField('Боковые подушки не исправны коэффициент 5001', default=0, null=True, blank=True)
    airbag_side_danger_amount_min_5001 = models.IntegerField('Боковые подушки не исправны мин сумма 5001', default=0, null=True, blank=True)
    airbag_side_warning_amount_5001 = models.IntegerField('Боковые подушки есть замечания сумма 5001', default=0, null=True, blank=True)
    airbag_side_warning_kf_5001 = models.IntegerField('Боковые подушки есть замечания коэффициент 5001', default=0, null=True, blank=True)
    airbag_side_warning_amount_min_5001 = models.IntegerField('Боковые подушки есть замечания мин сумма 5001', default=0, null=True, blank=True)
    
    # Безопасность - Подушка коленная
    airbag_knee_danger_amount_200 = models.IntegerField('Подушка коленная не исправна сумма 200', default=0, null=True, blank=True)
    airbag_knee_danger_kf_200 = models.IntegerField('Подушка коленная не исправна коэффициент 200', default=0, null=True, blank=True)
    airbag_knee_danger_amount_min_200 = models.IntegerField('Подушка коленная не исправна мин сумма 200', default=0, null=True, blank=True)
    airbag_knee_warning_amount_200 = models.IntegerField('Подушка коленная есть замечания сумма 200', default=0, null=True, blank=True)
    airbag_knee_warning_kf_200 = models.IntegerField('Подушка коленная есть замечания коэффициент 200', default=0, null=True, blank=True)
    airbag_knee_warning_amount_min_200 = models.IntegerField('Подушка коленная есть замечания мин сумма 200', default=0, null=True, blank=True)
    
    airbag_knee_danger_amount_400 = models.IntegerField('Подушка коленная не исправна сумма 400', default=0, null=True, blank=True)
    airbag_knee_danger_kf_400 = models.IntegerField('Подушка коленная не исправна коэффициент 400', default=0, null=True, blank=True)
    airbag_knee_danger_amount_min_400 = models.IntegerField('Подушка коленная не исправна мин сумма 400', default=0, null=True, blank=True)
    airbag_knee_warning_amount_400 = models.IntegerField('Подушка коленная есть замечания сумма 400', default=0, null=True, blank=True)
    airbag_knee_warning_kf_400 = models.IntegerField('Подушка коленная есть замечания коэффициент 400', default=0, null=True, blank=True)
    airbag_knee_warning_amount_min_400 = models.IntegerField('Подушка коленная есть замечания мин сумма 400', default=0, null=True, blank=True)
    
    airbag_knee_danger_amount_700 = models.IntegerField('Подушка коленная не исправна сумма 700', default=0, null=True, blank=True)
    airbag_knee_danger_kf_700 = models.IntegerField('Подушка коленная не исправна коэффициент 700', default=0, null=True, blank=True)
    airbag_knee_danger_amount_min_700 = models.IntegerField('Подушка коленная не исправна мин сумма 700', default=0, null=True, blank=True)
    airbag_knee_warning_amount_700 = models.IntegerField('Подушка коленная есть замечания сумма 700', default=0, null=True, blank=True)
    airbag_knee_warning_kf_700 = models.IntegerField('Подушка коленная есть замечания коэффициент 700', default=0, null=True, blank=True)
    airbag_knee_warning_amount_min_700 = models.IntegerField('Подушка коленная есть замечания мин сумма 700', default=0, null=True, blank=True)
    
    airbag_knee_danger_amount_1200 = models.IntegerField('Подушка коленная не исправна сумма 1200', default=0, null=True, blank=True)
    airbag_knee_danger_kf_1200 = models.IntegerField('Подушка коленная не исправна коэффициент 1200', default=0, null=True, blank=True)
    airbag_knee_danger_amount_min_1200 = models.IntegerField('Подушка коленная не исправна мин сумма 1200', default=0, null=True, blank=True)
    airbag_knee_warning_amount_1200 = models.IntegerField('Подушка коленная есть замечания сумма 1200', default=0, null=True, blank=True)
    airbag_knee_warning_kf_1200 = models.IntegerField('Подушка коленная есть замечания коэффициент 1200', default=0, null=True, blank=True)
    airbag_knee_warning_amount_min_1200 = models.IntegerField('Подушка коленная есть замечания мин сумма 1200', default=0, null=True, blank=True)
    
    airbag_knee_danger_amount_2000 = models.IntegerField('Подушка коленная не исправна сумма 2000', default=0, null=True, blank=True)
    airbag_knee_danger_kf_2000 = models.IntegerField('Подушка коленная не исправна коэффициент 2000', default=0, null=True, blank=True)
    airbag_knee_danger_amount_min_2000 = models.IntegerField('Подушка коленная не исправна мин сумма 2000', default=0, null=True, blank=True)
    airbag_knee_warning_amount_2000 = models.IntegerField('Подушка коленная есть замечания сумма 2000', default=0, null=True, blank=True)
    airbag_knee_warning_kf_2000 = models.IntegerField('Подушка коленная есть замечания коэффициент 2000', default=0, null=True, blank=True)
    airbag_knee_warning_amount_min_2000 = models.IntegerField('Подушка коленная есть замечания мин сумма 2000', default=0, null=True, blank=True)
    
    airbag_knee_danger_amount_3000 = models.IntegerField('Подушка коленная не исправна сумма 3000', default=0, null=True, blank=True)
    airbag_knee_danger_kf_3000 = models.IntegerField('Подушка коленная не исправна коэффициент 3000', default=0, null=True, blank=True)
    airbag_knee_danger_amount_min_3000 = models.IntegerField('Подушка коленная не исправна мин сумма 3000', default=0, null=True, blank=True)
    airbag_knee_warning_amount_3000 = models.IntegerField('Подушка коленная есть замечания сумма 3000', default=0, null=True, blank=True)
    airbag_knee_warning_kf_3000 = models.IntegerField('Подушка коленная есть замечания коэффициент 3000', default=0, null=True, blank=True)
    airbag_knee_warning_amount_min_3000 = models.IntegerField('Подушка коленная есть замечания мин сумма 3000', default=0, null=True, blank=True)
    
    airbag_knee_danger_amount_5000 = models.IntegerField('Подушка коленная не исправна сумма 5000', default=0, null=True, blank=True)
    airbag_knee_danger_kf_5000 = models.IntegerField('Подушка коленная не исправна коэффициент 5000', default=0, null=True, blank=True)
    airbag_knee_danger_amount_min_5000 = models.IntegerField('Подушка коленная не исправна мин сумма 5000', default=0, null=True, blank=True)
    airbag_knee_warning_amount_5000 = models.IntegerField('Подушка коленная есть замечания сумма 5000', default=0, null=True, blank=True)
    airbag_knee_warning_kf_5000 = models.IntegerField('Подушка коленная есть замечания коэффициент 5000', default=0, null=True, blank=True)
    airbag_knee_warning_amount_min_5000 = models.IntegerField('Подушка коленная есть замечания мин сумма 5000', default=0, null=True, blank=True)
    
    airbag_knee_danger_amount_5001 = models.IntegerField('Подушка коленная не исправна сумма 5001', default=0, null=True, blank=True)
    airbag_knee_danger_kf_5001 = models.IntegerField('Подушка коленная не исправна коэффициент 5001', default=0, null=True, blank=True)
    airbag_knee_danger_amount_min_5001 = models.IntegerField('Подушка коленная не исправна мин сумма 5001', default=0, null=True, blank=True)
    airbag_knee_warning_amount_5001 = models.IntegerField('Подушка коленная есть замечания сумма 5001', default=0, null=True, blank=True)
    airbag_knee_warning_kf_5001 = models.IntegerField('Подушка коленная есть замечания коэффициент 5001', default=0, null=True, blank=True)
    airbag_knee_warning_amount_min_5001 = models.IntegerField('Подушка коленная есть замечания мин сумма 5001', default=0, null=True, blank=True)
    
    # Безопасность - Восстановление ремней безопасности
    seat_belt_restore_danger_amount_200 = models.IntegerField('Восстановление ремней безопасности не исправно сумма 200', default=0, null=True, blank=True)
    seat_belt_restore_danger_kf_200 = models.IntegerField('Восстановление ремней безопасности не исправно коэффициент 200', default=0, null=True, blank=True)
    seat_belt_restore_danger_amount_min_200 = models.IntegerField('Восстановление ремней безопасности не исправно мин сумма 200', default=0, null=True, blank=True)
    seat_belt_restore_warning_amount_200 = models.IntegerField('Восстановление ремней безопасности есть замечания сумма 200', default=0, null=True, blank=True)
    seat_belt_restore_warning_kf_200 = models.IntegerField('Восстановление ремней безопасности есть замечания коэффициент 200', default=0, null=True, blank=True)
    seat_belt_restore_warning_amount_min_200 = models.IntegerField('Восстановление ремней безопасности есть замечания мин сумма 200', default=0, null=True, blank=True)
    
    seat_belt_restore_danger_amount_400 = models.IntegerField('Восстановление ремней безопасности не исправно сумма 400', default=0, null=True, blank=True)
    seat_belt_restore_danger_kf_400 = models.IntegerField('Восстановление ремней безопасности не исправно коэффициент 400', default=0, null=True, blank=True)
    seat_belt_restore_danger_amount_min_400 = models.IntegerField('Восстановление ремней безопасности не исправно мин сумма 400', default=0, null=True, blank=True)
    seat_belt_restore_warning_amount_400 = models.IntegerField('Восстановление ремней безопасности есть замечания сумма 400', default=0, null=True, blank=True)
    seat_belt_restore_warning_kf_400 = models.IntegerField('Восстановление ремней безопасности есть замечания коэффициент 400', default=0, null=True, blank=True)
    seat_belt_restore_warning_amount_min_400 = models.IntegerField('Восстановление ремней безопасности есть замечания мин сумма 400', default=0, null=True, blank=True)
    
    seat_belt_restore_danger_amount_700 = models.IntegerField('Восстановление ремней безопасности не исправно сумма 700', default=0, null=True, blank=True)
    seat_belt_restore_danger_kf_700 = models.IntegerField('Восстановление ремней безопасности не исправно коэффициент 700', default=0, null=True, blank=True)
    seat_belt_restore_danger_amount_min_700 = models.IntegerField('Восстановление ремней безопасности не исправно мин сумма 700', default=0, null=True, blank=True)
    seat_belt_restore_warning_amount_700 = models.IntegerField('Восстановление ремней безопасности есть замечания сумма 700', default=0, null=True, blank=True)
    seat_belt_restore_warning_kf_700 = models.IntegerField('Восстановление ремней безопасности есть замечания коэффициент 700', default=0, null=True, blank=True)
    seat_belt_restore_warning_amount_min_700 = models.IntegerField('Восстановление ремней безопасности есть замечания мин сумма 700', default=0, null=True, blank=True)
    
    seat_belt_restore_danger_amount_1200 = models.IntegerField('Восстановление ремней безопасности не исправно сумма 1200', default=0, null=True, blank=True)
    seat_belt_restore_danger_kf_1200 = models.IntegerField('Восстановление ремней безопасности не исправно коэффициент 1200', default=0, null=True, blank=True)
    seat_belt_restore_danger_amount_min_1200 = models.IntegerField('Восстановление ремней безопасности не исправно мин сумма 1200', default=0, null=True, blank=True)
    seat_belt_restore_warning_amount_1200 = models.IntegerField('Восстановление ремней безопасности есть замечания сумма 1200', default=0, null=True, blank=True)
    seat_belt_restore_warning_kf_1200 = models.IntegerField('Восстановление ремней безопасности есть замечания коэффициент 1200', default=0, null=True, blank=True)
    seat_belt_restore_warning_amount_min_1200 = models.IntegerField('Восстановление ремней безопасности есть замечания мин сумма 1200', default=0, null=True, blank=True)
    
    seat_belt_restore_danger_amount_2000 = models.IntegerField('Восстановление ремней безопасности не исправно сумма 2000', default=0, null=True, blank=True)
    seat_belt_restore_danger_kf_2000 = models.IntegerField('Восстановление ремней безопасности не исправно коэффициент 2000', default=0, null=True, blank=True)
    seat_belt_restore_danger_amount_min_2000 = models.IntegerField('Восстановление ремней безопасности не исправно мин сумма 2000', default=0, null=True, blank=True)
    seat_belt_restore_warning_amount_2000 = models.IntegerField('Восстановление ремней безопасности есть замечания сумма 2000', default=0, null=True, blank=True)
    seat_belt_restore_warning_kf_2000 = models.IntegerField('Восстановление ремней безопасности есть замечания коэффициент 2000', default=0, null=True, blank=True)
    seat_belt_restore_warning_amount_min_2000 = models.IntegerField('Восстановление ремней безопасности есть замечания мин сумма 2000', default=0, null=True, blank=True)
    
    seat_belt_restore_danger_amount_3000 = models.IntegerField('Восстановление ремней безопасности не исправно сумма 3000', default=0, null=True, blank=True)
    seat_belt_restore_danger_kf_3000 = models.IntegerField('Восстановление ремней безопасности не исправно коэффициент 3000', default=0, null=True, blank=True)
    seat_belt_restore_danger_amount_min_3000 = models.IntegerField('Восстановление ремней безопасности не исправно мин сумма 3000', default=0, null=True, blank=True)
    seat_belt_restore_warning_amount_3000 = models.IntegerField('Восстановление ремней безопасности есть замечания сумма 3000', default=0, null=True, blank=True)
    seat_belt_restore_warning_kf_3000 = models.IntegerField('Восстановление ремней безопасности есть замечания коэффициент 3000', default=0, null=True, blank=True)
    seat_belt_restore_warning_amount_min_3000 = models.IntegerField('Восстановление ремней безопасности есть замечания мин сумма 3000', default=0, null=True, blank=True)
    
    seat_belt_restore_danger_amount_5000 = models.IntegerField('Восстановление ремней безопасности не исправно сумма 5000', default=0, null=True, blank=True)
    seat_belt_restore_danger_kf_5000 = models.IntegerField('Восстановление ремней безопасности не исправно коэффициент 5000', default=0, null=True, blank=True)
    seat_belt_restore_danger_amount_min_5000 = models.IntegerField('Восстановление ремней безопасности не исправно мин сумма 5000', default=0, null=True, blank=True)
    seat_belt_restore_warning_amount_5000 = models.IntegerField('Восстановление ремней безопасности есть замечания сумма 5000', default=0, null=True, blank=True)
    seat_belt_restore_warning_kf_5000 = models.IntegerField('Восстановление ремней безопасности есть замечания коэффициент 5000', default=0, null=True, blank=True)
    seat_belt_restore_warning_amount_min_5000 = models.IntegerField('Восстановление ремней безопасности есть замечания мин сумма 5000', default=0, null=True, blank=True)
    
    seat_belt_restore_danger_amount_5001 = models.IntegerField('Восстановление ремней безопасности не исправно сумма 5001', default=0, null=True, blank=True)
    seat_belt_restore_danger_kf_5001 = models.IntegerField('Восстановление ремней безопасности не исправно коэффициент 5001', default=0, null=True, blank=True)
    seat_belt_restore_danger_amount_min_5001 = models.IntegerField('Восстановление ремней безопасности не исправно мин сумма 5001', default=0, null=True, blank=True)
    seat_belt_restore_warning_amount_5001 = models.IntegerField('Восстановление ремней безопасности есть замечания сумма 5001', default=0, null=True, blank=True)
    seat_belt_restore_warning_kf_5001 = models.IntegerField('Восстановление ремней безопасности есть замечания коэффициент 5001', default=0, null=True, blank=True)
    seat_belt_restore_warning_amount_min_5001 = models.IntegerField('Восстановление ремней безопасности есть замечания мин сумма 5001', default=0, null=True, blank=True)
    
    # Безопасность - Блок SRS
    srs_block_danger_amount_200 = models.IntegerField('Блок SRS не исправен сумма 200', default=0, null=True, blank=True)
    srs_block_danger_kf_200 = models.IntegerField('Блок SRS не исправен коэффициент 200', default=0, null=True, blank=True)
    srs_block_danger_amount_min_200 = models.IntegerField('Блок SRS не исправен мин сумма 200', default=0, null=True, blank=True)
    srs_block_warning_amount_200 = models.IntegerField('Блок SRS есть замечания сумма 200', default=0, null=True, blank=True)
    srs_block_warning_kf_200 = models.IntegerField('Блок SRS есть замечания коэффициент 200', default=0, null=True, blank=True)
    srs_block_warning_amount_min_200 = models.IntegerField('Блок SRS есть замечания мин сумма 200', default=0, null=True, blank=True)
    
    srs_block_danger_amount_400 = models.IntegerField('Блок SRS не исправен сумма 400', default=0, null=True, blank=True)
    srs_block_danger_kf_400 = models.IntegerField('Блок SRS не исправен коэффициент 400', default=0, null=True, blank=True)
    srs_block_danger_amount_min_400 = models.IntegerField('Блок SRS не исправен мин сумма 400', default=0, null=True, blank=True)
    srs_block_warning_amount_400 = models.IntegerField('Блок SRS есть замечания сумма 400', default=0, null=True, blank=True)
    srs_block_warning_kf_400 = models.IntegerField('Блок SRS есть замечания коэффициент 400', default=0, null=True, blank=True)
    srs_block_warning_amount_min_400 = models.IntegerField('Блок SRS есть замечания мин сумма 400', default=0, null=True, blank=True)
    
    srs_block_danger_amount_700 = models.IntegerField('Блок SRS не исправен сумма 700', default=0, null=True, blank=True)
    srs_block_danger_kf_700 = models.IntegerField('Блок SRS не исправен коэффициент 700', default=0, null=True, blank=True)
    srs_block_danger_amount_min_700 = models.IntegerField('Блок SRS не исправен мин сумма 700', default=0, null=True, blank=True)
    srs_block_warning_amount_700 = models.IntegerField('Блок SRS есть замечания сумма 700', default=0, null=True, blank=True)
    srs_block_warning_kf_700 = models.IntegerField('Блок SRS есть замечания коэффициент 700', default=0, null=True, blank=True)
    srs_block_warning_amount_min_700 = models.IntegerField('Блок SRS есть замечания мин сумма 700', default=0, null=True, blank=True)
    
    srs_block_danger_amount_1200 = models.IntegerField('Блок SRS не исправен сумма 1200', default=0, null=True, blank=True)
    srs_block_danger_kf_1200 = models.IntegerField('Блок SRS не исправен коэффициент 1200', default=0, null=True, blank=True)
    srs_block_danger_amount_min_1200 = models.IntegerField('Блок SRS не исправен мин сумма 1200', default=0, null=True, blank=True)
    srs_block_warning_amount_1200 = models.IntegerField('Блок SRS есть замечания сумма 1200', default=0, null=True, blank=True)
    srs_block_warning_kf_1200 = models.IntegerField('Блок SRS есть замечания коэффициент 1200', default=0, null=True, blank=True)
    srs_block_warning_amount_min_1200 = models.IntegerField('Блок SRS есть замечания мин сумма 1200', default=0, null=True, blank=True)
    
    srs_block_danger_amount_2000 = models.IntegerField('Блок SRS не исправен сумма 2000', default=0, null=True, blank=True)
    srs_block_danger_kf_2000 = models.IntegerField('Блок SRS не исправен коэффициент 2000', default=0, null=True, blank=True)
    srs_block_danger_amount_min_2000 = models.IntegerField('Блок SRS не исправен мин сумма 2000', default=0, null=True, blank=True)
    srs_block_warning_amount_2000 = models.IntegerField('Блок SRS есть замечания сумма 2000', default=0, null=True, blank=True)
    srs_block_warning_kf_2000 = models.IntegerField('Блок SRS есть замечания коэффициент 2000', default=0, null=True, blank=True)
    srs_block_warning_amount_min_2000 = models.IntegerField('Блок SRS есть замечания мин сумма 2000', default=0, null=True, blank=True)
    
    srs_block_danger_amount_3000 = models.IntegerField('Блок SRS не исправен сумма 3000', default=0, null=True, blank=True)
    srs_block_danger_kf_3000 = models.IntegerField('Блок SRS не исправен коэффициент 3000', default=0, null=True, blank=True)
    srs_block_danger_amount_min_3000 = models.IntegerField('Блок SRS не исправен мин сумма 3000', default=0, null=True, blank=True)
    srs_block_warning_amount_3000 = models.IntegerField('Блок SRS есть замечания сумма 3000', default=0, null=True, blank=True)
    srs_block_warning_kf_3000 = models.IntegerField('Блок SRS есть замечания коэффициент 3000', default=0, null=True, blank=True)
    srs_block_warning_amount_min_3000 = models.IntegerField('Блок SRS есть замечания мин сумма 3000', default=0, null=True, blank=True)
    
    srs_block_danger_amount_5000 = models.IntegerField('Блок SRS не исправен сумма 5000', default=0, null=True, blank=True)
    srs_block_danger_kf_5000 = models.IntegerField('Блок SRS не исправен коэффициент 5000', default=0, null=True, blank=True)
    srs_block_danger_amount_min_5000 = models.IntegerField('Блок SRS не исправен мин сумма 5000', default=0, null=True, blank=True)
    srs_block_warning_amount_5000 = models.IntegerField('Блок SRS есть замечания сумма 5000', default=0, null=True, blank=True)
    srs_block_warning_kf_5000 = models.IntegerField('Блок SRS есть замечания коэффициент 5000', default=0, null=True, blank=True)
    srs_block_warning_amount_min_5000 = models.IntegerField('Блок SRS есть замечания мин сумма 5000', default=0, null=True, blank=True)
    
    srs_block_danger_amount_5001 = models.IntegerField('Блок SRS не исправен сумма 5001', default=0, null=True, blank=True)
    srs_block_danger_kf_5001 = models.IntegerField('Блок SRS не исправен коэффициент 5001', default=0, null=True, blank=True)
    srs_block_danger_amount_min_5001 = models.IntegerField('Блок SRS не исправен мин сумма 5001', default=0, null=True, blank=True)
    srs_block_warning_amount_5001 = models.IntegerField('Блок SRS есть замечания сумма 5001', default=0, null=True, blank=True)
    srs_block_warning_kf_5001 = models.IntegerField('Блок SRS есть замечания коэффициент 5001', default=0, null=True, blank=True)
    srs_block_warning_amount_min_5001 = models.IntegerField('Блок SRS есть замечания мин сумма 5001', default=0, null=True, blank=True)

    to_1_5000    = models.IntegerField('ТО 1 5000',      default=0, null=False, blank=True)
    to_2_5000    = models.IntegerField('ТО 2 5000',      default=0, null=False, blank=True)
    to_3_5000    = models.IntegerField('ТО 3 5000',      default=0, null=False, blank=True)
    
    to_1_5001    = models.IntegerField('ТО 1 5001',      default=0, null=False, blank=True)
    to_2_5001    = models.IntegerField('ТО 2 5001',      default=0, null=False, blank=True)
    to_3_5001    = models.IntegerField('ТО 3 5001',      default=0, null=False, blank=True)

    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'regEstimationsSettings'
        verbose_name = "Настройки интерактивной оценки"
        verbose_name_plural = "Настройки интерактивной оценки"


class RegInfoRefreshEstimationCarsExpress(models.Model):
    date            = models.DateTimeField('Дата начала', default=datetime.now, blank=False)
    date_end        = models.DateTimeField('Дата окончания', default=datetime.now, blank=False)
    count_all       = models.IntegerField('Всего авто', default=0, null=True, blank=True)
    count_success   = models.IntegerField('Всего авто успешно', default=0, null=True, blank=True)
    count_error     = models.IntegerField('Всего авто с ошибками', default=0, null=True, blank=True)
    
    def __str__(self):
        return "{} / {}".format(self.date, self.date_end)

    class Meta:
        db_table = 'regInfoRefreshEstimationCarsExpress'
        verbose_name = "Обновление экспресс оценки автомобиля на складе"
        verbose_name_plural = "Обновление экспресс оценок автомобилей на складе"


class RegInfoRefreshCatalog(models.Model):
    date        = models.DateTimeField('Дата обновления', default=datetime.now, blank=False)
    site        = models.CharField("Сайт", null=True, blank=True, max_length=512)
    
    def __str__(self):
        return "{} / {}".format(self.date, self.site)

    class Meta:
        db_table = 'regInfoRefreshCatalog'
        verbose_name = "Обновление каталога"
        verbose_name_plural = "Обновления каталогов"


class RegBoardsPage(models.Model):
    unit        = models.ForeignKey(RefUnit, null=True, on_delete=models.SET_NULL, verbose_name="Подразделение ДЦ")
    title       = models.CharField("Наименование", max_length=300)
    activated   = models.BooleanField("Активна", default = False, null=True, blank=True)
    html        = RichTextUploadingField(null=True, blank=True)
    time        = models.IntegerField("Время отображения", default=60, null=True, blank=True)
    
    def __str__(self):
        return "{} / {}".format(self.unit, self.title)

    class Meta:
        db_table = 'regBoardsPage'
        verbose_name = "Страница монитора сервиса"
        verbose_name_plural = "Страницы монитора сервиса"


class SettingsRegPrices(models.Model):
    name                    = models.CharField("Наименование", null=True, blank=True, max_length=512)
    manufacturer            = models.ForeignKey(RefManufacturer, null=True, on_delete=models.SET_NULL, verbose_name="Производитель")
    manufacturer_str        = models.CharField("Производитель строкой", null=True, blank=True, max_length=1512)
    user                    = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=u'Автор', on_delete=models.CASCADE, null=True)
    start_row               = models.IntegerField('Начальная строка', default=0, null=True, blank=True)
    number_manufacturer     = models.IntegerField('Столбец производитель', default=0, null=True, blank=True)
    number_name             = models.IntegerField('Столбец наименование', default=0, null=True, blank=True)
    number_article          = models.IntegerField('Столбец артикул', default=0, null=True, blank=True)
    number_category         = models.IntegerField('Столбец категория', default=0, null=True, blank=True)
    number_group            = models.IntegerField('Столбец группа', default=0, null=True, blank=True)
    number_price_min        = models.IntegerField('Столбец дилерская цена', default=0, null=True, blank=True)
    number_price            = models.IntegerField('Столбец цена продажи', default=0, null=True, blank=True)
    email_push              = models.CharField("Адреса электронной почты для оповещения", null=True, blank=True, max_length=2048)

    def __str__(self):
        return "{} / {} ".format(self.name, self.manufacturer)

    class Meta:
        db_table = 'settingsRegPrices'
        verbose_name = "Настройки загрузки прайс листов"
        verbose_name_plural = "Настройки загрузки прайс листов"


class TaskRegPrices(models.Model):
    
    date                = models.DateTimeField('Дата обновления', default=datetime.now, blank=False)
    manufacturer        = models.ForeignKey(RefManufacturer, null=True, on_delete=models.SET_NULL, verbose_name="Производитель")
    user                = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=u'Автор', on_delete=models.CASCADE, null=True)
    positions_all               = models.IntegerField('Позиций всего', default=0, null=True, blank=True)
    positions_success           = models.IntegerField('Позиций обработано', default=0, null=True, blank=True)
    status                      = models.CharField("Статус", null=True, blank=True, max_length=512)
    path_file_price             = models.CharField("Путь к файлу", null=True, blank=True, max_length=512)
    file_name                   = models.CharField("Имя файла", null=True, blank=True, max_length=512)
    settings                    = models.ForeignKey(SettingsRegPrices, null=True, on_delete=models.SET_NULL, verbose_name="Настройка")
    progress                    = models.IntegerField('Прогресс', default=0, null=True, blank=True)

    def count_success(self):
        return RegPrices.objects.filter(task = self).count()

    def __str__(self):
        return "{} / {}".format(self.date, self.manufacturer)

    class Meta:
        db_table = 'taskRegPrices'
        verbose_name = "Задание по загрузке прайс листа"
        verbose_name_plural = "Задания по загрузке прайс листа"


class RegPrices(models.Model):
    task                = models.ForeignKey(TaskRegPrices, null=True, on_delete=models.SET_NULL, verbose_name="Задание")
    date                = models.DateTimeField('Дата обновления', default=datetime.now, blank=False)
    manufacturer        = models.ForeignKey(RefManufacturer, null=True, on_delete=models.SET_NULL, verbose_name="Производитель")
    article             = models.CharField("Артикул", null=True, blank=True, max_length=512)
    article_search      = models.CharField("Артикул поиск", null=True, blank=True, max_length=512)
    name                = models.CharField("Наименование", null=True, blank=True, max_length=512)
    category            = models.ForeignKey(RefCategoryProduct, null=True, on_delete=models.SET_NULL, verbose_name="Категория")
    group               = models.ForeignKey(RefGroupProduct, null=True, on_delete=models.SET_NULL, verbose_name="Группа")
    price_min           = models.FloatField('Цена дилера / Мин цена продажи', default=0.00, null=True, blank=True)
    price               = models.FloatField('Цена', default=0.00, null=True, blank=True)
    
    def __str__(self):
        return "{} / {} / {}".format(self.date, self.manufacturer, self.article)

    
    class Meta:
        indexes = [
			models.Index(fields=['article_search', 'manufacturer'])
		]
        db_table = 'regPrices'
        verbose_name = "Товары прайс листа"
        verbose_name_plural = "Товары прайс листа"


class RegViewsCarsOrganization(models.Model):
    cars        = models.ForeignKey(RefCarsOrganization, null=True, on_delete=models.SET_NULL, verbose_name="Автомобиль")
    store       = models.ForeignKey(RefStore, null=True, on_delete=models.SET_NULL, verbose_name="Стоянка")
    type        = models.ForeignKey(RefEventCarsOrganization, null=True, on_delete=models.SET_NULL, verbose_name="Тип события")
    model       = models.CharField("Модель", null=True, blank=True, max_length=300)
    model_pk    = models.CharField("ИД записи", null=True, blank=True, max_length=300)
    date        = models.DateTimeField('Дата', default=datetime.now, blank=False)
    quantity    = models.IntegerField('Остаток на момент запроса', default=0, null=True, blank=True)
    reserve     = models.IntegerField('Резерв на момент запроса', default=0, null=True, blank=True)

    def __str__(self):
        return "{} / {} / {}".format(self.cars, self.store, self.type)

    class Meta:
        db_table = 'regViewsCarsOrganization'
        verbose_name = "Статистика карточки автомобиля"
        verbose_name_plural = "Статистика карточки автомобиля"


class RegDashboardError(models.Model):
    name            = models.CharField("Наименование", max_length=512, default='', blank=True)
    uin             = models.CharField("Технический код", max_length=512, default='', blank=True)
    file            = models.FileField(storage=save_directory,  upload_to="dashboard_error/", verbose_name="Файл", blank=True, null=True)
    description     = models.CharField("Описание", max_length=512, default='', blank=True)
    critical        = models.BooleanField("Критичная", default=False, blank=True)
    
    def get_absolute_url(self):
        try:
            return self.file.url.replace('/media/', '/media_dop/')
        except:
            return ""
    
    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        db_table = 'regDashboardError'
        verbose_name = "Ошибка приборной панели"
        verbose_name_plural = "Ошибки приборной панели"


#Страница дистанционной интерактивной оценки
class RegInteractivOcenkaRemote(ChangeloggableMixin, models.Model):
    start_estimation    = models.DateTimeField('Дата начала', blank=True, null=True)
    end_estimation      = models.DateTimeField('Дата окончания', blank=True, null=True)
    text_json           = models.TextField("Текст", blank=True, null=True)
    
    type_reception      = models.ForeignKey(RefTypeReceptionCarsOrganization, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Тип приема автомобиля')
    organization        = models.ForeignKey(RefOrganization, on_delete=models.SET_NULL, null=True, verbose_name="Организация")
    filial              = models.ForeignKey(RefFilial, on_delete=models.SET_NULL, null=True, verbose_name="Филиал")
    unit                = models.ForeignKey(RefUnit, on_delete=models.SET_NULL, null=True, verbose_name="Подразделение")
    store               = models.ForeignKey(RefStore, null=True, on_delete=models.SET_NULL, verbose_name='Склад / стоянка')
    
    count_owners        = models.IntegerField('Количество владельцев', default=0, null=True, blank=True)
    run                 = models.IntegerField('Пробег', default=0, null=True, blank=True)
    
    cleaning_int            = models.IntegerField('Требуеться химчистка',                   default=10, null=True, blank=True)       #'// 0 - не требуется 1 - требуется 2 - "" 3 - нет действия'
    damage_kpp_int          = models.IntegerField('Повреждения рычага кпп',                 default=10, null=True, blank=True)       #'// 0 - нет 1 - да 2 - "" 3 - нет действия'
    damage_wheel_int        = models.IntegerField('Повреждения / затертый руль',            default=10, null=True, blank=True)       #'// 0 - нет 1 - да 2 - "" 3 - нет действия'
    damage_pedal_int        = models.IntegerField('Повреждения / затертые педали',          default=10, null=True, blank=True)       #'// 0 - нет 1 - да 2 - "" 3 - нет действия'
    damage_door_int         = models.IntegerField('Повреждения / затертые карты дверей',    default=10, null=True, blank=True)       #'// 0 - нет 1 - да 2 - "" 3 - нет действия'
    damage_seat_int         = models.IntegerField('Повреждения / затертые сиденья',         default=10, null=True, blank=True)       #'// 0 - нет 1 - да 2 - "" 3 - нет действия'
    
    price_reception         = models.IntegerField('Цена приема',         default=0, null=True, blank=True)       #'// 0 - нет 1 - да 2 - "" 3 - нет действия'
    price_sale              = models.IntegerField('Цена продажи',         default=0, null=True, blank=True)       #'// 0 - нет 1 - да 2 - "" 3 - нет действия'
    
    price_eco               = models.IntegerField('Цена приема ецо',         default=0, null=True, blank=True)       #'// 0 - нет 1 - да 2 - "" 3 - нет действия'
    price_eco_user          = models.ForeignKey(User, related_name="price_eco_user", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Согласовал")

    car_sale_info           = models.CharField("Информация по приобритаемому автомобилю", max_length=2048, default='', null=True, blank=True) 
    car_sale_price          = models.CharField("Стоимость приобритаемого автомобиля", max_length=512, default='', null=True, blank=True) 
    comment                 = models.CharField("Комментарий", max_length=2048, default='', null=True, blank=True) 
    
    price_auto                      = models.IntegerField('Автоматическая', default=0, null=False, blank=True)
    price_zna                       = models.IntegerField('ЦНА Автоматическая', default=0, null=False, blank=True)
    price_auto_bcp                  = models.IntegerField('БЦП', default=0, null=False, blank=True)
    zachita_ot_ubitka               = models.FloatField('Защита от убытка', default=0.00, null=True, blank=True)
    finance_price                   = models.FloatField('Финансирование', default=0.00, null=True, blank=True)
    discount_torg                   = models.FloatField('Скидка торг', default=0.00, null=True, blank=True)
    amount_recovery                 = models.FloatField('Затраты на восстановительный ремонт', default=0.00, null=True, blank=True)

    k_i                     = models.FloatField("Коэфицент износа", default=0.0, blank=True)
    iznos                   = models.BooleanField("Повышенный износ", default = False, null=True, blank=True)
    
    hub_avg                 = models.IntegerField('Цена автохаб', default=0, null=False, blank=True)    

    def __str__(self):
        return "{} / {}".format(self.start_estimation, self.end_estimation)

    class Meta:
        db_table = 'regInteractivOcenkaRemote'
        verbose_name = "Данные интерактивной оценки страница удаленной оценки"
        verbose_name_plural = "Данные интерактивной оценки страница удаленной оценки"
post_save.connect(journal_save_handler, sender=RegInteractivOcenkaRemote)
post_delete.connect(journal_delete_handler, sender=RegInteractivOcenkaRemote)


#Страница документы интерактивной оценки
class RegInteractivOcenkaDocument(ChangeloggableMixin, models.Model):
    start_estimation    = models.DateTimeField('Дата начала', blank=True, null=True)
    end_estimation      = models.DateTimeField('Дата окончания', blank=True, null=True)
    text_json           = models.TextField("Текст", blank=True, null=True)
    
    type_reception      = models.ForeignKey(RefTypeReceptionCarsOrganization, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Тип приема автомобиля')
    organization        = models.ForeignKey(RefOrganization, on_delete=models.SET_NULL, null=True, verbose_name="Организация")
    filial              = models.ForeignKey(RefFilial, on_delete=models.SET_NULL, null=True, verbose_name="Филиал")
    unit                = models.ForeignKey(RefUnit, on_delete=models.SET_NULL, null=True, verbose_name="Подразделение")
    store               = models.ForeignKey(RefStore, null=True, on_delete=models.SET_NULL, verbose_name='Склад / стоянка')
    customer_family     = models.CharField('Фамилия', max_length=250, default='', null=True, blank=True)  
    customer_name       = models.CharField('Имя', max_length=250, default='', null=True, blank=True)  
    customer_patronymic = models.CharField('Отчество', max_length=250, default='', null=True, blank=True)
    customer_phone      = models.CharField('Телефон', max_length=250, default='', null=True, blank=True)
    customer_region     = models.CharField('Область', max_length=250, default='', null=True, blank=True) 
    count_key           = models.IntegerField('Количество ключей', default=0, null=True, blank=True)
    count_owners        = models.IntegerField('Количество владельцев', default=0, null=True, blank=True)
    plate_number        = models.CharField('Гос номер', max_length=20, default='', null=True, blank=True) 
    engine_number       = models.CharField('Номер двигателя', max_length=50, default='', null=True, blank=True) 
    pts_color           = models.CharField('Цвет по птс', max_length=250, default='', null=True, blank=True) 
    pts_number          = models.CharField('ПТС Номер', max_length=250, default='', null=True, blank=True) 
    pts_date            = models.DateTimeField('ПТС Дата ', blank=True, null=True) 
    pts_original        = models.BooleanField("ПТС оригинал", default = False, null=True, blank=True)
    pts_mark_model      = models.CharField('Марка модель по птс', max_length=250, default='', null=True, blank=True) 
    sts_number          = models.CharField('CТС Номер', max_length=250, default='', null=True, blank=True) 
    sts_date            = models.DateTimeField('CТС Дата', blank=True, null=True) 
    car_credit          = models.BooleanField("Автомобиль в залоге / кредите", default = False, null=True, blank=True)
    sale_auto_ru        = models.BooleanField("Автомобиль продается на авто ру", default = False, null=True, blank=True)
    sale_avito_ru       = models.BooleanField("Автомобиль продается на авито ру", default = False, null=True, blank=True)
    sale_drom_ru        = models.BooleanField("Автомобиль продается на дром ру", default = False, null=True, blank=True)
    new_car             = models.CharField("Модель нового а/м", max_length=250, default='', null=True, blank=True)
    new_staff_name      = models.CharField("Менеджер", max_length=250, default='', null=True, blank=True)
    
    def __str__(self):
        return "{} / {}".format(self.start_estimation, self.end_estimation)

    class Meta:
        db_table = 'regInteractivOcenkaDocument'
        verbose_name = "Данные интерактивной оценки страница документы"
        verbose_name_plural = "данные интерактивных оценок страница документы"
post_save.connect(journal_save_handler, sender=RegInteractivOcenkaDocument)
post_delete.connect(journal_delete_handler, sender=RegInteractivOcenkaDocument)

#Страница салон интерактивной оценки
class RegInteractivOcenkaSalon(ChangeloggableMixin, models.Model):
    start_estimation    = models.DateTimeField('Дата начала', blank=True, null=True)
    end_estimation      = models.DateTimeField('Дата окончания', blank=True, null=True)
    text_json           = models.TextField("Текст", blank=True, null=True)
    
    run                     = models.IntegerField('Пробег', default=0, null=True, blank=True)
    run_confirmed           = models.BooleanField('Пробег подтвержден', default = False, null=True, blank=True)                     # не будем использовать с 02042025
    
    hand_brake              = models.IntegerField('работоспособность ручного тормоза',      default=10, null=True, blank=True)       #'// 0 - не работает 1 - работает 2 - не проверен 3 - нет действия'
    conductor               = models.IntegerField('работоспособность кондиционера',         default=10, null=True, blank=True)       #'// 0 - не работает 1 - работает 2 - не проверен 3 - нет действия'
    wiper                   = models.IntegerField('работоспособность стеклоочистителя',     default=10, null=True, blank=True)       #'// 0 - не работает 1 - работает 2 - не проверен 3 - нет действия'
    signal                  = models.IntegerField('работоспособность сигнала',              default=10, null=True, blank=True)       #'// 0 - не работает 1 - работает 2 - не проверен 3 - нет действия'
    power_windows           = models.IntegerField('работоспособность стеклоподьемников',    default=10, null=True, blank=True)       #'// 0 - не работает 1 - работает 2 - не проверен 3 - нет действия'
    seat_belt               = models.IntegerField('работоспособность ремней безопастности', default=10, null=True, blank=True)       #'// 0 - не работает 1 - работает 2 - не проверен 3 - нет действия'

    cleaning                = models.BooleanField('Требуеться химчистка', default = False, null=True, blank=True)                   # не будем использовать с 02042025
    damage_kpp              = models.BooleanField('Повреждения рычага кпп', default = False, null=True, blank=True)                 # не будем использовать с 02042025
    damage_wheel            = models.BooleanField('Повреждения / затертый руль', default = False, null=True, blank=True)            # не будем использовать с 02042025
    damage_pedal            = models.BooleanField('Повреждения / затертые педали', default = False, null=True, blank=True)          # не будем использовать с 02042025
    damage_door             = models.BooleanField('Повреждения / затертые карты дверей', default = False, null=True, blank=True)    # не будем использовать с 02042025
    damage_seat             = models.BooleanField('Повреждения / затертые сиденья', default = False, null=True, blank=True)         # не будем использовать с 02042025
    
    dashboard_error         = models.ManyToManyField(RegDashboardError, verbose_name='Ошибки приборной панели', blank=True)

    run_respond             = models.IntegerField('Пробег соответствует состоянию', default=10, null=True, blank=True)               #'// 0 - нет 1 - да 2 - "" 3 - нет действия'
    
    run_confirmed_comment   = models.CharField('Пробег подтвержден комментарий', max_length=250, default='', null=True, blank=True)
    
    cleaning_int            = models.IntegerField('Требуеться химчистка',                   default=10, null=True, blank=True)       #'// 0 - не требуется 1 - требуется 2 - "" 3 - нет действия'
    damage_kpp_int          = models.IntegerField('Повреждения рычага кпп',                 default=10, null=True, blank=True)       #'// 0 - нет 1 - да 2 - "" 3 - нет действия'
    damage_wheel_int        = models.IntegerField('Повреждения / затертый руль',            default=10, null=True, blank=True)       #'// 0 - нет 1 - да 2 - "" 3 - нет действия'
    damage_pedal_int        = models.IntegerField('Повреждения / затертые педали',          default=10, null=True, blank=True)       #'// 0 - нет 1 - да 2 - "" 3 - нет действия'
    damage_door_int         = models.IntegerField('Повреждения / затертые карты дверей',    default=10, null=True, blank=True)       #'// 0 - нет 1 - да 2 - "" 3 - нет действия'
    damage_seat_int         = models.IntegerField('Повреждения / затертые сиденья',         default=10, null=True, blank=True)       #'// 0 - нет 1 - да 2 - "" 3 - нет действия'
    
    type_salon_int         = models.IntegerField('Тип салона',         default=10, null=True, blank=True)       #'// 0 - нет 1 - ткань 2 - кожа 3 - кожа'


    def __str__(self):
        return "{} / {}".format(self.start_estimation, self.end_estimation)

    class Meta:
        db_table = 'regInteractivOcenkaSalon'
        verbose_name = "Данные интерактивной оценки страница салон"
        verbose_name_plural = "данные интерактивных оценок страница салон"
post_save.connect(journal_save_handler, sender=RegInteractivOcenkaSalon)
post_delete.connect(journal_delete_handler, sender=RegInteractivOcenkaSalon)

#Страница документы интерактивной оценки
class RegInteractivOcenkaVnesh(ChangeloggableMixin, models.Model):
    start_estimation    = models.DateTimeField('Дата начала', blank=True, null=True)
    end_estimation      = models.DateTimeField('Дата окончания', blank=True, null=True)
    text_json           = models.TextField("Текст", blank=True, null=True)
    
    windshield_error    = models.BooleanField("Лобовое стекло с повреждениями", default = False, null=True, blank=True)
    light_error         = models.BooleanField("Световые приборы есть проблемы", default = False, null=True, blank=True)
    oil_error           = models.BooleanField("Следы подтекания масла", default = False, null=True, blank=True)
    water_error         = models.BooleanField("Следы подтекания охлаждающей жидкости", default = False, null=True, blank=True)
    color               = models.CharField("Цвет", max_length=150, default='', null=True, blank=True)    
    check_vin           = models.BooleanField("Проверка VIN", default = False, null=True, blank=True)
    check_engine        = models.BooleanField("Проверка двигателя и коробки на месте", default = False, null=True, blank=True)
    comment_vnesh       = models.CharField("Комментарий внешнего осмотра", max_length=1500, default='', null=True, blank=True)    
    
    check_vin_int       = models.IntegerField('Проверка VIN', default=10, null=True, blank=True) #'// 0 - есть проблемы 1 - все ок 2 - "" 3 - нет действия'
    check_engine_int    = models.IntegerField('Проверка ДВС и КПП на месте', default=10, null=True, blank=True) #'// 0 - есть проблемы 1 - все ок 2 - "" 3 - нет действия'
    
    windshield_error_int    = models.IntegerField('Лобовое стекло с повреждениями', default=10, null=True, blank=True) #'// 0 - есть проблемы 1 - все ок 2 - "" 3 - нет действия'
    light_error_int         = models.IntegerField('Световые приборы есть проблемы', default=10, null=True, blank=True) #'// 0 - есть проблемы 1 - все ок 2 - "" 3 - нет действия'

    oil_error_int           = models.IntegerField('Следы подтекания масла', default=10, null=True, blank=True) #'// 0 - есть проблемы 1 - все ок 2 - "" 3 - нет действия'
    water_error_int         = models.IntegerField('Следы подтекания охлаждающей жидкости', default=10, null=True, blank=True) #'// 0 - есть проблемы 1 - все ок 2 - "" 3 - нет действия'

    windshield_heat_int    = models.IntegerField('Лобовое стекло с обогревом', default=10, null=True, blank=True) #'// 1 - есть обогрев
    
    def __str__(self):
        return "{} / {}".format(self.start_estimation, self.end_estimation)

    class Meta:
        db_table = 'regInteractivOcenkaVnesh'
        verbose_name = "Данные интерактивной оценки страница внешний осмотр"
        verbose_name_plural = "Данные интерактивной оценки страницы внешннего осмотра"
post_save.connect(journal_save_handler, sender=RegInteractivOcenkaVnesh)
post_delete.connect(journal_delete_handler, sender=RegInteractivOcenkaVnesh)

#Страница комплектность интерактивной оценки
class RegInteractivOcenkaComplectnost(ChangeloggableMixin, models.Model):
    start_estimation    = models.DateTimeField('Дата начала', blank=True, null=True)
    end_estimation      = models.DateTimeField('Дата окончания', blank=True, null=True)
    text_json           = models.TextField("Текст", blank=True, null=True)
    

    prikur_int          = models.IntegerField('Прикуриватель',   default=10, null=True, blank=True)                      #'// 0 - нет 1 - да 2 - "" 3 - нет действия'
    ognet_int           = models.IntegerField('Огнетушитель',   default=10, null=True, blank=True)                       #'// 0 - нет 1 - да 2 - "" 3 - нет действия'
    kovrik_int          = models.IntegerField('Коврики',   default=10, null=True, blank=True)                            #'// 0 - нет 1 - да 2 - "" 3 - нет действия'
    tros_int            = models.IntegerField('Буксировочный трос',   default=10, null=True, blank=True)                 #'// 0 - нет 1 - да 2 - "" 3 - нет действия'
    domkrat_int         = models.IntegerField('Домкрат',   default=10, null=True, blank=True)                            #'// 0 - нет 1 - да 2 - "" 3 - нет действия'
    znak_av_int         = models.IntegerField('Знак аварийной остановки',   default=10, null=True, blank=True)           #'// 0 - нет 1 - да 2 - "" 3 - нет действия'
    ball_key_int        = models.IntegerField('Баллонный ключ',   default=10, null=True, blank=True)                     #'// 0 - нет 1 - да 2 - "" 3 - нет действия'
    zapas_int           = models.IntegerField('Запасное колесо / докатка',   default=10, null=True, blank=True)          #'// 0 - нет 1 - да 2 - "" 3 - нет действия'
    aptechka_int        = models.IntegerField('Аптечка',   default=10, null=True, blank=True)                            #'// 0 - нет 1 - да 2 - "" 3 - нет действия'

    prikur              = models.BooleanField("Прикуриватель", default = False, null=True, blank=True)
    ognet               = models.BooleanField("Огнетушитель", default = False, null=True, blank=True)
    kovrik              = models.BooleanField("Коврики", default = False, null=True, blank=True)
    tros                = models.BooleanField("Буксировочный трос", default = False, null=True, blank=True)
    domkrat             = models.BooleanField("Домкрат", default = False, null=True, blank=True)
    znak_av             = models.BooleanField("Знак аварийной остановки", default = False, null=True, blank=True)
    ball_key            = models.BooleanField("Баллонный ключ", default = False, null=True, blank=True)
    zapas               = models.BooleanField("Запасное колесо / докатка", default = False, null=True, blank=True)
    aptechka            = models.BooleanField("Аптечка", default = False, null=True, blank=True)

    def __str__(self):
        return "{} / {}".format(self.start_estimation, self.end_estimation)

    class Meta:
        db_table = 'regInteractivOcenkaComplectnost'
        verbose_name = "Данные интерактивной оценки страница комплектность"
        verbose_name_plural = "Данные интерактивной оценки страницы комплектности"
post_save.connect(journal_save_handler, sender=RegInteractivOcenkaComplectnost)
post_delete.connect(journal_delete_handler, sender=RegInteractivOcenkaComplectnost)

#Страница тест-драйв интерактивной оценки
class RegInteractivOcenkaKolesa(ChangeloggableMixin, models.Model):
    start_estimation    = models.DateTimeField('Дата начала', blank=True, null=True)
    end_estimation      = models.DateTimeField('Дата окончания', blank=True, null=True)
    text_json           = models.TextField("Текст", blank=True, null=True)
    mark_tyre           = models.ForeignKey(RefMarkTyres, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Марка резины")
    model_tyre          = models.CharField('Модель резины', max_length=250, default='', null=True, blank=True)
    width_tyre          = models.ForeignKey(RefWidthTyres, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Ширина резины")
    disk_type           = models.ForeignKey(RefTypeDisk, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Тип диска")
    profil_tyre         = models.ForeignKey(RefProfileTyres, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Профиль резины")
    radius              = models.ForeignKey(RefRadius, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Радиус колес")
    sezon               = models.ForeignKey(RefSezonTyres, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Сезон колес")
    model_disk          = models.CharField('Модель дисков', max_length=250, default='', null=True, blank=True)
    et_disk             = models.ForeignKey(RefEtDisk, on_delete=models.PROTECT, null=True, blank=True, verbose_name="ET дисков")
    dia_disk            = models.ForeignKey(RefDiaDisk, on_delete=models.PROTECT, null=True, blank=True, verbose_name="DIA дисков")
    psd_disk            = models.ForeignKey(RefPsdDisk, on_delete=models.PROTECT, null=True, blank=True, verbose_name="PSD дисков")
    kolesa2             = models.BooleanField("Второй копмплект", default = False, null=True, blank=True)
    mark_tyre2          = models.ForeignKey(RefMarkTyres, related_name="mark_tyre2", on_delete=models.PROTECT, null=True, blank=True, verbose_name="Марка резины 2")
    model_tyre2         = models.CharField('Модель резины 2', max_length=250, default='', null=True, blank=True)
    width_tyre2         = models.ForeignKey(RefWidthTyres, related_name="width_tyre2", on_delete=models.PROTECT, null=True, blank=True, verbose_name="Ширина резины 2")
    profil_tyre2        = models.ForeignKey(RefProfileTyres, related_name="profil_tyre2", on_delete=models.PROTECT, null=True, blank=True, verbose_name="Профиль резины 2")
    radius2             = models.ForeignKey(RefRadius, related_name="radius2", on_delete=models.PROTECT, null=True, blank=True, verbose_name="Радиус колес 2")
    sezon2              = models.ForeignKey(RefSezonTyres, related_name="sezon2", on_delete=models.PROTECT, null=True, blank=True, verbose_name="Сезон колес 2")
    disk_type2          = models.ForeignKey(RefTypeDisk, related_name="disk_type2", on_delete=models.PROTECT, null=True, blank=True, verbose_name="Тип диска 2")
    model_disk2         = models.CharField('Модель дисков 2', max_length=250, default='', null=True, blank=True)
    et_disk2            = models.ForeignKey(RefEtDisk, related_name="et_disk2", on_delete=models.PROTECT, null=True, blank=True, verbose_name="ET дисков 2")
    dia_disk2           = models.ForeignKey(RefDiaDisk, related_name="dia_disk2", on_delete=models.PROTECT, null=True, blank=True, verbose_name="DIA дисков 2")
    psd_disk2           = models.ForeignKey(RefPsdDisk, related_name="psd_disk2", on_delete=models.PROTECT, null=True, blank=True, verbose_name="PSD дисков 2")
    count_disk2         = models.IntegerField('Количество дисков 2', default=0, null=True, blank=True)
    count_tyre2         = models.IntegerField('Количество резины 2', default=0, null=True, blank=True)
    
    

    def __str__(self):
        return "{} / {}".format(self.start_estimation, self.end_estimation)

    class Meta:
        db_table = 'regInteractivOcenkaKolesa'
        verbose_name = "Данные интерактивной оценки страница колеса"
        verbose_name_plural = "Данные интерактивной оценки страницы колеса"
post_save.connect(journal_save_handler, sender=RegInteractivOcenkaKolesa)
post_delete.connect(journal_delete_handler, sender=RegInteractivOcenkaKolesa)

#Страница тест-драйв интерактивной оценки
class RegInteractivOcenkaTestDrive(ChangeloggableMixin, models.Model):
    start_estimation    = models.DateTimeField('Дата начала', blank=True, null=True)
    end_estimation      = models.DateTimeField('Дата окончания', blank=True, null=True)
    text_json           = models.TextField("Текст", blank=True, null=True)
    
    engine                  = models.IntegerField('Двигатель', default=10, null=True, blank=True)                   #'// 0 - не работает 1 работает 2 есть замечания'
    system_og               = models.IntegerField('Система выпуска ОГ', default=10, null=True, blank=True)          #'// 0 - не работает 1 работает 2 есть замечания'
    gear                    = models.IntegerField('КПП', default=10, null=True, blank=True)                         #'// 0 - не работает 1 работает 2 есть замечания'
    suspension              = models.IntegerField('Подвеска', default=10, null=True, blank=True)                    #'// 0 - не работает 1 работает 2 есть замечания'
    airbag                  = models.IntegerField('Подушка безопастности', default=10, null=True, blank=True)       #'// 0 - не работает 1 работает 2 есть замечания'
    wheel                   = models.IntegerField('Рулевое управление', default=10, null=True, blank=True)          #'// 0 - не работает 1 работает 2 есть замечания'
    brake                   = models.IntegerField('Тормозная система', default=10, null=True, blank=True)           #'// 0 - не работает 1 работает 2 есть замечания 4 не предусмотрен'
    subframe                = models.IntegerField('Подрамник', default=10, null=True, blank=True)                  #'// 0 - не работает 1 работает 2 есть замечания'
    conditioner             = models.IntegerField('Кондиционер', default=10, null=True, blank=True)                 #'// 0 - не работает 1 работает 2 есть замечания'
    turbo                   = models.IntegerField('Турбина', default=10, null=True, blank=True)                     #'// 0 - не работает 1 работает 2 есть замечания'
    drive                   = models.IntegerField('Полный привод', default=10, null=True, blank=True)                     #'// 0 - не работает 1 работает 2 есть замечания'
    to                      = models.IntegerField('ТО', default=10, null=True, blank=True)                     #'// 0 - не работает 1 работает 2 есть замечания'
    
    # Стапель
    stapele_type            = models.IntegerField('Тип стапеля', null=True, blank=True, 
                                                   help_text='1 - легкий, 2 - средний, 3 - тяжелый')
    stapele_hours           = models.IntegerField('Часы стапеля', null=True, blank=True)
    stapele_cost            = models.IntegerField('Стоимость стапеля', null=True, blank=True)

    comment_engine          = models.CharField('Комментарий двигатель', max_length=512, default='', null=True, blank=True)  
    comment_system_og       = models.CharField('Комментарий система выпуска ОГ', max_length=512, default='', null=True, blank=True)  
    comment_gear            = models.CharField('Комментарий коробка передач', max_length=512, default='', null=True, blank=True)  
    comment_suspension      = models.CharField('Комментарий подвеска', max_length=512, default='', null=True, blank=True)  
    comment_airbag          = models.CharField('Комментарий подушки безопастности', max_length=512, default='', null=True, blank=True)
    
    # Конкретные проблемы безопасности (битовые флаги или JSON)
    airbag_issues = models.CharField('Проблемы безопасности (JSON)', max_length=2048, default='', null=True, blank=True)
    # Альтернативно можно использовать отдельные BooleanField для каждого пункта:
    airbag_driver_issue = models.BooleanField('Проблема: Подушка водителя', default=False, null=True, blank=True)
    airbag_passenger_issue = models.BooleanField('Проблема: Подушка пассажира + перешив торпеды', default=False, null=True, blank=True)
    airbag_side_issue = models.BooleanField('Проблема: Боковые подушки', default=False, null=True, blank=True)
    airbag_knee_issue = models.BooleanField('Проблема: Подушка коленная', default=False, null=True, blank=True)
    seat_belt_restore_issue = models.BooleanField('Проблема: Восстановление ремней безопасности', default=False, null=True, blank=True)
    srs_block_issue = models.BooleanField('Проблема: Блок SRS', default=False, null=True, blank=True)  
    comment_wheel           = models.CharField('Комментарий рулевого управления', max_length=512, default='', null=True, blank=True)  
    comment_brake            = models.CharField('Комментарий тормозной системы', max_length=512, default='', null=True, blank=True)
    comment_subframe        = models.CharField('Комментарий подрамника', max_length=512, default='', null=True, blank=True)  
    hood_trunk_shock_absorber = models.IntegerField('Амортизатор капота/багажника', default=10, null=True, blank=True)  #'// 1 - исправны 0 - не исправны 4 - не предусмотрены'
    comment_hood_trunk_shock_absorber = models.CharField('Комментарий амортизатор капота/багажника', max_length=512, default='', null=True, blank=True)
    comment_conditioner     = models.CharField('Комментарий системы кондиционирования', max_length=512, default='', null=True, blank=True)  
    comment_turbo           = models.CharField('Комментарий турбокомпрессора', max_length=512, default='', null=True, blank=True)  
    comment_drive           = models.CharField('Комментарий полный привод', max_length=512, default='', null=True, blank=True)  
    
    pp_dinamyc              = models.IntegerField('Разгонная динамика, посторонние шумы, вибрации при движении', default=10, null=True, blank=True)  #'// 0 - ремонт 1 норма 2 диагностика'
    pp_kpp                  = models.IntegerField('Плавность включения передач (автомобили с МКПП и АКПП, проверка CVT во всех режимах), все передачи', default=10, null=True, blank=True)  #'// 0 - ремонт 1 норма 2 диагностика'
    pp_uvod                 = models.IntegerField('Увод от прямолинейного движения', default=10, null=True, blank=True)  #'// 0 - ремонт 1 норма 2 диагностика'
    pp_pribor               = models.IntegerField('Работа измерительных приборов и указателей (исправность, корректность показаний)', default=10, null=True, blank=True)  #'// 0 - ремонт 1 норма 2 диагностика'

    no_test                 = models.BooleanField("Тест драйв не производился", default = False, null=True, blank=True)
    comment                 = models.CharField('Комментарий тест - драйва', max_length=250, default='', null=True, blank=True)  

    def __str__(self):
        return "{} / {}".format(self.start_estimation, self.end_estimation)

    class Meta:
        db_table = 'regInteractivOcenkaTestDrive'
        verbose_name = "Данные интерактивной оценки страница тест - драйв"
        verbose_name_plural = "Данные интерактивной оценки страницы тест - драйва"
post_save.connect(journal_save_handler, sender=RegInteractivOcenkaTestDrive)


# Справочник диагностики для интерактивной оценки
class DiagnosticReferenceCategory(models.Model):
    """
    Категории справочника диагностики (Двигатель, КПП, Тормозная система и т.д.)
    """
    code = models.CharField('Код категории', max_length=50, unique=True, db_index=True)  # engine, gear, brake и т.д.
    name = models.CharField('Наименование', max_length=200)
    description = models.TextField('Описание', blank=True, null=True)
    order = models.IntegerField('Порядок сортировки', default=0, db_index=True)
    is_active = models.BooleanField('Активна', default=True, db_index=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'diagnostic_reference_category'
        verbose_name = "Категория справочника диагностики"
        verbose_name_plural = "Категории справочника диагностики"
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['code', 'is_active']),
        ]


class DiagnosticReferenceItem(models.Model):
    """
    Элементы справочника диагностики (конкретные признаки неисправностей)
    """
    category = models.ForeignKey(
        DiagnosticReferenceCategory, 
        on_delete=models.CASCADE, 
        related_name='items',
        verbose_name='Категория',
        db_index=True
    )
    title = models.CharField('Заголовок', max_length=300)  # "Запотевание (тонкая масляная плёнка)"
    description = models.TextField('Описание', blank=True, null=True)
    
    # Где наблюдается
    observation_zones = models.TextField('Где наблюдается', blank=True, null=True)
    
    # Возможные причины
    possible_causes = models.TextField('Возможные причины', blank=True, null=True)
    
    # Последствия при игнорировании
    consequences = models.TextField('Последствия при игнорировании', blank=True, null=True)
    
    # Дополнительная информация
    additional_info = models.TextField('Дополнительная информация', blank=True, null=True)
    
    # Метаданные
    order = models.IntegerField('Порядок сортировки', default=0, db_index=True)
    is_active = models.BooleanField('Активна', default=True, db_index=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    def __str__(self):
        return f"{self.category.name}: {self.title}"
    
    class Meta:
        db_table = 'diagnostic_reference_item'
        verbose_name = "Элемент справочника диагностики"
        verbose_name_plural = "Элементы справочника диагностики"
        ordering = ['category', 'order', 'title']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['is_active', 'order']),
        ]


class DiagnosticReferenceSelection(models.Model):
    """
    Связь выбранных элементов справочника с оценкой (альтернативный вариант)
    """
    test_drive = models.ForeignKey(
        RegInteractivOcenkaTestDrive,
        on_delete=models.CASCADE,
        related_name='reference_selections',
        verbose_name='Тест-драйв',
        db_index=True
    )
    category_code = models.CharField('Код категории', max_length=50, db_index=True)  # engine, gear, brake
    reference_item = models.ForeignKey(
        DiagnosticReferenceItem,
        on_delete=models.CASCADE,
        related_name='selections',
        verbose_name='Элемент справочника'
    )
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    
    def __str__(self):
        return f"{self.test_drive} - {self.category_code} - {self.reference_item.title}"
    
    class Meta:
        db_table = 'diagnostic_reference_selection'
        verbose_name = "Выбор элемента справочника"
        verbose_name_plural = "Выборы элементов справочника"
        unique_together = ['test_drive', 'category_code', 'reference_item']
        indexes = [
            models.Index(fields=['test_drive', 'category_code']),
        ]
post_delete.connect(journal_delete_handler, sender=RegInteractivOcenkaTestDrive)

#Страница проверки интерактивной оценки
class RegInteractivOcenkaProverki(ChangeloggableMixin, models.Model):
    start_estimation    = models.DateTimeField('Дата начала', blank=True, null=True)
    end_estimation      = models.DateTimeField('Дата окончания', blank=True, null=True)
    text_json           = models.TextField("Текст", blank=True, null=True)
    
    car_credit          = models.BooleanField("Автомобиль в залоге / кредите", default = False, null=True, blank=True)
    count_dtp           = models.IntegerField('Количество дтп', default=0, null=True, blank=True)
    
    
    def __str__(self):
        return "{} / {}".format(self.start_estimation, self.end_estimation)

    class Meta:
        db_table = 'regInteractivOcenkaProverki'
        verbose_name = "Данные интерактивной оценки страница проверка"
        verbose_name_plural = "Данные интерактивной оценки страницы проверки"
post_save.connect(journal_save_handler, sender=RegInteractivOcenkaProverki)
post_delete.connect(journal_delete_handler, sender=RegInteractivOcenkaProverki)

#Страница проверки интерактивной оценки
class RegInteractivOcenkaSoglasovanie(ChangeloggableMixin, models.Model):
    start_estimation    = models.DateTimeField('Дата начала', blank=True, null=True)
    end_estimation      = models.DateTimeField('Дата окончания', blank=True, null=True)
    text_json           = models.TextField("Текст", blank=True, null=True)
    
    price_reception         = models.IntegerField('Цена приема', default=0, null=True, blank=True)
    price_sale              = models.IntegerField('Цена продажи', default=0, null=True, blank=True)
    price_recovery          = models.IntegerField('Затраты на ремонт / подготовку', default=0, null=True, blank=True)
    
    price_before_kd         = models.IntegerField('Согласованая цена до диагностики', default=0, null=True, blank=True)
    price_before_kd_comment = models.CharField("Комментарий до кд", max_length=5120, default='', null=True, blank=True) 
    
    price_after_kd          = models.IntegerField('Согласованая цена после диагностики', default=0, null=True, blank=True)
    price_after_kd_comment  = models.CharField("Комментарий после кд", max_length=5120, default='', null=True, blank=True)
    price_bcp               = models.IntegerField('БЦП', default=0, null=True, blank=True)
    price_auto_bcp          = models.IntegerField('БЦП', default=0, null=True, blank=True)

    comment                 = models.CharField("Комментарий", max_length=2048, default='', null=True, blank=True) 
    comment_diagnostica     = models.CharField("Комментарий после диагностки", max_length=2048, default='', null=True, blank=True) 
    no_diagnostica          = models.BooleanField("Без диагностики", default = False, null=True, blank=True)
    no_diagnostica_comment  = models.CharField("Комментарий отсутствия диагностики диагностки", max_length=2048, default='', null=True, blank=True) 
    
    comment_no_endoscop  = models.CharField("Комментарий отсутствия фото эндоскопа", max_length=2048, default='', null=True, blank=True) 
    comment_no_scaner   = models.CharField("Комментарий отсутствия фото сканера", max_length=2048, default='', null=True, blank=True) 
    
    
    amount_podgotovka       = models.FloatField('Затраты на подготовку', default=0.00, null=True, blank=True)
    amount_ss               = models.FloatField('Затраты на слесарный ремонт', default=0.00, null=True, blank=True)
    amount_mcu              = models.FloatField('Затраты на кузовной ремонт', default=0.00, null=True, blank=True)
    
    car_sale_info           = models.CharField("Информация по приобритаемому автомобилю", max_length=2048, default='', null=True, blank=True) 
    car_sale_price          = models.CharField("Стоимость приобритаемого автомобиля", max_length=512, default='', null=True, blank=True) 

    price_auto_1                    = models.IntegerField('Автоматическая 1', default=0, null=False, blank=True)
    price_auto_2                    = models.IntegerField('Автоматическая 2', default=0, null=False, blank=True)
    price_auto_3                    = models.IntegerField('Автоматическая 3', default=0, null=False, blank=True)

    price_zna_1                    = models.IntegerField('ЦНА Автоматическая 1', default=0, null=False, blank=True)
    price_zna_2                    = models.IntegerField('ЦНА Автоматическая 2', default=0, null=False, blank=True)
    price_zna_3                    = models.IntegerField('ЦНА Автоматическая 3', default=0, null=False, blank=True)

    price_auto_bcp_1                    = models.IntegerField('БЦП 1', default=0, null=False, blank=True)
    price_auto_bcp_2                    = models.IntegerField('БЦП 2', default=0, null=False, blank=True)
    price_auto_bcp_3                    = models.IntegerField('БЦП 3', default=0, null=False, blank=True)

    price_type                      = models.CharField("Тип ценообразования", max_length=100, default='', null=False, blank=True) 
    price_correction                = models.FloatField("Ручная коррекция", default=0.00, null=False, blank=True) 
    price_correction_comment        = models.CharField("Ручная коррекция комментарий", max_length=5120, default='', null=True, blank=True) 
    price_correction_comment_author = models.ForeignKey(User, related_name="price_correction_comment_author", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Коррекция автор")

    price_correction_before                = models.FloatField("Ручная коррекция 1", default=0.00, null=False, blank=True) 
    price_correction_before_comment        = models.CharField("Ручная коррекция комментарий 1", max_length=5120, default='', null=True, blank=True) 
    price_correction_before_comment_author = models.ForeignKey(User, related_name="price_correction_comment_author_1", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Коррекция автор 1")

    price_bcp_test_price            = models.IntegerField('БЦП тест - прайс', default=0, null=True, blank=True)
    
    zna_to_amount                   = models.IntegerField('ЦНА - затраты', default=0, null=True, blank=True)
    
    price_auto_auction              = models.BooleanField("Автоматически аукцион", default = False, null=True, blank=True)
    
    zachita_ot_ubitka               = models.FloatField('Защита от убытка', default=0.00, null=True, blank=True)
    finance_price                   = models.FloatField('Финансирование', default=0.00, null=True, blank=True)
    discount_torg                   = models.FloatField('Скидка торг', default=0.00, null=True, blank=True)
    amount_recovery                 = models.FloatField('Затраты на восстановительный ремонт', default=0.00, null=True, blank=True)

    settings                        = models.ForeignKey(RegEstimationsSettings, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Настройка ценообразования" ) 

    def __str__(self):
        return "{} / {}".format(self.start_estimation, self.end_estimation)

    def save(self, *args, **kwargs):
        
        try:
            self.amount_recovery = self.amount_podgotovka + self.amount_ss + self.amount_mcu 
        except:
            s=1

        try:
            s = 1
            #add_swap(self.reginteractivocenka)
        except:
            s =1 
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'regInteractivOcenkaSoglasovanie'
        verbose_name = "Данные интерактивной оценки страница согласование"
        verbose_name_plural = "Данные интерактивной оценки страницы согласования"
post_save.connect(journal_save_handler, sender=RegInteractivOcenkaSoglasovanie)
post_delete.connect(journal_delete_handler, sender=RegInteractivOcenkaSoglasovanie)

class RegInteractivOcenka(ChangeloggableMixin, models.Model):
    rlk                 = models.OneToOneField(DocRLK, null=True, on_delete=models.SET_NULL, verbose_name="Рабочий лист")
    type_estimation     = models.IntegerField('Тип оценки', default=0, null=True, blank=True)
    vin                 = models.CharField("ВИН", max_length=21, default='') 
    year                = models.IntegerField("Год выпуска",  default=0, null=True, blank=True) 
    
    type_drive              = models.CharField("Тип привода", max_length=21, default='', null=True, blank=True) 
    type_body               = models.ForeignKey(RefTypeBody, null=True, on_delete=models.SET_NULL, verbose_name='Вид кузова')
    type_engine             = models.ForeignKey(RefTypeEngine, null=True, on_delete=models.SET_NULL, verbose_name='Вид двигателя')
    type_gear               = models.ForeignKey(RefTypeKpp, null=True, on_delete=models.SET_NULL, verbose_name='Вид коробки передач')
    
    number_body         = models.CharField("Номер кузова", max_length=21, default='', null=True, blank=True) 
    staff               = models.ForeignKey(RefStaff, related_name="staff_estimation", on_delete=models.SET_NULL, null=True, verbose_name="Оценщик")
    staff_eco_1         = models.ForeignKey(User, related_name="staff_eco_1", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Аналитик до кд")
    staff_eco_2         = models.ForeignKey(User, related_name="staff_eco_2", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Аналитик после кд")
    start_estimation    = models.DateTimeField('Дата начала оценки', blank=True, null=True)
    end_estimation      = models.DateTimeField('Дата окончания оценки', blank=True, null=True)
    modification        = models.ForeignKey(AutoruModification, blank=True, null=True, on_delete=models.SET_NULL, verbose_name='Модификация')
    mark_name           = models.CharField("Марка  наименование ручное", max_length=512, default='', null=True, blank=True) 
    model_name          = models.CharField("Модель  наименование ручное", max_length=512, default='', null=True, blank=True) 
    modification_name   = models.CharField("Модификация наименование ручное", max_length=512, default='', null=True, blank=True) 
    complectation       = models.ForeignKey(AutoruComplectation, blank=True, null=True, on_delete=models.SET_NULL, verbose_name='Комплектация')
    modification_avito  = models.ForeignKey(RefAvito, blank=True,null=True, on_delete=models.SET_NULL, verbose_name='Модификация авито')
    complectation_avito = models.ForeignKey(RefAvitoComplectation, blank=True, null=True, on_delete=models.SET_NULL, verbose_name='Комплектация авито')
    page_remote         = models.OneToOneField(RegInteractivOcenkaRemote, blank=True, null=True, on_delete=models.SET_NULL, verbose_name="Удаленный осмотр")
    page_documents      = models.OneToOneField(RegInteractivOcenkaDocument, blank=True, null=True, on_delete=models.SET_NULL, verbose_name="Документы")
    page_salon          = models.OneToOneField(RegInteractivOcenkaSalon, blank=True, null=True, on_delete=models.SET_NULL, verbose_name="Салон")
    page_vnesh          = models.OneToOneField(RegInteractivOcenkaVnesh, blank=True, null=True, on_delete=models.SET_NULL, verbose_name="Внешний осмотр")
    page_complectnost   = models.OneToOneField(RegInteractivOcenkaComplectnost, blank=True, null=True, on_delete=models.SET_NULL, verbose_name="Комплектность")
    page_kolesa         = models.OneToOneField(RegInteractivOcenkaKolesa, blank=True, null=True, on_delete=models.SET_NULL, verbose_name="Колеса")
    page_test_drive     = models.OneToOneField(RegInteractivOcenkaTestDrive, blank=True, null=True, on_delete=models.SET_NULL, verbose_name="Тест - драйв")
    page_proverki       = models.OneToOneField(RegInteractivOcenkaProverki, blank=True, null=True, on_delete=models.SET_NULL, verbose_name="Проверки")
    page_soglasovanie   = models.OneToOneField(RegInteractivOcenkaSoglasovanie, blank=True, null=True, on_delete=models.SET_NULL, verbose_name="Согласование")
    status              = models.ForeignKey(RefStatusEstimation, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Статус")
    access_user         = models.ManyToManyField(User, verbose_name='Пользователь', blank=True)
    returned            = models.BooleanField("Возвращена", default = False, null=True, blank=True)
    prev_img            = models.CharField("Превью", max_length=2500, default='', null=True, blank=True) 
    qr                  = models.ImageField(storage=save_directory,  upload_to="estimation/qr/", verbose_name="QR", blank=True, null=True)
    custom_zna          = models.IntegerField('ЦНА ручная', default=0, null=True, blank=True)
    custom_zna_comment  = models.CharField("ЦНА ручная комментарий", max_length=2500, default='', null=True, blank=True)
    custom_zna_author   = models.ForeignKey(User, related_name="custom_zna_author", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="ЦНА ручная автор")

    avtoteka_web        = models.CharField("Ссылка на автотеку веб", max_length=2500, default='', null=True, blank=True) 
    avtoteka_pdf        = models.CharField("Ссылка на автотеку пдф", max_length=2500, default='', null=True, blank=True) 
    avtoteka_data       = models.TextField("Автотека", blank=True, null=True)
    avtoteka_preview    = models.CharField("Автотека задание превью", max_length=250, default='', null=True, blank=True)
    avtoteka_task       = models.TextField("Автотека задание", blank=True, null=True)

    avtoteka_car_autodex            = models.FloatField('Автотека сумма расчетов ремонтов', default=0.00, null=True, blank=True)

    avito_price_avg_market_price    = models.FloatField('Оценка на основе объявлений', default=0.00, null=True, blank=True)
    avito_price_avg_condition       = models.FloatField('Оценка с учетом состояния автомобилей на основе реальных сделок', default=0.00, null=True, blank=True)
    avito_price_market_min          = models.FloatField('Минимальная граница "рыночной" оценки данного автомобиля по закрытым сделкам', default=0.00, null=True, blank=True)
    avito_price_market_max          = models.FloatField('Максимальная граница "рыночной" оценки данного автомобиля по закрытым сделкам', default=0.00, null=True, blank=True)
    avito_price_min                 = models.FloatField('Минимальная цена похожих авто на основе объявлений', default=0.00, null=True, blank=True)
    avito_price_max                 = models.FloatField('Максимальная цена похожих авто на основе объявлений', default=0.00, null=True, blank=True)

    kors_price_avg_market_price    = models.FloatField('Корс Оценка на основе объявлений', default=0.00, null=True, blank=True)
    kors_price_avg_condition       = models.FloatField('Корс Оценка с учетом состояния', default=0.00, null=True, blank=True)
    kors_price_market_min          = models.FloatField('Корс Минимальная граница "рыночной" оценки данного автомобиля по закрытым сделкам', default=0.00, null=True, blank=True)
    kors_price_market_max          = models.FloatField('Корс Максимальная граница "рыночной" оценки данного автомобиля по закрытым сделкам', default=0.00, null=True, blank=True)
    kors_price_min                 = models.FloatField('Корс Минимальная цена похожих авто на основе объявлений', default=0.00, null=True, blank=True)
    kors_price_max                 = models.FloatField('Корс Максимальная цена похожих авто на основе объявлений', default=0.00, null=True, blank=True)
    kors_count_store               = models.FloatField('Корс автомобилей на складе', default=0.00, null=True, blank=True)
    kors_count_sale                = models.FloatField('Корс продано автомобилей', default=0.00, null=True, blank=True)
    kors_start_store               = models.DateTimeField('Дата анализа склада', blank=True, null=True)
    kors_start_sale                = models.DateTimeField('Дата анализа продаж', blank=True, null=True)

    kors_cost_price_min         = models.FloatField('Корс Минимальная себестоимость', default=0.00, null=True, blank=True)
    kors_cost_price_max         = models.FloatField('Корс Максимальная себестоимость', default=0.00, null=True, blank=True)
    kors_price_max              = models.FloatField('Корс Максимальная цена похожих авто на основе объявлений', default=0.00, null=True, blank=True)
    kors_days_in_stok_avg    = models.FloatField('Корс среднее дней на складе', default=0.00, null=True, blank=True)
    kors_cost_price_avg      = models.FloatField('Корс среднее себестоимость', default=0.00, null=True, blank=True)
    kors_outlay_avg          = models.FloatField('Корс среднее затраты', default=0.00, null=True, blank=True)
    kors_price_avg           = models.FloatField('Корс среднее цена', default=0.00, null=True, blank=True)
    kors_run_avg             = models.FloatField('Корс среднее пробег', default=0.00, null=True, blank=True)
    kors_year_avg            = models.FloatField('Корс среднее год выпуска', default=0.00, null=True, blank=True)
    kors_ownewrs_avg         = models.FloatField('Корс среднее владельцев', default=0.00, null=True, blank=True)
    kors_cum_avg             = models.FloatField('Корс среднее кумулятив', default=0.00, null=True, blank=True)


    kors_sale_cost_price_min        = models.FloatField('Корс продажи Минимальная себестоимость', default=0.00, null=True, blank=True)
    kors_sale_cost_price_max        = models.FloatField('Корс продажи Максимальная себестоимость', default=0.00, null=True, blank=True)
    kors_sale_days_in_stok_avg    = models.FloatField('Корс продажи среднее дней на складе', default=0.00, null=True, blank=True)
    kors_sale_cost_price_avg      = models.FloatField('Корс продажи среднее себестоимость', default=0.00, null=True, blank=True)
    kors_sale_outlay_avg          = models.FloatField('Корс продажи среднее затраты', default=0.00, null=True, blank=True)
    kors_sale_price_avg           = models.FloatField('Корс продажи среднее цена', default=0.00, null=True, blank=True)
    kors_sale_run_avg             = models.FloatField('Корс продажи среднее пробег', default=0.00, null=True, blank=True)
    kors_sale_year_avg            = models.FloatField('Корс продажи среднее год выпуска', default=0.00, null=True, blank=True)
    kors_sale_ownewrs_avg         = models.FloatField('Корс продажи среднее владельцев', default=0.00, null=True, blank=True)
    kors_sale_cum_avg             = models.FloatField('Корс продажи среднее кумулятив', default=0.00, null=True, blank=True)      

    kors_price                      = models.FloatField('Оценка корс', default=0.00, null=True, blank=True)      
    kors_price_correction           = models.FloatField('Оценка корс скоректированная', default=0.00, null=True, blank=True)                            
    
    hub_price                      = models.FloatField('Оценка автохаб', default=0.00, null=True, blank=True)      
    hub_price_correction           = models.FloatField('Оценка автохаб скоректированная', default=0.00, null=True, blank=True)                            

    hub_start                       = models.DateTimeField('Дата анализа автохаб', blank=True, null=True)

    hub_sale_avg                    = models.FloatField('avgPriceWithCorrection', default=0.00, null=True, blank=True)
    hub_sale_days_in_stok_avg       = models.FloatField('hub_sale_days_in_stok_avg', default=0.00, null=True, blank=True)
    hub_sale_run_avg                = models.FloatField('hub_sale_run_avg', default=0.00, null=True, blank=True)
    hub_sale_year_avg               = models.FloatField('hub_sale_year_avg', default=0.00, null=True, blank=True)
    hub_sale_price_max              = models.FloatField('hub_sale_price_max', default=0.00, null=True, blank=True)
    hub_sale_price_min              = models.FloatField('hub_sale_price_min', default=0.00, null=True, blank=True)
    hub_sale_pricePosition          = models.FloatField('hub_sale_pricePosition', default=0.00, null=True, blank=True)
    hub_sale_vRating                = models.FloatField('hub_sale_vRating', default=0.00, null=True, blank=True)
    hub_sale_total                  = models.FloatField('hub_sale_salesTotal', default=0.00, null=True, blank=True)      

    hub_avg                    = models.FloatField('avgPriceWithCorrection', default=0.00, null=True, blank=True)
    hub_days_in_stok_avg       = models.FloatField('hub_days_in_stok_avg', default=0.00, null=True, blank=True)
    hub_run_avg                = models.FloatField('hub_run_avg', default=0.00, null=True, blank=True)
    hub_year_avg               = models.FloatField('hub_year_avg', default=0.00, null=True, blank=True)
    hub_price_max              = models.FloatField('hub_price_max', default=0.00, null=True, blank=True)
    hub_price_min              = models.FloatField('hub_price_min', default=0.00, null=True, blank=True)
    hub_pricePosition          = models.FloatField('hub_pricePosition', default=0.00, null=True, blank=True)
    hub_vRating                 = models.FloatField('hub_vRating', default=0.00, null=True, blank=True)
    hub_total                   = models.FloatField('hub_salesTotal', default=0.00, null=True, blank=True)      

    hub_data        = models.TextField("Автохаб дата", blank=True, null=True)
    hub_data_2      = models.TextField("Автохаб дата 2", blank=True, null=True)

    count_dtp       = models.IntegerField('Количество ДТП', default=0, null=True, blank=True)
    dtp_red         = models.BooleanField('Есть сильные повреждения при дтп', default = False, null=True, blank=True)
    taxi            = models.BooleanField("Использование в такси", default = False, null=True, blank=True)
    carsharing      = models.BooleanField("Использование в каршеринге", default = False, null=True, blank=True)
    k_i             = models.FloatField("Коэфицент износа", default=0.0, blank=True)
    iznos           = models.BooleanField("Повышенный износ", default = False, null=True, blank=True)

    slug                    = models.SlugField(max_length=512, null=True, blank=True)
    
    v                       = models.IntegerField('Версия интерактивной оценки', default=3, null=True, blank=True)
    
    auction_auto_no_user    = models.BooleanField("Аукцион не подтвержден", default = False, null=True, blank=True)
    auction_auto_comment    = models.CharField("Аукцион не подтвержден комментарий", max_length=2500, default='', null=True, blank=True)
    
    auction                 = models.BooleanField("Аукцион", default = False, null=True, blank=True)
    auction_comment         = models.CharField("Аукцион комментарий", max_length=2500, default='', null=True, blank=True)
    auction_data            = models.CharField("Аукцион тип (причина)", max_length = 512, default='', null=True, blank=True)
    
    type_price              = models.IntegerField('Тип формирования цены', default=0, null=True, blank=True)
    
    users_eco               = models.IntegerField('Сотрудников ецо в чате', default=0, null=True, blank=True)
    users_no_eco            = models.IntegerField('Сотрудников не ецо в чате', default=0, null=True, blank=True)
    users_dop               = models.IntegerField('Сотрудников доп согласования', default=0, null=True, blank=True)

    date_s_remote   = models.DateTimeField('Дата согласования дистанционной', blank=True, null=True)
    date_s_do_diag  = models.DateTimeField('Дата согласования до диагностики', blank=True, null=True)
    date_diagnostic = models.DateTimeField('Дата диагностики', blank=True, null=True)
    date_s_diag     = models.DateTimeField('Дата согласования после диагностики', blank=True, null=True)
    
    status_ocenka                       = models.IntegerField('Секунд оценка', default=0, null=True, blank=True)
    status_soglasovanie_do_diag         = models.IntegerField('Секунд до согласования диагностики', default=0, null=True, blank=True)
    status_diagnostika                  = models.IntegerField('Секунд диагностика', default=0, null=True, blank=True)
    status_soglasovanie_posle_kd        = models.IntegerField('Секунд после диагностики', default=0, null=True, blank=True)
    
    count_task                          = models.IntegerField('Задач', default=0, null=True, blank=True)
    seconds_task                        = models.IntegerField('Время на задачи', default=0, null=True, blank=True)
    count_answer                        = models.IntegerField('Ответов ЕЦО', default=0, null=True, blank=True)
    seconds_answer                      = models.IntegerField('Среднее время ответа', default=0, null=True, blank=True)
    seconds_estimation                  = models.IntegerField('Секунд оценки', default=0, null=True, blank=True)
    #text_json   = models.DateTimeField('Дата окончания оценки', blank=True, null=True)
    #upload      = models.FileField(storage=save_directory,  upload_to='tessttt/%Y/%m/%d/', verbose_name="Видео", blank=True, null=True)
    
    def duration_answer(self):
        try:
            return str(timedelta(seconds=(int(self.seconds_answer / self.count_answer))))
        except:
            return str(timedelta(seconds=0))
    
    def duration(self):
        if self.seconds_estimation != None:
            return str(timedelta(seconds=self.seconds_estimation))
        return str(timedelta(seconds=0))
    
    def link_car(self):
        car_organizations = RefCarsOrganization.objects.filter(lo__rlk = self.rlk) 
        if len(car_organizations) == 1:
            car_organization    = car_organizations[0]
            slug = '/cars/' + car_organization.slug + '/'
            return slug
        return ''
    
    def check_infos(self):
        list_danger = list()
        if self.fotos_vnesh_vod_count() == 0:
            info = {
                'name'      : 'Водительская сторона',
                'result'    : False
            }
            list_danger.append(info)
        if self.fotos_vnesh_pass_count() == 0:
            info = {
                'name'      : 'Пассажирская сторона',
                'result'    : False
            }
            list_danger.append(info)
        if self.fotos_vnesh_pered_count() == 0:
            info = {
                'name'      : 'Передняя сторона',
                'result'    : False
            }
            list_danger.append(info)
        if self.fotos_vnesh_zad_count() == 0:
            info = {
                'name'      : 'Задняя сторона',
                'result'    : False
            }
            list_danger.append(info)
        if self.fotos_vnesh_up_count() == 0:
            info = {
                'name'      : 'Верхняя сторона',
                'result'    : False
            }
            list_danger.append(info)
        if self.avtoteka_data == None or self.avtoteka_data == '':
            info = {
                'name'      : 'Нет данных Автотека',
                'result'    : False
            }
            list_danger.append(info)
        if self.page_test_drive == None or self.page_test_drive.end_estimation == None:
            info = {
                'name'      : 'Нет данных тест-драйва',
                'result'    : False
            }
            list_danger.append(info)
        return list_danger

    def list_data_active(self):
        
        return RegInteractivOcenkaKorsStore.objects.filter(estimation = self).filter(active = True).order_by('-doc__dataTime') 

    def list_data_no_active(self):
        
        return RegInteractivOcenkaKorsStore.objects.filter(estimation = self).filter(active = False).order_by('-doc__dataTime')

    def list_data_sale_active(self):
        
        list_data_sale  = RegInteractivOcenkaKorsStoreSale.objects.filter(estimation = self).filter(active = True).order_by('-doc__dataTime') 
        
        return list_data_sale
    
    def list_data_sale_no_active(self):
        
        list_data_sale  = RegInteractivOcenkaKorsStoreSale.objects.filter(estimation = self).filter(active = False).order_by('-doc__dataTime') 
        
        return list_data_sale

    def calculate_kors_sale_stock(self):
        
        list_store_info = RefCarsOrganization.objects.filter(modification_autoru__idSiteGeneration = self.modification.idSiteGeneration).filter(quantity = 1).filter(year__lte=self.year + 1).filter(year__gte=self.year - 1).order_by('days_in_stok')        
        return 0
    
    def tasks(self):
        return RegInteractivOcenkaTask.objects.filter(estimation = self)

    def fotos_remote_alls(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'images_remote').order_by('file_number')
        fotos = fotos.order_by('type_file', 'file_number')
        return fotos     

    def fotos_prev(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vnesh_car_all').order_by('file_number')
        fotos = fotos.order_by('type_file', 'file_number')
        if fotos.count() > 0:
            return fotos[0]
        return None
    
    def fotos_skol(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(name__icontains = 'скол').count()
        return fotos
    
    def fotos_vmatin(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(name__icontains = 'вмятина').count()
        return fotos
    
    def fotos_carap(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(name__icontains = 'царапи').count()
        return fotos

    def fotos_rzav(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(name__icontains = 'ржавчи').count()
        return fotos

    def fotos_sts_count(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'sts').count()
        return fotos

    def fotos_sts(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'sts').order_by('file_number')
        fotos = fotos.order_by('type_file', 'file_number')
        return fotos
    
    def fotos_pts(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'pts').order_by('file_number')
        fotos = fotos.order_by('type_file', 'file_number')
        return fotos

    def fotos_gibdd_count(self):
        return RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'gibdd').count()
        fotos = fotos.order_by('type_file', 'file_number')
        return fotos
    
    def fotos_reestr_count(self):
        return RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'reestr').count()
        fotos = fotos.order_by('type_file', 'file_number')
        return fotos

    def fotos_market_count(self):
        return RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'market').count()
        fotos = fotos.order_by('type_file', 'file_number')
        return fotos
    
    def fotos_gibdd(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'gibdd').order_by('file_number')
        fotos = fotos.order_by('type_file', 'file_number')
        return fotos
    
    def fotos_windshield_error(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'windshield_error').order_by('file_number')
        fotos = fotos.order_by('type_file', 'file_number')
        return fotos
    
    def fotos_light_error(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'light_error').order_by('file_number')
        fotos = fotos.order_by('type_file', 'file_number')
        return fotos
    
    def fotos_reestr(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'reestr').order_by('file_number')
        fotos = fotos.order_by('type_file', 'file_number')
        return fotos

    def fotos_market(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'market').order_by('file_number')
        fotos = fotos.order_by('type_file', 'file_number')
        return fotos
    
    def fotos_documents(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'sts').order_by('file_number') | RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'pts').order_by('file_number')
        fotos = fotos.order_by('type_file', 'file_number')
        return fotos
    
    def fotos_glav(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'sts').order_by('file_number') | RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'pts').order_by('file_number')
        fotos = fotos.order_by('type_file', 'file_number')
        return fotos

    def fotos_kolesa(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'kolesa').order_by('file_number') 
        fotos = fotos.order_by('type_file', 'file_number')
        return fotos
    
    def fotos_kolesa_count(self):
        return RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'kolesa').count()
        
    def fotos_kolesa2(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'kolesa2').order_by('file_number') 
        fotos = fotos.order_by('type_file', 'file_number')
        return fotos

    def fotos_run_count(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'run').count()
        return fotos
    
    def fotos_run(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'run').order_by('file_number') 
        fotos = fotos.order_by('type_file', 'file_number')
        return fotos

    def fotos_car_all(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vnesh_car_all').order_by('file_number') 
        fotos = fotos.order_by('type_file', 'file_number')
        return fotos

    def fotos_car_all_new(self):
        fotos_car               = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vnesh_car_all').order_by('file_number') 
        fotos_vin               = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vin').order_by('file_number') 
        fotos_pod_capot         = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'pod_capot').order_by('file_number') 
        fotos_windshield_error  = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'windshield_error').order_by('file_number') 
        fotos_salon_error       = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'light_error').order_by('file_number') 
        
        fotos = chain(fotos_car, fotos_vin, fotos_pod_capot, fotos_windshield_error, fotos_salon_error)
        return list(fotos)

    def fotos_car_a1(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vnesh_car_all').filter(file_number = 1).order_by('file_number') 
        fotos = fotos.order_by('type_file', 'file_number')
        if fotos.count() > 0:
            return fotos[0].get_absolute_url()
        else:
            return '/media_dop/static/estimation/a1.jpg'

    def fotos_car_a2(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vnesh_car_all').filter(file_number = 2).order_by('file_number') 
        fotos = fotos.order_by('type_file', 'file_number')
        if fotos.count() > 0:
            return fotos[0].get_absolute_url()
        else:
            return '/media_dop/static/estimation/a2.jpg'

    def fotos_car_a3(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vnesh_car_all').filter(file_number = 3).order_by('file_number') 
        fotos = fotos.order_by('type_file', 'file_number')
        if fotos.count() > 0:
            return fotos[0].get_absolute_url()
        else:
            return '/media_dop/static/estimation/a3.jpg'

    def fotos_car_a4(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vnesh_car_all').filter(file_number = 4).order_by('file_number') 
        fotos = fotos.order_by('type_file', 'file_number')
        if fotos.count() > 0:
            return fotos[0].get_absolute_url()
        else:
            return '/media_dop/static/estimation/a4.jpg'

    def fotos_car_a5(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vnesh_car_all').filter(file_number = 5).order_by('file_number') 
        fotos = fotos.order_by('type_file', 'file_number')
        if fotos.count() > 0:
            return fotos[0].get_absolute_url()
        else:
            return '/media_dop/static/estimation/a5.jpg'
        
    def fotos_car_a6(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vnesh_car_all').filter(file_number = 6).order_by('file_number') 
        fotos = fotos.order_by('type_file', 'file_number')
        if fotos.count() > 0:
            return fotos[0].get_absolute_url()
        else:
            return '/media_dop/static/estimation/a6.jpg'
        
    def fotos_car_a7(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vnesh_car_all').filter(file_number = 7).order_by('file_number') 
        fotos = fotos.order_by('type_file', 'file_number')
        if fotos.count() > 0:
            return fotos[0].get_absolute_url()
        else:
            return '/media_dop/static/estimation/a7.jpg'
        
    def fotos_car_a8(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vnesh_car_all').filter(file_number = 8).order_by('file_number') 
        fotos = fotos.order_by('type_file', 'file_number')
        if fotos.count() > 0:
            return fotos[0].get_absolute_url()
        else:
            return '/media_dop/static/estimation/a8.jpg'

    def fotos_salon_alls(self):
        fotos_salon = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'salon_all').order_by('file_number') 
        return list(fotos_salon)
    
    def fotos_salon_damage(self):
        fotos_salon_error = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'salon_error').order_by('file_number') 
        return list(fotos_salon_error)
    
    def fotos_salon(self):
        fotos_run   = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'run').order_by('file_number') 
        fotos_salon = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'salon_all').order_by('file_number') 
        fotos_salon_error = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'salon_error').order_by('file_number') 
        
        fotos = chain(fotos_run, fotos_salon, fotos_salon_error)
        return list(fotos)
    
    def dachboard_critical_error(self):
        return self.page_salon.dashboard_error.all().filter(critical = True).count()

    def dachboard_no_critical_error(self):
        return self.page_salon.dashboard_error.all().filter(critical = False).count()
    
    def fotos_salon_capture(self):
        fotos   = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'osmotr_salon')
        if fotos.count() > 0:
            return fotos[0].get_absolute_url()    
        return '/media_dop/salon_capture/salon.png'
    
    def fotos_vnesh_pered_count(self):
        return RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vnesh_car_osmotr_pered').count()
        if fotos.count() > 0:
            return fotos[0]    
        return '/media_dop/body_capture/sedan_new.png'
   
    def fotos_vnesh_pered(self):
        fotos   = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vnesh_car_osmotr_pered')
        if fotos.count() > 0:
            return fotos[0].get_absolute_url()    
        return '/media_dop/body_capture/sedan_new.png'
    
    def fotos_vnesh_vod_count(self):
        return RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vnesh_car_osmotr_vod').count()
        if fotos.count() > 0:
            return fotos[0]    
        return '/media_dop/body_capture/sedan_left_new.png'

    def fotos_vnesh_vod(self):
        fotos   = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vnesh_car_osmotr_vod')
        if fotos.count() > 0:
            return fotos[0].get_absolute_url() 
        return '/media_dop/body_capture/sedan_left_new.png'

    def fotos_vnesh_zad_count(self):
        return RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vnesh_car_osmotr_zad').count()
        if fotos.count() > 0:
            return fotos[0]    
        return '/media_dop/body_capture/sedan_back_new.png'
    
    def fotos_vnesh_zad(self):
        fotos   = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vnesh_car_osmotr_zad')
        if fotos.count() > 0:
            return fotos[0].get_absolute_url()    
        return '/media_dop/body_capture/sedan_back_new.png'

    def fotos_vnesh_up_count(self):
        return RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vnesh_car_osmotr_up').count()
        if fotos.count() > 0:
            return fotos[0]    
        return '/media_dop/body_capture/sedan_up.png'

    def fotos_vnesh_up(self):
        fotos   = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vnesh_car_osmotr_up')
        if fotos.count() > 0:
            return fotos[0].get_absolute_url()     
        return '/media_dop/body_capture/sedan_up.png'

    def fotos_vnesh_pass_count(self):
        return RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vnesh_car_osmotr_pass').count()
        if fotos.count() > 0:
            return fotos[0]    
        return '/media_dop/body_capture/sedan_right_new.png'    
    
    def fotos_vnesh_pass(self):
        fotos   = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vnesh_car_osmotr_pass')
        if fotos.count() > 0:
            return fotos[0].get_absolute_url()    
        return '/media_dop/body_capture/sedan_right_new.png'
    
    def fotos_array_images_pered(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'array_images_pered').order_by('file_number') 
        fotos = fotos.order_by('type_file', 'file_number')
        return fotos

    def fotos_array_images_vod(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'array_images_vod').order_by('file_number') 
        fotos = fotos.order_by('type_file', 'file_number')
        return fotos
    
    def fotos_array_images_zad(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'array_images_zad').order_by('file_number') 
        fotos = fotos.order_by('type_file', 'file_number')
        return fotos
    
    def fotos_array_images_up(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'array_images_up').order_by('file_number') 
        fotos = fotos.order_by('type_file', 'file_number')
        return fotos
    
    def fotos_array_images_pass(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'array_images_pass').order_by('file_number') 
        fotos = fotos.order_by('type_file', 'file_number')
        return fotos

    def fotos_vin_count(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vin').count()
        return fotos
  
    def fotos_vin(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vin').order_by('file_number') 
        fotos = fotos.order_by('type_file', 'file_number')
        return fotos

    def fotos_pod_capot_count(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'pod_capot').count() 
        return fotos
    
    def fotos_pod_capot(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'pod_capot').order_by('file_number') 
        fotos = fotos.order_by('type_file', 'file_number')
        return fotos

    def fotos_vnesh_count(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vnesh_car_all').count()
        return fotos

    def fotos_vnesh_all(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'pod_capot').order_by('file_number') | RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vnesh_windows_error').order_by('file_number') | RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vnesh_light_error').order_by('file_number') | RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'vin').order_by('file_number') 
        fotos = fotos.order_by('order', 'file_number')
        return fotos

    def get_files_diagnostic(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'diagnostic').order_by('file_number')
        fotos = fotos.order_by('order', 'file_number')
        return fotos
    
    def get_files_diagnostic_count(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'diagnostic').order_by('file_number')
        fotos = fotos.order_by('order', 'file_number')
        return fotos.count()

    def get_files_scaner_count(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'scaner').order_by('file_number')
        fotos = fotos.order_by('order', 'file_number')
        return fotos.count()
    
    def get_files_scaner(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'scaner').order_by('file_number')
        fotos = fotos.order_by('order', 'file_number')
        return fotos
    
    def get_files_endoscop_count(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'endoscop').order_by('file_number')
        fotos = fotos.order_by('order', 'file_number')
        return fotos.count()
    
    def get_files_endoscop(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(type_file = 'endoscop').order_by('file_number')
        fotos = fotos.order_by('order', 'file_number')
        return fotos
    
    def get_files_all_count(self):
        fotos       = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(blank = False).count()
        fotos_task  = RegRegInteractivOcenkaTaskFiles.objects.filter(estimation_task__estimation = self).count()

        return fotos + fotos_task
    
    def get_files_all(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self)
        fotos = fotos.filter(blank = False).order_by('date', 'order', 'type_file', 'file_number')

        fotos_task  = RegRegInteractivOcenkaTaskFiles.objects.filter(estimation_task__estimation = self)
        
        fotos = chain(fotos, fotos_task)

        return fotos

    def chat_message(self):
        from chats.models import ChatMessage
        return ChatMessage.objects.filter(chat__slug = 'rlk_' + str(self.rlk.id)).count()

    def chat_message_users(self):
        from chats.models import ChatMessage
        return ChatMessage.objects.filter(chat__slug = 'rlk_' + str(self.rlk.id)).values('user').distinct().count()
    
    def car_repaint(self):
        fotos = RegRegInteractivOcenkaFiles.objects.filter(estimation = self).filter(kraska__gte = 350).count()
        if fotos > 0:
            return True
        return False

    def check_run(self):
        check = True
        if self.avtoteka_data != None and len(self.avtoteka_data) > 100:
            data_autoteka = json.loads(self.avtoteka_data)['result']['report']['data']
            eventsOthersHistory = data_autoteka.get('eventsOthersHistory')
            run_sum     = 0
            run         = 0
            run_other   = 0
            
            for event in eventsOthersHistory:
                if event['source'] != 'Audatex':
                    if event['mileage'] > 0:
                        run = event['mileage']
                        if run_other > run:
                            if run_other - run > 1000:
                                run_ok = False
                                run_sum = run_sum + (run_other - run)                            
                        run_other = run
            if run_sum > 0:
                check = False
        return check
    

    def get_bcp(self):
        bcp = 0
        if self.page_soglasovanie != None:
            if self.page_soglasovanie.price_auto_bcp_1 > 0:
                bcp = self.page_soglasovanie.price_auto_bcp_1
            elif self.page_soglasovanie.price_auto_bcp_2 > 0:
                bcp = self.page_soglasovanie.price_auto_bcp_2
            elif self.page_soglasovanie.price_auto_bcp_3 > 0:
                bcp = self.page_soglasovanie.price_auto_bcp_3
         
        return bcp

    def get_zna(self):
        zna = 0
        if self.page_soglasovanie != None:
            if self.page_soglasovanie.price_zna_1 > 0:
                zna = self.page_soglasovanie.price_zna_1
            elif self.page_soglasovanie.price_zna_2 > 0:
                zna = self.page_soglasovanie.price_zna_2
            elif self.page_soglasovanie.price_zna_3 > 0:
                zna = self.page_soglasovanie.price_zna_3
         
        return zna

    def save(self, *args, **kwargs):
        
        self.status = RefStatusEstimation.objects.get(pk = 1)

        try:
            if self.page_salon != None:
                if self.page_salon.run > 0:
                    eyar_k = datetime.now().year - self.year
                    if eyar_k == 0:
                        eyar_k = 1
                    run = self.page_salon.run
                    self.k_i = round(run / (eyar_k * 35000), 2)
                    run_iznos = eyar_k * 35000
                    if run > run_iznos or run > 175000:
                        self.iznos = True
                    else:
                        self.iznos = False
                    # if run <= 175000 and self.k_i <= 1.2:
                    #     self.iznos = False
                    # elif run <= 175000 and self.k_i > 1.2:
                    #     self.iznos = True
                    # elif run > 175000 and self.k_i > 0:
                    #     self.iznos = True
            elif self.page_remote != None:
                if self.page_remote.run > 0:
                    eyar_k = datetime.now().year - self.year
                    if eyar_k == 0:
                        eyar_k = 1
                    run = self.page_remote.run
                    self.k_i = round(run / (eyar_k * 35000), 2)
                    run_iznos = eyar_k * 35000
                    if run > run_iznos or run > 175000:
                        self.iznos = True
                    else:
                        self.iznos = False
                    # if run <= 175000 and self.k_i <= 1.2:
                    #     self.iznos = False
                    # elif run <= 175000 and self.k_i > 1.2:
                    #     self.iznos = True
                    # elif run > 175000 and self.k_i > 0:
                    #     self.iznos = True
        except:
            s = 1

        try:
            
            self.returned = False
            
            if RegInteractivOcenkaTask.objects.filter(estimation = self).filter(staff_close = None).count() > 0:
                self.returned = True            

            self.prev_img = self.fotos_car_a1()

            if self.vin == None:
                self.vin = ''
            
            if self.number_body == None:
                self.number_body = ''

            if self.vin != '':
                self.vin = self.vin.upper()
                if not self.slug:
                    name_slug = str(self.rlk.pk) + '_' + str(self.vin[0:5]) + '_' + self.vin[15:18] + '_' + random_slug()
                    self.slug = slugify(name_slug.lower())

                if not self.qr:
                    self.qr = ContentFile(get_qrcode(self.slug), name=self.slug)

            if self.number_body != '':
                self.number_body = self.number_body.upper()

            if self.vin == '' and self.number_body == '':
                self.status = RefStatusEstimation.objects.get(pk = 1)
            elif self.returned:
                self.status = RefStatusEstimation.objects.get(pk = 7)
            elif self.page_remote != None and self.page_remote.end_estimation == None:
                self.status = RefStatusEstimation.objects.get(pk = 9) 
            elif self.end_estimation != None and self.page_soglasovanie != None:
                count_success = DocLO.objects.filter(rlk = self.rlk).filter(active = True).count()
                if count_success > 0:
                    self.status = RefStatusEstimation.objects.get(pk = 8)                    
                elif self.page_soglasovanie.price_before_kd == 0:
                    self.status = RefStatusEstimation.objects.get(pk = 3)
                elif self.page_soglasovanie.price_before_kd > 0 and not self.page_soglasovanie.no_diagnostica and self.page_soglasovanie.comment_diagnostica == '':
                    self.status = RefStatusEstimation.objects.get(pk = 5)
                elif self.page_soglasovanie.price_after_kd == 0 and (self.page_soglasovanie.no_diagnostica or self.page_soglasovanie.comment_diagnostica != ''):
                    self.status = RefStatusEstimation.objects.get(pk = 6)
                elif self.page_soglasovanie.price_after_kd > 0:
                    self.status = RefStatusEstimation.objects.get(pk = 4)   
            else:
                self.status = RefStatusEstimation.objects.get(pk = 2)
                
        except:
            self.status = RefStatusEstimation.objects.get(pk = 1)
        
        #add_swap(self)
        
        try:
            if self.status == RefStatusEstimation.objects.get(pk = 8):
                from website.views import refresh_estimation_balance_unit
                refresh_estimation_balance_unit(self.rlk.id)
        except:
            s = 1

        super().save(*args, **kwargs)

        # Обновляем витрину аналитиков
        try:
            if self.start_estimation != None:
                update_trade_in_funnel(self)
        except Exception:
            pass
        

    def __str__(self):
        return "{} / {}".format(self.rlk, self.type_estimation)

    class Meta:
        indexes = [
            models.Index(fields=['rlk', 'status', 'vin', 'avtoteka_web', 'avtoteka_preview', 'avtoteka_task', ])
        ]
        db_table = 'regInteractivOcenka'
        verbose_name = "Данные интерактивной оценки"
        verbose_name_plural = "данные интерактивных оценок"

post_save.connect(journal_save_handler, sender=RegInteractivOcenka)
post_delete.connect(journal_delete_handler, sender=RegInteractivOcenka)

def update_trade_in_funnel(estimation):
    try:
        from analytics.models import TradeInFunnel
    except Exception:
        return
    
    rlk_id = estimation.rlk.id

    mark_id     = 0
    mark_name   = ''
    model_id    = 0
    model_name  = 0
    modification_id     = 0
    modification_name   = ''
    vin                 = ''
    year                = 0
    run                 = 0
    type_reception_id   = 0
    type_reception_name = ''
    unit_id     = 0
    unit_name   = ''
    staff_id    = 0
    staff_name  = ''
    analyst_remote_id = 0
    analyst_remote_name = ''
    analyst_before_id       = 0
    analyst_before_name     = ''
    analyst_after_id        = 0
    analyst_after_name      = ''
    city_id = 0
    city_name = ''
    owners = 0
    price_reception_staff = 0
    price_sale_staff = 0
    cost_plan               = 0
    cost_plan_ss            = 0
    cost_plan_mcu           = 0
    cost_plan_preparation   = 0

    price_remote        = 0
    price_before        = 0
    price_after         = 0
    price_sale          = 0
    price_auto_bcp      = 0

    price_auto_remote   = 0
    price_auto_before   = 0
    price_auto_after    = 0
    price_auto_bcp      = 0
    zna                 = 0
    zna_custom          = 0

    comparison_remote   = 0
    comparison_before   = 0
    comparison_after    = 0
    comparison_remote_type   = 0
    comparison_before_type   = 0
    comparison_after_type    = 0
    diagostica          = False 
    diff_summ           = 0

    date_start_estimation = estimation.start_estimation

    remote = False if not estimation.page_remote else True
    if remote and estimation.page_remote != None:
        
        run = estimation.page_remote.run
        type_reception_id   = estimation.page_remote.type_reception.id
        type_reception_name = estimation.page_remote.type_reception.name
        unit_id   = estimation.page_remote.unit.id
        unit_name = estimation.page_remote.unit.name
        if estimation.page_remote.price_eco > 0:
            analyst_remote_id       = estimation.page_remote.price_eco_user.profiles.id
            analyst_remote_name     = estimation.page_remote.price_eco_user.profiles.eco_name
        city_id     = estimation.page_remote.unit.city.id
        city_name   = estimation.page_remote.unit.city.name
        owners      = estimation.page_remote.count_owners
        price_reception_staff   = estimation.page_remote.price_reception
        price_sale_staff        = estimation.page_remote.price_sale
        price_remote            = estimation.page_remote.price_eco
        price_auto_remote       = estimation.page_remote.price_auto
        zna             = estimation.page_remote.price_zna 
        price_auto_bcp  = estimation.page_remote.price_auto_bcp
        diff            = estimation.page_remote.discount_torg + estimation.page_remote.zachita_ot_ubitka
        diff_summ = estimation.page_remote.price_eco - estimation.page_remote.price_auto
        if diff_summ < 0:
            comparison_remote_type = -1
        elif diff_summ >= 0 and diff_summ <= diff:
            comparison_remote_type = 0
        else:
            comparison_remote_type = 1
        comparison_remote = estimation.page_remote.price_eco - estimation.page_remote.price_auto

    if estimation.page_soglasovanie != None:
        if estimation.page_salon != None:
            run = estimation.page_salon.run
        if estimation.page_documents != None: 
            type_reception_id   = estimation.page_documents.type_reception.id
            type_reception_name = estimation.page_documents.type_reception.name
            unit_id   = estimation.page_documents.unit.id
            unit_name = estimation.page_documents.unit.name
            city_id     = estimation.page_documents.unit.city.id
            city_name   = estimation.page_documents.unit.city.name
            owners      = estimation.page_documents.count_owners
        if estimation.page_soglasovanie != None:
            price_reception_staff   = estimation.page_soglasovanie.price_reception
            price_sale_staff        = estimation.page_soglasovanie.price_sale
            cost_plan               = estimation.page_soglasovanie.amount_podgotovka + estimation.page_soglasovanie.amount_ss + estimation.page_soglasovanie.amount_mcu  
            cost_plan_ss            = estimation.page_soglasovanie.amount_ss
            cost_plan_mcu           = estimation.page_soglasovanie.amount_mcu
            cost_plan_preparation   = estimation.page_soglasovanie.amount_podgotovka
            price_before            = estimation.page_soglasovanie.price_before_kd
            price_after             = estimation.page_soglasovanie.price_after_kd
            if estimation.page_soglasovanie.price_before_kd > 0:
                price_auto_before       = estimation.page_soglasovanie.price_auto_2 - estimation.page_soglasovanie.amount_ss
                comparison_before       = price_before - estimation.page_soglasovanie.price_auto_2 - estimation.page_soglasovanie.amount_ss
                diff            = estimation.page_soglasovanie.discount_torg + estimation.page_soglasovanie.zachita_ot_ubitka
                diff_summ       = price_before - price_auto_before
                if diff_summ < 0:
                    comparison_before_type = -1
                elif diff_summ >= 0 and diff_summ <= diff:
                    comparison_before_type = 0
                else:
                    comparison_before_type = 1
            if price_after> 0: 
                price_auto_after        = estimation.page_soglasovanie.price_auto_2
                comparison_after        = price_after - estimation.page_soglasovanie.price_auto_2
                diff            = estimation.page_soglasovanie.discount_torg + estimation.page_soglasovanie.zachita_ot_ubitka
                diff_summ       = price_after - estimation.page_soglasovanie.price_auto_2
                if diff_summ < 0:
                    comparison_after_type = -1
                elif diff_summ >= 0 and diff_summ <= diff:
                    comparison_after_type = 0
                else:
                    comparison_after_type = 1

            price_auto_bcp = estimation.page_soglasovanie.price_auto_bcp_2
            zna = estimation.page_soglasovanie.price_zna_2 
            diagostica = not estimation.page_soglasovanie.no_diagnostica
    
    year    = estimation.year
    vin     = estimation.vin 
    if estimation.staff != None:
        staff_id    = estimation.staff.id
        staff_name  = estimation.staff.name

    if estimation.staff_eco_1 != None:
        analyst_before_id       = estimation.staff_eco_1.profiles.id
        analyst_before_name     = estimation.staff_eco_1.profiles.eco_name

    if estimation.staff_eco_2 != None:    
        analyst_after_id        = estimation.staff_eco_2.profiles.id
        analyst_after_name      = estimation.staff_eco_2.profiles.eco_name
   
    if estimation.modification != None:
        mark_id             = estimation.modification.model.mark.idSite
        mark_name           = estimation.modification.model.mark.name
        model_id            = estimation.modification.model.idSite
        model_name          = estimation.modification.model.name
        modification_id     = estimation.modification.idSite
        modification_name   = estimation.modification.name
    
    zg_id = 0
    zg_name = ''
    if zna <= 200000:
        zg_id = 7
        zg_name = '200'
    elif zna <= 400000:
        zg_id = 1
        zg_name = '400'
    elif zna <= 700000:
        zg_id = 6
        zg_name = '700'
    elif zna <= 1200000:
        zg_id = 2
        zg_name = '1 200'
    elif zna <= 2000000:
        zg_id = 3
        zg_name = '2 000'
    elif zna <= 3000000:
        zg_id = 4
        zg_name = '3 000'
    elif zna <= 5000000:
        zg_id = 11
        zg_name = '5 000'
    elif zna > 5000000:
        zg_id = 12
        zg_name = '5 000+'

    TradeInFunnel.objects.update_or_create(
                        rlk_id = rlk_id,
                        defaults={
                            'estimation_id' : estimation.id,
                            'unit_id'       : unit_id,
                            'unit_name'     : unit_name,
                            'staff_id'      : staff_id,
                            'staff_name'    : staff_name,
                            'city_id'       : city_id,
                            'city_name'     : city_name,
                            'analyst_remote_id'     : analyst_remote_id,
                            'analyst_remote_name'   : analyst_remote_name,
                            'analyst_before_id'     : analyst_before_id,
                            'analyst_before_name'   : analyst_before_name,
                            'analyst_after_id'      : analyst_after_id,
                            'analyst_after_name'    : analyst_after_name,
                            'type_reception_id'     : type_reception_id,
                            'type_reception_name'   : type_reception_name,
                            'vin'       : vin,
                            'year'      : year,
                            'run'       : run,
                            'mark_id'       : mark_id,
                            'mark_name'     : mark_name,
                            'model_id'      : model_id,
                            'model_name'        : model_name,
                            'modification_id'   : modification_id,
                            'modification_name' : modification_name,
                            'date_start_estimation' : date_start_estimation,
                            'remote'    : remote,
                            'owners'    : owners,
                            'count_dtp' : estimation.count_dtp,
                            'dtp_red'   : estimation.dtp_red,
                            'iznos'     : estimation.iznos,
                            'taxi'      : estimation.taxi,
                            'carsharing'    : estimation.carsharing,
                            'k_i'           : estimation.k_i,
                            'autodex'       : estimation.avtoteka_car_autodex,
                            'date_before_success'       : estimation.date_s_do_diag,
                            'date_diagnostic_success'   : estimation.date_diagnostic,
                            'date_after_success'        : estimation.date_s_diag,
                            'date_remote_success'       : estimation.date_s_remote,
                            'price_reception_staff'     : price_reception_staff,
                            'price_sale_staff'          : price_sale_staff,                       
                            'auction'                   : estimation.auction,
                            'cost_plan'                 : cost_plan,
                            'cost_plan_ss'              : cost_plan_ss,
                            'cost_plan_mcu'             : cost_plan_mcu,
                            'cost_plan_preparation'     : cost_plan_preparation,
                            'price_remote'              : price_remote,
                            'price_before'              : price_before,
                            'price_after'               : price_after,
                            'price_auto_remote'         : price_auto_remote,
                            'price_auto_before'         : price_auto_before,
                            'price_auto_after'          : price_auto_after,
                            'price_sale'                : price_auto_bcp,
                            'price_auto_bcp'            : price_auto_bcp,
                            'stage'                     : estimation.status.name,
                            'diagostica'                : diagostica,
                            'zna'                       : zna,
                            'zna_custom'                : estimation.custom_zna,
                            'comparison_after'          : comparison_after,
                            'comparison_before'         : comparison_before,
                            'comparison_remote'         : comparison_remote,
                            'comparison_after_type'          : comparison_after_type,
                            'comparison_before_type'         : comparison_before_type,
                            'comparison_remote_type'         : comparison_remote_type,
                            'zg_id'     : zg_id,
                            'zg_name'   : zg_name,
                        }
                    )


class RegInteractivOcenkaRLK(ChangeloggableMixin, models.Model):
    rlk                 = models.OneToOneField(DocRLK, null=True, on_delete=models.SET_NULL, verbose_name="Рабочий лист")
    estimation          = models.ForeignKey(RegInteractivOcenka, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Оценка")
    
    type_reception      = models.ForeignKey(RefTypeReceptionCarsOrganization, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Тип приема автомобиля')
    
    organization        = models.ForeignKey(RefOrganization, on_delete=models.SET_NULL, null=True, verbose_name="Организация")
    filial              = models.ForeignKey(RefFilial, on_delete=models.SET_NULL, null=True, verbose_name="Филиал")
    unit                = models.ForeignKey(RefUnit, on_delete=models.SET_NULL, null=True, verbose_name="Подразделение")
    store               = models.ForeignKey(RefStore, null=True, on_delete=models.SET_NULL, verbose_name='Склад / стоянка')
    
    staff_rlk               = models.ForeignKey(RefStaff, related_name="staff_estimation_rlk", on_delete=models.SET_NULL, null=True, verbose_name="Оценщик")
    staff_eco_1_rlk         = models.ForeignKey(User, related_name="staff_eco_1_rlk", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Аналитик до кд")
    staff_eco_2_rlk         = models.ForeignKey(User, related_name="staff_eco_2_rlk", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Аналитик после кд")
    
    page_soglasovanie   = models.ForeignKey(RegInteractivOcenkaSoglasovanie, blank=True, null=True, on_delete=models.SET_NULL, verbose_name="Согласование")
    
    status              = models.ForeignKey(RefStatusEstimation, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Статус")
    
    access_user         = models.ManyToManyField(User, verbose_name='Пользователь', blank=True)
    
    prev_img                = models.CharField("Превью", max_length=2500, default='', null=True, blank=True) 
    qr                      = models.ImageField(storage=save_directory,  upload_to="estimationrlk/qr/", verbose_name="QR", blank=True, null=True)
    slug                    = models.SlugField(max_length=512, null=True, blank=True)
    
    users_eco               = models.IntegerField('Сотрудников ецо в чате', default=0, null=True, blank=True)
    users_no_eco            = models.IntegerField('Сотрудников не ецо в чате', default=0, null=True, blank=True)
    users_dop               = models.IntegerField('Сотрудников доп согласования', default=0, null=True, blank=True)

    date_s_do_diag  = models.DateTimeField('Дата согласования до диагностики', blank=True, null=True)
    date_diagnostic = models.DateTimeField('Дата диагностики', blank=True, null=True)
    date_s_diag     = models.DateTimeField('Дата согласования после диагностики', blank=True, null=True)
    
    status_ocenka                       = models.IntegerField('Секунд оценка', default=0, null=True, blank=True)
    status_soglasovanie_do_diag         = models.IntegerField('Секунд до согласования диагностики', default=0, null=True, blank=True)
    status_diagnostika                  = models.IntegerField('Секунд диагностика', default=0, null=True, blank=True)
    status_soglasovanie_posle_kd        = models.IntegerField('Секунд после диагностики', default=0, null=True, blank=True)
    
    count_task                          = models.IntegerField('Задач', default=0, null=True, blank=True)
    seconds_task                        = models.IntegerField('Время на задачи', default=0, null=True, blank=True)
    count_answer                        = models.IntegerField('Ответов ЕЦО', default=0, null=True, blank=True)
    seconds_answer                      = models.IntegerField('Среднее время ответа', default=0, null=True, blank=True)
    seconds_estimation                  = models.IntegerField('Секунд оценки', default=0, null=True, blank=True)
    
    
    def save(self, *args, **kwargs):
        
        if self.estimation != None:
            if self.estimation.vin == '' and self.estimation.number_body == '':
                self.status = RefStatusEstimation.objects.get(pk = 1)
        else:
            self.status = RefStatusEstimation.objects.get(pk = 1)

        super().save(*args, **kwargs)
    

    def __str__(self):
        return "{} / {}".format(self.rlk, self.estimation)

    class Meta:
        indexes = [
            models.Index(fields=['rlk', 'estimation'])
        ]
        db_table = 'regInteractivOcenkaRLK'
        verbose_name = "Данные интерактивной оценки рабочего листа"
        verbose_name_plural = "данные интерактивных оценок рабочего листа"


class RegInteractivOcenkaOptions(models.Model):
    estimation          = models.OneToOneField(RegInteractivOcenka, null=True, on_delete=models.SET_NULL, verbose_name="Рабочий лист")
    name                = models.CharField('Опция', max_length=21, default='')
    
    def __str__(self):
        return "{} / {}".format(self.estimation, self.name)

    class Meta:
        db_table = 'regInteractivOcenkaOptions'
        verbose_name = "Опция автомобиля"
        verbose_name_plural = "Опции автомобиля"


class RegRegInteractivOcenkaFiles(models.Model):
    estimation  = models.ForeignKey(RegInteractivOcenka, on_delete=models.PROTECT, null=True, verbose_name="Оценка")
    name        = models.CharField("Наименование", max_length=512, default='', blank=True)
    type_file   = models.CharField("Принадлежность файлов", max_length=512, default='', blank=True)
    file        = models.FileField(storage=save_directory,  upload_to="estimation/%Y/%m/%d/", verbose_name="Файл", blank=True, null=True)
    file_mini   = models.FileField(storage=save_directory,  upload_to="estimation/%Y/%m/%d/", verbose_name="Файл сжатый", blank=True, null=True) 
    comment     = models.CharField("Комментарий", max_length=512, default='', blank=True)
    file_number = models.IntegerField('Порядок', default=0, null=True, blank=True) 
    text        = models.CharField("Текст", max_length=512, default='', blank=True)
    type_point  = models.CharField("Тип метки", max_length=512, default='', blank=True)
    cor_x       = models.IntegerField('Координата X', default=0, null=True, blank=True) 
    cor_y       = models.IntegerField('Координата Y', default=0, null=True, blank=True) 
    kraska      = models.IntegerField('Показание толщиномера', default=0, null=True, blank=True) 
    order       = models.IntegerField('Приоритет', default=0, null=True, blank=True) 
    blank       = models.BooleanField("Пустой", default = False, null=True, blank=True)
    date        = models.DateTimeField('Дата', blank=True, null=True)
    user        = models.ForeignKey(User, related_name="author", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Автор")

    def get_absolute_url(self):
        
        try:
            return self.file.url.replace('/media/', '/media_dop/')
        except:
            if self.kraska > 0:
                return '/media_dop/static/estimation/pribor.jpg'

        return '/media_dop/static/estimation/no_foto.jpg'
    
    def is_video(self):
        list_world_name = self.file.name.lower().split('.')
        format = list_world_name[-1]
        if format.find('jpg') > -1 or format.find('jpeg') > -1 or format.find('svg') > -1 or format.find('gif') > -1 or format.find('png') > -1 or format.find('tiff') > -1:
            return False
        return True

    def save(self, *args, **kwargs):
        try:
            if self.type_file == 'vin':
                self.order = 0
            elif self.type_file == 'salon_error':
                self.order = 8
            elif self.type_file == 'salon_all':
                self.order = 7
            elif self.type_file == 'vnesh_car_all':
                self.order = 6
            elif self.type_file == 'run':
                self.order = 8
            elif self.type_file == 'vnesh_light_error':
                self.order = 50
            elif self.type_file == 'kolesa':
                self.order = 9
            elif self.type_file == 'kolesa2':
                self.order = 10
            elif self.type_file == 'vnesh_windows_error':
                self.order = 40
            elif self.type_file == 'vnesh_windows_error':
                self.order = 30
            elif self.type_file == 'pod_capot':
                self.order = 20
            
            if self.date == None:
                self.date = datetime.now()

        except:
            self.order = 0

        super().save(*args, **kwargs)

    def __str__(self):
        return "{}".format(self.estimation)

    class Meta:
        db_table = 'regRegInteractivOcenkaFiles'
        verbose_name = "Фото интерактивной оценки"
        verbose_name_plural = "Фото интерактивной оценки"


class RegInteractivOcenkaEmailPush(models.Model):
    date            = models.DateTimeField('Дата создания', default=datetime.now, blank=False)
    estimation      = models.ForeignKey(RegInteractivOcenka, null=True, on_delete=models.SET_NULL, verbose_name="Интерактивная оценка")
    user            = models.ForeignKey(User, related_name="user", on_delete=models.SET_NULL, null=True, verbose_name="Пользователь")
    email           = models.CharField("Email", max_length=2048, default='', null=True, blank=True)
    comment         = models.CharField("Текст", max_length=2048, default='', null=True, blank=True) 
    send            = models.BooleanField("Отправлено", default = False, null=True, blank=True)
    agreement_start     = models.BooleanField("Согласование", default = False, null=True, blank=True)
    agreement_before_kd = models.BooleanField("Согласована до кд", default = False, null=True, blank=True)
    agreement_success   = models.BooleanField("Соглаование выполнено", default = False, null=True, blank=True)
    test_drive          = models.BooleanField("Пройден тест драйв", default = False, null=True, blank=True)
    diagnostica         = models.BooleanField("Диагностика", default = False, null=True, blank=True)
    task                = models.BooleanField("Задача", default = False, null=True, blank=True)
    task_success        = models.BooleanField("Задача выполнена", default = False, null=True, blank=True)
    message_websoket    = models.BooleanField("Сообщение web-socket", default = False, null=True, blank=True)

    def __str__(self):
        return "{} / {}".format(self.estimation, self.user)

    class Meta:
        db_table = 'regInteractivOcenkaEmailPush'
        verbose_name = "Оповещения по интерактивной оценке"
        verbose_name_plural = "Оповещения по интерактивным оценкам"


class RegInteractivOcenkaHistoryOpens(models.Model):
    estimation  = models.ForeignKey(RegInteractivOcenka, on_delete=models.PROTECT, null=True, verbose_name="Оценка")
    page        = models.IntegerField("Страница номер",  default=0, null=True, blank=True) 
    page_title  = models.CharField("Страница", max_length=512, default='', blank=True)
    staff       = models.ForeignKey(User, related_name="staff_open", on_delete=models.SET_NULL, null=True, verbose_name="Пользователь")
    date_open   = models.DateTimeField('Дата начала', default=datetime.now, blank=True, null=True)
    

    def __str__(self):
        return "{} - {} - {} - {} ".format(self.date_open, self.page, self.estimation, self.staff)

    class Meta:
        db_table = 'regInteractivOcenkaHistoryOpens'
        verbose_name = "Информация по открытию страниц оценки"
        verbose_name_plural = "Информация по открытию страницы оценки"


class RegInteractivOcenkaTask(models.Model):
    estimation          = models.ForeignKey(RegInteractivOcenka, on_delete=models.PROTECT, null=True, verbose_name="Оценка")
    staff_open          = models.ForeignKey(User, related_name="task_staff_open", on_delete=models.SET_NULL, null=True, verbose_name="Пользователь автор")
    staff_close         = models.ForeignKey(User, related_name="task_staff_close", on_delete=models.SET_NULL, null=True, verbose_name="Пользователь выполнивший")
    date_open           = models.DateTimeField('Дата начала', default=datetime.now, blank=True, null=True)
    date_close          = models.DateTimeField('Дата закрытия', blank=True, null=True)
    comment_task        = models.CharField("Комментарий задания", max_length=2048, default='', null=True, blank=True) 
    comment_success     = models.CharField("Комментарий выполнения", max_length=2048, default='', null=True, blank=True) 
    
    def files_all(self):
        fotos = RegRegInteractivOcenkaTaskFiles.objects.filter(estimation_task = self)
        return fotos

    def files_all_count(self):
        fotos = RegRegInteractivOcenkaTaskFiles.objects.filter(estimation_task = self).count()
        return fotos
    
    def __str__(self):
        return "{} - {} - {} - {} ".format(self.date_open, self.date_close, self.estimation, self.staff_open)

    class Meta:
        db_table = 'regInteractivOcenkaTask'
        verbose_name = "Задача по интерактивной оценке"
        verbose_name_plural = "Задачи по интерактивной оценке"


class RegRegInteractivOcenkaTaskFiles(models.Model):
    estimation_task  = models.ForeignKey(RegInteractivOcenkaTask, on_delete=models.PROTECT, null=True, verbose_name="Задача по оценке")
    name        = models.CharField("Наименование", max_length=512, default='', blank=True)
    file        = models.FileField(storage=save_directory,  upload_to="estimation_task/%Y/%m/%d/", verbose_name="Файл", blank=True, null=True)
    file_mini   = models.FileField(storage=save_directory,  upload_to="estimation_task/%Y/%m/%d/", verbose_name="Файл сжатый", blank=True, null=True) 
    comment     = models.CharField("Комментарий", max_length=512, default='', blank=True)
    
    def get_absolute_url(self):
        
        try:
            return self.file.url.replace('/media/', '/media_dop/')
        except:
            return '/media_dop/static/estimation/pribor.jpg'
        
        return ""
    
    def is_video(self):
        list_world_name = self.file.name.lower().split('.')
        format = list_world_name[-1]
        if format.find('jpg') > -1 or format.find('jpeg') > -1 or format.find('svg') > -1 or format.find('gif') > -1 or format.find('png') > -1 or format.find('tiff') > -1:
            return False
        return True

    
    def __str__(self):
        return "{}".format(self.estimation_task)

    class Meta:
        db_table = 'regRegInteractivOcenkaTaskFiles'
        verbose_name = "Фото задач интерактивной оценки"
        verbose_name_plural = "Фото задачи интерактивной оценки"


class RegSwapKors(models.Model):
    
    estimation  = models.ForeignKey(RegInteractivOcenka, on_delete=models.PROTECT, blank=True, null=True, verbose_name="Оценка")
    rlk         = models.ForeignKey(DocRLK, on_delete=models.PROTECT, blank=True, null=True, verbose_name="Рабочий лист")
    
    date        = models.DateTimeField('Дата начала', default=datetime.now, blank=True, null=True)
    uid         = models.CharField(max_length=100, blank=True, unique=True, default=uuid.uuid4)
    comment     = models.CharField("Комментарий", max_length=512, default='', blank=True)
    status      = models.CharField(max_length=100, blank=True, unique=False, default='')
    status_code = models.IntegerField("Код ответа", default=60, null=True, blank=True)
    status_date = models.DateTimeField('Дата ответа', blank=True, null=True)
    
    def __str__(self):
        return "{}".format(self.estimation)

    class Meta:
        db_table = 'regSwapKors'
        verbose_name = "Выгрузка информации в корсавто"
        verbose_name_plural = "Выгрузки информации в корсавто"


class RegInfoBody(models.Model):
    
    type_body       = models.CharField("Тип кузова", max_length=512, default='', blank=True)
    side            = models.CharField("Сторона", max_length=512, default='', blank=True)
    body_element    = models.CharField("Элемент", max_length=512, default='', blank=True)
    polygon         = models.CharField("Полигон", max_length=512, default='', blank=True)
    body_elem_name  = models.CharField("Элемент наименование", max_length=512, default='', blank=True)
    
    def __str__(self):
        return "{} - {} / {}".format(self.type_body, self.side, self.body_element)

    class Meta:
        db_table = 'regInfoBody'
        verbose_name = "Информации по полигонам кузовов"
        verbose_name_plural = "Информации по полигонам кузовов"


class RegInteractivOcenkaKorsStore(models.Model):
    
    estimation              = models.ForeignKey(RegInteractivOcenka, on_delete=models.PROTECT, null=True, verbose_name="Оценка")
    store                   = models.ForeignKey(RefStore, null=True, on_delete=models.SET_NULL, verbose_name="Стоянка")
    doc                     = models.ForeignKey(DocLO, null=True, on_delete=models.SET_NULL, verbose_name="Лист оценки")
    
    vin                     = models.CharField("ВИН", max_length=21, default='') 
    year                    = models.IntegerField("Год выпуска",  default=0, null=True, blank=True) 
    run                     = models.IntegerField("Пробег", null=True, default=0, blank=True)
    owners                  = models.IntegerField("Владельцев", null=True, default=0, blank=True)

    type_drive              = models.CharField("Тип привода", max_length=21, default='', null=True, blank=True) 
    number_body             = models.CharField("Номер кузова", max_length=21, default='', null=True, blank=True) 
    modification            = models.ForeignKey(AutoruModification, blank=True, null=True, on_delete=models.SET_NULL, verbose_name='Модификация')
    complectation           = models.ForeignKey(AutoruComplectation, blank=True, null=True, on_delete=models.SET_NULL, verbose_name='Комплектация')
    modification_avito      = models.ForeignKey(RefAvito, blank=True,null=True, on_delete=models.SET_NULL, verbose_name='Модификация авито')
    complectation_avito     = models.ForeignKey(RefAvitoComplectation, blank=True, null=True, on_delete=models.SET_NULL, verbose_name='Комплектация авито')
    prev_img                = models.CharField("Превью", max_length=2500, default='', null=True, blank=True) 
    qr                      = models.ImageField(storage=save_directory,  upload_to="estimation/qr/", verbose_name="QR", blank=True, null=True)
    
    count_dtp               = models.IntegerField('Количество дтп', default=0, null=True, blank=True)
    
    price_bcp               = models.IntegerField('БЦП', default=0, null=True, blank=True)
    price                   = models.IntegerField("Цена продажи", blank=True, default=0)
    cost_price              = models.IntegerField("Себестоимость", blank=True, default=0)
    outlay                  = models.IntegerField("Расходы на АМ", blank=True, default=0)
    days_in_stok            = models.IntegerField("Дней на складе", blank=True, default=0)
    k_i                     = models.FloatField("Коэфицент износа", default=0.0, blank=True)
    iznos                   = models.BooleanField("Повышенный износ", default = False, null=True, blank=True)
    zna                     = models.IntegerField("ЦНА", null=True, default=0, blank=True)
    active                  = models.BooleanField("Учавствует в расчете", default = False, null=True, blank=True)

    def cum(self):
        return self.price - (self.cost_price + self.outlay)
    
    def save(self, *args, **kwargs):
        try:
            avtohubs = Avtohub.objects.filter(vin = self.vin).exclude(avgMarketPrice = 0).order_by('-date')
            self.zna = avtohubs[0].avgMarketPrice
        except:
            s=1 
        try:
            eyar_k = datetime.now().year - self.year
            if eyar_k == 0:
                eyar_k = 1
            self.k_i = round(self.run / (eyar_k * 35000), 2)
            if self.run <= 175000 and self.k_i <= 1.2:
                self.iznos = False
            elif self.run <= 175000 and self.k_i > 1.2:
                self.iznos = True
            elif self.run > 175000 and self.k_i > 0:
                self.iznos = True
        except:
            s =1 

        super().save(*args, **kwargs)

    def __str__(self):
        return "{} / {}".format(self.estimation, self.vin)

    class Meta:
        db_table = 'regInteractivOcenkaKorsStore'
        verbose_name = "Склад корсавто на момент оценки"
        verbose_name_plural = "Данные интерактивной оценки страницы колеса" 


class RegInteractivOcenkaKorsStoreSale(models.Model):
    
    estimation              = models.ForeignKey(RegInteractivOcenka, on_delete=models.PROTECT, null=True, verbose_name="Оценка")
    store                   = models.ForeignKey(RefStore, null=True, on_delete=models.SET_NULL, verbose_name="Стоянка")
    doc                     = models.ForeignKey(DocCarShipment, null=True, on_delete=models.SET_NULL, verbose_name="Отгрузка")
    
    vin                     = models.CharField("ВИН", max_length=21, default='') 
    year                    = models.IntegerField("Год выпуска",  default=0, null=True, blank=True) 
    run                     = models.IntegerField("Пробег", null=True, default=0, blank=True)
    owners                  = models.IntegerField("Владельцев", null=True, default=0, blank=True)

    type_drive              = models.CharField("Тип привода", max_length=21, default='', null=True, blank=True) 
    number_body             = models.CharField("Номер кузова", max_length=21, default='', null=True, blank=True) 
    modification            = models.ForeignKey(AutoruModification, blank=True, null=True, on_delete=models.SET_NULL, verbose_name='Модификация')
    complectation           = models.ForeignKey(AutoruComplectation, blank=True, null=True, on_delete=models.SET_NULL, verbose_name='Комплектация')
    modification_avito      = models.ForeignKey(RefAvito, blank=True,null=True, on_delete=models.SET_NULL, verbose_name='Модификация авито')
    complectation_avito     = models.ForeignKey(RefAvitoComplectation, blank=True, null=True, on_delete=models.SET_NULL, verbose_name='Комплектация авито')
    prev_img                = models.CharField("Превью", max_length=2500, default='', null=True, blank=True) 
    qr                      = models.ImageField(storage=save_directory,  upload_to="estimation/qr/", verbose_name="QR", blank=True, null=True)
    
    count_dtp               = models.IntegerField('Количество дтп', default=0, null=True, blank=True)
    
    price_bcp               = models.IntegerField('БЦП', default=0, null=True, blank=True)
    price                   = models.IntegerField("Цена продажи", blank=True, default=0)
    cost_price              = models.IntegerField("Себестоимость", blank=True, default=0)
    outlay                  = models.IntegerField("Расходы на АМ", blank=True, default=0)
    days_in_stok            = models.IntegerField("Дней на складе", blank=True, default=0)
    
    discountAmount          = models.FloatField("Скидка итог", default=0.0, blank=True)
    discountAmountTorg      = models.FloatField("Скидка торг", default=0.0, blank=True)
    discountAmountTradeIN   = models.FloatField("Скидка трейдин", default=0.0, blank=True)
    
    k_i                     = models.FloatField("Коэфицент износа", default=0.0, blank=True)
    iznos                   = models.BooleanField("Повышенный износ", default = False, null=True, blank=True)
    zna                     = models.IntegerField("ЦНА", null=True, default=0, blank=True)
    active                  = models.BooleanField("Учавствует в расчете", default = False, null=True, blank=True)

    def cum(self):
        return self.price - (self.cost_price + self.outlay)

    def save(self, *args, **kwargs):
        try:
            avtohubs = Avtohub.objects.filter(vin = self.vin).exclude(avgMarketPrice = 0).order_by('-date')
            self.zna = avtohubs[0].avgMarketPrice
        except:
            s=1 
        try:
            eyar_k              = self.doc.dataTime.year - self.year
            if eyar_k == 0:
                eyar_k = 1
            self.k_i = round(self.run / (eyar_k * 35000), 2)
            if self.run <= 175000 and self.k_i <= 1.2:
                self.iznos = False
            elif self.run <= 175000 and self.k_i > 1.2:
                self.iznos = True
            elif self.run > 175000 and self.k_i > 0:
                self.iznos = True
        except:
            s =1 
            
        super().save(*args, **kwargs)

    def __str__(self):
        return "{} / {}".format(self.estimation, self.vin)

    class Meta:
        db_table = 'regInteractivOcenkaKorsStoreSale'
        verbose_name = "Склад корсавто на момент оценки"
        verbose_name_plural = "Данные интерактивной оценки страницы колеса"


class RegPodgotovkaWork(models.Model):
    
    name                    = models.CharField("Наименование", max_length=512, default='') 
    name_group              = models.CharField("Наименование группа", max_length=512, default='') 
    price_podrad            = models.IntegerField("Стоимость подряд",  default=0, null=True, blank=True) 
    price_kors              = models.IntegerField("Стоимость корсавто",  default=0, null=True, blank=True) 
    normo                   = models.FloatField("НормоЧас", default=0.0, blank=True)
    materials_kf            = models.FloatField("Материалы коэфицент", default=0.0, null=False, blank=True)
    materials_price         = models.FloatField("Материалы цена", default=0.0, null=False, blank=True)
    materials_amount        = models.FloatField("Материалы сумма", default=0.0, null=False, blank=True)
    type_settings           = models.IntegerField("Тип настройки для интерактивной оценки",  default=0, null=True, blank=True) 
    
    def save(self, *args, **kwargs):
        try:
            if self.materials_kf > 0:
                self.materials_price = self.materials_amount / self.materials_kf
        except:
            s=1
        
        super().save(*args, **kwargs)

    def __str__(self):
        return "{} / {}".format(self.name_group, self.name)

    class Meta:
        db_table = 'regPodgotovkaWork'
        verbose_name = "Работа по подготовке АМ"
        verbose_name_plural = "Работы по подготовке АМ"


class RegEstimationPodgotovka(models.Model):
    estimation              = models.ForeignKey(RegInteractivOcenka, on_delete=models.PROTECT, null=True, verbose_name="Оценка")
    name                    = models.CharField("Наименование", max_length=512, default='') 
    normo                   = models.FloatField("НормоЧас", default=0.0, blank=True)
    materials_kf            = models.FloatField("Материалы коэфицент", default=0.0, null=False, blank=True)
    materials_price         = models.FloatField("Материалы цена", default=0.0, null=False, blank=True)
    materials_amount        = models.FloatField("Материалы сумма", default=0.0, null=False, blank=True)
    price_podrad            = models.IntegerField("Стоимость подряд",  default=0, null=True, blank=True) 
    price_kors              = models.IntegerField("Стоимость корсавто",  default=0, null=True, blank=True) 
    status                  = models.IntegerField("Статус",  default=0, null=False, blank=True)
    start                   = models.DateTimeField('Дата начала оценки', blank=True, null=True)
    end                     = models.DateTimeField('Дата окончания оценки', blank=True, null=True)

    def __str__(self):
        return "{} / {}".format(self.estimation, self.name)

    class Meta:
        indexes = [
            models.Index(fields=['estimation'])
        ]
        db_table = 'regEstimationPodgotovka'
        verbose_name = "Работа по подготовке расчитанные"
        verbose_name_plural = "Работы по подготовке расчитанные"


class RegEstimationSS(models.Model):
    estimation              = models.ForeignKey(RegInteractivOcenka, on_delete=models.PROTECT, null=True, verbose_name="Оценка")
    name                    = models.CharField("Наименование", max_length=512, default='') 
    normo                   = models.FloatField("НормоЧас", default=0.0, blank=True)
    materials_kf            = models.FloatField("Материалы коэфицент", default=0.0, null=False, blank=True)
    materials_price         = models.FloatField("Материалы цена", default=0.0, null=False, blank=True)
    materials_amount        = models.FloatField("Материалы сумма", default=0.0, null=False, blank=True)
    price_podrad            = models.IntegerField("Стоимость подряд",  default=0, null=True, blank=True) 
    price_kors              = models.IntegerField("Стоимость корсавто",  default=0, null=True, blank=True) 
    status                  = models.IntegerField("Статус",  default=0, null=False, blank=True)
    start                   = models.DateTimeField('Дата начала оценки', blank=True, null=True)
    end                     = models.DateTimeField('Дата окончания оценки', blank=True, null=True)

    def __str__(self):
        return "{} / {}".format(self.estimation, self.name)

    class Meta:
        indexes = [
            models.Index(fields=['estimation'])
        ]
        db_table = 'regEstimationSS'
        verbose_name = "Работа по слесарному цеху расчитанные"
        verbose_name_plural = "Работы по слесарному цеху расчитанные"


class RegEstimationMCU(models.Model): 
    estimation              = models.ForeignKey(RegInteractivOcenka, on_delete=models.PROTECT, null=True, verbose_name="Оценка")
    name                    = models.CharField("Наименование", max_length=512, default='') 
    normo                   = models.FloatField("НормоЧас", default=0.0, blank=False)
    materials_kf            = models.FloatField("Материалы коэфицент", default=0.0, null=False, blank=True)
    materials_price         = models.FloatField("Материалы цена", default=0.0, null=False, blank=True)
    materials_amount        = models.FloatField("Материалы сумма", default=0.0, null=False, blank=True)
    price_podrad            = models.IntegerField("Стоимость подряд",  default=0, null=False, blank=True) 
    price_kors              = models.IntegerField("Стоимость корсавто",  default=0, null=False, blank=True) 
    status                  = models.IntegerField("Статус",  default=0, null=False, blank=True)
    start                   = models.DateTimeField('Дата начала оценки', blank=True, null=True)
    end                     = models.DateTimeField('Дата окончания оценки', blank=True, null=True)
     
    def __str__(self):
        return "{} / {}".format(self.estimation, self.name)

    class Meta:
        indexes = [
            models.Index(fields=['estimation'])
        ]
        db_table = 'regEstimationMCU'
        verbose_name = "Работа по кузовному цеху расчитанные"
        verbose_name_plural = "Работы по кузовному цеху расчитанные"


class RegEstimationBalanceUnit(models.Model):
    unit                    = models.ForeignKey(RefUnit, on_delete=models.PROTECT, null=True, verbose_name="Подразделение")
    date                    = models.DateTimeField('Дата операции', blank=True, null=True)
    estimation              = models.ForeignKey(RegInteractivOcenka, on_delete=models.PROTECT, null=True, verbose_name="Оценка")
    shipment                = models.ForeignKey(DocCarShipment, on_delete=models.PROTECT, null=True, verbose_name="Отгрузка")
    amount_in               = models.FloatField("Сумма движения вход", default=0.0, blank=False)
    amount_out              = models.FloatField("Сумма движения выход", default=0.0, blank=False)    
    amount_custom           = models.FloatField("Сумма движения ручная", default=0.0, blank=False)    
    amount                  = models.FloatField("Сумма движения итог", default=0.0, blank=False)
    comment_1               = models.CharField("Комментарий", max_length=1024, default='') 
    comment_2               = models.CharField("Комментарий 2", max_length=1024, default='')
    comment_3               = models.CharField("Комментарий 3", max_length=1024, default='') 
     
    def __str__(self):
        return "{} / {} / {}".format(self.unit, self.date, self.date, self.amount)

    def save(self, *args, **kwargs):
        try:
            if self.amount_custom != None and self.amount_custom != 0:
               self.amount = self.amount_custom
            else:     
                if self.shipment != None:
                    self.amount = self.amount_out
                else:
                    self.amount = self.amount_in
        except:
            s=1

        try:
            self.date = self.estimation.start_estimation
        except:
            s=1

        try:
            if self.shipment != None:
                self.date = self.shipment.dataTime
        except:
            s=1
        
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['unit', 'estimation', 'shipment'])
        ]
        db_table = 'regEstimationBalanceUnit'
        verbose_name = "Баланс подразделений организациий"
        verbose_name_plural = "Баланс подразделений организации"


class RegEstimationBalanceStaffEco(models.Model):
    staff                   = models.ForeignKey(RefStaff, on_delete=models.PROTECT, null=True, verbose_name="Подразделение")
    date                    = models.DateTimeField('Дата операции', blank=True, null=True)
    estimation              = models.ForeignKey(RegInteractivOcenka, on_delete=models.PROTECT, null=True, verbose_name="Оценка")
    shipment                = models.ForeignKey(DocCarShipment, on_delete=models.PROTECT, null=True, verbose_name="Отгрузка")
    amount                  = models.FloatField("Сумма движения", default=0.0, blank=False)
     
    def __str__(self):
        return "{} / {} / {}".format(self.staff, self.date, self.date, self.amount)

    class Meta:
        db_table = 'regEstimationBalanceStaffEco'
        verbose_name = "Баланс сотрудники ецо"
        verbose_name_plural = "Баланс сотрудники ецо"


def refresh_balance_unit(estimation):
    
    unit = estimation.rlk.unit
    
    if unit == None:
        unit = estimation.rlk.unit_dc
    
    if estimation.page_documents.type_reception.id == 7 and estimation.rlk.unit != None:
        unit = estimation.rlk.unit

    RegEstimationBalanceUnit.objects.filter(estimation = estimation).delete()
    
    save = True
    if unit.name.find('КорсАвто') < 0 and unit.name.find('Корс Авто') < 0 and estimation.page_documents.type_reception.id != 4:
        if estimation.page_documents.type_reception.id == 2:
            save = True
    else:
        if estimation.page_documents.type_reception.id == 4:
            save = True
    
    amount = 0
    
    if estimation.page_documents.type_reception.id == 3:
        save = False

    if estimation.page_soglasovanie.price_auto_1 > 0:
        if estimation.page_soglasovanie.price_auto_1 < estimation.page_soglasovanie.price_after_kd:
            amount = estimation.page_soglasovanie.price_auto_1 - estimation.page_soglasovanie.price_after_kd
        elif estimation.page_soglasovanie.zachita_ot_ubitka != None and estimation.page_soglasovanie.zachita_ot_ubitka > 0:
            amount = estimation.page_soglasovanie.zachita_ot_ubitka

    elif estimation.page_soglasovanie.price_auto_2 > 0:
        if estimation.page_soglasovanie.price_auto_2 < estimation.page_soglasovanie.price_after_kd:
            amount = estimation.page_soglasovanie.price_auto_2 - estimation.page_soglasovanie.price_after_kd
        elif estimation.page_soglasovanie.zachita_ot_ubitka != None and estimation.page_soglasovanie.zachita_ot_ubitka > 0:
            amount = estimation.page_soglasovanie.zachita_ot_ubitka

    elif estimation.page_soglasovanie.price_auto_3 > 0:
        if estimation.page_soglasovanie.price_auto_3 < estimation.page_soglasovanie.price_after_kd:
            amount = estimation.page_soglasovanie.price_auto_3 - estimation.page_soglasovanie.price_after_kd
        elif estimation.page_soglasovanie.zachita_ot_ubitka != None and estimation.page_soglasovanie.zachita_ot_ubitka > 0:
            amount = estimation.page_soglasovanie.zachita_ot_ubitka
          
    if save:
        new_record              = RegEstimationBalanceUnit()
        new_record.unit         = unit
        new_record.date         = estimation.start_estimation
        new_record.estimation   = estimation
        new_record.amount       = amount
        new_record.save()


def refresh_balance_unit_staff(estimation):
    
    staff = estimation.staff_eco_2
    
    RegEstimationBalanceStaffEco.objects.filter(estimation = estimation).delete()
    count = RefStaff.objects.filter(domain_login = staff.username).count()
    if count > 0:
        user_staff              = RefStaff.objects.filter(domain_login = staff.username)[0] 
        new_record              = RegEstimationBalanceStaffEco()
        new_record.staff        = user_staff
        new_record.date         = estimation.start_estimation
        new_record.estimation   = estimation
        
        if estimation.page_soglasovanie.price_auto_1 > 0:
            new_record.amount       = estimation.page_soglasovanie.price_auto_1 - estimation.page_soglasovanie.price_after_kd
        elif estimation.page_soglasovanie.price_auto_2 > 0:
            new_record.amount       = estimation.page_soglasovanie.price_auto_2 - estimation.page_soglasovanie.price_after_kd
        elif estimation.page_soglasovanie.price_auto_3 > 0:
            new_record.amount       = estimation.page_soglasovanie.price_auto_3 - estimation.page_soglasovanie.price_after_kd
        
        new_record.save()

                             
class RegEstimationRefCarsOrganizations(models.Model):
    car                     = models.ForeignKey(RefCarsOrganization, on_delete=models.PROTECT, null=True, verbose_name="Автомобиль")
    date                    = models.DateTimeField('Дата', default=datetime.now, blank=True, null=True)
    avg_price               = models.IntegerField("Средняя стоимость",  default=0, null=False, blank=True) 
    avg_days                = models.IntegerField("Среднее дней на складе",  default=0, null=False, blank=True) 
    position                = models.IntegerField("Позиция",  default=0, null=False, blank=True) 
    price                   = models.IntegerField("Цена наша",  default=0, null=False, blank=True)  
    total                   = models.IntegerField("Всего авто",  default=0, null=False, blank=True)  
    error                   = models.CharField("Правило", max_length=2048, default='')

    def __str__(self):
        return "{} / {} / {}".format(self.car, self.date, self.avg_price)

    class Meta:
        indexes = [
            models.Index(fields=['car'])
        ]
        db_table = 'regEstimationRefCarsOrganizations'
        verbose_name = "Данные по оценке автомобиля на складе"
        verbose_name_plural = "Данные по оценкам автомобилей на складе"


class RegRefCarsOrganizationsPrice(models.Model):
    date                    = models.DateTimeField('Дата', default=datetime.now, blank=True, null=True)
    car                     = models.ForeignKey(RefCarsOrganization, on_delete=models.PROTECT, null=True, verbose_name="Автомобиль")
    price                   = models.IntegerField("Цена",  default=0, null=False, blank=True) 
     
    def __str__(self):
        return "{} / {} / {}".format(self.car, self.date, self.price)

    class Meta:
        indexes = [
            models.Index(fields=['car']),
            models.Index(fields=['date'])
        ]
        db_table = 'regRefCarsOrganizationsPrice'
        verbose_name = "Цены автомобилей организаций"
        verbose_name_plural = "Цены автомобилей организаций"


class RegRefCarsOrganizationsCalculationPrice(models.Model):
    date                    = models.DateTimeField('Дата', default=datetime.now, blank=True, null=True)
    car                     = models.ForeignKey(RefCarsOrganization, on_delete=models.PROTECT, null=True, verbose_name="Автомобиль")
    price                   = models.IntegerField("Цена",  default=0, null=False, blank=True) 
    evaluation              = models.ForeignKey(RefTypeEvaluationCarsOrganization, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Вариант управления ценообразованием')
    rule                    = models.CharField("Правило", max_length=2048, default='')

    def __str__(self):
        return "{} / {} / {}".format(self.car, self.date, self.price)

    class Meta:
        indexes = [
            models.Index(fields=['car']),
            models.Index(fields=['date']),
            models.Index(fields=['evaluation']) 
        ]
        db_table = 'regRefCarsOrganizationsCalculationPrice'
        verbose_name = "Цены автомобилей организаций расчетные"
        verbose_name_plural = "Цены автомобилей организаций расчетные"


class RegCarsRepricingHistory(models.Model):
    """История переоценки автомобилей"""
    
    STATUS_CHOICES = [
        ('pending', 'В очереди'),
        ('processing', 'Обрабатывается'),
        ('success', 'Успешно'),
        ('error', 'Ошибка'),
        ('partial', 'Частично'),
    ]
    
    unit = models.ForeignKey(RefUnit, null=True, on_delete=models.SET_NULL, verbose_name='Подразделение ДЦ')
    evaluation = models.ForeignKey(RefTypeEvaluationCarsOrganization, null=True, blank=True, 
                                   on_delete=models.SET_NULL, verbose_name='Вариант управления ценообразованием')
    
    # Статус и результат
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default='pending')
    cars_total = models.IntegerField("Всего автомобилей", default=0)
    cars_processed = models.IntegerField("Обработано автомобилей", default=0)
    cars_updated = models.IntegerField("Обновлено цен", default=0)
    cars_skipped = models.IntegerField("Пропущено автомобилей", default=0)
    cars_errors = models.IntegerField("Ошибок", default=0)
    
    # Детали
    error_message = models.TextField("Сообщение об ошибке", blank=True, default='')
    details = models.TextField("Детали переоценки (JSON)", blank=True, default='{}',
                               help_text="Дополнительная информация о переоценке")
    
    # Метаданные
    date_start = models.DateTimeField('Дата начала', default=datetime.now, blank=False)
    date_end = models.DateTimeField('Дата окончания', null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                            on_delete=models.SET_NULL, related_name='cars_repricing_history',
                            verbose_name="Пользователь")
    is_manual = models.BooleanField("Ручная переоценка", default=False,
                                    help_text="True если запущена вручную, False если автоматически")
    
    def __str__(self):
        return f"{self.unit.name if self.unit else 'Все'} - {self.date_start.strftime('%d.%m.%Y %H:%M')} ({self.status})"
    
    def get_details(self):
        """Получить детали переоценки как словарь"""
        try:
            return json.loads(self.details) if self.details else {}
        except:
            return {}
    
    def set_details(self, details_dict):
        """Установить детали переоценки из словаря"""
        self.details = json.dumps(details_dict, ensure_ascii=False)
    
    class Meta:
        db_table = 'regCarsRepricingHistory'
        verbose_name = "История переоценки автомобилей"
        verbose_name_plural = "История переоценок автомобилей"
        ordering = ['-date_start']
        indexes = [
            models.Index(fields=['unit', 'date_start']),
            models.Index(fields=['status']),
            models.Index(fields=['evaluation']),
        ]


class RegCarsRepricingLog(models.Model):
    """Лог переоценки конкретного автомобиля"""
    
    STATUS_CHOICES = [
        ('success', 'Успешно'),
        ('error', 'Ошибка'),
        ('skipped', 'Пропущен'),
    ]
    
    repricing_history = models.ForeignKey(RegCarsRepricingHistory, on_delete=models.CASCADE,
                                         related_name='repricing_logs', verbose_name="История переоценки")
    car = models.ForeignKey(RefCarsOrganization, on_delete=models.CASCADE,
                           related_name='repricing_logs', verbose_name="Автомобиль")
    
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default='success')
    old_price = models.IntegerField("Старая цена", null=True, blank=True, default=None)
    new_price = models.IntegerField("Новая цена", null=True, blank=True, default=None)
    price_difference = models.IntegerField("Разница в цене", null=True, blank=True, default=None)
    error_message = models.TextField("Сообщение об ошибке", blank=True, default='')
    calculation_details = models.TextField("Детали расчета (JSON)", blank=True, default='{}',
                                          help_text="Детали расчета новой цены")
    
    date_create = models.DateTimeField('Дата создания', default=datetime.now, blank=False)
    
    def __str__(self):
        return f"{self.car.vin} - {self.status}"
    
    def get_calculation_details(self):
        """Получить детали расчета как словарь"""
        try:
            return json.loads(self.calculation_details) if self.calculation_details else {}
        except:
            return {}
    
    class Meta:
        db_table = 'regCarsRepricingLog'
        verbose_name = "Лог переоценки автомобиля"
        verbose_name_plural = "Логи переоценки автомобилей"
        ordering = ['-date_create']
        indexes = [
            models.Index(fields=['repricing_history', 'car']),
            models.Index(fields=['status']),
        ]


class RegCarsExpenses(models.Model):
    car                     = models.ForeignKey(RefCarsOrganization, on_delete=models.PROTECT, null=True, verbose_name="Автомобиль")
    date                    = models.DateTimeField('Дата', default=datetime.now, blank=True, null=True)
    name                    = models.CharField("Наименование", max_length=512, default='') 
    normo                   = models.FloatField("НормоЧас", default=0.0, blank=True)
    price                   = models.IntegerField("Цена",  default=0, null=True, blank=True) 
    amount                  = models.IntegerField("Сумма",  default=0, null=True, blank=True) 
   
    def __str__(self):
        return "{} / {}".format(self.car, self.name)

    class Meta:
        indexes = [
            models.Index(fields=['car'])
        ]
        db_table = 'regCarsExpenses'
        verbose_name = "Затраты на автомобиль"
        verbose_name_plural = "Затраты на автомобиль"


class RegEstimationsCalculationDetail(models.Model):
    estimations = models.ForeignKey(RegInteractivOcenka, on_delete=models.PROTECT, null=True, verbose_name="Оценка")
    type_price  = models.CharField("Тип", max_length=512, default='') 
    date        = models.DateTimeField('Дата', default=datetime.now, blank=True, null=True)
    name        = models.CharField("Наименование", max_length=512, default='') 
    amount      = models.IntegerField("Цена",  default=0, null=True, blank=True) 
    
    def __str__(self):
        return "{} / {} / {}".format(self.estimations, self.name, self.amount)

    class Meta:
        indexes = [
            models.Index(fields=['estimations'])
        ]
        db_table = 'regEstimationsCalculationDetail'
        verbose_name = "Суммы понижений расчетов интерктивной оценки"
        verbose_name_plural = "Суммы понижений расчетов интерктивной оценки"


class RegUnitMonthlyPlan(models.Model):
    unit = models.ForeignKey(RefUnit, on_delete=models.CASCADE, verbose_name="Подразделение")
    year = models.IntegerField("Год")
    month = models.IntegerField("Месяц")
    intake_plan = models.PositiveIntegerField("План по приему, шт.", default=0)
    sale_plan = models.PositiveIntegerField("План по продажам, шт.", default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'regUnitMonthlyPlan'
        verbose_name = "План подразделения на месяц"
        verbose_name_plural = "Планы подразделений на месяц"
        unique_together = ('unit', 'year', 'month')

    def __str__(self):
        return f"{self.unit} — {self.month:02d}.{self.year}"