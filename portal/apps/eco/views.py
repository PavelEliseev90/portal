from tkinter.tix import Tree
from django.shortcuts import redirect, render
from register.models import RegEstimationsCalculationDetail, RegEstimationPodgotovka, RegEstimationSS, RegEstimationMCU, RegSwapKors, RegPodgotovkaWork, RegInfoBody, RegEstimationsSettings, RegRegInteractivOcenkaTaskFiles, RegInteractivOcenkaTask, RegInteractivOcenkaHistoryOpens, RegInteractivOcenkaEmailPush, RegInteractivOcenkaSoglasovanie, RegInteractivOcenkaProverki, RegInteractivOcenkaKolesa, RegInteractivOcenkaTestDrive, RegInteractivOcenkaComplectnost, RegInteractivOcenkaVnesh, RegDashboardError, RegInteractivOcenka, RegInteractivOcenkaDocument, RegRegInteractivOcenkaFiles, RegInteractivOcenkaSalon
from django.core.paginator import Paginator
from refs.models import RefCarsOrganization, RefCustomerFiltr, RefStatusEstimation, RefTypeDisk, RefMarkTyres, RefWidthTyres, RefProfileTyres, RefRadius, RefSezonTyres, RefEtDisk, RefDiaDisk, RefPsdDisk, RefStatusOcenka, RefUnit, RefStaff, RefTypeReceptionCarsOrganization
from profiles.models import Profiles
from documents.models import DocCarAgreement, DocRLK, DocZN, DocLO
from task_manager.views import send_message_socket, get_info_max, kors_estimation_data
import json
from checklists.models import CheckListTradeIn
from chats.models import Chat, ChatMessage
from django.db.models import Count, Sum, Max, Avg, F, OuterRef, Subquery, Sum, Q, Value, IntegerField
from django.db import models
import datetime as DT
from django.http import Http404, HttpResponseRedirect, HttpResponseNotFound, HttpResponse
from django.contrib.auth.models import User, Group
from django.db.models.functions import Cast, Coalesce


import re
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.conf import settings

from django.http.response import JsonResponse
from rest_framework import status

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from django.views.decorators.csrf import csrf_exempt
from changelog.models import ChangeLog


def add_swap(estimation):
    try:        
        swap                = RegSwapKors()
        swap.estimation     = estimation
        swap.save()        
    except:
        s = 1


def send_web_socket_message(group, chat, user, text, estimation_id):
    
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
            'estimation_id' : estimation_id
        }    
    
    send_message_socket(message = message_json)


def add_log_history_open(estimation, user, page):
    
    page_title = 'Главная'
    
    if page == 1:
        page_title = 'Документы'
    elif page == 2:
        page_title = 'Салон'
    elif page == 3:
        page_title = 'Внешний осмотр'
    elif page == 11:
        page_title = 'Дистанционная оценка'
    elif page == 4:
        page_title = 'Комплектность'
    elif page == 5:
        page_title = 'Колеса'
    elif page == 6:
        page_title = 'Тест - драйв'
    elif page == 7:
        page_title = 'Проверки'
    elif page == 8:
        page_title = 'История оценок'
    elif page == 13:
        page_title = 'История ремонтов'
    elif page == 9:
        page_title = 'Согласование'
    elif page == 17:
        page_title = 'Все фото осмотра'
    elif page == 18:
        page_title = 'История просмотров'
    elif page == 20:
        page_title = 'Ценообразование админ'
    elif page == 21:
        page_title = 'Ценообразование'
    elif page == 22:
        page_title = 'История изменений'
    elif page == 403:
        page_title = 'Отказано в доступе'
    elif page == 301:
        page_title = 'Не авторизованный пользователь'

    new_info                = RegInteractivOcenkaHistoryOpens()
    new_info.staff          = user
    new_info.estimation     = estimation
    new_info.page_title     = page_title
    new_info.page           = page
    new_info.save() 


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


def eco_monitors(request):
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    if not request.user.profiles.eco and not request.user.profiles.eco_visible:
        params = {
        'type'          : 'eco',
        'nav_selected'  : 4,
        'request'       : request,
        }
        return render(request, 'errors/403.html', {'params': params})
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    if not request.user.profiles.eco and not request.user.profiles.eco_visible:
        params = {
        'type'          : 'eco',
        'nav_selected'  : 4,
        'request'       : request,
        }
        return render(request, 'errors/403.html', {'params': params})
    
    new_filtr       = request.GET.get('new_filtr', '')
    path_start      = request.path
    delite_filter   = request.GET.get('delite_filter', '')
    
    if len(delite_filter) > 0:
        if RefCustomerFiltr.objects.filter(pk = delite_filter).count() > 0:
            RefCustomerFiltr.objects.get(pk = delite_filter).delete()

    date                = request.GET.get('date_start', '')
    date_e              = request.GET.get('date_end', '')
    
    date_period = DT.datetime.now()
    date_start 	= date_period.replace(hour = 0, minute=0, second=0, microsecond=0)
    date_end    = date_period.replace(hour = 23, minute=59, second=59, microsecond=0)
    
    if date != '':
        dates = date.split('-')
        if len(dates) == 3:
            year 	        = int(dates[0])
            month 	        = int(dates[1])
            day             = int(dates[2])
            date_period     = DT.datetime.now()
            date_start 	    = date_period.replace(year = year, month = month, day = day, hour = 0, minute=0, second=0, microsecond=0)
            
    if date_e != '':
        dates = date_e.split('-')
        if len(dates) == 3:
            year 	        = int(dates[0])
            month 	        = int(dates[1])
            day             = int(dates[2])
            date_period     = DT.datetime.now()
            date_end 	    = date_period.replace(year = year, month = month, day = day, hour = 0, minute=0, second=0, microsecond=0)
            
    countList = 15

    staffKKID   = ""
    staffsKK    = Profiles.objects.filter(view_checklist = False).order_by('user__last_name')
			
    unit_id      = ""
    units_select = RefUnit.objects.filter(buauto = True).filter(active_eco = True).exclude(name = '').order_by("name")
    
    type_receptions_id = request.GET.get('type_receptions_id', '')

    staffID         = ""
    staffsSelect    = ""
    
    docs        = DocRLK.objects.filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(type__id = 7).filter(eco = True).order_by('-dataTime')
    subquery    = RegInteractivOcenka.objects.filter(rlk__id = OuterRef(name='id'))
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
        count_data = Value(1, output_field=IntegerField())
        )

    filtr_number_doc = request.GET.get('number_doc', '')
    
    data        = docs.order_by('type_estimation_ocenka').values('type_estimation_ocenka').distinct().annotate(Sum('count_data')).exclude(type_estimation_ocenka = None)
    data_unit   = docs.order_by('unit_name').values('unit_name').distinct().annotate(Sum('count_data')).exclude(unit_name = None)
    
    count_new               = docs.filter(status_estimation_id = 1).count()
    count_estimations       = docs.filter(status_estimation_id = 2).count()
    count_soglasovanie      = docs.filter(status_estimation_id = 3).count()
    count_ok                = docs.filter(status_estimation_id = 4).count()
    count_kd                = docs.filter(status_estimation_id = 5).count()
    count_soglasovanie_kd   = docs.filter(status_estimation_id = 6).count()
    count_8                 = docs.filter(status_estimation_id = 8).count()

    count_6 = count_ok
    count_5 = count_soglasovanie_kd + count_6
    count_4 = count_kd + count_5 
    count_3 = count_soglasovanie + count_4
    count_2 = count_estimations + count_3 
    count_1 = count_new + count_estimations + count_soglasovanie + count_ok + count_kd + count_soglasovanie_kd + count_8
    
    count_1_detail = docs.filter(status_estimation_id = 1) 
    count_2_detail = docs.filter(status_estimation_id = 2) 

    if filtr_number_doc != '':
        docs = docs.filter(nomer__icontains = filtr_number_doc)    
    if type_receptions_id != '':
        type_receptions_id = int(type_receptions_id)
        docs = docs.filter(type_estimation_ocenka_id = type_receptions_id)    
    
        
    status_id = request.GET.get('status_id', '')
    if status_id != '':
        status_id = int(status_id)
        docs = docs.filter(status_estimation_id = status_id)
    else:
        docs = docs.exclude(status_estimation_id = 0)
 
    if request.GET.get('unit_id', '') != '':
        unit_id         = int(request.GET['unit_id'])
        docs            = docs.filter(unit__id = unit_id) | docs.filter(unit_dc__id = unit_id) | docs.filter(unit_name_dc = unit_id) 
        #staffsSelect    = list(RefStaff.objects.filter(unit = RefUnit.objects.get(id = unit_id)).order_by('name'))
   
    filtr = {
        'date_start'    : date_start,
        'date_end'      : date_end,
    }

    params = {
        'type'          : 'eco_monitors',
        'nav_selected'  : 4,
        'request'       : request,
        'filtr'         : filtr,
        'count_new'     : count_new,
        'count_estimations'     : count_estimations,
        'count_soglasovanie'    : count_soglasovanie,
        'count_ok'              : count_ok,
        'count_kd'              : count_kd,
        'count_soglasovanie_kd' : count_soglasovanie_kd,
        'count_1'   : count_1,
        'count_2'   : count_2,
        'count_3'   : count_3,
        'count_4'   : count_4,
        'count_5'   : count_5,
        'count_6'   : count_6,
        'count_8'   : count_8,
        'count_1_detail'    : count_1_detail,
        'count_2_detail'    : count_2_detail,
        'data_unit'         : data_unit,
        'data'              : data
    }

    return render(request, 'lo/eco_monitors.html', {'params': params})


@csrf_exempt
def post_chats_list(request):
    
    body_unicode    = request.body.decode()
    data            = json.loads(body_unicode)

    channel_layer = get_channel_layer()
    message_json = json.dumps(data['message'])
    
    async_to_sync(channel_layer.group_send)(
        'chat_rlk_list_eco',
        {'type'     : 'channel_message',
         'message'  : message_json}
    )

    return JsonResponse(body_unicode, safe=False, status=status.HTTP_200_OK)


def get_chats_list(request):
    
    chats                   = Chat.objects.all()
    subqyery_reg_interactiv = RegInteractivOcenka.objects.filter(rlk = OuterRef(name = 'rlk_id'))
    subqyery_message_rlk    = DocRLK.objects.filter(id = OuterRef(name = 'rlk_id'))
    subqyery_message_info   = ChatMessage.objects.filter(chat_id = OuterRef(name = 'id')).filter(date = OuterRef(name = 'max_date'))
    subqyery_message        = Subquery(ChatMessage.objects.filter(chat__id = OuterRef(name = 'id')).annotate(max_date = Max('date')).order_by('-max_date').values('max_date')[:1])
    chats = chats.annotate(max_date = subqyery_message)
    chats = chats.order_by('-max_date')
    chats = chats.exclude(max_date = None)
    chats = chats.annotate(rlk = Subquery(subqyery_message_rlk.values('pk')[:1])) 
    chats = chats.annotate(
        rlk_unit = Subquery(subqyery_message_rlk.values('unit__name')[:1])).annotate(
        rlk_unit_dc = Subquery(subqyery_message_rlk.values('unit_dc__name')[:1])).annotate(
        vin = Subquery(subqyery_reg_interactiv.values('vin')[:1])).annotate(
        mark = Subquery(subqyery_reg_interactiv.values('modification__model__mark__name')[:1])).annotate(
        model = Subquery(subqyery_reg_interactiv.values('modification__model__name')[:1])).annotate(
        modification = Subquery(subqyery_reg_interactiv.values('modification__name')[:1])).annotate(
        staff_name = Subquery(subqyery_message_rlk.values('staff__name')[:1])).annotate(
        content = Subquery(subqyery_message_info.values('content')[:1])).annotate(
        user_content = Subquery(subqyery_message_info.values('user')[:1]))
    
    return JsonResponse(list(chats.values()), safe=False, status=status.HTTP_200_OK)


def text_to_dict(text_json):
    text_json_replace = text_json.replace("/sdcard",'')
    data = json.loads(text_json_replace)
    return data


def get_chats_list_online_info(request, id):
    
    chats                   = Chat.objects.filter(slug = id)
    subqyery_reg_interactiv = RegInteractivOcenka.objects.filter(rlk = OuterRef(name = 'rlk_id'))
    subqyery_message_rlk    = DocRLK.objects.filter(id = OuterRef(name = 'rlk_id'))
    subqyery_message_info   = ChatMessage.objects.filter(chat_id = OuterRef(name = 'id')).filter(date = OuterRef(name = 'max_date'))
    subqyery_message        = Subquery(ChatMessage.objects.filter(chat__id = OuterRef(name = 'id')).annotate(max_date = Max('date')).order_by('-max_date').values('max_date')[:1])
    chats = chats.annotate(max_date = subqyery_message)
    chats = chats.order_by('-max_date')
    chats = chats.exclude(max_date = None)
    
        
    chats = chats.annotate(
        type_estimation_ocenka = Subquery(subqyery_reg_interactiv.values('page_documents__type_reception__name')[:1])).annotate(
        car_year                = Subquery(subqyery_reg_interactiv.values('year')[:1])).annotate( 
        car_prev_img            = Subquery(subqyery_reg_interactiv.values('prev_img')[:1])).annotate( 
        car_run                 = Subquery(subqyery_reg_interactiv.values('page_salon__run')[:1])).annotate(    
        unit_name               = Subquery(subqyery_reg_interactiv.values('page_documents__unit__name')[:1])).annotate(
        unit_name_dc            = Subquery(subqyery_reg_interactiv.values('page_documents__unit__id')[:1])).annotate(
        status_estimation       = Subquery(subqyery_reg_interactiv.values('status__name')[:1])).annotate(
        status_estimation_id    = Subquery(subqyery_reg_interactiv.values('status__id')[:1])).annotate(
        start_estimation        = Subquery(subqyery_reg_interactiv.values('start_estimation')[:1])).annotate(
        end_estimation          = Subquery(subqyery_reg_interactiv.values('end_estimation')[:1])).annotate(
        staff_estimation_name   = Subquery(subqyery_reg_interactiv.values('staff__name')[:1])).annotate(
        staff_estimation        = Subquery(subqyery_reg_interactiv.values('staff')[:1])).annotate(            
        soglasovanie_price_reception = Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_reception')[:1])).annotate(                       
        car_price_before_kd = Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_before_kd')[:1])).annotate(                       
        car_price_after_kd  = Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_after_kd')[:1])).annotate(                       
        car_price_reception = Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_reception')[:1])).annotate(                       
        car_price_sale      = Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_sale')[:1])).annotate(                       
        car_price_bcp       = Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_bcp')[:1])).annotate(                       
        rlk_date = Subquery(subqyery_message_rlk.values('dataTime')[:1])).annotate(    
        rlk_number = Subquery(subqyery_message_rlk.values('nomer')[:1])).annotate(    
        rlk_unit = Subquery(subqyery_message_rlk.values('unit__name')[:1])).annotate(
        rlk_unit_dc = Subquery(subqyery_message_rlk.values('unit_dc__name')[:1])).annotate(
        vin = Subquery(subqyery_reg_interactiv.values('vin')[:1])).annotate(
        mark = Subquery(subqyery_reg_interactiv.values('modification__model__mark__name')[:1])).annotate(
        model = Subquery(subqyery_reg_interactiv.values('modification__model__name')[:1])).annotate(
        modification = Subquery(subqyery_reg_interactiv.values('modification__name')[:1])).annotate(
        staff_name = Subquery(subqyery_message_rlk.values('staff__name')[:1])).annotate(
        content = Subquery(subqyery_message_info.values('content')[:1])).annotate(
        user_name = Subquery(subqyery_message_info.values('user__profiles__eco_name')[:1])).annotate(
        user_content = Subquery(subqyery_message_info.values('user')[:1])).annotate(
        eco         = Subquery(subqyery_message_info.values('user__profiles__eco')[:1]))
    
    chats = chats.filter(status_estimation_id__gte = 2)
    chats = chats.annotate(rlk = Subquery(subqyery_message_rlk.values('pk')[:1]))[:1] 

    return JsonResponse(list(chats.values()), safe=False, status=status.HTTP_200_OK)


def get_chats_list_online(request):
    
    filtr_search                = request.GET.get('search', '')
    filtr_vin                   = request.GET.get('vin', '')
    page                        = int(request.GET.get('page', '1')) - 1

    
    chats                   = Chat.objects.all()
    subqyery_reg_interactiv = RegInteractivOcenka.objects.filter(rlk = OuterRef(name = 'rlk_id'))
    subqyery_message_rlk    = DocRLK.objects.filter(id = OuterRef(name = 'rlk_id'))
    subqyery_message_info   = ChatMessage.objects.filter(chat_id = OuterRef(name = 'id')).filter(date = OuterRef(name = 'max_date'))
    subqyery_message        = Subquery(ChatMessage.objects.filter(chat__id = OuterRef(name = 'id')).annotate(max_date = Max('date')).order_by('-max_date').values('max_date')[:1])
    chats = chats.annotate(max_date = subqyery_message)
    chats = chats.order_by('-max_date')
    chats = chats.exclude(max_date = None)
    
        
    chats = chats.annotate(
        type_estimation_ocenka = Coalesce(Subquery(subqyery_reg_interactiv.values('page_documents__type_reception__name')[:1]), Subquery(subqyery_reg_interactiv.values('page_remote__type_reception__name')[:1]))).annotate(
        car_year                = Subquery(subqyery_reg_interactiv.values('year')[:1])).annotate( 
        car_prev_img            = Subquery(subqyery_reg_interactiv.values('prev_img')[:1])).annotate( 
        car_run                 = Coalesce(Subquery(subqyery_reg_interactiv.values('page_salon__run')[:1]), Subquery(subqyery_reg_interactiv.values('page_remote__run')[:1]))).annotate(    
        unit_name               = Coalesce(Subquery(subqyery_reg_interactiv.values('page_documents__unit__name')[:1]), Subquery(subqyery_reg_interactiv.values('page_remote__unit__name')[:1]))).annotate(
        unit_name_dc            = Coalesce(Subquery(subqyery_reg_interactiv.values('page_documents__unit__id')[:1]), Subquery(subqyery_reg_interactiv.values('page_remote__unit__id')[:1]))).annotate(
        status_estimation       = Subquery(subqyery_reg_interactiv.values('status__name')[:1])).annotate(
        status_estimation_id    = Subquery(subqyery_reg_interactiv.values('status__id')[:1])).annotate(
        start_estimation        = Subquery(subqyery_reg_interactiv.values('start_estimation')[:1])).annotate(
        end_estimation          = Subquery(subqyery_reg_interactiv.values('end_estimation')[:1])).annotate(
        staff_estimation_name   = Subquery(subqyery_reg_interactiv.values('staff__name')[:1])).annotate(
        staff_estimation        = Subquery(subqyery_reg_interactiv.values('staff')[:1])).annotate(            
        soglasovanie_price_reception = Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_reception')[:1])).annotate(                       
        car_price_before_kd         = Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_before_kd')[:1])).annotate(                       
        car_price_after_kd          = Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_after_kd')[:1])).annotate(                       
        car_price_reception         = Coalesce(Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_reception')[:1]), Subquery(subqyery_reg_interactiv.values('page_remote__price_reception')[:1]))).annotate(                       
        car_price_sale              = Coalesce(Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_sale')[:1]), Subquery(subqyery_reg_interactiv.values('page_remote__price_sale')[:1]))).annotate(                       
        car_price_bcp               = Subquery(subqyery_reg_interactiv.values('page_soglasovanie__price_bcp')[:1])).annotate(                       
        rlk_date                    = Subquery(subqyery_message_rlk.values('dataTime')[:1])).annotate(    
        rlk_number                  = Subquery(subqyery_message_rlk.values('nomer')[:1])).annotate(    
        rlk_unit                    = Subquery(subqyery_message_rlk.values('unit__name')[:1])).annotate(
        rlk_unit_dc                 = Subquery(subqyery_message_rlk.values('unit_dc__name')[:1])).annotate(
        vin                         = Subquery(subqyery_reg_interactiv.values('vin')[:1])).annotate(
        mark                        = Subquery(subqyery_reg_interactiv.values('modification__model__mark__name')[:1])).annotate(
        model                       = Subquery(subqyery_reg_interactiv.values('modification__model__name')[:1])).annotate(
        modification                = Subquery(subqyery_reg_interactiv.values('modification__name')[:1])).annotate(
        staff_name                  = Coalesce(Subquery(subqyery_message_rlk.values('staff__name')[:1]), Subquery(subqyery_reg_interactiv.values('staff__name')[:1]))).annotate(
        content                     = Subquery(subqyery_message_info.values('content')[:1])).annotate(
        user_name                   = Subquery(subqyery_message_info.values('user__profiles__eco_name')[:1])).annotate(
        user_content                = Subquery(subqyery_message_info.values('user')[:1])).annotate(
        eco                         = Subquery(subqyery_message_info.values('user__profiles__eco')[:1])).annotate(
        auction                     = Subquery(subqyery_reg_interactiv.values('auction')[:1]))
    
    chats = chats.filter(status_estimation_id__gte = 2)
    
    if filtr_vin != '':
        chats = chats.filter(vin__icontains = filtr_vin)

    if filtr_search != '':
        chats = chats.filter(mark__icontains = filtr_search) | chats.filter(model__icontains = filtr_search) | chats.filter(modification__icontains = filtr_search)
    
    start   = 0 + (30 * page)
    end     = 30 + (30 * page)

    chats = chats.annotate(rlk = Subquery(subqyery_message_rlk.values('pk')[:1]))[start:end] 

    return JsonResponse(list(chats.values()), safe=False, status=status.HTTP_200_OK)


def list_eco_online(request):
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    if not request.user.profiles.eco and not request.user.profiles.eco_visible:
        params = {
        'type'          : 'eco',
        'nav_selected'  : 4,
        'request'       : request,
        }
        return render(request, 'errors/403.html', {'params': params})
    
    params = {
        'type'          : 'eco',
        'nav_selected'  : 4
    }

    return render(request, 'lo/lo_list_online.html', {'params': params})


def list_eco(request):
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    if not request.user.profiles.eco and not request.user.profiles.eco_visible:
        params = {
        'type'          : 'eco',
        'nav_selected'  : 4,
        'request'       : request,
        }
        return render(request, 'errors/403.html', {'params': params})
    
    new_filtr       = request.GET.get('new_filtr', '')
    path_start      = request.path
    delite_filter   = request.GET.get('delite_filter', '')
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
    units_select = RefUnit.objects.filter(buauto = True).filter(active_eco = True).exclude(name = '').order_by("name")
    
    type_receptions_id = request.GET.get('type_receptions_id', '')

    staffID         = ""
    staffsSelect    = ""
    
    docs        = DocRLK.objects.filter(dataTime__gte = date_start).filter(eco = True).order_by('-dataTime')
    subquery    = RegInteractivOcenka.objects.filter(rlk__id = OuterRef(name='id'))
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
        lo_pk = Subquery(subquery.values('id')[:1]))

    filtr_number_doc = request.GET.get('number_doc', '')
    
    if filtr_number_doc != '':
        docs = docs.filter(nomer__icontains = filtr_number_doc)    
    if type_receptions_id != '':
        type_receptions_id = int(type_receptions_id)
        docs = docs.filter(type_estimation_ocenka_id = type_receptions_id)    
    
    #docs = RegInteractivOcenka.objects.filter(page__id = 1).order_by('-rlk__dataTime')
    chats                   = Chat.objects.all()
    subqyery_reg_interactiv = RegInteractivOcenka.objects.filter(rlk = OuterRef(name = 'rlk_id'))
    subqyery_message_rlk    = DocRLK.objects.filter(id = OuterRef(name = 'rlk_id'))
    subqyery_message_info   = ChatMessage.objects.filter(chat_id = OuterRef(name = 'id')).filter(date = OuterRef(name = 'max_date'))
    subqyery_message        = Subquery(ChatMessage.objects.filter(chat__id = OuterRef(name = 'id')).annotate(max_date = Max('date')).order_by('-max_date').values('max_date')[:1])
    chats = chats.annotate(max_date = subqyery_message)
    chats = chats.order_by('-max_date')
    chats = chats.exclude(max_date = None)
    chats = chats.annotate(rlk = Subquery(subqyery_message_rlk.values('pk')[:1])) 
    chats = chats.annotate(
        rlk_unit = Subquery(subqyery_message_rlk.values('unit__name')[:1])).annotate(
        vin = Subquery(subqyery_reg_interactiv.values('vin')[:1])).annotate(
        mark = Subquery(subqyery_reg_interactiv.values('modification__model__mark__name')[:1])).annotate(
        model = Subquery(subqyery_reg_interactiv.values('modification__model__name')[:1])).annotate(
        modification = Subquery(subqyery_reg_interactiv.values('modification__name')[:1])).annotate(
        staff_name = Subquery(subqyery_message_rlk.values('staff__name')[:1])).annotate(
        content = Subquery(subqyery_message_info.values('content')[:1])).annotate(
        user_content = Subquery(subqyery_message_info.values('user')[:1]))
    
    search = request.GET.get('search', '')
    if len(search) > 0:
        docs = docs.filter(vin__icontains = search) | docs.filter(
            mark__icontains = search) | docs.filter(
                model__icontains = search) | docs.filter(
                    modification__icontains = search) | docs.filter(
                    staff_estimation_name__icontains = search)
        
        
    status_id = request.GET.get('status_id', '')
    if status_id != '':
        status_id = int(status_id)
        docs = docs.filter(status_estimation_id = status_id)
    else:
        docs = docs.exclude(status_estimation_id = 0)
 
    if request.GET.get('unit_id', '') != '':
        unit_id         = int(request.GET['unit_id'])
        docs            = docs.filter(unit__id = unit_id) | docs.filter(unit_dc__id = unit_id) | docs.filter(unit_name_dc = unit_id) 
        #staffsSelect    = list(RefStaff.objects.filter(unit = RefUnit.objects.get(id = unit_id)).order_by('name'))
    
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
        'custom'            : custom,
        'search'            : search
    }
    selected = {
        'units'             : units_select,
        'staffs'            : staffsSelect,
        'staffsKK'          : '',
        'statuses'          : list(RefStatusEstimation.objects.all().order_by('-pk')),
        'type_receptions'   : RefTypeReceptionCarsOrganization.objects.exclude(name = '').order_by('name')
    }
    params = {
        'type'          : 'eco',
        'nav_selected'  : 4,
        'objects'       : page_obj,
        'request'       : request,
        'counts'        : len(docs),
        'selected'      : selected,
        'filtr'         : filtr,
        'filters_user'  : filters_user,
        'chats'         : chats
    }

    return render(request, 'lo/lo_list.html', {'params': params})


def doc(request, id):
     
    if not request.user.is_authenticated:
        try:
            rlk                     = DocRLK.objects.get(pk=id)
            estimation, created     = RegInteractivOcenka.objects.get_or_create(rlk = rlk)
            add_log_history_open(estimation, None, 301)
        except:
            s = 1
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())

    rlk     = DocRLK.objects.get(pk=id)
    estimation, created  = RegInteractivOcenka.objects.get_or_create(rlk = rlk)

    if not request.user.profiles.eco and not request.user.profiles.eco_visible and not request.user in estimation.access_user.all() and not request.user.username == estimation.staff.domain_login  and (estimation.page_documents.store != None and not estimation.page_documents.store in request.user.profiles.korsavto_stores.all()):
        
        add_log_history_open(estimation, request.user, 403)
        
        params = {
        'type'          : 'eco',
        'nav_selected'  : 4,
        'request'       : request,
        }
        return render(request, 'errors/403.html', {'params': params})

    params  = {}
    chat    = Chat.objects.get_or_create(name = rlk.pk, slug = 'rlk_' + str(rlk.pk))[0]
    user    = request.user
    messages = chat.get_last_messages()
    versions = ''
    body     = ''
    list_work_podgotovka    = list()
    list_work_mcu           = list()
    list_work_ss            = list()
    lo                      = None
    car                     = None
    agreement               = None

    if request.method == "GET":
        
        if 'playcar' in request.GET:
            page_remote = estimation.page_remote
            page_remote.end_estimation = DT.datetime.now()
            page_remote.save()
            
            estimation.avtoteka_web = ''
            estimation.avtoteka_preview = ''
            estimation.avtoteka_task = None 
            estimation.hub_start = None
            estimation.kors_start_store = DT.datetime.now().replace(year=2024)

            estimation.end_estimation = None
            
            if estimation.page_documents == None:
                reg_interactiv_ocenka_document = RegInteractivOcenkaDocument()
                reg_interactiv_ocenka_document.save()
                estimation.page_documents = reg_interactiv_ocenka_document
            else:
                reg_interactiv_ocenka_document = estimation.page_documents
            
            reg_interactiv_ocenka_document.unit             = estimation.page_remote.unit
            reg_interactiv_ocenka_document.type_reception   = estimation.page_remote.type_reception
            reg_interactiv_ocenka_document.store            = estimation.page_remote.store
            reg_interactiv_ocenka_document.organization     = estimation.page_remote.organization
            reg_interactiv_ocenka_document.filial           = estimation.page_remote.filial
            reg_interactiv_ocenka_document.save()

            if estimation.page_soglasovanie == None:
                reg_interactiv_ocenka_soglasovane = RegInteractivOcenkaSoglasovanie()
                reg_interactiv_ocenka_soglasovane.save()
                estimation.page_soglasovanie = reg_interactiv_ocenka_soglasovane
            else:
                reg_interactiv_ocenka_soglasovane = estimation.page_soglasovanie
            
            reg_interactiv_ocenka_soglasovane.price_sale            = estimation.page_remote.price_sale
            reg_interactiv_ocenka_soglasovane.price_reception       = estimation.page_remote.price_reception
            reg_interactiv_ocenka_soglasovane.car_sale_info         = estimation.page_remote.car_sale_info
            reg_interactiv_ocenka_soglasovane.car_sale_price        = estimation.page_remote.car_sale_price
            reg_interactiv_ocenka_soglasovane.comment               = estimation.page_remote.comment
            reg_interactiv_ocenka_soglasovane.save()

            estimation.save()
            
            send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= User.objects.get(pk = 1), text='Автомобиль приехал на осмотр. Данные автотека, корсавто будут обновлены автоматически.', estimation_id= estimation.id)
            return HttpResponseRedirect('/estimations/' + str(estimation.rlk.pk) + '/')
            
        price           = {}
        price_autohub   = {}
        price_custom    = {}
        price_kors      = {}

        repair_info         = list()
        estimation_history  = list()
        users               = list()
        opens_infos         = list()
        json_autoteka       = list()

        list_store_info     = list()

        page = 0
        
        if 'page' in request.GET:
            page = int(request.GET['page'])

        estimation, created  = RegInteractivOcenka.objects.get_or_create(rlk = rlk)

        add_log_history_open(estimation, user, page)

        if page == 21 or page == 20:
            
            if page == 20:
                if not request.user.profiles.eco_page_price_info:
                    return HttpResponseRedirect(request.build_absolute_uri().replace('page=21', 'page=9'))
            elif page == 21:
                if not request.user.profiles.eco and not request.user.profiles.eco_page_price_info:
                    return HttpResponseRedirect(request.build_absolute_uri().replace('page=21', 'page=9'))
                    
            refresh = request.GET.get('refresh_data', '')
            if refresh != '':
                if refresh == 'autohub':
                    get_info_max(estimation.id)
                    return HttpResponseRedirect(request.path_info + '?page=' + str(page))
                elif refresh == 'kors':
                    kors_estimation_data(estimation.id)
                    return HttpResponseRedirect(request.path_info + '?page=' + str(page))
                elif refresh == 'all':
                    get_info_max(estimation.id)
                    kors_estimation_data(estimation.id)
                    return HttpResponseRedirect(request.path_info + '?page=' + str(page))
            
            if DocLO.objects.filter(rlk = estimation.rlk).count() > 0:
                lo  = DocLO.objects.filter(rlk = estimation.rlk)[0]  
                if RefCarsOrganization.objects.filter(lo = lo).count() > 0:
                    car = RefCarsOrganization.objects.get(lo = lo)
                    if lo.agreement_number != '':
                        agreements = DocCarAgreement.objects.filter(nomer__icontains = lo.agreement_number).filter(active = True).filter(unit__name__icontains = lo.agreement_unit.name).count()
                        if agreements > 0:
                            agreement = DocCarAgreement.objects.filter(nomer__icontains = lo.agreement_number).filter(active = True).filter(unit__name__icontains = lo.agreement_unit.name)[0]

            price_kors      = estimations_price_calculation(estimation, type_calculation='kors')
            price           = estimations_price_calculation(estimation, type_calculation='avito')
            price_autohub   = estimations_price_calculation(estimation, type_calculation='autohub')
            price_custom    = estimations_price_calculation(estimation, type_calculation='custom')
            body            = body_estimation(estimation=estimation)
            if estimation.avtoteka_data != '' and estimation.avtoteka_data != None:
                json_autoteka = json.loads(estimation.avtoteka_data)['result']['report']['data']
            list_store_info = list()

        if page == 30:
            
            if page == 30:
                if not request.user.profiles.eco_page_price_auto:
                    return HttpResponseRedirect(request.build_absolute_uri().replace('page=21', 'page=9'))
            
            price_kors      = estimations_price_calculation(estimation, type_calculation='kors')
            price           = estimations_price_calculation(estimation, type_calculation='avito')
            price_autohub   = estimations_price_calculation(estimation, type_calculation='autohub')
            price_custom    = estimations_price_calculation(estimation, type_calculation='custom')
            body            = body_estimation(estimation=estimation)
            if estimation.avtoteka_data != '' and estimation.avtoteka_data != None:
                json_autoteka = json.loads(estimation.avtoteka_data)['result']['report']['data']
            list_store_info = list()
            
        if page == 22:
            versions = {}
            versions_page_1 = get_versions('RegInteractivOcenka', estimation.id)
            versions['page_1'] = versions_page_1

        if page == 18:
            opens_infos = opens_info(estimation)
        if page == 13:
            repair_info = repair_history(estimation)
        if page == 5:
            selected = {
                'mark_tyres' : RefMarkTyres.objects.all().order_by('name'),
                'width_tyres' : RefWidthTyres.objects.all().order_by('name'),
                'disk_types' : RefTypeDisk.objects.all().order_by('name'),
                'profil_tyres' : RefProfileTyres.objects.all().order_by('name'),
                'radiuses' : RefRadius.objects.all().order_by('name'),
                'sezons' : RefSezonTyres.objects.all().order_by('name'),
                'et_disks' : RefEtDisk.objects.all().order_by('name'),
                'dia_disks' : RefDiaDisk.objects.all().order_by('name'),
                'psd_disks' : RefPsdDisk.objects.all().order_by('name')
            }
            params = params = {
                            'type'          : 'eco',
                            'rlk'           : rlk,
                            'estimation'    : estimation,
                            'tabindex'      : page,
                            'chat'          : chat,
                            'messages'      : messages,
                            'selected'      : selected,
                            'tab_repairs_count'     : repair_history(estimation, count = True),
                            'tab_estimations_count' : estimation_lo_history(estimation, count = True),
                            'repairs_info'          : repair_info,
                            'estimations_info'      : estimation_history,
                            'user'                  : user,
                        }
            return render(request, 'lo/lo.html', {'params': params})  
        if page == 8:
            estimation_history = estimation_lo_history(estimation) 
        if page == 14:
            if estimation.avtoteka_data != '' and estimation.avtoteka_data != None:
                json_autoteka = json.loads(estimation.avtoteka_data)['result']['report']['data']
        if page == 9:
            
            if 'del_u' in request.GET:
                uusr = User.objects.get(id = request.GET.get('del_u'))
                estimation.access_user.remove(uusr)
                estimation.save()
                return HttpResponseRedirect(request.path_info + '?page=9')
            
            if 'add_u' in request.GET:
                
                uusr = User.objects.get(id = request.GET.get('add_u'))
                estimation.access_user.add(uusr)
                estimation.save()
                
                new_message = RegInteractivOcenkaEmailPush()
                new_message.estimation  = estimation
                new_message.user        = uusr
                new_message.email       = uusr.email
                new_message.comment     = 'Вы добавлены в участники интерактивной оценки.'
                new_message.save()

                return HttpResponseRedirect(request.path_info + '?page=9') 

            users = User.objects.exclude(pk__in = estimation.access_user.all().values_list('id')).exclude(email = '').exclude(first_name = '').filter(is_active = True).order_by('last_name', 'first_name').values('profiles__eco_name', 'last_name', 'first_name', 'id', 'email')
            start_eco_1 = request.GET.get('start_eco_1','')
            if start_eco_1 != '':
                estimation.staff_eco_1 = request.user
                estimation.save()
            start_eco_2 = request.GET.get('start_eco_2','')
            if start_eco_2 != '':
                estimation.staff_eco_2 = request.user
                estimation.save()   

            list_work_podgotovka    = RegEstimationPodgotovka.objects.filter(estimation = estimation)
            list_work_ss            = RegEstimationSS.objects.filter(estimation = estimation)
            list_work_mcu           = RegEstimationMCU.objects.filter(estimation = estimation)

        params = {
                
                'type'                  : 'eco',
                'rlk'                   : rlk,
                'estimation'            : estimation,
                'price'                 : price,
                'price_kors'            : price_kors,
                'price_autohub'         : price_autohub,
                'price_custom'          : price_custom,
                'tabindex'              : page,
                'chat'                  : chat,
                'messages'              : messages,
                'opens_infos'           : opens_infos,
                'json_autoteka'         : json_autoteka,
                'tab_repairs_count'     : repair_history(estimation, count = True),
                'tab_estimations_count' : estimation_lo_history(estimation, count = True),
                'repairs_info'          : repair_info,
                'estimations_info'      : estimation_history,
                'user'                  : user,
                'users'                 : users,
                'store_info'            : list_store_info,
                'versions'              : versions,
                'body'                  : body,
                'list_work_podgotovka'  : list_work_podgotovka,
                'list_work_ss'          : list_work_ss,
                'list_work_mcu'         : list_work_mcu,
                'lo'                    : lo,
                'car'                   : car,
                'agreement'             : agreement
            }
    
    elif request.method == "POST":
        
        reg_interactiv_ocenka, created  = RegInteractivOcenka.objects.get_or_create(rlk = rlk)
        
        add_swap(reg_interactiv_ocenka)

        if 'custom_zna' in request.POST:
            zna = int(request.POST.get('custom_zna', 0)) 
            reg_interactiv_ocenka.custom_zna = zna
            reg_interactiv_ocenka.custom_zna_comment    = request.POST.get('custom_zna_comment', "")
            reg_interactiv_ocenka.custom_zna_author     = request.user
            reg_interactiv_ocenka.save(update_fields=['custom_zna', 'custom_zna_comment', 'custom_zna_author'])
            return HttpResponseRedirect(request.build_absolute_uri())
        
        if 'save_new_task_text' in request.POST:
            
            new_task = RegInteractivOcenkaTask()
            new_task.comment_task   = request.POST.get('save_new_task_text')
            new_task.estimation     = reg_interactiv_ocenka
            new_task.staff_open     = request.user
            new_task.save()

            reg_interactiv_ocenka.end_estimation = DT.datetime(1,1,1)
            reg_interactiv_ocenka.returned = True
            reg_interactiv_ocenka.save()

            send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= user, text='Новая задача - ' + new_task.comment_task, estimation_id= reg_interactiv_ocenka.id)
            reg_interactiv_ocenka.save()
            return HttpResponseRedirect(request.build_absolute_uri())            
        
        if 'save_test_drive' in request.POST:
            
            if reg_interactiv_ocenka.page_test_drive == None:
                reg_interactiv_ocenka_test_drive = RegInteractivOcenkaTestDrive()
                reg_interactiv_ocenka_test_drive.save()
                reg_interactiv_ocenka.page_test_drive = reg_interactiv_ocenka_test_drive
                reg_interactiv_ocenka.save()
            else:
                reg_interactiv_ocenka_test_drive = reg_interactiv_ocenka.page_test_drive

            if reg_interactiv_ocenka_test_drive.start_estimation == None:
                reg_interactiv_ocenka_test_drive.start_estimation     = DT.datetime.now()
            
            reg_interactiv_ocenka_test_drive.engine         = int(request.POST.get('radio_engine', '3'))
            reg_interactiv_ocenka_test_drive.comment_engine = request.POST.get('comment_engine', '')

            reg_interactiv_ocenka_test_drive.system_og          = int(request.POST.get('radio_system_og', '3'))
            reg_interactiv_ocenka_test_drive.comment_system_og  = request.POST.get('comment_system_og', '')

            reg_interactiv_ocenka_test_drive.gear         = int(request.POST.get('radio_gear', '3'))
            reg_interactiv_ocenka_test_drive.comment_gear = request.POST.get('comment_gear', '')

            reg_interactiv_ocenka_test_drive.suspension         = int(request.POST.get('radio_suspension', '3'))
            reg_interactiv_ocenka_test_drive.comment_suspension = request.POST.get('comment_suspension', '')

            reg_interactiv_ocenka_test_drive.airbag             = int(request.POST.get('radio_airbag', '3'))
            reg_interactiv_ocenka_test_drive.comment_airbag     = request.POST.get('comment_airbag', '')

            reg_interactiv_ocenka_test_drive.pp_dinamyc             = int(request.POST.get('radio_pp_dinamyc', '3'))
            reg_interactiv_ocenka_test_drive.pp_kpp                 = int(request.POST.get('radio_pp_kpp', '3'))
            reg_interactiv_ocenka_test_drive.pp_uvod                = int(request.POST.get('radio_pp_uvod', '3'))
            reg_interactiv_ocenka_test_drive.pp_pribor              = int(request.POST.get('radio_pp_pribor', '3'))  

            reg_interactiv_ocenka_test_drive.no_test            = 'no_test' in request.POST
            reg_interactiv_ocenka_test_drive.comment            = request.POST.get('comment', '')
            reg_interactiv_ocenka_test_drive.end_estimation     = DT.datetime.now()
            reg_interactiv_ocenka_test_drive.save()
            
            comment_diagnostica = request.POST.get('comment_diagnostica', '')
            if reg_interactiv_ocenka.page_soglasovanie == None:
                reg_interactiv_ocenka_soglasovanie = RegInteractivOcenkaSoglasovanie()
                reg_interactiv_ocenka_soglasovanie.save()
                reg_interactiv_ocenka.page_soglasovanie = reg_interactiv_ocenka_soglasovanie
                reg_interactiv_ocenka.save()
            else:
                reg_interactiv_ocenka_soglasovanie = reg_interactiv_ocenka.page_soglasovanie
            if comment_diagnostica != reg_interactiv_ocenka_soglasovanie.comment_diagnostica:
                reg_interactiv_ocenka_soglasovanie.comment_diagnostica = comment_diagnostica
                reg_interactiv_ocenka_soglasovanie.save()
            
            type_point  = ''
            text        = ''
            x = 0
            y = 0
            
            send_diagnostic = False
            no_diagnostica_comment = request.POST.get('no_diagnostica_comment', '')
            if no_diagnostica_comment != '':
                reg_interactiv_ocenka_soglasovanie.no_diagnostica_comment = no_diagnostica_comment
                reg_interactiv_ocenka_soglasovanie.no_diagnostica = True
            else:
                reg_interactiv_ocenka_soglasovanie.no_diagnostica_comment = ''
                reg_interactiv_ocenka_soglasovanie.no_diagnostica = False

            files_diagnostic = request.FILES.getlist('file_diagnistic')
            for file_object in files_diagnostic: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'diagnostic', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name)
                new_estimation_files.file_number    = 1 
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save()
                send_diagnostic = True
            if len(comment_diagnostica) > 0:
                send_diagnostic = True

            reg_interactiv_ocenka_soglasovanie.save()
            reg_interactiv_ocenka.save()
            if send_diagnostic:
                send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= user, text='Пройдена диагностика - ' + comment_diagnostica, estimation_id= reg_interactiv_ocenka.id)
            return HttpResponseRedirect(request.build_absolute_uri())
        
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

                #reg_interactiv_ocenka.save()
                send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= user, text='Закрыта задача ' + str(task.comment_task) + " - " + task.comment_success, estimation_id= reg_interactiv_ocenka.id)

            return HttpResponseRedirect(request.build_absolute_uri())   

        if 'price_before_kd' in request.POST:
            if reg_interactiv_ocenka.page_soglasovanie == None:
                reg_interactiv_ocenka_soglasovanie = RegInteractivOcenkaSoglasovanie()
                reg_interactiv_ocenka_soglasovanie.save()
                reg_interactiv_ocenka.page_soglasovanie = reg_interactiv_ocenka_soglasovanie
                reg_interactiv_ocenka.save()
            else:
                reg_interactiv_ocenka_soglasovanie = reg_interactiv_ocenka.page_soglasovanie
            reg_interactiv_ocenka_soglasovanie.price_before_kd = int(request.POST.get('price_before_kd', '0'))
            reg_interactiv_ocenka_soglasovanie.save()
            reg_interactiv_ocenka.save() 
            send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= user, text='Согласована цена до диагностики - ' + '{:0,.2f}'.format(reg_interactiv_ocenka_soglasovanie.price_before_kd).replace(',', ' ') + ' ₽', estimation_id= reg_interactiv_ocenka.id)
            return HttpResponseRedirect(request.build_absolute_uri())
        
        if 'price_after_kd' in request.POST:
            if reg_interactiv_ocenka.page_soglasovanie == None:
                reg_interactiv_ocenka_soglasovanie = RegInteractivOcenkaSoglasovanie()
                reg_interactiv_ocenka_soglasovanie.save()
                reg_interactiv_ocenka.page_soglasovanie = reg_interactiv_ocenka_soglasovanie
                reg_interactiv_ocenka.save()
            else:
                reg_interactiv_ocenka_soglasovanie = reg_interactiv_ocenka.page_soglasovanie
            reg_interactiv_ocenka_soglasovanie.price_after_kd   = int(request.POST.get('price_after_kd', '0'))
            reg_interactiv_ocenka_soglasovanie.price_bcp        = int(request.POST.get('price_bcp', '0'))
            text = ''
            try:
                auction = request.POST.get('auction', '')
                if auction == 'Аукцион':
                    reg_interactiv_ocenka.auction = True
                    reg_interactiv_ocenka.auction_comment = request.POST.get('auction_comment', '')
                    reg_interactiv_ocenka.save()  
                    text = "Продажа: Аукцион. Комментарий: " + reg_interactiv_ocenka.auction_comment
                else:
                    reg_interactiv_ocenka.auction = False
                    reg_interactiv_ocenka.auction_comment = ''
                    reg_interactiv_ocenka.save()
                    text = "Продажа: Розница."                  
            except:
                s=1
                
            price_kors      = estimations_price_calculation(reg_interactiv_ocenka, type_calculation='kors')
            if price_kors != None:
                if price_kors['estimation_price'] > reg_interactiv_ocenka_soglasovanie.price_after_kd:
                    reg_interactiv_ocenka_soglasovanie.price_auto_1         = price_kors['estimation_price']
                    reg_interactiv_ocenka_soglasovanie.price_auto_bcp_1     = price_kors['cna_expenses']
                    reg_interactiv_ocenka_soglasovanie.zachita_ot_ubitka    = price_kors['zachita_ot_ubitka']
                    reg_interactiv_ocenka_soglasovanie.finance_price        = price_kors['finance_price']
                    reg_interactiv_ocenka_soglasovanie.price_zna_1          = price_kors['zna']
                    reg_interactiv_ocenka_soglasovanie.save()
            else:
                price_autohub   = estimations_price_calculation(reg_interactiv_ocenka, type_calculation='autohub')
                if price_autohub != None:
                    if price_autohub['estimation_price'] > reg_interactiv_ocenka_soglasovanie.price_after_kd:
                        reg_interactiv_ocenka_soglasovanie.price_auto_2         = price_autohub['estimation_price']
                        reg_interactiv_ocenka_soglasovanie.price_auto_bcp_2     = price_autohub['cna_expenses']
                        reg_interactiv_ocenka_soglasovanie.zachita_ot_ubitka    = price_autohub['zachita_ot_ubitka']
                        reg_interactiv_ocenka_soglasovanie.finance_price        = price_autohub['finance_price']
                        reg_interactiv_ocenka_soglasovanie.price_zna_2          = price_autohub['zna']
                        reg_interactiv_ocenka_soglasovanie.save()
                else:
                    price_avito   = estimations_price_calculation(reg_interactiv_ocenka, type_calculation='avito')
                    if price_avito != None:
                        if price_avito['estimation_price'] > reg_interactiv_ocenka_soglasovanie.price_after_kd:
                            reg_interactiv_ocenka_soglasovanie.price_auto_3         = price_avito['estimation_price']
                            reg_interactiv_ocenka_soglasovanie.price_auto_bcp_3     = price_avito['cna_expenses']
                            reg_interactiv_ocenka_soglasovanie.zachita_ot_ubitka    = price_avito['zachita_ot_ubitka']
                            reg_interactiv_ocenka_soglasovanie.finance_price        = price_avito['finance_price']
                            reg_interactiv_ocenka_soglasovanie.price_zna_3          = price_avito['zna']
                            reg_interactiv_ocenka_soglasovanie.save()
            
            reg_interactiv_ocenka_soglasovanie.save()
            reg_interactiv_ocenka.save()
            send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= user, text='Согласована цена после диагностики - ' + '{:0,.2f}'.format(reg_interactiv_ocenka_soglasovanie.price_after_kd).replace(',', ' ') + ' ₽' + " " + text, estimation_id= reg_interactiv_ocenka.id)
            return HttpResponseRedirect(request.build_absolute_uri())
        
        if 'type_post' in request.POST:
            
            type_post = request.POST.get('type_post', '')
            if type_post == 'price_remote':
                price_remote = float(request.POST.get('price_remote', '0'))
                page_remote = reg_interactiv_ocenka.page_remote

                page_remote.price_eco       = price_remote
                page_remote.price_eco_user  = request.user
                page_remote.save()

                send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= user, text='Согласована цена до осмотра автомобиля - ' + '{:0,.2f}'.format(price_remote).replace(',', ' ') + ' ₽', estimation_id= reg_interactiv_ocenka.id)
                return HttpResponseRedirect(request.build_absolute_uri()) 
            
            elif type_post == 'save_auto_price':
                
                reg_interactiv_ocenka_soglasovanie = reg_interactiv_ocenka.page_soglasovanie

                price_info = estimations_price_calculation(estimation= reg_interactiv_ocenka, type_calculation = 'custom')
                #Сохраняем данные по планированию восстановительного ремонта
                RegEstimationPodgotovka.objects.filter(estimation = reg_interactiv_ocenka).delete()
                RegEstimationSS.objects.filter(estimation = reg_interactiv_ocenka).delete()
                RegEstimationMCU.objects.filter(estimation = reg_interactiv_ocenka).delete()
                for podgotovka in price_info['list_work_podgotovka']:
                    new_record = RegEstimationPodgotovka()
                    new_record.estimation       = reg_interactiv_ocenka
                    new_record.name             = podgotovka['name']
                    new_record.normo            = podgotovka['quantity']
                    new_record.price_podrad     = podgotovka['amount_pod']
                    new_record.price_kors       = podgotovka['amount']
                    new_record.save()
                    #materials_kf            = models.FloatField("Материалы коэфицент", default=0.0, null=False, blank=True)
                    #materials_price         = models.FloatField("Материалы цена", default=0.0, null=False, blank=True)
                    #materials_amount        = models.FloatField("Материалы сумма", default=0.0, null=False, blank=True)
                for podgotovka in price_info['list_work_service']:
                    new_record                  = RegEstimationSS()
                    new_record.estimation       = reg_interactiv_ocenka
                    new_record.name             = podgotovka['name']
                    new_record.normo            = podgotovka['quantity']
                    new_record.price_podrad     = podgotovka['amount_pod']
                    new_record.price_kors       = podgotovka['amount']
                    new_record.save()
                    #materials_kf            = models.FloatField("Материалы коэфицент", default=0.0, null=False, blank=True)
                    #materials_price         = models.FloatField("Материалы цена", default=0.0, null=False, blank=True)
                    #materials_amount        = models.FloatField("Материалы сумма", default=0.0, null=False, blank=True)
                for podgotovka in price_info['list_work_mcu']:
                    new_record                  = RegEstimationMCU()
                    new_record.estimation       = reg_interactiv_ocenka
                    new_record.name             = podgotovka['name']
                    new_record.normo            = podgotovka['quantity']
                    new_record.price_podrad     = podgotovka['amount_pod']
                    new_record.price_kors       = podgotovka['amount']
                    new_record.save()
                    #materials_kf            = models.FloatField("Материалы коэфицент", default=0.0, null=False, blank=True)
                    #materials_price         = models.FloatField("Материалы цена", default=0.0, null=False, blank=True)
                    #materials_amount        = models.FloatField("Материалы сумма", default=0.0, null=False, blank=True)    
                #
                    
                estimation_price_do_kd  = float(request.POST.get('estimation_price_do_kd', '0')) 
                price_before_kd_comment = request.POST.get('price_before_kd_comment', '')
                
                reg_interactiv_ocenka_soglasovanie.price_before_kd          = estimation_price_do_kd
                reg_interactiv_ocenka_soglasovanie.price_before_kd_comment  = price_before_kd_comment

                if 'estimation_price_after_kd' in request.POST: 
                    reg_interactiv_ocenka_soglasovanie.price_after_kd              = float(request.POST.get('estimation_price_after_kd', '0')) 
                    reg_interactiv_ocenka_soglasovanie.price_after_kd_comment      = request.POST.get('price_after_kd_comment', '') 
                    reg_interactiv_ocenka_soglasovanie.price_bcp                   = float(request.POST.get('price_bcp', '0')) 

                    type_price                  = request.POST.get('type_price', '')
                
                reg_interactiv_ocenka_soglasovanie.amount_podgotovka    = price_info['amount_podgotovka']
                reg_interactiv_ocenka_soglasovanie.amount_ss            = price_info['amount_ss']
                reg_interactiv_ocenka_soglasovanie.amount_mcu           = price_info['amount_mcu']
                reg_interactiv_ocenka_soglasovanie.save()
                
                try:
                    auction = request.POST.get('auction', '')
                    if auction == 'Аукцион':
                        reg_interactiv_ocenka.auction = True
                        reg_interactiv_ocenka.auction_comment = request.POST.get('auction_comment', '')
                        reg_interactiv_ocenka.save()  
                        text = "Продажа: Аукцион. Комментарий: " + reg_interactiv_ocenka.auction_comment
                    else:
                        reg_interactiv_ocenka.auction = False
                        reg_interactiv_ocenka.auction_comment = ''
                        reg_interactiv_ocenka.save()
                        text = "Продажа: Розница."                  
                except:
                    s=1
                
                reg_interactiv_ocenka.save()

                if reg_interactiv_ocenka_soglasovanie.price_after_kd > 0:
                    
                    RegEstimationsCalculationDetail.objects.filter(estimations = reg_interactiv_ocenka).delete()

                    price_kors      = estimations_price_calculation(reg_interactiv_ocenka, type_calculation='kors')
                    if price_kors != None:
                        if price_kors['estimation_price'] > reg_interactiv_ocenka_soglasovanie.price_after_kd:
                            reg_interactiv_ocenka_soglasovanie.price_auto_1         = price_kors['estimation_price']
                            reg_interactiv_ocenka_soglasovanie.price_auto_bcp_1     = price_kors['cna_expenses']
                            reg_interactiv_ocenka_soglasovanie.zachita_ot_ubitka    = price_kors['zachita_ot_ubitka']
                            reg_interactiv_ocenka_soglasovanie.finance_price        = price_kors['finance_price']
                            reg_interactiv_ocenka_soglasovanie.price_zna_1          = price_kors['zna']
                            reg_interactiv_ocenka_soglasovanie.save()
                    else:
                        price_autohub   = estimations_price_calculation(reg_interactiv_ocenka, type_calculation='autohub')
                        if price_autohub != None:
                            if price_autohub['estimation_price'] > reg_interactiv_ocenka_soglasovanie.price_after_kd:
                                reg_interactiv_ocenka_soglasovanie.price_auto_2         = price_autohub['estimation_price']
                                reg_interactiv_ocenka_soglasovanie.price_auto_bcp_2     = price_autohub['cna_expenses']
                                reg_interactiv_ocenka_soglasovanie.zachita_ot_ubitka    = price_autohub['zachita_ot_ubitka']
                                reg_interactiv_ocenka_soglasovanie.finance_price        = price_autohub['finance_price']
                                reg_interactiv_ocenka_soglasovanie.price_zna_2          = price_autohub['zna']
                                reg_interactiv_ocenka_soglasovanie.save()
                        else:
                            price_avito   = estimations_price_calculation(reg_interactiv_ocenka, type_calculation='avito')
                            if price_avito != None:
                                if price_avito['estimation_price'] > reg_interactiv_ocenka_soglasovanie.price_after_kd:
                                    reg_interactiv_ocenka_soglasovanie.price_auto_3         = price_avito['estimation_price']
                                    reg_interactiv_ocenka_soglasovanie.price_auto_bcp_3     = price_avito['cna_expenses']
                                    reg_interactiv_ocenka_soglasovanie.zachita_ot_ubitka    = price_avito['zachita_ot_ubitka']
                                    reg_interactiv_ocenka_soglasovanie.finance_price        = price_avito['finance_price']
                                    reg_interactiv_ocenka_soglasovanie.price_zna_3          = price_avito['zna']
                                    reg_interactiv_ocenka_soglasovanie.save()

                    reg_interactiv_ocenka.staff_eco_2 = request.user
                    reg_interactiv_ocenka.save()
                    send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= user, text='Согласована цена после диагностики - ' + '{:0,.2f}'.format(reg_interactiv_ocenka_soglasovanie.price_after_kd).replace(',', ' ') + ' ₽' + " " + text, estimation_id= reg_interactiv_ocenka.id)
                elif reg_interactiv_ocenka_soglasovanie.price_before_kd > 0:
                    reg_interactiv_ocenka.staff_eco_1 = request.user
                    reg_interactiv_ocenka.save()
                    send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= user, text='Согласована цена до диагностики - ' + '{:0,.2f}'.format(reg_interactiv_ocenka_soglasovanie.price_before_kd).replace(',', ' ') + ' ₽', estimation_id= reg_interactiv_ocenka.id)
  
            else:

                type_post = request.POST.get('type_post', '')
                
                if type_post == "save_auto_price":
                    if reg_interactiv_ocenka.page_soglasovanie == None:
                        reg_interactiv_ocenka_soglasovanie = RegInteractivOcenkaSoglasovanie()
                        reg_interactiv_ocenka_soglasovanie.save()
                        reg_interactiv_ocenka.page_soglasovanie = reg_interactiv_ocenka_soglasovanie
                        reg_interactiv_ocenka.save()
                    else:
                        reg_interactiv_ocenka_soglasovanie = reg_interactiv_ocenka.page_soglasovanie
            
                reg_interactiv_ocenka_soglasovanie.price_type                      = request.POST.get('type_price', '')
                reg_interactiv_ocenka_soglasovanie.price_correction                = int(request.POST.get('price_correction', '0'))
                reg_interactiv_ocenka_soglasovanie.price_correction_comment        = request.POST.get('price_correction_comment', '')
                reg_interactiv_ocenka_soglasovanie.price_correction_comment_author = request.user                

                custom_estimation_price_do_kd_old   = float(request.POST.get('custom_estimation_price_do_kd_old', '0'))
                custom_estimation_price_old         = float(request.POST.get('custom_estimation_price_old', '0'))
                custom_estimation_price_do_kd       = float(request.POST.get('custom_estimation_price_do_kd', '0'))
                custom_estimation_price             = float(request.POST.get('custom_estimation_price', '0'))

                price_info = estimations_price_calculation(estimation= reg_interactiv_ocenka, type_calculation = 'custom')
                
                RegEstimationPodgotovka.objects.filter(estimation = reg_interactiv_ocenka).delete()
                RegEstimationSS.objects.filter(estimation = reg_interactiv_ocenka).delete()
                RegEstimationMCU.objects.filter(estimation = reg_interactiv_ocenka).delete()

                
                for podgotovka in price_info['list_work_podgotovka']:
                    new_record = RegEstimationPodgotovka()
                    new_record.estimation   = reg_interactiv_ocenka
                    new_record.name         = podgotovka['name']
                    new_record.normo            = podgotovka['quantity']
                    new_record.price_podrad     = podgotovka['amount_pod']
                    new_record.price_kors       = podgotovka['amount']
                    new_record.save()
                    #materials_kf            = models.FloatField("Материалы коэфицент", default=0.0, null=False, blank=True)
                    #materials_price         = models.FloatField("Материалы цена", default=0.0, null=False, blank=True)
                    #materials_amount        = models.FloatField("Материалы сумма", default=0.0, null=False, blank=True)

                for podgotovka in price_info['list_work_service']:
                    new_record = RegEstimationSS()
                    new_record.estimation       = reg_interactiv_ocenka
                    new_record.name         = podgotovka['name']
                    new_record.normo            = podgotovka['quantity']
                    new_record.price_podrad     = podgotovka['amount_pod']
                    new_record.price_kors       = podgotovka['amount']
                    new_record.save()
                    #materials_kf            = models.FloatField("Материалы коэфицент", default=0.0, null=False, blank=True)
                    #materials_price         = models.FloatField("Материалы цена", default=0.0, null=False, blank=True)
                    #materials_amount        = models.FloatField("Материалы сумма", default=0.0, null=False, blank=True)

                for podgotovka in price_info['list_work_mcu']:
                    new_record = RegEstimationMCU()
                    new_record.estimation       = reg_interactiv_ocenka
                    new_record.name         = podgotovka['name']
                    new_record.normo            = podgotovka['quantity']
                    new_record.price_podrad     = podgotovka['amount_pod']
                    new_record.price_kors       = podgotovka['amount']
                    new_record.save()
                    #materials_kf            = models.FloatField("Материалы коэфицент", default=0.0, null=False, blank=True)
                    #materials_price         = models.FloatField("Материалы цена", default=0.0, null=False, blank=True)
                    #materials_amount        = models.FloatField("Материалы сумма", default=0.0, null=False, blank=True)    
                
                if custom_estimation_price_do_kd > 0:
                    reg_interactiv_ocenka_soglasovanie.price_before_kd = custom_estimation_price_do_kd

                if custom_estimation_price > 0:
                    reg_interactiv_ocenka_soglasovanie.price_after_kd      = custom_estimation_price
                    reg_interactiv_ocenka_soglasovanie.price_bcp            = int(request.POST.get('price_bcp', '0'))
                    
                amount_podgotovka   = float(request.POST.get('amount_podgotovka', '0'))
                amount_ss           = float(request.POST.get('amount_ss', '0'))
                amount_mcu          = float(request.POST.get('amount_mcu', '0'))
                
                reg_interactiv_ocenka_soglasovanie.amount_podgotovka    = amount_podgotovka
                reg_interactiv_ocenka_soglasovanie.amount_ss            = amount_ss
                reg_interactiv_ocenka_soglasovanie.amount_mcu           = amount_mcu
                reg_interactiv_ocenka_soglasovanie.zachita_ot_ubitka    = 0
                reg_interactiv_ocenka_soglasovanie.save()
            
                try:
                    auction = request.POST.get('auction', '')
                    if auction == 'Аукцион':
                        reg_interactiv_ocenka.auction = True
                        reg_interactiv_ocenka.auction_comment = request.POST.get('auction_comment', '')
                        reg_interactiv_ocenka.save()  
                        text = "Продажа: Аукцион. Комментарий: " + reg_interactiv_ocenka.auction_comment
                    else:
                        reg_interactiv_ocenka.auction = False
                        reg_interactiv_ocenka.auction_comment = ''
                        reg_interactiv_ocenka.save()
                        text = "Продажа: Розница."                  
                except:
                    s=1
                reg_interactiv_ocenka.save()
                
                if reg_interactiv_ocenka_soglasovanie.price_after_kd > 0:
                    
                    RegEstimationsCalculationDetail.objects.filter(estimations = reg_interactiv_ocenka).delete()

                    price_kors      = estimations_price_calculation(reg_interactiv_ocenka, type_calculation='kors')
                    if price_kors != None:
                        if price_kors['estimation_price'] > reg_interactiv_ocenka_soglasovanie.price_after_kd:
                            reg_interactiv_ocenka_soglasovanie.price_auto_1         = price_kors['estimation_price']
                            reg_interactiv_ocenka_soglasovanie.price_auto_bcp_1     = price_kors['cna_expenses']
                            reg_interactiv_ocenka_soglasovanie.zachita_ot_ubitka    = price_kors['zachita_ot_ubitka']
                            reg_interactiv_ocenka_soglasovanie.finance_price        = price_kors['finance_price']
                            reg_interactiv_ocenka_soglasovanie.save()
                    else:
                        price_autohub   = estimations_price_calculation(reg_interactiv_ocenka, type_calculation='autohub')
                        if price_autohub != None:
                            if price_autohub['estimation_price'] > reg_interactiv_ocenka_soglasovanie.price_after_kd:
                                reg_interactiv_ocenka_soglasovanie.price_auto_2         = price_autohub['estimation_price']
                                reg_interactiv_ocenka_soglasovanie.price_auto_bcp_2     = price_autohub['cna_expenses']
                                reg_interactiv_ocenka_soglasovanie.zachita_ot_ubitka    = price_autohub['zachita_ot_ubitka']
                                reg_interactiv_ocenka_soglasovanie.finance_price        = price_autohub['finance_price']
                                reg_interactiv_ocenka_soglasovanie.save()
                        else:
                            price_avito   = estimations_price_calculation(reg_interactiv_ocenka, type_calculation='avito')
                            if price_avito != None:
                                if price_avito['estimation_price'] > reg_interactiv_ocenka_soglasovanie.price_after_kd:
                                    reg_interactiv_ocenka_soglasovanie.price_auto_3         = price_avito['estimation_price']
                                    reg_interactiv_ocenka_soglasovanie.price_auto_bcp_3     = price_avito['cna_expenses']
                                    reg_interactiv_ocenka_soglasovanie.zachita_ot_ubitka    = price_avito['zachita_ot_ubitka']
                                    reg_interactiv_ocenka_soglasovanie.finance_price        = price_avito['finance_price']
                                    reg_interactiv_ocenka_soglasovanie.save()

                    reg_interactiv_ocenka.staff_eco_2 = request.user
                    reg_interactiv_ocenka.save()
                    send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= user, text='Согласована цена после диагностики - ' + '{:0,.2f}'.format(reg_interactiv_ocenka_soglasovanie.price_after_kd).replace(',', ' ') + ' ₽' + " " + text, estimation_id= reg_interactiv_ocenka.id)
                elif reg_interactiv_ocenka_soglasovanie.price_before_kd > 0:
                    reg_interactiv_ocenka.staff_eco_1 = request.user
                    reg_interactiv_ocenka.save()
                    send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= user, text='Согласована цена до диагностики - ' + '{:0,.2f}'.format(reg_interactiv_ocenka_soglasovanie.price_before_kd).replace(',', ' ') + ' ₽', estimation_id= reg_interactiv_ocenka.id)
            
            #send_web_socket_message(group = 'rlk_' + str(id), chat=chat, user= user, text='Согласована цена после диагностики - ' + str(reg_interactiv_ocenka_soglasovanie.price_after_kd) + " " + text, estimation_id= reg_interactiv_ocenka.id)
            return HttpResponseRedirect(request.build_absolute_uri())    

        return HttpResponseRedirect(request.build_absolute_uri())  

    if estimation.v > 1:
        return render(request, 'lo/lo_v' + str(estimation.v) + '.html', {'params': params})             
    else:
        return render(request, 'lo/lo.html', {'params': params}) 


def body_estimation(estimation):
    
    array_info  = list()
    polys = RegInfoBody.objects.all().order_by('body_elem_name').values('body_elem_name').distinct().order_by('body_elem_name')
    for poly in polys:
        dict_elem = dict()
        dict_elem['name']           = poly['body_elem_name']
        dict_elem['tr']             = 0
        dict_elem['carap']          = 0
        dict_elem['carap_strong']   = 0
        dict_elem['rzav']           = 0
        dict_elem['rzav_strong']    = 0
        dict_elem['vmyat']          = 0
        dict_elem['vmyat_strong']   = 0
        dict_elem['skol']           = 0
        dict_elem['perecras']       = 0
        dict_elem['perecras_strong'] = 0
        dict_elem['stiker']         = 0
        dict_elem['toner']          = 0
        dict_elem['poly']           = 0
        dict_elem['replace']        = 0
        dict_elem['replace_add']    = 0
        dict_elem['work']           = ''
        dict_elem['normo']          = 0.0
        dict_elem['podryad']        = 0
        dict_elem['all']            = 0
        dict_elem['kors']           = 0
        array_info.append(dict_elem)

    array_body  = list()
    files       = RegRegInteractivOcenkaFiles.objects.filter(type_file__icontains = 'array_images').filter(estimation = estimation).order_by('-type_file')
    
    
    carap           = 0
    carap_strong    = 0
    rzav            = 0
    rzav_strong     = 0
    vmyat           = 0
    vmyat_strong    = 0
    skol            = 0
    perecras        = 0
    perecras_strong = 0
    tr              = 0    
    all             = 0
    replace_add     = 0
    stiker          = 0
    toner           = 0
    poly            = 0
    replace         = 0

    for file in files:
        
        if file.type_file == 'array_images_pass':
            bodys_info  = RegInfoBody.objects.filter(type_body = 'седан').filter(side = 'пассажирская')
        elif file.type_file == 'array_images_vod':
            bodys_info  = RegInfoBody.objects.filter(type_body = 'седан').filter(side = 'водительская')
        elif file.type_file == 'array_images_pered':
            bodys_info  = RegInfoBody.objects.filter(type_body = 'седан').filter(side = 'перед')
        elif file.type_file == 'array_images_zad':
            bodys_info  = RegInfoBody.objects.filter(type_body = 'седан').filter(side = 'зад')
        elif file.type_file == 'array_images_up':
            bodys_info  = RegInfoBody.objects.filter(type_body = 'седан').filter(side = 'верх')
        else:
            bodys_info = list()

        point = Point(file.cor_x , file.cor_y)
        for body in bodys_info:
            polygon  = list()
            poly_str = body.polygon
            lens_str = poly_str.split(',')
            len_mas  = len(lens_str)
            s = 0
            while s < len_mas:
                if s % 2 == 0:
                    polygon.append(Point(int(lens_str[s]), int(lens_str[s+1])))   
                s = s + 1
            # Check if the point is inside the polygon
            if point_in_polygon(point, polygon):
                dict_elem = ''
                elem_name = body.body_elem_name
                name = '' + body.body_elem_name + ' - ' + file.type_point 
                if file.type_point == 'толщиномер':
                    if file.kraska > 300:
                        name = '' + body.body_elem_name + ' - окрашено'
                    else:
                        name = ''
                if name != '':
                    try:
                        index = array_body.index(name)
                    except ValueError:
                        for elem_data in array_info:
                            if elem_data['name'] == elem_name:
                                dict_elem = elem_data
                                all = elem_data['all']
                        if dict_elem == '':
                            all = 0
                            dict_elem = dict()
                            dict_elem['name']               = elem_name
                            dict_elem['tr']                 = 0
                            dict_elem['carap']              = 0
                            dict_elem['carap_strong']       = 0
                            dict_elem['rzav']               = 0
                            dict_elem['rzav_strong']        = 0
                            dict_elem['vmyat']              = 0
                            dict_elem['vmyat_strong']       = 0
                            dict_elem['skol']               = 0
                            dict_elem['perecras']           = 0
                            dict_elem['perecras_strong']    = 0
                            dict_elem['replace_add']        = 0
                            dict_elem['replace']            = 0
                            dict_elem['stiker']             = 0
                            dict_elem['toner']              = 0
                            dict_elem['poly']               = 0
                            dict_elem['work']               = ''
                            dict_elem['normo']              = 0.0
                            dict_elem['podryad']            = 0
                            dict_elem['all']                = 0
                            dict_elem['kors']               = 0
                            

                        if file.type_point == 'толщиномер':
                            if file.kraska > 300:
                                dict_elem['perecras'] = dict_elem['perecras'] + 1
                                perecras = perecras + 1
                            if file.kraska > 900:
                                dict_elem['perecras_strong'] = dict_elem['perecras_strong'] + 1
                                perecras_strong = perecras_strong + 1
                        if file.type_point == 'ржавчина':
                            dict_elem['rzav']           = dict_elem['rzav']  + 1
                            rzav = rzav + 1
                            all = all + 1
                        elif file.type_point == 'ржавчина сквозная':
                            dict_elem['rzav_strong']    =  dict_elem['rzav_strong']  + 1
                            rzav_strong = rzav_strong + 1
                            all = all + 1
                        elif file.type_point == 'царапина':
                            dict_elem['carap']          =  dict_elem['carap']  + 1
                            carap = carap + 1
                            all = all + 1
                        elif file.type_point == 'царапина сильная':
                            dict_elem['carap_strong']    =  dict_elem['carap_strong']  + 1
                            carap_strong = carap_strong + 1
                            all = all + 1
                        elif file.type_point == 'вмятина':
                            dict_elem['vmyat']          =  dict_elem['vmyat']  + 1
                            vmyat = vmyat + 1
                            all = all + 1
                        elif file.type_point == 'вмятина сильная':
                            dict_elem['vmyat_strong']    =  dict_elem['vmyat_strong']  + 1
                            vmyat_strong = vmyat_strong + 1
                            all = all + 1
                        elif file.type_point == 'скол':
                            dict_elem['skol']               =  dict_elem['skol']  + 1
                            skol = skol + 1
                            all = all + 1
                        elif file.type_point == 'трещина':
                            dict_elem['tr']               =  dict_elem['tr']  + 1
                            tr = tr + 1
                            all = all + 1
                        elif file.type_point == 'заменить':
                            dict_elem['replace_add'] = dict_elem['replace_add']  + 1
                            replace_add = replace_add + 1
                            all = all + 1
                        elif file.type_point == 'заменен':
                            dict_elem['replace'] = dict_elem['replace']  + 1
                            replace = replace + 1
                            all = all + 1
                        elif file.type_point == 'наклейка':
                            dict_elem['stiker'] = dict_elem['stiker']  + 1
                            stiker = stiker + 1
                            all = all + 1
                        elif file.type_point == 'тонировка':
                            dict_elem['toner'] = dict_elem['toner']  + 1
                            toner = toner + 1
                            all = all + 1
                        elif file.type_point == 'полировка':
                            dict_elem['poly'] = dict_elem['poly']  + 1
                            poly = poly + 1
                            all = all + 1
                        dict_elem['all'] = all
                        for elem_data in array_info:
                            if elem_data['name'] == elem_name:
                                elem_data = dict_elem
                        
                        array_body.append(name)

    body = {
        'array'             : array_info,
        'carap'             : carap,
        'carap_strong'      : carap_strong,
        'rzav'              : rzav,
        'rzav_strong'       : rzav_strong,
        'vmyat'             : vmyat,
        'vmyat_strong'      : vmyat_strong,
        'skol'              : skol,
        'perecras'          : perecras,
        'perecras_strong'   : perecras_strong,
        'tr'                : tr,
        'replace_add'       : replace_add,
        'stiker'            : stiker,
        'toner'             : toner,
        'poly'              : poly,
        'replace'           : replace
        }
    
    
    return body


def repair_history(estimation, count = False):
    if estimation.vin != '':
        if count:
            return DocZN.objects.filter(cars__vin__icontains = estimation.vin).count()
        else:
            return DocZN.objects.filter(cars__vin__icontains = estimation.vin).order_by('-dataTime')
    return list()


def repair_history_vin(vin, count = False):
    if vin != '':
        if count:
            return DocZN.objects.filter(cars__vin__icontains = vin).count()
        else:
            return DocZN.objects.filter(cars__vin__icontains = vin).order_by('-dataTime')
    return list()


def estimation_lo_history(estimation, count = False):
    if estimation.vin != '':
        if count:
            lo = DocLO.objects.filter(vin = estimation.vin)
            subqyery_interactiv = Subquery(RegInteractivOcenka.objects.filter(rlk__id = OuterRef(name='rlk__id')).values('rlk__id')[:1], output_field = models.IntegerField())
            lo = lo.annotate(interactiv = Count(subqyery_interactiv))
            lo = lo.filter(interactiv = 0).count()
            interatciv = RegInteractivOcenka.objects.filter(vin = estimation.vin).count()
            return lo + interatciv
        else:
            list_info = list()
            interatcivs = RegInteractivOcenka.objects.filter(vin = estimation.vin).order_by('-start_estimation')
            sub_lo = DocLO.objects.filter(rlk__id = OuterRef(name='rlk__id'))
            interatcivs = interatcivs.annotate(
                lo_number   = Subquery(sub_lo.values('nomer')[:1])).annotate(
                interactiv  = Value(True))
            
            for interatciv in interatcivs:
                list_info.append(interatciv)
            lo = DocLO.objects.filter(vin = estimation.vin).order_by('-dataTime')
            subqyery_interactiv = Subquery(RegInteractivOcenka.objects.filter(rlk__id = OuterRef(name='rlk__id')).values('rlk__id')[:1], output_field = models.IntegerField())
            lo = lo.annotate(interactiv = Count(subqyery_interactiv))
            lo = lo.filter(interactiv = 0)
            for lo_info in lo:
                list_info.append(lo_info)
            return list_info
        
    return list()


def estimations_price_calculation(estimation, type_calculation):


    estimation_settings     = RegEstimationsSettings.objects.get(pk = 1)
    if estimation.page_soglasovanie != None:
        if estimation.page_soglasovanie.settings != None:
            estimation_settings = estimation.page_soglasovanie.settings 

    modification            = estimation.modification
    
    list_work_podgotovka    = list()
    list_work_service       = list()
    list_work_mcu           = list()

    auction_success     = False
    auction             = False
    auction_comment     = ''
    amount_podgotovka   = 0
    amount_ss           = 0
    amount_mcu          = 0
    ammount_sum         = 0
    kf_auction          = 75 

    list_info_price     = list()
    zna_type            = ''
    zna                 = 0
    zachita_ot_ubitka   = 0
    finance_price       = 0
    iznos_price         = 0

    if type_calculation == 'kors':
        zna         = estimation.kors_price
        zna_type    = '1C'
    if type_calculation == 'autohub':
        if estimation.hub_avg == 0 and estimation.page_remote != None:
            zna = estimation.page_remote.hub_avg
        else:
            zna         = estimation.hub_avg
        zna_type    = 'Автохаб'
    elif type_calculation == 'avito':
        zna = estimation.avito_price_avg_market_price
        zna_type = 'Авито'   
    elif type_calculation == 'custom':
        zna = estimation.custom_zna
        zna_type = 'Ручная'

    if zna == 0:
        return None
    
    zg  = "Неопределена"
    if estimation.page_documents == None or estimation.page_documents.unit == None:
        dc              = estimation.page_remote.unit
    else:
        dc              = estimation.page_documents.unit
    
    fin_all         = estimation_settings.all_percent_financity
    day_sale_all    = estimation_settings.all_days_stok_financity
    
    kf                  = 100
    percent_ss          = 0
    percent_torg        = 0
    zna_izp_kf          = 0
    zna_izp_type        = 0
    percent_sale_1C     = 100
    percent_sale        = 100
    battery             = 0

    if zna < 200000:
        zg              = '200'
        kf              = dc.ratio_avtohub_txt_200
        percent_ss      = dc.percent_txt_200
        percent_torg    = dc.percent_torg_txt_200
        zna_izp_kf      = estimation_settings.izp_200
        zna_izp_type    = estimation_settings.izp_200_v
        percent_sale_1C = dc.ratio_1с_test_price_200
        percent_sale    = dc.ratio_avtohub_test_price_200
        percent_sale_rdo= dc.ratio_avtohub_rdo_200
        percent_sale_kor= dc.ratio_avtohub_kor_200
        kf_auction      = estimation_settings.auction_kf_200
        fin_zg          = estimation_settings.percent_financity_200
        day_sale_zg     = estimation_settings.days_stok_financity_200
        
        windshield      = estimation_settings.windshield_200
        windshield_heat = estimation_settings.windshield_heat_200
        light_pered     = estimation_settings.light_pered_200
        light_pered_kf  = estimation_settings.light_pered_kf_200
        light_zad       = estimation_settings.light_zad_200
        light_zad_kf    = estimation_settings.light_zad_kf_200
        battery         = estimation_settings.battery_200
        engine_danger_kf            = estimation_settings.engine_danger_kf_200            
        engine_danger_amount_min    = estimation_settings.engine_danger_amount_min_200        
        engine_warning_kf           = estimation_settings.engine_warning_kf_200 
        engine_warning_amount_min   = estimation_settings.engine_warning_amount_min_200 
        engine_dt_danger_kf         = estimation_settings.engine_dt_danger_kf_200   
        engine_dt_danger_amount_min = estimation_settings.engine_dt_danger_amount_min_200   
        engine_dt_warning_kf        = estimation_settings.engine_dt_warning_kf_200    
        engine_dt_warning_amount_min= estimation_settings.engine_dt_warning_amount_min_200    
        gear_at_danger_kf           = estimation_settings.gear_at_danger_kf_200 
        gear_at_danger_amount_min   = estimation_settings.gear_at_danger_amount_min_200 
        gear_at_warning_kf          = estimation_settings.gear_at_warning_kf_200  
        gear_at_warning_amount_min  = estimation_settings.gear_at_warning_amount_min_200  
        gear_amt_danger_kf          = estimation_settings.gear_amt_danger_kf_200  
        gear_amt_danger_amount_min  = estimation_settings.gear_amt_danger_amount_min_200  
        gear_amt_warning_kf         = estimation_settings.gear_amt_warning_kf_200   
        gear_amt_warning_amount_min = estimation_settings.gear_amt_warning_amount_min_200   
        gear_cvt_danger_kf          = estimation_settings.gear_cvt_danger_kf_200  
        gear_cvt_danger_amount_min  = estimation_settings.gear_cvt_danger_amount_min_200  
        gear_cvt_warning_kf         = estimation_settings.gear_cvt_warning_kf_200   
        gear_cvt_warning_amount_min = estimation_settings.gear_cvt_warning_amount_min_200   
        gear_mt_danger_kf           = estimation_settings.gear_mt_danger_kf_200 
        gear_mt_danger_amount_min   = estimation_settings.gear_mt_danger_amount_min_200 
        gear_mt_warning_kf          = estimation_settings.gear_mt_warning_kf_200     
        gear_mt_warning_amount_min  = estimation_settings.gear_mt_warning_amount_min_200   
        suspension_danger_kf        = estimation_settings.suspension_danger_kf_200   
        suspension_danger_amount_min= estimation_settings.suspension_danger_amount_min_200       
        suspension_warning_kf        = estimation_settings.suspension_warning_kf_200        
        suspension_warning_amount_min= estimation_settings.suspension_warning_amount_min_200       
        system_og_danger_kf          = estimation_settings.system_og_danger_kf_200     
        system_og_danger_amount_min  = estimation_settings.system_og_danger_amount_min_200     
        system_og_warning_kf         = estimation_settings.system_og_warning_kf_200      
        system_og_warning_amount_min = estimation_settings.system_og_warning_amount_min_200
    elif zna < 400000:
        zg              = '400'
        fin_zg          = estimation_settings.percent_financity_400
        day_sale_zg     = estimation_settings.days_stok_financity_400
        kf              = dc.ratio_avtohub_txt_400
        percent_ss      = dc.percent_txt_400
        percent_torg    = dc.percent_torg_txt_400
        zna_izp_kf      = estimation_settings.izp_400
        zna_izp_type    = estimation_settings.izp_400_v
        percent_sale_1C = dc.ratio_1с_test_price_400
        percent_sale    = dc.ratio_avtohub_test_price_400
        percent_sale_rdo= dc.ratio_avtohub_rdo_400
        percent_sale_kor= dc.ratio_avtohub_kor_400
        kf_auction      = estimation_settings.auction_kf_400
        windshield      = estimation_settings.windshield_400
        windshield_heat = estimation_settings.windshield_heat_400
        light_pered     = estimation_settings.light_pered_400
        light_pered_kf  = estimation_settings.light_pered_kf_400
        light_zad       = estimation_settings.light_zad_400
        light_zad_kf    = estimation_settings.light_zad_kf_400
        battery         = estimation_settings.battery_400
        engine_danger_kf            = estimation_settings.engine_danger_kf_400            
        engine_danger_amount_min    = estimation_settings.engine_danger_amount_min_400
        engine_warning_kf           = estimation_settings.engine_warning_kf_400 
        engine_warning_amount_min   = estimation_settings.engine_warning_amount_min_400 
        engine_dt_danger_kf         = estimation_settings.engine_dt_danger_kf_400   
        engine_dt_danger_amount_min = estimation_settings.engine_dt_danger_amount_min_400   
        engine_dt_warning_kf        = estimation_settings.engine_dt_warning_kf_400    
        engine_dt_warning_amount_min= estimation_settings.engine_dt_warning_amount_min_400    
        gear_at_danger_kf           = estimation_settings.gear_at_danger_kf_400 
        gear_at_danger_amount_min   = estimation_settings.gear_at_danger_amount_min_400 
        gear_at_warning_kf          = estimation_settings.gear_at_warning_kf_400  
        gear_at_warning_amount_min  = estimation_settings.gear_at_warning_amount_min_400  
        gear_amt_danger_kf          = estimation_settings.gear_amt_danger_kf_400  
        gear_amt_danger_amount_min  = estimation_settings.gear_amt_danger_amount_min_400  
        gear_amt_warning_kf         = estimation_settings.gear_amt_warning_kf_400   
        gear_amt_warning_amount_min = estimation_settings.gear_amt_warning_amount_min_400   
        gear_cvt_danger_kf          = estimation_settings.gear_cvt_danger_kf_400  
        gear_cvt_danger_amount_min  = estimation_settings.gear_cvt_danger_amount_min_400  
        gear_cvt_warning_kf         = estimation_settings.gear_cvt_warning_kf_400   
        gear_cvt_warning_amount_min = estimation_settings.gear_cvt_warning_amount_min_400   
        gear_mt_danger_kf           = estimation_settings.gear_mt_danger_kf_400 
        gear_mt_danger_amount_min   = estimation_settings.gear_mt_danger_amount_min_400 
        gear_mt_warning_kf          = estimation_settings.gear_mt_warning_kf_400     
        gear_mt_warning_amount_min  = estimation_settings.gear_mt_warning_amount_min_400   
        suspension_danger_kf        = estimation_settings.suspension_danger_kf_400   
        suspension_danger_amount_min= estimation_settings.suspension_danger_amount_min_400       
        suspension_warning_kf        = estimation_settings.suspension_warning_kf_400        
        suspension_warning_amount_min= estimation_settings.suspension_warning_amount_min_400       
        system_og_danger_kf          = estimation_settings.system_og_danger_kf_400     
        system_og_danger_amount_min  = estimation_settings.system_og_danger_amount_min_400     
        system_og_warning_kf         = estimation_settings.system_og_warning_kf_400      
        system_og_warning_amount_min = estimation_settings.system_og_warning_amount_min_400
    elif zna < 700000:
        zg              = '700'
        fin_zg          = estimation_settings.percent_financity_700
        day_sale_zg     = estimation_settings.days_stok_financity_700
        kf              = dc.ratio_avtohub_txt_700
        percent_ss      = dc.percent_txt_700
        percent_torg    = dc.percent_torg_txt_700
        zna_izp_kf      = estimation_settings.izp_700
        zna_izp_type    = estimation_settings.izp_700_v
        percent_sale_1C = dc.ratio_1с_test_price_700
        percent_sale    = dc.ratio_avtohub_test_price_700
        percent_sale_rdo= dc.ratio_avtohub_rdo_700
        percent_sale_kor= dc.ratio_avtohub_kor_700
        kf_auction      = estimation_settings.auction_kf_700
        windshield      = estimation_settings.windshield_700
        windshield_heat = estimation_settings.windshield_heat_700
        light_pered     = estimation_settings.light_pered_700
        light_pered_kf  = estimation_settings.light_pered_kf_700
        light_zad       = estimation_settings.light_zad_700
        light_zad_kf    = estimation_settings.light_zad_kf_700
        battery         = estimation_settings.battery_700
        engine_danger_kf            = estimation_settings.engine_danger_kf_700            
        engine_danger_amount_min    = estimation_settings.engine_danger_amount_min_700
        engine_warning_kf           = estimation_settings.engine_warning_kf_700 
        engine_warning_amount_min   = estimation_settings.engine_warning_amount_min_700 
        engine_dt_danger_kf         = estimation_settings.engine_dt_danger_kf_700   
        engine_dt_danger_amount_min = estimation_settings.engine_dt_danger_amount_min_700   
        engine_dt_warning_kf        = estimation_settings.engine_dt_warning_kf_700    
        engine_dt_warning_amount_min= estimation_settings.engine_dt_warning_amount_min_700    
        gear_at_danger_kf           = estimation_settings.gear_at_danger_kf_700 
        gear_at_danger_amount_min   = estimation_settings.gear_at_danger_amount_min_700 
        gear_at_warning_kf          = estimation_settings.gear_at_warning_kf_700  
        gear_at_warning_amount_min  = estimation_settings.gear_at_warning_amount_min_700  
        gear_amt_danger_kf          = estimation_settings.gear_amt_danger_kf_700  
        gear_amt_danger_amount_min  = estimation_settings.gear_amt_danger_amount_min_700  
        gear_amt_warning_kf         = estimation_settings.gear_amt_warning_kf_700   
        gear_amt_warning_amount_min = estimation_settings.gear_amt_warning_amount_min_700   
        gear_cvt_danger_kf          = estimation_settings.gear_cvt_danger_kf_700  
        gear_cvt_danger_amount_min  = estimation_settings.gear_cvt_danger_amount_min_700  
        gear_cvt_warning_kf         = estimation_settings.gear_cvt_warning_kf_700   
        gear_cvt_warning_amount_min = estimation_settings.gear_cvt_warning_amount_min_700   
        gear_mt_danger_kf           = estimation_settings.gear_mt_danger_kf_700 
        gear_mt_danger_amount_min   = estimation_settings.gear_mt_danger_amount_min_700 
        gear_mt_warning_kf          = estimation_settings.gear_mt_warning_kf_700     
        gear_mt_warning_amount_min  = estimation_settings.gear_mt_warning_amount_min_700   
        suspension_danger_kf        = estimation_settings.suspension_danger_kf_700   
        suspension_danger_amount_min= estimation_settings.suspension_danger_amount_min_700       
        suspension_warning_kf        = estimation_settings.suspension_warning_kf_700        
        suspension_warning_amount_min= estimation_settings.suspension_warning_amount_min_700       
        system_og_danger_kf          = estimation_settings.system_og_danger_kf_700     
        system_og_danger_amount_min  = estimation_settings.system_og_danger_amount_min_700     
        system_og_warning_kf         = estimation_settings.system_og_warning_kf_700      
        system_og_warning_amount_min = estimation_settings.system_og_warning_amount_min_700
    elif zna < 1200000:
        zg              = '1 200'
        fin_zg          = estimation_settings.percent_financity_1200
        day_sale_zg     = estimation_settings.days_stok_financity_1200
        kf              = dc.ratio_avtohub_txt_1200
        percent_ss      = dc.percent_txt_1200
        percent_torg    = dc.percent_torg_txt_1200
        zna_izp_kf      = estimation_settings.izp_1200
        zna_izp_type    = estimation_settings.izp_1200_v
        percent_sale_1C = dc.ratio_1с_test_price_1200
        percent_sale    = dc.ratio_avtohub_test_price_1200
        percent_sale_rdo= dc.ratio_avtohub_rdo_1200
        percent_sale_kor= dc.ratio_avtohub_kor_1200
        kf_auction      = estimation_settings.auction_kf_1200
        windshield      = estimation_settings.windshield_1200
        windshield_heat = estimation_settings.windshield_heat_1200
        light_pered     = estimation_settings.light_pered_1200
        light_pered_kf  = estimation_settings.light_pered_kf_1200
        light_zad       = estimation_settings.light_zad_1200
        light_zad_kf    = estimation_settings.light_zad_kf_1200
        battery         = estimation_settings.battery_1200
        engine_danger_kf            = estimation_settings.engine_danger_kf_1200            
        engine_danger_amount_min    = estimation_settings.engine_danger_amount_min_1200
        engine_warning_kf           = estimation_settings.engine_warning_kf_1200 
        engine_warning_amount_min   = estimation_settings.engine_warning_amount_min_1200 
        engine_dt_danger_kf         = estimation_settings.engine_dt_danger_kf_1200   
        engine_dt_danger_amount_min = estimation_settings.engine_dt_danger_amount_min_1200   
        engine_dt_warning_kf        = estimation_settings.engine_dt_warning_kf_1200    
        engine_dt_warning_amount_min= estimation_settings.engine_dt_warning_amount_min_1200    
        gear_at_danger_kf           = estimation_settings.gear_at_danger_kf_1200 
        gear_at_danger_amount_min   = estimation_settings.gear_at_danger_amount_min_1200 
        gear_at_warning_kf          = estimation_settings.gear_at_warning_kf_1200  
        gear_at_warning_amount_min  = estimation_settings.gear_at_warning_amount_min_1200  
        gear_amt_danger_kf          = estimation_settings.gear_amt_danger_kf_1200  
        gear_amt_danger_amount_min  = estimation_settings.gear_amt_danger_amount_min_1200  
        gear_amt_warning_kf         = estimation_settings.gear_amt_warning_kf_1200   
        gear_amt_warning_amount_min = estimation_settings.gear_amt_warning_amount_min_1200   
        gear_cvt_danger_kf          = estimation_settings.gear_cvt_danger_kf_1200  
        gear_cvt_danger_amount_min  = estimation_settings.gear_cvt_danger_amount_min_1200  
        gear_cvt_warning_kf         = estimation_settings.gear_cvt_warning_kf_1200   
        gear_cvt_warning_amount_min = estimation_settings.gear_cvt_warning_amount_min_1200   
        gear_mt_danger_kf           = estimation_settings.gear_mt_danger_kf_1200 
        gear_mt_danger_amount_min   = estimation_settings.gear_mt_danger_amount_min_1200 
        gear_mt_warning_kf          = estimation_settings.gear_mt_warning_kf_1200     
        gear_mt_warning_amount_min  = estimation_settings.gear_mt_warning_amount_min_1200   
        suspension_danger_kf        = estimation_settings.suspension_danger_kf_1200   
        suspension_danger_amount_min= estimation_settings.suspension_danger_amount_min_1200       
        suspension_warning_kf        = estimation_settings.suspension_warning_kf_1200        
        suspension_warning_amount_min= estimation_settings.suspension_warning_amount_min_1200       
        system_og_danger_kf          = estimation_settings.system_og_danger_kf_1200     
        system_og_danger_amount_min  = estimation_settings.system_og_danger_amount_min_1200     
        system_og_warning_kf         = estimation_settings.system_og_warning_kf_1200      
        system_og_warning_amount_min = estimation_settings.system_og_warning_amount_min_1200
    elif zna < 2000000:
        zg              = '2 000'
        fin_zg          = estimation_settings.percent_financity_2000
        day_sale_zg     = estimation_settings.days_stok_financity_2000
        kf              = dc.ratio_avtohub_txt_2000
        percent_ss      = dc.percent_txt_2000
        percent_torg    = dc.percent_torg_txt_2000
        zna_izp_kf      = estimation_settings.izp_2000
        zna_izp_type    = estimation_settings.izp_2000_v
        percent_sale_1C = dc.ratio_1с_test_price_2000
        percent_sale    = dc.ratio_avtohub_test_price_2000
        percent_sale_rdo= dc.ratio_avtohub_rdo_2000
        percent_sale_kor= dc.ratio_avtohub_kor_2000
        kf_auction      = estimation_settings.auction_kf_2000
        windshield      = estimation_settings.windshield_2000
        windshield_heat = estimation_settings.windshield_heat_2000
        light_pered     = estimation_settings.light_pered_2000
        light_pered_kf  = estimation_settings.light_pered_kf_2000
        light_zad       = estimation_settings.light_zad_2000
        light_zad_kf    = estimation_settings.light_zad_kf_2000
        battery         = estimation_settings.battery_2000
        engine_danger_kf            = estimation_settings.engine_danger_kf_2000            
        engine_danger_amount_min    = estimation_settings.engine_danger_amount_min_2000
        engine_warning_kf           = estimation_settings.engine_warning_kf_2000 
        engine_warning_amount_min   = estimation_settings.engine_warning_amount_min_2000 
        engine_dt_danger_kf         = estimation_settings.engine_dt_danger_kf_2000   
        engine_dt_danger_amount_min = estimation_settings.engine_dt_danger_amount_min_2000   
        engine_dt_warning_kf        = estimation_settings.engine_dt_warning_kf_2000    
        engine_dt_warning_amount_min= estimation_settings.engine_dt_warning_amount_min_2000    
        gear_at_danger_kf           = estimation_settings.gear_at_danger_kf_2000 
        gear_at_danger_amount_min   = estimation_settings.gear_at_danger_amount_min_2000 
        gear_at_warning_kf          = estimation_settings.gear_at_warning_kf_2000  
        gear_at_warning_amount_min  = estimation_settings.gear_at_warning_amount_min_2000  
        gear_amt_danger_kf          = estimation_settings.gear_amt_danger_kf_2000  
        gear_amt_danger_amount_min  = estimation_settings.gear_amt_danger_amount_min_2000  
        gear_amt_warning_kf         = estimation_settings.gear_amt_warning_kf_2000   
        gear_amt_warning_amount_min = estimation_settings.gear_amt_warning_amount_min_2000   
        gear_cvt_danger_kf          = estimation_settings.gear_cvt_danger_kf_2000  
        gear_cvt_danger_amount_min  = estimation_settings.gear_cvt_danger_amount_min_2000  
        gear_cvt_warning_kf         = estimation_settings.gear_cvt_warning_kf_2000   
        gear_cvt_warning_amount_min = estimation_settings.gear_cvt_warning_amount_min_2000   
        gear_mt_danger_kf           = estimation_settings.gear_mt_danger_kf_2000 
        gear_mt_danger_amount_min   = estimation_settings.gear_mt_danger_amount_min_2000 
        gear_mt_warning_kf          = estimation_settings.gear_mt_warning_kf_2000     
        gear_mt_warning_amount_min  = estimation_settings.gear_mt_warning_amount_min_2000   
        suspension_danger_kf        = estimation_settings.suspension_danger_kf_2000   
        suspension_danger_amount_min= estimation_settings.suspension_danger_amount_min_2000       
        suspension_warning_kf        = estimation_settings.suspension_warning_kf_2000        
        suspension_warning_amount_min= estimation_settings.suspension_warning_amount_min_2000       
        system_og_danger_kf          = estimation_settings.system_og_danger_kf_2000     
        system_og_danger_amount_min  = estimation_settings.system_og_danger_amount_min_2000     
        system_og_warning_kf         = estimation_settings.system_og_warning_kf_2000      
        system_og_warning_amount_min = estimation_settings.system_og_warning_amount_min_2000
    elif zna < 3000000:
        zg              = '3 000'
        fin_zg          = estimation_settings.percent_financity_3000
        day_sale_zg     = estimation_settings.days_stok_financity_3000
        kf              = dc.ratio_avtohub_txt_3000
        percent_ss      = dc.percent_txt_3000
        percent_torg    = dc.percent_torg_txt_3000
        zna_izp_kf      = estimation_settings.izp_3000
        zna_izp_type    = estimation_settings.izp_3000_v
        percent_sale_1C = dc.ratio_1с_test_price_3000
        percent_sale    = dc.ratio_avtohub_test_price_3000
        percent_sale_rdo= dc.ratio_avtohub_rdo_3000
        percent_sale_kor= dc.ratio_avtohub_kor_3000
        kf_auction      = estimation_settings.auction_kf_3000
        windshield      = estimation_settings.windshield_3000
        windshield_heat = estimation_settings.windshield_heat_3000
        light_pered     = estimation_settings.light_pered_3000
        light_pered_kf  = estimation_settings.light_pered_kf_3000
        light_zad       = estimation_settings.light_zad_3000
        light_zad_kf    = estimation_settings.light_zad_kf_3000
        battery         = estimation_settings.battery_3000
        engine_danger_kf            = estimation_settings.engine_danger_kf_3000            
        engine_danger_amount_min    = estimation_settings.engine_danger_amount_min_3000
        engine_warning_kf           = estimation_settings.engine_warning_kf_3000 
        engine_warning_amount_min   = estimation_settings.engine_warning_amount_min_3000 
        engine_dt_danger_kf         = estimation_settings.engine_dt_danger_kf_3000   
        engine_dt_danger_amount_min = estimation_settings.engine_dt_danger_amount_min_3000   
        engine_dt_warning_kf        = estimation_settings.engine_dt_warning_kf_3000    
        engine_dt_warning_amount_min= estimation_settings.engine_dt_warning_amount_min_3000    
        gear_at_danger_kf           = estimation_settings.gear_at_danger_kf_3000 
        gear_at_danger_amount_min   = estimation_settings.gear_at_danger_amount_min_3000 
        gear_at_warning_kf          = estimation_settings.gear_at_warning_kf_3000  
        gear_at_warning_amount_min  = estimation_settings.gear_at_warning_amount_min_3000  
        gear_amt_danger_kf          = estimation_settings.gear_amt_danger_kf_3000  
        gear_amt_danger_amount_min  = estimation_settings.gear_amt_danger_amount_min_3000  
        gear_amt_warning_kf         = estimation_settings.gear_amt_warning_kf_3000   
        gear_amt_warning_amount_min = estimation_settings.gear_amt_warning_amount_min_3000   
        gear_cvt_danger_kf          = estimation_settings.gear_cvt_danger_kf_3000  
        gear_cvt_danger_amount_min  = estimation_settings.gear_cvt_danger_amount_min_3000  
        gear_cvt_warning_kf         = estimation_settings.gear_cvt_warning_kf_3000   
        gear_cvt_warning_amount_min = estimation_settings.gear_cvt_warning_amount_min_3000   
        gear_mt_danger_kf           = estimation_settings.gear_mt_danger_kf_3000 
        gear_mt_danger_amount_min   = estimation_settings.gear_mt_danger_amount_min_3000 
        gear_mt_warning_kf          = estimation_settings.gear_mt_warning_kf_3000     
        gear_mt_warning_amount_min  = estimation_settings.gear_mt_warning_amount_min_3000   
        suspension_danger_kf        = estimation_settings.suspension_danger_kf_3000   
        suspension_danger_amount_min= estimation_settings.suspension_danger_amount_min_3000       
        suspension_warning_kf        = estimation_settings.suspension_warning_kf_3000        
        suspension_warning_amount_min= estimation_settings.suspension_warning_amount_min_3000       
        system_og_danger_kf          = estimation_settings.system_og_danger_kf_3000     
        system_og_danger_amount_min  = estimation_settings.system_og_danger_amount_min_3000     
        system_og_warning_kf         = estimation_settings.system_og_warning_kf_3000      
        system_og_warning_amount_min = estimation_settings.system_og_warning_amount_min_3000
    elif zna < 5000000:
        zg              = '5 000'
        fin_zg          = estimation_settings.percent_financity_5000
        day_sale_zg     = estimation_settings.days_stok_financity_5000
        kf              = dc.ratio_avtohub_txt_5000
        percent_ss      = dc.percent_txt_5000
        percent_torg    = dc.percent_torg_txt_5000
        zna_izp_kf      = estimation_settings.izp_5000
        zna_izp_type    = estimation_settings.izp_5000_v
        percent_sale_1C = dc.ratio_1с_test_price_5000
        percent_sale    = dc.ratio_avtohub_test_price_5000
        percent_sale_rdo= dc.ratio_avtohub_rdo_5000
        percent_sale_kor= dc.ratio_avtohub_kor_5000
        kf_auction      = estimation_settings.auction_kf_5000
        windshield      = estimation_settings.windshield_5000
        windshield_heat = estimation_settings.windshield_heat_5000
        light_pered     = estimation_settings.light_pered_5000
        light_pered_kf  = estimation_settings.light_pered_kf_5000
        light_zad       = estimation_settings.light_zad_5000
        light_zad_kf    = estimation_settings.light_zad_kf_5000
        battery         = estimation_settings.battery_5000
        engine_danger_kf            = estimation_settings.engine_danger_kf_5000            
        engine_danger_amount_min    = estimation_settings.engine_danger_amount_min_5000
        engine_warning_kf           = estimation_settings.engine_warning_kf_5000 
        engine_warning_amount_min   = estimation_settings.engine_warning_amount_min_5000 
        engine_dt_danger_kf         = estimation_settings.engine_dt_danger_kf_5000   
        engine_dt_danger_amount_min = estimation_settings.engine_dt_danger_amount_min_5000   
        engine_dt_warning_kf        = estimation_settings.engine_dt_warning_kf_5000    
        engine_dt_warning_amount_min= estimation_settings.engine_dt_warning_amount_min_5000    
        gear_at_danger_kf           = estimation_settings.gear_at_danger_kf_5000 
        gear_at_danger_amount_min   = estimation_settings.gear_at_danger_amount_min_5000 
        gear_at_warning_kf          = estimation_settings.gear_at_warning_kf_5000  
        gear_at_warning_amount_min  = estimation_settings.gear_at_warning_amount_min_5000  
        gear_amt_danger_kf          = estimation_settings.gear_amt_danger_kf_5000  
        gear_amt_danger_amount_min  = estimation_settings.gear_amt_danger_amount_min_5000  
        gear_amt_warning_kf         = estimation_settings.gear_amt_warning_kf_5000   
        gear_amt_warning_amount_min = estimation_settings.gear_amt_warning_amount_min_5000   
        gear_cvt_danger_kf          = estimation_settings.gear_cvt_danger_kf_5000  
        gear_cvt_danger_amount_min  = estimation_settings.gear_cvt_danger_amount_min_5000  
        gear_cvt_warning_kf         = estimation_settings.gear_cvt_warning_kf_5000   
        gear_cvt_warning_amount_min = estimation_settings.gear_cvt_warning_amount_min_5000   
        gear_mt_danger_kf           = estimation_settings.gear_mt_danger_kf_5000 
        gear_mt_danger_amount_min   = estimation_settings.gear_mt_danger_amount_min_5000 
        gear_mt_warning_kf          = estimation_settings.gear_mt_warning_kf_5000     
        gear_mt_warning_amount_min  = estimation_settings.gear_mt_warning_amount_min_5000   
        suspension_danger_kf        = estimation_settings.suspension_danger_kf_5000   
        suspension_danger_amount_min= estimation_settings.suspension_danger_amount_min_5000       
        suspension_warning_kf        = estimation_settings.suspension_warning_kf_5000        
        suspension_warning_amount_min= estimation_settings.suspension_warning_amount_min_5000       
        system_og_danger_kf          = estimation_settings.system_og_danger_kf_5000     
        system_og_danger_amount_min  = estimation_settings.system_og_danger_amount_min_5000     
        system_og_warning_kf         = estimation_settings.system_og_warning_kf_5000      
        system_og_warning_amount_min = estimation_settings.system_og_warning_amount_min_5000
    else:
        zg              = '5 000+'
        fin_zg          = estimation_settings.percent_financity_5001
        day_sale_zg     = estimation_settings.days_stok_financity_5001
        kf              = dc.ratio_avtohub_txt_5001
        percent_ss      = dc.percent_txt_5001
        percent_torg    = dc.percent_torg_txt_5001
        zna_izp_kf      = estimation_settings.izp_5001
        zna_izp_type    = estimation_settings.izp_5001_v
        percent_sale_1C = dc.ratio_1с_test_price_5001
        percent_sale    = dc.ratio_avtohub_test_price_5001
        percent_sale_rdo= dc.ratio_avtohub_rdo_5001
        percent_sale_kor= dc.ratio_avtohub_kor_5001
        kf_auction      = estimation_settings.auction_kf_5001
        windshield      = estimation_settings.windshield_5001
        windshield_heat = estimation_settings.windshield_heat_5001
        light_pered     = estimation_settings.light_pered_5001
        light_pered_kf  = estimation_settings.light_pered_kf_5001
        light_zad       = estimation_settings.light_zad_5001
        light_zad_kf    = estimation_settings.light_zad_kf_5001
        battery         = estimation_settings.battery_5001
        engine_danger_kf            = estimation_settings.engine_danger_kf_5001            
        engine_danger_amount_min    = estimation_settings.engine_danger_amount_min_5001
        engine_warning_kf           = estimation_settings.engine_warning_kf_5001 
        engine_warning_amount_min   = estimation_settings.engine_warning_amount_min_5001 
        engine_dt_danger_kf         = estimation_settings.engine_dt_danger_kf_5001   
        engine_dt_danger_amount_min = estimation_settings.engine_dt_danger_amount_min_5001   
        engine_dt_warning_kf        = estimation_settings.engine_dt_warning_kf_5001    
        engine_dt_warning_amount_min= estimation_settings.engine_dt_warning_amount_min_5001    
        gear_at_danger_kf           = estimation_settings.gear_at_danger_kf_5001 
        gear_at_danger_amount_min   = estimation_settings.gear_at_danger_amount_min_5001 
        gear_at_warning_kf          = estimation_settings.gear_at_warning_kf_5001  
        gear_at_warning_amount_min  = estimation_settings.gear_at_warning_amount_min_5001  
        gear_amt_danger_kf          = estimation_settings.gear_amt_danger_kf_5001  
        gear_amt_danger_amount_min  = estimation_settings.gear_amt_danger_amount_min_5001  
        gear_amt_warning_kf         = estimation_settings.gear_amt_warning_kf_5001   
        gear_amt_warning_amount_min = estimation_settings.gear_amt_warning_amount_min_5001   
        gear_cvt_danger_kf          = estimation_settings.gear_cvt_danger_kf_5001  
        gear_cvt_danger_amount_min  = estimation_settings.gear_cvt_danger_amount_min_5001  
        gear_cvt_warning_kf         = estimation_settings.gear_cvt_warning_kf_5001   
        gear_cvt_warning_amount_min = estimation_settings.gear_cvt_warning_amount_min_5001   
        gear_mt_danger_kf           = estimation_settings.gear_mt_danger_kf_5001 
        gear_mt_danger_amount_min   = estimation_settings.gear_mt_danger_amount_min_5001 
        gear_mt_warning_kf          = estimation_settings.gear_mt_warning_kf_5001     
        gear_mt_warning_amount_min  = estimation_settings.gear_mt_warning_amount_min_5001   
        suspension_danger_kf        = estimation_settings.suspension_danger_kf_5001   
        suspension_danger_amount_min= estimation_settings.suspension_danger_amount_min_5001       
        suspension_warning_kf        = estimation_settings.suspension_warning_kf_5001        
        suspension_warning_amount_min= estimation_settings.suspension_warning_amount_min_5001       
        system_og_danger_kf          = estimation_settings.system_og_danger_kf_5001     
        system_og_danger_amount_min  = estimation_settings.system_og_danger_amount_min_5001     
        system_og_warning_kf         = estimation_settings.system_og_warning_kf_5001      
        system_og_warning_amount_min = estimation_settings.system_og_warning_amount_min_5001

    if percent_torg < 0:
        percent_torg = percent_torg * -1

    if percent_ss < 0:
        percent_ss = percent_ss * -1
                                            
    price = zna 
    # повышенный износ / такси
    if estimation.iznos and estimation.taxi:
        price_new  = price - (price * 40 / 100)
        diff       = price - price_new
        price = price_new
        inf_price = {
            'price'     : price,
            'dif'       : diff,
            'comment'   : "Цена скоректирована c учетом повышенного износа и использования в такси",  
            'name'      : "износ"
        }
        list_info_price.append(inf_price)
        auction = True
        auction_comment = auction_comment + "Повышенный износ и использование в такси. Коэфицент 0.6."
        auction_success = True
    elif estimation.iznos:
        price_new  = price - (price * 10 / 100)
        diff       = price - price_new
        price = price_new
        inf_price = {
            'price'     : price,
            'dif'       : diff,
            'comment'  : "Цена скоректирована c учетом повышенного износа",  
            'name'      : "износ" 
        }
        iznos_price = diff
        list_info_price.append(inf_price)

    #Считаем авто в продаже 
    price_sale_rdo = 0
    price_sale_kor = 0
    if type_calculation == 'kors':
        price_sale      = price *  percent_sale_1C / 100
        price_sale_rdo  = price * percent_sale_rdo / 100
        price_sale_kor  = price *  percent_sale_kor / 100
        
    if type_calculation == 'autohub':
        price_sale = price * percent_sale / 100
        price_sale_rdo  = price * percent_sale_rdo / 100
        price_sale_kor  = price *  percent_sale_kor / 100
        
    elif type_calculation == 'avito':
        price_sale = price * percent_sale / 100
        price_sale_rdo  = price * percent_sale_rdo/ 100
        price_sale_kor  = price *  percent_sale_kor / 100
        
    elif type_calculation == 'custom':
        price_sale = price *  percent_sale_1C / 100
        price_sale_rdo  = price * percent_sale_rdo / 100
        price_sale_kor  = price *  percent_sale_kor / 100
    
    #Считаем авто в токсичке
    price_old       = price
    price           = price - (price * (100 - kf) / 100) 
    diff            = (price_old * (100 - kf) / 100)
    inf_price = {
        'price'     : price,
        'dif'       : diff,
        'comment'   : "ЦНА * ИРЦ ТХТ / посчитана цена с учетом продажи в токсичном стоке",
        'name'      : "цена в токсичной продаже"
    }
    list_info_price.append(inf_price)
    
    #Cчитаем с защитой от убытка
    price_old       = price
    price           = price - (price * percent_ss / 100) 
    diff            = (price_old * percent_ss / 100)
    inf_price = {
        'price'     : price,
        'dif'       : diff,
        'comment'   : "Цена с учетом защиты от убытка CC " + str(percent_ss) + " %",
        'name'      : "защита от убытка"   
    }
    zachita_ot_ubitka = diff
    list_info_price.append(inf_price)
    
    # cчитаем с защитой от скидкой торг
    price_old       = price
    price           = price - (price * percent_torg / 100) 
    diff            = (price_old * percent_torg / 100)
    inf_price = {
        'price'     : price,
        'dif'       : diff,
        'comment'   : "Цена с учетом защиты скидки торг " + str(percent_torg) + " %",
        'name'      : "скидка торг"  
    }
    list_info_price.append(inf_price)


    # продажи и статистика корсавто
    # пока убрали
    #if estimation.kors_sale_cost_price_avg > 0:
    #    price_new   = (price + estimation.kors_sale_cost_price_avg) / 2
    #    diff        = price - price_new
    #    if diff > 0:
    #        price = price_new
    #        inf_price = {
    #            'price'     : price,
    #            'dif'       : diff,
    #            'comment'   : "Цена скоректирована c учетом истории продаж аналогичных АМ КорсАвто",  
    #            'name'      : "история корсавто"  
    #        }
    #        list_info_price.append(inf_price)

    # расчеты ремонта
    if estimation.avtoteka_car_autodex > 0:
        price           = price - (estimation.avtoteka_car_autodex / 2)
        diff            = estimation.avtoteka_car_autodex / 2
        inf_price = {
            'price'     : price,
            'dif'       : diff,
            'comment'   : "Цена скоректирована на основании суммы ремонтов / 2",  
            'name'      : "расчеты ремонтов"   
        }
        list_info_price.append(inf_price)
    
    if estimation.page_salon != None:
    
    # Химчистка +
        if estimation.page_salon.cleaning_int == 1:
            work = RegPodgotovkaWork.objects.get(pk = 117) 
            diff = work.price_kors 
            dop = {
                'name'      : work.name_group + " / " +  work.name,
                'quantity'  : work.normo,
                'amount_pod': work.price_podrad,   
                'amount'    : diff
            }
            list_work_podgotovka.append(dop)  
            amount_podgotovka = amount_podgotovka + diff
        elif estimation.page_salon.cleaning_int == 2:
            work = RegPodgotovkaWork.objects.get(pk = 116) 
            diff = work.price_kors 
            dop = {
                'name'      : work.name_group + " / " +  work.name,
                'quantity'  : work.normo,
                'amount_pod': work.price_podrad,   
                'amount'    : diff
            }
            list_work_podgotovka.append(dop)  
            amount_podgotovka = amount_podgotovka + diff
        elif estimation.page_salon.cleaning_int == 3:
            work = RegPodgotovkaWork.objects.get(pk = 115) 
            diff = work.price_kors 
            dop = {
                'name'      : work.name_group + " / " +  work.name,
                'quantity'  : work.normo,
                'amount_pod': work.price_podrad,   
                'amount'    : diff
            }
            list_work_podgotovka.append(dop)  
            amount_podgotovka = amount_podgotovka + diff
            
        #Рычаг КПП +
        if estimation.page_salon.damage_kpp_int == 1:
            diff_sum = 0
            work = RegPodgotovkaWork.objects.get(pk = 66) 
            diff_sum = diff_sum + work.price_kors 
            dop = {
                'name'      : work.name_group + " / " +  work.name,
                'quantity'  : work.normo,
                'amount_pod': work.price_podrad,   
                'amount'    : work.price_kors
            }
            list_work_podgotovka.append(dop)  
            work = RegPodgotovkaWork.objects.get(pk = 67) 
            diff_sum = diff_sum + work.price_kors 
            dop = {
                'name'      : work.name_group + " / " +  work.name,
                'quantity'  : work.normo,
                'amount_pod': work.price_podrad,   
                'amount'    : work.price_kors
            }
            list_work_podgotovka.append(dop)  
            amount_podgotovka = amount_podgotovka + diff_sum

        #Руль +
        if estimation.page_salon.damage_wheel_int == 1:
            diff_sum = 0
            work = RegPodgotovkaWork.objects.get(pk = 96) 
            diff_sum = diff_sum + work.price_kors 
            dop = {
                'name'      : work.name_group + " / " +  work.name,
                'quantity'  : work.normo,
                'amount_pod': work.price_podrad,   
                'amount'    : work.price_kors
            }
            list_work_podgotovka.append(dop)  
            work = RegPodgotovkaWork.objects.get(pk = 99) 
            diff_sum = diff_sum + work.price_kors 
            dop = {
                'name'      : work.name_group + " / " +  work.name,
                'quantity'  : work.normo,
                'amount_pod': work.price_podrad,   
                'amount'    : work.price_kors
            }
            list_work_podgotovka.append(dop)  
            amount_podgotovka = amount_podgotovka + diff_sum

        if estimation.page_salon.damage_pedal_int == 1:
            price           = price - estimation_settings.damage_pedal_int
            diff            = estimation_settings.damage_pedal_int
            inf_price = {
                'price'     : price,
                'dif'       : diff,
                'comment'   : "Цена скоректирована повреждений / затертости педалей",  
                'name'      : "салон - педали"  
            }
            list_info_price.append(inf_price)
            amount_podgotovka = amount_podgotovka + diff

        if estimation.page_salon.damage_door_int == 1:
            price           = price - estimation_settings.damage_door_int
            diff            = estimation_settings.damage_door_int
            inf_price = {
                'price'     : price,
                'dif'       : diff,
                'comment'   : "Цена скоректирована повреждений / затертости дверей",
                'name'      : 'неопределено'  
            }
            list_info_price.append(inf_price)
            amount_podgotovka = amount_podgotovka + diff
        
        if estimation.page_salon.damage_seat_int == 1:
            price           = price - estimation_settings.damage_seat_int
            diff            = estimation_settings.damage_seat_int
            inf_price = {
                'price'     : price,
                'dif'       : diff,
                'comment'  : "Цена скоректирована повреждений / затертости сидений",
                'name'      : 'неопределено'  
            }
            list_info_price.append(inf_price) 
            amount_podgotovka = amount_podgotovka + diff 

        if estimation.page_salon.hand_brake == 0:
            price           = price - estimation_settings.hand_brake
            diff            = estimation_settings.hand_brake
            inf_price = {
                'price'     : price,
                'dif'       : diff,
                'comment'  : "Цена скоректирована с учетом не работающего ручного тормоза",
                'name'      : 'неопределено'  
            }
            list_info_price.append(inf_price)  

        if estimation.page_salon.conductor == 0:
            price           = price - estimation_settings.conductor
            diff            = estimation_settings.conductor
            inf_price = {
                'price'     : price,
                'dif'       : diff,
                'comment'  : "Цена скоректирована с учетом не работающего кондиционера",
                'name'      : 'неопределено'  
            }
            list_info_price.append(inf_price) 
        
        if estimation.page_salon.wiper == 0:
            price           = price - estimation_settings.wiper
            diff            = estimation_settings.wiper
            inf_price = {
                'price'     : price,
                'dif'       : diff,
                'comment'  : "Цена скоректирована с учетом не работающего стеклоочистителей",
                'name'      : 'неопределено'  
            }
            list_info_price.append(inf_price)

        if estimation.page_salon.signal == 0:
            price           = price - estimation_settings.signal
            diff            = estimation_settings.signal
            inf_price = {
                'price'     : price,
                'dif'       : diff,
                'comment'  : "Цена скоректирована с учетом не работающего сигнала",
                'name'      : 'неопределено'  
            }
            list_info_price.append(inf_price)

        if estimation.page_salon.power_windows == 0:
            price           = price - estimation_settings.power_windows
            diff            = estimation_settings.power_windows
            inf_price = {
                'price'     : price,
                'dif'       : diff,
                'comment'  : "Цена скоректирована с учетом не работающющих стеклоподъемников",
                'name'      : 'неопределено'  
            }
            list_info_price.append(inf_price)   

        if estimation.page_salon.seat_belt == 0:
            price           = price - estimation_settings.seat_belt
            diff            = estimation_settings.seat_belt
            inf_price = {
                'price'     : price,
                'dif'       : diff,
                'comment'  : "Цена скоректирована с учетом не работающющих ремней безопастности",
                'name'      : 'неопределено'  
            }
            list_info_price.append(inf_price)      

    
    # двигатель
    if estimation.page_test_drive != None and estimation.page_test_drive.engine == 0:
        
        info_diff = ''
        price_diff = 0
        if modification.typeEngine.id == 1:
            price_diff  = (price * engine_danger_kf / 100)
            info_diff   = 'Бензиновый двигатель сумма ремонта в процентах ' +  str(engine_danger_kf)

            if price_diff < engine_danger_amount_min:
                price_diff  = engine_danger_amount_min
                info_diff   = 'Бензиновый двигатель сумма ремонта минимальное значение ' +  str(engine_danger_amount_min)
        else:
            price_diff  = (price * engine_dt_danger_kf / 100)
            info_diff   = 'Дизельный двигатель сумма ремонта в процентах ' +  str(engine_dt_danger_kf)

            if price_diff < engine_dt_danger_amount_min:
                price_diff  = engine_dt_danger_amount_min
                info_diff   = 'Дизельный двигатель сумма ремонта минимальное значение ' +  str(engine_dt_danger_amount_min)
        dop = {
            'name'      : info_diff,
            'quantity'  : 0,
            'amount_pod': 0, 
            'amount'    : price_diff
        }
        list_work_service.append(dop)
        amount_ss = amount_ss + price_diff

    if estimation.page_test_drive != None and estimation.page_test_drive.engine == 2:
        
        info_diff = ''
        price_diff = 0
        
        if modification.typeEngine.id == 1:  
            price_diff = (price * engine_warning_kf / 100)
            info_diff   = 'Бензиновый двигатель сумма ремонта в процентах ' +  str(engine_warning_kf)
            
            if price_diff < engine_warning_amount_min:
                price_diff = engine_warning_amount_min
                info_diff   = 'Бензиновый двигатель сумма ремонта минимальное значение ' +  str(engine_warning_amount_min)
        else:
        
            price_diff = (price * engine_dt_warning_kf / 100)
            info_diff   = 'Дизельный двигатель сумма ремонта в процентах ' +  str(engine_dt_warning_kf)

            if price_diff < engine_dt_warning_amount_min:
                price_diff = engine_dt_warning_amount_min
                info_diff   = 'Дизельный двигатель сумма ремонта минимальное значение ' +  str(engine_dt_warning_amount_min)

        dop = {
            'name'      : info_diff,
            'quantity'  : 0,
            'amount_pod': 0, 
            'amount'    : price_diff
        }
        list_work_service.append(dop)
        amount_ss = amount_ss + price_diff

    # кпп
    if estimation.page_test_drive != None and estimation.page_test_drive.gear == 0:
        
        info_diff = ''
        price_diff = 0
        
        if modification.typeGear.id == 1:
            price_diff = (price * gear_amt_danger_kf / 100)
            info_diff   = 'Робот сумма ремонта в процентах ' +  str(gear_amt_danger_kf)

            if price_diff < gear_amt_danger_amount_min:
                price_diff = gear_amt_danger_amount_min
                info_diff   = 'Робот сумма ремонта минимальное значение ' +  str(gear_amt_danger_amount_min)

        elif modification.typeGear.id == 2:
            price_diff = (price * gear_mt_danger_kf / 100)
            info_diff   = 'Механика сумма ремонта в процентах ' +  str(gear_mt_danger_kf)

            if price_diff < gear_mt_danger_amount_min:
                price_diff = gear_mt_danger_amount_min
                info_diff   = 'Механика сумма ремонта минимальное значение ' +  str(gear_mt_danger_amount_min)

        elif modification.typeGear.id == 3:
            price_diff = (price * gear_at_danger_kf / 100)
            info_diff   = 'Автомат сумма ремонта в процентах ' +  str(gear_at_danger_kf)
            if price_diff < gear_at_danger_amount_min:
                price_diff = gear_at_danger_amount_min
                info_diff   = 'Автомат сумма ремонта минимальное значение ' +  str(gear_at_danger_amount_min)

        elif modification.typeGear.id == 4:
            price_diff = (price * gear_cvt_danger_kf / 100)
            info_diff   = 'Вариатор сумма ремонта в процентах ' +  str(gear_cvt_danger_kf)

            if price_diff < gear_cvt_danger_amount_min:
                price_diff = gear_cvt_danger_amount_min
                info_diff   = 'Вариатор сумма ремонта минимальное значение ' +  str(gear_cvt_danger_amount_min)

        dop = {
            'name'      : info_diff,
            'quantity'  : 0,
            'amount_pod': 0, 
            'amount'    : price_diff
        }
        list_work_service.append(dop)
        amount_ss = amount_ss + price_diff

    if estimation.page_test_drive != None and estimation.page_test_drive.gear == 2:
        
        price_diff = 0
        info_diff = ''

        if modification.typeGear.id == 1:
            
            price_diff = (price * gear_amt_warning_kf / 100)
            info_diff   = 'Робот сумма ремонта в процентах ' +  str(gear_amt_warning_kf)

            if price_diff < gear_amt_warning_amount_min:
                price_diff = gear_amt_warning_amount_min
                info_diff   = 'Робот сумма ремонта минимальное значение ' +  str(gear_amt_warning_amount_min)

        elif modification.typeGear.id == 2:
            
            price_diff = (price * gear_mt_warning_kf / 100)
            info_diff   = 'Механика сумма ремонта в процентах ' +  str(gear_mt_warning_kf)

            if price_diff < gear_mt_warning_amount_min:
                price_diff = gear_mt_warning_amount_min
                info_diff   = 'Механика сумма ремонта минимальное значение ' +  str(gear_mt_warning_amount_min)

        elif modification.typeGear.id == 3:
            
            price_diff = (price * gear_at_warning_kf / 100)
            info_diff   = 'Автомат сумма ремонта в процентах ' +  str(gear_at_warning_kf)

            if price_diff < gear_at_warning_amount_min:
                price_diff = gear_at_warning_amount_min
                info_diff   = 'Автомат сумма ремонта минимальное значение ' +  str(gear_at_warning_amount_min)
        
        elif modification.typeGear.id == 4:
            
            price_diff = (price * gear_cvt_warning_kf / 100)
            info_diff   = 'Вариатор сумма ремонта в процентах ' +  str(gear_cvt_warning_kf)

            if price_diff < gear_cvt_warning_amount_min:
                price_diff = gear_cvt_warning_amount_min
                info_diff   = 'Вариатор сумма ремонта минимальное значение ' +  str(gear_cvt_warning_amount_min)
        
        dop = {
            'name'      : info_diff,
            'quantity'  : 0,
            'amount_pod': 0, 
            'amount'    : price_diff
        }
        list_work_service.append(dop)
        amount_ss = amount_ss + price_diff
    
    # подвеска
    if estimation.page_test_drive != None and estimation.page_test_drive.suspension == 0:
        
        info_diff = ''
        price_diff = 0
        price_diff = (price * suspension_danger_kf / 100)
        info_diff   = 'Сумма ремонта в процентах ' +  str(suspension_danger_kf)

        if price_diff < suspension_danger_amount_min:
            price_diff = suspension_danger_amount_min
            info_diff   = 'Сумма ремонта минимальное значение ' +  str(suspension_danger_amount_min)

        dop = {
            'name'      : 'Подвеска ремонт неисправности',
            'quantity'  : 0,
            'amount_pod': 0, 
            'amount'    : price_diff
        }
        list_work_service.append(dop)  
        
        amount_ss = amount_ss + price_diff

    if estimation.page_test_drive != None and estimation.page_test_drive.suspension == 2:
        
        info_diff = ''
        price_diff = 0
        
        price_diff = (price * suspension_warning_kf / 100)
        info_diff   = 'Сумма ремонта в процентах ' +  str(suspension_warning_kf)

        if price_diff < suspension_warning_amount_min:
            price_diff = suspension_warning_amount_min
            info_diff   = 'Сумма ремонта минимальное значение ' +  str(suspension_warning_amount_min)

        dop = {
            'name'      : 'Подвеска устранение замечаний',
            'quantity'  : 0,
            'amount_pod': 0, 
            'amount'    : price_diff
        }
        list_work_service.append(dop) 
        amount_ss = amount_ss + price_diff

    # система выпуска ог
    if estimation.page_test_drive != None and estimation.page_test_drive.system_og == 0:
        
        info_diff = ''
        price_diff = 0
        price_diff = (price * system_og_danger_kf / 100)
        info_diff   = 'Сумма ремонта в процентах ' +  str(system_og_danger_kf)

        if price_diff < system_og_danger_amount_min:
            price_diff = system_og_danger_amount_min
            info_diff   = 'Сумма ремонта минимальное значение ' +  str(system_og_danger_amount_min)

        dop = {
            'name'      : 'Система выпуска ОГ ремонт',
            'quantity'  : 0,
            'amount_pod': 0, 
            'amount'    : price_diff
        }
        list_work_service.append(dop) 
        amount_ss = amount_ss + price_diff

    if estimation.page_test_drive != None and estimation.page_test_drive.system_og == 2:
        info_diff = ''
        price_diff = 0
        price_diff = (price * system_og_warning_kf / 100)
        info_diff   = 'Сумма ремонта в процентах ' +  str(system_og_warning_kf)

        if price_diff < system_og_warning_amount_min:
            price_diff = system_og_warning_amount_min
            info_diff   = 'Сумма ремонта минимальное значение ' +  str(system_og_warning_amount_min)

        dop = {
            'name'      : 'Система выпуска ОГ устранение замечаний',
            'quantity'  : 0,
            'amount_pod': 0, 
            'amount'    : price_diff
        }
        list_work_service.append(dop) 
        amount_ss = amount_ss + price_diff


    kors_price_reception = 0
    if estimation.kors_count_sale > 0: 
        kors_price_reception = round(((estimation.kors_sale_cost_price_min + estimation.kors_sale_cost_price_max)  / 2) - estimation.kors_outlay_avg, -3)
    
    hub_sale_price_avg = 0
    if estimation.hub_sale_total > 0:
        hub_sale_price_avg = (estimation.hub_sale_price_min + estimation.hub_sale_price_max)  / 2 
    
    kors_hub_correction_sale = 0
    kors_hub_correction_store = 0
    count_hub = (estimation.hub_sale_total + estimation.hub_total) / 2

    hub_sale_price_avg = 0
    if estimation.hub_sale_total > 0:
        hub_sale_price_avg  = (estimation.hub_sale_price_min + estimation.hub_sale_price_max)  / 2 
    
    hub_price_avg = 0
    if estimation.hub_total > 0:
        hub_price_avg       = (estimation.hub_price_min + estimation.hub_price_max)  / 2

    if count_hub > 0:
        kors_hub_correction = round((kors_hub_correction_sale + kors_hub_correction_store) / 2 * 0.82, 0)
    
    ###Проверяем пробег
    run_ok = True
    if estimation.avtoteka_data != None and len(estimation.avtoteka_data) > 100:
        data_autoteka = json.loads(estimation.avtoteka_data)['result']['report']['data']
        eventsOthersHistory = data_autoteka.get('eventsOthersHistory')
        run         = 0
        run_other   = 0
        run_sum     = 0
        for event in eventsOthersHistory:
            if event['mileage'] > 0:
                run = event['mileage']
                if run_other > run:
                    if run_other - run > 20000:
                        run_ok = False
                        run_sum = run_sum + (run_other - run)
                        auction = True
                        auction_comment = auction_comment + 'Пробег автомобиля вызывает сомнения. (примерно на '  + str(run_sum) + ' км.)'
                run_other = run

    ###Проверяем требуется ли замена аккамулятора
    if battery > 0:
        try:
            if estimation.start_estimation.year - estimation.year > 4:
                diff_sum    = 0
                work        = 'Замена аккамулятора'
                diff_sum    = battery
                dop = {
                    'name'      : work,
                    'quantity'  : 1,
                    'amount_pod': diff_sum, 
                    'amount'    : diff_sum
                }
                list_work_podgotovka.append(dop)
                amount_podgotovka = amount_podgotovka + diff_sum 
        except:
            s = 1

    body_info = body_estimation(estimation)            
    elem_rzav = 0
    elem_rzav_data = ''
    for info in body_info['array']:
        if (info['name'] == 'фара правая' or info['name'] == 'фара левая') and info['all'] > 0:
            if info['poly'] > 0 and info['replace_add'] == 0 and info['tr'] == 0:
                diff_sum    = 0
                work        = RegPodgotovkaWork.objects.get(pk = 77)
                diff_sum    = work.price_kors
                dop = {
                    'name'      : info['name'].capitalize() + " / " + work.name_group + ' / ' +  work.name,
                    'quantity'  : work.normo,
                    'amount_pod': work.price_podrad, 
                    'amount'    : work.price_kors
                }
                list_work_podgotovka.append(dop)
                amount_podgotovka = amount_podgotovka + diff_sum 
            elif info['replace_add'] > 0:
                price_diff = (price * light_pered_kf / 100)
                info_diff   = info['name'].title() + ' / замена'

                if price_diff < light_pered:
                    price_diff = light_pered
                    info_diff   = info['name']
                work        = info_diff.title()
                diff_sum    = price_diff
                dop = {
                    'name'      : work,
                    'quantity'  : 1,
                    'amount_pod': diff_sum * 2, 
                    'amount'    : diff_sum * 2
                }
                list_work_mcu.append(dop)
                amount_mcu = amount_mcu + diff_sum
            else:
                price_diff = (price * light_pered_kf / 100)
                info_diff   = info['name'].title()

                if price_diff < light_pered:
                    price_diff = light_pered
                    info_diff   = info['name']
                work        = info_diff.title()
                diff_sum    = price_diff
                dop = {
                    'name'      : work,
                    'quantity'  : 1,
                    'amount_pod': diff_sum, 
                    'amount'    : diff_sum
                }
                list_work_mcu.append(dop)
                amount_mcu = amount_mcu + diff_sum
        elif (info['name'] == 'фонарь правый' or info['name'] == 'фонарь левый' ) and info['all'] > 0:
            if info['poly'] > 0 and info['replace_add'] == 0 and info['tr'] == 0:
                diff_sum    = 0
                work        = RegPodgotovkaWork.objects.get(pk = 77)
                diff_sum    = work.price_kors
                dop = {
                    'name'      : info['name'].capitalize() + " / " + work.name_group + ' / ' +  work.name,
                    'quantity'  : work.normo,
                    'amount_pod': work.price_podrad, 
                    'amount'    : work.price_kors
                }
                list_work_podgotovka.append(dop)
                amount_podgotovka = amount_podgotovka + diff_sum 
            elif info['replace_add'] > 0:
                price_diff = (price * light_zad_kf / 100)
                info_diff   = info['name'] + ' / замена'

                if price_diff < light_zad:
                    price_diff = light_zad
                    info_diff   = info['name']
                work        = info_diff.title()
                diff_sum    = price_diff
                dop = {
                    'name'      : work,
                    'quantity'  : 1,
                    'amount_pod': diff_sum, 
                    'amount'    : diff_sum
                }
                list_work_mcu.append(dop)
                amount_mcu = amount_mcu + diff_sum 
            else:
                price_diff = (price * light_zad_kf / 100)
                info_diff   = info['name']

                if price_diff < light_zad:
                    price_diff = light_zad
                    info_diff   = info['name']
                work        = info_diff.title()
                diff_sum    = price_diff
                dop = {
                    'name'      : work,
                    'quantity'  : 1,
                    'amount_pod': diff_sum, 
                    'amount'    : diff_sum
                }
                list_work_mcu.append(dop)
                amount_mcu = amount_mcu + diff_sum              
        elif (info['name'] == 'лобовое стекло') and info['all'] > 0:
            price_diff = windshield
            info_diff   = info['name']

            work        = info_diff.title()
            diff_sum    = price_diff
            dop = {
                'name'      : work,
                'quantity'  : 1,
                'amount_pod': diff_sum, 
                'amount'    : diff_sum
            }
            list_work_mcu.append(dop)
            amount_mcu = amount_mcu + diff_sum    
        else:
            if info['rzav_strong'] > 0:
                elem_rzav = elem_rzav + 1
                elem_rzav_data    = elem_rzav_data + info['name'] + "; "
            
            if info['vmyat_strong'] > 0 or info['carap_strong'] > 0 or info['rzav'] > 0 or info['rzav_strong'] > 0:
                if info['name'] == 'передний бампер':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 14)
                    diff_sum    = work.price_podrad
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum 
                elif info['name'] ==  'крыло заднее левое' or info['name'] ==  'крыло заднее правое':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 43)
                    diff_sum    = work.price_podrad
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
                elif info['name'] ==  'задний бампер':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 9)
                    diff_sum    = work.price_podrad
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
                elif info['name'] ==  'порог левый' or info['name'] ==  'порог правый':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 59)
                    diff_sum    = work.price_podrad
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
                elif info['name'] ==  'крыло переднее левое' or info['name'] ==  'крыло переднее правое':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 46)
                    diff_sum    = work.price_podrad
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
                elif info['name'] ==  'крыша':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 51)
                    diff_sum    = work.price_podrad
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
                elif info['name'] ==  'крышка багажника':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 4)
                    diff_sum    = work.price_podrad
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
                elif info['name'] ==  'дверь задняя левая' or info['name'] ==  'дверь задняя правая':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 24)
                    diff_sum    = work.price_podrad
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
                elif info['name'] ==  'дверь передняя левая' or info['name'] ==  'дверь передняя правая':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 28)
                    diff_sum    = work.price_podrad
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
                elif info['name'] ==  'капот':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 38)
                    diff_sum    = work.price_podrad
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_mcu.append(dop)
                    amount_mcu = amount_mcu + diff_sum
            elif info['vmyat'] > 0 or info['carap'] > 0:
                if info['name'] == 'передний бампер':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 16)
                    diff_sum    = work.price_kors
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_podgotovka.append(dop)
                    amount_podgotovka = amount_podgotovka + diff_sum 
                elif info['name'] ==  'крыло заднее левое' or info['name'] ==  'крыло заднее правое':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 45)
                    diff_sum    = work.price_kors
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_podgotovka.append(dop)
                    amount_podgotovka = amount_podgotovka + diff_sum
                elif info['name'] ==  'задний бампер':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 11)
                    diff_sum    = work.price_kors
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_podgotovka.append(dop)
                    amount_podgotovka = amount_podgotovka + diff_sum
                elif info['name'] ==  'порог левый' or info['name'] ==  'порог правый':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 61)
                    diff_sum    = work.price_kors
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_podgotovka.append(dop)
                    amount_podgotovka = amount_podgotovka + diff_sum
                elif info['name'] ==  'крыло переднее левое' or info['name'] ==  'крыло переднее правое':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 47)
                    diff_sum    = work.price_kors
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_podgotovka.append(dop)
                    amount_podgotovka = amount_podgotovka + diff_sum
                elif info['name'] ==  'крыша':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 52)
                    diff_sum    = work.price_kors
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_podgotovka.append(dop)
                    amount_podgotovka = amount_podgotovka + diff_sum
                elif info['name'] ==  'крышка багажника':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 5)
                    diff_sum    = work.price_kors
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_podgotovka.append(dop)
                    amount_podgotovka = amount_podgotovka + diff_sum
                elif info['name'] ==  'дверь задняя левая' or info['name'] ==  'дверь задняя правая':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 25)
                    diff_sum    = work.price_kors
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_podgotovka.append(dop)
                    amount_podgotovka = amount_podgotovka + diff_sum
                elif info['name'] ==  'дверь передняя левая' or info['name'] ==  'дверь передняя правая':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 29)
                    diff_sum    = work.price_kors
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_podgotovka.append(dop)
                    amount_podgotovka = amount_podgotovka + diff_sum
                elif info['name'] ==  'капот':
                    diff_sum    = 0
                    work        = RegPodgotovkaWork.objects.get(pk = 39)
                    diff_sum    = work.price_kors
                    dop = {
                        'name'      : work.name_group + ' / ' +  work.name,
                        'quantity'  : work.normo,
                        'amount_pod': work.price_podrad, 
                        'amount'    : work.price_kors
                    }
                    list_work_podgotovka.append(dop)
                    amount_podgotovka = amount_podgotovka + diff_sum
            
            if info['skol'] > 0 and info['vmyat_strong'] == 0 and info['carap_strong'] == 0 and info['rzav'] == 0 and info['rzav_strong'] == 0:
            
                diff_sum    = 0
                work        = RegPodgotovkaWork.objects.get(pk = 80)
                diff_sum    = work.price_kors
                dop = {
                    'name'      : info['name'].capitalize() + " / " + work.name_group + ' / ' +  work.name,
                    'quantity'  : work.normo,
                    'amount_pod': work.price_podrad, 
                    'amount'    : work.price_kors
                }
                list_work_podgotovka.append(dop)
                amount_podgotovka = amount_podgotovka + diff_sum 

    if elem_rzav > 3:
        auction = True
        auction_comment = auction_comment + " " + "3 более элемента с сквозной корозией (" +  elem_rzav_data +  "). "

    if amount_ss > 0:
        price           = price - amount_ss
        diff            = amount_ss
        inf_price = {
            'price'     : price,
            'dif'       : diff,
            'comment'   : "Цена скоректирована с учетом затрат на слесарный ремонт " + '{:0,.2f}'.format(diff).replace(',', ' ') + ' ₽',  
            'name'      : "слесарный"
        }
        list_info_price.append(inf_price)     

    if amount_podgotovka > 0:
        price           = price - amount_podgotovka
        diff            = amount_podgotovka
        inf_price = {
            'price'     : price,
            'dif'       : diff,
            'comment'   : "Цена скоректирована с учетом затрат на подготовку " + '{:0,.2f}'.format(diff).replace(',', ' ') + ' ₽',  
            'name'      : "подготовка"
        }
        list_info_price.append(inf_price)   

    if amount_mcu > 0:
        price           = price - amount_mcu
        diff            = amount_mcu
        inf_price = {
            'price'     : price,
            'dif'       : diff,
            'comment'   : "Цена скоректирована с учетом затрат на кузовной ремонт " + '{:0,.2f}'.format(diff).replace(',', ' ') + ' ₽',  
            'name'      : "кузовной"
        }
        list_info_price.append(inf_price)
    
    if auction_success == False and auction:
        price_new  = price - (price * (100 - kf_auction) / 100)
        diff       = price - price_new
        price = price_new
        inf_price = {
            'price'     : price,
            'dif'       : diff,
            'comment'  : "Цена скоректирована c учетом продажи АМ на АУКЦИОНЕ " + str(kf_auction) + "%"  
        }
        list_info_price.append(inf_price)

    #Финансирование
    if zna_type != '1C':
        #Проверяем корректировку ЦНА
        if zna_izp_type > 0:            
            #if zna_izp_type == 2 or zna_izp_type == 1 and estimation.kors_sale_cost_price_avg == 0:
            zna_type_name = ''
            if zna_izp_type == 1:
                zna_type_name = '""'
            else:
                zna_type_name = '""'
            price_old       = price
            day = day_sale_all
            if day_sale_zg > 0:
                day = day_sale_zg

            fin = fin_all
            if fin_zg > 0:
                fin = fin_zg

            if estimation.hub_days_in_stok_avg > 0:
                day = estimation.hub_sale_days_in_stok_avg
                #day = estimation.hub_days_in_stok_avg # Переключил по согласованию с Серебрянниковым, для расчета дней не текущего рынка а истории продаж
            
            finance = round(price * ((fin / 365) / 100) * day, 2) 
            
            price           = price - finance
            diff            = finance
            finance_price   = finance

            inf_price = {
                'price'     : price,
                'dif'       : diff,
                'comment'   : "Финансирование " + str(fin)  + "% для продажи авто за " + str(round(day)) + " дней, (вариант использования: " + zna_type_name + ")",
                'name'      : "финансирование"
            }
            '''
            price           = price - (price * zna_izp_kf / 100) 
            diff            = (price_old *  zna_izp_kf / 100)
            inf_price = {
                'price'     : price,
                'dif'       : diff,
                'comment'  : "ЦНА скоректирована на " + str(zna_izp_kf)  + "% (вариант использования: " + zna_type_name + ")"
            }
            '''
            list_info_price.append(inf_price)
    
    #ИТОГ
    estimation_price    = round(price, -2)
    amount_sum          = amount_mcu + amount_podgotovka + amount_ss
    profit              = round(price_sale - price - amount_sum, -2)
    
    estimation_price_do_kd = estimation_price + amount_ss
    if estimation.page_test_drive != None and estimation.page_test_drive.end_estimation != None:
        estimation_price = estimation_price_do_kd - amount_ss 
        if estimation_price < 1000:
            estimation_price = 1000
    else:
        estimation_price = 0

    if estimation_price_do_kd < 1000:
        estimation_price_do_kd = 1000 
    
    cna_expenses = zna - amount_sum 
    
    if cna_expenses < 0:
        cna_expenses = zna
        
    price = {
        'kors_price_reception'          : kors_price_reception,
        'profit'                        : profit,
        'hub_sale_price_avg'            : hub_sale_price_avg,
        'hub_price_avg'                 : hub_price_avg,
        'zna'                           : zna,
        'zna_type'                      : zna_type,
        'estimation_price_do_kd'        : estimation_price_do_kd,
        'estimation_price'              : estimation_price,
        'zg'                            : zg,
        'kf'                            : kf,
        'kors_price_correction_sale'    : 0,
        'list_info_price'               : list_info_price,
        'array_body'                    : body_info,
        'amount_podgotovka'             : amount_podgotovka,
        'list_work_podgotovka'          : list_work_podgotovka,
        'list_work_service'             : list_work_service,
        'list_work_mcu'                 : list_work_mcu,
        'amount_sum'                    : amount_sum,
        'amount_ss'                     : amount_ss,
        'amount_mcu'                    : amount_mcu,
        'auction'                       : auction,
        'auction_comment'               : auction_comment,
        'sale'                          : price_sale,
        'price_sale'                    : price_sale,
        'price_sale_rdo'                : price_sale_rdo,
        'price_sale_kor'                : price_sale_kor,
        'cna_expenses'                  : cna_expenses,
        'zachita_ot_ubitka'             : zachita_ot_ubitka,
        'finance_price'                 : finance_price,
        'iznos_price'                   : iznos_price
    }

    return price


def estimation_history_vin(vin, count = False):
    if vin != '':
        if count:
            return DocLO.objects.filter(vin__icontains = vin).count()
        else:
            return DocLO.objects.filter(vin__icontains = vin).order_by('-dataTime')
    return list()


def start_soglas(request, id):
    if 'status' in request.GET:
        status = int(request.GET['status'])
    rlk = DocRLK.objects.get(pk=id)
    #rlk.statusOcenka = RefStatusOcenka.objects.get(pk=status)
    if status == 2:
        rlk.staffECO1 = request.user.id
    return redirect('/eco/doc/?checkid=' + id)


def opens_info(estimation):
   return RegInteractivOcenkaHistoryOpens.objects.filter(estimation = estimation).order_by('-date_open') 


def point_in_polygon(point, polygon):
    num_vertices = len(polygon)
    x, y = point.x, point.y
    inside = False
 
    # Store the first point in the polygon and initialize the second point
    p1 = polygon[0]
 
    # Loop through each edge in the polygon
    for i in range(1, num_vertices + 1):
        # Get the next point in the polygon
        p2 = polygon[i % num_vertices]
 
        # Check if the point is above the minimum y coordinate of the edge
        if y > min(p1.y, p2.y):
            # Check if the point is below the maximum y coordinate of the edge
            if y <= max(p1.y, p2.y):
                # Check if the point is to the left of the maximum x coordinate of the edge
                if x <= max(p1.x, p2.x):
                    # Calculate the x-intersection of the line connecting the point to the edge
                    x_intersection = (y - p1.y) * (p2.x - p1.x) / (p2.y - p1.y) + p1.x
 
                    # Check if the point is on the same line as the edge or to the left of the x-intersection
                    if p1.x == p2.x or x <= x_intersection:
                        # Flip the inside flag
                        inside = not inside
 
        # Store the current point as the first point for the next iteration
        p1 = p2
 
    # Return the value of the inside flag
    return inside


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

#История изменений
def get_versions(table, id):
	return ChangeLog.objects.filter(model = table).filter(record_id = id).order_by('changed')