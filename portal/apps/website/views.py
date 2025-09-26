from django.shortcuts import render, get_object_or_404
from openpyxl import Workbook, load_workbook
from documents.models import DocCarAgreement, DocZNWork, DocZNProduct, DocLO, DocZN, DocZNPerformers, DocOprosZN, DocCarShipment, DocOprosZN, DocOprosCarShipment, DoсRecomendation, DocRecomendationFiles, DocRLK, DocRLKEvents, DoсRecomendationMCU, DocRecomendationFilesMCU, ResourcePlanning
import datetime as DT
from dateutil.relativedelta import relativedelta
from django.http import Http404, HttpResponseRedirect, HttpResponseNotFound, HttpResponse
from django.contrib.auth import authenticate
from django.contrib.auth import login as dj_login
from django.contrib.auth import logout as dj_logout
import re
import requests
from powerbi.models import Bi_logs, Bi_wash
import glob, os
import platform
import sys
import ctypes
from recognition.models import Records_voice_recorder, Records_voice_recorder_cvc, Records_voice_recorder_queue, Records_voice_recorder_cvc_checklist, Records_voice_recorder_cvc_checklist_tematics, Records_voice_recorder_cvc_checklist_kg, Records_questions, Check_settings
from django.http.response import JsonResponse
from rest_framework import status
from django.core.paginator import Paginator
import json
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

import xml.etree.ElementTree as ETree
from refs.models import Auction, AuctionStructure, RefCarsOrganizationFiles, RefStore, RefTypeEvaluationCarsOrganization, RefStagePrice, RefGroupPrice, RefRatingCarsOrganization, RefCarsOrganization, RefFilial, RefStatusEstimation, RefTypeReceptionCarsOrganization, AutoruModificationSpecifications, RefManufacturer, RefAvito, RefAvitoComplectation, RefTypeKPPAvito, RefTypeEngineAvito, RefTypeDriveAvito, RefTypeBodyAvito,  RefExchangeCars, RefTypeCanceledSMS, RefTypeExchange, RefIb, AutoruMark, AutoruModel, AutoruModification, AutoruComplectation, RefTypeKpp, RefTypeBody, RefTypeEngine, RefUnit, RefCity, RefStaff, RefBoardsPage, RefUnitGroup, RefTypeRepair, RefBoards, RefTypeResourcePlanning, RefTypeCategoryNegative, RefCustomerFiltr
from profiles.models import Profiles, Profiles_save_search
from updatesportal.models import Updatesportal
import random
from django.db.models import Count, Sum, Max, Avg, F, OuterRef, Subquery, Sum, Q, Func, Value, CharField, IntegerField
from django.db.models.functions import Cast, Coalesce
from django.db import models
from django.conf import settings
from checklists.models import CheckList, CheckList_op_kors, CheckListServiceIn, CheckListTradeIn, CheckListServiceOut
from .services import open_file
from django.http import StreamingHttpResponse
from task_manager.views import send_auction, refresh_car_my_kors_portal, refresh_estimation_cars_organization, kors_estimation_data, get_info_max, get_info_max_remote, refresh_signal, send_files_estimations, send_message_socket, send_push_estimation, swap_estimation, refresh_avtoteka_vin, refresh_catalog_auto_ru, add_task, refresh_autohub, start_back_monitoring, refresh_queue_recognition, cvc_background, cvc_get_info, start_hystory_call, cvc_get_record_info, refresh_wash, cvc_record_info, refresh_price
from online.models import Records_online_doc, Online_doc
from telephony.models import Telephony_records_queue
from telephony.views import refresh_records_download
from django.contrib.auth import get_user_model
from helpDesk.views import tasks_user_desctop
from avtosalon.models import Avtohub, Autoteka_signal
from django.contrib.contenttypes.models import ContentType
from django.apps import apps
from avtosalon.models import RefreshCarsLog
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from register.models import RegEstimationBalanceUnit, RegSwapKors, RegEstimationPodgotovka, RegEstimationSS, RegEstimationMCU, RegInteractivOcenkaTestDrive, RegPodgotovkaWork, RegRegInteractivOcenkaFiles, RegInfoBody, RegEstimationsSettings, RegInteractivOcenkaKorsStoreSale, RegInteractivOcenkaKorsStore, RegInteractivOcenkaTask, RegInteractivOcenkaEmailPush, RegRegInteractivOcenkaTaskFiles, RegInteractivOcenka, SettingsRegPrices, TaskRegPrices, RegPrices, RegInfoRefreshCatalog
from chats.models import Chat, ChatMessage
from register.serializers import RegInteractivOcenkaSerializer
import urllib
from django.contrib.auth.models import User, Group

from eco.views import estimations_price_calculation 

#Настройки параметров доступа
#server_im      = 'http://k01srv1c07/rinternetmag/hs/mb/'
server_im      = 'http://k01srv1c10/ralfa01/hs/mb/'
time_out_im    = 25


def send_web_socket_message(group, chat, user, text):
    
    message_json = {
            'chat_id'       : str(chat.pk),
            'name'          : str(user),
            'chat'          : group,
            'message'       : text,
            'username'      : str(user),
            'last_name'     : user.last_name,
            'first_name'    : user.first_name,
            'psevdo_name'   : user.profiles.eco_name,
            'eco'           : user.profiles.eco
        }
    
    send_message_socket(message = message_json)

def get_path_in_dict(dict_filtr):
    path = ''
    one = True
    for key in dict_filtr:
        if one:
            path = path + '?' + str(key) + '=' + dict_filtr[key]
            one = False
        else:
            path = path + '&' + str(key) + '=' + dict_filtr[key]
    return path


def custom_page_not_found_view(request, exception):
    
    if request.path_info[len(request.path_info)-1] != '/':
        return HttpResponseRedirect(request.path_info + '/') 
    
    user    = request.user
    
    params  = {
				'type'		    : 'home',
				'user'		    : user                
			}
    return render(request, "errors/404.html", {'params': params})

def custom_error_view(request, exception=None):
    
    user    = None
    
    params  = {
				'type'		    : 'home',
				'user'		    : user                
			}
    
    return render(request, "errors/500.html", {'params': params})

def custom_permission_denied_view(request, exception=None):
    user    = request.user
    params  = {
				'type'		    : 'home',
				'user'		    : user                
			}
    return render(request, "errors/403.html", {'params': params})

def custom_bad_request_view(request, exception=None):
    user    = request.user
    params  = {
				'type'		    : 'home',
				'user'		    : user                
			}
    return render(request, "errors/400.html", {'params': params})

###
##agga
# Главная страница портала
def get_rlk_eco(user, type):
    
    rlks = RegInteractivOcenka.objects.filter(staff__domain_login = user.username)
    

    if type == 1: #Продолжить оценку
        rlks1 = rlks.filter(end_estimation = None)
    elif type == 2: #На согласовании
        rlks1 = rlks.exclude(end_estimation = None).filter(page_soglasovanie__price_after_kd = 0)

    
    rlks = rlks.values(
        slug_rlk = F("rlk__id"),
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
        price_sale = F('page_soglasovanie__price_sale'),
        number = F('rlk__nomer'),
        estimation_status = F('status__name'),
            ).values(
                'estimation_start_formated' ,
                'slug_rlk',
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
                'price_reception',
                'price_sale',
                'estimation_status',
                ).distinct().order_by('-rlk__dataTime')
    
    return list(rlks)


def start(request):

    if request.user.is_authenticated:
        Users_model     = get_user_model()
        user            = request.user 

        if 'user_id' in request.GET:
            user_id = request.GET.get('user_id')
            user = Users_model.objects.get(pk = user_id)

        info            = get_info(user)
        rab_stol        = get_start(user)
        users           = Users_model.objects.all().order_by('last_name')
        user_id         = user.pk

        params = {
            'type'      : 'desctop',
            'user'      : request.user,
            'user_id'   : user_id,
            'users'     : users,
            'rab_stol'  : rab_stol,
            'info'      : info
        }

        if request.method == "POST":
            if 'updates_ok' in request.POST:
                id_update = request.POST['id_update']
                updatesportal = Updatesportal.objects.get(pk = id_update)
                updatesportal.users.add(request.user)
                updatesportal.save()
            return HttpResponseRedirect(request.build_absolute_uri())

        return render(request, "website/start.html", {'params': params})    
    else:
        return HttpResponseRedirect('/login') 


def get_info(user):
    updates_count   = 0
    updatesportal   = Updatesportal.objects.filter(activated = True).exclude(users__in = [user]).filter(dateUpdate__gte = user.date_joined).order_by('dateUpdate')
    updates_count   = Updatesportal.objects.filter(activated = True).exclude(users__in = [user]).filter(dateUpdate__gte = user.date_joined).count()
    if updates_count > 0:
         updatesportal = updatesportal[0]
    
    info = {
        'test'              : 'ok',
        'updates'           :  updatesportal,
        'updates_count'     :  updates_count,
        
    }
    return info

###Главная страница
def get_start(user):
    
    warning_list    = list()
    
    currentdate             = DT.datetime.today()
    currentdate             = currentdate.combine(currentdate.date(), currentdate.min.time())
    currentdate_end         = currentdate.replace(hour=23, minute=59) 
    curent_date_mounth      = currentdate.replace(day=1, hour=1) 
    
    rating                          = 0
    rating_common                   = 0
    
    query_rating_common_count       = DocOprosZN.objects.filter(close = True).filter(canceled = False).filter(zn__master__domain_login = user.username).count()
    if query_rating_common_count > 0:
        rating_qyeryset_common = DocOprosZN.objects.filter(close = True).filter(canceled = False).filter(zn__master__domain_login = user.username).aggregate(Sum('v1'), Sum('v2'), Sum('v3'), Sum('v4'), Sum('v5'), Sum('v6'))
        rating_sum_common      = rating_qyeryset_common['v1__sum'] + rating_qyeryset_common['v2__sum'] + rating_qyeryset_common['v3__sum'] + rating_qyeryset_common['v4__sum'] + rating_qyeryset_common['v5__sum'] + rating_qyeryset_common['v6__sum']     
        rating_common          = round(rating_sum_common  / query_rating_common_count / 6, 2)
    
    doc_zn_count_rating     = DocZN.objects.filter(dataTime__gte = curent_date_mounth).filter(dataTime__lte = DT.datetime.today()).filter(master__domain_login = user.username).count()
    if doc_zn_count_rating > 0:
        doc_zn_rating           = DocZN.objects.filter(dataTime__gte = curent_date_mounth).filter(dataTime__lte = DT.datetime.today()).filter(master__domain_login = user.username)
        rating_qyeryset_count   = DocOprosZN.objects.filter(close = True).filter(canceled = False).filter(zn__in =  doc_zn_rating).count()
        rating_qyeryset         = DocOprosZN.objects.filter(close = True).filter(canceled = False).filter(zn__in =  doc_zn_rating).aggregate(Sum('v1'), Sum('v2'), Sum('v3'), Sum('v4'), Sum('v5'), Sum('v6'))    
        if rating_qyeryset_count > 0:
            rating_sum          = rating_qyeryset['v1__sum'] + rating_qyeryset['v2__sum'] + rating_qyeryset['v3__sum'] + rating_qyeryset['v4__sum'] + rating_qyeryset['v5__sum'] + rating_qyeryset['v6__sum']     
            rating              = round(rating_sum  / rating_qyeryset_count / 6, 2) 
           
    rlks_count      = DocRLK.objects.filter(dataTime__gte = currentdate).filter(staff__domain_login = user.username).count()
    doc_rlks        = list()
    
    doc_zn_count    = DocZN.objects.filter(dataTime__gte = currentdate).filter(dataTime__lte = currentdate_end).filter(master__domain_login = user.username).count()
    docs_zn_in      = list()

    #Проверка есть ли рабочие листы и записи диктофона загруженные на портал
    if rlks_count > 0:
        '''
        doc_rlks_qyeri = DocRLK.objects.filter(dataTime__gte = currentdate).filter(staff__domain_login = user.username)
        for doc in doc_rlks_qyeri:
            check_lists = CheckList.objects.filter(rlk = doc)
            check_list = ''
            if len(check_lists) > 0:
                check_list = check_lists[0]
            doc_info = {
				'check_list': check_list,
				'doc': doc
			}
            doc_rlks.append(doc_info)
        '''
        sound_count = get_sound_count(user, currentdate)
        if sound_count == 0:
            warning = {
                'text': "У Вас " + str(rlks_count) + " рабочих листа, но нет загруженых записей диктофона",
                'link_text': 'Перейти к загрузке',
                'link': 'voice_recorders',
                'time': DT.datetime.today()
            }
            warning_list.append(warning)
    
    #Проверка есть ли заказ наряды и записи диктофона загруженные на портал
    if doc_zn_count > 0: 
        
        zn_count_in     = DocZN.objects.filter(dataTime__gte = currentdate).filter(master__domain_login = user.username).count()
        zn_count_out    = DocZN.objects.filter(dataTime__gte = currentdate).filter(masterOut__domain_login = user.username).count()
        
        if zn_count_in > 0:
            docs_zn_in = DocZN.objects.filter(dataTime__gte = currentdate).filter(master__domain_login = user.username) 
        
        sound_count = get_sound_count(user, currentdate)
        if sound_count == 0 and zn_count_in > 0:
            warning = {
                'text': "Вы мастер-консультант в " + str(zn_count_in) + " заказ-нарядах, но нет загруженых записей диктофона",
                'link_text': 'Перейти к загрузке',
                'link': 'voice_recorders',
                'time': DT.datetime.today()
            }
            warning_list.append(warning)
        if sound_count == 0 and zn_count_out > 0:   
            warning = {
                'text': "Вы выпускающий мастер-консультант в " + str(zn_count_in) + " заказ-нарядах, но нет загруженых записей диктофона",
                'link_text': 'Перейти к загрузке',
                'link': 'voice_recorders',
                'time': DT.datetime.today()
            }
            warning_list.append(warning)

    #param_help = tasks_user_desctop(user)
    
    rab_stol = {
        'rlk_count'     : rlks_count,
        'warning_list'  : warning_list,
        'doc_rlks'      : doc_rlks,
        'docs_zn_in'    : docs_zn_in,
        'rating'        : rating,
        'rating_common' : rating_common,
        'rlk_estimation_continue' : get_rlk_eco(user=user, type=1),
        'rlks_estimation_sogrlasovanie' : get_rlk_eco(user=user, type=2),
    }
    
    return rab_stol

def get_sound_count(user, date):
    return Records_voice_recorder.objects.filter(user = user).filter(date__gte = date).count()


def loging(request):
    error = ''
    login = ''
    password = ''
    result = ''
    next = request.GET.get('next', '')
    data = ''

    if request.method == "POST":
	
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        if request.META['SERVER_NAME'] == '127.0.0.1':
            if len(error) == 0:
                login       = request.POST.get("login", '')
                password    = request.POST.get("password", '')
                if login == "":
                    error = error + "Не указан логин"
                if password == "":
                    error = error + "Не указан пароль"
                user = authenticate(username=login, password=password)

                if user is not None:
                    if user.is_active:
                        dj_login(request, user)
                        if len(next) > 0:
                            return HttpResponseRedirect(next) 
                        return HttpResponseRedirect('/')
                    else:
                        error = "Пароль действителен, но учетная запись была отключена!"
                else:
                    error = "Имя пользователя и/или пароль неверные."
        else:
            recaptcha_response = request.POST.get('g-recaptcha-response')
            data = {
                    'secret': settings.RECAPTCHA_PRIVATE_KEY,
                    'response': recaptcha_response
            }
            r = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data, headers=headers)
            result = r.json()
            
            if result['success']:
                if len(error) == 0:
                    login       = request.POST.get("login", '')
                    password    = request.POST.get("password", '')
                    if login == "":
                        error = error + "Не указан логин"
                    if password == "":
                        error = error + "Не указан пароль"
                    user = authenticate(username=login, password=password)

                    if user is not None:
                        if user.is_active:
                            dj_login(request, user)
                            if len(next) > 0:
                                return HttpResponseRedirect(next) 
                            return HttpResponseRedirect('/')
                        else:
                            error = "Пароль действителен, но учетная запись была отключена!"
                    else:
                        error = "Имя пользователя и/или пароль неверные."
            else:
                error = error + "Проверка не пройдена! Повторите проверку и повторите попытку входа в учетную запись."

        params = {
            'error' : error, 
            'login' : login,
            'result': result,
            'data'  : data
        }
        return render(request, 'login.html', {'params': params})
    
    return render(request, 'login.html' )

def logout(request):
	dj_logout(request)
	return HttpResponseRedirect('/')


def balance_edit(request, id):
    
    if not request.user.profiles.eco_page_price_info:
        params = {
        'type'          : 'home',
        'nav_selected'  : 4,
        'request'       : request,
        }
        return render(request, 'errors/403.html', {'params': params})
    
    balance = RegEstimationBalanceUnit.objects.get(pk = id)
    if request.method == "POST":
        balance.amount_custom = int(request.POST.get('amount_custom', '0'))
        balance.comment_3 = request.POST.get('comment_3', '0')
        balance.save()
        return HttpResponseRedirect(request.build_absolute_uri())
    else:
        if 'refresh' in request.GET:
            refresh_estimation_balance_unit(balance.estimation.rlk.pk)
            return HttpResponseRedirect(request.path)
    
    params = {
        'type'      : 'korsavto_settings',
        'balance'   : balance
    }

    return render(request, "website/balance_edit.html", {'params': params}) 

###
##
# Справочники
def refs(request):
    params = {
        'type': 'refs'
    }

    return render(request, "website/refs.html", {'params': params})

def refs_unit_group_list(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        if request.method == 'POST':
            name = request.POST.get('name', '')
            if name != '':
                new_group = RefUnitGroup()
                new_group.name = name
                new_group.save()
                return HttpResponseRedirect(request.build_absolute_uri())
        
        object_list = RefUnitGroup.objects.all().order_by('name')
        
        params = {
            'type'          : 'units_group',
            'object_list'   : object_list 
        }

        return render(request, "website/refs_unit_group_list.html", {'params': params})

###
##
# Опросы сервис
@csrf_exempt
def service(request, id):

    docs = DocZN.objects.filter(uin = id) 
    
    if len(docs) > 0:
        doc = docs[0]
        
        if request.method == "GET":
            url = request.build_absolute_uri()
            return HttpResponseRedirect(request.build_absolute_uri())

        if request.method == "POST":
           
            if "send_opros" in request.POST:
                doc_opros  = doc.get_opros()
                if doc_opros == None: 
                    doc_opros = DocOprosZN()
                    doc_opros.dataTime      = DT.datetime.now()
                doc_opros.close         = True
                doc_opros.dataClose     = DT.datetime.now()
                doc_opros.zn            = doc
                doc_opros.uin           = doc.uin
                doc_opros.v1            = int(request.POST['a1'])
                doc_opros.v2            = int(request.POST['a2'])
                doc_opros.v3            = int(request.POST['a3'])
                doc_opros.v4            = int(request.POST['a4'])
                doc_opros.v5            = int(request.POST['a5'])
                doc_opros.v6            = int(request.POST['a6'])
                doc_opros.v7            = request.POST['a7']
                doc_opros.v8            = request.POST['a8']
                doc_opros.save()

                return HttpResponseRedirect(request.build_absolute_uri())
            
            if 'id_recomendation_mcu' in request.POST: 
                id_recomendation_mcu = request.POST['id_recomendation_mcu']
                recomendation_mcu = DoсRecomendationMCU.objects.get(pk = id_recomendation_mcu)
                if 'yes' in request.POST:
                    recomendation_mcu.customerStatus = 2
                if 'no' in request.POST:
                    recomendation_mcu.customerStatus = 3
                recomendation_mcu.dataTimeCutomerEvent = DT.datetime.now()
                recomendation_mcu.save()
                
                return HttpResponseRedirect(request.build_absolute_uri())

            if 'dop_cancel' in request.POST:
                
                id_recomendation    = request.POST['dop_cancel']
                
                recomendation       = DoсRecomendation.objects.get(pk = id_recomendation)
                
                if recomendation.zn == doc:
                    recomendation.customerStatus        = 3
                    recomendation.dataTimeCutomerEvent  = DT.datetime.now()
                    recomendation.save()
                
                return HttpResponseRedirect(request.build_absolute_uri())       

            if 'dop_success' in request.POST:
                
                id_recomendation    = request.POST['dop_success']
                
                recomendation       = DoсRecomendation.objects.get(pk = id_recomendation)
                
                if recomendation.zn == doc:
                    #kod = request.POST['dop_key']
                    recomendation.customerStatus        = 2
                    recomendation.dataTimeCutomerEvent  = DT.datetime.now()
                    recomendation.save()
                    answer = 'Рекомендация согласована'
                    return JsonResponse({}, status=status.HTTP_200_OK)
                    '''
                    if str(recomendation.kod_recomendation) == kod:
                        recomendation.customerStatus        = 2
                        recomendation.dataTimeCutomerEvent  = DT.datetime.now()
                        recomendation.save()
                        answer = 'Рекомендация согласована'
                        return JsonResponse({}, status=status.HTTP_200_OK)
                    else:
                        return JsonResponse({}, status=status.HTTP_400_BAD_REQUEST)
                    '''
                else:
                    return JsonResponse({}, status=status.HTTP_400_BAD_REQUEST)
                       
        else:
            params = {
                'doc': doc
            }

            return render(request, "website/opros_service.html", {'params': params})
    
    return render(request, "website/opros_404.html")

# Опросы сервис
@csrf_exempt
def service_new(request, id):

    docs = DocZN.objects.filter(uin = id).select_related() 
    
    if len(docs) > 0:
        doc = docs[0]

        '''
        if request.method == "GET":
            if doc.typeRemont.warranty:
                url = request.build_absolute_uri()
                if url.find('#o') < 0:
                    url = url.replace('#r', '')
                    url = url + "#o" 
                    return HttpResponseRedirect(url)
        '''
        if request.method == "POST":
           
            if "send_opros" in request.POST:
                doc_opros  = doc.get_opros()
                if doc_opros == None: 
                    doc_opros = DocOprosZN()
                    doc_opros.dataTime      = DT.datetime.now()
                doc_opros.close         = True
                doc_opros.dataClose     = DT.datetime.now()
                doc_opros.zn            = doc
                doc_opros.uin           = doc.uin
                doc_opros.v1            = int(request.POST['a1'])
                doc_opros.v2            = int(request.POST['a2'])
                doc_opros.v3            = int(request.POST['a3'])
                doc_opros.v4            = int(request.POST['a4'])
                doc_opros.v5            = int(request.POST['a5'])
                doc_opros.v6            = int(request.POST['a6'])
                doc_opros.v7            = request.POST['a7']
                doc_opros.v8            = request.POST['a8']

                try:
                    doc_opros.info = str(request.META)
                except:
                    s =1 

                    
                try:
                    value = request.COOKIES.get('ahkg')
                    if value is None:
                        doc_opros.negative = 'yes'
                    else:
                        doc_opros.cookie_key = value
                except:
                    s =1 

                doc_opros.save()

                return HttpResponseRedirect(request.build_absolute_uri())
            
            if 'id_recomendation_mcu' in request.POST: 
                id_recomendation_mcu = request.POST['id_recomendation_mcu']
                recomendation_mcu = DoсRecomendationMCU.objects.get(pk = id_recomendation_mcu)
                if 'yes' in request.POST:
                    recomendation_mcu.customerStatus = 2
                if 'no' in request.POST:
                    recomendation_mcu.customerStatus = 3
                recomendation_mcu.dataTimeCutomerEvent = DT.datetime.now()
                recomendation_mcu.save()
                
                return HttpResponseRedirect(request.build_absolute_uri())

            if 'dop_cancel' in request.POST:
                
                id_recomendation    = request.POST['dop_cancel']
                
                recomendation       = DoсRecomendation.objects.get(pk = id_recomendation)
                
                if recomendation.zn == doc:
                    recomendation.customerStatus        = 3
                    recomendation.dataTimeCutomerEvent  = DT.datetime.now()
                    recomendation.save()
                
                return HttpResponseRedirect(request.build_absolute_uri())       

            if 'dop_success' in request.POST:
                
                id_recomendation    = request.POST['dop_success']
                
                recomendation       = DoсRecomendation.objects.get(pk = id_recomendation)
                
                if recomendation.zn == doc:
                    recomendation.customerStatus        = 2
                    recomendation.dataTimeCutomerEvent  = DT.datetime.now()
                    recomendation.save()
                    answer = 'Рекомендация согласована'
                    return JsonResponse({}, status=status.HTTP_200_OK)
                    '''
                    kod = request.POST['dop_key']
                    if str(recomendation.kod_recomendation) == kod:
                        recomendation.customerStatus        = 2
                        recomendation.dataTimeCutomerEvent  = DT.datetime.now()
                        recomendation.save()
                        answer = 'Рекомендация согласована'
                        return JsonResponse({}, status=status.HTTP_200_OK)
                    else:
                        return JsonResponse({}, status=status.HTTP_400_BAD_REQUEST)
                    '''
                else:
                    return JsonResponse({}, status=status.HTTP_400_BAD_REQUEST)
                       
        else:
            get_opros_close = False
            
            try:
                opros = DocOprosZN.objects.get(uin = doc.uin)
                get_opros_close = opros.close
            except:
                get_opros_close = False
            
            opros_close = get_opros_close and doc.active and doc.typeIB == ''
            
            params = {
                'doc'           : doc,
                'opros'         : doc.typeRemont.opros,
                'opros_close'   : opros_close
            }

            set_cookie  = False
            value       = request.COOKIES.get('ahkg')
            if value is None:
                set_cookie = True

            if doc.typeRemont.warranty:
                response =  render(request, "website/opros_service_new_warranty.html", {'params': params})
                if set_cookie:
                    response.set_cookie(key='ahkg', value=str(doc.pk))   
                return response
            
            else:
                response = render(request, "website/opros_service_new.html", {'params': params})
                if set_cookie:
                    response.set_cookie(key='ahkg', value=str(doc.pk))   
                return response
    
    return render(request, "website/opros_404.html")

###
##
# Опросы по продажам АМ
@csrf_exempt
def sale(request, id):
    
    docs = DocCarShipment.objects.filter(uin = id) 
    
    if len(docs) > 0:
        doc = docs[0]
        if request.method == "POST":
            if "send_opros" in request.POST:
                doc_opros  = doc.get_opros()
                if doc_opros == None: 
                    doc_opros = DocOprosCarShipment()
                    doc_opros.dataTime      = DT.datetime.now()
                doc_opros.close         = True
                doc_opros.dataClose     = DT.datetime.now()
                doc_opros.shipment       = doc
                doc_opros.uin           = doc.uin
                if doc.unit.buauto:
                    doc_opros.v1            = int(request.POST['a1'])
                    doc_opros.v2            = int(request.POST['a2'])
                    doc_opros.v3            = int(request.POST['a3'])
                    doc_opros.v4            = int(request.POST['a4'])
                    if len(request.POST['a5']) > 0:
                        doc_opros.v5            = int(request.POST['a5'])
                    doc_opros.v6            = 0
                    doc_opros.v7            = request.POST['a7']
                    doc_opros.v8            = request.POST['a6']
                else:
                    doc_opros.v1            = int(request.POST['a1'])
                    doc_opros.v2            = int(request.POST['a2'])
                    doc_opros.v3            = int(request.POST['a3'])
                    doc_opros.v4            = int(request.POST['a4'])
                    if len(request.POST['a5']) > 0:
                        doc_opros.v5            = int(request.POST['a5'])
                    doc_opros.v6            = 0
                    doc_opros.v7            = ""
                    doc_opros.v8            = request.POST['a6']
                doc_opros.save()

                return HttpResponseRedirect(request.build_absolute_uri())
        else:
            params = {
                'doc': doc
            }
            if doc != None:
                if doc.unit.buauto:
                    return render(request, "website/opros_sale_bu.html", {'params': params})    
                else:
                    return render(request, "website/opros_sale.html", {'params': params})
    return render(request, "website/opros_404.html")
    
###
##
# Статистика по опросам

def send_opros_change(doc, canceled_name, op):
    success     = False
    text        = ''
    ib          = ''
    unit        = ''
    if op:
        ib      = doc.shipment.unit.ib
        unit    = doc.shipment.unit
    else:
        ib      = doc.zn.unit.ib
        unit    = doc.zn.unit
    
    if ib == None and unit.buauto:
        url_hs = '/hs/mb/data'
        url    = 'http://a01srv1cka/zbusiness' + url_hs
    else:
        url_hs = '/hs/mb/'
        url    = 'http://' + ib.server.lower() + '/' + ib.base.lower() + url_hs
    

    try:
        post_data = {
            'Uin'       : doc.uin,
            'Op'        : op,
            'Reason'    : canceled_name,
            'Type'      : 'Change_opros'
        }
        response    = requests.post(url, data= json.dumps(post_data), timeout=15)
        status      = int(response.status_code)
        text        = response.text
        if status == 200:
            json_data   = json.loads(text)
            data        = json_data['Data']
            if data['Success']: 
                success = True 
            else:
                text        = data['Answer']
                status      = 400    

    except:
        text        = 'Ошибка'
        status      = 500
    
    info = {
            'Success'   : success,
            'Status'    : status,
            'Text'      : text
        }

    return info
    


def sms_opros_op(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        select_count = request.GET.get('select_count', 25)
        
        filter_count = 0

        name    = ''
        toast   = ''
        date    = ''

        docs    = DocOprosCarShipment.objects.all().order_by('dataTime')

        units_selected  = RefUnit.objects.filter(buauto = False).exclude(name = 'ЕЦО ГК').exclude(name = 'Основное подразделение') | RefUnit.objects.filter(buauto = True).filter(name__icontains = 'корсавто')
        units_selected  = units_selected.order_by('name')
       
        date_start      = request.GET.get('date_start', '')
        date_end        = request.GET.get('date_end', '')
        name            = request.GET.get('name', '')
        close           = request.GET.get('close',          '')
        negative        = request.GET.get('negative',       '')
        organization    = request.GET.get('organization',   '')
        phone           = request.GET.get('phone',          '')
        unit_id         = request.GET.get('unit_id',        '')
        coment          = request.GET.get('coment',         '')
        status          = request.GET.get('status',         '')
        op_direction    = request.GET.get('op_direction',   '')
        
        date_period = DT.datetime.now()
        if len(date_start) == 0:
            date_start 	= date_period.replace(day = 1, hour = 0, minute=0, second=0, microsecond=0)
        else:
            date_start  = DT.datetime.strptime(date_start, '%Y-%m-%d').date()   

        if len(date_end) == 0:
            if date_period.month > 11:
                month_end	= 1
                year_end 	= date_period.year + 1
            else:
                month_end	= date_period.month + 1
                year_end 	= date_period.year
            date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0, microsecond=0)
        else:
            date_end  = DT.datetime.strptime(date_end, '%Y-%m-%d').date()   

        docs    = docs.filter(dataTime__gte = date_start).filter(dataTime__lt = date_end).order_by('-dataTime')
        
        filter_count = filter_count + 1

        if len(status) > 0:
            filter_count = filter_count + 1
            if status == 'Не пройден':
                docs = docs.filter(close = False)
            elif status == 'Пройден':    
                docs = docs.filter(close = True).filter(canceled = False)
            else:
                docs = docs.filter(close = True).filter(canceled = True)

        if len(op_direction) > 0:
            filter_count = filter_count + 1
            if op_direction == 'Новые авто':
                docs = docs.filter(shipment__unit__buauto = False)
            elif op_direction == 'Б/У авто':    
                docs = docs.filter(shipment__unit__buauto = True)


        if len(name) > 0:
            docs = docs.filter(shipment__nomer__icontains = name) | docs.filter(shipment__client__name__icontains = name) | docs.filter(shipment__cars__vin__icontains = name) | docs.filter(shipment__cars__mark__icontains = name) | docs.filter(shipment__cars__model__icontains = name)
            filter_count = filter_count + 1

        if len(phone) > 0:
            docs = docs.filter(phone__icontains = phone)
            filter_count = filter_count + 1
        
        if len(unit_id) > 0:
            filter_count = filter_count + 1
            unit_id = int(unit_id)
            docs = docs.filter(shipment__unit__id = unit_id)

        if len(coment) > 0:
            docs = docs.filter(v8__icontains = coment)
            filter_count = filter_count + 1

        if len(close) > 0:
            if close == 'Да':
                docs = docs.filter(close = True)
            else:
                docs = docs.filter(close = False)
            filter_count = filter_count + 1

        if len(negative) > 0:
            if negative == 'Да':
                docs = docs.filter(close = True).filter(v2__lt = 8)
            else:
                docs = docs.filter(v2__gte = 8)
            filter_count = filter_count + 1

        count   = len(docs)
        docs    = docs.select_related('shipment')
        
        page_number = request.GET.get('page')
        
        paginator   = Paginator(list(docs), select_count)
        page_obj    = paginator.get_page(page_number)
        
        filtr = {
            'name'              : name,
            'date_start'        : date_start,
            'date_end'          : date_end,
            'op_direction'      : op_direction,
            'organization'      : organization,
            'unit_id'           : unit_id,
            'close'             : close,
            'phone'             : phone,
            'negative'          : negative,
            'coment'            : coment,
            'select_count'      : select_count,
            'status'            : status,
            'filtr_count'       : filter_count
        }

        selected = {
            'units'     : units_selected
        }
        
        params = {
            'type'          : 'sms_opros_op',
            'page_number'   : page_number,
            'objects'       : page_obj,
            'selected'      : selected,
            'filtr'         : filtr,
            'toast'         : toast,
            'count'         : count
        }
        return render(request, 'website/sms_opros_op.html', {'params': params})

def sms_opros_op_export(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        select_count = request.GET.get('select_count', 25)
        
        filter_count = 0

        name    = ''
        toast   = ''
        date    = ''

        docs    = DocOprosCarShipment.objects.all().order_by('dataTime')

        units_selected  = RefUnit.objects.filter(buauto = False).exclude(name = 'ЕЦО ГК').exclude(name = 'Основное подразделение') | RefUnit.objects.filter(buauto = True).filter(name__icontains = 'корсавто')
        units_selected  = units_selected.order_by('name')
       
        date_start      = request.GET.get('date_start', '')
        date_end        = request.GET.get('date_end', '')
        name            = request.GET.get('name', '')
        close           = request.GET.get('close', '')
        negative        = request.GET.get('negative', '')
        organization    = request.GET.get('organization', '')
        phone           = request.GET.get('phone', '')
        unit_id         = request.GET.get('unit_id', '')
        coment          = request.GET.get('coment', '')
        status          = request.GET.get('status', '')
        op_direction    = request.GET.get('op_direction', '')
        
        date_period = DT.datetime.now()
        if len(date_start) == 0:
            date_start 	= date_period.replace(day = 1, hour = 0, minute=0, second=0, microsecond=0)
        else:
            date_start  = DT.datetime.strptime(date_start, '%Y-%m-%d').date()   

        if len(date_end) == 0:
            if date_period.month > 11:
                month_end	= 1
                year_end 	= date_period.year + 1
            else:
                month_end	= date_period.month + 1
                year_end 	= date_period.year
            date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0, microsecond=0)
        else:
            date_end  = DT.datetime.strptime(date_end, '%Y-%m-%d').date()   

        docs    = docs.filter(dataTime__gte = date_start).filter(dataTime__lt = date_end).order_by('-dataTime')
        
        filter_count = filter_count + 1

        if len(status) > 0:
            filter_count = filter_count + 1
            if status == 'Не пройден':
                docs = docs.filter(close = False)
            elif status == 'Пройден':    
                docs = docs.filter(close = True).filter(canceled = False)
            else:
                docs = docs.filter(close = True).filter(canceled = True)

        if len(op_direction) > 0:
            filter_count = filter_count + 1
            if op_direction == 'Новые авто':
                docs = docs.filter(shipment__unit__buauto = False)
            elif op_direction == 'Б/У авто':    
                docs = docs.filter(shipment__unit__buauto = True)


        if len(name) > 0:
            docs = docs.filter(shipment__nomer__icontains = name) | docs.filter(shipment__client__name__icontains = name) | docs.filter(shipment__cars__vin__icontains = name) | docs.filter(shipment__cars__mark__icontains = name) | docs.filter(shipment__cars__model__icontains = name)
            filter_count = filter_count + 1

        if len(phone) > 0:
            docs = docs.filter(phone__icontains = phone)
            filter_count = filter_count + 1
        
        if len(unit_id) > 0:
            filter_count = filter_count + 1
            unit_id = int(unit_id)
            docs = docs.filter(shipment__unit__id = unit_id)

        if len(coment) > 0:
            docs = docs.filter(v8__icontains = coment)
            filter_count = filter_count + 1

        if len(close) > 0:
            if close == 'Да':
                docs = docs.filter(close = True)
            else:
                docs = docs.filter(close = False)
            filter_count = filter_count + 1

        if len(negative) > 0:
            if negative == 'Да':
                docs = docs.filter(close = True).filter(v2__lt = 8)
            else:
                docs = docs.filter(v2__gte = 8)
            filter_count = filter_count + 1

        docs    = docs.select_related('shipment')
        
        headers = {
            'file_name' : 'sms_opros_op.xlsx'
        }

        response = HttpResponse(content_type='application/ms-excel', headers = headers)
        response['Content-Disposition'] = 'attachment; filename="sms_opros_op.xlsx"'
        
        wb = Workbook()
        ws = wb.active
        ws.title = "СМС опросы отдела продаж"

        # Add headers
        headers = ["Статус", "Дата опроса", "Дата отгрузки", "Номер отгрузки", "Подразделение", "Клиент", "Автомобиль", 'VIN', "Вопрос 1", "Вопрос 2", "Вопрос 3", "Вопрос 4", "Вопрос 5", "Вопрос 6", "Вопрос 7", "Комментарий клиента", "Сотрудник"]
        ws.append(headers)

        # Add data from the model
        docs = docs.values('close', 'canceled', 'dataTime', 'shipment__cars__mark', 'shipment__cars__model', 'shipment__cars__vin', 'shipment__dataTime', 'shipment__nomer', 'shipment__unit__name', 'shipment__client__name', 'v1', 'v2', 'v3', 'v4', 'v5', 'v6', 'v7', 'v8', 'shipment__staff__name')
        for opros in docs:
            status = ''
            if opros['close'] and opros['canceled']:
                status = 'Апеллирован'
            elif opros['close']:
                status = 'Пройден'
            else:
                status = 'Не пройден'

            cars = "" + str(opros['shipment__cars__mark']) + " " + str(opros['shipment__cars__model']) + " " + str(opros['shipment__cars__vin'])
        
            ws.append([status, opros['dataTime'], opros['shipment__dataTime'], opros['shipment__nomer'], opros['shipment__unit__name'], opros['shipment__client__name'], cars, opros['shipment__cars__vin'], opros['v1'], opros['v2'], opros['v3'], opros['v4'], opros['v5'], opros['v6'], opros['v7'], opros['v8'], opros['shipment__staff__name']])

        # Save the workbook to the HttpResponse
        wb.save(response)
        return response

def sms_opros_op_doc(request, pk):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        doc    = DocOprosCarShipment.objects.get(pk = pk)
        answer = ''
        error  = ''

        if request.method == 'POST':
            canceled_name = ''
            if 'canceled' in request.POST:
                doc.canceled = True
                doc.canceled_comment    = request.POST.get('canceled_comment', '')
                doc.canceled_type       = RefTypeCanceledSMS.objects.get(pk = request.POST.get('select_type_canceled', ''))
                doc.canceled_user       = request.user
                canceled_name = doc.canceled_type.name
            else:
                doc.canceled = False
                doc.canceled_comment    = ''
                doc.canceled_type       = None
                doc.canceled_user       = None

            try:
                answer_change = send_opros_change(doc, canceled_name, True)
                if answer_change['Success']:
                    doc.save() 
            except:
                error = 'Ошибка, необходимо обратиться в техническую поддержку.'

            #doc.save()
            return HttpResponseRedirect(request.build_absolute_uri())
            
        check   = None
        rlk     = None
        if doc.shipment.rlk != None:
            rlk = doc.shipment.rlk 
            if rlk.unit.buauto:
                check_in_count = CheckList_op_kors.objects.filter(rlk = rlk).count()
                if check_in_count > 0:
                    check = CheckListServiceIn.objects.filter(rlk = rlk)[0] 
            else:
                check_in_count = CheckList.objects.filter(rlk = rlk).count()
                if check_in_count > 0:
                    check = CheckList.objects.filter(rlk = rlk)[0] 

        selected = {
            'type_canceled' : RefTypeCanceledSMS.objects.all().order_by('name')            
        }        
        params = {
            'type'          : 'sms_opros_op',
            'selected'      : selected,
            'object'        : doc,
            'check'         : check,
            'rlk'           : rlk,
            'error'         : error,
            'answer'        : answer
        }
        return render(request, 'website/sms_opros_op_doc.html', {'params': params})




def sms_opros_service(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        select_count = request.GET.get('select_count', 25)
        
        filter_count = 0

        name    = ''
        toast   = ''
        date    = ''

        docs    = DocOprosZN.objects.all().order_by('dataTime')

        units_selected  = RefUnit.objects.filter(buauto = False).exclude(name = 'ЕЦО ГК').exclude(name = 'Основное подразделение').order_by('name')
        types_zn        = DocOprosZN.objects.filter(close = True).values('zn__typeRemont', 'zn__typeRemont__name').distinct().order_by('zn__typeRemont__name')

        date_start      = request.GET.get('date_start', '')
        date_end        = request.GET.get('date_end', '')
        name            = request.GET.get('name', '')
        close           = request.GET.get('close', '')
        negative        = request.GET.get('negative', '')
        organization    = request.GET.get('organization', '')
        phone           = request.GET.get('phone', '')
        unit_id         = request.GET.get('unit_id', '')
        coment          = request.GET.get('coment', '')
        type_zn         = request.GET.get('type_zn', '')
        status          = request.GET.get('status', '')

        date_period = DT.datetime.now()
        if len(date_start) == 0:
            date_start 	= date_period.replace(day = 1, hour = 0, minute=0, second=0, microsecond=0)
        else:
            date_start  = DT.datetime.strptime(date_start, '%Y-%m-%d').date()   

        if len(date_end) == 0:
            if date_period.month > 11:
                month_end	= 1
                year_end 	= date_period.year + 1
            else:
                month_end	= date_period.month + 1
                year_end 	= date_period.year
            date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0, microsecond=0)
        else:
            date_end  = DT.datetime.strptime(date_end, '%Y-%m-%d').date()   

        docs    = docs.filter(dataTime__gte = date_start).filter(dataTime__lt = date_end).order_by('-dataTime')
        
        filter_count = filter_count + 1

        if len(status) > 0:
            filter_count = filter_count + 1
            if status == 'Не пройден':
                docs = docs.filter(close = False)
            elif status == 'Пройден':    
                docs = docs.filter(close = True).filter(canceled = False)
            else:
                docs = docs.filter(close = True).filter(canceled = True)

        if len(name) > 0:
            docs = docs.filter(zn__nomer__icontains = name) | docs.filter(zn__customer__name__icontains = name) | docs.filter(zn__cars__vin__icontains = name) | docs.filter(zn__cars__mark__icontains = name) | docs.filter(zn__cars__model__icontains = name) | docs.filter(zn__carsGRZ__icontains = name)
            filter_count = filter_count + 1

        if len(phone) > 0:
            docs = docs.filter(zn__customer__phoneNorm__icontains = phone)
            filter_count = filter_count + 1
        
        if len(unit_id) > 0:
            filter_count = filter_count + 1
            unit_id = int(unit_id)
            docs = docs.filter(zn__unit__id = unit_id)

        if len(type_zn) > 0:
            filter_count = filter_count + 1
            type_zn = int(type_zn)
            docs = docs.filter(zn__typeRemont__id = type_zn)

        if len(coment) > 0:
            docs = docs.filter(v8__icontains = coment)
            filter_count = filter_count + 1

        if len(close) > 0:
            if close == 'Да':
                docs = docs.filter(close = True)
            else:
                docs = docs.filter(close = False)
            filter_count = filter_count + 1

        if len(negative) > 0:
            if negative == 'Да':
                docs = docs.filter(close = True).filter(v2__lt = 8)
            else:
                docs = docs.filter(v2__gte = 8)
            filter_count = filter_count + 1

        count   = len(docs)
        docs    = docs.select_related('zn')
        
        page_number = request.GET.get('page')
        
        paginator   = Paginator(list(docs), select_count)
        page_obj    = paginator.get_page(page_number)
        
        filtr = {
            'name'              : name,
            'date_start'        : date_start,
            'date_end'          : date_end,
            'organization'      : organization,
            'unit_id'           : unit_id,
            'close'             : close,
            'phone'             : phone,
            'negative'          : negative,
            'coment'            : coment,
            'type_zn'           : type_zn,
            'select_count'      : select_count,
            'status'            : status,
            'filtr_count'       : filter_count
        }

        selected = {
            'types_zn'  : types_zn,
            'units'     : units_selected
        }
        
        params = {
            'type'          : 'sms_opros_service',
            'page_number'   : page_number,
            'objects'       : page_obj,
            'selected'      : selected,
            'filtr'         : filtr,
            'toast'         : toast,
            'count'         : count
        }
        return render(request, 'website/sms_opros_service.html', {'params': params})

def sms_opros_service_export(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        select_count = request.GET.get('select_count', 25)
        
        filter_count = 0

        name    = ''
        toast   = ''
        date    = ''

        docs    = DocOprosZN.objects.all().order_by('dataTime')

        units_selected  = RefUnit.objects.filter(buauto = False).exclude(name = 'ЕЦО ГК').exclude(name = 'Основное подразделение').order_by('name')
        types_zn        = DocOprosZN.objects.filter(close = True).values('zn__typeRemont', 'zn__typeRemont__name').distinct().order_by('zn__typeRemont__name')

        date_start      = request.GET.get('date_start', '')
        date_end        = request.GET.get('date_end', '')
        name            = request.GET.get('name', '')
        close           = request.GET.get('close', '')
        negative        = request.GET.get('negative', '')
        organization    = request.GET.get('organization', '')
        phone           = request.GET.get('phone', '')
        unit_id         = request.GET.get('unit_id', '')
        coment          = request.GET.get('coment', '')
        type_zn         = request.GET.get('type_zn', '')
        status          = request.GET.get('status', '')

        date_period = DT.datetime.now()
        if len(date_start) == 0:
            date_start 	= date_period.replace(day = 1, hour = 0, minute=0, second=0, microsecond=0)
        else:
            date_start  = DT.datetime.strptime(date_start, '%Y-%m-%d').date()   

        if len(date_end) == 0:
            if date_period.month > 11:
                month_end	= 1
                year_end 	= date_period.year + 1
            else:
                month_end	= date_period.month + 1
                year_end 	= date_period.year
            date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0, microsecond=0)
        else:
            date_end  = DT.datetime.strptime(date_end, '%Y-%m-%d').date()   

        docs    = docs.filter(dataTime__gte = date_start).filter(dataTime__lt = date_end).order_by('-dataTime')
        
        filter_count = filter_count + 1

        if len(status) > 0:
            filter_count = filter_count + 1
            if status == 'Не пройден':
                docs = docs.filter(close = False)
            elif status == 'Пройден':    
                docs = docs.filter(close = True).filter(canceled = False)
            else:
                docs = docs.filter(close = True).filter(canceled = True)

        if len(name) > 0:
            docs = docs.filter(zn__nomer__icontains = name) | docs.filter(zn__customer__name__icontains = name) | docs.filter(zn__cars__vin__icontains = name) | docs.filter(zn__cars__mark__icontains = name) | docs.filter(zn__cars__model__icontains = name) | docs.filter(zn__carsGRZ__icontains = name)
            filter_count = filter_count + 1

        if len(phone) > 0:
            docs = docs.filter(zn__customer__phoneNorm__icontains = phone)
            filter_count = filter_count + 1
        
        if len(unit_id) > 0:
            filter_count = filter_count + 1
            unit_id = int(unit_id)
            docs = docs.filter(zn__unit__id = unit_id)

        if len(type_zn) > 0:
            filter_count = filter_count + 1
            type_zn = int(type_zn)
            docs = docs.filter(zn__typeRemont__id = type_zn)

        if len(coment) > 0:
            docs = docs.filter(v8__icontains = coment)
            filter_count = filter_count + 1

        if len(close) > 0:
            if close == 'Да':
                docs = docs.filter(close = True)
            else:
                docs = docs.filter(close = False)
            filter_count = filter_count + 1

        if len(negative) > 0:
            if negative == 'Да':
                docs = docs.filter(close = True).filter(v2__lte = 8)
            else:
                docs = docs.filter(v2__gt = 8)
            filter_count = filter_count + 1

        docs    = docs.select_related('zn')
        
        headers = {
            'file_name' : 'sms_opros_service.xlsx'
        }

        response = HttpResponse(content_type='application/ms-excel', headers = headers)
        response['Content-Disposition'] = 'attachment; filename="sms_opros_service.xlsx"'
        
        wb = Workbook()
        ws = wb.active
        ws.title = "СМС опросы сервиса"

        # Add headers
        headers = ["Статус", "Дата опроса", "Дата ЗН", "Номер ЗН", "Подразделение", "Вид ЗН", "Клиент", "Телефон", "Автомобиль", 'VIN', "Вопрос 1", "Вопрос 2", "Вопрос 3", "Вопрос 4", "Вопрос 5", "Вопрос 6", "Вопрос 7", "Комментарий клиента", "Сотрудник"]
        ws.append(headers)

        # Add data from the model
        docs = docs.values('close', 'canceled', 'dataTime', 'zn__cars__mark', 'zn__cars__model', 'zn__cars__vin', 'zn__dataTime', 'zn__nomer', 'zn__unit__name', 'zn__typeRemont__name', 'zn__customer__name', 'v1', 'v2', 'v3', 'v4', 'v5', 'v6', 'v7', 'v8', 'zn__master__name')
        for opros in docs:
            status = ''
            if opros['close'] and opros['canceled']:
                status = 'Апеллирован'
            elif opros['close']:
                status = 'Пройден'
            else:
                status = 'Не пройден'

            cars = "" + str(opros['zn__cars__mark']) + " " + str(opros['zn__cars__model']) + " " + str(opros['zn__cars__vin'])
        
            ws.append([status, opros['dataTime'], opros['zn__dataTime'], opros['zn__nomer'], opros['zn__unit__name'], opros['zn__typeRemont__name'], opros['zn__customer__name'], '', cars, opros['zn__cars__vin'], opros['v1'], opros['v2'], opros['v3'], opros['v4'], opros['v5'], opros['v6'], opros['v7'], opros['v8'], opros['zn__master__name']])

        # Save the workbook to the HttpResponse
        wb.save(response)
        return response

def sms_opros_service_doc(request, pk):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        answer_change   = ''
        doc             = DocOprosZN.objects.get(pk = pk)
        canceled_name   = ''

        if request.method == 'POST':
            if 'canceled' in request.POST:
                doc.canceled = True
                doc.canceled_comment    = request.POST.get('canceled_comment', '')
                doc.canceled_type       = RefTypeCanceledSMS.objects.get(pk = request.POST.get('select_type_canceled', ''))
                doc.canceled_user       = request.user
                canceled_name = doc.canceled_type.name
            else:
                doc.canceled = False
                doc.canceled_comment    = ''
                doc.canceled_type       = None
                doc.canceled_user       = None
            try:
                answer_change = send_opros_change(doc, canceled_name, False)
                if answer_change['Success']:
                    doc.save()
                    return HttpResponseRedirect(request.build_absolute_uri()) 
            except:
                error = 'Ошибка, необходимо обратиться в техническую поддержку.'    
            
            
        check_in = None
        check_in_count = CheckListServiceIn.objects.filter(zn = doc.zn).count()
        if check_in_count > 0:
            check_in = CheckListServiceIn.objects.filter(zn = doc.zn)[0] 
        
        check_out = None
        check_out_count = CheckListServiceOut.objects.filter(zn = doc.zn).count()
        if check_out_count > 0:
            check_out = CheckListServiceOut.objects.filter(zn = doc.zn)[0] 

        master = doc.zn.master

        rating                          = 0
        rating_common                   = 0
        curent_date_mounth              = DT.datetime.today() - DT.timedelta(days=30)

        query_rating_common_count       = DocOprosZN.objects.filter(close = True).filter(canceled = False).filter(zn__master = master).count()
        if query_rating_common_count > 0:
            rating_qyeryset_common = DocOprosZN.objects.filter(close = True).filter(canceled = False).filter(zn__master = master).aggregate(Sum('v1'), Sum('v2'), Sum('v3'), Sum('v4'), Sum('v5'), Sum('v6'))
            rating_sum_common      = rating_qyeryset_common['v1__sum'] + rating_qyeryset_common['v2__sum'] + rating_qyeryset_common['v3__sum'] + rating_qyeryset_common['v4__sum'] + rating_qyeryset_common['v5__sum'] + rating_qyeryset_common['v6__sum']     
            rating_common          = round(rating_sum_common / query_rating_common_count / 6, 2)
        
        doc_zn_count_rating     = DocZN.objects.filter(dataTime__gte = curent_date_mounth).filter(dataTime__lte = DT.datetime.today()).filter(master = master).count()
        if doc_zn_count_rating > 0:
            doc_zn_rating           = DocZN.objects.filter(dataTime__gte = curent_date_mounth).filter(dataTime__lte = DT.datetime.today()).filter(master = master)
            rating_qyeryset_count   = DocOprosZN.objects.filter(close = True).filter(canceled = False).filter(zn__in =  doc_zn_rating).count()
            rating_qyeryset         = DocOprosZN.objects.filter(close = True).filter(canceled = False).filter(zn__in =  doc_zn_rating).aggregate(Sum('v1'), Sum('v2'), Sum('v3'), Sum('v4'), Sum('v5'), Sum('v6'))    
            if rating_qyeryset_count > 0:
                rating_sum          = rating_qyeryset['v1__sum'] + rating_qyeryset['v2__sum'] + rating_qyeryset['v3__sum'] + rating_qyeryset['v4__sum'] + rating_qyeryset['v5__sum'] + rating_qyeryset['v6__sum']     
                rating              = round(rating_sum / rating_qyeryset_count / 6, 2) 

        selected = {
            'type_canceled' : RefTypeCanceledSMS.objects.all().order_by('name')            
        }        
        params = {
            'type'          : 'sms_opros_service',
            'selected'      : selected,
            'check_in'      : check_in,
            'check_out'     : check_out,
            'rating_common' : rating_common,
            'rating'        : rating,
            'object'        : doc,
            'error'         : 'error',
            'answer_change' : answer_change
        }
        return render(request, 'website/sms_opros_service_doc.html', {'params': params})


def dashboard_sms_opros(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        date_start      = request.GET.get('date_start', '')
        date_end        = request.GET.get('date_end', '')
        
        date_period = DT.datetime.now()
        
        if len(date_start) == 0:
            date_start 	= date_period.replace(day = 1, hour = 0, minute=0, second=0, microsecond=0)
        else:
            date_start  = DT.datetime.strptime(date_start, '%Y-%m-%d')
        
        if len(date_end) == 0:
            if date_period.month > 11:
                month_end	= 1
                year_end 	= date_period.year + 1
            else:
                month_end	= date_period.month + 1
                year_end 	= date_period.year
            date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0, microsecond=0)
        else:
            date_end  = DT.datetime.strptime(date_end, '%Y-%m-%d')
        
        data_list = list()
        citys    = DocZN.objects.filter(dataTime__gte = date_start).filter(dataTime__lt = date_end).values('unit__city', 'unit__city__name').exclude(unit__name = 'ЕЦО ГК').distinct().order_by('unit__city__name')
        for city in citys:
            city_name = str(city['unit__city__name'])
            if len(city_name) > 0:
                units_city = DocZN.objects.filter(dataTime__gte = date_start).filter(unit__city__pk = city['unit__city']).filter(dataTime__lt = date_end).exclude(unit__name = 'ЕЦО ГК').values('unit', 'unit__name').distinct().order_by('unit__name')
                
                container_unit                  = list()
                container_docs_no               = list()
                container_docs_opros            = list()
                container_docs_opros_close      = list()
                
                for unit in units_city:
                    unit_name = unit['unit__name']
                    if len(unit_name) > 0:
                        docs = DocZN.objects.filter(dataTime__gte = date_start).filter(unit__pk = unit['unit']).filter(dataTime__lt = date_end)
                        docs_count              = docs.count()
                        doc_opros_count         = DocOprosZN.objects.filter(zn__in = docs).count()
                        doc_opros_count_close   = DocOprosZN.objects.filter(close = True).filter(zn__in = docs).count()
                        
                        container_unit.append(unit_name)
                        container_docs_no.append(docs_count - doc_opros_count)
                        container_docs_opros.append(doc_opros_count - doc_opros_count_close)
                        container_docs_opros_close.append(doc_opros_count_close)
                data_list_params = {
                    'city_name'                     : city['unit__city__name'],
                    'container_unit'                : str(container_unit).replace("'",'"'),
                    'container_docs_no'             : container_docs_no,
                    'container_docs_opros'          : container_docs_opros,
                    'container_docs_opros_close'    : container_docs_opros_close,
                }
                data_list.append(data_list_params)

        filtr = {
            'date_start'        : date_start,
            'date_end'          : date_end
        }
        params = {
            'type'          : 'dashboard_sms_opros',
            'filtr'         : filtr,
            'data_list'     : data_list
        }
        return render(request, 'website/dashboard_sms_opros.html', {'params': params}) 

###
##
# Мониторинг
@csrf_exempt
def board_monitoring(request):
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    #ИП
    #Проверка папок ИП
    try:
        if request.method == "POST":
            if 'delite_base' in request.POST:
                id_base = request.POST.get('id_base', '')
                if id_base != '':
                    ref_object = RefIb.objects.get(pk = id_base)
                    ref_object.active = False
                    ref_object.save()
                    return HttpResponseRedirect(request.build_absolute_uri())
    except:
        s = 1

    path = "//a01srvfs/ftp"
    try:
        dirs = os.listdir(path)
    except:
        dirs = list()
    ip_list = list()
    ip_errors = False
    
    info_ip     = '' 
    list_ip     = list()
    list_ip_in  = list() 
    list_ip_out = list()
    
    for dir in dirs:
        pathdir = path + "/" + dir
        if os.path.isdir(pathdir) and pathdir.find("ip_")>0 and pathdir.find("ip_backup") < 0:
            name = dir
            list_ip.append(name)
            files_ip = list()
            dirs_ip = os.listdir(pathdir)
            size_in     = 0
            size_out    = 0    
            for dir_ip in dirs_ip:
                if os.path.isfile(pathdir + '/' + dir_ip):
                    namefile = dir_ip
                    try:
                        sizefile = os.path.getsize(path + '/' + dir + '/' + namefile)
                    except Exception:
                        sizefile = 0  
                    if namefile.startswith("Message_CentralBase"):
                        size_in = sizefile
                    else:
                        size_out = sizefile
                    json_files_ip = {
                        'name': namefile,
                        'size': int(sizefile / 1024)
                    }
                    if int(sizefile / 1024) > 10:
                        ip_errors = True
                    files_ip.append(json_files_ip)
            list_ip_in.append(size_in)
            list_ip_out.append(size_out)
            json_ip = {
                'name': name,
                'files': files_ip
            }
            if name != 'ip_a01-srv-1c03':
                ip_list.append(json_ip)
    info_ip = {
        'list_name'     : list_ip,
        'list_ip_in'    : list_ip_in, 
        'list_ip_out'   : list_ip_out
    }

    #КорсАвто
    #Проверка веб сервиса корсавто
    answer_kors_avto = False
    try:
        ping_korsavto = requests.get('http://a01srv1cka/zbusiness/hs/mb/activesession', timeout=1)
    except:
        answer_kors_avto = False
    else:
        answer_kors_avto = True
    
    count_swap = 0
    try:
        answer = requests.get('http://a01srv1cka/zbusiness/hs/mb/info_svap', timeout=2)
        answer_json = answer.json()
        count_swap = answer_json.get('Swap')
    except:
        count_swap = 888888
    answer_bu_avito = False
    
    #ИП Кострюков
    #Проверка доступности файлообменика 
    try:
        ping_answer_bu_avito = requests.get('http://194.87.107.139:55510', timeout=1)
    except:
        answer_bu_avito = False
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
        
    space_disk_free     = float('{:.3f}'.format(get_free_space_mb('D:\\')))
    space_disk_free_e   = float('{:.3f}'.format(get_free_space_mb('E:\\')))
    # Логи обновления каталогов
     # Логи загрузки автомобилей
    list_log_refresh_catalogs = list()
    info_refresh_catalogs = RegInfoRefreshCatalog.objects.values('site').annotate(max_date = Max('date')).order_by('-site')

    # Автохаб статистика с макспостерс
    autohab     = Avtohub.objects.all().order_by('-date')[0].date
    
    # Робомойки статистика
    robowash    = Bi_wash.objects.all().order_by('-date_time')[0].date_time

    # Логи загрузки автомобилей
    list_log_refresh_cars = list()
    info_refresh_cars = RefreshCarsLog.objects.values('unit').annotate(max_date = Max('date')).order_by('-unit')
    for info_refresh_car in info_refresh_cars:
        info_refresh_data  = RefreshCarsLog.objects.filter(unit = info_refresh_car['unit']).filter(date = info_refresh_car['max_date'])[0]
        info_refresh = {
            'date'  : info_refresh_data.date,
            'unit'  : info_refresh_data.unit,
            'add'   : info_refresh_data.count_add,
            'del'   : info_refresh_data.count_del, 
            'stock' : info_refresh_data.count_stock 
        }
        list_log_refresh_cars.append(info_refresh)
    
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
    refs_ib = RefIb.objects.filter(active= True).order_by('name')
    url_suf = '/ws/DCChange.1cws?wsdl'
    url_hs = '/hs/mb/'
    error_ib_dc = False
    for ib in refs_ib:
        url         = 'http://' + ib.server.lower() + '/' + ib.base.lower() + url_hs
        count       = '-'
        try:
            response    = requests.get(url, timeout=2)
            status      = int(response.status_code)
            if status == 200:
                json_data = json.loads(response.text)
                count = json_data.get('Count_portal', '-') 
        except:
            status = 400
        ibs = {
            'ib'        : ib,
            'response'  : status,
            'url'       : url,
            'count'     : count

        }
        if status != 200:
            error_ib_dc = True    
        refs_ib_list.append(ibs)
    start   = DT.datetime.today() + DT.timedelta(days=-3)    
    op_queue_doc    = Telephony_records_queue.objects.filter(direction = 1).filter(data_json = '').values('rlk').distinct().count()
    op_queue        = Telephony_records_queue.objects.filter(direction = 1).filter(data_json = '').count()
    
    modifications           = AutoruModification.objects.all().order_by('-pk')
    subquery                = Subquery(AutoruModificationSpecifications.objects.filter(modification__id = OuterRef(name='id')).values('id')[:1], output_field = models.IntegerField())
    modifications           = modifications.annotate(spec = Count(subquery))
    modifications_count     = modifications.filter(spec = 0).count()
    
    # Проверка интерактивных оценок
    object_estimations_report_autohub_remote    = object_estimations_report_autohub = RegInteractivOcenka.objects.exclude(year = 0).filter(start_estimation__gt = DT.date(2025, 3, 1)).exclude(modification = None).exclude(page_remote = None).exclude(page_remote__price_sale = 0).exclude(page_remote__run = 0).filter(page_remote__hub_avg = 0).order_by('-start_estimation').values('pk').count()
    object_estimations_report_autohub           = RegInteractivOcenka.objects.exclude(year = 0).exclude(end_estimation = None).filter(start_estimation__gt = DT.date(2025, 3, 1)).exclude(page_soglasovanie = None).exclude(page_salon__run = None).exclude(modification = None).filter(hub_start = None).order_by('-start_estimation').values('pk').count()
    autohub_count           = object_estimations_report_autohub_remote + object_estimations_report_autohub 
    autoteka_count_1        = RegInteractivOcenka.objects.filter(start_estimation__gt = DT.date(2025, 7, 1)).exclude(vin = ' ').exclude(vin = '').exclude(vin__icontains = '*').exclude(vin__icontains = 'отсут').filter(avtoteka_web = '').filter(avtoteka_preview = '').filter(avtoteka_task = None).count() + RegInteractivOcenka.objects.exclude(vin = '').exclude(vin = ' ').exclude(vin__icontains = '*').exclude(vin__icontains = 'отсут').filter(start_estimation__gt = DT.date(2025, 4, 1)).filter(avtoteka_web = '').filter(avtoteka_preview = '').filter(avtoteka_task = '').count()
    #autoteka_count_1        = RegInteractivOcenka.objects.filter(start_estimation__gt = DT.date(2025, 7, 1)).filter(avtoteka_web = '').filter(avtoteka_preview = '').filter(avtoteka_task = None).count() + RegInteractivOcenka.objects.filter(start_estimation__gt = DT.date(2025, 4, 1)).filter(avtoteka_web = '').filter(avtoteka_preview = '').filter(avtoteka_task = '').count()
    autoteka_count_2        = RegInteractivOcenka.objects.exclude(vin = ' ').exclude(vin = '').exclude(vin__icontains = '*').exclude(vin__icontains = 'отсут').filter(start_estimation__gt = DT.date(2025, 6, 1)).filter(avtoteka_web = '').exclude(avtoteka_preview = '').filter(avtoteka_task = '').count() + RegInteractivOcenka.objects.exclude(vin__icontains = ' ').exclude(vin = '').exclude(vin__icontains = '*').exclude(vin__icontains = 'отсут').filter(vin__regex = r'^.{17}.*').filter(start_estimation__gt = DT.date(2025, 4, 1)).filter(avtoteka_web = '').exclude(avtoteka_preview = '').filter(avtoteka_task = None).count()
    autoteka_count_3        = RegInteractivOcenka.objects.exclude(vin = ' ').exclude(vin = '').exclude(vin__icontains = '*').exclude(vin__icontains = 'отсут').filter(start_estimation__gt = DT.date(2025, 6, 1)).filter(avtoteka_web = '').exclude(avtoteka_preview = '').exclude(avtoteka_task = '').exclude(avtoteka_task = None).count()
    push_count              = RegInteractivOcenkaEmailPush.objects.exclude(send = True).exclude(user__email = '').count()
    send_1c                 = RegSwapKors.objects.filter(status_code = 60).count()
    task_price_count        = TaskRegPrices.objects.exclude(status = 'Обработан').exclude(status = 'Ошибка').count()
    estimation_1c           = RegInteractivOcenka.objects.filter(start_estimation__gt = DT.date(2025, 3, 1)).exclude(modification = None).filter(kors_start_store = None).count() + RegInteractivOcenka.objects.filter(start_estimation__gt = DT.date(2025, 3, 1)).exclude(modification = None).filter(kors_start_store__lt = DT.date(2025, 3, 1)).count()
    
    params = {
        'type'                  : 'monitorings',
        'ip'                    : ip_list,
        'ip_errors'             : ip_errors,
        'answer_kors_avto'      : answer_kors_avto,
        'count_swap'            : count_swap,
        'count_swap_opfu'       : count_swap_opfu,
        'space_disk_free'       : space_disk_free,
        'space_disk_free_e'     : space_disk_free_e,
        'answer_bu_avito'       : answer_bu_avito,
        'power_bi'              : power_bi,
        'record_convert'        : Records_voice_recorder.objects.filter(time__lte = 0).filter(date__gte = start).count(),
        'record_recognitions'   : Records_voice_recorder_queue.objects.filter(data_json = '').count(),
        'refs_ib'               : refs_ib_list, 
        'refs_ib_error'         : error_ib_dc,
        'op_queue_doc'          : op_queue_doc,
        'op_queue'              : op_queue,
        'autohab'               : autohab,
        'robowash'              : robowash,
        'info_ip'               : info_ip,
        'list_log_refresh_cars' : list_log_refresh_cars,
        'info_refresh_catalogs' : info_refresh_catalogs,
        'modifications_count'   : modifications_count,
        'autohub_count'         : autohub_count,
        'autoteka_count_1'        : autoteka_count_1,
        'autoteka_count_2'        : autoteka_count_2,
        'autoteka_count_3'        : autoteka_count_3,
        'estimation_1c'         : estimation_1c,
        'push_count'            : push_count,
        'send_1c'               : send_1c,
        'task_price_count'      : task_price_count,
        'now'                   : DT.datetime.now()

    }
    
    return render(request, 'website/board_monitoring.html', {"params": params}) 


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


def board_monitoring_alert_telegram(text):
    token       = "5936060836:AAHvjlsiWmlZMv44pNdsD4-LW3HGo5Zr274"
    url         = "https://api.telegram.org/bot"
    channel_id  = "382698912"
    url += token
    method = url + "/sendMessage"

    r = requests.post(method, data={
         "chat_id": channel_id,
         "text": text
          })

    if r.status_code != 200:
        raise Exception("post_text error")

###
##
# Записи диктофона
@csrf_exempt
def voice_recorders(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        
        countListRecord = 15
        
        name    = ''
        toast   = ''
        
        user = request.user

        if request.method == "POST":
            file_objects = request.FILES.getlist('file_audio')
            for file_object in file_objects: 
                name = file_object.name.lower()
                #if name.find('.wav') > 0 or name.find('.mp3') > 0: 
                    
                date = ''    
                
                if 'date' in request.POST:
                    date_user = request.POST["date"]
                    if date_user != '':
                        date = DT.datetime.strptime(date_user,'%Y-%m-%dT%H:%M%S')
                
                if date == '':
                    date = get_date_in_name(name)
                
                comment = ''
                if 'comment' in request.POST:
                    comment = request.POST["comment"]

                new_record = Records_voice_recorder()
                if date != '':
                    new_record.date = date   
                new_record.audio        = file_object
                new_record.name         = name
                new_record.user         = request.user
                new_record.comment      = comment
                new_record.save()

                toast = "Запись " + name +  " успешно загружена"
            return JsonResponse({}, status=status.HTTP_200_OK)
        
        if request.method == 'GET':
            name = request.GET.get('name', '')
        
        records     = Records_voice_recorder.objects.filter(user = user).order_by('-date_create')
        
        if name != '':
            records = records.filter(name__icontains = name)
        
        count       = records.count()
        
        page_number = request.GET.get('page')
        
        paginator   = Paginator(records, countListRecord)
        page_obj    = paginator.get_page(page_number)
        
        filtr = {
            'name': name
        }

        params = {
            'type'          : 'voice_recorders',
            'page_number'   : page_number,
            'paginator'     : page_obj,
            'filtr'         : filtr,
            'toast'         : toast,
            'count'         : count
        }
        return render(request, 'website/voice_recorders.html', {'params': params})


def voice_recorder(request, id):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        
        params = {
            'request': request
        }

        recognition     = Records_voice_recorder.objects.get(pk = id)
        data_json       = ''
        data_list       = list()
        
        if len(recognition.data_json) > 0:
            data_json   = json.loads(recognition.data_json)
            conf        = data_json['conf']
            prev        = 0
            text        = ''
            for inf in conf:
                if inf['start'] - prev > 1:
                    data_list.append({'time': convert_to_preferred_format(prev), 'text': text})
                    text = inf['data']['word']
                    prev = inf['start']
                else:
                    text = text + ' ' + inf['data']['word']
                    prev = inf['start']
        
        path    = recognition.audio.url
        time    = 0

        if recognition.time != None:
            time = convert_to_preferred_format(recognition.time)

    
        #audio_file  = AudioSegment.from_file(settings.MEDIA_ROOT + recognition.audio.url)
        #samples     = audio_file.get_array_of_samples()

        params = {
            'type'          : 'voice_recorders',
            'audio_voice'   : recognition,
            'data_json'     : data_json,
            'path'          : path,
            'time'          : time,
            'data_list'     : data_list,
            #'data'          : samples          
        }
        
        return render(request, 'website/voice_recorder.html', {'params': params})


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


def convert_to_preferred_format(sec): 
    sec = int(sec)
    if sec > 0:
        sec = sec % (24 * 3600) 
        hour = sec // 3600 
        sec %= 3600 
        min = sec // 60 
        sec %= 60 
        if hour > 0:
            return "%02d:%02d:%02d" % (hour, min, sec)
        else:
            return "%02d:%02d" % (min, sec)
    else:
        return "00:00"


def convert_time_to_sec(time_str): 
    list_time = time_str.split(':')
    if len(list_time) == 2:
        hh = 0
        mm = int(time_str.split(':')[0].strip())
        ss = int(time_str.split(':')[1].strip())
    elif len(list_time) == 3:
        hh = int(time_str.split(':')[0].strip())
        mm = int(time_str.split(':')[1].strip())
        ss = int(time_str.split(':')[2].strip())
    sec = ss + (mm * 60) + (hh * 60)
    return sec


def record_strip(id, start, end, nomer, comment, times):
    recognition = Records_voice_recorder.objects.get(pk = id)
    name        = recognition.name
    audio_path  = recognition.audio.url
    path_static = r'C:/django_project/kors/kors'
    path_audio  = r'C:/django_project/kors/kors' + audio_path
    path_temp   = path_static + "/temp/"

    AudioSegment.converter  = path_static + "/static/ffmpeg/bin/ffmpeg.exe"
    AudioSegment.ffmpeg     = path_static + "/static/ffmpeg/bin/ffmpeg.exe"
    AudioSegment.ffprobe    = path_static + "/static/ffmpeg/bin/ffprobe.exe"

    mp3 = False
    if name.find('.mp3')> 0:
        sound   = AudioSegment.from_mp3(path_audio)
        mp3     = True
        name_save = path_temp + name.replace('.mp3', '')
    else:
        sound = AudioSegment.from_file(path_audio)
        name_save = path_temp + name.replace('.wav', '')

    start_ms    = start * 1000
    end_ms      = end * 1000
    sound_save  = sound[start_ms:end_ms]
    
    duration = len(sound_save) / 1000

    if mp3:
        name_save = name_save  + '.mp3'
    else:
        name_save = name_save  + '.wav'

    sound_save.export(name_save)

    recognition_new             = Records_voice_recorder()
    recognition_new.user        = recognition.user
    recognition_new.comment     = comment
    #recognition_new.nomer       = nomer
    recognition_new.date        = recognition.date
    recognition_new.name        = recognition.name + ' / ' + times
    recognition_new.recognition = recognition.recognition
    recognition_new.time        = duration
    
    with open(name_save, 'rb') as fi:
        file = File(fi, name=name)
        recognition_new.audio.save(name, file)

    if len(recognition.data_json) > 0:
        data_json       = json.loads(recognition.data_json)
        conf            = data_json['conf']
        new_data_list   = list()
        for inf in conf:
            start_inf_mc = inf['start'] * 1000
            if start_inf_mc >= start_ms and start_inf_mc <= end_ms:
                new_inf = inf
                new_inf['start']            = round((start_inf_mc - start_ms) / 1000, 2)
                new_inf['data']['start']    = round((inf['data']['start'] * 1000  - start_ms) / 1000, 2)
                new_inf['data']['end']      = round(((inf['data']['end'] * 1000) - start_ms) / 1000, 2)
                new_data_list.append(new_inf)
        data_json['conf'] = new_data_list 
        
        data            = data_json['data']
        new_data_list   = list()
        for inf in data:
            start_inf_mc = convert_time_to_sec(inf['start']) * 1000
            if start_inf_mc >= start_ms and start_inf_mc <= end_ms:
                new_data = inf
                new_data['start']  = round((start_inf_mc - start_ms) / 1000, 2)
                new_data_list.append(new_data)
        data_json['data']           = new_data_list
        recognition_new.data_json   = str(data_json).replace("'", '"')
    recognition_new.save()

    return recognition_new.id

###
##
# Рабочие листы 
def docs_rlk(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        countListRecord = 15
        
        filter_count = 0

        name    = ''
        toast   = ''
        date    = ''

        docs    = DocRLK.objects.all()

        units_selected  = RefUnit.objects.filter(buauto = False).exclude(name = 'ЕЦО ГК').exclude(name = 'Основное подразделение') | RefUnit.objects.filter(buauto = True).filter(name__icontains = 'корсавто')
        units_selected  = units_selected.order_by('name')
       
        date            = request.GET.get('date', '')
        name            = request.GET.get('name', '')
        organization    = request.GET.get('organization', '')
        closed          = request.GET.get('closed', '')
        new             = request.GET.get('new', '')
        unit_id         = request.GET.get('unit_id', '')


        if len(date) == 0:
            date_period = DT.datetime.now()
            date_start 	= date_period.replace(day = 1, hour = 0, minute=0, second=0, microsecond=0)
            if date_period.month > 11:
                month_end	= 1
                year_end 	= date_period.year + 1
            else:
                month_end	= date_period.month + 1
                year_end 	= date_period.year
            date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0, microsecond=0)
        else:
            dates = date.split('-')
            if len(dates) == 2:
                year 	        = int(dates[0])
                month 	        = int(dates[1])
                date_period     = DT.datetime.now()
                date_start 	    = date_period.replace(year = year, month = month, day = 1, hour = 0, minute=0, second=0, microsecond=0)
                if month > 11:
                    month_end 	= 1
                    year_end 	= year + 1
                else:
                    month_end 	= month + 1 
                    year_end 	= year
                date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0, microsecond=0)			
        
        date    = date_start

        docs    = docs.filter(dataTime__gte = date_start).filter(dataTime__lt = date_end).order_by('-dataTime')
        
        filter_count = filter_count + 1

        if len(unit_id) > 0:
            filter_count = filter_count + 1
            unit_id = int(unit_id)
            docs = docs.filter(unit__id = unit_id)

        count   = len(docs)
        
        page_number = request.GET.get('page')
        
        paginator   = Paginator(list(docs), countListRecord)
        page_obj    = paginator.get_page(page_number)
        
        filtr = {
            'name'          : name,
            'date'          : date,
            'organization'  : organization,
            'new'           : new,
            'closed'        : closed,
            'unit_id'       : unit_id,
            'filtr_count'   : filter_count
        }

        selected = {
            'units' : units_selected
        }
        
        params = {
            'type'          : 'docs_rlk',
            'page_number'   : page_number,
            'paginator'     : page_obj,
            'selected'      : selected,
            'filtr'         : filtr,
            'toast'         : toast,
            'count'         : count
        }
        return render(request, 'website/docs_rlk.html', {'params': params})    


def doc_rlk(request, id):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        countListRecord = 25
        if request.GET.get('select_count', 25):
            countListRecord = int(request.GET.get('select_count', 25))
        name    = ''
        toast   = ''
        doc   = DocRLK.objects.get(pk = id)

        filtr = {
            'name': name
        }
        params = {
            'type'          : 'docs_rlk',
            'filtr'         : filtr,
            'toast'         : toast,
            'doc'           : doc
        }
        return render(request, 'website/doc_rlk.html', {'params': params}) 




###
##
# Заказ - наряды и расширения зн и сервис
def docs_zn(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        countListRecord = int(request.GET.get('select_count', '25'))
        
        filter_count = 0

        name    = ''
        toast   = ''
        date    = ''

        docs    = DocZN.objects.filter(typeRemont__tizer = True)

        '''
        if request.user.is_superuser == False:
            
            user_login      = request.user.username.lower()
            staffs          = RefStaff.objects.filter(domain_login__iexact = user_login)
            staffs_unit_id  = staffs.distinct()
            units_selected  = RefUnit.objects.filter(pk__in = staffs_unit_id).order_by('name')
            docs            = docs.filter(unit__in = units_selected)
        else:
            units_selected  = RefUnit.objects.filter(buauto = False).order_by('name')
        '''

        units_selected  = RefUnit.objects.filter(buauto = False).exclude(name = 'ЕЦО ГК').exclude(name = 'Основное подразделение').order_by('name')
        units_selected_name  = RefUnit.objects.filter(buauto = False).exclude(name__icontains = 'Техцентр').exclude(name = 'Это ГК').exclude(name__icontains = 'МКЦ ').exclude(name__icontains = 'ОП ').exclude(name = 'ЕЦО ГК').exclude(name = 'Основное подразделение').order_by('name_search').values('name_search').distinct()
        
        date            = request.GET.get('date', '')
        name            = request.GET.get('name', '')
        organization    = request.GET.get('organization', '')
        closed          = request.GET.get('closed', '')
        new             = request.GET.get('new', '')
        unit_id         = request.GET.get('unit_id', '')
        unit_group_id   = request.GET.get('unit_group_id', '')
        list_units_name = request.GET.getlist('units_name[]')
        new_filtr           = request.GET.get('new_filtr')
        save_filter_new     = request.GET.get('save_filter_new')
        path_start          = request.path
        delite_filter       = request.GET.get('delite_filter', '')
        if len(delite_filter) > 0:
            if RefCustomerFiltr.objects.filter(pk = delite_filter).count() > 0:
                RefCustomerFiltr.objects.get(pk = delite_filter).delete()

        filters_user    = RefCustomerFiltr.objects.filter(user = request.user).filter(page = path_start).order_by('-date')  
        if new_filtr != '' and new_filtr != None:
            dict_filtr  = request.get_full_path()
            path_save = ''
            list_path_filtr = dict_filtr.split('/?')[1].split('&')
            one = True
            for path_filtrs in list_path_filtr:
                if path_filtrs[:4] == 'date':
                    continue

                if path_filtrs[:15] == 'save_filter_new': 
                    continue

                if path_filtrs[:9] == 'new_filtr':
                    continue

                if one:
                    path_save = path_save + '?' + path_filtrs
                    one = False
                else:
                    path_save = path_save + '&' + path_filtrs
                    
            path_redirect = path_start + path_save 
            new_filtr_object = RefCustomerFiltr()
            new_filtr_object.page = path_start
            new_filtr_object.path = path_save
            new_filtr_object.user = request.user
            new_filtr_object.name = new_filtr
            new_filtr_object.save()

            return HttpResponseRedirect(path_redirect)
            
        '''
        if len(closed) == 0:
            docs = docs.filter(active = False)
        else:
            filter_count = filter_count + 1
        '''

        if len(date) == 0:
            date_period = DT.datetime.now()
            date_start 	= date_period.replace(day = 1, hour = 0, minute=0, second=0, microsecond=0)
            if date_period.month > 11:
                month_end	= 1
                year_end 	= date_period.year + 1
            else:
                month_end	= date_period.month + 1
                year_end 	= date_period.year
            date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0, microsecond=0)
        else:
            dates = date.split('-')
            if len(dates) == 2:
                year 	        = int(dates[0])
                month 	        = int(dates[1])
                date_period     = DT.datetime.now()
                date_start 	    = date_period.replace(year = year, month = month, day = 1, hour = 0, minute=0, second=0, microsecond=0)
                if month > 11:
                    month_end 	= 1
                    year_end 	= year + 1
                else:
                    month_end 	= month + 1 
                    year_end 	= year
                date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0, microsecond=0)			
        
        date    = date_start

        docs    = docs.filter(dataTime__gte = date_start).filter(dataTime__lt = date_end).order_by('-dataTime')
        
        filter_count = filter_count + 1
        qyery = Q()
        if len(list_units_name) > 0:
            for names_unit in list_units_name:
                qyery.add(Q(('unit__name_search__icontains', names_unit)), Q.OR)
            filter_count = filter_count + 1
            docs = docs.filter(qyery)

        if len(name) > 0:
            docs = docs.filter(nomer__icontains = name) | docs.filter(customer__name__icontains = name) | docs.filter(cars__vin__icontains = name) | docs.filter(cars__mark__icontains = name) | docs.filter(cars__model__icontains = name) | docs.filter(carsGRZ__icontains = name)
            filter_count = filter_count + 1

        if len(organization) > 0:
            filter_count = filter_count + 1
            organization = True
        else:
            docs = docs.filter(customer__company = False)
            organization = False

        if len(unit_group_id) > 0:
            filter_count = filter_count + 1
            unit_group_id = int(unit_group_id)
            units_ = RefUnitGroup.objects.get(pk = unit_group_id)
            docs = docs.filter(unit__in = units_.units.all())

        if len(unit_id) > 0:
            filter_count = filter_count + 1
            unit_id = int(unit_id)
            docs = docs.filter(unit__id = unit_id)

        ###Добавляем инормацию о рекомендациях
        subquery    = Subquery(DoсRecomendation.objects.filter(status__lt = 2).filter(zn_id = OuterRef(name='id')).values('id')[:1], output_field = models.IntegerField())
        docs        = docs.annotate(recomendations_new = Count(subquery))
        
        if len(new) > 0:
           docs = docs.filter(recomendations_new__gt = 0)
           filter_count = filter_count + 1
        
        count   = docs.count()
        
        page_number = request.GET.get('page')
        
        paginator   = Paginator(docs, countListRecord)
        page_obj    = paginator.get_page(page_number)
        
        filtr = {
            'name'          : name,
            'date'          : date,
            'organization'  : organization,
            'new'           : new,
            'closed'        : closed,
            'unit_id'       : unit_id,
            'unit_group_id' : unit_group_id,
            'filtr_count'   : filter_count,
            'list_units_name': list_units_name
        }

        selected = {
            'units_name'    : units_selected_name,
            'units'         : units_selected,
            'units_group'   : RefUnitGroup.objects.filter(active = True).order_by('name')
        }
        
        params = {
            'type'          : 'docs_zn',
            'page_number'   : page_number,
            'select_count'  : countListRecord,
            'paginator'     : page_obj,
            'selected'      : selected,
            'filtr'         : filtr,
            'toast'         : toast,
            'count'         : count,
            'filters_user'  : filters_user
        }
        return render(request, 'website/docs_zn.html', {'params': params})    


def doc_zn(request, id):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        countListRecord = 25
        if request.GET.get('select_count', 25):
            countListRecord = int(request.GET.get('select_count', 25))
        name    = ''
        toast   = ''
        doc   = DocZN.objects.get(pk = id)

        if request.method == "POST":
            
            if 'video' in request.POST:
                file = request.FILES.get('file_video')
                doc.video = file
                doc.save()
                return HttpResponseRedirect(request.build_absolute_uri())

            if 'dop_new' in request.POST:
                new_recomendation                       = DoсRecomendation()
                new_recomendation.zn                    = doc
                new_recomendation.name                  = request.POST['name']
                new_recomendation.kod_recomendation     = random.randrange(1000, 9999)
                new_recomendation.save()

                file_objects = request.FILES.getlist('files')
                for file_object in file_objects: 
                    new_recomendation_files                 = DocRecomendationFiles()
                    new_recomendation_files.recomendation   = new_recomendation
                    new_recomendation_files.file            = file_object
                    new_recomendation_files.save()

                return HttpResponseRedirect(request.build_absolute_uri())
            
            if 'dop_mcu_name' in request.POST:
                new_recomendation                       = DoсRecomendationMCU()
                new_recomendation.zn                    = doc
                new_recomendation.name                  = request.POST['dop_mcu_name']
                new_recomendation.customerStatus        = 1
                new_recomendation.save()

                file_objects = request.FILES.getlist('files')
                for file_object in file_objects: 
                    new_recomendation_files                 = DocRecomendationFilesMCU()
                    new_recomendation_files.recomendation   = new_recomendation
                    new_recomendation_files.file            = file_object
                    new_recomendation_files.save()

                return HttpResponseRedirect(request.build_absolute_uri())

        
        filtr = {
            'name': name
        }
        params = {
            'type'          : 'docs_zn',
            'filtr'         : filtr,
            'toast'         : toast,
            'doc'           : doc
        }
        return render(request, 'website/doc_zn.html', {'params': params}) 


def docs_zn_report_tizer(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        countListRecord = 15
        filter_count    = 0
        docs            = DocZN.objects.filter(closed = True).filter(typeRemont__tizer = True)
        date_start      = request.GET.get('date_start', '')
        date_end        = request.GET.get('date_end', '')
        name            = request.GET.get('name', '')
        organization    = request.GET.get('organization', '')
        closed          = request.GET.get('closed', '')
        new             = request.GET.get('new', '')
        
        filtr_unit_group      = request.GET.get('unit_group', 'yes')

        filter_unit_id          = request.GET.get('select_unit_id', '')
        filter_group_unit_id    = request.GET.get('select_unit_group_id', '')

        if len(closed) == 10:
            docs = docs.filter(active = False)
        else:
            filter_count = filter_count + 1
        
        date_period = DT.datetime.now()
        
        if len(date_start) == 0:
            date_start 	= date_period.replace(day = 1, hour = 0, minute=0, second=0, microsecond=0)
        else:
            date_start  = DT.datetime.strptime(date_start, '%Y-%m-%d')
        
        if len(date_end) == 0:
            if date_period.month > 11:
                month_end	= 1
                year_end 	= date_period.year + 1
            else:
                month_end	= date_period.month + 1
                year_end 	= date_period.year
            date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0, microsecond=0)
        else:
            date_end  = DT.datetime.strptime(date_end, '%Y-%m-%d')
        
        if filtr_unit_group == 'no':
            if filter_unit_id == '':
                units    = docs.filter(dataTime__gte = date_start).filter(dataTime__lt = date_end).values('unit', 'unit__name').distinct().order_by('unit__name')
            else:
                filter_unit_id = int(filter_unit_id)
                units    = docs.filter(dataTime__gte = date_start).filter(unit__id = filter_unit_id).filter(dataTime__lt = date_end).values('unit', 'unit__name').distinct().order_by('unit__name')
            
            recomendationds_count   = 0
            recomendationds_sum     = 0
            
            table_data = list() 
            for unit in units:
                unit_name           = unit['unit__name']
                unit_id             = unit['unit']
                zn_count_all        = docs.filter(dataTime__gte = date_start).filter(dataTime__lt = date_end).filter(unit__id = unit_id).values('pk').distinct().count()
                zn_count            = DoсRecomendation.objects.filter(zn__closed = True).filter(zn__dataTime__gte = date_start).filter(zn__dataTime__lt = date_end).filter(zn__unit__id = unit_id).values('zn').distinct().count()
                if zn_count_all > 0: 
                    zn_percent          = round(zn_count * 100 / zn_count_all, 1)
                else:
                    zn_percent          = 0
                recomendations      = DoсRecomendation.objects.filter(zn__closed = True).filter(zn__dataTime__gte = date_start).filter(zn__dataTime__lt = date_end).filter(zn__unit__id = unit_id).order_by("dataTime")
                recomendations_0    = DoсRecomendation.objects.filter(zn__closed = True).filter(zn__dataTime__gte = date_start).filter(customerStatus = 0).filter(zn__dataTime__lt = date_end).filter(zn__unit__id = unit_id).count()
                recomendations_1    = DoсRecomendation.objects.filter(zn__closed = True).filter(zn__dataTime__gte = date_start).filter(customerStatus = 1).filter(zn__dataTime__lt = date_end).filter(zn__unit__id = unit_id).count()
                recomendations_2    = DoсRecomendation.objects.filter(zn__closed = True).filter(zn__dataTime__gte = date_start).filter(customerStatus = 2).filter(zn__dataTime__lt = date_end).filter(zn__unit__id = unit_id).count()
                recomendations_3    = DoсRecomendation.objects.filter(zn__closed = True).filter(zn__dataTime__gte = date_start).filter(customerStatus = 3).filter(zn__dataTime__lt = date_end).filter(zn__unit__id = unit_id).count()
                
                zn_send_count       =  DoсRecomendation.objects.filter(zn__closed = True).filter(zn__dataTime__gte = date_start).filter(zn__dataTime__lt = date_end).filter(zn__unit__id = unit_id).exclude(customerStatus = 0).values('zn').distinct().count()
                
                try:
                    zn_send_count_sr    = round(zn_send_count * 100 / zn_count_all, 1)
                except:
                    zn_send_count_sr    = 0

                zn_success_count       = DoсRecomendation.objects.filter(zn__closed = True).filter(zn__dataTime__gte = date_start).filter(zn__dataTime__lt = date_end).filter(zn__unit__id = unit_id).filter(customerStatus = 2).values('zn').distinct().count()
                try:
                    zn_success_count_sr    = round(zn_success_count * 100 / zn_send_count, 1)
                except:
                    zn_success_count_sr    = 0

                params_unit = {
                    'unit_name'         : unit_name,
                    'unit_id'           : unit_id,
                    'zn_count_all'      : zn_count_all,
                    'zn_count'          : zn_count,
                    'zn_percent'        : zn_percent, 
                    'recomendations'    : recomendations,
                    'recomendations_0'  : recomendations_0,
                    'recomendations_1'  : recomendations_1,
                    'recomendations_2'  : recomendations_2,
                    'recomendations_3'  : recomendations_3,
                    'zn_send_count'             : zn_send_count,
                    'zn_send_count_sr'          : zn_send_count_sr,
                    'zn_success_count'          : zn_success_count,
                    'zn_success_count_sr'       : zn_success_count_sr
                }
                table_data.append(params_unit)
        else:
            
            if filter_group_unit_id == '':
                units_group = RefUnitGroup.objects.filter(active = True).order_by('name_bi')
            else:
                filter_group_unit_id = int(filter_group_unit_id)
                units_group = RefUnitGroup.objects.filter(active = True).filter(pk = filter_group_unit_id).order_by('name_bi')
            
            recomendationds_count   = 0
            recomendationds_sum     = 0
            
            table_data = list() 
            for unit_group in units_group:
                unit_name           = unit_group.name_bi
                unit_id             = unit_group.id
                unit_info           = unit_group.get_info_units()
                units_group_all     = unit_group.units.all()
                zn_count_all        = docs.filter(dataTime__gte = date_start).filter(dataTime__lt = date_end).filter(unit__in = units_group_all).values('pk').distinct().count()
                zn_count            = DoсRecomendation.objects.filter(zn__closed = True).filter(zn__dataTime__gte = date_start).filter(zn__dataTime__lt = date_end).filter(zn__unit__in = units_group_all).values('zn').distinct().count()
                if zn_count_all > 0: 
                    zn_percent          = round(zn_count * 100 / zn_count_all, 1)
                else:
                    zn_percent          = 0
                recomendations      = DoсRecomendation.objects.filter(zn__closed = True).filter(zn__dataTime__gte = date_start).filter(zn__dataTime__lt = date_end).filter(zn__unit__in = units_group_all).order_by("dataTime")
                recomendations_0    = DoсRecomendation.objects.filter(zn__closed = True).filter(zn__dataTime__gte = date_start).filter(customerStatus = 0).filter(zn__dataTime__lt = date_end).filter(zn__unit__in = units_group_all).count()
                recomendations_1    = DoсRecomendation.objects.filter(zn__closed = True).filter(zn__dataTime__gte = date_start).filter(customerStatus = 1).filter(zn__dataTime__lt = date_end).filter(zn__unit__in = units_group_all).count()
                recomendations_2    = DoсRecomendation.objects.filter(zn__closed = True).filter(zn__dataTime__gte = date_start).filter(customerStatus = 2).filter(zn__dataTime__lt = date_end).filter(zn__unit__in = units_group_all).count()
                recomendations_3    = DoсRecomendation.objects.filter(zn__closed = True).filter(zn__dataTime__gte = date_start).filter(customerStatus = 3).filter(zn__dataTime__lt = date_end).filter(zn__unit__in = units_group_all).count()
                
                zn_send_count       = DoсRecomendation.objects.filter(zn__closed = True).filter(zn__dataTime__gte = date_start).filter(zn__dataTime__lt = date_end).filter(zn__unit__in = units_group_all).exclude(customerStatus = 0).values('zn').distinct().count()
                
                try:
                    zn_send_count_sr    = round(zn_send_count * 100 / zn_count_all, 1)
                except:
                    zn_send_count_sr    = 0

                zn_success_count       = DoсRecomendation.objects.filter(zn__closed = True).filter(zn__dataTime__gte = date_start).filter(zn__dataTime__lt = date_end).filter(zn__unit__in = units_group_all).filter(customerStatus = 2).values('zn').distinct().count()
                try:
                    zn_success_count_sr    = round(zn_success_count * 100 / zn_send_count, 1)
                except:
                    zn_success_count_sr    = 0

                params_unit = {
                    'unit_name'         : unit_name,
                    'unit_id'           : unit_id,
                    'unit_info'         : unit_info,
                    'zn_count_all'      : zn_count_all,
                    'zn_count'          : zn_count,
                    'zn_percent'        : zn_percent, 
                    'recomendations'    : recomendations,
                    'recomendations_0'  : recomendations_0,
                    'recomendations_1'  : recomendations_1,
                    'recomendations_2'  : recomendations_2,
                    'recomendations_3'          : recomendations_3,
                    'zn_send_count'             : zn_send_count,
                    'zn_send_count_sr'          : zn_send_count_sr,
                    'zn_success_count'          : zn_success_count,
                    'zn_success_count_sr'       : zn_success_count_sr
                }
                table_data.append(params_unit)
        
        
        name    = ''
       
        filtr = {
            'name'                  : name,
            'date_start'            : date_start,
            'date_end'              : date_end,
            'unit_group'            : filtr_unit_group,
            'unit_id'               : filter_unit_id,
            'filter_group_unit_id'  : filter_group_unit_id
        }

        selected = {
            'units'              : RefUnit.objects.filter(buauto = False).order_by('name'),
            'units_group'        : RefUnitGroup.objects.filter(active = True).order_by('name_bi'),
        }

        params = {
            'type'          : 'docs_zn_report_tizer',
            'selected'      : selected,
            'filtr'         : filtr,
            'docs'          : table_data
        }
        return render(request, 'website/docs_zn_report_tizer.html', {'params': params}) 


def docs_zn_report_tizer_mcu(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        countListRecord = 15
        filter_count    = 0
        docs            = DocZN.objects.filter(closed = True)
        date_start      = request.GET.get('date_start', '')
        date_end        = request.GET.get('date_end', '')
        name            = request.GET.get('name', '')
        organization    = request.GET.get('organization', '')
        closed          = request.GET.get('closed', '')
        new             = request.GET.get('new', '')

        filtr_unit_group      = request.GET.get('unit_group', 'yes')

        filter_unit_id          = request.GET.get('select_unit_id', '')
        filter_group_unit_id    = request.GET.get('select_unit_group_id', '')

        date_period = DT.datetime.now()

        if len(date_start) == 0:
            date_start 	= date_period.replace(day = 1, hour = 0, minute=0, second=0, microsecond=0)
        else:
            date_start  = DT.datetime.strptime(date_start, '%Y-%m-%d')
        
        if len(date_end) == 0:
            if date_period.month > 11:
                month_end	= 1
                year_end 	= date_period.year + 1
            else:
                month_end	= date_period.month + 1
                year_end 	= date_period.year
            date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0, microsecond=0)
        else:
            date_end  = DT.datetime.strptime(date_end, '%Y-%m-%d')

        if filtr_unit_group == 'no':
            if filter_unit_id == '':
                units    = docs.filter(dataTime__gte = date_start).filter(dataTime__lt = date_end).values('unit', 'unit__name').distinct().order_by('unit__name')
            else:
                filter_unit_id = int(filter_unit_id)
                units    = docs.filter(dataTime__gte = date_start).filter(unit__id = filter_unit_id).filter(dataTime__lt = date_end).values('unit', 'unit__name').distinct().order_by('unit__name')
            
            recomendationds_count   = 0
            recomendationds_sum     = 0
            
            table_data = list() 
            for unit in units:
                unit_name           = unit['unit__name']
                unit_id             = unit['unit']
                zn_count            = DoсRecomendationMCU.objects.filter(zn__closed = True).filter(zn__dataTime__gte = date_start).filter(zn__dataTime__lt = date_end).filter(zn__unit__id = unit_id).values('zn').distinct().count()
                zn_count_all        = docs.filter(dataTime__gte = date_start).filter(dataTime__lt = date_end).filter(unit__id = unit_id).values('pk').distinct().count()
                if zn_count_all > 0: 
                    zn_percent          = round(zn_count * 100 / zn_count_all, 1)
                else:
                    zn_percent          = 0
                recomendations      = DoсRecomendationMCU.objects.filter(zn__dataTime__gte = date_start).filter(zn__dataTime__lt = date_end).filter(zn__unit__id = unit_id).order_by("dataTime")
                recomendations_0    = DoсRecomendationMCU.objects.filter(zn__dataTime__gte = date_start).filter(customerStatus = 0).filter(zn__dataTime__lt = date_end).filter(zn__unit__id = unit_id).count()
                recomendations_1    = DoсRecomendationMCU.objects.filter(zn__dataTime__gte = date_start).filter(customerStatus = 1).filter(zn__dataTime__lt = date_end).filter(zn__unit__id = unit_id).count()
                recomendations_2    = DoсRecomendationMCU.objects.filter(zn__dataTime__gte = date_start).filter(customerStatus = 2).filter(zn__dataTime__lt = date_end).filter(zn__unit__id = unit_id).count()
                recomendations_3    = DoсRecomendationMCU.objects.filter(zn__dataTime__gte = date_start).filter(customerStatus = 3).filter(zn__dataTime__lt = date_end).filter(zn__unit__id = unit_id).count()
                
                zn_send_count       = DoсRecomendationMCU.objects.filter(zn__closed = True).filter(zn__dataTime__gte = date_start).filter(zn__dataTime__lt = date_end).filter(zn__unit__id = unit_id).exclude(customerStatus = 0).values('zn').distinct().count()
                try:
                    zn_send_count_sr    = round(zn_send_count * 100 / zn_count_all, 1)
                except:
                    zn_send_count_sr    = 0
                    
                zn_success_count       = DoсRecomendationMCU.objects.filter(zn__closed = True).filter(zn__dataTime__gte = date_start).filter(zn__dataTime__lt = date_end).filter(zn__unit__id = unit_id).filter(customerStatus = 2).values('zn').distinct().count()
                try:
                    zn_success_count_sr    = round(zn_success_count * 100 / zn_send_count, 1)
                except:
                    zn_success_count_sr    = 0


                params_unit = {
                    'unit_name'         : unit_name,
                    'unit_id'           : unit_id,
                    'zn_count'          : zn_count,
                    'zn_count_all'      : zn_count_all,
                    'zn_percent'        : zn_percent,
                    'recomendations'    : recomendations,
                    'recomendations_0'  : recomendations_0,
                    'recomendations_1'  : recomendations_1,
                    'recomendations_2'  : recomendations_2,
                    'recomendations_3'  : recomendations_3,
                    'zn_send_count'             : zn_send_count,
                    'zn_send_count_sr'          : zn_send_count_sr,
                    'zn_success_count'          : zn_success_count,
                    'zn_success_count_sr'       : zn_success_count_sr
                }
                table_data.append(params_unit)
        else:
            if filter_group_unit_id == '':
                units_group = RefUnitGroup.objects.filter(active = True).order_by('name_bi')
            else:
                filter_group_unit_id = int(filter_group_unit_id)
                units_group = RefUnitGroup.objects.filter(active = True).filter(pk = filter_group_unit_id).order_by('name_bi')
            
            recomendationds_count   = 0
            recomendationds_sum     = 0
            
            table_data = list() 
            for unit_group in units_group:
                unit_name           = unit_group.name_bi
                unit_id             = unit_group.id
                unit_info           = unit_group.get_info_units()
                units_group_all     = unit_group.units.all()
                zn_count            = DoсRecomendationMCU.objects.filter(zn__closed = True).filter(zn__dataTime__gte = date_start).filter(zn__dataTime__lt = date_end).filter(zn__unit__in = units_group_all).values('zn').distinct().count()
                zn_count_all        = docs.filter(dataTime__gte = date_start).filter(dataTime__lt = date_end).filter(unit__in = units_group_all).values('pk').distinct().count()
                if zn_count_all > 0: 
                    zn_percent          = round(zn_count * 100 / zn_count_all, 1)
                else:
                    zn_percent          = 0
                recomendations      = DoсRecomendationMCU.objects.filter(zn__dataTime__gte = date_start).filter(zn__dataTime__lt = date_end).filter(zn__unit__in = units_group_all).order_by("dataTime")
                recomendations_0    = DoсRecomendationMCU.objects.filter(zn__dataTime__gte = date_start).filter(customerStatus = 0).filter(zn__dataTime__lt = date_end).filter(zn__unit__in = units_group_all).count()
                recomendations_1    = DoсRecomendationMCU.objects.filter(zn__dataTime__gte = date_start).filter(customerStatus = 1).filter(zn__dataTime__lt = date_end).filter(zn__unit__in = units_group_all).count()
                recomendations_2    = DoсRecomendationMCU.objects.filter(zn__dataTime__gte = date_start).filter(customerStatus = 2).filter(zn__dataTime__lt = date_end).filter(zn__unit__in = units_group_all).count()
                recomendations_3    = DoсRecomendationMCU.objects.filter(zn__dataTime__gte = date_start).filter(customerStatus = 3).filter(zn__dataTime__lt = date_end).filter(zn__unit__in = units_group_all).count()
                
                zn_send_count       = DoсRecomendationMCU.objects.filter(zn__closed = True).filter(zn__dataTime__gte = date_start).filter(zn__dataTime__lt = date_end).filter(zn__unit__in = units_group_all).exclude(customerStatus = 0).values('zn').distinct().count()
                try:
                    zn_send_count_sr    = round(zn_send_count * 100 / zn_count_all, 1)
                except:
                    zn_send_count_sr    = 0
                    
                zn_success_count       = DoсRecomendationMCU.objects.filter(zn__closed = True).filter(zn__dataTime__gte = date_start).filter(zn__dataTime__lt = date_end).filter(zn__unit__in = units_group_all).filter(customerStatus = 2).values('zn').distinct().count()
                try:
                    zn_success_count_sr    = round(zn_success_count * 100 / zn_send_count, 1)
                except:
                    zn_success_count_sr    = 0

                params_unit = {
                    'unit_name'         : unit_name,
                    'unit_id'           : unit_id,
                    'unit_info'         : unit_info,
                    'zn_count'          : zn_count,
                    'zn_count_all'      : zn_count_all,
                    'zn_percent'        : zn_percent,
                    'recomendations'    : recomendations,
                    'recomendations_0'  : recomendations_0,
                    'recomendations_1'  : recomendations_1,
                    'recomendations_2'  : recomendations_2,
                    'recomendations_3'  : recomendations_3,
                    'zn_send_count'             : zn_send_count,
                    'zn_send_count_sr'          : zn_send_count_sr,
                    'zn_success_count'          : zn_success_count,
                    'zn_success_count_sr'       : zn_success_count_sr
                }
                table_data.append(params_unit)

        name    = ''
       
        filtr = {
            'name'          : name,
            'date_start'    : date_start,
            'date_end'      : date_end,
            'unit_group_id' : filter_group_unit_id,
            'unit_group'            : filtr_unit_group,
            'unit_id'               : filter_unit_id,
            'filter_group_unit_id'  : filter_group_unit_id
        }
        selected = {
            'units'              : RefUnit.objects.filter(buauto = False).order_by('name'),
            'units_group'        : RefUnitGroup.objects.filter(active = True).order_by('name_bi'),            
        }
        
        params = {
            'filtr'         : filtr,
            'type'          : 'docs_zn_report_tizer_mcu',
            'selected'      : selected,
            'docs'          : table_data
        }
        return render(request, 'website/docs_zn_report_tizer_mcu.html', {'params': params}) 


def doc_recomendation(request, id):
    
    recomendation = DoсRecomendation.objects.get(pk = id)
        
    params = {
        'recomendation' : recomendation,
        'url'           : request.build_absolute_uri(),
        'doc'           : recomendation.zn
    }
    return render(request, 'website/doc_recomendation.html', {'params': params}) 


def doc_recomendation_mcu(request, id):
    
    recomendation = DoсRecomendationMCU.objects.get(pk = id)
        
    params = {
        'recomendation' : recomendation,
        'url'           : request.build_absolute_uri(),
        'doc'           : recomendation.zn
    }
    return render(request, 'website/doc_recomendation_mcu.html', {'params': params}) 


def get_video(request, pk: int):
    _video = get_object_or_404(DocRecomendationFiles, id=pk)
    return render(request, "video_hosting/video.html", {"video": _video})


def get_streaming_video(request, pk: int):
    file, status_code, content_length, content_range = open_file(request, pk)
    response = StreamingHttpResponse(file, status=status_code, content_type='video/mp4')

    response['Accept-Ranges'] = 'bytes'
    response['Content-Length'] = str(content_length)
    response['Cache-Control'] = 'no-cache'
    response['Content-Range'] = content_range
    response['X-Frame-Options'] = "ALLOW"
    return response


def rem_zone(request):
    
    #date_start      = DT.datetime.today()
    #date_start      = date_start.combine(date_start.date(), date_start.min.time())
    #date_end        = date_start.replace(hour=23, minute=59, second=59) 
    
    #subquery    = Subquery(DocZNPerformers.objects.filter(zn_id = OuterRef(name='id')).values('id')[:1], output_field = models.IntegerField())
    #docs_zn     = DocZN.objects.filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(unit__id = 14)
    #docs_zn     = docs_zn.annotate(perfomers = Count(subquery)).order_by('dataTime')

    units = RefUnit.objects.filter(name__icontains = 'КорсАвто').order_by('name')

    estimations = RegInteractivOcenka.objects.all()
    sub_podgotovka  = RegEstimationPodgotovka.objects.filter(estimation__id = OuterRef(name='id')).filter(start = None).filter(status = 0).values('estimation').annotate(cnt=Count('pk'))
    sub_ss          = RegEstimationSS.objects.filter(estimation__id = OuterRef(name='id')).filter(start = None).filter(status = 0).values('estimation').annotate(cnt=Count('pk'))
    sub_mcu         = RegEstimationMCU.objects.filter(estimation__id = OuterRef(name='id')).filter(start = None).filter(status = 0).values('estimation').annotate(cnt=Count('pk'))

    #Coalesce(Subquery(subquery_eval_avtohab_s), Value(0)))
    
    estimations = estimations.annotate(
        start_podgotovka        = Coalesce(Subquery(sub_podgotovka.values('cnt')[:1]), Value(0))).annotate(
        start_ss                = Coalesce(Subquery(sub_ss.values('cnt')[:1]), Value(0))).annotate(
        start_mcu               = Coalesce(Subquery(sub_mcu.values('cnt')[:1]), Value(0)))
        
    estimations_start = estimations.filter(Q(start_podgotovka__gt = 0) | Q(start_ss__gt = 0) | Q(start_mcu__gt = 0))

    params = {
        'units'                 : units,
        'estimations_start'     : estimations_start
        }
    return render(request, 'website/rem_zone.html', {'params': params})   


def online_doc(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        countListRecord = 25
        if request.GET.get('select_count', 25):
            countListRecord = int(request.GET.get('select_count', 25))
        
        unit_id         = request.GET.get('unit_id', '')
        unit_name       = ''

        filter_count    = 0
        docs            = Online_doc.objects.all()
        date_start      = request.GET.get('date_start', '')
        date_end        = request.GET.get('date_end', '')
        
        date_period = DT.datetime.now()

        if len(date_start) == 0:
            date_start 	= date_period.replace(day = 1, hour = 0, minute=0, second=0, microsecond=0)
        else:
            date_start  = DT.datetime.strptime(date_start, '%Y-%m-%d')
        
        if len(date_end) == 0:
            if date_period.month > 11:
                month_end	= 1
                year_end 	= date_period.year + 1
            else:
                month_end	= date_period.month + 1
                year_end 	= date_period.year
            date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0, microsecond=0)
        else:
            date_end  = DT.datetime.strptime(date_end, '%Y-%m-%d')

        docs = docs.filter(dataTimeCreate__gte = date_start).filter(dataTimeCreate__lte = date_end).order_by('-dataTimeCreate')

        if len(unit_id) > 0:
            unit        = RefUnit.objects.get(pk = unit_id)
            unit_name   = unit.name
            docs        = docs.filter(unit = unit)

        page_number = request.GET.get('page')
        
        paginator   = Paginator(docs, countListRecord)
        page_obj    = paginator.get_page(page_number)
        if docs.count() > 0:
            count                           = docs.count()
            count_opened                    = docs.exclude(dataTimeOpen = None).count()
            count_confirmed                 = docs.exclude(dataTimeRecord = None).count() + docs.filter(call = True).count() 
            count_opened_percent            = round(count_opened * 100 / count, 1)
            count_confirmed_percent         = round(count_confirmed * 100 / count, 1)
            count_opened_confirmed_percent  = round(count_confirmed * 100 / count_opened, 1)
        else:
            count                           = 0
            count_opened                    = 0
            count_confirmed                 = 0
            count_opened_percent            = 0
            count_confirmed_percent         = 0
            count_opened_confirmed_percent  = 0

        select = {
            'units' : RefUnit.objects.filter(buauto = False).exclude(name = 'ЕЦО ГК').exclude(name = 'Основное подразделение').order_by('name')
        }
        filtr = {
            'unit_id'       : unit_id,
            'unit_name'     : unit_name,
            'date_start'    : date_start,
            'date_end'      : date_end
        }
        params = {
            'filtr'                             : filtr,
            'type'                              : 'online_doc',
            'paginator'                         : page_obj,
            'select_count'                      : countListRecord,
            'count'                             : count,
            'count_opened'                      : count_opened,
            'count_opened_percent'              : count_opened_percent,
            'count_confirmed'                   : count_confirmed,
            'count_confirmed_percent'           : count_confirmed_percent,
            'count_opened_confirmed_percent'    : count_opened_confirmed_percent,
            'select'                            : select
        }
        return render(request, 'website/online_doc.html', {'params': params})    


def records_online_doc(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        countListRecord = 25
        if request.GET.get('select_count', 25):
            countListRecord = int(request.GET.get('select_count', 25))
        
        unit_id         = request.GET.get('unit_id', '')
        unit_name       = ''

        filter_count    = 0
        docs            = Records_online_doc.objects.all()
        date_start      = request.GET.get('date_start', '')
        date_end        = request.GET.get('date_end', '')
        
        date_period = DT.datetime.now()

        if len(date_start) == 0:
            date_start 	= date_period.replace(day = 1, hour = 0, minute=0, second=0, microsecond=0)
        else:
            date_start  = DT.datetime.strptime(date_start, '%Y-%m-%d')
        
        if len(date_end) == 0:
            if date_period.month > 11:
                month_end	= 1
                year_end 	= date_period.year + 1
            else:
                month_end	= date_period.month + 1
                year_end 	= date_period.year
            date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0, microsecond=0)
        else:
            date_end  = DT.datetime.strptime(date_end, '%Y-%m-%d')

        docs = docs.filter(dataTimeRecord__gte = date_start).filter(dataTimeRecord__lte = date_end).order_by('-dataTimeRecord')

        if len(unit_id) > 0:
            unit        = RefUnit.objects.get(pk = unit_id)
            unit_name   = unit.name
            docs        = docs.filter(unit = unit)

        page_number = request.GET.get('page')
        
        paginator   = Paginator(docs, countListRecord)
        page_obj    = paginator.get_page(page_number)
        if docs.count() > 0:
            count                           = docs.count()
            count_opened                    = docs.exclude(dataTimeOpen = None).count()
            count_confirmed                 = docs.filter(confirmed = True).count()
            count_opened_percent            = round(count_opened * 100 / count, 1)
            count_confirmed_percent         = round(count_confirmed * 100 / count, 1)
            count_opened_confirmed_percent  = round(count_confirmed * 100 / count_opened, 1)
        else:
            count                           = 0
            count_opened                    = 0
            count_confirmed                 = 0
            count_opened_percent            = 0
            count_confirmed_percent         = 0
            count_opened_confirmed_percent  = 0

        select = {
            'units' : RefUnit.objects.filter(buauto = False).exclude(name = 'ЕЦО ГК').exclude(name = 'Основное подразделение').order_by('name')
        }
        filtr = {
            'unit_id'       : unit_id,
            'unit_name'     : unit_name,
            'date_start'    : date_start,
            'date_end'      : date_end
        }
        params = {
            'filtr'             : filtr,
            'type'              : 'records_online_doc',
            'paginator'         : page_obj,
            'select_count'      : countListRecord,
            'count'             : count,
            'count_opened'      : count_opened,
            'count_opened_percent'      : count_opened_percent,
            'count_confirmed'           : count_confirmed,
            'count_confirmed_percent'   : count_confirmed_percent,
            'count_opened_confirmed_percent'    : count_opened_confirmed_percent,
            'select'                    : select
        }
        return render(request, 'website/records_online_doc.html', {'params': params})    



###
##
# Обновление каталогов авто ру
def upload_auto_ru(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else: 
        params = {
            'type'  : 'autoru',
            'text'  : 'Выберите файл и нажмите загрузить'
        }
        return render(request, 'website/upload_auto_ru.html', {'params': params})

def upload_auto_ru_post(request):

    xmlfile     = request.FILES['xmlfile']
    parser      = ETree.XMLParser(encoding="utf-8")
    tree        = ETree.parse(xmlfile, parser=parser)

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
            autoru_model.save()
            
            for modification in model.findall('modification'):
                modificationName    = modification.get('name')
                modificationID      = modification.get('id')

                result = re.search(r'(\d\.\d)?(HYB|D|Electro)?\s(AT|MT|AMT|CVT)?\s\((.+)\)', modificationName, re.IGNORECASE)
                engineVolume = result.group(1) if result.group(1) else '0.0'        # Объем двигателя

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
                
                typeBody = RefTypeBody.objects.get_or_create(name=bt)[0]
                
                '''
                if modificationID == None:
                    newAutoruModification_count = AutoruModification.objects.filter(model = autoru_model).filter(name = modificationName).count()
                    if newAutoruModification_count == 0:
                        newAutoruModification = AutoruModification()
                    else:
                        newAutoruModification = AutoruModification.objects.filter(model = autoru_model).filter(name = modificationName)[0]
                else:
                    newAutoruModification_count = AutoruModification.objects.filter(model = autoru_model).filter(idSite = int(modificationID)).count()
                    if newAutoruModification_count == 0:
                        newAutoruModification = AutoruModification()
                    else:
                        newAutoruModification = AutoruModification.objects.filter(model = autoru_model).filter(idSite = int(modificationID))[0]
                '''
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
                newAutoruModification.save()

                complectations = modification[7]
                if len(complectations) > 0:
                    countComplectation = 0
                    
                    while countComplectation < len(complectations):
                        complectationName   = complectations[countComplectation].text
                        complectationID     = complectations[countComplectation].get('id')
                        try:
                            newAutoruComplectation = AutoruComplectation.objects.get(idSite = complectationID)
                        except:
                            newAutoruComplectation = AutoruComplectation()
                        newAutoruComplectation.name         = complectationName
                        newAutoruComplectation.idSite       = complectationID
                        newAutoruComplectation.modification = newAutoruModification
                        newAutoruComplectation.save()
                        countComplectation = countComplectation + 1

    return render(request, 'website/upload_auto_ru.html', {'params': 'ok'})



# Обновление каталогов авито
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

def upload_avito_ru(request):
    text = ''
    if request.method == 'POST':
        xmlfile     = request.FILES['xmlfile']
        parser      = ETree.XMLParser(encoding="utf-8")
        tree        = ETree.parse(xmlfile, parser=parser)

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

        text = 'post'
    else:
        text = 'Выберите файл и нажмите загрузить'
    params = {
        'type'  : 'avito',
        'text'  : text
    }
    return render(request, 'website/refresh_avito.html', {'params': params})




###
##
# Ссылки на выгрузки
def links_dc(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        countListRecord = 25
        
        unit_id         = request.GET.get('unit_id', '')
        type_id         = request.GET.get('type_id', '')
        page_number     = request.GET.get('page')

        links       = RefExchangeCars.objects.order_by('unit')
        
        if len(unit_id) > 0:
            links = links.filter(unit__id = unit_id) 

        if len(type_id) > 0:
            links = links.filter(type_exchange__id = type_id)
    
        paginator   = Paginator(links, countListRecord)
        page_obj    = paginator.get_page(page_number)
        
        filtr = {
            'unit_id'           : unit_id,
            'type_id'           : type_id,
            'page_number'       : page_number
        }

        toast   = ''
        count   = ''

        selected = {
            'units' : RefUnit.objects.filter(buauto = False).order_by('name'),
            'type'  : RefTypeExchange.objects.all().order_by('name')
        }

        params = {
            'type'          : 'links',
            'page_number'   : page_number,
            'paginator'     : page_obj,
            'filtr'         : filtr,
            'selected'      : selected,
            'toast'         : toast,
            'count'         : count
        }
        return render(request, 'website/link_dc_exchange.html', {'params': params}) 



###
##
# Доски приветствия
def boards(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        countListRecord = 25
        
        name        = request.POST.get('name', '')
        city        = request.POST.get('select_city', '')
        page_number = request.GET.get('page')

        units       = RefUnit.objects.filter(buauto = False).order_by('name')
        
        if len(name) > 0:
            units = units.filter(name__icontains = name) 
        
        if len(city) > 0:
           units = units.filter(city__id = city) 

        paginator   = Paginator(list(units), countListRecord)
        page_obj    = paginator.get_page(page_number)
        
        filtr = {
            'name'          : name,
            'city_id'       : city,
            'page_number'   : page_number
        }

        toast   = ''
        count   = ''

        selected = {
            'citys': RefCity.objects.all().order_by('name')
        }

        params = {
            'type'          : 'boards',
            'page_number'   : page_number,
            'paginator'     : page_obj,
            'filtr'         : filtr,
            'selected'      : selected,
            'toast'         : toast,
            'count'         : count
        }
        return render(request, 'boards/boards_list.html', {'params': params}) 


def board(request, id):
    
    unit            = RefUnit.objects.get(pk = id)
    page            = 0
    docs_online     = list()

    if 'page' in request.GET:
        page = int(request.GET['page'])
    page = 0

    if page == 0:
        date_start      = DT.datetime.now().date()
        date_end        = date_start + DT.timedelta(days=1)
        docs            = DocZN.objects.filter(unit = unit).exclude(master = None).filter(typeRemont__tizer = True).filter(active = False).filter(dataTime__range = [date_start, date_end]).order_by('dataTime')
        staffs_doc      = DocZN.objects.filter(unit = unit).exclude(master = None).filter(typeRemont__tizer = True).filter(active = False).filter(dataTime__range = [date_start, date_end]).values('master').distinct('master')
        staffs          = RefStaff.objects.filter(id__in = [staffs_doc]).order_by('name')
        url_next        = '/boards/' + id + '/?page=' + str(page + 1)
        if unit.board_name == 'lada':
            docs_online     = Records_online_doc.objects.filter(dataTimeRecord__range = [DT.datetime.now(), date_end]).filter(unit = unit).order_by('dataTimeRecord')
            get_staff = int(request.GET.get('staff_number', 0))
            count = len(list(staffs)) - 1
            if len(list(staffs)) > 0:
                if get_staff > count:
                    get_staff = 0
                staffs_list = list(staffs)[get_staff]
                docs        = docs.filter(master__id = staffs_list.id)
                staffs      = list()
                staffs.append(staffs_list)
            url_next        = '/boards/' + id + '/?page=' + str(0) + '&staff_number=' + str(get_staff + 1)
            
        params = {
            'time'          : 30,
            'docs'          : docs,
            'staffs'        : staffs,
            'url_next'      : url_next,
            'unit'          : unit,
            'name'          : unit.name_board,
            'docs_online'   : docs_online
        }

        if len(unit.board_name) == 0:
            return render(request, 'boards/board.html', {'params': params})
        else:
            board_name = "boards/board_" + unit.board_name + ".html" 
            return render(request, board_name, {'params': params})
    else:
        url_next = '/boards/' + id + '/?page=' + str(page + 1)
        params = {
            'time'      : page_ref.time,
            'url_next'  : url_next,
            'page_ref'  : page_ref
        }
        return render(request, 'boards/board_page.html', {'params': params})


def monitors(request):
    
    count_list_records  = 25
    
    boards              = RefBoards.objects.all().order_by('name')   
    page                = int(request.GET.get('page', '1'))

    name = request.GET.get('name', '')
    if len(name) > 0:
        boards = boards.filter(name__icontains = name) 
    
    filtr = {
            'name'          : name,
            'page_number'   : page
        }

    paginator   = Paginator(list(boards), count_list_records)
    page_obj    = paginator.get_page(page)

    params = {
            'type'          : 'monitors',
            'page_number'   : page,
            'paginator'     : page_obj,
            'filtr'         : filtr
        }
    
    return render(request, 'monitors/monitors_list.html', {'params': params})


def monitor_edit(request, id):
    
    if id == '0':
        if request.method == 'POST':
            board = RefBoards()
            board.name                      = request.POST.get('name', '')
            board.name_title                = request.POST.get('name_title', '')
            board.filter_mark               = request.POST.get('filter_mark', '')
            board.max_count_records_page    = int(request.POST.get('max_count_records_page', '60'))
            board.time_refresh              = int(request.POST.get('time_refresh', '60'))
            board.board_name                = request.POST.get('board_name', '')
            board.phone                     = request.POST.get('phone', '')
            board.email                     = request.POST.get('email', '')
            board.webSite                   = request.POST.get('webSite', '')
            board.adress                    = request.POST.get('adress', '')
            board.table_view_customer       = 'table_view_customer' in request.POST
            board.table_view_staff          = 'table_view_staff' in request.POST
            board.table_view_plate_number   = 'table_view_plate_number' in request.POST
            board.table_view_status         = 'table_view_status' in request.POST
            board.table_view_vin            = 'table_view_vin' in request.POST
            board.table_view_mark           = 'table_view_mark' in request.POST
            board.table_view_model          = 'table_view_model' in request.POST
            board.save()
            return HttpResponseRedirect(request.get_full_path().replace('/0/', '/' + str(board.pk) + '/'))
            
        params = {
                'type'          : 'monitors',
                'tabindex'      : 0,
                'board'         : None
            }
        return render(request, 'monitors/monitor_edit.html', {'params': params})        

    if id != '0':
        board       = RefBoards.objects.get(pk = id)
        page        = int(request.GET.get('page', '0')) 
        params = {
                        'type'          : 'monitors',
                        'tabindex'      : page,
                        'board'         : board
            }

        if request.method == 'POST':
            
            if 'new_fotos_staff' in request.POST:
                pk_staff = request.POST.get('staff_id', '')
                if pk_staff != '':
                    staff = RefStaff.objects.get(pk = pk_staff)
                    if 'image_staff'  in request.FILES:
                        filename = request.FILES['image_staff']
                        staff.main_photo = filename
                        staff.save()
                
            if 'save_ass' in request.POST:
                board.name                      = request.POST.get('name', '')
                board.name_title                = request.POST.get('name_title', '')
                board.filter_mark               = request.POST.get('filter_mark', '')
                board.max_count_records_page    = int(request.POST.get('max_count_records_page', '60'))
                board.time_refresh              = int(request.POST.get('time_refresh', '60'))
                board.board_name                = request.POST.get('board_name', '')
                board.phone                     = request.POST.get('phone', '')
                board.email                     = request.POST.get('email', '')
                board.webSite                   = request.POST.get('webSite', '')
                board.adress                    = request.POST.get('adress', '')
                board.table_view_customer       = 'table_view_customer' in request.POST
                board.table_view_staff          = 'table_view_staff' in request.POST
                board.table_view_plate_number   = 'table_view_plate_number' in request.POST
                board.table_view_status         = 'table_view_status' in request.POST
                board.table_view_vin            = 'table_view_vin' in request.POST
                board.table_view_mark           = 'table_view_mark' in request.POST
                board.table_view_model          = 'table_view_model' in request.POST

                board.save()
            
            if 'save_units' in request.POST:
                board.units.clear()                    
                for key in request.POST.keys():
                    if key.startswith('unit_'):
                        val_key = request.POST.get(key)
                        pk      = key.replace('unit_', '')
                        board.units.add(RefUnit.objects.get(pk = pk))
                board.save()

            return HttpResponseRedirect(request.get_full_path())
        
        if request.method == 'GET':
            
            if page == 0:
                params = {
                        'type'          : 'monitors',
                        'tabindex'      : page,
                        'board'         : board
                    }
            elif page == 1:
                list_units  = list()
                units       = RefUnit.objects.filter(buauto = False).order_by('name')
                for unit in units:
                    success = False
                    if unit in board.units.all():
                        success = True
                    
                    unit_info = {
                        'unit'      : unit,
                        'success'   : success
                    }
                    list_units.append(unit_info) 

                params = {
                        'type'          : 'monitors',
                        'tabindex'      : page,
                        'board'         : board,
                        'units'         : list_units
            }
            elif page == 2:
                staffs_resource = ResourcePlanning.objects.filter(type__in_service = True).filter(serviceRequest__unit__in = board.units.all()).filter(active = True).values('staff').distinct('staff')
                staffs          = RefStaff.objects.filter(id__in = [staffs_resource]).order_by('name')
                params = {
                        'type'          : 'monitors',
                        'tabindex'      : page,
                        'board'         : board,
                        'staffs'        : list(staffs)
            }
        return render(request, 'monitors/monitor_edit.html', {'params': params})


def monitor(request, id):
    
    board       = RefBoards.objects.get(pk = id)    
    page        = 0

    if 'page' in request.GET:
        page = int(request.GET['page'])
    '''
    if page > 0:
        
        lists_page = RefBoardsPage.objects.filter(unit=unit).filter(activated= True)
        if page <= len(lists_page):
            if page > 0:
                page_ref = lists_page[page-1]
        else:
            page = 0
    '''

    if page == 0:
        date_start      = DT.datetime.now().date()
        date_end        = date_start + DT.timedelta(days=1)
        
        objects         = ResourcePlanning.objects.filter(type__in_service = True).filter(serviceRequest__unit__in = board.units.all()).filter(active = True).filter(dateStart__range = [date_start, date_end]).filter(staff__no_monitors = False)
        
        if board.filter_mark != '': 
            objects = objects.filter(serviceRequest__cars__mark__icontains = board.filter_mark)
        
        subquery        = Subquery(ResourcePlanning.objects.filter(type__out_service = True).filter(serviceRequest__unit__in = board.units.all()).filter(active = True).filter(dateStart__range = [date_start, date_end]).filter(serviceRequest_id = OuterRef(name='serviceRequest_id')).values('dateStart')[:1], output_field = models.DateField())
        subquery_zn     = Subquery(DocZN.objects.filter(serviceRequest_id = OuterRef(name='serviceRequest_id')).values('closed')[:1], output_field = models.BooleanField())
        
        objects         = objects.annotate(date_end = subquery)
        objects         = objects.annotate(status   = subquery_zn)
        
        staffs_doc      = objects.values('staff').distinct('staff')
        staffs          = RefStaff.objects.filter(id__in = [staffs_doc]).order_by('name')
        
        objects         = objects.order_by('dateStart')
        page_number     = int(request.GET.get('list_page', '1'))

        if board.one_staff:
            get_staff = int(request.GET.get('staff_number', 0))
            count = len(list(staffs)) - 1
            if len(list(staffs)) > 0:
                if get_staff > count:
                    get_staff = 0
                staffs_list = list(staffs)[get_staff]
                objects        = objects.filter(staff__id = staffs_list.id)
                staffs      = list()
                staffs.append(staffs_list)
            paginator       = Paginator(objects, board.max_count_records_page)
        
            page_max        = int(paginator.count / board.max_count_records_page + 1)

            if page_number > page_max:
                page_number = 1
                url_next        = '/monitors/' + id + '/?list_page=' + str(page_number) + '&staff_number=' + str(get_staff + 1)
            else:
                url_next        = '/monitors/' + id + '/?list_page=' + str(page_number + 1) + '&staff_number=' + str(get_staff)
            
        else:
            paginator       = Paginator(objects, board.max_count_records_page)
        
            page_max        = int(paginator.count / board.max_count_records_page + 1)

            if page_number > page_max:
                page_number = 1
            
            url_next = '/monitors/' + id + '/?list_page=' + str(page_number + 1)

        page_obj    = paginator.get_page(page_number)
        
        params = {
            'time'          : 30,
            'board'         : board,
            'objects'       : page_obj.object_list,
            'staffs'        : staffs,
            'count'         : page_max,
            'url_next'      : url_next,
            'time_refresh'  : board.time_refresh
            #'name'          : unit.name_board,
            #'docs_online'   : docs_online
        }

        if len(board.board_name) == 0:
            return render(request, 'monitors/board.html', {'params': params})
        else:
            board_name = "monitors/" + board.board_name + ".html" 
            return render(request, board_name, {'params': params})
    else:
        url_next = '/monitors/' + id + '/?page=' + str(page + 1)
        params = {
            'time'      : page_ref.time,
            'url_next'  : url_next,
            'page_ref'  : page_ref
        }
        return render(request, 'monitors/board_page.html', {'params': params})


def refresh_base_manufacturen(request):
    text = ''
    if request.method == 'POST':

        RefManufacturer.objects.all().delete()

        xmlfile     = request.FILES['xmlfile']
        try:
            path = default_storage.save('tmp/' + xmlfile.name, ContentFile(xmlfile.read()))
            tmp_file = os.path.join(settings.MEDIA_ROOT, path)
            wb = load_workbook(tmp_file)
            worksheet = wb.active
            # Iterate the loop to read the cell values
            for i in range(1, worksheet.max_row):
                
                name_manuf      = str(worksheet.cell(row = i, column=1).value)
                alias           = worksheet.cell(row = i, column=2).value
                if alias == None:
                    alias = ''
                else:
                    alias = str(alias)
                new_manufacturen, created = RefManufacturer.objects.get_or_create(name=name_manuf)
                new_manufacturen.alias  = alias
                new_manufacturen.save() 


        finally:
            os.unlink(tmp_file)
        
        # Define variable to read the active sheet:
        #worksheet = wookbook.active
        # Iterate the loop to read the cell values
        #for i in range(0, worksheet.max_row):
        #    for col in worksheet.iter_cols(1, worksheet.max_column):
        #        print(col[i].value, end="\t\t")
        #    print('')
        text = 'post'
    else:
        text = 'Выберите файл и нажмите загрузить'
    params = {
        'type'  : 'avito',
        'text'  : text
    }

    '''
    fl = RefManufacturer.objects.all()
    for f in fl:
        f.save()
    '''

    return render(request, 'catalog/refresh_manufacturen.html', {'params': params})


def prices_lists(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        text = ''
        countListRecord = int(request.GET.get('select_count', '25'))
        
        filter_count = 0

        tasks    = TaskRegPrices.objects.all().order_by('-date')
        
        manufacturen            = request.GET.get('manufacturen', '')
        
        if len(manufacturen) > 0:
            tasks = tasks.filter(manufacturer__name__icontains = manufacturen)
            filter_count = filter_count + 1
            
        count   = tasks.count()
        
        page_number = request.GET.get('page', 1)
        
        paginator   = Paginator(tasks, countListRecord)
        page_obj    = paginator.get_page(page_number)
        
        filtr = {
            'manufacturen'  : manufacturen,
            'filtr_count'   : filter_count
        }

        params = {
            'type'          : 'prices',
            'page_number'   : page_number,
            'select_count'  : countListRecord,
            'manufacturer'  : RefManufacturer.objects.all().order_by('name') ,
            'paginator'     : page_obj,
            'filtr'         : filtr,
        }


        return render(request, 'prices/prices_lists.html', {'params': params})


def prices_list(request, id):
    
    text        = ''
    file_name   = ''
    file_path   = ''
    column_max      = 0
    positions_row   = 0
    list_info       = list()
    manufacturen    = ''

    type_price_one_manufacturer = True
    manufacturer                = RefManufacturer.objects.all().order_by('name')
    new                         = False

    if request.method == 'POST':
        if 'download' in request.POST:
            
            info_one_price  = request.POST.get('price_one_manufacturen', '')
            if info_one_price == 'false':
                info_one_price = False

            file_path       = request.POST.get('file_path_success', '')
            file_name       = request.POST.get('file_name_success', '')
            positions_row   = int(request.POST.get('positions_row_success', 0))
            manufacturen    = request.POST.get('manufacturen', '')
            start_row       = int(request.POST.get('start_row', '1'))
            email           = request.POST.get('email', '')
            article         = 0
            name            = 0
            category        = 0
            group           = 0
            price_min       = 0
            price           = 0
            manufacturen_col    = 0
            
            positions_row  = positions_row - start_row

            if len(manufacturen) > 0:
                manufacturen_object = RefManufacturer.objects.get(name = manufacturen)
            else:
                manufacturen_object = None

            for key in request.POST.keys():
                if key.startswith('col_'):
                    val_key = request.POST.get(key, 0)
                    if val_key != '-':
                        val_int = int(val_key)
                        if val_int == 1:
                            article = int(key.replace('col_', ''))
                        elif val_int == 2:
                            name = int(key.replace('col_', ''))
                        elif val_int == 3:
                            category = int(key.replace('col_', ''))
                        elif val_int == 4:
                            group = int(key.replace('col_', ''))
                        elif val_int == 5:
                            price_min = int(key.replace('col_', ''))
                        elif val_int == 6:
                            price = int(key.replace('col_', ''))
                        elif val_int == 7:
                            manufacturen_col = int(key.replace('col_', ''))
            
            settingsRegPrices                   = SettingsRegPrices()

            if manufacturen_object != None:
                settingsRegPrices.name              = "" + manufacturen_object.name
            else:
                settingsRegPrices.name              = "Мультипрайс список появится после загрузки"
            
            settingsRegPrices.manufacturer      = manufacturen_object
            settingsRegPrices.user              = request.user
            settingsRegPrices.start_row         = start_row
            settingsRegPrices.number_name       = name
            settingsRegPrices.number_article    = article
            settingsRegPrices.number_category   = category
            settingsRegPrices.number_group      = group
            settingsRegPrices.number_price_min  = price_min
            settingsRegPrices.number_price      = price
            settingsRegPrices.email_push        = email
            settingsRegPrices.number_manufacturer = manufacturen_col
            settingsRegPrices.save()

            taskRegPrices = TaskRegPrices()
            taskRegPrices.manufacturer  = manufacturen_object
            taskRegPrices.user          = request.user
            taskRegPrices.positions_all = positions_row 
            taskRegPrices.status        = "Ожидается загрузка"
            taskRegPrices.path_file_price   = file_path
            taskRegPrices.file_name         = file_name
            taskRegPrices.settings          = settingsRegPrices
            taskRegPrices.save()

            return HttpResponseRedirect('/prices_lists/' +  str(taskRegPrices.pk) + '/')

        else:
            manufacturen = request.POST.get('manufacturen', '')

            if len(request.FILES):
                xmlfile     = request.FILES['file']
                
                try:
                    path = default_storage.save('tmp/' + xmlfile.name, ContentFile(xmlfile.read()))
                    tmp_file = os.path.join(settings.MEDIA_ROOT, path)
                    wb = load_workbook(tmp_file)
                    worksheet = wb.active
                    
                    positions_row   = worksheet.max_row
                    column_max      = worksheet.max_column
                    column_max      = min(30, worksheet.max_column)
                    
                    file_path       = tmp_file
                    file_name       = xmlfile.name

                    list_info       = list()
                    for i in range(1, 25):
                        list_row = list()
                        for s in range(1, column_max +1):
                            val = worksheet.cell(row = i, column = s).value
                            if val == None:
                                val = ''
                            list_row.append(val)
                        list_info.append(list_row)
                finally:
                    sd = 1

    else:
        text = 'Выберите файл и нажмите загрузить'
    
    if int(id) == 0:
        new     = True

    if new == False:
        
        search = request.GET.get('search', '')

        task = TaskRegPrices.objects.get(pk = id)
        file_download = task.path_file_price.replace(settings.MEDIA_ROOT, '/media/')
        
        prices      = RegPrices.objects.filter(task = task).order_by('date')
        if len(search) > 0:
            prices = prices.filter(article_search__icontains = search) | prices.filter(name__icontains = search)
        page_number = request.GET.get('page', 1)
        
        paginator   = Paginator(prices, 25)
        page_obj    = paginator.get_page(page_number)
        
        params = {
            'file_download'     : file_download,
            'type'              : 'prices',
            'new'               : new,
            'task'              : task,
            'paginator'         : page_obj,
            'search'            : search
        }

        return render(request, 'prices/prices_list.html', {'params': params})   

    params = {
        'type'          : 'prices',
        'new'           : new,
        'manufacturen'  : manufacturen,
        'manufacturer'  : manufacturer,
        'text'          : text,
        'type_price_one_manufacturer'   : type_price_one_manufacturer,
        'file_name'         : file_name,
        'file_path'         : file_path,
        'column_max'        : column_max,
        'positions_row'     : positions_row,
        'list_info'         : list_info
    }

    return render(request, 'prices/prices_list.html', {'params': params})


def catalog_products(request):
    
    search          = request.GET.get('search', '')
    manufacturen    = request.GET.get('manufacturen', '')
    
    prices      = RegPrices.objects.all().order_by('-date')
    search_field = re.sub("[^A-Za-z А-Яа-я 0-9]", "", search).rstrip()

    if len(search_field) > 0:
        prices = prices.filter(article_search__icontains = search_field) | prices.filter(name__icontains = search_field)
    
    if len(manufacturen) > 0:
        prices = prices.filter(manufacturer__name__icontains = manufacturen)
    
    if 'save' in request.GET:
        file_name = 'products_' + f'{DT.datetime.now():%Y-%m-%d %H:%M:%S}' + '.xlsx'
        headers = {
            'file_name' : file_name
        }

        response = HttpResponse(content_type='application/ms-excel', headers = headers)
        response['Content-Disposition'] = 'attachment; filename="' + file_name + '"'
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Прайс лист"

        # Add headers
        headers = ["Производитель", "Артикул", "Наименование", "Категория", "Группа", "Цена дилера", "Цена", "Дата обновления"]
        ws.append(headers)

        # Add data from the model
        price = prices.values('date', 'manufacturer__name', 'article', 'name', 'category__name', 'group__name', 'price_min', 'price', 'date')
        for pric in price:
            ws.append([pric['manufacturer__name'], pric['article'], pric['name'], pric['category__name'], pric['group__name'], pric['price_min'], pric['price'], pric['date']])

        # Save the workbook to the HttpResponse
        wb.save(response)
        return response
    
    page_number = request.GET.get('page', 1)
    
    paginator   = Paginator(prices, 25)
    page_obj    = paginator.get_page(page_number)
    
    params = {
        'type'              : 'catalog_products',
        'paginator'         : page_obj,
        'manufacturer'      : RefManufacturer.objects.all().order_by('name') ,
        'search'            : search,
        'manufacturen'      : manufacturen
    }

    return render(request, 'catalog/products.html', {'params': params})   



###
##
# Работа с данными дял CVC
def cvc(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        if request.method == "POST":
            '''
            if 'id_record' in request.POST:
                url         = 'https://int-kors.audio-control.by/api/add-files' 
                record      = Records_voice_recorder.objects.get(pk = request.POST['id_record'])
                date        = record.date.strftime('%Y-%m-%d')
                date_start  = record.date.replace(hour=0, minute=0, second=0)
                date_end    = record.date.replace(hour=23, minute=59, second=59)
                
                fragments   = list()

                docs_rlk = DocRLK.objects.filter(staff__domain_login = str(record.user)).filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(Q(contacType__id= 7) | Q(contacType__id = 42))

                for doc_rlk in docs_rlk:
                    rlk_events = DocRLKEvents.objects.filter(rlk = doc_rlk).order_by('dataTime')[0]
                    
                    date_start_rlk = rlk_events.dataTime
                    hour_new    = int(date_start_rlk.strftime('%H'))
                    minute_new  = int(date_start_rlk.strftime('%M'))

                    if minute_new < 10:
                        minute_new  = minute_new + 60 - 10
                        hour_new    = hour_new - 1
                    else:
                        minute_new  = minute_new - 10

                    date_start_rlk = date_start_rlk.replace(hour=hour_new, minute=minute_new)

                    params_doc = {
                        "event_id"              : doc_rlk.id,
                        "manager"               : doc_rlk.staff.name,
                        "fragment_time_start"   : int(date_start_rlk.strftime('%Y%m%d%H%M%S')),
                        "fragment_time_end"     : int(doc_rlk.dataEnd.strftime('%Y%m%d%H%M%S'))
                    }
                    fragments.append(params_doc) 

                
                params = {
                    "master_key"        : "Ga8FQ0dgmALiA1bFr7k7tqIym84rnLM0",
                    "category"          : "recorder",
                    "date_call"         : record.date.strftime('%Y-%m-%dT%H:%M:%S%z'),
                    "json_fragments"    : str(fragments).replace("'", '"'),
                    
                }

                json_data = str(params).replace("'", '"')
                
                #headers = {'content-type': 'multipart/form-data'}
                with open(record.audio.path, 'rb') as f:
                    response = requests.post(url, data = params, files = {"files": (record.name, f)})


                params_answer = {
                    'code'  : response.status_code,
                    'text'  : response.text,
                    'params': params
                    
                }
                return render(request, 'test/test.html', {'params': params_answer}) 
        '''
        if request.method == "GET":
            directions = list()
            directions.append({'id': 1, 'name': 'Отдел продаж'})
        #directions.append({'id': 2, 'name': 'Сервис (прием авто)'})
        #directions.append({'id': 3, 'name': 'Сервис (выдача авто)'})
        #directions.append({'id': 4, 'name': 'Отдел оценки (Корс-авто)'})
        #directions.append({'id': 5, 'name': 'Отдел продаж (Корс-авто)'})
            
            direction_id 	= ''
            unit_id			= ''	

            citys 		= RefCity.objects.all().order_by("name")
            city_id 	= ""

            units       = RefUnit.objects.filter(buauto = False).order_by('name')

            date_start 	= ""
            date 		= ""
            date_end 	= ""
            
            if request.GET.get('date', ""):
                date 		= request.GET['date']
            
            if 'select_city' in request.GET:
                city_id = request.GET['select_city']
                if len(city_id) > 0:
                    units = units.filter(city__id = city_id)

            if 'select_direction' in request.GET:
                direction_id = request.GET['select_direction']
            
            if 'select_unit' in request.GET:
                unit_id = request.GET['select_unit']
            
            if len(date) == 0:
                date_period = DT.datetime.now()
                date_start 	= date_period.replace(day = 1, hour = 0, minute=0, second=0, microsecond=0)
                if date_period.month > 11:
                    month_end	= 1
                    year_end 	= date_period.year + 1
                else:
                    month_end	= date_period.month + 1
                    year_end 	= date_period.year
                date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0, microsecond=0)
            else:
                dates = date.split('-')
                if len(dates) == 2:
                    year 	        = int(dates[0])
                    month 	        = int(dates[1])
                    date_period     = DT.datetime.now()
                    date_start 	    = date_period.replace(year = year, month = month, day = 1, hour = 0, minute=0, second=0, microsecond=0)
                    if month > 11:
                        month_end 	= 1
                        year_end 	= year + 1
                    else:
                        month_end 	= month + 1 
                        year_end 	= year
                    date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0, microsecond=0)			
            records = list()
            
            if "send_record" in request.GET:
                id_record   = request.GET['send_record']
                send_record(id_record)
                url         = request.build_absolute_uri()
                url_new     = url.replace('&send_record=' + id_record, '')
                return HttpResponseRedirect(url_new)

            if len(unit_id) > 0:
                staffs = DocRLK.objects.filter(unit__id = unit_id).filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(Q(contacType__id= 7) | Q(contacType__id = 42)).values_list('staff__domain_login').distinct()
                records_query = Records_voice_recorder.objects.filter(date__gte = date_start).filter(date__lt = date_end).filter(user__username__in = staffs).order_by('date')
                for record_query in records_query:
                    records.append(get_record_info(record_query))

            filtr = {
                'date' 			: date_start,
                'city_id'		: city_id,
                'direction_id'	: direction_id,
                'unit_id'	    : unit_id,
            }

            selected = {
                'citys'			: citys,
                'directions' 	: directions,
                'units' 	    : units,
            }

            params = {
                    'filtr'			: filtr,
                    'selected'		: selected,
                    'records'       : records,
                    'url'           : request.build_absolute_uri()
            }
        return render(request, 'test/test.html', {'params': params}) 

def send_record(send_record):
    record_query    = Records_voice_recorder.objects.get(pk = send_record)
    info            = get_record_info(record_query)
    url             = 'https://int-kors.audio-control.by/api/add-files' 
    params = {
        "master_key"        : "Ga8FQ0dgmALiA1bFr7k7tqIym84rnLM0",
        "category"          : "recorder",
        "date_call"         : record_query.date.strftime('%Y-%m-%dT%H:%M:%S%z'),
        "json_fragments"    : str(info['fragments']).replace("'", '"'),
        
    }
    
    with open(record_query.audio.path, 'rb') as f:
        response = requests.post(url, data = params, files = {"files": (record_query.name, f)})

    records = Records_voice_recorder_cvc.objects.filter(records = record_query)
    if len(records) > 0:
        record = records[0]
    else:
        record = Records_voice_recorder_cvc()
    record.date         = DT.datetime.now()
    record.comment      = str(response.status_code)
    record.data_json    = str(response.text)
    record.records      = record_query
    record.save()

def get_record_info(record_query):
    date_record_start   = record_query.date.replace(hour=1)
    date_record_end     = record_query.date.replace(hour=23) 
    user_record         = record_query.user
    id                  = record_query.id
    record              = record_query
    send                = get_send_info(record_query)
    
    date_event_start    = record_query.date
    date_event_end      = date_event_start + DT.timedelta(seconds = record_query.time) 

    docs_rlk            = DocRLK.objects.filter(staff__domain_login = str(user_record)).filter(dataTime__gte = date_record_start).filter(dataTime__lte = date_record_end).filter(Q(contacType__id= 7) | Q(contacType__id = 42))  

    fragments   = list() 
    for doc_rlk in docs_rlk:
        rlk_events = DocRLKEvents.objects.filter(rlk = doc_rlk).order_by('dataTime')[0]
        
        if rlk_events.dataTime > date_event_start and doc_rlk.dataEnd < date_event_end:
            date_start_rlk  = rlk_events.dataTime
            hour_new        = int(date_start_rlk.strftime('%H'))
            minute_new      = int(date_start_rlk.strftime('%M'))

            if minute_new < 10:
                minute_new  = minute_new + 60 - 10
                hour_new    = hour_new - 1
            else:
                minute_new  = minute_new - 10

            date_start_rlk = date_start_rlk.replace(hour=hour_new, minute=minute_new)

            params_doc = {
                "event_id"              : doc_rlk.id,
                "manager"               : doc_rlk.staff.name,
                "fragment_time_start"   : int(date_start_rlk.strftime('%Y%m%d%H%M%S')),
                "fragment_time_end"     : int(doc_rlk.dataEnd.strftime('%Y%m%d%H%M%S'))
            }
            if doc_rlk.dataEnd > date_start_rlk:
                fragments.append(params_doc) 
    
    info = {
        'id'            : id,
        'time'          : record.time_human,
        'date'          : record.date,
        'name'          : record.name,
        'user'          : user_record,
        'fragments'     : fragments,
        'send'          : send,
        'docs_count'    : len(fragments)
    }
    return info

def get_send_info(record):
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



### im
def stok_im(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        url         = request.build_absolute_uri()
       
        url_search  = ''
        if url.find('?') > -1:
            url_search = "?" + url.split('?')[1]
        answer      = requests.get(server_im + 'stok/' + url_search, timeout = time_out_im)
        json_text   = json.loads(answer.text)
        
        filtr = request.GET
        
        params = {
            'type'          : 'stok_im',
            'filtr'         : filtr,
            'filtr_count'   : len(filtr),
            'answer'        : json_text
        }
        return render(request, 'im/stok.html', {'params':params})

def product(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/')
    else:
        
        url         = request.build_absolute_uri()
       
        url_search  = ''
        if url.find('?') > -1:
            url_search = "?" + url.split('?')[1]
        
        if request.method == "POST":
            file_objects = request.FILES.getlist('files')
            for file_object in file_objects: 
                response = requests.post(server_im + 'product/' + url_search,
                                            params={'file_name': file_object.name}, 
                                        files = {"files": (file_object.name, file_object)}, verify=False)
                if response.status_code == 200:
                    return HttpResponseRedirect(request.build_absolute_uri())

        answer      = requests.get(server_im + 'product/' + url_search, timeout = time_out_im)
        json_text   = json.loads(answer.text)
        
        filtr = request.GET
        '''
        if len(json_text['МассивФото']) == 0:
            json_text['МассивФото'] = list()
        else:
            json_text['МассивФото'] = json_text['МассивФото'].split(';')
            del json_text['МассивФото'][len(json_text['МассивФото'])-1]
        '''
        params = {
            'type'          : 'stok_im',
            'filtr'         : filtr,
            'filtr_count'   : len(filtr),
            'answer'        : json_text
        }
        return render(request, 'im/product.html', {'params': params})


###
##
#
def cvc_send(request):
    
    date_start = DT.datetime.now()

    #cvc_background()
  
    date_end = DT.datetime.now()
    
    to = {
        'date_start'    : date_start.strftime("%d/%m/%Y %H:%M:%S"),
        'date_end'      : date_end.strftime("%d/%m/%Y %H:%M:%S")
    }    
    
    return JsonResponse(to, status=status.HTTP_200_OK, safe=False)


import tqdm
class ProgressBar(tqdm.tqdm):
    def update_to(self, n: int) -> None:
        t=1


def rlks_trade_in(request):
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    filtr_unit_name     = request.GET.get('unit_name', '') 
    new_filtr           = request.GET.get('new_filtr', '')
    path_start          = request.path
    delite_filter       = request.GET.get('delite_filter', '')
    
    if len(delite_filter) > 0:
        if RefCustomerFiltr.objects.filter(pk = delite_filter).count() > 0:
            RefCustomerFiltr.objects.get(pk = delite_filter).delete()

    filters_user    = RefCustomerFiltr.objects.filter(user = request.user).filter(page = path_start).order_by('-date')  
    custom          = request.GET.get('custom', '') 
    if len(new_filtr) > 0:
        dict_filtr = request.GET.copy()
        dict_filtr.pop('new_filtr')
        dict_filtr.pop('save_filtr')
        path_filtr = get_path_in_dict(dict_filtr)

        path_redirect = path_start + path_filtr 
        new_filtr_object = RefCustomerFiltr()
        new_filtr_object.page = path_start
        new_filtr_object.path = path_filtr
        new_filtr_object.user = request.user
        new_filtr_object.name = new_filtr 
        new_filtr_object.save()

        return HttpResponseRedirect(path_redirect + '&custom='+ str(new_filtr_object.pk))
    
    date            = request.GET.get('date_start', '')

    if len(date) == 0:
    
        date_period = DT.datetime.now()
        date_start 	= date_period.replace(day = 1, hour = 0, minute=0, second=0, microsecond=0)
        if date_period.month > 11:
            month_end	= 1
            year_end 	= date_period.year + 1
        else:
            month_end	= date_period.month + 1
            year_end 	= date_period.year
        date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0, microsecond=0)
    
    else:
    
        dates = date.split('-')
        if len(dates) == 3:
            year 	        = int(dates[0])
            month 	        = int(dates[1])
            day             = int(dates[2])
            date_period     = DT.datetime.now()
            date_start 	    = date_period.replace(year = year, month = month, day = day, hour = 0, minute=0, second=0, microsecond=0)
            if month > 11:
                month_end 	= 1
                year_end 	= year + 1
            else:
                month_end 	= month + 1 
                year_end 	= year
            date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0, microsecond=0)			
    
    countList = 15

    staffKKID   = ""
    staffsKK    = Profiles.objects.filter(view_checklist = False).order_by('user__last_name')
            
    unit_id      = ""
    units_select = RefUnit.objects.filter(buauto = True).exclude(name = '').order_by("name")
    
    type_receptions_id = request.GET.get('type_receptions_id', '')

    staffID         = ""
    staffsSelect    = ""
    
    #docs        = DocRLK.objects.filter(dataTime__gte = date_start).filter(type__id = 7).filter(eco = True).filter(staff__domain_login = request.user.username ).order_by('-dataTime')
    docs        = DocRLK.objects.filter(dataTime__gte = date_start).filter(type__id = 2).filter(unit_dc__buauto = True) | DocRLK.objects.filter(dataTime__gte = date_start).filter(type__id = 7).filter(eco = True).order_by('-dataTime') | DocRLK.objects.filter(dataTime__gte = date_start).filter(type__id = 1).filter(eco = True).order_by('-dataTime') | DocRLK.objects.filter(dataTime__gte = date_start).filter(type__id = 19).filter(eco = True).order_by('-dataTime') | DocRLK.objects.filter(dataTime__gte = date_start).filter(eco = True).order_by('-dataTime') 
    subquery    = RegInteractivOcenka.objects.filter(rlk__id = OuterRef(name='id'))
    docs        = docs.annotate(
        unit_name               = Subquery(subquery.values('page_documents__unit__name')[:1])).annotate(
        status_estimation       = Subquery(subquery.values('status__name')[:1])).annotate(
        status_estimation_id    = Subquery(subquery.values('status__id')[:1])).annotate(
        start_estimation    = Subquery(subquery.values('start_estimation')[:1])).annotate(
        end_estimation      = Subquery(subquery.values('end_estimation')[:1])).annotate(
        staff_estimation    = Subquery(subquery.values('staff')[:1])).annotate(
        remote_price        = Subquery(subquery.values('page_remote__price_sale')[:1])).annotate(
        mark                = Subquery(subquery.values('modification__model__mark__name')[:1])).annotate(
        model = Subquery(subquery.values('modification__model__name')[:1])).annotate(
        modification = Subquery(subquery.values('modification__name')[:1])).annotate(
        type_estimation_ocenka = Subquery(subquery.values('page_documents__type_reception__name')[:1])).annotate(
        type_estimation_ocenka_id = Subquery(subquery.values('page_documents__type_reception__id')[:1])).annotate(
        year = Subquery(subquery.values('year')[:1])).annotate(
        vin = Subquery(subquery.values('vin')[:1])).annotate(
        lo_pk = Subquery(subquery.values('id')[:1]))

    filtr_number_doc    = request.GET.get('number_doc', '')
    filtr_vin           = request.GET.get('vin', '')
    if filtr_number_doc != '':
        docs = docs.filter(nomer__icontains = filtr_number_doc)    
    if type_receptions_id != '':
        type_receptions_id = int(type_receptions_id)
        docs = docs.filter(type_estimation_ocenka_id = type_receptions_id)    
    
    if filtr_vin != '':
        docs = docs.filter(vin__icontains = filtr_vin)  
    
    if filtr_unit_name != '':
        docs = docs.filter(unit__name__icontains = filtr_unit_name) | docs.filter(unit_dc__name__icontains = filtr_unit_name)
    
    status_id = request.GET.get('status_id', '')
    if status_id != '':
        status_id = int(status_id)
        docs = docs.filter(status_estimation_id = status_id)

    if request.GET.get('unit_id', ""):
        unit_id         = request.GET['unit_id']
        unit_id         = int(unit_id)
        docs = docs.filter(unit__id = unit_id) | docs.filter(unit_dc__id = unit_id)
        staffsSelect = list(RefStaff.objects.filter(units__in = [RefUnit.objects.get(id = unit_id)]).order_by('name'))
    else:
        if 'unit_id' in request.COOKIES:
            unit_id = request.COOKIES.get('unit_id')
            if len(unit_id) > 0:
                unit_id = int(unit_id)
                docs = docs.filter(rlk__unit = RefUnit.objects.get(id = unit_id))
                staffsSelect = list(RefStaff.objects.filter(unit = RefUnit.objects.get(id = unit_id)).order_by('name'))

    paginator   = Paginator(docs, countList)	
    page_number = request.GET.get('page', 1)
    page_obj    = paginator.get_page(page_number)

    filtr = {
        'unit_id'           : unit_id,
        'staffID'           : staffID,
        'staffKKID'         : staffKKID,
        'number_doc'        : filtr_number_doc,
        'date_start'        : date_start,
        'type_receptions_id': type_receptions_id, 
        'date_end'          : date_end,
        'status_id'         : status_id,
        'unit_name'         : filtr_unit_name,
        'vin'               : filtr_vin
    }

    selected = {
        'units'             : units_select,
        'staffs'            : staffsSelect,
        'staffsKK'          : '',
        'statuses'          : list(RefStatusEstimation.objects.all().order_by('-pk')),
        'type_receptions'   : RefTypeReceptionCarsOrganization.objects.exclude(name = '').order_by('name')
    }

    params = {
        'type'          : 'rlks_trade_in',
        'filtr'         : filtr,
        'filtr_count'   : len(filtr),
        'objects'       : page_obj,
        'filters_user'  : filters_user,
        'selected'      : selected
    }
    return render(request, 'website/rlks_trade_in.html', {'params':params}) 


def rlk_trade_in(request, id):
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    if request.method == 'POST':
        if 'task_edit' in request.POST:
            task_edit = request.POST.get('task_edit', 0)
            if task_edit != 0:
                
                task = RegInteractivOcenkaTask.objects.get(id = task_edit)
                task.comment_success = request.POST.get('comment_success', '')
                task.date_close = DT.datetime.now()
                task.staff_close = request.user
                task.save()

                images_task = request.FILES.getlist('images_task')
                for file_object in images_task: 
                    name = file_object.name.lower()
                    new_estimation_files, created       = RegRegInteractivOcenkaTaskFiles.objects.get_or_create(estimation_task = task, name = name)
                    new_estimation_files.name           = name
                    new_estimation_files.file           = file_object
                    new_estimation_files.save()
            chat    = Chat.objects.get_or_create(name = id, slug = 'rlk_' + str(id))[0]    
            send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= request.user, text='Закрыта задача ' + str(task.comment_task) + " - " + str(task.comment_success))
            
            return HttpResponseRedirect(request.build_absolute_uri())   

    
    docs        = DocRLK.objects.filter(pk = id).filter(eco = True).order_by('-dataTime')
    subquery    = RegInteractivOcenka.objects.filter(rlk__id = OuterRef(name='id'))
    docs        = docs.annotate(
        status_estimation    = Subquery(subquery.values('status__name')[:1])).annotate(
        status_estimation_id  = Subquery(subquery.values('status__id')[:1])).annotate(
        start_estimation    = Subquery(subquery.values('start_estimation')[:1])).annotate(
        remote_price        = Subquery(subquery.values('page_remote__price_sale')[:1])).annotate(
        end_estimation      = Subquery(subquery.values('end_estimation')[:1])).annotate(
        staff_estimation    = Subquery(subquery.values('staff')[:1])).annotate(
        mark                = Subquery(subquery.values('modification__model__mark__name')[:1])).annotate(
        model = Subquery(subquery.values('modification__model__name')[:1])).annotate(
        modification = Subquery(subquery.values('modification__name')[:1])).annotate(
        type_estimation_ocenka = Subquery(subquery.values('page_documents__type_reception__name')[:1])).annotate(
        type_estimation_ocenka_id = Subquery(subquery.values('page_documents__type_reception__id')[:1])).annotate(
        year = Subquery(subquery.values('year')[:1])).annotate(
        vin = Subquery(subquery.values('vin')[:1])).annotate(
        number_body = Subquery(subquery.values('number_body')[:1])).annotate(
        lo_pk = Subquery(subquery.values('id')[:1])).annotate(
        estimation_price_staff = Subquery(subquery.values('page_soglasovanie__price_reception')[:1])).annotate(
        estimation_price_staff_sale = Subquery(subquery.values('page_soglasovanie__price_sale')[:1])).annotate(
        estimation_price_before_kd = Subquery(subquery.values('page_soglasovanie__price_before_kd')[:1])).annotate(
        estimation_price_after_kd = Subquery(subquery.values('page_soglasovanie__price_after_kd')[:1]))
    
    subquery_signal = Autoteka_signal.objects.filter(vin = OuterRef(name='vin')).order_by('date')
        
    docs = docs.annotate(
        signal_seller       = Subquery(subquery_signal.values('seller')[:1])).annotate(
        signal_brand        = Subquery(subquery_signal.values('brand')[:1])).annotate(
        signal_model        = Subquery(subquery_signal.values('model')[:1])).annotate(
        signal_year         = Subquery(subquery_signal.values('year')[:1])).annotate(
        signal_mileage      = Subquery(subquery_signal.values('mileage')[:1])).annotate(
        signal_url          = Subquery(subquery_signal.values('url')[:1])).annotate(
        signal_price        = Subquery(subquery_signal.values('price')[:1])).annotate(
        signal_description  = Subquery(subquery_signal.values('description')[:1])).annotate(
        signal_city_name  = Subquery(subquery_signal.values('city_name')[:1])).annotate(
        signal_region_name  = Subquery(subquery_signal.values('region_name__name')[:1]))
        

    estimation  = None
    chat        = None
    page_obj = ''

    if len(docs) > 0:
        page_obj = docs[0]
        if page_obj.lo_pk != None:
            estimation  = RegInteractivOcenka.objects.get(pk=  page_obj.lo_pk)
            chat        = Chat.objects.get_or_create(name = page_obj.pk, slug = 'rlk_' + str(page_obj.pk))[0]

    selected = {
        'staffsKK'          : '',
        'type_receptions'   : RefTypeReceptionCarsOrganization.objects.exclude(name = '').order_by('name')
    }
    params = {
        
        'type'          : 'rlks_trade_in',
        'object'        : page_obj,
        'user'          : request.user,
        'estimation'    : estimation,
        'selected'      : selected,
        'chat'          : chat


    }
    return render(request, 'website/doc_rlk_tradein.html', {'params':params}) 


def docs_car_agreement(request):
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    filtr_count = 0
    subqyery                = RefCarsOrganization.objects.filter(lo__id = OuterRef(name='lo__id'))
    
    docs        = DocCarAgreement.objects.all().order_by('-dataTime')
    docs        = docs.annotate(
        lo_date                     = Subquery(subqyery.values('lo_link_date')[:1])).annotate(
        lo_number                   = Subquery(subqyery.values('lo_link_number')[:1])).annotate(
        lo_type_reception           = Subquery(subqyery.values('type_reception__name')[:1])).annotate(
        lo_status                   = Subquery(subqyery.values('status__name')[:1])).annotate(
        lo_vin                      = Subquery(subqyery.values('vin')[:1])).annotate(
        lo_vin2                     = Subquery(subqyery.values('vin2')[:1])).annotate(
        lo_days_in_stok             = Subquery(subqyery.values('days_in_stok')[:1])).annotate(
        lo_type_sale                = Subquery(subqyery.values('type_sale__name')[:1])).annotate(
        lo_description_podgotovka   = Subquery(subqyery.values('description_podgotovka')[:1])).annotate(
        lo_description_op           = Subquery(subqyery.values('description_op')[:1])).annotate(
        lo_evaluation               = Subquery(subqyery.values('evaluation__name')[:1])).annotate(
        lo_group_price              = Subquery(subqyery.values('group_price__name')[:1])).annotate(
        lo_stageprice               = Subquery(subqyery.values('stage_price__name')[:1])).annotate(
        lo_rating                   = Subquery(subqyery.values('rating__name')[:1])).annotate(
        lo_mark                     = Subquery(subqyery.values('modification_autoru__model__mark__name')[:1])).annotate(
        lo_model                    = Subquery(subqyery.values('modification_autoru__model__name')[:1])).annotate(     
        lo_modification             = Subquery(subqyery.values('modification_autoru__name')[:1])).annotate(    
        lo_year                     = Subquery(subqyery.values('year')[:1])).annotate(     
        lo_quantity                 = Subquery(subqyery.values('quantity')[:1])).annotate(   
        lo_run                      = Subquery(subqyery.values('run')[:1])).annotate(     
        lo_year                     = Subquery(subqyery.values('year')[:1])).annotate(
        lo_color                    = Subquery(subqyery.values('color')[:1])).annotate(     
        lo_days_next_stage          = Subquery(subqyery.values('days_next_stage')[:1])).annotate(     
        lo_task                     = Subquery(subqyery.values('task')[:1])).annotate(                 
        lo_store                    = Subquery(subqyery.values('store__name')[:1])).annotate(
        lo_unit                     = Subquery(subqyery.values('unit__name')[:1])).annotate(
        lo_is_new                   = Subquery(subqyery.values('is_new')[:1])).annotate(
        lo_plate_number             = Subquery(subqyery.values('plate_number')[:1])).annotate(
        lo_slug                     = Subquery(subqyery.values('slug')[:1]))
        
    subqyery_estimations    = RegInteractivOcenka.objects.filter(rlk__id = OuterRef(name='lo__rlk'))   
    
    docs = docs.annotate(
        estimation                     = Subquery(subqyery_estimations.values('pk')[:1]))
    
    name = request.GET.get('name', '')
    if name != '':
        docs = docs.filter(lo_vin__icontains = name) | docs.filter(lo_mark__icontains = name) | docs.filter(lo_model__icontains = name) | docs.filter(client__full_name__icontains = name) 
        filtr_count = filtr_count + 1
    page_number = request.GET.get('page')
        
    paginator   = Paginator(docs, 15)
    page_obj    = paginator.get_page(page_number)
    
    filtr = {
        'name'          : name,
        'filtr_count'   : filtr_count
    }
    params = {
        'type'              : 'doc_car_agreement',
        'user'              : request.user,
        'filtr'             : filtr,
        'paginator'         : page_obj,
    }
    return render(request, 'website/docs_car_agreement.html', {'params': params}) 


def doc_car_agreement(request, id):
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    subqyery            = RefCarsOrganization.objects.filter(lo__id = OuterRef(name='lo__id'))
    subqyery_shipment   = DocCarShipment.objects.filter(agreement__id = OuterRef(name='id'))
    
    doc        = DocCarAgreement.objects.filter(pk = id)
    doc        = doc.annotate(
        sp_id                       = Subquery(subqyery_shipment.values('id')[:1])).annotate(
        lo_date                     = Subquery(subqyery.values('lo_link_date')[:1])).annotate(
        lo_number                   = Subquery(subqyery.values('lo_link_number')[:1])).annotate(
        lo_type_reception           = Subquery(subqyery.values('type_reception__name')[:1])).annotate(
        lo_status                   = Subquery(subqyery.values('status__name')[:1])).annotate(
        lo_vin                      = Subquery(subqyery.values('vin')[:1])).annotate(
        lo_vin2                     = Subquery(subqyery.values('vin2')[:1])).annotate(
        lo_days_in_stok             = Subquery(subqyery.values('days_in_stok')[:1])).annotate(
        lo_type_sale                = Subquery(subqyery.values('type_sale__name')[:1])).annotate(
        lo_description_podgotovka   = Subquery(subqyery.values('description_podgotovka')[:1])).annotate(
        lo_description_op           = Subquery(subqyery.values('description_op')[:1])).annotate(
        lo_evaluation               = Subquery(subqyery.values('evaluation__name')[:1])).annotate(
        lo_group_price              = Subquery(subqyery.values('group_price__name')[:1])).annotate(
        lo_stageprice               = Subquery(subqyery.values('stage_price__name')[:1])).annotate(
        lo_rating                   = Subquery(subqyery.values('rating__name')[:1])).annotate(
        lo_mark                     = Subquery(subqyery.values('modification_autoru__model__mark__name')[:1])).annotate(
        lo_model                    = Subquery(subqyery.values('modification_autoru__model__name')[:1])).annotate(     
        lo_modification             = Subquery(subqyery.values('modification_autoru__name')[:1])).annotate(    
        lo_year                     = Subquery(subqyery.values('year')[:1])).annotate(     
        lo_quantity                 = Subquery(subqyery.values('quantity')[:1])).annotate(   
        lo_run                      = Subquery(subqyery.values('run')[:1])).annotate(     
        lo_year                     = Subquery(subqyery.values('year')[:1])).annotate(
        lo_color                    = Subquery(subqyery.values('color')[:1])).annotate(     
        lo_days_next_stage          = Subquery(subqyery.values('days_next_stage')[:1])).annotate(     
        lo_task                     = Subquery(subqyery.values('task')[:1])).annotate(                 
        lo_store                    = Subquery(subqyery.values('store__name')[:1])).annotate(
        lo_unit                     = Subquery(subqyery.values('unit__name')[:1])).annotate(
        lo_is_new                   = Subquery(subqyery.values('is_new')[:1])).annotate(
        lo_plate_number             = Subquery(subqyery.values('plate_number')[:1])).annotate(
        lo_slug                     = Subquery(subqyery.values('slug')[:1]))
        
    subqyery_estimations    = RegInteractivOcenka.objects.filter(rlk__id = OuterRef(name='lo__rlk'))   
    
    doc = doc.annotate(
        estimation                     = Subquery(subqyery_estimations.values('pk')[:1]))
    

    doc = doc[0]   
    params = {
        
        'type'          : 'doc_car_agreement',
        'user'          : request.user,
        'object'        : doc,
    }
    return render(request, 'website/doc_car_agreement.html', {'params': params}) 


def docs_car_shipment(request):
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    filtr_count = 0
    subqyery                = RefCarsOrganization.objects.filter(lo__id = OuterRef(name='lo__id'))
    
    docs        = DocCarShipment.objects.all().order_by('-dataTime')
    docs        = docs.annotate(
        lo_date                     = Subquery(subqyery.values('lo_link_date')[:1])).annotate(
        lo_number                   = Subquery(subqyery.values('lo_link_number')[:1])).annotate(
        lo_type_reception           = Subquery(subqyery.values('type_reception__name')[:1])).annotate(
        lo_status                   = Subquery(subqyery.values('status__name')[:1])).annotate(
        lo_vin                      = Subquery(subqyery.values('vin')[:1])).annotate(
        lo_vin2                     = Subquery(subqyery.values('vin2')[:1])).annotate(
        lo_days_in_stok             = Subquery(subqyery.values('days_in_stok')[:1])).annotate(
        lo_type_sale                = Subquery(subqyery.values('type_sale__name')[:1])).annotate(
        lo_description_podgotovka   = Subquery(subqyery.values('description_podgotovka')[:1])).annotate(
        lo_description_op           = Subquery(subqyery.values('description_op')[:1])).annotate(
        lo_evaluation               = Subquery(subqyery.values('evaluation__name')[:1])).annotate(
        lo_group_price              = Subquery(subqyery.values('group_price__name')[:1])).annotate(
        lo_stageprice               = Subquery(subqyery.values('stage_price__name')[:1])).annotate(
        lo_rating                   = Subquery(subqyery.values('rating__name')[:1])).annotate(
        lo_mark                     = Subquery(subqyery.values('modification_autoru__model__mark__name')[:1])).annotate(
        lo_model                    = Subquery(subqyery.values('modification_autoru__model__name')[:1])).annotate(     
        lo_modification             = Subquery(subqyery.values('modification_autoru__name')[:1])).annotate(    
        lo_year                     = Subquery(subqyery.values('year')[:1])).annotate(     
        lo_quantity                 = Subquery(subqyery.values('quantity')[:1])).annotate(   
        lo_run                      = Subquery(subqyery.values('run')[:1])).annotate(     
        lo_year                     = Subquery(subqyery.values('year')[:1])).annotate(
        lo_color                    = Subquery(subqyery.values('color')[:1])).annotate(     
        lo_days_next_stage          = Subquery(subqyery.values('days_next_stage')[:1])).annotate(     
        lo_task                     = Subquery(subqyery.values('task')[:1])).annotate(                 
        lo_store                    = Subquery(subqyery.values('store__name')[:1])).annotate(
        lo_unit                     = Subquery(subqyery.values('unit__name')[:1])).annotate(
        lo_is_new                   = Subquery(subqyery.values('is_new')[:1])).annotate(
        lo_plate_number             = Subquery(subqyery.values('plate_number')[:1])).annotate(
        lo_slug                     = Subquery(subqyery.values('slug')[:1]))
        
    subqyery_estimations    = RegInteractivOcenka.objects.filter(rlk__id = OuterRef(name='lo__rlk'))   
    
    docs = docs.annotate(
        estimation                     = Subquery(subqyery_estimations.values('pk')[:1]))
    
    name = request.GET.get('name', '')
    if name != '':
        docs = docs.filter(lo_vin__icontains = name) | docs.filter(lo_mark__icontains = name) | docs.filter(lo_model__icontains = name) | docs.filter(client__full_name__icontains = name) 
        filtr_count = filtr_count + 1
    page_number = request.GET.get('page')
        
    paginator   = Paginator(docs, 15)
    page_obj    = paginator.get_page(page_number)
    
    filtr = {
        'name'          : name,
        'filtr_count'   : filtr_count
    }
    params = {
        'type'              : 'doc_car_shipment',
        'user'              : request.user,
        'filtr'             : filtr,
        'paginator'         : page_obj,
    }
    return render(request, 'website/docs_car_shipment.html', {'params': params}) 


def doc_car_shipment(request, id):
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    subqyery                = RefCarsOrganization.objects.filter(lo__id = OuterRef(name='lo__id'))
    shipment                = DocCarShipment.objects.get(pk = id)
    agreement               = shipment.agreement

    doc        = DocCarAgreement.objects.filter(pk = agreement.id)
    doc        = doc.annotate(
        lo_date                     = Subquery(subqyery.values('lo_link_date')[:1])).annotate(
        lo_number                   = Subquery(subqyery.values('lo_link_number')[:1])).annotate(
        lo_type_reception           = Subquery(subqyery.values('type_reception__name')[:1])).annotate(
        lo_status                   = Subquery(subqyery.values('status__name')[:1])).annotate(
        lo_vin                      = Subquery(subqyery.values('vin')[:1])).annotate(
        lo_vin2                     = Subquery(subqyery.values('vin2')[:1])).annotate(
        lo_days_in_stok             = Subquery(subqyery.values('days_in_stok')[:1])).annotate(
        lo_type_sale                = Subquery(subqyery.values('type_sale__name')[:1])).annotate(
        lo_description_podgotovka   = Subquery(subqyery.values('description_podgotovka')[:1])).annotate(
        lo_description_op           = Subquery(subqyery.values('description_op')[:1])).annotate(
        lo_evaluation               = Subquery(subqyery.values('evaluation__name')[:1])).annotate(
        lo_group_price              = Subquery(subqyery.values('group_price__name')[:1])).annotate(
        lo_stageprice               = Subquery(subqyery.values('stage_price__name')[:1])).annotate(
        lo_rating                   = Subquery(subqyery.values('rating__name')[:1])).annotate(
        lo_mark                     = Subquery(subqyery.values('modification_autoru__model__mark__name')[:1])).annotate(
        lo_model                    = Subquery(subqyery.values('modification_autoru__model__name')[:1])).annotate(     
        lo_modification             = Subquery(subqyery.values('modification_autoru__name')[:1])).annotate(    
        lo_year                     = Subquery(subqyery.values('year')[:1])).annotate(     
        lo_quantity                 = Subquery(subqyery.values('quantity')[:1])).annotate(   
        lo_run                      = Subquery(subqyery.values('run')[:1])).annotate(     
        lo_year                     = Subquery(subqyery.values('year')[:1])).annotate(
        lo_color                    = Subquery(subqyery.values('color')[:1])).annotate(     
        lo_days_next_stage          = Subquery(subqyery.values('days_next_stage')[:1])).annotate(     
        lo_task                     = Subquery(subqyery.values('task')[:1])).annotate(                 
        lo_store                    = Subquery(subqyery.values('store__name')[:1])).annotate(
        lo_unit                     = Subquery(subqyery.values('unit__name')[:1])).annotate(
        lo_is_new                   = Subquery(subqyery.values('is_new')[:1])).annotate(
        lo_plate_number             = Subquery(subqyery.values('plate_number')[:1])).annotate(
        lo_slug                     = Subquery(subqyery.values('slug')[:1]))
        
    subqyery_estimations    = RegInteractivOcenka.objects.filter(rlk__id = OuterRef(name='lo__rlk'))   
    
    doc = doc.annotate(
        estimation                     = Subquery(subqyery_estimations.values('pk')[:1]))
    

    doc = doc[0]   
    params = {
        
        'type'          : 'doc_car_shipment',
        'user'          : request.user,
        'object'        : doc,
        'shipment'      : shipment
    }
    return render(request, 'website/doc_car_shipment.html', {'params':params}) 


def korsavto_settings_dc(request):
    
    if request.method == 'POST':
        if 'save_settings_estimation' in request.POST:
            estimation_settings = RegEstimationsSettings.objects.get(pk = 1)
            
            estimation_settings.all_percent_financity   = float(request.POST.get('all_percent_financity', 0))
            estimation_settings.all_days_stok_financity = float(request.POST.get('all_days_stok_financity', 0))
            
            estimation_settings.percent_financity_200   = float(request.POST.get('percent_financity_200', 0))
            estimation_settings.days_stok_financity_200 = float(request.POST.get('days_stok_financity_200', 0))

            estimation_settings.percent_financity_400   = float(request.POST.get('percent_financity_400', 0))
            estimation_settings.days_stok_financity_400 = float(request.POST.get('days_stok_financity_400', 0))

            estimation_settings.percent_financity_700   = float(request.POST.get('percent_financity_700', 0))
            estimation_settings.days_stok_financity_700 = float(request.POST.get('days_stok_financity_700', 0))

            estimation_settings.percent_financity_1200   = float(request.POST.get('percent_financity_1200', 0))
            estimation_settings.days_stok_financity_1200 = float(request.POST.get('days_stok_financity_1200', 0))

            estimation_settings.percent_financity_2000   = float(request.POST.get('percent_financity_2000', 0))
            estimation_settings.days_stok_financity_2000 = float(request.POST.get('days_stok_financity_2000', 0))

            estimation_settings.percent_financity_3000   = float(request.POST.get('percent_financity_3000', 0))
            estimation_settings.days_stok_financity_3000 = float(request.POST.get('days_stok_financity_3000', 0))

            estimation_settings.percent_financity_5000   = float(request.POST.get('percent_financity_5000', 0))
            estimation_settings.days_stok_financity_5000 = float(request.POST.get('days_stok_financity_5000', 0))

            estimation_settings.percent_financity_5001   = float(request.POST.get('percent_financity_5001', 0))
            estimation_settings.days_stok_financity_5001 = float(request.POST.get('days_stok_financity_5001', 0))

            estimation_settings.battery_200 = float(request.POST.get('battery_200', 0))
            estimation_settings.battery_400 = float(request.POST.get('battery_400', 0))
            estimation_settings.battery_700 = float(request.POST.get('battery_700', 0))
            estimation_settings.battery_1200 = float(request.POST.get('battery_1200', 0))
            estimation_settings.battery_2000 = float(request.POST.get('battery_2000', 0))
            estimation_settings.battery_3000 = float(request.POST.get('battery_3000', 0))
            estimation_settings.battery_5000 = float(request.POST.get('battery_5000', 0))
            estimation_settings.battery_5001 = float(request.POST.get('battery_5001', 0))

            estimation_settings.izp_200 = float(request.POST.get('izp_200', 0))
            estimation_settings.izp_200_v = int(request.POST.get('izp_200_v', 0))
            estimation_settings.auction_kf_200 = float(request.POST.get('auction_kf_200', 0))

            estimation_settings.izp_400 = float(request.POST.get('izp_400', 0))
            estimation_settings.izp_400_v = int(request.POST.get('izp_400_v', 0))
            estimation_settings.auction_kf_400 = float(request.POST.get('auction_kf_400', 0))

            estimation_settings.izp_700 = float(request.POST.get('izp_700', 0))
            estimation_settings.izp_700_v = int(request.POST.get('izp_700_v', 0))
            estimation_settings.auction_kf_700 = float(request.POST.get('auction_kf_700', 0))

            estimation_settings.izp_1200 = float(request.POST.get('izp_1200', 0))
            estimation_settings.izp_1200_v = int(request.POST.get('izp_1200_v', 0))
            estimation_settings.auction_kf_1200 = float(request.POST.get('auction_kf_1200', 0))

            estimation_settings.izp_2000 = float(request.POST.get('izp_2000', 0))
            estimation_settings.izp_2000_v = int(request.POST.get('izp_2000_v', 0))
            estimation_settings.auction_kf_2000 = float(request.POST.get('auction_kf_2000', 0))

            estimation_settings.izp_3000 = float(request.POST.get('izp_3000', 0))
            estimation_settings.izp_3000_v = int(request.POST.get('izp_3000_v', 0))
            estimation_settings.auction_kf_3000 = float(request.POST.get('auction_kf_3000', 0))

            estimation_settings.izp_5000 = float(request.POST.get('izp_5000', 0))
            estimation_settings.izp_5000_v = int(request.POST.get('izp_5000_v', 0))
            estimation_settings.auction_kf_5000 = float(request.POST.get('auction_kf_5000', 0))

            estimation_settings.izp_5001 = float(request.POST.get('izp_5001', 0))
            estimation_settings.izp_5001_v = int(request.POST.get('izp_5001_v', 0))
            estimation_settings.auction_kf_5001 = float(request.POST.get('auction_kf_5001', 0))

            estimation_settings.windshield_200      = int(request.POST.get('windshield_200', 0))
            estimation_settings.windshield_heat_200 = int(request.POST.get('windshield_heat_200', 0))

            estimation_settings.windshield_400      = int(request.POST.get('windshield_400', 0))
            estimation_settings.windshield_heat_400 = int(request.POST.get('windshield_heat_400', 0))

            estimation_settings.windshield_700      = int(request.POST.get('windshield_700', 0))
            estimation_settings.windshield_heat_700 = int(request.POST.get('windshield_heat_700', 0))

            estimation_settings.windshield_1200      = int(request.POST.get('windshield_1200', 0))
            estimation_settings.windshield_heat_1200 = int(request.POST.get('windshield_heat_1200', 0))

            estimation_settings.windshield_2000      = int(request.POST.get('windshield_2000', 0))
            estimation_settings.windshield_heat_2000 = int(request.POST.get('windshield_heat_2000', 0))

            estimation_settings.windshield_3000      = int(request.POST.get('windshield_3000', 0))
            estimation_settings.windshield_heat_3000 = int(request.POST.get('windshield_heat_3000', 0))

            estimation_settings.windshield_5000      = int(request.POST.get('windshield_5000', 0))
            estimation_settings.windshield_heat_5000 = int(request.POST.get('windshield_heat_5000', 0))

            estimation_settings.windshield_5001      = int(request.POST.get('windshield_5001', 0))
            estimation_settings.windshield_heat_5001 = int(request.POST.get('windshield_heat_5001', 0))

            estimation_settings.light_pered_200      = int(request.POST.get('light_pered_200', 0))
            estimation_settings.light_zad_200 = int(request.POST.get('light_zad_200', 0))

            estimation_settings.light_pered_400      = int(request.POST.get('light_pered_400', 0))
            estimation_settings.light_zad_400 = int(request.POST.get('light_zad_400', 0))

            estimation_settings.light_pered_700      = int(request.POST.get('light_pered_700', 0))
            estimation_settings.light_zad_700 = int(request.POST.get('light_zad_700', 0))

            estimation_settings.light_pered_1200      = int(request.POST.get('light_pered_1200', 0))
            estimation_settings.light_zad_1200 = int(request.POST.get('light_zad_1200', 0))

            estimation_settings.light_pered_2000      = int(request.POST.get('light_pered_2000', 0))
            estimation_settings.light_zad_2000 = int(request.POST.get('light_zad_2000', 0))

            estimation_settings.light_pered_3000      = int(request.POST.get('light_pered_3000', 0))
            estimation_settings.light_zad_3000 = int(request.POST.get('light_zad_3000', 0))

            estimation_settings.light_pered_5000      = int(request.POST.get('light_pered_5000', 0))
            estimation_settings.light_zad_5000 = int(request.POST.get('light_zad_5000', 0))

            estimation_settings.light_pered_5001      = int(request.POST.get('light_pered_5001', 0))
            estimation_settings.light_zad_5001 = int(request.POST.get('light_zad_5001', 0))

            estimation_settings.light_pered_kf_200      = int(request.POST.get('light_pered_kf_200', 0))
            estimation_settings.light_zad_kf_200 = int(request.POST.get('light_zad_kf_200', 0))

            estimation_settings.light_pered_kf_400      = int(request.POST.get('light_pered_kf_400', 0))
            estimation_settings.light_zad_kf_400 = int(request.POST.get('light_zad_kf_400', 0))

            estimation_settings.light_pered_kf_700      = int(request.POST.get('light_pered_kf_700', 0))
            estimation_settings.light_zad_kf_700 = int(request.POST.get('light_zad_kf_700', 0))

            estimation_settings.light_pered_kf_1200      = int(request.POST.get('light_pered_kf_1200', 0))
            estimation_settings.light_zad_kf_1200 = int(request.POST.get('light_zad_kf_1200', 0))

            estimation_settings.light_pered_kf_2000      = int(request.POST.get('light_pered_kf_2000', 0))
            estimation_settings.light_zad_kf_2000 = int(request.POST.get('light_zad_kf_2000', 0))

            estimation_settings.light_pered_kf_3000      = int(request.POST.get('light_pered_kf_3000', 0))
            estimation_settings.light_zad_kf_3000 = int(request.POST.get('light_zad_kf_3000', 0))
            
            estimation_settings.light_pered_kf_5000      = int(request.POST.get('light_pered_kf_5000', 0))
            estimation_settings.light_zad_kf_5000 = int(request.POST.get('light_zad_kf_5000', 0))
            
            estimation_settings.light_pered_kf_5001      = int(request.POST.get('light_pered_kf_5001', 0))
            estimation_settings.light_zad_kf_5001 = int(request.POST.get('light_zad_kf_5001', 0))

            estimation_settings.bumper_pered_200        = int(request.POST.get('bumper_pered_200', 0))
            estimation_settings.bumper_zad_200          = int(request.POST.get('bumper_zad_200', 0))
            estimation_settings.bumper_replace_pered_200        = int(request.POST.get('bumper_pered_200', 0))
            estimation_settings.bumper_replace_zad_200          = int(request.POST.get('bumper_zad_200', 0))


            estimation_settings.bumper_pered_400      = int(request.POST.get('bumper_pered_400', 0))
            estimation_settings.bumper_zad_400 = int(request.POST.get('bumper_zad_400', 0))
            estimation_settings.bumper_replace_pered_400        = int(request.POST.get('bumper_pered_400', 0))
            estimation_settings.bumper_replace_zad_400          = int(request.POST.get('bumper_zad_400', 0))


            estimation_settings.bumper_pered_700      = int(request.POST.get('bumper_pered_700', 0))
            estimation_settings.bumper_zad_700 = int(request.POST.get('bumper_zad_700', 0))
            estimation_settings.bumper_replace_pered_700        = int(request.POST.get('bumper_pered_700', 0))
            estimation_settings.bumper_replace_zad_700          = int(request.POST.get('bumper_zad_700', 0))

            estimation_settings.bumper_pered_1200      = int(request.POST.get('bumper_pered_1200', 0))
            estimation_settings.bumper_zad_1200 = int(request.POST.get('bumper_zad_1200', 0))
            estimation_settings.bumper_replace_pered_1200        = int(request.POST.get('bumper_pered_1200', 0))
            estimation_settings.bumper_replace_zad_1200          = int(request.POST.get('bumper_zad_1200', 0))

            estimation_settings.bumper_pered_2000      = int(request.POST.get('bumper_pered_2000', 0))
            estimation_settings.bumper_zad_2000 = int(request.POST.get('bumper_zad_2000', 0))
            estimation_settings.bumper_replace_pered_2000        = int(request.POST.get('bumper_pered_2000', 0))
            estimation_settings.bumper_replace_zad_2000          = int(request.POST.get('bumper_zad_2000', 0))
    
            estimation_settings.bumper_pered_3000      = int(request.POST.get('bumper_pered_3000', 0))
            estimation_settings.bumper_zad_3000 = int(request.POST.get('bumper_zad_3000', 0))
            estimation_settings.bumper_replace_pered_3000        = int(request.POST.get('bumper_pered_3000', 0))
            estimation_settings.bumper_replace_zad_3000          = int(request.POST.get('bumper_zad_3000', 0))

            estimation_settings.bumper_pered_5000      = int(request.POST.get('bumper_pered_5000', 0))
            estimation_settings.bumper_zad_5000 = int(request.POST.get('bumper_zad_5000', 0))
            estimation_settings.bumper_replace_pered_5000        = int(request.POST.get('bumper_pered_5000', 0))
            estimation_settings.bumper_replace_zad_5000          = int(request.POST.get('bumper_zad_5000', 0))

            estimation_settings.bumper_pered_5001      = int(request.POST.get('bumper_pered_5001', 0))
            estimation_settings.bumper_zad_5001 = int(request.POST.get('bumper_zad_5001', 0))
            estimation_settings.bumper_pered_replace_5001      = int(request.POST.get('bumper_pered_replace_5001', 0))
            estimation_settings.bumper_zad_replace_5001 = int(request.POST.get('bumper_zad_replace_5001', 0))


            estimation_settings.bumper_pered_kf_200      = int(request.POST.get('bumper_pered_kf_200', 0))
            estimation_settings.bumper_zad_kf_200 = int(request.POST.get('bumper_zad_kf_200', 0))
            estimation_settings.bumper_pered_replace_kf_200         = int(request.POST.get('bumper_pered_replace_kf_200', 0))
            estimation_settings.bumper_zad_replace_kf_200           = int(request.POST.get('bumper_zad_replace_kf_200', 0))

            estimation_settings.bumper_pered_kf_400      = int(request.POST.get('bumper_pered_kf_400', 0))
            estimation_settings.bumper_zad_kf_400 = int(request.POST.get('bumper_zad_kf_400', 0))
            estimation_settings.bumper_pered_replace_kf_400         = int(request.POST.get('bumper_pered_replace_kf_400', 0))
            estimation_settings.bumper_zad_replace_kf_400           = int(request.POST.get('bumper_zad_replace_kf_400', 0))


            estimation_settings.bumper_pered_kf_700      = int(request.POST.get('bumper_pered_kf_700', 0))
            estimation_settings.bumper_zad_kf_700 = int(request.POST.get('bumper_zad_kf_700', 0))
            estimation_settings.bumper_pered_replace_kf_700         = int(request.POST.get('bumper_pered_replace_kf_700', 0))
            estimation_settings.bumper_zad_replace_kf_700           = int(request.POST.get('bumper_zad_replace_kf_700', 0))


            estimation_settings.bumper_pered_kf_1200      = int(request.POST.get('bumper_pered_kf_1200', 0))
            estimation_settings.bumper_zad_kf_1200 = int(request.POST.get('bumper_zad_kf_1200', 0))
            estimation_settings.bumper_pered_replace_kf_1200         = int(request.POST.get('bumper_pered_replace_kf_1200', 0))
            estimation_settings.bumper_zad_replace_kf_1200           = int(request.POST.get('bumper_zad_replace_kf_1200', 0))


            estimation_settings.bumper_pered_kf_2000        = int(request.POST.get('bumper_pered_kf_2000', 0))
            estimation_settings.bumper_zad_kf_2000          = int(request.POST.get('bumper_zad_kf_2000', 0))
            estimation_settings.bumper_pered_replace_kf_2000         = int(request.POST.get('bumper_pered_replace_kf_2000', 0))
            estimation_settings.bumper_zad_replace_kf_2000           = int(request.POST.get('bumper_zad_replace_kf_2000', 0))

            estimation_settings.bumper_pered_kf_3000      = int(request.POST.get('bumper_pered_kf_3000', 0))
            estimation_settings.bumper_zad_kf_3000 = int(request.POST.get('bumper_zad_kf_3000', 0))
            estimation_settings.bumper_pered_replace_kf_3000         = int(request.POST.get('bumper_pered_replace_kf_3000', 0))
            estimation_settings.bumper_zad_replace_kf_3000           = int(request.POST.get('bumper_zad_replace_kf_3000', 0))

            estimation_settings.bumper_pered_kf_5000      = int(request.POST.get('bumper_pered_kf_5000', 0))
            estimation_settings.bumper_zad_kf_5000 = int(request.POST.get('bumper_zad_kf_5000', 0))
            estimation_settings.bumper_pered_replace_kf_5000         = int(request.POST.get('bumper_pered_replace_kf_5000', 0))
            estimation_settings.bumper_zad_replace_kf_5000           = int(request.POST.get('bumper_zad_replace_kf_5000', 0))

            estimation_settings.bumper_pered_kf_5001      = int(request.POST.get('bumper_pered_kf_5001', 0))
            estimation_settings.bumper_zad_kf_5001 = int(request.POST.get('bumper_zad_kf_5001', 0))
            estimation_settings.bumper_pered_replace_kf_5001         = int(request.POST.get('bumper_pered_replace_kf_5001', 0))
            estimation_settings.bumper_zad_replace_kf_5001           = int(request.POST.get('bumper_zad_replace_kf_5001', 0))

            estimation_settings.max_kf_iznos = float(request.POST.get('max_kf_iznos', 0))

            for key in request.POST.keys():
                if key.startswith('workdata_') and key.find('normo') > 0:
                    pk_work             = key.split('_')[1]
                    work                = RegPodgotovkaWork.objects.get(pk = pk_work)
                    work.normo          = float(request.POST.get('workdata_'+ pk_work + '_normo'))
                    work.price_podrad   = int(request.POST.get('workdata_'+ pk_work + '_price_podrad'))
                    work.price_kors     = int(request.POST.get('workdata_'+ pk_work + '_price_kors'))

                    work.materials_kf       = float(request.POST.get('workdata_'+ pk_work + '_materials_kf'))
                    work.materials_amount   = float(request.POST.get('workdata_'+ pk_work + '_materials_amount'))
                    
                    work.save()
                if key.startswith('engine_') or key.startswith('system_og_') > 0 or key.startswith('suspension_') > 0 or key.startswith('gear_') > 0 or key.startswith('wheel_') > 0 or key.startswith('turbo_') > 0 or key.startswith('conditioner_') > 0: 
                    setattr(estimation_settings, key, int(request.POST.get(key)))          

            estimation_settings.save()
            return HttpResponseRedirect(request.build_absolute_uri())
        
    dc          = request.GET.get('dc', '')
    page        = request.GET.get('page', '')
    unit        = None
    users       = list()
    docs        = list()
    list_dc     = list()
    cars        = list() 
    filtr       = dict()
    estimations = dict()
    balance_units   = list()
    balance_unit    = list() 
    paginator   = ''
    rating      = 0
    dash        = ''
    filter_unit = request.GET.getlist('unit[]')
    selected    = dict()

    select_units = RefUnit.objects.filter(buauto = True).order_by('name')
    list_dc_filtr = list()
    
    date                = request.GET.get('date_start', '')
    date_ends           = request.GET.get('date_end', '')

    if len(date) == 0:
        date_period = DT.datetime.now()
        date_start 	= date_period.replace(day = 1, hour = 0, minute=0, second=0, microsecond=0)
        if date_period.month > 11:
            month_end	= 1
            year_end 	= date_period.year + 1
        else:
            month_end	= date_period.month + 1
            year_end 	= date_period.year
        if len(date_ends) == 0:
            date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0, microsecond=0)
    else:
        dates = date.split('-')
        if len(dates) == 3:
            year 	        = int(dates[0])
            month 	        = int(dates[1])
            day             = int(dates[2])
            date_period     = DT.datetime.now()
            date_start 	    = date_period.replace(year = year, month = month, day = day, hour = 0, minute=0, second=0, microsecond=0)
            if month > 11:
                month_end 	= 1
                year_end 	= year + 1
            else:
                month_end 	= month + 1 
                year_end 	= year
            if len(date_ends) == 0:
                date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0, microsecond=0)			
    
    if len(date_ends) > 0:
        dates = date_ends.split('-')
        if len(dates) == 3:
            year 	        = int(dates[0])
            month 	        = int(dates[1])
            day             = int(dates[2])
            date_period     = DT.datetime.now()
            date_end 	    = date_period.replace(year = year, month = month, day = day, hour = 0, minute=0, second=0, microsecond=0)

    if page == '':
        if len(filter_unit) == 0:
            list_dc     = RefUnit.objects.filter(buauto = True).order_by('name')
        else:
            #unit        = RefUnit.objects.get(pk = dc)
            filter_unit = list(map(int, filter_unit))
            list_dc     = RefUnit.objects.filter(id__in = filter_unit).order_by('name')

        subquery_sale   = DocCarShipment.objects.filter(unit__id = OuterRef(name='id')).filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(active = True).annotate(count=Func(F('id'), function='Count')).values('count')
        subquery_sale_s = DocCarShipment.objects.filter(unit__id = OuterRef(name='id')).filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(active = True).annotate(amount_car=Func(F('amount'), function='Sum')).values('amount_car')

        subquery                    = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).annotate(count=Func(F('id'), function='Count')).values('count')
        subquery_s                  = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).annotate(price_car=Func(F('price'), function='Sum')).values('price_car')
        subquery_test_price         = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(stage_price__id = 4).annotate(count=Func(F('id'), function='Count')).values('count')
        subquery_test_price_s       = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(stage_price__id = 4).annotate(price_car=Func(F('price'), function='Sum')).values('price_car')
        subquery_rdo                = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(stage_price__id = 2).annotate(count=Func(F('id'), function='Count')).values('count')
        subquery_rdo_s              = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(stage_price__id = 2).annotate(price_car=Func(F('price'), function='Sum')).values('price_car')
        subquery_kor                = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(stage_price__id = 3).annotate(count=Func(F('id'), function='Count')).values('count')
        subquery_kor_s              = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(stage_price__id = 3).annotate(price_car=Func(F('price'), function='Sum')).values('price_car')
        subquery_txt                = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(stage_price__id = 1).annotate(count=Func(F('id'), function='Count')).values('count')
        subquery_txt_s              = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(stage_price__id = 1).annotate(price_car=Func(F('price'), function='Sum')).values('price_car')
        subquery_eval_avtohab       = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(evaluation__id = 1).annotate(count=Func(F('id'), function='Count')).values('count')
        subquery_eval_1c            = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(evaluation__id__in = [2, 8]).annotate(count=Func(F('id'), function='Count')).values('count')
        subquery_eval_uk            = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(evaluation__id = 3).annotate(count=Func(F('id'), function='Count')).values('count')
        subquery_eval_man           = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(evaluation__id = 4).annotate(count=Func(F('id'), function='Count')).values('count')
        subquery_eval_sed           = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(evaluation__id = 5).annotate(count=Func(F('id'), function='Count')).values('count')
        subquery_eval_express       = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(evaluation__id = 7).annotate(count=Func(F('id'), function='Count')).values('count')
        subquery_eval_avtohab_s     = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(evaluation__id = 1).annotate(price_car=Func(F('price'), function='Sum')).values('price_car')
        subquery_eval_1c_s          = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(evaluation__id__in = [2, 8]).annotate(price_car=Func(F('price'), function='Sum')).values('price_car')
        subquery_eval_uk_s          = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(evaluation__id = 3).annotate(price_car=Func(F('price'), function='Sum')).values('price_car')
        subquery_eval_man_s         = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(evaluation__id = 4).annotate(price_car=Func(F('price'), function='Sum')).values('price_car')
        subquery_eval_sed_s         = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(evaluation__id = 5).annotate(price_car=Func(F('price'), function='Sum')).values('price_car')
        subquery_eval_express_s     = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(evaluation__id = 7).annotate(price_car=Func(F('price'), function='Sum')).values('price_car')
        subquery_200                = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(group_price__id = 7).annotate(count=Func(F('id'), function='Count')).values('count')
        subquery_200_s              = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(group_price__id = 7).annotate(price_car=Func(F('price'), function='Sum')).values('price_car')
        subquery_400                = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(group_price__id = 1).annotate(count=Func(F('id'), function='Count')).values('count')
        subquery_400_s              = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(group_price__id = 1).annotate(price_car=Func(F('price'), function='Sum')).values('price_car')
        subquery_700                = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(group_price__id = 6).annotate(count=Func(F('id'), function='Count')).values('count')
        subquery_700_s              = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(group_price__id = 6).annotate(price_car=Func(F('price'), function='Sum')).values('price_car')
        subquery_1200               = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(group_price__id__in = [9,2]).annotate(count=Func(F('id'), function='Count')).values('count')
        subquery_1200_s             = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(group_price__id__in = [9,2]).annotate(price_car=Func(F('price'), function='Sum')).values('price_car')
        subquery_2000               = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(group_price__id__in = [10,3]).annotate(count=Func(F('id'), function='Count')).values('count')
        subquery_2000_s             = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(group_price__id__in = [10,3]).annotate(price_car=Func(F('price'), function='Sum')).values('price_car')
        subquery_3000               = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(group_price__id = 4).annotate(count=Func(F('id'), function='Count')).values('count')
        subquery_3000_s             = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(group_price__id = 4).annotate(price_car=Func(F('price'), function='Sum')).values('price_car')
        subquery_5000               = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(group_price__id__in = [8,5]).annotate(count=Func(F('id'), function='Count')).values('count')
        subquery_5000_s             = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(group_price__id__in = [8,5]).annotate(price_car=Func(F('price'), function='Sum')).values('price_car')
        subquery_5001               = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(group_price__id = 12).annotate(count=Func(F('id'), function='Count')).values('count')
        subquery_5001_s             = RefCarsOrganization.objects.filter(unit__id = OuterRef(name='id')).filter(quantity = 1).filter(group_price__id = 12).annotate(price_car=Func(F('price'), function='Sum')).values('price_car')

        list_dc     = list_dc.annotate(
            count_eval_avtohab      = Coalesce(Subquery(subquery_eval_avtohab), Value(0))).annotate(
            count_eval_1c           = Coalesce(Subquery(subquery_eval_1c), Value(0))).annotate( 
            count_eval_uk           = Coalesce(Subquery(subquery_eval_uk), Value(0))).annotate( 
            count_eval_man          = Coalesce(Subquery(subquery_eval_man), Value(0))).annotate(
            count_eval_sed          = Coalesce(Subquery(subquery_eval_sed), Value(0))).annotate(
            count_eval_express      = Coalesce(Subquery(subquery_eval_express), Value(0))).annotate(
            count_eval_avtohab_s    = Coalesce(Subquery(subquery_eval_avtohab_s), Value(0))).annotate(
            count_eval_1c_s         = Coalesce(Subquery(subquery_eval_1c_s), Value(0))).annotate(
            count_eval_uk_s         = Coalesce(Subquery(subquery_eval_uk_s), Value(0))).annotate(
            count_eval_man_s        = Coalesce(Subquery(subquery_eval_man_s), Value(0))).annotate(
            count_eval_sed_s        = Coalesce(Subquery(subquery_eval_sed_s), Value(0))).annotate(
            count_eval_express_s    = Coalesce(Subquery(subquery_eval_express_s), Value(0))).annotate(
            count_sale      = Subquery(subquery_sale)).annotate(
            count_sale_s    = Subquery(subquery_sale_s)).annotate(
            count_cars      = Subquery(subquery)).annotate(
            count_cars_s    = Subquery(subquery_s)).annotate(
            count_test      = Subquery(subquery_test_price)).annotate(
            count_test_s    = Subquery(subquery_test_price_s)).annotate(    
            count_rdo       = Subquery(subquery_rdo)).annotate(
            count_rdo_s     = Subquery(subquery_rdo_s)).annotate(
            count_kor       = Subquery(subquery_kor)).annotate(
            count_kor_s     = Subquery(subquery_kor_s)).annotate(
            count_txt       = Subquery(subquery_txt)).annotate(
            count_txt_s     = Subquery(subquery_txt_s)).annotate(
            count_200       = Subquery(subquery_200)).annotate(
            count_200_s     = Coalesce(Subquery(subquery_200_s), Value(0))).annotate(
            count_400       = Subquery(subquery_400)).annotate(
            count_400_s     = Coalesce(Subquery(subquery_400_s), Value(0))).annotate(
            count_700       = Subquery(subquery_700)).annotate(
            count_700_s     = Coalesce(Subquery(subquery_700_s), Value(0))).annotate(
            count_1200      = Subquery(subquery_1200)).annotate(
            count_1200_s    = Coalesce(Subquery(subquery_1200_s), Value(0))).annotate(
            count_2000      = Subquery(subquery_2000)).annotate(
            count_2000_s    = Coalesce(Subquery(subquery_2000_s), Value(0))).annotate(
            count_3000      = Subquery(subquery_3000)).annotate(
            count_3000_s    = Coalesce(Subquery(subquery_3000_s), Value(0))).annotate(
            count_5000      = Subquery(subquery_5000)).annotate(
            count_5000_s    = Coalesce(Subquery(subquery_5000_s), Value(0))).annotate(
            count_5001      = Subquery(subquery_5001)).annotate(
            count_5001_s    = Coalesce(Subquery(subquery_5001_s), Value(0)))
        
        #docs            = DocRLK.objects.filter(unit__in = list_dc).filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(type__id = 7).filter(eco = True).order_by('-dataTime') | DocRLK.objects.filter(unit__in = list_dc).filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(type__id = 7).filter(eco = True).order_by('-dataTime')
        #docs            = DocRLK.objects.filter(unit__in = list_dc).filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(eco = True).order_by('-dataTime') | DocRLK.objects.filter(unit__in = list_dc).filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(eco = True).order_by('-dataTime')
        if len(filter_unit) == 0:
            docs            = DocRLK.objects.filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(eco = True)
        else:
            docs            = DocRLK.objects.filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(eco = True).filter(unit__in = list_dc) | DocRLK.objects.filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(eco = True).filter(unit_dc__in = list_dc)
        
        subquery        = RegInteractivOcenka.objects.filter(rlk__id = OuterRef(name='id'))
        subquery_lo     = DocLO.objects.filter(rlk__id = OuterRef(name='id'))
        docs        = docs.annotate(
            unit_name               = Subquery(subquery.values('page_documents__unit__name')[:1])).annotate(
            unit_name_dc               = Subquery(subquery.values('page_documents__unit__id')[:1])).annotate(
            status_estimation       = Subquery(subquery.values('status__name')[:1])).annotate(
            status_estimation_id    = Subquery(subquery.values('status__id')[:1])).annotate(
            start_estimation        = Subquery(subquery.values('start_estimation')[:1])).annotate(
            end_estimation          = Subquery(subquery.values('end_estimation')[:1])).annotate(
            staff_estimation_name    = Subquery(subquery.values('staff__name')[:1])).annotate(
            staff_estimation    = Subquery(subquery.values('staff')[:1])).annotate(
            mark                = Subquery(subquery.values('modification__model__mark__name')[:1])).annotate(
            model = Subquery(subquery.values('modification__model__name')[:1])).annotate(
            modification = Subquery(subquery.values('modification__name')[:1])).annotate(
            type_estimation_ocenka = Subquery(subquery.values('page_documents__type_reception__name')[:1])).annotate(
            type_estimation_ocenka_id = Subquery(subquery.values('page_documents__type_reception__id')[:1])).annotate(
            year = Subquery(subquery.values('year')[:1])).annotate(
            vin = Subquery(subquery.values('vin')[:1])).annotate(
            lo_pk = Subquery(subquery.values('id')[:1])).annotate(
            lo_active = Subquery(subquery_lo.values('active')[:1])).annotate(
            count_data = Value(1, output_field=IntegerField())
            )

        data        = docs.order_by('type_estimation_ocenka').values('type_estimation_ocenka').exclude(type_estimation_ocenka = None).distinct().annotate(Sum('count_data'))
        data_unit   = docs.order_by('unit_name').values('unit_name').distinct().annotate(Sum('count_data')).exclude(unit_name = None)
        
        dash = list_dc.order_by('id').aggregate(Sum('count_eval_avtohab'), 
                                                Sum('count_eval_1c'), 
                                                Sum('count_eval_man'), 
                                                Sum('count_eval_uk'), 
                                                Sum('count_eval_sed'),
                                                Sum('count_eval_express'),  
                                                Sum('count_eval_avtohab_s'), 
                                                Sum('count_eval_1c_s'), 
                                                Sum('count_eval_man_s'), 
                                                Sum('count_eval_uk_s'), 
                                                Sum('count_eval_sed_s'),
                                                Sum('count_eval_express_s'), 
                                                Sum('count_200'), 
                                                Sum('count_400'), 
                                                Sum('count_700'), 
                                                Sum('count_1200'), 
                                                Sum('count_2000'), 
                                                Sum('count_3000'), 
                                                Sum('count_5000'), 
                                                Sum('count_5001'), 
                                                Sum('count_200_s'), 
                                                Sum('count_400_s'), 
                                                Sum('count_700_s'), 
                                                Sum('count_1200_s'), 
                                                Sum('count_2000_s'), 
                                                Sum('count_3000_s'), 
                                                Sum('count_5000_s'),
                                                Sum('count_5001_s'), 
                                                Sum('count_test'), 
                                                Sum('count_rdo'), 
                                                Sum('count_kor'), 
                                                Sum('count_txt'), 
                                                Sum('count_test_s'), 
                                                Sum('count_rdo_s'), 
                                                Sum('count_kor_s'), 
                                                Sum('count_txt_s'), 
                                                Sum('count_cars'), 
                                                Sum('count_cars_s'),
                                                Sum('count_sale'),
                                                Sum('count_sale_s'))

        count_rlk_all           = docs.count()
        count_kd                = docs.exclude(status_estimation_id = None).count()
        count_affter_kd         = docs.filter(status_estimation_id__in = [6,8,4,7]).count()
        count_success           = docs.filter(lo_active = True).count()

        try:
            count_kd_percent            = 0
            count_after_kd_percent      = 0
            count_success_kd_percent    = 0
            if count_rlk_all > 0:
                if count_kd > 0: 
                    count_kd_percent = str(round(count_kd / count_rlk_all * 100, 2))
                    if count_affter_kd > 0:
                        count_after_kd_percent = str(round(count_affter_kd / count_kd * 100, 2))
                        if count_success > 0:
                            count_success_kd_percent = str(round(count_success / count_affter_kd * 100, 2))

            estimations = {
                'count_rlk_all'         : count_rlk_all,
                'count_kd'              : count_kd,
                'count_affter_kd'       : count_affter_kd,
                'count_success'         : count_success,
                'count_kd_percent'              : count_kd_percent,
                'count_after_kd_percent'        : count_after_kd_percent,
                'count_success_kd_percent'      : count_success_kd_percent,
                'data'  : data
            }
        except:
            estimations = {
                'count_rlk_all'         : count_rlk_all,
                'count_kd'              : count_kd,
                'count_affter_kd'       : count_affter_kd,
                'count_success'         : count_success,
                'count_kd_percent'              : 0,
                'count_after_kd_percent'        : 0,
                'count_success_kd_percent'      : 0,
                'data'  : data
            }
        
        #unit = list_dc[0]
        rating = rating_nps_sale_unit(units = list_dc.values('id'), date_start=date_start, date_end=date_end)
        
        filtr = {
            'date_start'    : date_start,
            'date_end'      : date_end,
            'filter_unit'   : filter_unit
        }

    if page == 'rlk_trade_in':
        


        date                = request.GET.get('date_start', '')
        date_ends           = request.GET.get('date_end', '')

        if len(date) == 0:
            date_period = DT.datetime.now()
            date_start 	= date_period.replace(day = 1, hour = 0, minute=0, second=0, microsecond=0)
            if date_period.month > 11:
                month_end	= 1
                year_end 	= date_period.year + 1
            else:
                month_end	= date_period.month + 1
                year_end 	= date_period.year
            if len(date_ends) == 0:
                date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0, microsecond=0)
        else:
            dates = date.split('-')
            if len(dates) == 3:
                year 	        = int(dates[0])
                month 	        = int(dates[1])
                day             = int(dates[2])
                date_period     = DT.datetime.now()
                date_start 	    = date_period.replace(year = year, month = month, day = day, hour = 0, minute=0, second=0, microsecond=0)
                if month > 11:
                    month_end 	= 1
                    year_end 	= year + 1
                else:
                    month_end 	= month + 1 
                    year_end 	= year
                if len(date_ends) == 0:
                    date_end 	= date_period.replace(year = year_end, month = month_end, day = 1, hour = 0, minute=0, second=0, microsecond=0)			
        
        if len(date_ends) > 0:
            dates = date_ends.split('-')
            if len(dates) == 3:
                year 	        = int(dates[0])
                month 	        = int(dates[1])
                day             = int(dates[2])
                date_period     = DT.datetime.now()
                date_end 	    = date_period.replace(year = year, month = month, day = day, hour = 0, minute=0, second=0, microsecond=0)
        
        filtr_vin       = request.GET.get('vin', '') 
        filtr_rlk_nomer = request.GET.get('number_doc', '')         
        filtr_lo        = request.GET.get('filtr_lo', '')
        filtr_rlk_op    = request.GET.get('filtr_rlk_op', '')
        filtr_sale      = request.GET.get('filtr_sale', '')
        if len(filter_unit) == 0:
            list_dc     = RefUnit.objects.filter(buauto = True).order_by('name')
        else:
            #unit        = RefUnit.objects.get(pk = dc)
            filter_unit = list(map(int, filter_unit))
            list_dc     = RefUnit.objects.filter(id__in = filter_unit).order_by('name')

        staffKKID   = ""
        staffsKK    = Profiles.objects.filter(view_checklist = False).order_by('user__last_name')
                
        unit_id      = ""
        units_select = RefUnit.objects.filter(buauto = True).exclude(name = '').order_by("name")
        
        type_receptions_id = request.GET.get('type_receptions_id', '')

        staffID         = ""
        staffsSelect    = ""
        
        docs            = DocRLK.objects.filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(type__id = 2).filter(unit_dc__buauto = True) | DocRLK.objects.filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(type__id = 7).filter(eco = True).order_by('-dataTime') | DocRLK.objects.filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(type__id = 1).filter(eco = True).order_by('-dataTime') | DocRLK.objects.filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(type__id = 19).filter(eco = True).order_by('-dataTime')
        docs            = docs.filter(unit__in = list_dc) | docs.filter(unit_dc__in = list_dc)

        docs_rlk_op                 = DocRLK.objects.filter(eco = False).filter(uin = OuterRef(name='uin'))
        docs_rlk_op_kors            = DocRLK.objects.filter(uin = OuterRef(name='uin'))
        subquery_lo                 = DocLO.objects.filter(rlk__id = OuterRef(name='id'))
        subquery                    = RegInteractivOcenka.objects.filter(rlk__id = OuterRef(name='id'))
        subqyery_chat               = Chat.objects.filter(rlk_id = OuterRef(name = 'id'))
        
        
        docs        = docs.annotate(
            estimation_unit_id                 = Subquery(subquery.values('page_documents__unit__id')[:1])).annotate(
            unit_name               = Subquery(subquery.values('page_documents__unit__name')[:1])).annotate(
            status_estimation       = Subquery(subquery.values('status__name')[:1])).annotate(
            status_estimation_id    = Subquery(subquery.values('status__id')[:1])).annotate(
            start_estimation    = Subquery(subquery.values('start_estimation')[:1])).annotate(
            end_estimation      = Subquery(subquery.values('end_estimation')[:1])).annotate(
            staff_estimation    = Subquery(subquery.values('staff')[:1])).annotate(
            estimation_id                               = Subquery(subquery.values('id')[:1])).annotate(
            estimation_avito_price_avg_market_price     = Subquery(subquery.values('avito_price_avg_market_price')[:1])).annotate(
            estimation_avito_price_avg_condition        = Subquery(subquery.values('avito_price_avg_condition')[:1])).annotate(
            estimation_avito_price_market_min           = Subquery(subquery.values('avito_price_market_min')[:1])).annotate(
            estimation_avito_price_min                  = Subquery(subquery.values('avito_price_min')[:1])).annotate(
            estimation_avito_price_market_max           = Subquery(subquery.values('avito_price_market_max')[:1])).annotate(
            estimation_avito_price_max                  = Subquery(subquery.values('avito_price_max')[:1])).annotate(
            estimation_taxi                             = Subquery(subquery.values('taxi')[:1])).annotate(
            estimation_carsharing                       = Subquery(subquery.values('carsharing')[:1])).annotate(
            estimation_count_dtp                        = Subquery(subquery.values('count_dtp')[:1])).annotate(
            estimation_dtp_red                          = Subquery(subquery.values('dtp_red')[:1])).annotate(
            estimation_avtoteka_car_autodex             = Subquery(subquery.values('avtoteka_car_autodex')[:1])).annotate(                
            estimation_avtoteka_web                     = Subquery(subquery.values('avtoteka_web')[:1])).annotate(                
            estimation_count_owners                     = Subquery(subquery.values('page_documents__count_owners')[:1])).annotate(                
            estimation_kors_price_min                   = Subquery(subquery.values('kors_price_min')[:1])).annotate(                
            estimation_kors_price_max                   = Subquery(subquery.values('kors_price_max')[:1])).annotate(                
            estimation_kors_price_market_min            = Subquery(subquery.values('kors_price_market_min')[:1])).annotate(                
            estimation_kors_price_market_max            = Subquery(subquery.values('kors_price_market_max')[:1])).annotate(                
            estimation_kors_sale_price_avg  = Subquery(subquery.values('kors_sale_price_avg')[:1])).annotate( 
            estimation_hub_start = Subquery(subquery.values('hub_start')[:1])).annotate(
            estimation_hub_sale_price_max = Subquery(subquery.values('hub_sale_price_max')[:1])).annotate(
            estimation_hub_sale_price_min= Subquery(subquery.values('hub_sale_price_min')[:1])).annotate(
            estimation_hub_price_max= Subquery(subquery.values('hub_price_max')[:1])).annotate(
            estimation_hub_price_min= Subquery(subquery.values('hub_price_min')[:1])).annotate(
            estimation_kors_start_store = Subquery(subquery.values('kors_start_store')[:1])).annotate( 
            price_recept            = Subquery(subquery.values('page_soglasovanie__price_reception')[:1])).annotate(
            price_sale              = Subquery(subquery.values('page_soglasovanie__price_sale')[:1])).annotate(
            price_before_kd         = Subquery(subquery.values('page_soglasovanie__price_before_kd')[:1])).annotate(
            price_after_kd          = Subquery(subquery.values('page_soglasovanie__price_after_kd')[:1])).annotate(
            price_price_bcp          = Subquery(subquery.values('page_soglasovanie__price_bcp')[:1])).annotate(
            amount_podgotovka           = Subquery(subquery.values('page_soglasovanie__amount_podgotovka')[:1])).annotate(
            amount_ss                   = Subquery(subquery.values('page_soglasovanie__amount_ss')[:1])).annotate(
            amount_mcu                  = Subquery(subquery.values('page_soglasovanie__amount_mcu')[:1])).annotate(
            car_sale_info          = Subquery(subquery.values('page_soglasovanie__car_sale_info')[:1])).annotate(
            car_sale_price          = Subquery(subquery.values('page_soglasovanie__car_sale_price')[:1])).annotate(
            mark                    = Subquery(subquery.values('modification__model__mark__name')[:1])).annotate(
            model                   = Subquery(subquery.values('modification__model__name')[:1])).annotate(
            modification            = Subquery(subquery.values('modification__name')[:1])).annotate(
            run                     = Subquery(subquery.values('page_salon__run')[:1])).annotate(
            type_estimation_ocenka      = Subquery(subquery.values('page_documents__type_reception__name')[:1])).annotate(
            type_estimation_ocenka_id   = Subquery(subquery.values('page_documents__type_reception__id')[:1])).annotate(
            year                = Subquery(subquery.values('year')[:1])).annotate(
            vin                 = Subquery(subquery.values('vin')[:1])).annotate(
            lo_pk               = Subquery(subquery.values('id')[:1])).annotate(
            lo_nomer            = Coalesce(Subquery(subquery_lo.values('nomer')[:1]), Value(''))).annotate(
            lo_date             = Coalesce(Subquery(subquery_lo.values('dataTime')[:1]), Value(DT.datetime(1,1,1)))).annotate(
            lo_active           = Coalesce(Subquery(subquery_lo.values('active')[:1]), Value(False))).annotate(
            rlk_op              = Coalesce(Subquery(docs_rlk_op.values('footing__uin')[:1]), Subquery(docs_rlk_op_kors.values('footing__uin')[:1]))).annotate(
            rlk_op_nomer        = Coalesce(Subquery(docs_rlk_op.values('footing__nomer')[:1]), Subquery(docs_rlk_op_kors.values('footing__nomer')[:1]))).annotate(
            rlk_op_dataTime     = Coalesce(Subquery(docs_rlk_op.values('footing__dataTime')[:1]), Subquery(docs_rlk_op_kors.values('footing__dataTime')[:1]))).annotate(
            rlk_op_unit         = Coalesce(Subquery(docs_rlk_op.values('footing__unit')[:1]), Subquery(docs_rlk_op.values('footing__unit_dc')[:1]))).annotate(
            rlk_op_unitname     = Coalesce(Subquery(docs_rlk_op.values('footing__unit__name')[:1]), Subquery(docs_rlk_op_kors.values('footing__unit__name')[:1]))).annotate(
            rlk_op_unitdcname   = Coalesce(Subquery(docs_rlk_op.values('footing__unit_dc__name')[:1]), Subquery(docs_rlk_op_kors.values('footing__unit_dc__name')[:1]))).annotate(
            rlk_op_staff        = Coalesce(Subquery(docs_rlk_op.values('footing__staff__name')[:1]), Subquery(docs_rlk_op_kors.values('footing__staff__name')[:1]))).annotate(
            rlk_op_id           = Coalesce(Subquery(docs_rlk_op.values('id')[:1]), Subquery(docs_rlk_op_kors.values('id')[:1])))
        
        subqyery_sale = DocCarShipment.objects.filter(active = True).filter(rlk__uin = OuterRef(name='rlk_op'))
        
        #.annotate(related_count=Count('related_table'))

        docs = docs.annotate(
           count_task = Coalesce(Subquery(RegInteractivOcenkaTask.objects.filter(estimation__id = OuterRef(name='estimation_id')).order_by().annotate(count=Func(F('id'), function='Count')).values('count')), Value(0))
        )
        docs = docs.annotate(
            chat_id = Coalesce(Subquery(subqyery_chat.values('id')[:1]), Value(0))   
        )
        #.annotate(count=Func(F('id'), function='Count')).values('count')
        subqyery_message            = User.objects.filter(chatmessage__chat__id = OuterRef(name = 'chat_id')).order_by().distinct().annotate(count=Func(F('id'), function='Count')).values('count')
        subqyery_message_info       = ChatMessage.objects.filter(chat__id = OuterRef(name = 'chat_id')).filter(user__profiles__eco = False).order_by().values('user__id').annotate(count=Func(F('user__id'), function='DISTINCT Count')).values('count')
        subqyery_message_info_eco   = ChatMessage.objects.filter(chat__id = OuterRef(name = 'chat_id')).filter(user__profiles__eco = True).order_by().annotate(count=Func(F('user__id'), function='Count')).values('count')
        
        docs = docs.annotate(
            count_users_chat = Coalesce(Subquery(subqyery_message), Value(0))
        )        
        docs = docs.annotate(
            count_users_eco = Coalesce(Subquery(subqyery_message_info_eco), Value(0))
        )    
        
        docs = docs.annotate(
            chat_user = F('count_users_chat') + F('count_users_eco')
        )

        docs = docs.annotate(
           sale_id              = Coalesce(Subquery(subqyery_sale.values('id')[:1]), Value(0))).annotate(
           sale_nomer           = Coalesce(Subquery(subqyery_sale.values('nomer')[:1]), Value(''))).annotate(
           sale_active          = Coalesce(Subquery(subqyery_sale.values('active')[:1]), Value(False))).annotate(
           sale_car_mark        = Coalesce(Subquery(subqyery_sale.values('cars__mark')[:1]), Value(''))).annotate(
           sale_car_model        = Coalesce(Subquery(subqyery_sale.values('cars__model')[:1]), Value(''))).annotate(
           sale_car_year        = Coalesce(Subquery(subqyery_sale.values('cars__year')[:1]), Value(''))).annotate(
           sale_car             = Coalesce(Subquery(subqyery_sale.values('cars__vin')[:1]), Value(''))).annotate(
           sale_date            = Coalesce(Subquery(subqyery_sale.values('dataTime')[:1]), Value(DT.datetime(1,1,1)))).annotate(
           sale_staff           = Coalesce(Subquery(subqyery_sale.values('staff__name')[:1]), Value('')))
        

        subquery_signal = Autoteka_signal.objects.filter(vin = OuterRef(name='vin')).order_by('date')
        
        docs = docs.annotate(
            signal_seller       = Subquery(subquery_signal.values('seller')[:1])).annotate(
            signal_brand        = Subquery(subquery_signal.values('brand')[:1])).annotate(
            signal_model        = Subquery(subquery_signal.values('model')[:1])).annotate(
            signal_year         = Subquery(subquery_signal.values('year')[:1])).annotate(
            signal_mileage      = Subquery(subquery_signal.values('mileage')[:1])).annotate(
            signal_url          = Subquery(subquery_signal.values('url')[:1])).annotate(
            signal_price        = Subquery(subquery_signal.values('price')[:1])).annotate(
            signal_description  = Subquery(subquery_signal.values('description')[:1]))
            
        filtr_signal = request.GET.get('filtr_signal', '')
        if len(filtr_signal) > 0:
            filtr_signal = int(filtr_signal)
            if filtr_signal == 1:
                docs = docs.exclude(signal_seller = None)    
            elif filtr_signal == 2:
                docs = docs.filter(signal_seller__icontains = 'Автодилер')
            elif filtr_signal == 3:
                docs = docs.filter(signal_seller__icontains = 'Частное лицо').exclude(signal_seller__icontains = 'перепродажи')
            elif filtr_signal == 4:
                docs = docs.filter(signal_seller__icontains = 'перепродажи')
        if filtr_vin != '':
            docs = docs.filter(vin__icontains = filtr_vin)

        if filtr_rlk_nomer != '':
            docs = docs.filter(nomer__icontains = filtr_rlk_nomer) | docs.filter(rlk_op_nomer__icontains = filtr_rlk_nomer) 
        
        if filtr_lo != '':
            if filtr_lo == '1':
                docs = docs.filter(lo_nomer = '')
            elif filtr_lo == '2':
                docs = docs.exclude(lo_nomer = '').filter(lo_active = False)
            elif filtr_lo == '3':
                docs = docs.exclude(lo_nomer = '').filter(lo_active = True)
        if filtr_rlk_op != '':
            if filtr_rlk_op == '1':
                docs = docs.filter(rlk_op_nomer = '')
            elif filtr_rlk_op == '2':
                docs = docs.exclude(rlk_op_nomer = '')
        if filtr_sale != '':
            if filtr_sale == '1':
                docs = docs.filter(sale_nomer = '')
            elif filtr_sale == '2':
                docs = docs.exclude(sale_nomer = '')

        if 'save_xls' in request.GET:
            
            stamp = DT.datetime.now().strftime("%d_%m_%Y %H:%M:%S")
            headers = {
                'file_name' : 'rlk_trade_in_' + stamp + '.xlsx'
            }

            response = HttpResponse(content_type='application/ms-excel', headers = headers)
            response['Content-Disposition'] = 'attachment; filename="rlk_trade_in_' + stamp + '.xlsx"'
            
            wb = Workbook()
            ws = wb.active
            ws.title = "Рабочие листы трейд ин"
            ws.append([stamp,])
            ws.append([str(request.get_full_path()),])
            ws.append([])
            # Add headers
            headers = ["РЛК трейд ин дата", 
                       "РЛК трейд ин номер", 
                        "РЛК трейд ин подразделение", 
                        "РЛК трейд ин сотрудник", 
                        "РЛК трейд ин Дата архива", 
                        "РЛК трейд ин Причина архива",
                        "РЛК трейд ин тип оценки", 
                        "Лист оценки дата", 
                        "Лист оценки номер",
                        "Лист оценки проведен",
                        "РЛК ОП есть", 
                        "РЛК ОП дата", 
                        "РЛК ОП номер", 
                        "РЛК ОП подразделение", 
                        "РЛК ОП сотрудник", 
                        "Отгрузка ОП дата",
                        "Отгрузка ОП номер",
                        "Отгрузка ОП проведена",
                        "Отгрузка ОП автомобиль",
                        "Отгрузка ОП сотрудник",
                        "Марка",
                        "Модель",
                        "Модификация",
                        "Владельцев",
                        "Год",
                        "Пробег",
                        "VIN",
                        "Такси",
                        "Каршеринг",
                        "Количество ДТП",
                        "Есть серьезное ДТП",
                        "Cумма расчетов ремонтов",
                        "Автотека",
                        "Начало оценки",
                        "Конец оценки",
                        "Задач",
                        "Участников чата",
                        "Оценщик цена выкуп",
                        "Оценщик цена продажа",
                        "ЕЦО цена выкуп до кд",
                        "ЕЦО цена выкуп после кд",
                        "Затраты на подготовку",
                        "Затраты на слесарный участок",
                        "Затраты на кузовной участок",
                        "БЦП",
                        "Приобретаемый автомобиль",
                        "Цена приобритаемого автомобиля",
                        "Ссылка на оценку",
                        "Сигнал",
                        "Сигнал АМ",
                        "Сигнал УРЛ",
                        "Сигнал Цена",
                        "Сигнал описание",
                       ]
            
            ws.append(headers)

            # Add data from the model
            #docs = docs.values()

            for doc in docs:
                if doc.unit != None:
                    unit = str(doc.unit.name)
                elif doc.unit_dc != None:
                    unit = str(doc.unit_dc.name)
                else:
                    unit = ''
                if doc.staff != None:
                    staff = str(doc.staff.name)
                else:
                    staff = ''

                rlk_op = False
                if doc.rlk_op != None:
                    rlk_op = True

                signal_car = ""
                if doc.signal_brand != None:
                    signal_car = doc.signal_brand + " " + doc.signal_model + " " + str(doc.signal_year) + " " + str(doc.signal_mileage)
                
                ws.append([doc.dataTime, 
                            doc.nomer, 
                            unit, 
                            staff, 
                            doc.dateArchive, 
                            doc.reasonArchive,
                            doc.type_estimation_ocenka, 
                            doc.lo_date,
                            doc.lo_nomer,
                            doc.lo_active,
                            rlk_op,
                            doc.rlk_op_dataTime,
                            doc.rlk_op_nomer,
                            doc.rlk_op_unitname,
                            doc.rlk_op_staff,
                            doc.sale_date,
                            doc.sale_nomer,
                            doc.sale_active,
                            doc.sale_car + " / " + doc.sale_car_mark + " " + doc.sale_car_model + " " + doc.sale_car_year,
                            doc.sale_staff,
                            doc.mark,
                            doc.model,
                            doc.modification,
                            doc.estimation_count_owners,
                            doc.year,
                            doc.run,
                            doc.vin,
                            doc.estimation_taxi,
                            doc.estimation_carsharing,
                            doc.estimation_count_dtp,
                            doc.estimation_dtp_red,
                            doc.estimation_avtoteka_car_autodex,
                            doc.estimation_avtoteka_web,
                            doc.start_estimation,
                            doc.end_estimation,
                            doc.count_task, 
                            doc.count_users_chat, 
                            doc.price_recept, 
                            doc.price_sale,
                            doc.price_before_kd, 
                            doc.price_after_kd,
                            doc.amount_podgotovka,
                            doc.amount_ss,
                            doc.amount_mcu,
                            doc.price_price_bcp,
                            doc.car_sale_info,
                            doc.car_sale_price,
                            "https://ah.kors-group.com/eco/" + str(doc.id) + "/?page=9",
                            doc.signal_seller,
                            signal_car,
                            doc.signal_url,
                            doc.signal_price,
                            doc.signal_description,
                           ])

            # Save the workbook to the HttpResponse
            wb.save(response)
            return response
    
        page_number     = request.GET.get('page_num')
        select_count    = int(request.GET.get('select_count', '25'))
        paginator       = Paginator(docs, select_count)
        paginator       = paginator.get_page(page_number)
        filtr_vin       = request.GET.get('vin', '') 
        filtr = {
            'date_start'    : date_start,
            'date_end'      : date_end,
            'filter_unit'   : filter_unit,
            'number_doc'    : filtr_rlk_nomer,
            'select_count'  : select_count,
            'filtr_vin'     : filtr_vin,
            'filtr_lo'      : filtr_lo,
            'filtr_rlk_op'  : filtr_rlk_op,
            'filtr_sale'    : filtr_sale,
            'filtr_signal'  : filtr_signal
            }    

    if page == 'cars':
        cars = RefCarsOrganization.objects.filter(quantity = 1)
        filtr_vin   = request.GET.get('vin', '')
        filtr_name  = request.GET.get('name', '') 

        if filtr_vin != '':
            cars = cars.filter(vin__icontains = filtr_vin)

        if filtr_name != '':
            cars = cars.filter(modification_autoru__name__icontains = filtr_name) | cars.filter(modification_autoru__model__name__icontains = filtr_name) | cars.filter(modification_autoru__model__mark__name__icontains = filtr_name)
        
        page_number     = request.GET.get('page_num')
        select_count    = int(request.GET.get('select_count', '25'))
        paginator       = Paginator(cars, select_count)
        paginator       = paginator.get_page(page_number)

        filtr = {
            'filter_unit'   : filter_unit,
            'select_count'  : select_count,
            'filtr_vin'     : filtr_vin,
            'filtr_name'    : filtr_name
            }
        
    if page == 'sale':
        cars = DocCarShipment.objects.filter(unit = unit).filter(dataTime__gte = date_start).filter(dataTime__lte = date_end)

    if page == 'balance_units':
        
        type_receptions = RefTypeReceptionCarsOrganization.objects.all().order_by('name')
        
        name_unit           = request.GET.get('name_unit','')
        type_reception_id   = request.GET.get('type_reception_id','')    
        vin                 = request.GET.get('vin', '')
        
        date_start      = request.GET.get('date_start', '')
        date_end        = request.GET.get('date_end', '')
        
        if date_start == '':
            date_start = DT.datetime.now() - relativedelta(months=2)
            date_start = date_start.replace(day = 1, hour = 0, minute=0, second=0)
        else:
            date_start =  DT.datetime.strptime(date_start, "%Y-%m-%d")
        
        if date_end == '':
            date_end = DT.datetime.now().replace(hour = 23)
        else:
            date_end = DT.datetime.strptime(date_end, "%Y-%m-%d").replace(hour = 23)
        
        selected = {
            'type_receptions'   : type_receptions
        }

        from register.models import RegEstimationBalanceUnit
        if request.user.profiles.korsavto_city != None and request.user.profiles.korsavto_city != "":
            balance_units = RegEstimationBalanceUnit.objects.filter(unit__name__icontains = request.user.profiles.korsavto_city)
        else:
            balance_units = RegEstimationBalanceUnit.objects.all()
        balance_units = balance_units.filter(date__gte = date_start).filter(date__lte = date_end)
        
        if vin != '':
            balance_units = balance_units.filter(estimation__vin__icontains = vin)
        if type_reception_id != '':
            type_reception_id = int(type_reception_id)
            balance_units = balance_units.filter(estimation__page_documents__type_reception__id = type_reception_id)
        
        balance_units = balance_units.values('unit').order_by('unit').distinct().annotate(sum = Sum('amount')).values('unit', 'unit__name', 'sum' , ).order_by('-sum')
        if len(name_unit) > 0:
            balance_units = balance_units.filter(unit__name__icontains = name_unit)
        
        filtr = {
            'name_unit'         : name_unit,
            'date_start'        : date_start,
            'date_end'          : date_end,
            'vin'               : vin,
            'type_reception_id' : type_reception_id,
        }
        
    if page == 'balance_unit':
        type_receptions = RefTypeReceptionCarsOrganization.objects.all().order_by('name')
        type_reception_id   = request.GET.get('type_reception_id','')    
        
        unit = RefUnit.objects.get(pk = request.GET.get('dc',''))
        
        vin             = request.GET.get('vin', '')
        date_start      = request.GET.get('date_start', '')
        date_end        = request.GET.get('date_end', '')
        
        if date_start == '':
            date_start = DT.datetime.now() - relativedelta(months=2)
            date_start = date_start.replace(day = 1, hour = 0, minute=0, second=0)
        else:
            date_start =  DT.datetime.strptime(date_start, "%Y-%m-%d")
        
        if date_end == '':
            date_end = DT.datetime.now().replace(hour = 23) 
        else:
            date_end = DT.datetime.strptime(date_end, "%Y-%m-%d").replace(hour = 23)
        
        from register.models import RegEstimationBalanceUnit
        balance_unit = RegEstimationBalanceUnit.objects.filter(unit = unit)
        balance_unit = balance_unit.filter(date__gte = date_start).filter(date__lte = date_end)
        if vin != '':
            balance_unit = balance_unit.filter(estimation__vin__icontains = vin)
        if type_reception_id != '':
            type_reception_id = int(type_reception_id)
            balance_unit = balance_unit.filter(estimation__page_documents__type_reception__id = type_reception_id)
        balance_unit = balance_unit.order_by('-date')
        
        selected = {
            'type_receptions'   : type_receptions
        }
        filtr = {
            'date_start'        : date_start,
            'date_end'          : date_end,
            'vin'               : vin,
            'unit'              : unit,
            'type_reception_id' : type_reception_id,
            }
        
    settings = ''
    if page == 'settings':
        settings_estimation = RegEstimationsSettings.objects.get(pk = 1)
        units = RefUnit.objects.filter(buauto = True).filter(name__icontains = 'КорсАвто').order_by('name')
        works = RegPodgotovkaWork.objects.all().order_by('name_group', 'name')
        settings = {
            'units'                 : units,
            'works'                 : works,
            'settings_estimation'   : settings_estimation
        }

    params = {
        'type'          : 'korsavto_settings',
        'user'          : request.user,
        'page'          : page,
        'list_dc'       : list_dc,
        'dash'          : dash,
        'dc'            : dc,
        'unit'          : unit,
        'paginator'     : paginator,
        'filtr'         : filtr,
        'selected'      : selected,
        'rating'        : rating,
        'estimations'   : estimations,
        'cars'          : cars,
        'select_units'  : select_units,
        'settings'      : settings,
        'balance_units' : balance_units,
        'balance_unit'  : balance_unit
    }

    return render(request, 'kors/settings_dc.html', {'params':params})  


def korsavto_settings_dc_cars(request, slug):
    
    car = RefCarsOrganization.objects.filter(slug = slug)[0]
    
    selected = {
        'stores'        : RefStore.objects.all().order_by('name'),
        'evaluations'   : RefTypeEvaluationCarsOrganization.objects.all().order_by('name'),
        'stageprices'   : RefStagePrice.objects.all().order_by('name'),
        'groupprices'   : RefGroupPrice.objects.all().order_by('name'),
        'ratings'       : RefRatingCarsOrganization.objects.all().order_by('name'), 
    }

    params = {
        'type'          : 'korsavto_settings',
        'object'        : car,
        'selected'      : selected,
        'unit'          : car.unit
    }
    
    return render(request, "avtosalon/car_new.html", {'params': params})
  

def rating_nps_sale_unit(units, date_start, date_end):
    query_rating_common_count       = DocOprosCarShipment.objects.filter(close = True).filter(canceled = False).filter(shipment__unit__id__in = units).filter(shipment__dataTime__gte = date_start).filter(shipment__dataTime__lte = date_end).count()
    if query_rating_common_count > 0:
        rating_qyeryset_common = DocOprosCarShipment.objects.filter(close = True).filter(canceled = False).filter(shipment__unit__id__in = units).filter(shipment__dataTime__gte = date_start).filter(shipment__dataTime__lte = date_end).aggregate(Sum('v1'), Sum('v2'), Sum('v3'), Sum('v4'))
        rating_sum_common      = rating_qyeryset_common['v1__sum'] + rating_qyeryset_common['v2__sum'] + rating_qyeryset_common['v3__sum'] + rating_qyeryset_common['v4__sum']     
        rating_common          = round(rating_sum_common / query_rating_common_count / 4, 2)
        return rating_common
    return 0


@login_required
def sales_funnel(request):
    
    date_end        = DT.datetime.now() + DT.timedelta(days=-1)
    date_start      = date_end + DT.timedelta(days=-13)
    cars            = RefCarsOrganization.objects.filter(quantity = 0).filter(date_refresh__gte = date_start).filter(stage_price__id = 4)
    sub_qyery               = DocCarAgreement.objects.filter(lo__pk = OuterRef(name='lo__pk'))
    sub_cars_store_mod      = RefCarsOrganization.objects.exclude(quantity = 0).filter(modification_autoru__pk = OuterRef(name='modification_autoru__pk')).annotate(count=Func(F('id'), function='Count')).values('count')
    
    cars    = cars.annotate(
        agreement_cm                    = Subquery(sub_qyery.values('cm_actual')[:1])).annotate(
        agreement_pk                    = Subquery(sub_qyery.values('pk')[:1])).annotate(
        agreement_amount                = Subquery(sub_qyery.values('amount')[:1])).annotate(
        agreement_cost_price            = Subquery(sub_qyery.values('cost_price')[:1])).annotate(
        agreement_kso_actual            = Subquery(sub_qyery.values('kso_actual')[:1])).annotate(
        agreement_bu_wheels_actual      = Subquery(sub_qyery.values('bu_wheels_actual')[:1])).annotate(
        car_modification_store          = Subquery(sub_cars_store_mod)).annotate(
        agreement_type_sale   = Subquery(sub_qyery.values('typeSale')[:1]))
        
    
    objects = cars.filter(agreement_cm__gt = 0)

    params = {
        'type'          : 'korsavto_settings',
        'objects'       : objects[:50]
    }
    
    return render(request, "kors/sales_funnel.html", {'params': params})

@login_required
def kpi_eco(request):
    
    type_receptions = RefTypeReceptionCarsOrganization.objects.all().order_by('name')
        
    name_unit           = request.GET.get('name_unit','')
    type_reception_id   = request.GET.get('type_reception_id','')    
    vin                 = request.GET.get('vin', '')
    
    date_start      = request.GET.get('date_start', '')
    date_end        = request.GET.get('date_end', '')
    
    if date_start == '':
        date_start = DT.datetime.now() - relativedelta(months=2)
        date_start = date_start.replace(day = 1, hour = 0, minute=0, second=0)
    else:
        date_start =  DT.datetime.strptime(date_start, "%Y-%m-%d")
    
    if date_end == '':
        date_end = DT.datetime.now().replace(hour = 23)
    else:
        date_end = DT.datetime.strptime(date_end, "%Y-%m-%d").replace(hour = 23)
    
    selected = {
        'type_receptions'   : type_receptions
    }

    doc_lo      = DocLO.objects.filter(dataTime__gte = date_start).filter(dataTime__lte = date_end)
    interactiv  = RegInteractivOcenka.objects.filter(rlk__pk = OuterRef(name='rlk__pk'))

    data    = doc_lo.annotate(
        interactiv_status           = Subquery(interactiv.values('status__name')[:1])).annotate(
        interactiv_status_order     = Subquery(interactiv.values('status__order')[:1])).annotate(
        interactiv                  = Subquery(interactiv.values('id')[:1])).annotate(
        staff_name                  = Subquery(interactiv.values('staff__name')[:1])).annotate(
        staff_eco                   = Coalesce(Subquery(interactiv.values('staff_eco_2__profiles__eco_name')[:1]), Subquery(interactiv.values('staff_eco_1__profiles__eco_name')[:1])))
    
    statuses = data.values('interactiv_status').annotate(count = Count('interactiv')).order_by('interactiv_status_order')
    statuses_count = statuses.aggregate(Sum('count'))['count__sum']
    dash = {
        'count_estimations' : statuses_count
    }
    filtr = {
            'name_unit'         : name_unit,
            'date_start'        : date_start,
            'date_end'          : date_end 
        }
    params = {
        'type'          : 'korsavto_kpi_eco',
        'filtr'         : filtr,
        'dash'          : dash,
        'statuses'      : statuses,
        'data'          : data[:50]
    }
    
    return render(request, "kors/kpi_eco.html", {'params': params})


def refresh_estimation_balance_unit(id_estimation):
    
    estimations_list    = RegInteractivOcenka.objects.filter(rlk__pk = id_estimation).exclude(year = 0).exclude(end_estimation = None).filter(start_estimation__gt = DT.date(2025, 6, 1)).exclude(modification = None).order_by('-start_estimation')
    docs_lo             = DocLO.objects.filter(rlk__pk = OuterRef(name='rlk__pk'))
    estimations_list    = estimations_list.annotate(
        lo_active               = Subquery(docs_lo.values('active')[:1])).annotate(
        lo_uin                  = Subquery(docs_lo.values('uin')[:1])).annotate(
        lo_agreement_unit_pk    = Subquery(docs_lo.values('agreement_unit__pk')[:1]))
    
    estimations_list = estimations_list.filter(lo_active = True).filter(auction = False).values('pk', 'lo_agreement_unit_pk', 'lo_uin')
    from register.models import RegEstimationBalanceUnit, RegEstimationsSettings, RegEstimationPodgotovka, RegEstimationSS, RegEstimationMCU
    
    for estimation_pk in estimations_list:
        
        estimation  = RegInteractivOcenka.objects.get(pk = estimation_pk['pk']) 
        
        unit        = estimation.rlk.unit
        
        if unit == None:
            unit = estimation.rlk.unit_dc
        
        if estimation.page_documents.type_reception.id == 7 and estimation.rlk.unit != None:
            unit = estimation.rlk.unit
        
        if estimation_pk['lo_agreement_unit_pk'] != None:
            unit = RefUnit.objects.get(pk = estimation_pk['lo_agreement_unit_pk'])

        save            = True
        new_record      = None

        new_record_count = RegEstimationBalanceUnit.objects.filter(estimation = estimation).count() 
        if new_record_count > 0:
            new_record = RegEstimationBalanceUnit.objects.filter(estimation = estimation)[0]
            if new_record.shipment != None:
                save = False
            else:
                new_record = RegEstimationBalanceUnit.objects.filter(estimation = estimation)[0] 

        if save:
            if new_record == None:
                new_record = RegEstimationBalanceUnit()

            new_record.estimation = estimation
        if unit == None:
            unit = estimation.page_documents.unit
        
        if estimation.page_documents.type_reception.id != 3 and estimation.page_documents.type_reception.id != 15:
            save = True
        
        amount = 0
        
        if estimation.page_documents.type_reception.id == 3:
            save = False

        if estimation.page_soglasovanie != None:
            
            reg_interactiv_ocenka_soglasovanie = estimation.page_soglasovanie
            if reg_interactiv_ocenka_soglasovanie.settings == None:
                reg_interactiv_ocenka_soglasovanie.settings = RegEstimationsSettings.objects.get(pk = 1)

            price_autohub   = estimations_price_calculation(estimation, type_calculation='autohub')
            if price_autohub != None:
                reg_interactiv_ocenka_soglasovanie.price_auto_2         = price_autohub['estimation_price']
                reg_interactiv_ocenka_soglasovanie.price_auto_bcp_2     = price_autohub['cna_expenses']
                reg_interactiv_ocenka_soglasovanie.zachita_ot_ubitka    = price_autohub['zachita_ot_ubitka']
                reg_interactiv_ocenka_soglasovanie.finance_price        = price_autohub['finance_price']
                reg_interactiv_ocenka_soglasovanie.price_auto_auction   = price_autohub['auction']
                reg_interactiv_ocenka_soglasovanie.price_zna_2          = price_autohub['zna']
                reg_interactiv_ocenka_soglasovanie.save()
                price_info = price_autohub
            else:
                price_avito   = estimations_price_calculation(estimation, type_calculation='avito')
                if price_avito != None:
                    if price_avito['estimation_price'] > reg_interactiv_ocenka_soglasovanie.price_after_kd:
                        reg_interactiv_ocenka_soglasovanie.price_auto_3         = price_avito['estimation_price']
                        reg_interactiv_ocenka_soglasovanie.price_auto_bcp_3     = price_avito['cna_expenses']
                        reg_interactiv_ocenka_soglasovanie.zachita_ot_ubitka    = price_avito['zachita_ot_ubitka']
                        reg_interactiv_ocenka_soglasovanie.finance_price        = price_avito['finance_price']
                        reg_interactiv_ocenka_soglasovanie.price_auto_auction   = price_avito['auction']
                        reg_interactiv_ocenka_soglasovanie.price_zna_3          = price_avito['zna']
                        reg_interactiv_ocenka_soglasovanie.save()
                        price_info = price_avito

            if reg_interactiv_ocenka_soglasovanie.price_auto_auction == False:
                
                if estimation.page_soglasovanie.price_auto_2 > 0:
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
                    count = RegEstimationBalanceUnit.objects.filter(estimation = estimation).count()
                    if count > 0:
                        new_record = RegEstimationBalanceUnit.objects.filter(estimation = estimation)[0]
                    else:
                        new_record              = RegEstimationBalanceUnit()
                    new_record.unit         = unit
                    new_record.date         = estimation.start_estimation
                    new_record.estimation   = estimation
                    new_record.amount_in    = amount
                    new_record.save()

                    agreement   = None
                    lo          = estimation_pk['lo_uin']
                    agreements_ = DocCarAgreement.objects.filter(lo__uin = lo).filter(active = True)
                    for agreement_ in agreements_:
                        agreement = agreement_
                        cum = agreement.cm_actual 
                    if agreement != None:
                        docs = DocCarShipment.objects.filter(agreement = agreement).count()
                        if docs > 0:
                            doc = DocCarShipment.objects.filter(agreement = agreement)[0] 
                            page_soglasovanie = estimation.page_soglasovanie
                            if page_soglasovanie != None:
                                price_info = None 
                                zna = 0
                                zak = 0
                                if page_soglasovanie.price_zna_2 > 0:
                                    zna = page_soglasovanie.price_zna_2
                                    zak = page_soglasovanie.price_auto_2
                                    price_info = estimations_price_calculation(estimation, 'autohub')
                                else:
                                    zna = page_soglasovanie.price_zna_3 
                                    zak = page_soglasovanie.price_auto_3
                                    price_info = estimations_price_calculation(estimation, 'avito')

                                if zna > 0:
                                    car_organizations = RefCarsOrganization.objects.filter(lo__rlk = estimation.rlk) 
                                    if len(car_organizations) == 1:
                                        
                                        car_organization    = car_organizations[0]
                                        unit                = car_organization.unit
                                        stage               = car_organization.stage_price
                                        zg                  = car_organization.group_price
                                        kf                  = 100
                                        
                                        if zg.name == '200':
                                            if stage.pk == 1:
                                                kf = unit.ratio_avtohub_txt_200
                                            elif stage.pk == 2:
                                                kf = unit.ratio_avtohub_rdo_200
                                            elif stage.pk == 3:
                                                kf = unit.ratio_avtohub_kor_200
                                            elif stage.pk == 4:
                                                kf = unit.ratio_avtohub_test_price_200
                                        elif zg.name == '400':
                                            if stage.pk == 1:
                                                kf = unit.ratio_avtohub_txt_400
                                            elif stage.pk == 2:
                                                kf = unit.ratio_avtohub_rdo_400
                                            elif stage.pk == 3:
                                                kf = unit.ratio_avtohub_kor_400
                                            elif stage.pk == 4:
                                                kf = unit.ratio_avtohub_test_price_400   
                                        elif zg.name == '700':
                                            if stage.pk == 1:
                                                kf = unit.ratio_avtohub_txt_700
                                            elif stage.pk == 2:
                                                kf = unit.ratio_avtohub_rdo_700
                                            elif stage.pk == 3:
                                                kf = unit.ratio_avtohub_kor_700
                                            elif stage.pk == 4:
                                                kf = unit.ratio_avtohub_test_price_700 
                                        elif zg.name == '1200' or zg.name == '1 200':
                                            if stage.pk == 1:
                                                kf = unit.ratio_avtohub_txt_1200
                                            elif stage.pk == 2:
                                                kf = unit.ratio_avtohub_rdo_1200
                                            elif stage.pk == 3:
                                                kf = unit.ratio_avtohub_kor_1200
                                            elif stage.pk == 4:
                                                kf = unit.ratio_avtohub_test_price_1200
                                        elif zg.name == '2000' or zg.name == '2 000':
                                            if stage.pk == 1:
                                                kf = unit.ratio_avtohub_txt_2000
                                            elif stage.pk == 2:
                                                kf = unit.ratio_avtohub_rdo_2000
                                            elif stage.pk == 3:
                                                kf = unit.ratio_avtohub_kor_2000
                                            elif stage.pk == 4:
                                                kf = unit.ratio_avtohub_test_price_2000 
                                        elif zg.name == '3000' or zg.name == '3 000' or zg.name == '3 001+':
                                            if stage.pk == 1:
                                                kf = unit.ratio_avtohub_txt_3000
                                            elif stage.pk == 2:
                                                kf = unit.ratio_avtohub_rdo_3000
                                            elif stage.pk == 3:
                                                kf = unit.ratio_avtohub_kor_3000
                                            elif stage.pk == 4:
                                                kf = unit.ratio_avtohub_test_price_3000
                                        elif zg.name == '5000' or zg.name == '5 000':
                                            if stage.pk == 1:
                                                kf = unit.ratio_avtohub_txt_5000
                                            elif stage.pk == 2:
                                                kf = unit.ratio_avtohub_rdo_5000
                                            elif stage.pk == 3:
                                                kf = unit.ratio_avtohub_kor_5000
                                            elif stage.pk == 4:
                                                kf = unit.ratio_avtohub_test_price_5000
                                        elif zg.name == '5 000' or zg.name == '5 000+':
                                            if stage.pk == 1:
                                                kf = unit.ratio_avtohub_txt_5001
                                            elif stage.pk == 2:
                                                kf = unit.ratio_avtohub_rdo_5001
                                            elif stage.pk == 3:
                                                kf = unit.ratio_avtohub_kor_5001
                                            elif stage.pk == 4:
                                                kf = unit.ratio_avtohub_test_price_5001

                                        if estimation != None:
                                            
                                            new_record_count = RegEstimationBalanceUnit.objects.filter(estimation = estimation).count()     
                                            if new_record_count > 0:
                                                new_record = RegEstimationBalanceUnit.objects.filter(estimation = estimation)[0] 
                                                
                                                fin_prim = price_info['finance_price']
                                                
                                                kso_fact        = agreement.kso_actual
                                                bu_wheels_fact  = agreement.bu_wheels_actual
                                                
                                                fin_fact = round(estimation.page_soglasovanie.price_after_kd * 0.25 /365 * car_organization.days_in_stok)
                                                zak     = zak
                                                zak_new = zak + price_info['iznos_price'] + price_info['amount_sum']  
                                                
                                                if doc.typeSale != 'Аукцион':
                                                    vr_int      = price_info['amount_sum'] 
                                                    var_sum     = vr_int - agreement.outlay
                                                    #iznos       = price_info['iznos_price']
                                                    t           = zna - (zna - zna * kf / 100) - (zak + var_sum  + fin_prim - fin_fact) 
                                                    val_itog    = cum - (t + kso_fact + bu_wheels_fact)

                                                    kso         = ", КСО: " + str(kso_fact)
                                                    wheels      = ", БУРезина: " + str(bu_wheels_fact)
                                                    #iznos   = ", Износ: " + str(price_info['iznos_price']) 
                                                    vr      = ", ВР: " + str(price_info['amount_sum']) 
                                                    fin_r   = ", Финансирование расчетное: " + str(price_info['finance_price']) 
                                                    fin_f   = ", Финансирование факт: " + str(fin_fact) 
                                                    day_f   = ", Дней на складе: " + str(car_organization.days_in_stok) 
                                                    new_record.shipment     = doc
                                                    new_record.amount_out   = val_itog
                                                    new_record.comment_2    = "ЦГ:" + str(zg) + ', Этап продажи: ' + str(stage) + ', ИРЦ: ' + str(kf) + ', ЦНА: ' + str(zna) + ', РекЦенаЗакупки: ' + str(zak) + vr + fin_r + fin_f + day_f +  kso +  wheels +  ', КМ: ' + str(cum)
                                                    new_record.save()                                
                else:
                    count = RegEstimationBalanceUnit.objects.filter(estimation = estimation).count()
                    if count > 0:
                        new_record = RegEstimationBalanceUnit.objects.filter(estimation = estimation)[0]  
                        if new_record.shipment == None:
                            new_record.delete()
            else:
                count = RegEstimationBalanceUnit.objects.filter(estimation = estimation).count()
                if count > 0:
                    new_record = RegEstimationBalanceUnit.objects.filter(estimation = estimation)[0]  
                    if new_record.shipment == None:
                        new_record.delete()    

def refresh_balance_unit_car_shipment(car_shipment_id):
    car_shipment = DocCarShipment.objects.get(id = car_shipment_id)
    if car_shipment.lo != None:
        rlk = car_shipment.lo.rlk
        if rlk != None:
            count_estimations = RegInteractivOcenka.objects.filter(rlk = rlk).count()
            if count_estimations == 1:
                refresh_estimation_balance_unit(rlk.id)

@login_required
def auction_list(request):
    
    select_count = 10
    
    user = request.user

    if user.is_superuser:
        select_stores =  RefStore.objects.all()
    else:
        select_stores =  user.profiles.korsavto_stores.all()
    
    objects     = Auction.objects.all().order_by('dataTime')
    page_number = request.GET.get('page', 0)
    
    subquery_1 = AuctionStructure.objects.filter(auction__id=OuterRef('pk')).values('auction__id').annotate(count=Count('pk')).values('count')
    
    objects    = objects.annotate(
        count_cars  = Subquery(subquery_1))
    
    amount      = objects.aggregate(Sum('start_price'))['start_price__sum']
    count_cars  = objects.aggregate(Sum('count_cars'))['count_cars__sum']
        
    paginator   = Paginator(list(objects), select_count)
    paginator   = paginator.get_page(page_number)

    select = {
        'stores' : select_stores
    }
    params = {
        'type'          : 'auction',
        'paginator'     : paginator,
        'amount'        : amount,
        'count_cars'    : count_cars,
        'count'         : objects.count(),
        'select'        : select
    }
    
    return render(request, "auction/auction_list.html", {'params': params})

@login_required
def auction_doc(request, slug_auction):
    auction = None
    new = False
    if slug_auction == 'new_lots':
        new = True
    else:
        new = False
        auction = Auction.objects.get(uid = slug_auction)

    user = request.user

    if user.is_superuser:
        select_stores =  RefStore.objects.filter(active_eco = True)
    else:
        select_stores =  user.profiles.korsavto_stores.all()
    
    select = {
        'stores' : select_stores
    }

    if request.method == 'POST':
        if new:
            auction = Auction()
            auction.user = user
        else:
            auction = Auction.objects.get(uid = slug_auction)
        auction.user                = user
        auction.store               = RefStore.objects.get(name = request.POST.get('store', ''))
        auction.start_price         = int(request.POST.get('price_start', '0')) 
        auction.dateStart           = DT.datetime.strptime(request.POST.get('dateStart', ''), "%Y-%m-%dT%H:%M")
        auction.description         = request.POST.get('description', '')        
        auction.save()

        AuctionStructure.objects.filter(auction = auction).delete()

        for key in request.POST.keys():
            if key.startswith('cars_list_data_slug_'):
                val_key = request.POST.get(key)
                pk      = key.replace('cars_list_data_slug_', '')
                car     = RefCarsOrganization.objects.get(slug = pk)
                structure = AuctionStructure()
                structure.auction = auction
                structure.car = car
                structure.save()

        if 'send' in request.POST:
            send_auction(auction)
        return HttpResponseRedirect(request.build_absolute_uri().replace('new_lots', str(auction.uid)))
     
    params = {
        'type'          : 'auction',
        'auction'       : auction,
        'new'           : new,
        'user'          : user,
        'select'        : select
    }
    
    return render(request, "auction/auction_doc.html", {'params': params})

def auction_doc_get_cars(request):

    search = request.GET.get('search', '')

    if len(search) > 0:
        cars = RefCarsOrganization.objects.filter(search_fields__icontains = search)
    else:    
        cars = RefCarsOrganization.objects.exclude(quantity = 0)[:10]
    
    data = list(cars.values('vin', 
                       'slug', 
                       'year',
                       'price',
                       'run', 
                       modification_name = F('modification_autoru__name'),
                       model_name   = F('modification_autoru__model__name'),
                       mark_name    = F('modification_autoru__model__mark__name'),
                       url          = F('prev_photo')))
    for car in data:
        car['url'] = get_url_image(car['slug'])
    
    return JsonResponse(data, safe=False, status=status.HTTP_200_OK)

def auction_doc_get_cars_info(request, slug):
    
    cars        = RefCarsOrganization.objects.filter(slug = slug)
    subquery    = RegInteractivOcenka.objects.filter(rlk__id = OuterRef(name='lo__rlk__id'))
    cars    = cars.annotate(
        int_ocenka_id           = Subquery(subquery.values('id')[:1])).annotate(
        int_ocenka_diagnostika = Subquery(subquery.values('page_soglasovanie__comment_diagnostica')[:1])).annotate(
        int_ocenka_url_pered = Value('', output_field=CharField())).annotate(
        int_ocenka_url_zad = Value('', output_field=CharField())).annotate(
        int_ocenka_url_up = Value('', output_field=CharField())).annotate(
        int_ocenka_url_right = Value('', output_field=CharField())).annotate(
        int_ocenka_url_left = Value('', output_field=CharField()))
    
    
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
                       'int_ocenka_id',
                       'int_ocenka_url_pered',
                       'int_ocenka_url_zad',
                       'int_ocenka_url_up',
                       'int_ocenka_url_right',
                       'int_ocenka_url_left',
                       type_sale_name = F('type_sale__name'),
                       type_reception_name = F('type_reception__name'),
                       stage_price_name = F('stage_price__name'),
                       status_name = F('status__name'),
                       modification_name = F('modification_autoru__name'),
                       model_name   = F('modification_autoru__model__name'),
                       mark_name    = F('modification_autoru__model__mark__name'),
                       url          = F('prev_photo')))
    for car in data:
        car['url'] = get_url_images(car['slug'])
        car['int_ocenka_url_pered'] = get_url_image_osmotr(car['int_ocenka_id'], 'vnesh_car_osmotr_pered')
        car['int_ocenka_url_zad']   = get_url_image_osmotr(car['int_ocenka_id'], 'vnesh_car_osmotr_zad')
        car['int_ocenka_url_up']    = get_url_image_osmotr(car['int_ocenka_id'], 'vnesh_car_osmotr_up')
        car['int_ocenka_url_right'] = get_url_image_osmotr(car['int_ocenka_id'], 'vnesh_car_osmotr_pass')
        car['int_ocenka_url_left']  = get_url_image_osmotr(car['int_ocenka_id'], 'vnesh_car_osmotr_vod')
    
    return JsonResponse(data, safe=False, status=status.HTTP_200_OK)

def get_url_image_osmotr(estimation_id, type_file):
    photos_count = RegRegInteractivOcenkaFiles.objects.filter(estimation__id = estimation_id).filter(type_file = type_file).count()
    try:
        if photos_count > 0:
            return RegRegInteractivOcenkaFiles.objects.filter(estimation__id = estimation_id).filter(type_file = type_file)[0].file.url.replace('/media/','/media_dop/')
    except:
        return '/media/nophoto.png'
    return '/media/nophoto.png'

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


def test(request):
    
    hour_start_day  = 9
    hour_end_day    = 20

    estimations = RegInteractivOcenka.objects.filter(rlk__pk = 2314324).exclude(start_estimation__lte = DT.date(2025, 6, 1)).order_by('-start_estimation')
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
    


    
    '''
    date_start = DT.datetime.now()
    date_start = date_start.replace(year=2025, month=9, day = 16, hour = 0, minute=0, second=0, microsecond=0)
    list_checklist_cvc = Records_voice_recorder_cvc_checklist.objects.filter(success = True).filter(rlk__dataTime__gte = date_start)
    for s in list_checklist_cvc:
        s.success = False
        s.save()
    '''

    #object_estimations = RegInteractivOcenka.objects.filter(status__pk = 8).exclude(start_estimation__lte = DT.date(2025, 6, 1)).order_by('-start_estimation')
    #refresh_estimation_cars_organization()
    
    '''
    object_estimations = RegInteractivOcenka.objects.filter(status__pk = 8).exclude(start_estimation__lte = DT.date(2025, 6, 1)).order_by('-start_estimation')
    s = 0
    count = object_estimations.count()
    object_estimations = object_estimations.values('rlk__pk')
    for object_estimation in object_estimations:
        refresh_estimation_balance_unit(object_estimation['rlk__pk'])     
        s = s + 1
        print(str(s) + '/' + str(count))
    '''

    return render(request, "website/test.html")