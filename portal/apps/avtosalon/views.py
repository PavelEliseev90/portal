from django.shortcuts import render
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
from documents.models import DocCarAgreement, DocCarShipment
from django.http import JsonResponse
from rest_framework import status


url_hs_kors_auto    = 'http://a01srv1cka/zbusiness/hs/mb'


def get_cars_organization(user, filter):
    cars = RefCarsOrganization.objects.exclude(quantity = 0).exclude(modification_autoru = None)

    return cars


def get_catalog():
    
    autoru = AutoruMark.objects.all().order_by('name')

    cars = RefCarsOrganization.objects.exclude(quantity = 0).exclude(modification_autoru = None).filter(modification_autoru__model__mark__id = OuterRef(name='id')).annotate(count=Func(F('id'), function='Count')).values('count')
    
    autoru = autoru.annotate(cars_count = Subquery(cars))
    autoru = autoru.exclude(cars_count = 0)

    return autoru


def get_catalog_mark(mark):
    
    autoru = AutoruModel.objects.filter(mark__nameEn = mark).order_by('name').distinct()

    cars = RefCarsOrganization.objects.exclude(quantity = 0).exclude(modification_autoru = None).filter(modification_autoru__model__id = OuterRef(name='id')).annotate(count=Func(F('id'), function='Count')).values('count')
    
    autoru = autoru.annotate(cars_count = Subquery(cars))
    autoru = autoru.exclude(cars_count = 0).distinct()

    return autoru.order_by('nameEn').values('nameEn', 'nameHuman').annotate(sum = Sum('cars_count')).distinct()


def catalog_mark(request, mark_name_en):
    
    select_count    = request.GET.get('select_count', 12)
    catalog         = get_catalog_mark(mark_name_en) 
    
    cars = get_cars_organization(request.user, filter = '')
    cars = cars.filter(modification_autoru__model__mark__nameEn = mark_name_en)

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

    selected = {
        'stores'        : RefStore.objects.all().order_by('name'),
        'evaluations'   : RefTypeEvaluationCarsOrganization.objects.all().order_by('name'),
    }
    
    params = {
        'type'          : 'cars',
        'page_number'   : page_number,
        'paginator'     : page_obj,
        'selected'      : selected,
        'filtr'         : filtr,
        'catalog'       : catalog
    } 
    params = {
        'type'          : 'cars',
        'mark_name_en'  : mark_name_en,
        'page_number'   : page_number,
        'paginator'     : page_obj,
        'selected'      : selected,
        'filtr'         : filtr,
        'catalog'       : catalog
    }
    
    return render(request, "avtosalon/cars_catalog_new.html", {'params': params})  


def catalog_model(request, mark_name_en, model_name):
    
    select_count    = request.GET.get('select_count', 12)
    catalog         = get_catalog_mark(mark_name_en) 
    
    cars = get_cars_organization(request.user, filter = '')
    cars = cars.filter(modification_autoru__model__mark__nameEn = mark_name_en).filter(modification_autoru__model__nameEn__icontains = model_name)

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

    selected = {
        'stores'        : RefStore.objects.all().order_by('name'),
        'evaluations'   : RefTypeEvaluationCarsOrganization.objects.all().order_by('name'),
    }
    
    params = {
        'type'          : 'cars',
        'page_number'   : page_number,
        'paginator'     : page_obj,
        'selected'      : selected,
        'filtr'         : filtr,
        'catalog'       : catalog
    } 
    params = {
        'type'          : 'cars',
        'mark_name_en'  : mark_name_en,
        'page_number'   : page_number,
        'paginator'     : page_obj,
        'selected'      : selected,
        'filtr'         : filtr,
        'catalog'       : catalog
    }
    
    return render(request, "avtosalon/cars_catalog_new.html", {'params': params})  


def cars_catalog(request):

    catalog         = get_catalog() 

    params = {
        'type'          : 'cars',
        'catalog'       : catalog,
        'glav'          : True

    }
    
    return render(request, "avtosalon/cars_catalog_new.html", {'params': params})


def cars(request):

    select_count    = request.GET.get('select_count', 12)
    catalog         = get_catalog() 

    cars        = RefCarsOrganization.objects.exclude(quantity = 0).exclude(modification_autoru = None)
    subquery    = Subquery(RefCarsOrganizationFiles.objects.filter(сars_organization__id = OuterRef(name='pk')).values('id')[:1])
    cars        = cars.annotate(photos = Count(subquery))    
    cars        = cars.order_by('-photos', '-date_create')
    
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

    selected = {
        'stage_prices'  : RefStagePrice.objects.all().order_by('name'),
        'type_sales'    : RefTypeSaleCarsOrganization.objects.all().order_by('name'),
        'statuses'      : RefStatusCarsOrganization.objects.all().order_by('name'),
        'marks'         : AutoruMark.objects.all().order_by('name'),
        'bodys'         : RefTypeBody.objects.all().order_by('name'),
        'drives'        : RefTypeDrive.objects.all().order_by('name'),
        'gears'         : RefTypeKpp.objects.all().order_by('name'),
        'stores'        : RefStore.objects.all().order_by('name'),
        'evaluations'   : RefTypeEvaluationCarsOrganization.objects.all().order_by('name'),
        'citys'         : RefUnit.objects.filter(buauto = True).exclude(city = None).order_by('city__name').values('city', 'city__name').distinct()
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


def car(request, slug):

    car = RefCarsOrganization.objects.filter(slug = slug)[0]
    
    add_statistic_cars_organization(cars=car, store=car.store, type=1)
    
    selected = {
        'stores'        : RefStore.objects.all().order_by('name'),
        'evaluations'   : RefTypeEvaluationCarsOrganization.objects.all().order_by('name'),
        'stageprices'   : RefStagePrice.objects.all().order_by('name'),
        'groupprices'   : RefGroupPrice.objects.all().order_by('name'),
        'ratings'       : RefRatingCarsOrganization.objects.all().order_by('name'), 
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
