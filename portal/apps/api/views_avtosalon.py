from django.shortcuts import render
from asyncio.windows_events import NULL
import random
import os
from itertools import groupby
from django.utils.translation import activate
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from collections import defaultdict
from decimal import Decimal
from django.conf import settings
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.http.response import JsonResponse
from rest_framework.authentication import BasicAuthentication
from rest_framework.parsers import JSONParser
from rest_framework import status
from rest_framework.decorators import api_view
import json
from django.contrib.auth.models import User, Group
import datetime as DT
import base64
from email import header
from itertools import product
import requests
from fake_headers import Headers
import fake_proxy
import qrcode
import urllib.parse
import io
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers import serialize
from refs.models import RefEventCarsOrganization, RefAvito, RefCarsOrganizationFiles, RefCarsOrganization, AutoruModification, AutoruComplectation, AutoruModel, AutoruMark, AutoruModificationSpecifications
from avtosalon.models import Avtohub, RefreshCarsLog
from avtosalon.serializers import AvtohubSerializer
from api.views import get_unit, get_organization, get_store, get_stage_price, get_group_price, get_model_object
import tempfile
from django.core import files
from register.models import RegRefCarsOrganizationsCalculationPrice, RegEstimationRefCarsOrganizations, RegViewsCarsOrganization, RegRefCarsOrganizationsPrice
from datetime import datetime
from django.db.models import Q
from api.tasks_cars import load_photos_async, normalize_photos_payload


def add_statistic_cars_organization(user, cars, store, type):
    new_view        = RegViewsCarsOrganization()
    new_view.cars   = cars
    new_view.store  = store
    new_view.type   = RefEventCarsOrganization.objects.get(pk = type)
    new_view.date   = datetime.now()
    new_view.quantity   = cars.quantity
    new_view.reserve    = cars.reserve
    new_view.user       = user
    new_view.save()


@api_view(['GET', 'POST'])
def zna_info(request):
    
    list_info   = list()
    
    objects         = RegEstimationRefCarsOrganizations.objects.all()
    
    date_start      = request.GET.get('date_start', '')
    if date_start != '':
        objects = objects.filter(date__gte = date_start)
    
    date_end        = request.GET.get('date_end', '')
    if date_end != '':
        objects = objects.filter(date__lte = date_end)
    
    vin             = request.GET.get('vin', '')
    if vin != '':
        objects = objects.filter(car__vin = vin)
            
    for object in objects:
        car_inf = {
            'date'      : object.date,
            'uin'       : object.car.lo_uin,
            'zna'       : object.avg_price,
            'total'     : object.total,
            'price'     : object.price,
            'position'  : object.position,
            'days'      : object.avg_days
            }
        list_info.append(car_inf)
        
    info = {
        'data' : list_info
    }
    return JsonResponse(info, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
def avtohub_info(request):
    
    list_info   = list()
    
    objects         = Avtohub.objects.all()

    date_start      = request.GET.get('date_start', '')
    if date_start != '':
        objects = objects.filter(date__gte = date_start)
    date_end        = request.GET.get('date_end', '')
    if date_end != '':
        objects = objects.filter(date__lte = date_end)
    vin             = request.GET.get('vin', '')
    if vin != '':
        objects = objects.filter(vin = vin)
        
    list_info = serialize('json', objects)
    info = {
        'data' : list_info
    }
    return JsonResponse(info, status=status.HTTP_200_OK)


@api_view(['GET'])
def avtohub_options(request):
    """Справочник AvtohubOptions (группы AvtohubGroupOptions).

    GET-параметры:
      modification_id   — id_avtohub модификации Avtohub
      car_id            — RefCarsOrganization.pk (фильтр по модификации авто)
      group_id          — pk группы опций
      group_id_avtohub  — id_avtohub группы
      id_avtohub        — id_avtohub опции
      name / q          — поиск по названию
      format            — grouped (по умолчанию) или flat

    Отдельный режим (другой формат ответа):
      modification_autoru_id / modification_autoru — autoruId модификации
      complectation_autoru_id / complectation_autoru — autoruId комплектации
    """
    from avtosalon.car_options import (
        build_avtohub_options_groups,
        get_avtohub_options_autoru_filter,
        get_avtohub_options_queryset,
        serialize_avtohub_option,
    )

    autoru_payload = get_avtohub_options_autoru_filter(request.GET)
    if autoru_payload is not None:
        return JsonResponse(autoru_payload, status=status.HTTP_200_OK, safe=False)

    qs = get_avtohub_options_queryset(request.GET)
    response_format = (request.GET.get('format') or 'grouped').strip().lower()

    if response_format == 'flat':
        items = [serialize_avtohub_option(opt) for opt in qs]
        return JsonResponse({
            'ok': True,
            'count': len(items),
            'items': items,
        }, status=status.HTTP_200_OK, safe=False)

    groups = build_avtohub_options_groups(qs)
    total_count = sum(len(g['options']) for g in groups)
    return JsonResponse({
        'ok': True,
        'count': total_count,
        'groups': groups,
    }, status=status.HTTP_200_OK, safe=False)


@api_view(['GET', 'POST'])
def get_image_change(request):
    '''
    files = RefCarsOrganizationFiles.objects.filter(processed = True)
    for file in files:
        file.processed = False
        file.car = False
        file.save()
    '''

    files = RefCarsOrganizationFiles.objects.filter(processed = False)[:1]
    if len(files)> 0:
        file = files[0]

        answer = {
            'url'           : file.file.url,
            'pk'            : file.pk
        }
        return JsonResponse(answer, status = status.HTTP_200_OK, safe = False)
    
    answer = {
        'ok'        : 'ok',
        'url'       : ''
    }
    return JsonResponse(answer, status = status.HTTP_200_OK, safe = False)


@api_view(['GET', 'POST'])
def post_image_change(request):
    
    body_unicode    = request.body.decode().replace("'", '"')
    data            = json.loads(body_unicode) 
    
    pk              = data['pk']
    image           = data['image']
    processed       = data['processed']
    
    cars_organization_files = RefCarsOrganizationFiles.objects.get(pk = pk)
    if len(image) > 0:
        file_name = cars_organization_files.name.replace('.jpg','.png')
        file_name = file_name.replace('.jpeg','.png')
        decoded_image = ContentFile(base64.b64decode(image), name = file_name)
        cars_organization_files.car         = True
        cars_organization_files.file_bak    = decoded_image
    cars_organization_files.processed       = True
    cars_organization_files.save()
    
    answer = {
           'ok' : True
        }
    return JsonResponse(answer, status = status.HTTP_200_OK, safe = False)


@api_view(['GET', 'POST'])
def post_image_autoru_mark(request):
    
    body_unicode    = request.body.decode().replace("'", '"')
    data            = json.loads(body_unicode) 
    
    name        = data['name']
    image      = data['image']
    
    decoded_image = ContentFile(base64.b64decode(image), name=name)
    names = name.split(".")
    mark_name = names[0]

    count = AutoruMark.objects.filter(name__icontains = mark_name).count()
    if count > 0 :
        marks = AutoruMark.objects.filter(name__icontains = mark_name)
        for mark in marks:
            mark.file = decoded_image
            mark.save()

    answer = {
           'ok' : True
        }
    return JsonResponse(answer, status = status.HTTP_200_OK, safe = False)


def _api_param(request, key, default=''):
    value = request.GET.get(key, '')
    if value not in ('', None):
        return value
    if request.method == 'POST' and request.body:
        try:
            data = json.loads(request.body.decode().replace("'", '"'))
            value = data.get(key, default)
            if value not in ('', None):
                return value
        except (ValueError, json.JSONDecodeError):
            pass
    return default


def _autoru_mark_queryset(request):
    qs = AutoruMark.objects.all().order_by('name')
    id_mark = _api_param(request, 'id_mark')
    if id_mark not in ('', None):
        qs = qs.filter(idSite=id_mark)
    name = _api_param(request, 'name')
    if name:
        qs = qs.filter(Q(name__icontains=name) | Q(nameEn__icontains=name))
    only_with_logo = _api_param(request, 'only_with_logo')
    if str(only_with_logo).lower() in ('1', 'true', 'yes'):
        qs = qs.exclude(file='').exclude(file__isnull=True)
    return qs


def _resolve_autoru_mark(request):
    pk = _api_param(request, 'id')
    if pk not in ('', None):
        return AutoruMark.objects.filter(pk=pk).first()
    id_mark = _api_param(request, 'id_mark')
    if id_mark not in ('', None):
        return AutoruMark.objects.filter(idSite=id_mark).first()
    name = _api_param(request, 'name')
    if name:
        qs = AutoruMark.objects.filter(Q(name__iexact=name) | Q(nameEn__iexact=name))
        if qs.exists():
            return qs.first()
        return AutoruMark.objects.filter(
            Q(name__icontains=name) | Q(nameEn__icontains=name),
        ).first()
    return None


def _mark_logo_file_info(mark, request):
    if not mark.file or not mark.file.name:
        return None
    file_name = os.path.basename(mark.file.name)
    extension = os.path.splitext(file_name)[1].lstrip('.').lower() or 'png'
    return {
        'file_name': file_name,
        'extension': extension,
        'logo_url': request.build_absolute_uri(mark.file.url),
    }


@api_view(['GET', 'POST'])
def get_autoru_mark_logos(request):
    """Список марок AutoruMark с URL существующих логотипов для загрузки из 1С."""
    marks = _autoru_mark_queryset(request)
    result = []
    for mark in marks:
        item = {
            'id': mark.pk,
            'idSite': mark.idSite,
            'name': mark.name,
            'nameEn': mark.nameEn,
            'has_logo': bool(mark.file and mark.file.name),
            'logo_url': '',
            'file_name': '',
            'extension': '',
        }
        info = _mark_logo_file_info(mark, request)
        if info:
            item.update(info)
        result.append(item)
    return JsonResponse({'marks': result}, status=status.HTTP_200_OK, safe=False)


@api_view(['GET', 'POST'])
def get_autoru_mark_logo(request):
    """Скачать логотип марки AutoruMark (base64 + URL) для 1С."""
    mark = _resolve_autoru_mark(request)
    if not mark:
        return JsonResponse({
            'ok': False,
            'error': 'mark_not_found',
        }, status=status.HTTP_404_NOT_FOUND, safe=False)

    info = _mark_logo_file_info(mark, request)
    if not info:
        return JsonResponse({
            'ok': False,
            'error': 'logo_not_found',
            'id': mark.pk,
            'idSite': mark.idSite,
            'name': mark.name,
        }, status=status.HTTP_404_NOT_FOUND, safe=False)

    with mark.file.open('rb') as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode()

    return JsonResponse({
        'ok': True,
        'id': mark.pk,
        'idSite': mark.idSite,
        'name': mark.name,
        'nameEn': mark.nameEn,
        'file_name': info['file_name'],
        'extension': info['extension'],
        'logo_url': info['logo_url'],
        'image': image_base64,
    }, status=status.HTTP_200_OK, safe=False)


@api_view(['GET', 'POST'])
def post_image_avito_mark(request):
    
    body_unicode    = request.body.decode().replace("'", '"')
    data            = json.loads(body_unicode) 
    
    name        = data['name']
    image      = data['image']
    
    decoded_image = ContentFile(base64.b64decode(image), name=name)
    names = name.split(".")
    mark_name = names[0]

    count = RefAvito.objects.filter(parent = None).filter(name__icontains = mark_name).count()
    if count > 0 :
        marks = RefAvito.objects.filter(parent = None).filter(name__icontains = mark_name)
        for mark in marks:
            mark.file = decoded_image
            mark.save()

    answer = {
           'ok' : True
        }
    return JsonResponse(answer, status = status.HTTP_200_OK, safe = False)


@api_view(['GET', 'POST'])
def info_cars_organization(request):
    slug = request.GET.get('slug')
    try:
        cars_organization = RefCarsOrganization.objects.get(slug= slug)
        store = cars_organization.store
        user = None
        user_id = request.GET.get('user','')
        if user_id != '':
            user = User.objects.get(pk = int(user_id))
        add_statistic_cars_organization(user, cars_organization, store= store, type=request.GET.get('type'))
        
    except:
        s=1

    answer = {
        'ok': '200'
    }   
    return JsonResponse(answer, status=status.HTTP_200_OK)


@api_view(['POST'])
def refresh_cars(request):

    list_cars = list()

    data = json.loads(request.body)

    unit_json   = data['Unit']
    unit        = get_unit(unit_json)
    
    one_car = False
    if 'One' in data:
        one_car = data['One'] 

    count_add   = 0
    count_del   = 0
    count_stock = 0

    list_del = list()

    list_load_photo = list()
    cars_json       = data['Cars']
    
    list_cars_id = list()

    for car in cars_json:

        vin             = car.get('Vin', '').upper()
        lo_link_number  = car.get('Lo_link_number', '').upper()
        lo_uin          = car.get('Lo_uin', '').upper()

        car_object, created = RefCarsOrganization.objects.filter(Q(vin = vin) 
                                                                 and Q(lo_link_number = lo_link_number) 
                                                                 and Q(lo_uin = lo_uin),).get_or_create(vin = vin,
                lo_link_number = lo_link_number,
                lo_uin = lo_uin
            )
        
        if created:
            count_add = count_add + 1
        else:
            try:
                list_del.remove(car_object.pk)
            except:
                s = 1
        list_cars_id.append(car_object.pk)

        car_object.date_refresh     = datetime.now()    
        car_object.organization     = get_organization(car['Organization'])    
        car_object.unit             = unit
        car_object.store            = get_store(car['Store'])
        car_object.is_new           = car['Is_new']
        car_object.vin              = car.get('Vin', '').upper()
        car_object.vin2             = car['Vin2']
        car_object.name             = car['Name']
        car_object.year             = car['Year']
        car_object.mark             = car['Mark']
        car_object.model            = car['Model']
        car_object.modification     = car['Modification']
        car_object.color            = car['Color']
        car_object.run              = car['Run']
        car_object.plate_number     = car['Plate_number']
        car_object.cost_price       = car['Cost_price']
        car_object.outlay           = car['Outlay']
        car_object.days_in_stok     = car['Days_in_stok']
        car_object.price            = car['Price']
        car_object.quantity         = car['Quantity']
        car_object.lo_link              = car['Lo_link']
        car_object.lo_link_date         = car['Lo_link_date']
        car_object.lo_link_number       = car.get('Lo_link_number', '').upper()
        car_object.lo_uin               = car.get('Lo_uin', '').upper()
        car_object.type_drive           = get_model_object('RefTypeDrive', car['Type_drive'])
        car_object.stage_price          = get_stage_price(car['Stage_price'])
        car_object.group_price          = get_group_price(car['Group_price'])
        car_object.type_sale            = get_model_object('RefTypeSaleCarsOrganization', car['Type_sale'])
        car_object.status               = get_model_object('RefStatusCarsOrganization', car['Status'])
        car_object.type_reception       = get_model_object('RefTypeReceptionCarsOrganization', car['Type_reception'])
        car_object.evaluation           = get_model_object('RefTypeEvaluationCarsOrganization', car['Evaluation'])
        car_object.rating               = get_model_object('RefRatingCarsOrganization', car['Rating'])
        
        car_object.owners               = car['Owners']
        car_object.keys                 = car['Keys']
        car_object.task                 = car['Task']  
        car_object.reserve              = car['Reserve']             

        car_object.days_next_stage      = car['Days_next_stage']
        car_object.link_avtoteka_web    = car['Link_avtoteka_web']
        car_object.link_avtoteka_pdf    = car['Link_avtoteka_pdf']
        car_object.bcp                  = car['BCP']
        
        id_avito = car['ID_avitoru']
        try:
            if id_avito > 0:
                car_object.modification_avito = RefAvito.objects.get(avito_id = id_avito)
        except:
            s=1
            
        id_avtoru = car['ID_autoru']
        try:
            if id_avtoru > 0:
                car_object.modification_autoru = AutoruModification.objects.get(idSite = id_avtoru)
        except:
            s=1

        car_object.engine_power         = car['Engine_power']
        car_object.engine_volume        = car['Engine_volume']

        car_object.description_podgotovka   = car['Description_podgotovka']
        car_object.description_op           = car['Description_op']

        car_object.save()

        if 'Prices_list' in car:
            #RegRefCarsOrganizationsPrice.objects.filter(car= car_object).delete()
            for car_price in car['Prices_list']:
                if RegRefCarsOrganizationsPrice.objects.filter(Q(car = car_object) and Q(date = car_price['Date'])).count() < 2:
                    data_info, created = RegRefCarsOrganizationsPrice.objects.filter(Q(car = car_object) 
                                                                    and Q(date = car_price['Date']) 
                                                                                            ).get_or_create(car = car_object,
                                                                                                                    date = car_price['Date']
                                                                                                                )
                    if created:
                        data_info.price = car_price['Price']
                        data_info.save()  

        if 'Prices_calculation_list' in car:
            #RegRefCarsOrganizationsCalculationPrice.objects.filter(car= car_object).delete()
            for car_price in car['Prices_calculation_list']:
                evaluation = get_model_object('RefTypeEvaluationCarsOrganization', car_price['Evaluation'])
                if RegRefCarsOrganizationsCalculationPrice.objects.filter(Q(car = car_object) 
                                                                 and Q(date = car_price['Date']) 
                                                                 and Q(evaluation = evaluation),).count() < 2:
                    data_info, created = RegRefCarsOrganizationsCalculationPrice.objects.filter(Q(car = car_object) 
                                                                    and Q(date = car_price['Date']) 
                                                                    and Q(evaluation = evaluation),).get_or_create(car = car_object,
                                                                                                                    date = car_price['Date'],
                                                                                                                    evaluation = evaluation
                                                                                                                )
                    if created:
                        data_info.price         = car_price['Price']
                        data_info.rule          = car_price['Rule']
                        data_info.save()     

        info_car = {
            'Car_object'        : car_object,
            'Lo_uin'            : car['Lo_uin'],
            'Photos'            : car['Photos']
        }
        list_load_photo.append(info_car)
    
    if one_car == False:
        cars_update = RefCarsOrganization.objects.filter(unit = unit).exclude(quantity = 0).exclude(pk__in = list_cars_id)    
        for car in cars_update:
            car.quantity = 0
            car.save()
            list_del.append(car.pk)
        
    count_del   = len(list_del)
    count_stock = len(cars_json)

    refresh_log = RefreshCarsLog()
    refresh_log.unit = unit
    refresh_log.count_add   = count_add
    refresh_log.count_del   = count_del
    refresh_log.count_stock = count_stock
    refresh_log.save()

    for car in list_load_photo:
        car_object = car['Car_object']
        photos = normalize_photos_payload(car.get('Photos'))
        # Фото — в фоне (очередь refresh_cars_photos), ответ 1С не ждёт скачивания
        load_photos_async(car_object.pk, photos)

        qr_b64 = ''
        try:
            if car_object.qr:
                with car_object.qr.open() as image:
                    qr_b64 = base64.b64encode(image.read()).decode()
        except Exception:
            qr_b64 = ''

        car_link = 'https://ah.kors-group.com/cars/' + str(car_object.slug or '') + '/'
        list_cars.append({
            'Lo_Uin': car['Lo_uin'],
            'QR_Base64': qr_b64,
            'Lo_link': car_link,
        })

    info = {
        'list_cars' : list_cars
    }

    return JsonResponse(info, status=status.HTTP_200_OK)

@api_view(['POST'])
def refresh_new_cars(request):

    list_cars = list()

    data = json.loads(request.body)

    unit_json   = data['Unit']
    unit        = get_unit(unit_json)
    
    one_car = False
    if 'One' in data:
        one_car = data['One'] 

    count_add   = 0
    count_del   = 0
    count_stock = 0

    list_del = list()

    list_load_photo = list()
    cars_json       = data['Cars']
    
    list_cars_id = list()

    RefCarsOrganization.objects.filter(unit = unit).filter(quantity__gt = 0).update(quantity = 0)

    for car in cars_json:

        uin          = car.get('Uin', '').upper()

        car_object, created = RefCarsOrganization.objects.filter(Q(lo_uin = uin) 
                                                                 and Q(is_new = True)).get_or_create(
                                                                     lo_uin = uin,
                                                                     is_new = True)
        if created:
            count_add = count_add + 1
        else:
            try:
                list_del.remove(car_object.pk)
            except:
                s = 1
        list_cars_id.append(car_object.pk)

        car_object.date_refresh     = datetime.now()    
        car_object.organization     = get_organization(car['Organization'])    
        car_object.unit             = unit
        #car_object.store            = get_store(car['Store'])
        car_object.is_new           = True
        car_object.vin              = car.get('Vin', '').upper()
        #car_object.vin2             = car['Vin2']
        #car_object.name             = car['Name']
        car_object.year             = car['Year']
        #car_object.mark             = car['Mark']
        #car_object.model            = car['Model']
        #car_object.modification     = car['Modification']
        car_object.color            = car['Color']
        #car_object.run              = car['Run']
        #car_object.plate_number     = car['Plate_number']
        car_object.cost_price       = car['Cost_price']
        #car_object.outlay           = car['Outlay']
        #car_object.days_in_stok     = DT.datetime.strptime(car['Days_in_stok'], '%Y-%m-%dT%H:%M:%S').date()
        car_object.price            = car['Price']
        car_object.quantity         = 1
        #car_object.lo_link              = car['Lo_link']
        car_object.lo_link_date         = DT.datetime.strptime(car['Lo_link_date'], '%Y-%m-%dT%H:%M:%S')
        #car_object.lo_link_number       = car.get('Lo_link_number', '').upper()
        #car_object.lo_uin               = car.get('Lo_uin', '').upper()
        #car_object.type_drive           = get_model_object('RefTypeDrive', car['Type_drive'])
        #car_object.stage_price          = get_stage_price(car['Stage_price'])
        #car_object.group_price          = get_group_price(car['Group_price'])
        #car_object.type_sale            = get_model_object('RefTypeSaleCarsOrganization', car['Type_sale'])
        car_object.status               = get_model_object('RefStatusCarsOrganization', car['Status'])
        #car_object.type_reception       = get_model_object('RefTypeReceptionCarsOrganization', car['Type_reception'])
        #car_object.evaluation           = get_model_object('RefTypeEvaluationCarsOrganization', car['Evaluation'])
        #car_object.rating               = get_model_object('RefRatingCarsOrganization', car['Rating'])
        
        #car_object.owners               = car['Owners']
        #car_object.keys                 = car['Keys']
        #car_object.task                 = car['Task']  
        car_object.reserve              = car['Reserve']             
        car_object.status_availability  = get_model_object('RefStatusAvailability', car['Status_availability'])
        car_object.attention            = car['Attention']
        car_object.note                 = car['Note']

        #car_object.days_next_stage      = car['Days_next_stage']
        #car_object.link_avtoteka_web    = car['Link_avtoteka_web']
        #car_object.link_avtoteka_pdf    = car['Link_avtoteka_pdf']
        #car_object.bcp                  = car['BCP']
        
        #id_avito = car['ID_avitoru']
        #try:
        #    if id_avito > 0:
        #        car_object.modification_avito = RefAvito.objects.get(avito_id = id_avito)
        #except:
        #    s=1
            
        id_avtoru = car['ID_autoru']
        try:
            if int(id_avtoru) > 0:
                car_object.modification_autoru = AutoruModification.objects.get(idSite = int(id_avtoru))
        except:
            s=1

        id_complectation = car['ID_complectation']
        try:
            if int(id_complectation) > 0:
                
                car_object.complectation_autoru = AutoruComplectation.objects.get(modification = car_object.modification_autoru, idSite = int(id_complectation))
        except:
            s=1
        #car_object.engine_power         = car['Engine_power']
        #car_object.engine_volume        = car['Engine_volume']

        #car_object.description_podgotovka   = car['Description_podgotovka']
        #car_object.description_op           = car['Description_op']

        car_object.save()
        car_object.refresh_data()


        # if 'Prices_list' in car:
        #     #RegRefCarsOrganizationsPrice.objects.filter(car= car_object).delete()
        #     for car_price in car['Prices_list']:
        #         if RegRefCarsOrganizationsPrice.objects.filter(Q(car = car_object) and Q(date = car_price['Date'])).count() < 2:
        #             data_info, created = RegRefCarsOrganizationsPrice.objects.filter(Q(car = car_object) 
        #                                                             and Q(date = car_price['Date']) 
        #                                                                                     ).get_or_create(car = car_object,
        #                                                                                                             date = car_price['Date']
        #                                                                                                         )
        #             if created:
        #                 data_info.price = car_price['Price']
        #                 data_info.save()  

        # if 'Prices_calculation_list' in car:
        #     #RegRefCarsOrganizationsCalculationPrice.objects.filter(car= car_object).delete()
        #     for car_price in car['Prices_calculation_list']:
        #         evaluation = get_model_object('RefTypeEvaluationCarsOrganization', car_price['Evaluation'])
        #         if RegRefCarsOrganizationsCalculationPrice.objects.filter(Q(car = car_object) 
        #                                                          and Q(date = car_price['Date']) 
        #                                                          and Q(evaluation = evaluation),).count() < 2:
        #             data_info, created = RegRefCarsOrganizationsCalculationPrice.objects.filter(Q(car = car_object) 
        #                                                             and Q(date = car_price['Date']) 
        #                                                             and Q(evaluation = evaluation),).get_or_create(car = car_object,
        #                                                                                                             date = car_price['Date'],
        #                                                                                                             evaluation = evaluation
        #                                                                                                         )
        #             if created:
        #                 data_info.price         = car_price['Price']
        #                 data_info.rule          = car_price['Rule']
        #                 data_info.save()     

        # info_car = {
        #     'Car_object'        : car_object,
        #     'Lo_uin'            : car['Lo_uin'],
        #     'Photos'            : car['Photos']
        # }
        # list_load_photo.append(info_car)
    
    # if one_car == False:
    #     cars_update = RefCarsOrganization.objects.filter(unit = unit).exclude(quantity = 0).exclude(pk__in = list_cars_id)    
    #     for car in cars_update:
    #         car.quantity = 0
    #         car.save()
    #         list_del.append(car.pk)
        
    # count_del   = len(list_del)
    # count_stock = len(cars_json)

    # refresh_log = RefreshCarsLog()
    # refresh_log.unit = unit
    # refresh_log.count_add   = count_add
    # refresh_log.count_del   = count_del
    # refresh_log.count_stock = count_stock
    # refresh_log.save()

    # for car in list_load_photo:
        
    #     car_object = car['Car_object']
    #     load_photos(car_object, car['Photos'])

    #     image           = car_object.qr.open()
    #     image_content   = image.read()
    #     image_base64    = base64.b64encode(image_content)
    #     car_link        = 'https://ah.kors-group.com/cars/' + str(car_object.slug) + '/'
        
    #     car_info = {
    #         'Lo_Uin'    : car['Lo_uin'],
    #         'QR_Base64' : str(image_base64.decode()),
    #         'Lo_link'   : car_link
    #     }
        
    #     list_cars.append(car_info)
    
    list_cars = list()
    info = {
        'list_cars' : list_cars
    }

    return JsonResponse(info, status=status.HTTP_200_OK)


# load_photos / load_photos_async — см. api.tasks_cars
