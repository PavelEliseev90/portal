from django.shortcuts import render
from asyncio.windows_events import NULL
import random
import os
from itertools import groupby
from django.utils.translation import activate
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from collections import defaultdict
from django.contrib.auth.models import Group
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
from django.db.models.functions import Concat

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
from refs.models import RefTypeDisk, RefMarkTyres, RefWidthTyres, RefProfileTyres, RefRadius, RefSezonTyres, RefEtDisk, RefDiaDisk, RefPsdDisk, RefTypeReceptionCarsOrganization, AutoruModification, RefOrganization, RefStaff, RefUnit, RefFilial, RefManufacturer, RefCarsOrganization, RefStore, RefTypeEvaluationCarsOrganization, RefCarsOrganizationFiles, filter_units_available_for_portal_estimation, rlk_blocks_portal_estimation
from register.models import RegInteractivOcenkaEmailPush, RegInteractivOcenkaSoglasovanie, RegInteractivOcenkaProverki, RegInteractivOcenkaKolesa, RegInteractivOcenkaTestDrive, RegInteractivOcenkaComplectnost, RegInteractivOcenkaVnesh, RegDashboardError, RegInteractivOcenka, RegInteractivOcenkaDocument, RegRegInteractivOcenkaFiles, RegInteractivOcenkaSalon

from documents.models import DocRLK, DocLO, DocZN
import tempfile
from django.core import files
from datetime import datetime
from django.db.models import Q
from refs.serializers import RefTypeReceptionCarsOrganizationSerializer, RefManufacturerSerializer, RefCarsOrganizationSerializer, RefStoreSerializer, RefOrganizationSerializer, RefUnitSerializer, RefFilialSerializer
from documents.serializers import DocRLKSerializer
from django.core.paginator import Paginator
import json
from django.db.models import Count, Sum, Max, Avg, F, OuterRef, Subquery, Sum, Q, Func, Value, CharField
from django.db import models
from django.shortcuts import get_object_or_404

from django.contrib.contenttypes.models import ContentType
from django.apps import apps
from django.contrib.auth.models import User, Group




def get_rlk_eco(user, type):
    
    rlks = RegInteractivOcenka.objects.filter(staff__domain_login = user.username)


    if type == 1: #Продолжить оценку
        rlks = rlks.filter(end_estimation = None)
    elif type == 2: #На согласовании
        rlks = rlks.exclude(end_estimation = None).filter(page_soglasovanie__price_after_kd = 0)

    
    rlks = rlks.values(
        slug = F("rlk__id"),
        estimation      = F('id'),
        estimation_vin  = F('vin'),
        estimation_modification_name  = F('modification__name'),
        estimation_model_name      = F('modification__model__name'),
        estimation_mark_name       = F('modification__model__mark__name'),
        estimation_year       = F('year'),
        unit_name       = F('rlk__unit__name'),
        estimation_start_formated =Func(
            F('start_estimation'),
            Value('DD.MM.YYYY HH:MM:SS'),
            function='to_char',
            output_field=CharField()
        ),
        date =Func(
            F('rlk__dataTime'),
            Value('DD.MM.YYYY HH:MM:SS'),
            function='to_char',
            output_field=CharField()
        ),
        staff_name = F('rlk__staff__name'),
        comment_administrator = F('rlk__commentAdministrator'),
        comment_manager = F('rlk__commentManager'),
        type_contact = F('rlk__contacType__name'),
        customer_name = F('rlk__clientName'),
        price_reception = F('page_soglasovanie__price_reception'),
        number = F('rlk__nomer'),
            ).values(
                'estimation_start_formated' ,
                'slug',
                'estimation',
                'estimation_vin',
                'unit_name',
                'date',
                'staff_name',
                'comment_administrator',
                'comment_manager',
                'type_contact',
                'customer_name',
                'number',
                'estimation_modification_name',
                'estimation_model_name',
                'estimation_mark_name',
                'estimation_year',
                'price_reception'
                ).distinct().order_by('-rlk__dataTime')
    
    return list(rlks)


def get_user_info(request):

    user            = None
    profiles        = None
    user_auth_tuple = BasicAuthentication().authenticate(request)
    
    if user_auth_tuple is not None:
        user, _         = user_auth_tuple
    elif request.user and request.user.is_authenticated:
        # Веб-пользователи: сессия Django (cookies)
        user            = request.user
    
    if user == None:
        answer = {
            'autentification'   : False   
        }
        user_info = {
            'autentification'   : False,
            'user'              : user, 
            'answer'            : answer
        }
        return user_info
    
    profiles = user.profiles

    answer = {
        'autentification'   : True, 
        'user'              : user.pk, 
        'family'            : user.last_name,
        'name'              : user.first_name,
        'phone'             : str(user.profiles.phone),
        'email'             : user.email,
        'city'              : '',
        'date'              : user.date_joined.strftime("%d-%m-%Y %H:%M:%S"),
        'is_staff'          : user.is_staff
        
    }
    user_info = {
        'autentification'   : True,
        'user'              : user,
        'porfiles'          : profiles,
        'answer'            : answer
    }
    return user_info


@api_view(['GET'])
def user_desctop(request):
    user_info   = get_user_info(request)
    
    if user_info['user'] == None:
        
        answer = {
            'type'              : 'desctop',
            'user'              : user_info['answer'],
            'objects'           : list(),
            'app_version_number': settings.APP_VERSION_NUMBER,
            'app_link'          : settings.APP_LINK
        }

        return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)
    
    user        = user_info['user']
    
    to_json = {
        'type'              : 'desctop',
        'user'              : user_info['answer'],
        'error'             : '',
        'app_version_number': settings.APP_VERSION_NUMBER,
        'app_link'          : settings.APP_LINK
    }
    
    if user.is_staff:
        rlk_eco                 = get_rlk_eco(user, 1)
        rlk_eco_soglasovanie    = get_rlk_eco(user, 2)
        to_json['rlks_estimation'] = rlk_eco
        to_json['rlks_estimation_sogrlasovanie'] = rlk_eco_soglasovanie
    
    return JsonResponse(to_json, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
def login_in(request):
    
    user                = None
    profiles_user       = False
    error               = ''
    data                = None

    user_auth_tuple = BasicAuthentication().authenticate(request)
    if user_auth_tuple is not None:
        user, _         = user_auth_tuple
        profiles_user   = True
    
    if request.method == 'POST':
        
        body_unicode    = request.body.decode()
        if len(body_unicode):
            data            = json.loads(body_unicode)

        if user != None:
            if user.is_active:
                
                answer_json = {
                    'family'    : user.last_name,
                    'name'      : user.first_name,
                    'phone'     : str(user.profiles.phone),
                    'email'     : user.email,
                    'role'      : 0,
                    'city'      : '',
                    #'pol'       : user.profiles.bio,
                    'date'      : user.date_joined.strftime("%d-%m-%Y %H:%M:%S")
                }

            else:
                error = 'Учетная запись не активна'
        else:
            error = 'Неправильная пара логин / пароль'

        to_json = {
            'user'      : str(user),
            'profiles'  : profiles_user,
            'answer'    : answer_json,
            'type'      : 'login',
            'error'     : error
        }

        return JsonResponse(to_json, status=status.HTTP_200_OK)
    
    return JsonResponse('', status=status.HTTP_200_OK)


@api_view(['GET'])
def login_info(request):
    
    user_info           = get_user_info(request)
    error               = ''
    
    to_json = {
        'type'      : 'login_info',
        'user'      : user_info['answer'],
        'answer'    : user_info['answer'],
        'error'     : error
    }

    return JsonResponse(to_json, status=status.HTTP_200_OK)


#Оценка автомобилилей
@api_view(['GET'])
def rlk_eco(request):
    
    user_info = get_user_info(request=request)

    docs        = DocRLK.objects.filter(eco = True)
    subquery    = DocLO.objects.filter(rlk__id = OuterRef(name='id'))
    docs        = docs.annotate(lo_vin = Subquery(subquery.values('vin')[:1])).annotate(lo_pk = Subquery(subquery.values('id')[:1]))

    return JsonResponse('', status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
def list_cars_new_refresh(request):

    user_info = get_user_info(request=request)

    select_count = request.GET.get('select_count', 5)
    
    cars = RefCarsOrganization.objects.filter(status__id = 2).filter(reserve = 0).exclude(quantity = 0).order_by('-lo_link_date')
    subquery    = Subquery(RefCarsOrganizationFiles.objects.filter(сars_organization_id = OuterRef(name='id')).values('id')[:1], output_field = models.IntegerField())
    cars        = cars.annotate(photos = Count(subquery))
    cars        = cars.exclude(photos = 0)
        
    filter_count = 0
    store_id = request.GET.get('store', '')
    if store_id != "":
        filter_count = filter_count + 1 
        cars = cars.filter(store__id = store_id)
    
    page_number = request.GET.get('page', 1)
        
    paginator   = Paginator(cars, select_count)
    page_obj    = paginator.get_page(page_number)

    cars_json = RefCarsOrganizationSerializer(page_obj.object_list, many=True).data
    
    answer = {
        'type'              : 'cars_refresh',
        'user'              : user_info['answer'],
        'page_number'       : page_number,
        'objects'           : cars_json
    }   
    
    return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
def list_cars(request):
    
    user_info = get_user_info(request=request)

    select_count = request.GET.get('select_count', 5)
    
    cars        = RefCarsOrganization.objects.filter(status__id = 2).filter(reserve = 0).exclude(quantity = 0).order_by('-lo_link_date')
    subquery    = Subquery(RefCarsOrganizationFiles.objects.filter(сars_organization_id = OuterRef(name='id')).values('id')[:1], output_field = models.IntegerField())
    cars        = cars.annotate(photos = Count(subquery))
    cars        = cars.exclude(photos = 0)
        
    filter_count = 0
    store_id = request.GET.get('store', '')
    if store_id != "":
        filter_count = filter_count + 1 
        cars = cars.filter(store__id = store_id)
    
    page_number = request.GET.get('page', 1)
        
    paginator   = Paginator(cars, select_count)
    page_obj    = paginator.get_page(page_number)

    cars_json = RefCarsOrganizationSerializer(page_obj.object_list, many=True).data

    answer = {
        'type'              : 'cars_refresh',
        'user'              : user_info['answer'],
        'page_number'       : page_number,
        'objects'           : cars_json    
    }   
    
    return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)


@api_view(['GET'])
def car(request, slug_car):
    user_info = get_user_info(request=request)

    try:
        car_object = RefCarsOrganization.objects.get(slug=slug_car)
        car = RefCarsOrganizationSerializer(car_object, many=False).data
    except RefCarsOrganization.DoesNotExist:
        car = None
        raise Http404("Given query not found....")
    
    answer = {
        'type'  : 'car',
        'user'  : user_info['answer'],
        'car'   : car
    }

    return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)


@api_view(['GET'])
def staff_rlks_units(request):
    user_info = get_user_info(request=request)
    if user_info['user'] == None:
        answer = {
        'type'      : 'staff_rlks_unit',
        'user'      : user_info['answer'],
        'objects'   : list()
        }

        return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)
    
    objects = DocRLK.objects.filter(unit__buauto = True).filter(eco = True).values('unit_id', 'unit__name').distinct().order_by('unit__name')

    answer = {
        'type'      : 'staff_rlks_unit',
        'user'      : user_info['answer'],
        'objects'   : list(objects)
    }

    return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)


@api_view(['GET'])
def staff_rlks_unit(request, slug_unit):
    select_count = 10
    user_info = get_user_info(request=request)
    if user_info['user'] == None:
        answer = {
        'type'      : 'staff_rlks_unit',
        'user'      : user_info['answer'],
        'objects'   : list()
        }

        return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)
    
    unit    = RefUnit.objects.get(id = slug_unit)
    objects = DocRLK.objects.filter(unit__buauto = True).filter(eco = True).filter(unit_id = slug_unit).values(
        slug = F("id"),
        estimation      = F('reginteractivocenka'),
        estimation_vin  = F('reginteractivocenka__vin'),
        estimation_start_formated = Func(
            F('reginteractivocenka__start_estimation'),
            Value('DD.MM.YYYY HH:MM:SS'),
            function='to_char',
            output_field=CharField()
        ),
        unit_name       = F('unit__name'),
        date = Func(
            F('dataTime'),
            Value('DD.MM.YYYY HH:MM:SS'),
            function='to_char',
            output_field=CharField()
        ),
        staff_name = F('staff__name'),
        comment_administrator = F('commentAdministrator'),
        comment_manager = F('commentManager'),
        type_contact = F('contacType__name'),
        customer_name = F('clientName'),
        number = F('nomer'),
            ).distinct().order_by('-dataTime')
    
    page_number = request.GET.get('page', 1)
        
    paginator   = Paginator(objects, select_count)
    page_obj    = paginator.get_page(page_number)
    
    answer = {
        'type'              : 'staff_rlks_unit',
        'user'              : user_info['answer'],
        'title'             : unit.name,
        'objects'           : list(page_obj),
        'objects_count'     : paginator.count,
    }

    return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)


@api_view(['GET'])
def staff_rlk(request, slug_rlk):
    select_count = 10
    user_info = get_user_info(request=request)
    
    if user_info['user'] == None:
        
        answer = {
            'type'      : 'staff_rlk',
            'user'      : user_info['answer'],
            'objects'   : list()
        }

        return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)
    
    try:
        object              = DocRLK.objects.get(id=slug_rlk)
        object_serializer   = DocRLKSerializer(object, many=False).data
    except DocRLK.DoesNotExist:
        object = None
        raise Http404("Given query not found....")
    
    answer = {
        'type'              : 'staff_rlk',
        'user'              : user_info['answer'],
        'title'             : '' + str(object.nomer) + ' от ' + object.dataTime.strftime("%d.%m.%Y %H:%M:%S"),
        'object'            : object_serializer
    }

    return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)


#Начало оценки автомобиля
#Вкладка документы
@api_view(['GET'])
def estimation_documents_start(request, slug_rlk):
    
    user_info = get_user_info(request=request)

    firms               = RefOrganizationSerializer(RefOrganization.objects.filter(active_eco = True).order_by('name'), many=True).data
    filials             = RefFilialSerializer(RefFilial.objects.filter(active_eco = True).order_by('name'), many=True).data
    #units               = RefUnitSerializer(RefUnit.objects.filter(active_eco = True).order_by('name'), many=True).data
    stores              = RefStoreSerializer(RefStore.objects.filter(active_eco = True).order_by('name'), many=True).data
    type_receptions     = RefTypeReceptionCarsOrganizationSerializer(RefTypeReceptionCarsOrganization.objects.all().order_by('name'), many=True).data

    answer = {
        'type'              : 'estimation_documents_start',
        'user'              : user_info['answer'],
        'title'             : 'Данные заполнения документов',
        'firms'             : firms,
        'filials'           : filials,
        #'units'             : units,
        'stores'            : stores,
        'type_receptions'   : type_receptions
    }

    return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)


@api_view(['POST'])
def estimation_documents_post(request, slug_rlk):
    
    user_info = get_user_info(request=request)

    body_unicode    = request.body.decode().replace("'", '"')
    data            = json.loads(body_unicode)

    object                          = DocRLK.objects.get(id = slug_rlk)
    reg_interactiv_ocenka, created  = RegInteractivOcenka.objects.get_or_create(rlk = object)
    
    if reg_interactiv_ocenka.page_documents == None:
        reg_interactiv_ocenka_document = RegInteractivOcenkaDocument()
        reg_interactiv_ocenka_document.save()
        reg_interactiv_ocenka.page_documents = reg_interactiv_ocenka_document
        reg_interactiv_ocenka.save()
    else:
        reg_interactiv_ocenka_document = reg_interactiv_ocenka.page_documents

    reg_interactiv_ocenka_document.start_estimation     = datetime.fromtimestamp(int(str(data.get('TimeStart'))[:10]))
    reg_interactiv_ocenka_document.end_estimation       = datetime.fromtimestamp(int(str(data.get('TimeEnd'))[:10]))
    reg_interactiv_ocenka_document.count_owners         = 0 if data.get('CountOwners') == '' else data.get('CountOwners')
    reg_interactiv_ocenka_document.count_key            = 0 if data.get('CountKeys') == '' else data.get('CountKeys')
    reg_interactiv_ocenka_document.plate_number         = data.get('GosNomer')
    reg_interactiv_ocenka_document.engine_number        = data.get('EngineNomer')
    reg_interactiv_ocenka_document.pts_color            = data.get('ColorPTS')
    reg_interactiv_ocenka_document.pts_number           = data.get('PTSNomer')

    reg_interactiv_ocenka_document.organization         = get_organization(data.get('Firma'))
    reg_interactiv_ocenka_document.filial               = get_filial(data.get('Filial'))
    reg_interactiv_ocenka_document.store                = get_store(data.get('Store'))
    reg_interactiv_ocenka_document.type_reception       = get_type_reception(data.get('TypeOcenki'))

    reg_interactiv_ocenka_document.customer_family      = data.get('ClientFamily')  
    reg_interactiv_ocenka_document.customer_name        = data.get('ClientName')  
    reg_interactiv_ocenka_document.customer_patronymic  = data.get('ClientOtv')  
    reg_interactiv_ocenka_document.customer_phone       = data.get('ClientPhone')  
    reg_interactiv_ocenka_document.customer_region      = data.get('ClientObl')  

    if reg_interactiv_ocenka_document.store != None:
        reg_interactiv_ocenka_document.unit = reg_interactiv_ocenka_document.store.unit

    if data.get('PTSDate') != '':
        reg_interactiv_ocenka_document.pts_date     = datetime.strptime(data.get('PTSDate'), '%d.%m.%Y')
        
    reg_interactiv_ocenka_document.pts_original         = data.get('PTSOriginal')
    reg_interactiv_ocenka_document.pts_mark_model       = data.get('MarkModPTS')
    reg_interactiv_ocenka_document.sts_number           = data.get('STSNomer')

    if data.get('STSDate') != '':
        reg_interactiv_ocenka_document.sts_date = datetime.strptime(data.get('STSDate'), '%d.%m.%Y')

    reg_interactiv_ocenka_document.car_credit           = data.get('Kredit')
    reg_interactiv_ocenka_document.sale_auto_ru         = data.get('AutoRu')
    reg_interactiv_ocenka_document.sale_avito_ru        = data.get('Avito')
    reg_interactiv_ocenka_document.sale_drom_ru         = data.get('Drom')

    reg_interactiv_ocenka_document.text_json = str(data)
    reg_interactiv_ocenka_document.save()

    answer = {
        'type'              : 'estimation_documents_post',
        'user'              : user_info['answer'],
        'title'             : 'Данные заполнения документов',
        
    }

    return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)



    #            data.get("Firma",          firma);
    #            data.get("Filial",         filial);
    #            data.get("Mop",            mop);
    #                data.get("Store",              stoyanka);

    #            data.get("TypeOcenki",         typeOcenka);
    #            data.get("TypeOcenkaCount",    typeOcenkaCount);

    #            data.get("NewAvto",            newAvto);
    #            data.get("NewAvtoMenedger",    newAvtoMenedger);


@api_view(['POST'])
def estimation_salon_post(request, slug_rlk):
    
    user_info = get_user_info(request=request)

    body_unicode    = request.body.decode().replace("'", '"')
    data            = json.loads(body_unicode)

    object                          = DocRLK.objects.get(id = slug_rlk)
    reg_interactiv_ocenka, created  = RegInteractivOcenka.objects.get_or_create(rlk = object)
    
    if reg_interactiv_ocenka.page_salon == None:
        reg_interactiv_ocenka_salon = RegInteractivOcenkaSalon()
        reg_interactiv_ocenka_salon.save()
        reg_interactiv_ocenka.page_salon = reg_interactiv_ocenka_salon
        reg_interactiv_ocenka.save()
    else:
        reg_interactiv_ocenka_salon = reg_interactiv_ocenka.page_salon

    reg_interactiv_ocenka_salon.start_estimation        = datetime.fromtimestamp(int(str(data.get('TimeStart'))[:10]))
    reg_interactiv_ocenka_salon.end_estimation          = datetime.fromtimestamp(int(str(data.get('TimeEnd'))[:10]))

    reg_interactiv_ocenka_salon.run                     = 0 if data.get('Run') == '' else data.get('Run')
    reg_interactiv_ocenka_salon.run_confirmed           = data.get('RunPodtv')
    reg_interactiv_ocenka_salon.run_confirmed_comment   = data.get('RunPodtvText')

    reg_interactiv_ocenka_salon.cleaning        = data.get('RSTrebHim')
    reg_interactiv_ocenka_salon.damage_kpp      = data.get('RSKppFail')
    reg_interactiv_ocenka_salon.damage_wheel    = data.get('RSRulFail')
    reg_interactiv_ocenka_salon.damage_pedal    = data.get('RSPedalFail')
    reg_interactiv_ocenka_salon.damage_door     = data.get('RSDverFail')
    reg_interactiv_ocenka_salon.damage_seat     = data.get('RSSidenFail')

    if data.get('RSRTormozOK'):
        reg_interactiv_ocenka_salon.hand_brake          = 1        #'// 0 - не работает 1 работает 2 не проверен'
    if data.get('RSRTormozF'):
        reg_interactiv_ocenka_salon.hand_brake          = 0        #'// 0 - не работает 1 работает 2 не проверен'
    if data.get('RSRTormozFNo'):
        reg_interactiv_ocenka_salon.hand_brake          = 2        #'// 0 - не работает 1 работает 2 не проверен'

    if data.get('RSKondeyOK'):
        reg_interactiv_ocenka_salon.conductor          = 1        #'// 0 - не работает 1 работает 2 не проверен'
    if data.get('RSKondeyF'):
        reg_interactiv_ocenka_salon.conductor          = 0        #'// 0 - не работает 1 работает 2 не проверен'
    if data.get('RSKondeyFNo'):
        reg_interactiv_ocenka_salon.conductor          = 2        #'// 0 - не работает 1 работает 2 не проверен'

    if data.get('RSStekloOchT'):
        reg_interactiv_ocenka_salon.wiper          = 1        #'// 0 - не работает 1 работает 2 не проверен'
    if data.get('RSStekloOchF'):
        reg_interactiv_ocenka_salon.wiper          = 0        #'// 0 - не работает 1 работает 2 не проверен'
    if data.get('RSStekloOchFNo'):
        reg_interactiv_ocenka_salon.wiper          = 2        #'// 0 - не работает 1 работает 2 не проверен'

    if data.get('RSSignalOK'):
        reg_interactiv_ocenka_salon.signal          = 1        #'// 0 - не работает 1 работает 2 не проверен'
    if data.get('RSSignalF'):
        reg_interactiv_ocenka_salon.signal          = 0        #'// 0 - не работает 1 работает 2 не проверен'
    if data.get('RSSignalFNo'):
        reg_interactiv_ocenka_salon.signal          = 2        #'// 0 - не работает 1 работает 2 не проверен'

    if data.get('RSStekloPodOK'):
        reg_interactiv_ocenka_salon.power_windows       = 1        #'// 0 - не работает 1 работает 2 не проверен'
    if data.get('RSStekloPodF'):
        reg_interactiv_ocenka_salon.power_windows       = 0        #'// 0 - не работает 1 работает 2 не проверен'
    if data.get('RSStekloPodFNo'):
        reg_interactiv_ocenka_salon.power_windows       = 2        #'// 0 - не работает 1 работает 2 не проверен'
    
    if data.get('RSRemenOK'):
        reg_interactiv_ocenka_salon.seat_belt          = 1        #'// 0 - не работает 1 работает 2 не проверен'
    if data.get('RSRemenF'):
        reg_interactiv_ocenka_salon.seat_belt          = 0        #'// 0 - не работает 1 работает 2 не проверен'
    if data.get('RSRemenFNo'):
        reg_interactiv_ocenka_salon.seat_belt          = 2        #'// 0 - не работает 1 работает 2 не проверен'
    
    errors = data.get('ErrorPriborPanel')
    reg_interactiv_ocenka_salon.dashboard_error.clear()

    for error in errors:
        object_error = RegDashboardError.objects.get(uin = error)
        reg_interactiv_ocenka_salon.dashboard_error.add(object_error)

    reg_interactiv_ocenka_salon.text_json = str(data)
    reg_interactiv_ocenka_salon.save()

    answer = {
        'type'              : 'estimation_salon_post',
        'user'              : user_info['answer'],
        'title'             : 'Данные заполнения документов',
        
    }

    return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)



    #            data.get("Firma",          firma);
    #            data.get("Filial",         filial);
    #            data.get("Mop",            mop);
    #                data.get("Store",              stoyanka);

    #            data.get("TypeOcenki",         typeOcenka);
    #            data.get("TypeOcenkaCount",    typeOcenkaCount);

    #            data.get("NewAvto",            newAvto);
    #            data.get("NewAvtoMenedger",    newAvtoMenedger);


@api_view(['POST'])
def estimation_vnesh_post(request, slug_rlk):
    
    user_info = get_user_info(request=request)

    body_unicode    = request.body.decode().replace("'", '"')
    data            = json.loads(body_unicode)

    object                          = DocRLK.objects.get(id = slug_rlk)
    reg_interactiv_ocenka, created  = RegInteractivOcenka.objects.get_or_create(rlk = object)
    
    if reg_interactiv_ocenka.page_vnesh == None:
        reg_interactiv_ocenka_vnesh = RegInteractivOcenkaVnesh()
        reg_interactiv_ocenka_vnesh.save()
        reg_interactiv_ocenka.page_vnesh = reg_interactiv_ocenka_vnesh
        reg_interactiv_ocenka.save()
    else:
        reg_interactiv_ocenka_vnesh = reg_interactiv_ocenka.page_vnesh

    reg_interactiv_ocenka_vnesh.start_estimation        = datetime.fromtimestamp(int(str(data.get('TimeStart'))[:10]))
    reg_interactiv_ocenka_vnesh.end_estimation          = datetime.fromtimestamp(int(str(data.get('TimeEnd'))[:10]))

    reg_interactiv_ocenka_vnesh.windshield_error    = data.get('LobStekloError')
    reg_interactiv_ocenka_vnesh.light_error         = data.get('SvetPriborError')
    reg_interactiv_ocenka_vnesh.oil_error           = data.get('OilFail')
    reg_interactiv_ocenka_vnesh.water_error         = data.get('WaterFail')
    reg_interactiv_ocenka_vnesh.color               = data.get('ColorName')
    reg_interactiv_ocenka_vnesh.check_vin           = data.get('CProverkaVin')
    reg_interactiv_ocenka_vnesh.check_engine        = data.get('CProverkaEngine')
    reg_interactiv_ocenka_vnesh.text_json           = str(data)
    reg_interactiv_ocenka_vnesh.save()

    answer = {
        'type'              : 'estimation_vnesh_post',
        'user'              : user_info['answer'],
        'title'             : 'Данные заполнения документов',
        
    }

    return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)


@api_view(['POST'])
def estimation_complectnost_post(request, slug_rlk):
    
    user_info = get_user_info(request=request)

    body_unicode    = request.body.decode().replace("'", '"')
    data            = json.loads(body_unicode)

    object                          = DocRLK.objects.get(id = slug_rlk)
    reg_interactiv_ocenka, created  = RegInteractivOcenka.objects.get_or_create(rlk = object)
    
    if reg_interactiv_ocenka.page_complectnost == None:
        reg_interactiv_ocenka_compl = RegInteractivOcenkaComplectnost()
        reg_interactiv_ocenka_compl.save()
        reg_interactiv_ocenka.page_complectnost = reg_interactiv_ocenka_compl
        reg_interactiv_ocenka.save()
    else:
        reg_interactiv_ocenka_compl = reg_interactiv_ocenka.page_complectnost

    reg_interactiv_ocenka_compl.start_estimation        = datetime.fromtimestamp(int(str(data.get('TimeStart'))[:10]))
    reg_interactiv_ocenka_compl.end_estimation          = datetime.fromtimestamp(int(str(data.get('TimeEnd'))[:10]))

    reg_interactiv_ocenka_compl.prikur          = data.get('RKPrikurOK')
    reg_interactiv_ocenka_compl.ognet           = data.get('RKOgnetOK')
    reg_interactiv_ocenka_compl.kovrik          = data.get('RKKovrikOK')
    reg_interactiv_ocenka_compl.tros            = data.get('RKTrosOK')
    reg_interactiv_ocenka_compl.domkrat         = data.get('RKDomkratOK')
    reg_interactiv_ocenka_compl.znak_av         = data.get('RKZnakAvOK')
    reg_interactiv_ocenka_compl.ball_key        = data.get('RKBallKeyOK')
    reg_interactiv_ocenka_compl.zapas           = data.get('RKZapasOK')
    reg_interactiv_ocenka_compl.aptechka        = data.get('RKAptechkaOK')
    
    reg_interactiv_ocenka_compl.text_json           = str(data)
    reg_interactiv_ocenka_compl.save()

    answer = {
        'type'              : 'estimation_complectnost_post',
        'user'              : user_info['answer'],
        'title'             : 'Данные заполнения документов',
        
    }

    return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)


@api_view(['POST'])
def estimation_kolesa_post(request, slug_rlk):
    
    user_info = get_user_info(request=request)

    body_unicode    = request.body.decode().replace("'", '"')
    data            = json.loads(body_unicode)

    object                          = DocRLK.objects.get(id = slug_rlk)
    reg_interactiv_ocenka, created  = RegInteractivOcenka.objects.get_or_create(rlk = object)
    
    if reg_interactiv_ocenka.page_kolesa == None:
        reg_interactiv_ocenka_kolesa = RegInteractivOcenkaKolesa()
        reg_interactiv_ocenka_kolesa.save()
        reg_interactiv_ocenka.page_kolesa = reg_interactiv_ocenka_kolesa
        reg_interactiv_ocenka.save()
    else:
        reg_interactiv_ocenka_kolesa = reg_interactiv_ocenka.page_kolesa

    reg_interactiv_ocenka_kolesa.start_estimation       = datetime.fromtimestamp(int(str(data.get('TimeStart'))[:10]))
    reg_interactiv_ocenka_kolesa.end_estimation         = datetime.fromtimestamp(int(str(data.get('TimeEnd'))[:10]))
    reg_interactiv_ocenka_kolesa.mark_tyre              = get_ref_object('RefMarkTyres', data.get('MarkRez'))
    reg_interactiv_ocenka_kolesa.model_tyre             = data.get('ModRez')
    reg_interactiv_ocenka_kolesa.width_tyre             = get_ref_object('RefWidthTyres', data.get('WidthRez'))
    reg_interactiv_ocenka_kolesa.profil_tyre            = get_ref_object('RefProfileTyres', data.get('ProfilRez'))
    reg_interactiv_ocenka_kolesa.sezon                  = get_ref_object('RefSezonTyres', data.get('SezonRez'))
    reg_interactiv_ocenka_kolesa.model_disk             = data.get('ModelDisk')
    reg_interactiv_ocenka_kolesa.disk_type              = get_ref_object('RefTypeDisk', data.get('VidDisk'))
    reg_interactiv_ocenka_kolesa.radius                 = get_ref_object('RefRadius', data.get('RadiusRez'))
    reg_interactiv_ocenka_kolesa.et_disk                = get_ref_object('RefEtDisk', data.get('ETDisk'))
    reg_interactiv_ocenka_kolesa.dia_disk                = get_ref_object('RefDiaDisk', data.get('DIADisk'))
    reg_interactiv_ocenka_kolesa.psd_disk                = get_ref_object('RefPsdDisk', data.get('PCDDisk'))

    reg_interactiv_ocenka_kolesa.kolesa2                =  data.get('Kolesa2')
    if reg_interactiv_ocenka_kolesa.kolesa2:

        reg_interactiv_ocenka_kolesa.sezon2                 = get_ref_object('RefSezonTyres', data.get('SezonRez2'))
        reg_interactiv_ocenka_kolesa.mark_tyre2             = get_ref_object('RefMarkTyres', data.get('MarkRez2'))
        reg_interactiv_ocenka_kolesa.model_tyre2            = data.get('ModRez2')
        reg_interactiv_ocenka_kolesa.width_tyre2            = get_ref_object('RefWidthTyres', data.get('WidthRez2'))
        reg_interactiv_ocenka_kolesa.profil_tyre2           = get_ref_object('RefProfileTyres', data.get('ProfilRez2'))
        reg_interactiv_ocenka_kolesa.disk_type2             = get_ref_object('RefTypeDisk', data.get('VidDisk2'))
        reg_interactiv_ocenka_kolesa.model_disk2            = data.get('ModelDisk2')
        reg_interactiv_ocenka_kolesa.et_disk2               = get_ref_object('RefEtDisk', data.get('ETDisk2'))
        reg_interactiv_ocenka_kolesa.dia_disk2               = get_ref_object('RefDiaDisk', data.get('DIADisk2'))
        reg_interactiv_ocenka_kolesa.psd_disk2               = get_ref_object('RefPsdDisk', data.get('PCDDisk2'))
        reg_interactiv_ocenka_kolesa.count_disk2            = data.get('CountDisk2')
        reg_interactiv_ocenka_kolesa.count_tyre2            = data.get('CountRez2')

    reg_interactiv_ocenka_kolesa.text_json           = str(data)
    reg_interactiv_ocenka_kolesa.save()

    answer = {
        'type'              : 'estimation_kolesa_post',
        'user'              : user_info['answer'],
        'title'             : 'Данные заполнения документов',
        
    }

    return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)



@api_view(['POST'])
def estimation_test_drive_post(request, slug_rlk):
    
    user_info = get_user_info(request=request)

    body_unicode    = request.body.decode().replace("'", '"')
    data            = json.loads(body_unicode)

    object                          = DocRLK.objects.get(id = slug_rlk)
    reg_interactiv_ocenka, created  = RegInteractivOcenka.objects.get_or_create(rlk = object)
    
    if reg_interactiv_ocenka.page_test_drive == None:
        reg_interactiv_ocenka_test_drive = RegInteractivOcenkaTestDrive()
        reg_interactiv_ocenka_test_drive.save()
        reg_interactiv_ocenka.page_test_drive = reg_interactiv_ocenka_test_drive
        reg_interactiv_ocenka.save()
    else:
        reg_interactiv_ocenka_test_drive = reg_interactiv_ocenka.page_test_drive

    reg_interactiv_ocenka_test_drive.start_estimation        = datetime.fromtimestamp(int(str(data.get('TimeStart'))[:10]))
    reg_interactiv_ocenka_test_drive.end_estimation          = datetime.fromtimestamp(int(str(data.get('TimeEnd'))[:10]))

    if data.get('EOK'):
        reg_interactiv_ocenka_test_drive.engine          = 1        #'// 0 - не работает 1 работает 2 не проверен'
    if data.get('EFail'):
        reg_interactiv_ocenka_test_drive.engine          = 0        #'// 0 - не работает 1 работает 2 не проверен'
    if data.get('EAttention'):
        reg_interactiv_ocenka_test_drive.engine          = 2        #'// 0 - не работает 1 работает 2 не проверен'
    reg_interactiv_ocenka_test_drive.comment_engine = data.get('EngineComment')

    if data.get('VOK'):
        reg_interactiv_ocenka_test_drive.system_og          = 1        #'// 0 - не работает 1 работает 2 не проверен'
    if data.get('VFail'):
        reg_interactiv_ocenka_test_drive.system_og          = 0        #'// 0 - не работает 1 работает 2 не проверен'
    if data.get('VAttention'):
        reg_interactiv_ocenka_test_drive.system_og          = 2        #'// 0 - не работает 1 работает 2 не проверен'
    reg_interactiv_ocenka_test_drive.comment_system_og = data.get('VComment')


    if data.get('KppOK'):
        reg_interactiv_ocenka_test_drive.gear          = 1        #'// 0 - не работает 1 работает 2 не проверен'
    if data.get('KppFail'):
        reg_interactiv_ocenka_test_drive.gear          = 0        #'// 0 - не работает 1 работает 2 не проверен'
    if data.get('KppAttention'):
        reg_interactiv_ocenka_test_drive.gear          = 2        #'// 0 - не работает 1 работает 2 не проверен'
    reg_interactiv_ocenka_test_drive.comment_gear = data.get('KppComment')

    if data.get('PodveskaOK'):
        reg_interactiv_ocenka_test_drive.suspension          = 1        #'// 0 - не работает 1 работает 2 не проверен'
    if data.get('PodveskaFail'):
        reg_interactiv_ocenka_test_drive.suspension          = 0        #'// 0 - не работает 1 работает 2 не проверен'
    if data.get('PodveskaAttention'):
        reg_interactiv_ocenka_test_drive.suspension          = 2        #'// 0 - не работает 1 работает 2 не проверен'
    reg_interactiv_ocenka_test_drive.comment_suspension = data.get('PodveskaComment')

    reg_interactiv_ocenka_test_drive.no_test = data.get('СDriveOFF')
    reg_interactiv_ocenka_test_drive.comment = data.get('СDriveOFFCommeent')

    reg_interactiv_ocenka_test_drive.text_json           = str(data)
    reg_interactiv_ocenka_test_drive.save()

    answer = {
        'type'              : 'estimation_test_drive_post',
        'user'              : user_info['answer'],
        'title'             : 'Данные заполнения документов',
        
    }

    return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)


@api_view(['POST'])
def estimation_proverki_post(request, slug_rlk):
    
    user_info = get_user_info(request=request)

    body_unicode    = request.body.decode().replace("'", '"')
    data            = json.loads(body_unicode)

    object                          = DocRLK.objects.get(id = slug_rlk)
    reg_interactiv_ocenka, created  = RegInteractivOcenka.objects.get_or_create(rlk = object)
    
    if reg_interactiv_ocenka.page_proverki == None:
        reg_interactiv_ocenka_proverki = RegInteractivOcenkaProverki()
        reg_interactiv_ocenka_proverki.save()
        reg_interactiv_ocenka.page_proverki = reg_interactiv_ocenka_proverki
        reg_interactiv_ocenka.save()
    else:
        reg_interactiv_ocenka_proverki = reg_interactiv_ocenka.page_proverki

    reg_interactiv_ocenka_proverki.start_estimation        = datetime.fromtimestamp(int(str(data.get('TimeStart'))[:10]))
    reg_interactiv_ocenka_proverki.end_estimation          = datetime.fromtimestamp(int(str(data.get('TimeEnd'))[:10]))

    reg_interactiv_ocenka_proverki.count_dtp            = int(str(data.get('CountDTP')))
    reg_interactiv_ocenka_proverki.car_credit           = data.get('Kredit')
    
    reg_interactiv_ocenka_proverki.text_json           = str(data)
    reg_interactiv_ocenka_proverki.save()

    answer = {
        'type'              : 'estimation_proverki_post',
        'user'              : user_info['answer'],
        'title'             : 'Данные заполнения документов',
        
    }

    return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)


@api_view(['GET'])
def estimation_soglasovanie_get(request, slug_rlk):
    
    user_info = get_user_info(request=request)

    object                          = DocRLK.objects.get(id = slug_rlk)
    estimation, created             = RegInteractivOcenka.objects.get_or_create(rlk = object)
    
    #users = User.objects.exclude(pk__in = estimation.access_user.all().values_list('id')).exclude(email = '').exclude(first_name = '').filter(is_active = True).order_by('last_name', 'first_name').values('profiles__eco_name', 'last_name', 'first_name', 'id', 'email')
    users = User.objects.exclude(pk__in = estimation.access_user.all().values_list('id')).exclude(email = '').exclude(first_name = '').annotate(name=Concat('last_name', Value(' '), 'first_name', output_field=CharField())).order_by('last_name', 'first_name').values('name', 'id')
    answer = {
        'type'              : 'estimation_soglasovanie_get',
        'user'              : user_info['answer'],
        'title'             : 'Данные заполнения документов',
        'users'             : list(users)
    }

    return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)


@api_view(['POST'])
def estimation_soglasovanie_post(request, slug_rlk):
    
    user_info = get_user_info(request=request)

    body_unicode    = request.body.decode().replace("'", '"')
    data            = json.loads(body_unicode)

    object                          = DocRLK.objects.get(id = slug_rlk)
    reg_interactiv_ocenka, created  = RegInteractivOcenka.objects.get_or_create(rlk = object)
    
    if reg_interactiv_ocenka.page_soglasovanie == None:
        reg_interactiv_ocenka_soglasovanie = RegInteractivOcenkaSoglasovanie()
        reg_interactiv_ocenka_soglasovanie.save()
        reg_interactiv_ocenka.page_soglasovanie = reg_interactiv_ocenka_soglasovanie
        reg_interactiv_ocenka.save()
    else:
        reg_interactiv_ocenka_soglasovanie = reg_interactiv_ocenka.page_soglasovanie

    reg_interactiv_ocenka_soglasovanie.start_estimation        = datetime.fromtimestamp(int(str(data.get('TimeStart'))[:10]))
    reg_interactiv_ocenka_soglasovanie.end_estimation          = datetime.fromtimestamp(int(str(data.get('TimeEnd'))[:10]))

    reg_interactiv_ocenka_soglasovanie.price_sale               = int(str(data.get('PriceSale')))
    reg_interactiv_ocenka_soglasovanie.price_reception          = int(str(data.get('PriceReception')))
    reg_interactiv_ocenka_soglasovanie.comment                  = data.get('Comment')
    
    reg_interactiv_ocenka_soglasovanie.text_json           = str(data)
    reg_interactiv_ocenka_soglasovanie.save()

    users_ac = data.get('Access_user')
    for uss in users_ac:
        uss_base = User.objects.get(pk = uss['id'])
        reg_interactiv_ocenka.access_user.add(uss_base)
        new_message             = RegInteractivOcenkaEmailPush()
        new_message.estimation  = reg_interactiv_ocenka
        new_message.user        = uss_base
        new_message.comment     = 'Вы добавлены в участники интерактивной оценки.'
        new_message.save()
    
    reg_interactiv_ocenka.end_estimation = DT.datetime.now()
    reg_interactiv_ocenka.save()
    
    new_message             = RegInteractivOcenkaEmailPush()
    new_message.estimation  = reg_interactiv_ocenka
    new_message.user        = user_info['user']
    new_message.comment     = 'Интерактивная оценка отправлена на согласование.'
    new_message.save()
    
    users = User.objects.exclude(email = '').filter(profiles__eco = True)
    for user_push in users: 
        new_message = RegInteractivOcenkaEmailPush()
        new_message.estimation  = reg_interactiv_ocenka
        new_message.user        = user_push
        new_message.comment     = 'Интерактивная оценка отправлена на согласование, ознакомтесь.'
        new_message.save()

    #
    users = User.objects.exclude(email = '').filter(profiles__eco_visible = True)
    for user_push in users: 
        new_message = RegInteractivOcenkaEmailPush()
        new_message.estimation  = reg_interactiv_ocenka
        new_message.user        = user_push
        new_message.comment     = 'Новая интерактивная оценка отправлена на согласование'
        new_message.save()
    

    answer = {
        'type'              : 'estimation_soglasovanie_post',
        'user'              : user_info['answer'],
        'title'             : 'Данные заполнения документов',
        
    }

    return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)


#Добавление фотографий приемки автомобиля
@api_view(['POST'])
def estimation_add_fotos(request, slug_rlk):
    
    user_info = get_user_info(request=request)

    object                          = DocRLK.objects.get(id = slug_rlk)
    reg_interactiv_ocenka, created  = RegInteractivOcenka.objects.get_or_create(rlk = object)
    
    for key in request.POST.keys():
        if key.startswith('keys_'):
            file_info_key   = key.replace('keys', '')
            type_file       = request.POST.get('type' + file_info_key)
            file_name       = request.POST.get('file_name' + file_info_key, "")
            file_number     = int(request.POST.get('file_number' + file_info_key, '0'))

            key_text = 'text' + file_info_key
            if key_text in request.POST:
                text        = request.POST.get(key_text)
                type_point  = request.POST.get("type_point" + file_info_key)
                x           = int(request.POST.get("x" + file_info_key, '0'))
                y           = int(request.POST.get("y" + file_info_key, '0'))
                kraska_text = request.POST.get("kraska" + file_info_key)
                kraska = False
                if kraska_text == 'true':
                    kraska = True
                
                file_path  = request.POST.get("file_path" + file_info_key, "")   
                
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = type_file, type_point = type_point, text = text, cor_x = x, cor_y = y)
                new_estimation_files.name           = text
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                
                if kraska:
                    new_estimation_files.kraska         = int(text)

                if len(file_path) > 0:
                    file_object                 = request.FILES.get("file"+ file_info_key)
                    new_estimation_files.file           = file_object
                else:
                    new_estimation_files.blank  = True
                new_estimation_files.save()
    

            else:
                file_object     = request.FILES.get("file"+ file_info_key)
                
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = type_file, name = file_name )
                new_estimation_files.file           = file_object
                new_estimation_files.file_number    = file_number
                new_estimation_files.save()


    answer = {
        'type'              : 'estimation_add_fotos',
        'user'              : user_info['answer'],
        'title'             : 'Данные заполнения документов',
        'result'            : 'ok'
        
    }

    return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)


#История по автомобилю
#История оценок
@api_view(['GET'])
def vin_estimation(request, vin):
    
    user_info = get_user_info(request=request)
    
    if user_info['user'] == None:
        
        answer = {
            'type'      : 'vin_estimation',
            'user'      : user_info['answer'],
            'objects'   : list()
        }

        return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)
    
    objects = DocLO.objects.filter(vin = vin).values(
        slug            = F('id'),
        active_doc      = F('active'),
        unit_name       = F('unit__name'),
        year_car        = F('year'),
        run_car         = F('run'),
        car_mark        = F('cars__mark'),
        car_model       = F('cars__model'),
        car_name        = F('cars__name'),
        owners_doc      = F('owners'),
        cost_price_doc  = F('cost_price'),
        plate_number    = F('carsGRZ'),
        modification    = F('modification_autoru'),
        model           = F('modification_autoru__model'),
        mark            = F('modification_autoru__model__mark'),
        date = Func(
            F('dataTime'),
            Value('DD.MM.YYYY HH:MM:SS'),
            function='to_char',
            output_field=CharField()
        ),
        staff_name                  = F('staff__name'),
        description_podgotovka_doc  = F('description_podgotovka'),
        description_op_doc          = F('description_op'),
        type_reception_name         = F('type_reception__name'),
        customer_name               = F('clientName'),
        number                      = F('nomer'),
            ).distinct().order_by('-dataTime')

    answer = {
        'type'              : 'vin_estimation',
        'user'              : user_info['answer'],
        'title'             : 'История оценок по VIN',
        'objects'           : list(objects),
        'objects_count'     : len(objects)
    }

    return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)


#История ремонтов
@api_view(['GET'])
def vin_repairs(request, vin):
    
    user_info = get_user_info(request=request)
    
    if user_info['user'] == None:
        
        answer = {
            'type'      : 'vin_repairs',
            'user'      : user_info['answer'],
            'objects'   : list()
        }

        return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)
    
    objects = DocZN.objects.filter(cars__vin = vin).filter(closed = True).values(
        slug            = F('id'),
        active_doc      = F('closed'),
        unit_name       = F('unit__name'),
        run_car         = F('run'),
        amount_doc      = F('amount'),
        plate_number    = F('carsGRZ'),
        car_mark        = F('cars__mark'),
        car_model       = F('cars__model'),
        car_name        = F('cars__name'),
        date = Func(
            F('dataTime'),
            Value('DD.MM.YYYY HH:MM:SS'),
            function='to_char',
            output_field=CharField()
        ),
        staff_name                  = F('master__name'),
        customer_words              = F('customerWords'),
        recomendation_work          = F('recomendation'),
        type_repair_name            = F('typeRemont__name'),
        customer_name               = F('clientName'),
        number                      = F('nomer'),
            ).distinct().order_by('-dataTime')
    

    answer = {
        'type'              : 'vin_repairs',
        'user'              : user_info['answer'],
        'title'             : 'История реомнтов по VIN',
        'objects'           : list(objects),
        'objects_count'     : len(objects)
    }

    return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)


# Начало оценки
@api_view(['GET'])
def start_estimation(request, slug_rlk):
    user_info = get_user_info(request=request)
    
    if user_info['user'] == None:
        
        answer = {
            'type'      : 'start_estimation',
            'user'      : user_info['answer'],
            'objects'   : list()
        }

        return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)
    
    try:
        object              = DocRLK.objects.get(id=slug_rlk)
        if rlk_blocks_portal_estimation(object):
            answer = {
                'type': 'start_estimation',
                'user': user_info['answer'],
                'error': 'Подразделение переведено на Альфа-Авто. Оценку на портале начинать нельзя.',
                'objects': list(),
            }
            return JsonResponse(answer, safe=False, status=status.HTTP_400_BAD_REQUEST)
        type_estimation     = int(request.GET.get('type', '0'))
        if type_estimation == 1:
            vin                 = request.GET.get('vin', '')
            reg_interactiv_ocenka, created = RegInteractivOcenka.objects.get_or_create(rlk = object)
            reg_interactiv_ocenka.vin               = vin
            reg_interactiv_ocenka.type_estimation   = type_estimation
            reg_interactiv_ocenka.start_estimation  = datetime.now()            
            count = RefStaff.objects.filter(domain_login = user_info["user"].username).count()
            if count > 0:
                staff = RefStaff.objects.filter(domain_login = user_info["user"].username)[0]
                reg_interactiv_ocenka.staff = staff

            reg_interactiv_ocenka.save()
            
            list_organizations = RefOrganization.objects.filter(active_eco = True).values(
                slug            = F('id')           
                ).values('slug', 'name')
            list_filials = RefFilial.objects.filter(active_eco = True).values(
                slug            = F('id')           
                ).values('slug', 'name')
            list_stores = RefStore.objects.filter(active_eco = True).values(
                slug            = F('id')           
                ).values('slug', 'name')
            list_units = filter_units_available_for_portal_estimation(
                RefUnit.objects.filter(active_eco=True)
            ).values(
                slug            = F('id')           
                ).values('slug', 'name')
            
        
    except DocRLK.DoesNotExist:
        object = None
        return JsonResponse('', safe=False, status=status.HTTP_400_BAD_REQUEST)
    
    

    answer = {
        'type'                  : 'start_estimation',
        'user'                  : user_info['answer'],
        'title'                 : 'Начало оценки',
        'list_organizations'    : list(list_organizations),
        'list_filials'          : list(list_filials),
        'list_stores'           : list(list_stores),
        'list_units'            : list(list_units)
    }
    return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)

    # Начало оценки


@api_view(['GET'])
def start_estimation_modification(request, slug_rlk):
    user_info = get_user_info(request=request)
    
    if user_info['user'] == None:
        
        answer = {
            'type'      : 'start_estimation_modification',
            'user'      : user_info['answer'],
            'objects'   : list()
        }

        return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)
    
    try:
        object              = DocRLK.objects.get(id=slug_rlk)
        if rlk_blocks_portal_estimation(object):
            answer = {
                'type': 'start_estimation_modification',
                'user': user_info['answer'],
                'error': 'Подразделение переведено на Альфа-Авто. Оценку на портале начинать нельзя.',
                'objects': list(),
            }
            return JsonResponse(answer, safe=False, status=status.HTTP_400_BAD_REQUEST)
        modification        = request.GET.get('modification_id', '0')
        year                = int(request.GET.get('year', '0'))
        drive               = request.GET.get('drive', '0')

        modification_object = AutoruModification.objects.get(idSite = modification)

        reg_interactiv_ocenka, created = RegInteractivOcenka.objects.get_or_create(rlk = object)
        reg_interactiv_ocenka.year              = year
        reg_interactiv_ocenka.type_drive        = drive
        reg_interactiv_ocenka.modification      = modification_object
        reg_interactiv_ocenka.save()
            
        list_organizations = RefOrganization.objects.filter(active_eco = True).values(
            slug            = F('id')           
            ).values('slug', 'name')
        list_filials = RefFilial.objects.filter(active_eco = True).values(
            slug            = F('id')           
            ).values('slug', 'name')
        list_stores = RefStore.objects.filter(active_eco = True).values(
            slug            = F('id')           
            ).values('slug', 'name')
        list_units = filter_units_available_for_portal_estimation(
            RefUnit.objects.filter(active_eco=True)
        ).values(
            slug            = F('id')           
            ).values('slug', 'name')
            
        
    except DocRLK.DoesNotExist:
        object = None
        return JsonResponse('', safe=False, status=status.HTTP_400_BAD_REQUEST)
    
    

    answer = {
        'type'                  : 'start_estimation_modification',
        'user'                  : user_info['answer'],
        'title'                 : 'Начало оценки',
        'list_organizations'    : list(list_organizations),
        'list_filials'          : list(list_filials),
        'list_stores'           : list(list_stores),
        'list_units'            : list(list_units)
    }
    return JsonResponse(answer, safe=False, status=status.HTTP_200_OK)


def get_organization(name):
    objects = RefOrganization.objects.filter(active_eco = True).filter(name = name)
    if len(objects) > 0:
        return objects[0]
    return None

def get_filial(name):
    objects = RefFilial.objects.filter(active_eco = True).filter(name = name)
    if len(objects) > 0:
        return objects[0]
    return None

def get_store(name):
    objects = RefStore.objects.filter(active_eco = True).filter(name = name)
    if len(objects) > 0:
        return objects[0]
    return None

def get_type_reception(name):
    objects = RefTypeReceptionCarsOrganization.objects.filter(name = name)
    if len(objects) > 0:
        return objects[0]
    return None

def get_ref_object(model, name):
    
    if len(name) == 0 or name == None:
        return None
    
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