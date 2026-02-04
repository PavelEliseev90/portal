from django.shortcuts import render
from django.shortcuts import render, get_object_or_404
from django.http import Http404, HttpResponseRedirect, HttpResponseNotFound, HttpResponse
from telephony.models import MangoGroup, MangoNumberSip, MangoNumberSipGroup, MangoHystoryCalls, MangoHystoryCallsRecords, Telephony_Recognition_Tematika, Telephony_Recognition_Dictonary, Telephony_Recognition_Tematika_fraza, Telephony_records_queue, Telephony_Recognition_Dictonary, Telephony_Recognition_Dictonary_Model, Telephony_question
import requests
import hashlib
import json
import unicodedata
import datetime
import time
import datetime as DT
from django.core.paginator import Paginator
from documents.models import DocRLK, SurveysOP
from django.db.models import OuterRef, Subquery, Sum
from refs.models import RefUnit
import os
import urllib.request
from django.views.decorators.csrf import csrf_exempt
from django.http.response import JsonResponse
from rest_framework import status
import urllib.parse
from fuzzywuzzy import fuzz


mango_url       = 'https://app.mango-office.ru/vpbx/'
mango_api_key   = 'ko9yxp3j8vrqcd588wtm2v7iqq2qtr13'
mango_api_salt  = '50stgl3e7kuanp8mcsy4dwduc6awn2pj'

path_sounds_kg          = r'\\a01srvfs\\PBX\\A15\\sounds\\'
path_sounds_kg_external = 'http://ah.kors-group.com:8011/sounds/'
#path_sounds_kg_external = 'http://ah.kors-group.com/media/'
###
##
# Служебные функции

###
##
#WEB
def telephony_recognitions(request):
    if request.user.is_authenticated:
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

        # Оптимизация: объединяем count запросы
        from django.db.models import Q
        
        # Статические данные (можно кешировать)
        tematiks_count = Telephony_Recognition_Tematika.objects.filter(direction=1).count()
        questions_count = Telephony_question.objects.filter(direction=1).count()
        
        # Оптимизация: используем select_related для rlk
        op_queue_base = Telephony_records_queue.objects.filter(direction=1, data_json='').select_related('rlk')
        op_queue_doc = op_queue_base.values('rlk').distinct().count()
        op_queue = op_queue_base.count()
        
        # Оптимизация: сложный запрос с subquery
        op_queue_doc_succsecc = Telephony_records_queue.objects.filter(
            direction=1,
            rlk__dataTime__gte=date_start,
            rlk__dataTime__lte=date_end
        ).exclude(data_json='').select_related('rlk')
        subquery = Subquery(Telephony_records_queue.objects.filter(
            rlk_id=OuterRef(name='rlk_id'),
            data_json=''
        ).values('rlk')[:1])        
        op_queue_doc_succsecc = op_queue_doc_succsecc.annotate(queue=subquery).filter(queue=None).values('rlk').distinct().count()
        
        # Оптимизация: объединяем count запросы для словарей
        dictonary_stats = Telephony_Recognition_Dictonary_Model.objects.aggregate(
            total=Count('id'),
            success=Count('id', filter=Q(added=True)),
            fail=Count('id', filter=Q(added=False))
        )
        dictonary_count = Telephony_Recognition_Dictonary.objects.all().count()
        dictonary_model_count = dictonary_stats['total'] or 0
        dictonary_model_count_fail = dictonary_stats['fail'] or 0
        dictonary_model_count_success = dictonary_stats['success'] or 0
        
        filtr = {
            'date_start'    : date_start,
            'date_end'      : date_end
        }
        params = {
            'type'                      : 'telephony_recognitions',
            'filtr'                     : filtr,
            'tematiks_count'            : tematiks_count,
            'questions_count'           : questions_count,
            'op_queue'                  : op_queue,
            'op_queue_doc'              : op_queue_doc,
            'op_queue_doc_succsecc'     : op_queue_doc_succsecc,
            'dictonary_count'           : dictonary_count,
            'dictonary_model_count'     : dictonary_model_count,
            'dictonary_model_count_fail'    : dictonary_model_count_fail,
            'dictonary_model_count_success' : dictonary_model_count_success
        }
        return render(request, 'telephony/telephony_recognition_start.html', {'params': params})
    else:
        return HttpResponseRedirect('/')
    

def telephony_queue(request):
    if request.user.is_authenticated:
        select_count    = 25
        
        if 'select_count' in request.GET:
            select_count = int(request.GET.get('select_count'))
        
        object_list     = Telephony_records_queue.objects.filter(direction = 1).filter(data_json = '').values('rlk', 'rlk__nomer', 'rlk__dataTime', 'rlk__unit__name', 'rlk__staff__name').distinct()
        object_list     = object_list.order_by('-rlk__dataTime')
        
        page_number = request.GET.get('page')
        paginator   = Paginator(object_list, select_count)
        page_obj    = paginator.get_page(page_number)

        params = {
            'type'                      : 'telephony_recognitions',
            'paginator'                 : page_obj
        }
        return render(request, 'telephony/telephony_queue.html', {'params': params})
    else:
        return HttpResponseRedirect('/')
    

def telephony_queue_success(request):
    if request.user.is_authenticated:
        
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
       
        filtr = {
            'date_start'    : date_start,
            'date_end'      : date_end
        }

        data_list = list()
        
        citys               = Telephony_records_queue.objects.all()
        subquery            = Subquery(Telephony_records_queue.objects.filter(rlk_id = OuterRef(name='rlk_id')).filter(data_json = '').values('rlk')[:1])        
        citys               = citys.annotate(queue = subquery).order_by('-rlk__dataTime')
        citys               = citys.filter(queue = None).values('rlk__unit__city', 'rlk__unit__city__name').exclude(data_json = '').distinct().order_by('rlk__unit__city__name')
        
        #citys       = Telephony_records_queue.objects.values('rlk__unit__city', 'rlk__unit__city__name').exclude(data_json = '').distinct().order_by('rlk__unit__city__name')
        #citys       = citys.filter(rlk__dataTime__gte = date_start).filter(rlk__dataTime__lte = date_end)

        for city in citys:
            units       = Telephony_records_queue.objects.annotate(queue = subquery).filter(queue = None).order_by('-rlk__dataTime').filter(rlk__dataTime__gte = date_start).filter(rlk__dataTime__lte = date_end).filter(rlk__unit__city__id = city['rlk__unit__city']).exclude(data_json = '').distinct().values('rlk__unit', 'rlk__unit__name').distinct().order_by('rlk__unit__name')
            units_list  = list()
            count_city      = 0
            duration_city   = 0

            for unit in units:
                count           = Telephony_records_queue.objects.annotate(queue = subquery).filter(queue = None).filter(rlk__dataTime__gte = date_start).filter(rlk__dataTime__lte = date_end).filter(rlk__unit__id = unit['rlk__unit']).exclude(data_json = '').values('rlk').distinct().count()
                duration        = Telephony_records_queue.objects.annotate(queue = subquery).filter(queue = None).filter(rlk__dataTime__gte = date_start).filter(rlk__dataTime__lte = date_end).filter(rlk__unit__id = unit['rlk__unit']).exclude(data_json = True).distinct().aggregate(Sum('duration'))
                count_city      = count_city + count
                duration_city   = duration_city + duration['duration__sum']
                unit_params = {
                    'unit__id'      : unit['rlk__unit'],
                    'unit__name'    : unit['rlk__unit__name'],
                    'count'         : count,
                    'duration'      : time_human(duration['duration__sum'])
                }
                units_list.append(unit_params)
            
            params_city = {
               'city__id'       : city['rlk__unit__city'],
               'city__name'     : city['rlk__unit__city__name'],
               'units'          : units_list,
               'count_city'     : count_city,
               'duration_city'  : time_human(duration_city)
            }
            data_list.append(params_city)

        params = {
            'type'              : 'telephony_recognitions',
            'filtr'             : filtr,
            'data'              : data_list
        }
        return render(request, "telephony/telephony_queue_success.html", {'params': params})    
    else:
        return HttpResponseRedirect('/login')


def telephony_queue_success_unit(request, id):
    if request.user.is_authenticated:
        
        filtr_count     = 0
        select_count    = 25
        
        if 'select_count' in request.GET:
            select_count = int(request.GET.get('select_count'))
        
        date_start      = request.GET.get('date_start', '')
        date_end        = request.GET.get('date_end', '')
        
        date_period = DT.datetime.now()
        
        if len(date_start) == 0:
            date_start 	= date_period.replace(day = 1, hour = 0, minute=0, second=0, microsecond=0)
        else:
            date_start  = DT.datetime.strptime(date_start, '%Y-%m-%d')
            filtr_count = filtr_count + 1
        
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
            filtr_count = filtr_count + 1

        subquery_queue   = Subquery(Telephony_records_queue.objects.filter(rlk_id = OuterRef(name='rlk_id')).filter(data_json = '').values('rlk')[:1])        
        subquery_survey  = Subquery(SurveysOP.objects.filter(rlk_id = OuterRef(name='rlk_id')).values('result')[:1])        
        
        object_list     = Telephony_records_queue.objects.filter(direction = 1).filter(rlk__dataTime__gte = date_start).filter(rlk__dataTime__lte = date_end).exclude(data_json = '').filter(rlk__unit__id = id).values('rlk', 'rlk__nomer', 'rlk__dataTime', 'rlk__unit__name', 'rlk__staff__name').annotate(sum_duration=Sum('duration')).distinct()
        object_list     = object_list.annotate(queue = subquery_queue).filter(queue = None).annotate(survey = subquery_survey)
        
        #object_list     = object_list.annotate(survey = subquery)
        object_list     = object_list.order_by('-rlk__dataTime')
        
        page_number = request.GET.get('page')
        paginator   = Paginator(object_list, select_count)
        page_obj    = paginator.get_page(page_number)
        unit        = RefUnit.objects.get(pk = id)
        
        filtr = {
            'date_start'    : date_start,
            'date_end'      : date_end,
            'filtr_count'   : filtr_count
        }
        
        params = {
            'type'                      : 'telephony_recognitions',
            'filtr'                     : filtr,
            'paginator'                 : page_obj,
            'unit'                      : unit
        }
        return render(request, 'telephony/telephony_queue_success_unit.html', {'params': params})
    else:
        return HttpResponseRedirect('/')

@csrf_exempt
def telephony_queue_success_unit_doc(request, id, pk):
    if request.user.is_authenticated:
        if request.method == 'POST':
            body_unicode    = request.body.decode().replace("'", '"')
            data            = json.loads(body_unicode)
            if 'add_auto_replace_save' in data:
                new_dictonary = Telephony_Recognition_Dictonary()
                new_dictonary.date      = DT.datetime.now()
                new_dictonary.name_s    = data['text_s'] 
                new_dictonary.name_n    = data['text_n']
                new_dictonary.save()
                to = {
                    'answer': 'ok'
                }    
                return JsonResponse(to, status = status.HTTP_200_OK, safe=False)
            if 'add_model_window_save' in data: 
                new_dictonary_model             = Telephony_Recognition_Dictonary_Model()
                new_dictonary_model.date        = DT.datetime.now()
                new_dictonary_model.name        = data['text']
                new_dictonary_model.save()
                to = {
                    'answer': 'ok'
                }    
                return JsonResponse(to, status = status.HTTP_200_OK, safe=False)
            
        rlk                     = DocRLK.objects.get(pk = pk)
        data_list               = list()
        recognitions            = Telephony_records_queue.objects.filter(rlk = rlk) 
        audio_voice_call        = None       
        record_array            = list()
        survey                  = None

        surveys_count           = SurveysOP.objects.filter(rlk = rlk).count()
        if surveys_count > 0:
            survey = SurveysOP.objects.filter(rlk = rlk)[0]    
        entrys_id               = rlk_hystory_calls_day_create(rlk)
        records_data            = entrys_id.values('start', 'records')
        records_list            = list()
        for record_data in records_data:
            if len(record_data['records']) > 3:
                record      = record_data['records']
                record      = record.strip().replace('[','').replace(']', '')
                records     = record.split(';')
                for rec in records:
                    recognitions   = Telephony_records_queue.objects.filter(rlk = rlk).filter(record = rec)
                    if len(recognitions) == 1:
                        recognition     = recognitions[0] 
                        direction_call  = get_direction_call(recognition.record)
                        data_list       = get_text_recognition(recognition, data_list, direction_call, record_data['start'])
                        params_record_array = {
                            'record'    : rec,
                            'img1'      : recognition.img_chanel_1.url,
                            'img2'      : recognition.img_chanel_2.url,
                            'duration'  : recognition.duration,
                            'path'      : path_sounds_kg_external + rec + '.mp3'
                        }
                        record_array.append(params_record_array)
                        if audio_voice_call == None:
                            audio_voice_call = recognition  

                    params_record = {
                        'start'     : record_data['start'],
                        'record'    : rec,
                        'duration'  : time_human(Telephony_records_queue.objects.filter(rlk = rlk).filter(record = rec).values('duration')[0]['duration'])
                    }
                    records_list.append(params_record)
        
        survey_kg           = refresh_survey_rlk(rlk) 
        tematics_list       = list()
        qyestions_check     = 0
        qyestions           = list()
        
        if survey != None:
            data_list           = survey_kg['data_list']
            tematics_list       = survey_kg['tematics_list']
            qyestions_check     = survey_kg['qyestions_check']
            qyestions           = survey_kg['qyestions']


        params = {
            'type'                      : 'telephony_recognitions',
            'survey'                    : survey,
            'path_sounds_kg_external'   : path_sounds_kg_external,
            'rlk'                       : rlk,
            'data_list'                 : data_list,
            'recognitions'              : recognitions,
            'entrys_id'                 : entrys_id,
            'audio_voice_call'          : audio_voice_call,
            'records_list'              : records_list,
            'tematics_list'             : tematics_list,
            'qyestions_check'           : qyestions_check,
            'qyestions'                 : qyestions,
            'record_array'              : "'" + json.dumps(record_array) + "'"
        }
        return render(request, 'telephony/telephony_queue_success_unit_doc.html', {'params': params})
    else:
        return HttpResponseRedirect('/')


def telephony_queue_view(request, id):
    if request.user.is_authenticated:
        
        object_list     = Telephony_records_queue.objects.filter(direction = 1).filter(data_json = '').values('rlk', 'rlk__nomer', 'rlk__dataTime', 'rlk__unit__name', 'rlk__staff__name').distinct()
        object_list     = object_list.order_by('-rlk__dataTime')
        
        page_number = request.GET.get('page')
        
        params = {
            'type'                      : 'telephony_recognitions',
        }
        return render(request, 'telephony/telephony_queue_view.html', {'params': params})
    else:
        return HttpResponseRedirect('/')
    

def telephony_tematiks(request):
    if request.user.is_authenticated:
        
        tematics_list = Telephony_Recognition_Tematika.objects.all().order_by('name')
        
        name    = ''
        status  = 0

        if 'name' in request.GET:
            name            = request.GET.get('name')
            tematics_list   = tematics_list.filter(name__icontains = name)

        if 'status' in request.GET:
            status = request.GET.get('status')
            if len(status) > 0:
                if status == '1':
                    tematics_list = tematics_list.filter(enabled = True)
                elif status == '2':
                    tematics_list = tematics_list.filter(enabled = False)
        
        tematics_count_enabled      = tematics_list.filter(enabled = True).count()
        tematics_count_not_enabled  = tematics_list.filter(enabled = False).count()

        filtr = {
            'name'      : name,
            'status'    : status
        }
        params = {
            'type'                          : 'telephony_recognitions',
            'paginator'                     : tematics_list,
            'tematics_count_enabled'        : tematics_count_enabled,
            'tematics_count_not_enabled'    : tematics_count_not_enabled,
            'filtr'                         : filtr
        }
        return render(request, 'telephony/telephony_tematiks.html', {'params': params})
    else:
        return HttpResponseRedirect('/')
 

def telephony_tematiks_edit(request, id):
    params = {
        'request':request
    }
    if request.user.is_authenticated:
        
        new             = False
        tematika        = ''
        select_count    = 25
        
        if id == '0':
            new = True
        else:
            tematika = Telephony_Recognition_Tematika.objects.get(pk = id)
        
        if request.method == 'POST':
           
            if 'save_button' in request.POST:
                if new:
                    tematika    = Telephony_Recognition_Tematika()
                tematika.name           = request.POST['name']
                tematika.field          = request.POST['field'][:200]
                rating                  = request.POST['rating']
                if len(rating) > 0:
                    tematika.rating = int(rating)
                direction      = request.POST['direction']
                if len(direction) > 0:
                    tematika.direction = int(direction)
                tematika.enabled        = 'status' in request.POST 
                tematika.save()
                
            if 'save_fraza' in request.POST:
                if new:
                    tematika    = Telephony_Recognition_Tematika()
                tematika.name       = request.POST['name']
                tematika.field      = request.POST['field'][:200]
                rating = request.POST['rating']
                if len(rating) > 0:
                    tematika.rating = int(rating)
                direction      = request.POST['direction']
                if len(direction) > 0:
                    tematika.direction = int(direction)
                tematika.enabled = 'status' in request.POST 
                tematika.save()
                
                fraza_name      = request.POST['fraza']
                fraza_rating    = request.POST['fraza_rating']
                fraza_enabled   = 'fraza_enabled' in request.POST 

                fraza = Telephony_Recognition_Tematika_fraza()
                fraza.name      = fraza_name
                fraza.works     = fraza_enabled
                fraza.tematika  = tematika
                fraza.doorstep  = fraza_rating
                fraza.save()
           
            return HttpResponseRedirect(request.build_absolute_uri())
        
        page_obj = list()
        if not new:
            if 'select_count' in request.GET:
                select_count = int(request.GET.get('select_count'))

            fraza_list  = Telephony_Recognition_Tematika_fraza.objects.filter(tematika = tematika).order_by('name')
            page_number = request.GET.get('page')
            paginator   = Paginator(fraza_list, select_count)
            page_obj    = paginator.get_page(page_number)

        params = {
            'type'              : 'telephony_recognitions',
            'new'               : new,
            'tematika'          : tematika,
            'paginator'         : page_obj,
            'select_count'      : select_count   
        }
        return render(request, 'telephony/telephony_tematiks_edit.html', {'params':params})
    else:
        return render(request, 'website/start.html', {'params': params})

def telephony_tematiks_edit_delete_fraza(request, id, pk):
    Telephony_Recognition_Tematika_fraza.objects.get(pk = pk).delete()
    return HttpResponseRedirect('/telephony/recognitions/tematiks/' + str(id) + '/')

def telephony_questions(request):
    if request.user.is_authenticated:
        
        telephony_question = Telephony_question.objects.all().order_by('name')
        
        name    = ''
        status  = 0

        if 'name' in request.GET:
            name                    = request.GET.get('name')
            telephony_question      = telephony_question.filter(name__icontains = name)

        if 'status' in request.GET:
            status = request.GET.get('status')
            if len(status) > 0:
                if status == '1':
                    telephony_question = telephony_question.filter(estimation__gt = 0)
                elif status == '2':
                    telephony_question = telephony_question.filter(estimation = 0)
        
        telephony_question_count_enabled      = telephony_question.filter(estimation__gt = 0).count()
        telephony_question_count_not_enabled  = telephony_question.filter(estimation = 0).count()

        filtr = {
            'name'      : name,
            'status'    : status
        }
        params = {
            'type'                                      : 'telephony_recognitions',
            'paginator'                                 : telephony_question,
            'telephony_question_count_enabled'          : telephony_question_count_enabled,
            'telephony_question_count_not_enabled'      : telephony_question_count_not_enabled,
            'filtr'                                     : filtr
        }
        return render(request, 'telephony/telephony_questions.html', {'params': params})
    else:
        return HttpResponseRedirect('/')
 

def telephony_questions_edit(request, id):
    params = {
        'request':request
    }
    if request.user.is_authenticated:
        
        new             = False
        object          = ''
        select_count    = 25
        
        if id == '0':
            new = True
        else:
            object = Telephony_question.objects.get(pk = id)
        
        if request.method == 'POST':
            
            if 'save_button' in request.POST:
                if new:
                    object    = Telephony_question()
                object.name             = request.POST['name']
                estimation              = request.POST['estimation']
                if len(estimation) > 0:
                    object.estimation = int(estimation)
                object.direction      = 1
                object.save()
            
                object.tematics.clear()

                for key in request.POST.keys():
                    if key.startswith('tematic_'):
                        pk_tematic  = str(key).replace('tematic_', '')
                        tematics    = Telephony_Recognition_Tematika.objects.get(pk = pk_tematic)
                        object.tematics.add(tematics)
                object.save() 

            '''
            if 'save_fraza' in request.POST:
                if new:
                    tematika    = Telephony_Recognition_Tematika()
                tematika.name       = request.POST['name']
                tematika.field      = request.POST['field'][:200]
                rating = request.POST['rating']
                if len(rating) > 0:
                    tematika.rating = int(rating)
                direction      = request.POST['direction']
                if len(direction) > 0:
                    tematika.direction = int(direction)
                tematika.enabled = 'status' in request.POST 
                tematika.save()
                
                fraza_name      = request.POST['fraza']
                fraza_rating    = request.POST['fraza_rating']
                fraza_enabled   = 'fraza_enabled' in request.POST 

                fraza = Telephony_Recognition_Tematika_fraza()
                fraza.name      = fraza_name
                fraza.works     = fraza_enabled
                fraza.tematika  = tematika
                fraza.doorstep  = fraza_rating
                fraza.save()
            '''
            return HttpResponseRedirect(request.build_absolute_uri())
        
        tematics = Telephony_Recognition_Tematika.objects.filter(direction = 1)
        if new == True:
            tematics = Telephony_Recognition_Tematika.objects.filter(direction = 1)
        count_enabled = 0

        if object != '':
            subquery_queue      = Subquery(object.tematics.all().filter(id = OuterRef(name='id')).values('rating')[:1]) 
            tematics            = tematics.annotate(test = subquery_queue)        
            count_enabled       = object.tematics.all().count()
        
        params = {
            'type'              : 'telephony_recognitions',
            'new'               : new,
            'tematics'          : tematics,
            'object'            : object,
            'count_enabled'     : count_enabled, 
            'count_off'         : tematics.count() - count_enabled,
            'select_count'      : select_count   
        }
        return render(request, 'telephony/telephony_questions_edit.html', {'params':params})
    else:
        return render(request, 'website/start.html', {'params': params})


def dictonarys(request):  
    params = {
        'request':request
    }
    if request.user.is_authenticated:
        
        param_url       = urllib.parse.urlencode(request.GET)
        select_count    = 25
        
        if 'delite' in request.GET:
            pk_delite = int(request.GET.get('delite', 0))
            if pk_delite > 0:
                count = Telephony_Recognition_Dictonary.objects.filter(pk = pk_delite).count()
                if count > 0:
                    Telephony_Recognition_Dictonary.objects.get(pk = pk_delite).delete()
                querydict = request.GET.copy()
                if 'delite' in querydict:
                    del querydict['delite']
                url         = request.build_absolute_uri(request.path)
                param_url   = urllib.parse.urlencode(querydict)
                if len(param_url) > 0:
                    url = url + "?" + param_url
                return HttpResponseRedirect(url)
        
        dictonarys      = Telephony_Recognition_Dictonary.objects.all().order_by('id')
        
        name = ''
        if 'name' in request.GET:
            name            = request.GET.get('name')
            dictonarys   = dictonarys.filter(name_s__icontains = name) | dictonarys.filter(name_n__icontains = name)

        page_number     = request.GET.get('page')
        paginator       = Paginator(dictonarys, select_count)
        page_obj        = paginator.get_page(page_number)

        filtr = {
            'name': name
        }
        params = {
            'type'              : 'telephony_recognitions',
            'filtr'             : filtr,
            'paginator'         : page_obj,
            'select_count'      : select_count,
            'param_url'         : param_url   
        }
        return render(request, 'telephony/telephony_dictonarys.html', {'params':params})
    else:
        return render(request, 'website/start.html', {'params': params})


def dictonary_edit(request, id):
    params = {
        'request':request
    }
    if request.user.is_authenticated:
        
        new             = False
        dictonary       = ''
        select_count    = 25
        
        if id == '0':
            new = True
        else:
            dictonary = Telephony_Recognition_Dictonary.objects.get(pk = id)
        
        if request.method == 'POST':
           
            if 'save_button' in request.POST:
                if new:
                    dictonary    = Telephony_Recognition_Dictonary()
                dictonary.name_s             = request.POST['name_s']
                dictonary.name_n             = request.POST['name_n'][:200]
                dictonary.date               = DT.datetime.now() 
                dictonary.save()
            if new:
                return HttpResponseRedirect('/telephony/recognitions/dictonarys/' + str(dictonary.id) + '/')
            else:
                return HttpResponseRedirect(request.build_absolute_uri())
        
        params = {
            'type'              : 'telephony_recognitions',
            'new'               : new,
            'dictonary'         : dictonary  
        }
        return render(request, 'telephony/telephony_dictonary_edit.html', {'params':params})
    else:
        return render(request, 'website/start.html', {'params': params})


def refresh_survey_rlk(rlk):
    #Проверим все ли записи из очереди расспознаны
    count_queue_rlk_fail = Telephony_records_queue.objects.filter(rlk = rlk).filter(data_json = '').count()
    if count_queue_rlk_fail == 0:
        recognitions_data_text  = list()
        data_list               = list()
        tematics_list           = list()
        entrys_id               = rlk_hystory_calls_day_create(rlk)
        records_data            = entrys_id.values('start', 'records')
        records_list            = list()
        for record_data in records_data:
            if len(record_data['records']) > 3:
                record      = record_data['records']
                record      = record.strip().replace('[','').replace(']', '')
                records     = record.split(';')
                for rec in records:
                    recognitions   = Telephony_records_queue.objects.filter(rlk = rlk).filter(record = rec)
                    if len(recognitions) == 1:
                        recognition     = recognitions[0] 
                        direction_call  = get_direction_call(recognition.record)
                        data_list       = get_text_recognition(recognition, data_list, direction_call, record_data['start'])
        
        data_tematics       = dict()
        qyestions           = list()
        qyestions_check     = 0
        if len(data_list) > 0:
            #Автозаменаслов и фраз из словаря
            ref_replace = Telephony_Recognition_Dictonary.objects.all()
            for data in data_list:
                text = data['text']
                for replace in ref_replace:
                    text = text.replace(replace.name_s, replace.name_n)
                data['text'] = text
            ref_questions = Telephony_question.objects.filter(direction = 1).filter(estimation__gt = 0)
            for question in ref_questions: 
                ref_tematics = Telephony_Recognition_Tematika_fraza.objects.filter(tematika__direction = 1).filter(tematika__enabled = True).filter(tematika__in = question.tematics.all())
                #ref_tematics = question.tematics.all()
                for tematics in ref_tematics:
                    tematics_text = tematics.name
                    for data in data_list:
                        text = data['text']
                        resulttoken_sort_ratio = fuzz.token_set_ratio(text, tematics_text)
                        if resulttoken_sort_ratio > 70:
                            if not question in qyestions:
                                qyestions.append(question)
                                qyestions_check = qyestions_check + question.estimation
                            par = {
                                'tematics'                  : tematics.tematika.name,
                                'tematics_id'               : tematics.tematika.id,
                                'resulttoken_sort_ratio'    : resulttoken_sort_ratio,
                                'tematics_text'             : tematics_text,
                                'sec'                       : data['sec'],
                                'sec_human'                 : time_human(data['sec']),
                                'record'                    : data['recognition']   
                            }
                            tematics_list.append(par)
                            if str(tematics.tematika) in data_tematics:
                                data_tematics[str(tematics.tematika)].append(par)
                            else:
                                data_tematics[str(tematics.tematika)] = list()
                                data_tematics[str(tematics.tematika)].append(par)
            
        tema = list()
        
        for dat in data_tematics:
            par = {
                'name' : dat,
                'data' : data_tematics[dat]
            }
            tema.append(par)
        data_return = {
            'data_list'         : data_list,
            'tematics_list'     : tema,
            'qyestions_check'   : qyestions_check,
            'qyestions'         : qyestions
        }
        return data_return

    else: 
        return None
                        
###
##
# function

def refresh_history(request):
    refresh_records_download()
    return HttpResponseRedirect('/')


def refresh_history_task():
    refresh_mango_group()
    refresh_mango_number()
    refresh_mango_hystory_calls()
    refresh_quequ()
    refresh_records_download()
    

def refresh_mango_hystory_calls():
    
    path                = 'stats/request/'
    hystory_date_end    = MangoHystoryCalls.objects.all().count() 
    
    if hystory_date_end == 0:
        hystory_date_end = datetime.datetime(year=2021, month=11, day=1)
    else:
        hystory_calls       = MangoHystoryCalls.objects.all().order_by('-start')[0]
        hystory_date_end    = hystory_calls.start
    
    hystory_date_start  = hystory_date_end
    curent_time         = datetime.datetime.now() 
    hystory_date_end    = hystory_date_end + datetime.timedelta(days=5)

    hystory_date_end = min(hystory_date_end, curent_time)

    date_start  = int((hystory_date_start + datetime.timedelta(hours=-1)).timestamp())
    date_end    = int((hystory_date_end).timestamp())  
    
    params  = {
        'date_from' : date_start,
        'date_to'   : date_end,
        'fields'    : 'records,start,finish,answer,from_extension,from_number,to_extension,to_number,disconnect_reason,line_number,location,entry_id'
    }
    
    answer = send_mango(path, json.dumps(params))
    
    if len(answer) > 0:
        time.sleep(15)
        data    = json.loads(answer)
        key     = data['key']
        get_result_hystory_calls(key)
    

def get_result_hystory_calls(key):
    
    path = 'stats/result/'
    params  = {
        'key' : key
    }
    
    answer          = ''
    count_request   = 0

    while count_request < 10:
        time.sleep(10)
        answer = send_mango(path, json.dumps(params))
        if len(answer) == 0:
            count_request = count_request + 1
        else:
            count_request = 777
        
    if len(answer) > 0:
        data = answer.split('\r\n')
        for data_infos in data:
            if len(data_infos) > 0:
                
                infos_call = data_infos.split(';')
                entry_id    = infos_call[11]
                start       = datetime.datetime.utcfromtimestamp(int(infos_call[1]) + 10800)
                finish      = datetime.datetime.utcfromtimestamp(int(infos_call[2]) + 10800)
                times       = (datetime.datetime.utcfromtimestamp(int(infos_call[2])) - datetime.datetime.utcfromtimestamp(int(infos_call[1]))).seconds
                records     = infos_call[0]
                from_number = infos_call[5]
                to_number   = infos_call[7]
                
                count_hystory_calls = MangoHystoryCalls.objects.filter(start = start).filter(finish = finish).filter(entry_id = entry_id).filter(from_number = from_number).filter(to_number = to_number).count()
                
                if count_hystory_calls == 0:
                    hystory_call                = MangoHystoryCalls()
                    hystory_call.entry_id       = entry_id
                    hystory_call.from_number    = from_number
                    hystory_call.to_number      = to_number
                    hystory_call.start          = start
                    hystory_call.finish         = finish
                    hystory_call.records        = records
                    hystory_call.time           = times
                    if int(infos_call[3]) > 0:
                        hystory_call.answer = True
                    hystory_call.duration       = convert_to_preferred_format(times)
                    if from_number.find('sip') > -1 and to_number.find('sip') > -1: 
                        hystory_call.direction      = MangoHystoryCalls.DirectionCall.INTERNAL
                    elif from_number.find('sip') > -1:
                        hystory_call.direction      = MangoHystoryCalls.DirectionCall.OUTBOUND
                    else:
                        hystory_call.direction      = MangoHystoryCalls.DirectionCall.INBOUND
                    hystory_call.save()


def refresh_mango_number():
    path    = 'config/users/request'
    list_selection = list()
    list_selection.append('groups')
    params  = {
        'ext_fields' : list_selection
    }
    answer = send_mango(path, json.dumps(params))
    if len(answer) > 0:
        data    = json.loads(answer)
        users   = data['users']
        for user in users:
            general = user['general']
            name    = general['name']

            telephony   = user['telephony']
            numbers     = telephony['numbers']

            groups      = user['groups'] 
            list_groups = list()
            for group in groups:
                count = MangoGroup.objects.filter(mango_id = group).count()
                if count == 1:
                    group_object = MangoGroup.objects.filter(mango_id = group)[0]
                    list_groups.append(group_object)
            for number_mango in numbers:
                number_str      = number_mango['number']
                number_count    = MangoNumberSip.objects.filter(name = number_str).count()
                if number_count == 1:
                    number_object = MangoNumberSip.objects.filter(name = number_str)[0]
                else:
                    number_object = MangoNumberSip()
                number_object.name          = number_str
                number_object.description   = name
                number_object.sip           = number_str
                number_object.save()

                MangoNumberSipGroup.objects.filter(number = number_object).delete()

                for list_group in list_groups:
                    mangoNumberSipGroup = MangoNumberSipGroup()
                    mangoNumberSipGroup.group   = list_group
                    mangoNumberSipGroup.number  = number_object
                    mangoNumberSipGroup.save()
                

def refresh_mango_group():
    path    = 'groups'
    params  = '""'

    answer = send_mango(path, params)

    if len(answer) > 0:
        data = json.loads(answer)
        if data['result'] == 1000:
            for group in data['groups']:
                name        = group['name']
                mango_id    = group['id']
                count_group = MangoGroup.objects.filter(mango_id = mango_id).count()
                if count_group == 0:
                    mango_group = MangoGroup()
                    mango_group.mango_id    = mango_id
                    mango_group.name        = name
                    mango_group.save()
                else:
                    mango_group = MangoGroup.objects.filter(mango_id = mango_id)[0]
                    mango_group.name = name
                    mango_group.save()


def refresh_records_download():
    records = Telephony_records_queue.objects.filter(data_json = '').filter(record = 'MToxMDE3MTA1MToyMzgwNzgyNjkyMzow')
    for record in records:
        name_file   = path_sounds_kg + record.record + '.mp3' 
        if not os.path.exists(name_file) or os.path.getsize(name_file) == 0:
            download_record(record.record)


def refresh_quequ():
    date_end    = datetime.datetime.now() 
    date_start  = date_end + datetime.timedelta(days=-7)
    docs_rlk    = DocRLK.objects.filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(contacType__id = 5)
    
    for doc_rlk in docs_rlk:
        phone_number    = doc_rlk.phone.strip()
        records_list    = list()
        if len(phone_number) > 0:
            
            date_start_rlk  = doc_rlk.dataTime.replace(hour=0) 
            date_end_rlk    = doc_rlk.dataTime.replace(hour=23) 

            phone_number = phone_number.replace(';', '')
            if len(phone_number) == 11:
                phone_number = phone_number[1:10]
            entrys_id = MangoHystoryCalls.objects.filter(from_number__icontains = phone_number).filter(start__gte = date_start_rlk).filter(start__lte = date_end_rlk) | MangoHystoryCalls.objects.filter(to_number__icontains = phone_number).filter(start__gte = date_start_rlk).filter(start__lte = date_end_rlk)
            entrys_id = entrys_id.values('entry_id').distinct()
            for entry in entrys_id:
                records = MangoHystoryCallsRecords.objects.filter(entry_id = entry['entry_id'])
                for rec in records:
                    records_list.append(rec.record)
            
            if len(records_list) > 0:
                for record in records_list:
                    count_queue_record = Telephony_records_queue.objects.filter(record = record).count()
                    if count_queue_record == 0:
                        trq             = Telephony_records_queue()
                        trq.date        = DT.datetime.now()
                        trq.rlk         = doc_rlk
                        trq.direction   = 1
                        trq.record      = record
                        trq.save()


def download_record(record):
    path    = 'queries/recording/post'
    params  = {
        'recording_id'  : record,
        'action'        : 'download'
    }
    answer = send_mango(path, json.dumps(params))
    if len(answer) > 0:
        path_save = path_sounds_kg + record + '.mp3'
        urllib.request.urlretrieve(answer, path_save)
        s = 1


def send_mango(path, params):
    url = mango_url + path
    headers ={
        'Content-type'          : 'application/x-www-form-urlencoded',
        'Accept-Language'       : 'en',
        'Accept-Charset'        : 'utf-8',
	    'Content-Language'      : 'en',
	    'Content-Charset'       : 'utf-8',
	    }
    sign = hashlib.sha256((mango_api_key + str(params) + mango_api_salt).encode('utf-8')).hexdigest()
    
    params_send = str('vpbx_api_key=' + mango_api_key + '&sign=' + sign + '&json=' + params)
    
    #"vpbx_api_key="+КодироватьСтроку(ApiKey, СпособКодированияСтроки.КодировкаURL)+"&sign=" + КодироватьСтроку(Sign, СпособКодированияСтроки.КодировкаURL) + "&json=" + КодироватьСтроку(СтрокаJSON, СпособКодированияСтроки.КодировкаURL) + "";
    response = requests.post(url, data = params_send, headers = headers)
    if response.status_code == 200:
        if path == 'queries/recording/post':
            return response.url
        else:
            return response.text
    return ''

###
##
# Служебные функции
def get_direction_call(record):
    return MangoHystoryCalls.objects.filter(records__icontains = record)[0].direction

def get_text_recognition(recognition, data_list, direction_call, start_time):
    if recognition.data_json != '':
            data_json       = json.loads(recognition.data_json.replace("'",'"').replace('True', '"True"').replace('False', '"False"'))
            path            = data_json['info_audio']['path']
            data_text       = data_json['data']
            for param_fraza in data_text:
                time        = param_fraza['time_start']
                date_time   = DT.timedelta(seconds=int(time))
                date        = start_time + date_time
                talking = "Клиент"
                if (direction_call == 'INBOUND' and param_fraza['chanel'] == 0) or (direction_call == 'INTERNAL' and param_fraza['chanel'] == 0):
                    talking = "Сотрудник"
                data_list.append({'recognition': recognition.record, 'talking': talking, 'direction_call': direction_call, 'chanel': param_fraza['chanel'], 'time': convert_to_preferred_format(time), 'date': date, 'sec': int(time), 'text': param_fraza['text']})
    return data_list 

def rlk_hystory_calls_day_create(rlk):
    phone_number    = rlk.phone.strip()
    phone_number    = phone_number.replace(';', '')
    if len(phone_number) == 11:
        phone_number = phone_number[1:10]
    date_start_rlk  = rlk.dataTime.replace(hour=0) 
    date_end_rlk    = rlk.dataTime.replace(hour=23) 
    entrys_id       = MangoHystoryCalls.objects.filter(from_number__icontains = phone_number).filter(start__gte = date_start_rlk).filter(start__lte = date_end_rlk) | MangoHystoryCalls.objects.filter(to_number__icontains = phone_number).filter(start__gte = date_start_rlk).filter(start__lte = date_end_rlk)
    entrys_id       = entrys_id.order_by('start')
    return entrys_id   

def time_human(time_seconds):
    if time_seconds != None:
        sec = time_seconds
        if sec > 0:
            sec     = sec % (24 * 3600) 
            hour    = time_seconds // 3600 
            sec     %= 3600 
            min     = sec // 60 
            sec     %= 60 
            if hour > 0:
                return "%02d:%02d:%02d" % (hour, min, sec)
            else:
                return "%02d:%02d" % (min, sec)
        else:
            return "00:00"
    else:
            return "00:00"
    
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