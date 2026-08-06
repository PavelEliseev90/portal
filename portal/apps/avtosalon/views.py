from django.contrib import messages
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.conf import settings
from django.contrib.auth import login as dj_login
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from refs.models import AutoruComplectation, RefCarsOrganization, RefStore, RefTypeEvaluationCarsOrganization, RefStagePrice, RefGroupPrice, RefRatingCarsOrganization, RefTypeDrive
from refs.models import RefCarsOrganizationAction, RefStagePrice, RefTypeSaleCarsOrganization, RefStatusCarsOrganization, RefTypeDrive, RefTypeBody, RefTypeKpp, RefUnit, RefCity, RefSpecificationData, RefEventCarsOrganization, RefAvito, RefCarsOrganizationFiles, RefCarsOrganization, AutoruModification, AutoruComplectation, AutoruModel, AutoruMark, AutoruModificationSpecifications
from api.views_avtosalon import add_statistic_cars_organization
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import json
from api.views import get_unit, get_organization, get_store, get_stage_price, get_group_price, get_model_object
from avtosalon.models import RefreshCarsLog
from datetime import datetime
import base64
from email import header
from itertools import product
import requests
import tempfile
import random
from django.db.models import Count, Sum, Max, Min, Avg, F, OuterRef, Subquery, Sum, Q, Func, Value, CharField, IntegerField, Case, When, FloatField, ExpressionWrapper, Exists, Prefetch
from django.db.models.functions import Coalesce, Concat
from django.utils import timezone
from datetime import timedelta
import os
from django.http import Http404, HttpResponseRedirect, HttpResponseNotFound, HttpResponse
from register.models import RegRefCarsOrganizationsCalculationPrice, RegInteractivOcenka, RegRefCarsOrganizationsPrice, RegEstimationRefCarsOrganizations
from avtosalon.models import Avtohub, AvtohubSiteInfo, AvtohubSite, RegCarsOrganizationTask, RegCarsOrganizationTaskComment, RegCarsOrganizationTaskFile, CarsWarehouseShowcase, CarsOrganizationEquipment
from avtosalon.car_options import build_car_options_context, save_car_equipment
from documents.models import DocCarAgreement, DocCarShipment, DocZNKA, DocZNWorkKA, DocZNProductKA, DocZNServicesKA, DocZNPerformersKA, DocRLK, DocLO, RefService, DocServiceItem
from django.http import JsonResponse
from rest_framework import status
import qrcode
import io
import base64
from chats.models import Chat, ChatMessage
from chats.rlk_chat_utils import (
    build_rlk_chat_page_url,
    build_rlk_chat_params,
    build_rlk_chat_poll_url,
    build_rlk_chat_send_url,
    broadcast_rlk_chat_ws_message,
    extract_rlk_chat_request,
    fetch_new_rlk_chat_messages,
    resolve_rlk_chat_access,
    resolve_rlk_chat_poll,
    serialize_rlk_chat_messages,
    user_can_access_rlk_op_chat,
)
from profiles.models import Profiles
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.crypto import get_random_string
from prices_car.models import EmailPushCar, CarCalculations
from avtosalon.deal_calc_approval import (
    build_deal_calc_approval_context,
    handle_deal_calc_approval_post,
    recalculate_deal_calculation_km,
    try_approve_by_prior_uk_threshold,
    try_auto_approve_calculation,
    user_can_access_deal_calculation_doc,
    user_has_deal_calc_uk_access,
)
from prices_car.km_raschet import apply_km_raschet_to_calculation
from prices_car.brand_resolve import resolve_price_car_brand_for_car


url_hs_kors_auto    = 'http://a01srv1cka/zbusiness/hs/mb'


def get_cars_organization(user, filter):
    cars = RefCarsOrganization.objects.exclude(quantity = 0).exclude(modification_autoru = None)

    return cars


def get_catalog():
    # ОПТИМИЗАЦИЯ: Используем Count напрямую вместо Func для более эффективного подсчета
    autoru = AutoruMark.objects.all().order_by('name')

    # ОПТИМИЗАЦИЯ: Используем Count напрямую в аннотации через связанные модели
    # Путь: AutoruMark -> AutoruModel -> AutoruModification -> RefCarsOrganization
    autoru = autoru.annotate(
        cars_count=Count('autorumodel__autorumodification__refcarsorganization', 
                        filter=Q(autorumodel__autorumodification__refcarsorganization__quantity__gt=0) &
                               Q(autorumodel__autorumodification__refcarsorganization__modification_autoru__isnull=False),
                        distinct=True)
    )
    autoru = autoru.exclude(cars_count = 0)

    return autoru


def get_catalog_mark(mark):
    # ОПТИМИЗАЦИЯ: Используем Count напрямую вместо Func и Subquery
    autoru = AutoruModel.objects.filter(mark__nameEn = mark).select_related('mark').order_by('name').distinct()

    # ОПТИМИЗАЦИЯ: Используем Count напрямую в аннотации
    autoru = autoru.annotate(
        cars_count=Count('autorumodification__refcarsorganization',
                        filter=Q(autorumodification__refcarsorganization__quantity__gt=0) &
                               Q(autorumodification__refcarsorganization__modification_autoru__isnull=False),
                        distinct=True)
    )
    autoru = autoru.exclude(cars_count = 0).distinct()
    
    # Группируем по nameEn и суммируем cars_count
    seen_names = {}
    for model in autoru:
        name_en = model.nameEn
        name_human = model.nameHuman
        if name_en not in seen_names:
            seen_names[name_en] = {
                'nameEn': name_en,
                'nameHuman': name_human,
                'cars_count': 0
            }
        # Count возвращает значение напрямую
        seen_names[name_en]['cars_count'] += model.cars_count or 0
    
    return list(seen_names.values())


def catalog_mark(request, mark_name_en):
    
    select_count    = request.GET.get('select_count', 12)
    catalog         = get_catalog_mark(mark_name_en) 
    
    # ОПТИМИЗАЦИЯ: Добавляем select_related для связанных объектов
    cars = get_cars_organization(request.user, filter = '')
    cars = cars.filter(modification_autoru__model__mark__nameEn = mark_name_en).select_related(
        'modification_autoru',
        'modification_autoru__model',
        'modification_autoru__model__mark',
        'store'
    )

    page_number = request.GET.get('page', 1)
        
    paginator   = Paginator(cars, select_count)
    page_obj    = paginator.get_page(page_number)
    
    filter_count = 0
    
    store_id = request.GET.get('store', '')
    if store_id != "":
        filter_count = filter_count + 1 
        cars = cars.filter(store__id = store_id)

    filtr = {
        'store_id'          : store_id,
        'select_count'      : select_count,
        'filtr_count'       : filter_count
    }

    # ОПТИМИЗАЦИЯ: Используем only() для загрузки только необходимых полей
    selected = {
        'stores'        : RefStore.objects.only('id', 'name').order_by('name'),
        'evaluations'   : RefTypeEvaluationCarsOrganization.objects.only('id', 'name').order_by('name'),
    }
    
    # ОПТИМИЗАЦИЯ: Подсчет общего количества автомобилей в каталоге
    total_count = RefCarsOrganization.objects.exclude(quantity=0).exclude(modification_autoru=None).count()
    
    # ОПТИМИЗАЦИЯ: Подсчет количества автомобилей для данной марки
    mark_count = RefCarsOrganization.objects.exclude(quantity=0).exclude(modification_autoru=None).filter(
        modification_autoru__model__mark__nameEn=mark_name_en
    ).count()
    
    params = {
        'type'          : 'cars',
        'mark_name_en'  : mark_name_en,
        'page_number'   : page_number,
        'paginator'     : page_obj,
        'selected'      : selected,
        'filtr'         : filtr,
        'catalog'       : catalog,
        'total_count'   : total_count,
        'mark_count'    : mark_count
    }
    
    return render(request, "avtosalon/cars_catalog_new.html", {'params': params})  


def catalog_model(request, mark_name_en, model_name):
    
    select_count    = request.GET.get('select_count', 12)
    catalog         = get_catalog_mark(mark_name_en) 
    
    # ОПТИМИЗАЦИЯ: Добавляем select_related для связанных объектов
    cars = get_cars_organization(request.user, filter = '')
    cars = cars.filter(modification_autoru__model__mark__nameEn = mark_name_en).filter(
        modification_autoru__model__nameEn__icontains = model_name
    ).select_related(
        'modification_autoru',
        'modification_autoru__model',
        'modification_autoru__model__mark',
        'store'
    )

    page_number = request.GET.get('page', 1)
        
    paginator   = Paginator(cars, select_count)
    page_obj    = paginator.get_page(page_number)
    
    filter_count = 0
    
    store_id = request.GET.get('store', '')
    if store_id != "":
        filter_count = filter_count + 1 
        cars = cars.filter(store__id = store_id)

    filtr = {
        'store_id'          : store_id,
        'select_count'      : select_count,
        'filtr_count'       : filter_count
    }

    # ОПТИМИЗАЦИЯ: Используем only() для загрузки только необходимых полей
    selected = {
        'stores'        : RefStore.objects.only('id', 'name').order_by('name'),
        'evaluations'   : RefTypeEvaluationCarsOrganization.objects.only('id', 'name').order_by('name'),
    }
    
    # ОПТИМИЗАЦИЯ: Подсчет общего количества автомобилей в каталоге
    total_count = RefCarsOrganization.objects.exclude(quantity=0).exclude(modification_autoru=None).count()
    
    # ОПТИМИЗАЦИЯ: Подсчет количества автомобилей для данной марки
    mark_count = RefCarsOrganization.objects.exclude(quantity=0).exclude(modification_autoru=None).filter(
        modification_autoru__model__mark__nameEn=mark_name_en
    ).count()
    
    params = {
        'type'          : 'cars',
        'mark_name_en'  : mark_name_en,
        'page_number'   : page_number,
        'paginator'     : page_obj,
        'selected'      : selected,
        'filtr'         : filtr,
        'catalog'       : catalog,
        'total_count'   : total_count,
        'mark_count'    : mark_count
    }
    
    return render(request, "avtosalon/cars_catalog_new.html", {'params': params})  


def cars_catalog(request):
    # ОПТИМИЗАЦИЯ: Используем кэширование и оптимизированные запросы
    catalog = get_catalog() 
    
    # ОПТИМИЗАЦИЯ: Подсчет общего количества через аннотацию в get_catalog или отдельным оптимизированным запросом
    # Используем только() для загрузки минимальных данных
    total_count = RefCarsOrganization.objects.exclude(quantity=0).exclude(modification_autoru=None).count()

    params = {
        'type'          : 'cars',
        'catalog'       : catalog,
        'glav'          : True,
        'total_count'   : total_count
    }
    
    return render(request, "avtosalon/cars_catalog_new.html", {'params': params})


def cars(request):

    select_count    = request.GET.get('select_count', 12)
    catalog         = get_catalog() 

    # ОПТИМИЗАЦИЯ: Добавляем select_related и prefetch_related для связанных объектов
    cars = RefCarsOrganization.objects.exclude(quantity = 0).exclude(modification_autoru = None).select_related(        
        'modification_autoru',
        'modification_autoru__model',
        'modification_autoru__model__mark',
        'modification_autoru__typeBody',
        'modification_autoru__typeGear',
        'status',
        'store',
        'store__city',
        'unit',
        'type_sale',
        'stage_price',
        'evaluation',
        'type_drive'
    ).prefetch_related(
        'refcarsorganizationfiles_set'
    )
    
    # ОПТИМИЗАЦИЯ: Используем Count напрямую вместо Subquery для подсчета фото
    cars = cars.annotate(photos=Count('refcarsorganizationfiles', distinct=True))
    cars = cars.order_by('-photos', '-date_create')
    
    filter_count    = 0
    
    price_start = request.GET.get('price_start', '')
    if price_start != '':
        filter_count = filter_count + 1
        cars = cars.filter(price__gte = int(price_start))

    price_end = request.GET.get('price_end', '')
    if price_end != '':
        filter_count = filter_count + 1
        cars = cars.filter(price__lte = int(price_end))

    run_start = request.GET.get('run_start', '')
    if run_start != '':
        filter_count = filter_count + 1
        cars = cars.filter(run__gte = int(run_start))

    run_end = request.GET.get('run_end', '')
    if run_end != '':
        filter_count = filter_count + 1
        cars = cars.filter(run__lte = int(run_end))

    year_start = request.GET.get('year_start', '')
    if year_start != '':
        filter_count = filter_count + 1
        cars = cars.filter(year__gte = int(year_start))

    year_end = request.GET.get('year_end', '')
    if year_end != '':
        filter_count = filter_count + 1
        cars = cars.filter(year__lte = int(year_end))  

    vin         = request.GET.get('vin', '')
    if vin != '':
        cars = cars.filter(vin__icontains = vin)

    filter_mark     = list()
    list_mark = request.GET.getlist('mark[]')
    if len(list_mark) > 0:
        filter_count = filter_count + 1
        cars = cars.filter(modification_autoru__model__mark__id__in = list_mark)
        for mark in list_mark:
            filter_mark.append(int(mark))

    filter_city     = list()
    list_city = request.GET.getlist('city[]')
    if len(list_city) > 0:
        filter_count = filter_count + 1
        cars = cars.filter(store__city__id__in = list_city)
        for city in list_city:
            filter_city.append(int(city))  

    filter_gear     = list()
    list_gear = request.GET.getlist('gear[]')
    if len(list_gear) > 0:
        filter_count = filter_count + 1
        cars = cars.filter(modification_autoru__typeGear__id__in = list_gear)
        for gear in list_gear:
            filter_gear.append(int(gear))
    
    filter_drive     = list()
    list_drive = request.GET.getlist('drive[]')
    if len(list_drive) > 0:
        filter_count = filter_count + 1
        cars = cars.filter(type_drive__id__in = list_drive)
        for drive in list_drive:
            filter_drive.append(int(drive))

    filter_body     = list()
    list_body = request.GET.getlist('body[]')
    if len(list_body) > 0:
        filter_count = filter_count + 1
        cars = cars.filter(modification_autoru__typeBody__id__in = list_body)
        for body in list_body:
            filter_body.append(int(body))

    filter_type_sale     = list()
    list_type_sale = request.GET.getlist('type_sale[]')
    if len(list_type_sale) > 0:
        filter_count = filter_count + 1
        cars = cars.filter(type_sale__id__in = list_type_sale)
        for type_sale in list_type_sale:
            filter_type_sale.append(int(type_sale))  

    filter_stage_price     = list()
    list_stage_price = request.GET.getlist('stage_price[]')
    if len(list_stage_price) > 0:
        filter_count = filter_count + 1
        cars = cars.filter(stage_price__id__in = list_stage_price)
        for stage_price in list_stage_price:
            filter_stage_price.append(int(stage_price))  

    filter_status     = list()
    list_status = request.GET.getlist('status[]')
    if len(list_status) > 0:
        filter_count = filter_count + 1
        cars = cars.filter(status__id__in = list_status)
        for status in list_status:
            filter_status.append(int(status))  

    store_id = request.GET.get('store', '')
    if store_id != "":
        filter_count = filter_count + 1 
        cars = cars.filter(store__id = store_id)
    
    page_number = request.GET.get('page', 1)
        
    paginator   = Paginator(cars, select_count)
    page_obj    = paginator.get_page(page_number)

    filtr = {
        'year_start'        : year_start,
        'year_end'          : year_end,
        'price_start'       : price_start,
        'price_end'         : price_end,
        'run_start'         : run_start,
        'run_end'           : run_end,
        'vin'               : vin,
        'store_id'          : store_id,
        'select_count'      : select_count,
        'filter_city'       : filter_city,
        'filter_gear'       : filter_gear,
        'filter_body'       : filter_body,
        'filter_mark'       : filter_mark,
        'filter_drive'      : filter_drive,
        'filter_status'     : filter_status,
        'filter_type_sale'  : filter_type_sale,
        'filter_stage_price': filter_stage_price,
        'filtr_count'       : filter_count
    }

    # ОПТИМИЗАЦИЯ: Используем only() для загрузки только необходимых полей
    selected = {
        'stage_prices'  : RefStagePrice.objects.only('id', 'name').order_by('name'),
        'type_sales'    : RefTypeSaleCarsOrganization.objects.only('id', 'name').order_by('name'),
        'statuses'      : RefStatusCarsOrganization.objects.only('id', 'name').order_by('name'),
        'marks'         : AutoruMark.objects.only('id', 'name').order_by('name'),
        'bodys'         : RefTypeBody.objects.only('id', 'name').order_by('name'),
        'drives'        : RefTypeDrive.objects.only('id', 'name').order_by('name'),
        'gears'         : RefTypeKpp.objects.only('id', 'name').order_by('name'),
        'stores'        : RefStore.objects.only('id', 'name').order_by('name'),
        'evaluations'   : RefTypeEvaluationCarsOrganization.objects.only('id', 'name').order_by('name'),
        'citys'         : RefUnit.objects.filter(buauto = True).exclude(city = None).select_related('city').only('city', 'city__name').order_by('city__name').values('city', 'city__name').distinct()
    }
    
    params = {
        'type'          : 'cars',
        'page_number'   : page_number,
        'paginator'     : page_obj,
        'selected'      : selected,
        'filtr'         : filtr,
        'catalog'       : catalog
    }
    
    return render(request, "avtosalon/cars_new.html", {'params': params})  


def disposition(request):
    """
    Страница диспозиции - отображение автомобилей с фильтрацией
    """
    from datetime import datetime, timedelta
    from django.db.models import Q
    
    # Параметры фильтрации
    status_type = request.GET.get('status', 'all')  # По умолчанию "Все"
    select_count = int(request.GET.get('select_count', 50))
    
    # ОПТИМИЗАЦИЯ: Добавляем select_related и prefetch_related для связанных объектов
    # Базовый запрос
    cars = RefCarsOrganization.objects.exclude(quantity=0).select_related(
        'modification_autoru',
        'modification_autoru__model',
        'modification_autoru__model__mark',
        'modification_autoru__typeBody',
        'modification_autoru__typeGear',
        'status',
        'store',
        'store__city',
        'unit',
        'evaluation',
        'type_drive',
        'stage_price'
    ).prefetch_related(
        'refcarsorganizationfiles_set'
    ).annotate(
        # Подсчет активных задач (новые + в работе)
        active_tasks_count=Count('tasks', filter=Q(tasks__status__in=['new', 'in_progress']))
    )
    
    # Фильтр по статусу (тип диспозиции)
    # Если status_type == 'all' или пустой, показываем все автомобили в наличии (без фильтра по статусу)
    if status_type == 'all' or status_type == '':
        # Не применяем фильтр по статусу - показываем все автомобили в наличии
        pass
    elif status_type == 'warehouse':
        cars = cars.filter(status__name__icontains='Склад')
    elif status_type == 'ready':
        cars = cars.filter(status__name__icontains='Готов')
    elif status_type == 'sale':
        cars = cars.filter(status__name__icontains='В продаже')
    elif status_type == 'auction':
        cars = cars.filter(status__name__icontains='Аукцион')
    elif status_type == 'reserve':
        cars = cars.filter(reserve__gt=0)
    elif status_type == 'transit':
        cars = cars.filter(status__name__icontains='Транзит')
    elif status_type == 'preparation':
        cars = cars.filter(status__name__icontains='Подготовка')
    elif status_type == 'repair':
        cars = cars.filter(status__name__icontains='Ремонт')
    elif status_type == 'sold':
        cars = cars.filter(status__name__icontains='Продан')
    elif status_type == 'no_sale':
        cars = cars.filter(status__name__icontains='Не продавать')
    elif status_type == 'returned':
        cars = cars.filter(status__name__icontains='Возвращен')
    
    # Фильтры
    vin = request.GET.get('vin', '').strip()
    if vin:
        cars = cars.filter(Q(vin__icontains=vin) | Q(vin2__icontains=vin))
    
    # Фильтр по search_fields (поиск по всем полям)
    search_fields = request.GET.get('search_fields', '').strip()
    if search_fields:
        cars = cars.filter(search_fields__icontains=search_fields)
    
    # Фильтр по маркам (множественный выбор)
    mark_ids = request.GET.getlist('mark[]')
    if mark_ids:
        try:
            mark_ids_int = [int(mid) for mid in mark_ids if mid]
            if mark_ids_int:
                cars = cars.filter(modification_autoru__model__mark__id__in=mark_ids_int)
        except ValueError:
            pass
    
    # Фильтр по моделям (множественный выбор)
    model_ids = request.GET.getlist('model[]')
    if model_ids:
        try:
            model_ids_int = [int(mid) for mid in model_ids if mid]
            if model_ids_int:
                cars = cars.filter(modification_autoru__model__id__in=model_ids_int)
        except ValueError:
            pass
    
    year_start = request.GET.get('year_start', '')
    if year_start:
        try:
            cars = cars.filter(year__gte=int(year_start))
        except ValueError:
            pass
    
    year_end = request.GET.get('year_end', '')
    if year_end:
        try:
            cars = cars.filter(year__lte=int(year_end))
        except ValueError:
            pass
    
    price_start = request.GET.get('price_start', '')
    if price_start:
        try:
            cars = cars.filter(price__gte=int(float(price_start)))
        except ValueError:
            pass
    
    price_end = request.GET.get('price_end', '')
    if price_end:
        try:
            cars = cars.filter(price__lte=int(float(price_end)))
        except ValueError:
            pass
    
    stock_number = request.GET.get('stock_number', '').strip()
    if stock_number:
        cars = cars.filter(lo_link_number__icontains=stock_number)
    
    no_photo = request.GET.get('no_photo', '')
    if no_photo == 'on':
        cars = cars.annotate(photos_count=Count('refcarsorganizationfiles__id')).filter(photos_count=0)
    
    promotion = request.GET.get('promotion', '')
    if promotion == 'on':
        # Фильтр по акции (можно настроить по полю stage_price или другому)
        cars = cars.filter(stage_price__name__icontains='акция')
    
    # Дополнительные фильтры - множественный выбор
    body_type_ids = request.GET.getlist('body_type[]')
    if body_type_ids:
        try:
            cars = cars.filter(modification_autoru__typeBody__id__in=[int(btid) for btid in body_type_ids])
        except ValueError:
            pass
    
    gear_type_ids = request.GET.getlist('gear_type[]')
    if gear_type_ids:
        try:
            cars = cars.filter(modification_autoru__typeGear__id__in=[int(gtid) for gtid in gear_type_ids])
        except ValueError:
            pass
    
    drive_type_ids = request.GET.getlist('drive_type[]')
    if drive_type_ids:
        try:
            cars = cars.filter(type_drive__id__in=[int(dtid) for dtid in drive_type_ids])
        except ValueError:
            pass
    
    evaluation_type_ids = request.GET.getlist('evaluation_type[]')
    if evaluation_type_ids:
        try:
            cars = cars.filter(evaluation__id__in=[int(etid) for etid in evaluation_type_ids])
        except ValueError:
            pass
    
    unit_ids = request.GET.getlist('unit[]')
    if unit_ids:
        try:
            cars = cars.filter(unit__id__in=[int(uid) for uid in unit_ids])
        except ValueError:
            pass
    
    store_ids = request.GET.getlist('store[]')
    if store_ids:
        try:
            cars = cars.filter(store__id__in=[int(sid) for sid in store_ids])
        except ValueError:
            pass
    
    color = request.GET.get('color', '').strip()
    if color:
        cars = cars.filter(color__icontains=color)
    
    run_start = request.GET.get('run_start', '')
    if run_start:
        try:
            cars = cars.filter(run__gte=int(run_start))
        except ValueError:
            pass
    
    run_end = request.GET.get('run_end', '')
    if run_end:
        try:
            cars = cars.filter(run__lte=int(run_end))
        except ValueError:
            pass
    
    engine_volume_start = request.GET.get('engine_volume_start', '')
    if engine_volume_start:
        try:
            cars = cars.filter(modification_autoru__engineVolume__gte=float(engine_volume_start))
        except (ValueError, AttributeError):
            pass
    
    engine_volume_end = request.GET.get('engine_volume_end', '')
    if engine_volume_end:
        try:
            cars = cars.filter(modification_autoru__engineVolume__lte=float(engine_volume_end))
        except (ValueError, AttributeError):
            pass
    
    days_in_stock_start = request.GET.get('days_in_stock_start', '')
    if days_in_stock_start:
        try:
            days = int(days_in_stock_start)
            target_date = datetime.now().date() - timedelta(days=days)
            cars = cars.filter(date_create__lte=target_date)
        except ValueError:
            pass
    
    days_in_stock_end = request.GET.get('days_in_stock_end', '')
    if days_in_stock_end:
        try:
            days = int(days_in_stock_end)
            target_date = datetime.now().date() - timedelta(days=days)
            cars = cars.filter(date_create__gte=target_date)
        except ValueError:
            pass
    
    # Сортировка
    order_by = request.GET.get('order_by', '-date_create')
    if order_by:
        cars = cars.order_by(order_by)
    else:
        cars = cars.order_by('-date_create')
    
    # Подсчет общего количества отфильтрованных автомобилей
    total_cars_count = cars.count()
    
    # Пагинация
    page_number = request.GET.get('page', 1)
    paginator = Paginator(cars, select_count)
    page_obj = paginator.get_page(page_number)
    
    # Проверка, есть ли активные фильтры (исключая статус, так как он всегда есть)
    has_filters = bool(
        vin or mark_ids or model_ids or year_start or year_end or 
        price_start or price_end or stock_number or (no_photo == 'on') or 
        (promotion == 'on') or body_type_ids or gear_type_ids or 
        drive_type_ids or evaluation_type_ids or unit_ids or 
        store_ids or color or run_start or run_end or 
        engine_volume_start or engine_volume_end or 
        days_in_stock_start or days_in_stock_end
    )
    
    # ОПТИМИЗАЦИЯ: Используем only() для загрузки только необходимых полей
    # Данные для фильтров
    selected = {
        'marks': AutoruMark.objects.only('id', 'name').order_by('name'),
        'statuses': RefStatusCarsOrganization.objects.only('id', 'name').order_by('name'),
        'stores': RefStore.objects.only('id', 'name').order_by('name'),
        'units': RefUnit.objects.filter(buauto=True).only('id', 'name').order_by('name'),
        'body_types': RefTypeBody.objects.only('id', 'name').order_by('name'),
        'gear_types': RefTypeKpp.objects.only('id', 'name').order_by('name'),
        'drive_types': RefTypeDrive.objects.only('id', 'name').order_by('name'),
        'evaluation_types': RefTypeEvaluationCarsOrganization.objects.only('id', 'name').order_by('name'),
    }
    
    # ОПТИМИЗАЦИЯ: Загружаем модели с select_related для марки
    # Загружаем модели (все для множественного выбора, или отфильтрованные по выбранным маркам)
    models_list = AutoruModel.objects.select_related('mark').only('id', 'name', 'mark').order_by('name')
    if mark_ids:
        try:
            mark_ids_int = [int(mid) for mid in mark_ids if mid]
            if mark_ids_int:
                models_list = models_list.filter(mark__id__in=mark_ids_int)
        except ValueError:
            pass
    
    # Преобразуем списки в строки для шаблона (для удобства проверки selected)
    mark_ids_str = [str(mid) for mid in mark_ids] if mark_ids else []
    model_ids_str = [str(mid) for mid in model_ids] if model_ids else []
    body_type_ids_str = [str(btid) for btid in body_type_ids] if body_type_ids else []
    gear_type_ids_str = [str(gtid) for gtid in gear_type_ids] if gear_type_ids else []
    drive_type_ids_str = [str(dtid) for dtid in drive_type_ids] if drive_type_ids else []
    evaluation_type_ids_str = [str(etid) for etid in evaluation_type_ids] if evaluation_type_ids else []
    unit_ids_str = [str(uid) for uid in unit_ids] if unit_ids else []
    store_ids_str = [str(sid) for sid in store_ids] if store_ids else []
    
    # Для фильтров с чекбоксами - списки ID для проверки в шаблоне (всегда списки, даже пустые)
    mark_ids_list = [int(mid) for mid in mark_ids if mid] if mark_ids else []
    model_ids_list = [int(mid) for mid in model_ids if mid] if model_ids else []
    body_type_ids_list = [int(btid) for btid in body_type_ids if btid] if body_type_ids else []
    gear_type_ids_list = [int(gtid) for gtid in gear_type_ids if gtid] if gear_type_ids else []
    drive_type_ids_list = [int(dtid) for dtid in drive_type_ids if dtid] if drive_type_ids else []
    evaluation_type_ids_list = [int(etid) for etid in evaluation_type_ids if etid] if evaluation_type_ids else []
    unit_ids_list = [int(uid) for uid in unit_ids if uid] if unit_ids else []
    store_ids_list = [int(sid) for sid in store_ids if sid] if store_ids else []
    
    filtr = {
        'status': status_type,
        'vin': vin,
        'search_fields': search_fields,
        'mark': mark_ids_str,
        'model': model_ids_str,
        'year_start': year_start,
        'year_end': year_end,
        'price_start': price_start,
        'price_end': price_end,
        'stock_number': stock_number,
        'no_photo': no_photo,
        'promotion': promotion,
        'select_count': select_count,
        'order_by': order_by,
        'body_type': body_type_ids_str,
        'gear_type': gear_type_ids_str,
        'drive_type': drive_type_ids_str,
        'evaluation_type': evaluation_type_ids_str,
        'unit': unit_ids_str,
        'store': store_ids_str,
        'color': color,
        'run_start': run_start,
        'run_end': run_end,
        'engine_volume_start': engine_volume_start,
        'engine_volume_end': engine_volume_end,
        'days_in_stock_start': days_in_stock_start,
        'days_in_stock_end': days_in_stock_end,
    }
    
    params = {
        'type': 'disposition',
        'page_obj': page_obj,
        'paginator': paginator,
        'selected': selected,
        'filtr': filtr,
        'models_list': models_list,
        'all_models': AutoruModel.objects.select_related('mark').only('id', 'name', 'mark').order_by('name'),  # ОПТИМИЗАЦИЯ: Все модели для множественного выбора
        'total_cars_count': total_cars_count,
        'has_filters': has_filters,
        # Для фильтров с чекбоксами
        'mark_ids_list': mark_ids_list,
        'model_ids_list': model_ids_list,
        'body_type_ids_list': body_type_ids_list,
        'gear_type_ids_list': gear_type_ids_list,
        'drive_type_ids_list': drive_type_ids_list,
        'evaluation_type_ids_list': evaluation_type_ids_list,
        'unit_ids_list': unit_ids_list,
        'store_ids_list': store_ids_list,
    }
    
    return render(request, "avtosalon/disposition.html", {'params': params})


def disposition_get_marks(request):
    """
    AJAX endpoint для загрузки марок (с поиском)
    """
    from django.http import JsonResponse
    
    search = request.GET.get('search', '').strip()
    
    try:
        marks = AutoruMark.objects.only('id', 'name').order_by('name')
        if search:
            marks = marks.filter(name__icontains=search)
        # Ограничиваем количество для производительности
        marks = marks[:100]
        marks_list = [{'id': mark.id, 'name': mark.name} for mark in marks]
        return JsonResponse({'marks': marks_list})
    except Exception as e:
        return JsonResponse({'marks': [], 'error': str(e)})


def disposition_get_models(request):
    """
    AJAX endpoint для загрузки моделей по маркам (поддерживает несколько марок)
    """
    from django.http import JsonResponse
    
    mark_ids = request.GET.getlist('mark_ids[]')
    search = request.GET.get('search', '').strip()
    
    if not mark_ids:
        return JsonResponse({'models': []})
    
    try:
        mark_ids_int = [int(mid) for mid in mark_ids if mid]
        if not mark_ids_int:
            return JsonResponse({'models': []})
        
        models = AutoruModel.objects.filter(mark__id__in=mark_ids_int).select_related('mark').only('id', 'name', 'mark').order_by('name')
        if search:
            models = models.filter(name__icontains=search)
        # Ограничиваем количество для производительности
        models = models[:200]
        models_list = [{'id': model.id, 'name': model.name, 'mark_id': model.mark.id, 'mark_name': model.mark.name} for model in models]
        return JsonResponse({'models': models_list})
    except Exception as e:
        return JsonResponse({'models': [], 'error': str(e)})


def _get_request_ip(request):
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
    if ',' in ip_address:
        ip_address = ip_address.split(',')[0].strip()
    return ip_address or None


def _normalize_phone(phone):
    digits = ''.join(ch for ch in str(phone or '') if ch.isdigit())
    if len(digits) == 11 and digits.startswith('8'):
        digits = '7' + digits[1:]
    elif len(digits) == 10:
        digits = '7' + digits
    return digits


def _send_sms_code(phone_normalized, code):
    """
    Реальная отправка SMS через провайдера из settings.
    Поддерживаемые значения:
    - SMS_AUTH_PROVIDER = 'smsru'
      - SMSRU_API_ID = '...'
    - SMS_AUTH_PROVIDER = 'easysms'
      - EASY_SMS_LOGIN = '...'
      - EASY_SMS_PASSWORD = '...'
      - EASY_SMS_CONNECT_ID = '...'
      - EASY_SMS_ORIGINATOR = '...'
      - EASY_SMS_BASE_URL = 'https://xml.smstec.ru' (опционально)
    """
    provider = getattr(settings, 'SMS_AUTH_PROVIDER', 'smsru')
    message = f"Код входа Kors Group: {code}. Никому не сообщайте."

    if provider == 'smsru':
        api_id = getattr(settings, 'SMSRU_API_ID', '')
        if not api_id:
            return False, "Не настроен ключ SMS-провайдера (SMSRU_API_ID)."

        try:
            response = requests.get(
                'https://sms.ru/sms/send',
                params={
                    'api_id': api_id,
                    'to': phone_normalized,
                    'msg': message,
                    'json': 1,
                },
                timeout=15,
            )
            data = response.json()
            if str(data.get('status')) == 'OK':
                return True, None
            status_text = data.get('status_text') or 'Ошибка SMS-провайдера.'
            return False, status_text
        except Exception as ex:
            return False, str(ex)

    if provider == 'easysms':
        login = getattr(settings, 'EASY_SMS_LOGIN', '')
        password = getattr(settings, 'EASY_SMS_PASSWORD', '')
        connect_id = getattr(settings, 'EASY_SMS_CONNECT_ID', '')
        originator = getattr(settings, 'EASY_SMS_ORIGINATOR', '')

        if not login or not password or not connect_id:
            return False, "Не заданы настройки EasySMS: EASY_SMS_LOGIN / EASY_SMS_PASSWORD / EASY_SMS_CONNECT_ID."
        if not originator:
            return False, "Не задано имя отправителя EasySMS (EASY_SMS_ORIGINATOR)."

        base_url = getattr(settings, 'EASY_SMS_BASE_URL', 'https://xml.smstec.ru').rstrip('/')
        url = f"{base_url}/api/v3/easysms/{connect_id}/SendMessage"

        # Формат по документации easysms/v3
        payload = {
            "Header": {
                "login": login,
                "password": password,
            },
            "Payload": {
                "message": {
                    "client_message_id": f"sms_auth_{phone_normalized}_{int(timezone.now().timestamp())}",
                    "messenger_type": "sms",
                    "originator": originator,
                    "recipient": phone_normalized,
                    "text": message,
                }
            }
        }

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=20)
            data = {}
            try:
                data = response.json()
            except Exception:
                data = {}

            # Транспортные ошибки
            if response.status_code != 200:
                transport_error = data.get('error', {})
                if isinstance(transport_error, dict):
                    msg = transport_error.get('error_message') or transport_error.get('message')
                    if msg:
                        return False, f"EasySMS: {msg}"
                return False, f"EasySMS HTTP {response.status_code}"

            # Платформенные ошибки в успешном HTTP-ответе
            msg_obj = data.get('message', {}) if isinstance(data, dict) else {}
            err_obj = msg_obj.get('error', {}) if isinstance(msg_obj, dict) else {}
            if isinstance(err_obj, dict) and err_obj:
                err_code = err_obj.get('error_code', '')
                err_message = err_obj.get('error_message') or 'Ошибка платформы easysms'
                if err_code:
                    return False, f"EasySMS [{err_code}]: {err_message}"
                return False, f"EasySMS: {err_message}"

            # Успех, если есть message_id либо часть каскадного ответа
            if isinstance(msg_obj, dict) and (msg_obj.get('message_id') or msg_obj.get('cascade_message_id')):
                return True, None
            if isinstance(data, dict) and data.get('message'):
                return True, None

            return False, "EasySMS: некорректный ответ сервера."
        except Exception as ex:
            return False, str(ex)

    return False, f"Провайдер SMS '{provider}' не поддерживается."


def _check_sms_rate_limit(phone_normalized, ip):
    """
    Ограничения отправки SMS-кодов:
    - не чаще 1 раза в 60 секунд на телефон;
    - не более 5 отправок за 10 минут на телефон;
    - не более 20 отправок за сутки на телефон;
    - не более 30 отправок за час с одного IP.
    """
    from avtosalon.models import SmsAuthSession

    now = timezone.now()
    one_min_ago = now - timedelta(minutes=1)
    ten_min_ago = now - timedelta(minutes=10)
    one_hour_ago = now - timedelta(hours=1)
    one_day_ago = now - timedelta(days=1)

    recent_phone = SmsAuthSession.objects.filter(
        phone_normalized=phone_normalized,
        code_sent_at__isnull=False,
    )

    last_by_phone = recent_phone.order_by('-code_sent_at').first()
    if last_by_phone and last_by_phone.code_sent_at and last_by_phone.code_sent_at > one_min_ago:
        retry_after = int((last_by_phone.code_sent_at + timedelta(minutes=1) - now).total_seconds())
        return False, f"Слишком частая отправка. Повторите через {max(retry_after, 1)} сек."

    phone_10m_count = recent_phone.filter(code_sent_at__gte=ten_min_ago).count()
    if phone_10m_count >= 5:
        return False, "Лимит отправок на этот номер: 5 кодов за 10 минут."

    phone_24h_count = recent_phone.filter(code_sent_at__gte=one_day_ago).count()
    if phone_24h_count >= 20:
        return False, "Лимит отправок на этот номер за сутки исчерпан."

    if ip:
        ip_1h_count = SmsAuthSession.objects.filter(
            request_ip=ip,
            code_sent_at__isnull=False,
            code_sent_at__gte=one_hour_ago,
        ).count()
        if ip_1h_count >= 30:
            return False, "Слишком много запросов с вашего IP. Попробуйте позже."

    return True, None


@csrf_exempt
@require_POST
def car_sms_send_code(request, slug):
    from avtosalon.models import SmsAuthSession

    car = get_object_or_404(RefCarsOrganization, slug=slug)
    payload = {}
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Некорректный формат запроса.'}, status=400)

    phone_raw = payload.get('phone', '')
    phone = _normalize_phone(phone_raw)
    consent_pd = bool(payload.get('consent_personal_data', False))
    consent_ads = bool(payload.get('consent_ads', False))

    if len(phone) != 11:
        return JsonResponse({'ok': False, 'error': 'Введите корректный номер телефона.'}, status=400)
    if not consent_pd:
        return JsonResponse({'ok': False, 'error': 'Необходимо согласие на обработку персональных данных.'}, status=400)

    ip = _get_request_ip(request)
    is_allowed, rate_limit_error = _check_sms_rate_limit(phone, ip)
    if not is_allowed:
        return JsonResponse({'ok': False, 'error': rate_limit_error}, status=429)

    code = ''.join(random.choices('0123456789', k=6))
    now = timezone.now()
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    session = SmsAuthSession()
    session.phone = str(phone_raw or '')
    session.phone_normalized = phone
    session.code_hash = make_password(code)
    session.car = car
    session.created_at = now
    session.code_sent_at = now
    session.code_expires_at = now + timedelta(minutes=5)
    session.request_ip = ip
    session.request_user_agent = user_agent
    session.consent_personal_data = True
    session.consent_personal_data_at = now
    session.consent_personal_data_ip = ip
    session.consent_ads = consent_ads
    if consent_ads:
        session.consent_ads_at = now
        session.consent_ads_ip = ip
    session.save()

    sent, send_error = _send_sms_code(phone, code)
    if not sent:
        session.delete()
        return JsonResponse({'ok': False, 'error': f'Не удалось отправить SMS: {send_error}'}, status=502)

    return JsonResponse({
        'ok': True,
        'session_id': session.id,
        'message': 'Код отправлен.',
        'expires_in_sec': 300,
    }, status=200)


@csrf_exempt
@require_POST
def car_sms_verify_code(request, slug):
    from avtosalon.models import SmsAuthSession

    get_object_or_404(RefCarsOrganization, slug=slug)
    payload = {}
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Некорректный формат запроса.'}, status=400)

    session_id = payload.get('session_id')
    code = ''.join(ch for ch in str(payload.get('code', '') or '') if ch.isdigit())
    if not session_id:
        return JsonResponse({'ok': False, 'error': 'Сессия подтверждения не найдена.'}, status=400)
    if len(code) < 4:
        return JsonResponse({'ok': False, 'error': 'Введите код из SMS.'}, status=400)

    try:
        session = SmsAuthSession.objects.select_related('user').get(pk=session_id)
    except SmsAuthSession.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Сессия подтверждения не найдена.'}, status=404)

    if session.is_verified:
        return JsonResponse({'ok': True, 'message': 'Код уже подтвержден.'}, status=200)
    if session.code_expires_at and timezone.now() > session.code_expires_at:
        return JsonResponse({'ok': False, 'error': 'Срок действия кода истек. Запросите новый код.'}, status=400)
    if session.attempts_count >= session.max_attempts:
        return JsonResponse({'ok': False, 'error': 'Превышено число попыток. Запросите новый код.'}, status=400)

    is_valid = check_password(code, session.code_hash)
    if not is_valid:
        session.attempts_count = session.attempts_count + 1
        session.save(update_fields=['attempts_count'])
        return JsonResponse({'ok': False, 'error': 'Неверный код.'}, status=400)

    phone = session.phone_normalized
    username = f"phone_{phone}"
    user = User.objects.filter(username=username).first()
    if not user:
        user = User.objects.create_user(
            username=username,
            password=get_random_string(24),
        )
        user.first_name = ''
        user.last_name = ''
        user.email = ''
        user.is_staff = False
        user.is_superuser = False
        user.save()

    try:
        profile = Profiles.objects.filter(user=user).first()
        if not profile:
            profile = Profiles.objects.create(user=user)
        profile.phone = f"+{phone}"
        profile.save()
    except Exception:
        pass

    session.is_verified = True
    session.verified_at = timezone.now()
    session.user = user
    session.save(update_fields=['is_verified', 'verified_at', 'user'])

    dj_login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    return JsonResponse({'ok': True, 'message': 'Авторизация успешна.'}, status=200)


def car(request, slug):
    
    # ОПТИМИЗАЦИЯ: Добавляем select_related и prefetch_related для всех связанных объектов
    car = RefCarsOrganization.objects.select_related(
        'modification_autoru',
        'modification_autoru__model',
        'modification_autoru__model__mark',
        'modification_autoru__typeBody',
        'modification_autoru__typeGear',
        'modification_autoru__typeEngine',
        'status',
        'store',
        'store__city',
        'unit',
        'evaluation',
        'type_drive',
        'type_sale',
        'stage_price',
        'group_price',
        'rating',
        'complectation_autoru'
    ).prefetch_related(
        'refcarsorganizationfiles_set'
    ).get(slug=slug)
    
    qr = request.GET.get('q', '')
    
    user = None
    if request.user.is_authenticated:
        user = request.user
    
    if qr != '':
        add_statistic_cars_organization(user, cars=car, store=car.store, type=4)
    else:
        add_statistic_cars_organization(user, cars=car, store=car.store, type=1)
    
    
    # Генерация QR-кода со ссылкой на страницу автомобиля
    car_url = request.build_absolute_uri(f'/cars/{car.slug}/?q=1')
    qr_code_image = qrcode.make(car_url)
    buffer = io.BytesIO()
    qr_code_image.save(buffer, format="PNG")
    qr_code_image_data = base64.b64encode(buffer.getvalue()).decode()
    qr_code_base64 = f'data:image/png;base64,{qr_code_image_data}'
    
    # ОПТИМИЗАЦИЯ: Используем only() для загрузки только необходимых полей
    selected = {
        'stores'        : RefStore.objects.only('id', 'name').order_by('name'),
        'evaluations'   : RefTypeEvaluationCarsOrganization.objects.only('id', 'name').order_by('name'),
        'stageprices'   : RefStagePrice.objects.only('id', 'name').order_by('name'),
        'groupprices'   : RefGroupPrice.objects.only('id', 'name').order_by('name'),
        'ratings'       : RefRatingCarsOrganization.objects.only('id', 'name').order_by('name'), 
    }
    tasks_count = 0
    tasks_new_count = 0
    tasks_in_progress_count = 0

    if request.user.is_authenticated and request.user.is_staff:
        # Подсчет задач по автомобилю для сотрудников
        tasks_count = RegCarsOrganizationTask.objects.filter(car=car).count()
        tasks_new_count = RegCarsOrganizationTask.objects.filter(car=car, status='new').count()
        tasks_in_progress_count = RegCarsOrganizationTask.objects.filter(car=car, status='in_progress').count()

    base_template = 'base_web_customer.html'
    if request.user.is_authenticated and request.user.is_staff:
        base_template = 'base_web.html'
    
    params = {
        'user'          : user,
        'object'        : car,
        'selected'      : selected,
        'qr_code'       : qr_code_base64,
        'car_url'       : car_url,
        'tasks_count'   : tasks_count,
        'tasks_new_count': tasks_new_count,
        'tasks_in_progress_count': tasks_in_progress_count,
        'base_template': base_template,
    }
    
    return render(request, "avtosalon/car_new.html", {'params': params})    


def specifications(request, slug):
    
    car = RefCarsOrganization.objects.filter(slug = slug)[0]
    
    specifications = RefSpecificationData.objects.filter(modification_specifications__modification = car.modification_autoru).filter(modification_specifications__complectation = None)
    
    complectations = AutoruComplectation.objects.filter(modification = car.modification_autoru)

    selected = {
        'stores'        : RefStore.objects.all().order_by('name'),
        'evaluations'   : RefTypeEvaluationCarsOrganization.objects.all().order_by('name'),
        'stageprices'   : RefStagePrice.objects.all().order_by('name'),
        'groupprices'   : RefGroupPrice.objects.all().order_by('name'),
        'ratings'       : RefRatingCarsOrganization.objects.all().order_by('name'),
        
    }
    base_template = 'base_web_customer.html'
    if request.user.is_authenticated and request.user.is_staff:
        base_template = 'base_web.html'

    params = {
        'object'            : car,
        'selected'          : selected,
        'specifications'    : specifications,
        'complectations'    : complectations,
        'base_template'     : base_template,
    }
    
    return render(request, "avtosalon/car_new_specifications.html", {'params': params})


def _price_edit_page(request):
    try:
        return int(request.GET.get('page', 0))
    except (TypeError, ValueError):
        return 0


def _car_photos_queryset(car):
    return RefCarsOrganizationFiles.objects.filter(сars_organization=car).order_by('-main', '-date')


def _car_avtohub_queryset(car):
    """Queryset Avtohub с тем же фильтром периода, что и в аналитике."""
    qs = Avtohub.objects.filter(vin=car.vin)
    if car.lo_link_date and car.date_refresh:
        in_range = qs.filter(date__range=[car.lo_link_date, car.date_refresh])
        if in_range.exists():
            qs = in_range
    return qs


def _price_edit_tab_counts(car):
    """Лёгкие счётчики для навигации price_edit (без тяжёлой аналитики)."""
    avtohub_n = _car_avtohub_queryset(car).count()
    estimation_n = RegEstimationRefCarsOrganizations.objects.filter(car_id=car.pk).count()
    return {
        'photos': RefCarsOrganizationFiles.objects.filter(сars_organization=car).count(),
        'price_revaluations': RegRefCarsOrganizationsPrice.objects.filter(car=car).count(),
        'options': CarsOrganizationEquipment.objects.filter(car=car).count(),
        'avtohub': avtohub_n,
        'estimation': estimation_n,
        'analytics_total': avtohub_n + estimation_n,
    }


def _cumulative_to_daily_deltas(values):
    """Прирост по дням из накопительных счётчиков Avtohub."""
    deltas = []
    prev = None
    for value in values:
        current = value or 0
        if prev is None:
            deltas.append(current)
        else:
            diff = current - prev
            deltas.append(current if diff < 0 else diff)
        prev = current
    return deltas


def _latest_avtohub_snapshot(records):
    """Последний снимок с данными (последний пустой снимок Avtohub не затирает сводку)."""
    if not records:
        return None
    for ah in reversed(records):
        if (
            (ah.avgMarketPrice or 0) > 0
            or (ah.numberOfCompetitors or 0) > 0
            or (ah.averageDaysInSale or 0) > 0
            or (ah.avitoViews or 0) + (ah.autoruViews or 0) + (ah.dromViews or 0) > 0
        ):
            return ah
    return records[-1]


def _car_avtohub_analytics(car):
    """Сводка и ряды Avtohub для вкладки «Аналитика»."""
    records = list(_car_avtohub_queryset(car).order_by('date'))

    rows = []
    labels = []
    avg_market_prices = []
    avtohub_prices = []
    attractiveness = []
    days_in_sale = []
    advertising = []
    raw_views_avito = []
    raw_views_autoru = []
    raw_views_drom = []
    competitors = []
    marketing = 0

    for ah in records:
        marketing = round(max(marketing, ah.totalAdvertisingCost or 0), 2)
        raw_views_avito.append(ah.avitoViews or 0)
        raw_views_autoru.append(ah.autoruViews or 0)
        raw_views_drom.append(ah.dromViews or 0)
        competitors.append(ah.numberOfCompetitors or 0)

    views_avito_delta = _cumulative_to_daily_deltas(raw_views_avito)
    views_autoru_delta = _cumulative_to_daily_deltas(raw_views_autoru)
    views_drom_delta = _cumulative_to_daily_deltas(raw_views_drom)

    for index, ah in enumerate(records):
        pct = 0
        if ah.numberOfCompetitors > 0:
            pct = round(100 * ah.vRatingPosition / ah.numberOfCompetitors, 1)

        rows.append({
            'date': ah.date,
            'price': ah.price,
            'avg_market_price': ah.avgMarketPrice,
            'imv': ah.imv,
            'v_rating_position': ah.vRatingPosition,
            'number_of_competitors': ah.numberOfCompetitors,
            'attractiveness_pct': pct,
            'average_days_in_sale': ah.averageDaysInSale,
            'days_in_sale': ah.daysInSale,
            'total_advertising_cost': ah.totalAdvertisingCost,
            'avito_views': ah.avitoViews,
            'autoru_views': ah.autoruViews,
            'drom_views': ah.dromViews,
            'avito_views_delta': views_avito_delta[index],
            'autoru_views_delta': views_autoru_delta[index],
            'drom_views_delta': views_drom_delta[index],
            'calls': ah.callsCounts_uniqueTotal,
            'actual_market_sales': ah.actualMarketSales,
        })
        labels.append(ah.date.strftime('%d.%m.%y') if ah.date else '—')
        avg_market_prices.append(ah.avgMarketPrice or 0)
        avtohub_prices.append(ah.price or 0)
        attractiveness.append(pct)
        days_in_sale.append(ah.averageDaysInSale or 0)
        advertising.append(round(ah.totalAdvertisingCost or 0))

    latest = _latest_avtohub_snapshot(records)
    car_price = car.price or 0
    avg_market = latest.avgMarketPrice if latest else None
    price_vs_market = None
    if latest is not None and avg_market is not None:
        price_vs_market = car_price - avg_market

    chart_data = {
        'labels': labels,
        'avg_market_price': avg_market_prices,
        'car_price': car.price or 0,
        'avtohub_price': avtohub_prices,
        'attractiveness': attractiveness,
        'days_in_sale': days_in_sale,
        'advertising': advertising,
        'views_avito_delta': views_avito_delta,
        'views_autoru_delta': views_autoru_delta,
        'views_drom_delta': views_drom_delta,
        'competitors': competitors,
    }

    return {
        'count': len(rows),
        'rows': list(reversed(rows)),
        'summary': {
            'latest_date': latest.date if latest else None,
            'avg_market_price': avg_market,
            'car_price': car_price,
            'price_vs_market': price_vs_market,
            'position': latest.vRatingPosition if latest is not None else None,
            'competitors': latest.numberOfCompetitors if latest is not None else None,
            'attractiveness_pct': (
                round(100 * latest.vRatingPosition / latest.numberOfCompetitors, 1)
                if latest and (latest.numberOfCompetitors or 0) > 0
                else None
            ),
            'average_days_in_sale': latest.averageDaysInSale if latest is not None else None,
            'marketing': marketing,
            'total_views': (
                (latest.avitoViews or 0) + (latest.autoruViews or 0) + (latest.dromViews or 0)
            ) if latest else 0,
        },
        'used_date_filter': bool(car.lo_link_date and car.date_refresh),
        'chart_json': json.dumps(chart_data, ensure_ascii=False),
        'period_from': car.lo_link_date,
        'period_to': car.date_refresh,
    }


def _car_estimation_analytics(car):
    """История оценок калькулятора RegEstimationRefCarsOrganizations."""
    records = list(
        RegEstimationRefCarsOrganizations.objects.filter(car_id=car.pk).order_by('date')
    )
    rows = []
    labels = []
    avg_prices = []
    our_prices = []
    attractiveness = []
    avg_days_list = []

    for est in records:
        pct = round(100 * est.position / est.total, 1) if (est.total or 0) > 0 else 0
        rows.append({
            'date': est.date,
            'avg_price': est.avg_price,
            'avg_days': est.avg_days,
            'position': est.position,
            'total': est.total,
            'price': est.price,
            'attractiveness_pct': pct,
            'percent': pct / 100,
            'error': est.error,
        })
        labels.append(est.date.strftime('%d.%m.%y') if est.date else '—')
        avg_prices.append(est.avg_price or 0)
        our_prices.append(est.price or 0)
        attractiveness.append(pct)
        avg_days_list.append(est.avg_days or 0)

    latest = records[-1] if records else None
    car_price = car.price or 0
    latest_avg = latest.avg_price if latest else None
    price_vs_market = None
    if latest is not None and latest_avg is not None:
        price_vs_market = (latest.price or 0) - latest_avg

    chart_data = {
        'labels': labels,
        'avg_price': avg_prices,
        'our_price': our_prices,
        'car_price': car_price,
        'attractiveness': attractiveness,
        'avg_days': avg_days_list,
    }

    return {
        'count': len(rows),
        'rows': list(reversed(rows)),
        'summary': {
            'latest_date': latest.date if latest else None,
            'avg_price': latest_avg,
            'our_price': latest.price if latest else None,
            'car_price': car_price,
            'price_vs_market': price_vs_market,
            'position': latest.position if latest is not None else None,
            'total': latest.total if latest is not None else None,
            'attractiveness_pct': rows[-1]['attractiveness_pct'] if rows else None,
            'avg_days': latest.avg_days if latest is not None else None,
        },
        'chart_json': json.dumps(chart_data, ensure_ascii=False),
    }


def _car_price_revaluations(car):
    """История цен RegRefCarsOrganizationsPrice для таблицы переоценок."""
    prices = list(RegRefCarsOrganizationsPrice.objects.filter(car=car).order_by('-date'))
    rows = []
    for index, item in enumerate(prices):
        delta = None
        if index + 1 < len(prices):
            delta = item.price - prices[index + 1].price
        rows.append({
            'date': item.date,
            'price': item.price,
            'delta': delta,
        })
    return rows


def _ensure_photo_date(photo):
    """Дата добавления фото (для загрузки через портал)."""
    if not photo.date:
        photo.date = timezone.now()


def _save_car_photo(photo, update_fields=None):
    _ensure_photo_date(photo)
    if update_fields is not None:
        photo.save(update_fields=update_fields)
    else:
        photo.save()


def handle_car_photos_post(request, car):
    """POST: upload / delete / set_main для фотографий автомобиля."""
    from django.contrib import messages

    action = request.POST.get('action', '')
    if action not in ('delete', 'set_main', 'upload'):
        return False

    if action == 'delete':
        photo_id = request.POST.get('photo_id', '')
        try:
            photo = RefCarsOrganizationFiles.objects.get(id=photo_id, сars_organization=car)
            photo.delete()
            messages.success(request, 'Фотография успешно удалена')
        except RefCarsOrganizationFiles.DoesNotExist:
            messages.error(request, 'Фотография не найдена')

    elif action == 'set_main':
        photo_id = request.POST.get('photo_id', '')
        try:
            RefCarsOrganizationFiles.objects.filter(сars_organization=car).update(main=False)
            photo = RefCarsOrganizationFiles.objects.get(id=photo_id, сars_organization=car)
            photo.main = True
            photo.save()
            messages.success(request, 'Главная фотография обновлена')
        except RefCarsOrganizationFiles.DoesNotExist:
            messages.error(request, 'Фотография не найдена')

    elif action == 'upload':
        uploaded_files = request.FILES.getlist('photos')
        if uploaded_files:
            uploaded_count = 0
            errors = []

            for uploaded_file in uploaded_files:
                if not uploaded_file.content_type.startswith('image/'):
                    continue

                try:
                    photo = RefCarsOrganizationFiles()
                    photo.сars_organization = car
                    photo.name = uploaded_file.name
                    photo.file = uploaded_file
                    photo.main = False
                    photo.car = True
                    photo.processed = False
                    photo.date = timezone.now()
                    _save_car_photo(photo)

                    try:
                        from PIL import Image
                        from django.core.files.base import ContentFile
                        import io
                        import time

                        if photo.file and photo.file.name:
                            file_path = photo.file.path
                            if not os.path.exists(file_path):
                                time.sleep(0.1)
                                if not os.path.exists(file_path):
                                    raise FileNotFoundError(f"Файл {file_path} не найден после сохранения")

                            img = Image.open(file_path)
                            if img.mode in ('RGBA', 'LA', 'P'):
                                background = Image.new('RGB', img.size, (255, 255, 255))
                                if img.mode == 'P':
                                    img = img.convert('RGBA')
                                if img.mode == 'RGBA' and len(img.split()) >= 4:
                                    background.paste(img, mask=img.split()[3])
                                else:
                                    background.paste(img)
                                img = background
                            elif img.mode not in ('RGB', 'L'):
                                img = img.convert('RGB')

                            max_size = (400, 400)
                            img.thumbnail(max_size, Image.Resampling.LANCZOS)
                            thumb_io = io.BytesIO()
                            img.save(thumb_io, format='JPEG', quality=85, optimize=True)
                            thumb_io.seek(0)
                            base_name = os.path.basename(photo.file.name)
                            name_without_ext, ext = os.path.splitext(base_name)
                            mini_name = f'{name_without_ext}_mini.jpg'
                            photo.file_mini.save(
                                mini_name,
                                ContentFile(thumb_io.read()),
                                save=False
                            )
                            _save_car_photo(photo)

                    except ImportError:
                        if photo.file:
                            photo.file_mini = photo.file
                            _save_car_photo(photo)
                        errors.append(f'Pillow не установлен, миниатюра не создана для {uploaded_file.name}')
                    except Exception as e:
                        if photo.file:
                            try:
                                photo.file_mini = photo.file
                                _save_car_photo(photo)
                            except Exception:
                                pass
                        errors.append(f'Ошибка создания миниатюры для {uploaded_file.name}: {str(e)}')

                    uploaded_count += 1

                except Exception as e:
                    errors.append(f'Ошибка загрузки {uploaded_file.name}: {str(e)}')
                    continue

            if uploaded_count > 0:
                if errors:
                    messages.warning(request, f'Загружено фотографий: {uploaded_count}. Предупреждения: {len(errors)}')
                else:
                    messages.success(request, f'Загружено фотографий: {uploaded_count}')
            else:
                if errors:
                    messages.error(request, f'Не удалось загрузить фотографии. Ошибки: {"; ".join(errors[:3])}')
                else:
                    messages.warning(request, 'Не удалось загрузить фотографии')

    return True


@login_required
def price_edit(request, slug):
    
    car     = RefCarsOrganization.objects.filter(slug = slug)[0]
    base1C  = ''
    page    = _price_edit_page(request)
    if page == 1 and not request.user.profiles.korsavto_settings:
        page = 0

    if request.method == "POST":
        options_action = request.POST.get('options_action', '')
        if options_action == 'save':
            from django.contrib import messages
            option_ids = request.POST.getlist('option_ids')
            save_car_equipment(car, option_ids, user=request.user)
            messages.success(request, f'Сохранено опций: {len(option_ids)}')
            return HttpResponseRedirect(request.path + '?page=11')

        photo_action = request.POST.get('action', '')
        if photo_action in ('delete', 'set_main', 'upload'):
            if not request.user.profiles.korsavto_settings:
                from django.contrib import messages
                messages.error(request, 'Нет прав на управление фотографиями')
                return HttpResponseRedirect(request.path + '?page=0')
            handle_car_photos_post(request, car)
            return HttpResponseRedirect(request.path + '?page=1')

        min_km      = int(request.POST.get('min_km', '0'))   
        percent_ss  = int(request.POST.get('percent_ss', '0'))
        url_post    = url_hs_kors_auto + "/car/"
        
        data = {
            'type'          : 'save_min_km',
            'uin_lo'        : car.lo_uin,
            'min_km'        : min_km,
            'percent_ss'    : percent_ss,
        }
        response = requests.post(url_post, json=data)
        if response.status_code == 200:
            if response.text != '':
                s = 1
                
        return HttpResponseRedirect(request.path + '?page=0')
        
    else:
        
        url_get = url_hs_kors_auto + "/car/?uin_lo=" + car.lo_uin
        response = requests.get(url_get)
        base1C = ''
    
        if response.status_code == 200:
            if response.text != '':
                base1C = json.loads(response.text)

    tab_counts = _price_edit_tab_counts(car)
    price_revaluations = _car_price_revaluations(car) if page == 4 else []
    photos = _car_photos_queryset(car) if page == 1 else []
    car_options_ctx = build_car_options_context(car) if page == 11 else {}
    list_price = RegRefCarsOrganizationsPrice.objects.filter(car=car).order_by('-date')

    interactiv = None

    if RegInteractivOcenka.objects.filter(rlk = car.lo.rlk).count() > 0:
        interactiv = RegInteractivOcenka.objects.filter(rlk = car.lo.rlk)[0]    
    
    agreement = None
    if DocCarAgreement.objects.filter(active = True).filter(lo = car.lo).count() > 0:
        agreement = DocCarAgreement.objects.filter(active = True).filter(lo = car.lo).order_by('-dataTime')[0] 
    
    shipment = None
    if agreement != None:
        if DocCarShipment.objects.filter(active = True).filter(rlk = agreement.rlk).count() > 0:
            shipment = DocCarShipment.objects.filter(active = True).filter(rlk = agreement.rlk)[0] 

    finance = round(car.cost_price * ((18 / 365) / 100) * car.days_in_stok, 2)

    avtohub_analytics = None
    estimation_analytics = None
    marketing = 0
    avtohubs = []
    calculations = []
    if page == 10:
        avtohub_analytics = _car_avtohub_analytics(car)
        estimation_analytics = _car_estimation_analytics(car)
        avtohub_analytics['estimation'] = estimation_analytics
        avtohub_analytics['total_count'] = (
            avtohub_analytics['count'] + estimation_analytics['count']
        )
        marketing = avtohub_analytics['summary']['marketing']
        avtohubs = avtohub_analytics['rows']
        calculations = estimation_analytics['rows']

    market_trends = None
    if page == 12:
        from eco.market_model_trends import market_car_trends_page_params
        market_trends = market_car_trends_page_params(car, request, embedded=True)

    calc_express    = RegRefCarsOrganizationsCalculationPrice.objects.filter(car = car).filter(evaluation__id = 7).order_by('-date')
    calc_autohub    = RegRefCarsOrganizationsCalculationPrice.objects.filter(car = car).filter(evaluation__id = 1).order_by('-date')
    calc_1C         = RegRefCarsOrganizationsCalculationPrice.objects.filter(car = car).filter(evaluation__id = 8).order_by('-date')

    selected = {
        'stores'        : RefStore.objects.all().order_by('name'),
        'evaluations'   : RefTypeEvaluationCarsOrganization.objects.all().order_by('name'),
        'stageprices'   : RefStagePrice.objects.all().order_by('name'),
        'groupprices'   : RefGroupPrice.objects.all().order_by('name'),
        'ratings'       : RefRatingCarsOrganization.objects.all().order_by('name'),
    }

    params = {
        'object'            : car,
        'selected'          : selected,
        'list_price'        : list_price,
        'tab_counts'        : tab_counts,
        'price_revaluations': price_revaluations,
        '1C'                : base1C,
        'calculations'      : calculations,
        'avtohubs'          : avtohubs,
        'avtohub_analytics' : avtohub_analytics,
        'estimation_analytics': estimation_analytics,
        'finance'           : finance,
        'marketing'         : marketing,
        'interactiv'        : interactiv,
        'agreement'         : agreement,
        'shipment'          : shipment,
        'calc_express'      : calc_express,
        'calc_autohub'      : calc_autohub,
        'calc_1C'           : calc_1C,
        'page'              : page,
        'photos'            : photos,
        'can_edit_photos'   : request.user.profiles.korsavto_settings,
        'market_trends'     : market_trends,
    }
    params.update(car_options_ctx)
    
    return render(request, "avtosalon/car_new_price_edit.html", {'params': params})


@login_required
def price(request, slug):
    
    if not request.user.profiles.price_car_new and not request.user.profiles.price_car_new_settings: 
        params = {
            'type': 'home',
            'request': request,
        }
        return render(request, 'errors/403.html', {'params': params})
    
    car = RefCarsOrganization.objects.filter(slug=slug).select_related(
        'unit', 'complectation_autoru', 'modification_autoru',
        'modification_autoru__model', 'modification_autoru__model__mark',
    ).first()
    if not car:
        raise Http404
    
    dop_car_info = {}
    chat, created = Chat.objects.get_or_create(name=car.slug, slug='car_' + str(car.slug))
    user = request.user 

    if 'del_u' in request.GET:
        uusr = User.objects.get(id = request.GET.get('del_u'))
        car.access_user.remove(uusr)
        car.save()
        return HttpResponseRedirect(request.path_info)
    
    if 'add_u' in request.GET:
                
        uusr = User.objects.get(id = request.GET.get('add_u'))
        car.access_user.add(uusr)
        car.save()
    
        new_message               = EmailPushCar()
        new_message.car           = car
        new_message.user          = uusr
        new_message.email         = uusr.email
        new_message.comment       = 'Вы добавлены к информации по ценнообразованию.'
        new_message.price         = True
        new_message.save()

        return HttpResponseRedirect(request.path_info)
    
    if request.method == 'POST':
        
        if 'min_km' in request.POST:
            min_km = int(request.POST.get('min_km', '0'))
            car.min_km = min_km
            car.min_km_user = user
            car.min_km_date = datetime.now()

            car.save(update_fields =['min_km', 'min_km_user', 'min_km_date'])
            if min_km != 0:
                send_web_socket_message(group = 'car_' + str(car.slug), chat = chat, user = user, text='Установлен минимальный км - ' + str(min_km), estimation_id='')
            else:
                send_web_socket_message(group = 'car_' + str(car.slug), chat = chat, user = user, text='Отключен ручной минимальный км', estimation_id='')
            return HttpResponseRedirect(request.get_full_path())            
    
    current_tab = request.GET.get('tab', 'avto')
    
    finance = round(car.cost_price * ((18 / 365) / 100) * car.days_in_stok, 2)
    marketing = 0
    avtohubs_list = Avtohub.objects.filter(vin=car.vin).filter(date__range=[car.lo_link_date, car.date_refresh]).order_by('-date')
    avtohubs = []
    for avtohub in avtohubs_list:
        percent = 0
        marketing = round(max(marketing, avtohub.totalAdvertisingCost), 2)
        if avtohub.numberOfCompetitors > 0:
            percent = avtohub.vRatingPosition / avtohub.numberOfCompetitors
        avtohubs.append({
            'date': avtohub.date,
            'avgMarketPrice': avtohub.avgMarketPrice,
            'averageDaysInSale': avtohub.averageDaysInSale,
            'vRatingPosition': avtohub.vRatingPosition,
            'numberOfCompetitors': avtohub.numberOfCompetitors,
            'percent': percent,
        })

    # Аналитика: остатки и продажи за последний месяц
    now = timezone.now()
    first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_end = first_day_this_month - timedelta(seconds=1)
    last_month_start = last_month_end.replace(day=1, hour=1, minute=1, second=0)
    last_month_end = now

    analytics = {
        'last_month_start'  : last_month_start,
        'last_month_end'    : last_month_end,
        'count_in_unit': 0,
        'count_all_dc': 0,
        'unit_sales_count': 0,
        'complectation_sales_count': 0,
        'cumulative_detail': [],
        'sales_by_day': [],
    }

    if car.complectation_autoru_id:
        analytics['count_in_unit'] = RefCarsOrganization.objects.filter(
            unit_id=car.unit_id,
            complectation_autoru_id=car.complectation_autoru_id,
            quantity__gt=0,
        ).count()
        analytics['count_all_dc'] = RefCarsOrganization.objects.filter(
            complectation_autoru_id=car.complectation_autoru_id,
            quantity__gt=0,
        ).count()

    from django.db.models.functions import TruncDate
    
    sale_type          = int(request.GET.get('sale_type', '1'))
    sale_dc            = request.GET.get('sale_dc', 'all')

    from powerbi.models import Cumulative

    analytics_current_vp = _cumulative_vp_metrics(Cumulative.objects.none())
    analytics_brand_other_vp = _cumulative_vp_metrics(Cumulative.objects.none())
    analytics_current_vp['unit_names'] = []
    analytics_brand_other_vp['unit_names'] = []

    q_cumulative = Cumulative.objects.filter(
        TipProdazhi = 'Розница',
        DataProdazhi__gte=last_month_start,
        DataProdazhi__lte=last_month_end,
        SebestoimostPoDokumentu__gt = 0
    )

    q_sales_base = _apply_car_sale_type_filter(q_cumulative, car, sale_type)
    if car.unit and car.unit.name:
        analytics_current_vp = _cumulative_vp_metrics(
            q_sales_base.filter(PodrazdelenieDTs__icontains=car.unit.name),
        )
        analytics_current_vp['unit_names'] = [car.unit.name]

        brand_other_units = _brand_other_unit_names(car)
        analytics_brand_other_vp['unit_names'] = brand_other_units
        if brand_other_units:
            analytics_brand_other_vp = _cumulative_vp_metrics(
                q_sales_base.filter(PodrazdelenieDTs__in=brand_other_units),
            )
            analytics_brand_other_vp['unit_names'] = brand_other_units

    if car.unit and car.unit.name:
        if sale_dc == 'all':
            q_unit = q_sales_base
        else:
            q_unit = q_sales_base.filter(PodrazdelenieDTs__icontains=car.unit.name)

        analytics['unit_sales_count'] = q_unit.count()
        q_unit = q_unit.annotate(
            cum = Sum('SummaMarzhiBezNDS') + Sum('VPOPFU') + Sum('SummaTreydInPoPlanu') + Sum('ValovayaPribylZChShiny') + Sum('SummaRabot') + Sum('ValovayaPribylZCh') + Sum('SummaGosreg')
        )
        analytics['cumulative_detail'] = list(
            q_unit.order_by('-DataProdazhi')[:100].values(
                'DataProdazhi', 'Marka', 'Model', 'Modifikatsiya', 'VIN',
                'VyruchkaZaAvto', 'KolichestvoAvto', 'PodrazdelenieDTs', 
                'TipProdazhi', 'SummaMarzhiBezNDS', 'VPOPFU', 'SummaTreydInPoPlanu',
                'ValovayaPribylZChShiny', 'SummaRabot', 'ValovayaPribylZCh', 'SummaGosreg', 'cum'  
            )
        )

        analytics['cumulative_sum_detail'] = q_unit.aggregate(
                sum_SummaMarzhiBezNDS = Sum("SummaMarzhiBezNDS"),
                sum_VPOPFU = Sum("VPOPFU"),
                sum_SummaTreydInPoPlanu = Sum("SummaTreydInPoPlanu"),
                sum_ValovayaPribylZChShiny = Sum("ValovayaPribylZChShiny"),
                sum_SummaRabot = Sum("SummaRabot"),
                sum_ValovayaPribylZCh = Sum("ValovayaPribylZCh"),
                sum_SummaGosreg = Sum("SummaGosreg"),
                sum_count = Count("VIN"),   
            )
        
        analytics['cumulative_sum'] = analytics['cumulative_sum_detail']['sum_SummaMarzhiBezNDS'] + analytics['cumulative_sum_detail']['sum_VPOPFU'] + analytics['cumulative_sum_detail']['sum_SummaTreydInPoPlanu'] + analytics['cumulative_sum_detail']['sum_ValovayaPribylZChShiny'] + analytics['cumulative_sum_detail']['sum_SummaRabot'] + analytics['cumulative_sum_detail']['sum_ValovayaPribylZCh'] + analytics['cumulative_sum_detail']['sum_SummaGosreg']
        
        if analytics['cumulative_sum_detail']['sum_count'] > 0: 
            analytics['udelka'] = analytics['cumulative_sum'] / analytics['cumulative_sum_detail']['sum_count']  
            analytics['udelka_count']  = analytics['cumulative_sum_detail']['sum_count']
        
        js_data = {
            'sum_SummaMarzhiBezNDS' : analytics['cumulative_sum_detail']['sum_SummaMarzhiBezNDS'] / analytics['cumulative_sum'] * 100,
            'sum_VPOPFU' : analytics['cumulative_sum_detail']['sum_VPOPFU'] / analytics['cumulative_sum'] * 100,
            'sum_SummaTreydInPoPlanu' : analytics['cumulative_sum_detail']['sum_SummaTreydInPoPlanu'] / analytics['cumulative_sum'] * 100,
            'sum_ValovayaPribylZChShiny' : analytics['cumulative_sum_detail']['sum_ValovayaPribylZChShiny'] / analytics['cumulative_sum'] * 100, 
            'sum_SummaRabot' : analytics['cumulative_sum_detail']['sum_SummaRabot'] / analytics['cumulative_sum'] * 100, 
            'sum_ValovayaPribylZCh' : analytics['cumulative_sum_detail']['sum_ValovayaPribylZCh'] / analytics['cumulative_sum'] * 100, 
            'sum_SummaGosreg' : analytics['cumulative_sum_detail']['sum_SummaGosreg'] / analytics['cumulative_sum'] * 100, 
        }
        js_data_udelka = {
            'udelka_SummaMarzhiBezNDS' : analytics['cumulative_sum_detail']['sum_SummaMarzhiBezNDS'] / analytics['cumulative_sum_detail']['sum_count'],
            'udelka_VPOPFU' : analytics['cumulative_sum_detail']['sum_VPOPFU'] / analytics['cumulative_sum_detail']['sum_count'],
            'udelka_SummaTreydInPoPlanu' : analytics['cumulative_sum_detail']['sum_SummaTreydInPoPlanu'] / analytics['cumulative_sum_detail']['sum_count'],
            'udelka_ValovayaPribylZChShiny' : analytics['cumulative_sum_detail']['sum_ValovayaPribylZChShiny'] / analytics['cumulative_sum_detail']['sum_count'], 
            'udelka_SummaRabot' : analytics['cumulative_sum_detail']['sum_SummaRabot'] / analytics['cumulative_sum_detail']['sum_count'], 
            'udelka_ValovayaPribylZCh' : analytics['cumulative_sum_detail']['sum_ValovayaPribylZCh'] / analytics['cumulative_sum_detail']['sum_count'], 
            'udelka_SummaGosreg' : analytics['cumulative_sum_detail']['sum_SummaGosreg'] / analytics['cumulative_sum_detail']['sum_count'], 
        }
        analytics['cumulative_sum_detail_percent']  = js_data
        analytics['cumulative_sum_detail_udelka']   = js_data_udelka

        # Продажи по дням для графика
        sales_by_day_qs = q_unit.annotate(
            day=TruncDate('DataProdazhi')
        ).values('day').annotate(count=Count('id')).order_by('day')
        analytics['sales_by_day'] = [
            {'date': d['day'].strftime('%d.%m') if d['day'] else '', 'count': d['count']}
            for d in sales_by_day_qs
        ]
        analytics['sales_by_day_json'] = json.dumps(analytics['sales_by_day'])

    if car.modification_autoru_id and car.modification_autoru.model_id:
        mark_name = car.modification_autoru.model.mark.name
        model_name = car.modification_autoru.model.name
        if mark_name and model_name:
            analytics['complectation_sales_count'] = q_cumulative.filter(
                Marka__icontains=mark_name,
                Model__icontains=model_name,
            ).count()

    selected = {
        'stores': RefStore.objects.all().order_by('name'),
        'evaluations': RefTypeEvaluationCarsOrganization.objects.all().order_by('name'),
        'stageprices': RefStagePrice.objects.all().order_by('name'),
        'groupprices': RefGroupPrice.objects.all().order_by('name'),
        'ratings': RefRatingCarsOrganization.objects.all().order_by('name'),
    }

    # Заказ-наряды с типом ремонта «допоборудование» (RefTypeRepair.dop=True)
    from documents.models import DocZN
    zn_list = []
    info_dop = None
    if car.vin:
        zn_list = DocZN.objects.filter(cars__vin=car.vin, typeRemont__dop=True).select_related('typeRemont', 'readyStatus', 'unit').order_by('-dataTime')[:200]
        
        info_dop = zn_list.aggregate(
                count=Count("id"),
                sum_amount=Sum("amount")  
            )
        dop_car_info['aggretgate_dop_zn'] = info_dop

    # Аналитика по ГК (все подразделения организации)
    analytics_gk = {
        'unit_sales_count': 0,
        'complectation_sales_count': 0,
        'sales_by_day': [],
        'sales_by_day_json': '[]',
        'cumulative_detail': [],
    }
    if car.organization_id:
        unit_names = list(
            RefCarsOrganization.objects.filter(organization_id=car.organization_id)
            .exclude(unit__isnull=True)
            .values_list('unit__name', flat=True)
            .distinct()
        )
        unit_names = [n for n in unit_names if n]
        if unit_names:
            q_gk = q_cumulative.filter(PodrazdelenieDTs__in=unit_names)
            analytics_gk['unit_sales_count'] = q_gk.count()
            if car.modification_autoru_id and car.modification_autoru.model_id:
                mark_name = car.modification_autoru.model.mark.name
                model_name = car.modification_autoru.model.name
                if mark_name and model_name:
                    analytics_gk['complectation_sales_count'] = q_gk.filter(
                        Marka__icontains=mark_name,
                        Model__icontains=model_name,
                    ).count()
            sales_by_day_gk = q_gk.annotate(day=TruncDate('DataProdazhi')).values('day').annotate(count=Count('id')).order_by('day')
            analytics_gk['sales_by_day'] = [
                {'date': d['day'].strftime('%d.%m') if d['day'] else '', 'count': d['count']}
                for d in sales_by_day_gk
            ]
            analytics_gk['sales_by_day_json'] = json.dumps(analytics_gk['sales_by_day'])
            analytics_gk['cumulative_detail'] = list(
                q_gk.order_by('-DataProdazhi')[:100].values(
                    'DataProdazhi', 'Marka', 'Model', 'Modifikatsiya', 'VIN',
                    'VyruchkaZaAvto', 'KolichestvoAvto', 'PodrazdelenieDTs', 'TipProdazhi',
                )
            )

    list_price = list(RegRefCarsOrganizationsPrice.objects.filter(car=car).order_by('-date')[:50])

    # Склад: остатки по модели (текущее подразделение или все подразделения)
    sclad = list()
    warehouse_scope     = ''
    sclad_type          = int(request.GET.get('sclad_type', '1'))
    if car.modification_autoru_id and car.modification_autoru.model_id:
        
        model_id            = car.modification_autoru.model_id
        warehouse_scope     = request.GET.get('warehouse_scope') 
        
        if warehouse_scope != None and warehouse_scope == 'all':
            sclad = RefCarsOrganization.objects.filter(
                    quantity__gt=0,
                ).select_related('unit', 'modification_autoru', 'complectation_autoru').order_by('name')
        else:
            sclad = RefCarsOrganization.objects.filter(
                    unit_id =car.unit_id,
                    quantity__gt=0,
                ).select_related('unit', 'modification_autoru', 'complectation_autoru').order_by('name')

        if sclad_type == 1:
            sclad = sclad.filter(modification_autoru__model = car.modification_autoru.model)
        elif sclad_type == 2: 
            sclad = sclad.filter(modification_autoru = car.modification_autoru)
        elif sclad_type == 3:
            sclad = sclad.filter(complectation_autoru = car.complectation_autoru)
         
    # Объекты для шаблона (страница price не загружает полные данные оценки/сделок)
    from types import SimpleNamespace
    estimation_empty = SimpleNamespace(tasks=[])
    interactiv_rlk_empty = SimpleNamespace(estimation=estimation_empty)

    car_analitics   = car.unit_info()
    sale_info       = car.sale_info()
    cumulative_data = car.cumulative_data()
    brand_mark_name = ''
    if car.modification_autoru and car.modification_autoru.model and car.modification_autoru.model.mark:
        brand_mark_name = ' ' + car.modification_autoru.model.mark.name

    car_price_and_dop = car.cost_price
    if info_dop != None and info_dop['sum_amount'] != None:
         car_price_and_dop = car_price_and_dop + info_dop['sum_amount']

    calcs = CarCalculations.objects.filter(car = car)
    params = {
        'object'    : car,
        'chat'      : chat,
        'calcs'     : calcs,
        'warehouse_scope'       : warehouse_scope,
        'sclad_type'            : sclad_type,
        'sale_type'             : sale_type,
        'sale_dc'               : sale_dc,
        'car_price_and_dop' : car_price_and_dop,
        'sale_info' : sale_info,
        'car_analitics' : car_analitics,
        'cumulative_data'   : cumulative_data,
        'brand_mark_name'   : brand_mark_name,
        'messages'      : chat.get_last_messages(),
        'selected'      : selected,
        'avtohubs'      : avtohubs,
        'finance'       : finance,
        'marketing'     : marketing,
        'user'          : request.user,
        'analytics'     : analytics,
        'analytics_current_vp': analytics_current_vp,
        'analytics_brand_other_vp': analytics_brand_other_vp,
        'analytics_gk'  : analytics_gk,
        'last_month_start': last_month_start,
        'last_month_end': last_month_end,
        'zn_list': zn_list,
        'current_tab': current_tab,
        'list_price': list_price,
        'sclad': sclad,
        'car_tasks': list(
            RegCarsOrganizationTask.objects.filter(car=car)
            .select_related('staff_created', 'staff_assignee')
            .prefetch_related('comments')
            .order_by('-date_created')[:100]
        ),
        'interactiv': None,
        'agreement': None,
        'shipment': None,
        'interactiv_rlk': interactiv_rlk_empty,
        'estimation': estimation_empty,
        'calculations': [],
        'calc_express': [],
        'calc_autohub': [],
        'calc_1C': [],
        'dop_car_info'   : dop_car_info,
        'base_template': 'base_web.html' if (request.user.is_authenticated and request.user.is_staff) else 'base_web_customer.html',
    }

    return render(request, "avtosalon/car_new_price.html", {'params': params})


def access_user(request, slug):
    search = request.GET.get('search', '')
    users = list()
    if id != '' and search != '':
        car = RefCarsOrganization.objects.filter(slug=slug).first()
        users = User.objects.exclude(pk__in = car.access_user.all().values_list('id')).exclude(email = '').exclude(first_name = '').filter(is_active = True).filter(is_staff = True)
        if search != '':
            users = users.filter(Q(profiles__eco_name__icontains = search) | Q(email__icontains = search))    
            users = list(users.order_by('last_name', 'first_name').values('profiles__eco_name', 'last_name', 'first_name', 'id', 'email'))
    return JsonResponse(users, safe=False, status=status.HTTP_200_OK)


def send_web_socket_message(group, chat, user, text, estimation_id):
    from task_manager.views import send_message_socket
    group_s = str(group or '')
    if group_s.startswith('car_') or 'car' in group_s:
        channel = 'cars'
    elif group_s.startswith('aav_'):
        channel = 'avito'
    else:
        channel = 'estimation'
    message_json = {
            'chat_id'       : str(chat.pk),
            'name'          : str(user),
            'chat'          : group,
            'message'       : text,
            'username'      : str(user),
            'last_name'     : user.last_name,
            'first_name'    : user.first_name,
            'psevdo_name'   : user.profiles.eco_name,
            'eco'           : user.profiles.eco,
            'estimation_id' : estimation_id,
            'channel'       : channel,
        }    
    
    send_message_socket(message = message_json)

@login_required
def photos_edit(request, slug):
    """
    Страница управления фотографиями автомобиля
    """
    from django.contrib import messages
    
    # ОПТИМИЗАЦИЯ: Используем select_related для оптимизации запросов
    car = RefCarsOrganization.objects.select_related(
        'modification_autoru',
        'modification_autoru__model',
        'modification_autoru__model__mark',
        'unit',
        'store'
    ).get(slug=slug)
    
    # Проверка прав доступа
    if not request.user.profiles.korsavto_settings:
        params = {
            'type': 'home',
            'request': request,
        }
        return render(request, 'errors/403.html', {'params': params})
    
    if request.method == "POST":
        if handle_car_photos_post(request, car):
            return HttpResponseRedirect(request.build_absolute_uri())
    
    photos = _car_photos_queryset(car)
    
    params = {
        'type': 'photos_edit',
        'object': car,
        'photos': photos,
    }
    
    return render(request, "avtosalon/car_new_photos_edit.html", {'params': params})


@login_required
def costs_edit(request, slug):
    """
    Страница отображения затрат на автомобиль
    Затраты хранятся в DocZNKA, связь через поле lo (DocLO)
    """
    # ОПТИМИЗАЦИЯ: Используем select_related для оптимизации запросов
    car = RefCarsOrganization.objects.select_related(
        'modification_autoru',
        'modification_autoru__model',
        'modification_autoru__model__mark',
        'unit',
        'store',
        'lo'
    ).get(slug=slug)
    
    # Проверка прав доступа
    if not request.user.profiles.korsavto_settings:
        params = {
            'type': 'home',
            'request': request,
        }
        return render(request, 'errors/403.html', {'params': params})
    
    # Получаем все заказ-наряды по листу оценки
    znka_list = []
    if car.lo:
        # ОПТИМИЗАЦИЯ: Загружаем все заказ-наряды с оптимизацией
        # Используем prefetch_related для загрузки всех связанных объектов одним запросом
        znka_queryset = DocZNKA.objects.filter(lo=car.lo).select_related(
            'organization',
            'unit',
            'master',
            'masterOut',
            'customer',
            'cars',
            'typeRemont',
            'readyStatus',
            'lo'
        ).prefetch_related(
            'docznworkka_set__work',
            'docznworkka_set__type',
            'docznproductka_set__product',
            'docznproductka_set__type',
            'docznserviceska_set__service',
            'docznserviceska_set__type',
            'docznperformerska_set__staff'
        ).order_by('-dataTime')
        
        for znka in znka_queryset:
            # ОПТИМИЗАЦИЯ: Используем уже загруженные через prefetch_related объекты
            # Не делаем дополнительных запросов к БД
            works = list(znka.docznworkka_set.all())
            products = list(znka.docznproductka_set.all())
            services = list(znka.docznserviceska_set.all())
            performers = list(znka.docznperformerska_set.all())
            
            # Подсчитываем суммы
            works_total = sum(w.amountResult for w in works)
            products_total = sum(p.amountResult for p in products)
            services_total = sum(s.amountResult for s in services)
            total_amount = works_total + products_total + services_total
            
            znka_data = {
                'znka': znka,
                'works': works,
                'products': products,
                'services': services,
                'performers': performers,
                'works_total': works_total,
                'products_total': products_total,
                'services_total': services_total,
                'total_amount': total_amount,
            }
            znka_list.append(znka_data)
    
    # Общие суммы по всем заказ-нарядам
    total_works = sum(z['works_total'] for z in znka_list)
    total_products = sum(z['products_total'] for z in znka_list)
    total_services = sum(z['services_total'] for z in znka_list)
    grand_total = sum(z['total_amount'] for z in znka_list)
    
    params = {
        'type': 'costs_edit',
        'object': car,
        'znka_list': znka_list,
        'total_works': total_works,
        'total_products': total_products,
        'total_services': total_services,
        'grand_total': grand_total,
    }
    
    return render(request, "avtosalon/car_new_costs_edit.html", {'params': params})


@login_required
def warehouse_analysis(request):
    """
    Анализ склада автомобилей - дашборд с метриками и проблемами
    """
    from datetime import datetime, timedelta
    from django.db.models import Exists, OuterRef
    try:
        from dateutil import parser
    except ImportError:
        parser = None
    
    # Фильтры
    unit_ids = request.GET.getlist('unit[]')
    status_ids = request.GET.getlist('status[]')
    days_in_stock_min = request.GET.get('days_in_stock_min', '')
    days_in_stock_max = request.GET.get('days_in_stock_max', '')
    photo_age_days = request.GET.get('photo_age_days', '90')
    evaluation_age_days = request.GET.get('evaluation_age_days', '90')
    
    try:
        photo_age_days = int(photo_age_days)
    except:
        photo_age_days = 90
    
    try:
        evaluation_age_days = int(evaluation_age_days)
    except:
        evaluation_age_days = 90
    
    # Базовый queryset с аннотациями для оптимизации
    from django.db.models import Min, Max, Prefetch
    
    # ОПТИМИЗАЦИЯ: Используем аннотации для подсчета фото прямо в queryset
    base_qs = RefCarsOrganization.objects.exclude(quantity=0).select_related(
        'unit', 'status', 'store', 'modification_autoru',
        'modification_autoru__model', 'modification_autoru__model__mark',
        'evaluation', 'lo'
    ).annotate(
        photos_count=Count('refcarsorganizationfiles', filter=Q(refcarsorganizationfiles__file__isnull=False), distinct=True),
        oldest_photo_date=Min('refcarsorganizationfiles__date', filter=Q(refcarsorganizationfiles__file__isnull=False))
    )
    
    # Применяем фильтры
    if unit_ids:
        try:
            base_qs = base_qs.filter(unit__id__in=[int(uid) for uid in unit_ids])
        except ValueError:
            pass
    
    if status_ids:
        try:
            base_qs = base_qs.filter(status__id__in=[int(sid) for sid in status_ids])
        except ValueError:
            pass
    
    if days_in_stock_min:
        try:
            base_qs = base_qs.filter(days_in_stok__gte=int(days_in_stock_min))
        except ValueError:
            pass
    
    if days_in_stock_max:
        try:
            base_qs = base_qs.filter(days_in_stok__lte=int(days_in_stock_max))
        except ValueError:
            pass
    
    # ОПТИМИЗАЦИЯ: Получаем все автомобили для статистики (без ограничений)
    # Но для отображения используем пагинацию
    cars_list_all = list(base_qs)
    car_ids_all = [car.id for car in cars_list_all]
    car_vins_all = [car.vin for car in cars_list_all if car.vin]
    
    # Данные о фото уже в аннотациях, создаем словарь для удобства
    photos_data = {}
    for car in cars_list_all:
        photos_data[car.id] = {
            'count': car.photos_count or 0,
            'oldest_date': car.oldest_photo_date
        }
    
    # Загружаем данные Autohub
    latest_autohub_data = {}
    prev_autohub_data = {}
    comparison_date = timezone.now() - timedelta(days=7)
    
    if car_vins_all:
        # ОПТИМИЗАЦИЯ: Используем один запрос с подзапросами для получения последних записей
        from django.db.models import Max
        
        # Получаем максимальные даты для каждого VIN одним запросом
        max_dates_qs = Avtohub.objects.filter(vin__in=car_vins_all).values('vin').annotate(
            max_date=Max('date')
        )
        max_date_dict = {item['vin']: item['max_date'] for item in max_dates_qs}
        
        # ОПТИМИЗАЦИЯ: Загружаем все последние записи одним запросом используя Q объекты
        if max_date_dict:
            # Создаем Q объект для фильтрации по vin и date одновременно
            q_objects = Q()
            for vin, max_date in max_date_dict.items():
                q_objects |= Q(vin=vin, date=max_date)
            
            latest_records = Avtohub.objects.filter(q_objects).only(
                'vin', 'autoruViews', 'avitoViews', 'callsCounts_uniqueTotal',
                'chatsCounts_uniqueTotal', 'vRatingPosition', 'avgMarketPrice', 'price', 'isInSale', 'date'
            )
            
            for record in latest_records:
                latest_autohub_data[record.vin] = record
        
        # ОПТИМИЗАЦИЯ: Загружаем предыдущие записи более эффективно - одним запросом
        if max_date_dict and latest_autohub_data:
            # Для каждого VIN получаем предыдущую запись
            prev_vins = list(latest_autohub_data.keys())
            # Загружаем все записи для этих VIN одним запросом
            prev_records_all = Avtohub.objects.filter(
                vin__in=prev_vins
            ).only(
                'vin', 'autoruViews', 'avitoViews', 'callsCounts_uniqueTotal',
                'chatsCounts_uniqueTotal', 'vRatingPosition', 'avgMarketPrice', 'price', 'date'
            ).order_by('vin', '-date')
            
            # Группируем по VIN и берем первую запись для каждого VIN, которая <= threshold
            current_vin = None
            current_max_date = None
            for record in prev_records_all:
                if record.vin != current_vin:
                    current_vin = record.vin
                    if current_vin in max_date_dict:
                        current_max_date = max_date_dict[current_vin]
                        prev_date_threshold = current_max_date - timedelta(days=7)
                        if record.date <= prev_date_threshold:
                            prev_autohub_data[current_vin] = record
                            current_vin = None  # Помечаем, что нашли для этого VIN
    
    # Загружаем информацию о размещении
    autoru_site = AvtohubSite.objects.filter(name__icontains='auto.ru').first()
    avito_site = AvtohubSite.objects.filter(name__icontains='avito').first()
    
    autoru_placement = {}
    avito_placement = {}
    
    if autoru_site and car_vins_all:
        # ОПТИМИЗАЦИЯ: Получаем последние записи с использованием only() и одного запроса
        from django.db.models import Max
        autoru_max_dates = AvtohubSiteInfo.objects.filter(
            vin__in=car_vins_all,
            site=autoru_site
        ).values('vin').annotate(max_date=Max('date'))
        
        # Создаем словарь для быстрого поиска
        vin_date_map = {item['vin']: item['max_date'] for item in autoru_max_dates}
        
        # Загружаем все записи одним запросом с only()
        if vin_date_map:
            # Используем Q объекты для фильтрации по vin и date одновременно
            q_objects = Q()
            for vin, max_date in vin_date_map.items():
                q_objects |= Q(vin=vin, date=max_date)
            
            autoru_records = AvtohubSiteInfo.objects.filter(
                site=autoru_site
            ).filter(q_objects).only('vin', 'externalState', 'hasProblems', 'externalURL')
            
            for record in autoru_records:
                autoru_placement[record.vin] = record
    
    if avito_site and car_vins_all:
        # ОПТИМИЗАЦИЯ: Получаем последние записи с использованием only() и одного запроса
        from django.db.models import Max
        avito_max_dates = AvtohubSiteInfo.objects.filter(
            vin__in=car_vins_all,
            site=avito_site
        ).values('vin').annotate(max_date=Max('date'))
        
        # Создаем словарь для быстрого поиска
        vin_date_map = {item['vin']: item['max_date'] for item in avito_max_dates}
        
        # Загружаем все записи одним запросом с only()
        if vin_date_map:
            # Используем Q объекты для фильтрации по vin и date одновременно
            q_objects = Q()
            for vin, max_date in vin_date_map.items():
                q_objects |= Q(vin=vin, date=max_date)
            
            avito_records = AvtohubSiteInfo.objects.filter(
                site=avito_site
            ).filter(q_objects).only('vin', 'externalState', 'hasProblems', 'externalURL')
            
            for record in avito_records:
                avito_placement[record.vin] = record
    
    # Загружаем данные о переоценке
    estimation_data = {}
    price_data = {}
    
    if car_ids_all:
        # ОПТИМИЗАЦИЯ: Используем агрегацию для получения последних дат одним запросом
        from django.db.models import Max
        
        # Последние оценки - получаем максимальные даты для каждого автомобиля
        estimation_dates = RegEstimationRefCarsOrganizations.objects.filter(
            car_id__in=car_ids_all
        ).values('car_id').annotate(max_date=Max('date'))
        estimation_data = {item['car_id']: item['max_date'] for item in estimation_dates}
        
        # Последние расчеты цены - получаем максимальные даты для каждого автомобиля
        price_dates = RegRefCarsOrganizationsCalculationPrice.objects.filter(
            car_id__in=car_ids_all
        ).values('car_id').annotate(max_date=Max('date'))
        price_data = {item['car_id']: item['max_date'] for item in price_dates}
    
    # Обрабатываем каждый автомобиль для статистики
    now = timezone.now()
    analysis_results_all = []
    
    stats = {
        'total_cars': len(cars_list_all),
        'no_photos': 0,
        'old_photos': 0,
        'poor_photo_quality': 0,
        'not_on_autoru': 0,
        'not_on_avito': 0,
        'falling_interest': 0,
        'falling_price': 0,
        'not_in_sale_status': 0,
        'old_evaluation': 0,
    }
    
    for car in cars_list_all:
        car_analysis = {
            'car': car,
            'issues': [],
            'metrics': {},
        }
        
        # 1. Анализ фото
        photo_info = photos_data.get(car.id, {})
        photos_count_val = photo_info.get('count', 0)
        
        if photos_count_val == 0:
            car_analysis['issues'].append('no_photos')
            stats['no_photos'] += 1
        else:
            # Проверяем возраст фото
            oldest_date = photo_info.get('oldest_date')
            if oldest_date:
                if isinstance(oldest_date, str):
                    try:
                        if parser:
                            oldest_date = parser.parse(oldest_date)
                        else:
                            from django.utils.dateparse import parse_datetime
                            oldest_date = parse_datetime(oldest_date)
                    except:
                        oldest_date = None
            
            if oldest_date:
                try:
                    if oldest_date.tzinfo is None:
                        oldest_date = timezone.make_aware(oldest_date)
                    days_old = (now - oldest_date).days
                    car_analysis['metrics']['photo_age_days'] = days_old
                    if days_old > photo_age_days:
                        car_analysis['issues'].append('old_photos')
                        stats['old_photos'] += 1
                except Exception:
                    pass
            
            # Проверяем количество фото
            if photos_count_val < 5:
                car_analysis['issues'].append('poor_photo_quality')
                stats['poor_photo_quality'] += 1
        
        car_analysis['metrics']['photos_count'] = photos_count_val
        
        # 2. Анализ размещения на Авто.ру
        if car.vin in autoru_placement:
            placement = autoru_placement[car.vin]
            if placement.externalState not in ['active', 'published'] or placement.hasProblems:
                car_analysis['issues'].append('autoru_problems')
        else:
            car_analysis['issues'].append('not_on_autoru')
            stats['not_on_autoru'] += 1
        
        # 3. Анализ размещения на Авито
        if car.vin in avito_placement:
            placement = avito_placement[car.vin]
            if placement.externalState not in ['active', 'published'] or placement.hasProblems:
                car_analysis['issues'].append('avito_problems')
        else:
            car_analysis['issues'].append('not_on_avito')
            stats['not_on_avito'] += 1
        
        # 4. Анализ по Autohub
        if car.vin in latest_autohub_data:
            latest = latest_autohub_data[car.vin]
            prev = prev_autohub_data.get(car.vin)
            
            if prev:
                views_change = (latest.autoruViews or 0) - (prev.autoruViews or 0)
                calls_change = (latest.callsCounts_uniqueTotal or 0) - (prev.callsCounts_uniqueTotal or 0)
                chats_change = (latest.chatsCounts_uniqueTotal or 0) - (prev.chatsCounts_uniqueTotal or 0)
                position_change = (prev.vRatingPosition or 999) - (latest.vRatingPosition or 999)
                price_change = (prev.avgMarketPrice or 0) - (latest.avgMarketPrice or 0)
                
                car_analysis['metrics']['autohub'] = {
                    'views_change': views_change,
                    'calls_change': calls_change,
                    'chats_change': chats_change,
                    'position_change': position_change,
                    'price_change': price_change,
                    'current_position': latest.vRatingPosition,
                    'current_price': latest.avgMarketPrice,
                }
                
                if views_change < -10 or calls_change < -2 or chats_change < -2:
                    car_analysis['issues'].append('falling_interest')
                    stats['falling_interest'] += 1
                
                if position_change < -5:
                    car_analysis['issues'].append('worse_position')
                
                if price_change > 50000:
                    car_analysis['issues'].append('falling_price')
                    stats['falling_price'] += 1
        
        # 5. Анализ статуса
        if car.status:
            status_name_lower = car.status.name.lower()
            if 'продаж' not in status_name_lower and 'готов' not in status_name_lower:
                if car.date_refresh:
                    try:
                        days_not_in_sale = (now - car.date_refresh).days
                        if days_not_in_sale > 3:
                            car_analysis['issues'].append('not_in_sale_status')
                            stats['not_in_sale_status'] += 1
                            car_analysis['metrics']['days_not_in_sale'] = days_not_in_sale
                    except Exception:
                        pass
        
        # 6. Анализ переоценки
        evaluation_date = estimation_data.get(car.id) or price_data.get(car.id)
        if not evaluation_date and car.lo and car.lo.dataTime:
            evaluation_date = car.lo.dataTime
        
        if evaluation_date:
            if isinstance(evaluation_date, str):
                try:
                    if parser:
                        evaluation_date = parser.parse(evaluation_date)
                    else:
                        from django.utils.dateparse import parse_datetime
                        evaluation_date = parse_datetime(evaluation_date)
                except:
                    evaluation_date = None
            
            if evaluation_date:
                try:
                    if evaluation_date.tzinfo is None:
                        evaluation_date = timezone.make_aware(evaluation_date)
                    days_since_evaluation = (now - evaluation_date).days
                    car_analysis['metrics']['days_since_evaluation'] = days_since_evaluation
                    if days_since_evaluation > evaluation_age_days:
                        car_analysis['issues'].append('old_evaluation')
                        stats['old_evaluation'] += 1
                except Exception:
                    pass
        
        if car_analysis['issues']:
            analysis_results_all.append(car_analysis)
    
    # Сортируем по количеству проблем
    analysis_results_all.sort(key=lambda x: len(x['issues']), reverse=True)
    
    # ПАГИНАЦИЯ: Разбиваем результаты на страницы по 25 автомобилей
    paginator = Paginator(analysis_results_all, 25)
    page = request.GET.get('page', 1)
    
    try:
        analysis_results = paginator.page(page)
    except PageNotAnInteger:
        analysis_results = paginator.page(1)
    except EmptyPage:
        analysis_results = paginator.page(paginator.num_pages)
    
    # Справочные данные
    units = RefUnit.objects.filter(buauto=True).only('id', 'name').order_by('name')
    statuses = RefStatusCarsOrganization.objects.only('id', 'name').order_by('name')
    
    params = {
        'type': 'warehouse_analysis',
        'analysis_results': analysis_results,
        'stats': stats,
        'units': units,
        'statuses': statuses,
        'filters': {
            'unit_ids': [int(uid) for uid in unit_ids if uid.isdigit()],
            'status_ids': [int(sid) for sid in status_ids if sid.isdigit()],
            'days_in_stock_min': days_in_stock_min,
            'days_in_stock_max': days_in_stock_max,
            'photo_age_days': photo_age_days,
            'evaluation_age_days': evaluation_age_days,
        },
    }
    
    return render(request, "avtosalon/warehouse_analysis.html", {'params': params})


def refresh_cars(request):

    list_cars = list()

    if request.method == "POST":
          
        data = json.loads(request.POST.get('data'))

        unit_json   = data['Unit']
        unit        = get_unit(unit_json)
        
        count_add   = 0
        count_del   = 0
        count_stock = 0

        list_del = list()
        cars_update = RefCarsOrganization.objects.filter(unit = unit).exclude(quantity = 0)
        for car in cars_update:
            car.quantity = 0
            car.save()
            list_del.append(car.pk)

        list_load_photo = list()

        cars_json   = data['Cars']
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
            info_car = {
                'Car_object'        : car_object,
                'Lo_uin'            : car['Lo_uin'],
                'Photos'            : car['Photos']
            }
            list_load_photo.append(info_car)

        for car in list_load_photo:
        
            car_object = car['Car_object']
            load_photos(car_object, car['Photos'])

            image           = car_object.qr.open()
            image_content   = image.read()
            image_base64    = base64.b64encode(image_content)
            car_link        = 'https://ah.kors-group.com/cars/' + str(car_object.slug) + '/'
            
            car_info = {
                'Lo_Uin'    : car['Lo_uin'],
                'QR_Base64' : str(image_base64.decode()),
                'Lo_link'   : car_link
            }
            
            list_cars.append(car_info)


        info = {
            'list_cars' : list_cars
        }
        count_del   = len(list_del)
        count_stock = len(cars_json)

        if count_stock > 0:
            refresh_log = RefreshCarsLog()
            refresh_log.unit = unit
            refresh_log.count_add   = count_add
            refresh_log.count_del   = count_del
            refresh_log.count_stock = count_stock
            refresh_log.save()

        info = {
            'list_cars' : list_cars
        }
        return render(request, "avtosalon/test.html") 
    return render(request, "avtosalon/test.html") 


def load_photos(car, photos):
    
    ref_photos = RefCarsOrganizationFiles.objects.filter(сars_organization = car)
    for ref_photo in ref_photos:
        name    = ref_photo.name
        delite  = True
        for photo in photos:
            if name == photo['Name']:
                delite = False
        if delite:
            ref_photo.delete()

    for photo in photos:
        ref_photos = RefCarsOrganizationFiles.objects.filter(сars_organization = car)
        add = True
        for ref_photo in ref_photos:
            if ref_photo.name == photo['Name']:
                add = False
        if add:
            photo_object                    = RefCarsOrganizationFiles()
            photo_object.сars_organization  = car
            photo_object.name               = photo['Name']
            photo_object.url                = photo['Url']
            photo_object.url_mini           = photo['UrlMini']
            photo_object.main               = photo['Main']
            
            image_url   = photo['Url']
            response    = requests.get(image_url, stream=True)
            if response.status_code != requests.codes.ok:
                continue 
            file_name = image_url.split('/')[-1]
            lf = tempfile.NamedTemporaryFile()
            for block in response.iter_content(1024 * 8):
                if not block:
                    break
                lf.write(block)
            photo_object.file.save(file_name, files.File(lf)) 

            image_url   = photo['UrlMini']
            response    = requests.get(image_url, stream=True)
            if response.status_code != requests.codes.ok:
                continue 
            file_name = image_url.split('/')[-1]
            lf = tempfile.NamedTemporaryFile()
            for block in response.iter_content(1024 * 8):
                if not block:
                    break
                lf.write(block)
            photo_object.file_mini.save(file_name, files.File(lf)) 

            photo_object.save()


def info_js(request, slug):
    
    car         = RefCarsOrganization.objects.get(slug = slug)
    cars_info   = RefCarsOrganization.objects.exclude(quantity = 0).filter(modification_autoru__pk = car.modification_autoru.pk)
    car_list    = list()
    for car_info in cars_info:
        car_data = {
            'slug'      : car_info.slug,
            'unit_name' : car_info.unit.name,
            'photo'     : car_info.get_photo(),
            'days'      : car_info.days_in_stok,
            'stage'     : car_info.stage_price.name,
            'group'     : car_info.group_price.name,
            'price'     : car_info.price,
            'cost_price'    : car_info.cost_price,
            'outlay'        : car_info.outlay,

        }
        car_list.append(car_data)

    params = {
        'title'     : car.name,
        'slug'      : slug,
        'car_list'  : car_list
        }
    
    return JsonResponse(params, safe=False, status=status.HTTP_200_OK)


def _empty_cumulative_vp_detail():
    return {
        'sum_SummaMarzhiBezNDS': 0,
        'sum_VPOPFU': 0,
        'sum_SummaTreydInPoPlanu': 0,
        'sum_ValovayaPribylZChShiny': 0,
        'sum_SummaRabot': 0,
        'sum_ValovayaPribylZCh': 0,
        'sum_SummaGosreg': 0,
        'sum_count': 0,
    }


def _empty_cumulative_vp_percent():
    return {k: 0 for k in (
        'sum_SummaMarzhiBezNDS', 'sum_VPOPFU', 'sum_SummaTreydInPoPlanu',
        'sum_ValovayaPribylZChShiny', 'sum_SummaRabot', 'sum_ValovayaPribylZCh', 'sum_SummaGosreg',
    )}


def _empty_cumulative_vp_udelka():
    return {k.replace('sum_', 'udelka_'): 0 for k in _empty_cumulative_vp_percent()}


def _cumulative_vp_metrics(qs):
    """Агрегаты ВП по queryset Cumulative (розница)."""
    analytics = {
        'cumulative_sum': 0,
        'udelka': 0,
        'udelka_count': 0,
        'unit_sales_count': qs.count(),
        'cumulative_sum_detail': _empty_cumulative_vp_detail(),
        'cumulative_sum_detail_percent': _empty_cumulative_vp_percent(),
        'cumulative_sum_detail_udelka': _empty_cumulative_vp_udelka(),
    }
    if not analytics['unit_sales_count']:
        return analytics

    detail = qs.aggregate(
        sum_SummaMarzhiBezNDS=Sum('SummaMarzhiBezNDS'),
        sum_VPOPFU=Sum('VPOPFU'),
        sum_SummaTreydInPoPlanu=Sum('SummaTreydInPoPlanu'),
        sum_ValovayaPribylZChShiny=Sum('ValovayaPribylZChShiny'),
        sum_SummaRabot=Sum('SummaRabot'),
        sum_ValovayaPribylZCh=Sum('ValovayaPribylZCh'),
        sum_SummaGosreg=Sum('SummaGosreg'),
        sum_count=Count('VIN'),
    )
    for key, val in detail.items():
        detail[key] = val or 0

    cumulative_sum = (
        detail['sum_SummaMarzhiBezNDS'] + detail['sum_VPOPFU'] + detail['sum_SummaTreydInPoPlanu']
        + detail['sum_ValovayaPribylZChShiny'] + detail['sum_SummaRabot'] + detail['sum_ValovayaPribylZCh']
        + detail['sum_SummaGosreg']
    )
    analytics['cumulative_sum_detail'] = detail
    analytics['cumulative_sum'] = cumulative_sum

    if detail['sum_count'] > 0:
        analytics['udelka'] = cumulative_sum / detail['sum_count']
        analytics['udelka_count'] = detail['sum_count']

    if cumulative_sum > 0:
        analytics['cumulative_sum_detail_percent'] = {
            'sum_SummaMarzhiBezNDS': detail['sum_SummaMarzhiBezNDS'] / cumulative_sum * 100,
            'sum_VPOPFU': detail['sum_VPOPFU'] / cumulative_sum * 100,
            'sum_SummaTreydInPoPlanu': detail['sum_SummaTreydInPoPlanu'] / cumulative_sum * 100,
            'sum_ValovayaPribylZChShiny': detail['sum_ValovayaPribylZChShiny'] / cumulative_sum * 100,
            'sum_SummaRabot': detail['sum_SummaRabot'] / cumulative_sum * 100,
            'sum_ValovayaPribylZCh': detail['sum_ValovayaPribylZCh'] / cumulative_sum * 100,
            'sum_SummaGosreg': detail['sum_SummaGosreg'] / cumulative_sum * 100,
        }

    if detail['sum_count'] > 0:
        cnt = detail['sum_count']
        analytics['cumulative_sum_detail_udelka'] = {
            'udelka_SummaMarzhiBezNDS': detail['sum_SummaMarzhiBezNDS'] / cnt,
            'udelka_VPOPFU': detail['sum_VPOPFU'] / cnt,
            'udelka_SummaTreydInPoPlanu': detail['sum_SummaTreydInPoPlanu'] / cnt,
            'udelka_ValovayaPribylZChShiny': detail['sum_ValovayaPribylZChShiny'] / cnt,
            'udelka_SummaRabot': detail['sum_SummaRabot'] / cnt,
            'udelka_ValovayaPribylZCh': detail['sum_ValovayaPribylZCh'] / cnt,
            'udelka_SummaGosreg': detail['sum_SummaGosreg'] / cnt,
        }

    return analytics


def _apply_car_sale_type_filter(q, car, sale_type):
    if not car.modification_autoru_id:
        return q
    if sale_type == 0:
        brand = _resolve_price_car_brand_for_car(car)
        if brand:
            mods = AutoruModification.objects.filter(
                model__mark_id__in=brand.marks.values_list('pk', flat=True),
            )
            model_ids = list(brand.models_included.values_list('pk', flat=True))
            if model_ids:
                mods = mods.filter(model_id__in=model_ids)
            return q.filter(IDModifikatsii__in=mods.values_list('idSite', flat=True))
        model_list = AutoruModification.objects.filter(
            model__mark=car.modification_autoru.model.mark,
        ).values_list('idSite', flat=True)
        return q.filter(IDModifikatsii__in=model_list)
    if sale_type == 1:
        model_list = AutoruModification.objects.filter(
            model=car.modification_autoru.model,
        ).values_list('idSite', flat=True)
        return q.filter(IDModifikatsii__in=model_list)
    if sale_type == 2:
        return q.filter(IDModifikatsii=car.modification_autoru.idSite)
    if sale_type == 3 and car.complectation_autoru_id:
        return q.filter(IdKomplektatsii=car.complectation_autoru.idSite)
    return q


def _resolve_price_car_brand_for_car(car):
    return resolve_price_car_brand_for_car(car)


def _cars_qs_for_price_car_brand(brand):
    mark_ids = list(brand.marks.values_list('pk', flat=True))
    if not mark_ids:
        return RefCarsOrganization.objects.none()
    qs = RefCarsOrganization.objects.filter(
        modification_autoru__model__mark_id__in=mark_ids,
    )
    model_ids = list(brand.models_included.values_list('pk', flat=True))
    if model_ids:
        qs = qs.filter(modification_autoru__model_id__in=model_ids)
    return qs


def _is_same_podrazdelenie(podrazdelenie, unit_name):
    if not podrazdelenie or not unit_name:
        return False
    podrazdelenie = podrazdelenie.strip().lower()
    unit_name = unit_name.strip().lower()
    return podrazdelenie == unit_name or unit_name in podrazdelenie or podrazdelenie in unit_name


def _brand_sales_podrazdeleniya(car, month_start, now, sale_type=3, current_unit_name=None):
    """Подразделения с продажами бренда за период (из Cumulative, не со склада)."""
    from powerbi.models import Cumulative

    if not car or not car.modification_autoru_id:
        return []

    q = Cumulative.objects.filter(
        TipProdazhi='Розница',
        DataProdazhi__gte=month_start,
        DataProdazhi__lte=now,
        SebestoimostPoDokumentu__gt=0,
    ).exclude(PodrazdelenieDTs__isnull=True).exclude(PodrazdelenieDTs='')
    q = _apply_car_sale_type_filter(q, car, sale_type)

    result = []
    seen = set()
    for name in q.values_list('PodrazdelenieDTs', flat=True).distinct():
        name = (name or '').strip()
        if not name:
            continue
        if _is_same_podrazdelenie(name, current_unit_name):
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(name)
    return sorted(result)


def _brand_other_unit_names(car):
    if not car.unit_id:
        return []

    brand = _resolve_price_car_brand_for_car(car)
    if brand:
        qs = _cars_qs_for_price_car_brand(brand)
        if car.organization_id:
            qs = qs.filter(organization_id=car.organization_id)
    elif car.modification_autoru_id and car.organization_id:
        qs = RefCarsOrganization.objects.filter(
            organization_id=car.organization_id,
            modification_autoru__model__mark_id=car.modification_autoru.model.mark_id,
        )
    else:
        return []

    return [
        name for name in qs.exclude(unit__isnull=True)
        .exclude(unit_id=car.unit_id)
        .values_list('unit__name', flat=True)
        .distinct()
        if name
    ]


_DEAL_SALES_TABLE_ROWS = (
    ('vp_udelka', 'КВП уд. ₽', 'money'),
    ('sales_count', 'Продаж, шт.', 'count'),
    ('vp_total', 'ВП итого, ₽', 'money'),
    ('udelka_SummaMarzhiBezNDS', 'Маржа без НДС уд., ₽', 'money'),
    ('udelka_VPOPFU', 'ОПФУ уд., ₽', 'money'),
    ('udelka_SummaTreydInPoPlanu', 'Trade-in уд., ₽', 'money'),
    ('udelka_ValovayaPribylZChShiny', 'ВП шины уд., ₽', 'money'),
    ('udelka_SummaRabot', 'Работы уд., ₽', 'money'),
    ('udelka_ValovayaPribylZCh', 'ВП запчасти уд., ₽', 'money'),
    ('udelka_SummaGosreg', 'Гос. рег. уд., ₽', 'money'),
)


def _deal_calc_month_period():
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    period_label = '{} — {}'.format(
        month_start.strftime('%d.%m.%Y'),
        now.strftime('%d.%m.%Y'),
    )
    return month_start, now, period_label


_DEAL_SALE_TYPE_LABELS = {
    0: 'Бренд',
    1: 'Модель',
    2: 'Модификация',
    3: 'Комплектация',
}


def _resolve_deal_calc_sale_type(request, car=None):
    """По умолчанию — комплектация (3)."""
    try:
        sale_type = int(request.GET.get('sale_type', '3'))
    except (TypeError, ValueError):
        sale_type = 3
    sale_type = max(0, min(3, sale_type))
    if sale_type == 3 and car and not car.complectation_autoru_id:
        sale_type = 2 if car.modification_autoru_id else 1
    return sale_type


def _deal_calc_cumulative_qs_for_unit_name(unit_name, month_start, now, car=None, sale_type=3):
    from powerbi.models import Cumulative

    q = Cumulative.objects.filter(
        TipProdazhi='Розница',
        DataProdazhi__gte=month_start,
        DataProdazhi__lte=now,
        SebestoimostPoDokumentu__gt=0,
        PodrazdelenieDTs__icontains=unit_name,
    )
    if car:
        q = _apply_car_sale_type_filter(q, car, sale_type)
    return q


def _deal_calc_cumulative_qs_for_podrazdelenie(podrazdelenie, month_start, now, car=None, sale_type=3):
    from powerbi.models import Cumulative

    q = Cumulative.objects.filter(
        TipProdazhi='Розница',
        DataProdazhi__gte=month_start,
        DataProdazhi__lte=now,
        SebestoimostPoDokumentu__gt=0,
        PodrazdelenieDTs=podrazdelenie,
    )
    if car:
        q = _apply_car_sale_type_filter(q, car, sale_type)
    return q


def _deal_sales_metric_value(metrics, row_key):
    if row_key == 'sales_count':
        return metrics.get('udelka_count') or 0
    if row_key == 'vp_total':
        return metrics.get('cumulative_sum') or 0
    if row_key == 'vp_udelka':
        return metrics.get('udelka') or 0
    udelka = metrics.get('cumulative_sum_detail_udelka') or {}
    return udelka.get(row_key) or 0


def _build_deal_sales_comparison_table(car, current_unit_name, month_start, now, sale_type=3):
    columns = [{
        'name': current_unit_name,
        'is_current': True,
        'metrics': _cumulative_vp_metrics(
            _deal_calc_cumulative_qs_for_unit_name(
                current_unit_name, month_start, now, car=car, sale_type=sale_type,
            ),
        ),
    }]
    if car:
        for podrazdelenie in _brand_sales_podrazdeleniya(
            car,
            month_start,
            now,
            sale_type=sale_type,
            current_unit_name=current_unit_name,
        ):
            metrics = _cumulative_vp_metrics(
                _deal_calc_cumulative_qs_for_podrazdelenie(
                    podrazdelenie, month_start, now, car=car, sale_type=sale_type,
                ),
            )
            if not metrics.get('udelka_count'):
                continue
            columns.append({
                'name': podrazdelenie,
                'is_current': False,
                'metrics': metrics,
            })

    current_by_key = {
        row_key: _deal_sales_metric_value(columns[0]['metrics'], row_key)
        for row_key, _, _ in _DEAL_SALES_TABLE_ROWS
    }

    rows = []
    for row_key, label, fmt in _DEAL_SALES_TABLE_ROWS:
        current_val = current_by_key[row_key]
        cells = []
        for col in columns:
            val = _deal_sales_metric_value(col['metrics'], row_key)
            css = ''
            if not col['is_current']:
                if val > current_val:
                    css = 'table-success'
                elif val < current_val:
                    css = 'table-danger'
            cells.append({
                'value': val,
                'css': css,
                'is_current': col['is_current'],
            })
        rows.append({
            'key': row_key,
            'label': label,
            'fmt': fmt,
            'cells': cells,
        })

    return {
        'columns': [{'name': col['name'], 'is_current': col['is_current']} for col in columns],
        'rows': rows,
    }


def _deal_calc_unit_month_analytics(unit, car=None, sale_type=3):
    """ВП по подразделению за текущий месяц (розница, Cumulative)."""
    month_start, now, period_label = _deal_calc_month_period()

    vp_chart_empty = {
        'labels': [], 'zhelezo': [], 'dop': [], 'opfu': [], 'ti': [], 'sales': [], 'totals': [], 'averages': [],
    }
    empty_comparison = {'columns': [], 'rows': []}
    analytics = {
        'cumulative_sum': 0,
        'udelka': 0,
        'udelka_count': 0,
        'cumulative_sum_detail': _empty_cumulative_vp_detail(),
        'cumulative_sum_detail_percent': _empty_cumulative_vp_percent(),
        'cumulative_sum_detail_udelka': _empty_cumulative_vp_udelka(),
        'period_label': period_label,
        'unit_name': unit.name if unit else '',
        'brand_name': '',
        'sale_type': sale_type,
        'sale_type_label': _DEAL_SALE_TYPE_LABELS.get(sale_type, ''),
        'sales_comparison': empty_comparison,
        'vp_by_model': vp_chart_empty,
        'vp_by_model_json': json.dumps(vp_chart_empty, ensure_ascii=False),
    }
    if not unit or not unit.name:
        return analytics

    price_car_brand = _resolve_price_car_brand_for_car(car) if car else None
    if price_car_brand:
        analytics['brand_name'] = price_car_brand.name
    elif car and car.modification_autoru_id and car.modification_autoru.model.mark_id:
        analytics['brand_name'] = car.modification_autoru.model.mark.name

    q_unit = _deal_calc_cumulative_qs_for_unit_name(
        unit.name, month_start, now, car=car, sale_type=sale_type,
    )
    vp_metrics = _cumulative_vp_metrics(q_unit)
    analytics['cumulative_sum'] = vp_metrics['cumulative_sum']
    analytics['udelka'] = vp_metrics['udelka']
    analytics['udelka_count'] = vp_metrics['udelka_count']
    analytics['cumulative_sum_detail'] = vp_metrics['cumulative_sum_detail']
    analytics['cumulative_sum_detail_percent'] = vp_metrics['cumulative_sum_detail_percent']
    analytics['cumulative_sum_detail_udelka'] = vp_metrics['cumulative_sum_detail_udelka']
    analytics['sales_comparison'] = _build_deal_sales_comparison_table(
        car, unit.name, month_start, now, sale_type=sale_type,
    )

    vp_rows = list(
        q_unit.exclude(Model__isnull=True).exclude(Model='')
        .values('Model')
        .annotate(
            zhelezo=Coalesce(Sum('SummaMarzhiBezNDS'), Value(0.0), output_field=FloatField()),
            sum_rabot=Coalesce(Sum('SummaRabot'), Value(0.0), output_field=FloatField()),
            sum_shiny=Coalesce(Sum('ValovayaPribylZChShiny'), Value(0.0), output_field=FloatField()),
            sum_zch=Coalesce(Sum('ValovayaPribylZCh'), Value(0.0), output_field=FloatField()),
            sum_gosreg=Coalesce(Sum('SummaGosreg'), Value(0.0), output_field=FloatField()),
            opfu=Coalesce(Sum('VPOPFU'), Value(0.0), output_field=FloatField()),
            ti=Coalesce(Sum('SummaTreydInPoPlanu'), Value(0.0), output_field=FloatField()),
            sales=Coalesce(Count('VIN'), Value(0), output_field=IntegerField()),
        )
    )
    vp_items = []
    for row in vp_rows:
        model_name = (row['Model'] or '—').strip()
        zhelezo = float(row['zhelezo'] or 0)
        dop = (
            float(row['sum_rabot'] or 0) + float(row['sum_shiny'] or 0)
            + float(row['sum_zch'] or 0) + float(row['sum_gosreg'] or 0)
        )
        opfu = float(row['opfu'] or 0)
        ti = float(row['ti'] or 0)
        total = zhelezo + dop + opfu + ti
        sales_count = int(row['sales'] or 0)
        if sales_count > 0:
            zhelezo_avg = zhelezo / sales_count
            dop_avg = dop / sales_count
            opfu_avg = opfu / sales_count
            ti_avg = ti / sales_count
            average = total / sales_count
        else:
            zhelezo_avg = dop_avg = opfu_avg = ti_avg = average = 0
        vp_items.append({
            'label': model_name,
            'zhelezo': zhelezo_avg,
            'dop': dop_avg,
            'opfu': opfu_avg,
            'ti': ti_avg,
            'sales': sales_count,
            'total': total,
            'average': average,
        })
    vp_items.sort(key=lambda item: abs(item['average']), reverse=True)
    vp_chart = {
        'labels': [item['label'] for item in vp_items],
        'zhelezo': [item['zhelezo'] for item in vp_items],
        'dop': [item['dop'] for item in vp_items],
        'opfu': [item['opfu'] for item in vp_items],
        'ti': [item['ti'] for item in vp_items],
        'sales': [item['sales'] for item in vp_items],
        'totals': [item['total'] for item in vp_items],
        'averages': [item['average'] for item in vp_items],
    }
    analytics['vp_by_model'] = vp_chart
    analytics['vp_by_model_json'] = json.dumps(vp_chart, ensure_ascii=False)

    return analytics


def _deal_calc_stock_by_models(car, unit_id=None):
    """Новые автомобили в наличии по моделям бренда ценообразования (PriceCarBrand)."""
    empty = {'labels': [], 'values': [], 'total': 0, 'mark_name': ''}
    if not car or not car.modification_autoru_id:
        return empty

    brand = _resolve_price_car_brand_for_car(car)
    if brand:
        qs = _cars_qs_for_price_car_brand(brand).exclude(quantity=0).filter(is_new=True)
        mark_name = brand.name
    else:
        model = car.modification_autoru.model
        if not model or not model.mark_id:
            return empty
        mark_name = model.mark.name if model.mark_id else ''
        qs = RefCarsOrganization.objects.exclude(quantity=0).filter(
            is_new=True,
            modification_autoru__model__mark_id=model.mark_id,
        )

    if unit_id:
        qs = qs.filter(unit_id=unit_id)

    rows = list(
        qs.values('modification_autoru__model__name')
        .annotate(count=Count('id'))
        .order_by('-count', 'modification_autoru__model__name')
    )
    labels = [(row['modification_autoru__model__name'] or '—') for row in rows]
    values = [row['count'] for row in rows]
    return {
        'labels': labels,
        'values': values,
        'total': sum(values),
        'mark_name': mark_name,
    }


@login_required
def deal_calculation(request):
    
    if not request.user.profiles.price_car_new and not request.user.profiles.price_car_new_settings: 
        params = {
            'type': 'home',
            'request': request,
        }
        return render(request, 'errors/403.html', {'params': params})
    
    try:
        from analytics.models import TradeInFunnel
    except ImportError:
        TradeInFunnel = None
    
    params = {
        'type': 'deal_calculation',
        'nav_selected': 4,
        'request': request,
    }
    
    # cumulative_data = car.cumulative_data()
    # Получаем выбранный автомобиль из диспозиции
    
    car_slug        = request.GET.get('car', '')
    calculation     = request.GET.get('calculation', '')
    calculation_id  = ''
    if calculation == '':
        calculation_id = calculation
    else:
        calculation_id = None

    car = RefCarsOrganization.objects.get(slug=car_slug)

    if request.method == 'POST':

        new_object =  CarCalculations()
        new_object.car = car
        new_object.user = request.user
        new_object.comment = request.POST.get('comment', '')

        new_object.discount        = int(request.POST.get('custom_discount', '0'))
        new_object.price           = int(request.POST.get('car_price_and_dop', '0'))
        new_object.custom_opfu     = int(request.POST.get('custom_opfu', '0'))
        new_object.custom_tradein  = int(request.POST.get('custom_tradein', '0'))
        new_object.custom_wheels   = int(request.POST.get('custom_wheels', '0'))
        new_object.custom_grz      = int(request.POST.get('custom_grz', '0'))
        new_object.custom_work     = int(request.POST.get('custom_work', '0'))
        new_object.custom_product  = int(request.POST.get('custom_product', '0'))
        apply_km_raschet_to_calculation(new_object, car)
        new_object.save()
        
        return HttpResponseRedirect('/cars/deal/calculation/' + str(new_object.pk) + '/')        

    from documents.models import DocZN
    zn_list = []
    info_dop = None
    if car.vin:
        zn_list = DocZN.objects.filter(cars__vin=car.vin, typeRemont__dop=True).select_related('typeRemont', 'readyStatus', 'unit').order_by('-dataTime')[:200]
        
        info_dop = zn_list.aggregate(
                count=Count("id"),
                sum_amount=Sum("amount")  
            )
        
    car_price_and_dop = car.cost_price
    if info_dop != None and info_dop['sum_amount'] != None:
         car_price_and_dop = car_price_and_dop + info_dop['sum_amount']

    # Расчет итоговой суммы
    total_amount = 0
    car_price = 0
    promotions_discount = 0
    bu_wheels_price = 0
    opfu_services_total = 0
    
    selected_opfu_ids = request.GET.getlist('opfu_services')
    if not selected_opfu_ids:
        selected_opfu_ids = []
    selected_opfu_services = []
    if selected_opfu_ids:
        selected_opfu_services = RefService.objects.filter(id__in=selected_opfu_ids)
        # Здесь можно добавить расчет стоимости услуг
        # Пока просто добавляем заглушку
        opfu_services_total = len(selected_opfu_services) * 1000  # Заглушка
    
    total_amount += opfu_services_total
    total_amount -= promotions_discount
    total_amount -= bu_wheels_price
    
    params.update({
        'car': car,
        'car_price_and_dop' :  car_price_and_dop,
        'cumulative_data' : car.cumulative_data(),
        'selected_opfu_services': selected_opfu_services,
        'selected_opfu_ids': [str(sid) for sid in selected_opfu_ids],  # Для использования в шаблоне
        'car_price': car_price,
        'promotions_discount': promotions_discount,
        'bu_wheels_price': bu_wheels_price,
        'opfu_services_total': opfu_services_total,
        'total_amount': total_amount
    })
    
    return render(request, 'avtosalon/deal_calculation.html', {'params': params})


@login_required
def deal_calculation_doc(request, id):
    
    calc    = CarCalculations.objects.select_related(
        'rlk', 'rlk__staff', 'rlk__unit',
        'unit', 'car', 'car__unit',
        'car__modification_autoru', 'car__modification_autoru__model', 'car__modification_autoru__model__mark',
        'car__complectation_autoru', 'car__status', 'car__status_availability',
        'director_approve_user', 'director_approve_user__profiles',
        'uk_approve_user', 'uk_approve_user__profiles',
        'uk_approval_reference',
        'uk_approval_reference__calculation',
        'uk_approval_reference__approved_by',
    ).get(pk=id)

    if not user_can_access_deal_calculation_doc(request.user, calc):
        params = {
            'type': 'home',
            'request': request,
        }
        return render(request, 'errors/403.html', {'params': params})
    
    try:
        from analytics.models import TradeInFunnel
    except ImportError:
        TradeInFunnel = None
    
    params = {
        'type': 'deal_calculation',
        'nav_selected': 4,
        'request': request,
    }
    
    car     = calc.car
    cumulative_data = None
    if car:
        try:
            cumulative_data = car.cumulative_data()
        except Exception:
            cumulative_data = None
        # Не перезаписываем снимок итога по формуле, если КП уже в согласовании /
        # решение принято. Иначе отчёт и карточка расходятся с моментом согласования.
        from avtosalon.deal_calc_approval import (
            is_km_rule_frozen,
            snapshot_km_rule_total,
        )
        if (not is_km_rule_frozen(calc)) or calc.km_raschet is None:
            snapshot_km_rule_total(calc, cumulative_data)
            if calc.km_raschet is not None:
                calc.save(update_fields=['km_raschet'])
    prior_uk_approved = try_approve_by_prior_uk_threshold(
        calc, send_chat=True, send_to_1c=True,
    )
    if not prior_uk_approved:
        try_auto_approve_calculation(
            calc, send_chat=True, cumulative_data=cumulative_data,
        )
        if getattr(calc, '_prior_uk_approval_revoked', False):
            from avtosalon.deal_calc_approval import (
                send_calculation_soglasovanie_result_to_1c,
            )
            send_calculation_soglasovanie_result_to_1c(calc, force=True)
    cumulative_data = cumulative_data or {}
    from prices_car.km_breakdown import build_km_calculation_breakdown
    if car:
        km_breakdown = build_km_calculation_breakdown(
            car,
            calc=calc,
            show_reference_methods=user_has_deal_calc_uk_access(request.user),
        )
    else:
        km_breakdown = {'available': False}

    if request.method == 'POST':
        if "send_1C" in request.POST:
            from avtosalon.deal_calc_approval import send_calculation_soglasovanie_result_to_1c
            send_calculation_soglasovanie_result_to_1c(calc)
            return HttpResponseRedirect('/cars/deal/calculation/' + str(calc.pk) + '/')

        if 'recalculate_km' in request.POST:
            from django.contrib import messages
            ok, msg = recalculate_deal_calculation_km(calc, request.user)
            if ok:
                messages.success(request, msg)
            else:
                messages.error(request, msg)
            return HttpResponseRedirect('/cars/deal/calculation/' + str(calc.pk) + '/')
        
        approval_response = handle_deal_calc_approval_post(
            request, calc, cumulative_data,
        )
        if approval_response is not None:
            return approval_response

        new_object = calc
        new_object.car = car
        new_object.user = request.user
        new_object.comment = request.POST.get('comment', '')

        new_object.discount        = int(request.POST.get('custom_discount', '0'))
        new_object.price           = int(request.POST.get('car_price_and_dop', '0'))
        new_object.custom_opfu     = int(request.POST.get('custom_opfu', '0'))
        new_object.custom_tradein  = int(request.POST.get('custom_tradein', '0'))
        new_object.custom_wheels   = int(request.POST.get('custom_wheels', '0'))
        new_object.custom_grz      = int(request.POST.get('custom_grz', '0'))
        new_object.custom_work     = int(request.POST.get('custom_work', '0'))
        new_object.custom_product  = int(request.POST.get('custom_product', '0'))
        apply_km_raschet_to_calculation(new_object, car)
        new_object.save()
        
        return HttpResponseRedirect('/cars/deal/calculation/' + str(new_object.pk) + '/')
    
    from documents.models import DocZN
    zn_list = []
    info_dop = None
    dop = 0
    if car.vin:
        zn_list = DocZN.objects.filter(cars__vin=car.vin, typeRemont__dop=True).select_related('typeRemont', 'readyStatus', 'unit').order_by('-dataTime')[:200]
        
        info_dop = zn_list.aggregate(
                count=Count("id"),
                sum_amount=Sum("amount")  
            )
        
    car_price_and_dop = car.cost_price
    if info_dop != None and info_dop['sum_amount'] != None:
         car_price_and_dop = car_price_and_dop + info_dop['sum_amount']
         dop = info_dop['sum_amount']

    
    # Расчет итоговой суммы
    total_amount = 0
    car_price = 0
    promotions_discount = 0
    bu_wheels_price = 0
    opfu_services_total = 0
    
    selected_opfu_ids = request.GET.getlist('opfu_services')
    if not selected_opfu_ids:
        selected_opfu_ids = []
    selected_opfu_services = []
    if selected_opfu_ids:
        selected_opfu_services = RefService.objects.filter(id__in=selected_opfu_ids)
        # Здесь можно добавить расчет стоимости услуг
        # Пока просто добавляем заглушку
        opfu_services_total = len(selected_opfu_services) * 1000  # Заглушка
    
    total_amount += opfu_services_total
    total_amount -= promotions_discount
    total_amount -= bu_wheels_price
    actions = RefCarsOrganizationAction.objects.filter(car = car)
    
    action_sum = RefCarsOrganizationAction.objects.filter(car = car).aggregate(
                sum_amount=Sum("amount")  
            )['sum_amount']

    unit_id = calc.unit_id or (car.unit_id if car else None)
    stock_chart_unit = _deal_calc_stock_by_models(car, unit_id=unit_id)
    stock_chart_all = _deal_calc_stock_by_models(car, unit_id=None)
    stock_chart_unit_name = ''
    if calc.unit_id:
        stock_chart_unit_name = calc.unit.name
    elif car and car.unit_id:
        stock_chart_unit_name = car.unit.name

    analytics_unit = calc.unit or (car.unit if car else None)
    sale_type = _resolve_deal_calc_sale_type(request, car)
    params_analytics = _deal_calc_unit_month_analytics(analytics_unit, car=car, sale_type=sale_type)

    rlk_calculations = []
    active_rlk_calculation = None
    if calc.rlk_id:
        rlk_calculations = list(
            CarCalculations.objects.filter(rlk_id=calc.rlk_id)
            .select_related('car', 'unit', 'author', 'staff')
            .order_by('-date', '-pk')
        )
        if calc.active:
            active_rlk_calculation = calc
        else:
            active_rlk_calculation = next(
                (c for c in rlk_calculations if c.active),
                None,
            )
    
    params.update({
        'car'               : car,
        'calc'              : calc,
        'rlk_calculations'  : rlk_calculations,
        'active_rlk_calculation': active_rlk_calculation,
        'dop'               : dop,
        'car_price_and_dop' : car_price_and_dop,
        'actions'           : actions,
        'action_sum'        : action_sum,
        'analytics': params_analytics,
        'stock_chart_unit': stock_chart_unit,
        'stock_chart_all': stock_chart_all,
        'stock_chart_unit_name': stock_chart_unit_name,
        'stock_chart_unit_json': json.dumps(stock_chart_unit, ensure_ascii=False),
        'stock_chart_all_json': json.dumps(stock_chart_all, ensure_ascii=False),
        'cumulative_data' : cumulative_data,
        'km_breakdown': km_breakdown,
        'selected_opfu_services': selected_opfu_services,
        'selected_opfu_ids': [str(sid) for sid in selected_opfu_ids],  # Для использования в шаблоне
        'car_price': car_price,
        'promotions_discount': promotions_discount,
        'bu_wheels_price': bu_wheels_price,
        'opfu_services_total': opfu_services_total,
        'total_amount': total_amount,
        'sale_type': sale_type,
    })
    params.update(build_deal_calc_approval_context(request.user, calc, cumulative_data))

    from avtosalon.client_suggestions import deal_needs_client_suggestions
    params['client_suggestions_enabled'] = deal_needs_client_suggestions(calc, cumulative_data, car)

    if calc.rlk_id and user_can_access_rlk_op_chat(request.user, calc.rlk):
        params.update(build_rlk_chat_params(request, calc.rlk))
    
    return render(request, 'avtosalon/deal_calculation.html', {'params': params})


def _get_deal_calc_for_suggestions(request, calc_id):
    calc = CarCalculations.objects.select_related(
        'unit', 'car', 'car__unit',
        'car__modification_autoru', 'car__modification_autoru__model',
        'car__complectation_autoru',
    ).get(pk=calc_id)
    if not user_can_access_deal_calculation_doc(request.user, calc):
        return None, JsonResponse({'ok': False, 'error': 'forbidden'}, status=403)
    return calc, None


@login_required
def deal_calc_client_suggestions_count(request, id):
    from avtosalon.client_suggestions import (
        count_client_suggestions,
        deal_needs_client_suggestions,
        get_reference_km_for_car,
    )

    calc, denied = _get_deal_calc_for_suggestions(request, id)
    if denied is not None:
        return denied

    car = calc.car
    cumulative_data = car.cumulative_data() if car else {}
    if not deal_needs_client_suggestions(calc, cumulative_data, car):
        return JsonResponse({'ok': True, 'show': False, 'count': 0})

    unit_id = calc.unit_id or (car.unit_id if car else None)
    reference_km = get_reference_km_for_car(car)
    if reference_km is None:
        return JsonResponse({'ok': True, 'show': False, 'count': 0})
    from avtosalon.client_suggestions import brand_allows_dc_transfers
    if not unit_id and not brand_allows_dc_transfers(car):
        return JsonResponse({'ok': True, 'show': False, 'count': 0})

    count = count_client_suggestions(car, unit_id, reference_km)
    return JsonResponse({
        'ok': True,
        'show': count > 0,
        'count': count,
        'reference_km': reference_km,
    })


@login_required
def deal_calc_client_suggestions_list(request, id):
    from avtosalon.client_suggestions import (
        deal_needs_client_suggestions,
        get_reference_km_for_car,
        list_client_suggestions,
    )

    calc, denied = _get_deal_calc_for_suggestions(request, id)
    if denied is not None:
        return denied

    car = calc.car
    cumulative_data = car.cumulative_data() if car else {}
    if not deal_needs_client_suggestions(calc, cumulative_data, car):
        return JsonResponse({'ok': False, 'error': 'not_applicable'}, status=400)

    unit_id = calc.unit_id or (car.unit_id if car else None)
    reference_km = get_reference_km_for_car(car)
    if reference_km is None:
        return JsonResponse({'ok': False, 'error': 'no_reference_km'}, status=400)
    from avtosalon.client_suggestions import brand_allows_dc_transfers
    if not unit_id and not brand_allows_dc_transfers(car):
        return JsonResponse({'ok': False, 'error': 'no_unit'}, status=400)

    data = list_client_suggestions(car, unit_id, reference_km, calc.kvp)
    return JsonResponse({'ok': True, **data})


@csrf_exempt
def rlk_op_chat(request, rlk_id=None, staff_uin=None, rlk_uin=None):
    """
    Чат по рабочему листу ОП (для 1С и прямой ссылки).
    1С: /cars/deal/rlk-chat/1c/<uin>/<rlk_uin>/ — отдельная сессия, без login().
    Портал: обычная авторизация.
    """
    from chats.models import ChatMessage
    from django.shortcuts import redirect

    ctx = resolve_rlk_chat_access(request, rlk_id=rlk_id, staff_uin=staff_uin, rlk_uin=rlk_uin)
    if ctx['error'] == 'uin_auth':
        return render(request, 'chats/rlk_chat_uin_auth_error.html')
    if ctx['error'] == 'login':
        return redirect_to_login(request.get_full_path())
    if ctx['error'] == 'not_found':
        raise Http404
    if ctx['error'] == 'access':
        return render(request, 'chats/rlk_chat_access_denied.html')

    chat_user = ctx['chat_user']
    rlk = ctx['rlk']
    staff_uin = ctx['staff_uin']
    rlk_uin = ctx['rlk_uin']
    from_1c = ctx['from_1c']
    chat_params = ctx['chat_params']

    if request.method == 'POST':
        message = (request.POST.get('message') or '').strip()
        if message:
            ChatMessage.objects.create(
                user=chat_user,
                chat=chat_params['chat'],
                content=message,
            )
            broadcast_rlk_chat_ws_message(chat_params['chat'], chat_user, message)
        return redirect(build_rlk_chat_page_url(staff_uin, rlk_uin, rlk_id=rlk.pk))

    messages = chat_params['messages']
    _, last_message_id = serialize_rlk_chat_messages(messages, chat_user.pk)

    params = {
        'type': 'rlk_op_chat',
        'request': request,
        'staff_uin': staff_uin,
        'rlk_uin': rlk_uin,
        'chat_page_url': build_rlk_chat_page_url(staff_uin, rlk_uin, rlk_id=rlk.pk),
        'poll_url': build_rlk_chat_poll_url(),
        'send_url': build_rlk_chat_send_url(),
        'last_message_id': last_message_id,
        'from_1c': from_1c,
    }
    params.update(chat_params)
    return render(request, 'chats/chat_rlk_op_page.html', {'params': params})


@csrf_exempt
def rlk_op_chat_send(request):
    """Отправка сообщения из 1С через XHR (без перезагрузки страницы)."""
    from chats.models import ChatMessage
    from django.http import JsonResponse

    if request.method != 'POST':
        return JsonResponse({'error': 'method'}, status=405)

    ctx = resolve_rlk_chat_poll(request)
    if ctx.get('error'):
        return JsonResponse({'error': ctx['error']}, status=403)

    message = (request.POST.get('message') or '').strip()
    if not message:
        return JsonResponse({'error': 'empty'}, status=400)

    from chats.models import Chat

    msg = ChatMessage.objects.create(
        user=ctx['chat_user'],
        chat_id=ctx['chat_id'],
        content=message,
    )
    msg.user = ctx['chat_user']
    chat = Chat.objects.filter(pk=ctx['chat_id']).only('pk', 'slug').first()
    if chat:
        broadcast_rlk_chat_ws_message(chat, ctx['chat_user'], message)
    items, last_id = serialize_rlk_chat_messages([msg], ctx['chat_user'].pk)
    return JsonResponse({
        'ok': True,
        'message': items[0] if items else None,
        'last_id': last_id,
    })


@csrf_exempt
def rlk_op_chat_poll(request):
    """HTTP-polling новых сообщений для 1С (без WebSocket)."""
    from django.http import JsonResponse

    ctx = resolve_rlk_chat_poll(request)
    if ctx.get('error'):
        return JsonResponse({'error': ctx['error']}, status=403)

    try:
        after_id = int(request.GET.get('after_id') or 0)
    except (TypeError, ValueError):
        after_id = 0

    items, last_id = fetch_new_rlk_chat_messages(
        ctx['chat_id'], after_id, ctx['chat_user'].pk,
    )
    return JsonResponse({'messages': items, 'last_id': last_id})


@login_required
def deal_calculation_old(request):
    
    try:
        from analytics.models import TradeInFunnel
    except ImportError:
        TradeInFunnel = None
    
    params = {
        'type': 'deal_calculation',
        'nav_selected': 4,
        'request': request,
    }
    
    # cumulative_data = car.cumulative_data()
    # Получаем выбранный автомобиль из диспозиции
    
    car_slug        = request.GET.get('car', '')
    calculation     = request.GET.get('calculation', '')
    calculation_id  = ''
    if calculation == '':
        calculation_id = calculation
    else:
        calculation_id = None

    car = RefCarsOrganization.objects.select_related(
                'modification_autoru__model__mark',
                'status',
                'unit',
                'store'
            ).get(slug=car_slug).last()

    selected_car = None
    if car_slug:
        try:
            selected_car = RefCarsOrganization.objects.select_related(
                'modification_autoru__model__mark',
                'status',
                'unit',
                'store'
            ).get(slug=car_slug)
        except RefCarsOrganization.DoesNotExist:
            pass
    
    # Получаем выбранную интерактивную оценку
    estimation_id = request.GET.get('estimation_id', '')
    selected_estimation = None
    estimation_price = 0
    if estimation_id:
        try:
            selected_estimation = RegInteractivOcenka.objects.select_related(
                'rlk',
                'rlk__unit',
                'rlk__unit_dc'
            ).get(pk=estimation_id)
            
            # Получаем цену из TradeInFunnel
            if selected_estimation.rlk and TradeInFunnel:
                try:
                    funnel = TradeInFunnel.objects.filter(rlk_id=selected_estimation.rlk.id).first()
                    if funnel:
                        # Приоритет: price_after > price_before > price_remote
                        if funnel.price_after and funnel.price_after > 0:
                            estimation_price = float(funnel.price_after)
                        elif funnel.price_before and funnel.price_before > 0:
                            estimation_price = float(funnel.price_before)
                        elif funnel.price_remote and funnel.price_remote > 0:
                            estimation_price = float(funnel.price_remote)
                except Exception as e:
                    print(f"Error getting estimation price: {e}")
                    pass
        except RegInteractivOcenka.DoesNotExist:
            pass
    
    # Получаем список автомобилей из диспозиции для выбора
    cars_list = RefCarsOrganization.objects.filter(
        quantity__gt=0
    ).select_related(
        'modification_autoru__model__mark',
        'status',
        'unit'
    ).order_by('-date_create')[:100]
    
    # Получаем список интерактивных оценок для выбора (связанных с DocRLK)
    estimations_list = RegInteractivOcenka.objects.filter(
        rlk__isnull=False
    ).select_related(
        'rlk',
        'rlk__unit',
        'rlk__unit_dc'
    ).order_by('-start_estimation')[:100]
    
    # Получаем список услуг ОПФУ
    opfu_services = RefService.objects.all().order_by('name')[:200]
    
    # Обработка POST запроса для сохранения калькуляции
    if request.method == 'POST':
        # Здесь будет логика сохранения калькуляции
        # Пока просто редирект
        pass
    
    # Расчет итоговой суммы
    total_amount = 0
    car_price = 0
    promotions_discount = 0
    bu_wheels_price = 0
    opfu_services_total = 0
    
    if selected_car:
        car_price = selected_car.price or 0
        total_amount += car_price
    
    # Если оценка используется в счет, вычитаем её из суммы
    use_estimation_in_payment = request.GET.get('use_estimation_in_payment') == '1'
    if use_estimation_in_payment and estimation_price > 0:
        total_amount -= estimation_price
    
    # Получаем выбранные услуги ОПФУ
    selected_opfu_ids = request.GET.getlist('opfu_services')
    if not selected_opfu_ids:
        selected_opfu_ids = []
    selected_opfu_services = []
    if selected_opfu_ids:
        selected_opfu_services = RefService.objects.filter(id__in=selected_opfu_ids)
        # Здесь можно добавить расчет стоимости услуг
        # Пока просто добавляем заглушку
        opfu_services_total = len(selected_opfu_services) * 1000  # Заглушка
    
    total_amount += opfu_services_total
    total_amount -= promotions_discount
    total_amount -= bu_wheels_price
    
    params.update({
        'selected_car': selected_car,
        'selected_estimation': selected_estimation,
        'cars_list': cars_list,
        'estimations_list': estimations_list,
        'opfu_services': opfu_services,
        'selected_opfu_services': selected_opfu_services,
        'selected_opfu_ids': [str(sid) for sid in selected_opfu_ids],  # Для использования в шаблоне
        'car_price': car_price,
        'estimation_price': estimation_price,
        'promotions_discount': promotions_discount,
        'bu_wheels_price': bu_wheels_price,
        'opfu_services_total': opfu_services_total,
        'total_amount': total_amount,
        'use_estimation_in_payment': use_estimation_in_payment,
    })
    
    return render(request, 'avtosalon/deal_calculation.html', {'params': params})



# ========== Директор ГК: склад и чаты по автомобилям ==========

@login_required
def gk_director_dashboard(request):
    """Страница директора ГК: все автомобили в наличии, фильтры, пагинация, чат по автомобилям."""
    open_tasks_filter = Q(tasks__status='new') | Q(tasks__status='in_progress')
    # Подзапрос: чат по машине (slug='car_'+car.slug)
    chat_sub = Chat.objects.filter(slug=Concat(Value('car_'), OuterRef('slug'))).values('pk')[:1]
    has_chat_messages = Exists(ChatMessage.objects.filter(chat_id=Subquery(chat_sub)))

    cars_qs = (
        RefCarsOrganization.objects.filter(quantity__gt=0)
        .select_related(
            'unit', 'status', 'modification_autoru', 'modification_autoru__model',
            'modification_autoru__model__mark', 'complectation_autoru',
        )
        .prefetch_related(Prefetch('refcarsorganizationfiles_set', queryset=RefCarsOrganizationFiles.objects.order_by('-main')))
        .annotate(
            open_tasks_count=Coalesce(
                Count('tasks', filter=open_tasks_filter, distinct=True),
                Value(0),
                output_field=IntegerField(),
            ),
            has_chat_messages=has_chat_messages,
        )
        .order_by('unit__name', '-date_create')
    )

    # Фильтр: состояние Все / Новые / С пробегом
    status_condition = request.GET.get('status_condition', 'all')
    if status_condition == 'new':
        cars_qs = cars_qs.filter(is_new=True)
    elif status_condition == 'used':
        cars_qs = cars_qs.filter(is_new=False)

    # Поиск по ВИН (основной и дополнительный) и/или номеру кузова (поиск по всем полям)
    vin = request.GET.get('vin', '').strip()
    if vin:
        cars_qs = cars_qs.filter(Q(vin__icontains=vin) | Q(vin2__icontains=vin))
    search_fields = request.GET.get('search_fields', '').strip()
    if search_fields:
        cars_qs = cars_qs.filter(search_fields__icontains=search_fields)

    # Подразделения (множественный выбор)
    unit_ids = request.GET.getlist('unit[]')
    if unit_ids:
        try:
            uid_list = [int(x) for x in unit_ids if x]
            if uid_list:
                cars_qs = cars_qs.filter(unit_id__in=uid_list)
        except ValueError:
            pass

    # Марки и модели (множественный выбор)
    mark_ids = request.GET.getlist('mark[]')
    if mark_ids:
        try:
            mid_list = [int(x) for x in mark_ids if x]
            if mid_list:
                cars_qs = cars_qs.filter(modification_autoru__model__mark_id__in=mid_list)
        except ValueError:
            pass
    model_ids = request.GET.getlist('model[]')
    if model_ids:
        try:
            mod_list = [int(x) for x in model_ids if x]
            if mod_list:
                cars_qs = cars_qs.filter(modification_autoru__model_id__in=mod_list)
        except ValueError:
            pass

    # Задачи: все / с открытыми / без задач
    tasks_filter = request.GET.get('tasks_filter', 'all')
    if tasks_filter == 'with_open':
        cars_qs = cars_qs.filter(tasks__status__in=['new', 'in_progress']).distinct()
    elif tasks_filter == 'no_tasks':
        cars_qs = cars_qs.annotate(total_tasks=Count('tasks', distinct=True)).filter(total_tasks=0)

    # Минимальный КМ: все / с минимальным км / без минимального км
    min_km_filter = request.GET.get('min_km_filter', 'all')
    if min_km_filter == 'with':
        cars_qs = cars_qs.filter(min_km__isnull=False).exclude(min_km=0)
    elif min_km_filter == 'without':
        cars_qs = cars_qs.filter(Q(min_km__isnull=True) | Q(min_km=0))

    # Сообщения в чате: все / с сообщениями / без
    chat_filter = request.GET.get('chat_filter', 'all')
    if chat_filter == 'with_messages':
        cars_qs = cars_qs.filter(has_chat_messages=True)
    elif chat_filter == 'no_messages':
        cars_qs = cars_qs.filter(has_chat_messages=False)

    # Цена от/до
    price_start = request.GET.get('price_start', '')
    if price_start:
        try:
            cars_qs = cars_qs.filter(price__gte=int(float(price_start)))
        except ValueError:
            pass
    price_end = request.GET.get('price_end', '')
    if price_end:
        try:
            cars_qs = cars_qs.filter(price__lte=int(float(price_end)))
        except ValueError:
            pass

    # Резерв: все / в резерве / без резерва
    reserve_filter = request.GET.get('reserve_filter', 'all')
    if reserve_filter == 'in_reserve':
        cars_qs = cars_qs.filter(reserve__gt=0)
    elif reserve_filter == 'no_reserve':
        cars_qs = cars_qs.filter(Q(reserve=0) | Q(reserve__isnull=True))

    # Пагинация: 10, 25, 50, 100 (по умолчанию 25)
    per_page_options = [10, 25, 50, 100]
    try:
        per_page = int(request.GET.get('per_page', 25))
        if per_page not in per_page_options:
            per_page = 25
    except ValueError:
        per_page = 25

    total_count = cars_qs.count()
    paginator = Paginator(cars_qs, per_page)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    # Списки для фильтров (подразделения, марки, модели)
    units_list = RefUnit.objects.filter(buauto=True).only('id', 'name').order_by('name')
    marks_list = AutoruMark.objects.only('id', 'name').order_by('name')
    models_list = AutoruModel.objects.select_related('mark').only('id', 'name', 'mark').order_by('name')
    if mark_ids:
        try:
            mid_list = [int(x) for x in mark_ids if x]
            if mid_list:
                models_list = models_list.filter(mark_id__in=mid_list)
        except ValueError:
            pass

    # ID для сохранения выбора в форме
    unit_ids_list = [int(x) for x in unit_ids if x] if unit_ids else []
    mark_ids_list = [int(x) for x in mark_ids if x] if mark_ids else []
    model_ids_list = [int(x) for x in model_ids if x] if model_ids else []

    filtr = {
        'status_condition': status_condition,
        'vin': vin,
        'search_fields': search_fields,
        'tasks_filter': tasks_filter,
        'min_km_filter': min_km_filter,
        'chat_filter': chat_filter,
        'reserve_filter': reserve_filter,
        'price_start': price_start,
        'price_end': price_end,
        'per_page': per_page,
    }

    # Query string без page для ссылок пагинации
    get_copy = request.GET.copy()
    if 'page' in get_copy:
        get_copy.pop('page')
    query_without_page = get_copy.urlencode()

    # Открыта из раздела «Настройки ценообразования новых»
    from_prices_car = request.resolver_match.app_name == 'prices_car'
    params = {
        'from_prices_car': from_prices_car,
        'page_obj': page_obj,
        'paginator': paginator,
        'total_count': total_count,
        'user': request.user,
        'chat_list_cars_url': '/cars/js/get_chats_list_cars/',
        'selected': {
            'units': units_list,
            'marks': marks_list,
            'models': models_list,
        },
        'filtr': filtr,
        'unit_ids_list': unit_ids_list,
        'mark_ids_list': mark_ids_list,
        'model_ids_list': model_ids_list,
        'per_page_options': per_page_options,
        'query_without_page': query_without_page,
    }
    return render(request, 'avtosalon/gk_director_dashboard.html', {'params': params})


@login_required
def get_chats_list_cars(request):
    """API: список чатов по автомобилям (slug содержит 'car'), для обновления блока чатов на странице директора ГК."""
    from django.db.models import Max
    # Чаты car_* с последним сообщением и данными авто (по Chat.name = car.slug)
    subq_msg_date = Subquery(
        ChatMessage.objects.filter(chat_id=OuterRef('pk'))
        .order_by('-date')
        .values('date')[:1]
    )
    subq_msg_content = Subquery(
        ChatMessage.objects.filter(chat_id=OuterRef('pk'))
        .order_by('-date')
        .values('content')[:1]
    )
    subq_msg_user = Subquery(
        ChatMessage.objects.filter(chat_id=OuterRef('pk'))
        .order_by('-date')
        .values('user__profiles__eco_name')[:1]
    )
    # Данные авто: RefCarsOrganization.slug = Chat.name
    car_unit = RefCarsOrganization.objects.filter(slug=OuterRef('name')).values('unit__name')[:1]
    car_vin = RefCarsOrganization.objects.filter(slug=OuterRef('name')).values('vin')[:1]
    car_mark = RefCarsOrganization.objects.filter(slug=OuterRef('name')).values('modification_autoru__model__mark__name')[:1]
    car_model = RefCarsOrganization.objects.filter(slug=OuterRef('name')).values('modification_autoru__model__name')[:1]
    car_mod = RefCarsOrganization.objects.filter(slug=OuterRef('name')).values('modification_autoru__name')[:1]
    chats = (
        Chat.objects.filter(slug__startswith='car_')
        .annotate(max_date=subq_msg_date, content=subq_msg_content, user_name = subq_msg_user)
        .annotate(
            rlk_unit=Subquery(car_unit),
            vin=Subquery(car_vin),
            mark=Subquery(car_mark),
            model=Subquery(car_model),
            modification=Subquery(car_mod),
        )
        .exclude(max_date__isnull=True)
        .order_by('-max_date')[:100]
    )
    result = []
    for c in chats:
        result.append({
            'pk': c.pk,
            'name': '/cars/{}/'.format(c.name or ''),
            'slug': c.slug or '',
            'rlk_unit': c.rlk_unit if hasattr(c, 'rlk_unit') else None,
            'rlk_unit_dc': None,
            'vin': c.vin or '',
            'mark': c.mark or '',
            'model': c.model or '',
            'modification': c.modification or '',
            'content': (c.content or '')[:200] if c.content else '',
            'user_name': (c.user_name or '')[:200] if c.user_name else '',
            'max_date': c.max_date.strftime('%Y-%m-%dT%H:%M:%S') if c.max_date else '',
        })
    return JsonResponse(result, safe=False, status=status.HTTP_200_OK)


# ========== Управление задачами по автомобилям ==========

@login_required
def car_tasks_list(request, car_id=None):
    """Список задач по автомобилю или всех задач"""
    from django.core.paginator import Paginator
    
    tasks = RegCarsOrganizationTask.objects.select_related('car', 'staff_created', 'staff_assignee').prefetch_related('comments')
    
    # Фильтры
    status_filter = request.GET.get('status', '')
    assignee_id = request.GET.get('assignee', '')
    unit_id = request.GET.get('unit', '')
    
    if car_id:
        tasks = tasks.filter(car_id=car_id)
    
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    if assignee_id:
        tasks = tasks.filter(staff_assignee_id=assignee_id)
    
    if unit_id:
        tasks = tasks.filter(car__unit_id=unit_id)
    
    # Аннотации для подсчета комментариев
    tasks = tasks.annotate(
        comments_count=Count('comments', filter=Q(comments__is_deleted=False))
    )
    
    # Пагинация
    page_number = request.GET.get('page', 1)
    paginator = Paginator(tasks.order_by('-date_created'), 25)
    page_obj = paginator.get_page(page_number)
    
    # Для фильтров
    from django.contrib.auth.models import User
    users = User.objects.filter(is_active=True).order_by('username')
    units = RefUnit.objects.all().order_by('name')
    
    params = {
        'page_obj': page_obj,
        'car_id': car_id,
        'users': users,
        'units': units,
        'filters': {
            'status': status_filter,
            'assignee': assignee_id,
            'unit': unit_id,
        }
    }
    
    return render(request, 'avtosalon/car_tasks_list.html', {'params': params})


@login_required
def car_task_create(request, car_id):
    """Создание задачи по автомобилю"""
    car = get_object_or_404(RefCarsOrganization, pk=car_id)
    
    if request.method == 'POST':
        title = request.POST.get('title', '')
        description = request.POST.get('description', '')
        assignee_id = request.POST.get('assignee', '')
        
        task = RegCarsOrganizationTask.objects.create(
            car=car,
            staff_created=request.user,
            title=title,
            description=description,
            status='new',
            date_created=timezone.now()
        )
        
        if assignee_id:
            try:
                assignee = User.objects.get(pk=assignee_id)
                task.staff_assignee = assignee
                task.save()
            except:
                pass
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'task_id': task.id})
        
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', f'/cars/{car.slug}/'))
    
    # GET запрос - форма создания
    from django.contrib.auth.models import User
    users = User.objects.filter(is_active=True).order_by('username')
    
    params = {
        'car': car,
        'users': users,
    }
    
    return render(request, 'avtosalon/car_task_create.html', {'params': params})


@login_required
def car_task_detail(request, task_id):
    """Детали задачи по автомобилю"""
    task = get_object_or_404(RegCarsOrganizationTask.objects.select_related('car', 'staff_created', 'staff_assignee').prefetch_related('comments__staff', 'files__staff'), pk=task_id)
    
    # Комментарии
    comments = task.comments.filter(is_deleted=False).order_by('date_created')
    
    # Файлы
    files = task.files.filter(is_deleted=False).order_by('-date_created')
    
    params = {
        'task': task,
        'comments': comments,
        'files': files,
    }
    
    return render(request, 'avtosalon/car_task_detail.html', {'params': params})


@login_required
def car_task_take(request, task_id):
    """Принятие задачи в работу"""
    task = get_object_or_404(RegCarsOrganizationTask, pk=task_id)
    
    if task.status != 'new':
        return JsonResponse({'success': False, 'error': 'Задача уже в работе или выполнена'}, status=400)
    
    task.staff_assignee = request.user
    task.status = 'in_progress'
    task.date_started = timezone.now()
    task.save()
    
    return JsonResponse({'success': True, 'message': 'Задача принята в работу'})


@login_required
def car_task_complete(request, task_id):
    """Завершение задачи"""
    task = get_object_or_404(RegCarsOrganizationTask, pk=task_id)
    
    if task.status == 'completed':
        return JsonResponse({'success': False, 'error': 'Задача уже выполнена'}, status=400)
    
    task.status = 'completed'
    task.date_completed = timezone.now()
    task.save()
    
    return JsonResponse({'success': True, 'message': 'Задача завершена'})


@login_required
def car_task_comment_add(request, task_id):
    """Добавление комментария к задаче"""
    task = get_object_or_404(RegCarsOrganizationTask, pk=task_id)
    
    if request.method == 'POST':
        comment_text = request.POST.get('comment', '')
        
        if comment_text:
            comment = RegCarsOrganizationTaskComment.objects.create(
                task=task,
                staff=request.user,
                comment=comment_text,
                date_created=timezone.now()
            )
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'comment': {
                        'id': comment.id,
                        'text': comment.comment,
                        'author': comment.staff.username if comment.staff else '',
                        'date': comment.date_created.strftime('%d.%m.%Y %H:%M') if comment.date_created else '',
                    }
                })
    
    return JsonResponse({'success': False, 'error': 'Ошибка добавления комментария'}, status=400)


@login_required
def car_task_file_upload(request, task_id):
    """Загрузка файла к задаче"""
    task = get_object_or_404(RegCarsOrganizationTask, pk=task_id)
    
    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')
        
        if not uploaded_file:
            return JsonResponse({'success': False, 'error': 'Файл не выбран'}, status=400)
        
        # Ограничение размера файла (50 МБ)
        max_size = 50 * 1024 * 1024  # 50 МБ
        if uploaded_file.size > max_size:
            return JsonResponse({'success': False, 'error': 'Размер файла превышает 50 МБ'}, status=400)
        
        # Создаем запись о файле
        task_file = RegCarsOrganizationTaskFile.objects.create(
            task=task,
            staff=request.user,
            file=uploaded_file,
            file_name=uploaded_file.name,
            file_size=uploaded_file.size,
            date_created=timezone.now()
        )
        
        return JsonResponse({
            'success': True,
            'file': {
                'id': task_file.id,
                'name': task_file.file_name,
                'size': task_file.file_size,
                'size_display': task_file.get_file_size_display(),
                'url': task_file.file.url if task_file.file else '',
                'date': task_file.date_created.strftime('%d.%m.%Y %H:%M') if task_file.date_created else '',
                'staff': task_file.staff.username if task_file.staff else '',
            }
        })
    
    return JsonResponse({'success': False, 'error': 'Метод не разрешен'}, status=405)


@login_required
def car_task_file_delete(request, file_id):
    """Удаление файла задачи"""
    task_file = get_object_or_404(RegCarsOrganizationTaskFile, pk=file_id)
    
    # Проверяем права (только автор или администратор)
    if task_file.staff != request.user and not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Нет прав на удаление файла'}, status=403)
    
    # Мягкое удаление
    task_file.is_deleted = True
    task_file.save()
    
    # Удаляем физический файл
    if task_file.file:
        try:
            task_file.file.delete(save=False)
        except:
            pass
    
    return JsonResponse({'success': True, 'message': 'Файл удален'})


# ========== Витрина склада ==========

@login_required
def warehouse_showcase_create(request):
    """Создание витрины склада (запуск через задание)"""
    from django.db import transaction
    import json as json_lib
    
    unit_id = request.GET.get('unit', '')
    unit = None
    if unit_id:
        unit = get_object_or_404(RefUnit, pk=unit_id)
    
    # Базовый queryset
    cars_qs = RefCarsOrganization.objects.exclude(quantity=0).select_related(
        'unit', 'status', 'store', 'modification_autoru',
        'modification_autoru__model', 'modification_autoru__model__mark',
        'evaluation', 'lo'
    )
    
    if unit:
        cars_qs = cars_qs.filter(unit=unit)
    
    # Подсчет метрик
    total_cars = cars_qs.count()
    total_price = cars_qs.aggregate(Sum('price'))['price__sum'] or 0
    total_cost = cars_qs.aggregate(Sum('cost_price'))['cost_price__sum'] or 0
    
    # Проблемы
    cars_no_photos = cars_qs.annotate(
        photos_count=Count('refcarsorganizationfiles', filter=Q(refcarsorganizationfiles__file__isnull=False), distinct=True)
    ).filter(photos_count=0).count()
    
    date_threshold_photos = timezone.now() - timedelta(days=90)
    cars_old_photos = cars_qs.annotate(
        oldest_photo_date=Min('refcarsorganizationfiles__date', filter=Q(refcarsorganizationfiles__file__isnull=False))
    ).filter(oldest_photo_date__lt=date_threshold_photos).count()
    
    cars_no_evaluation = cars_qs.filter(evaluation__isnull=True).count()
    
    date_threshold_eval = timezone.now() - timedelta(days=90)
    cars_old_evaluation = cars_qs.filter(
        Q(evaluation__date__lt=date_threshold_eval) | Q(evaluation__isnull=True)
    ).count()
    
    days_threshold = 180
    date_threshold_stock = timezone.now() - timedelta(days=days_threshold)
    cars_long_in_stock = cars_qs.filter(date_reception__lt=date_threshold_stock).count()
    
    # Создаем витрину
    with transaction.atomic():
        showcase = CarsWarehouseShowcase.objects.create(
            unit=unit,
            date_created=timezone.now(),
            total_cars=total_cars,
            total_price=total_price,
            total_cost=total_cost,
            cars_no_photos=cars_no_photos,
            cars_old_photos=cars_old_photos,
            cars_no_evaluation=cars_no_evaluation,
            cars_old_evaluation=cars_old_evaluation,
            cars_long_in_stock=cars_long_in_stock,
            data_json=json_lib.dumps({})  # Можно добавить детальные данные
        )
    
    return JsonResponse({
        'success': True,
        'showcase_id': showcase.id,
        'message': 'Витрина склада создана успешно'
    })


@login_required
def warehouse_analysis(request):
    """Анализ склада через витрину"""
    # Получаем последнюю витрину
    unit_id = request.GET.get('unit', '')
    showcase = None
    
    if unit_id:
        showcase = CarsWarehouseShowcase.objects.filter(unit_id=unit_id).order_by('-date_created').first()
    else:
        showcase = CarsWarehouseShowcase.objects.order_by('-date_created').first()
    
    units = RefUnit.objects.all().order_by('name')
    
    params = {
        'showcase': showcase,
        'units': units,
        'selected_unit_id': unit_id,
    }
    
    return render(request, 'avtosalon/warehouse_analysis.html', {'params': params})
