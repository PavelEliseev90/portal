from django.shortcuts import render
from tkinter.tix import Tree
from django.shortcuts import redirect, render
from register.models import RegInteractivOcenkaRemote, RegInteractivOcenkaEmailPush, RegInteractivOcenkaSoglasovanie, RegInteractivOcenkaProverki, RegInteractivOcenkaKolesa, RegInteractivOcenkaTestDrive, RegInteractivOcenkaComplectnost, RegInteractivOcenkaVnesh, RegDashboardError, RegInteractivOcenka, RegInteractivOcenkaDocument, RegRegInteractivOcenkaFiles, RegInteractivOcenkaSalon
from django.core.paginator import Paginator
from refs.models import RefCustomerFiltr, RefStatusEstimation, RefTypeDisk, RefMarkTyres, RefWidthTyres, RefProfileTyres, RefRadius, RefSezonTyres, RefEtDisk, RefDiaDisk, RefPsdDisk, RefStatusOcenka, RefUnit, RefStaff, RefTypeReceptionCarsOrganization
from profiles.models import Profiles
from documents.models import DocRLK, DocZN, DocLO
from task_manager.views import send_message_socket
import json
from checklists.models import CheckListTradeIn
from chats.models import Chat, ChatMessage
from django.db.models import Count, Sum, Max, Avg, F, OuterRef, Subquery, Sum, Q
import datetime as DT
from django.http import Http404, HttpResponseRedirect, HttpResponseNotFound, HttpResponse
from django.contrib.auth.models import User, Group
from refs.models import RefCars, RefTypeDisk, RefMarkTyres, RefWidthTyres, RefProfileTyres, RefRadius, RefSezonTyres, RefEtDisk, RefDiaDisk, RefPsdDisk, RefTypeReceptionCarsOrganization, AutoruModification, RefOrganization, RefStaff, RefUnit, RefFilial, RefManufacturer, RefCarsOrganization, RefStore, RefTypeEvaluationCarsOrganization, RefCarsOrganizationFiles
from PIL import Image
import io, base64
from django.core.files.base import ContentFile

import re
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.conf import settings
from eco.views import repair_history, estimation_lo_history, save_recovery_estimations
from register.models import RegSwapKors, RegInfoBody
from refs.models import RefStatusEstimation, RefTypeReceptionCarsOrganization, AutoruModificationSpecifications, RefManufacturer, RefAvito, RefAvitoComplectation, RefTypeKPPAvito, RefTypeEngineAvito, RefTypeDriveAvito, RefTypeBodyAvito,  RefExchangeCars, RefTypeCanceledSMS, RefTypeExchange, RefIb, AutoruMark, AutoruModel, AutoruModification, AutoruComplectation, RefTypeKpp, RefTypeBody, RefTypeEngine, RefUnit, RefCity, RefStaff, RefBoardsPage, RefUnitGroup, RefTypeRepair, RefBoards, RefTypeResourcePlanning, RefTypeCategoryNegative, RefCustomerFiltr
from avtosalon.models import AvtohubComplectations, AvtohubOptions, AvtohubGroupOptions

from datetime import datetime


import time
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import websockets
import asyncio
from asgiref.sync import sync_to_async


def refresh_analitick(estimation):
    
    estimation.avtoteka_web = ''
    estimation.avtoteka_preview = ''
    estimation.avtoteka_task = None 
    estimation.hub_start = None
    estimation.kors_start_store = DT.datetime.now().replace(year=2024)
 

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


def add_swap(rlk):
    
    try:
        
        swap        = RegSwapKors()
        swap.rlk    = rlk
        swap.save()
        
    except:
        s = 1


def get_car(reg_interactiv_ocenka):
    count = RefCars.objects.filter(vin = reg_interactiv_ocenka.vin).count()
    if count > 0:
        return RefCars.objects.filter(vin = reg_interactiv_ocenka.vin)[0]
    return 0


def check_estimations(reg_interactiv_ocenka):
    
    date_null = DT.datetime(1,1,1)

    error       = False
    list_check  = list()
    
    list_documents  = list()
    error_documents = False

    list_salon      = list()
    error_salon     = False

    list_vnesh      = list()
    error_vnesh     = False

    list_complectnost      = list()
    error_complectnost     = False

    list_kolesa      = list()
    error_kolesa     = False

    list_test      = list()
    error_test     = False

    list_proverki      = list()
    error_proverki     = False

    # документы
    if reg_interactiv_ocenka.page_documents == None:
        field = tr_check('Документы', 'Ошибка', False)
        list_documents.append(field)
        error_documents = True
    else:
        page_documents = reg_interactiv_ocenka.page_documents
        if page_documents.type_reception == None: 
            error_documents = True
            field = tr_check('Тип приема', 'Ошибка', False)
            list_documents.append(field)
        else:
            field = tr_check('Тип приема', 'ОК', True)
            list_documents.append(field)
        
        if page_documents.organization == None: 
            error_documents = True
            field = tr_check('Организация', 'Ошибка', False)
            list_documents.append(field)
        else:
            field = tr_check('Организация', 'ОК', True)
            list_documents.append(field)

        if page_documents.filial == None: 
            error_documents = True
            field = tr_check('Филиал', 'Ошибка', False)
            list_documents.append(field)
        else:
            field = tr_check('Филиал', 'ОК', True)
            list_documents.append(field)

        if page_documents.unit == None: 
            error_documents = True
            field = tr_check('Подразделение', 'Ошибка', False)
            list_documents.append(field)
        else:
            field = tr_check('Подразделение', 'ОК', True)
            list_documents.append(field)

        if page_documents.store == None: 
            error_documents = True
            field = tr_check('Стоянка', 'Ошибка', False)
            list_documents.append(field)
        else:
            field = tr_check('Стоянка', 'ОК', True)
            list_documents.append(field)

        if page_documents.customer_family == None or page_documents.customer_family == '': 
            error_documents = True
            field = tr_check('Фамилия клиента', 'Ошибка', False)
            list_documents.append(field)
            error_documents = True
        else:
            field = tr_check('Фамилия клиента', 'ОК', True)
            list_documents.append(field)
        
        if page_documents.customer_family == None or page_documents.customer_family == '': 
            error_documents = True
            field = tr_check('Имя клиента', 'Ошибка', False)
            list_documents.append(field)
            error_documents = True
        else:
            field = tr_check('Имя клиента', 'ОК', True)
            list_documents.append(field)

        if page_documents.plate_number == None or page_documents.plate_number == '': 
            error_documents = True
            field = tr_check('Гос. номер', 'Ошибка', False)
            list_documents.append(field)
            error_documents = True
        else:
            field = tr_check('Гос. номер', 'ОК', True)
            list_documents.append(field)

        if page_documents.count_owners == 0: 
            error_documents = True
            field = tr_check('Количество владельцев', 'Ошибка', False)
            list_documents.append(field)
            error_documents = True
        else:
            field = tr_check('Количество владельцев', 'ОК', True)
            list_documents.append(field)

        if page_documents.sts_number == None or page_documents.sts_number == '': 
            error_documents = True
            field = tr_check('СТС номер', 'Ошибка', False)
            list_documents.append(field)
            error_documents = True
        else:
            field = tr_check('СТС номер', 'ОК', True)
            list_documents.append(field)

        if page_documents.sts_date == date_null or page_documents.sts_date == '': 
            error_documents = True
            field = tr_check('СТС дата', 'Ошибка', False)
            list_documents.append(field)
            error_documents = True
        else:
            field = tr_check('СТС дата', 'ОК', True)
            list_documents.append(field)
        
        sts_foto = reg_interactiv_ocenka.fotos_sts_count()
        if sts_foto == 0:
            error_documents = True
            field = tr_check('СТС фото', 'Ошибка', False)
            list_documents.append(field)
            error_documents = True
        else:
            field = tr_check('СТС фото - ' + str(sts_foto), 'ОК', True)
            list_documents.append(field)    

    # салон
    if reg_interactiv_ocenka.page_salon == None:
        field = tr_check('Салон', 'Ошибка', False)
        list_salon.append(field)
        error_salon = True
    else:
        if reg_interactiv_ocenka.page_salon.run > 0:
            field = tr_check('Пробег', 'OK', True)
            list_salon.append(field)
        else:
            error_salon = True
            field = tr_check('Пробег', 'Ошибка', True)
            list_salon.append(field)
        
        fotos_run_count = reg_interactiv_ocenka.fotos_run_count()
        if fotos_run_count > 0:
            field = tr_check('Фото пробега - ' + str(fotos_run_count), 'OK', True)
            list_salon.append(field)
        else:
            error_salon = True
            field = tr_check('Фото пробега', 'Ошибка', False)
            list_salon.append(field)  
    
    # внешний осмотр
            
    if reg_interactiv_ocenka.page_vnesh == None:
        field = tr_check('Внешний осмотр', 'Ошибка', False)
        list_vnesh.append(field)
        error_vnesh = True
    else:
        fotos_vin_count = reg_interactiv_ocenka.fotos_vin_count()
        if fotos_vin_count > 0:
            field = tr_check('Фото VIN - ' + str(fotos_vin_count), 'OK', True)
            list_vnesh.append(field)
        else:
            field = tr_check('Фото VIN', 'Ошибка', False)
            list_vnesh.append(field)
            error_vnesh = True
        
        fotos_vnesh_count = reg_interactiv_ocenka.fotos_vnesh_count()
        if fotos_vnesh_count > 7:
            field = tr_check('Общие фото авто - ' + str(fotos_vnesh_count), 'OK', True)
            list_vnesh.append(field)
        else:
            field = tr_check('Общие фото авто', 'Ошибка', False)
            list_vnesh.append(field)
            error_vnesh = True

        fotos_pod_capot_count = reg_interactiv_ocenka.fotos_pod_capot_count()
        if fotos_pod_capot_count > 0:
            field = tr_check('Фото подкапотного пр-ва - ' + str(fotos_pod_capot_count), 'OK', True)
            list_vnesh.append(field)
        else:
            field = tr_check('Фото подкапотного пр-ва', 'Ошибка', False)
            list_vnesh.append(field)
            error_vnesh = True

        fotos_vnesh_pered = reg_interactiv_ocenka.fotos_vnesh_pered_count()
        if fotos_vnesh_pered > 0:
            field = tr_check('Осмотр передней части', 'OK', True)
            list_vnesh.append(field)
        else:
            field = tr_check('Осмотр передней части', 'Ошибка', False)
            list_vnesh.append(field)
            error_vnesh = True

        fotos_vnesh_vod_count = reg_interactiv_ocenka.fotos_vnesh_vod_count()
        if fotos_vnesh_vod_count > 0:
            field = tr_check('Осмотр водительской части', 'OK', True)
            list_vnesh.append(field)
        else:
            field = tr_check('Осмотр водительской части', 'Ошибка', False)
            list_vnesh.append(field)
            error_vnesh = True
        
        fotos_vnesh_zad_count = reg_interactiv_ocenka.fotos_vnesh_zad_count()
        if fotos_vnesh_zad_count > 0:
            field = tr_check('Осмотр задней части', 'OK', True)
            list_vnesh.append(field)
        else:
            field = tr_check('Осмотр задней части', 'Ошибка', False)
            list_vnesh.append(field)
            error_vnesh = True

        fotos_vnesh_pass_count = reg_interactiv_ocenka.fotos_vnesh_pass_count()
        if fotos_vnesh_pass_count > 0:
            field = tr_check('Осмотр пассажирской части', 'OK', True)
            list_vnesh.append(field)
        else:
            field = tr_check('Осмотр пассажирской части', 'Ошибка', False)
            list_vnesh.append(field)
            error_vnesh = True

        fotos_vnesh_up_count = reg_interactiv_ocenka.fotos_vnesh_up_count()
        if fotos_vnesh_up_count > 0:
            field = tr_check('Осмотр крыши', 'OK', True)
            list_vnesh.append(field)
        else:
            field = tr_check('Осмотр крыши', 'Ошибка', False)
            list_vnesh.append(field)
            error_vnesh = True


    # комплектность
    if reg_interactiv_ocenka.page_complectnost == None:
        field = tr_check('Комплектность', 'Ошибка', False)
        list_complectnost.append(field)
        error_complectnost = True
    else:
        field = tr_check('Комплектность', 'OK', True)
        list_complectnost.append(field)

    # колеса
    if reg_interactiv_ocenka.page_kolesa == None:
        field = tr_check('Колеса', 'Ошибка', False)
        list_kolesa.append(field)
        error_kolesa = True
    else:
        if reg_interactiv_ocenka.fotos_kolesa_count() < 4:
            field = tr_check('Фотографии каждого колеса установленого на ам', 'Ошибка', False)
            list_kolesa.append(field)
            error_kolesa = True
        else:
            field = tr_check('Фотографии каждого колеса установленого на ам', 'OK', True)
            list_kolesa.append(field)
        
        if reg_interactiv_ocenka.page_kolesa.mark_tyre == None:
            field = tr_check('Марка резины на АМ', 'Ошибка', False)
            list_kolesa.append(field)
            error_kolesa = True
        else:
            field = tr_check('Марка резины на АМ', 'OK', True)
            list_kolesa.append(field)

        if reg_interactiv_ocenka.page_kolesa.model_tyre == None:
            field = tr_check('Модель резины на АМ', 'Ошибка', False)
            list_kolesa.append(field)
            error_kolesa = True
        else:
            field = tr_check('Модель резины на АМ', 'OK', True)
            list_kolesa.append(field)

        if reg_interactiv_ocenka.page_kolesa.width_tyre == None:
            field = tr_check('Ширина резины на АМ', 'Ошибка', False)
            list_kolesa.append(field)
            error_kolesa = True
        else:
            field = tr_check('Ширина резины на АМ', 'OK', True)
            list_kolesa.append(field)

        if reg_interactiv_ocenka.page_kolesa.profil_tyre == None:
            field = tr_check('Профиль резины на АМ', 'Ошибка', False)
            list_kolesa.append(field)
            error_kolesa = True
        else:
            field = tr_check('Профиль резины на АМ', 'OK', True)
            list_kolesa.append(field)

        if reg_interactiv_ocenka.page_kolesa.radius == None:
            field = tr_check('Радиус колес на АМ', 'Ошибка', False)
            list_kolesa.append(field)
            error_kolesa = True
        else:
            field = tr_check('Радиус колес на АМ', 'OK', True)
            list_kolesa.append(field)
        
    '''
    # Тест - драйв
    if reg_interactiv_ocenka.page_test_drive == None:
        field = tr_check('Тест - драйв', 'Ошибка', False)
        list_test.append(field)
        error_test = True
    else:
        field = tr_check('Тест - драйв', 'OK', True)
        list_test.append(field)  
    '''

    # Проверки
    if reg_interactiv_ocenka.page_proverki == None:
        field = tr_check('Проверки', 'Ошибка', False)
        list_proverki.append(field)
        error_proverki = True
    else:
        fotos_gibdd_count = reg_interactiv_ocenka.fotos_gibdd_count()
        if fotos_gibdd_count > 0:
            field = tr_check('Фото ГИБДД - ' + str(fotos_gibdd_count), 'OK', True)
            list_proverki.append(field)
        else:
            field = tr_check('Фото ГИБДД', 'Ошибка', False)
            list_proverki.append(field)
            error_proverki = True
        
        fotos_reestr_count = reg_interactiv_ocenka.fotos_reestr_count()
        if fotos_reestr_count > 0:
            field = tr_check('Фото реестр залогов - ' + str(fotos_reestr_count), 'OK', True)
            list_proverki.append(field)
        else:
            field = tr_check('Фото реестр залогов', 'Ошибка', False)
            list_proverki.append(field)
            error_proverki = True

        fotos_market_count = reg_interactiv_ocenka.fotos_market_count()
        if fotos_market_count > 0:
            field = tr_check('Фото рынок - ' + str(fotos_market_count), 'OK', True)
            list_proverki.append(field)
        else:
            field = tr_check('Фото рынок', 'Ошибка', False)
            list_proverki.append(field)
            error_proverki = True 
        
    error = error_documents or error_salon or error_vnesh or error_complectnost or error_kolesa  or error_proverki

    check_info = {
        'error'             : error,
        'documents'         : list_documents,
        'documents_error'   : error_documents,
        'salons'            : list_salon,
        'salons_error'      : error_salon,
        'vneshs'            : list_vnesh,
        'vneshs_error'      : error_vnesh,
        
        'complectnosts'         : list_complectnost,
        'complectnosts_error'   : error_complectnost,

        'kolesa'         : list_kolesa,
        'kolesa_error'   : error_kolesa,

        'tests'         : list_test,
        'tests_error'   : error_test,

        'proverkis'             : list_proverki,
        'proverkis_error'       : error_proverki,
    }
    
    return check_info    


def tr_check(name, result, success):
    field   = {'name'       : name,
               'result'     : result,
               'success'    : success}
    return field    


def estimation_rlk(request, rlk_id):
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
        
    user    = request.user
    users   = list()

    object                          = DocRLK.objects.get(id=rlk_id)
    reg_interactiv_ocenka, created  = RegInteractivOcenka.objects.get_or_create(rlk = object)
    
    list_statuses = [1, 2, 7]
    if not reg_interactiv_ocenka.status.id in list_statuses:
        return HttpResponseRedirect('/eco/' + str(rlk_id) + '/?page=9')

    #send_channel_message(user, id_rlk = 0, message = 'Прикол')

    if request.method == 'POST':
        
        if 'vin_new' in request.POST or 'body_number_new' in request.POST:
            vin_new = request.POST.get('vin_new', '').strip()
            body_number_new = request.POST.get('body_number_new', '').strip()
            
            if vin_new:
                reg_interactiv_ocenka.vin = vin_new
                refresh_analitick(reg_interactiv_ocenka)
            
            if body_number_new:
                reg_interactiv_ocenka.number_body = body_number_new
            
            reg_interactiv_ocenka.save()
            return HttpResponseRedirect(request.path_info)
        
        if 'set_type_estimation' in request.POST:
            type_estimation = int(request.POST.get('type_estimation', '0'))
            reg_interactiv_ocenka.type_estimation = type_estimation
            if type_estimation == 3:
                if reg_interactiv_ocenka.page_remote == None:
                    reg_interactiv_ocenka_page_remote = RegInteractivOcenkaRemote()
                    reg_interactiv_ocenka_page_remote.save()
                    reg_interactiv_ocenka.page_remote = reg_interactiv_ocenka_page_remote
                    reg_interactiv_ocenka.save()
                else:
                    reg_interactiv_ocenka_page_remote = reg_interactiv_ocenka.page_remote
                if reg_interactiv_ocenka_page_remote.start_estimation == None:
                    reg_interactiv_ocenka_page_remote.start_estimation = datetime.now()
                if reg_interactiv_ocenka_page_remote.end_estimation != None:
                    reg_interactiv_ocenka_page_remote.start_estimation = None
                reg_interactiv_ocenka_page_remote.save()
            reg_interactiv_ocenka.save()
            return HttpResponseRedirect(request.path_info)

        if 'edit_modification' in request.POST:
            reg_interactiv_ocenka.year          = 0    
            reg_interactiv_ocenka.modification  = None
            refresh_analitick(reg_interactiv_ocenka)
            reg_interactiv_ocenka.save()
            return HttpResponseRedirect(request.path_info + "/s/")
        
        if 's_documents' in request.POST:
            
            if reg_interactiv_ocenka.page_documents == None:
                reg_interactiv_ocenka_document = RegInteractivOcenkaDocument()
                reg_interactiv_ocenka_document.save()
                reg_interactiv_ocenka.page_documents = reg_interactiv_ocenka_document
                reg_interactiv_ocenka.save()
            else:
                reg_interactiv_ocenka_document = reg_interactiv_ocenka.page_documents

            if reg_interactiv_ocenka_document.start_estimation == None:
                reg_interactiv_ocenka_document.start_estimation     = datetime.now() 
            
            organization_id = request.POST.get('organization_id', '')
            if organization_id != '':
                reg_interactiv_ocenka_document.organization = RefOrganization.objects.get(pk = organization_id)

            filial_id = request.POST.get('filial_id', '')
            if filial_id != '':
                reg_interactiv_ocenka_document.filial = RefFilial.objects.get(pk = filial_id)

            unit_id = request.POST.get('unit_id', '')
            if unit_id != '':
                reg_interactiv_ocenka_document.unit = RefUnit.objects.get(pk = unit_id)

            store_id = request.POST.get('store_id', '')
            if store_id != '':
                reg_interactiv_ocenka_document.store = RefStore.objects.get(pk = store_id)

            type_reception_id = request.POST.get('type_reception_id', '')
            if type_reception_id != '':
                reg_interactiv_ocenka_document.type_reception = RefTypeReceptionCarsOrganization.objects.get(pk = type_reception_id)

            type_drive           = request.POST.get('type_drive', '')
            if type_drive != '' and type_drive != reg_interactiv_ocenka.type_drive:
                reg_interactiv_ocenka.type_drive    = type_drive
                reg_interactiv_ocenka.save()

            reg_interactiv_ocenka_document.customer_family      = request.POST.get('customer_family', '')
            reg_interactiv_ocenka_document.customer_name        = request.POST.get('customer_name', '')
            reg_interactiv_ocenka_document.customer_patronymic  = request.POST.get('customer_patronymic', '')
            reg_interactiv_ocenka_document.customer_phone       = request.POST.get('customer_phone', '')
            
            
            reg_interactiv_ocenka_document.count_key            = int(request.POST.get('count_key', '0'))
            reg_interactiv_ocenka_document.count_owners         = int(request.POST.get('count_owners', '0'))
            reg_interactiv_ocenka_document.plate_number         = request.POST.get('plate_number', '')
            reg_interactiv_ocenka_document.engine_number        = request.POST.get('engine_number', '')
            reg_interactiv_ocenka_document.pts_color            = request.POST.get('pts_color', '')

            reg_interactiv_ocenka_document.pts_number            = request.POST.get('pts_number', '')
            reg_interactiv_ocenka_document.sts_number            = request.POST.get('sts_number', '')

            reg_interactiv_ocenka_document.pts_date            = datetime.strptime(request.POST.get('pts_date', '0001-01-01'), '%Y-%m-%d')
            reg_interactiv_ocenka_document.sts_date            = datetime.strptime(request.POST.get('sts_date', '0001-01-01'), '%Y-%m-%d')

            type_point  = ''
            text        = ''
            x = 0
            y = 0

            files_sts = request.FILES.getlist('image_sts')
            for file_object in files_sts: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'sts', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name)
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save()    

            files_pts = request.FILES.getlist('image_pts')
            for file_object in files_pts: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'pts', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name)
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save()  
            
            if "page" in request.POST:
                reg_interactiv_ocenka_document.save()
                return HttpResponseRedirect(request.path_info + '?page='+ request.POST.get('page'))
            
            if 'save' in request.POST:
                reg_interactiv_ocenka_document.save()
                return HttpResponseRedirect(request.path_info + '?page=1') 
            
            if 'save_and_next' in request.POST:
                reg_interactiv_ocenka_document.end_estimation   = datetime.now()
                reg_interactiv_ocenka_document.save()
                return HttpResponseRedirect(request.path_info + '?page=2') 

        if 's_salon' in request.POST:
            
            if reg_interactiv_ocenka.page_salon == None:
                reg_interactiv_ocenka_salon = RegInteractivOcenkaSalon()
                reg_interactiv_ocenka_salon.save()
                reg_interactiv_ocenka.page_salon = reg_interactiv_ocenka_salon
                reg_interactiv_ocenka.save()
            else:
                reg_interactiv_ocenka_salon = reg_interactiv_ocenka.page_salon

            if reg_interactiv_ocenka_salon.start_estimation == None:
                reg_interactiv_ocenka_salon.start_estimation     = datetime.now() 
            
            reg_interactiv_ocenka_salon.end_estimation          = datetime.now()  
            
            run = int(request.POST.get('run', '0'))
            if reg_interactiv_ocenka_salon.run != run:
                refresh_analitick(reg_interactiv_ocenka)  
            reg_interactiv_ocenka_salon.run                     = run

            reg_interactiv_ocenka_salon.run_confirmed_comment   = request.POST.get('run_confirmed_comment', '')
            
            reg_interactiv_ocenka_salon.run_confirmed           = 'run_confirmed' in request.POST


            reg_interactiv_ocenka_salon.hand_brake      = int(request.POST.get('hand_brake', '3'))
            reg_interactiv_ocenka_salon.conductor       = int(request.POST.get('conductor', '3'))
            reg_interactiv_ocenka_salon.wiper           = int(request.POST.get('wiper', '3'))
            reg_interactiv_ocenka_salon.signal          = int(request.POST.get('signal', '3'))
            reg_interactiv_ocenka_salon.power_windows   = int(request.POST.get('power_windows', '3'))
            reg_interactiv_ocenka_salon.seat_belt       = int(request.POST.get('seat_belt', '3'))
            
            reg_interactiv_ocenka_salon.run_respond     = int(request.POST.get('run_respond', '3'))

            reg_interactiv_ocenka_salon.cleaning_int            = int(request.POST.get('cleaning_int', '3'))
            reg_interactiv_ocenka_salon.type_salon_int          = int(request.POST.get('type_salon_int', '3'))
            reg_interactiv_ocenka_salon.damage_kpp_int          = int(request.POST.get('damage_kpp_int', '3'))
            reg_interactiv_ocenka_salon.damage_wheel_int        = int(request.POST.get('damage_wheel_int', '3'))
            reg_interactiv_ocenka_salon.damage_pedal_int        = int(request.POST.get('damage_pedal_int', '3'))
            reg_interactiv_ocenka_salon.damage_door_int         = int(request.POST.get('damage_door_int', '3'))
            reg_interactiv_ocenka_salon.damage_seat_int         = int(request.POST.get('damage_seat_int', '3'))


            reg_interactiv_ocenka_salon.cleaning        = 'cleaning' in request.POST
            reg_interactiv_ocenka_salon.damage_kpp      = 'damage_kpp' in request.POST
            reg_interactiv_ocenka_salon.damage_wheel    = 'damage_wheel' in request.POST
            reg_interactiv_ocenka_salon.damage_pedal    = 'damage_pedal' in request.POST
            reg_interactiv_ocenka_salon.damage_door     = 'damage_door' in request.POST
            reg_interactiv_ocenka_salon.damage_seat     = 'damage_seat' in request.POST
            
            reg_interactiv_ocenka_salon.dashboard_error.clear()

            for key in request.POST.keys():
                if key.startswith('uin_dash_'):
                    uin_dash = key.replace('uin_dash_', '')
                    reg_interactiv_ocenka_salon.dashboard_error.add(RegDashboardError.objects.get(uin = uin_dash))
                
            type_point  = ''
            text        = ''
            x = 0
            y = 0

            files_run = request.FILES.getlist('image_run')
            for file_object in files_run: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'run', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name)
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save() 

            files_salon_all = request.FILES.getlist('image_salon')
            for file_object in files_salon_all: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'salon_all', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name)
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save() 

            files_image_damage_salon = request.FILES.getlist('image_damage_salon')
            for file_object in files_image_damage_salon: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'salon_error', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name)
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save() 
            
            if "page_osmotr_salon" in request.POST:
                reg_interactiv_ocenka_salon.save()
                url = '/estimations/' + str(object.pk) + '/osmotr_salon/page_osmotr_salon/'
                return HttpResponseRedirect(url)
            
            if "page" in request.POST:
                reg_interactiv_ocenka_salon.save()
                return HttpResponseRedirect(request.path_info + '?page='+ request.POST.get('page'))
            
            if 'save' in request.POST:
                reg_interactiv_ocenka_salon.save()
                return HttpResponseRedirect(request.path_info + '?page=2') 
            if 'save_and_next' in request.POST:
                reg_interactiv_ocenka_salon.end_estimation   = datetime.now()
                reg_interactiv_ocenka_salon.save()
                return HttpResponseRedirect(request.path_info + '?page=3') 

        if 's_vnesh' in request.POST:
            
            if reg_interactiv_ocenka.page_vnesh == None:
                reg_interactiv_ocenka_vnesh = RegInteractivOcenkaVnesh()
                reg_interactiv_ocenka_vnesh.save()
                reg_interactiv_ocenka.page_vnesh = reg_interactiv_ocenka_vnesh
                reg_interactiv_ocenka.save()
            else:
                reg_interactiv_ocenka_vnesh = reg_interactiv_ocenka.page_vnesh

            if reg_interactiv_ocenka_vnesh.start_estimation == None:
                reg_interactiv_ocenka_vnesh.start_estimation     = datetime.now() 

            reg_interactiv_ocenka_vnesh.color = request.POST.get('color_body', '')
            
            reg_interactiv_ocenka_vnesh.check_vin_int           = int(request.POST.get('check_vin_int', '3'))
            reg_interactiv_ocenka_vnesh.check_engine_int        = int(request.POST.get('check_engine_int', '3'))
            reg_interactiv_ocenka_vnesh.windshield_heat_int     = int(request.POST.get('windshield_heat_int', '3'))
            reg_interactiv_ocenka_vnesh.windshield_error_int    = int(request.POST.get('windshield_error_int', '3'))
            reg_interactiv_ocenka_vnesh.light_error_int         = int(request.POST.get('light_error_int', '3'))
            reg_interactiv_ocenka_vnesh.oil_error_int           = int(request.POST.get('oil_error_int', '3'))
            reg_interactiv_ocenka_vnesh.water_error_int         = int(request.POST.get('water_error_int', '3'))

            reg_interactiv_ocenka_vnesh.windshield_error    = 'windshield_error' in request.POST
            reg_interactiv_ocenka_vnesh.light_error         = 'light_error' in request.POST
            reg_interactiv_ocenka_vnesh.oil_error           = 'oil_error' in request.POST
            reg_interactiv_ocenka_vnesh.water_error         = 'water_error' in request.POST            
            reg_interactiv_ocenka_vnesh.check_vin           = 'check_vin' in request.POST
            reg_interactiv_ocenka_vnesh.check_engine        = 'check_engine' in request.POST

            type_point  = ''
            text        = ''
            x = 0
            y = 0

            files_run = request.FILES.getlist('photo_a1')
            for file_object in files_run: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'vnesh_car_all', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name, file_number = 1)
                new_estimation_files.file_number    = 1 
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save() 
            files_run = request.FILES.getlist('photo_a2')
            for file_object in files_run: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'vnesh_car_all', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name, file_number = 2)
                new_estimation_files.file_number    = 2 
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save() 
            files_run = request.FILES.getlist('photo_a3')
            for file_object in files_run: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'vnesh_car_all', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name, file_number = 3)
                new_estimation_files.file_number    = 3 
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save() 
            files_run = request.FILES.getlist('photo_a4')
            for file_object in files_run: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'vnesh_car_all', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name, file_number = 4)
                new_estimation_files.file_number    = 4 
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save() 
            files_run = request.FILES.getlist('photo_a5')
            for file_object in files_run: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'vnesh_car_all', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name, file_number = 5)
                new_estimation_files.file_number    = 5 
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save() 
            files_run = request.FILES.getlist('photo_a6')
            for file_object in files_run: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'vnesh_car_all', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name, file_number = 6)
                new_estimation_files.file_number    = 6 
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save() 
            files_run = request.FILES.getlist('photo_a7')
            for file_object in files_run: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'vnesh_car_all', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name, file_number = 7)
                new_estimation_files.file_number    = 7 
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save() 
            files_run = request.FILES.getlist('photo_a8')
            for file_object in files_run: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'vnesh_car_all', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name, file_number = 8)
                new_estimation_files.file_number    = 8 
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save() 
            
            files_light_error = request.FILES.getlist('file_light_error')
            for file_object in files_light_error: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'light_error', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name)
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save()

            files_windshield_error = request.FILES.getlist('file_windshield_error')
            for file_object in files_windshield_error: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'windshield_error', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name)
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save()

            files_run = request.FILES.getlist('file_vin')
            for file_object in files_run: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'vin', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name)
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save() 
            files_run = request.FILES.getlist('file_podcapot')
            for file_object in files_run: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'pod_capot', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name)
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save() 

            if "page_pered" in request.POST:
                reg_interactiv_ocenka_vnesh.save()
                url = '/estimations/' + str(object.pk) + '/osmotr/pered/'
                return HttpResponseRedirect(url)
            
            if "page_vod" in request.POST:
                reg_interactiv_ocenka_vnesh.save()
                url = '/estimations/' + str(object.pk) + '/osmotr/vod/'
                return HttpResponseRedirect(url)
            
            if "page_zad" in request.POST:
                reg_interactiv_ocenka_vnesh.save()
                url = '/estimations/' + str(object.pk) + '/osmotr/zad/'
                return HttpResponseRedirect(url)
            
            if "page_pass" in request.POST:
                reg_interactiv_ocenka_vnesh.save()
                url = '/estimations/' + str(object.pk) + '/osmotr/pass/'
                return HttpResponseRedirect(url)
            
            if "page_up" in request.POST:
                reg_interactiv_ocenka_vnesh.save()
                url = '/estimations/' + str(object.pk) + '/osmotr/up/'
                return HttpResponseRedirect(url)

            if "page" in request.POST:
                reg_interactiv_ocenka_vnesh.save()
                return HttpResponseRedirect(request.path_info + '?page='+ request.POST.get('page'))
            if 'save' in request.POST:
                reg_interactiv_ocenka_vnesh.save()
                return HttpResponseRedirect(request.path_info + '?page=3') 
            if 'save_and_next' in request.POST:
                reg_interactiv_ocenka_vnesh.end_estimation = datetime.now()
                reg_interactiv_ocenka_vnesh.save()
                return HttpResponseRedirect(request.path_info + '?page=4') 
            
        if 's_complectnost' in request.POST:
            
            if reg_interactiv_ocenka.page_complectnost == None:
                reg_interactiv_ocenka_complectnost = RegInteractivOcenkaComplectnost()
                reg_interactiv_ocenka_complectnost.save()
                reg_interactiv_ocenka.page_complectnost = reg_interactiv_ocenka_complectnost
                reg_interactiv_ocenka.save()
            else:
                reg_interactiv_ocenka_complectnost = reg_interactiv_ocenka.page_complectnost
            
            if reg_interactiv_ocenka_complectnost.start_estimation == None:
                reg_interactiv_ocenka_complectnost.start_estimation     = datetime.now() 

            reg_interactiv_ocenka_complectnost.prikur_int       = int(request.POST.get('prikur_int', '3'))
            reg_interactiv_ocenka_complectnost.ognet_int        = int(request.POST.get('ognet_int', '3'))
            reg_interactiv_ocenka_complectnost.kovrik_int       = int(request.POST.get('kovrik_int', '3'))
            reg_interactiv_ocenka_complectnost.tros_int         = int(request.POST.get('tros_int', '3'))
            reg_interactiv_ocenka_complectnost.domkrat_int      = int(request.POST.get('domkrat_int', '3'))
            reg_interactiv_ocenka_complectnost.znak_av_int      = int(request.POST.get('znak_av_int', '3'))
            reg_interactiv_ocenka_complectnost.ball_key_int     = int(request.POST.get('ball_key_int', '3'))
            reg_interactiv_ocenka_complectnost.zapas_int        = int(request.POST.get('zapas_int', '3'))
            reg_interactiv_ocenka_complectnost.aptechka_int     = int(request.POST.get('aptechka_int', '3'))
            
            reg_interactiv_ocenka_complectnost.prikur       = True if int(request.POST.get('radio_rt_prikur', 0)) == 1 else False
            reg_interactiv_ocenka_complectnost.ognet        = True if int(request.POST.get('radio_rt_ognet', 0)) == 1 else False
            reg_interactiv_ocenka_complectnost.kovrik       = True if int(request.POST.get('radio_rt_kovrik', 0)) == 1 else False
            reg_interactiv_ocenka_complectnost.tros         = True if int(request.POST.get('radio_rt_tros', 0)) == 1 else False
            reg_interactiv_ocenka_complectnost.domkrat      = True if int(request.POST.get('radio_rt_domkrat', 0)) == 1 else False
            reg_interactiv_ocenka_complectnost.znak_av      = True if int(request.POST.get('radio_rt_znak', 0)) == 1 else False
            reg_interactiv_ocenka_complectnost.ball_key     = True if int(request.POST.get('radio_rt_ball_key', 0)) == 1 else False
            reg_interactiv_ocenka_complectnost.zapas        = True if int(request.POST.get('radio_rt_zapas', 0)) == 1 else False
            reg_interactiv_ocenka_complectnost.aptechka     = True if int(request.POST.get('radio_rt_aptechka', 0)) == 1 else False
            
            if "page" in request.POST:
                reg_interactiv_ocenka_complectnost.save()
                return HttpResponseRedirect(request.path_info + '?page='+ request.POST.get('page'))
            if 'save' in request.POST:
                reg_interactiv_ocenka_complectnost.save()
                return HttpResponseRedirect(request.path_info + '?page=4') 
            if 'save_and_next' in request.POST:
                reg_interactiv_ocenka_complectnost.end_estimation = datetime.now()
                reg_interactiv_ocenka_complectnost.save()
                return HttpResponseRedirect(request.path_info + '?page=5')

        if 's_koleso' in request.POST:
            
            if reg_interactiv_ocenka.page_kolesa == None:
                reg_interactiv_ocenka_kolesa = RegInteractivOcenkaKolesa()
                reg_interactiv_ocenka_kolesa.save()
                reg_interactiv_ocenka.page_kolesa = reg_interactiv_ocenka_kolesa
                reg_interactiv_ocenka.save()
            else:
                reg_interactiv_ocenka_kolesa = reg_interactiv_ocenka.page_kolesa

            if reg_interactiv_ocenka_kolesa.start_estimation == None:
                reg_interactiv_ocenka_kolesa.start_estimation     = datetime.now()
            
            
            if request.POST.get('mark_tyre', '') != '':
                reg_interactiv_ocenka_kolesa.mark_tyre = RefMarkTyres.objects.filter(pk = request.POST.get('mark_tyre', '0')).first()
            
            reg_interactiv_ocenka_kolesa.model_tyre     = request.POST.get('model_tyre', '')
            
            if request.POST.get('width_tyre', '') != '':
                reg_interactiv_ocenka_kolesa.width_tyre     = RefWidthTyres.objects.filter(pk = request.POST.get('width_tyre', '0')).first()            
            if request.POST.get('disk_type', '') != '':
                reg_interactiv_ocenka_kolesa.disk_type      = RefTypeDisk.objects.filter(pk = request.POST.get('disk_type', '0')).first()            
            if request.POST.get('profil_tyre', '') != '':
                reg_interactiv_ocenka_kolesa.profil_tyre    = RefProfileTyres.objects.filter(pk = request.POST.get('profil_tyre', '0')).first()            
            if request.POST.get('radius', '') != '':
                reg_interactiv_ocenka_kolesa.radius         = RefRadius.objects.filter(pk = request.POST.get('radius', '0')).first()            
            if request.POST.get('sezon', '') != '':
                reg_interactiv_ocenka_kolesa.sezon          = RefSezonTyres.objects.filter(pk = request.POST.get('sezon', '0')).first()
            
            reg_interactiv_ocenka_kolesa.model_disk     = request.POST.get('model_disk', '')
            
            if request.POST.get('et_disk', '') != '':
                reg_interactiv_ocenka_kolesa.et_disk        = RefEtDisk.objects.filter(pk = request.POST.get('et_disk', '0')).first()
            if request.POST.get('dia_disk', '') != '':
                reg_interactiv_ocenka_kolesa.dia_disk       = RefDiaDisk.objects.filter(pk = request.POST.get('dia_disk', '0')).first()
            if request.POST.get('psd_disk', '') != '':
                reg_interactiv_ocenka_kolesa.psd_disk       = RefPsdDisk.objects.filter(pk = request.POST.get('psd_disk', '0')).first()
            
            if 'kolesa2' in request.POST:
                reg_interactiv_ocenka_kolesa.kolesa2         = True
                reg_interactiv_ocenka_kolesa.mark_tyre2      = RefMarkTyres.objects.filter(pk = request.POST.get('mark_tyre2', '0')).first()
                reg_interactiv_ocenka_kolesa.model_tyre2     = request.POST.get('model_tyre2', '')
                reg_interactiv_ocenka_kolesa.width_tyre2     = RefWidthTyres.objects.filter(pk = request.POST.get('width_tyre2', '0')).first()
                reg_interactiv_ocenka_kolesa.disk_type2      = RefTypeDisk.objects.filter(pk = request.POST.get('disk_type2', '0')).first()
                reg_interactiv_ocenka_kolesa.profil_tyre2    = RefProfileTyres.objects.filter(pk = request.POST.get('profil_tyre2', '0')).first()
                reg_interactiv_ocenka_kolesa.radius2         = RefRadius.objects.filter(pk = request.POST.get('radius2', '0')).first()
                reg_interactiv_ocenka_kolesa.sezon2          = RefSezonTyres.objects.filter(pk = request.POST.get('sezon2', '0')).first()
                reg_interactiv_ocenka_kolesa.model_disk2     = request.POST.get('model_disk2', '')
                reg_interactiv_ocenka_kolesa.et_disk2        = RefEtDisk.objects.filter(pk = request.POST.get('et_disk2', '0')).first()
                reg_interactiv_ocenka_kolesa.dia_disk2       = RefDiaDisk.objects.filter(pk = request.POST.get('dia_disk2', '0')).first()
            else:
                reg_interactiv_ocenka_kolesa.kolesa2         = False
                reg_interactiv_ocenka_kolesa.mark_tyre2      = None
                reg_interactiv_ocenka_kolesa.model_tyre2     = ''
                reg_interactiv_ocenka_kolesa.width_tyre2     = None
                reg_interactiv_ocenka_kolesa.disk_type2      = None
                reg_interactiv_ocenka_kolesa.profil_tyre2    = None
                reg_interactiv_ocenka_kolesa.radius2         = None
                reg_interactiv_ocenka_kolesa.sezon2          = None
                reg_interactiv_ocenka_kolesa.model_disk2     = ''
                reg_interactiv_ocenka_kolesa.et_disk2        = None
                reg_interactiv_ocenka_kolesa.dia_disk2       = None

            type_point  = ''
            text        = ''
            x = 0
            y = 0
            
            file_kolesa_1 = request.FILES.getlist('file_kolesa_1')
            for file_object in file_kolesa_1: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'kolesa', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name)
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save() 

            file_kolesa_2 = request.FILES.getlist('file_kolesa_2')
            for file_object in file_kolesa_2: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'kolesa2', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name)
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save() 
            if "page" in request.POST:
                reg_interactiv_ocenka_kolesa.save()
                return HttpResponseRedirect(request.path_info + '?page='+ request.POST.get('page'))                       
            if 'save' in request.POST:
                reg_interactiv_ocenka_kolesa.save()
                return HttpResponseRedirect(request.path_info + '?page=5') 
            if 'save_and_next' in request.POST:
                reg_interactiv_ocenka_kolesa.end_estimation = datetime.now()
                reg_interactiv_ocenka_kolesa.save()
                return HttpResponseRedirect(request.path_info + '?page=7') 

        if 's_test_drive' in request.POST:
            
            if reg_interactiv_ocenka.page_test_drive == None:
                reg_interactiv_ocenka_test_drive = RegInteractivOcenkaTestDrive()
                reg_interactiv_ocenka_test_drive.save()
                reg_interactiv_ocenka.page_test_drive = reg_interactiv_ocenka_test_drive
                reg_interactiv_ocenka.save()
            else:
                reg_interactiv_ocenka_test_drive = reg_interactiv_ocenka.page_test_drive

            if reg_interactiv_ocenka_test_drive.start_estimation == None:
                reg_interactiv_ocenka_test_drive.start_estimation     = datetime.now()
            
            reg_interactiv_ocenka_test_drive.engine         = int(request.POST.get('radio_engine', '0'))
            reg_interactiv_ocenka_test_drive.comment_engine = request.POST.get('comment_engine', '')

            reg_interactiv_ocenka_test_drive.system_og          = int(request.POST.get('radio_system_og', '0'))
            reg_interactiv_ocenka_test_drive.comment_system_og  = request.POST.get('comment_system_og', '')

            reg_interactiv_ocenka_test_drive.gear         = int(request.POST.get('radio_gear', '0'))
            reg_interactiv_ocenka_test_drive.comment_gear = request.POST.get('comment_gear', '')

            reg_interactiv_ocenka_test_drive.suspension         = int(request.POST.get('radio_engine', '0'))
            reg_interactiv_ocenka_test_drive.comment_suspension = request.POST.get('comment_suspension', '')

            reg_interactiv_ocenka_test_drive.no_test            = 'no_test' in request.POST
            reg_interactiv_ocenka_test_drive.comment            = request.POST.get('comment', '')
            if "page" in request.POST:
                reg_interactiv_ocenka_test_drive.save()
                return HttpResponseRedirect(request.path_info + '?page='+ request.POST.get('page'))
            if 'save' in request.POST:
                reg_interactiv_ocenka_test_drive.save()
                return HttpResponseRedirect(request.path_info + '?page=6') 
            if 'save_and_next' in request.POST:
                reg_interactiv_ocenka_test_drive.end_estimation = datetime.now()
                reg_interactiv_ocenka_test_drive.save()
                return HttpResponseRedirect(request.path_info + '?page=7') 
            
        if 's_proverki' in request.POST:
            
            if reg_interactiv_ocenka.page_proverki == None:
                reg_interactiv_ocenka_proverki = RegInteractivOcenkaProverki()
                reg_interactiv_ocenka_proverki.save()
                reg_interactiv_ocenka.page_proverki = reg_interactiv_ocenka_proverki
                reg_interactiv_ocenka.save()
            else:
                reg_interactiv_ocenka_proverki = reg_interactiv_ocenka.page_proverki
            
            if reg_interactiv_ocenka_proverki.start_estimation == None:
                reg_interactiv_ocenka_proverki.start_estimation     = datetime.now()

            reg_interactiv_ocenka_proverki.count_dtp    = int(request.POST.get('count_dtp', '0'))
            reg_interactiv_ocenka_proverki.car_credit   = 'car_credit' in request.POST
            
            type_point  = ''
            text        = ''
            x = 0
            y = 0
            
            files_gibdd = request.FILES.getlist('file_gibdd')
            for file_object in files_gibdd: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'gibdd', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name)
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save() 

            files_reestr = request.FILES.getlist('file_reestr')
            for file_object in files_reestr: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'reestr', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name)
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save() 

            files_market = request.FILES.getlist('file_market')
            for file_object in files_market: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'market', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name)
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save() 
            if "page" in request.POST:
                reg_interactiv_ocenka_proverki.save()
                return HttpResponseRedirect(request.path_info + '?page='+ request.POST.get('page'))
            if 'save' in request.POST:
                reg_interactiv_ocenka_proverki.save()
                return HttpResponseRedirect(request.path_info + '?page=7') 
            if 'save_and_next' in request.POST:
                reg_interactiv_ocenka_proverki.end_estimation = datetime.now()
                reg_interactiv_ocenka_proverki.save()
                return HttpResponseRedirect(request.path_info + '?page=8') 

        if 's_soglas' in request.POST:
            
            if reg_interactiv_ocenka.page_soglasovanie == None:
                reg_interactiv_ocenka_page_soglasovanie = RegInteractivOcenkaSoglasovanie()
                reg_interactiv_ocenka_page_soglasovanie.save()
                reg_interactiv_ocenka.page_soglasovanie = reg_interactiv_ocenka_page_soglasovanie
                reg_interactiv_ocenka.save()
            else:
                reg_interactiv_ocenka_page_soglasovanie = reg_interactiv_ocenka.page_soglasovanie

            if reg_interactiv_ocenka_page_soglasovanie.start_estimation == None:
                reg_interactiv_ocenka_page_soglasovanie.start_estimation     = datetime.now()

            users_add           = request.POST.get('users', '')
            users_add_list      = users_add.split(';')
            #reg_interactiv_ocenka.access_user.clear()
            for user_add in users_add_list:
                if len(user_add) > 0:
                    uusr = User.objects.get(id = user_add)
                    reg_interactiv_ocenka.access_user.add(uusr)     

            price_reception = int(request.POST.get('price_reception', '0'))
            if price_reception > 0:
                reg_interactiv_ocenka_page_soglasovanie.price_reception     = price_reception
            
            
            price_recovery = int(request.POST.get('price_recovery', '0'))
            if price_recovery > 0:
                reg_interactiv_ocenka_page_soglasovanie.price_recovery  = price_recovery
                
            price_sale = int(request.POST.get('price_sale', '0'))
            if price_sale > 0:
                reg_interactiv_ocenka_page_soglasovanie.price_sale  = price_sale

            car_sale_info = request.POST.get('car_sale_info', '')
            if car_sale_info != '':
                reg_interactiv_ocenka_page_soglasovanie.car_sale_info   = car_sale_info

            car_sale_price = request.POST.get('car_sale_price', '')
            if car_sale_price != '':
                reg_interactiv_ocenka_page_soglasovanie.car_sale_price   = car_sale_price

            comment = request.POST.get('comment', '')
            if comment != '':
                reg_interactiv_ocenka_page_soglasovanie.comment   = comment
            
            reg_interactiv_ocenka_page_soglasovanie.save()

            #send_channel_message(request.user, id_rlk = reg_interactiv_ocenka.rlk.id, message = 'Оценка отправлена на согласование.')
            new_message             = RegInteractivOcenkaEmailPush()
            new_message.estimation  = reg_interactiv_ocenka
            new_message.user        = request.user
            new_message.email       = request.user.email
            new_message.comment     = 'Интерактивная оценка отправлена на согласование.'
            new_message.save()

            for uss_base in reg_interactiv_ocenka.access_user.all():
                sends_count = sends_user_info(reg_interactiv_ocenka, uss_base)
                if sends_count == 0:
                    new_message             = RegInteractivOcenkaEmailPush()
                    new_message.estimation  = reg_interactiv_ocenka
                    new_message.user        = uss_base
                    new_message.email       = uss_base.email
                    new_message.comment     = 'Вы добавлены в участники интерактивной оценки.'
                    new_message.save()
            reg_interactiv_ocenka.save()
            
            send_count = RegInteractivOcenkaEmailPush.objects.filter(user = None).filter(email = 'eco_all@kors-group.com').filter(estimation = reg_interactiv_ocenka).count()
            if send_count == 0:
                new_message = RegInteractivOcenkaEmailPush()
                new_message.estimation  = reg_interactiv_ocenka
                new_message.user        = None
                new_message.email       = 'eco_all@kors-group.com'
                new_message.comment     = 'Интерактивная оценка отправлена на согласование, ознакомтесь.'
                new_message.save()
            
            if "page" in request.POST:
                reg_interactiv_ocenka_page_soglasovanie.save()
                return HttpResponseRedirect(request.path_info + '?page='+ request.POST.get('page'))
            if 'save' in request.POST:
                reg_interactiv_ocenka_page_soglasovanie.save()
                return HttpResponseRedirect(request.path_info + '?page=8') 
            
            if 'save_and_next' in request.POST:
                
                reg_interactiv_ocenka_page_soglasovanie.end_estimation = datetime.now()
                reg_interactiv_ocenka_page_soglasovanie.save()
                
                reg_interactiv_ocenka.returned          = False
                reg_interactiv_ocenka.end_estimation    = datetime.now()
                reg_interactiv_ocenka.save()
                chat    = Chat.objects.get_or_create(name = object.pk, slug = 'rlk_' + str(object.pk))[0]    
                send_web_socket_message(group = 'rlk_' + str(rlk_id), chat=chat, user= user, text='Оценка отправлена на согласование', estimation_id= reg_interactiv_ocenka.id)
            
                return HttpResponseRedirect('/rlks_trade_in/' + rlk_id) 

        if 's_remote' in request.POST:
            if reg_interactiv_ocenka.page_remote == None:
                reg_interactiv_ocenka_remote = RegInteractivOcenkaRemote()
                reg_interactiv_ocenka_remote.save()
                reg_interactiv_ocenka.page_remote = reg_interactiv_ocenka_remote
                reg_interactiv_ocenka.save()
            else:
                reg_interactiv_ocenka_remote = reg_interactiv_ocenka.page_remote

            if reg_interactiv_ocenka_remote.start_estimation == None:
                reg_interactiv_ocenka_remote.start_estimation     = datetime.now() 
            
            users_add           = request.POST.get('users', '')
            users_add_list      = users_add.split(';')
            
            reg_interactiv_ocenka.access_user.clear()
            for user_add in users_add_list:
                if len(user_add) > 0:
                    uusr = User.objects.get(id = user_add)
                    reg_interactiv_ocenka.access_user.add(uusr) 
            reg_interactiv_ocenka.save()

            organization_id = request.POST.get('organization_id', '')
            if organization_id != '':
                reg_interactiv_ocenka_remote.organization = RefOrganization.objects.get(pk = organization_id)

            filial_id = request.POST.get('filial_id', '')
            if filial_id != '':
                reg_interactiv_ocenka_remote.filial = RefFilial.objects.get(pk = filial_id)

            unit_id = request.POST.get('unit_id', '')
            if unit_id != '':
                reg_interactiv_ocenka_remote.unit = RefUnit.objects.get(pk = unit_id)

            store_id = request.POST.get('store_id', '')
            if store_id != '':
                reg_interactiv_ocenka_remote.store = RefStore.objects.get(pk = store_id)

            type_reception_id = request.POST.get('type_reception_id', '')
            if type_reception_id != '':
                reg_interactiv_ocenka_remote.type_reception = RefTypeReceptionCarsOrganization.objects.get(pk = type_reception_id)

            run = int(request.POST.get('run', '0'))
            reg_interactiv_ocenka_remote.run = run

            price_reception = int(request.POST.get('price_reception', '0'))
            if price_reception > 0:
                reg_interactiv_ocenka_remote.price_reception     = price_reception
            
            price_sale = int(request.POST.get('price_sale', '0'))
            if price_sale > 0:
                reg_interactiv_ocenka_remote.price_sale  = price_sale

            car_sale_info = request.POST.get('car_sale_info', '')
            if car_sale_info != '':
                reg_interactiv_ocenka_remote.car_sale_info   = car_sale_info

            car_sale_price = request.POST.get('car_sale_price', '')
            if car_sale_price != '':
                reg_interactiv_ocenka_remote.car_sale_price   = car_sale_price

            comment = request.POST.get('comment', '')
            if comment != '':
                reg_interactiv_ocenka_remote.comment   = comment

            type_drive           = request.POST.get('type_drive', '')
            if type_drive != '' and type_drive != reg_interactiv_ocenka.type_drive:
                reg_interactiv_ocenka.type_drive    = type_drive
                reg_interactiv_ocenka.save()
            
            reg_interactiv_ocenka_remote.save()
            type_point  = ''
            text        = ''
            x = 0
            y = 0
            images_remote = request.FILES.getlist('images_remote')
            for file_object in images_remote: 
                name = file_object.name.lower()
                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = 'images_remote', type_point = type_point, text = text, cor_x = x, cor_y = y, name = name)
                new_estimation_files.name           = name
                new_estimation_files.text           = text
                new_estimation_files.type_point     = type_point
                new_estimation_files.cor_x          = x
                new_estimation_files.cor_y          = y
                new_estimation_files.file           = file_object
                new_estimation_files.user           = request.user
                new_estimation_files.save()
            
            if 'save' in request.POST:
                return HttpResponseRedirect(request.path_info + '?page=11') 
            
            if 'save_and_next' in request.POST:
                chat    = Chat.objects.get_or_create(name = object.pk, slug = 'rlk_' + str(object.pk))[0]    
                send_web_socket_message(group = 'rlk_' + str(rlk_id), chat=chat, user= user, text='Дистанционная оценка отправлена на согласование', estimation_id= reg_interactiv_ocenka.id)
            
                return HttpResponseRedirect('/rlks_trade_in/' + rlk_id) 

    if request.method == 'GET':
        
        if 'del_u' in request.GET:
                
            uusr = User.objects.get(id = request.GET.get('del_u'))
            reg_interactiv_ocenka.access_user.remove(uusr)
            reg_interactiv_ocenka.save()
            
            return HttpResponseRedirect(request.path_info + '?page=8')
            
        if 'add_u' in request.GET:
            
            uusr = User.objects.get(id = request.GET.get('add_u'))
            reg_interactiv_ocenka.access_user.add(uusr)
            reg_interactiv_ocenka.save()
            
            return HttpResponseRedirect(request.path_info + '?page=8') 

    if reg_interactiv_ocenka.staff == None or reg_interactiv_ocenka.staff.domain_login == '':
        count = RefStaff.objects.filter(domain_login = user.username).filter(buauto = True).count()
        if count > 0:
            staff = RefStaff.objects.filter(domain_login = user.username).filter(buauto = True)[0]
            reg_interactiv_ocenka.staff = staff
            reg_interactiv_ocenka.save()
    
    if reg_interactiv_ocenka.start_estimation == None:
        add_swap(object)
        reg_interactiv_ocenka.start_estimation  = datetime.now()    
        reg_interactiv_ocenka.save()

    if 'type_estimation' in request.GET:
        reg_interactiv_ocenka.type_estimation = int(request.GET.get('type_estimation', 0))
        if reg_interactiv_ocenka.type_estimation == 3:
            if reg_interactiv_ocenka.page_remote == None:
                    reg_interactiv_ocenka_page_remote = RegInteractivOcenkaRemote()
                    reg_interactiv_ocenka_page_remote.save()
                    reg_interactiv_ocenka.page_remote = reg_interactiv_ocenka_page_remote
                    reg_interactiv_ocenka.save()
            else:
                reg_interactiv_ocenka_page_remote = reg_interactiv_ocenka.page_remote

            if reg_interactiv_ocenka_page_remote.start_estimation == None:
                reg_interactiv_ocenka_page_remote.start_estimation     = datetime.now()
            
            if reg_interactiv_ocenka_page_remote.end_estimation != None:
                reg_interactiv_ocenka_page_remote.start_estimation     = None
            reg_interactiv_ocenka_page_remote.save()

        reg_interactiv_ocenka.save()                                          
        return HttpResponseRedirect(request.path_info)
            
    if 'modification_id' in request.GET:
        modification    = AutoruModification.objects.get(id = request.GET.get('modification_id'))
        year_str        = request.GET.get('year', '0')
        if len(year_str) > 2:
            reg_interactiv_ocenka.year = int(year_str)
        reg_interactiv_ocenka.modification = modification
        reg_interactiv_ocenka.save()
        return HttpResponseRedirect(request.path_info)
    
    vin = request.GET.get('vin', '')
    if vin != '':
        reg_interactiv_ocenka.vin = vin.strip()
        reg_interactiv_ocenka.save()  
        return HttpResponseRedirect(request.path_info) 
    
    list_repair_hisory_vin  = list()
    list_estimations_vin    = list()
    
    car     = None
    page    = int(request.GET.get('page', '0'))

    if reg_interactiv_ocenka.vin != '' and page == 0:
        list_repair_hisory_vin      = repair_history(reg_interactiv_ocenka, count=False)
        list_estimations_vin        = estimation_lo_history(reg_interactiv_ocenka, count=False)
        car                         = get_car(reg_interactiv_ocenka)

    params = {
        'estimation'                    : reg_interactiv_ocenka,
        'list_repair_hisory_vin'        : list_repair_hisory_vin,
        'list_estimations_vin'          : list_estimations_vin,
        'car'                           : car,
        'users'                         : users,
        'vin_trade_in'                  : object.vin_trade_in if hasattr(object, 'vin_trade_in') else ''
    }
    
    if reg_interactiv_ocenka.modification == None:
        return render(request, 'estimation/estimation.html', {'params': params}) 
    
    else:
        
        list_organizations = list()
        list_filials = list()
        list_stores = list()
        list_units = list()
        type_receptions = list()

        mark_tyres  = list()
        radiuses    = list()
        profil_tyres= list()
        width_tyres = list()
        sezons      = list()
        disk_types  = list()
        et_disks    = list()
        dia_disks   = list()
        psd_disks   = list()
        pribor_errors   = list()
        list_checks     = list()
        list_complectations = list()

        chat            = Chat.objects.get_or_create(name = object.pk, slug = 'rlk_' + str(object.pk))[0]
    
        page = int(request.GET.get('page', '0'))
        
        if reg_interactiv_ocenka.page_remote != None and reg_interactiv_ocenka.page_remote.end_estimation == None:
            users = User.objects.exclude(pk__in = reg_interactiv_ocenka.access_user.all().values_list('id')).exclude(email = '').exclude(first_name = '').filter(is_active = True).order_by('last_name', 'first_name').values('profiles__eco_name', 'last_name', 'first_name', 'id', 'email')
            page = 11
            
        if page == 1 or page == 0 or page == 11:
            if reg_interactiv_ocenka.modification != None:
                list_complectations = AutoruComplectation.objects.filter(modification = reg_interactiv_ocenka.modification).order_by('name')
            users = User.objects.exclude(pk__in = reg_interactiv_ocenka.access_user.all().values_list('id')).exclude(email = '').exclude(first_name = '').filter(is_active = True).order_by('last_name', 'first_name').values('profiles__eco_name', 'last_name', 'first_name', 'id', 'email')
            
            list_organizations = RefOrganization.objects.filter(active_eco = True).order_by('name').values(
                slug            = F('id')           
                ).values('slug', 'name')
            list_filials = RefFilial.objects.filter(active_eco = True).order_by('name').values(
                    slug            = F('id')           
                    ).values('slug', 'name')
            list_stores = RefStore.objects.filter(active_eco = True).order_by('name').values(
                    slug            = F('id')           
                    ).values('slug', 'name')
            list_units = RefUnit.objects.filter(active_eco = True).order_by('name').values(
                    slug            = F('id')           
                    ).values('slug', 'name')
            
            type_receptions = RefTypeReceptionCarsOrganization.objects.all().order_by('name').values(
                    slug            = F('id')           
                    ).values('slug', 'name')
        
        if page == 2:
            pribor_errors = RegDashboardError.objects.all()

        if page == 8:
            users = User.objects.exclude(pk__in = reg_interactiv_ocenka.access_user.all().values_list('id')).exclude(email = '').exclude(first_name = '').filter(is_active = True).order_by('last_name', 'first_name').values('profiles__eco_name', 'last_name', 'first_name', 'id', 'email')
            list_checks = check_estimations(reg_interactiv_ocenka)
        
        if page == 5:
           mark_tyres = RefMarkTyres.objects.all().order_by('name')
           radiuses     = RefRadius.objects.all().order_by('name')
           profil_tyres     = RefProfileTyres.objects.all().order_by('value')
           width_tyres      = RefWidthTyres.objects.all().order_by('name')

           sezons           = RefSezonTyres.objects.all().order_by('name')
           disk_types       = RefTypeDisk.objects.all().order_by('name')
           et_disks         = RefEtDisk.objects.all().order_by('value')
           dia_disks        = RefDiaDisk.objects.all().order_by('value')
           psd_disks        = RefPsdDisk.objects.all().order_by('value')

                    
        selected = {
            'complectations'        : list_complectations,
            'organizations'         : list_organizations,
            'units'                 : list_units,
            'filials'               : list_filials,
            'stores'                : list_stores,
            'type_receptions'       : type_receptions,
            'mark_tyres'            : mark_tyres,
            'radiuses'              : radiuses,
            'profil_tyres'          : profil_tyres,
            'width_tyres'           : width_tyres,
            'sezons'                : sezons,
            'disk_types'            : disk_types,
            'et_disks'              : et_disks,
            'dia_disks'             : dia_disks,
            'psd_disks'             : psd_disks,
            'pribor_errors'         : pribor_errors

        }
        params = {
            'tabindex'                      : page,
            'selected'                      : selected,
            'chat'                          : chat,
            'estimation'                    : reg_interactiv_ocenka,
            'list_repair_hisory_vin'        : list_repair_hisory_vin,
            'list_estimations_vin'          : list_estimations_vin,
            'users'                         : users,
            'list_checks'                   : list_checks,
            'user'                          : user
        }
        
        if reg_interactiv_ocenka.v > 1:
            return render(request, 'estimation/estimation_doc_v' + str(reg_interactiv_ocenka.v) + '.html', {'params': params}) 
        else:
            return render(request, 'estimation/estimation_doc.html', {'params': params}) 


def estimation(request):

    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    vin                     = request.GET.get('vin', '')
    list_repair_hisory_vin  = list()
    list_estimations_vin    = list()

    if 'start_vin' in request.GET:
        list_repair_hisory_vin      = repair_history(vin, count=False)
        list_estimations_vin        = estimation_lo_history(vin, count=False)

    params = {
        'vin'                           : vin,
        'list_repair_hisory_vin'        : list_repair_hisory_vin,
        'list_estimations_vin'          : list_estimations_vin
    }
    
    return render(request, 'estimation/estimation.html', {'params': params})	

def estimation_start(request, rlk_id):

    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    object                          = DocRLK.objects.get(id=rlk_id)
    reg_interactiv_ocenka, created  = RegInteractivOcenka.objects.get_or_create(rlk = object)
    
    # Обработка POST запроса - сохранение данных
    if request.method == 'POST':
        # VIN и номер кузова
        vin = request.POST.get('vin', '').strip()
        body_number = request.POST.get('body_number', '').strip()
        
        if vin:
            reg_interactiv_ocenka.vin = vin
            refresh_analitick(reg_interactiv_ocenka)
        else:
            reg_interactiv_ocenka.vin = ''
        
        if body_number:
            reg_interactiv_ocenka.number_body = body_number
        
        # Модификация (может быть из двух полей)
        modification_id = request.POST.get('modification_id', '')
        if not modification_id:
            modification_id = request.POST.get('modification_full', '')
        if modification_id:
            try:
                modification = AutoruModification.objects.get(pk=modification_id)
                reg_interactiv_ocenka.modification = modification
                # Автоматически устанавливаем год из модификации, если не указан
                if not reg_interactiv_ocenka.year and modification.ProductionStartYear:
                    reg_interactiv_ocenka.year = modification.ProductionStartYear
            except:
                pass
        
        # Комплектация
        complectation_id = request.POST.get('complectation_id', '')
        if complectation_id:
            try:
                complectation = AutoruComplectation.objects.get(pk=complectation_id)
                reg_interactiv_ocenka.complectation = complectation
            except:
                pass
        
        # Год выпуска
        year = request.POST.get('year', '')
        if year:
            try:
                reg_interactiv_ocenka.year = int(year)
            except:
                pass
        
        # Тип привода
        type_drive = request.POST.get('type_drive', '')
        if type_drive:
            reg_interactiv_ocenka.type_drive = type_drive
        
        # Пробег (сохраняем в page_salon, если он существует)
        run = request.POST.get('run', '')
        if run:
            try:
                if reg_interactiv_ocenka.page_salon == None:
                    reg_interactiv_ocenka_salon = RegInteractivOcenkaSalon()
                    reg_interactiv_ocenka_salon.save()
                    reg_interactiv_ocenka.page_salon = reg_interactiv_ocenka_salon
                    reg_interactiv_ocenka.save()
                else:
                    reg_interactiv_ocenka_salon = reg_interactiv_ocenka.page_salon
                
                reg_interactiv_ocenka_salon.run = int(run)
                reg_interactiv_ocenka_salon.save()
            except:
                pass
        
        reg_interactiv_ocenka.save()
        
        # Перенаправление на следующую страницу
        return HttpResponseRedirect('/estimations/' + str(rlk_id) + '/')
    
    # Получаем все марки
    marks = AutoruMark.objects.all().order_by('name')
    
    # Получаем данные для автозаполнения из предыдущей оценки
    previous_estimation = None
    if reg_interactiv_ocenka.vin:
        previous_estimation = RegInteractivOcenka.objects.filter(
            vin=reg_interactiv_ocenka.vin
        ).exclude(id=reg_interactiv_ocenka.id).order_by('-start_estimation').first()
    
    # Получаем справочники
    type_bodies = RefTypeBody.objects.all().order_by('name')
    type_engines = RefTypeEngine.objects.all().order_by('name')
    type_drives = ['Передний', 'Задний', 'Полный']
    type_kpp = RefTypeKpp.objects.all().order_by('name')
    
    # Годы выпуска
    current_year = datetime.now().year
    years = list(range(current_year, 1960, -1))
    
    params = {
        'rlk_id': rlk_id,
        'estimation': reg_interactiv_ocenka,
        'marks': marks,
        'previous_estimation': previous_estimation,
        'type_bodies': type_bodies,
        'type_engines': type_engines,
        'type_drives': type_drives,
        'type_kpp': type_kpp,
        'years': years,
    }
    
    return render(request, 'estimation/estimation_start.html', {'params': params})	

def years(request, rlk_id):

    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    object                          = DocRLK.objects.get(id=rlk_id)
    reg_interactiv_ocenka, created  = RegInteractivOcenka.objects.get_or_create(rlk = object)
    
    year_filter = ''
    if reg_interactiv_ocenka.vin != '':
        try:
            car             = get_car(reg_interactiv_ocenka)
            year_filter     = car.year
        except:
            year_filter     = ''

    list_years  = list()
    start       = 2025
    end         = 1960
    while start > end:
        list_years.append(str(start))
        start = start - 1

    params = {
        'rlk_id'        : rlk_id,
        'years'         : list_years,
        'year_filter'   : year_filter
    }   
    
    return render(request, 'estimation/estimation_years.html', {'params': params})


def catalog(request, years, rlk_id):

    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    object                          = DocRLK.objects.get(id=rlk_id)
    reg_interactiv_ocenka, created  = RegInteractivOcenka.objects.get_or_create(rlk = object)
    if reg_interactiv_ocenka.year == 0:
        reg_interactiv_ocenka.year = int(years)
        reg_interactiv_ocenka.save( )
    
    year = int(years)
    modifications   = AutoruModification.objects.filter(ProductionStartYear__lte = year).filter(ProductionEndYear__gte = year) | AutoruModification.objects.filter(ProductionStartYear__lte = year).filter(ProductionEndYear = 2050) 
    marks_id        = modifications.values('model__mark__id') 
    params = {
        'rlk_id'    : rlk_id,
        'year'      : year,
        'marks'     : AutoruMark.objects.filter(pk__in = marks_id).distinct().order_by('name')
    }   
    
    return render(request, 'estimation/estimation_catalog.html', {'params': params})


def models(request, rlk_id, years, mark_id):
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    year = int(years)
    mark = AutoruMark.objects.get(pk = mark_id)
    
    modifications   = AutoruModification.objects.filter(model__mark = mark).filter(ProductionStartYear__lte = year).filter(ProductionEndYear__gte = year) | AutoruModification.objects.filter(model__mark = mark).filter(ProductionStartYear__lte = year).filter(ProductionEndYear = 2050) 
    model_id        = modifications.values('model__id') 
    
    params = {
        'rlk_id'    : rlk_id,
        'year'      : year,
        'mark'      : mark,
        'objects'   : AutoruModel.objects.filter(mark = mark).filter(pk__in = model_id).distinct().order_by('name')
    }   
    
    return render(request, 'estimation/estimation_catalog_model.html', {'params': params})


def modifications(request, rlk_id, years, mark_id, model_id):
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    year    = int(years)
    mark    = AutoruMark.objects.get(pk = mark_id)
    model   = AutoruModel.objects.get(pk = model_id)
    
    modifications   = AutoruModification.objects.filter(model = model).filter(ProductionStartYear__lte = year).filter(ProductionEndYear__gte = year) | AutoruModification.objects.filter(model = model).filter(ProductionStartYear__lte = year).filter(ProductionEndYear = 2050) 
    
    params = {
        'rlk_id'    : rlk_id,
        'year'      : year,
        'mark'      : mark,
        'model'     : model,
        'objects'   : modifications.order_by('name')
    }   
    
    return render(request, 'estimation/estimation_catalog_modidication.html', {'params': params})


def osmotr(request, rlk_id, type):
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    object                          = DocRLK.objects.get(id=rlk_id)
    reg_interactiv_ocenka, created  = RegInteractivOcenka.objects.get_or_create(rlk = object)
    return_page                     = request.GET.get('return', '')
    list_info       = list()
    json_data       = list()
    bodys_info      = list()

    type_name = 'передняя часть'

    if type == 'pered':
        type_name = 'передняя часть'
    if type == 'vod':
        type_name = 'водительская сторона'
    if type == 'pass':
        type_name = 'пассажирская сторона'
    if type == 'zad':
        type_name = 'задняя сторона'
    if type == 'up':
        type_name = 'крыша'

    if request.method == 'POST':
        
        type_file   = 'array_images_pered'
        return_page = request.POST.get('return_page', '')

        if type == 'pered':
            url_base_64 = request.POST.get('url_image')
            url_base = url_base_64.split(',')[1].encode()
            file_name = 'imageViewOsmotrPered_maximum_' + str(object.id) +'.jpg'
            decoded_data_1 = ContentFile(base64.b64decode(url_base), name = file_name)
            type_file = 'vnesh_car_osmotr_pered'
            new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = type_file)
            new_estimation_files.name           = file_name
            new_estimation_files.type_file      = type_file
            new_estimation_files.file           = decoded_data_1
            new_estimation_files.user           = request.user
            new_estimation_files.save()
            type_file = 'array_images_pered'
        elif type == 'vod':
            url_base_64     = request.POST.get('url_image')
            url_base        = url_base_64.split(',')[1].encode()
            file_name       = 'imageViewOsmotrVod_maximum_' + str(object.id) +'.jpg'
            decoded_data_1  = ContentFile(base64.b64decode(url_base), name = file_name)
            type_file       = 'vnesh_car_osmotr_vod'
            new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = type_file)
            new_estimation_files.name           = file_name
            new_estimation_files.type_file      = type_file
            new_estimation_files.file           = decoded_data_1
            new_estimation_files.user           = request.user
            new_estimation_files.save()
            type_file = 'array_images_vod'
        elif type == 'pass':
            url_base_64 = request.POST.get('url_image')
            url_base = url_base_64.split(',')[1].encode()
            file_name = 'imageViewOsmotrPass_maximum_' + str(object.id) +'.jpg'
            decoded_data_1 = ContentFile(base64.b64decode(url_base), name = file_name)
            type_file = 'vnesh_car_osmotr_pass'
            new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = type_file)
            new_estimation_files.name           = file_name
            new_estimation_files.type_file      = type_file
            new_estimation_files.file           = decoded_data_1
            new_estimation_files.user           = request.user
            new_estimation_files.save()
            type_file = 'array_images_pass'
        elif type == 'zad':
            url_base_64 = request.POST.get('url_image')
            url_base = url_base_64.split(',')[1].encode()
            file_name = 'imageViewOsmotrZad_maximum_' + str(object.id) +'.jpg'
            decoded_data_1 = ContentFile(base64.b64decode(url_base), name = file_name)
            type_file = 'vnesh_car_osmotr_zad'
            new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = type_file)
            new_estimation_files.name           = file_name
            new_estimation_files.type_file      = type_file
            new_estimation_files.file           = decoded_data_1
            new_estimation_files.user           = request.user
            new_estimation_files.save()
            type_file = 'array_images_zad'
        elif type == 'up':
            url_base_64 = request.POST.get('url_image')
            url_base = url_base_64.split(',')[1].encode()
            file_name = 'imageViewOsmotrUp_maximum_' + str(object.id) +'.jpg'
            decoded_data_1 = ContentFile(base64.b64decode(url_base), name = file_name)
            type_file = 'vnesh_car_osmotr_up'
            new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = type_file)
            new_estimation_files.name           = file_name
            new_estimation_files.type_file      = type_file
            new_estimation_files.file           = decoded_data_1
            new_estimation_files.user           = request.user
            new_estimation_files.save()
            type_file = 'array_images_up'
            
        RegRegInteractivOcenkaFiles.objects.filter(estimation = reg_interactiv_ocenka).filter(type_file = type_file).delete()

        for key in request.POST.keys():
            
            if key.startswith('photo_type_'):
                photo_type_     = request.POST.get(key)
                uid             = key.replace('photo_type_', '')  
                photo_x_        = int(request.POST.get('photo_x_' + uid).split('.')[0])
                photo_y_        = int(request.POST.get('photo_y_' + uid).split('.')[0])
                photo_text_     = request.POST.get('photo_text_' + uid, '')
                photo_name_     = request.POST.get('photo_name_' + uid, '')
                photo_date_     = request.POST.get('photo_date_' + uid, '')

                s = datetime.strptime(photo_date_, '%d-%m-%Y %H:%M')

                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = type_file, type_point = photo_type_, text = photo_text_, cor_x = photo_x_, cor_y = photo_y_)
                new_estimation_files.name           = photo_name_
                new_estimation_files.text           = photo_text_
                new_estimation_files.type_point     = photo_type_
                new_estimation_files.cor_x          = photo_x_
                new_estimation_files.cor_y          = photo_y_
                new_estimation_files.date           = s
                new_estimation_files.user           = request.user
                
                if len(photo_text_) > 0:
                    new_estimation_files.kraska         = int(photo_text_)

                if request.FILES.get('photo_' + uid) != None:
                    file_object                 = request.FILES.get('photo_' + uid) 
                    new_estimation_files.file   = file_object
                else:
                    new_estimation_files.blank  = True    
                new_estimation_files.save()

        if return_page == 'eco':
            save_recovery_estimations(reg_interactiv_ocenka)
            return HttpResponseRedirect('/eco/' + rlk_id + '/?page=21')    
        return HttpResponseRedirect('/estimations/' + rlk_id + '/?page=3')
    else:
          
        if type == 'pered':
            type_name = 'передняя сторона'
            type_file = 'array_images_pered'
            bodys_info      = RegInfoBody.objects.filter(type_body = 'седан').filter(side = 'перед')
        if type == 'vod':
            type_name = 'водительская сторона'
            type_file = 'array_images_vod'
            bodys_info      = RegInfoBody.objects.filter(type_body = 'седан').filter(side = 'водительская')
        if type == 'pass':
            type_name = 'пассажирская сторона'
            type_file = 'array_images_pass'
            bodys_info      = RegInfoBody.objects.filter(type_body = 'седан').filter(side = 'пассажирская')
        if type == 'zad':
            type_name = 'задняя сторона'
            type_file = 'array_images_zad'
            bodys_info      = RegInfoBody.objects.filter(type_body = 'седан').filter(side = 'зад')
        if type == 'up':
            type_name = 'крыша' 
            type_file = 'array_images_up'
            bodys_info      = RegInfoBody.objects.filter(type_body = 'седан').filter(side = 'верх')
    
        files_data = RegRegInteractivOcenkaFiles.objects.filter(estimation = reg_interactiv_ocenka).filter(type_file = type_file).order_by('date')
        for files in files_data:
            tol             = False
            f_type_array    = files.type_point
            type_array      = ''
            text_cor        = ''
            
            if f_type_array == 'толщиномер':
                type_array  = 'tol'
                tol         = True
                text_cor    = str(files.kraska)
            elif f_type_array == 'наклейка':
                type_array = 'stiker'
            elif f_type_array == 'тонировка':
                type_array = 'toner'
            elif f_type_array == 'полировка':
                type_array = 'poly'
            elif f_type_array == 'вмятина':
                type_array = 'vmyat'
            elif f_type_array == 'вмятина сильная':
                type_array = 'vmyat_strong'
            elif f_type_array == 'царапина':
                type_array = 'carap'
            elif f_type_array == 'царапина сильная':
                type_array = 'carap_strong'
            elif f_type_array == 'ржавчина':
                type_array = 'rzav'
            elif f_type_array == 'ржавчина сквозная':
                type_array = 'rzav_strong'
            elif f_type_array == 'скол':
                type_array = 'skol'
            elif f_type_array == 'трещина':
                type_array = 'tr'
            elif f_type_array == 'заменен':
                type_array = 'replace'
            elif f_type_array == 'заменить':
                type_array = 'replace_add'

            date_str    = '' 
            file_date   = files.date
            if file_date != None:
                date_str = file_date.strftime('%d-%m-%Y %H:%M')
            x_cor       = files.cor_x
            y_cor       = files.cor_y
            data_to_list    = list()
            data_to_list.append(type_array)
            data_to_list.append(x_cor)
            data_to_list.append(y_cor)
            data_to_list.append(tol)
            data_to_list.append(text_cor)
            data_to_list.append(files.pk)
            data_to_list.append(date_str)
            json_data.append(data_to_list)

    elements_body   = list()
    
    for body in bodys_info:
        name        = body.body_element
        polygon_x   = list()
        polygon_y   = list()
        poly_str = body.polygon
        lens_str = poly_str.split(',')
        len_mas  = len(lens_str)
        s = 0
        while s < len_mas:
            if s % 2 == 0:
                polygon_x.append(int(lens_str[s]))   
                polygon_y.append(int(lens_str[s+1]))
            s = s + 1
        info_body_element = {
            'name'      : name,
            'coor_x'    : polygon_x,
            'coor_y'    : polygon_y,
        }
        elements_body.append(info_body_element)

        

    params = {
        'rlk_id'        : rlk_id,
        'estimation'    : reg_interactiv_ocenka,
        'type'          : type,
        'return_page'   : return_page,
        'type_name'     : type_name,
        'elements_body' : json.dumps(elements_body),
        'json_data'     : json.dumps(json_data)
    }   
    
    return render(request, 'estimation/estimation_doc_body_osmotr.html', {'params': params})


def osmotr_salon(request, rlk_id, type):
    
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/?next=' + request.build_absolute_uri())
    
    object                          = DocRLK.objects.get(id=rlk_id)
    reg_interactiv_ocenka, created  = RegInteractivOcenka.objects.get_or_create(rlk = object)
    return_page                     = request.GET.get('return', '')
    list_info       = list()
    json_data       = list()
    salons_info     = list()

    type_name = 'передняя часть'

    if type == 'page_osmotr_salon':
        type_name = 'осмотр салона автомобиля'

    if request.method == 'POST':
        
        type_file   = 'osmotr_salon'
        return_page = request.POST.get('return_page', '')

        if type == 'page_osmotr_salon':
            url_base_64 = request.POST.get('url_image')
            url_base = url_base_64.split(',')[1].encode()
            file_name = 'osmotr_salon_' + str(object.id) +'.jpg'
            decoded_data_1 = ContentFile(base64.b64decode(url_base), name = file_name)
            type_file = 'osmotr_salon'
            new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = type_file)
            new_estimation_files.name           = file_name
            new_estimation_files.type_file      = type_file
            new_estimation_files.file           = decoded_data_1
            new_estimation_files.user           = request.user
            new_estimation_files.save()
            type_file = 'array_images_osmotr_salon'
            
        RegRegInteractivOcenkaFiles.objects.filter(estimation = reg_interactiv_ocenka).filter(type_file = type_file).delete()

        for key in request.POST.keys():
            
            if key.startswith('photo_type_'):
                photo_type_     = request.POST.get(key)
                uid             = key.replace('photo_type_', '')  
                photo_x_        = int(request.POST.get('photo_x_' + uid).split('.')[0])
                photo_y_        = int(request.POST.get('photo_y_' + uid).split('.')[0])
                photo_text_     = request.POST.get('photo_text_' + uid, '')
                photo_name_     = request.POST.get('photo_name_' + uid, '')
                photo_date_     = request.POST.get('photo_date_' + uid, '')

                s = datetime.strptime(photo_date_, '%d-%m-%Y %H:%M')

                new_estimation_files, created       = RegRegInteractivOcenkaFiles.objects.get_or_create(estimation = reg_interactiv_ocenka, type_file = type_file, type_point = photo_type_, text = photo_text_, cor_x = photo_x_, cor_y = photo_y_)
                new_estimation_files.name           = photo_name_
                new_estimation_files.text           = photo_text_
                new_estimation_files.type_point     = photo_type_
                new_estimation_files.cor_x          = photo_x_
                new_estimation_files.cor_y          = photo_y_
                new_estimation_files.date           = s
                new_estimation_files.user           = request.user
                
                if request.FILES.get('photo_' + uid) != None:
                    file_object                 = request.FILES.get('photo_' + uid) 
                    new_estimation_files.file   = file_object
                else:
                    new_estimation_files.blank  = True    
                new_estimation_files.save()

        if return_page == 'eco':
            save_recovery_estimations(reg_interactiv_ocenka)
            return HttpResponseRedirect('/eco/' + rlk_id + '/?page=21')    
        return HttpResponseRedirect('/estimations/' + rlk_id + '/?page=2')
    else:
          
        if type == 'page_osmotr_salon':
            type_name           = 'осмотр салона автомобиля'
            type_file           = 'array_images_osmotr_salon'
            salons_info         = RegInfoBody.objects.filter(type_body = 'седан').filter(side = 'салон')
        
        files_data = RegRegInteractivOcenkaFiles.objects.filter(estimation = reg_interactiv_ocenka).filter(type_file = type_file).order_by('date')
        for files in files_data:
            tol             = False
            f_type_array    = files.type_point
            type_array      = ''
            text_cor        = ''
            
            if f_type_array == 'перекрас':
                type_array = 'perecras'
            elif f_type_array == 'перешив':
                type_array = 'pereshiv'
            elif f_type_array == 'дырка':
                type_array = 'dirka'
            elif f_type_array == 'восстановление':
                type_array = 'vost'

            date_str    = '' 
            file_date   = files.date
            if file_date != None:
                date_str = file_date.strftime('%d-%m-%Y %H:%M')

            x_cor       = files.cor_x
            y_cor       = files.cor_y
            data_to_list    = list()
            data_to_list.append(type_array)
            data_to_list.append(x_cor)
            data_to_list.append(y_cor)
            data_to_list.append(tol)
            data_to_list.append(text_cor)
            data_to_list.append(files.pk)
            data_to_list.append(date_str)
            json_data.append(data_to_list)

    elements_salon   = list()
    
    for salon in salons_info:
        name        = salon.body_element
        polygon_x   = list()
        polygon_y   = list()
        poly_str = salon.polygon
        lens_str = poly_str.split(',')
        len_mas  = len(lens_str)
        s = 0
        while s < len_mas:
            if s % 2 == 0:
                polygon_x.append(int(lens_str[s]))   
                polygon_y.append(int(lens_str[s+1]))
            s = s + 1
        info_salon_element = {
            'name'      : name,
            'coor_x'    : polygon_x,
            'coor_y'    : polygon_y,
        }
        elements_salon.append(info_salon_element)

        

    params = {
        'rlk_id'            : rlk_id,
        'estimation'        : reg_interactiv_ocenka,
        'type'              : type,
        'return_page'       : return_page,
        'type_name'         : type_name,
        'elements_salon'    : json.dumps(elements_salon),
        'json_data'         : json.dumps(json_data)
    }   
    
    return render(request, 'estimation/estimation_doc_salon_osmotr.html', {'params': params})


def get_mark_tyres(name):
    if len(name) > 0:
        count_objects = RefMarkTyres.objects.filter(name = name).count() 
        if count_objects > 0:
            return RefMarkTyres.objects.filter(name = name)[0]    
    return None


def sends_user_info(reg_interactiv_ocenka, uss_base):
    return RegInteractivOcenkaEmailPush.objects.filter(estimation = reg_interactiv_ocenka).filter(user = uss_base).count()
          

def send_channel_message(user, id_rlk = 0, message = ''):

    '''
    group_name_chat = 'chat_rlk_' + str(id_rlk)
    group_name      = 'rlk_' + str(id_rlk)
    chat_object     = Chat.objects.get(slug = group_name)
    message = {
            'chat_id'       : str(chat_object.id),
            'name'          : str(user),
            'chat'          : group_name,
            'message'       : message,
            'username'      : str(user),
            'last_name'     : user.last_name,
            'first_name'    : user.first_name,
            'psevdo_name'   : user.profiles.eco_name
        }

    message_json = json.dumps(message)
    '''

    #channel_layer = get_channel_layer()
    '''
    async_to_sync(channel_layer.group_send)(
        group_name_chat,
        {'type'     : 'channel_message',
         'message'  : message_json}
    )
'''
    message = {
            'chat_id'       : str(''),
            'name'          : str(user),
            'chat'          : 'rlk_list_eco',
            'message'       : message,
            'username'      : str(user),
            'last_name'     : user.last_name,
            'first_name'    : user.first_name,
            'psevdo_name'   : user.profiles.eco_name
        }
    
    message_json = json.dumps(message)
    #asyncio.get_event_loop().run_until_complete(connect_to_server('rlk_list_eco', message_json))
    
    #await connect_to_server('rlk_list_eco', message_json)
    
'''
@sync_to_async
def connect_to_server(group, text):

    async with websockets.connect("wss://ah.kors-group.com/ws/" + group + "/") as websocket:
        await websocket.send(text)
        response = await websocket.recv()
        
'''

# API endpoints для новой страницы начала оценки

from django.http import JsonResponse
from rest_framework.decorators import api_view

@api_view(['GET'])
def api_get_models_by_mark(request, rlk_id):
    """Получение моделей по марке и году"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    mark_id = request.GET.get('mark_id', '')
    year = request.GET.get('year', '')
    
    if not mark_id or not year:
        return JsonResponse({'models': []})
    
    try:
        mark = AutoruMark.objects.get(pk=mark_id)
        year_int = int(year)
        
        # Получаем модели, которые имеют модификации для указанного года
        modifications = AutoruModification.objects.filter(
            model__mark=mark
        ).filter(
            Q(ProductionStartYear__lte=year_int) & 
            (Q(ProductionEndYear__gte=year_int) | Q(ProductionEndYear=2050))
        )
        
        model_ids = modifications.values_list('model__id', flat=True).distinct()
        models = AutoruModel.objects.filter(pk__in=model_ids, mark=mark).order_by('name')
        models_data = [{'id': m.id, 'name': m.name} for m in models]
        return JsonResponse({'models': models_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@api_view(['GET'])
def api_get_marks_by_year(request, rlk_id):
    """Получение марок по году выпуска"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    year = request.GET.get('year', '')
    if not year:
        return JsonResponse({'marks': []})
    
    try:
        year_int = int(year)
        
        # Получаем марки, которые имеют модификации для указанного года
        modifications = AutoruModification.objects.filter(
            Q(ProductionStartYear__lte=year_int) & 
            (Q(ProductionEndYear__gte=year_int) | Q(ProductionEndYear=2050))
        )
        
        mark_ids = modifications.values_list('model__mark__id', flat=True).distinct()
        marks = AutoruMark.objects.filter(pk__in=mark_ids).order_by('name')
        marks_data = [{'id': m.id, 'name': m.name} for m in marks]
        return JsonResponse({'marks': marks_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@api_view(['GET'])
def api_get_modifications_by_model_year(request, rlk_id):
    """Получение модификаций по модели, году и фильтрам (тип кузова, тип двигателя, КПП)"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    model_id = request.GET.get('model_id', '')
    year = request.GET.get('year', '')
    type_body_id = request.GET.get('type_body_id', '')
    type_engine_id = request.GET.get('type_engine_id', '')
    type_kpp_id = request.GET.get('type_kpp_id', '')
    
    if not model_id or not year:
        return JsonResponse({'modifications': []})
    
    try:
        model = AutoruModel.objects.get(pk=model_id)
        year_int = int(year)
        
        modifications = AutoruModification.objects.filter(
            model=model
        ).filter(
            Q(ProductionStartYear__lte=year_int) & 
            (Q(ProductionEndYear__gte=year_int) | Q(ProductionEndYear=2050))
        )
        
        # Применяем фильтры, если они указаны
        if type_body_id:
            try:
                modifications = modifications.filter(typeBody_id=int(type_body_id))
            except (ValueError, TypeError):
                pass
        
        if type_engine_id:
            try:
                modifications = modifications.filter(typeEngine_id=int(type_engine_id))
            except (ValueError, TypeError):
                pass
        
        if type_kpp_id:
            try:
                modifications = modifications.filter(typeGear_id=int(type_kpp_id))
            except (ValueError, TypeError):
                pass
        
        modifications = modifications.order_by('name')
        
        modifications_data = []
        for mod in modifications:
            mod_data = {
                'id': mod.id,
                'name': mod.name,
                'type_body_id': mod.typeBody.id if mod.typeBody else None,
                'type_body_name': mod.typeBody.name if mod.typeBody else '',
                'type_engine_id': mod.typeEngine.id if mod.typeEngine else None,
                'type_engine_name': mod.typeEngine.name if mod.typeEngine else '',
                'type_kpp_id': mod.typeGear.id if mod.typeGear else None,
                'type_kpp_name': mod.typeGear.name if mod.typeGear else '',
                'engine_volume': mod.engineVolume,
                'engine_power': mod.enginePower,
            }
            modifications_data.append(mod_data)
        
        return JsonResponse({'modifications': modifications_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@api_view(['GET'])
def api_get_body_types_by_model(request, rlk_id):
    """Получение доступных типов кузова для модели и года"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    model_id = request.GET.get('model_id', '')
    year = request.GET.get('year', '')
    
    if not model_id or not year:
        return JsonResponse({'body_types': []})
    
    try:
        model = AutoruModel.objects.get(pk=model_id)
        year_int = int(year)
        
        # Получаем все модификации для модели и года
        modifications = AutoruModification.objects.filter(
            model=model
        ).filter(
            Q(ProductionStartYear__lte=year_int) & 
            (Q(ProductionEndYear__gte=year_int) | Q(ProductionEndYear=2050))
        ).exclude(typeBody__isnull=True)
        
        # Получаем уникальные типы кузова
        body_type_ids = modifications.values_list('typeBody_id', flat=True).distinct()
        body_types = RefTypeBody.objects.filter(pk__in=body_type_ids).order_by('name')
        body_types_data = [{'id': b.id, 'name': b.name} for b in body_types]
        return JsonResponse({'body_types': body_types_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@api_view(['GET'])
def api_get_engine_types_by_model(request, rlk_id):
    """Получение доступных типов двигателя для модели и года"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    model_id = request.GET.get('model_id', '')
    year = request.GET.get('year', '')
    
    if not model_id or not year:
        return JsonResponse({'engine_types': []})
    
    try:
        model = AutoruModel.objects.get(pk=model_id)
        year_int = int(year)
        
        # Получаем все модификации для модели и года
        modifications = AutoruModification.objects.filter(
            model=model
        ).filter(
            Q(ProductionStartYear__lte=year_int) & 
            (Q(ProductionEndYear__gte=year_int) | Q(ProductionEndYear=2050))
        ).exclude(typeEngine__isnull=True)
        
        # Получаем уникальные типы двигателя
        engine_type_ids = modifications.values_list('typeEngine_id', flat=True).distinct()
        engine_types = RefTypeEngine.objects.filter(pk__in=engine_type_ids).order_by('name')
        engine_types_data = [{'id': e.id, 'name': e.name} for e in engine_types]
        return JsonResponse({'engine_types': engine_types_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@api_view(['GET'])
def api_get_kpp_types_by_model(request, rlk_id):
    """Получение доступных типов КПП для модели и года"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    model_id = request.GET.get('model_id', '')
    year = request.GET.get('year', '')
    
    if not model_id or not year:
        return JsonResponse({'kpp_types': []})
    
    try:
        model = AutoruModel.objects.get(pk=model_id)
        year_int = int(year)
        
        # Получаем все модификации для модели и года
        modifications = AutoruModification.objects.filter(
            model=model
        ).filter(
            Q(ProductionStartYear__lte=year_int) & 
            (Q(ProductionEndYear__gte=year_int) | Q(ProductionEndYear=2050))
        ).exclude(typeGear__isnull=True)
        
        # Получаем уникальные типы КПП
        kpp_type_ids = modifications.values_list('typeGear_id', flat=True).distinct()
        kpp_types = RefTypeKpp.objects.filter(pk__in=kpp_type_ids).order_by('name')
        kpp_types_data = [{'id': k.id, 'name': k.name} for k in kpp_types]
        return JsonResponse({'kpp_types': kpp_types_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@api_view(['GET'])
def api_get_complectations_by_modification(request, rlk_id):
    """Получение комплектаций по модификации"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    modification_id = request.GET.get('modification_id', '')
    if not modification_id:
        return JsonResponse({'complectations': []})
    
    try:
        modification = AutoruModification.objects.get(pk=modification_id)
        complectations = AutoruComplectation.objects.filter(modification=modification).order_by('name')
        complectations_data = [{'id': c.id, 'name': c.name} for c in complectations]
        return JsonResponse({'complectations': complectations_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@api_view(['GET'])
def api_get_complectation_options(request, rlk_id):
    """Опции комплектации из AvtohubComplectations по autoruId (AutoruComplectation.idSite), с группировкой по AvtohubGroupOptions"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    complectation_id = request.GET.get('complectation_id', '')
    if not complectation_id:
        return JsonResponse({'groups': [], 'total_count': 0})
    
    try:
        complectation = AutoruComplectation.objects.get(pk=complectation_id)
        autoru_id = complectation.idSite
        if autoru_id is None:
            return JsonResponse({'groups': [], 'total_count': 0})
        
        avtohub_comp = AvtohubComplectations.objects.filter(autoruId=autoru_id).first()
        if not avtohub_comp:
            return JsonResponse({'groups': [], 'total_count': 0})
        
        options = avtohub_comp.equipment.select_related('groupId').order_by('groupId__sortOrder', 'groupId__name', 'sortOrder', 'name')
        
        groups_dict = {}
        for opt in options:
            group = opt.groupId
            group_key = group.id if group else 0
            if group_key not in groups_dict:
                groups_dict[group_key] = {
                    'id': group.id if group else None,
                    'name': group.name if group else 'Без группы',
                    'sortOrder': group.sortOrder if group else 999,
                    'options': [],
                    'count': 0,
                }
            groups_dict[group_key]['options'].append({'id': opt.id, 'name': opt.name or ''})
            groups_dict[group_key]['count'] += 1
        
        groups = sorted(groups_dict.values(), key=lambda g: (g['sortOrder'], g['name'] or ''))
        total_count = sum(g['count'] for g in groups)
        return JsonResponse({'groups': groups, 'total_count': total_count})
    except AutoruComplectation.DoesNotExist:
        return JsonResponse({'groups': [], 'total_count': 0})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@api_view(['GET'])
def api_get_previous_estimation(request, rlk_id):
    """Получение данных предыдущей оценки по VIN"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    vin = request.GET.get('vin', '').strip()
    body_number = request.GET.get('body_number', '').strip()
    
    if not vin and not body_number:
        return JsonResponse({'estimation': None})
    
    try:
        object = DocRLK.objects.get(id=rlk_id)
        reg_interactiv_ocenka, created = RegInteractivOcenka.objects.get_or_create(rlk=object)
        
        # Ищем предыдущую оценку
        query = Q()
        if vin:
            query |= Q(vin=vin)
        if body_number:
            query |= Q(number_body=body_number)
        
        previous_estimation = RegInteractivOcenka.objects.filter(query).exclude(
            id=reg_interactiv_ocenka.id
        ).order_by('-start_estimation').first()
        
        if not previous_estimation:
            return JsonResponse({'estimation': None})
        
        estimation_data = {
            'id': previous_estimation.id,
            'vin': previous_estimation.vin,
            'number_body': previous_estimation.number_body,
            'year': previous_estimation.year,
            'type_drive': previous_estimation.type_drive,
            'start_estimation': previous_estimation.start_estimation.strftime('%Y-%m-%d') if previous_estimation.start_estimation else None,
        }
        
        # Данные модификации
        if previous_estimation.modification:
            mod = previous_estimation.modification
            estimation_data['modification'] = {
                'id': mod.id,
                'name': mod.name,
                'modification_id': mod.id if mod else None,
                'modification_name': mod.name if mod else '',
                'model_id': mod.model.id if mod.model else None,
                'model_name': mod.model.name if mod.model else '',
                'mark_id': mod.model.mark.id if mod.model and mod.model.mark else None,
                'mark_name': mod.model.mark.name if mod.model and mod.model.mark else '',
                'type_body_id': mod.typeBody.id if mod.typeBody else None,
                'type_body_name': mod.typeBody.name if mod.typeBody else '',
                'type_engine_id': mod.typeEngine.id if mod.typeEngine else None,
                'type_engine_name': mod.typeEngine.name if mod.typeEngine else '',
                'type_kpp_id': mod.typeGear.id if mod.typeGear else None,
                'type_kpp_name': mod.typeGear.name if mod.typeGear else '',
            }
        
        # Данные комплектации
        if previous_estimation.complectation:
            estimation_data['complectation'] = {
                'id': previous_estimation.complectation.id,
                'name': previous_estimation.complectation.name,
            }
        
        # Данные из документов
        if previous_estimation.page_documents:
            doc = previous_estimation.page_documents
            estimation_data['documents'] = {
                'pts_number': doc.pts_number,
                'pts_date': doc.pts_date.strftime('%Y-%m-%d') if doc.pts_date else None,
                'pts_original': doc.pts_original,
                'count_owners': doc.count_owners,
            }
        
        # Пробег из салона
        if previous_estimation.page_salon:
            estimation_data['run'] = previous_estimation.page_salon.run
        
        return JsonResponse({'estimation': estimation_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@api_view(['GET'])
def api_get_repair_history(request, rlk_id):
    """История ремонтов по VIN (session auth)"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    vin = request.GET.get('vin', '').strip()
    if not vin:
        return JsonResponse({'objects': [], 'objects_count': 0})
    try:
        docs = DocZN.objects.filter(cars__vin__icontains=vin).filter(closed=True).order_by('-dataTime')
        objects = []
        for d in docs:
            objects.append({
                'slug': d.id,
                'date': d.dataTime.strftime('%d.%m.%Y %H:%M:%S') if d.dataTime else 'Не указано',
                'amount_doc': float(d.amount) if d.amount else 0,
                'run_car': d.run or 0,
                'type_repair_name': d.typeRemont.name if d.typeRemont else 'Ремонт',
                'staff_name': d.master.name if d.master else '',
                'unit_name': d.unit.name if d.unit else '',
            })
        return JsonResponse({'objects': objects, 'objects_count': len(objects)})
    except Exception as e:
        return JsonResponse({'objects': [], 'objects_count': 0, 'error': str(e)})


@api_view(['GET'])
def api_get_estimation_history(request, rlk_id):
    """История оценок по VIN (session auth)"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    vin = request.GET.get('vin', '').strip()
    if not vin:
        return JsonResponse({'objects': [], 'objects_count': 0})
    try:
        objects = []
        # RegInteractivOcenka (интерактивные оценки)
        for est in RegInteractivOcenka.objects.filter(vin=vin).order_by('-start_estimation')[:50]:
            rlk_id = est.rlk.id if est.rlk else None
            car_name = ''
            if est.modification:
                car_name = f"{est.modification.model.mark.name if est.modification.model and est.modification.model.mark else ''} {est.modification.model.name if est.modification.model else ''} {est.modification.name}".strip()
            objects.append({
                'slug': rlk_id,
                'rlk_id': rlk_id,
                'date': est.start_estimation.strftime('%d.%m.%Y %H:%M:%S') if est.start_estimation else 'Не указано',
                'cost_price_doc': 0,
                'run_car': est.page_salon.run if est.page_salon else 0,
                'year_car': est.year or '',
                'mark': est.modification.model.mark.name if est.modification and est.modification.model and est.modification.model.mark else '',
                'model': est.modification.model.name if est.modification and est.modification.model else '',
                'car_name': car_name,
                'staff_name': est.staff.name if est.staff else '',
                'unit_name': est.rlk.unit.name if est.rlk and est.rlk.unit else '',
                'number': '',
            })
        # DocLO (документы оценки)
        lo_qs = DocLO.objects.filter(vin=vin).order_by('-dataTime')[:50]
        for lo in lo_qs:
            if RegInteractivOcenka.objects.filter(rlk=lo.rlk).exists():
                continue
            rlk_id = lo.rlk.id if lo.rlk else None
            mod = lo.modification_autoru if hasattr(lo, 'modification_autoru') and lo.modification_autoru else None
            objects.append({
                'slug': rlk_id,
                'rlk_id': rlk_id,
                'date': lo.dataTime.strftime('%d.%m.%Y %H:%M:%S') if lo.dataTime else 'Не указано',
                'cost_price_doc': float(lo.cost_price) if lo.cost_price else 0,
                'run_car': lo.run or 0,
                'year_car': lo.year or '',
                'mark': mod.model.mark.name if mod and mod.model and mod.model.mark else '',
                'model': mod.model.name if mod and mod.model else '',
                'car_name': mod.name if mod else '',
                'staff_name': lo.staff.name if lo.staff else '',
                'unit_name': lo.unit.name if lo.unit else '',
                'number': lo.nomer or '',
            })
        objects.sort(key=lambda x: x['date'] or '', reverse=True)
        return JsonResponse({'objects': objects[:50], 'objects_count': len(objects)})
    except Exception as e:
        return JsonResponse({'objects': [], 'objects_count': 0, 'error': str(e)})
