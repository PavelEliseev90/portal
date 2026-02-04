from django.shortcuts import render
from django.core.paginator import Paginator
import json
from recognition.models import Records_voice_recorder_cvc, Records_voice_recorder_cvc_checklist_kg, Records_voice_recorder_cvc_checklist_tematics, Records_voice_recorder_cvc_checklist, Records_voice_recorder_cvc_tematics, Recognition_Anketa, Records_voice_recorder, Recognition_Tematika_fraza, Recognition_Tematika, Records_voice_recorder_queue, Records_voice_recorder_cvc_tematics_fields, Records_questions, Check_settings, Settings_check_records, Check_settings_cvc
from fuzzywuzzy import fuzz
from django.http import Http404, HttpResponseRedirect, HttpResponseNotFound, HttpResponse
from django.db.models import Count, Sum, Max, Avg, F, OuterRef, Subquery, Q, Case, When, IntegerField
from documents.models import DocRLKEvents, DocZN, DocRLK
from django.db import models
from refs.models import RefCity, RefUnit
import datetime as DT
from checklists.models import CheckList, CheckListServiceIn, CheckListServiceOut, CheckListTradeIn, CheckList_op_kors
from task_manager.views import cvc_get_info, cvc_get_record_info_no_send
from django.contrib.auth.models import User
from openpyxl import Workbook
from django.db.models.functions import Coalesce



def refresh_cvc_cheklist():
    id      = check_list.rlk.id
    rlk     = DocRLK.objects.get(pk = id)
    info    = get_check_cvc(token, id)
    if len(info) > 3:
        company = False
        Records_voice_recorder_cvc_checklist_tematics.objects.filter(checklist = check_list).delete()
        js                              = json.loads(info)
        checklists_cvc_info = js['checklists']
        
        refresh_check_list_info(checklists_cvc_info) 

        id_check_cvc = 0
        if check_list.сheck_settings != None:
            if check_list.сheck_settings.check_settings_cvc != None:
                id_check_cvc = check_list.сheck_settings.check_settings_cvc.id_cvc
        
        cvc_checklists = None

        if id_check_cvc != 0:
            for checklist_cvc_info in checklists_cvc_info:
                if id_check_cvc == checklist_cvc_info['checklist_id']:
                    cvc_checklists = checklist_cvc_info    

        if cvc_checklists == None:
            if len(checklists_cvc_info) > 1:
                cvc_checklists                  = checklists_cvc_info[len(checklists_cvc_info)-1]
            else:
                cvc_checklists                  = checklists_cvc_info[0]
        
        worked_dictionaries             = cvc_checklists['worked_dictionaries']
        dictionaries_that_dont_work     = cvc_checklists['dictionaries_that_dont_work']
        
        for dictonary in worked_dictionaries:
            id_dictonary_cvc    = dictonary['dictionary_id']
            name                = dictonary['name']
            value               = dictonary['positive_weight']
            dictonary_cvc       = get_dictonary_cvc(id_dictonary_cvc, name)
            if dictonary_cvc.company == True:
                company = True    
            tematics            = Records_voice_recorder_cvc_checklist_tematics()
            tematics.checklist  = check_list
            tematics.tematic    = dictonary_cvc
            tematics.value      = value
            tematics.confirmed  = True
            tematics.save()
        
        for dictonary in dictionaries_that_dont_work:
            id_dictonary_cvc    = dictonary['dictionary_id']
            name                = dictonary['name']
            dictonary_cvc       = get_dictonary_cvc(id_dictonary_cvc, name)
            tematics            = Records_voice_recorder_cvc_checklist_tematics()
            tematics.checklist  = check_list
            tematics.tematic    = dictonary_cvc
            tematics.value      = 0
            tematics.confirmed  = False
            tematics.save()
        
        if len(worked_dictionaries) > 0: 
            check_list.success = True
        
        check_list.company = company
        check_list.save()

        Records_voice_recorder_cvc_checklist_kg.objects.filter(checklist_cvc = check_list).delete()
        confirmed_tematics  = Records_voice_recorder_cvc_checklist_tematics.objects.filter(confirmed = True).filter(checklist = check_list)
        direction = check_list.direction
        if direction == 0:
            direction = 1
        questions_records   = Records_questions.objects.filter(direction = direction).filter(сheck_settings = check_list.сheck_settings).order_by('chapter', '-priority_chapter')
        
        for questions in questions_records:
            if questions.event_sale:
                agreement = get_sale_to_day_rlk(check_list.rlk)
                if agreement:
                    checklist_kg = Records_voice_recorder_cvc_checklist_kg()
                    checklist_kg.checklist_cvc  = check_list
                    checklist_kg.questions_kg   = questions
                    checklist_kg.value          = questions.estimation
                    checklist_kg.save()
                    if questions.priority_chapter > 0:
                        Records_voice_recorder_cvc_checklist_kg.objects.filter(checklist_cvc = check_list).filter(questions_kg__chapter = questions.chapter).filter(questions_kg__priority_chapter__gt = questions.priority_chapter).delete()
                    continue
                
            for tematics_confirmed in confirmed_tematics:
                if questions.tematics.filter(pk = tematics_confirmed.tematic.pk).count() > 0:
                    if Records_voice_recorder_cvc_checklist_kg.objects.filter(checklist_cvc = check_list).filter(questions_kg = questions).count() == 0:
                        checklist_kg = Records_voice_recorder_cvc_checklist_kg()
                        checklist_kg.checklist_cvc  = check_list
                        checklist_kg.questions_kg   = questions
                        checklist_kg.value          = questions.estimation
                        checklist_kg.save()
                        if questions.priority_chapter > 0:
                            Records_voice_recorder_cvc_checklist_kg.objects.filter(checklist_cvc = check_list).filter(questions_kg__chapter = questions.chapter).filter(questions_kg__priority_chapter__gt = questions.priority_chapter).delete()
        check_list.save()


def cvc_get_info_cvc(request):
    cvc_get_info()    
    return render(request, "recognition/lk_recognition_start.html", {'params': 'params'})

def start(request):
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

        # Оптимизация: объединяем count запросы и используем select_related
        # Базовые queryset с оптимизацией
        cvc_checklist_qs = Records_voice_recorder_cvc_checklist.objects.select_related('rlk')
        cvc_queue_qs = Records_voice_recorder_cvc_checklist.objects.select_related('rlk')
        op_queue_qs = Records_voice_recorder_queue.objects.select_related('rlk')
        
        # Объединяем count запросы для CVC ОП
        cvc_op_stats = cvc_checklist_qs.filter(
            direction__lte=1,
            rlk__dataTime__gte=date_start,
            rlk__dataTime__lte=date_end
        ).aggregate(
            success_count=Count('id', filter=Q(success=True)),
            queue_count=Count('id', filter=Q(success=False))
        )
        
        # Объединяем duration запросы для CVC ОП
        cvc_op_queue_duration = cvc_queue_qs.filter(
            direction__lte=1,
            success=False
        ).aggregate(duration_sum=Sum('duration'))['duration_sum'] or 0
        
        # Объединяем count запросы для CVC КОРС
        cvc_kors_stats = cvc_checklist_qs.filter(
            direction=5,
            rlk__dataTime__gte=date_start,
            rlk__dataTime__lte=date_end
        ).aggregate(
            success_count=Count('id', filter=Q(success=True)),
            queue_count=Count('id', filter=Q(success=False))
        )
        
        # Объединяем duration запросы для CVC КОРС
        cvc_kors_queue_duration = cvc_queue_qs.filter(
            direction=5,
            success=False
        ).aggregate(duration_sum=Sum('duration'))['duration_sum'] or 0
        
        # Объединяем count запросы для ОП
        op_stats = op_queue_qs.filter(
            direction=1,
            error=False,
            rlk__dataTime__gte=date_start,
            rlk__dataTime__lte=date_end
        ).aggregate(
            check_count=Count('id', filter=~Q(data_json='')),
            queue_count=Count('id', filter=Q(data_json=''))
        )
        
        # Duration для ОП очереди
        op_queue_duration = op_queue_qs.filter(
            direction=1,
            error=False,
            data_json=''
        ).aggregate(duration_sum=Sum('duration'))['duration_sum'] or 0
        
        # Статические данные (не зависят от дат) - можно кешировать
        op_records_questions = Records_questions.objects.filter(direction=1).count()
        op_kors_records_questions = Records_questions.objects.filter(direction=5).count()
        cvc_op_tematiks = Records_voice_recorder_cvc_tematics.objects.filter(activated=True).count()
        op_tematiks = Recognition_Tematika.objects.filter(anketa__id=1, enabled=True).count()
        
        params = {
            'type'                          : 'recognitions',
            'filtr'                         : filtr,
            
            'op_records_questions'          : op_records_questions,
            'op_kors_records_questions'     : op_kors_records_questions,
            'check_settings_1'              : get_settings_checklist(1),
            'check_settings_5'              : get_settings_checklist(5),

            'cvc_op_success'                : cvc_op_stats['success_count'] or 0,
            'cvc_op_tematiks'               : cvc_op_tematiks,
            'cvc_op_queue'                  : cvc_op_stats['queue_count'] or 0,
            'cvc_op_queue_duration'         : time_human(cvc_op_queue_duration),
            
            'cvc_op_kors_success'           : cvc_kors_stats['success_count'] or 0,
            'cvc_op_kors_queue'             : cvc_kors_stats['queue_count'] or 0,
            'cvc_op_kors_queue_duration'    : time_human(cvc_kors_queue_duration),
            
            'op_chek_count'                 : op_stats['check_count'] or 0,
            'op_tematiks'                   : op_tematiks,
            'op_queue'                      : op_stats['queue_count'] or 0,
            'op_queue_duration'             : time_human(op_queue_duration)
            
        }
        return render(request, "recognition/lk_recognition_start.html", {'params': params})    
    else:
        return HttpResponseRedirect('/login')


def check_lists(request):
    if request.user.is_authenticated:
        
        if request.method == "GET":
            # Оптимизация: добавляем select_related для check_settings_cvc
            check_settings_list = Check_settings.objects.all().select_related('check_settings_cvc').order_by('name')
            
            name        = ''
            direction               = int(request.GET.get('direction', '1'))
            check_settings_list     = check_settings_list.filter(direction=direction)
            
            # Оптимизация: используем first() вместо [0] и select_related
            settings_check_records_obj = Settings_check_records.objects.filter(direction=direction).select_related('check_settings').first()
            settings_check_records  = ''
            if settings_check_records_obj:
                settings_check_records = settings_check_records_obj.check_settings.pk
            
            if 'name' in request.GET:
                name                   = request.GET.get('name')
                check_settings_list    = check_settings_list.filter(name__icontains=name)
            
            # Оптимизация: добавляем annotate для подсчета вопросов одним запросом
            from django.db.models import Count
            check_settings_list = check_settings_list.annotate(
                questions_count=Count('records_questions')
            )

            filtr = {
                'name'      : name,
                'direction' : direction,
                'settings_check_records'                    : settings_check_records
                
            }

            params = {
                'type'                                      : 'recognitions',
                'check_settings_list'                       : check_settings_list,
                'filtr'                                     : filtr
            }
            return render(request, 'recognition/check_lists.html', {'params': params})
        if request.method == 'POST':
            if 'save_check' in request.POST:
                direction               = int(request.POST.get('direction_id', '1'))
                
                # Оптимизация: используем get_or_create или first()
                settings_check_records = Settings_check_records.objects.filter(direction=direction).first()
                if not settings_check_records:
                    settings_check_records = Settings_check_records()
                settings_check_records.direction        = direction
                settings_check_records.check_settings   = Check_settings.objects.get(pk = request.POST.get('check_id', '1'))
                settings_check_records.save()
            return HttpResponseRedirect(request.build_absolute_uri())
    else:
        return HttpResponseRedirect('/')


def check_lists_edit(request, id):
    params = {
        'request':request
    }
    if request.user.is_authenticated:
        
        new             = False
        object          = ''
        select_count    = 25
        direction       = 0
        
        if id == '0':
            new                     = True
            direction               = int(request.GET.get('direction', '1'))
        else:
            object      = Check_settings.objects.get(pk = id)
            direction   = object.direction

        if request.method == 'POST':
            if 'refresh_check' in request.POST:
                list_checklist_cvc = Records_voice_recorder_cvc_checklist.objects.filter(success = True).filter(сheck_settings = object)
                for check_list in list_checklist_cvc:
                    Records_voice_recorder_cvc_checklist_kg.objects.filter(checklist_cvc = check_list).delete()
                    confirmed_tematics  = Records_voice_recorder_cvc_checklist_tematics.objects.filter(confirmed = True).filter(checklist = check_list)
                    direction = check_list.direction
                    if direction == 0:
                        direction = 1
                    questions_records   = Records_questions.objects.filter(direction = direction).filter(сheck_settings = check_list.сheck_settings).order_by('chapter', '-priority_chapter')
                    
                    for questions in questions_records:
                        if questions.event_sale:
                            agreement = get_sale_to_day_rlk(check_list.rlk)
                            if agreement:
                                checklist_kg = Records_voice_recorder_cvc_checklist_kg()
                                checklist_kg.checklist_cvc  = check_list
                                checklist_kg.questions_kg   = questions
                                checklist_kg.value          = questions.estimation
                                checklist_kg.save()
                                if questions.priority_chapter > 0:
                                    Records_voice_recorder_cvc_checklist_kg.objects.filter(checklist_cvc = check_list).filter(questions_kg__chapter = questions.chapter).filter(questions_kg__priority_chapter__gt = questions.priority_chapter).delete()
                                continue
                            
                        for tematics_confirmed in confirmed_tematics:
                            if questions.tematics.filter(pk = tematics_confirmed.tematic.pk).count() > 0:
                                if Records_voice_recorder_cvc_checklist_kg.objects.filter(checklist_cvc = check_list).filter(questions_kg = questions).count() == 0:
                                    checklist_kg = Records_voice_recorder_cvc_checklist_kg()
                                    checklist_kg.checklist_cvc  = check_list
                                    checklist_kg.questions_kg   = questions
                                    checklist_kg.value          = questions.estimation
                                    checklist_kg.save()
                                    if questions.priority_chapter > 0:
                                        Records_voice_recorder_cvc_checklist_kg.objects.filter(checklist_cvc = check_list).filter(questions_kg__chapter = questions.chapter).filter(questions_kg__priority_chapter__gt = questions.priority_chapter).delete()
                
            if 'save_button' in request.POST:
                if new:
                    object              = Check_settings()
                object.name             = request.POST['name']
                object.direction        = direction
                try:
                    object.check_settings_cvc = Check_settings_cvc.objects.get(pk = request.POST['check_settings_cvc'])
                except:
                    s = 1
                object.save()

            return HttpResponseRedirect(request.build_absolute_uri())
        
        if new == False:
            records_questions                       = Records_questions.objects.filter(сheck_settings = object).order_by('chapter','field')
            records_questions_count_enabled         = records_questions.filter(estimation__gt = 0).count()
            records_questions_count_not_enabled     = records_questions.filter(estimation = 0).count()
        else:
            records_questions                       = list()
            records_questions_count_enabled         = 0
            records_questions_count_not_enabled     = 0

        params = {
            'type'              : 'recognitions',
            'direction'         : direction,
            'new'               : new,
            'object'            : object,
            'checks_cvc'        : Check_settings_cvc.objects.all().order_by('name'),
            'paginator'                                 : records_questions,
            'records_questions_count_enabled'           : records_questions_count_enabled,
            'records_questions_count_not_enabled'       : records_questions_count_not_enabled,
            'select_count'      : select_count   
        }
        return render(request, 'recognition/check_lists_edit.html', {'params': params})
    else:
        return render(request, 'website/start.html', {'params': params})


def get_settings_checklist(direction):
    count_settings = Settings_check_records.objects.filter(direction = direction).count()
    if count_settings == 0:
        settings_check_records = None
    else:
        settings_check_records = Settings_check_records.objects.filter(direction = direction)[0]
    return settings_check_records


def get_sale_to_day_rlk(rlk):
    date_start  = rlk.dataTime.replace(hour = 0)
    date_end    = rlk.dataTime.replace(hour = 23)
    count = DocRLKEvents.objects.filter(rlk = rlk).filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(contacType__id = 17).count()    
    if count > 0:
        return True
    return False


def check_lists_edit_question(request, id, pk):
    params = {
        'request':request
    }
    if request.user.is_authenticated:
        
        new             = False
        object          = ''
        direction       = 0
        check_list      = Check_settings.objects.get(pk = id)
        
        if pk == '0':
            new                     = True
        else:
            object = Records_questions.objects.get(pk = pk)
        
        if request.method == 'POST':
            
            if 'save_button' in request.POST:
                if new:
                    object                  = Records_questions()
                    object.сheck_settings   = check_list
                    object.direction        = check_list.direction

                object.name             = request.POST['name']
                estimation              = request.POST['estimation']
                object.field            = request.POST['field'][:200]
                if len(estimation) > 0:
                    object.estimation = int(estimation)
                if len(object.field) > 0:
                    object.chapter          = int(object.field[:1])
                    object.chapter_name     = object.field[:1]
                object.priority_chapter     = request.POST.get('priority_chapter', 0)      
                object.direction            = check_list.direction
                event_sale                  = request.POST.get('event_sale', False)
                if event_sale == 'on':
                    object.event_sale = True
                else:
                    object.event_sale = False    
                
                event_trade_in   = request.POST.get('event_trade_in', False)
                if event_trade_in == 'on':
                    object.event_trade_in = True
                else:
                    object.event_trade_in = False 
                object.save()
            
                object.tematics.clear()

                for key in request.POST.keys():
                    if key.startswith('tematic_'):
                        pk_tematic  = str(key).replace('tematic_', '')
                        tematics    = Records_voice_recorder_cvc_tematics.objects.get(pk = pk_tematic)
                        object.tematics.add(tematics)
                object.save()
            return HttpResponseRedirect(request.build_absolute_uri())
        
        tematics = Records_voice_recorder_cvc_tematics.objects.all().order_by('name')
        if new == True:
            tematics = Records_voice_recorder_cvc_tematics.objects.all().order_by('name')
        count_enabled = 0

        if object != '':
            subquery_queue      = Subquery(object.tematics.all().filter(id = OuterRef(name='id')).values('id')[:1]) 
            tematics            = tematics.annotate(test = subquery_queue).order_by('name')        
            count_enabled       = object.tematics.all().count()
        
        params = {
            'type'              : 'recognitions',
            'direction'         : direction,
            'check_list'        : check_list,
            'new'               : new,
            'fields'            : get_fields(direction),
            'tematics'          : tematics,
            'object'            : object,
            'count_enabled'     : count_enabled, 
            'count_off'         : tematics.count() - count_enabled  
        }
        return render(request, 'recognition/check_list_questions_edit.html', {'params': params})
    else:
        return render(request, 'website/start.html', {'params': params})


def op(request):
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

        # Оптимизация: используем annotate для группировки вместо циклов с запросами
        # Один запрос вместо N+1 запросов
        base_qs = Records_voice_recorder_queue.objects.filter(
            direction=1,
            error=False
        ).exclude(
            data_json=''
        ).filter(
            rlk__dataTime__gte=date_start,
            rlk__dataTime__lte=date_end
        ).select_related('rlk', 'rlk__unit', 'rlk__unit__city')
        
        # Группируем по городам и подразделениям с агрегацией
        city_unit_stats = base_qs.values(
            'rlk__unit__city',
            'rlk__unit__city__name',
            'rlk__unit',
            'rlk__unit__name'
        ).annotate(
            count=Count('id'),
            duration_sum=Sum('duration')
        ).order_by('rlk__unit__city__name', 'rlk__unit__name')
        
        # Группируем данные по городам
        data_dict = {}
        for item in city_unit_stats:
            city_id = item['rlk__unit__city']
            city_name = item['rlk__unit__city__name'] or 'Не указан'
            
            if city_id not in data_dict:
                data_dict[city_id] = {
                    'city__id': city_id,
                    'city__name': city_name,
                    'units': [],
                    'count_city': 0,
                    'duration_city': 0
                }
            
            duration_sum = item['duration_sum'] or 0
            data_dict[city_id]['units'].append({
                'unit__id': item['rlk__unit'],
                'unit__name': item['rlk__unit__name'] or 'Не указано',
                'count': item['count'],
                'duration': time_human(duration_sum)
            })
            
            data_dict[city_id]['count_city'] += item['count']
            data_dict[city_id]['duration_city'] += duration_sum
        
        # Преобразуем в список и форматируем duration_city
        data_list = []
        for city_data in data_dict.values():
            city_data['duration_city'] = time_human(city_data['duration_city'])
            data_list.append(city_data)

        params = {
            'type'              : 'recognitions',
            'filtr'             : filtr,
            'data'              : data_list
        }
        return render(request, "recognition/recognition_success.html", {'params': params})    
    else:
        return HttpResponseRedirect('/login')


def op_detail(request, id):
    
    params = {
        'request':request
    }
    if request.user.is_authenticated:
        
        
        select_count = 25
        object_list     = Records_voice_recorder_queue.objects.filter(direction = 1).filter(error = False).filter(rlk__unit__id = id).exclude(data_json = '')
        filtr_count     = 0
        date_start      = ''
        date_end        = ''

        if 'select_count' in request.GET:
            select_count = int(request.GET.get('select_count'))

        if 'date_start' in request.GET:
            date_start = request.GET['date_start']
            if len(date_start) > 0:
                date_start = DT.datetime.strptime(request.GET['date_start'], "%Y-%m-%d")
                object_list = object_list.filter(rlk__dataTime__gte = date_start)
                filtr_count = filtr_count + 1

        if 'date_end' in request.GET:
            date_end = request.GET['date_end']
            if len(date_end) > 0:
                date_end = DT.datetime.strptime(request.GET['date_end'], "%Y-%m-%d")
                object_list = object_list.filter(rlk__dataTime__lte = date_end)
                filtr_count = filtr_count + 1
        
        name    = ''
        status  = 0

        page_number = request.GET.get('page')
        
        object_list = object_list.order_by('-rlk__dataTime') 

        paginator   = Paginator(object_list, select_count)
        page_obj    = paginator.get_page(page_number)
        
        filtr = {
            'name'          : name,
            'status'        : status,
            'date_start'    : date_start,
            'date_end'      : date_end,
            'filtr_count'   : filtr_count

        }
        params = {
            'type'              : 'recognitions',
            'page_number'       : page_number,
            'paginator'         : page_obj,
            'filtr'             : filtr,
            'select_count'      : select_count     
        }
        return render(request, 'recognition/recognition_success_detail.html', {'params':params})
    else:
        return render(request, 'website/start.html', {'params': params})


def op_detail_recognition(request, id, pk):
    params = {
        'request':request
    }
    result_list = list()
    text_search = request.GET.get('text')

    if request.user.is_authenticated:
        
        WRatio          = list()
        partial_ratio   = list()
        token_set_ratio = list()
        token_sort_ratio = list()
        recognition      = Records_voice_recorder_queue.objects.get(pk = pk)
        data_list       = list()

        if recognition.data_json != '':
            data_json       = json.loads(recognition.data_json.replace("'",'"').replace('True', '"True"').replace('False', '"False"'))
            path            = data_json['info_audio']['path']
            data_text       = data_json['data']
            for param_fraza in data_text:
                time = param_fraza['time_start']
                data_list.append({'time': convert_to_preferred_format(time), 'sec': int(time), 'text': param_fraza['text']})
                '''
                if inf['start'] - prev > 3:
                    if inf['start'] - prev > 3:
                        data_list.append({'time':convert_to_preferred_format(prev - 2), 'sec': int(prev - 2 ), 'text': ''})  
                    data_list.append({'time':convert_to_preferred_format(prev), 'sec': int(prev), 'text': text})
                    
                    resultpartial_ratio = fuzz.partial_ratio(text_search, text)
                    if resultpartial_ratio > 70 and len(text) > 3:
                        partial_ratio.append('-' + str(resultpartial_ratio) + ' - ' + text + "<br>")

                    resultWRatio = fuzz.WRatio(text_search, text)
                    if resultWRatio > 70 and len(text) > 3:
                        WRatio.append('-' + str(resultWRatio) + ' - ' + text + "<br>") 

                    resulttoken_set_ratio = fuzz.token_set_ratio(text_search, text)
                    if resulttoken_set_ratio > 70 and len(text) > 3:
                        token_set_ratio.append('-' + str(resulttoken_set_ratio) + ' - ' + text + "<br>")

                    resulttoken_sort_ratio = fuzz.token_sort_ratio(text_search, text)
                    if resulttoken_sort_ratio > 70 and len(text) > 3:
                        token_sort_ratio.append('-' + str(resulttoken_set_ratio) + ' - ' + text + "<br>")

                    text = inf['data']['word']
                    prev = inf['start']
                else:
                    text = text + ' ' + inf['data']['word']
                    prev = inf['start']
                '''
        else:
            data_json       = ''
            path            = ''
        
        params = {
            'type'                  : 'recognitions',
            'recognition'           : recognition,
            'data_json'             : data_json,
            'path'                  : path.replace("\\","/"),  
            'audio_voice'           : recognition.records,
            'data_list'             : data_list,
            'result_list'           : result_list,
            'text'                  : text_search,
            'start_record_seconds'  : (recognition.time_start - recognition.records.date).seconds,
            'start_record_human'    : time_human((recognition.time_start - recognition.records.date).seconds),
            'WRatio'                : WRatio,
            'partial_ratio'         : partial_ratio,
            'token_set_ratio'       : token_set_ratio,
            'token_sort_ratio'      : token_sort_ratio
        }
        return render(request, 'recognition/recognition_success_detail_recognition.html', {'params':params})
    else:
        return render(request, 'website/start.html', {'params': params})


def tematiks_op(request):
    params = {
        'request':request
    }
    
    if request.user.is_authenticated:
        
        
        select_count = 25
        if 'select_count' in request.GET:
            select_count = int(request.GET.get('select_count'))

        # Оптимизация: добавляем select_related для anketa
        tematics_list = Recognition_Tematika.objects.filter(anketa__id=1).select_related('anketa').order_by('name')
        
        name    = ''
        status  = 0

        if 'name' in request.GET:
            name = request.GET.get('name')
            tematics_list = tematics_list.filter(name__icontains=name)

        if 'status' in request.GET:
            status = request.GET.get('status')
            if len(status) > 0:
                if status == '1':
                    tematics_list = tematics_list.filter(enabled=True)
                elif status == '2':
                    tematics_list = tematics_list.filter(enabled=False)
        
        # Оптимизация: добавляем annotate для подсчета фраз (если нужно)
        # Пока оставляем как есть, так как worlds_count может быть полем модели
        
        page_number = request.GET.get('page')
        
        paginator   = Paginator(tematics_list, select_count)
        page_obj    = paginator.get_page(page_number)
        
        filtr = {
            'name'      : name,
            'status'    : status
        }
        params = {
            'type'              : 'recognitions',
            'page_number'       : page_number,
            'paginator'         : page_obj,
            'filtr'             : filtr,
            'select_count'      : select_count     
        }
        return render(request, 'recognition/tematiks_op.html', {'params':params})
    else:
        return render(request, 'website/start.html', {'params': params})


def tematiks_op_edit(request, id):
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
            tematika = Recognition_Tematika.objects.get(pk = id)
        
        if request.method == 'POST':
           
            if 'save_button' in request.POST:
                if new:
                    tematika = Recognition_Tematika()
                tematika.name   = request.POST['name']
                tematika.anketa = Recognition_Anketa.objects.get(pk=1)
                tematika.field  = request.POST['field'][:200]
                rating = request.POST['rating']
                if len(rating) > 0:
                    tematika.rating = int(rating)
                tematika.enabled = 'status' in request.POST 
                tematika.save()
                
            if 'save_fraza' in request.POST:
                if new:
                    tematika = Recognition_Tematika()
                tematika.name   = request.POST['name']
                tematika.anketa = Recognition_Anketa.objects.get(pk=1)
                tematika.field  = request.POST['field'][:200]
                rating = request.POST['rating']
                if len(rating) > 0:
                    tematika.rating = int(rating)
                tematika.enabled = 'status' in request.POST 
                tematika.save()
                
                fraza_name      = request.POST['fraza']
                fraza_rating    = request.POST['fraza_rating']
                fraza_enabled   = 'fraza_enabled' in request.POST 

                fraza = Recognition_Tematika_fraza()
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

            fraza_list  = Recognition_Tematika_fraza.objects.filter(tematika = tematika).order_by('name')
            page_number = request.GET.get('page')
            paginator   = Paginator(fraza_list, select_count)
            page_obj    = paginator.get_page(page_number)

        params = {
            'type'              : 'recognitions',
            'new'               : new,
            'tematika'          : tematika,
            'paginator'         : page_obj,
            'fields'            : get_fields(1),
            'select_count'      : select_count   
        }
        return render(request, 'recognition/tematiks_edit.html', {'params':params})
    else:
        return render(request, 'website/start.html', {'params': params})


def tematiks(request):
    params = {
        'request':request
    }
    if request.user.is_authenticated:
        countListRecord = 15
        tematics_list = Recognition_Tematika.objects.filter(anketa__id = 1).order_by('name')
        name = ''
        if 'name' in request.GET:
            name = request.GET.get('name')
            tematics_list = tematics_list.filter(name__contains = name)
        page_number = request.GET.get('page')
        
        paginator   = Paginator(tematics_list, countListRecord)
        page_obj    = paginator.get_page(page_number)
        filtr = {
            'name': name
        }
        params = {
            'page_number'   : page_number,
            'paginator'     : page_obj,
            'filtr'         : filtr,
            'type'          : 12
        }
        return render(request, 'recognition/tematiks.html', {'params':params})
    else:
        return render(request, 'website/start.html', {'params': params})


def recognitions(request):
    params = {
        'request':request
    }
    if request.user.is_authenticated:
        countListRecord = 15
        recognitions_list = Recognition_call.objects.all().order_by('-date')
        name = ''
        if 'name' in request.GET:
            name = request.GET.get('name')
            recognitions_list = recognitions_list.filter(name__contains = name)
        page_number = request.GET.get('page')
        
        # Оптимизация: убираем list() - передаем QuerySet напрямую в Paginator
        paginator = Paginator(recognitions_list, countListRecord)
        page_obj = paginator.get_page(page_number)
        filtr = {
            'name': name
        }
        params = {
            'page_number': page_number,
            'paginator': page_obj,
            'filtr': filtr,
            'type': 12
        }
        return render(request, 'recognition/lk_recognitions.html', {'params':params})
    else:
        return render(request, 'website/start.html', {'params': params})


def recognition(request, id):
    params = {
        'request':request
    }
    result_list = list()
    text_search = request.GET.get('text')

    WRatio          = list()
    partial_ratio   = list()
    token_set_ratio = list()
    token_sort_ratio = list()

    if request.user.is_authenticated:
        recognition     = Records_voice_recorder.objects.get(pk = id)
        data_list = list()

        if recognition.data_json != '':
            data_json       = json.loads(recognition.data_json)
            path            = data_json['info_audio']['path']
            conf            = data_json['conf']
            prev = 0
            text = ''
            for inf in conf:
                if inf['start'] - prev > 3:
                    if inf['start'] - prev > 3:
                        data_list.append({'time':convert_to_preferred_format(prev - 2), 'sec': int(prev - 2 ), 'text': ''})  
                    data_list.append({'time':convert_to_preferred_format(prev), 'sec': int(prev), 'text': text})
                    
                    resultpartial_ratio = fuzz.partial_ratio(text_search, text)
                    if resultpartial_ratio > 70 and len(text) > 3:
                        partial_ratio.append('-' + str(resultpartial_ratio) + ' - ' + text + "<br>")

                    resultWRatio = fuzz.WRatio(text_search, text)
                    if resultWRatio > 70 and len(text) > 3:
                        WRatio.append('-' + str(resultWRatio) + ' - ' + text + "<br>") 

                    resulttoken_set_ratio = fuzz.token_set_ratio(text_search, text)
                    if resulttoken_set_ratio > 70 and len(text) > 3:
                        token_set_ratio.append('-' + str(resulttoken_set_ratio) + ' - ' + text + "<br>")

                    resulttoken_sort_ratio = fuzz.token_sort_ratio(text_search, text)
                    if resulttoken_sort_ratio > 70 and len(text) > 3:
                        token_sort_ratio.append('-' + str(resulttoken_set_ratio) + ' - ' + text + "<br>")

                    text = inf['data']['word']
                    prev = inf['start']
                else:
                    text = text + ' ' + inf['data']['word']
                    prev = inf['start']
        else:
            data_json       = ''
            path            = ''
        
        params = {
            'type'                  : 'recognition',
            'recognition'           : recognition,
            'data_json'             : data_json,
            'path'                  : path.replace("\\","/"),  
            'audio_voice'           : recognition,
            'data_list'             : data_list,
            'result_list'           : result_list,
            'text'                  : text_search,
            'WRatio'                : WRatio,
            'partial_ratio'         : partial_ratio,
            'token_set_ratio'       : token_set_ratio,
            'token_sort_ratio'      : token_sort_ratio
        }
        
        return render(request, 'recognition/lk_recognition.html', {'params':params})
    else:
        return render(request, 'website/start.html', {'params': params})


#Контроль
def control(request):
    if request.user.is_authenticated:
        direction       = int(request.GET.get('direction', '1'))
        date_start      = request.GET.get('date_start', '')
        date_end        = request.GET.get('date_end', '')
        buauto          = False
        number          = ''

        if 'number' in request.GET:
            number = request.GET.get('number')

        if direction == 5:
            buauto = True
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
            'date_end'      : date_end,
            'direction'     : direction,
            'number'        : number
        }

        # Оптимизация: устраняем N+1 проблему - используем annotate для группировки
        from django.db.models import Case, When, Value, IntegerField, Exists, OuterRef
        
        base_qs = DocRLK.objects.filter(
            dataTime__gte=date_start,
            dataTime__lte=date_end
        ).filter(
            Q(contacType__id=7) | Q(contacType__id=42)
        ).filter(
            unit__buauto=buauto
        ).exclude(
            type__id=19
        ).select_related('unit', 'unit__city', 'type', 'contacType')
        
        if len(number) > 0:
            base_qs = base_qs.filter(nomer__icontains=number)
        
        # Группируем по городам и подразделениям с агрегацией
        # Используем подзапрос для проверки наличия success_cheklist_cvc
        # Сначала аннотируем каждый документ наличием CVC чеклиста
        base_qs_annotated = base_qs.annotate(
            has_cvc_success=Exists(
                Records_voice_recorder_cvc_checklist.objects.filter(
                    rlk_id=OuterRef('pk')
                ).filter(result__gt=0)
            )
        )
        
        # Теперь группируем и считаем
        city_unit_stats = base_qs_annotated.values(
            'unit__city',
            'unit__city__name',
            'unit',
            'unit__name'
        ).annotate(
            total_count=Count('id'),
            # Подсчитываем документы с успешным CVC чеклистом
            cvc_ok_count=Count('id', filter=Q(has_cvc_success=True)),
            # Подсчитываем документы без успешного CVC чеклиста
            cvc_no_count=Count('id', filter=Q(has_cvc_success=False))
        ).order_by('unit__city__name', 'unit__name')
        
        # Группируем данные по городам
        data_dict = {}
        doc_count = 0
        cvc_ok = 0
        cvc_no = 0
        
        for item in city_unit_stats:
            city_id = item['unit__city']
            city_name = item['unit__city__name'] or 'Не указан'
            
            if city_id not in data_dict:
                data_dict[city_id] = {
                    'city__id': city_id,
                    'city__name': city_name,
                    'units': [],
                    'count_city': 0,
                    'cvc_ok_city': 0,
                    'cvc_no_city': 0
                }
            
            data_dict[city_id]['units'].append({
                'unit__id': item['unit'],
                'unit__name': item['unit__name'] or 'Не указано',
                'count': item['total_count'],
                'cvc_ok': item['cvc_ok_count'],
                'cvc_no': item['cvc_no_count']
            })
            
            data_dict[city_id]['count_city'] += item['total_count']
            data_dict[city_id]['cvc_ok_city'] += item['cvc_ok_count']
            data_dict[city_id]['cvc_no_city'] += item['cvc_no_count']
        
        # Преобразуем в список и считаем общие итоги
        data_list = []
        for city_data in data_dict.values():
            data_list.append(city_data)
            doc_count += city_data['count_city']
            cvc_ok += city_data['cvc_ok_city']
            cvc_no += city_data['cvc_no_city']

        params = {
            'type'              : 'recognitions',
            'filtr'             : filtr,
            'data'              : data_list,
            'doc_count'         : doc_count,
            'cvc_ok'            : cvc_ok,
            'cvc_no'            : cvc_no,
            'link_save'         : request.build_absolute_uri().replace('control', 'control_excel')
            
        }
        return render(request, "recognition/recognition_control.html", {'params': params})    
    else:
        return HttpResponseRedirect('/login')

def control_excel(request):
    if request.user.is_authenticated:
        direction       = int(request.GET.get('direction', '1'))
        date_start      = request.GET.get('date_start', '')
        date_end        = request.GET.get('date_end', '')
        buauto          = False
        number          = ''

        if 'number' in request.GET:
            number = request.GET.get('number')

        if direction == 5:
            buauto = True
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
            'date_end'      : date_end,
            'direction'     : direction,
            'number'        : number
        }

        data_list           = list() 
       
        qyery               = DocRLK.objects.filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(Q(contacType__id= 7) | Q(contacType__id = 42)).filter(unit__buauto = buauto).exclude(type__id = 19)
        if len(number) > 0:
            qyery = qyery.filter(nomer__icontains = number)   
            
        subquery_success    = Subquery(Records_voice_recorder_cvc_checklist.objects.filter(rlk__id = OuterRef(name='id')).values('result')[:1])        
        object_list         = qyery.annotate(success_cheklist_cvc = Count(subquery_success)).order_by('-rlk__dataTime')
        subquery        = Subquery(CheckList.objects.filter(rlk_id = OuterRef(name='id')).values('result')[:1])  
        subquery_cvc    = Subquery(Records_voice_recorder_cvc_checklist.objects.filter(rlk_id = OuterRef(name='id')).values('result')[:1])        
        object_list     = object_list.annotate(custom_cheklist = subquery).order_by('-dataTime')
        object_list     = object_list.annotate(custom_cheklist_cvc = subquery_cvc).order_by('-dataTime')

        headers = {
            'file_name' : 'rlk_records_kg_cvc_all.xlsx'
        }

        response = HttpResponse(content_type='application/ms-excel', headers = headers)
        response['Content-Disposition'] = 'attachment; filename="rlk_records_kg_cvc_all.xlsx"'
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Контроль рабочих листов по всем ДЦ"

        # Add headers
        headers = ["Дата РЛК", "Номер РЛК", "Подразделение ДЦ", "Сотрудник", "Начало", "Окончания", "Продолжительность", "Запись", "Чек KG", "Чек CVC"]
        ws.append(headers)

        for doc in object_list:
            ws.append([doc.dataTime, doc.nomer, str(doc.unit.name), str(doc.staff), doc.dataTimeCreate, doc.dataEnd.strftime("%Y-%m-%d %H:%M"), doc.time_visit(), doc.sound_count(), doc.custom_cheklist, doc.custom_cheklist_cvc])

        # Save the workbook to the HttpResponse
        wb.save(response)
        return response


def control_detail(request, id):
    params = {
        'request':request
    }
    if request.user.is_authenticated:
        staff           = ''
        filtr_count     = 0
        select_count    = 25
        number          = ''

        if 'number' in request.GET:
            number = request.GET.get('number')

        if 'select_count' in request.GET:
            select_count = int(request.GET.get('select_count'))
        
        #select_staff        = 
        status_cheklist     = int(request.GET.get('status_cheklist', '0'))
        status_canceled     = int(request.GET.get('status_canceled', '0'))
        date_start          = ''
        date_end            = ''

        # Оптимизация: добавляем select_related для связанных объектов
        unit = RefUnit.objects.select_related('city').get(pk=id)
        object_list = DocRLK.objects.filter(
            unit__id=id
        ).filter(
            Q(contacType__id=7) | Q(contacType__id=42)
        ).exclude(
            type__id=19
        ).select_related('unit', 'unit__city', 'staff', 'type', 'contacType')
        
        subquery = Subquery(CheckList.objects.filter(rlk_id=OuterRef(name='id')).values('result')[:1])  
        subquery_cvc = Subquery(Records_voice_recorder_cvc_checklist.objects.filter(rlk_id=OuterRef(name='id')).values('result')[:1])        
        object_list = object_list.annotate(custom_cheklist=subquery)
        object_list = object_list.annotate(custom_cheklist_cvc=subquery_cvc)
        staffs = object_list.order_by('staff__name').values('staff', 'staff__name').distinct()

        if len(number) > 0:
            object_list = object_list.filter(nomer__icontains = number)

        if 'date_start' in request.GET:
            date_start = request.GET['date_start']
            if len(date_start) > 0:
                date_start = DT.datetime.strptime(request.GET['date_start'], "%Y-%m-%d")
                object_list = object_list.filter(dataTime__gte = date_start)
                filtr_count = filtr_count + 1

        if 'staff' in request.GET:
            staff = request.GET['staff']
            if len(staff) > 0:
                if staff == "None":
                    object_list = object_list.filter(staff = None)
                else:
                    object_list = object_list.filter(staff__name = staff)
                filtr_count = filtr_count + 1

        if 'date_end' in request.GET:
            date_end = request.GET['date_end']
            if len(date_end) > 0:
                date_end = DT.datetime.strptime(request.GET['date_end'], "%Y-%m-%d")
                object_list = object_list.filter(dataTime__lte = date_end)
                filtr_count = filtr_count + 1
        
        if status_cheklist == 1:
            object_list = object_list.filter(custom_cheklist__gte = 1)
            filtr_count = filtr_count + 1    
        if status_cheklist == 2:
            object_list = object_list.filter(custom_cheklist = None)
            filtr_count = filtr_count + 1    

        if status_canceled == 1:
            object_list = object_list.filter(canceled = True)
            filtr_count = filtr_count + 1    
        if status_canceled == 2:
            object_list = object_list.filter(canceled = False)
            filtr_count = filtr_count + 1   

        page_number = request.GET.get('page')
        
        object_list = object_list.order_by('-dataTime')
        
        paginator   = Paginator(object_list, select_count)
        page_obj    = paginator.get_page(page_number)
        
        selected = {
            "staffs" : staffs
        }

        filtr = {
            'status_cheklist'       : status_cheklist,
            'status_canceled'       : status_canceled,
            'date_start'            : date_start,
            'date_end'              : date_end,
            'staff'                 : staff,
            'number'                : number,
            'filtr_count'           : filtr_count
        }

        params = {
            'type'              : 'recognitions',
            'unit'              : unit,
            'page_number'       : page_number,
            'paginator'         : page_obj,
            'paginator_'        : paginator,
            'filtr'             : filtr,
            'selected'          : selected,
            'select_count'      : select_count,
            'link_save'         : request.build_absolute_uri().replace('control', 'control_excel')    
        }
        return render(request, 'recognition/recognition_control_detail.html', {'params':params})
    else:
        return render(request, 'website/start.html', {'params': params})

def control_detail_excel(request, id):
    params = {
        'request':request
    }
    if request.user.is_authenticated:
        staff           = ''
        filtr_count     = 0
        select_count    = 25
        number          = ''

        if 'number' in request.GET:
            number = request.GET.get('number')

        if 'select_count' in request.GET:
            select_count = int(request.GET.get('select_count'))
        
        #select_staff        = 
        status_cheklist     = int(request.GET.get('status_cheklist', '0'))
        status_canceled     = int(request.GET.get('status_canceled', '0'))
        date_start          = ''
        date_end            = ''

        # Оптимизация: добавляем select_related для связанных объектов
        unit = RefUnit.objects.select_related('city').get(pk=id)
        object_list = DocRLK.objects.filter(
            unit__id=id
        ).filter(
            Q(contacType__id=7) | Q(contacType__id=42)
        ).exclude(
            type__id=19
        ).select_related('unit', 'unit__city', 'staff', 'type', 'contacType')
        
        subquery = Subquery(CheckList.objects.filter(rlk_id=OuterRef(name='id')).values('result')[:1])  
        subquery_cvc = Subquery(Records_voice_recorder_cvc_checklist.objects.filter(rlk_id=OuterRef(name='id')).values('result')[:1])        
        object_list = object_list.annotate(custom_cheklist=subquery)
        object_list = object_list.annotate(custom_cheklist_cvc=subquery_cvc)
        staffs = object_list.order_by('staff__name').values('staff', 'staff__name').distinct()

        if len(number) > 0:
            object_list = object_list.filter(nomer__icontains = number)

        if 'date_start' in request.GET:
            date_start = request.GET['date_start']
            if len(date_start) > 0:
                date_start = DT.datetime.strptime(request.GET['date_start'], "%Y-%m-%d")
                object_list = object_list.filter(dataTime__gte = date_start)
                filtr_count = filtr_count + 1

        if 'staff' in request.GET:
            staff = request.GET['staff']
            if len(staff) > 0:
                if staff == "None":
                    object_list = object_list.filter(staff = None)
                else:
                    object_list = object_list.filter(staff__name = staff)
                filtr_count = filtr_count + 1

        if 'date_end' in request.GET:
            date_end = request.GET['date_end']
            if len(date_end) > 0:
                date_end = DT.datetime.strptime(request.GET['date_end'], "%Y-%m-%d")
                object_list = object_list.filter(dataTime__lte = date_end)
                filtr_count = filtr_count + 1
        
        if status_cheklist == 1:
            object_list = object_list.filter(custom_cheklist__gte = 1)
            filtr_count = filtr_count + 1    
        if status_cheklist == 2:
            object_list = object_list.filter(custom_cheklist = None)
            filtr_count = filtr_count + 1    

        if status_canceled == 1:
            object_list = object_list.filter(canceled = True)
            filtr_count = filtr_count + 1    
        if status_canceled == 2:
            object_list = object_list.filter(canceled = False)
            filtr_count = filtr_count + 1   

        page_number = request.GET.get('page')
        
        object_list = object_list.order_by('-dataTime')
        
        headers = {
            'file_name' : 'sms_opros_service.xlsx'
        }

        response = HttpResponse(content_type='application/ms-excel', headers = headers)
        response['Content-Disposition'] = 'attachment; filename="sms_opros_service.xlsx"'
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Контроль " + unit.name

        # Add headers
        headers = ["Дата РЛК", "Номер РЛК", "Подразделение ДЦ", "Сотрудник", "Начало", "Окончания", "Продолжительность", "Запись", "Чек KG", "Чек CVC"]
        ws.append(headers)

        for doc in object_list:
            ws.append([doc.dataTime, doc.nomer, str(doc.unit.name), str(doc.staff), doc.dataTimeCreate, doc.dataEnd, doc.time_visit(), doc.sound_count(), doc.custom_cheklist, doc.custom_cheklist_cvc])

        # Save the workbook to the HttpResponse
        wb.save(response)
        return response
    else:
        return render(request, 'website/start.html', {'params': params})


def control_detail_doc(request, id, doc_id):
    params = {
        'request':request
    }
    if request.user.is_authenticated:
        
        # Оптимизация: добавляем select_related для связанных объектов
        audio_success = ''
        doc = DocRLK.objects.select_related('unit', 'unit__city', 'staff', 'type', 'contacType').get(pk=doc_id)
        
        if request.method == 'POST':
            if 'record_replace_send_id' in request.POST:
                id_record = request.POST.get('record_replace_send_id', '')
                if len(id_record) > 0:
                    Records_voice_recorder_cvc.objects.filter(records__id = id_record).delete()
                    return HttpResponseRedirect(request.path_info) 

        audio_list_qyery    = get_audio_records(doc)
        audio_list_doc      = list()
        
        for audio_list in audio_list_qyery:
            audio                   = audio_list
            success                 = False
            start_record_seconds    = 0
            end_record_seconds      = audio.time

            rlk_events          = doc.dataTimeCreate
            date_event_start    = audio.date
            date_event_end      = date_event_start + DT.timedelta(seconds = audio.time) 

            if rlk_events > date_event_start and doc.dataEnd < date_event_end:
                date_start_rlk  = rlk_events
                hour_new        = date_start_rlk.hour
                minute_new      = date_start_rlk.minute

                if minute_new < 5:
                    minute_new  = minute_new + 60 - 5
                    hour_new    = hour_new - 1
                else:
                    minute_new  = minute_new - 5
                
                date_start_rlk = date_start_rlk.replace(hour=hour_new, minute=minute_new)
                dateNull = DT.datetime(1,1,1,0,0, tzinfo=DT.timezone.utc)
                if doc.dataEnd == dateNull or doc.dataEnd == DT.datetime(1,1,1,0,0):
                    dataEnd = date_start_rlk + DT.timedelta(hours=1)
                    if dataEnd > date_event_end:
                        dataEnd = date_event_end
                else:
                    dataEnd = doc.dataEnd
                    
                if (dataEnd - date_start_rlk).seconds > 480:
                    success                 = True
                    audio_success           = audio
                    start_record_seconds    = (rlk_events - date_event_start).seconds
                    end_record_seconds      = (rlk_events - date_event_start).seconds + (doc.dataEnd - rlk_events).seconds
            
            fragments = cvc_get_record_info_no_send(audio_list)
                
            audio_info = {
                'id'                            : audio.id,
                'audio_record'                  : audio,
                'success'                       : success,
                'start_record_seconds'          : start_record_seconds,
                'end_record_seconds'            : end_record_seconds,
                'start_record_seconds_human'    : time_human(start_record_seconds),
                'end_record_seconds_human'      : time_human(end_record_seconds),
                'fragments'                     : fragments
            }
            if success:
                audio_success = audio_info     
            audio_list_doc.append(audio_info)
 
        audio_list_array = list()
        for record in audio_list_doc:
            params_audio = {
                'id'                            : record['id'],
                'url'                           : record['audio_record'].audio.url,
                'start_record_seconds'          : record['start_record_seconds'],
                'end_record_seconds'            : record['end_record_seconds'],
                'start_record_seconds_human'    : record['start_record_seconds_human'],
                'end_record_seconds_human'      : record['end_record_seconds_human'],
                

            }
            audio_list_array.append(params_audio)

        if doc.unit.buauto:
            cheklist_count    = CheckList_op_kors.objects.filter(rlk__id = doc.id).count()
            if cheklist_count > 0:
                cheklist = CheckList_op_kors.objects.filter(rlk__id = doc.id)[0]
            else:
                cheklist = None 
            direction   = 5
        else:
            direction   = 1
            cheklist_count    = CheckList.objects.filter(rlk__id = doc.id).count()
            if cheklist_count > 0:
                cheklist = CheckList.objects.filter(rlk__id = doc.id)[0]
            else:
                cheklist = None 
                                     
        params = {
            'type'              : 'recognitions',
            'cheklist'          : cheklist,
            'cheklist_direction': direction,
            'doc'               : doc,
            'audio'             : audio_success,
            'audio_list'        : audio_list_doc,
            'audio_list_array'  : "'" + json.dumps(audio_list_array) + "'"
        }
        return render(request, 'recognition/recognition_control_detail_doc.html', {'params':params})
    else:
        return render(request, 'website/start.html', {'params': params})

def get_audio_records(rlk: DocRLK):
    """
    Ищем по документу рабочий лист записи диктофона сотрудника за этот день и 
    возвращаем qyeryset записей диктофона
    """
    audios = list()
	
    if rlk.staff != None:
        date    = rlk.dataTimeCreate
        dateID  = rlk.dataTimeCreate.date()
        dateIDT = dateID + DT.timedelta(days=1)
        
        user_bases = User.objects.filter(username__iexact = rlk.staff.domain_login.lower())
        if len(user_bases) == 1:
            user_base = user_bases[0]
            audios = Records_voice_recorder.objects.filter(date__range = (dateID, dateIDT)).filter(user = user_base).order_by('date')

    return audios	


#cvc
def cvc_op(request):
    if request.user.is_authenticated:
        direction       = int(request.GET.get('direction', '1'))
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
            'date_end'      : date_end,
            'direction'     : direction
        }

        data_list = list()
        
        citys       = Records_voice_recorder_cvc_checklist.objects.filter(direction = direction).filter(success = True).values('rlk__unit__city', 'rlk__unit__city__name').distinct().order_by('rlk__unit__city__name')
        citys       = citys.filter(rlk__dataTime__gte = date_start).filter(rlk__dataTime__lte = date_end)

        cvc_count       = 0
        cvc_duration    = 0

        for city in citys:
            units       = Records_voice_recorder_cvc_checklist.objects.filter(direction = direction).filter(rlk__dataTime__gte = date_start).filter(rlk__dataTime__lte = date_end).filter(rlk__unit__city__id = city['rlk__unit__city']).filter(success = True).values('rlk__unit', 'rlk__unit__name').distinct().order_by('rlk__unit__name')
            units_list  = list()
            count_city  = 0   
            duration_city = 0 
            for unit in units:
                count       = Records_voice_recorder_cvc_checklist.objects.filter(direction = direction).filter(rlk__dataTime__gte = date_start).filter(rlk__dataTime__lte = date_end).filter(rlk__unit__id = unit['rlk__unit']).filter(success = True).count()
                duration    = Records_voice_recorder_cvc_checklist.objects.filter(direction = direction).filter(rlk__dataTime__gte = date_start).filter(rlk__dataTime__lte = date_end).filter(rlk__unit__id = unit['rlk__unit']).filter(success = True).aggregate(Sum('duration'))
                
                count_city          = count_city + count
                duration_city       = duration_city + duration['duration__sum'] 
            
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
               'count_city'     : count_city,
               'duration_city'  : time_human(duration_city),
               'units'          : units_list
            }
            data_list.append(params_city)
            cvc_count       = cvc_count + count_city
            cvc_duration    = cvc_duration + duration_city

        params = {
            'type'              : 'recognitions',
            'filtr'             : filtr,
            'data'              : data_list,
            'cvc_count'         : cvc_count,
            'cvc_duration'      : time_human(cvc_duration)
        }
        return render(request, "recognition/recognition_success_cvc.html", {'params': params})    
    else:
        return HttpResponseRedirect('/login')

def cvc_op_detail(request, id):
    params = {
        'request':request
    }
    if request.user.is_authenticated:
        
        filtr_count     = 0
        select_count    = 25
        if 'select_count' in request.GET:
            select_count = int(request.GET.get('select_count'))
        
        #select_staff        = 
        status_cheklist     = int(request.GET.get('status_cheklist', '0'))
        status_canceled     = int(request.GET.get('status_canceled', '0'))
        date_start          = ''
        date_end            = ''

        object_list = Records_voice_recorder_cvc_checklist.objects.filter(success = True).filter(rlk__unit__id = id)
        subquery    = Subquery(CheckList.objects.filter(rlk_id = OuterRef(name='rlk_id')).values('result')[:1])        
        object_list = object_list.annotate(custom_cheklist = subquery).order_by('-rlk__dataTime')

        if 'date_start' in request.GET:
            date_start = request.GET['date_start']
            if len(date_start) > 0:
                date_start = DT.datetime.strptime(request.GET['date_start'], "%Y-%m-%d")
                object_list = object_list.filter(rlk__dataTime__gte = date_start)
                filtr_count = filtr_count + 1

        if 'date_end' in request.GET:
            date_end = request.GET['date_end']
            if len(date_end) > 0:
                date_end = DT.datetime.strptime(request.GET['date_end'], "%Y-%m-%d")
                object_list = object_list.filter(rlk__dataTime__lte = date_end)
                filtr_count = filtr_count + 1
        
        if status_cheklist == 1:
            object_list = object_list.filter(custom_cheklist__gte = 1)
            filtr_count = filtr_count + 1    
        if status_cheklist == 2:
            object_list = object_list.filter(custom_cheklist = None)
            filtr_count = filtr_count + 1    

        if status_canceled == 1:
            object_list = object_list.filter(canceled = True)
            filtr_count = filtr_count + 1    
        if status_canceled == 2:
            object_list = object_list.filter(canceled = False)
            filtr_count = filtr_count + 1   

        page_number = request.GET.get('page')
        
        object_list = object_list.order_by('-rlk__dataTime')
        
        paginator   = Paginator(object_list, select_count)
        page_obj    = paginator.get_page(page_number)
        
        filtr = {
            'status_cheklist'       : status_cheklist,
            'status_canceled'       : status_canceled,
            'date_start'            : date_start,
            'date_end'              : date_end,
            'filtr_count'           : filtr_count
        }
        params = {
            'type'              : 'recognitions',
            'page_number'       : page_number,
            'paginator'         : page_obj,
            'filtr'             : filtr,
            'select_count'      : select_count     
        }
        return render(request, 'recognition/recognition_success_detail_cvc.html', {'params':params})
    else:
        return render(request, 'website/start.html', {'params': params})

def cvc_op_detail_recognition(request, id, pk):
    params = {
        'request':request
    }
    result_list = list()
    text_search = request.GET.get('text')

    if request.user.is_authenticated:
        
        recognition         = Records_voice_recorder_cvc_checklist.objects.get(pk = pk)
        data_list           = list()
        tematiks            = Records_voice_recorder_cvc_checklist_tematics.objects.filter(checklist = recognition).order_by('-tematic__field')
        recognitions_kg     = Records_voice_recorder_queue.objects.filter(rlk = recognition.rlk)
        
        data_list           = list()
        if len(recognitions_kg) > 0:
            recognition_kg  = Records_voice_recorder_queue.objects.filter(rlk = recognition.rlk)[0]    
            data_list       = get_text_recognition(recognition_kg)
        
        checklists = CheckList.objects.filter(rlk = recognition.rlk)
        checklist = ''
        if len(checklists) > 0:
            checklist = checklists[0]
        
        if 'open_checkList' in request.GET:
            if checklist != '':
                if recognition.rlk.unit.buauto:
                    return HttpResponseRedirect('/checklists/glav/op_kors/op_kors_doc/?checkid=' + str(checklist.rlk.id))
                else:
                    return HttpResponseRedirect('/checklists/glav/op/doc/?checkid=' + str(checklist.rlk.id))

        if 'new_checklist' in request.GET:
            if recognition.rlk.unit.buauto:
                return HttpResponseRedirect('/checklists/glav/op_kors/op_kors_doc/?checkid=' + str(recognition.rlk.id))
            else:
                return HttpResponseRedirect('/checklists/glav/op/op_doc_new/?check_new_cvc=' + pk)
        checklist_kg = Records_voice_recorder_cvc_checklist_kg.objects.filter(checklist_cvc = recognition).order_by('questions_kg__chapter', '-questions_kg__priority_chapter')
        params = {
            'type'                  : 'recognitions',
            'recognition'           : recognition,
            'audio_voice'           : recognition.records,
            'data_list'             : data_list,
            'result_list'           : result_list,
            'text'                  : text_search,
            'start_record_seconds'  : (recognition.time_start - recognition.records.date).seconds,
            'end_record_seconds'    : (recognition.time_start - recognition.records.date).seconds + recognition.duration,
            'start_record_human'    : time_human((recognition.time_start - recognition.records.date).seconds),
            'tematiks'              : tematiks,
            'data_list'             : data_list,
            'checklist'             : checklist,
            'checklist_kg'          : checklist_kg
        }
        return render(request, 'recognition/recognition_success_detail_recognition_cvc.html', {'params':params})
    else:
        return render(request, 'website/start.html', {'params': params})

def cvc_tematiks_op(request):
    params = {
        'request':request
    }
    
    if request.user.is_authenticated:
        
        select_count = 25
        if 'select_count' in request.GET:
            select_count = int(request.GET.get('select_count'))

        tematics_list = Records_voice_recorder_cvc_tematics.objects.order_by('name')
        
        name    = ''
        status  = 0

        if 'name' in request.GET:
            name = request.GET.get('name')
            tematics_list = tematics_list.filter(name__icontains = name)

        if 'status' in request.GET:
            status = request.GET.get('status')
            if len(status) > 0:
                if status == '1':
                    tematics_list = tematics_list.filter(activated = True)
                elif status == '2':
                    tematics_list = tematics_list.filter(activated = False)
            
        page_number = request.GET.get('page')
        
        paginator   = Paginator(tematics_list, select_count)
        page_obj    = paginator.get_page(page_number)
        
        filtr = {
            'name'      : name,
            'status'    : status
        }
        params = {
            'type'              : 'recognitions',
            'page_number'       : page_number,
            'paginator'         : page_obj,
            'filtr'             : filtr,
            'select_count'      : select_count     
        }
        return render(request, 'recognition/tematiks_op_cvc.html', {'params':params})
    else:
        return render(request, 'website/start.html', {'params': params})

def cvc_tematiks_op_edit(request, id):
    params = {
        'request':request
    }
    if request.user.is_authenticated:
        
        tematika = Records_voice_recorder_cvc_tematics.objects.get(pk = id)
        
        if request.method == 'POST':
            if 'save_button' in request.POST:
                tematika.name           = request.POST['name']
                #tematika.field          = request.POST['field'][:200]
                tematika.activated      = 'status' in request.POST 
                tematika.canceled       = 'canceled' in request.POST 
                tematika.company        = 'company' in request.POST 
                tematika.save() 

                Records_voice_recorder_cvc_tematics_fields.objects.filter(tematics_cvc = tematika).delete()

                for key in request.POST.keys():
                    if key.startswith('field_check_'):
                        pk_tematic          = str(key).replace('field_check_', '')
                        tematics_field      = Records_voice_recorder_cvc_tematics_fields()
                        tematics_field.tematics_cvc = tematika
                        tematics_field.field        = pk_tematic
                        tematics_field.value        = int(request.POST['field_value_' + pk_tematic])
                        tematics_field.save()
            
            return HttpResponseRedirect(request.build_absolute_uri())
        
        fields_list = list()

        fields_check = get_fields(1)
        for field_check in fields_check:
            fields = field_check['fields']
            for field in fields:
                count = Records_voice_recorder_cvc_tematics_fields.objects.filter(tematics_cvc = tematika).filter(field = field['id']).count()
                if count > 0:
                    field['check'] = True
                    field['value'] = Records_voice_recorder_cvc_tematics_fields.objects.filter(tematics_cvc = tematika).filter(field = field['id'])[0].value
                else:
                    field['check'] = False
                    field['value'] = 0   
            
        params = {
            'type'              : 'recognitions',
            'tematika'          : tematika,
            'fields'            : fields_check   
        }
        return render(request, 'recognition/tematiks_edit_cvc.html', {'params':params})
    else:
        return render(request, 'website/start.html', {'params': params})

def cvc_tematiks_op_quequ(request):
    
    params = {
        'request':request
    }
    
    if request.user.is_authenticated:
        select_count = 25
        if 'select_count' in request.GET:
            select_count = int(request.GET.get('select_count'))
        
        direction       = int(request.GET.get('direction', '1'))
        
        lists = Records_voice_recorder_cvc_checklist.objects.filter(direction = direction).filter(success = False).order_by('rlk__dataTime')   
        page_number = request.GET.get('page')
        
        paginator   = Paginator(lists, select_count)
        page_obj    = paginator.get_page(page_number)
        filtr = {
            'direction' : direction
        }
        params = {
            'type'              : 'recognitions',
            'page_number'       : page_number,
            'paginator'         : page_obj,
            'filtr'             : filtr,
            'select_count'      : select_count     
        }
        return render(request, 'recognition/tematiks_op_cvc_quequ.html', {'params':params})
    else:
        return render(request, 'website/start.html', {'params': params})

#Общие функции
def records_questions(request):
    if request.user.is_authenticated:
        
        records_questions = Records_questions.objects.all().order_by('chapter','field')
        
        name        = ''
        status      = 0
        direction               = int(request.GET.get('direction', '1'))
        records_questions       = records_questions.filter(direction = direction)

        if 'name' in request.GET:
            name                   = request.GET.get('name')
            records_questions      = records_questions.filter(name__icontains = name)

        if 'status' in request.GET:
            status = request.GET.get('status')
            if len(status) > 0:
                if status == '1':
                    records_questions = records_questions.filter(estimation__gt = 0)
                elif status == '2':
                    records_questions = records_questions.filter(estimation = 0)
        
        records_questions_count_enabled      = records_questions.filter(estimation__gt = 0).count()
        records_questions_count_not_enabled  = records_questions.filter(estimation = 0).count()

        filtr = {
            'name'      : name,
            'status'    : status
        }
        params = {
            'type'                                      : 'recognitions',
            'direction'                                 : direction,
            'paginator'                                 : records_questions,
            'records_questions_count_enabled'           : records_questions_count_enabled,
            'records_questions_count_not_enabled'       : records_questions_count_not_enabled,
            'filtr'                                     : filtr
        }
        return render(request, 'recognition/records_questions.html', {'params': params})
    else:
        return HttpResponseRedirect('/')
 

def records_questions_edit(request, id):
    params = {
        'request':request
    }
    if request.user.is_authenticated:
        
        new             = False
        object          = ''
        select_count    = 25
        direction       = 0
        
        if id == '0':
            new                     = True
            direction               = int(request.GET.get('direction', '1'))
        else:
            object = Records_questions.objects.get(pk = id)
        
        if request.method == 'POST':
            
            if 'save_button' in request.POST:
                if new:
                    object              = Records_questions()
                object.name             = request.POST['name']
                estimation              = request.POST['estimation']
                object.field            = request.POST['field'][:200]
                if len(estimation) > 0:
                    object.estimation = int(estimation)
                if len(object.field) > 0:
                    object.chapter          = int(object.field[:1])
                    object.chapter_name     = object.field[:1]
                object.priority_chapter     = request.POST.get('priority_chapter', 0)      
                object.direction            = int(request.POST.get('direction', '1'))
                event_sale                  = request.POST.get('event_sale', False)
                if event_sale == 'on':
                    object.event_sale = True
                else:
                    object.event_sale = False    
                
                event_trade_in   = request.POST.get('event_trade_in', False)
                if event_trade_in == 'on':
                    object.event_trade_in = True
                else:
                    object.event_trade_in = False 
                object.save()
            
                object.tematics.clear()

                for key in request.POST.keys():
                    if key.startswith('tematic_'):
                        pk_tematic  = str(key).replace('tematic_', '')
                        tematics    = Records_voice_recorder_cvc_tematics.objects.get(pk = pk_tematic)
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
        
        tematics = Records_voice_recorder_cvc_tematics.objects.all().order_by('name')
        if new == True:
            tematics = Records_voice_recorder_cvc_tematics.objects.all().order_by('name')
        count_enabled = 0

        if object != '':
            subquery_queue      = Subquery(object.tematics.all().filter(id = OuterRef(name='id')).values('id')[:1]) 
            tematics            = tematics.annotate(test = subquery_queue).order_by('name')        
            count_enabled       = object.tematics.all().count()
        
        params = {
            'type'              : 'recognitions',
            'direction'         : direction,
            'new'               : new,
            'fields'            : get_fields(direction),
            'tematics'          : tematics,
            'object'            : object,
            'count_enabled'     : count_enabled, 
            'count_off'         : tematics.count() - count_enabled,
            'select_count'      : select_count   
        }
        return render(request, 'recognition/records_questions_edit.html', {'params': params})
    else:
        return render(request, 'website/start.html', {'params': params})



#Отчеты
def report_cvc_kg_op(request):
    params = {
        'request':request
    }
    
    countListRecord = 25
    if request.GET.get('select_count', 25):
        countListRecord = int(request.GET.get('select_count', 25))

    if request.user.is_authenticated:
        
        date_start      = request.GET.get('date_start', '')
        date_end        = request.GET.get('date_end', '')
        direction       = int(request.GET.get('direction', '1'))
        number          = request.GET.get('number', '')
        date_period     = DT.datetime.now()
        
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
        
        if direction == 1:
            docs            = DocRLK.objects.filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(Q(contacType__id= 7) | Q(contacType__id = 42)).filter(unit__buauto = False).exclude(type__id = 19)
            subquery_check 	= Subquery(CheckList.objects.filter(rlk_id = OuterRef(name='id')).values('result')[:1])
        elif direction == 5:
            docs            = DocRLK.objects.filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(Q(contacType__id= 7) | Q(contacType__id = 42)).filter(unit__buauto = True)
            subquery_check 	= Subquery(CheckList_op_kors.objects.filter(rlk_id = OuterRef(name='id')).values('result')[:1])

        if number != '':
            docs = docs.filter(nomer__icontains = number)

        subquery        = Subquery(Records_voice_recorder_cvc_checklist.objects.filter(success = True).filter(rlk_id = OuterRef(name='id')).values('result')[:1])        
        docs 		= docs.annotate(result = Coalesce(subquery_check, 0)).order_by('dataTime')
        docs 		= docs.annotate(cheklist_cvc = Coalesce(subquery, 0)).order_by('dataTime')
        docs 		= docs.annotate(difference = Coalesce(F('result'), 0) - Coalesce(F('cheklist_cvc'), 0)) 
        
        list_docs   = docs
        '''
        for doc in docs:
            if doc.result != None or doc.cheklist_cvc != None:
                doc.result          = 0 if doc.result == None else doc.result
                doc.cheklist_cvc    = 0 if doc.cheklist_cvc == None else doc.cheklist_cvc 
                doc_new = {
                    'doc'           : doc,
                    'difference'    : doc.result - doc.cheklist_cvc
                }
                list_docs.append(doc_new)
        '''
        filtr = {
            'date_start'        : date_start,
            'date_end'          : date_end,
            'direction'         : direction,
            'number'            : number
            
        }
        
        
        page = 0
        if request.GET.get('page', ""):
            page = int(request.GET['page'])
        paginator 	= Paginator(list_docs, countListRecord)
        page_obj 	= paginator.get_page(page)

        params = {
            'type'              : 'recognitions',
            'filtr'             : filtr,
            'objects'           : page_obj,
            'link_save'         : request.build_absolute_uri().replace('report_cvc_kg_op', 'report_cvc_kg_op_xls')
        }
        return render(request, 'recognition/report_cvc_kg_op.html', {'params': params})
    else:
        return render(request, 'website/start.html', {'params': params})

def report_cvc_kg_op_xls(request):
    
    params = {
        'request':request
    }
    
    countListRecord = 25
    if request.GET.get('select_count', 25):
        countListRecord = int(request.GET.get('select_count', 25))

    if request.user.is_authenticated:
        
        date_start      = request.GET.get('date_start', '')
        date_end        = request.GET.get('date_end', '')
        direction       = int(request.GET.get('direction', '1'))
        number          = request.GET.get('number', '')
        date_period     = DT.datetime.now()
        
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
        
        if direction == 1:
            docs            = DocRLK.objects.filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(Q(contacType__id= 7) | Q(contacType__id = 42)).filter(unit__buauto = False).exclude(type__id = 19)
            subquery_check 	= Subquery(CheckList.objects.filter(rlk_id = OuterRef(name='id')).values('result')[:1])
        elif direction == 5:
            docs            = DocRLK.objects.filter(dataTime__gte = date_start).filter(dataTime__lte = date_end).filter(Q(contacType__id= 7) | Q(contacType__id = 42)).filter(unit__buauto = True)
            subquery_check 	= Subquery(CheckList_op_kors.objects.filter(rlk_id = OuterRef(name='id')).values('result')[:1])

        if number != '':
            docs = docs.filter(nomer__icontains = number)

        subquery        = Subquery(Records_voice_recorder_cvc_checklist.objects.filter(success = True).filter(rlk_id = OuterRef(name='id')).values('result')[:1])        
        docs 		= docs.annotate(result = Coalesce(subquery_check, 0)).order_by('dataTime')
        docs 		= docs.annotate(cheklist_cvc = Coalesce(subquery, 0)).order_by('dataTime')
        docs 		= docs.annotate(difference = Coalesce(F('result'), 0) - Coalesce(F('cheklist_cvc'), 0)) 
        
        headers = {
            'file_name' : 'Сравнение показателей CVC и KG.xlsx'
        }

        response = HttpResponse(content_type='application/ms-excel', headers = headers)
        response['Content-Disposition'] = 'attachment; filename="report_cvc_kg_op.xlsx"'
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Сравнение показателей CVC и KG"

        # Add headers
        headers = ["Дата РЛК", "Номер РЛК", "Подразделение", "KG", "CVC", "Разница"]
        ws.append(headers)

        # Add data from the model
        docs = docs.values('dataTime', 'nomer', 'unit__name', 'result', 'cheklist_cvc', 'difference')
        for opros in docs:
            ws.append([opros['dataTime'], opros['nomer'], opros['unit__name'], opros['result'], opros['cheklist_cvc'], opros['difference']])

        # Save the workbook to the HttpResponse
        wb.save(response)
        return response
    else:
        return render(request, 'website/start.html', {'params': params})



#Служебные функции
def get_text_recognition(recognition):
    data_list = list()
    if recognition.data_json != '':
            data_json       = json.loads(recognition.data_json.replace("'",'"').replace('True', '"True"').replace('False', '"False"'))
            path            = data_json['info_audio']['path']
            data_text       = data_json['data']
            for param_fraza in data_text:
                time = param_fraza['time_start']
                data_list.append({'time': convert_to_preferred_format(time), 'sec': int(time), 'text': param_fraza['text']})
    return data_list   

def get_fields(direction):

    filds_razdel 	= list()
    fields			= list()
    razdel = ''

    if direction == 1:
        meta_fields = CheckList._meta.get_fields()
    else:
        meta_fields = CheckList_op_kors._meta.get_fields()
    
    for meta_field in meta_fields:
        name = meta_field.__dict__['name']
        if name.startswith('v'): 
            
            if name[1:2] != razdel:
                if len(fields) > 0:
                    info = {
                        'razdel': razdel,
                        'fields': fields
                    }
                    filds_razdel.append(info)
                fields = list()
                razdel = name[1:2]
            
            field = {
                'id' 			: name,
                'razdel' 		: name.replace('v',''),
                'name'			: meta_field.__dict__['verbose_name'],
                'name_human'	: name.replace('v','').replace('_', '.')
            }
            fields.append(field)
    if len(fields) > 0:
        info = {
            'razdel': razdel,
            'fields': fields
        }
        filds_razdel.append(info)
        fields = list()
        razdel = razdel

    return filds_razdel
    
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