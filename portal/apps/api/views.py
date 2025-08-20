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
from django.db import models
from datetime import datetime
from django.conf import settings
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.http.response import JsonResponse
from django.core.paginator import Paginator

from rest_framework.authentication import BasicAuthentication
from rest_framework.parsers import JSONParser
from rest_framework import status
from rest_framework.decorators import api_view
from django.db.models import Count, Sum, Max, Avg, F, OuterRef, Subquery, Sum, Q
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.models import User
from django.dispatch import receiver
import json
from urllib.parse import unquote

from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from refs.models import RefReasonArchiveRLK, RefMarkTyres, RefWidthTyres, RefProfileTyres, RefRadius, RefSezonTyres, RefTypeDisk, RefDiaDisk, RefEtDisk, RefPsdDisk, RefFilial, RefSpecificationData, RefSpecification, AutoruModification, AutoruModificationSpecifications, AutoruComplectation, RefStore, RefStagePrice, RefGroupPrice, RefExchangeCars, RefTypeExchange, RefIb, RefTypeItemRepair, AutoruMark, AutoruModel, AutoruComplectation, AutoruModification, RefOrganization, RefUnit, RefCustomer, RefCity, RefCars, RefStaff, RefTypeDocRLK, RefWork, RefProduct, RefTypeRepair, RefStatusDocZN, RefContactType, RefStatusEvent, RefManufacturer, RefCatalogProduct, RefTypeResourcePlanning, RefTypeCategoryCustomer, RefTypeCategoryNegative, RefSMSStatusBase, RefSMSStatusBase
from documents.models import DocCarAgreement, DocLO, DocZN, DocZNPerformers, DocZNProductCustomer, DocZNRecomendation, DocZNProduct, DocZNWork, DocCarShipment, DocRLK, DocRLKEvents, DocOprosZN, DocOprosCarShipment, DoсRecomendation, DoсRecomendationWork, DoсRecomendationProduct, DoсRecomendationMCU, SurveysOP, SurveysOP_tematics, SurveysOP_questions, ResourcePlanning, DocServiceRequest, DocSMS
import datetime as DT
from recognition.models import Records_voice_recorder, Records_voice_recorder_queue
from refs.serializers import AutoruComplectationSerializer, AutoruMarkSerializer, AutoruModelSerializer, AutoruModificationSerializer
from online.models import Online_doc, Records_online_doc
from register.models import RegPrices
from avtosalon.models import RefreshSpecificationsAutoRU
from recognition.models import Recognition_call, Records_voice_recorder
from telephony.models import Telephony_records_queue
import base64
from email import header
from itertools import product
from bs4 import BeautifulSoup
import requests
from fake_headers import Headers
import fake_proxy
import qrcode
import urllib.parse
import io
from django.contrib.contenttypes.models import ContentType
from django.apps import apps
import re
from django.views.decorators.csrf import csrf_exempt

@api_view(['POST'])
def post_info(request):
    
    list_info = json.loads(request.body)
    '''
    for dat in list_info:
        data = RefWidthTyres()
        data.name   = dat
        data.value  = float(dat)
        data.save()
    '''
    to_json = {
        'list_info'          : list_info
    }
    
    return JsonResponse(to_json, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_info_article_product(request):
    
    article         = request.GET.get('article', '')
    manufacturen    = request.GET.get('manufacturen', '')
    page            = int(request.GET.get('page', '1'))
    count_answer    = int(request.GET.get('count', '1000'))
    count_all       = 0

    list_info = list()

    if len(article) > 0 or len(manufacturen) > 0:

        infos = RegPrices.objects.all().exclude(manufacturer = None).order_by('name')

        if len(article) > 0:
            article_search = re.sub("[^A-Za-z А-Яа-я 0-9]", "", article).rstrip()
            infos = infos.filter(article_search__icontains = article_search).exclude(manufacturer = None)
        
        if len(manufacturen) > 0:
            infos = infos.filter(manufacturer__name__icontains = manufacturen).exclude(manufacturer = None)
        
        count_all   = infos.count()
        paginator   = Paginator(infos, count_answer)	
        page_obj    = paginator.get_page(page)

        for info in page_obj:
        
            if info.category != None:
                category              = info.category.name
            else:
                category              = None

            if info.group != None:
                group              = info.group.name
            else:
                group              = None

            product = {
                'manufacturer'          : info.manufacturer.name,
                'date'                  : info.date,
                'name'                  : info.name,
                'article'               : info.article,
                'article_search'        : info.article_search,
                'category'              : category,
                'group'                 : group,
                'price'                 : info.price,
                'price_min'             : info.price_min
            }
            list_info.append(product)

        '''
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
'''                            
    filtr = {
        'article'       : article,
        'manufacturen'  : manufacturen

    }
    to_json = {
        'list_info'             : list_info,
        'page'                  : page,
        'count_answer'          : count_answer,
        'count'                 : count_all,
        'filter'                : filtr
    }
    
    return JsonResponse(to_json, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
def get_qrcode(request):
    
    body_unicode    = request.body.decode().replace("'", '"')
    data            = json.loads(body_unicode) 
    qr_code_image   = qrcode.make(body_unicode)
    buffer          = io.BytesIO()
    qr_code_image.save(buffer, format="PNG")
    qr_code_image_data = base64.b64encode(buffer.getvalue()).decode()
    
    to_json = {
        'info'          : body_unicode,
        'img_base64'    : str(qr_code_image_data)
    }
    
    return JsonResponse(to_json, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
def info_brand_article_shop_autoshina(request):
    
    list_products   = list()
    brand           = request.GET.get('brand', '')
    article         = request.GET.get('article', '')
    
    if len(brand) > 0 and len(article) > 0:
        from requests.auth import HTTPBasicAuth
        basic       = HTTPBasicAuth('feniks_pro90@mail.ru', 'Audi80b4')
        header      = Headers(os="mac", headers=True).generate()
        url         = 'https://shop.autoshina.com/search/' + brand + '/' + article
        response    = requests.get(url, headers=header, auth=basic)
        html        = BeautifulSoup(response.content,'html.parser')

        table_results = html.find_all(id = 'searchResultsTable')
        
        for table_result in table_results:
            tr_table_result = table_result.find_all(['tr'])
            for td_tr_table_result_info in tr_table_result:
                if str(tr_table_result).find('resultTr') > 0 and str(tr_table_result).find('resultPrice') > 0: 
                    product_info = {
                        'brand'         : '',
                        'articul'       : '',
                        'description'   : '',
                        'availability'  : 0,
                        'store'         : '',
                        'date'          : '',
                        'chance'        : '',
                        'price'         : ''
                    }
                    td_tr_table_result_info_td = td_tr_table_result_info.find_all(['td'])
                    append = False
                    for td_tr_table_result in td_tr_table_result_info_td:
                        try:
                            if len(td_tr_table_result.text.strip()) > 0:
                                if not 'resultHidden' in td_tr_table_result.attrs['class']: 
                                    if 'resultWarehouse' in td_tr_table_result.attrs['class']:
                                        product_info['store'] = td_tr_table_result.text.strip()
                                        append = True
                                    if 'resultPrice' in td_tr_table_result.attrs['class']:
                                        price = str(td_tr_table_result.text.strip())
                                        product_info['price'] = price
                                        append = True
                                    if 'resultBrand' in td_tr_table_result.attrs['class']:
                                        product_info['brand'] = td_tr_table_result.text.strip()
                                        append = True
                                    if 'resultPartCode' in td_tr_table_result.attrs['class']:
                                        product_info['articul'] = td_tr_table_result.text.strip()
                                        append = True
                                    if 'resultDescription' in td_tr_table_result.attrs['class']:
                                        product_info['description'] = td_tr_table_result.text.strip()
                                        append = True
                                    if 'resultAvailability' in td_tr_table_result.attrs['class']:
                                        product_info['availability'] = td_tr_table_result.text.strip()
                                        append = True
                                    if 'resultDeadline' in td_tr_table_result.attrs['class']:
                                        product_info['date'] = td_tr_table_result.text.strip()
                                        append = True
                                    if 'resultProbability' in td_tr_table_result.attrs['class']:
                                        product_info['chance'] = td_tr_table_result.text.strip()
                                        append = True
                        except:
                            s = 1
                    if append:
                        list_products.append(product_info)
        
    to_json = {
        'products_list'     : list_products,
        'products_count'    : len(list_products)
    }
    
    return JsonResponse(to_json, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
def info_brand_article_emex_list(request):
    
    list_products   = list()
    brand           = request.GET.get('brand', '')
    article         = request.GET.get('article', '')
    
    if len(brand) > 0 and len(article) > 0:
        header      = Headers(os="mac", headers=True).generate()
        geo     = '{"name":"Тула","description":"Тульская область","position":{"latitude":54.2021,"longitude":37.6179}}'

        cookies = {
            'map-zoom'              : '10',
            'yandex-geolocation'    : urllib.parse.quote_plus(geo)
            }
        url = 'https://emex.ru/products/' + article + '/' + brand

        response    = requests.get(url, headers=header, cookies=cookies)
        html        = BeautifulSoup(response.content,'html.parser')

        json_data_text = html.find("script", {"id": "__NEXT_DATA__"})

        if json_data_text != None:
            data_json   = json_data_text.text
            
            json_data        = json.loads(data_json)

            props           = json_data['props']
            initialState    = props['initialState']
            details         = initialState['details']
            if details.get('points') != None:
                points          = details['points']
                list_points     = points['list']
                for point in list_points:
                    name    = point['name'] 
                    url     = point['url']
                    price_dict      = point['price']
                    delivery_dict   = point['delivery']

                    price = price_dict['value']
                    product_info = {
                        'brand'         : brand,
                        'articul'       : article,
                        'description'   : details['name'],
                        'availability'  : 0,
                        'store'         : name,
                        'date'          : delivery_dict['value'],
                        'chance'        : '',
                        'price'         : price,
                        'url'           : url
                    }
                    list_products.append(product_info)
        
    to_json = {
        'products_list'     : list_products,
        'products_count'    : len(list_products)
    }
    
    return JsonResponse(to_json, status=status.HTTP_200_OK)

@api_view(['GET', 'POST'])
def info_brand_article_emex_list_provider(request):
    
    list_products   = list()
    brand           = request.GET.get('brand', '')
    article         = request.GET.get('article', '')
    
    if len(brand) > 0 and len(article) > 0:
        
        header      = Headers(os="mac", headers=True).generate()
        geo     = '{"name":"Тула","description":"Тульская область","position":{"latitude":54.2021,"longitude":37.6179}}'

        cookies = {
            'map-zoom'              : '10',
            'yandex-geolocation'    : urllib.parse.quote_plus(geo)
            }
        url = 'https://emex.ru/products/' + article + '/' + brand

        response    = requests.get(url, headers=header, cookies=cookies)
        html        = BeautifulSoup(response.content,'html.parser')

        json_data_text = html.find("script", {"id": "__NEXT_DATA__"})

        if json_data_text != None:
            data_json   = json_data_text.text
            
            json_data        = json.loads(data_json)

            props           = json_data['props']
            initialState    = props['initialState']
            details         = initialState['details']
            if details.get('points') != None:
                points          = details['points']
                list_points     = points['list']
                for point in list_points:
                    name    = point['name'] 
                    url     = point['url']
                    price_dict      = point['price']
                    delivery_dict   = point['delivery']

                    price = price_dict['value']
                    product_info = {
                        'brand'         : brand,
                        'articul'       : article,
                        'description'   : details['name'],
                        'availability'  : 0,
                        'store'         : name,
                        'date'          : delivery_dict['value'],
                        'chance'        : '',
                        'price'         : price,
                        'url'           : url
                    }
                    list_products.append(product_info)
        
    to_json = {
        'products_list'     : list_products,
        'products_count'    : len(list_products)
    }
    
    return JsonResponse(to_json, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
def info_brand_article_emex(request):
    
    list_products   = list()
    brand           = request.GET.get('brand', '')
    article         = request.GET.get('article', '')
    
    if len(brand) > 0 and len(article) > 0:
        header      = Headers(os="mac", headers=True).generate()
        url         = 'https://emex.ru/products/' + article + '/' + brand + '/22909/'
        response    = requests.get(url, headers=header)
        html        = BeautifulSoup(response.content,'html.parser')

        elem_table_orginals = html.findAll("div", {"data-testid" : "Offers:block:tableoriginals"})
        elem_table_orginals0 = html.findAll("div", {"data-testid" : "Offers:block:tableoriginals[0]"})
        elem_table_item = list()

        if len(elem_table_orginals) > 0:
            elem_table_item = elem_table_orginals[0].findAll("div", {"data-testid" : "Offers:block:tableItem"})
        if len(elem_table_orginals0) > 0:
            elem_table_item = elem_table_orginals0[0].findAll("div", {"data-testid" : "Offers:block:tableItem"}) 

        if len(elem_table_item) > 0:
            product_info = {
                'brand'         : '',
                'articul'       : '',
                'description'   : '',
                'availability'  : 0,
                'store'         : '',
                'date'          : '',
                'chance'        : '',
                'price'         : ''
            }
            for elem_item in elem_table_item:
                itm_price               = elem_item.findAll("div", {"data-testid" : "Offers:text:priceInfo"})[0]
                product_info['price']       = itm_price.findAll(['span'])[0].text.strip()
                product_info['brand']       = brand
                product_info['articul']     = article
                list_products.append(product_info)

    to_json = {
        'products_list'     : list_products,
        'products_count'    : len(list_products)
    }
    
    return JsonResponse(to_json, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
def info_brand_article_image(request):
    
    brand           = request.GET.get('brand', '')
    article         = request.GET.get('article', '')
    
    image_url       = ''
    ref_image       = None

    manufacturer    = get_manufacturer(brand)
    count_catalog = RefCatalogProduct.objects.filter(manufacturer = manufacturer).filter(article = article).count()
    if count_catalog > 0:
        ref_image = RefCatalogProduct.objects.filter(manufacturer = manufacturer).filter(article = article)[0]
        
    else:
        url_img_article = get_url_foto(article= article, brand=brand)
        if url_img_article != None:
            ref_image = download_foto_url(url_img_article, brand, article)
            
    if ref_image != None:
        image_url = ref_image.main_photo.url
        to_json = {
            'image_url' : image_url,
            'name'      : ref_image.name,
            'exp'       : '.' + ref_image.name.split('.')[len(ref_image.name.split('.'))-1]
        }
    else:
        to_json = {
            'image_url'     : '',
            'name'          : '',
            'exp'           : ''
        }
    
    return JsonResponse(to_json, status=status.HTTP_200_OK)


def download_foto_url(urls, brand, article):
    url = urls.split(',')[0] 
    if url.find('http') < 0:
        response  = requests.get('https:' + url)
    else:
        response  = requests.get(url)

    if response.status_code == 200:
        if len(response.content) > 3000:
            exp                                     = '.' + url.split('.')[len(url.split('.'))-1]
            manufacturer                            = get_manufacturer(brand)
            new_ref_catalog_product                 = RefCatalogProduct()
            new_ref_catalog_product.name            = brand + '___' + article + exp
            new_ref_catalog_product.manufacturer    = manufacturer
            new_ref_catalog_product.article         = article
            new_ref_catalog_product.main_photo.save(brand + '___' + article + exp, ContentFile(response.content), save=True)
            new_ref_catalog_product.save()

            return new_ref_catalog_product
    return None


def get_url_foto(brand, article):
    url_photo = None
    if len(brand) > 0 and len(article) > 0:
        try:
           
            header      = Headers(headers=True).generate()
            url         = 'https://shop.autoshina.com/search/' + brand + '/' + article
            response    = requests.get(url, headers=header)
            html        = BeautifulSoup(response.content, 'html.parser')

            table_results = html.find_all(id = 'searchResultsTable')
            
            for table_result in table_results:
                tr_table_result = table_result.find_all(['tr'])
                if str(tr_table_result).find('resultTr') > 0: 
                        for td_tr_table_result in tr_table_result:
                            if str(td_tr_table_result).find('resultTr2') > 0: 
                                for str_info_article in td_tr_table_result:
                                    if str(str_info_article).find('resultImage'):
                                        img_info = table_result.find(['img'])
                                        url_photo = img_info['data-photos']
                                        return url_photo                
        except:
            return url_photo    
    return url_photo


def get_manufacturer(manufacturer_name):
    count = RefManufacturer.objects.filter(name = manufacturer_name).count()
    if count > 0:
        return RefManufacturer.objects.filter(name = manufacturer_name)[0]
    
    manufacturer = RefManufacturer()
    manufacturer.name = manufacturer_name
    manufacturer.save()

    return manufacturer
        

###исправить###

@api_view(['GET', 'POST',])
def versions(request):
    to_json = {
        'version': '1.1',
        'date'   : '23/11/2022'
    }
    
    return JsonResponse(to_json, status=status.HTTP_200_OK)


@api_view(['GET', 'POST',])
def index(request):
    to_json = {
        'count': 'ok'
    }
    return JsonResponse(to_json, status=status.HTTP_200_OK)


######
#####
####
###
##
# Обрабатываем запросы по заполнению и получению информации по спецификациям автомобилей каталога
@api_view(['GET', 'POST'])
def specifications_refresh_info(request):
    if request.method == 'GET':
        link_spec_auto_ru = 'https://auto.ru/catalog/cars/'

        if 'reverse' in request.GET:
            modifications   = AutoruModification.objects.all().order_by('-pk')
        else:
            modifications   = AutoruModification.objects.all().order_by('pk')
        
        subquery        = Subquery(AutoruModificationSpecifications.objects.filter(modification__id = OuterRef(name='id')).values('id')[:1], output_field = models.IntegerField())
        modifications   = modifications.annotate(spec = Count(subquery))
        modifications   = modifications.filter(spec = 0)
        if modifications.count() > 0:
            mod     = modifications[0]
            compls  = AutoruComplectation.objects.filter(modification__id = mod.id) 
            
            links = list()
            # модификация 
            link_mod = {
                'id'        : mod.id,
                'id_compl'  : 0,
                'info'      : '',
                'link'      : link_spec_auto_ru + mod.model.mark.nameEn.lower() + '/' + mod.model.nameEn.lower() + '/' + str(mod.idSiteGeneration) + '/' + str(mod.idSiteKonf) + '/specifications/' + str(mod.idSiteKonf) + '__' + str(mod.idSiteTech) + '/'
            }
            links.append(link_mod)
            for compl in compls:
                link_mod = {
                    'id'        : mod.id,
                    'id_compl'  : compl.id,
                    'info'      : '',
                    'link'      : link_spec_auto_ru + mod.model.mark.nameEn.lower() + '/' + mod.model.nameEn.lower() + '/' + str(mod.idSiteGeneration) + '/' + str(mod.idSiteKonf) + '/specifications/' + str(mod.idSiteKonf) + '_' + str(compl.id) +'_' + str(mod.idSiteTech) + '/'
                }
                links.append(link_mod)
  

            to_json = {
                'links': links
            }
            return JsonResponse(to_json, status=status.HTTP_200_OK)
    else:
        body_unicode    = request.body
        data            = json.loads(body_unicode)
        links           = data
        for link in links:
            mod     = AutoruModification.objects.get(pk = link['id'])
            id_compl = link['id_compl']
            compl   = ''
            new_mod_spec = AutoruModificationSpecifications()
            new_mod_spec.modification = mod
            if id_compl > 0:
                compl = AutoruComplectation.objects.get(id = id_compl)
                new_mod_spec.complectation = compl
            new_mod_spec.name = link['name']
            new_mod_spec.link = link['link']
            new_mod_spec.save()

            log_inf = RefreshSpecificationsAutoRU()
            log_inf.modification = mod
            if compl != '':
                log_inf.complectation = compl
            log_inf.save()

            list_info = link['info']
            for info in list_info:
                item    = info['item'] 
                val     = info['val']

                item_object = get_item_spec(item)
                newRefSpecificationData = RefSpecificationData() 
                newRefSpecificationData.modification_specifications = new_mod_spec
                newRefSpecificationData.specification   = item_object
                newRefSpecificationData.value           = val
                newRefSpecificationData.save()
            
        to_json = {
            'links': 'ok'
        }
        return JsonResponse(to_json, status=status.HTTP_200_OK)
            

    to_json = {
        'links': list()
    }
    return JsonResponse(to_json, status=status.HTTP_200_OK)


######
#####
####
###
##
#Функция работы для распознавания записей
@api_view(['GET', 'POST', 'DELETE'])
def create_recognition_call(request):
    
    body_unicode    = request.body.decode().replace("'", '"')
    data            = json.loads(body_unicode) 

    recognition_call        = Recognition_call()
    recognition_call.name   = data['info_audio']['name']
    #recognition_call.path   = data['info_audio']['path']   
    recognition_call.time   = data['info_audio']['seconds']
    recognition_call.data_json = body_unicode
    recognition_call.save()

    to = {
        'answer': 'ok'
    }    
    return JsonResponse(to, status=status.HTTP_200_OK, safe=False)


@api_view(['GET', 'POST', 'DELETE'])
def get_recordeds_voice_audio(request):
    
    records = list(Records_voice_recorder.objects.filter(time__gte = 0).filter(recognition = False).order_by('dateRecognitions'))
    
    answer = list()

    if len(records) > 0:
        record = records[0]
        record.dateRecognitions = DT.datetime.now()
        record.save()
        answer = records = list(Records_voice_recorder.objects.filter(pk = record.id).values_list('id', 'name', 'audio'))
    
    to = {
        'answer': answer
    }    
    
    return JsonResponse(to, status=status.HTTP_200_OK, safe=False)


@api_view(['GET', 'POST', 'DELETE'])
def post_recordeds_voice_audio(request):
    body_unicode    = request.body.decode().replace("'", '"')
    data            = json.loads(body_unicode) 

    id              = data['id']
    rec             = Records_voice_recorder.objects.get(pk = id)
    rec.data_json   = body_unicode
    rec.time        = data['info_audio']['seconds']
    rec.recognition = True
    rec.save()

    to = {
        'answer': 'ok'
    }    
    return JsonResponse(to, status=status.HTTP_200_OK, safe=False)


@api_view(['GET', 'POST', 'DELETE'])
def post_recordeds_voice_audio_find(request):
    body_unicode    = request.body.decode().replace("'", '"')
    data            = json.loads(body_unicode) 

    name_file       = data['name']
    user_login      = data['user']
    counts          = Records_voice_recorder.objects.filter(name = name_file).filter(user__username = user_login).count()
    
    to = {
        'answer': counts
    }    

    return JsonResponse(to, status=status.HTTP_200_OK, safe=False)


@api_view(['GET', 'POST', 'DELETE'])
def post_recordeds_voice_audio_portative_programm(request):
    user_login          = ""
    counts              = 0
    version_programm    = 1

    if 'user' in request.headers:
        
        user_login      = request.headers['user']
        sound_len = 0
        try:
            sound_len       = int(request.headers['soundlentime'].split('.')[0])
        except:
            sound_len       = int(request.headers['soundlentime'])

        users_object        = User.objects.filter(username = user_login)
        version_programm    = int(request.headers.get('versions', '1'))

        if len(users_object) == 1:
            user = users_object[0]
            file_objects = request.FILES.getlist('file_audio')
            for file_object in file_objects: 
                name = file_object.name.lower()
                if name.find('.wav') > 0 or name.find('.mp3') > 0: 
                    date        = ''
                    date        = get_date_in_name(name)
                    new_record  = Records_voice_recorder()
                    
                    if date != '':
                        new_record.date = date
                    else:
                        new_record.date = DT.datetime.now()

                    try:
                        date_create = request.headers['date_create']
                        if date_create != '':
                            new_record.date_create = date_create
                        else:
                            new_record.date_create = DT.datetime.now()
                    except:
                        s =1
                       
                    new_record.audio            = file_object
                    new_record.name             = name
                    new_record.user             = user
                    new_record.time             = sound_len
                    new_record.dateRecognitions = DT.datetime.now()
                    new_record.version_programm = version_programm
                    new_record.save()

                counts  = Records_voice_recorder.objects.filter(name = name).filter(user__username = user_login).count()
        
    to = {
        'answer': counts
    }    

    return JsonResponse(to, status=status.HTTP_200_OK, safe=False)


def get_date_in_name(name):
    date = ''
    dates = name.split('.')
    if len(dates) == 2:
        date_str = dates[0]
        if len(date_str) == 14:
            try:
                date = DT.datetime.strptime(date_str,'%Y%m%d%H%M%S')
            except:
                date = '' 
    return date 


# Запрос данных к распознованию звонков из очереди
@api_view(['GET', 'POST', 'DELETE'])
def get_call_queue(request):
    
    '''
    records = Telephony_records_queue.objects.order_by('date')
    for rec in records:
        rec.data_json = ''
        rec.error = False
        rec.save()
    '''
    records = Telephony_records_queue.objects.filter(data_json = '').filter(error = False).order_by('date')
    answer = {
        'work'          : False 
    }

    if len(records) > 0:
        record      = records[0]
        record.date = DT.datetime.now()
        name_file   = r'\\a01srvfs\\PBX\\A15\\sounds\\' + record.record + '.mp3' 
        # and os.path.getsize(name_file) > 0
        #if os.path.exists(name_file):
        answer = {
                'id'                : record.id,
                'path'              : name_file,
                'work'              : True,
                'error'             : '' 
            }            
        #else:
        #    params = {
        #        'work'  : False,
        #        'error' : 'Запись на диске не найдена. Приносим извинения.'
        #    }
        #    record.error        = True
        #    record.data_json    = str(params)
        record.save() 
    return JsonResponse(answer, status = status.HTTP_200_OK, safe = False)

# Запись данных распознования звонков из очереди
@api_view(['GET', 'POST', 'DELETE'])
def post_call_queue(request):
    
    body_unicode    = request.body.decode().replace("'", '"')
    data            = json.loads(body_unicode) 
    id              = data['id']
    info_audio      = data['info_audio']
    
    chanel_1 = data['chanel_1']
    chanel_2 = data['chanel_2']
    
    decoded_data_1 = ContentFile(base64.b64decode(chanel_1), name='temp1.' + 'png')
    decoded_data_2 = ContentFile(base64.b64decode(chanel_2), name='temp2.' + 'png')

    record              = Telephony_records_queue.objects.get(pk = id)
    record.data_json    = data
    record.duration     = int(info_audio['seconds'])
    record.img_chanel_1 = decoded_data_1
    record.img_chanel_2 = decoded_data_2
    record.save()

    answer = {
           'ok' : True
        }
    return JsonResponse(answer, status = status.HTTP_200_OK, safe = False)



# Запрос данных к распознованию из очереди
@api_view(['GET', 'POST', 'DELETE'])
def get_records_queue(request):
    records = Records_voice_recorder_queue.objects.filter(data_json = '').filter(error = False).order_by('date')
    answer = {
        'work'          : False 
    }

    if len(records) > 0:
        record      = records[0]
        record.date = DT.datetime.now()
        if os.path.exists(record.records.audio.path) and os.path.getsize(record.records.audio.path) > 0:
            answer = {
                'id'                : record.id,
                'time_start'        : record.time_start.strftime("%Y-%m-%d %H:%M:%S"),
                'time_end'          : record.time_end.strftime("%Y-%m-%d %H:%M:%S"),
                'path'              : record.records.audio.url,
                'record_date_start' : record.records.date.strftime("%Y-%m-%d %H:%M:%S"),
                'work'              : True,
                'error'             : '' 
            }            
        else:
            params = {
                'work'  : False,
                'error' : 'Запись на диске не найдена. Приносим извинения.'
            }
            record.error        = True
            record.data_json    = str(params)
        record.save() 
    return JsonResponse(answer, status = status.HTTP_200_OK, safe = False)

# Запись данных распознования из очереди
@api_view(['GET', 'POST', 'DELETE'])
def post_records_queue(request):
    body_unicode    = request.body.decode().replace("'", '"')
    data            = json.loads(body_unicode) 
    id              = data['id']
    
    record              = Records_voice_recorder_queue.objects.get(pk = id)
    record.data_json    = data
    record.save()

    answer = {
           'ok' : True
        }
    return JsonResponse(answer, status = status.HTTP_200_OK, safe = False)


###
##
# Отдача информации по каталогам авто ру
@api_view(['GET', 'POST', 'DELETE'])
def catalog_mark(request):

    marks = AutoruMark.objects.all()
    if "id_mark" in request.GET:
        marks = marks.filter(idSite=request.GET.get("id_mark"))
    
    if "name" in request.GET:
        marks = marks.filter(name__icontains = request.GET.get("name")) | marks.filter(nameEn__icontains = request.GET.get("name"))  

    catalog_mark_serializer = AutoruMarkSerializer(list(marks), many=True)
    
    to = {
        'marks': catalog_mark_serializer.data
    }
        
    return JsonResponse(to, status=status.HTTP_200_OK, safe=False)


@api_view(['GET', 'POST', 'DELETE'])
def catalog_model(request):

    model = AutoruModel.objects.all()
    if "id_mark" in request.GET:
        model = model.filter(mark__idSite = request.GET.get("id_mark"))
    if "name_mark" in request.GET:
        model = model.filter(mark__name__icontains = request.GET.get("name_mark")) | model.filter(mark__nameEn__icontains = request.GET.get("name_mark"))
    if "id_model" in request.GET:
        model = model.filter(idSite=request.GET.get("id_model"))
    
    catalog_model_serializer = AutoruModelSerializer(list(model), many=True)
    
    to = {
        'model': catalog_model_serializer.data
    }
        
    return JsonResponse(to, status=status.HTTP_200_OK, safe=False)


@api_view(['GET', 'POST', 'DELETE'])
def catalog_modification(request):

    modification = AutoruModification.objects.all()
    if "id_mark" in request.GET:
        modification = modification.filter(model__mark__idSite = request.GET.get("id_mark"))
    if "id_model" in request.GET:
        modification = modification.filter(model__idSite = request.GET.get("id_model"))
    if "id_modification" in request.GET:
        modification = modification.filter(idSite = request.GET.get("id_modification"))
    
    catalog_modification_serializer = AutoruModificationSerializer(list(modification), many=True)
    
    to = {
        'modification': catalog_modification_serializer.data
    }
        
    return JsonResponse(to, status=status.HTTP_200_OK, safe=False)


@api_view(['GET'])
def catalog_modification_tech_info(request):

    list_info = list()
    if "id_modification" in request.GET:
        id_modification = request.GET.get("id_modification")
        modification = AutoruModification.objects.get(idSite = id_modification)
        specifications = AutoruModificationSpecifications.objects.filter(modification = modification)
        for specification in specifications:
            modification_infos  = RefSpecificationData.objects.filter(modification_specifications = specification)
            id_complectation    = 0
            name_complectation  = ''
            if specification.complectation != None:
                id_complectation    = specification.complectation.idSite
                name_complectation  = specification.complectation.name                 
            
            list_datas = list()
            for modification_info in modification_infos:
                if modification_info.specification != None:
                    info = {
                        'item'  : modification_info.specification.name, 
                        'value' : modification_info.value
                    }
                    list_datas.append(info) 
            spec = {
                'name'                  : specification.name,
                'id_modification'       : id_modification,
                'id_complectation'      : id_complectation,
                'name_complectation'    : name_complectation,
                'infos'                 : list_datas
            }
            list_info.append(spec)
    to = {
        'list_info': list_info
    }
        
    return JsonResponse(to, status=status.HTTP_200_OK, safe=False)



@api_view(['GET', 'POST', 'DELETE'])
def catalog_complectation(request):

    complectation = AutoruComplectation.objects.all()
    if "id_mark" in request.GET:
        complectation = complectation.filter(modification__model__mark__idSite = request.GET.get("id_mark"))
    if "id_model" in request.GET:
        complectation = complectation.filter(modification__model__idSite = request.GET.get("id_model"))
    if "id_modification" in request.GET:
        complectation = complectation.filter(modification__idSite = int(request.GET.get("id_modification")))
    if "id_complectation" in request.GET:
        complectation = complectation.filter(idSite=request.GET.get("id_complectation"))
    
    catalog_complectation_serializer = AutoruComplectationSerializer(list(complectation), many=True)
    
    to = {
        'complectation': catalog_complectation_serializer.data
    }
        
    return JsonResponse(to, status=status.HTTP_200_OK, safe=False)


###
##
# Временный обмен с корсавто
@api_view(['GET', 'POST', 'DELETE'])
def refresh_rlk_bu(request):
    
    body_unicode = request.body.decode()
    data = json.loads(body_unicode)
    
    for doc in data:
        jsonUnit    = doc.get('Unit')
        unitUin     = jsonUnit.get('Uin')
        unitL = RefUnit.objects.filter(uin = unitUin)

        typeRLK = ''

        if 'Type' in doc:
            typeRLK = doc.get('Type')

        if len(list(unitL)) == 0:
            unitO = RefUnit()
            unitO.uin = unitUin
            unitO.name = jsonUnit.get('Name')
            unitO.buauto = True
            unitO.save()
        else:
            unitO = unitL[0]

        jsonMaster = doc.get('Master')
        masterUin = jsonMaster.get('Uin')
        masterL = RefStaff.objects.filter(uin = masterUin)

        if len(list(masterL)) == 0:
            masterO = RefStaff()
        else:
            masterO = masterL[0]
        masterO.uin = masterUin
        masterO.name = jsonMaster.get('Name')
        masterO.domain_login = jsonMaster.get('Domain')
        masterO.save()

        masterO.units.clear()
        masterO.units.add(unitO)
        masterO.save()
        
        docUIN = doc.get('Uin')

        docL = DocRLK.objects.filter(uin = docUIN).filter(unit = unitO)
        
        if len(list(docL)) == 0:
            docO = DocRLK()
        else:
            docO = docL[0]

        if len(typeRLK) > 0:
            typeRLKobjectCount = RefTypeDocRLK.objects.filter(name__iregex = typeRLK).count()
            if typeRLKobjectCount > 0:
                docO.type = RefTypeDocRLK.objects.filter(name__iregex = typeRLK)[0]
            else:
                refTypeDocRLK = RefTypeDocRLK()
                refTypeDocRLK.name = typeRLK
                refTypeDocRLK.save()
                docO.type = refTypeDocRLK

        docO.unit           = unitO
        docO.staff          = masterO
        docO.uin            = docUIN
        docO.clientName     = doc.get('ClientName')
        docO.nomer          = doc.get('Nomer')
        docO.dataTime       = doc.get('DataTime')
        docO.timeStr        = doc.get('TimeStr')
        docO.tradeInModel   = doc.get('TradeInModel')
        
        if 'DateEnd' in doc:
            docO.dataEnd          = doc['DateEnd'] 
        if 'DateCreate' in doc:
            docO.dataTimeCreate   = doc['DateCreate']
        if 'IsMissed' in doc:
            docO.is_missed        = doc['IsMissed']
        
        docO.contacType           = get_contactType(doc['ContactType'])
        docO.commentAdministrator = doc['CommentAdministrator']
        docO.commentManager       = doc['CommentManager']

        docO.save()

        to = {
            'answer': 'ok'
        }
        
    return JsonResponse(to, status=status.HTTP_200_OK)

'''
def create_opros_sale(request):
    try: 
        body_unicode = request.body.decode().replace("'", '"')
        doc = json.loads(body_unicode) 
        
    ######## Unit
        jsonUnit = doc.get('Unit')
        unitUin = jsonUnit.get('Uin')
        unitL = RefUnit.objects.filter(uin = unitUin)

        if len(list(unitL)) == 0:
            unitO = RefUnit()
            unitO.uin = unitUin
            unitO.name = jsonUnit.get('Name')
            unitO.save()
        else:
            unitO = unitL[0]

    ######## Master
        jsonMaster = doc.get('Master')
        masterUin = jsonMaster.get('Uin')
        masterL = RefStaff.objects.filter(uin = masterUin)

        if len(list(masterL)) == 0:
            masterO = RefStaff()
            masterO.uin     = masterUin
            masterO.name    = jsonMaster.get('Name')
            masterO.save()
        else:
            masterO = masterL[0]

    ######## Customer
        customerJson = doc.get("Customer")        
        customers = RefCustomer.objects.filter(phoneNorm = customerJson.get("PhoneNorm"))
        if len(list(customers)) == 0:
            customer = RefCustomer()
            customer.name = customerJson.get("Name") 
            customer.phoneNorm = customerJson.get("PhoneNorm")
            customer.email = customerJson.get("Email")
            customer.save()
        else:
            customer = customers[0]

    ######## Car
        carJson = doc.get("Car")
        car = getCar(carJson.get("Vin"), carJson.get("Mark"), carJson.get("Model"))

    ######## Document
        docUIN = doc.get('Uin')
        docL = DocCarShipment.objects.filter(uin = docUIN).filter(unit = unitO)
        if len(list(docL)) == 0:
            docO = DocCarShipment()
        else:
            docO = docL[0]

    ######## Refresh
        docO.unit = unitO
        docO.staff  = masterO
        docO.uin = docUIN
        docO.nomer = doc.get('Nomer')
        docO.client = customer
        docO.cars = car
        docO.save()

        opros = OprosSale.objects.filter(document = docO)
        uin = ''
        if len(list(opros)) == 0:
            oprosDoc = OprosSale()
            oprosDoc.document = docO
            oprosDoc.dataTime = datetime.datetime.now()
            oprosDoc.uin = docUIN.replace('-','')
            oprosDoc.save()
            uin = str(oprosDoc.uin) 
        else:
            oprosDoc = opros[0]
            uin = str(oprosDoc.uin)

    ######## Answer
        to = {
            'answer': 'ok',
            'url': str(uin)
        }
            
        return JsonResponse(to, status=status.HTTP_200_OK)
    
    except:
        return JsonResponse("", status=status.HTTP_200_OK)    



@api_view(['POST'])
def refresh_opros(request):
    try: 
        body_unicode = request.body.decode().replace("'", '"')
        doc = json.loads(body_unicode) 
        
    ######## Unit
        jsonUnit = doc.get('Unit')
        dataTime = doc.get('Date')
        unitUin = jsonUnit.get('Uin')
        unitL = RefUnit.objects.filter(uin = unitUin)

        if len(list(unitL)) == 0:
            unitO = RefUnit()
            unitO.uin = unitUin
            unitO.name = jsonUnit.get('Name')
            unitO.save()
        else:
            unitO = unitL[0]
        
        #currentdate = datetime.datetime.today()
        #currentdateN = currentdate.combine(currentdate.date(), currentdate.min.time())
    ######## Opros
        oprosList = OprosZN.objects.filter(document__unit = unitO).filter(dataClose__gte = dataTime)
        oprosListJson = list()
        for opros in oprosList:
            oprosJson = {
                "UinZN": opros.document.uin,
                "v1": opros.v1,
                "v2": opros.v2,
                "v3": opros.v3,
                "v4": opros.v4,
                "v5": opros.v5,
                "v6": opros.v6,
                "v7": opros.v7,
                "v8": opros.v8,
                "dataClose": opros.dataClose.strftime("%Y%m%d%H%M%S"),
                "uin": opros.uin,
            }
            oprosListJson.append(oprosJson)
    ######## OprosSale
        oprosListSale = OprosSale.objects.filter(document__unit = unitO).filter(dataClose__gte = dataTime)
        oprosListSaleJson = list()
        for oprosSale in oprosListSale:
            oprosSaleJson = {
                "UinSale": oprosSale.document.uin,
                "v1": oprosSale.v1,
                "v2": oprosSale.v2,
                "v3": oprosSale.v3,
                "v4": oprosSale.v4,
                "v5": oprosSale.v5,
                "v6": oprosSale.v6,
                "v7": oprosSale.v7,
                "dataClose": oprosSale.dataClose.strftime("%Y%m%d%H%M%S"),
                "uin": oprosSale.uin,
            }
            oprosListSaleJson.append(oprosSaleJson)
    
    ######## Answer
        to = {
            'answer': oprosListJson,
            'oprosSale': oprosListSaleJson,
            'count': len(oprosList)
        }
            
        return JsonResponse(to, status=status.HTTP_200_OK)
    
    except:
        return JsonResponse("", status=status.HTTP_200_OK)    


@api_view(['GET', 'POST', 'DELETE'])
def refresh_rlk(request):
    
    body_unicode = request.body.decode().replace("'", '"')
    data = json.loads(body_unicode)
    
    for doc in data:
        jsonUnit = doc.get('Unit')
        unitUin = jsonUnit.get('Uin')
        typeRLK = ''

        if 'Type' in doc:
            typeRLK = doc.get('Type')

        unitL = RefUnit.objects.filter(uin = unitUin)

        if len(list(unitL)) == 0:
            unitO = RefUnit()
            unitO.uin = unitUin
            unitO.name = jsonUnit.get('Name')
            unitO.save()
        else:
            unitO = unitL[0]

        jsonMaster = doc.get('Master')
        masterUin = jsonMaster.get('Uin')
        masterL = RefStaff.objects.filter(uin = masterUin)

        if len(list(masterL)) == 0:
            masterO = RefStaff()
            masterO.uin = masterUin
            masterO.unit = unitO 
            masterO.name = jsonMaster.get('Name')
            masterO.save()
        else:
            masterO = masterL[0]

        
        docUIN = doc.get('Uin')

        docL = DocRLK.objects.filter(uin = docUIN).filter(unit = unitO)
        
        if len(list(docL)) == 0:
            docO = DocRLK()
        else:
            docO = docL[0]

        if len(typeRLK) > 0:
            typeRLKobjectCount = RefTypeDocRLK.objects.filter(name__iregex = typeRLK).count()
            if typeRLKobjectCount > 0:
                docO.type = RefTypeDocRLK.objects.filter(name__iregex = typeRLK)[0]
            else:
                refTypeDocRLK = RefTypeDocRLK()
                refTypeDocRLK.name = typeRLK
                refTypeDocRLK.save()
                docO.type = refTypeDocRLK

        docO.unit = unitO
        docO.staff = masterO
        docO.uin = docUIN
        docO.clientName = doc.get('ClientName')
        docO.nomer = doc.get('Nomer')
        docO.dataTime = doc.get('DataTime')
        docO.timeStr = doc.get('TimeStr')
        docO.save()

        to = {
            'answer': 'ok'
        }
        
    return JsonResponse(to, status=status.HTTP_200_OK)


@api_view(['GET', 'POST', 'DELETE'])
def refresh_sale(request):
    
    body_unicode = request.body.decode().replace("'", '"')
    data = json.loads(body_unicode)
    
    for doc in data:
        jsonUnit = doc.get('Unit')
        unitUin = jsonUnit.get('Uin')

        unitL = RefUnit.objects.filter(uin = unitUin)

        if len(list(unitL)) == 0:
            unitO = RefUnit()
            unitO.uin = unitUin
            unitO.name = jsonUnit.get('Name')
            unitO.save()
        else:
            unitO = unitL[0]

        jsonMaster = doc.get('Master')
        masterUin = jsonMaster.get('Uin')
        masterL = RefStaff.objects.filter(uin = masterUin)

        if len(list(masterL)) == 0:
            masterO = RefStaff()
            masterO.uin = masterUin
            masterO.unit = unitO 
            masterO.name = jsonMaster.get('Name')
            masterO.save()
        else:
            masterO = masterL[0]

        
        docUIN = doc.get('Uin')

        docL = DocRLK.objects.filter(uin = docUIN).filter(unit = unitO)
        
        if len(list(docL)) == 0:
            docO = DocRLK()
        else:
            docO = docL[0]

        docO.unit = unitO
        docO.staff = masterO
        docO.uin = docUIN
        docO.clientName = doc.get('ClientName')
        docO.nomer = doc.get('Nomer')
        docO.dataTime = doc.get('DataTime')
        docO.timeStr = doc.get('TimeStr')
        docO.save()

        to = {
            'answer': 'ok'
        }
        
    return JsonResponse(to, status=status.HTTP_200_OK)


@api_view(['GET', 'POST', 'DELETE'])
def refresh_rlk_bu(request):
    
    body_unicode = request.body.decode().replace("'", '"')
    data = json.loads(body_unicode)
    
    for doc in data:
        jsonUnit = doc.get('Unit')
        unitUin = jsonUnit.get('Uin')

        unitL = RefUnit.objects.filter(uin = unitUin)

        typeRLK = ''

        if 'Type' in doc:
            typeRLK = doc.get('Type')

        if len(list(unitL)) == 0:
            unitO = RefUnit()
            unitO.uin = unitUin
            unitO.name = jsonUnit.get('Name')
            unitO.buauto = True
            unitO.save()
        else:
            unitO = unitL[0]

        jsonMaster = doc.get('Master')
        masterUin = jsonMaster.get('Uin')
        masterL = RefStaff.objects.filter(uin = masterUin)

        if len(list(masterL)) == 0:
            masterO = RefStaff()
            masterO.uin = masterUin
            masterO.unit = unitO 
            masterO.name = jsonMaster.get('Name')
            masterO.save()
        else:
            masterO = masterL[0]

        
        docUIN = doc.get('Uin')

        docL = DocRLK.objects.filter(uin = docUIN).filter(unit = unitO)
        
        if len(list(docL)) == 0:
            docO = DocRLK()
        else:
            docO = docL[0]

        if len(typeRLK) > 0:
            typeRLKobjectCount = RefTypeDocRLK.objects.filter(name__iregex = typeRLK).count()
            if typeRLKobjectCount > 0:
                docO.type = RefTypeDocRLK.objects.filter(name__iregex = typeRLK)[0]
            else:
                refTypeDocRLK = RefTypeDocRLK()
                refTypeDocRLK.name = typeRLK
                refTypeDocRLK.save()
                docO.type = refTypeDocRLK

        docO.unit = unitO
        docO.staff = masterO
        docO.uin = docUIN
        docO.clientName = doc.get('ClientName')
        docO.nomer = doc.get('Nomer')
        docO.dataTime = doc.get('DataTime')
        docO.timeStr = doc.get('TimeStr')
        docO.tradeInModel = doc.get('TradeInModel')
        docO.save()

        to = {
            'answer': 'ok'
        }
        
    return JsonResponse(to, status=status.HTTP_200_OK)


@api_view(['GET', 'POST', 'DELETE'])
def refresh(request):
    
    body_unicode = request.body.decode().replace("'", '"')
    data = json.loads(body_unicode)
    answer = ""
    typeRequest = data.get("Type")
    
    if typeRequest == "Customer":
        customerJson = data.get("Customer")

        customers = RefCustomer.objects.filter(phoneNorm = customerJson.get("PhoneNorm"))
        
        if customers.count() == 0:
            customer = RefCustomer()
            customer.name = customerJson.get("Name") 
            customer.phoneNorm = customerJson.get("PhoneNorm")
            customer.email = customerJson.get("Email")
            customer.save()
            answer = "add " + str(customer.id)
        else:
            answer = "refresh"

            
        to = {
            'answer': 'ok'
        }
        
    return JsonResponse(to, status=status.HTTP_200_OK)


def getCar(vin_nomer, mark, model):
    cars = RefCars.objects.filter(name = vin_nomer)
    if len(list(cars)) == 0:
        car = RefCars()
        car.name = vin_nomer 
        car.mark = mark
        car.model = model
        car.save()
    else:
        car = cars[0]
    return car    

"""

@api_view(['GET', 'POST', 'DELETE'])
def user_xls(request):
    params = {}
    staffs = list()

    file = request.FILES['xlsfile']
    path = default_storage.save('temp/somename.xls', ContentFile(file.read()))
    tmp_file = os.path.join(settings.MEDIA_ROOT, path)
    rb = xlrd.open_workbook(tmp_file)
    sheet = rb.sheet_by_index(0)
    for rownum in range(sheet.nrows):
        row = sheet.row_values(rownum)
        name = ""
        password = ""
        fio = ""
        if rownum != 0:
            i = 0
            for c_el in row:
                if i == 0:
                    name = c_el
                elif i == 1:
                    password = c_el
                elif i == 2:
                    fio = c_el
                i = i + 1
        staff = {
            'name': name,
            'password': password,
            'fio': fio
        }
        staffs.append(staff)
    params = {"staffs": staffs}
    for staff in staffs:
        if len(staff['name']) > 0:
            us = User.objects.filter(username = staff['name']).count()
            if us == 0:
                us = User()
                us.username = staff['name']
                us.last_name = staff['fio']
                us.is_staff = True
                us.is_active = True
                us.is_superuser = True
                us.set_password(staff['password'])
                us.save()
            else:
                us = User.objects.filter(username = staff['name'])[0]
                us.set_password(staff['password'])
                us.save()
            profil = ProfilesUser.objects.get(id=us.id)
            profil.view_checklist = True
            profil.save()  

    return render(request, 'up.html', {'params': params})



@api_view(['GET', 'POST', 'DELETE'])
def catalog_mark(request):

    marks = AutoruMark.objects.all()
    if "id_mark" in request.GET:
        marks = marks.filter(idSite=request.GET.get("id_mark"))
    
    catalog_mark_serializer = AutoruMarkSerializer(list(marks), many=True)
    
    to = {
        'marks': catalog_mark_serializer.data
    }
        
    return JsonResponse(to, status=status.HTTP_200_OK, safe=False)


@api_view(['GET', 'POST', 'DELETE'])
def catalog_model(request):

    model = AutoruModel.objects.all()
    if "id_mark" in request.GET:
        model = model.filter(mark__idSite=request.GET.get("id_mark"))
    if "name_mark" in request.GET:
        model = model.filter(mark__name=request.GET.get("name_mark"))
    if "id_model" in request.GET:
        model = model.filter(idSite=request.GET.get("id_model"))
    
    catalog_model_serializer = AutoruModelSerializer(list(model), many=True)
    
    to = {
        'model': catalog_model_serializer.data
    }
        
    return JsonResponse(to, status=status.HTTP_200_OK, safe=False)


@api_view(['GET', 'POST', 'DELETE'])
def catalog_modification(request):

    modification = AutoruModification.objects.all()
    if "id_mark" in request.GET:
        modification = modification.filter(model__mark__idSite=request.GET.get("id_mark"))
    if "id_model" in request.GET:
        modification = modification.filter(model__idSite=request.GET.get("id_model"))
    if "id_modification" in request.GET:
        modification = modification.filter(idSite=request.GET.get("id_modification"))
    
    catalog_modification_serializer = AutoruModificationSerializer(list(modification), many=True)
    
    to = {
        'modification': catalog_modification_serializer.data
    }
        
    return JsonResponse(to, status=status.HTTP_200_OK, safe=False)


@api_view(['GET', 'POST', 'DELETE'])
def catalog_complectation(request):

    complectation = AutoruComplectation.objects.all()
    if "id_mark" in request.GET:
        complectation = complectation.filter(modification__model__mark__idSite=request.GET.get("id_mark"))
    if "id_model" in request.GET:
        complectation = complectation.filter(modification__model__idSite=request.GET.get("id_model"))
    if "id_modification" in request.GET:
        complectation = complectation.filter(modification__idSite=request.GET.get("id_modification"))
    if "id_�omplectation" in request.GET:
        complectation = complectation.filter(idSite=request.GET.get("id_�omplectation"))
    
    catalog_�omplectation_serializer = AutoruComplectationSerializer(list(complectation), many=True)
    
    to = {
        'complectation': catalog_�omplectation_serializer.data
    }
        
    return JsonResponse(to, status=status.HTTP_200_OK, safe=False)
"""
'''

######
#####
####
###
##
# Создание анкеты для онлайн записи
@api_view(['POST'])
def create_online(request):
    try: 
        
        body_unicode    = request.body.decode().replace("'", '"')
        data            = json.loads(body_unicode) 
        
        ref_unit        = get_unit(data["Unit"])
        ref_customer    = get_сustomer(data["Customer"]) 
        ref_cars        = get_car(data['Car'])
        
    ######## Document
        docUIN = data["Uin"]

        docOnlines = Online_doc.objects.filter(uin = docUIN)
        
        uin = ''
        
        if len(list(docOnlines)) == 0:
            docOnline                   = Online_doc()
            docOnline.dataTimeCreate    = DT.datetime.now()
            docOnline.uin               = docUIN
            docOnline.customer          = ref_customer           
            docOnline.clientName        = ref_customer.name
            docOnline.clientPhone       = ref_customer.phoneNorm
            docOnline.unit              = ref_unit 
            docOnline.cars              = ref_cars
            docOnline.save()
        else:
            docOnline = docOnlines[0]

        ######## Answer
        to = {
            'answer'    : 'ok',
            'url'       : str(docOnline.uid)
        }

        return JsonResponse(to, status=status.HTTP_200_OK)
    
    except:
        return JsonResponse("", status=status.HTTP_200_OK)

# Создание документа для подтверждения записи на сервис
@api_view(['POST'])
def create_records_online_doc(request):
    try: 
        
        body_unicode    = request.body.decode().replace("'", '"')
        data            = json.loads(body_unicode) 
        
        ref_customer    = ''
        ref_cars        = ''

        ref_unit        = get_unit(data["Unit"])
        
        customer    = False
        car         = False
        if len(data["Customer"]) > 0:
            ref_customer    = get_сustomer(data["Customer"])
            customer        = True
        if len(data['Car']) > 0:
            ref_cars        = get_car(data['Car'])
            car             = True
        
    ######## Document
        docUIN = data["Uin"]

        docOnlines = Records_online_doc.objects.filter(uin = docUIN)
        
        if len(list(docOnlines)) == 0:
            docOnline                   = Records_online_doc()
            docOnline.dataTimeCreate    = DT.datetime.now()
            docOnline.dataTimeRecord    = data['DataTime']
            docOnline.uin               = docUIN
            if customer:
                docOnline.customer          = ref_customer           
                docOnline.clientName        = ref_customer.name
                docOnline.clientPhone       = ref_customer.phoneNorm
            docOnline.unit              = ref_unit 
            if car:
                docOnline.cars              = ref_cars
            docOnline.save()
        else:
            docOnline = docOnlines[0]

        url = str(docOnline.short_url)
        ######## Answer
        to = {
            'answer'    : 'ok',
            'url'       : url
        }

        return JsonResponse(to, status=status.HTTP_200_OK)
    
    except:
        return JsonResponse("", status=status.HTTP_200_OK)


######
#####
####
###
##
# Работа с аудио
@api_view(['GET', 'POST', 'DELETE'])
def get_recordeds_voice_audio_convert(request):
    if request.method == 'GET':
        records = list(Records_voice_recorder.objects.filter(time__lte = 0).exclude(error = True).order_by('id').values_list('id', 'name', 'audio'))
        to = {
            'answer': records
        }
    elif request.method == 'POST':  
        body_unicode = request.body.decode().replace("'", '"')
        data = json.loads(body_unicode) 

        id          = data['id']
        duration    = data['duration']
        
        rec         = Records_voice_recorder.objects.get(pk = id)
        rec.time    = duration
        
        if 'error' in data:
            rec.error   = data['error']
        
        rec.save()
        
        to = {
            'answer': str(id) 
        }

    return JsonResponse(to, status=status.HTTP_200_OK, safe=False)

@csrf_exempt
@api_view(['POST',])
def post_recordeds_voice_audio_convert(request):
    body_unicode = request.body.decode().replace("'", '"')
    data = json.loads(body_unicode) 

    id          = data['id']
    duration    = data['duration']
    error       = data['error']
    
    rec                     = Records_voice_recorder.objects.get(pk = id)
    rec.dateRecognitions    = DT.datetime.now()
    rec.time                = duration
    rec.error               = error
    rec.save()
    
    to = {
        'answer': str(id) 
    }

    return JsonResponse(to, status=status.HTTP_200_OK, safe=False)

######
#####
####
###
##
# Создание опроса
@api_view(['POST',])
def create_opros(request):
    
    body_unicode    = request.body.decode()
    data            = json.loads(body_unicode)

    #Заказ - наряд
    doc_zn          = get_order(data)
    doc_zn.active   = True
    doc_zn.save()
     
    docs_opros      = DocOprosZN.objects.filter(zn = doc_zn)
    
    if len(docs_opros) == 0:
        doc_opros = DocOprosZN()
    else:
        doc_opros = docs_opros[0]
    
    doc_opros.dataTime      = DT.datetime.now()
    doc_opros.zn            = doc_zn
    doc_opros.uin           = doc_zn.uin
    doc_opros.save()

    to = {
        'answer'    : 'ok',
        'url'       : str(doc_zn.uin)
    }
        
    return JsonResponse(to, status=status.HTTP_200_OK)     

@api_view(['POST',])
def create_opros_sale(request):
    try: 
        body_unicode = request.body.decode().replace("'", '')
        data = json.loads(body_unicode) 

        docCarShipment  = get_shipment(data)
        docs_opros      = DocOprosCarShipment.objects.filter(shipment = docCarShipment)
        if len(docs_opros) == 0:
            doc_opros = DocOprosCarShipment()
        else:
            doc_opros = docs_opros[0]
        doc_opros.dataTime      = DT.datetime.now()
        doc_opros.shipment      = docCarShipment
        doc_opros.uin           = docCarShipment.uin
        doc_opros.save()
    
        to = {
            'answer': 'ok',
            'url': str(docCarShipment.uin)
        }
            
        return JsonResponse(to, status=status.HTTP_200_OK)
    
    except:
        return JsonResponse("", status=status.HTTP_200_OK)    

@api_view(['POST'])
def create_opros_sale_bu(request):
    try: 
        try:
            body_unicode = request.body.decode().replace("'", '"')
            doc = json.loads(body_unicode) 
        except:
            body_unicode = request.body.decode()
            doc = json.loads(body_unicode)    
    ######## Unit
        jsonUnit    = doc.get('Unit')
        unitUin     = jsonUnit.get('Uin')
        unitL       = RefUnit.objects.filter(uin = unitUin)

        if len(list(unitL)) == 0:
            unitO       = RefUnit()
            unitO.uin   = unitUin
            unitO.name  = jsonUnit.get('Name')
            unitO.buauto = True
            unitO.save()
        else:
            unitO = unitL[0]
            unitO.uin   = unitUin
            unitO.name  = jsonUnit.get('Name')
            unitO.buauto = True
            unitO.save()

    ######## Master
        jsonMaster  = doc.get('Master')
        masterUin   = jsonMaster.get('Uin')
        masterL     = RefStaff.objects.filter(uin = masterUin)

        if len(list(masterL)) == 0:
            masterO         = RefStaff()
            masterO.uin     = masterUin
            masterO.name    = jsonMaster.get('Name')
            masterO.save()
        else:
            masterO = masterL[0]

    ######## Customer
        customerJson = doc.get("Customer")        
        customers = RefCustomer.objects.filter(phoneNorm = customerJson.get("PhoneNorm"))
        if len(list(customers)) == 0:
            customer = RefCustomer()
            customer.name       = customerJson.get("Name") 
            customer.phoneNorm  = customerJson.get("PhoneNorm")
            customer.email      = customerJson.get("Email")
            customer.save()
        else:
            customer = customers[0]

    ######## Car
        carJson = doc.get("Car")
        car = get_car(carJson)

    ######## Document
        docUIN = doc.get('Uin')
        docL = DocCarShipment.objects.filter(uin = docUIN).filter(unit = unitO)
        if len(list(docL)) == 0:
            docO = DocCarShipment()
        else:
            docO = docL[0]

    ######## Refresh
        docO.unit = unitO
        docO.staff  = masterO
        docO.uin = docUIN
        docO.nomer = doc.get('Nomer')
        docO.client = customer
        docO.cars = car
        docO.save()

        opros = DocOprosCarShipment.objects.filter(shipment = docO)
        uin = ''
        if len(list(opros)) == 0:
            oprosDoc = DocOprosCarShipment()
            oprosDoc.shipment   = docO
            oprosDoc.dataTime   = DT.datetime.now()
            oprosDoc.uin        = docUIN
            oprosDoc.save()
            uin = str(oprosDoc.uin) 
        else:
            oprosDoc = opros[0]
            uin = str(oprosDoc.uin)

    ######## Answer
        to = {
            'answer': 'ok',
            'url': str(uin)
        }
            
        return JsonResponse(to, status=status.HTTP_200_OK)
    
    except:
        return JsonResponse("", status=status.HTTP_200_OK)

######
#####
####
###
##
# Обновление опросов 
@api_view(['POST'])
def refresh_opros(request):
    try: 
        body_unicode = request.body.decode().replace("'", '"')
        
        doc = json.loads(body_unicode) 
        
    ######## Unit
        jsonUnit    = doc.get('Unit')
        dataTime    = doc.get('Date')
        unitUin     = jsonUnit.get('Uin')
        unitL       = RefUnit.objects.filter(uin = unitUin)

        if len(list(unitL)) == 0:
            unitO = RefUnit()
            unitO.uin = unitUin
            unitO.name = jsonUnit.get('Name')
            unitO.save()
        else:
            unitO = unitL[0]
        
        #currentdate = datetime.datetime.today()
        #currentdateN = currentdate.combine(currentdate.date(), currentdate.min.time())
    ######## Opros
        v1_name = DocOprosZN._meta.get_field('v1')._verbose_name
        v2_name = DocOprosZN._meta.get_field('v2')._verbose_name
        v3_name = DocOprosZN._meta.get_field('v3')._verbose_name
        v4_name = DocOprosZN._meta.get_field('v4')._verbose_name
        v5_name = DocOprosZN._meta.get_field('v5')._verbose_name
        v6_name = DocOprosZN._meta.get_field('v6')._verbose_name
        v7_name = DocOprosZN._meta.get_field('v7')._verbose_name
        v8_name = DocOprosZN._meta.get_field('v8')._verbose_name

        oprosList = DocOprosZN.objects.filter(zn__unit = unitO).filter(dataClose__gte = dataTime)
        oprosListJson = list()
        for opros in oprosList:
            oprosJson = {
                "UinZN"         : opros.zn.uin,
                "v1"            : opros.v1,
                "v2"            : opros.v2,
                "v3"            : opros.v3,
                "v4"            : opros.v4,
                "v5"            : opros.v5,
                "v6"            : opros.v6,
                "v7"            : opros.v7,
                "v8"            : opros.v8,
                "v1_name"        : v1_name,
                "v2_name"        : v2_name,
                "v3_name"        : v3_name,
                "v4_name"        : v4_name,
                "v5_name"        : v5_name,
                "v6_name"        : v6_name,
                "v7_name"        : v7_name,
                "v8_name"        : v8_name,
                "dataClose"     : opros.dataClose.strftime("%Y%m%d%H%M%S"),
                "uin"           : opros.uin,
            }
            oprosListJson.append(oprosJson)

    ######## OprosSale
        v1_name = DocOprosCarShipment._meta.get_field('v1')._verbose_name
        v2_name = DocOprosCarShipment._meta.get_field('v2')._verbose_name
        v3_name = DocOprosCarShipment._meta.get_field('v3')._verbose_name
        v4_name = DocOprosCarShipment._meta.get_field('v4')._verbose_name
        v5_name = DocOprosCarShipment._meta.get_field('v5')._verbose_name
        v6_name = DocOprosCarShipment._meta.get_field('v6')._verbose_name
        v7_name = DocOprosCarShipment._meta.get_field('v7')._verbose_name
        v8_name = DocOprosCarShipment._meta.get_field('v8')._verbose_name
        
        oprosListSale = DocOprosCarShipment.objects.filter(shipment__unit = unitO).filter(dataClose__gte = dataTime)
        oprosListSaleJson = list()
        for oprosSale in oprosListSale:
            oprosSaleJson = {
                "UinSale"   : oprosSale.shipment.uin,
                "v1"        : oprosSale.v1,
                "v2"        : oprosSale.v2,
                "v3"        : oprosSale.v3,
                "v4"        : oprosSale.v4,
                "v5"        : oprosSale.v5,
                "v6"        : oprosSale.v6,
                "v7"        : oprosSale.v7,
                "v8"        : oprosSale.v8,
                "v1_name"        : v1_name,
                "v2_name"        : v2_name,
                "v3_name"        : v3_name,
                "v4_name"        : v4_name,
                "v5_name"        : v5_name,
                "v6_name"        : v6_name,
                "v7_name"        : v7_name,
                "v8_name"        : v8_name,
                "dataClose" : oprosSale.dataClose.strftime("%Y%m%d%H%M%S"),
                "uin"       : oprosSale.uin,
            }
            oprosListSaleJson.append(oprosSaleJson)
    
    ######## Answer
        to = {
            'answer'    : oprosListJson,
            'oprosSale' : oprosListSaleJson,
            'count'     : len(oprosList)
        }
            
        return JsonResponse(to, status=status.HTTP_200_OK)
    
    except:
        return JsonResponse("", status=status.HTTP_200_OK) 

######  
#####
####
###
##
#Функционал работы с расширениями заказ наряда (Тизер)
@api_view(['GET', 'POST',])
def recomendations_exchange(request):

    if request.method == 'GET':
        uin = request.GET['Uin']
        docs_zn = DocZN.objects.filter(uin = uin)
        if len(docs_zn) == 1:
            doc_zn          = docs_zn[0]
            recomendations  = get_recomendations_zn(doc_zn)
        to = {
            'Recomendations' : recomendations
        }
        return JsonResponse(to, status=status.HTTP_200_OK)
    else:
        body_unicode    = request.body.decode().replace("'", '"')
        data            = json.loads(body_unicode)
        type            = data['Type']
        if type == "GET":
            uin = data['Uin']
            docs_zn = DocZN.objects.filter(uin = uin)
            if len(docs_zn) == 1:
                doc_zn          = docs_zn[0]
                recomendations  = get_recomendations_zn(doc_zn)
            to = {
                'Recomendations' : recomendations
            }
            return JsonResponse(to, status=status.HTTP_200_OK)
        if type == "POST":
            doc_zn              = get_order(data["Order"])
            doc_recomendation   = get_recomendation_id(data['Recomendation'])

            doc_recomendation.status            = data['Status']
            doc_recomendation.customerStatus    = data['СustomerStatus']
            doc_recomendation.save()

            DoсRecomendationProduct.objects.filter(recomendation = doc_recomendation).delete()
            DoсRecomendationWork.objects.filter(recomendation = doc_recomendation).delete()

            works = data["Works"]
            for work in works:
                ref_work = get_work(work['Work'])
                new_work = DoсRecomendationWork()
                new_work.recomendation  = doc_recomendation
                new_work.work           = ref_work
                new_work.price          = work["Price"]
                new_work.quantity       = work["Quantity"]
                new_work.amount         = work["Amount"]
                new_work.save()
            
            products = data["Products"]
            for product in products:
                ref_product = get_product(product['Product'])
                new_product = DoсRecomendationProduct()
                new_product.recomendation  = doc_recomendation
                new_product.product        = ref_product
                new_product.price          = product["Price"]
                new_product.quantity       = product["Quantity"]
                new_product.amount         = product["Amount"]
                new_product.save()

        to = {
            'ok': 'ok'
        }
    
    return JsonResponse(to, status=status.HTTP_200_OK)

def get_recomendations_zn(doc_zn):
    recomendations      = list()
    doc_recomendations  = DoсRecomendation.objects.filter(zn = doc_zn)
    for rec in doc_recomendations:
        doc_rec = {
            "Id"                    : rec.id,
            "Zn"                    : rec.zn.uin,
            "name"                  : rec.name,
            'dataTimeCutomerEvent'  : rec.dataTimeCutomerEvent,
            'customerStatus'        : rec.customerStatus,
            'status'                : rec.status,
            'kod_recomendation'     : rec.kod_recomendation,
            'DataTime'              : rec.dataTime,
        }
        recomendations.append(doc_rec)
    return recomendations

def get_recomendation_id(id):
    return DoсRecomendation.objects.get(pk = id) 


#Функционал обновления ссылок на выгрузки автомобилей на сайты
@api_view(['GET', 'POST',])
def refresh_link_cars_exchange(request):

    body_unicode    = request.body.decode().replace("'", '"')
    data            = json.loads(body_unicode)
    for settings_unit in data:
        unit_dc     = get_dc(settings_unit['ПодразделениеДЦ'])
        link_type   = get_type_link(settings_unit['НазначениеВыгрузки'])
        mark_filter = settings_unit['ОтборМарка']
        link        = settings_unit['Ссылка']
        if unit_dc != None:
            count_setting = RefExchangeCars.objects.filter(unit = unit_dc).filter(mark_filter = mark_filter).filter(type_exchange = link_type).filter(link = link).count()
            if count_setting == 0:
                new_ref                 = RefExchangeCars()
                new_ref.unit            = unit_dc
                new_ref.type_exchange   = link_type
                new_ref.link            = link
                new_ref.mark_filter     = mark_filter
                new_ref.city_name       = settings_unit['Город']
                new_ref.file_name       = settings_unit['ИмяФайла']
                new_ref.adress          = settings_unit['Адрес']
                new_ref.save()

    to = {
        'ok': 'ok'
    }

    return JsonResponse(to, status=status.HTTP_200_OK)

def get_dc(name):
    units_count = RefUnit.objects.filter(name = name).filter(buauto = False).count()
    if units_count == 1:
        return RefUnit.objects.filter(name = name).filter(buauto = False)[0]
    return None

def get_type_link(name):
    links_type_count = RefTypeExchange.objects.filter(name = name).count()
    if links_type_count == 1:
        return RefTypeExchange.objects.filter(name = name)[0]
    else:
        links_type = RefTypeExchange()
        links_type.name = name
        links_type.save() 
        return links_type



######
#####
####
###
##
#Функция обмена данными с 1С Корс Авто
@api_view(['POST',])
def exchange_bu(request):
    
    body_unicode    = request.body.decode().replace("'", '"')
    data            = json.loads(body_unicode)
    
    list_staff              = list()
    list_cars               = list()
    list_сustomers          = list()
    list_order_service      = list()
    list_worksheets         = list()
    list_worksheets_events  = list()
    list_shipments          = list()
    list_surveys            = list()
    list_smss               = list()
    list_los                = list()
    list_agreements         = list()

    #Сотрудники
    staffs  = data['Staffs']
    if len(staffs) > 0:
        list_staff = load_staffs(staffs)
    
    #Автомобили клиентов
    cars = data['Cars']
    if len(cars) > 0:
        list_cars = load_cars(cars)

    #Клиенты
    сustomers = data['Customers']
    if len(сustomers) > 0:
        list_сustomers = load_сustomers(сustomers)
    
    
    #Рабочие листы
    worksheets = data['Worksheets']
    if len(worksheets) > 0:
        list_worksheets = load_worksheets(worksheets)

    #События рабочих листов
    worksheets_events = data['WorksheetEvents']
    if len(worksheets_events) > 0:
        list_worksheets_events = load_worksheets_events(worksheets_events)

    #Соглашения по автомобилям
    agreements = data['Agreements']
    if len(agreements) > 0:
        list_agreements = load_agreements(agreements)

    #Отгрузки автомобиля
    shipments = data['Shipments']
    if len(shipments) > 0:
        list_shipments = load_shipments(shipments)

    #Опросы
    if 'Surveys' in data:
        surveys = data['Surveys']
        if len(surveys) > 0:
            list_surveys = load_surveys(surveys)

    #СМС документы
    if 'SMSS' in data:
        smss = data['SMSS']
        if len(smss) > 0:
            list_smss = load_smss(smss)
    
    #Листы оценок
    los = data['Los']
    if len(los) > 0:
        list_los = load_los(los)


    #Ответ
    to = {
        'Staffs'            : list_staff,
        'Cars'              : list_cars,
        'Customers'         : list_сustomers,
        'OrdersService'     : list_order_service,
        'Worksheets'        : list_worksheets,
        'WorksheetEvents'   : list_worksheets_events,
        'Agreements'        : list_agreements,
        'Shipments'         : list_shipments,
        'Surveys'           : list_surveys,
        'SMSS'              : list_smss,
        'Los'               : list_los
    }   

    return JsonResponse(to, status=status.HTTP_200_OK)





######
#####
####
###
##
#Функция обмена данными с 1С
@api_view(['POST',])
def exchange(request):
    
    body_unicode    = request.body.decode().replace("'", '"')
    data            = json.loads(body_unicode)
    
    list_staff              = list()
    list_cars               = list()
    list_сustomers          = list()
    list_order_service      = list()
    list_worksheets         = list()
    list_worksheets_events  = list()
    list_agreements         = list()
    list_shipments          = list()
    list_surveys            = list()
    list_resource_plannings = list()
    list_smss               = list()

    #Сотрудники
    staffs  = data['Staffs']
    if len(staffs) > 0:
        list_staff = load_staffs(staffs)
    
    #Автомобили клиентов
    cars = data['Cars']
    if len(cars) > 0:
        list_cars = load_cars(cars)

    #Клиенты
    сustomers = data['Customers']
    if len(сustomers) > 0:
        list_сustomers = load_сustomers(сustomers)
    
    
    #Рабочие листы
    worksheets = data['Worksheets']
    if len(worksheets) > 0:
        list_worksheets = load_worksheets(worksheets)

    #События рабочих листов
    worksheets_events = data['WorksheetEvents']
    if len(worksheets_events) > 0:
        list_worksheets_events = load_worksheets_events(worksheets_events)

    #Соглашения по автомобилям
    #agreements = data['Agreements']
    #if len(agreements) > 0:
    #    list_agreements = load_agreements(agreements)

    #Отгрузки автомобиля
    shipments = data['Shipments']
    if len(shipments) > 0:
        list_shipments = load_shipments(shipments)

    #Опросы
    if 'Surveys' in data:
        surveys = data['Surveys']
        if len(surveys) > 0:
            list_surveys = load_surveys(surveys)

    #Планируемые ресурсы
    if 'ResourcePlannings' in data:
        resourcePlannings = data['ResourcePlannings']
        if len(resourcePlannings) > 0:
            list_resource_plannings = load_resource_planings(resourcePlannings)

    #СМС документы
    if 'SMSS' in data:
        smss = data['SMSS']
        if len(smss) > 0:
            list_smss = load_smss(smss)
    
    #Заказ-Наряды
    orders_service = data['OrdersService']
    if len(orders_service) > 0:
        list_order_service = load_orders_service(orders_service)
    
    # Добавить в ответ нужные данные:
    recomendations              = list()
    recomendations_mcu          = list()
    records_online_confirmed    = list()
    out                         = data['Out']
    units                       = out['Units']
    for unit in units:
        ref_units = RefUnit.objects.filter(uin = unit['Uin'])
        if len(ref_units) > 0:
            ref_unit = ref_units[0]
            get_recomendations(ref_unit, recomendations)
            get_recomendations_mcu(ref_unit, recomendations_mcu)
            get_records_online_confirmed(ref_unit, records_online_confirmed)

    
    answer = {
        'Recomendations'            : recomendations,
        'Recomendations_mcu'        : recomendations_mcu,
        'Records_online_confirmed'  : records_online_confirmed 
    }


    #Ответ
    to = {
        'Staffs'            : list_staff,
        'Cars'              : list_cars,
        'Customers'         : list_сustomers,
        'OrdersService'     : list_order_service,
        'Worksheets'        : list_worksheets,
        'WorksheetEvents'   : list_worksheets_events,
        'Agreements'        : list_agreements,
        'Shipments'         : list_shipments,
        'Surveys'           : list_surveys,
        'ResourcePlannings' : list_resource_plannings,
        'SMSS'              : list_smss,
        'Answer'            : answer,
    }   

    return JsonResponse(to, status=status.HTTP_200_OK)


######
#####
####
###
##
#Выгрузка данных c портала в 1С
def get_recomendations(unit, recomendations):
    date = DT.datetime.utcnow().date() + DT.timedelta(days=-1)
    doc_recomendations = DoсRecomendation.objects.filter(zn__unit = unit).filter(dataTime__gte = date)
    for rec in doc_recomendations:
        doc_rec = {
            "Id"                    : rec.id,
            "Zn"                    : rec.zn.uin,
            "Name"                  : rec.name,
            'DataTimeCutomerEvent'  : rec.dataTimeCutomerEvent,
            'CustomerStatus'        : rec.customerStatus,
            'Status'                : rec.status,
            'Kod_recomendation'     : rec.kod_recomendation,
            'DataTime'              : rec.dataTime,
        }
        recomendations.append(doc_rec)


def get_recomendations_mcu(unit, recomendations_mcu):
    date = DT.datetime.utcnow().date() + DT.timedelta(days=-1)
    doc_recomendations_mcu = DoсRecomendationMCU.objects.filter(zn__unit = unit).filter(dataTime__gte = date)
    for rec in doc_recomendations_mcu:
        doc_rec = {
            "Id"                    : rec.id,
            "Zn"                    : rec.zn.uin,
            "Name"                  : rec.name,
            'DataTimeCutomerEvent'  : rec.dataTimeCutomerEvent,
            'CustomerStatus'        : rec.customerStatus,
            'Status'                : rec.status,
            'DataTime'              : rec.dataTime,
        }
        recomendations_mcu.append(doc_rec)


def get_records_online_confirmed(unit, records_online_confirmed):
    date = DT.datetime.utcnow().date() + DT.timedelta(days=-1)
    doc_records_online_confirmed = Records_online_doc.objects.filter(unit = unit).filter(dataTimeRecord__gte = date).filter(confirmed = True)
    for rec in doc_records_online_confirmed:
        doc_rec = {
            "Id"                    : rec.uin 
        }
        records_online_confirmed.append(doc_rec)


######
#####
####
###
##
#Загрузка данных
def load_los(los):
    
    answer_data = list()
    for lo in los:
        try:
            lo_object = get_lo(lo)
            answer = {
                'Uin'       : lo_object.uin,
                'Version'   : lo['Version']
            }
            answer_data.append(answer)
        except:
            error = lo
    return answer_data        


def load_smss(smss):
    
    answer_data = list()
    for sms in smss:
        try:
            sms_object = get_sms(sms)
            answer = {
                'Uin'       : sms_object.uin,
                'Version'   : sms['Version']
            }
            answer_data.append(answer)
        except:
            error = sms
    return answer_data        

def load_staffs(staffs):
    
    answer_data = list()
    for staff in staffs:
        try:
            staff_object = get_staff(staff)
            answer = {
                'Uin'       : staff_object.uin,
                'Version'   : staff['Version']
            }
            answer_data.append(answer)
        except:
            error = staff 
    return answer_data

def load_cars(cars):
    
    answer_data = list()
    for car in cars:
        try:
            car_object = get_car(car)
            answer = {
                'Vin'       : car_object.name,
                'Version'   : car['Version']
            }
            answer_data.append(answer)
        except:
            error = car
    return answer_data

def load_сustomers(сustomers):
    
    answer_data = list()
    for сustomer in сustomers:
        try:
            сustomer_object = get_сustomer(сustomer)
            answer = {
                'Uin'       : сustomer_object.uin,
                'Version'   : сustomer['Version']
            }
            answer_data.append(answer)
        except:
            error = сustomer
    return answer_data

def load_orders_service(orders_service):
    answer_data = list()
    for order in orders_service:
        try:
            order_object = get_order(order)
            answer = {
                'Uin'       : order_object.uin,
                'Version'   : order['Version']
            }
            answer_data.append(answer)
        except:
            error = order
    return answer_data   

def load_worksheets(worksheets):
    answer_data = list()
    for worksheet in worksheets:
        try:
            worksheet_object = get_worksheet(worksheet)
            answer = {
                'Uin'       : worksheet_object.uin,
                'Version'   : worksheet['Version']
            }
            answer_data.append(answer)
        except:
            error = worksheet
    return answer_data   

def load_worksheets_events(worksheets_events):
    answer_data = list()
    for worksheets_event in worksheets_events:
        try:
            worksheet_events_object = get_worksheet_event(worksheets_event)
            answer_data.append(worksheet_events_object.uin)
        except:
            error = worksheets_event
    return answer_data

def load_agreements(agreements):
    answer_data = list()
    for agreement in agreements:
        try:
            agreement_object = get_agreement(agreement)
            answer = {
                'Uin'       : agreement_object.uin,
                'Version'   : agreement['Version']
            }
            answer_data.append(answer)
        except:
            error = agreement
    return answer_data

def load_shipments(shipments):
    answer_data = list()
    for shipment in shipments:
        try:
            shipment_object = get_shipment(shipment)
            answer = {
                'Uin'       : shipment_object.uin,
                'Version'   : shipment['Version']
            }
            answer_data.append(answer)
        except:
            error = shipment
    return answer_data

def load_surveys(surveys):
    answer_data = list()
    for survey in surveys:
        try:
            survey_object = get_survey(survey)
            answer = {
                'Uin'       : survey_object.uin,
                'Version'   : survey['Version']
            }
            answer_data.append(answer)
        except:
            error = survey
    return answer_data

def load_resource_planings(resource_planings):
    answer_data = list()
    for resource_planing in resource_planings:
        try:
            resource_planing_object = get_resource_planing(resource_planing)
            answer = {
                'Uin'                   : resource_planing_object.uin,
                'ServiceRequest'        : resource_planing_object.serviceRequest.uin, 
                'Active'                : resource_planing['Active'],
                'DateStart'             : resource_planing['DateStart'],
                'DateEnd'               : resource_planing['DateEnd']
            }
            answer_data.append(answer)
        except:
            error = resource_planing
    return answer_data    
######
#####
####
###
##
#Служебные функции
def get_lo(lo):
    uin         = lo.get('Uin')
    docs_lo = DocLO.objects.filter(uin = uin)
    if len(docs_lo) == 0:
        object = DocLO()
    else:
        object = docs_lo[0]
    object.uin              = uin
    object.save()

    object.active           = lo['Active']
    object.dataTime         = lo['Date']
    object.nomer            = lo['Number']
    object.organization     = get_organization(lo['Organization'])
    
    if lo['Staff'] != '':
        object.staff            = get_staff(lo['Staff'])

    if lo['Auction'] in lo:
        object.auction  = lo['auction']

    if lo['Store'] != '':
        object.store            = get_store(lo['Store'])
    
    if lo['Unit'] != '':
        object.unit             = get_unit(lo['Unit'])
    
    if lo['Customer'] != '':
        object.customer         = get_сustomer(lo['Customer'])
    
    if 'Filial' in lo:
        if lo['Filial'] != '':
            object.filial       = get_filial(lo['Filial'])
    
    if 'CostPrice' in lo:
        object.cost_price = lo['CostPrice']

    if 'BCP' in lo:
        object.bcp = lo['BCP']

    object.rlk                  = get_worksheet(lo['Worksheet'])
    object.clientName           = lo['ClientName']
    object.type_reception       = get_model_object('RefTypeReceptionCarsOrganization', lo['TypeReception'])
    object.cars                 = get_car(lo['Cars'])
    object.vin                  = lo['Vin'][:21]
    object.vin2                 = lo['Vin2'][:21]
    object.owners               = lo['Owners']
    object.vin_new              = lo['VinNew']
    object.name_new_auto        = lo['NameNewAuto']
    object.run                  = lo['Run']
    object.description_podgotovka   = lo['DescriptionPodgotovka']
    object.description_op           = lo['DescriptionOp']
    object.carsGRZ                  = lo['PlateNumber']
    object.year                     = lo['Year']
    
    modificationAutoru = lo['ModificationAutoru']
    if modificationAutoru > 0:
        object.modification_autoru = AutoruModification.objects.get(idSite = modificationAutoru)
    object.save()

    return object
    
def get_sms(sms):
    uin         = sms.get('Uin')
    docs_sms = DocSMS.objects.filter(uin = uin)
    if len(docs_sms) == 0:
        sms_object = DocSMS()
    else:
        sms_object = docs_sms[0]
    sms_object.uin              = uin
    sms_object.save()

    sms_object.active           = sms['Active']
    sms_object.dateTime         = sms['Date']
    sms_object.dateSend         = sms['DateSend']
    sms_object.nomer            = sms['Number']
    sms_object.staff            = get_staff(sms['Staff'])
    sms_object.unit             = get_unit(sms['Unit'])
    sms_object.customer         = get_сustomer(sms['Client'])
    sms_object.clientName       = sms['ClientName']
    sms_object.phone            = sms['Phone']
    sms_object.messageId        = sms['IdMessage']
    sms_object.message          = sms['Message']
    sms_object.thema            = sms['Thema']
    sms_object.statusBase       = get_sms_status_base(sms['Status'])
    sms_object.error            = sms['Error']
    
    sms_object.modelName = sms['Type']
    type_doc = sms['Type']
    if type_doc == 'DocZN':
        doc = get_order(sms['DocZN'])
        sms_object.modelId = doc.pk
    elif type_doc == 'DocCarShipment': 
        doc = get_shipment(sms['DocCarShipment'])
        sms_object.modelId = doc.pk
    elif type_doc == 'DocRLK': 
        doc = get_worksheet(sms['DocRLK'])
        sms_object.modelId = doc.pk
    sms_object.save()

    return sms_object

def get_resource_planing(resource_planing):
    uin                     = resource_planing.get('Uin')
    docs_resource_planing   = ResourcePlanning.objects.filter(uin = uin)
    if len(docs_resource_planing) == 0:
        resource_planing_object = ResourcePlanning()
    else:
        resource_planing_object = docs_resource_planing[0]
    resource_planing_object.uin             = uin
    resource_planing_object.staff           = get_staff(resource_planing.get('Staff'))
    resource_planing_object.dateStart       = resource_planing.get('DateStart')
    resource_planing_object.dateEnd         = resource_planing.get('DateEnd')
    resource_planing_object.active          = resource_planing.get('Active')
    resource_planing_object.type            = get_type_resource_planing(resource_planing.get('Type'))
    resource_planing_object.serviceRequest  = get_service_request(resource_planing.get('ServiceRequest'))
    
    resource_planing_object.save()

    return resource_planing_object

def get_survey(survey):
    
    uin         = survey.get('Uin')
    docs_survey = SurveysOP.objects.filter(uin = uin)
    if len(docs_survey) == 0:
        survey_object = SurveysOP()
    else:
        survey_object = docs_survey[0]
    survey_object.uin           = uin
    survey_object.dateTime      = survey['Date']
    survey_object.nomer         = survey['Number']
    survey_object.staff         = get_staff(survey['Staff'])
    survey_object.unit          = get_unit(survey['Unit'])
    survey_object.сonclusions   = survey['Conclusions']
    if len(str(survey['Result'])) > 0:
        survey_object.result        = int(survey['Result'])
    else:
        survey_object.result        = 0
    if 'WorkSheet' in survey: 
        survey_object.rlk           = get_worksheet(survey['WorkSheet'])
    
    if 'Order' in survey:
        try:
            
            order                               = survey['Order']
            doc_opros_zn                        = DocOprosZN.objects.get(uin = order['Uin'])
            doc_opros_zn.comment_tech_dir       = survey['СommentDC']
            doc_opros_zn.category_negative      = get_category_negative(survey['CategoryNegative'])
            doc_opros_zn.category_customer      = get_category_customer(survey['CategoryCustomer'])
            doc_opros_zn.number_base            = survey['Number']
            doc_opros_zn.date_base              = survey['Date']
            doc_opros_zn.save()

        except:
            s =1

    if 'Shipment' in survey:
        try:
           
            shipment                                    = survey['Shipment']
            doc_opros_shipment                          = DocOprosCarShipment.objects.get(uin = shipment['Uin'])
            doc_opros_shipment.comment_tech_dir         = survey['СommentDC']
            doc_opros_shipment.category_negative        = get_category_negative(survey['CategoryNegative'])
            doc_opros_shipment.category_customer        = get_category_customer(survey['CategoryCustomer'])
            doc_opros_shipment.number_base              = survey['Number']
            doc_opros_shipment.date_base                = survey['Date']
            doc_opros_shipment.save()

        except:
            s =1

    survey_object.save()

    SurveysOP_tematics.objects.filter(surveys = survey_object).delete()
    SurveysOP_questions.objects.filter(surveys = survey_object).delete()

    list_tematics = survey['Tematics']
    for tematics in list_tematics:
        surveysOP_tematics_object = SurveysOP_tematics()
        surveysOP_tematics_object.surveys   = survey_object
        surveysOP_tematics_object.name      = tematics['Name']
        surveysOP_tematics_object.entry_id  = tematics['Entry_id']
        surveysOP_tematics_object.record    = tematics['Record']
        surveysOP_tematics_object.save()
    
    list_questions = survey['Questions']
    for question in list_questions:
        surveysOP_questions_object = SurveysOP_questions()
        surveysOP_questions_object.surveys   = survey_object
        surveysOP_questions_object.name      = question['Question']
        answer = question['Answer']
        if len(answer) > 0:
            surveysOP_questions_object.answer    = int(answer)
        else:
            surveysOP_questions_object.answer    = 0
        surveysOP_questions_object.canceled  = question['Canceled']
        surveysOP_questions_object.save()
    


    return survey_object

def get_store(store):
    
    uin         = store.get('Uin')
    stores      = RefStore.objects.filter(uin = uin)
    
    if len(stores) == 0:
        store_object = RefStore()
    else:
        store_object = stores[0]

    store_object.uin            = uin
    store_object.unit           = get_unit(store['Unit'])
    store_object.name           = store['Name']
    store_object.city           = get_city(store['City'])
    store_object.phone          = store['Phone']
    store_object.adress         = store['Adress']
    store_object.email          = store['Email']
    store_object.save()

    return store_object

def get_organization(organization):
    organizations = RefOrganization.objects.filter(inn = organization['Inn']).filter(kpp = organization['Kpp'])
    if len(organizations) == 0:
        ref_organization = RefOrganization()
    else:
        ref_organization = organizations[0]
    ref_organization.name           = organization['Name']
    ref_organization.full_name      = organization['FullName']
    ref_organization.phone          = organization['Phone']
    ref_organization.inn            = organization['Inn']
    ref_organization.kpp            = organization['Kpp']
    ref_organization.actual_adress  = organization['ActualAddress']
    ref_organization.adress         = organization['Address']
    ref_organization.save()

    return ref_organization

def get_worksheet_event(worksheets_event):
    worksheet   = get_worksheet(worksheets_event['WorkSheet'])
    uin         = worksheets_event['Uin']
    events = DocRLKEvents.objects.filter(uin = uin)
    if len(events) == 0:
        event_object = DocRLKEvents()
    else:
        event_object = events[0]
    event_object.uin            = uin
    event_object.rlk            = worksheet
    event_object.dataTime       = worksheets_event['Date']
    event_object.dataTimeEvent  = worksheets_event['DateEvent']
    event_object.staff          = get_staff(worksheets_event['Staff'])
    event_object.contacType     = get_contactType(worksheets_event['ContactType'])
    event_object.comment        = worksheets_event['Comment']
    event_object.status         = get_status_event(worksheets_event['Status'])
    event_object.save()
    
    return event_object
    
def get_worksheet(worksheet):
    
    uin     = worksheet.get('Uin')
    nomer   = worksheet['Number']
    
    unit    = get_unit(worksheet['Unit'])
    
    docs_rlk = DocRLK.objects.filter(uin = uin).filter(nomer = nomer)
    
    if len(docs_rlk) == 0:
        rlk_object = DocRLK()
    else:
        rlk_object = docs_rlk[0]
    
    rlk_object.uin                  = uin
    rlk_object.unit                 = unit
    rlk_object.save()
    
    rlk_object.dataTime             = worksheet['Date']
    rlk_object.nomer                = worksheet['Number']
    rlk_object.clientName           = worksheet['ClientName']
    rlk_object.staff                = get_staff(worksheet['Staff'])
    
    if 'DateEnd' in worksheet:
        rlk_object.dataEnd          = worksheet['DateEnd'] 
    
    if 'DateCreate' in worksheet:
        rlk_object.dataTimeCreate   = worksheet['DateCreate']
    
    if 'IsMissed' in worksheet:
        rlk_object.is_missed        = worksheet['IsMissed']
    
    if 'Еco' in worksheet:
        rlk_object.eco              = worksheet['Еco']
    else:
        rlk_object.eco              = False

    if 'UnitDC' in worksheet:
        rlk_object.unit_dc          = get_unit(worksheet['UnitDC'])

    if 'TradeInManager' in worksheet:
        rlk_object.manager_trade_in = worksheet['TradeInManager']
    
    if 'Footing' in worksheet:
        rlk_object.footing = get_worksheet(worksheet['Footing'])
    else:
        rlk_object.footing = None

    if 'Type_archive' in worksheet:
        type_archive = worksheet.get('Type_archive', '')
        if len(type_archive) > 0:
            rlk_object.type_archive = get_type_reason_archive_rlk(type_archive)

    if 'DateArchive' in worksheet:
        rlk_object.dateArchive      = worksheet['DateArchive']

    if 'Archive' in worksheet:
        rlk_object.archive              = worksheet['Archive']
    else:
        rlk_object.archive              = False

    if 'ReasonArchive' in worksheet:
        rlk_object.reasonArchive      = worksheet['ReasonArchive']

    rlk_object.type                 = get_type_rlk(worksheet['Type'])
    rlk_object.contacType           = get_contactType(worksheet['ContactType'])
    rlk_object.phone                = worksheet['Phone']
    rlk_object.customer             = get_сustomer(worksheet['Client'])
    
    rlk_object.commentAdministrator = worksheet['CommentAdministrator']
    rlk_object.commentManager       = worksheet['CommentManager']
   
    rlk_object.save()

    return rlk_object

def get_order(order):
    
    uin     = order.get('Uin')
    docs    = DocZN.objects.filter(uin = uin)
    
    if len(docs) == 0:
        order_object = DocZN()
    else:
        order_object = docs[0]

    order_object.uin            = uin
    order_object.unit           = get_unit(order['Unit'])
    order_object.master         = get_staff(order['MasterIn'])
    order_object.masterOut      = get_staff(order['MasterOut'])
    order_object.nomer          = order['Number']
    order_object.dataTime       = order['Date']
    order_object.carsGRZ        = order['StateNumber']
    order_object.customer       = get_сustomer(order['Customer'])
    
    try:
        order_object.clientName     = order['Customer']['Name']
    except:
        order_object.clientName     = ''
    try:
        order_object.organization   = get_organization(order['Organization'])
    except:
        order_object.organization   = None
    
    if 'ServiceRequest' in order:
        order_object.serviceRequest = get_service_request(order['ServiceRequest'])
    
    if 'TypeIB' in order:
        order_object.typeIB     = order['TypeIB']

    order_object.cars           = get_car(order['Car'])
    order_object.typeRemont     = get_type_remont(order['TypeRepair'])
    order_object.readyStatus    = get_status_zn(order['ReadyStatus'])
    order_object.customerWords  = order['Reason']
    order_object.active         = order['Active']
    order_object.dateStart      = order['DateStart']
    order_object.dateEnd        = order['DateEnd']
    order_object.run            = order['Run']
    order_object.amount         = order['Amount']
    order_object.save()

    if 'Performers' in order:
        load_performers(order_object, order['Performers'])

    if 'ProductsCustomer' in order:
        load_products_customer(order_object, order['ProductsCustomer'])
        
    if 'Recomendations' in order:
        load_recomendations(order_object, order['Recomendations'])

    load_works_zn(order_object, order['Works'])
    load_products_zn(order_object, order['Products'])

    return order_object

def get_agreement(agreement):
    
    uin     = agreement.get('Uin')
    docs    = DocCarAgreement.objects.filter(uin = uin)
    
    if len(docs) == 0:
        agreement_object = DocCarAgreement()
    else:
        agreement_object = docs[0]

    agreement_object.uin             = uin
    agreement_object.unit            = get_unit(agreement['Unit'])
    agreement_object.organization    = get_organization(agreement['Organization'])
    agreement_object.dataTime        = agreement['Date']
    agreement_object.active          = agreement['Active']
    agreement_object.nomer           = agreement['Number']
    agreement_object.client          = get_сustomer(agreement['Client'])
    agreement_object.staff           = get_staff(agreement['Staff'])
    agreement_object.cars            = get_car(agreement['Car'])
    agreement_object.rlk             = get_worksheet(agreement['Worksheet'])

    if 'CheckEstimated' in agreement:
        agreement_object.check_estimated = agreement['CheckEstimated']

    if 'CheckActual' in agreement:
        agreement_object.check_actual = agreement['CheckActual']

    if 'DateCheck' in agreement:
        agreement_object.check_date_time = agreement['DateCheck']

    if 'BuWheelsEst' in agreement:
        agreement_object.bu_wheels_est = agreement['BuWheelsEst']
    
    if 'BuWheelsActual' in agreement:
        agreement_object.bu_wheels_actual = agreement['BuWheelsActual']

    if 'KsoEst' in agreement:
        agreement_object.kso_est = agreement['KsoEst']
    
    if 'KsoActual' in agreement:
        agreement_object.kso_actual = agreement['KsoActual']

    if 'СheckText' in agreement:
        agreement_object.check_text = agreement['СheckText']

    if 'DatePlanedSale' in agreement:
        agreement_object.date_planed_sale = agreement['DatePlanedSale']

    if 'CmEst' in agreement:
        agreement_object.cm_est = agreement['CmEst']
    
    if 'CmMin' in agreement:
        agreement_object.cm_min = agreement['CmMin']

    if 'CmActual' in agreement:
        agreement_object.cm_actual = agreement['CmActual']

    if 'CmGoal' in agreement:
        agreement_object.cm_goal = agreement['CmGoal']

    if 'Amount' in agreement:
        agreement_object.amount = agreement['Amount']

    if 'CostPrice' in agreement:
        agreement_object.cost_price = agreement['CostPrice']

    if 'Outlay' in agreement:
        agreement_object.outlay = agreement['Outlay']

    if 'Lo' in agreement:
        agreement_object.lo = get_lo(agreement['Lo']) 

    if 'DiscountAmount' in agreement:
        agreement_object.discountAmount = agreement['DiscountAmount']
    
    if 'DiscountAmountTorg' in agreement:
        agreement_object.discountAmountTorg = agreement['DiscountAmountTorg']

    if 'DiscountAmountTradeIN' in agreement:
        agreement_object.discountAmountTradeIN = agreement['DiscountAmountTradeIN']

    if 'DiscountAmountTorgComment' in agreement:
        agreement_object.discountAmountTorgComment = agreement['DiscountAmountTorgComment']
    
    if 'DiscountAmountTradeINComment' in agreement:
        agreement_object.discountAmountTradeINComment = agreement['DiscountAmountTradeINComment']

    if 'Run' in agreement:
        agreement_object.run = agreement['Run']
    
    if 'Owners' in agreement:
        agreement_object.owners = agreement['Owners']
    
    if 'TypeSale' in agreement:
        agreement_object.typeSale = agreement['TypeSale']

    agreement_object.save()

    return agreement_object

def get_shipment(shipment):
    uin = shipment.get('Uin')
    docs = DocCarShipment.objects.filter(uin = uin)
    if len(docs) == 0:
        shipment_object = DocCarShipment()
    else:
        shipment_object = docs[0]

    shipment_object.uin             = uin
    shipment_object.unit            = get_unit(shipment['Unit'])
    shipment_object.organization    = get_organization(shipment['Organization'])
    shipment_object.dataTime        = shipment['Date']
    shipment_object.active          = shipment['Active']
    shipment_object.nomer           = shipment['Number']
    shipment_object.client          = get_сustomer(shipment['Client'])
    shipment_object.staff           = get_staff(shipment['Staff'])
    shipment_object.cars            = get_car(shipment['Car'])
    shipment_object.rlk             = get_worksheet(shipment['Worksheet'])

    if 'Agreement' in shipment:
        if shipment['Agreement'] != '' and shipment['Agreement'] != None:
            shipment_object.agreement = get_agreement(shipment['Agreement'])

    if 'Amount' in shipment:
        shipment_object.amount = shipment['Amount']

    if 'CostPrice' in shipment:
        shipment_object.cost_price = shipment['CostPrice']

    if 'Outlay' in shipment:
        shipment_object.outlay = shipment['Outlay']

    if 'Lo' in shipment:
        shipment_object.lo = get_lo(shipment['Lo']) 

    if 'DiscountAmount' in shipment:
        shipment_object.discountAmount = shipment['DiscountAmount']
    
    if 'DiscountAmountTorg' in shipment:
        shipment_object.discountAmountTorg = shipment['DiscountAmountTorg']

    if 'DiscountAmountTradeIN' in shipment:
        shipment_object.discountAmountTradeIN = shipment['DiscountAmountTradeIN']

    if 'DiscountAmountTorgComment' in shipment:
        shipment_object.discountAmountTorgComment = shipment['DiscountAmountTorgComment']
    
    if 'DiscountAmountTradeINComment' in shipment:
        shipment_object.discountAmountTradeINComment = shipment['DiscountAmountTradeINComment']

    if 'Run' in shipment:
        shipment_object.run = shipment['Run']
    
    if 'Owners' in shipment:
        shipment_object.owners = shipment['Owners']
    
    if 'TypeSale' in shipment:
        shipment_object.typeSale = shipment['TypeSale']

    shipment_object.save()

    return shipment_object

def load_recomendations(order_object, recomendations):
    DocZNRecomendation.objects.filter(zn = order_object).delete()
    for recomendation in recomendations:
        docZNPerformers_object                  = DocZNRecomendation()
        docZNPerformers_object.zn               = order_object
        docZNPerformers_object.name             = recomendation['Name']
        docZNPerformers_object.uin              = recomendation['Uin']
        docZNPerformers_object.thisZN           = recomendation['ThisZN']
        docZNPerformers_object.close            = recomendation['Close']
        docZNPerformers_object.date             = recomendation['Date']
        docZNPerformers_object.description      = recomendation['Description']
        docZNPerformers_object.reasonClose      = recomendation['ReasonClose']
        docZNPerformers_object.show             = recomendation['Show']
        docZNPerformers_object.save()

def load_products_customer(order_object, products_customer):
    DocZNProductCustomer.objects.filter(zn = order_object).delete()
    for product_customer in products_customer:
        docZNPerformers_object              = DocZNProductCustomer()
        docZNPerformers_object.zn           = order_object
        docZNPerformers_object.product      = product_customer['Product']
        docZNPerformers_object.quantity     = product_customer['Quantity']
        docZNPerformers_object.price        = product_customer['Price']
        docZNPerformers_object.amount       = product_customer['Amount']
        docZNPerformers_object.article      = product_customer['Article']
        docZNPerformers_object.save()

def load_performers(order_object, performers):
    DocZNPerformers.objects.filter(zn = order_object).delete()
    for performer in performers:
        docZNPerformers_object = DocZNPerformers()
        docZNPerformers_object.zn       = order_object
        docZNPerformers_object.uin      = performer['Uin']
        docZNPerformers_object.staff    = get_staff(performer['Staff'])
        docZNPerformers_object.percent  = performer['Percent']
        docZNPerformers_object.save()

def load_products_zn(order_object, products_zn):
    DocZNProduct.objects.filter(zn = order_object).delete()
    for product_zn in products_zn:
        product = get_product(product_zn['Product'])
        product_zn_object = DocZNProduct()
        product_zn_object.zn           = order_object
        product_zn_object.product      = product
        product_zn_object.type         = get_type_item_zn(product_zn['Type'])
        product_zn_object.quantity     = product_zn['Quantity']
        product_zn_object.price        = product_zn['Price']
        product_zn_object.amount       = product_zn['Amount']
        if 'DiscountPercentage' in product_zn:
            product_zn_object.discountPercentage = product_zn['DiscountPercentage']
        if 'Uin' in product_zn:
            product_zn_object.uin = product_zn['Uin'] 
        product_zn_object.save()

def load_works_zn(order_object, works_zn):
    DocZNWork.objects.filter(zn = order_object).delete()
    for work_zn in works_zn:
        work = get_work(work_zn['Work'])
        work_zn_object = DocZNWork()
        work_zn_object.zn           = order_object
        work_zn_object.work         = work
        work_zn_object.type         = get_type_item_zn(work_zn['Type'])
        work_zn_object.quantity     = work_zn['Quantity']
        work_zn_object.price        = work_zn['Price']
        work_zn_object.amount       = work_zn['Amount']
        if 'DiscountPercentage' in work_zn:
            work_zn_object.discountPercentage = work_zn['DiscountPercentage']
        if 'Uin' in work_zn:
            work_zn_object.uin = work_zn['Uin']
        work_zn_object.save()
        
def get_product(product):
    article = product['Article']
    name    = product['Name']
    uin     = product['Uin']
    products_object = RefProduct.objects.filter(uin = uin)
    if len(products_object) == 0:
        product_object = RefProduct()
    else:
        product_object = products_object[0]
    product_object.uin          = uin
    product_object.name         = name
    product_object.article      = article
    product_object.article_dop  = product['ArticleDop']
    product_object.manufacturer = product['Manufacturer']
    product_object.save()
    return product_object 

def get_type_item_zn(type_str):
    refTypeCount = RefTypeItemRepair.objects.filter(name = type_str).count()
    if refTypeCount > 0:
        refType     = RefTypeItemRepair.objects.filter(name = type_str)[0]
        return refType
    else:
        refType         = RefTypeItemRepair()
        refType.name    = type_str
        return refType.save()

def get_work(work):
    article = work['Article']
    name    = work['Name']
    uin     = work['Uin']
    works_object = RefWork.objects.filter(uin = uin)
    if len(works_object) == 0:
        work_object = RefWork()
    else:
        work_object = works_object[0]
    work_object.uin     = uin
    work_object.name    = name
    work_object.article = article
    work_object.save()
    return work_object 

def get_staff(staff):
    
    if len(staff) == 0:
        return None
    if len(staff.get('Name')) == 0:
        return None
    
    staff.get('Name')
    staff_uin       = staff.get('Uin')
    staff_objects    = RefStaff.objects.filter(uin = staff_uin)
    if len(list(staff_objects)) == 0:
        staff_object = RefStaff()
    else:
        staff_object = staff_objects[0]
    staff_object.uin            = staff_uin
    staff_object.name           = staff.get('Name')
    staff_object.domain_login   = staff.get('Domain')
    staff_object.post           = staff.get('Post')
    staff_object.status         = staff.get('Status')
    
    if 'Buauto' in staff:
        staff_object.buauto = staff.get('Buauto', False)
        
    staff_object.save()
    
    staff_object.units.clear()
    units = staff.get('Units')
    for unit in units:
        unit_info = get_unit(unit)
        if unit_info != None:
            staff_object.units.add(unit_info)
    staff_object.save()

    return staff_object

def get_unit(json_unit):
    
    name    = json_unit['Name'] 

    if len(name) < 2:
        return None
    
    ref_unit        = ''
    uin             = json_unit['Uin']
    unit_objects    = RefUnit.objects.filter(uin = uin)

    saves = False

    if len(list(unit_objects)) == 0:
        ref_unit = RefUnit() 
    else:
        ref_unit = unit_objects[0]
    
    if ref_unit.uin != uin:
        ref_unit.uin       = uin
        saves = True

    if ref_unit.name != name:
        ref_unit.name = name
        saves = True
    
    if ref_unit.city != get_city(json_unit['City']):
        ref_unit.city = get_city(json_unit['City'])
        saves = True

    if 'MCC' in json_unit:
            ref_unit.mcc = json_unit['MCC']
            saves = True

    if "Settings" in json_unit:
        settings_unit = json_unit['Settings']

        if 'ЦГ200КорректировкаТестПрайс' in settings_unit: 
            if settings_unit['ЦГ200КорректировкаТестПрайс'] != ref_unit.ratio_avtohub_test_price_200: 
                ref_unit.ratio_avtohub_test_price_200 = settings_unit['ЦГ200КорректировкаТестПрайс']
                saves = True
        if 'ЦГ200КорректировкаРДО' in settings_unit: 
            if settings_unit['ЦГ200КорректировкаРДО'] != ref_unit.ratio_avtohub_rdo_200: 
                ref_unit.ratio_avtohub_rdo_200 = settings_unit['ЦГ200КорректировкаРДО']
                saves = True
        if 'ЦГ200КорректировкаКоррекция' in settings_unit: 
            if settings_unit['ЦГ200КорректировкаКоррекция'] != ref_unit.ratio_avtohub_kor_200: 
                ref_unit.ratio_avtohub_kor_200 = settings_unit['ЦГ200КорректировкаКоррекция']
                saves = True
        if 'ЦГ200КорректировкаТХТ' in settings_unit: 
            if settings_unit['ЦГ200КорректировкаТХТ'] != ref_unit.ratio_avtohub_txt_200: 
                ref_unit.ratio_avtohub_txt_200 = settings_unit['ЦГ200КорректировкаТХТ']
                saves = True
        if 'ЦГ200КорректировкаТестПрайс1С' in settings_unit: 
            if settings_unit['ЦГ200КорректировкаТестПрайс1С'] != ref_unit.ratio_1с_test_price_200: 
                ref_unit.ratio_1с_test_price_200 = settings_unit['ЦГ200КорректировкаТестПрайс1С']
                saves = True
        if 'ЦГ200КорректировкаРДО1С' in settings_unit: 
            if settings_unit['ЦГ200КорректировкаРДО1С'] != ref_unit.ratio_1с_rdo_200: 
                ref_unit.ratio_1с_rdo_200 = settings_unit['ЦГ200КорректировкаРДО1С']
                saves = True
        if 'ЦГ200КорректировкаКоррекция1С' in settings_unit: 
            if settings_unit['ЦГ200КорректировкаКоррекция1С'] != ref_unit.ratio_1с_kor_200: 
                ref_unit.ratio_1с_kor_200 = settings_unit['ЦГ200КорректировкаКоррекция1С']
                saves = True
        if 'ЦГ200КорректировкаТХТ1С' in settings_unit: 
            if settings_unit['ЦГ200КорректировкаТХТ1С'] != ref_unit.ratio_1с_txt_200: 
                ref_unit.ratio_1с_txt_200 = settings_unit['ЦГ200КорректировкаТХТ1С']
                saves = True
        if 'ЦГ400КорректировкаТестПрайс' in settings_unit: 
            if settings_unit['ЦГ400КорректировкаТестПрайс'] != ref_unit.ratio_avtohub_test_price_400: 
                ref_unit.ratio_avtohub_test_price_400 = settings_unit['ЦГ400КорректировкаТестПрайс']
                saves = True
        if 'ЦГ400КорректировкаРДО' in settings_unit: 
            if settings_unit['ЦГ400КорректировкаРДО'] != ref_unit.ratio_avtohub_rdo_400: 
                ref_unit.ratio_avtohub_rdo_400 = settings_unit['ЦГ400КорректировкаРДО']
                saves = True
        if 'ЦГ400КорректировкаКоррекция' in settings_unit: 
            if settings_unit['ЦГ400КорректировкаКоррекция'] != ref_unit.ratio_avtohub_kor_400: 
                ref_unit.ratio_avtohub_kor_400 = settings_unit['ЦГ400КорректировкаКоррекция']
                saves = True
        if 'ЦГ400КорректировкаТХТ' in settings_unit: 
            if settings_unit['ЦГ400КорректировкаТХТ'] != ref_unit.ratio_avtohub_txt_400: 
                ref_unit.ratio_avtohub_txt_400 = settings_unit['ЦГ400КорректировкаТХТ']
                saves = True
        if 'ЦГ400КорректировкаТестПрайс1С' in settings_unit: 
            if settings_unit['ЦГ400КорректировкаТестПрайс1С'] != ref_unit.ratio_1с_test_price_400: 
                ref_unit.ratio_1с_test_price_400 = settings_unit['ЦГ400КорректировкаТестПрайс1С']
                saves = True
        if 'ЦГ400КорректировкаРДО1С' in settings_unit: 
            if settings_unit['ЦГ400КорректировкаРДО1С'] != ref_unit.ratio_1с_rdo_400: 
                ref_unit.ratio_1с_rdo_400 = settings_unit['ЦГ400КорректировкаРДО1С']
                saves = True
        if 'ЦГ400КорректировкаКоррекция1С' in settings_unit: 
            if settings_unit['ЦГ400КорректировкаКоррекция1С'] != ref_unit.ratio_1с_kor_400: 
                ref_unit.ratio_1с_kor_400 = settings_unit['ЦГ400КорректировкаКоррекция1С']
                saves = True
        if 'ЦГ400КорректировкаТХТ1С' in settings_unit: 
            if settings_unit['ЦГ400КорректировкаТХТ1С'] != ref_unit.ratio_1с_txt_400: 
                ref_unit.ratio_1с_txt_400 = settings_unit['ЦГ400КорректировкаТХТ1С']
                saves = True
        if 'ЦГ700КорректировкаТестПрайс' in settings_unit: 
            if settings_unit['ЦГ700КорректировкаТестПрайс'] != ref_unit.ratio_avtohub_test_price_700: 
                ref_unit.ratio_avtohub_test_price_700 = settings_unit['ЦГ700КорректировкаТестПрайс']
                saves = True
        if 'ЦГ700КорректировкаРДО' in settings_unit: 
            if settings_unit['ЦГ700КорректировкаРДО'] != ref_unit.ratio_avtohub_rdo_700: 
                ref_unit.ratio_avtohub_rdo_700 = settings_unit['ЦГ700КорректировкаРДО']
                saves = True
        if 'ЦГ700КорректировкаКоррекция' in settings_unit: 
            if settings_unit['ЦГ700КорректировкаКоррекция'] != ref_unit.ratio_avtohub_kor_700: 
                ref_unit.ratio_avtohub_kor_700 = settings_unit['ЦГ700КорректировкаКоррекция']
                saves = True
        if 'ЦГ700КорректировкаТХТ' in settings_unit: 
            if settings_unit['ЦГ700КорректировкаТХТ'] != ref_unit.ratio_avtohub_txt_700: 
                ref_unit.ratio_avtohub_txt_700 = settings_unit['ЦГ700КорректировкаТХТ']
                saves = True
        if 'ЦГ700КорректировкаТестПрайс1С' in settings_unit: 
            if settings_unit['ЦГ700КорректировкаТестПрайс1С'] != ref_unit.ratio_1с_test_price_700: 
                ref_unit.ratio_1с_test_price_700 = settings_unit['ЦГ700КорректировкаТестПрайс1С']
                saves = True
        if 'ЦГ700КорректировкаРДО1С' in settings_unit: 
            if settings_unit['ЦГ700КорректировкаРДО1С'] != ref_unit.ratio_1с_rdo_700: 
                ref_unit.ratio_1с_rdo_700 = settings_unit['ЦГ700КорректировкаРДО1С']
                saves = True
        if 'ЦГ700КорректировкаКоррекция1С' in settings_unit: 
            if settings_unit['ЦГ700КорректировкаКоррекция1С'] != ref_unit.ratio_1с_kor_700: 
                ref_unit.ratio_1с_kor_700 = settings_unit['ЦГ700КорректировкаКоррекция1С']
                saves = True
        if 'ЦГ700КорректировкаТХТ1С' in settings_unit: 
            if settings_unit['ЦГ700КорректировкаТХТ1С'] != ref_unit.ratio_1с_txt_700: 
                ref_unit.ratio_1с_txt_700 = settings_unit['ЦГ700КорректировкаТХТ1С']
                saves = True
        if 'ЦГ1200КорректировкаТестПрайс' in settings_unit: 
            if settings_unit['ЦГ1200КорректировкаТестПрайс'] != ref_unit.ratio_avtohub_test_price_1200: 
                ref_unit.ratio_avtohub_test_price_1200 = settings_unit['ЦГ1200КорректировкаТестПрайс']
                saves = True
        if 'ЦГ1200КорректировкаРДО' in settings_unit: 
            if settings_unit['ЦГ1200КорректировкаРДО'] != ref_unit.ratio_avtohub_rdo_1200: 
                ref_unit.ratio_avtohub_rdo_1200 = settings_unit['ЦГ1200КорректировкаРДО']
                saves = True
        if 'ЦГ1200КорректировкаКоррекция' in settings_unit: 
            if settings_unit['ЦГ1200КорректировкаКоррекция'] != ref_unit.ratio_avtohub_kor_1200: 
                ref_unit.ratio_avtohub_kor_1200 = settings_unit['ЦГ1200КорректировкаКоррекция']
                saves = True
        if 'ЦГ1200КорректировкаТХТ' in settings_unit: 
            if settings_unit['ЦГ1200КорректировкаТХТ'] != ref_unit.ratio_avtohub_txt_1200: 
                ref_unit.ratio_avtohub_txt_1200 = settings_unit['ЦГ1200КорректировкаТХТ']
                saves = True
        if 'ЦГ1200КорректировкаТестПрайс1С' in settings_unit: 
            if settings_unit['ЦГ1200КорректировкаТестПрайс1С'] != ref_unit.ratio_1с_test_price_1200: 
                ref_unit.ratio_1с_test_price_1200 = settings_unit['ЦГ1200КорректировкаТестПрайс1С']
                saves = True
        if 'ЦГ1200КорректировкаРДО1С' in settings_unit: 
            if settings_unit['ЦГ1200КорректировкаРДО1С'] != ref_unit.ratio_1с_rdo_1200: 
                ref_unit.ratio_1с_rdo_1200 = settings_unit['ЦГ1200КорректировкаРДО1С']
                saves = True
        if 'ЦГ1200КорректировкаКоррекция1С' in settings_unit: 
            if settings_unit['ЦГ1200КорректировкаКоррекция1С'] != ref_unit.ratio_1с_kor_1200: 
                ref_unit.ratio_1с_kor_1200 = settings_unit['ЦГ1200КорректировкаКоррекция1С']
                saves = True
        if 'ЦГ1200КорректировкаТХТ1С' in settings_unit: 
            if settings_unit['ЦГ1200КорректировкаТХТ1С'] != ref_unit.ratio_1с_txt_1200: 
                ref_unit.ratio_1с_txt_1200 = settings_unit['ЦГ1200КорректировкаТХТ1С']
                saves = True
        if 'ЦГ2000КорректировкаТестПрайс' in settings_unit: 
            if settings_unit['ЦГ2000КорректировкаТестПрайс'] != ref_unit.ratio_avtohub_test_price_2000: 
                ref_unit.ratio_avtohub_test_price_2000 = settings_unit['ЦГ2000КорректировкаТестПрайс']
                saves = True
        if 'ЦГ2000КорректировкаРДО' in settings_unit: 
            if settings_unit['ЦГ2000КорректировкаРДО'] != ref_unit.ratio_avtohub_rdo_2000: 
                ref_unit.ratio_avtohub_rdo_2000 = settings_unit['ЦГ2000КорректировкаРДО']
                saves = True
        if 'ЦГ2000КорректировкаКоррекция' in settings_unit: 
            if settings_unit['ЦГ2000КорректировкаКоррекция'] != ref_unit.ratio_avtohub_kor_2000: 
                ref_unit.ratio_avtohub_kor_2000 = settings_unit['ЦГ2000КорректировкаКоррекция']
                saves = True
        if 'ЦГ2000КорректировкаТХТ' in settings_unit: 
            if settings_unit['ЦГ2000КорректировкаТХТ'] != ref_unit.ratio_avtohub_txt_2000: 
                ref_unit.ratio_avtohub_txt_2000 = settings_unit['ЦГ2000КорректировкаТХТ']
                saves = True
        if 'ЦГ2000КорректировкаТестПрайс1С' in settings_unit: 
            if settings_unit['ЦГ2000КорректировкаТестПрайс1С'] != ref_unit.ratio_1с_test_price_2000: 
                ref_unit.ratio_1с_test_price_2000 = settings_unit['ЦГ2000КорректировкаТестПрайс1С']
                saves = True
        if 'ЦГ2000КорректировкаРДО1С' in settings_unit: 
            if settings_unit['ЦГ2000КорректировкаРДО1С'] != ref_unit.ratio_1с_rdo_2000: 
                ref_unit.ratio_1с_rdo_2000 = settings_unit['ЦГ2000КорректировкаРДО1С']
                saves = True
        if 'ЦГ2000КорректировкаКоррекция1С' in settings_unit: 
            if settings_unit['ЦГ2000КорректировкаКоррекция1С'] != ref_unit.ratio_1с_kor_2000: 
                ref_unit.ratio_1с_kor_2000 = settings_unit['ЦГ2000КорректировкаКоррекция1С']
                saves = True
        if 'ЦГ2000КорректировкаТХТ1С' in settings_unit: 
            if settings_unit['ЦГ2000КорректировкаТХТ1С'] != ref_unit.ratio_1с_txt_2000: 
                ref_unit.ratio_1с_txt_2000 = settings_unit['ЦГ2000КорректировкаТХТ1С']
                saves = True
        if 'ЦГ3000КорректировкаТестПрайс' in settings_unit: 
            if settings_unit['ЦГ3000КорректировкаТестПрайс'] != ref_unit.ratio_avtohub_test_price_3000: 
                ref_unit.ratio_avtohub_test_price_3000 = settings_unit['ЦГ3000КорректировкаТестПрайс']
                saves = True
        if 'ЦГ3000КорректировкаРДО' in settings_unit: 
            if settings_unit['ЦГ3000КорректировкаРДО'] != ref_unit.ratio_avtohub_rdo_3000: 
                ref_unit.ratio_avtohub_rdo_3000 = settings_unit['ЦГ3000КорректировкаРДО']
                saves = True
        if 'ЦГ3000КорректировкаКоррекция' in settings_unit: 
            if settings_unit['ЦГ3000КорректировкаКоррекция'] != ref_unit.ratio_avtohub_kor_3000: 
                ref_unit.ratio_avtohub_kor_3000 = settings_unit['ЦГ3000КорректировкаКоррекция']
                saves = True
        if 'ЦГ3000КорректировкаТХТ' in settings_unit: 
            if settings_unit['ЦГ3000КорректировкаТХТ'] != ref_unit.ratio_avtohub_txt_3000: 
                ref_unit.ratio_avtohub_txt_3000 = settings_unit['ЦГ3000КорректировкаТХТ']
                saves = True
        if 'ЦГ3000КорректировкаТестПрайс1С' in settings_unit: 
            if settings_unit['ЦГ3000КорректировкаТестПрайс1С'] != ref_unit.ratio_1с_test_price_3000: 
                ref_unit.ratio_1с_test_price_3000 = settings_unit['ЦГ3000КорректировкаТестПрайс1С']
                saves = True
        if 'ЦГ3000КорректировкаРДО1С' in settings_unit: 
            if settings_unit['ЦГ3000КорректировкаРДО1С'] != ref_unit.ratio_1с_rdo_3000: 
                ref_unit.ratio_1с_rdo_3000 = settings_unit['ЦГ3000КорректировкаРДО1С']
                saves = True
        if 'ЦГ3000КорректировкаКоррекция1С' in settings_unit: 
            if settings_unit['ЦГ3000КорректировкаКоррекция1С'] != ref_unit.ratio_1с_kor_3000: 
                ref_unit.ratio_1с_kor_3000 = settings_unit['ЦГ3000КорректировкаКоррекция1С']
                saves = True
        if 'ЦГ3000КорректировкаТХТ1С' in settings_unit: 
            if settings_unit['ЦГ3000КорректировкаТХТ1С'] != ref_unit.ratio_1с_txt_3000: 
                ref_unit.ratio_1с_txt_3000 = settings_unit['ЦГ3000КорректировкаТХТ1С']
                saves = True
        if 'ЦГ5000КорректировкаТестПрайс' in settings_unit: 
            if settings_unit['ЦГ5000КорректировкаТестПрайс'] != ref_unit.ratio_avtohub_test_price_5000: 
                ref_unit.ratio_avtohub_test_price_5000 = settings_unit['ЦГ5000КорректировкаТестПрайс']
                saves = True
        if 'ЦГ5000КорректировкаРДО' in settings_unit: 
            if settings_unit['ЦГ5000КорректировкаРДО'] != ref_unit.ratio_avtohub_rdo_5000: 
                ref_unit.ratio_avtohub_rdo_5000 = settings_unit['ЦГ5000КорректировкаРДО']
                saves = True
        if 'ЦГ5000КорректировкаКоррекция' in settings_unit: 
            if settings_unit['ЦГ5000КорректировкаКоррекция'] != ref_unit.ratio_avtohub_kor_5000: 
                ref_unit.ratio_avtohub_kor_5000 = settings_unit['ЦГ5000КорректировкаКоррекция']
                saves = True
        if 'ЦГ5000КорректировкаТХТ' in settings_unit: 
            if settings_unit['ЦГ5000КорректировкаТХТ'] != ref_unit.ratio_avtohub_txt_5000: 
                ref_unit.ratio_avtohub_txt_5000 = settings_unit['ЦГ5000КорректировкаТХТ']
                saves = True
        if 'ЦГ5000КорректировкаТестПрайс1С' in settings_unit: 
            if settings_unit['ЦГ5000КорректировкаТестПрайс1С'] != ref_unit.ratio_1с_test_price_5000: 
                ref_unit.ratio_1с_test_price_5000 = settings_unit['ЦГ5000КорректировкаТестПрайс1С']
                saves = True
        if 'ЦГ5000КорректировкаРДО1С' in settings_unit: 
            if settings_unit['ЦГ5000КорректировкаРДО1С'] != ref_unit.ratio_1с_rdo_5000: 
                ref_unit.ratio_1с_rdo_5000 = settings_unit['ЦГ5000КорректировкаРДО1С']
                saves = True
        if 'ЦГ5000КорректировкаКоррекция1С' in settings_unit: 
            if settings_unit['ЦГ5000КорректировкаКоррекция1С'] != ref_unit.ratio_1с_kor_5000: 
                ref_unit.ratio_1с_kor_5000 = settings_unit['ЦГ5000КорректировкаКоррекция1С']
                saves = True
        if 'ЦГ5000КорректировкаТХТ1С' in settings_unit: 
            if settings_unit['ЦГ5000КорректировкаТХТ1С'] != ref_unit.ratio_1с_txt_5000: 
                ref_unit.ratio_1с_txt_5000 = settings_unit['ЦГ5000КорректировкаТХТ1С']
                saves = True
        if 'ЦГ5001КорректировкаТестПрайс' in settings_unit: 
            if settings_unit['ЦГ5001КорректировкаТестПрайс'] != ref_unit.ratio_avtohub_test_price_5001: 
                ref_unit.ratio_avtohub_test_price_5001 = settings_unit['ЦГ5001КорректировкаТестПрайс']
                saves = True
        if 'ЦГ5001КорректировкаРДО' in settings_unit: 
            if settings_unit['ЦГ5001КорректировкаРДО'] != ref_unit.ratio_avtohub_rdo_5001: 
                ref_unit.ratio_avtohub_rdo_5001 = settings_unit['ЦГ5001КорректировкаРДО']
                saves = True
        if 'ЦГ5001КорректировкаКоррекция' in settings_unit: 
            if settings_unit['ЦГ5001КорректировкаКоррекция'] != ref_unit.ratio_avtohub_kor_5001: 
                ref_unit.ratio_avtohub_kor_5001 = settings_unit['ЦГ5001КорректировкаКоррекция']
                saves = True
        if 'ЦГ5001КорректировкаТХТ' in settings_unit: 
            if settings_unit['ЦГ5001КорректировкаТХТ'] != ref_unit.ratio_avtohub_txt_5001: 
                ref_unit.ratio_avtohub_txt_5001 = settings_unit['ЦГ5001КорректировкаТХТ']
                saves = True
        if 'ЦГ5001КорректировкаТестПрайс1С' in settings_unit: 
            if settings_unit['ЦГ5001КорректировкаТестПрайс1С'] != ref_unit.ratio_1с_test_price_5001: 
                ref_unit.ratio_1с_test_price_5001 = settings_unit['ЦГ5001КорректировкаТестПрайс1С']
                saves = True
        if 'ЦГ5001КорректировкаРДО1С' in settings_unit: 
            if settings_unit['ЦГ5001КорректировкаРДО1С'] != ref_unit.ratio_1с_rdo_5001: 
                ref_unit.ratio_1с_rdo_5001 = settings_unit['ЦГ5001КорректировкаРДО1С']
                saves = True
        if 'ЦГ5001КорректировкаКоррекция1С' in settings_unit: 
            if settings_unit['ЦГ5001КорректировкаКоррекция1С'] != ref_unit.ratio_1с_kor_5001: 
                ref_unit.ratio_1с_kor_5001 = settings_unit['ЦГ5001КорректировкаКоррекция1С']
                saves = True
        if 'ЦГ5001КорректировкаТХТ1С' in settings_unit: 
            if settings_unit['ЦГ5001КорректировкаТХТ1С'] != ref_unit.ratio_1с_txt_5001: 
                ref_unit.ratio_1с_txt_5001 = settings_unit['ЦГ5001КорректировкаТХТ1С']
                saves = True
        
        if 'ЦГ200ПроцентНаценкиТХТ' in settings_unit: 
            if settings_unit['ЦГ200ПроцентНаценкиТХТ'] != ref_unit.percent_txt_200: 
                ref_unit.percent_txt_200 = settings_unit['ЦГ200ПроцентНаценкиТХТ']
                saves = True
        if 'ЦГ400ПроцентНаценкиТХТ' in settings_unit: 
            if settings_unit['ЦГ400ПроцентНаценкиТХТ'] != ref_unit.percent_txt_400: 
                ref_unit.percent_txt_400 = settings_unit['ЦГ400ПроцентНаценкиТХТ']
                saves = True
        if 'ЦГ700ПроцентНаценкиТХТ' in settings_unit: 
            if settings_unit['ЦГ700ПроцентНаценкиТХТ'] != ref_unit.percent_txt_700: 
                ref_unit.percent_txt_700 = settings_unit['ЦГ700ПроцентНаценкиТХТ']
                saves = True
        if 'ЦГ1200ПроцентНаценкиТХТ' in settings_unit: 
            if settings_unit['ЦГ1200ПроцентНаценкиТХТ'] != ref_unit.percent_txt_1200: 
                ref_unit.percent_txt_1200 = settings_unit['ЦГ1200ПроцентНаценкиТХТ']
                saves = True
        
        if 'ЦГ2000ПроцентНаценкиТХТ' in settings_unit: 
            if settings_unit['ЦГ2000ПроцентНаценкиТХТ'] != ref_unit.percent_txt_2000: 
                ref_unit.percent_txt_2000 = settings_unit['ЦГ2000ПроцентНаценкиТХТ']
                saves = True
        if 'ЦГ3000ПроцентНаценкиТХТ' in settings_unit: 
            if settings_unit['ЦГ3000ПроцентНаценкиТХТ'] != ref_unit.percent_txt_3000: 
                ref_unit.percent_txt_3000 = settings_unit['ЦГ3000ПроцентНаценкиТХТ']
                saves = True
        if 'ЦГ5000ПроцентНаценкиТХТ' in settings_unit: 
            if settings_unit['ЦГ5000ПроцентНаценкиТХТ'] != ref_unit.percent_txt_5000: 
                ref_unit.percent_txt_5000 = settings_unit['ЦГ5000ПроцентНаценкиТХТ']
                saves = True
        if 'ЦГ5001ПроцентНаценкиТХТ' in settings_unit: 
            if settings_unit['ЦГ5001ПроцентНаценкиТХТ'] != ref_unit.percent_txt_5001: 
                ref_unit.percent_txt_5001 = settings_unit['ЦГ5001ПроцентНаценкиТХТ']
                saves = True
        if 'ЦГ200МаксимальнаяСкидкаТоргВПроцентах' in settings_unit: 
            if settings_unit['ЦГ200МаксимальнаяСкидкаТоргВПроцентах'] != ref_unit.percent_torg_txt_200: 
                ref_unit.percent_torg_txt_200 = settings_unit['ЦГ200МаксимальнаяСкидкаТоргВПроцентах']
                saves = True
        if 'ЦГ400МаксимальнаяСкидкаТоргВПроцентах' in settings_unit: 
            if settings_unit['ЦГ400МаксимальнаяСкидкаТоргВПроцентах'] != ref_unit.percent_torg_txt_400: 
                ref_unit.percent_torg_txt_400 = settings_unit['ЦГ400МаксимальнаяСкидкаТоргВПроцентах']
                saves = True
        if 'ЦГ700МаксимальнаяСкидкаТоргВПроцентах' in settings_unit: 
            if settings_unit['ЦГ700МаксимальнаяСкидкаТоргВПроцентах'] != ref_unit.percent_torg_txt_700: 
                ref_unit.percent_torg_txt_700 = settings_unit['ЦГ700МаксимальнаяСкидкаТоргВПроцентах']
                saves = True
        if 'ЦГ1200МаксимальнаяСкидкаТоргВПроцентах' in settings_unit: 
            if settings_unit['ЦГ1200МаксимальнаяСкидкаТоргВПроцентах'] != ref_unit.percent_torg_txt_1200: 
                ref_unit.percent_torg_txt_1200 = settings_unit['ЦГ1200МаксимальнаяСкидкаТоргВПроцентах']
                saves = True
        
        if 'ЦГ2000МаксимальнаяСкидкаТоргВПроцентах' in settings_unit: 
            if settings_unit['ЦГ2000МаксимальнаяСкидкаТоргВПроцентах'] != ref_unit.percent_torg_txt_2000: 
                ref_unit.percent_torg_txt_2000 = settings_unit['ЦГ2000МаксимальнаяСкидкаТоргВПроцентах']
                saves = True
        if 'ЦГ3000МаксимальнаяСкидкаТоргВПроцентах' in settings_unit: 
            if settings_unit['ЦГ3000МаксимальнаяСкидкаТоргВПроцентах'] != ref_unit.percent_torg_txt_3000: 
                ref_unit.percent_torg_txt_3000 = settings_unit['ЦГ3000МаксимальнаяСкидкаТоргВПроцентах']
                saves = True
        if 'ЦГ5000МаксимальнаяСкидкаТоргВПроцентах' in settings_unit: 
            if settings_unit['ЦГ5000МаксимальнаяСкидкаТоргВПроцентах'] != ref_unit.percent_torg_txt_5000: 
                ref_unit.percent_torg_txt_5000 = settings_unit['ЦГ5000МаксимальнаяСкидкаТоргВПроцентах']
                saves = True
        if 'ЦГ5001МаксимальнаяСкидкаТоргВПроцентах' in settings_unit: 
            if settings_unit['ЦГ5001МаксимальнаяСкидкаТоргВПроцентах'] != ref_unit.percent_torg_txt_5001: 
                ref_unit.percent_torg_txt_5001 = settings_unit['ЦГ5001МаксимальнаяСкидкаТоргВПроцентах']
                saves = True
        if 'ЦГ200МаксимальнаяСкидкаЗаTradeIn' in settings_unit:
            if settings_unit['ЦГ200МаксимальнаяСкидкаЗаTradeIn'] != ref_unit.discount_tt_200: 
                ref_unit.discount_tt_200 = settings_unit['ЦГ200МаксимальнаяСкидкаЗаTradeIn']
                saves = True
        if 'ЦГ400МаксимальнаяСкидкаЗаTradeIn' in settings_unit:
            if settings_unit['ЦГ400МаксимальнаяСкидкаЗаTradeIn'] != ref_unit.discount_tt_400: 
                ref_unit.discount_tt_400 = settings_unit['ЦГ400МаксимальнаяСкидкаЗаTradeIn']
                saves = True   
        if 'ЦГ700МаксимальнаяСкидкаЗаTradeIn' in settings_unit:
            if settings_unit['ЦГ700МаксимальнаяСкидкаЗаTradeIn'] != ref_unit.discount_tt_700: 
                ref_unit.discount_tt_700 = settings_unit['ЦГ700МаксимальнаяСкидкаЗаTradeIn']
                saves = True 
        if 'ЦГ1200МаксимальнаяСкидкаЗаTradeIn' in settings_unit:
            if settings_unit['ЦГ1200МаксимальнаяСкидкаЗаTradeIn'] != ref_unit.discount_tt_1200: 
                ref_unit.discount_tt_1200 = settings_unit['ЦГ1200МаксимальнаяСкидкаЗаTradeIn']
                saves = True   
        if 'ЦГ2000МаксимальнаяСкидкаЗаTradeIn' in settings_unit:
            if settings_unit['ЦГ2000МаксимальнаяСкидкаЗаTradeIn'] != ref_unit.discount_tt_2000: 
                ref_unit.discount_tt_2000 = settings_unit['ЦГ2000МаксимальнаяСкидкаЗаTradeIn']
                saves = True
        if 'ЦГ3000МаксимальнаяСкидкаЗаTradeIn' in settings_unit:
            if settings_unit['ЦГ3000МаксимальнаяСкидкаЗаTradeIn'] != ref_unit.discount_tt_3000: 
                ref_unit.discount_tt_3000 = settings_unit['ЦГ3000МаксимальнаяСкидкаЗаTradeIn']
                saves = True
        if 'ЦГ5000МаксимальнаяСкидкаЗаTradeIn' in settings_unit:
            if settings_unit['ЦГ5000МаксимальнаяСкидкаЗаTradeIn'] != ref_unit.discount_tt_5000: 
                ref_unit.discount_tt_5000 = settings_unit['ЦГ5000МаксимальнаяСкидкаЗаTradeIn']
                saves = True    
        if 'ЦГ5001МаксимальнаяСкидкаЗаTradeIn' in settings_unit:
            if settings_unit['ЦГ5001МаксимальнаяСкидкаЗаTradeIn'] != ref_unit.discount_tt_5001: 
                ref_unit.discount_tt_5001 = settings_unit['ЦГ5001МаксимальнаяСкидкаЗаTradeIn']
                saves = True    

    if "BuAuto" in json_unit:
        if json_unit['BuAuto'] != ref_unit.buauto: 
            ref_unit.buauto = json_unit['BuAuto']
            saves = True

    try:

        ref_ib = get_ib(json_unit['Ib'])
        if ref_unit.ib != ref_ib:
            ref_unit.ib = ref_ib
            saves = True

        if ref_unit.phone != json_unit['Phone']:
            ref_unit.phone = json_unit['Phone']
            saves = True
        
        if ref_unit.email != json_unit['Email']:
            ref_unit.email = json_unit['Email']
            saves = True

        if ref_unit.webSite != json_unit['WebSite']:
            ref_unit.webSite = json_unit['WebSite']
            saves = True

        if ref_unit.adress != json_unit['Adress']:
            ref_unit.adress = json_unit['Adress']
            saves = True

    except:
        s = 1
        
    if saves == True:
        ref_unit.save()
    
    return ref_unit

def get_ib(json_ib):
    
    base            = json_ib['База']
    server          = json_ib['Сервер']
    name            = server + ' --> ' +  base
    
    refs_ib_count = RefIb.objects.filter(base = base).count()
    if refs_ib_count == 0:
        ref_ib          = RefIb()
        ref_ib.name     = name
        ref_ib.server   = json_ib['Сервер']
        ref_ib.base     = json_ib['База']
        ref_ib.save()
    else:
        ref_ib = RefIb.objects.filter(base = base)[0] 
        if ref_ib.server != server:
            ref_ib.name     = name
            ref_ib.server   = server 
            ref_ib.save()

    return ref_ib

def get_modification(id_modification):
    modifications = AutoruModification.objects.filter(idSite = int(id_modification))
    if len(modifications) != 0:
        return modifications[0]
    return 0

def get_city(city_name):
    citys = RefCity.objects.filter(name = city_name)
    if len(citys) == 0:
        city = RefCity()
        city.name = city_name
        city.save()
        return city
    else:
       return citys[0] 

def get_status_zn(status_zn):
    refStatusDocZNCount = RefStatusDocZN.objects.filter(name = status_zn).count()
    if refStatusDocZNCount > 0:
        refStatusDocZN = RefStatusDocZN.objects.filter(name = status_zn)[0]
        return refStatusDocZN
    else:
        refStatusDocZN = RefStatusDocZN()
        refStatusDocZN.name = status_zn
        return refStatusDocZN.save() 

def get_type_remont(type_remont):
    refTypeRemontCount = RefTypeRepair.objects.filter(name = type_remont).count()
    if refTypeRemontCount > 0:
        refTypeRemont = RefTypeRepair.objects.filter(name = type_remont)[0]
        return refTypeRemont
    else:
        refTypeRemont = RefTypeRepair()
        refTypeRemont.name = type_remont
        return refTypeRemont.save() 

def get_car(json_car):
    
    if len(json_car) == 0:
        return None

    cars = RefCars.objects.filter(name = json_car['Vin'])
    if len(cars) == 0:
        car = RefCars()
    else:
        car = cars[0]    
    car.vin     = json_car['Vin'][:18]
    car.save()

    car.name    = json_car['Vin']
    car.vin2    = json_car['Vin2'][:17]
    year = json_car['Year']
    if year != None:
        if len(year) > 1:
            car.year    = json_car['Year']
            
    car.mark    = json_car['Mark']
    car.model   = json_car['Model']
    id_modification = json_car['ModificationID']
    if len(str(id_modification)) > 0 and id_modification != 0:
        modification = get_modification(id_modification)
        if modification != 0:
            car.modification_autoru = get_modification(id_modification)
    car.save()
    return car

def get_filial(json_filial):
    
    if len(json_filial) == 0:
        return None
    
    uin         = json_filial.get('Uin')
    
    filials    = RefFilial.objects.filter(uin = uin)
    
    if len(filials) == 0: 
        filial      = RefFilial()
        filial.uin  = uin
        filial.save()
    else:
        filial = filials[0]

    filial.name           = json_filial['Name']
    if len(json_filial['Organization']) > 0:
        filial.organization   = get_organization(json_filial['Organization'])

    if 'Unit' in json_filial:
        unit_data = json_filial['Unit']
        if len(unit_data) > 0:
            filial.unit   = get_unit(unit_data)

    filial.save()

    return filial

def get_сustomer(json_customer):
    
    if len(json_customer) == 0:
        return None
    
    inn = str(json_customer['Inn'])
    kpp = str(json_customer['Kpp'])
    uin = json_customer['Uin']
    if len(inn) > 0 and len(kpp) > 0:
        customers = RefCustomer.objects.filter(inn = inn).filter(kpp = kpp)
    else:
        customers = RefCustomer.objects.filter(uin = uin) 
    
    if len(customers) == 0:
        customers = RefCustomer.objects.filter(phoneNorm = json_customer["PhoneText"])
        if len(customers) == 0:
            customer = RefCustomer()
        else:
            customer = customers[0]    
    else:
        customer = customers[0] 

    customer.uin            = uin
    customer.name           = json_customer['Name']
    customer.inn            = inn
    customer.kpp            = kpp
    customer.full_name      = json_customer['FullName']
    customer.phoneNorm      = json_customer['PhoneText']
    customer.email          = json_customer['Email']
    customer.actual_addres  = json_customer['ActualAddress']
    customer.addres         = json_customer['Address']
    customer.description    = json_customer['Description']
    customer.comment        = json_customer['Comment'][0:200]
    customer.company        = json_customer['Company']
    customer.save()

    return customer

def get_type_rlk(type):
    refTypeCount = RefTypeDocRLK.objects.filter(name = type).count()
    if refTypeCount > 0:
        refType = RefTypeDocRLK.objects.filter(name = type)[0]
        return refType
    else:
        refType = RefTypeDocRLK()
        refType.name = type
        return refType.save() 

def get_contactType(type):
    refTypeCount = RefContactType.objects.filter(name = type).count()
    if refTypeCount > 0:
        refType = RefContactType.objects.filter(name = type)[0]
        return refType
    else:
        refType = RefContactType()
        refType.name = type
        return refType.save()

def get_status_event(type):
    refTypeCount = RefStatusEvent.objects.filter(name = type).count()
    if refTypeCount > 0:
        refType = RefStatusEvent.objects.filter(name = type)[0]
        return refType
    else:
        refType = RefStatusEvent()
        refType.name = type
        return refType.save()

def get_type_reason_archive_rlk(type):
    refTypeCount = RefReasonArchiveRLK.objects.filter(name = type).count()
    if refTypeCount > 0:
        refType = RefReasonArchiveRLK.objects.filter(name = type)[0]
        return refType
    else:
        refType = RefReasonArchiveRLK()
        refType.name = type
        return refType.save()

def get_type_resource_planing(type):
    refTypeCount = RefTypeResourcePlanning.objects.filter(name = type).count()
    if refTypeCount > 0:
        refType = RefTypeResourcePlanning.objects.filter(name = type)[0]
        return refType
    else:
        refType = RefTypeResourcePlanning()
        refType.name = type
        return refType.save()
    
def get_service_request(service_request):
    
    if service_request == '':
        return None
    
    uin     = service_request.get('Uin')
    docs    = DocServiceRequest.objects.filter(uin = uin)
    
    if len(docs) == 0:
        service_request_object = DocServiceRequest()
    else:
        service_request_object = docs[0]

    service_request_object.uin            = uin
    service_request_object.unit           = get_unit(service_request['Unit'])
    service_request_object.master         = get_staff(service_request['MasterIn'])
    service_request_object.masterOut      = get_staff(service_request['MasterOut'])
    service_request_object.nomer          = service_request['Number']
    service_request_object.dataTime       = service_request['Date']
    service_request_object.carsGRZ        = service_request['StateNumber']
    service_request_object.customer       = get_сustomer(service_request['Customer'])
    try:
        service_request_object.clientName     = service_request['Customer']['Name']
    except:
        service_request_object.clientName     = ''
    try:
        service_request_object.organization   = get_organization(service_request['Organization'])
    except:
        service_request_object.organization   = None
    
    service_request_object.cars           = get_car(service_request['Car'])
    #order_object.typeRemont     = get_type_remont(order['TypeRepair'])
    service_request_object.readyStatus    = get_status_zn(service_request['ReadyStatus'])
    service_request_object.customerWords  = service_request['Reason']
    service_request_object.active         = service_request['Active']
    #order_object.dateStart      = order['DateStart']
    #order_object.dateEnd        = order['DateEnd']
    service_request_object.run            = service_request['Run']
    #order_object.amount         = order['Amount']
    service_request_object.save()

    return service_request_object

def get_category_negative(category_negative):
    if category_negative == '':
        return None
    else:
        refTypeCount = RefTypeCategoryNegative.objects.filter(name = category_negative).count()
    if refTypeCount > 0:
        refType = RefTypeCategoryNegative.objects.filter(name = category_negative)[0]
        return refType
    else:
        refType = RefTypeCategoryNegative()
        refType.name = category_negative
        return refType.save()

def get_sms_status_base(name):
    refCount = RefSMSStatusBase.objects.filter(name = name).count()
    if refCount > 0:
        refObject = RefSMSStatusBase.objects.filter(name = name)[0]
        return refObject
    else:
        refObject = RefSMSStatusBase()
        refObject.name = name
        return refObject.save()

def get_stage_price(name):
    refCount = RefStagePrice.objects.filter(name = name).count()
    if refCount > 0:
        ref = RefStagePrice.objects.filter(name = name)[0]
        return ref
    else:
        ref = RefStagePrice()
        ref.name = name
        return ref.save()
    
def get_group_price(name):
    refCount = RefGroupPrice.objects.filter(name = name).count()
    if refCount > 0:
        ref = RefGroupPrice.objects.filter(name = name)[0]
        return ref
    else:
        ref = RefGroupPrice()
        ref.name = name
        return ref.save()
    
def get_category_customer(category_customer):
    if category_customer == '':
        return None
    else:
        refTypeCount = RefTypeCategoryCustomer.objects.filter(name = category_customer).count()
    if refTypeCount > 0:
        refType = RefTypeCategoryCustomer.objects.filter(name = category_customer)[0]
        return refType
    else:
        refType = RefTypeCategoryCustomer()
        refType.name = category_customer
        return refType.save()
    
def get_model_object(model, name):
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
    
def get_item_spec(name):
    refCount = RefSpecification.objects.filter(name = name).count()
    if refCount > 0:
        ref = RefSpecification.objects.filter(name = name)[0]
        return ref
    else:
        ref = RefSpecification()
        ref.name = name
        return ref.save()