from background_task import background
from django.shortcuts import render
import glob, os
from powerbi.models import Bi_logs, Bi_wash
from django.conf import settings
import requests
from refs.models import RefCarsOrganizationAuctionStatus, RefCarsOrganizationFiles, RefCarsOrganization, RefManufacturer, RefIb, RefCategoryProduct, RefGroupProduct, AutoruMark, AutoruModel, AutoruModification, AutoruComplectation, RefTypeKpp, RefTypeBody, RefTypeEngine, RefAvito, RefAvitoComplectation
from documents.models import DocCarShipment, DocRLK, DocRLKEvents, DocLO
from recognition.models import Check_settings_cvc, Records_voice_recorder_cvc_checklist_tematics, Records_voice_recorder_cvc_tematics, Records_voice_recorder_cvc_checklist, Records_voice_recorder, Records_voice_recorder_cvc, Records_voice_recorder_queue, Records_voice_recorder_cvc_checklist_kg, Records_questions
import platform
import datetime as DT
import ctypes
from django.db.models import Count, Sum, Max, Avg, F, OuterRef, Subquery, Sum, Q, Min
import json
from telephony.views import refresh_history_task
from requests.auth import HTTPBasicAuth
import time
from avtosalon.models import AvtohubGroupOptions, AvtohubOptions, AvtohubComplectations,  AvtohubModifications, Avtohub, AvtohubSite, AvtohubSiteInfo, Autoteka_signal, Autoteka_signal_region, Autoteka_signal_last_id 
from register.models import RegInteractivOcenkaRLK, SettingsMatrixAuction, RegInfoRefreshEstimationCarsExpress, RegEstimationRefCarsOrganizations, RegEstimationsSettings, RegInteractivOcenkaKorsStore, RegInteractivOcenkaKorsStoreSale, RegRegInteractivOcenkaFiles, TaskRegPrices, RegPrices, RegInfoRefreshCatalog, RegInteractivOcenkaEmailPush, RegInteractivOcenka
from openpyxl import Workbook, load_workbook
import re
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
import xml.etree.ElementTree as ETree
import requests
import tempfile
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.contenttypes.models import ContentType
from django.apps import apps
import time
from register.models import RegEstimationPodgotovka, RegEstimationMCU, RegEstimationSS, RegInteractivOcenka, RegSwapKors
from register.serializers import RegInteractivOcenkaSerializer, RegInteractivOcenkaSoglasovanieSerializer, RegInteractivOcenkaRLK, RegInteractivOcenkaRLKSerializer
from documents.serializers import DocRLKSerializer
from dateutil.relativedelta import relativedelta
from refs.serializers import RefCarsOrganizationSerializer, RefStoreSerializer
from datetime import datetime, date, time
import base64
from django.db.models import Min, Count, Sum, Max, Avg, F, OuterRef, Subquery, Sum, Q, Func, Value, CharField, IntegerField
from chats.models import ChatMessage, Chat, ChatSuccesDate

import asyncio
import websockets
from asgiref.sync import sync_to_async
import ssl
import pathlib

url_websocket_kors  = 'wss://ah.kors-group.com/'

url_hs_kors_auto        = 'http://a01srv1cka/zbusiness/hs/mb'
#url_hs_kors_auto       = 'http://a01srv1cka/zbusiness030724/hs/mb'
url_hs_alfa_auto        = 'http://k01srv1c10/ralfa01/hs/mb'
#url_hs_alfa_auto        = 'http://k01srv1c05/ralfa01eliseev/hs/mb'

url_my_kors_portal          = 'http://my.kors-group.com'
url_auction_kors_portal     = 'https://auction.kors-group.ru'
#url_auction_kors_portal     = 'http://k01-1c-prog01'

url_catalog_autoru  = 'https://auto-export.s3.yandex.net/auto/price-list/catalog/cars.xml'
url_catalog_avitoru = 'http://autoload.avito.ru/format/Autocatalog.xml'


login_cvc       = "kors-admin"
password_cvc    = "Admin2023KORS"


login_wash          = "791b8102-c3e7-4d83-801f-3d614f51ece9"
password_wash       = "eb746857-d61c-4641-afe8-33028f5f7449"
url_wash            = 'https://api.robodinamika.ru:8443/api/v1/'
limit_wash          = 100


avtoteka_client_id      = 'Xqr-oPLac4IvI5F_Hyn0'
avtoteka_client_secret  = 'E2rfzwSZmdkzySZYRi_DJdwfzEYehXU6yoEn-XpU'
avtoteka_url            = 'https://api.avito.ru/'


ssl_context         = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
localhost_pem       = 'D:\\kors_group\\portal\\portal\\apps\\task_manager\\certificate.pem'
ssl_context.load_verify_locations(localhost_pem)

def send_settings_unit(unit):
    """Отправить настройки подразделения в 1С. Возвращает dict с результатом."""
    from refs.unit_settings_1c import build_unit_settings_dc_payload

    result = {
        'ok': False,
        'status_code': None,
        'error': None,
        'unit_id': unit.pk,
        'unit_name': unit.name,
    }
    try:
        data_unit = build_unit_settings_dc_payload(unit)
        js_data = {
            'Type': 'settings_dc',
            'Settings': data_unit,
        }
        if unit.ib.alfa:
            response = requests.post(url_hs_alfa_auto, json=js_data, timeout=60)
        else:
            response = requests.post(url_hs_kors_auto, json=js_data, timeout=60)
        response = requests.post(url_hs_kors_auto, json=js_data, timeout=60)
        result['status_code'] = response.status_code
        if 200 <= response.status_code < 300:
            result['ok'] = True
        else:
            result['error'] = 'HTTP {}'.format(response.status_code)
    except requests.RequestException as exc:
        result['error'] = str(exc)
    except Exception as exc:
        result['error'] = str(exc)
    return result


def _indicator_kvp_code(indicator):
    if indicator is None:
        return ''
    for code in ('bu_wheels', 'osago', 'kasko', 'credit', 'gap', 'life'):
        if getattr(indicator, code, False):
            return code
    name = (indicator.name or '').strip()
    return name or str(indicator.pk)


def _agreement_cumulative_1c_url(agreement):
    unit = agreement.unit if agreement else None
    if unit and getattr(unit, 'ib_id', None) and unit.ib.alfa:
        return url_hs_alfa_auto
    return url_hs_kors_auto


def build_agreement_cumulative_1c_payload(row, delete=False):
    agreement = row.agreement
    return {
        'Type': 'agreement_cumulative',
        'Uin': (agreement.uin or '') if agreement else '',
        'Indicator': _indicator_kvp_code(row.indicatorKVP),
        'Amount': row.amount,
        'Author': row.author or '',
        'Comment': row.comment or '',
        'Delete': bool(delete),
    }


def send_agreement_cumulative_to_1c(row):
    """Отправить расчётные данные соглашения в 1С. При успехе выставляет send_1c."""
    from prices_car_bu.models import CalculatedCumulativeData

    result = {'ok': False, 'status_code': None, 'error': None}
    agreement = row.agreement
    if not agreement or not (agreement.uin or '').strip():
        result['error'] = 'Пустой uin соглашения'
        return result
    if not row.indicatorKVP_id:
        result['error'] = 'Не указан показатель'
        return result
    try:
        js_data = build_agreement_cumulative_1c_payload(row, delete=False)
        response = requests.post(
            _agreement_cumulative_1c_url(agreement),
            json=js_data,
            timeout=60,
        )
        result['status_code'] = response.status_code
        if 200 <= response.status_code < 300:
            result['ok'] = True
            CalculatedCumulativeData.objects.filter(pk=row.pk).update(send_1c=True)
        else:
            result['error'] = 'HTTP {}'.format(response.status_code)
    except requests.RequestException as exc:
        result['error'] = str(exc)
    except Exception as exc:
        result['error'] = str(exc)
    return result


def delete_agreement_cumulative_from_1c(row):
    """Удалить запись в 1С по ключу uin соглашения + показатель."""
    result = {'ok': False, 'status_code': None, 'error': None}
    agreement = row.agreement
    if not agreement or not (agreement.uin or '').strip():
        result['error'] = 'Пустой uin соглашения'
        return result
    if not row.indicatorKVP_id:
        result['error'] = 'Не указан показатель'
        return result
    try:
        js_data = build_agreement_cumulative_1c_payload(row, delete=True)
        response = requests.post(
            _agreement_cumulative_1c_url(agreement),
            json=js_data,
            timeout=60,
        )
        result['status_code'] = response.status_code
        if 200 <= response.status_code < 300:
            result['ok'] = True
        else:
            result['error'] = 'HTTP {}'.format(response.status_code)
    except requests.RequestException as exc:
        result['error'] = str(exc)
    except Exception as exc:
        result['error'] = str(exc)
    return result


#Отправка информации о матрице бцп аукциона
def send_matrix_auction():
    
    settings_matrix = SettingsMatrixAuction.objects.get(pk = 1)
    
    list_settings = list()
    cg_200 = {
        'ЦГ': '200',
        'БазоваяНаценка'        : settings_matrix.charge_bcp_200,
        'МинимальныйКМ'         : settings_matrix.min_km_200,
        'УмеренноеСнижение'     : settings_matrix.charge_km_stage_1_200,
        'СреднееСнижение'       : settings_matrix.charge_km_stage_2_200,
        'ЗначительноеСнижение'  : settings_matrix.charge_km_stage_3_200
    }
    list_settings.append(cg_200)
    cg_400 = {
        'ЦГ': '400',
        'БазоваяНаценка'        : settings_matrix.charge_bcp_400,
        'МинимальныйКМ'         : settings_matrix.min_km_400,
        'УмеренноеСнижение'     : settings_matrix.charge_km_stage_1_400,
        'СреднееСнижение'       : settings_matrix.charge_km_stage_2_400,
        'ЗначительноеСнижение'  : settings_matrix.charge_km_stage_3_400
    }
    list_settings.append(cg_400)
    cg_700 = {
        'ЦГ': '700',
        'БазоваяНаценка'        : settings_matrix.charge_bcp_700,
        'МинимальныйКМ'         : settings_matrix.min_km_700,
        'УмеренноеСнижение'     : settings_matrix.charge_km_stage_1_700,
        'СреднееСнижение'       : settings_matrix.charge_km_stage_2_700,
        'ЗначительноеСнижение'  : settings_matrix.charge_km_stage_3_700
    }
    list_settings.append(cg_700)
    cg_1200 = {
        'ЦГ': '1 200',
        'БазоваяНаценка'        : settings_matrix.charge_bcp_1200,
        'МинимальныйКМ'         : settings_matrix.min_km_1200,
        'УмеренноеСнижение'     : settings_matrix.charge_km_stage_1_1200,
        'СреднееСнижение'       : settings_matrix.charge_km_stage_2_1200,
        'ЗначительноеСнижение'  : settings_matrix.charge_km_stage_3_1200
    }
    list_settings.append(cg_1200)
    cg_2000 = {
        'ЦГ': '2 000',
        'БазоваяНаценка'        : settings_matrix.charge_bcp_2000,
        'МинимальныйКМ'         : settings_matrix.min_km_2000,
        'УмеренноеСнижение'     : settings_matrix.charge_km_stage_1_2000,
        'СреднееСнижение'       : settings_matrix.charge_km_stage_2_2000,
        'ЗначительноеСнижение'  : settings_matrix.charge_km_stage_3_2000
    }
    list_settings.append(cg_2000)
    cg_3000 = {
        'ЦГ': '3 000',
        'БазоваяНаценка'        : settings_matrix.charge_bcp_3000,
        'МинимальныйКМ'         : settings_matrix.min_km_3000,
        'УмеренноеСнижение'     : settings_matrix.charge_km_stage_1_3000,
        'СреднееСнижение'       : settings_matrix.charge_km_stage_2_3000,
        'ЗначительноеСнижение'  : settings_matrix.charge_km_stage_3_3000
    }
    list_settings.append(cg_3000)
    cg_5000 = {
        'ЦГ': '5 000',
        'БазоваяНаценка'        : settings_matrix.charge_bcp_5000,
        'МинимальныйКМ'         : settings_matrix.min_km_5000,
        'УмеренноеСнижение'     : settings_matrix.charge_km_stage_1_5000,
        'СреднееСнижение'       : settings_matrix.charge_km_stage_2_5000,
        'ЗначительноеСнижение'  : settings_matrix.charge_km_stage_3_5000
    }
    list_settings.append(cg_5000)
    cg_5001 = {
        'ЦГ': '5 000+',
        'БазоваяНаценка'        : settings_matrix.charge_bcp_5001,
        'МинимальныйКМ'         : settings_matrix.min_km_5001,
        'УмеренноеСнижение'     : settings_matrix.charge_km_stage_1_5001,
        'СреднееСнижение'       : settings_matrix.charge_km_stage_2_5001,
        'ЗначительноеСнижение'  : settings_matrix.charge_km_stage_3_5001
    }
    list_settings.append(cg_5001)

    js_data = {
        'Type'      : 'matrix',
        'Settings'  : list_settings 
    }
    
    response = requests.post(url_hs_kors_auto, json=js_data)
    
    response_alfa = requests.post(url_hs_alfa_auto, json=js_data)
    
    return response.status_code


def add_task():
    s=1
    #start_send_push_car(schedule = 60, repeat = 60, verbose_name = "Оповещения по автомобилям")
    #start_cumulative(schedule = 600, repeat = 86400, verbose_name = "Получение кумулятива альфа")
    #start_stock(schedule = 600, repeat = 86400, verbose_name = "Получение стока альфа")
    
    #start_refresh_signal(schedule = 60, repeat = 86400, verbose_name = "Получение данных сигнала")
    #start_refresh_estimation_cars_organization(schedule = 60, repeat = 86400, verbose_name = "Получение оценок по автомобилям на складе")
    #start_get_info_max(schedule = 60, repeat = 120, verbose_name = "Анализ склада / продаж Автохаб по интерактивной оценке")
    #start_kors_estimation_data(schedule = 60, repeat = 120, verbose_name = "Анализ склада / продаж корсаавто по интерактивной оценке")
    #start_refresh_avtoteka_vin(schedule = 60, repeat = 120, verbose_name = "Получение автотека по интерактивным оценкам")
    #start_swap_estimation(schedule = 60, repeat = 120, verbose_name = "Выгрузка информации в корсавто")
    #start_refresh_catalog(schedule = 60, repeat = 86400, verbose_name = "Обновление каталогов с сайтов объявлений")
    #start_refresh_price(schedule = 60, repeat = 600, verbose_name = "Обновление прайс - листов производителей")
    #start_refresh_autohub(schedule = 60, repeat = 86400, verbose_name = "Обновление данных Автохаб")
    #cvc_background(schedule = 60, repeat = 86400, verbose_name = "Отправка записей в CVC")
    #start_send_push_estimation(schedule = 60, repeat = 60, verbose_name = "Оповещения по интерактивным оценкам")

####
###
##
# Отправка сообщений в websocket с сервера (чат)
def send_message_socket(message):
    
    message_json = json.dumps(message)
    
    try:        
       
       asyncio.run(hello_ws_rlk_eco(text = message_json))        
    
    except:
        
        estimation_id = message['estimation_id']

        new_message = RegInteractivOcenkaEmailPush()
        
        new_message.estimation          = RegInteractivOcenka.objects.get(pk = estimation_id)
        new_message.user                = None
        new_message.email               = 'p.eliseev@kors-group.com'
        new_message.comment             = message_json
        new_message.message_websoket    = True
        
        new_message.save()

    
async def hello_ws_rlk_eco(text):
    async with websockets.connect(url_websocket_kors + 'ws/rlk_list_eco/', ssl = ssl_context) as websocket:
        await websocket.send(text)
        response = await websocket.recv()
        s= 1


####
###
##
# Обновление кумулятивной маржи из альфа 
@background(queue='cumulative')
def start_cumulative():
    from powerbi.views import cumulative_get_refresh
    date_start  = DT.datetime.now().replace(day=1, hour = 0, minute=1, second=1)
    date_end    = DT.datetime.now()
    cumulative_get_refresh(date_start, date_end)
        
####
###
##
# Обновление стока из альфа 
@background(queue='stock')
def start_stock():
    from powerbi.views import stock_get_refresh
    stock_get_refresh()


####
###
##
# Расчет данных интерактивной оценки 1С 
@background(queue='kors_estimation_data')
def start_kors_estimation_data():
    object_estimations_kors = RegInteractivOcenka.objects.filter(start_estimation__gt = DT.date(2025, 3, 1)).exclude(modification = None).filter(kors_start_store = None).order_by('-start_estimation') | RegInteractivOcenka.objects.filter(start_estimation__gt = DT.date(2025, 3, 1)).exclude(modification = None).filter(kors_start_store__lt = DT.date(2025, 3, 1)).order_by('-start_estimation')
    for object_estimation in object_estimations_kors:
        try:
            kors_estimation_data(object_estimation.pk)
        except:
            s = 1
        
def kors_estimation_data(id_estimation):
    
    save = True
    estimation                  = RegInteractivOcenka.objects.get(pk = id_estimation)
    estimation_settings         = RegEstimationsSettings.objects.all().last()
    
    kf                          = estimation_settings.max_kf_iznos
    kf_min                      = estimation.k_i - (estimation.k_i * kf / 100)
    kf_max                      = estimation.k_i + (estimation.k_i * kf / 100)
    
    k_sum = 0
    k_count = 0 
    k_zna = 0
    
    estimation.kors_count_sale  = 0
    estimation.kors_start_store = 0
    date_start                  = estimation.start_estimation - relativedelta(months=1)
    date_start                  = date_start.replace(day = 1, hour = 1 , minute=0)
    year_current                = DT.datetime.now().year  
    #Продажи
    list_sale_info = DocCarShipment.objects.filter(cars__modification_autoru = estimation.modification).exclude(cars__year = '').exclude(lo = None).filter(dataTime__gte = date_start).order_by('dataTime')
    RegInteractivOcenkaKorsStoreSale.objects.filter(estimation = estimation).delete()
    for doc_sale in list_sale_info:
        new_info                        = RegInteractivOcenkaKorsStoreSale()
        new_info.store                  = doc_sale.lo.store
        new_info.estimation             = estimation        
        new_info.vin                    = doc_sale.cars.vin
        new_info.doc                    = doc_sale
        new_info.year                   = int(doc_sale.cars.year)
        new_info.run                    = doc_sale.run
        new_info.modification           = doc_sale.cars.modification_autoru
        new_info.owners                 = doc_sale.owners
        new_info.price                  = doc_sale.amount 
        new_info.cost_price             = doc_sale.cost_price
        new_info.outlay                 = doc_sale.outlay
        new_info.discountAmount         = doc_sale.discountAmount
        new_info.discountAmountTorg     = doc_sale.discountAmountTorg
        new_info.discountAmountTradeIN  = doc_sale.discountAmountTradeIN
        new_info.days_in_stok           = (doc_sale.dataTime - doc_sale.lo.dataTime).days
        
        if new_info.price > new_info.outlay:            
            year_start  = estimation.year
            year_end    = estimation.year
            if new_info.year >=  year_start and new_info.year <=  year_end:
                new_info.active = True
        new_info.save()
        
        if new_info.k_i >= kf_min and new_info.k_i <= kf_max:
            if new_info.year >=  year_start and new_info.year <=  year_end:
                new_info.active = True
        else:
            new_info.active = False
        new_info.save()
        if new_info.active:
            k_count = k_count + 1
            if new_info.cost_price + new_info.outlay > new_info.price:
                k_sum = k_sum + new_info.price
            else:
                k_sum = k_sum + new_info.cost_price + new_info.outlay
            k_zna = k_zna + new_info.zna
    
    #Считаем среднее по продажам
    list_data_sale = RegInteractivOcenkaKorsStoreSale.objects.filter(estimation = estimation).filter(active = True)    
    
    cost_price_min = list_data_sale.aggregate(Min('cost_price')).get('cost_price__min')
    cost_price_max = list_data_sale.aggregate(Max('cost_price')).get('cost_price__max')
    
    price_min = list_data_sale.aggregate(Min('price')).get('price__min')
    price_max = list_data_sale.aggregate(Max('price')).get('price__max')
    if price_min == None:
        price_min = 0
    if price_max == None:
        price_max = 0
    diff_price_sale = (price_max - price_min) / 2

    count_car       = list_data_sale.count()
    cost_price      = list_data_sale.aggregate(Sum('cost_price')).get('cost_price__sum')
    outlay          = list_data_sale.aggregate(Sum('outlay')).get('outlay__sum')
    days_in_stok    = list_data_sale.aggregate(Sum('days_in_stok')).get('days_in_stok__sum')
    price           = list_data_sale.aggregate(Sum('price')).get('price__sum')
    run             = list_data_sale.aggregate(Sum('run')).get('run__sum')
    owners          = list_data_sale.aggregate(Sum('owners')).get('owners__sum')
    year            = list_data_sale.aggregate(Sum('year')).get('year__sum')
    if count_car > 0:
        days_in_stok_avg    = days_in_stok / count_car
        cost_price_avg      = cost_price / count_car
        outlay_avg          = outlay / count_car
        price_avg           = price / count_car
        run_avg             = run / count_car
        year_avg            = year / count_car
        owners_avg          = owners / count_car
        cum_avg             = (price - cost_price - outlay) / count_car 
    
        estimation.kors_price_market_min = price_min
        estimation.kors_price_market_max = price_max
        estimation.kors_sale_cost_price_min = cost_price_min
        estimation.kors_sale_cost_price_max = cost_price_max

        estimation.kors_sale_days_in_stok_avg    = days_in_stok_avg
        estimation.kors_sale_cost_price_avg      = cost_price_avg
        estimation.kors_sale_outlay_avg          = outlay_avg
        estimation.kors_sale_price_avg           = price_avg
        estimation.kors_sale_run_avg             = run_avg
        estimation.kors_sale_year_avg            = year_avg
        estimation.kors_sale_cum_avg             = cum_avg
        
    estimation.kors_start_sale          = DT.datetime.now()
    estimation.kors_count_sale          = count_car
    save = True
         

    #Склад
    list_store_info = RefCarsOrganization.objects.exclude(vin = estimation.vin).filter(modification_autoru = estimation.modification).filter(quantity = 1).order_by('days_in_stok')
    
    RegInteractivOcenkaKorsStore.objects.filter(estimation = estimation).delete()
    for car in list_store_info:
        new_info                        = RegInteractivOcenkaKorsStore()
        new_info.estimation             = estimation
        if len(car.lo_uin) > 0:
            lo = DocLO.objects.filter(uin__icontains = car.lo_uin).first()
            if lo != None:
                new_info.doc = lo
        new_info.store                  = car.store
        new_info.vin                    = car.vin
        new_info.year                   = car.year
        new_info.run                    = car.run
        new_info.modification           = car.modification_autoru
        new_info.modification           = car.modification_autoru
        new_info.owners                 = car.owners
        new_info.price                  = car.price
        new_info.cost_price             = car.cost_price
        new_info.outlay                 = car.outlay
        new_info.days_in_stok           = car.days_in_stok
        
        if new_info.price > new_info.outlay:
            year_start  = estimation.year
            year_end    = estimation.year
            if new_info.year >=  year_start and new_info.year <=  year_end:
                new_info.active = True

        new_info.save()
        
        if new_info.k_i >= kf_min and new_info.k_i <= kf_max:
            if new_info.year >=  year_start and new_info.year <=  year_end:
                new_info.active = True
        else:
            new_info.active = False
        new_info.save()

        if new_info.active:
            k_count = k_count + 1
            if new_info.cost_price + new_info.outlay > new_info.price:
                k_sum = k_sum + new_info.price
            else:
                k_sum = k_sum + new_info.cost_price + new_info.outlay
            k_zna = k_zna + new_info.zna
    
    #Считаем среднее по складу
    list_data = RegInteractivOcenkaKorsStore.objects.filter(estimation = estimation).filter(active = True)
    
    cost_price_min = list_data.aggregate(Min('cost_price')).get('cost_price__min')
    cost_price_max = list_data.aggregate(Max('cost_price')).get('cost_price__max')
    
    price_min = list_data.aggregate(Min('price')).get('price__min')
    price_max = list_data.aggregate(Max('price')).get('price__max')
    if price_min == None:
        price_min = 0
    if price_max == None:
        price_max = 0
    diff_price_store = price_max - price_min 

    count_car       = list_data.count()
    cost_price      = list_data.aggregate(Sum('cost_price')).get('cost_price__sum')
    outlay          = list_data.aggregate(Sum('outlay')).get('outlay__sum')
    days_in_stok    = list_data.aggregate(Sum('days_in_stok')).get('days_in_stok__sum')
    price           = list_data.aggregate(Sum('price')).get('price__sum')
    run             = list_data.aggregate(Sum('run')).get('run__sum')
    owners         = list_data.aggregate(Sum('owners')).get('owners__sum')
    year            = list_data.aggregate(Sum('year')).get('year__sum')
    
    if count_car > 0:
        days_in_stok_avg    = days_in_stok / count_car
        cost_price_avg      = cost_price / count_car
        outlay_avg          = outlay / count_car
        price_avg           = price / count_car
        run_avg             = run / count_car
        year_avg            = year / count_car
        owners_avg          = owners / count_car
        cum_avg             = (price - cost_price - outlay) / count_car 
        
        estimation.kors_price_min = price_min
        estimation.kors_price_max = price_max
        estimation.kors_cost_price_min = cost_price_min
        estimation.kors_cost_price_max = cost_price_max

        estimation.kors_days_in_stok_avg    = days_in_stok_avg
        estimation.kors_cost_price_avg      = cost_price_avg
        estimation.kors_outlay_avg          = outlay_avg
        estimation.kors_price_avg           = price_avg
        estimation.kors_run_avg             = run_avg
        estimation.kors_year_avg            = year_avg
        estimation.kors_cum_avg             = cum_avg
        
    estimation.kors_start_store              = DT.datetime.now()
    estimation.kors_count_store              = count_car
    save = True
    
    if k_count > 0:
        kors_price = round((k_sum / k_count + k_zna / k_count) / 2, 2)
    else:
        kors_price = 0

    estimation.kors_price = kors_price

    if save:
        estimation.save(update_fields=[
            'kors_count_sale',
            'kors_start_sale',
            'kors_start_store',
            'kors_count_store',
            'kors_price',
            'kors_price_market_min',
            'kors_price_market_max',
            'kors_sale_cost_price_min',
            'kors_sale_cost_price_max',
            'kors_sale_days_in_stok_avg',
            'kors_sale_cost_price_avg',
            'kors_sale_outlay_avg',
            'kors_sale_price_avg',
            'kors_sale_run_avg',
            'kors_sale_year_avg',
            'kors_sale_cum_avg',
            'kors_price_min',
            'kors_price_max',
            'kors_cost_price_min',
            'kors_cost_price_max',
            'kors_days_in_stok_avg',
            'kors_cost_price_avg',
            'kors_outlay_avg',
            'kors_price_avg',
            'kors_run_avg',
            'kors_year_avg',
            'kors_cum_avg',
        ])


####
###
##
# Обновление каталога модификаций автохаб для экспресс оценки
def refresh_auctohub_guide():
    
    refresh_group_options_autohub()
    refresh_options_autohub()
    refresh_complectations_autohub()
    refresh_autohub_modification()

def refresh_complectations_autohub():
    url_request = 'https://api.maxposter.ru/partners-api/directories/vehicle-complectations'  
    r   = requests.get(url_request)
    if r.status_code == 200:   
        data        = r.text
        s = 1 
        json_data   = json.loads(data)
        if json_data['status'] == 'success':
            data_response = json_data['data']
            vehicleComplectations = data_response['vehicleComplectations']
            for vehicleComplectation in vehicleComplectations:
                avtohub_complectation                         = AvtohubComplectations.objects.get_or_create(id_avtohub = vehicleComplectation['id'])[0]
                avtohub_complectation.id_avtohub              = vehicleComplectation['id']
                avtohub_complectation.brandId                 = vehicleComplectation['brandId']
                avtohub_complectation.modelId                 = vehicleComplectation['modelId']
                avtohub_complectation.generationId            = vehicleComplectation['generationId']
                avtohub_complectation.bodyConfigurationId     = vehicleComplectation['bodyConfigurationId']
                avtohub_complectation.modificationId          = vehicleComplectation['modificationId']
                avtohub_complectation.autoruId                = vehicleComplectation['autoruId']
                avtohub_complectation.isActive                = vehicleComplectation['isActive']
                avtohub_complectation.name                    = vehicleComplectation['name']
                equintments = vehicleComplectation['equipment']
                avtohub_complectation.equipment.clear()
                for equintment in equintments: 
                    try:
                        avtohub_complectation.equipment.add(AvtohubOptions.objects.get(id_avtohub = equintment))
                    except:
                        s = 1
                avtohub_complectation.save()

def refresh_options_autohub():
    url_request = 'https://api.maxposter.ru/partners-api/directories/vehicle-equipment'  
    r   = requests.get(url_request)
    if r.status_code == 200:   
        data        = r.text
        s = 1 
        json_data   = json.loads(data)
        if json_data['status'] == 'success':
            data_response = json_data['data']
            vehicleEquipments = data_response['vehicleEquipment']
            for vehicleEquipment in vehicleEquipments:
                avtohub_options               = AvtohubOptions.objects.get_or_create(id_avtohub = vehicleEquipment['id'])[0]
                avtohub_options.id_avtohub    = vehicleEquipment['id']
                avtohub_options.name          = vehicleEquipment['name']
                avtohub_options.sortOrder     = vehicleEquipment['sortOrder']
                try:
                    avtohub_options.groupId   = AvtohubGroupOptions.objects.get(id_avtohub = vehicleEquipment['groupId'])
                except:
                    s == 1
                avtohub_options.include         = vehicleEquipment['include']
                avtohub_options.exclude         = vehicleEquipment['exclude']
                avtohub_options.keyEquipment    = vehicleEquipment['keyEquipment']
                avtohub_options.save()

def refresh_group_options_autohub():
    url_request = 'https://api.maxposter.ru/partners-api/directories/vehicle-equipment-groups'  
    r   = requests.get(url_request)
    if r.status_code == 200:   
        data        = r.text
        s = 1 
        json_data   = json.loads(data)
        if json_data['status'] == 'success':
            data_response = json_data['data']
            vehicleEquipmentGroups = data_response['vehicleEquipmentGroups']
            for vehicleEquipmentGroup in vehicleEquipmentGroups:
                avtohub_group_options               = AvtohubGroupOptions.objects.get_or_create(id_avtohub = vehicleEquipmentGroup['id'])[0]
                avtohub_group_options.id_avtohub    = vehicleEquipmentGroup['id']
                avtohub_group_options.name          = vehicleEquipmentGroup['name']
                avtohub_group_options.sortOrder     = vehicleEquipmentGroup['sortOrder']
                avtohub_group_options.save()
                
def refresh_autohub_modification():
    url_request = 'https://api.maxposter.ru/partners-api/directories/vehicle-modifications'  
    r   = requests.get(url_request)
    if r.status_code == 200:   
        data        = r.text
        s = 1 
        json_data   = json.loads(data)
        if json_data['status'] == 'success':
            data_modification = json_data['data']
            vehicleModifications = data_modification['vehicleModifications']
            for vehicleModification in vehicleModifications:
                avtohub_modifications = AvtohubModifications.objects.get_or_create(id_avtohub = vehicleModification['id'])[0]
                avtohub_modifications.brandId               = vehicleModification['brandId']
                avtohub_modifications.modelId               = vehicleModification['modelId']
                avtohub_modifications.generationId          = vehicleModification['generationId']
                avtohub_modifications.bodyConfigurationId   = vehicleModification['bodyConfigurationId']
                avtohub_modifications.name              = vehicleModification['name']
                avtohub_modifications.autoruId          = vehicleModification['autoruId'] if vehicleModification['autoruId'] != None else 0
                avtohub_modifications.yearFrom          = vehicleModification['yearFrom']
                avtohub_modifications.yearTo            = vehicleModification['yearTo']
                avtohub_modifications.bodyType          = vehicleModification['bodyType']
                avtohub_modifications.bodyDoorCount     = vehicleModification['bodyDoorCount']
                avtohub_modifications.engineType        = vehicleModification['engineType']
                avtohub_modifications.engineVolume      = vehicleModification['engineVolume']
                avtohub_modifications.enginePower       = vehicleModification['enginePower']
                avtohub_modifications.driveType         = vehicleModification['driveType']
                avtohub_modifications.gearboxType       = vehicleModification['gearboxType']
                avtohub_modifications.gearboxGearCount  = vehicleModification['gearboxGearCount']
                avtohub_modifications.isActive          = vehicleModification['isActive']
                avtohub_modifications.save()
                

####
###
##
# Экспресс оценка автохаб - макспостерс
@background(queue='get_info_max')
def start_get_info_max():

    object_estimations_report_autohub = RegInteractivOcenka.objects.exclude(year = 0).filter(start_estimation__gt = DT.date(2025, 10, 1)).exclude(modification = None).exclude(page_remote = None).exclude(page_remote__price_sale = 0).exclude(page_remote__run = 0).filter(page_remote__hub_avg = 0).order_by('-start_estimation').values('pk')
    for object_estimation_autohub in object_estimations_report_autohub:
        try:
            interctiv_rlk = RegInteractivOcenkaRLK.objects.filter(estimation__pk = object_estimation_autohub['pk']).first()
            get_info_max_remote(interctiv_rlk, object_estimation_autohub['pk'])
        except:
            s = 1    

    object_estimations_report_autohub = RegInteractivOcenka.objects.exclude(year = 0).exclude(page_soglasovanie = None).exclude(page_salon__run = None).exclude(end_estimation = None).filter(start_estimation__gt = DT.date(2025, 10, 1)).exclude(modification = None).filter(hub_start = None).order_by('-start_estimation').values('pk')
    for object_estimation_autohub in object_estimations_report_autohub:
        try:
            interctiv_rlk = RegInteractivOcenkaRLK.objects.filter(estimation__pk = object_estimation_autohub['pk']).first()
            get_info_max(interctiv_rlk, object_estimation_autohub['pk'])
        except:
            s = 1    

def get_info_max_remote(interctiv_rlk, estimation_id):
    
    estimation  = RegInteractivOcenka.objects.get(pk = estimation_id)
    
    username        = "korsgroup@maxposter.ru"
    password        = "pJ%[QwwqH,YxP9J-"
    url             = "api.maxposter.ru"
    URL_TEMPLATE    = "https://api.maxposter.ru/partners-api/express"
    token           = 'a29yc2dyb3VwQG1heHBvc3Rlci5ydTpwSiVbUXd3cUgsWXhQOUot'
    headers         = { 'Authorization' : 'Basic %s' % token }

    year_curent = DT.datetime.now().year
    if year_curent - estimation.year > 5:
        year_start  = estimation.year - 1   
        year_end    = estimation.year + 1
    else:
        year_start  = estimation.year   
        year_end    = estimation.year

    try:
        
        avtohub_modification = None
        count_avtohub_modification = AvtohubModifications.objects.filter(autoruId = estimation.modification.idSiteTech).count()
        if count_avtohub_modification == 1:
            avtohub_modification = AvtohubModifications.objects.filter(autoruId = estimation.modification.idSiteTech)[0]    
            if year_start < avtohub_modification.yearFrom:
                year_start = avtohub_modification.yearFrom
            if year_end > avtohub_modification.yearTo:
                year_end = avtohub_modification.yearTo

        if avtohub_modification != None:
            brand = {
                'id'    : avtohub_modification.brandId,
                'name'  : estimation.modification.model.mark.name.strip()
            }
            model = {
                'id'    : avtohub_modification.modelId,
                'name'  : get_name_re(estimation.modification.model.name, 0)
            }
            generation = {
                'id'    : avtohub_modification.generationId,
                'name'  : get_name_re(estimation.modification.model.name, 1)
            }
            modification = {
                'id'    : avtohub_modification.id_avtohub,
                'name'  : estimation.modification.name
            }
        else:
            brand = {
                'id'    : None,
                'name'  : estimation.modification.model.mark.name.strip()
            }
            model = {
                'id'    : None,
                'name'  : get_name_re(estimation.modification.model.name, 0)
            }
            generation = {
                'id'    : None,
                'name'  : get_name_re(estimation.modification.model.name, 1)
            }
            modification = {
                'id'    : None,
                'name'  : estimation.modification.name
            }

        marketFilter = {
            'brand'         : brand,
            'model'         : model,
            'generation'    : generation,
            'modification'  : modification,
            'geoDistance'   : 500,
            'yearFrom'      : year_start,
            "yearTo"        : year_end
        }
        
        salesFromDate = estimation.start_estimation - relativedelta(months=2)
        salesFromDate = salesFromDate.replace(day=1, hour=1)

        filter = {
            'brand'         : brand,
            'model'         : model,
            'generation'    : generation,
            'modification'  : modification,
            'geoDistance'   : 500,
            'useAutoFilter' : False,
            'yearFrom'      : year_start,
            "yearTo"        : year_end,
            'salesFromDate' : salesFromDate.strftime('%Y-%m-%d')
        }

        vehicle = {
            'year'      : estimation.year,
            'mileage'   : interctiv_rlk.estimation.page_remote.run,
            'rubPrice'  : interctiv_rlk.estimation.page_remote.price_sale
        }
        
        data_info = {
            'dealerId'          : 2107,
            'marketFilter'      : marketFilter,
            'filter'            : filter,
            'vehicle'           : vehicle 
        }
        
        r   = requests.post(URL_TEMPLATE, auth=HTTPBasicAuth(username, password), json=data_info)
        if r.status_code == 200:
            
            estimation.hub_data = r.text
            js_data = json.loads(r.text)
            
            data = js_data['data']
            if len(data) == 1:
                data = data[0]  

            analyticsByActualSales              = data['analyticsByActualSales']
            page_remote                         = estimation.page_remote 
            page_remote.hub_avg                 = analyticsByActualSales['avgPriceWithCorrection']
            page_remote.save()

    except:
        s = 1

def get_info_max_znak(interactiv_rlk, estimation_id):
    
    estimation  = RegInteractivOcenka.objects.get(pk = estimation_id)
    
    if estimation.complectation != None:
        username        = "korsgroup@maxposter.ru"
        password        = "pJ%[QwwqH,YxP9J-"
        url             = "api.maxposter.ru"
        URL_TEMPLATE    = "https://api.maxposter.ru/partners-api/express"
        token           = 'a29yc2dyb3VwQG1heHBvc3Rlci5ydTpwSiVbUXd3cUgsWXhQOUot'
        headers         = { 'Authorization' : 'Basic %s' % token }

        year_curent = DT.datetime.now().year
        if year_curent - estimation.year > 5:
            year_start  = estimation.year - 1   
            year_end    = estimation.year + 1
        else:
            year_start  = estimation.year - 1   
            year_end    = estimation.year 

        try:
            avtohub_modification    = None
            count_avtohub_modification = AvtohubModifications.objects.filter(autoruId = estimation.modification.idSiteTech).count()
            if count_avtohub_modification == 1:
                avtohub_modification    = AvtohubModifications.objects.filter(autoruId = estimation.modification.idSiteTech)[0]    
                autohub_complectation   = AvtohubComplectations.objects.filter(modificationId = avtohub_modification.id_avtohub).filter(autoruId = estimation.complectation.idSite).count()
                if autohub_complectation == 1:
                    autohub_complectation   = AvtohubComplectations.objects.filter(modificationId = avtohub_modification.id_avtohub).filter(autoruId = estimation.complectation.idSite)[0]
                    if year_start < avtohub_modification.yearFrom:
                        year_start = avtohub_modification.yearFrom
                    if year_end > avtohub_modification.yearTo:
                        year_end = avtohub_modification.yearTo
                        
            if avtohub_modification != None:
                brand = {
                    'id'    : avtohub_modification.brandId,
                    'name'  : estimation.modification.model.mark.name.strip()
                }
                model = {
                    'id'    : avtohub_modification.modelId,
                    'name'  : ''
                }
                generation = {
                    'id'    : avtohub_modification.generationId,
                    'name'  : ''
                }
                modification = {
                    'id'    : avtohub_modification.id_avtohub,
                    'name'  : ''
                }
                complectation = {
                    'id'    : autohub_complectation.id_avtohub,
                    'name'  : ''
                }
            else:
                brand = {
                    'id'    : None,
                    'name'  : estimation.modification.model.mark.name.strip()
                }
                model = {
                    'id'    : None,
                    'name'  : get_name_re(estimation.modification.model.name, 0)
                }
                generation = {
                    'id'    : None,
                    'name'  : get_name_re(estimation.modification.model.name, 1)
                }
                modification = {
                    'id'    : None,
                    'name'  : estimation.modification.name
                }
                complectation = {
                    'id'    : estimation.complectation.name,
                    'name'  : ''
                }
            marketFilter = {
                'brand'         : brand,
                'model'         : model,
                'generation'    : generation,
                'modification'  : modification,
                'complectation' : complectation,
                'geoDistance'   : 500,
                'yearFrom'      : year_start,
                "yearTo"        : year_end
            }
            
            salesFromDate = estimation.start_estimation - relativedelta(months=2)
            salesFromDate = salesFromDate.replace(day=1, hour=1)

            filter = {
                'brand'         : brand,
                'model'         : model,
                'generation'    : generation,
                'modification'  : modification,
                'complectation' : complectation,
                'geoDistance'   : 500,
                'useAutoFilter' : True,
                'yearFrom'      : year_start,
                "yearTo"        : year_end,
                'salesFromDate' : salesFromDate.strftime('%Y-%m-%d')
            }

            if estimation.page_salon != None:
                vehicle = {
                    'year'      : estimation.year,
                    'mileage'   : estimation.page_salon.run,
                    'rubPrice'  : interactiv_rlk.page_soglasovanie.price_sale
                }
            else:
                vehicle = {
                    'year'      : estimation.year,
                    'mileage'   : estimation.page_remote.run,
                    'rubPrice'  : estimation.page_remote.price_sale
                }
            
            data_info = {
                'dealerId'          : 2107,
                'marketFilter'      : marketFilter,
                'filter'            : filter,
                'vehicle'           : vehicle 
            }
            
            r   = requests.post(URL_TEMPLATE, auth=HTTPBasicAuth(username, password), json=data_info)
            if r.status_code == 200:
                
                estimation.hub_data = r.text
                js_data = json.loads(r.text)
                
                data = js_data['data']
                if len(data) == 1:
                    data = data[0]    

                analyticsByCompletedSales               = data['analyticsByCompletedSales']
                estimation.hub_sale_avg_k                 = analyticsByCompletedSales['avgPriceWithCorrection']
                estimation.hub_sale_days_in_stok_avg_k    = analyticsByCompletedSales['avgDaysInSale']
                estimation.hub_sale_run_avg_k             = analyticsByCompletedSales['avgMileage']
                estimation.hub_sale_year_avg_k            = analyticsByCompletedSales['avgYear']
                estimation.hub_sale_price_max_k           = analyticsByCompletedSales['maxPriceWithCorrection']
                estimation.hub_sale_price_min_k           = analyticsByCompletedSales['minPriceWithCorrection']
                estimation.hub_sale_pricePosition_k       = analyticsByCompletedSales['pricePosition']
                estimation.hub_sale_vRating_k             = analyticsByCompletedSales['vRating']
                estimation.hub_sale_total_k               = analyticsByCompletedSales['usefulSalesTotal']
            
                
                analyticsByActualSales                  = data['analyticsByActualSales']
                estimation.hub_avg_k                    = analyticsByActualSales['avgPriceWithCorrection']
                estimation.hub_days_in_stok_avg_k       = analyticsByActualSales['avgDaysInSale']
                estimation.hub_run_avg_k                = analyticsByActualSales['avgMileage']
                estimation.hub_year_avg_k               = analyticsByActualSales['avgYear']
                estimation.hub_price_max_k              = analyticsByActualSales['maxPriceWithCorrection']
                estimation.hub_price_min_k              = analyticsByActualSales['minPriceWithCorrection']
                estimation.hub_pricePosition_k          = analyticsByActualSales['pricePosition']
                estimation.hub_vRating_k                = analyticsByActualSales['vRating']
                estimation.hub_total_k                  = analyticsByActualSales['usefulSalesTotal']
                estimation.hub_start_k                  = DT.datetime.now()
                estimation.save(
                    update_fields=[
                        'hub_sale_avg_k',
                        'hub_sale_days_in_stok_avg_k',
                        'hub_sale_run_avg_k',
                        'hub_sale_year_avg_k',
                        'hub_sale_price_max_k',
                        'hub_sale_price_min_k',
                        'hub_sale_pricePosition_k',
                        'hub_sale_vRating_k',
                        'hub_sale_total_k',
                        'hub_avg_k',
                        'hub_days_in_stok_avg_k',
                        'hub_run_avg_k',
                        'hub_year_avg_k',
                        'hub_price_max_k',
                        'hub_price_min_k',
                        'hub_pricePosition_k',
                        'hub_vRating_k',
                        'hub_total_k',
                        'hub_start_k',
                        ])

            else:
                text = r.text
                estimation.hub_start_k  = DT.datetime.now()
                estimation.hub_data_2   = r.text
                estimation.save(update_fields=[
                        'hub_data_2',
                        'hub_start_k',
                        ])

        except:
            s = 1

def refresh_cd_zna(cd):

    estimation = cd.estimation

    username        = "korsgroup@maxposter.ru"
    password        = "pJ%[QwwqH,YxP9J-"
    url             = "api.maxposter.ru"
    URL_TEMPLATE    = "https://api.maxposter.ru/partners-api/express"
    token           = 'a29yc2dyb3VwQG1heHBvc3Rlci5ydTpwSiVbUXd3cUgsWXhQOUot'
    headers         = { 'Authorization' : 'Basic %s' % token }

    year_curent = DT.datetime.now().year
    if year_curent - estimation.year > 5:
        year_start  = estimation.year - 1   
        year_end    = estimation.year + 1
    else:
        year_start  = estimation.year - 1   
        year_end    = estimation.year 

    try:
        
        avtohub_modification = None
        count_avtohub_modification = AvtohubModifications.objects.filter(autoruId = estimation.modification.idSiteTech).count()
        if count_avtohub_modification == 1:
            avtohub_modification = AvtohubModifications.objects.filter(autoruId = estimation.modification.idSiteTech)[0]    
            if year_start < avtohub_modification.yearFrom:
                year_start = avtohub_modification.yearFrom
            if year_end > avtohub_modification.yearTo:
                year_end = avtohub_modification.yearTo
                    
        if avtohub_modification != None:
            brand = {
                'id'    : avtohub_modification.brandId,
                'name'  : estimation.modification.model.mark.name.strip()
            }
            model = {
                'id'    : avtohub_modification.modelId,
                'name'  : ''
            }
            generation = {
                'id'    : avtohub_modification.generationId,
                'name'  : ''
            }
            modification = {
                'id'    : avtohub_modification.id_avtohub,
                'name'  : ''
            }
        else:
            brand = {
                'id'    : None,
                'name'  : estimation.modification.model.mark.name.strip()
            }
            model = {
                'id'    : None,
                'name'  : get_name_re(estimation.modification.model.name, 0)
            }
            generation = {
                'id'    : None,
                'name'  : get_name_re(estimation.modification.model.name, 1)
            }
            modification = {
                'id'    : None,
                'name'  : estimation.modification.name
            }
        
        marketFilter = {
            'brand'         : brand,
            'model'         : model,
            'generation'    : generation,
            'modification'  : modification,
            'geoDistance'   : 500,
            'yearFrom'      : year_start,
            "yearTo"        : year_end
        }
        
        salesFromDate = estimation.start_estimation - relativedelta(months=2)
        salesFromDate = salesFromDate.replace(day=1, hour=1)

        filter = {
            'brand'         : brand,
            'model'         : model,
            'generation'    : generation,
            'modification'  : modification,
            'geoDistance'   : 500,
            'useAutoFilter' : False,
            'yearFrom'      : year_start,
            "yearTo"        : year_end,
            'salesFromDate' : salesFromDate.strftime('%Y-%m-%d')
        }

        if estimation.page_salon != None:
            vehicle = {
                'year'      : estimation.year,
                'mileage'   : estimation.page_salon.run,
                'rubPrice'  : cd.price_auto_2
            }
        else:
            vehicle = {
                'year'      : estimation.year,
                'mileage'   : estimation.page_remote.run,
                'rubPrice'  : estimation.page_remote.price_sale
            }
        
        data_info = {
            'dealerId'          : 2107,
            'marketFilter'      : marketFilter,
            'filter'            : filter,
            'vehicle'           : vehicle 
        }
        
        r   = requests.post(URL_TEMPLATE, auth=HTTPBasicAuth(username, password), json=data_info)
        if r.status_code == 200:
            
            js_data = json.loads(r.text)
            
            data = js_data['data']
            if len(data) == 1:
                data = data[0]    

            analyticsByActualSales          = data['analyticsByActualSales']
            cd.hub_avg                      = analyticsByActualSales['avgPriceWithCorrection']
            cd.hub_days_in_stok_avg         = analyticsByActualSales['avgDaysInSale']
            cd.hub_start                    = DT.datetime.now()
            cd.save()

        else:
            text = r.text
            
    except:
        s = 1

def get_info_max(interactiv_rlk, estimation_id):
    
    estimation  = RegInteractivOcenka.objects.get(pk = estimation_id)
    
    username        = "korsgroup@maxposter.ru"
    password        = "pJ%[QwwqH,YxP9J-"
    url             = "api.maxposter.ru"
    URL_TEMPLATE    = "https://api.maxposter.ru/partners-api/express"
    token           = 'a29yc2dyb3VwQG1heHBvc3Rlci5ydTpwSiVbUXd3cUgsWXhQOUot'
    headers         = { 'Authorization' : 'Basic %s' % token }

    year_curent = DT.datetime.now().year
    if year_curent - estimation.year > 5:
        year_start  = estimation.year - 1   
        year_end    = estimation.year + 1
    else:
        year_start  = estimation.year - 1   
        year_end    = estimation.year 

    try:
        
        avtohub_modification = None
        count_avtohub_modification = AvtohubModifications.objects.filter(autoruId = estimation.modification.idSiteTech).count()
        if count_avtohub_modification == 1:
            avtohub_modification = AvtohubModifications.objects.filter(autoruId = estimation.modification.idSiteTech)[0]    
            if year_start < avtohub_modification.yearFrom:
                year_start = avtohub_modification.yearFrom
            if year_end > avtohub_modification.yearTo:
                year_end = avtohub_modification.yearTo
                    
        if avtohub_modification != None:
            brand = {
                'id'    : avtohub_modification.brandId,
                'name'  : estimation.modification.model.mark.name.strip()
            }
            model = {
                'id'    : avtohub_modification.modelId,
                'name'  : ''
            }
            generation = {
                'id'    : avtohub_modification.generationId,
                'name'  : ''
            }
            modification = {
                'id'    : avtohub_modification.id_avtohub,
                'name'  : ''
            }
        else:
            brand = {
                'id'    : None,
                'name'  : estimation.modification.model.mark.name.strip()
            }
            model = {
                'id'    : None,
                'name'  : get_name_re(estimation.modification.model.name, 0)
            }
            generation = {
                'id'    : None,
                'name'  : get_name_re(estimation.modification.model.name, 1)
            }
            modification = {
                'id'    : None,
                'name'  : estimation.modification.name
            }
        
        marketFilter = {
            'brand'         : brand,
            'model'         : model,
            'generation'    : generation,
            'modification'  : modification,
            'geoDistance'   : 500,
            'yearFrom'      : year_start,
            "yearTo"        : year_end
        }
        
        # imvFilter = {
        #     'brand'         : brand,
        #     'model'         : model,
        #     'generation'    : generation,
        #     'modification'  : modification
        # }
        salesFromDate = estimation.start_estimation - relativedelta(months=2)
        salesFromDate = salesFromDate.replace(day=1, hour=1)

        filter = {
            'brand'         : brand,
            'model'         : model,
            'generation'    : generation,
            'modification'  : modification,
            'geoDistance'   : 500,
            'useAutoFilter' : False,
            'yearFrom'      : year_start,
            "yearTo"        : year_end,
            'salesFromDate' : salesFromDate.strftime('%Y-%m-%d')
        }

        if estimation.page_salon != None:
            vehicle = {
                'year'      : estimation.year,
                'mileage'   : estimation.page_salon.run,
                'rubPrice'  : interactiv_rlk.page_soglasovanie.price_sale
            }
        else:
            vehicle = {
                'year'      : estimation.year,
                'mileage'   : estimation.page_remote.run,
                'rubPrice'  : estimation.page_remote.price_sale
            }
        
        data_info = {
            'dealerId'          : 2107,
            'marketFilter'      : marketFilter,
            'filter'            : filter,
            'vehicle'           : vehicle 
        }
        
        r   = requests.post(URL_TEMPLATE, auth=HTTPBasicAuth(username, password), json=data_info)
        if r.status_code == 200:
            
            estimation.hub_data = r.text
            js_data = json.loads(r.text)
            
            data = js_data['data']
            if len(data) == 1:
                data = data[0]    

            analyticsByCompletedSales               = data['analyticsByCompletedSales']
            estimation.hub_sale_avg                 = analyticsByCompletedSales['avgPriceWithCorrection']
            estimation.hub_sale_days_in_stok_avg    = analyticsByCompletedSales['avgDaysInSale']
            estimation.hub_sale_run_avg             = analyticsByCompletedSales['avgMileage']
            estimation.hub_sale_year_avg            = analyticsByCompletedSales['avgYear']
            estimation.hub_sale_price_max           = analyticsByCompletedSales['maxPriceWithCorrection']
            estimation.hub_sale_price_min           = analyticsByCompletedSales['minPriceWithCorrection']
            estimation.hub_sale_pricePosition       = analyticsByCompletedSales['pricePosition']
            estimation.hub_sale_vRating             = analyticsByCompletedSales['vRating']
            estimation.hub_sale_total               = analyticsByCompletedSales['usefulSalesTotal']
        
            
            analyticsByActualSales              = data['analyticsByActualSales']
            estimation.hub_avg                  = analyticsByActualSales['avgPriceWithCorrection']
            estimation.hub_days_in_stok_avg     = analyticsByActualSales['avgDaysInSale']
            estimation.hub_run_avg              = analyticsByActualSales['avgMileage']
            estimation.hub_year_avg             = analyticsByActualSales['avgYear']
            estimation.hub_price_max            = analyticsByActualSales['maxPriceWithCorrection']
            estimation.hub_price_min            = analyticsByActualSales['minPriceWithCorrection']
            estimation.hub_pricePosition        = analyticsByActualSales['pricePosition']
            estimation.hub_vRating              = analyticsByActualSales['vRating']
            estimation.hub_total                = analyticsByActualSales['usefulSalesTotal']
            estimation.hub_start = DT.datetime.now()
            estimation.save()
        else:
            text = r.text
            estimation.hub_start    = DT.datetime.now()
            estimation.hub_data_2   = r.text
            estimation.save()

    except:
        s = 1

def get_name_re(name, ind):

    name_new = name
    #if name_new.find('(') > 0:
    #    name_new = name_new.split('(')[0]
    
    if name_new.find(',') > 0:
        if ind == 0:
            name_new = name_new.split(',')[ind]
        else:
            name_new = name_new.replace(name_new.split(',')[0]+',', '')
    elif ind > 0:
        return ''
    return name_new.replace('_', ' ').strip()



####
###
##
# Функции отправки/обновления данных портала аукциона
def refresh_list_auction_status():
    lots_list = list()
    r   = requests.get(url_auction_kors_portal + '/api/swap/get/', auth=('Admin_auction', 'Audi80b4'))
    if r.status_code == 200:
        data = json.loads(r.text)
        swap_list = data['swap_list']
        for swap in swap_list:
            lot_uin = swap['lot_uin']['search']
            if not lot_uin in lots_list:
                lots_list.append(lot_uin)
    
    for lot in lots_list:
        from refs.models import Auction
        if lot != '':
            auction = Auction.objects.get(uid = lot)
            refresh_auction(auction)

def datetime_handler(obj):
    """Fallback при json.dumps: даты лота без T (как date_start)."""
    if isinstance(obj, (datetime, date)):
        return _format_auction_datetime(obj, 'space')
    if isinstance(obj, time):
        return obj.replace(microsecond=0).strftime('%H:%M:%S')
    return str(obj)


def _normalize_auction_dt(value):
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        dt = value
        try:
            from django.utils import timezone as dj_timezone
            if dj_timezone.is_aware(dt):
                dt = dj_timezone.localtime(dt)
        except Exception:
            pass
        return dt.replace(tzinfo=None)
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime.combine(value, time.min)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        text = text.split('+')[0].strip()
        if text.endswith('Z'):
            text = text[:-1]
        for fmt in (
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
        ):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None
    return None


def _format_auction_datetime(value, fmt='space'):
    """
    Форматы под парсинг на портале аукциона:
    - space:       %Y-%m-%d %H:%M:%S       (date_start, date_end)
    - iso_t:       %Y-%m-%dT%H:%M:%S       (lo_link_date)
    - iso_t_micro: %Y-%m-%dT%H:%M:%S.%f    (date_create)
    """
    dt = _normalize_auction_dt(value)
    if dt is None:
        return None
    if fmt == 'iso_t':
        return dt.replace(microsecond=0).strftime('%Y-%m-%dT%H:%M:%S')
    if fmt == 'iso_t_micro':
        return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')
    return dt.replace(microsecond=0).strftime('%Y-%m-%d %H:%M:%S')


_AUCTION_CAR_DATE_FORMATS = {
    'lo_link_date': 'iso_t',
    'date_create': 'iso_t_micro',
    'date_refresh': 'iso_t',
    'min_km_date': 'iso_t',
    'date_report': 'iso_t',
    'date_reserve': 'iso_t',
}

_AUCTION_CAR_FK_FIELDS = (
    'organization', 'unit', 'store', 'status', 'type_sale', 'type_reception',
    'evaluation', 'modification_avito', 'complectation_avito', 'modification_autoru',
    'complectation_autoru', 'type_body', 'type_engine', 'type_gear', 'type_drive',
    'stage_price', 'group_price', 'rating', 'status_ransom', 'status_availability',
    'min_km_user', 'lo',
)


def _safe_auction_fk_dict(value, default_name=''):
    if value is None:
        return {'id': None, 'name': default_name}
    if isinstance(value, dict):
        safe = dict(value)
        if safe.get('name') in (None, ''):
            safe['name'] = default_name
        return safe
    return {'id': None, 'name': default_name}


def _sanitize_car_payload_for_auction(car_data):
    """Подготовка car_info для process_lot_cars на портале аукциона."""
    if not isinstance(car_data, dict):
        return car_data
    car_data = dict(car_data)
    for field, fmt in _AUCTION_CAR_DATE_FORMATS.items():
        if field in car_data:
            car_data[field] = _format_auction_datetime(car_data.get(field), fmt)
    for field in _AUCTION_CAR_FK_FIELDS:
        if field not in car_data:
            continue
        default_name = 'Аукцион' if field == 'type_sale' else ''
        car_data[field] = _safe_auction_fk_dict(car_data.get(field), default_name=default_name)
    return car_data

def _loads_auction_files_json(value):
    if not value:
        return []
    try:
        data = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []

def refresh_auction(auction):
    
    r   = requests.get(url_auction_kors_portal + '/api/get_auction/' + str(auction.uid)  +'/', auth=('Admin_auction', 'Audi80b4'))
    if r.status_code == 200:
        data = json.loads(r.text)
        lot_info = data['lot_info']
        if lot_info != None:
            auction.status              = get_status(lot_info['status'])
            auction.rejection_reason    = lot_info['rejection_reason']
            if 'pk_auction' in lot_info:
                auction.pk_auction = str(lot_info['pk_auction'])
            if lot_info['profile_winner'] != None:
                winner = lot_info['profile_winner']
                auction.winner_name = winner['name']
                auction.winner_phone = winner['phone']
                auction.winner_email = winner['email']
                auction.winner_price = lot_info['winning_bid']

            auction.save()

def get_status(status_name):
    status, created = RefCarsOrganizationAuctionStatus.objects.filter(name = status_name).get_or_create(name = status_name)
    return status

def send_auction(auction):
    
    store_serializer = RefStoreSerializer(auction.store, many=False).data

    status_name = 'Новый'
    if auction.status != None:
        status_name = auction.status.name 

    list_cars = list()

    user_data = {
        'username'      : auction.user.username,
        'first_name'    : auction.user.first_name,
        'last_name'     : auction.user.last_name,
        'email'         : auction.user.email,
    }

    cars_auction = auction.cars()
    is_express = bool(getattr(auction, 'is_express', False))
    express_estimation_ctx = None
    if is_express:
        try:
            from eco.auction_express_lot import get_express_estimation_for_auction
            express_estimation_ctx = get_express_estimation_for_auction(auction)
        except Exception:
            express_estimation_ctx = None

    for auction_car in cars_auction:
        dop_info = info_car_auction(auction_car.car.slug)
        if is_express and (
            not dop_info
            or not (dop_info.get('mark_name') or dop_info.get('model_name'))
        ):
            if express_estimation_ctx:
                from eco.auction_express_lot import build_express_dop_info_for_car
                estimation, interactiv_rlk = express_estimation_ctx
                dop_info = build_express_dop_info_for_car(
                    auction_car.car,
                    estimation,
                    interactiv_rlk,
                )
        car_info = {
            'car'           : _sanitize_car_payload_for_auction(
                RefCarsOrganizationSerializer(auction_car.car, many=False).data
            ),
            'description'   : auction_car.description,
            'dop_info'      : dop_info,
            'diagnostic'    : auction_car.diagnostic,
            'works'         : auction_car.works,
            'op'            : auction_car.op,
            'podgotovka'    : auction_car.podgotovka,
            'autoteka_prev' : auction_car.autoteka_prev,
            'files_car'             : _loads_auction_files_json(auction_car.files_car),
            'files_salon'           : _loads_auction_files_json(auction_car.files_salon),
            'files_shema'           : _loads_auction_files_json(auction_car.files_shema),
            'files_damages'         : _loads_auction_files_json(auction_car.files_damages),
            'files_kolesa'          : _loads_auction_files_json(auction_car.files_kolesa),
            'files_diagnostic'      : _loads_auction_files_json(auction_car.files_diagnostic)
        }
        list_cars.append(car_info)
    
    json_doc = {
        'date_start'        : _format_auction_datetime(auction.dateStart, 'space'),
        'store'             : store_serializer,
        'date_create'       : _format_auction_datetime(auction.dataTime, 'iso_t_micro'),
        'date_end'          : _format_auction_datetime(auction.dateEnd, 'space'),
        'description'       : auction.description,
        'start_price'       : auction.start_price,
        'uid'               : str(auction.uid),
        'status'            : status_name,
        'user'              : user_data,
        'cars_info'         : list_cars,
        'is_express'        : bool(getattr(auction, 'is_express', False)),
        'lot_type'          : 'express' if getattr(auction, 'is_express', False) else 'standard',
    }
    
    data_info  = json.dumps(json_doc, default=datetime_handler)
    
    r   = requests.post(url_auction_kors_portal + '/api/refresh_auction/', json = data_info, auth=('Admin_auction', 'Audi80b4'))
    if r.status_code == 200:
        data_answer   = json.loads(r.text)
        if data_answer['success']:
            status = data_answer['status']
            auction.status = get_status(status)
            if 'pk_auction' in data_answer:
                auction.pk_auction = str(data_answer['pk_auction'])
            auction.save()

def info_car_auction(slug):
    cars        = RefCarsOrganization.objects.filter(slug = slug)
    subquery    = RegInteractivOcenkaRLK.objects.filter(rlk__id = OuterRef(name='lo__rlk__id'))
    cars        = cars.annotate(
        int_ocenka_id           = Subquery(subquery.values('id')[:1])).annotate(
        int_ocenka_diagnostika  = Subquery(subquery.values('page_soglasovanie__comment_diagnostica')[:1])).annotate(
        int_ocenka_work         = Value('', output_field=CharField())).annotate(
        int_ocenka_url_vnesh    = Value('', output_field=CharField())).annotate(
        int_ocenka_url_salon_all    = Value('', output_field=CharField())).annotate(
        int_ocenka_url_wheel        = Value('', output_field=CharField())).annotate(
        autoteka_web                = Value('', output_field=CharField())).annotate(
        int_ocenka_url_diagnostic    = Value('', output_field=CharField())).annotate(
        int_ocenka_url_damage   = Value('', output_field=CharField())).annotate(
        int_ocenka_url_salon    = Value('', output_field=CharField())).annotate(
        int_ocenka_url_pered    = Value('', output_field=CharField())).annotate(
        int_ocenka_url_zad      = Value('', output_field=CharField())).annotate(
        int_ocenka_url_up       = Value('', output_field=CharField())).annotate(
        int_ocenka_url_right    = Value('', output_field=CharField())).annotate(
        int_ocenka_url_left     = Value('', output_field=CharField())).annotate(
        price_moderate          = Value(0, output_field=IntegerField())).annotate(
        price_medium            = Value(0, output_field=IntegerField())).annotate(
        price_significant       = Value(0, output_field=IntegerField())).annotate(
        market_price            = Value(0, output_field=IntegerField()))

    data = list(cars.values('vin', 
                       'slug', 
                       'year',
                       'price',
                       'run', 
                       'days_in_stok',
                       'outlay',
                       'cost_price',
                       'bcp',
                       'description_op',
                       'description_podgotovka',
                       'int_ocenka_diagnostika',
                       'int_ocenka_work',
                       'int_ocenka_id',
                       'int_ocenka_url_salon_all',
                       'int_ocenka_url_wheel',
                       'int_ocenka_url_diagnostic',
                       'int_ocenka_url_salon',
                       'int_ocenka_url_pered',
                       'int_ocenka_url_zad',
                       'int_ocenka_url_up',
                       'int_ocenka_url_right',
                       'int_ocenka_url_left',
                       'int_ocenka_url_vnesh',
                       'int_ocenka_url_damage',
                       'price_moderate',
                       'price_medium',
                       'price_significant',
                       'market_price',
                       'autoteka_web',
                       group    = F('group_price'),
                       type_sale_name = F('type_sale__name'),
                       type_reception_name = F('type_reception__name'),
                       stage_price_name = F('stage_price__name'),
                       status_name = F('status__name'),
                       modification_name = F('modification_autoru__name'),
                       model_name   = F('modification_autoru__model__name'),
                       mark_name    = F('modification_autoru__model__mark__name'),
                       url          = F('prev_photo')))
    if not data:
        return {}
    for car in data:
        car['url']                  = get_url_images(car['slug'])
        car['market_price']         = get_market_price(car)
        if car['market_price'] == None:
            car['market_price'] = 0
        zg      = car['group']
        matrix  = SettingsMatrixAuction.objects.get(id = 1)
        if zg == 1: #400
            car['price_moderate']       = car['price'] - matrix.charge_km_stage_1_400
            car['price_medium']         = car['price'] - matrix.charge_km_stage_2_400
            car['price_significant']    = car['price'] - matrix.charge_km_stage_3_400
        elif zg == 2 or zg == 9: #1200
            car['price_moderate']       = car['price'] - matrix.charge_km_stage_1_1200
            car['price_medium']         = car['price'] - matrix.charge_km_stage_2_1200
            car['price_significant']    = car['price'] - matrix.charge_km_stage_3_1200
        elif zg == 3 or zg == 10 : #2000
            car['price_moderate']       = car['price'] - matrix.charge_km_stage_1_2000
            car['price_medium']         = car['price'] - matrix.charge_km_stage_2_2000
            car['price_significant']    = car['price'] - matrix.charge_km_stage_3_2000
        elif zg == 4 or zg == 5: #3000
            car['price_moderate']       = car['price'] - matrix.charge_km_stage_1_3000
            car['price_medium']         = car['price'] - matrix.charge_km_stage_2_3000
            car['price_significant']    = car['price'] - matrix.charge_km_stage_3_3000 
        elif zg == 6: #700
            car['price_moderate']       = car['price'] - matrix.charge_km_stage_1_700
            car['price_medium']         = car['price'] - matrix.charge_km_stage_2_700
            car['price_significant']    = car['price'] - matrix.charge_km_stage_3_700
        elif zg == 7: #200
            car['price_moderate']       = car['price'] - matrix.charge_km_stage_1_200
            car['price_medium']         = car['price'] - matrix.charge_km_stage_2_200
            car['price_significant']    = car['price'] - matrix.charge_km_stage_3_200
        elif zg == 11: #5000
            car['price_moderate']       = car['price'] - matrix.charge_km_stage_1_5000
            car['price_medium']         = car['price'] - matrix.charge_km_stage_2_5000
            car['price_significant']    = car['price'] - matrix.charge_km_stage_3_5000
        elif zg == 12: #5000+
            car['price_moderate']       = car['price'] - matrix.charge_km_stage_1_5000
            car['price_medium']         = car['price'] - matrix.charge_km_stage_2_5000
            car['price_significant']    = car['price'] - matrix.charge_km_stage_3_5000
            
        int_ocenka_id               = car['int_ocenka_id']
        
        estimation = None
        diagnostika = ''
        if car['int_ocenka_id'] != None and car['int_ocenka_id'] != '': 
            estimationrlk  = RegInteractivOcenkaRLK.objects.get(id = car['int_ocenka_id'])
            estimation = estimationrlk.estimation 
            if estimationrlk.page_soglasovanie != None:
                diagnostika = estimationrlk.page_soglasovanie.comment_diagnostica
            else:
                diagnostika = ''
            
            car['autoteka_web']             = estimation.avtoteka_web

            car['int_ocenka_url_vnesh']     = get_url_int(estimation.id, 'vnesh_car_all')
            car['int_ocenka_url_damage']    = get_url_int(estimation.id, 'damage')
            
            car['int_ocenka_url_diagnostic']    = get_url_int(estimation.id, 'diagnostic')
            car['int_ocenka_url_wheel']         = get_url_int(estimation.id, 'wheel')
            car['int_ocenka_url_salon_all']     = get_url_int(estimation.id, 'salon')

            car['int_ocenka_diagnostika']   = diagnostika
            car['int_ocenka_work']          = list_work(estimation.id)

            car['int_ocenka_url_salon'] = get_url_image_salon(estimation.id, 'osmotr_salon')
            car['int_ocenka_url_pered'] = get_url_image_osmotr(estimation.id, 'vnesh_car_osmotr_pered')
            car['int_ocenka_url_zad']   = get_url_image_osmotr(estimation.id, 'vnesh_car_osmotr_zad')
            car['int_ocenka_url_up']    = get_url_image_osmotr(estimation.id, 'vnesh_car_osmotr_up')
            car['int_ocenka_url_right'] = get_url_image_osmotr(estimation.id, 'vnesh_car_osmotr_pass')
            car['int_ocenka_url_left']  = get_url_image_osmotr(estimation.id, 'vnesh_car_osmotr_vod')
    
    return car

def get_market_price(car):
    infos = RegEstimationRefCarsOrganizations.objects.filter(car__slug = car['slug']).order_by('-date')
    for info in infos:
        return info.avg_price

def list_work(int_ocenka):
    work_podgotovka = list()
    podgotovkas     = RegEstimationPodgotovka.objects.filter(estimation__id = int_ocenka)
    for podgotovka in podgotovkas:
        list_work = {
            'name': podgotovka.name
        }
        work_podgotovka.append(list_work)
    podgotovkas     = RegEstimationSS.objects.filter(estimation__id = int_ocenka)
    for podgotovka in podgotovkas:
        list_work = {
            'name': podgotovka.name
        }
        work_podgotovka.append(list_work)
    podgotovkas     = RegEstimationMCU.objects.filter(estimation__id = int_ocenka)
    for podgotovka in podgotovkas:
        list_work = {
            'name': podgotovka.name
        }
        work_podgotovka.append(list_work)
    return work_podgotovka 

def get_url_image_salon(estimation_id, type_file):
    photos_count = RegRegInteractivOcenkaFiles.objects.filter(estimation__id = estimation_id).filter(type_file = type_file).count()
    try:
        if photos_count > 0:
            return RegRegInteractivOcenkaFiles.objects.filter(estimation__id = estimation_id).filter(type_file = type_file)[0].file.url.replace('/media/','/media_dop/')
    except:
        return '/media/nophoto.png'
    return '/media/nophoto.png'
    
def get_url_image_osmotr(estimation_id, type_file):
    photos_count = RegRegInteractivOcenkaFiles.objects.filter(estimation__id = estimation_id).filter(type_file = type_file).count()
    try:
        if photos_count > 0:
            return RegRegInteractivOcenkaFiles.objects.filter(estimation__id = estimation_id).filter(type_file = type_file)[0].file.url.replace('/media/','/media_dop/')
    except:
        return '/media/nophoto.png'
    return '/media/nophoto.png'

def get_url_int(estimation_id, type_file):
    
    list_url = list()
    
    if type_file == 'vnesh_car_all':
        photos = RegRegInteractivOcenkaFiles.objects.filter(estimation__id = estimation_id).filter(Q(type_file = 'vnesh_car_all') | Q(type_file = 'pod_capot') | Q(type_file = 'vin'))
    
    elif type_file == 'damage':
        photos = RegRegInteractivOcenkaFiles.objects.filter(estimation__id  = estimation_id).filter(Q(type_file = 'salon_error') | Q(type_file = 'array_images_pered') | Q(type_file = 'array_images_vod') | Q(type_file = 'array_images_zad')
                                                                                                       | Q(type_file = 'array_images_up')
                                                                                                        | Q(type_file = 'array_images_pass')
                                                                                                         | Q(type_file = 'fotos_salon_error')
                                                                                                         | Q(type_file = 'light_error')
                                                                                                          | Q(type_file = 'windshield_error') ).order_by('file_number')
    elif type_file == 'diagnostic':
        photos = RegRegInteractivOcenkaFiles.objects.filter(estimation__id  = estimation_id).filter(type_file = 'diagnostic').order_by('file_number') 
    
    elif type_file == 'wheel':
        photos = RegRegInteractivOcenkaFiles.objects.filter(estimation__id  = estimation_id).filter(Q(type_file = 'kolesa') | Q(type_file = 'kolesa2')).order_by('file_number') 
    
    elif type_file == 'salon':
        photos = RegRegInteractivOcenkaFiles.objects.filter(estimation__id  = estimation_id).filter(type_file = 'salon_all').order_by('file_number') 
         
    for photo in photos:
        try:
            list_url.append(photo.file.url.replace('/media/','/media_dop/'))
        except:
            s = 1

    return list_url

def get_url_image(slug):
    photos_count = RefCarsOrganizationFiles.objects.filter(сars_organization__slug = slug).filter(main = True).count()
    try:
        if photos_count > 0:
            return RefCarsOrganizationFiles.objects.filter(сars_organization__slug = slug).filter(main = True)[0].file_mini.url
        else:
            photos_count = RefCarsOrganizationFiles.objects.filter(сars_organization__slug = slug).count()
            if photos_count > 0:
                return RefCarsOrganizationFiles.objects.filter(сars_organization__slug = slug)[0].file_bak.url
    except:
        return '/media/nophoto.png'
    return '/media/nophoto.png'

def get_url_images(slug):
    list_url = list()
    photos_count = RefCarsOrganizationFiles.objects.filter(сars_organization__slug = slug).count()
    try:
        if photos_count > 0:
            photos = RefCarsOrganizationFiles.objects.filter(сars_organization__slug = slug).order_by('-main')
            for photo in photos:
                list_url.append(photo.file.url)
        else:
            list_url.append('/media/nophoto.png')
    except:
        list_url.append('/media/nophoto.png')

    return list_url

def refresh_car_my_kors_portal():
    
    list_cars = list()
    
    cars = RefCarsOrganization.objects.exclude(quantity = 0).exclude(modification_autoru = None)

    for car in cars: 
        car_info = RefCarsOrganizationSerializer(car, many=False).data  
        
        car_info['autohub']                         = list(car.avtohub_car_organizaton().values())
        car_info['car_link_auto_ru']                = car.get_link_autoru() 
        car_info['car_link_avito_ru']               = car.get_link_avitoru() 
        car_info['car_link_drom_ru']                = car.get_link_dromru() 
        car_info['car_price_info']                  = list(car.price_car_organizaton_info().values('date', 'price'))
        car_info['car_price_info_calculation']      = list(car.price_car_organizaton_calculation().values('date', 'price', 'evaluation__name'))
        car_info['car_price_info_estimations']      = list(car.price_car_organizaton_estimations().values('date', 'avg_price', 'avg_days', 'position', 'price', 'total'))
        
        #Фотографии
        try:
            car_info['car_photos']                      = list(car.get_files().values('url'))
        except:
            car_info['car_photos']                      = list()
        list_cars.append(car_info)
        
    
    if len(list_cars) > 0:
        
        data_info  = json.dumps(list_cars, default=datetime_handler)
        
        r   = requests.post(url_my_kors_portal + '/api/refresh/', json = data_info)
        if r.status_code == 200:
            s = 1


####
###
##
# Экспресс оценка автомобилей на складе по нашим фильтрам "Экспресс оценка"
@background(queue='refresh_estimation_cars_organization')
def start_refresh_estimation_cars_organization():
    refresh_estimation_cars_organization_run()

def refresh_estimation_cars_organization_run():
    
    username        = "korsgroup@maxposter.ru"
    password        = "pJ%[QwwqH,YxP9J-"
    url             = "api.maxposter.ru"
    URL_TEMPLATE    = "https://api.maxposter.ru/partners-api/express"
    token           = 'a29yc2dyb3VwQG1heHBvc3Rlci5ydTpwSiVbUXd3cUgsWXhQOUot'
    headers         = { 'Authorization' : 'Basic %s' % token }

    cars                    = RefCarsOrganization.objects.exclude(quantity = 0).exclude(run = 0).exclude(modification_autoru = None).order_by('-date_create')
    date_start              = DT.datetime.now().replace(hour = 0, minute=0, second=1) 
    subqyery_cars           = Subquery(RegEstimationRefCarsOrganizations.objects.filter(car__id = OuterRef(name = 'id')).annotate(max_date = Max('date')).order_by('-max_date').values('max_date')[:1])
    cars                    = cars.annotate(max_date = subqyery_cars)
    cars = cars.filter(Q(max_date__lte = date_start) | Q(max_date = None))
    cars = cars.order_by('max_date')
    cars = cars[:10]
    
    #cars                    = RefCarsOrganization.objects.filter(vin = 'XTAGFL440NY659465').exclude(modification_autoru = None).exclude(quantity = 0)

    car_all_count   = cars.count()
    car_success     = 0 
    car_error       = 0
    start_date      = DT.datetime.now()

    for car in cars:
        try:

            sleep(3)

            year_current = DT.datetime.now().year
            if year_current - car.year > 5:
                year_start  = car.year - 1
                year_end    = car.year + 1
            else:
                year_start  = car.year
                year_end    = car.year

            avtohub_modification = None
            count_avtohub_modification = AvtohubModifications.objects.filter(autoruId = car.modification_autoru.idSiteTech).count()
            if count_avtohub_modification == 1:
                avtohub_modification = AvtohubModifications.objects.filter(autoruId = car.modification_autoru.idSiteTech)[0]    
                if year_start < avtohub_modification.yearFrom:
                    year_start = avtohub_modification.yearFrom
                if year_end > avtohub_modification.yearTo:
                    year_end = avtohub_modification.yearTo

            if avtohub_modification != None:
                brand = {
                    'id'    : avtohub_modification.brandId,
                    'name'  : ''
                }
                model = {
                    'id'    : avtohub_modification.modelId,
                    'name'  : ''
                }
                generation = {
                    'id'    : avtohub_modification.generationId,
                    'name'  : ''
                }
                modification = {
                    'id'    : avtohub_modification.id_avtohub,
                    'name'  : ''
                }
            else:
                brand = {
                    'id'    : None,
                    'name'  : car.modification_autoru.model.mark.name.strip()
                }
                model = {
                    'id'    : None,
                    'name'  : get_name_re(car.modification_autoru.model.name, 0)
                }
                generation = {
                    'id'    : None,
                    'name'  : get_name_re(car.modification_autoru.model.name, 1)
                }
                modification = {
                    'id'    : None,
                    'name'  : car.modification_autoru.name
                }
            
            marketFilter = {
                'brand'         : brand,
                'model'         : model,
                'generation'    : generation,
                'modification'  : modification,
                'geoDistance'   : 500,
                'yearFrom'      : year_start,
                "yearTo"        : year_end
            }
            
            salesFromDate = DT.datetime.now() - relativedelta(months=2)
            salesFromDate = salesFromDate.replace(day=1, hour=1)

            filter = {
                'brand'         : brand,
                'model'         : model,
                'generation'    : generation,
                'modification'  : modification,
                'geoDistance'   : 500,
                'useAutoFilter' : False,
                'yearFrom'      : year_start,
                "yearTo"        : year_end,
                'salesFromDate' : salesFromDate.strftime('%Y-%m-%d')
            }

            vehicle = {
                'year'      : car.year,
                'mileage'   : car.run,
                'rubPrice'  : car.price
            }
            
            data_info = {
                'dealerId'          : 2107,
                'marketFilter'      : marketFilter,
                'filter'            : filter,
                'vehicle'           : vehicle 
            }
            r   = requests.post(URL_TEMPLATE, auth=HTTPBasicAuth(username, password), json=data_info)
            
            if r.status_code == 200:
                
                js_data = json.loads(r.text)
                data = js_data['data']

                if len(data) == 1:
                    data = data[0] 

                analyticsByActualSales              = data['analyticsByActualSales']
                
                new_record              = RegEstimationRefCarsOrganizations()
                new_record.car          = car
                new_record.avg_price    = analyticsByActualSales['avgPriceWithCorrection']
                new_record.avg_days     = analyticsByActualSales['avgDaysInSale']
                new_record.position     = analyticsByActualSales['vRating']
                new_record.total        = analyticsByActualSales['usefulSalesTotal']
                new_record.price        = car.price
                new_record.save()
                car_success = car_success + 1 

            else:
                text_error              = r.text
                new_record              = RegEstimationRefCarsOrganizations()
                new_record.car          = car
                new_record.avg_price    = 0
                new_record.avg_days     = 0
                new_record.position     = 0
                new_record.total        = 0
                new_record.price        = car.price
                new_record.error        = text_error[0:2048]
                new_record.save()

                car_error = car_error + 1  

        except:
            
            s = 1
            text_error              = 'Неопределено' 
            new_record              = RegEstimationRefCarsOrganizations()
            new_record.car          = car
            new_record.avg_price    = 0
            new_record.avg_days     = 0
            new_record.position     = 0
            new_record.total        = 0
            new_record.price        = car.price
            new_record.error        = text_error
            new_record.save()
            car_error               = car_error + 1      

    new_record = RegInfoRefreshEstimationCarsExpress()
    new_record.date             = start_date
    new_record.date_end         = DT.datetime.now()
    new_record.count_all        = car_all_count
    new_record.count_success    = car_success
    new_record.count_error      = car_error
    new_record.save()
    

####
###
##
# Получение данных автотека
@background(queue='refresh_avtoteka')
def start_refresh_avtoteka_vin():
    refresh_avtoteka_vin()


def calc_avtoteka_run_metrics(json_autoteka):
    """
    По eventsOthersHistory (как в eco):
    - avtoteka_last_run — последний заполненный пробег (source != Audatex);
    - avtoteka_warning_run — сумма скачков вниз > 1000 км (возможная скрутка).
    """
    last_run = 0
    run_sum = 0
    if not isinstance(json_autoteka, dict):
        return last_run, run_sum
    events = json_autoteka.get('eventsOthersHistory') or []
    run_other = 0
    for event in events:
        if not isinstance(event, dict):
            continue
        if event.get('source') == 'Audatex':
            continue
        try:
            mileage = int(event.get('mileage') or 0)
        except (TypeError, ValueError):
            continue
        if mileage > 0:
            run = mileage
            if run_other > run and (run_other - run) > 1000:
                run_sum += (run_other - run)
            run_other = run
            last_run = run
    return last_run, run_sum


def apply_avtoteka_run_fields(object_estimation, json_autoteka):
    last_run, warning_run = calc_avtoteka_run_metrics(json_autoteka)
    object_estimation.avtoteka_last_run = last_run or 0
    object_estimation.avtoteka_warning_run = warning_run or 0
    return last_run, warning_run


def refresh_avtoteka_data(interactiv_ocenka_id):
    token = ''
    header = {
        'X-Request-ID' : "4a68aa75-d369-4fcf-bb94-1863ffd704f5"
    }
    token = get_token_avtoteka()
    header['Authorization'] = f"Bearer {token}"
    object_estimation = RegInteractivOcenka.objects.get(pk = interactiv_ocenka_id)
    if object_estimation.avtoteka_preview == None or object_estimation.avtoteka_preview == '':
        task_id = 0
        url = 'https://pro.autoteka.ru/autoteka/v1/previews' 
        header['Authorization'] = f"Bearer {token}"
        id = {
            "vin": object_estimation.vin
        }
        response = requests.post(url, headers=header, json=id)

        if response.status_code == 200:
        
            data_prev   = json.loads(response.text)
            task_id     = data_prev['result']['preview']['previewId']
            object_estimation.avtoteka_preview = str(task_id)
            object_estimation.save(update_fields=['avtoteka_preview'])
    elif object_estimation.avtoteka_task == None or object_estimation.avtoteka_task == '':
        url_prev = 'https://pro.autoteka.ru/autoteka/v1/previews/' + str(object_estimation.avtoteka_preview)                        
        response_prev = requests.get(url_prev, headers=header)
        
        if response_prev.status_code == 200:
            
            status_prev = json.loads(response_prev.text)['result']['preview']['status']
            
            if status_prev == 'success':
                js               = {'previewId': object_estimation.avtoteka_preview}
                url_report_id    = 'https://pro.autoteka.ru/autoteka/v1/reports'
                status_report   = ''
                
                response_report = requests.post(url_report_id, headers=header, json=js)
                if response_report.status_code == 200:
                    reportId        = json.loads(response_report.text)['result']['report']['reportId']
                    object_estimation.avtoteka_task = str(reportId)
                    object_estimation.save(update_fields=['avtoteka_task'])
            elif status_prev == 'NotFound':
                object_estimation.avtoteka_task = '-'
                object_estimation.save(update_fields=['avtoteka_task'])                
    elif object_estimation.avtoteka_task != None and object_estimation.avtoteka_task != '-':
        status_report = ''
        if token != '':
            url_report = 'https://pro.autoteka.ru/autoteka/v1/reports/' + str(object_estimation.avtoteka_task)
            count_response = 0
            while status_report != 'success' and count_response < 5:
                response_report_data =  requests.get(url_report, headers=header)
                count_response = count_response + 1 
                if response_report_data.status_code == 200:
                    status_report = json.loads(response_report_data.text)['result']['report']['status']
                    if status_report == 'success':
                        status      = status_report
                        status_prev = status_report
                        object_estimation.avtoteka_data = response_report_data.text
                        response_report_json = json.loads(response_report_data.text)
                        object_estimation.avtoteka_web = response_report_json['result']['report']['webLink']
                        object_estimation.avtoteka_pdf = response_report_json['result']['report']['pdfLink'] 
                        try:
                            json_autoteka = json.loads(response_report_data.text)['result']['report']['data']
                            object_estimation.count_dtp                     = len(json_autoteka['accidents']['crashesHistory'])
                            apply_avtoteka_run_fields(object_estimation, json_autoteka)
                            
                            sum_audex = 0
                            for service_info in json_autoteka['eventsOthersHistory']:
                                if service_info.get('type') == 'repairCalculation':
                                    try:
                                        description = service_info.get('description').split('RUR')
                                        sum_new     = float(description[0].replace('Расчет стоимости ремонта:', '').replace('RUR','').strip())
                                        sum_audex   = max(sum_audex, sum_new)
                                    except:
                                        s = 1
                                    
                            for crash in json_autoteka['accidents']['crashesHistory']:
                                for damage in crash.get('damageTypes'):
                                    if damage.get('type') == 'red':
                                        object_estimation.dtp_red = True    
                            
                            if json_autoteka['taxiData'].get('events', '') != None and len(json_autoteka['taxiData'].get('events', '')) > 0:
                                object_estimation.taxi = True
                            else:
                                object_estimation.taxi = False

                            if json_autoteka['carsharingData'].get('events', '') != None and len(json_autoteka['carsharingData'].get('events', '')) > 0:
                                object_estimation.carsharing = True
                            else:
                                object_estimation.carsharing = False
                                
                            object_estimation.avtoteka_car_autodex = sum_audex 

                            price                                               = json_autoteka.get('avitoPriceValuation') 
                            object_estimation.avito_price_avg_market_price      = price.get('avgMarketPrice')
                            object_estimation.avito_price_avg_condition         = price.get('avgPriceWithCondition')
                            object_estimation.avito_price_market_min            = price.get('marketNormalPriceRange').get('min')
                            object_estimation.avito_price_market_max            = price.get('marketNormalPriceRange').get('max')
                            object_estimation.avito_price_min                   = price.get('minPrice')
                            object_estimation.avito_price_max                   = price.get('maxPrice')
                        except:
                            s = 1
                        object_estimation.save(update_fields = [
                                                    'avtoteka_data',
                                                    'avtoteka_web',
                                                    'avtoteka_pdf',
                                                    'count_dtp',
                                                    'dtp_red',
                                                    'taxi',
                                                    'carsharing',
                                                    'avtoteka_car_autodex',
                                                    'avito_price_avg_market_price',
                                                    'avito_price_avg_condition',
                                                    'avito_price_market_min',
                                                    'avito_price_market_max',
                                                    'avito_price_min',
                                                    'avito_price_max',
                                                    'avtoteka_last_run',
                                                    'avtoteka_warning_run',
                                                ])                 


def refresh_avtoteka_vin():
    
    token = ''
    header = {
        'X-Request-ID' : "4a68aa75-d369-4fcf-bb94-1863ffd704f5"
    }
    
    date_start = DT.datetime.now().replace(hour=1) - DT.timedelta(days=14)
    object_estimations = RegInteractivOcenka.objects.filter(start_estimation__gt = date_start).exclude(number_body = '')
    for object_estimation in object_estimations:
        if token == '':
            token = get_token_avtoteka()
            header['Authorization'] = f"Bearer {token}"

        if len(object_estimation.vin) != 17:
            number_body     = object_estimation.number_body
            status  = ''
            
            if number_body != None and len(number_body) != 17:
                
                id = {
                    "vin": number_body
                }
                task_id = 0
                url = 'https://pro.autoteka.ru/autoteka/v1/previews' 
                header['Authorization'] = f"Bearer {token}"
                response = requests.post(url, headers=header, json=id)
    
                if response.status_code == 200:
                
                    data_prev   = json.loads(response.text)
                    task_id     = data_prev['result']['preview']['previewId']
                    object_estimation.avtoteka_preview = str(task_id)
                    object_estimation.save(update_fields=['avtoteka_preview']) 
    
    #VIN
    object_estimations = RegInteractivOcenka.objects.filter(start_estimation__gt = date_start).exclude(vin = ' ').exclude(vin = '').exclude(vin__icontains = '*').exclude(vin__icontains = 'отсут').filter(avtoteka_web = '').filter(avtoteka_preview = '').filter(avtoteka_task = None).order_by('start_estimation') | RegInteractivOcenka.objects.exclude(vin = '').exclude(vin = ' ').exclude(vin__icontains = '*').exclude(vin__icontains = 'отсут').filter(start_estimation__gt = date_start).filter(avtoteka_web = '').filter(avtoteka_preview = '').filter(avtoteka_task = '').order_by('start_estimation')
    #object_estimations = RegInteractivOcenka.objects.filter(start_estimation__gt = start_autoteka).exclude(vin = ' ').exclude(vin = '').exclude(vin__icontains = '*').exclude(vin__icontains = 'отсут').filter(avtoteka_web = None) | RegInteractivOcenka.objects.filter(start_estimation__gt = start_autoteka).exclude(vin = ' ').exclude(vin = '').exclude(vin__icontains = '*').exclude(vin__icontains = 'отсут').filter(avtoteka_web = '')
    if len(object_estimations) > 0:
        
        if token == '':
            token = get_token_avtoteka()
            header['Authorization'] = f"Bearer {token}"

        for object_estimation in object_estimations: 
            
            if token != '':
                
                vin     = object_estimation.vin
                status  = ''
                
                if vin != None and len(vin) == 17 and re.match(r'^[A-Za-z0-9_-]*$', vin) is not None and vin.find("_") < 0:
                    
                    id = {
                        "vin": vin
                    }
                    task_id = 0
                    url = 'https://pro.autoteka.ru/autoteka/v1/previews' 
                    header['Authorization'] = f"Bearer {token}"
                    response = requests.post(url, headers=header, json=id)
        
                    if response.status_code == 200:
                    
                        data_prev   = json.loads(response.text)
                        task_id     = data_prev['result']['preview']['previewId']
                        object_estimation.avtoteka_preview = str(task_id)
                        object_estimation.save(update_fields=['avtoteka_preview'])                                                    

    object_estimations_prev = RegInteractivOcenka.objects.filter(start_estimation__gt = date_start).exclude(avtoteka_preview = '').filter(avtoteka_task = None).order_by('start_estimation')
    if len(object_estimations_prev) > 0:
        
        if token == '':
            token = get_token_avtoteka()
            header['Authorization'] = f"Bearer {token}"
        
        for object_estimation in object_estimations_prev: 
            
            if token != '':
                
                url_prev = 'https://pro.autoteka.ru/autoteka/v1/previews/' + str(object_estimation.avtoteka_preview)                        
                response_prev = requests.get(url_prev, headers=header)
                
                if response_prev.status_code == 200:
                    
                    status_prev = json.loads(response_prev.text)['result']['preview']['status']
                    
                    if status_prev == 'success':
                        js               = {'previewId': object_estimation.avtoteka_preview}
                        url_report_id    = 'https://pro.autoteka.ru/autoteka/v1/reports'
                        status_report   = ''
                        
                        response_report = requests.post(url_report_id, headers=header, json=js)
                        if response_report.status_code == 200:
                            reportId        = json.loads(response_report.text)['result']['report']['reportId']
                            object_estimation.avtoteka_task = str(reportId)
                            object_estimation.save(update_fields=['avtoteka_task'])

    object_estimations_report = RegInteractivOcenka.objects.filter(start_estimation__gt = date_start).filter(avtoteka_web = '').exclude(avtoteka_preview = '').exclude(avtoteka_task = '').exclude(avtoteka_task = None).order_by('start_estimation')
    if len(object_estimations_report) > 0:
        
        if token == '':
            token = get_token_avtoteka()
            header['Authorization'] = f"Bearer {token}"
            
        for object_estimation in object_estimations_report:             
            status_report = ''
            if token != '':
                url_report = 'https://pro.autoteka.ru/autoteka/v1/reports/' + str(object_estimation.avtoteka_task)
                count_response = 0
                while status_report != 'success' and count_response < 5:
                    response_report_data =  requests.get(url_report, headers=header)
                    count_response = count_response + 1 
                    if response_report_data.status_code == 200:
                        status_report = json.loads(response_report_data.text)['result']['report']['status']
                        if status_report == 'success':
                            status      = status_report
                            status_prev = status_report
                            object_estimation.avtoteka_data = response_report_data.text
                            response_report_json = json.loads(response_report_data.text)
                            object_estimation.avtoteka_web = response_report_json['result']['report']['webLink']
                            object_estimation.avtoteka_pdf = response_report_json['result']['report']['pdfLink'] 
                            try:
                                json_autoteka = json.loads(response_report_data.text)['result']['report']['data']
                                object_estimation.count_dtp                     = len(json_autoteka['accidents']['crashesHistory'])
                                apply_avtoteka_run_fields(object_estimation, json_autoteka)
                                
                                sum_audex = 0
                                for service_info in json_autoteka['eventsOthersHistory']:
                                    if service_info.get('type') == 'repairCalculation':
                                        try:
                                            description = service_info.get('description').split('RUR')
                                            sum_new     = float(description[0].replace('Расчет стоимости ремонта:', '').replace('RUR','').strip())
                                            sum_audex   = max(sum_audex, sum_new)
                                        except:
                                            s = 1
                                       
                                for crash in json_autoteka['accidents']['crashesHistory']:
                                    for damage in crash.get('damageTypes'):
                                        if damage.get('type') == 'red':
                                            object_estimation.dtp_red = True    
                                
                                if json_autoteka['taxiData'].get('events', '') != None and len(json_autoteka['taxiData'].get('events', '')) > 0:
                                    object_estimation.taxi = True
                                else:
                                    object_estimation.taxi = False

                                if json_autoteka['carsharingData'].get('events', '') != None and len(json_autoteka['carsharingData'].get('events', '')) > 0:
                                    object_estimation.carsharing = True
                                else:
                                    object_estimation.carsharing = False
                                    
                                object_estimation.avtoteka_car_autodex = sum_audex 

                                price                                               = json_autoteka.get('avitoPriceValuation') 
                                object_estimation.avito_price_avg_market_price      = price.get('avgMarketPrice')
                                object_estimation.avito_price_avg_condition         = price.get('avgPriceWithCondition')
                                object_estimation.avito_price_market_min            = price.get('marketNormalPriceRange').get('min')
                                object_estimation.avito_price_market_max            = price.get('marketNormalPriceRange').get('max')
                                object_estimation.avito_price_min                   = price.get('minPrice')
                                object_estimation.avito_price_max                   = price.get('maxPrice')
                            except:
                                s = 1
                            object_estimation.save(update_fields = [
                                                        'avtoteka_data',
                                                        'avtoteka_web',
                                                        'avtoteka_pdf',
                                                        'count_dtp',
                                                        'dtp_red',
                                                        'taxi',
                                                        'carsharing',
                                                        'avtoteka_car_autodex',
                                                        'avito_price_avg_market_price',
                                                        'avito_price_avg_condition',
                                                        'avito_price_market_min',
                                                        'avito_price_market_max',
                                                        'avito_price_min',
                                                        'avito_price_max',
                                                        'avtoteka_last_run',
                                                        'avtoteka_warning_run',
                                                    ])                 


def get_token_avtoteka():
    
    url = avtoteka_url + 'token'

    data = {'client_id'         : avtoteka_client_id,
            'client_secret'     : avtoteka_client_secret,
            'grant_type'         : 'client_credentials'}

    response = requests.post(url, data=data)
    
    if response.status_code == 200:
        return json.loads(response.text).get('access_token', '')
    return ''


####
###
##
# Получение данных сигнала
@background(queue='refresh_signal')
def start_refresh_signal():
    refresh_signal_run()

def refresh_signal_run():
    
    token = ''
    header = {
            'X-Request-ID' : "4a68aa75-d369-4fcf-bb94-1863ffd704f5"
        } 
    token = get_token_avtoteka()
    if token != '':
        
        count_id = Autoteka_signal_last_id.objects.all().count()
        if count_id == 1:
            last_id = Autoteka_signal_last_id.objects.all()[0].last_id
        else: 
            last_id = 0

        header['Authorization'] = f"Bearer {token}"

        url         = 'https://pro.autoteka.ru/autoteka/v1/get-leads/'
        data_filter = {
            "lastId"        : last_id,
            "limit"         : 5000,
            "subscriptionId": 1157
        } 
        response                = requests.post(url, headers=header, json = data_filter)
        last_id_response        = 0
        if response.status_code == 200:
            json_data = json.loads(response.text)
            
            pagination = json_data.get('pagination', '')
            if len(pagination) > 0:

                last_id_response    = json_data['pagination']['lastId']
                list_info           = json_data['result']

                for data in list_info:
                    id      = data.get('id')
                    count_data_base = Autoteka_signal.objects.filter(id_records = id).count()

                    if count_data_base == 0:
                        new_autoteka_signal = Autoteka_signal()
                        new_autoteka_signal.id_records = id 
                    else:
                        new_autoteka_signal = Autoteka_signal.objects.filter(id_records = id)[0]
                    
                    payload     = data.get('payload')

                    new_autoteka_signal.vin         = payload.get('vin')
                    new_autoteka_signal.year        = payload.get('year')
                    new_autoteka_signal.brand       = payload.get('brand') 
                    new_autoteka_signal.model       = payload.get('model') 
                    new_autoteka_signal.price       = payload.get('price')  
                    new_autoteka_signal.mileage     = payload.get('mileage') 
                    new_autoteka_signal.url         = payload.get('url')
                    new_autoteka_signal.region_id    = payload.get('regionId')
                    new_autoteka_signal.condition       = payload.get('condition')
                    new_autoteka_signal.description     = payload.get('description')[0:5120]
                    owners = payload.get('owners')
                    if owners != '' and owners != None:
                        try:
                            new_autoteka_signal.owners          = int(owners.replace('+',''))
                        except:
                            s=1

                    itemCreatedAt = payload.get('itemCreatedAt')
                    if len(itemCreatedAt) > 0:
                        new_autoteka_signal.item_created_at = DT.datetime.strptime(itemCreatedAt, '%Y-%m-%d %H:%M')

                    itemUpdatedAt = payload.get('itemUpdatedAt')
                    if len(itemUpdatedAt) > 0:
                        new_autoteka_signal.item_updated_at = DT.datetime.strptime(itemUpdatedAt, '%Y-%m-%d %H:%M')

                    extraPayload = payload.get('extraPayload')
                    if extraPayload != None:
                        new_autoteka_signal.seller          = extraPayload.get('seller')
                        new_autoteka_signal.is_pro_seller   = extraPayload.get('isProSeller')
                        new_autoteka_signal.pledge          = extraPayload.get('pledge')
                        try:
                            new_autoteka_signal.phone_number    = re.sub("0-9", "", extraPayload.get('phoneNumber')).strip()   
                        except:
                            new_autoteka_signal.phone_number    = ''
                        new_autoteka_signal.city_name       = extraPayload.get('cityName')   
                        new_autoteka_signal.region_name     = get_region(extraPayload.get('regionName', '').strip())
                    
                    priceAnalytics =  extraPayload.get('priceAnalytics')
                    if priceAnalytics != None:
                        averageDaysInSale = priceAnalytics.get('averageDaysInSale', 0)
                        new_autoteka_signal.average_days_in_sale    = averageDaysInSale
                        new_autoteka_signal.estimate_sell_price     = priceAnalytics.get('estimateSellPrice', 0)
                        new_autoteka_signal.liquidity_rating        = priceAnalytics.get('liquidityRating')
                        new_autoteka_signal.seller_price_diff       = priceAnalytics.get('sellerPriceDiff', 0)
                    new_autoteka_signal.save()
            
                Autoteka_signal_last_id.objects.all().delete()
                
                new_last_id = Autoteka_signal_last_id()
                new_last_id.last_id = last_id_response
                new_last_id.save()

def get_region(region_name):
    count = Autoteka_signal_region.objects.filter(name = region_name).count()
    if count > 0:
        return Autoteka_signal_region.objects.filter(name = region_name)[0]
    else:
        new_region = Autoteka_signal_region()
        new_region.name = region_name
        new_region.save()

        return new_region


####
###
##
# Обновление каталогов
@background(queue='refresh_catalog')
def start_refresh_catalog():
    
    try:
        refresh_catalog_avito_ru()
    except:
        s =1

    try:
        refresh_catalog_auto_ru()
    except:
        s =1
            
def refresh_catalog_auto_ru():
    
    try:
        
        response    = requests.get(url_catalog_autoru)
        if response.status_code == requests.codes.ok:
            
            path = default_storage.save('temp/catalog_auto_ru.xml', ContentFile(response.content))
            tmp_file = os.path.join(settings.MEDIA_ROOT, path)
                
            parser      = ETree.XMLParser(encoding="utf-8")
            tree        = ETree.parse(tmp_file, parser=parser)

            for mark in tree.getroot():
            
                name_mark       = mark.get('name')
                id_site_mark    = mark.get('id')
                if id_site_mark == None:
                    autoru_mark_count = AutoruMark.objects.filter(name = name_mark).filter(idSite = None).count()
                    if autoru_mark_count == 0:
                        autoru_mark = AutoruMark()
                    else:
                        autoru_mark = AutoruMark.objects.filter(name = name_mark).filter(idSite = None)[0]    
                else:
                    autoru_mark_count = AutoruMark.objects.filter(idSite = int(id_site_mark)).count()
                    if autoru_mark_count == 0:
                        autoru_mark = AutoruMark()
                    else:
                        autoru_mark = AutoruMark.objects.filter(idSite = int(id_site_mark))[0]
                

                autoru_mark.name    = name_mark
                autoru_mark.idSite  = id_site_mark
                try:
                    autoru_mark.nameEn = mark.find('code').text
                except:
                    s = 1
                autoru_mark.save()

                ###

                for model in mark.findall('folder'):
                    name_model      = model.get('name')
                    id_site_model   = model.get('id')
                    
                    try:
                        autoru_model = AutoruModel.objects.get(idSite = id_site_model)
                    except:
                        autoru_model = AutoruModel()

                    autoru_model.mark   = autoru_mark
                    autoru_model.name   = name_model
                    autoru_model.idSite = id_site_model
                    try:
                        autoru_model.nameEn = model.find('model').text
                    except:
                        s = 1
                    autoru_model.save()
                    
                    idSiteGeneration = 0
                    try:
                        idSiteGeneration = int(model.find('generation').text)
                    except:
                        s = 1
                        
                    for modification in model.findall('modification'):
                        modificationName    = modification.get('name')
                        modificationID      = modification.get('id')

                        result = re.search(r'(\d\.\d)?(HYB|D|Electro)?\s(AT|MT|AMT|CVT)?\s\((.+)\)', modificationName, re.IGNORECASE)
                        engineVolume = result.group(1) if result.group(1) else '0.0'      

                        # тип двигателя: Бензин, Дизель, Электро, Гибрид
                        engineFuel = result.group(2) if result.group(2) else 'Бензин'
                        if engineFuel.upper() == 'D':
                            engineFuel = 'Дизель'
                        elif engineFuel.upper() == 'HYP':
                            engineFuel = 'Гибрид'
                        elif engineFuel.upper() == 'ELECTRO':
                            engineFuel = 'Электро'
                        else:
                            engineFuel = 'Бензин'
                        typeEngine = RefTypeEngine.objects.get_or_create(name=engineFuel)[0]

                        transmissionType = str(result.group(3)).upper()
                        if transmissionType=='AT':
                            transmissionType = 'Автомат'
                        elif transmissionType=='MT':
                            transmissionType = 'Механика'
                        elif transmissionType=='AMT':
                            transmissionType = 'Робот'
                        elif transmissionType=='CVT':
                            transmissionType = 'Вариатор'
                        
                        typeKpp = RefTypeKpp.objects.get_or_create(name=str(transmissionType))[0]
                        
                        enginePower = str(result.group(4)).lower()
                        if enginePower.endswith(' л.с.'):
                            enginePower = enginePower[:-5] # отрежем хвост - последние 5 символов
                            try:
                                enginePower = float(enginePower)
                            except:
                                enginePower = 0.0
                        elif enginePower.endswith(' квт'):
                            enginePower = enginePower[:-4]
                            try:
                                enginePower = round(float(enginePower) * 1.35962)
                            except:
                                enginePower = 0.0
                        else:
                            enginePower = 0.0

                        yearsList   = modification.find('years').text.split('-')
                        yearFrom    = yearsList[0].rstrip()
                        yearsTo     = yearsList[1].lstrip() 
                        yearsTo     = yearsTo if yearsTo.isdigit() else '2050'
                        
                        bt = modification.find('body_type').text
                        
                        idSiteTech = 0
                        try:
                            idSiteTech = int(modification.find('tech_param_id').text)
                        except:
                            s = 1

                        idSiteKonf = 0
                        try:
                            idSiteKonf = int(modification.find('configuration_id').text)
                        except:
                            s = 1
                        
                        typeBody = RefTypeBody.objects.get_or_create(name=bt)[0]
                        
                        try:
                            newAutoruModification = AutoruModification.objects.get(idSite = modificationID)
                        except:
                            newAutoruModification = AutoruModification()

                        newAutoruModification.name                  = modificationName
                        newAutoruModification.idSite                = modificationID
                        newAutoruModification.model                 = autoru_model
                        newAutoruModification.engineVolume          = engineVolume
                        newAutoruModification.ProductionStartYear   = yearFrom
                        newAutoruModification.ProductionEndYear     = yearsTo
                        newAutoruModification.enginePower           = enginePower
                        newAutoruModification.typeEngine            = typeEngine
                        newAutoruModification.typeGear              = typeKpp
                        newAutoruModification.typeBody              = typeBody
                        newAutoruModification.idSiteTech            = idSiteTech
                        newAutoruModification.idSiteKonf            = idSiteKonf
                        newAutoruModification.idSiteGeneration      = idSiteGeneration
                        newAutoruModification.save()

                        complectations = modification[7]
                        if len(complectations) > 0:
                            countComplectation = 0
                            
                            while countComplectation < len(complectations):
                                complectationName   = complectations[countComplectation].text
                                complectationID     = complectations[countComplectation].get('id')
                                
                                newAutoruComplectation, created = AutoruComplectation.objects.filter(
                                    Q(idSite = complectationID) and Q(modification = newAutoruModification)).get_or_create(
                                        idSite = complectationID, modification = newAutoruModification)
                                #try:
                                #    newAutoruComplectation = AutoruComplectation.objects.get(idSite = complectationID, modification = newAutoruModification)
                                #except:
                                #    newAutoruComplectation = AutoruComplectation()
                                newAutoruComplectation.name         = complectationName
                                newAutoruComplectation.idSite       = complectationID
                                newAutoruComplectation.modification = newAutoruModification
                                newAutoruComplectation.save()
                                countComplectation = countComplectation + 1
    
            new_info        = RegInfoRefreshCatalog()
            new_info.date   = DT.datetime.now()
            new_info.site   = 'AUTO RU'
            new_info.save()
            
            os.remove(tmp_file)

    except:
        s = 1
        
def refresh_catalog_avito_ru():
    
    try:
        
        response    = requests.get(url_catalog_avitoru)
        if response.status_code == requests.codes.ok:
            
            path = default_storage.save('temp/catalog_avito_ru.xml', ContentFile(response.content))
            tmp_file = os.path.join(settings.MEDIA_ROOT, path)
                
            parser      = ETree.XMLParser(encoding="utf-8")
            tree        = ETree.parse(tmp_file, parser=parser)

            for mark in tree.getroot():
                mark_name       = mark.get('name')
                mark_id         = mark.get('id')
                mark_object     = get_object_avito(mark_name, mark_id, None)

                for model in mark.findall('Model'):
                    model_name          = model.get('name')
                    model_id            = model.get('id')
                    model_object        = get_object_avito(model_name, model_id, mark_object)

                    for generation in model.findall('Generation'):
                        generation_name         = generation.get('name')
                        generation_id           = generation.get('id')
                        generation_object       = get_object_avito(generation_name, generation_id, model_object)
                    
                        for modification in generation.findall('Modification'):
                            modification_name           = modification.get('name')
                            modification_id             = modification.get('id')
                            
                            type_drive_name             = modification.find('DriveType').text
                            type_engine_name            = modification.find('FuelType').text
                            type_transmission_name      = modification.find('Transmission').text
                            type_body_name              = modification.find('BodyType').text
                            doors_name                  = modification.find('Doors').text
                            year_to                     = modification.find('YearTo').text
                            year_from                   = modification.find('YearFrom').text
                            engine_power                = modification.find('Power').text
                            engine_volume               = modification.find('EngineSize').text

                            modification_object             = get_object_avito(modification_name, modification_id, generation_object)
                            modification_object.group       = False
                            modification_object.body        = get_ref_object('RefTypeBodyAvito', type_body_name)
                            modification_object.engine      = get_ref_object('RefTypeEngineAvito', type_engine_name) 
                            modification_object.kpp         = get_ref_object('RefTypeKPPAvito', type_transmission_name) 
                            modification_object.drive       = get_ref_object('RefTypeDriveAvito', type_drive_name) 
                            modification_object.doors           = int(doors_name) 
                            modification_object.year_end        = int(year_to) 
                            modification_object.year_star       = int(year_from) 
                            modification_object.engine_power    = int(engine_power) 
                            modification_object.engine_volume   = float(engine_volume) 
                            modification_object.save()

                            for complectations in modification.findall('Complectations'):
                                for complectation in complectations.findall('Complectation'): 
                                    complectation_id        = complectation.get('id')        
                                    complectation_name      = complectation.get('name')  
                                    complectation_object    = get_object_avito_complectation(complectation_name, complectation_id, modification_object)

            new_info        = RegInfoRefreshCatalog()
            new_info.date   = DT.datetime.now()
            new_info.site   = 'AVITO RU'
            new_info.save()
            
            os.remove(tmp_file)

    except:
        s = 1
        
def get_object_avito_complectation(name, id, parent):
    
    if len(id) > 0:
        id_int = int(id)
    else:
        id_int = 0

    avito_object = None

    if id_int > 0:
        avito_count = RefAvitoComplectation.objects.filter(avito_id = id_int).filter(avito_ref = parent).count()
        if avito_count == 0:
            avito_object = RefAvitoComplectation()
            avito_object.name           = name
            avito_object.avito_id       = id_int
            avito_object.avito_ref      = parent
            avito_object.save()
        else:
            avito_object = RefAvitoComplectation.objects.filter(avito_id = id_int).filter(avito_ref = parent)[0]
            if avito_object.name != name:
               avito_object.name = name
               avito_object.save()  

    else:
        avito_count = RefAvitoComplectation.objects.filter(name = name).filter(avito_ref = parent).count() 
        if avito_count == 0:
            avito_object = RefAvitoComplectation()
            avito_object.name       = name
            avito_object.avito_id   = id_int
            avito_object.avito_ref     = parent
            avito_object.save()
        else:
            avito_object = RefAvitoComplectation.objects.filter(name = name).filter(parent = parent)[0] 
    return avito_object

def get_object_avito(name, id, parent):
    
    if len(id) > 0:
        id_int = int(id)
    else:
        id_int = 0

    avito_object = None

    if id_int > 0:
        avito_count = RefAvito.objects.filter(avito_id = id_int).filter(parent = parent).count()
        if avito_count == 0:
            avito_object = RefAvito()
            avito_object.name       = name
            avito_object.avito_id   = id_int
            avito_object.parent     = parent
            avito_object.group      = True
            avito_object.save()
        else:
            avito_object = RefAvito.objects.filter(avito_id = id_int).filter(parent = parent)[0] 

    else:
        avito_count = RefAvito.objects.filter(name = name).filter(parent = parent).count() 
        if avito_count == 0:
            avito_object = RefAvito()
            avito_object.name       = name
            avito_object.avito_id   = id_int
            avito_object.parent     = parent
            avito_object.group      = True
            avito_object.save()
        else:
            avito_object = RefAvito.objects.filter(name = name).filter(parent = parent)[0] 
    return avito_object

def get_ref_object(model, name):
    z       = ContentType.objects.get(model=model.lower())
    ModelB  = apps.get_model(z.app_label, model)
    
    count = ModelB.objects.filter(name = name).count()
    if count == 0:
       ref_object = ModelB()
       ref_object.name = name
       ref_object.save()
       return ref_object
    else:
       return ModelB.objects.filter(name = name)[0] 


####
###
##
# Отправка почты по карточкам автомобилей 
@background(queue='send_push_car')
def start_send_push_car():
    send_push_car()

def send_push_car():

    from prices_car.models import EmailPushCar
    push_users = EmailPushCar.objects.exclude(send = True).exclude(user__email = '').order_by('date')
    
    for push_user in push_users:
        
        try:
            
            if push_user.car != None and push_user.price:
                
                emails      = re.sub(' ', '', push_user.email)
                to_emails   = emails.split(';')
                
                # plaintext   = get_template('email_car_price.txt')
                htmly       = get_template('email_car_price.html')
                
                car         = push_user.car

                car_name = '' + car.modification_autoru.model.mark.name + ' ' + car.modification_autoru.model.name + ', ' + car.vin.upper()
                
                comment         = push_user.comment
                unit_name       = car.unit.name
                car_mark        = car.modification_autoru.model.mark.name 
                car_model       = car.modification_autoru.model.name 
                car_modification    = car.modification_autoru.name
                car_complectation   = car.complectation_autoru.name
                car_year            = car.year
                car_run             = '{:,}'.format(car.run).replace(',', ' ')
                car_price           = '{:,}'.format(car.price).replace(',', ' ')
                car_photo_url       = 'https://ah.kors-group.com' + car.get_photo_mini()
                car_link            = 'https://ah.kors-group.com/cars/' + str(push_user.car.slug) + '/price/'

                d = ({
                        'car_name'      : car_name,
                        'comment'       : comment, 
                        'unit_name'     : unit_name, 
                        'car_mark'      : car_mark, 
                        'car_model'     : car_model,
                        'car_modification'  : car_modification,
                        'car_complectation' : car_complectation,
                        'car_year'          : car_year,
                        'car_run'           : car_run,
                        'car_price'         : car_price,
                        'car_photo_url'     : car_photo_url,
                        'car_link'          : car_link,
                    })

                subject, from_email, to = 'Карточка автомобиля - ' + car_name, settings.EMAIL_HOST_USER_INFO, to_emails
                
                # text_content = plaintext.render(d)
                html_content = htmly.render(d)
                
                msg = EmailMultiAlternatives(subject, html_content, settings.EMAIL_HOST_USER_INFO, to_emails)
                msg.attach_alternative(html_content, "text/html")
                msg.send()

                push_user.send = True
                push_user.save()
            elif push_user.car != None and push_user.calc != None:
                
                emails      = re.sub(' ', '', push_user.email)
                to_emails   = emails.split(';')
                
                # plaintext   = get_template('email_car_price.txt')
                htmly       = get_template('email_car_price_calc.html')
                
                car         = push_user.car

                car_name = '' + car.modification_autoru.model.mark.name + ' ' + car.modification_autoru.model.name + ', ' + car.vin.upper()
                
                comment         = push_user.comment
                unit_name       = car.unit.name
                car_mark        = car.modification_autoru.model.mark.name 
                car_model       = car.modification_autoru.model.name 
                car_modification    = car.modification_autoru.name
                if car.complectation_autoru != None:
                    car_complectation   = car.complectation_autoru.name
                else:
                    car_complectation   = "-"

                car_year            = car.year
                car_run             = '{:,}'.format(car.run).replace(',', ' ')
                car_price           = '{:,}'.format(car.price).replace(',', ' ')
                car_photo_url       = 'https://ah.kors-group.com' + car.get_photo_mini()
                car_link            = 'https://ah.kors-group.com/cars/deal/calculation/' + str(push_user.calc.id) + '/'

                d = ({
                        'car_name'      : car_name,
                        'comment'       : comment, 
                        'unit_name'     : unit_name, 
                        'car_mark'      : car_mark, 
                        'car_model'     : car_model,
                        'car_modification'  : car_modification,
                        'car_complectation' : car_complectation,
                        'car_year'          : car_year,
                        'car_run'           : car_run,
                        'car_price'         : car_price,
                        'car_photo_url'     : car_photo_url,
                        'car_link'          : car_link,
                    })

                subject, from_email, to = 'Калькуляция автомобиля - ' + car_name, settings.EMAIL_HOST_USER_INFO, to_emails
                
                # text_content = plaintext.render(d)
                html_content = htmly.render(d)
                
                msg = EmailMultiAlternatives(subject, html_content, settings.EMAIL_HOST_USER_INFO, to_emails)
                msg.attach_alternative(html_content, "text/html")
                msg.send()

                push_user.send = True
                push_user.save()
        except Exception as e:
            stt =  str(e)
    


####
###
##
# Отправка почты по интерактивным оценкам
@background(queue='send_push_estimation')
def start_send_push_estimation():
    send_push_estimation()

def send_push_estimation():
    
    push_users = RegInteractivOcenkaEmailPush.objects.exclude(send = True).exclude(user__email = '').order_by('date')
    
    for push_user in push_users:
        try:
            
            if push_user.message_websoket:
                js = json.loads(push_user.comment)
                send_message_socket(message=js)

            if push_user.rlk != None:
                emails      = re.sub(' ', '', push_user.email)
                to_emails   = emails.split(';')
                plaintext   = get_template('email_eco.txt')
                htmly       = get_template('email_eco.html')
                
                ref = 'https://ah.kors-group.com/eco/' + str(push_user.rlk.id)
                
                estimation = push_user.estimation 
                car = '' + estimation.modification.model.mark.name + ' ' + estimation.modification.model.name + ' ' + estimation.modification.name + ' ' + str(estimation.year)
                
                if estimation.staff != None:
                    staff = estimation.staff.name
                else:
                    staff = ''

                d = ({
                        'vin'       : push_user.estimation.vin, 
                        'ref'       : ref, 
                        'comment'   : push_user.comment, 
                        'car'       : car,
                        'staff'     : staff
                    })

                subject, from_email, to = 'Интерактивная оценка - ' + push_user.estimation.vin + ' ' + car, settings.EMAIL_HOST_USER_INFO, to_emails
                
                text_content = plaintext.render(d)
                html_content = htmly.render(d)
                
                msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER_INFO, to_emails)
                msg.attach_alternative(html_content, "text/html")
                msg.send()

                push_user.send = True
                push_user.save()
            else:
                emails      = re.sub(' ', '', push_user.email)
                to_emails   = emails.split(';')
                plaintext   = get_template('email_eco.txt')
                htmly       = get_template('email_eco.html')
                
                ref = 'https://ah.kors-group.com/eco/' + str(push_user.estimation.rlk.id)
                
                estimation = push_user.estimation 
                car = '' + estimation.modification.model.mark.name + ' ' + estimation.modification.model.name + ' ' + estimation.modification.name + ' ' + str(estimation.year)
                
                if estimation.staff != None:
                    staff = estimation.staff.name
                else:
                    staff = ''

                d = ({
                        'vin'       : push_user.estimation.vin, 
                        'ref'       : ref, 
                        'comment'   : push_user.comment, 
                        'car'       : car,
                        'staff'     : staff
                    })

                subject, from_email, to = 'Интерактивная оценка - ' + push_user.estimation.vin + ' ' + car, settings.EMAIL_HOST_USER_INFO, to_emails
                
                text_content = plaintext.render(d)
                html_content = htmly.render(d)
                
                msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER_INFO, to_emails)
                msg.attach_alternative(html_content, "text/html")
                msg.send()

                push_user.send = True
                push_user.save()

        except Exception as e:
            stt =  str(e)
    

####
###
##
# Отправка данных в корсавто
@background(queue='start_swap_estimation')
def start_swap_estimation():
    swap_estimation()

def estimation_send_1c(rlk_id, id):
    
    interactiv_rlk = RegInteractivOcenkaRLK.objects.filter(rlk__id = rlk_id).filter(estimation__id = id).first()
    estimation  = interactiv_rlk.estimation
    rlk         = interactiv_rlk.rlk
    js_data = {
        'Type'          : 'estimation',
        'Rlk'           : DocRLKSerializer(rlk, many=False).data,
        'Estimation'    : RegInteractivOcenkaSerializer(estimation, many=False).data,
        'Soglasovanie'  : RegInteractivOcenkaSoglasovanieSerializer(interactiv_rlk.page_soglasovanie, many=False).data,
        'Info'          : RegInteractivOcenkaRLKSerializer(interactiv_rlk, many=False).data,
    }
    if rlk.unit == None:
        response = requests.post(url_hs_kors_auto, json=js_data)
    else:
        if rlk.unit.ib.alfa:
            response = requests.post(url_hs_alfa_auto, json=js_data)
        else:
            response = requests.post(url_hs_kors_auto, json=js_data)

    return response.status_code
    

def swap_estimation():
    
    infos = RegSwapKors.objects.filter(status_code = 60).order_by('rlk','date')
    #infos = RegSwapKors.objects.filter(id = 938747).order_by('rlk','date')
    for info in infos:
        if info.estimation != None and info.rlk != None:
            try:
                interactiv_rlk = RegInteractivOcenkaRLK.objects.filter(rlk__id = info.rlk.id).filter(estimation__id = info.estimation.id).first()
                estimation  = interactiv_rlk.estimation
                rlk         = interactiv_rlk.rlk
                js_data = {
                    'Type'          : 'estimation',
                    'Rlk'           : DocRLKSerializer(rlk, many=False).data,
                    'Estimation'    : RegInteractivOcenkaSerializer(estimation, many=False).data,
                    'Soglasovanie'  : RegInteractivOcenkaSoglasovanieSerializer(interactiv_rlk.page_soglasovanie, many=False).data,
                    'Info'          : RegInteractivOcenkaRLKSerializer(interactiv_rlk, many=False).data,
                }
                unit = rlk.unit
                if unit == None:
                    unit = rlk.unit_dc
                if unit.ib.alfa:
                    response = requests.post(url_hs_alfa_auto, json=js_data)
                else:
                    response = requests.post(url_hs_kors_auto, json=js_data)
                #if response.status_code == 200:
                info.status_code = 200
                info.status = 'Ok'
                info.status_date = DT.datetime.now()
                info.save()
            except:
                s = 1
            #else:
            #    s = 1
                
        elif info.rlk != None:
            try:
                js_data = {
                    'Type'  : 'rlk', 
                    'Rlk'   : DocRLKSerializer(info.rlk, many=False).data        
                }
                unit = info.rlk.unit
                if unit == None:
                    unit = info.rlk.unit_dc
                if unit != None and unit.ib.alfa:
                    response = requests.post(url_hs_alfa_auto, json=js_data)
                else:
                    response = requests.post(url_hs_kors_auto, json=js_data)
                #response = requests.post(url_hs_kors_auto, json=js_data)
                if response.status_code == 200:
                    info.status_code = 200
                    info.status = 'Ok'
                    info.status_date = DT.datetime.now()
                    info.save()
                else:
                    s = 1
            except:
                s = 1   

    s = 1
    
def send_files_estimations():
    data            = RegRegInteractivOcenkaFiles.objects.get(pk = 28132)
    uin             = data.estimation.rlk.uin
    type_capture    = data.type_file
    order           = data.file_number
    file_encode     = ''
    
    if not data.blank:
        file_text   = open(data.file.file.name, 'rb')
        file_read   = file_text.read()
        file_encode = base64.b64encode(file_read)

    json_data = {
        'Type'          : 'estimation_files',
        'uin'           : uin,
        'type_capture'  : type_capture,
        'order'         : order,
        'captyre'       : file_encode
    }
    response = requests.post(url_hs_kors_auto, json=json_data)
    if response.status_code == 200:
        s = 1


####
###
##
# Обновление прайс листов
@background(queue='refresh_price')
def start_refresh_price():
    refresh_price()

def refresh_price():
    
    task_prices = TaskRegPrices.objects.exclude(status = 'Обработан').exclude(status = 'Ошибка')
    #task_prices = TaskRegPrices.objects.filter(id = 133)

    for task in task_prices:
       
        task.status = 'Начата обработка'
        task.save()

        try:
            wb = load_workbook(task.path_file_price)
            worksheet       = wb.active
            settings_reg    = task.settings
            positions_row   = worksheet.max_row
            column_max      = worksheet.max_column

            start_row         = settings_reg.start_row
            number_name       = settings_reg.number_name
            number_article    = settings_reg.number_article
            number_category   = settings_reg.number_category
            number_group      = settings_reg.number_group
            number_price_min  = settings_reg.number_price_min
            number_price      = settings_reg.number_price
            number_manufacturer = settings_reg.number_manufacturer
            email_push        = settings_reg.email_push

            manufacturer        = settings_reg.manufacturer
            count_success       = 0
            start_row           = max(task.positions_success, start_row) 

            for row in range(start_row, positions_row):
                try:
                    name            = ''
                    article         = ''
                    article_search  = ''
                    category        = None
                    group           = None
                    price_min       = 0
                    price           = 0

                    if number_name > 0:
                        name                = worksheet.cell(row = row, column = number_name).value
                    
                    if number_manufacturer > 0:
                        manufacturer_col = worksheet.cell(row = row, column = number_manufacturer).value
                        manufacturer        = get_refManufacturer(manufacturer_col)
                    
                    if number_article > 0:
                        article             = worksheet.cell(row = row, column = number_article).value
                        article_search      = re.sub("[^A-Za-z А-Яа-я 0-9]", "", article).rstrip() 
                    
                    if number_category > 0:
                        category            = worksheet.cell(row = row, column = number_category).value
                        if category != None:
                            category = get_refCategoryProduct(category)
                    
                    if number_group > 0:
                        group               = worksheet.cell(row = row, column = number_group).value
                        if group != None:
                            group = get_refGroupProduct(group)                          
                    
                    if number_price_min > 0:
                        try:
                            price_min           = str(worksheet.cell(row = row, column = number_price_min).value)
                            if len(price_min) == 0:
                                price = '0.00'

                            if price_min.find('.') < 0 and price_min.find(',') < 0:
                                price_min = price_min + '.00'
                            price_min           = float(re.sub('[^\d\.,]', '', str(price_min.replace(',','.'))))
                        except:
                            price_min = 0
                    
                    if number_price > 0:
                        try:
                            price               = str(worksheet.cell(row = row, column = number_price).value)
                            
                            if len(price) == 0:
                                price = '0.00'

                            if price.find('.') < 0 and price.find(',') < 0:
                                price = price + '.00'

                            price               = float(re.sub('[^\d\.,]', '', str(price.replace(',','.')))) 
                        except:
                            price = 0

                    if len(name) > 0 and len(article) > 0:
                        
                        reg_price, created = RegPrices.objects.filter(Q(manufacturer = manufacturer) 
                                                            and Q(article_search = article_search)).get_or_create(manufacturer = manufacturer,
                                article_search = article_search
                            )
                        reg_price.date              = DT.datetime.now()
                        reg_price.task              = task
                        reg_price.name              = name
                        reg_price.article           = article
                        reg_price.article_search    = article_search
                        reg_price.category          = category
                        reg_price.group             = group
                        reg_price.price             = price
                        reg_price.price_min         = price_min
                        reg_price.save()

                        #count_success = count_success + 1
                    
                    #task.positions_success = count_success
                    #task.save()
                except:
                    s = 1

            names = RefManufacturer.objects.filter(pk__in = RegPrices.objects.filter(task = task).values('manufacturer').distinct()).order_by('name')
            names_str = ''
            for name in names:
                names_str = names_str + name.name + '; '
            settings_reg.name = names_str
            settings_reg.save()

            task.positions_success  = task.count_success()         
            task.status             = 'Обработан'
            task.save()

        except:

            task.status = 'Ошибка'
            task.save()

        if task.settings.email_push != None and len(task.settings.email_push) > 0:
            
            emails      = re.sub(' ', '', task.settings.email_push)
            to_emails   = emails.split(';')
            plaintext   = get_template('email_price.txt')
            htmly       = get_template('email_price.html')
            
            page_price = 'https://ah.kors-group.com/prices_lists/' + str(task.id)
            
            d = ({'task': task, 'page_price': page_price})

            subject, from_email, to = 'Обработан прайс лист', settings.EMAIL_HOST_USER_INFO, to_emails
            
            text_content = plaintext.render(d)
            html_content = htmly.render(d)
            
            msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER_INFO, to_emails)
            msg.attach_alternative(html_content, "text/html")
            msg.send()

def get_refGroupProduct(name):
    refCount = RefGroupProduct.objects.filter(name = name).count()
    if refCount > 0:
        ref = RefGroupProduct.objects.filter(name = name)[0]
        return ref
    else:
        ref = RefGroupProduct()
        ref.name = name
        return ref.save()
    
def get_refCategoryProduct(name):
    refCount = RefCategoryProduct.objects.filter(name = name).count()
    if refCount > 0:
        ref = RefCategoryProduct.objects.filter(name = name)[0]
        return ref
    else:
        ref = RefCategoryProduct()
        ref.name = name
        return ref.save()

def get_refManufacturer(name):
    refCount = RefManufacturer.objects.filter(name = name).count()
    if refCount > 0:
        ref = RefManufacturer.objects.filter(name = name)[0]
        return ref
    else:
        return None


####
###
##
# История робомойки
@background(queue='refresh_wash')
def start_refresh_wash():
    refresh_wash()

def refresh_wash():
   
    header = {
        'X-Request-ID' : "4a68aa75-d369-4fcf-bb94-1863ffd704f5"
    }
    token = get_token_wash(header)
    
    if len(token) > 0:
        id_washs = list()
        id_washs.append(56)
        id_washs.append(57)
        header['Authorization'] = f"Bearer {token}"
        
        for id_wash in id_washs:
            date_time_end = DT.datetime.now() - DT.timedelta(hours=1)
            date_info_start = DT.datetime.now() 
            while date_time_end < date_info_start:
                data_id_info = Bi_wash.objects.filter(wash_id = id_wash).order_by('-date_time')
                if len(data_id_info) > 0:
                    date_time_start = data_id_info[0].date_time
                else:
                    date_time_start = DT.datetime(year=2023, month=8, day=1, hour=0, minute=0)
                date_time_end = date_time_start + DT.timedelta(days=2)
                if date_time_end > DT.datetime.now():
                   date_time_end = DT.datetime.now() 
                infos = get_wash(id_wash, header, date_time_start, date_time_end)
                for info in infos:
                    date    = info['date'] + DT.timedelta(hours=3)
                    count   = Bi_wash.objects.filter(card_number = info['card_number']).filter(date_time = date).filter(wash_id = info['wash_id']).filter(amount = info['amount']).filter(payment_type = info['payment_type']).filter(subject = info['subject']).count()
                    if count == 0:
                        wash                = Bi_wash()
                        wash.date_time      = date
                        wash.wash_id        = info['wash_id']
                        wash.card_number    = info['card_number']
                        wash.amount         = info['amount']                    
                        wash.source_type    = info['source_type']
                        wash.source_number  = info['source_number']
                        wash.dest_type      = info['dest_type']
                        wash.dest_number    = info['dest_number']
                        wash.payment_type   = info['payment_type']
                        wash.subject        = info['subject']
                        wash.save()
                    
    s = 1

def get_wash(id_wash, header, time_start, time_end):
     
    data_list   = list() 
    offset      = 0
    unix_start  = str(int(datetime.timestamp(time_start)))
    unix_end    = str(int(datetime.timestamp(time_end)))
    offset_while = True
     
    while offset_while:
        url         = url_wash + 'finance?include_all=true&wash_id=' + str(id_wash) + '&start_time=' + unix_start + '&end_time=' + unix_end + '&limit=' + str(limit_wash) + '&offset=' + str(offset)
        response    = requests.get(url, headers=header)
        if response.status_code == 200:
            data    =  json.loads(response.text)
            for data_info in data['data']:
                card_number = data_info['card_number']
                if card_number == None:
                    card_number = ''

                info = {
                    'date'              : DT.datetime.utcfromtimestamp(data_info['date_time']),
                    'amount'            : data_info['amount'],
                    'wash_id'           : id_wash,
                    'source_type'       : data_info['source']['type'],
                    'source_number'     : data_info['source']['number'],
                    'dest_type'         : data_info['dest']['type'],
                    'dest_number'       : data_info['dest']['number'],
                    'payment_type'      : data_info['payment_type'],
                    'card_number'       : card_number,
                    'subject'           : str(data_info['subject']).replace("['", "").replace("']", "")
                }
                data_list.append(info)
            if len(data['data']) == 0:
                offset_while    = False
            offset  = offset + limit_wash
        else:
            offset_while    = False
    return data_list
    
def get_token_wash(header):
    
    url = url_wash + 'token'

    response = requests.post(url, headers=header, auth=HTTPBasicAuth(login_wash, password_wash))
    
    if response.status_code == 200:
        return json.loads(response.text).get('access_token', '')
    return ''
    

####
####
###
##
# Автохаб
@background(queue='refresh_autohub')
def start_refresh_autohub():
    
    refresh_autohub()
    
def refresh_autohub():
    
    username       = "korsgroup@maxposter.ru"
    password        = "pJ%[QwwqH,YxP9J-"
    url             = "api.maxposter.ru"
    URL_TEMPLATE    = "https://api.maxposter.ru/partners-api/vehicles/active"
    token = 'a29yc2dyb3VwQG1heHBvc3Rlci5ydTpwSiVbUXd3cUgsWXhQOUot'
    headers = { 'Authorization' : 'Basic %s' % token }

    date = DT.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    page = 0
    send = True
    list_car    = list()
    
    list_filter = list()
    vin = {
        'fields'    : 'vin',
        'type'      : 'equal',
        'value'     : 'SJNJBNJ10U7177072'
    }
    #list_filter.append(vin)

    while send:
        filters = {
            "limit"     : 100,
            "offset"    : page * 100,
            "filters"   : list_filter,
            "orders": [
                        "-id"
                    ]
        }
        #r           = requests.post(URL_TEMPLATE, auth=HTTPBasicAuth(username, password), data=json.dumps(filters))
        r           = requests.post(URL_TEMPLATE, auth=HTTPBasicAuth(username, password), json=filters)
        res_status  = r.status_code
        if res_status == 200:
            data_info   = json.loads(r.text)

            info_data   = data_info['data']
            list_cars   = info_data['vehicles']
            
            if len(list_cars) == 0:
                send = False

            for car in list_cars:
                id_vencle       = car.get('id')
                vin             = car.get('vin')
                if vin == None:
                    vin = car.get('bodyNumber')
                delete_autohub(date, id_vencle)
                
                new_autohub = Avtohub()
                new_autohub.date        = date
                new_autohub.vin         = vin
                new_autohub.id_vencle   = id_vencle
                
                uin                     = car.get('uin')
                new_autohub.uin         = uin

                price           = car.get('price')
                new_autohub.price       = price

                dealer          = car.get('dealer')
                dealer_name     = dealer.get('companyName')
                new_autohub.dealer_name = dealer_name
                
                used                    = car.get('type')
                new_autohub.type = used
                
                year    = car.get('year')
                new_autohub.year = 0 if year is None else year

                mileage                 = car.get('mileage')
                new_autohub.mileage = 0 if mileage is None else mileage

                isInSale                = car.get('isInSale')
                new_autohub.isInSale = False if isInSale is None else isInSale 

                daysInStock             = car.get('daysInStock')
                new_autohub.daysInStock = 0 if daysInStock is None else daysInStock 

                daysInSale              = car.get('daysInSale')
                new_autohub.daysInSale = 0 if daysInSale is None else daysInSale 

                maxposterSaleCost       = car.get('maxposterSaleCost')
                new_autohub.maxposterSaleCost = 0 if maxposterSaleCost is None else maxposterSaleCost

                imv          = car.get('imv')
                new_autohub.imv = 0 if imv is None else imv 

                avgMarketPrice          = car.get('avgMarketPrice')
                new_autohub.avgMarketPrice = 0 if avgMarketPrice is None else avgMarketPrice 

                vRatingPosition         = car.get('vRatingPosition')
                new_autohub.vRatingPosition = 0 if vRatingPosition is None else vRatingPosition

                numberOfCompetitors     = car.get('numberOfCompetitors')
                new_autohub.numberOfCompetitors = 0 if numberOfCompetitors is None else numberOfCompetitors

                liquidity               = car.get('liquidity')
                if liquidity != None:
                    actualMarketSales       = liquidity.get('actualMarketSales') 
                    new_autohub.actualMarketSales = 0 if actualMarketSales is None else actualMarketSales

                    averageSalePeriod       = liquidity.get('averageSalePeriod')
                    new_autohub.averageSalePeriod = 0 if averageSalePeriod is None else averageSalePeriod

                    averageMarketMileage    = liquidity.get('averageMarketMileage') 
                    new_autohub.averageMarketMileage = 0 if averageMarketMileage is None else averageMarketMileage

                    averageDaysInSale       = liquidity.get('averageDaysInSale') 
                    new_autohub.averageDaysInSale = 0 if averageDaysInSale is None else averageDaysInSale 

                    totalMarketSales        = liquidity.get('totalMarketSales') 
                    new_autohub.totalMarketSales = 0 if totalMarketSales is None else totalMarketSales
                    
                    totalMarketSales90      = liquidity.get('totalMarketSales90') 
                    new_autohub.totalMarketSales90 = 0 if totalMarketSales90 is None else totalMarketSales90

                advertisingCosts        = car.get('advertisingCosts')
                if advertisingCosts != None:
                    totalAdvertisingCost    = advertisingCosts.get('totalAdvertisingCost')
                    new_autohub.totalAdvertisingCost = totalAdvertisingCost

                    placementOnAutoru       = advertisingCosts.get('placementOnAutoru')
                    new_autohub.placementOnAutoru = placementOnAutoru

                    promotionOnAutoru       = advertisingCosts.get('promotionOnAutoru')
                    new_autohub.promotionOnAutoru = promotionOnAutoru

                    placementOnAvito        = advertisingCosts.get('placementOnAvito')
                    new_autohub.placementOnAvito = placementOnAvito

                    promotionOnAvito        = advertisingCosts.get('promotionOnAvito')
                    new_autohub.promotionOnAvito = promotionOnAvito

                    placementOnDrom         = advertisingCosts.get('placementOnDrom')
                    new_autohub.placementOnDrom = placementOnDrom

                    promotionOnDrom         = advertisingCosts.get('promotionOnDrom')
                    new_autohub.promotionOnDrom = promotionOnDrom
                
                callsCounts         = car.get('callsCounts')
                if callsCounts != None:
                    callsCounts_uniqueTotal         = callsCounts.get('uniqueTotal')
                    new_autohub.callsCounts_uniqueTotal = callsCounts_uniqueTotal

                    callsCounts_uniqueTotalAutoru   = callsCounts.get('uniqueTotalAutoru')
                    new_autohub.callsCounts_uniqueTotalAutoru = callsCounts_uniqueTotalAutoru

                    callsCounts_uniqueTotalAvito    = callsCounts.get('uniqueTotalAvito')
                    new_autohub.callsCounts_uniqueTotalAvito = callsCounts_uniqueTotalAvito

                    callsCounts_uniqueTotalDrom     = callsCounts.get('uniqueTotalDrom')
                    new_autohub.callsCounts_uniqueTotalDrom = callsCounts_uniqueTotalDrom


                chatsCounts         = car.get('chatsCounts')
                if chatsCounts != None:
                    chatsCounts_uniqueTotal         = chatsCounts.get('uniqueTotal')
                    new_autohub.chatsCounts_uniqueTotal = chatsCounts_uniqueTotal

                    chatsCounts_uniqueTotalAutoru   = chatsCounts.get('uniqueTotalAutoru')
                    new_autohub.chatsCounts_uniqueTotalAutoru = chatsCounts_uniqueTotalAutoru

                    chatsCounts_uniqueTotalAvito    = chatsCounts.get('uniqueTotalAvito')
                    new_autohub.chatsCounts_uniqueTotalAvito = chatsCounts_uniqueTotalAvito

                    chatsCounts_uniqueTotalDrom     = chatsCounts.get('uniqueTotalDrom')
                    new_autohub.chatsCounts_uniqueTotalDrom = chatsCounts_uniqueTotalDrom

                autotekaReportLinks      = car.get('autotekaReportLinks')
                if autotekaReportLinks != None:
                    new_autohub.autotekaReportWeb = autotekaReportLinks.get('web')
                    new_autohub.autotekaReportPdf = autotekaReportLinks.get('pdf')

                siteStates      = car.get('siteStates')
                if siteStates != None:
                    for site_info in siteStates:
                        
                        site_info_site       = site_info.get('site')
                        site_avtohub    = get_site_avtohub(site_info_site)
                        
                        site_avtohub_object = AvtohubSiteInfo()
                        site_avtohub_object.date        = date
                        site_avtohub_object.id_vencle   = id_vencle
                        site_avtohub_object.vin         = vin
                        site_avtohub_object.uin         = uin
                        site_avtohub_object.site        = site_avtohub
                        site_avtohub_object.externalState   = site_info.get('externalState')
                        if site_info['externalURL'] != '':
                            s =1
                        site_avtohub_object.externalURL     = site_info.get('externalURL')
                        site_avtohub_object.hasProblems     = site_info.get('hasProblems')
                        site_avtohub_object.save()

                viewStatistics      = car.get('viewStatistics')
                if viewStatistics != None:
                    avitoViews          = viewStatistics.get('avitoViews')
                    new_autohub.avitoViews = avitoViews

                    autoruViews         = viewStatistics.get('autoruViews')
                    new_autohub.autoruViews = autoruViews

                    dromViews           = viewStatistics.get('dromViews')
                    new_autohub.dromViews = dromViews
                
                new_autohub.save()
                updatedAt = car.get('updatedAt')

            page = page + 1

def delete_autohub(date, id_vencle):
    Avtohub.objects.filter(date= date, id_vencle = id_vencle).delete()

def get_site_avtohub(site_info):
    sites = AvtohubSite.objects.filter(id_site = site_info.get('id'))
    if len(sites) == 0:
        site = AvtohubSite()
        site.name       = site_info.get('name')
        site.id_site    = site_info.get('id')
        site.save()
        return site
    else:
       return sites[0] 


####
###
##
# История звонков
def start_hystory_call():
    start_hystory_call_task(schedule = 60, repeat = 600, verbose_name = "История_звонков")

@background(queue='hystory_cals')
def start_hystory_call_task():
    refresh_history_task()


####
###
##
# Мониторинг
def start_back_monitoring():
    #board_monitoring()
    #start_cvc_get_info_background(schedule = 1, repeat = 3600, verbose_name = "CVC - get info")
    board_monitoring(schedule = 60, repeat = 300, verbose_name = "Мониторинг")
    #start_queue_recognition_kg(schedule = 1, repeat = 3600, verbose_name = "queue_recognition_kg")

@background(queue='monitoring')
def board_monitoring():
    error_list = list()
    path = "//a01srvfs/ftp"
    dirs = os.listdir(path)
    ip_list = list()
    ip_errors = False
    for dir in dirs:
        pathdir = path + "/" + dir
        if os.path.isdir(pathdir) and pathdir.find("ip_") > 0 and pathdir.find("ip_backup") < 0:
            name = dir
            files_ip = list()
            dirs_ip = os.listdir(pathdir)
            for dir_ip in dirs_ip:
                if os.path.isfile(pathdir + '/' + dir_ip):
                    namefile = dir_ip
                    try:
                        sizefile = os.path.getsize(path + '/' + dir + '/' + namefile)
                    except Exception:
                        sizefile = 0  
                    json_files_ip = {
                        'name': namefile,
                        'size': int(sizefile / 1024)
                    }
                    if int(sizefile / 1024) > 10:
                        ip_errors = True
                        error_list.append("Облако " + name + " - " + str(int(sizefile / 1024)) + " кб")
                    files_ip.append(json_files_ip)
            json_ip = {
                'name': name,
                'files': files_ip
            }
            ip_list.append(json_ip)

    #КорсАвто
    #Проверка веб сервиса корсавто
    answer_kors_avto = False
    try:
        ping_korsavto = requests.get('http://a01srv1cka/zbusiness/hs/mb/activesession', timeout=1)
    except:
        error_list.append("Корс авто веб-сервис - "  + "нет ответа")
        answer_kors_avto = False
    else:
        answer_kors_avto = True
    count_swap = 0
    try:
        answer = requests.get('http://a01srv1cka/zbusiness/hs/mb/info_svap', timeout=2)
        answer_json = answer.json()
        count_swap = answer_json.get('Swap')
        if count_swap > 50:
            error_list.append("Корс авто - "  + count_swap + " документов в обмене")
    except:
        count_swap = 888888
        error_list.append("Корс авто - " + " нет ответа по документам")
    answer_bu_avito = False
    
    #ИП Кострюков
    #Проверка доступности файлообменика 
    try:
        ping_answer_bu_avito = requests.get('http://194.87.107.139:55510', timeout=1)
    except:
        answer_bu_avito = False
        error_list.append("ИП Кострюков - " + " что то не так с доступон к файлам авито")
    else:
        answer_bu_avito = True
    

    #ОПФУ Сводная
    #данные на выгрузку
    count_swap_opfu = 0
    try:
        answer = requests.get('http://a01-srv-1c03/rsvodopfu/hs/mb/info_svap', timeout=2)
        answer_json = answer.json()
        count_swap_opfu = answer_json.get('Swap')
    except:
        count_swap_opfu = 888888

    if count_swap_opfu > 100:
        error_list.append("ОПФУ Главная  - "  + str(count_swap_opfu) + " документов в обмене")
        #board_monitoring_alert_telegram('Отправка в ДЦ - есть проблемы - ' + str(count_swap_opfu)  + " - это плохо")

    space_disk_free = float('{:.3f}'.format(get_free_space_mb('D:\\')))
    
    
    # Логи Повер БИ
    power_bi = list()

    logs    = Bi_logs.objects.values('bi_model').annotate(max_date = Max('date')).order_by('bi_model')
    start   = DT.datetime.today() + DT.timedelta(days=-1)
    start   = start.combine(start.date(), start.min.time())
        
    for log in logs:
        info    = Bi_logs.objects.filter(bi_model = log['bi_model']).filter(date = log['max_date'])
        add     = 0
        delite  = 0
        filtr   = ''
        if len(info) == 1:
            add     = info[0].count_add
            delite  = info[0].count_delite
            filtr   = info[0].filtr
        title = log['bi_model']
        error = log['max_date'].timestamp() < start.timestamp()
        error_int = 0
        if not error:
            if add < delite:
                error_int = 1
        else:
            error_int = 2

        data = {
            'date'      : log['max_date'],
            'title'     : title,
            'error'     : error_int,
            'add'       : add,
            'delite'    : delite,
            'filtr'     : filtr,
        }
        power_bi.append(data)

    

    #Проверка веб-сервисов баз дц
    refs_ib_list = list()
    refs_ib = RefIb.objects.all().order_by('name')
    url_suf = '/ws/DCChange.1cws?wsdl'
    #url_suf = 'hs/mb/'
    error_ib_dc = False
    for ib in refs_ib:
        url         = 'http://' + ib.server.lower() + '/' + ib.base.lower() + url_suf
        try:
            response    = requests.post(url, timeout=2)
            status      = int(response.status_code)
        except:
            status = 400
       
        if status != 200:
            name_ib = ib.server.lower() + '/' + ib.base.lower()
            #error_list.append("HTTP - " + name_ib + " надо проверить")   
        
    if len(error_list) > 0:
        board_monitoring_alert_telegram(error_list)
    
def get_free_space_mb(folder):
    """ Return folder/drive free space (in bytes)
    """
    if platform.system() == 'Windows':
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(folder), None, None, ctypes.pointer(free_bytes))
        return free_bytes.value/1024/1024/1024 
    else:
        st = os.statvfs(folder)
        return st.f_bavail * st.f_frsize/1024/1024

def board_monitoring_alert_telegram(error_list):
    #https://api.telegram.org/bot5936060836:AAHvjlsiWmlZMv44pNdsD4-LW3HGo5Zr274/getUpdates
    text = ''
    list_answer = list()
    list_answer.append("382698912")
    for error_text in error_list:
        text = text + error_text + "\n"
    token       = "5936060836:AAHvjlsiWmlZMv44pNdsD4-LW3HGo5Zr274"
    url         = "https://api.telegram.org/bot"
    url += token
    method = url + "/sendMessage"

    for answer in list_answer:
        channel_id  = answer
        r = requests.post(method, data={
            "chat_id"  : channel_id,
            "text"     : text
            })

        if r.status_code != 200:
            raise Exception("post_text error")


####
###
##
# KG
@background(queue='queue_recognition_kg')
def start_queue_recognition_kg():
    refresh_queue_recognition()


####
###
##
# CVC
@background(queue='cvc_get_info')
def start_cvc_get_info_background():
    cvc_get_info()

def get_sale_to_day_rlk(rlk):
    date_start  = rlk.dataTime.replace(hour = 0)
    date_end    = rlk.dataTime.replace(hour = 23)
    count = DocRLKEvents.objects.filter(rlk = rlk).filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(contacType__id = 17).count()    
    if count > 0:
        return True
    return False


#def start_cvc_background():
#    cvc_background(schedule = 1, repeat = 86400, verbose_name = "CVC")

#@background()
@background(queue='cvc_send_records')
def cvc_background():
   
    date_end        = DT.datetime.now()
    date_start      = date_end + DT.timedelta(days=-21)
    
    #if date_end.hour > 22 or date_end.hour < 6:
    try:
        recs = Records_voice_recorder_cvc_checklist.objects.filter(rlk__dataTime__lt = date_start).filter(success = False)
        for rec in recs:
            rec.success = True
            rec.save()
    except:
        bo = 1
    
    #records_query   = Records_voice_recorder.objects.filter(pk = 472241).filter(date__gte = date_start).filter(date__lt = date_end).filter(time__gt = 0).order_by('date')

    records_query   = Records_voice_recorder.objects.filter(date__gte = date_start).filter(date__lt = date_end).filter(time__gt = 0).order_by('-date')
    subquery        = Subquery(Records_voice_recorder_cvc.objects.filter(records__id = OuterRef(name='id')).values('id')[:1])        
    records_query   = records_query.annotate(send = Count(subquery))
    #records_query   = Records_voice_recorder.objects.filter(pk= 113348)
    send_count_max  = 25
    send_count      = 0
    for record_query in records_query:
        if record_query.send == 0:
            if send_count < send_count_max:
                cvc_get_record_info(record_query)
                if Records_voice_recorder_cvc.objects.filter(records = record_query).count() > 0: 
                    send_count = send_count + 1                    
            else:
                break

    '''
    cvc_get_info()
    refresh_queue_recognition()
    
    date_end    = DT.datetime.now()
    date_start  = date_end + DT.timedelta(days=-7)

    #date_end    = DT.datetime.now().replace(day=29, hour=23)
    date_start  = DT.datetime.now().replace(month=2, day=1, hour=1)
    #records_query = Records_voice_recorder.objects.filter(user__id = 209).filter(date__gte = date_start).filter(date__lt = date_end).order_by('date')
    
    records_query = Records_voice_recorder.objects.filter(date__gte = date_start).filter(date__lt = date_end).order_by('date')
    
    for record_query in records_query:
        cvc_get_record_info(record_query)
    
    '''

def sleep(times):
    s = 1
    while s < 10000:
        s = s + 1
    return 0
        
def refresh_check_list_info(checklists_cvc_info):
    for check in checklists_cvc_info:
        check_list = Check_settings_cvc.objects.filter(id_cvc = check['checklist_id'])
        if len(check_list) == 0:
            check_list =  Check_settings_cvc()
            check_list.name       = check['name']
            check_list.id_cvc     = check['checklist_id']
            check_list.save()
        
def cvc_get_info(rlk_id=None):
    
    date_start = DT.datetime.now() + DT.timedelta(days=-7)
    date_start = date_start.replace(year=2024, month=1, day = 1, hour = 0, minute=0, second=0, microsecond=0)
    
    if rlk_id == None:
        list_checklist_cvc = Records_voice_recorder_cvc_checklist.objects.filter(success = False).filter(rlk__dataTime__gte = date_start)
    else:
        list_checklist_cvc = Records_voice_recorder_cvc_checklist.objects.filter(success = False).filter(rlk__id = rlk_id)
    #list_checklist_cvc = Records_voice_recorder_cvc_checklist.objects.filter(pk = 145588)
    
    token = get_token()
    if len(token) > 0:
        for check_list in list_checklist_cvc:
            id      = check_list.rlk.id
            rlk     = DocRLK.objects.get(pk = id)
            info    = get_check_cvc(token, id)
            if len(info) > 3:
                company = False
                Records_voice_recorder_cvc_checklist_tematics.objects.filter(checklist = check_list).delete()
                js                              = json.loads(info)
                checklists_cvc_info = js['checklists']
                
                refresh_check_list_info(checklists_cvc_info) 

                id_check_cvc = 0
                if check_list.сheck_settings != None:
                    if check_list.сheck_settings.check_settings_cvc != None:
                        id_check_cvc = check_list.сheck_settings.check_settings_cvc.id_cvc
                
                cvc_checklists = None

                if id_check_cvc != 0:
                    for checklist_cvc_info in checklists_cvc_info:
                        if id_check_cvc == checklist_cvc_info['checklist_id']:
                            cvc_checklists = checklist_cvc_info    

                if cvc_checklists == None:
                    if len(checklists_cvc_info) > 1:
                        cvc_checklists                  = checklists_cvc_info[len(checklists_cvc_info)-1]
                    else:
                        cvc_checklists                  = checklists_cvc_info[0]
                
                worked_dictionaries             = cvc_checklists['worked_dictionaries']
                dictionaries_that_dont_work     = cvc_checklists['dictionaries_that_dont_work']
                
                for dictonary in worked_dictionaries:
                    id_dictonary_cvc    = dictonary['dictionary_id']
                    name                = dictonary['name']
                    value               = dictonary['positive_weight']
                    dictonary_cvc       = get_dictonary_cvc(id_dictonary_cvc, name)
                    if dictonary_cvc.company == True:
                        company = True    
                    tematics            = Records_voice_recorder_cvc_checklist_tematics()
                    tematics.checklist  = check_list
                    tematics.tematic    = dictonary_cvc
                    tematics.value      = value
                    tematics.confirmed  = True
                    tematics.save()
                
                for dictonary in dictionaries_that_dont_work:
                    id_dictonary_cvc    = dictonary['dictionary_id']
                    name                = dictonary['name']
                    dictonary_cvc       = get_dictonary_cvc(id_dictonary_cvc, name)
                    tematics            = Records_voice_recorder_cvc_checklist_tematics()
                    tematics.checklist  = check_list
                    tematics.tematic    = dictonary_cvc
                    tematics.value      = 0
                    tematics.confirmed  = False
                    tematics.save()
                
                if len(worked_dictionaries) > 0: 
                    check_list.success = True
                
                check_list.company = company
                check_list.save()

                Records_voice_recorder_cvc_checklist_kg.objects.filter(checklist_cvc = check_list).delete()
                confirmed_tematics  = Records_voice_recorder_cvc_checklist_tematics.objects.filter(confirmed = True).filter(checklist = check_list)
                direction = check_list.direction
                if direction == 0:
                    direction = 1
                questions_records   = Records_questions.objects.filter(direction = direction).filter(сheck_settings = check_list.сheck_settings).order_by('chapter', '-priority_chapter')
                
                for questions in questions_records:
                    if questions.event_sale:
                        agreement = get_sale_to_day_rlk(check_list.rlk)
                        if agreement:
                            checklist_kg = Records_voice_recorder_cvc_checklist_kg()
                            checklist_kg.checklist_cvc  = check_list
                            checklist_kg.questions_kg   = questions
                            checklist_kg.value          = questions.estimation
                            checklist_kg.save()
                            if questions.priority_chapter > 0:
                                Records_voice_recorder_cvc_checklist_kg.objects.filter(checklist_cvc = check_list).filter(questions_kg__chapter = questions.chapter).filter(questions_kg__priority_chapter__gt = questions.priority_chapter).delete()
                            continue
                        
                    for tematics_confirmed in confirmed_tematics:
                        if questions.tematics.filter(pk = tematics_confirmed.tematic.pk).count() > 0:
                            if Records_voice_recorder_cvc_checklist_kg.objects.filter(checklist_cvc = check_list).filter(questions_kg = questions).count() == 0:
                                checklist_kg = Records_voice_recorder_cvc_checklist_kg()
                                checklist_kg.checklist_cvc  = check_list
                                checklist_kg.questions_kg   = questions
                                checklist_kg.value          = questions.estimation
                                checklist_kg.save()
                                if questions.priority_chapter > 0:
                                    Records_voice_recorder_cvc_checklist_kg.objects.filter(checklist_cvc = check_list).filter(questions_kg__chapter = questions.chapter).filter(questions_kg__priority_chapter__gt = questions.priority_chapter).delete()
                check_list.save()

def cvc_get_info_check():
    date_start = DT.datetime.now() + DT.timedelta(days=-7)
    date_start = date_start.replace(year=2024, month=7, day = 1, hour = 0, minute=0, second=0, microsecond=0)
    
    list_checklist_cvc = Records_voice_recorder_cvc_checklist.objects.filter(success = True).filter(rlk__dataTime__gte = date_start).filter(direction = 5)
    for check_list in list_checklist_cvc:
        #check_list = Records_voice_recorder_cvc_checklist.objects.get(pk = id)
        rlk         = check_list.rlk
        token = get_token()
        info    = get_check_cvc(token, id)
        if len(info) > 3:
            company = False
            Records_voice_recorder_cvc_checklist_tematics.objects.filter(checklist = check_list).delete()
            js                              = json.loads(info)
            checklists_cvc_info = js['checklists']
            
            refresh_check_list_info(checklists_cvc_info) 

            id_check_cvc = 0
            if check_list.сheck_settings != None:
                if check_list.сheck_settings.check_settings_cvc != None:
                    id_check_cvc = check_list.сheck_settings.check_settings_cvc.id_cvc
            
            cvc_checklists = None

            if id_check_cvc != 0:
                for checklist_cvc_info in checklists_cvc_info:
                    if id_check_cvc == checklist_cvc_info['checklist_id']:
                        cvc_checklists = checklist_cvc_info    

            if cvc_checklists == None:
                if len(checklists_cvc_info) > 1:
                    cvc_checklists                  = checklists_cvc_info[len(checklists_cvc_info)-1]
                else:
                    cvc_checklists                  = checklists_cvc_info[0]
            
            worked_dictionaries             = cvc_checklists['worked_dictionaries']
            dictionaries_that_dont_work     = cvc_checklists['dictionaries_that_dont_work']
            
            for dictonary in worked_dictionaries:
                id_dictonary_cvc    = dictonary['dictionary_id']
                name                = dictonary['name']
                value               = dictonary['positive_weight']
                dictonary_cvc       = get_dictonary_cvc(id_dictonary_cvc, name)
                if dictonary_cvc.company == True:
                    company = True    
                tematics            = Records_voice_recorder_cvc_checklist_tematics()
                tematics.checklist  = check_list
                tematics.tematic    = dictonary_cvc
                tematics.value      = value
                tematics.confirmed  = True
                tematics.save()
            
            for dictonary in dictionaries_that_dont_work:
                id_dictonary_cvc    = dictonary['dictionary_id']
                name                = dictonary['name']
                dictonary_cvc       = get_dictonary_cvc(id_dictonary_cvc, name)
                tematics            = Records_voice_recorder_cvc_checklist_tematics()
                tematics.checklist  = check_list
                tematics.tematic    = dictonary_cvc
                tematics.value      = 0
                tematics.confirmed  = False
                tematics.save()
            
            if len(worked_dictionaries) > 0: 
                check_list.success = True
            
            check_list.company = company
            check_list.save()

            Records_voice_recorder_cvc_checklist_kg.objects.filter(checklist_cvc = check_list).delete()
            confirmed_tematics  = Records_voice_recorder_cvc_checklist_tematics.objects.filter(confirmed = True).filter(checklist = check_list)
            direction = check_list.direction
            if direction == 0:
                direction = 1
            questions_records   = Records_questions.objects.filter(direction = direction).filter(сheck_settings = check_list.сheck_settings).order_by('chapter', '-priority_chapter')
            
            for questions in questions_records:
                if questions.event_sale:
                    agreement = get_sale_to_day_rlk(check_list.rlk)
                    if agreement:
                        checklist_kg = Records_voice_recorder_cvc_checklist_kg()
                        checklist_kg.checklist_cvc  = check_list
                        checklist_kg.questions_kg   = questions
                        checklist_kg.value          = questions.estimation
                        checklist_kg.save()
                        if questions.priority_chapter > 0:
                            Records_voice_recorder_cvc_checklist_kg.objects.filter(checklist_cvc = check_list).filter(questions_kg__chapter = questions.chapter).filter(questions_kg__priority_chapter__gt = questions.priority_chapter).delete()
                        continue
                    
                for tematics_confirmed in confirmed_tematics:
                    if questions.tematics.filter(pk = tematics_confirmed.tematic.pk).count() > 0:
                        if Records_voice_recorder_cvc_checklist_kg.objects.filter(checklist_cvc = check_list).filter(questions_kg = questions).count() == 0:
                            checklist_kg = Records_voice_recorder_cvc_checklist_kg()
                            checklist_kg.checklist_cvc  = check_list
                            checklist_kg.questions_kg   = questions
                            checklist_kg.value          = questions.estimation
                            checklist_kg.save()
                            if questions.priority_chapter > 0:
                                Records_voice_recorder_cvc_checklist_kg.objects.filter(checklist_cvc = check_list).filter(questions_kg__chapter = questions.chapter).filter(questions_kg__priority_chapter__gt = questions.priority_chapter).delete()
            check_list.save()    
        else:
            Records_voice_recorder_cvc_checklist_kg.objects.filter(checklist_cvc = check_list).delete()
            confirmed_tematics  = Records_voice_recorder_cvc_checklist_tematics.objects.filter(confirmed = True).filter(checklist = check_list)
            direction = check_list.direction
            if direction == 0:
                direction = 1
            questions_records   = Records_questions.objects.filter(direction = direction).filter(сheck_settings = check_list.сheck_settings).order_by('chapter', '-priority_chapter')
            
            for questions in questions_records:
                if questions.event_sale:
                    agreement = get_sale_to_day_rlk(check_list.rlk)
                    if agreement:
                        checklist_kg = Records_voice_recorder_cvc_checklist_kg()
                        checklist_kg.checklist_cvc  = check_list
                        checklist_kg.questions_kg   = questions
                        checklist_kg.value          = questions.estimation
                        checklist_kg.save()
                        if questions.priority_chapter > 0:
                            Records_voice_recorder_cvc_checklist_kg.objects.filter(checklist_cvc = check_list).filter(questions_kg__chapter = questions.chapter).filter(questions_kg__priority_chapter__gt = questions.priority_chapter).delete()
                        continue
                    
                for tematics_confirmed in confirmed_tematics:
                    if questions.tematics.filter(pk = tematics_confirmed.tematic.pk).count() > 0:
                        if Records_voice_recorder_cvc_checklist_kg.objects.filter(checklist_cvc = check_list).filter(questions_kg = questions).count() == 0:
                            checklist_kg = Records_voice_recorder_cvc_checklist_kg()
                            checklist_kg.checklist_cvc  = check_list
                            checklist_kg.questions_kg   = questions
                            checklist_kg.value          = questions.estimation
                            checklist_kg.save()
                            if questions.priority_chapter > 0:
                                Records_voice_recorder_cvc_checklist_kg.objects.filter(checklist_cvc = check_list).filter(questions_kg__chapter = questions.chapter).filter(questions_kg__priority_chapter__gt = questions.priority_chapter).delete()
            check_list.save() 

def get_dictonary_cvc(id_dictonary_cvc, name):
    dictonarys = Records_voice_recorder_cvc_tematics.objects.filter(id_cvc = str(id_dictonary_cvc))
    if len(dictonarys) == 0:
       dictonary =  Records_voice_recorder_cvc_tematics()
       dictonary.name       = name
       dictonary.id_cvc     = str(id_dictonary_cvc)
       dictonary.activated  = True
       dictonary.save()
       return dictonary
    else:
        dictonary               = dictonarys[0]
        dictonary.activated     = True
        dictonary.save()
        return dictonary

def get_check_cvc(token, id):
    url = 'https://int-kors.audio-control.by/api/get-call-details'
    headers ={
        "accept"        : "application/json",
        "Content-Type"  : "application/json"
        }
    params = {
        "call_id"   : id,
        "token"     : token,
    }
    response = requests.post(url, data = str(params).replace("'", '"'), headers = headers, verify=False)
    if response.status_code == 200:
        return response.text
    return ''

def get_token():
    url = 'https://int-kors.audio-control.by/api/get-token'

    params = {
        "login"             : login_cvc.replace("'", '"'),
        "password"          : password_cvc.replace("'", '"'),
    }
    response = requests.post(url, data = str(params).replace("'", '"'))
    if response.status_code == 200:
        return json.loads(response.text)['token']
    return ''

def cvc_send_record(send_record, fragments):
    status_code     = 0 
    record_query    = send_record
    info            = fragments
    url             = 'https://int-kors.audio-control.by/api/add-files' 
    params = {
        "master_key"        : "Ga8FQ0dgmALiA1bFr7k7tqIym84rnLM0",
        "category"          : "recorder",
        "date_call"         : record_query.date.strftime('%Y-%m-%dT%H:%M:%S%z') + '+0300',
        "json_fragments"    : str(info).replace("'", '"'),   
    }
    try:
        with open(record_query.audio.path, 'rb') as f:
            response = requests.post(url, data = params, files = {"files": (record_query.name, f)}, verify=False, timeout=(10, 300))
        
        if response.status_code == 200:
            status_code = response.status_code
            records     = Records_voice_recorder_cvc.objects.filter(records = record_query)
            if len(records) > 0:
                record = records[0]
            else:
                record = Records_voice_recorder_cvc()
            record.date         = DT.datetime.now()
            record.comment      = str(response.status_code)
            record.data_json    = str(response.text)
            record.records      = record_query
            record.save()
        return status_code
    except Exception as e:
        error_text = str(e)
        return status_code

def cvc_record_info():
    record_query    = Records_voice_recorder.objects.get(pk = 410853)
    date_start      = record_query.date.replace(hour=1)
    date_end        = record_query.date.replace(hour=23) 

    user_record         = record_query.user
    id                  = record_query.id
    record              = record_query
    
    date_event_start    = record_query.date
    date_event_end      = date_event_start + DT.timedelta(seconds = record_query.time) 

    fragments   = list()
    docs_rlk            = DocRLK.objects.filter(staff__domain_login__iexact = str(user_record)).filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(Q(contacType__id= 7) | Q(contacType__id = 42)).filter(unit__buauto = True)

    fragments   = list() 
    
    for doc_rlk in docs_rlk:
        
        date_start_rlk  = doc_rlk.dataTimeCreate
        date_end_rlk    = doc_rlk.dataEnd
        if (date_end_rlk - date_start_rlk).seconds < 300:
            date_end_rlk = date_start_rlk + DT.timedelta(minutes=15)   

        if doc_rlk.dataTimeCreate > date_event_start and date_end_rlk < date_event_end:

            hour_new        = date_start_rlk.hour
            minute_new      = date_start_rlk.minute

            if minute_new < 5:
                minute_new  = minute_new + 60 - 5
                hour_new    = hour_new - 1
            else:
                minute_new  = minute_new - 5
                
            date_start_rlk = date_start_rlk.replace(hour=hour_new, minute=minute_new)
            dateNull = DT.datetime(1,1,1,0,0, tzinfo=DT.timezone.utc)
            
            if doc_rlk.dataEnd == dateNull or doc_rlk.dataEnd == DT.datetime(1,1,1,0,0):
                dataEnd = date_start_rlk + DT.timedelta(hours=1)
                if dataEnd > date_event_end:
                    dataEnd = date_event_end
            else:
                dataEnd = doc_rlk.dataEnd
                
            if (dataEnd - date_start_rlk).seconds > 600:
                params_doc = {
                    "event_id"              : doc_rlk.id,
                    "manager"               : doc_rlk.staff.name,
                    "fragment_time_start"   : int(date_start_rlk.strftime('%Y%m%d%H%M%S')),
                    "fragment_time_end"     : int(dataEnd.strftime('%Y%m%d%H%M%S'))
                }
                if doc_rlk.dataEnd > date_start_rlk:
                    fragments.append(params_doc)

    if len(fragments) > 0:
        s= 1 

def cvc_get_record_info_no_send(record_query):
    date_start      = record_query.date.replace(hour=1)
    date_end        = record_query.date.replace(hour=23) 

    user_record         = record_query.user
    id                  = record_query.id
    record              = record_query
    
    date_event_start    = record_query.date
    date_event_end      = date_event_start + DT.timedelta(seconds = record_query.time) 

    docs_rlk            = DocRLK.objects.filter(staff__domain_login__iexact = str(user_record)).filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(Q(contacType__id= 7) | Q(contacType__id = 42)).filter(unit__buauto = False)

    fragments   = list() 
    
    for doc_rlk in docs_rlk:
        
        rlk_events =  doc_rlk.dataTimeCreate
        
        if rlk_events > date_event_start and doc_rlk.dataEnd < date_event_end:
            date_start_rlk  = rlk_events
            hour_new        = date_start_rlk.hour
            minute_new      = date_start_rlk.minute

            if minute_new < 5:
                minute_new  = minute_new + 60 - 5
                hour_new    = hour_new - 1
            else:
                minute_new  = minute_new - 5
            
            date_start_rlk = date_start_rlk.replace(hour=hour_new, minute=minute_new)
            dateNull = DT.datetime(1,1,1,0,0, tzinfo=DT.timezone.utc)
            if doc_rlk.dataEnd == dateNull or doc_rlk.dataEnd == DT.datetime(1,1,1,0,0):
                dataEnd = date_start_rlk + DT.timedelta(hours=1)
                if dataEnd > date_event_end:
                    dataEnd = date_event_end
            else:
                dataEnd = doc_rlk.dataEnd
                
            if (dataEnd - date_start_rlk).seconds > 480:
                params_doc = {
                    "event_id"              : doc_rlk.id,
                    "event_nomer"           : doc_rlk.nomer,
                    "manager"               : doc_rlk.staff.name,
                    "fragment_time_start"   : date_start_rlk,
                    "fragment_time_end"     : dataEnd
                    
                }
                if doc_rlk.dataEnd > date_start_rlk:
                    fragments.append(params_doc)

    if len(fragments) > 0:            
        return fragments
    
    #Корс авто ОП
    docs_rlk            = DocRLK.objects.filter(staff__domain_login__iexact = str(user_record)).filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(Q(contacType__id= 7) | Q(contacType__id = 42)).filter(unit__buauto = True)

    fragments   = list() 
    
    for doc_rlk in docs_rlk:
        
        date_start_rlk  = doc_rlk.dataTimeCreate
        if doc_rlk.dataTimeCreate > date_event_start and doc_rlk.dataEnd < date_event_end:
            hour_new        = date_start_rlk.hour
            minute_new      = date_start_rlk.minute

            if minute_new < 5:
                minute_new  = minute_new + 60 - 5
                hour_new    = hour_new - 1
            else:
                minute_new  = minute_new - 5
                
            date_start_rlk = date_start_rlk.replace(hour=hour_new, minute=minute_new)
            dateNull = DT.datetime(1,1,1,0,0, tzinfo=DT.timezone.utc)
            
            if doc_rlk.dataEnd == dateNull or doc_rlk.dataEnd == DT.datetime(1,1,1,0,0):
                dataEnd = date_start_rlk + DT.timedelta(hours=1)
                if dataEnd > date_event_end:
                    dataEnd = date_event_end
            else:
                dataEnd = doc_rlk.dataEnd
                
            if (dataEnd - date_start_rlk).seconds > 480:
                params_doc = {
                    "event_id"              : doc_rlk.id,
                    "manager"               : doc_rlk.staff.name,
                    "fragment_time_start"   : int(date_start_rlk.strftime('%Y%m%d%H%M%S')),
                    "fragment_time_end"     : int(dataEnd.strftime('%Y%m%d%H%M%S'))
                }
                if doc_rlk.dataEnd > date_start_rlk:
                    fragments.append(params_doc)

    if len(fragments) > 0:            
        return fragments

    return fragments

def cvc_get_record_info(record_query):
    
    date_start      = record_query.date.replace(hour=1)
    date_end        = record_query.date.replace(hour=23) 

    user_record         = record_query.user
    id                  = record_query.id
    record              = record_query
    
    date_event_start    = record_query.date
    date_event_end      = date_event_start + DT.timedelta(seconds = record_query.time) 

    docs_rlk            = DocRLK.objects.filter(staff__domain_login__iexact = str(user_record)).filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(Q(contacType__id= 7) | Q(contacType__id = 42)).filter(unit__buauto = False)

    fragments   = list() 
    
    for doc_rlk in docs_rlk:
        
        rlk_events =  doc_rlk.dataTimeCreate
        
        if rlk_events > date_event_start and doc_rlk.dataEnd < date_event_end:
            date_start_rlk  = rlk_events
            hour_new        = date_start_rlk.hour
            minute_new      = date_start_rlk.minute

            if minute_new < 5:
                minute_new  = minute_new + 60 - 5
                hour_new    = hour_new - 1
            else:
                minute_new  = minute_new - 5
            
            date_start_rlk = date_start_rlk.replace(hour=hour_new, minute=minute_new)
            dateNull = DT.datetime(1,1,1,0,0, tzinfo=DT.timezone.utc)
            if doc_rlk.dataEnd == dateNull or doc_rlk.dataEnd == DT.datetime(1,1,1,0,0):
                dataEnd = date_start_rlk + DT.timedelta(hours=1)
                if dataEnd > date_event_end:
                    dataEnd = date_event_end
            else:
                dataEnd = doc_rlk.dataEnd
                
            if (dataEnd - date_start_rlk).seconds > 480:
                params_doc = {
                    "event_id"              : doc_rlk.id,
                    "manager"               : doc_rlk.staff.name,
                    "fragment_time_start"   : int(date_start_rlk.strftime('%Y%m%d%H%M%S')),
                    "fragment_time_end"     : int(dataEnd.strftime('%Y%m%d%H%M%S'))
                }
                if doc_rlk.dataEnd > date_start_rlk:
                    fragments.append(params_doc)

    if len(fragments) > 0:            
        counts_queue = Records_voice_recorder_cvc.objects.filter(records = record).count()
        if counts_queue == 0 and len(fragments) > 0:
            status_code = cvc_send_record(record, fragments)
            if status_code == 200:
                for fragment in fragments:
                    count = Records_voice_recorder_cvc_checklist.objects.filter(rlk__id = fragment['event_id']).count()
                    if count == 0:
                        new_fragment             = Records_voice_recorder_cvc_checklist()
                        new_fragment.rlk         = DocRLK.objects.get(pk = fragment['event_id'])
                        new_fragment.records     = record_query
                        new_fragment.date        = DT.datetime.now()
                        new_fragment.time_start  = DT.datetime.strptime(str(fragment['fragment_time_start']), '%Y%m%d%H%M%S')
                        new_fragment.time_end    = DT.datetime.strptime(str(fragment['fragment_time_end']), '%Y%m%d%H%M%S')
                        new_fragment.duration    = (new_fragment.time_end - new_fragment.time_start).seconds
                        new_fragment.save()
        if len(fragments) > 0:
            for fragment in fragments:
                count = Records_voice_recorder_cvc_checklist.objects.filter(rlk__id = fragment['event_id']).count()
                if count == 0:
                    new_fragment             = Records_voice_recorder_cvc_checklist()
                    new_fragment.rlk         = DocRLK.objects.get(pk = fragment['event_id'])
                    new_fragment.records     = record_query
                    new_fragment.date        = DT.datetime.now()
                    new_fragment.time_start  = DT.datetime.strptime(str(fragment['fragment_time_start']), '%Y%m%d%H%M%S')
                    new_fragment.time_end    = DT.datetime.strptime(str(fragment['fragment_time_end']), '%Y%m%d%H%M%S')
                    new_fragment.duration    = (new_fragment.time_end - new_fragment.time_start).seconds
                    new_fragment.save()
    #Корс авто ОП
    docs_rlk            = DocRLK.objects.filter(staff__domain_login__iexact = str(user_record)).filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(Q(contacType__id= 7) | Q(contacType__id = 42)).filter(unit__buauto = True)

    fragments   = list() 
    
    for doc_rlk in docs_rlk:
        
        date_start_rlk  = doc_rlk.dataTimeCreate
        if doc_rlk.dataTimeCreate > date_event_start and doc_rlk.dataEnd < date_event_end:
            hour_new        = date_start_rlk.hour
            minute_new      = date_start_rlk.minute

            if minute_new < 5:
                minute_new  = minute_new + 60 - 5
                hour_new    = hour_new - 1
            else:
                minute_new  = minute_new - 5
                
            date_start_rlk = date_start_rlk.replace(hour=hour_new, minute=minute_new)
            dateNull = DT.datetime(1,1,1,0,0, tzinfo=DT.timezone.utc)
            
            if doc_rlk.dataEnd == dateNull or doc_rlk.dataEnd == DT.datetime(1,1,1,0,0):
                dataEnd = date_start_rlk + DT.timedelta(hours=1)
                if dataEnd > date_event_end:
                    dataEnd = date_event_end
            else:
                dataEnd = doc_rlk.dataEnd
                
            if (dataEnd - date_start_rlk).seconds > 480:
                params_doc = {
                    "event_id"              : doc_rlk.id,
                    "manager"               : doc_rlk.staff.name,
                    "fragment_time_start"   : int(date_start_rlk.strftime('%Y%m%d%H%M%S')),
                    "fragment_time_end"     : int(dataEnd.strftime('%Y%m%d%H%M%S'))
                }
                if doc_rlk.dataEnd > date_start_rlk:
                    fragments.append(params_doc)

    if len(fragments) > 0:            
        counts_queue = Records_voice_recorder_cvc.objects.filter(records = record).count()
        if counts_queue == 0 and len(fragments) > 0:
            status_code = cvc_send_record(record, fragments)
            if status_code == 200:
                for fragment in fragments:
                    count = Records_voice_recorder_cvc_checklist.objects.filter(rlk__id = fragment['event_id']).count()
                    if count == 0:
                       new_fragment             = Records_voice_recorder_cvc_checklist()
                       new_fragment.rlk         = DocRLK.objects.get(pk = fragment['event_id'])
                       new_fragment.direction   = 5
                       new_fragment.records     = record_query
                       new_fragment.date        = DT.datetime.now()
                       new_fragment.time_start  = DT.datetime.strptime(str(fragment['fragment_time_start']), '%Y%m%d%H%M%S')
                       new_fragment.time_end    = DT.datetime.strptime(str(fragment['fragment_time_end']), '%Y%m%d%H%M%S')
                       new_fragment.duration    = (new_fragment.time_end - new_fragment.time_start).seconds
                       new_fragment.save()
        '''
        for fragment in fragments:
            count = Records_voice_recorder_cvc_checklist.objects.filter(rlk__id = fragment['event_id']).count()
            if count == 0:
                new_fragment                = Records_voice_recorder_cvc_checklist()
                new_fragment.rlk            = DocRLK.objects.get(pk = fragment['event_id'])
                new_fragment.records        = record_query
                new_fragment.date           = DT.datetime.now()
                new_fragment.time_start     = DT.datetime.strptime(str(fragment['fragment_time_start']), '%Y%m%d%H%M%S')
                new_fragment.time_end       = DT.datetime.strptime(str(fragment['fragment_time_end']), '%Y%m%d%H%M%S')
                new_fragment.duration       = (new_fragment.time_end - new_fragment.time_start).seconds
                new_fragment.save()
        '''                       
                             
def cvc_get_send_info(record):
    infos   = Records_voice_recorder_cvc.objects.filter(records = record)
    send    = False
    date    = ''
    comment = ''
    data    = ''
    if len(infos) > 0:
        info    = infos[0]
        send    = True
        date    = info.date
        comment = comment
        data    = info.data_json

    json_info = {
        'send'      : send,
        'date'      : date,
        'comment'   : comment,
        'data'      : data
    }
    return json_info


####
###
##
# Формирование очереди к распознованию
def get_record_info(record_query, direction):
    
    date_record_start   = record_query.date.replace(hour=1)
    date_record_end     = record_query.date.replace(hour=23) 
    user_record         = record_query.user
    id                  = record_query.id
    record              = record_query
    
    date_event_start    = record_query.date
    date_event_end      = date_event_start + DT.timedelta(seconds = record_query.time) 

    docs_rlk            = DocRLK.objects.filter(staff__domain_login = str(user_record)).filter(dataTime__gte = date_record_start).filter(dataTime__lte = date_record_end).filter(Q(contacType__id= 7) | Q(contacType__id = 42))  

    for doc_rlk in docs_rlk:
        rlk_events = DocRLKEvents.objects.filter(rlk = doc_rlk).order_by('dataTime')[0]
        if rlk_events.dataTime > date_event_start and doc_rlk.dataEnd < date_event_end:
            date_start_rlk  = rlk_events.dataTime
            hour_new        = int(date_start_rlk.strftime('%H'))
            minute_new      = int(date_start_rlk.strftime('%M'))

            if minute_new < 3:
                minute_new  = minute_new + 60 - 3
                hour_new    = hour_new - 1
            else:
                minute_new  = minute_new - 3

            date_start_rlk = date_start_rlk.replace(hour=hour_new, minute=minute_new)

            counts_queue = Records_voice_recorder_queue.objects.filter(records = record).filter(doc_id = doc_rlk.id).filter(direction = direction).count()
            if counts_queue == 0:
                date_end_rlk = doc_rlk.dataEnd 
                if date_end_rlk < date_start_rlk:
                    date_end_rlk = date_start_rlk.replace(hour = date_start_rlk.hour + 1) 
                records_voice_recorder_queue            = Records_voice_recorder_queue()
                records_voice_recorder_queue.date       = DT.datetime.now()
                records_voice_recorder_queue.records    = record
                records_voice_recorder_queue.doc_id     = doc_rlk.id
                records_voice_recorder_queue.time_start = date_start_rlk
                records_voice_recorder_queue.time_end   = date_end_rlk
                records_voice_recorder_queue.direction  = direction
                records_voice_recorder_queue.save()
     
def refresh_queue_recognition():
    
    date_end    = DT.datetime.now()
    date_start  = date_end + DT.timedelta(days=-7)

    records_query = Records_voice_recorder.objects.filter(date__gte = date_start).filter(date__lt = date_end).filter(time__gte = 1).order_by('date')
    for record_query in records_query:
        get_record_info(record_query, 1)

####
####Обновление аналитик интерактивной оценки
def refresh_chat_data():
    date_start = DT.datetime.now().replace(month=1)
    
    info_date   = ChatSuccesDate.objects.all().last()
    if info_date != None:
        date_start  = info_date.date
    else:
        info_date = ChatSuccesDate()
        info_date.date = date_start
        info_date.save()

    chats = ChatMessage.objects.filter(date__gte = date_start).order_by('date')[:20]
    for chat in chats:
        refresh_estimation_analitik(chat.chat.rlk_id)

    info_date.date = date_start
    info_date.save()   



def refresh_estimation_analitik(estimation_rlk_id):
      
    hour_start_day  = 9
    hour_end_day    = 20

    estimations = RegInteractivOcenka.objects.filter(rlk__pk = estimation_rlk_id).order_by('start_estimation')
    for estimation in estimations:
        slug_chat       = 'rlk_' + str(estimation.rlk.id)
        end_estimation  = estimation.end_estimation
        
        #Если нет окончания оценки проставим ее
        if end_estimation == DT.datetime(1,1,1):
            chats_messages_ = ChatMessage.objects.filter(chat__slug = slug_chat).filter(content = 'Оценка отправлена на согласование').order_by('date')
            for chats_message_ in chats_messages_:
                if end_estimation == DT.datetime(1,1,1):
                    end_estimation = chats_message_.date
            if end_estimation != DT.datetime(1,1,1):
                estimation.end_estimation = end_estimation 
                estimation.save(update_fields=['end_estimation'])

        #Если не указан аналитик до диагностики то пробуем его поставить
        if estimation.staff_eco_1 == None:
            staff_eco_1 = None
            chats_messages_ = ChatMessage.objects.filter(chat__slug = slug_chat).filter(content__startswith = 'Согласована цена до диагностики -').order_by('date')
            for chats_message_ in chats_messages_:
                if staff_eco_1 == None:
                    staff_eco_1 = chats_message_.user
            if staff_eco_1 != None:
                estimation.staff_eco_1 = staff_eco_1 
                estimation.save(update_fields=['staff_eco_1'])  

        #Если не указан аналитик после диагностки то пробуем его поставить
        if estimation.staff_eco_2 == None:
            staff_eco_2 = None
            chats_messages_ = ChatMessage.objects.filter(chat__slug = slug_chat).filter(content__startswith = 'Согласована цена после диагностики -').order_by('date')
            for chats_message_ in chats_messages_:
                if staff_eco_2 == None:
                    staff_eco_2 = chats_message_.user
            if staff_eco_2 != None:
                estimation.staff_eco_2 = staff_eco_2 
                estimation.save(update_fields=['staff_eco_2'])  

        #А тут соберем данные по пользователям согласования, вдруг просили подтверждение Серебрянникова или директора ДЦ
        messages_user = ChatMessage.objects.filter(chat__slug = slug_chat).values('user', 'user__profiles__eco', 'user__username').distinct()
        dop_soglasovanie    = 0
        users_eco           = 0
        users_no_eco        = 0           
        
        for message_user in messages_user:
            if message_user['user__profiles__eco']:
                users_eco = users_eco + 1
            else:
                users_no_eco = users_no_eco + 1
                if estimation.staff.domain_login != message_user['user__username']:
                    dop_soglasovanie = dop_soglasovanie + 1
        
        #Посчитаем среднее время приема
        #Не считаем время при переходе на следующий день, т.е. не считаем время от последнего до первого сообщения следующего дня.
        #Для принятых последнее сообщение и дату листа оценки.
        messages_date   = ChatMessage.objects.filter(chat__slug = slug_chat).values('date').order_by('date')
        mes_start       = ''
        seconds         = 0 
        for message_date in messages_date:
            if mes_start == '':
                mes_start = message_date['date']
            else:
                if mes_start.day == message_date['date'].day:
                    seconds = seconds + (message_date['date'] - mes_start).total_seconds()
                else:
                   day_end      = mes_start.replace(hour = hour_end_day, minute = 0, second = 0)
                   day_start    = message_date['date'].replace(hour = hour_start_day, minute = 0, second = 0)
                   sec_1        = (day_end - mes_start).total_seconds()
                   sec_2        = (message_date['date'] - day_start).total_seconds()
                   seconds = seconds + sec_1 + sec_2
                mes_start = message_date['date']
        s = 1
        
        #Проставим отметки этапов
        date_s_do_diag  = DT.datetime(1,1,1)
        date_diagnostic = DT.datetime(1,1,1)
        date_s_diag     = DT.datetime(1,1,1)
        messages_list = ChatMessage.objects.filter(chat__slug = slug_chat).order_by('date')
        
        status_ocenka                   = 0
        status_soglasovanie_do_diag     = 0
        status_diagnostika              = 0
        status_soglasovanie_posle_kd    = 0
        
        status          = 0
        mes_start       = ''
        sec             = 0
        seconds_status  = 0
        prev_user       = True
        seconds_answer  = 0
        answer_count    = 0
        for message in messages_list:
            
            if message.content.startswith('Согласована цена до диагностики -'):
               status = 1
               date_s_do_diag = message.date
            if message.content.startswith('Согласована цена после диагностики -'):
               status = 3
               date_s_diag = message.date
            if message.content.startswith('Пройдена диагностика -'):
               status = 2
               date_diagnostic = message.date 
            
            if mes_start == '':
                mes_start = message.date
            else:
                if mes_start.day == message.date.day:
                    seconds_status = seconds_status + (message.date - mes_start).total_seconds()
                    sec = (message.date - mes_start).total_seconds()
                else:
                   day_end      = mes_start.replace(hour = hour_end_day, minute = 0, second = 0)
                   day_start    = message.date.replace(hour = hour_start_day, minute = 0, second = 0)
                   sec_1        = (day_end - mes_start).total_seconds()
                   sec_2        = (message.date - day_start).total_seconds()
                   sec          = sec_1 + sec_2
                   seconds_status = seconds_status + sec_1 + sec_2
                
                if status == 1:
                    status_soglasovanie_do_diag = status_soglasovanie_do_diag + seconds_status
                    seconds_status = 0
                    status = 0
                elif status == 2:
                    status_diagnostika = status_diagnostika + seconds_status
                    seconds_status = 0
                    status = 0
                elif status == 3:
                    status_soglasovanie_posle_kd = status_soglasovanie_posle_kd + seconds_status        
                    seconds_status = 0
                    status = 0

            if message.user.profiles.eco and prev_user:
                seconds_answer = seconds_answer + sec                
                answer_count = answer_count + 1
            prev_user = not message.user.profiles.eco
            mes_start = message.date        

        #Пробуем посчитать время в статусах
        status_ocenka                   = (estimation.end_estimation - estimation.start_estimation).total_seconds()
        #status_soglasovanie_do_diag     = (date_s_do_diag - estimation.end_estimation).total_seconds()
        #status_diagnostika              = (date_diagnostic - date_s_do_diag).total_seconds()
        #status_soglasovanie_posle_kd    = (date_s_diag - date_diagnostic).total_seconds() 
        
        estimation.date_s_do_diag   = date_s_do_diag
        estimation.date_diagnostic  = date_diagnostic
        estimation.date_s_diag      = date_s_diag

        estimation.status_ocenka                    = status_ocenka
        estimation.status_soglasovanie_do_diag      = status_soglasovanie_do_diag
        estimation.status_diagnostika               = status_diagnostika
        estimation.status_soglasovanie_posle_kd     = status_soglasovanie_posle_kd
        estimation.seconds_estimation               = seconds
        estimation.count_answer     = answer_count
        estimation.seconds_answer   = seconds_answer
        estimation.users_eco        = users_eco
        estimation.users_no_eco     = users_no_eco
        estimation.users_dop        = dop_soglasovanie
        
        tasks = estimation.tasks()
        estimation.count_task   = len(tasks)
        second_task             = 0
        for task in tasks:
            if task.date_open.day == task.date_close.day:
                second_task = second_task + (task.date_close - task.date_open).total_seconds()
            else:
                day_end      = task.date_open.replace(hour = hour_end_day, minute = 0, second = 0)
                day_start    = task.date_close.replace(hour = hour_start_day, minute = 0, second = 0)
                sec_1        = (day_end - mes_start).total_seconds()
                sec_2        = (task.date - day_start).total_seconds()
                sec          = sec_1 + sec_2
                second_task = second_task + sec_1 + sec_2    
        estimation.seconds_task = second_task

        estimation.save(update_fields=['count_task',
                                       'seconds_task',
                                       'count_answer',
                                       'seconds_answer',
                                       'users_dop',
                                       'users_no_eco',
                                        'users_eco',
                                       'date_s_do_diag',
                                       'date_diagnostic',
                                       'date_s_diag',
                                       'status_ocenka',
                                       'seconds_estimation',
                                       'status_soglasovanie_do_diag',
                                       'status_diagnostika',
                                       'status_soglasovanie_posle_kd'
            ]) 
        #

