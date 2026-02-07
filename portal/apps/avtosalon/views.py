from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from refs.models import AutoruComplectation, RefCarsOrganization, RefStore, RefTypeEvaluationCarsOrganization, RefStagePrice, RefGroupPrice, RefRatingCarsOrganization, RefTypeDrive
from refs.models import RefStagePrice, RefTypeSaleCarsOrganization, RefStatusCarsOrganization, RefTypeDrive, RefTypeBody, RefTypeKpp, RefUnit, RefCity, RefSpecificationData, RefEventCarsOrganization, RefAvito, RefCarsOrganizationFiles, RefCarsOrganization, AutoruModification, AutoruComplectation, AutoruModel, AutoruMark, AutoruModificationSpecifications
from api.views_avtosalon import add_statistic_cars_organization
from django.core.paginator import Paginator
import json
from api.views import get_unit, get_organization, get_store, get_stage_price, get_group_price, get_model_object
from avtosalon.models import RefreshCarsLog
from datetime import datetime
import base64
from email import header
from itertools import product
import requests
import tempfile
from django.db.models import Count, Sum, Max, Avg, F, OuterRef, Subquery, Sum, Q, Func, Value, CharField, IntegerField
from django.http import Http404, HttpResponseRedirect, HttpResponseNotFound, HttpResponse
from register.models import RegRefCarsOrganizationsCalculationPrice, RegInteractivOcenka, RegRefCarsOrganizationsPrice, RegEstimationRefCarsOrganizations
from avtosalon.models import Avtohub
from documents.models import DocCarAgreement, DocCarShipment, DocZNKA, DocZNWorkKA, DocZNProductKA, DocZNServicesKA, DocZNPerformersKA
from django.http import JsonResponse
from rest_framework import status


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
    status_type = request.GET.get('status', 'sale')  # По умолчанию "В продаже"
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
    )
    
    # Фильтр по статусу (тип диспозиции)
    if status_type == 'warehouse':
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
    
    mark_id = request.GET.get('mark', '')
    if mark_id:
        cars = cars.filter(modification_autoru__model__mark__id=mark_id)
    
    model_ids = request.GET.getlist('model[]')
    if model_ids:
        try:
            cars = cars.filter(modification_autoru__model__id__in=[int(mid) for mid in model_ids])
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
        vin or mark_id or model_ids or year_start or year_end or 
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
    # Загружаем модели (все для множественного выбора, или отфильтрованные по марке)
    models_list = AutoruModel.objects.select_related('mark').only('id', 'name', 'mark').order_by('name')
    if mark_id:
        models_list = models_list.filter(mark__id=mark_id)
    
    # Преобразуем списки в строки для шаблона (для удобства проверки selected)
    model_ids_str = [str(mid) for mid in model_ids]
    body_type_ids_str = [str(btid) for btid in body_type_ids]
    gear_type_ids_str = [str(gtid) for gtid in gear_type_ids]
    drive_type_ids_str = [str(dtid) for dtid in drive_type_ids]
    evaluation_type_ids_str = [str(etid) for etid in evaluation_type_ids]
    unit_ids_str = [str(uid) for uid in unit_ids]
    store_ids_str = [str(sid) for sid in store_ids]
    
    # Для фильтров с чекбоксами - списки ID для проверки в шаблоне
    body_type_ids_list = body_type_ids
    gear_type_ids_list = gear_type_ids
    drive_type_ids_list = drive_type_ids
    evaluation_type_ids_list = evaluation_type_ids
    unit_ids_list = unit_ids
    store_ids_list = store_ids
    
    filtr = {
        'status': status_type,
        'vin': vin,
        'search_fields': search_fields,
        'mark': mark_id,
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
        'body_type_ids_list': body_type_ids_list,
        'gear_type_ids_list': gear_type_ids_list,
        'drive_type_ids_list': drive_type_ids_list,
        'evaluation_type_ids_list': evaluation_type_ids_list,
        'unit_ids_list': unit_ids_list,
        'store_ids_list': store_ids_list,
    }
    
    return render(request, "avtosalon/disposition.html", {'params': params})


def disposition_get_models(request):
    """
    AJAX endpoint для загрузки моделей по марке
    """
    from django.http import JsonResponse
    
    mark_id = request.GET.get('mark_id', '')
    if not mark_id:
        return JsonResponse({'models': []})
    
    try:
        models = AutoruModel.objects.filter(mark__id=mark_id).order_by('name')
        models_list = [{'id': model.id, 'name': model.name} for model in models]
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
    
    # ОПТИМИЗАЦИЯ: Используем only() для загрузки только необходимых полей
    selected = {
        'stores'        : RefStore.objects.only('id', 'name').order_by('name'),
        'evaluations'   : RefTypeEvaluationCarsOrganization.objects.only('id', 'name').order_by('name'),
        'stageprices'   : RefStagePrice.objects.only('id', 'name').order_by('name'),
        'groupprices'   : RefGroupPrice.objects.only('id', 'name').order_by('name'),
        'ratings'       : RefRatingCarsOrganization.objects.only('id', 'name').order_by('name'), 
    }

    params = {
        'object'        : car,
        'selected'      : selected,
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
