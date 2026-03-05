from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from refs.models import AutoruComplectation, RefCarsOrganization, RefStore, RefTypeEvaluationCarsOrganization, RefStagePrice, RefGroupPrice, RefRatingCarsOrganization, RefTypeDrive
from refs.models import RefStagePrice, RefTypeSaleCarsOrganization, RefStatusCarsOrganization, RefTypeDrive, RefTypeBody, RefTypeKpp, RefUnit, RefCity, RefSpecificationData, RefEventCarsOrganization, RefAvito, RefCarsOrganizationFiles, RefCarsOrganization, AutoruModification, AutoruComplectation, AutoruModel, AutoruMark, AutoruModificationSpecifications
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
from django.db.models import Count, Sum, Max, Min, Avg, F, OuterRef, Subquery, Sum, Q, Func, Value, CharField, IntegerField, Case, When, FloatField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta
import os
from django.http import Http404, HttpResponseRedirect, HttpResponseNotFound, HttpResponse
from register.models import RegRefCarsOrganizationsCalculationPrice, RegInteractivOcenka, RegRefCarsOrganizationsPrice, RegEstimationRefCarsOrganizations
from avtosalon.models import Avtohub, AvtohubSiteInfo, AvtohubSite, RegCarsOrganizationTask, RegCarsOrganizationTaskComment, RegCarsOrganizationTaskFile, CarsWarehouseShowcase
from documents.models import DocCarAgreement, DocCarShipment, DocZNKA, DocZNWorkKA, DocZNProductKA, DocZNServicesKA, DocZNPerformersKA, DocRLK, DocLO, RefService, DocServiceItem
from django.http import JsonResponse
from rest_framework import status
import qrcode
import io
import base64
from chats.models import Chat, ChatMessage

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
    
    add_statistic_cars_organization(cars=car, store=car.store, type=1)
    
    # Генерация QR-кода со ссылкой на страницу автомобиля
    car_url = request.build_absolute_uri(f'/cars/{car.slug}/')
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

    # Подсчет задач по автомобилю
    tasks_count = RegCarsOrganizationTask.objects.filter(car=car).count()
    tasks_new_count = RegCarsOrganizationTask.objects.filter(car=car, status='new').count()
    tasks_in_progress_count = RegCarsOrganizationTask.objects.filter(car=car, status='in_progress').count()
    
    params = {
        'object'        : car,
        'selected'      : selected,
        'qr_code'       : qr_code_base64,
        'car_url'       : car_url,
        'tasks_count'   : tasks_count,
        'tasks_new_count': tasks_new_count,
        'tasks_in_progress_count': tasks_in_progress_count,
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

    params = {
        'object'            : car,
        'selected'          : selected,
        'specifications'    : specifications,
        'complectations'    : complectations
    }
    
    return render(request, "avtosalon/car_new_specifications.html", {'params': params})


def price_edit(request, slug):
    
    car     = RefCarsOrganization.objects.filter(slug = slug)[0]
    base1C  = ''

    if request.method == "POST":
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
                
        return HttpResponseRedirect(request.build_absolute_uri())
        
    else:
        
        url_get = url_hs_kors_auto + "/car/?uin_lo=" + car.lo_uin
        response = requests.get(url_get)
        base1C = ''
    
        if response.status_code == 200:
            if response.text != '':
                base1C = json.loads(response.text)

    list_price = RegRefCarsOrganizationsPrice.objects.filter(car = car).order_by('-date')
    
    calculations_list    = RegEstimationRefCarsOrganizations.objects.filter(car = car).order_by('-date')    
    calculations = list()
    for calc in calculations_list:
        percent = 0 
        if calc.total > 0:
            percent = calc.position / calc.total
        
        data_calculations = {
            'date'      : calc.date,
            'avg_price' : calc.avg_price,
            'avg_days'  : calc.avg_days,
            'position'  : calc.position,
            'total'     : calc.total,
            'percent'   : percent 
        }
        calculations.append(data_calculations)
    
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

    finance     = round(car.cost_price * ((18 / 365) / 100) * car.days_in_stok, 2) 
    marketing   = 0  
    avtohubs_list = Avtohub.objects.filter(vin = car.vin).filter(date__range = [car.lo_link_date, car.date_refresh]).order_by('-date') 
    avtohubs      = list()
    for avtohub in avtohubs_list:
        percent = 0 

        marketing = round(max(marketing, avtohub.totalAdvertisingCost), 2)
        
        if avtohub.numberOfCompetitors > 0:
            percent = avtohub.vRatingPosition / avtohub.numberOfCompetitors
        
        data_avtohub = {
            'date'                  : avtohub.date,
            'avgMarketPrice'        : avtohub.avgMarketPrice,
            'averageDaysInSale'     : avtohub.averageDaysInSale,
            'vRatingPosition'       : avtohub.vRatingPosition,
            'numberOfCompetitors'   : avtohub.numberOfCompetitors,
            'percent'               : percent 
        }
        avtohubs.append(data_avtohub)

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
        '1C'                : base1C,
        'calculations'      : calculations,
        'avtohubs'          : avtohubs,
        'finance'           : finance,
        'marketing'         : marketing,
        'interactiv'        : interactiv,
        'agreement'         : agreement,
        'shipment'          : shipment,
        'calc_express'      : calc_express,
        'calc_autohub'      : calc_autohub,
        'calc_1C'           : calc_1C
    }
    
    return render(request, "avtosalon/car_new_price_edit.html", {'params': params})


def price(request, slug):
    car = RefCarsOrganization.objects.filter(slug=slug).select_related(
        'unit', 'complectation_autoru', 'modification_autoru',
        'modification_autoru__model', 'modification_autoru__model__mark',
    ).first()
    if not car:
        raise Http404

    chat, created = Chat.objects.get_or_create(name=car.slug, slug='car_' + str(car.slug))

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
    last_month_start = last_month_end.replace(day=1)

    analytics = {
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

    from powerbi.models import Cumulative
    from django.db.models.functions import TruncDate

    q_cumulative = Cumulative.objects.filter(
        DataProdazhi__gte=last_month_start,
        DataProdazhi__lte=last_month_end,
    )
    if car.unit and car.unit.name:
        q_unit = q_cumulative.filter(PodrazdelenieDTs__icontains=car.unit.name)
        analytics['unit_sales_count'] = q_unit.count()
        analytics['cumulative_detail'] = list(
            q_unit.order_by('-DataProdazhi')[:100].values(
                'DataProdazhi', 'Marka', 'Model', 'Modifikatsiya', 'VIN',
                'VyruchkaZaAvto', 'KolichestvoAvto', 'PodrazdelenieDTs', 'TipProdazhi',
            )
        )
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
    if car.vin:
        zn_list = list(
            DocZN.objects.filter(cars__vin=car.vin, typeRemont__dop=True)
            .select_related('typeRemont', 'readyStatus', 'unit')
            .order_by('-dataTime')[:200]
        )

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

    current_tab = request.GET.get('tab', 'avto')
    list_price = list(RegRefCarsOrganizationsPrice.objects.filter(car=car).order_by('-date')[:50])

    # Склад: остатки по модели (текущее подразделение или все подразделения)
    warehouse_current = []
    warehouse_all = []
    warehouse_scope = request.GET.get('warehouse', 'current')
    if car.modification_autoru_id and car.modification_autoru.model_id:
        model_id = car.modification_autoru.model_id
        warehouse_current = list(
            RefCarsOrganization.objects.filter(
                unit_id=car.unit_id,
                modification_autoru__model_id=model_id,
                quantity__gt=0,
            )
            .select_related('unit', 'modification_autoru', 'complectation_autoru')
            .order_by('name')[:500]
        )
        warehouse_all = list(
            RefCarsOrganization.objects.filter(
                modification_autoru__model_id=model_id,
                quantity__gt=0,
            )
            .select_related('unit', 'modification_autoru', 'complectation_autoru')
            .order_by('unit__name', 'name')[:500]
        )

    # Объекты для шаблона (страница price не загружает полные данные оценки/сделок)
    from types import SimpleNamespace
    estimation_empty = SimpleNamespace(tasks=[])
    interactiv_rlk_empty = SimpleNamespace(estimation=estimation_empty)

    params = {
        'object': car,
        'chat': chat,
        'messages': chat.get_last_messages(),
        'selected': selected,
        'avtohubs': avtohubs,
        'finance': finance,
        'marketing': marketing,
        'user': request.user,
        'analytics': analytics,
        'analytics_gk': analytics_gk,
        'last_month_start': last_month_start,
        'last_month_end': last_month_end,
        'zn_list': zn_list,
        'current_tab': current_tab,
        'list_price': list_price,
        'warehouse_current': warehouse_current,
        'warehouse_all': warehouse_all,
        'warehouse_scope': warehouse_scope,
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
    }

    return render(request, "avtosalon/car_new_price.html", {'params': params})


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
    
    # Обработка POST запросов
    if request.method == "POST":
        action = request.POST.get('action', '')
        
        # Удаление фотографии
        if action == 'delete':
            photo_id = request.POST.get('photo_id', '')
            try:
                photo = RefCarsOrganizationFiles.objects.get(id=photo_id, сars_organization=car)
                photo.delete()
                messages.success(request, 'Фотография успешно удалена')
            except RefCarsOrganizationFiles.DoesNotExist:
                messages.error(request, 'Фотография не найдена')
        
        # Установка главной фотографии
        elif action == 'set_main':
            photo_id = request.POST.get('photo_id', '')
            try:
                # Снимаем флаг главной со всех фотографий
                RefCarsOrganizationFiles.objects.filter(сars_organization=car).update(main=False)
                # Устанавливаем новую главную
                photo = RefCarsOrganizationFiles.objects.get(id=photo_id, сars_organization=car)
                photo.main = True
                photo.save()
                messages.success(request, 'Главная фотография обновлена')
            except RefCarsOrganizationFiles.DoesNotExist:
                messages.error(request, 'Фотография не найдена')
        
        # Загрузка новых фотографий
        elif action == 'upload':
            uploaded_files = request.FILES.getlist('photos')
            if uploaded_files:
                uploaded_count = 0
                errors = []
                
                for uploaded_file in uploaded_files:
                    # Проверка типа файла
                    if not uploaded_file.content_type.startswith('image/'):
                        continue
                    
                    try:
                        # Создаем объект фотографии
                        photo = RefCarsOrganizationFiles()
                        photo.сars_organization = car
                        photo.name = uploaded_file.name
                        photo.file = uploaded_file
                        photo.main = False
                        photo.car = True
                        photo.processed = False
                        photo.date = datetime.now()
                        
                        # Сохраняем основное изображение
                        photo.save()
                        
                        # Создаем миниатюру автоматически
                        try:
                            from PIL import Image
                            from django.core.files.base import ContentFile
                            import io
                            import os
                            
                            # Открываем сохраненный файл
                            if photo.file and photo.file.name:
                                # Получаем путь к файлу
                                file_path = photo.file.path
                                
                                # Проверяем существование файла на диске
                                if not os.path.exists(file_path):
                                    # Если файл еще не на диске, ждем немного и проверяем снова
                                    import time
                                    time.sleep(0.1)
                                    if not os.path.exists(file_path):
                                        raise FileNotFoundError(f"Файл {file_path} не найден после сохранения")
                                
                                # Открываем изображение с диска
                                img = Image.open(file_path)
                                
                                # Конвертируем в RGB если нужно (для JPEG)
                                original_mode = img.mode
                                if img.mode in ('RGBA', 'LA', 'P'):
                                    # Создаем белый фон
                                    background = Image.new('RGB', img.size, (255, 255, 255))
                                    if img.mode == 'P':
                                        img = img.convert('RGBA')
                                    # Вставляем изображение на фон с учетом альфа-канала
                                    if img.mode == 'RGBA' and len(img.split()) >= 4:
                                        background.paste(img, mask=img.split()[3])
                                    else:
                                        background.paste(img)
                                    img = background
                                elif img.mode not in ('RGB', 'L'):
                                    img = img.convert('RGB')
                                
                                # Создаем миниатюру (максимальный размер 400x400, сохраняя пропорции)
                                max_size = (400, 400)
                                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                                
                                # Сохраняем миниатюру в память
                                thumb_io = io.BytesIO()
                                
                                # Всегда сохраняем миниатюру как JPEG для универсальности и меньшего размера
                                img.save(thumb_io, format='JPEG', quality=85, optimize=True)
                                
                                thumb_io.seek(0)
                                
                                # Генерируем имя для миниатюры (всегда .jpg)
                                base_name = os.path.basename(photo.file.name)
                                name_without_ext, ext = os.path.splitext(base_name)
                                mini_name = f'{name_without_ext}_mini.jpg'
                                
                                # Сохраняем миниатюру
                                photo.file_mini.save(
                                    mini_name,
                                    ContentFile(thumb_io.read()),
                                    save=False
                                )
                                photo.save()
                                
                        except ImportError:
                            # Pillow не установлен - пытаемся использовать оригинал как миниатюру
                            if photo.file:
                                photo.file_mini = photo.file
                                photo.save()
                            errors.append(f'Pillow не установлен, миниатюра не создана для {uploaded_file.name}')
                        except Exception as e:
                            # Если не удалось создать миниатюру, используем оригинал
                            if photo.file:
                                try:
                                    photo.file_mini = photo.file
                                    photo.save()
                                except:
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
        
        return HttpResponseRedirect(request.build_absolute_uri())
    
    # Получаем все фотографии автомобиля
    photos = RefCarsOrganizationFiles.objects.filter(сars_organization=car).order_by('-main', '-date')
    
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


@login_required
def deal_calculation(request):
    """
    Калькулятор сделки автомобиля
    """
    try:
        from analytics.models import TradeInFunnel
    except ImportError:
        TradeInFunnel = None
    
    params = {
        'type': 'deal_calculation',
        'nav_selected': 4,
        'request': request,
    }
    
    # Получаем выбранный автомобиль из диспозиции
    car_slug = request.GET.get('car', '')
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
    """Страница директора ГК: все автомобили в наличии, кол-во незакрытых задач, общий чат по автомобилям."""
    # Автомобили в наличии с подсчётом незакрытых задач (new + in_progress)
    open_tasks_filter = Q(tasks__status='new') | Q(tasks__status='in_progress')
    cars_qs = (
        RefCarsOrganization.objects.filter(quantity__gt=0)
        .select_related(
            'unit', 'status', 'modification_autoru', 'modification_autoru__model',
            'modification_autoru__model__mark', 'complectation_autoru',
        )
        .annotate(
            open_tasks_count=Coalesce(
                Count('tasks', filter=open_tasks_filter, distinct=True),
                Value(0),
                output_field=IntegerField(),
            )
        )
        .order_by('unit__name', '-date_create')
    )
    # Ограничиваем выборку для отображения (можно пагинировать)
    cars_list = list(cars_qs[:2000])
    params = {
        'cars_list': cars_list,
        'user': request.user,
        'chats': [],  # чаты подгружаются по JS из get_chats_list_cars
        'chat_list_cars_url': '/cars/js/get_chats_list_cars/',
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
    # Данные авто: RefCarsOrganization.slug = Chat.name
    car_unit = RefCarsOrganization.objects.filter(slug=OuterRef('name')).values('unit__name')[:1]
    car_vin = RefCarsOrganization.objects.filter(slug=OuterRef('name')).values('vin')[:1]
    car_mark = RefCarsOrganization.objects.filter(slug=OuterRef('name')).values('modification_autoru__model__mark__name')[:1]
    car_model = RefCarsOrganization.objects.filter(slug=OuterRef('name')).values('modification_autoru__model__name')[:1]
    car_mod = RefCarsOrganization.objects.filter(slug=OuterRef('name')).values('modification_autoru__name')[:1]
    chats = (
        Chat.objects.filter(slug__startswith='car_')
        .annotate(max_date=subq_msg_date, content=subq_msg_content)
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
