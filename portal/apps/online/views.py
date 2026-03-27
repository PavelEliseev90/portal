from asyncio.windows_events import NULL
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
import datetime
from online.models import Online_doc, Records_online_doc, PersonalDataConsent, UserCarEstimation
from refs.models import RefCity, RefUnit, AutoruMark, AutoruModel, AutoruModification, AutoruComplectation
from django.conf import settings
import json
import requests
from django.template.loader import get_template
from django.core.mail import EmailMultiAlternatives
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Min, Max


@csrf_exempt
def record_service(request, id):
    count = Records_online_doc.objects.filter(short_url = id).count()
    if count > 0:
        doc = Records_online_doc.objects.filter(short_url = id)[0]
        doc.dataTimeOpen = datetime.datetime.now()
        doc.save()
        if request.method == "POST":
           if 'confirmed' in request.POST:
               doc.confirmed = True
               doc.save()
               return HttpResponseRedirect(request.build_absolute_uri()) 
        params = {
            'object' : doc
        }
        return render(request, 'online/record_service.html', {'params': params})
    else:
        return render(request, 'online/record_service_404.html')


@csrf_exempt
def online(request, id):
    online_doc  = Online_doc()
    online_docs = Online_doc.objects.filter(uid = id)
    
    if len(online_docs) == 1:
        online_doc = online_docs[0]
        select_units = list()
        select_times = list()
        select_citys = RefCity.objects.all().exclude(name = '').order_by("name")
        
        selected_city = ''
        selected_unit = ''
        selected_date = ''
        selected_time = ''
        
        selected = 0

        dt_now = datetime.datetime.today() - datetime.timedelta(days=-2)
        dt_now = dt_now.strftime('%Y-%m-%d')
        
        if request.method == "GET":
            online_doc.dataTimeOpen = datetime.datetime.today()
            online_doc.save()

        if request.method == "POST":
            if "selected_city" in request.POST.keys():
                selected_city = request.POST["selected_city"]
                if selected_city != '':
                    select_units = RefUnit.objects.filter(buauto = False).exclude(name_dop='').order_by("name")
                    select_units = select_units.filter(city__id = int(selected_city))
                    if "selected_unit" in request.POST.keys():
                        selected_unit = request.POST["selected_unit"]
                    if "selected_date" in request.POST.keys():
                        selected_date = request.POST["selected_date"]
                    if "selected_time" in request.POST.keys():
                        selected_time = request.POST["selected_time"]
            if 'selected' in request.POST.keys():
                selected = 1
            if 'call' in request.POST.keys():
                online_doc.call = True
                online_doc.save()
                send_messages_unit(request=request, doc=online_doc)
                return HttpResponseRedirect(request.build_absolute_uri())
            if 'record' in request.POST.keys():
                date_time_str               = selected_date + ' ' + selected_time 
                dateClose                   = datetime.datetime.strptime(date_time_str, '%Y-%m-%d %H:%M')
                online_doc.dataTimeRecord   = dateClose
                online_doc.unitRecord       = RefUnit.objects.get(id =selected_unit)
                online_doc.save()
                send_messages_unit(request = request, doc = online_doc)
                return HttpResponseRedirect(request.build_absolute_uri())
                
        if online_doc.call:
            selected = 2   
        if online_doc.dataTimeRecord != None:
            selected = 3 

        i=9
        while i < 20:
            select_times.append(''+ str(i) + ":00")
            i = i + 1
        
        filt = {
            'selected_city' : selected_city,
            'selected_unit' : selected_unit,
            'selected_date' : selected_date,
            'selected_time' : selected_time,
            'selected'      : selected   
        }
        
        params = {
            'select_units'  : select_units,
            'select_times'  : select_times,
            'select_citys'  : select_citys,
            'filt'          : filt,
            'dt_now'        : dt_now,
            'online_doc'    : online_doc
        }

        return render(request, 'online/welcome.html', {'params': params})
    return render(request, 'errors/404.html')


def send_messages_unit(request, doc):
    
    title           = ''
    email_list      = list()
    if doc.call:
        title = 'Он-лайн запись на сервис - ' + doc.clientName + ' / ' + doc.cars.name + ' / ' + 'заказан обратный звонок' + ' / ' + doc.dataTimeOpen.strftime("%d-%m-%Y %H:%M")
        params = {
            'unit'      : doc.unit.name,
            'vin'       : doc.cars.name,
            'mark'      : doc.cars.mark,
            'model'     : doc.cars.model,
            'date'      : doc.dataTimeOpen.strftime("%d-%m-%Y"),
            'time'      : doc.dataTimeOpen.strftime("%H:%M"),
            'customer'  : doc.clientName,
            'phone'     : doc.clientPhone,
            'unit_send' : doc.unit.name,
            'date_send' : doc.dataTimeCreate.strftime("%d-%m-%Y %H:%M"),
            'сall'      : True    
        }
        email_list = doc.unit.email_service.split(";")
    else:
        title = 'Он-лайн запись на сервис - ' + doc.clientName + ' / ' + doc.cars.name + ' / ' + doc.dataTimeRecord.strftime("%d-%m-%Y %H:%M")
        params = {
            'unit'      : doc.unitRecord.name,
            'vin'       : doc.cars.name,
            'mark'      : doc.cars.mark,
            'model'     : doc.cars.model,
            'date'      : doc.dataTimeRecord.strftime("%d-%m-%Y"),
            'time'      : doc.dataTimeRecord.strftime("%H:%M"),
            'customer'  : doc.clientName,
            'phone'     : doc.clientPhone,
            'unit_send' : doc.unit.name,
            'date_send' : doc.dataTimeCreate.strftime("%d-%m-%Y %H:%M")    
        }
        email_list = doc.unitRecord.email_service.split(";")

    d   = ({'params': params})
   
    plaintext   = get_template('email_online.txt')
    htmly       = get_template('email_online.html')
    
    email_list.append('p.eliseev@kors-group.com')
    
    subject, from_email, to = title, settings.EMAIL_HOST_USER, email_list
    
    text_content = plaintext.render(d)
    html_content = htmly.render(d)
    
    msg = EmailMultiAlternatives(subject, text_content, from_email, to)
    msg.attach_alternative(html_content, "text/html")
    msg.send()


@csrf_exempt
def personal_data_consent(request, token):
    """
    Отображение и обработка формы подтверждения обработки персональных данных
    """
    try:
        consent = PersonalDataConsent.objects.get(token=token)
    except PersonalDataConsent.DoesNotExist:
        return render(request, 'online/personal_data_consent_404.html')
    
    # Если уже подтверждено, показываем страницу успеха
    if consent.confirmed:
        params = {
            'consent': consent,
            'confirmed': True
        }
        return render(request, 'online/personal_data_consent_success.html', {'params': params})
    
    # Если отозвано, показываем соответствующую страницу
    if consent.revoked:
        params = {
            'consent': consent,
            'revoked': True
        }
        return render(request, 'online/personal_data_consent_revoked.html', {'params': params})
    
    # Получаем IP адрес и User Agent
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
    if ',' in ip_address:
        ip_address = ip_address.split(',')[0].strip()
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    # Если это первое открытие, сохраняем дату открытия
    if not consent.date_opened:
        consent.date_opened = datetime.datetime.now()
        consent.ip_address = ip_address
        consent.user_agent = user_agent
        consent.save()
    
    # Обработка POST запроса (подтверждение)
    if request.method == "POST":
        if 'confirm' in request.POST:
            # Валидация данных
            last_name = request.POST.get('last_name', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            middle_name = request.POST.get('middle_name', '').strip()
            phone = request.POST.get('phone', '').strip()
            email = request.POST.get('email', '').strip()
            agreement = request.POST.get('agreement', '')
            
            errors = []
            
            if not last_name:
                errors.append("Необходимо указать фамилию")
            if not first_name:
                errors.append("Необходимо указать имя")
            if not phone:
                errors.append("Необходимо указать номер телефона")
            if email and '@' not in email:
                errors.append("Указан некорректный email адрес")
            if agreement != 'on':
                errors.append("Необходимо дать согласие на обработку персональных данных")
            
            if errors:
                params = {
                    'consent': consent,
                    'errors': errors,
                    'form_data': {
                        'last_name': last_name,
                        'first_name': first_name,
                        'middle_name': middle_name,
                        'phone': phone,
                        'email': email
                    }
                }
                return render(request, 'online/personal_data_consent.html', {'params': params})
            
            # Сохраняем данные и подтверждаем
            consent.last_name = last_name
            consent.first_name = first_name
            consent.middle_name = middle_name
            consent.phone = phone
            consent.email = email
            consent.confirmed = True
            consent.date_confirmed = datetime.datetime.now()
            consent.ip_address = ip_address
            consent.user_agent = user_agent
            
            # Сохраняем текст согласия (версия на момент подтверждения)
            consent.consent_text = get_consent_text()
            
            consent.save()
            
            # Перенаправляем на страницу успеха
            return HttpResponseRedirect(request.build_absolute_uri())
    
    # Отображение формы
    params = {
        'consent': consent,
        'form_data': {
            'last_name': consent.last_name or '',
            'first_name': consent.first_name or '',
            'middle_name': consent.middle_name or '',
            'phone': consent.phone or '',
            'email': consent.email or ''
        }
    }
    return render(request, 'online/personal_data_consent.html', {'params': params})


def get_consent_text():
    """
    Возвращает актуальный текст согласия на обработку персональных данных
    """
    return """Я, действуя своей волей и в своем интересе, даю свое согласие на обработку моих персональных данных в соответствии с Федеральным законом от 27.07.2006 № 152-ФЗ «О персональных данных» на следующих условиях:

1. Согласие дается на обработку следующих персональных данных:
   - Фамилия, имя, отчество
   - Номер телефона
   - Email адрес (при указании)
   - Иные данные, предоставленные мной в процессе взаимодействия

2. Цели обработки персональных данных:
   - Обработка заявок и запросов
   - Предоставление услуг
   - Информирование о предоставляемых услугах
   - Ведение клиентской базы
   - Иные цели, связанные с предоставлением услуг

3. Способы обработки персональных данных:
   - Сбор, запись, систематизация, накопление, хранение
   - Уточнение (обновление, изменение), извлечение
   - Использование, передача (распространение, предоставление, доступ)
   - Обезличивание, блокирование, удаление, уничтожение

4. Согласие действует до момента его отзыва путем направления соответствующего уведомления.

5. Я подтверждаю, что предоставленные мной персональные данные являются достоверными.

6. Я понимаю, что в случае отзыва согласия обработка персональных данных должна быть прекращена, а мои персональные данные уничтожены в срок, не превышающий 30 дней с даты поступления указанного отзыва."""


def user_car_estimation(request, slug):
    return HttpResponseRedirect(f'/online/estimate/{slug}/year/')


def _wizard_session_key(slug):
    return f'user_estimation_wizard_{slug}'


def _get_wizard_state(request, slug):
    return request.session.get(_wizard_session_key(slug), {})


def _set_wizard_state(request, slug, state):
    request.session[_wizard_session_key(slug)] = state
    request.session.modified = True


def _clear_wizard_state(request, slug):
    if _wizard_session_key(slug) in request.session:
        del request.session[_wizard_session_key(slug)]
        request.session.modified = True


def _get_years_list():
    year_bounds = AutoruModification.objects.aggregate(
        min_year=Min('ProductionStartYear'),
        max_year=Max('ProductionEndYear'),
    )
    min_year = year_bounds.get('min_year') or 1960
    max_year = year_bounds.get('max_year') or datetime.datetime.now().year
    current_year = datetime.datetime.now().year
    max_year = min(max_year, current_year)
    years = list(range(max_year, min_year - 1, -1))
    return years if years else list(range(current_year, 1960, -1))


def _mods_for_year(year):
    return AutoruModification.objects.filter(
        Q(ProductionStartYear__lte=year) &
        (Q(ProductionEndYear__gte=year) | Q(ProductionEndYear=2050) | Q(ProductionEndYear=0))
    )


def _build_step_context(estimation, step, title, options, selected_id='', error=''):
    step_map = {
        'year': 1,
        'mark': 2,
        'model': 3,
        'modification': 4,
        'complectation': 5,
        'details': 6,
    }
    step_index = step_map.get(step, 1)
    return {
        'estimation': estimation,
        'step': step,
        'step_index': step_index,
        'progress_percent': int((step_index / 6) * 100),
        'title': title,
        'options': options,
        'selected_id': str(selected_id) if selected_id else '',
        'error': error,
        'selected_year': estimation.year,
    }


def _build_selected_summary(estimation, state):
    mark_name = ''
    model_name = ''
    mark_id = state.get('mark_id', '')
    model_id = state.get('model_id', '')

    if mark_id:
        mark = AutoruMark.objects.filter(pk=mark_id).only('name').first()
        mark_name = mark.name if mark else ''
    if model_id:
        model = AutoruModel.objects.filter(pk=model_id).only('name').first()
        model_name = model.name if model else ''

    modification_name = estimation.modification.name if estimation.modification else ''
    complectation_name = estimation.complectation.name if estimation.complectation else ''

    return {
        'year': estimation.year or '',
        'mark': mark_name,
        'model': model_name,
        'modification': modification_name,
        'complectation': complectation_name,
    }


def user_car_estimation_year(request, slug):
    estimation = get_object_or_404(UserCarEstimation, slug=slug)
    if request.method == 'GET' and not estimation.date_opened:
        estimation.date_opened = datetime.datetime.now()
        estimation.save(update_fields=['date_opened'])

    error = ''
    if request.method == 'POST':
        year_raw = request.POST.get('selected_id', '').strip()
        try:
            year_val = int(year_raw)
            estimation.year = year_val
            estimation.modification = None
            estimation.complectation = None
            estimation.save(update_fields=['year', 'modification', 'complectation'])
            _clear_wizard_state(request, slug)
            return HttpResponseRedirect(f'/online/estimate/{slug}/mark/')
        except (TypeError, ValueError):
            error = 'Выберите корректный год.'

    options = [{'id': y, 'name': str(y)} for y in _get_years_list()]
    params = _build_step_context(estimation, 'year', 'Выберите год выпуска', options, estimation.year, error)
    params['summary'] = _build_selected_summary(estimation, _get_wizard_state(request, slug))
    return render(request, 'online/user_car_estimation_step.html', {'params': params})


def user_car_estimation_mark(request, slug):
    estimation = get_object_or_404(UserCarEstimation, slug=slug)
    if not estimation.year:
        return HttpResponseRedirect(f'/online/estimate/{slug}/year/')

    state = _get_wizard_state(request, slug)
    # Если в сессии остались значения от старого шага - очищаем их
    if state.get('model_id'):
        state['model_id'] = ''
        _set_wizard_state(request, slug, state)
    mods = _mods_for_year(int(estimation.year))
    if not mods.exists():
        mods = AutoruModification.objects.all()
    mark_ids = mods.values_list('model__mark__id', flat=True).distinct()
    marks = list(AutoruMark.objects.filter(pk__in=mark_ids).order_by('name'))
    options = [{'id': m.id, 'name': m.name} for m in marks]

    error = ''
    if request.method == 'POST':
        mark_id = request.POST.get('selected_id', '').strip()
        if not mark_id or not any(str(m['id']) == mark_id for m in options):
            error = 'Выберите марку из списка.'
        else:
            state['mark_id'] = mark_id
            state['model_id'] = ''
            _set_wizard_state(request, slug, state)
            return HttpResponseRedirect(f'/online/estimate/{slug}/model/')

    params = _build_step_context(estimation, 'mark', 'Выберите марку', options, state.get('mark_id', ''), error)
    params['summary'] = _build_selected_summary(estimation, state)
    return render(request, 'online/user_car_estimation_step.html', {'params': params})


def user_car_estimation_model(request, slug):
    estimation = get_object_or_404(UserCarEstimation, slug=slug)
    state = _get_wizard_state(request, slug)
    mark_id = state.get('mark_id')
    if not estimation.year:
        return HttpResponseRedirect(f'/online/estimate/{slug}/year/')
    if not mark_id:
        return HttpResponseRedirect(f'/online/estimate/{slug}/mark/')

    mods = _mods_for_year(int(estimation.year)).filter(model__mark_id=mark_id)
    if not mods.exists():
        mods = AutoruModification.objects.filter(model__mark_id=mark_id)
    model_ids = mods.values_list('model__id', flat=True).distinct()
    models = list(AutoruModel.objects.filter(pk__in=model_ids).order_by('name'))
    options = [{'id': m.id, 'name': m.name} for m in models]
    # Если марка невалидна для текущего года/списка, возвращаем на выбор марки
    valid_mark_ids = set(str(m.model.mark_id) for m in mods.select_related('model'))
    if str(mark_id) not in valid_mark_ids:
        state['mark_id'] = ''
        state['model_id'] = ''
        _set_wizard_state(request, slug, state)
        return HttpResponseRedirect(f'/online/estimate/{slug}/mark/')

    error = ''
    if request.method == 'POST':
        model_id = request.POST.get('selected_id', '').strip()
        if not model_id or not any(str(m['id']) == model_id for m in options):
            error = 'Выберите модель из списка.'
        else:
            state['model_id'] = model_id
            _set_wizard_state(request, slug, state)
            return HttpResponseRedirect(f'/online/estimate/{slug}/modification/')

    params = _build_step_context(estimation, 'model', 'Выберите модель', options, state.get('model_id', ''), error)
    params['summary'] = _build_selected_summary(estimation, state)
    return render(request, 'online/user_car_estimation_step.html', {'params': params})


def user_car_estimation_modification(request, slug):
    estimation = get_object_or_404(UserCarEstimation, slug=slug)
    state = _get_wizard_state(request, slug)
    model_id = state.get('model_id')
    if not estimation.year:
        return HttpResponseRedirect(f'/online/estimate/{slug}/year/')
    if not state.get('mark_id'):
        return HttpResponseRedirect(f'/online/estimate/{slug}/mark/')
    if not model_id:
        return HttpResponseRedirect(f'/online/estimate/{slug}/model/')

    mods = _mods_for_year(int(estimation.year)).filter(model_id=model_id).order_by('name')
    if not mods.exists():
        mods = AutoruModification.objects.filter(model_id=model_id).order_by('name')
    options = [{'id': m.id, 'name': m.name} for m in mods]
    # Защита от прямого перехода: модель должна соответствовать выбранной марке
    if not AutoruModel.objects.filter(pk=model_id, mark_id=state.get('mark_id')).exists():
        state['model_id'] = ''
        _set_wizard_state(request, slug, state)
        return HttpResponseRedirect(f'/online/estimate/{slug}/model/')

    error = ''
    if request.method == 'POST':
        mod_id = request.POST.get('selected_id', '').strip()
        if not mod_id or not any(str(m['id']) == mod_id for m in options):
            error = 'Выберите модификацию из списка.'
        else:
            estimation.modification = AutoruModification.objects.filter(pk=mod_id).first()
            estimation.complectation = None
            estimation.save(update_fields=['modification', 'complectation'])
            return HttpResponseRedirect(f'/online/estimate/{slug}/complectation/')

    selected_mod = estimation.modification.id if estimation.modification else ''
    params = _build_step_context(estimation, 'modification', 'Выберите модификацию', options, selected_mod, error)
    params['summary'] = _build_selected_summary(estimation, state)
    return render(request, 'online/user_car_estimation_step.html', {'params': params})


def user_car_estimation_complectation(request, slug):
    estimation = get_object_or_404(UserCarEstimation, slug=slug)
    if not estimation.modification:
        return HttpResponseRedirect(f'/online/estimate/{slug}/modification/')
    state = _get_wizard_state(request, slug)
    if not state.get('mark_id') or not state.get('model_id'):
        return HttpResponseRedirect(f'/online/estimate/{slug}/mark/')

    comps = AutoruComplectation.objects.filter(modification=estimation.modification).order_by('name')
    options = [{'id': c.id, 'name': c.name} for c in comps]

    if not options:
        estimation.complectation = None
        estimation.save(update_fields=['complectation'])
        return HttpResponseRedirect(f'/online/estimate/{slug}/details/')

    error = ''
    if request.method == 'POST':
        comp_id = request.POST.get('selected_id', '').strip()
        if comp_id and any(str(c['id']) == comp_id for c in options):
            estimation.complectation = AutoruComplectation.objects.filter(pk=comp_id).first()
            estimation.save(update_fields=['complectation'])
            return HttpResponseRedirect(f'/online/estimate/{slug}/details/')
        error = 'Выберите комплектацию из списка.'

    selected_comp = estimation.complectation.id if estimation.complectation else ''
    params = _build_step_context(estimation, 'complectation', 'Выберите комплектацию', options, selected_comp, error)
    params['summary'] = _build_selected_summary(estimation, state)
    return render(request, 'online/user_car_estimation_step.html', {'params': params})


def user_car_estimation_details(request, slug):
    estimation = get_object_or_404(UserCarEstimation, slug=slug)
    if not estimation.year:
        return HttpResponseRedirect(f'/online/estimate/{slug}/year/')
    if not estimation.modification:
        return HttpResponseRedirect(f'/online/estimate/{slug}/modification/')
    state = _get_wizard_state(request, slug)
    if not state.get('mark_id') or not state.get('model_id'):
        return HttpResponseRedirect(f'/online/estimate/{slug}/mark/')

    errors = []
    if request.method == 'POST':
        vin = request.POST.get('vin', '').strip()
        body_number = request.POST.get('body_number', '').strip()
        run_raw = request.POST.get('run', '').strip()

        if not vin and not body_number:
            errors.append("Укажите VIN или номер кузова")
        if not run_raw:
            errors.append("Укажите пробег")

        if not errors:
            estimation.vin = vin
            estimation.body_number = body_number
            estimation.run = int(run_raw)
            estimation.photo_car = request.FILES.get('photo_car') or estimation.photo_car
            estimation.photo_mileage = request.FILES.get('photo_mileage') or estimation.photo_mileage
            estimation.is_submitted = True
            estimation.date_submitted = datetime.datetime.now()
            estimation.save()
            return HttpResponseRedirect(request.build_absolute_uri())

    params = {
        'estimation': estimation,
        'step': 'details',
        'step_index': 6,
        'progress_percent': 100,
        'title': 'Финальные данные',
        'errors': errors,
        'submitted': estimation.is_submitted,
        'summary': _build_selected_summary(estimation, state),
    }
    return render(request, 'online/user_car_estimation_step.html', {'params': params})


def _validate_estimation_slug(slug):
    if not UserCarEstimation.objects.filter(slug=slug).exists():
        raise UserCarEstimation.DoesNotExist


def user_estimation_api_marks(request, slug):
    try:
        _validate_estimation_slug(slug)
        year = request.GET.get('year', '')
        if not year:
            return JsonResponse({'marks': []})
        try:
            year_int = int(year)
        except (TypeError, ValueError):
            return JsonResponse({'marks': [], 'error': 'Некорректный год'})
        modifications = AutoruModification.objects.filter(
            Q(ProductionStartYear__lte=year_int) &
            (Q(ProductionEndYear__gte=year_int) | Q(ProductionEndYear=2050) | Q(ProductionEndYear=0))
        )
        if not modifications.exists():
            # Фоллбэк: если для конкретного года нет данных, показываем доступные марки
            modifications = AutoruModification.objects.all()
        mark_ids = modifications.values_list('model__mark__id', flat=True).distinct()
        marks = AutoruMark.objects.filter(pk__in=mark_ids).order_by('name')
        return JsonResponse({'marks': [{'id': m.id, 'name': m.name} for m in marks]})
    except Exception as e:
        return JsonResponse({'marks': [], 'error': str(e)})


def user_estimation_api_models(request, slug):
    try:
        _validate_estimation_slug(slug)
        mark_id = request.GET.get('mark_id', '')
        year = request.GET.get('year', '')
        if not mark_id or not year:
            return JsonResponse({'models': []})
        try:
            year_int = int(year)
        except (TypeError, ValueError):
            return JsonResponse({'models': [], 'error': 'Некорректный год'})
        modifications = AutoruModification.objects.filter(
            model__mark_id=mark_id
        ).filter(
            Q(ProductionStartYear__lte=year_int) &
            (Q(ProductionEndYear__gte=year_int) | Q(ProductionEndYear=2050) | Q(ProductionEndYear=0))
        )
        if not modifications.exists():
            modifications = AutoruModification.objects.filter(model__mark_id=mark_id)
        model_ids = modifications.values_list('model__id', flat=True).distinct()
        models = AutoruModel.objects.filter(pk__in=model_ids).order_by('name')
        return JsonResponse({'models': [{'id': m.id, 'name': m.name} for m in models]})
    except Exception as e:
        return JsonResponse({'models': [], 'error': str(e)})


def user_estimation_api_modifications(request, slug):
    try:
        _validate_estimation_slug(slug)
        model_id = request.GET.get('model_id', '')
        year = request.GET.get('year', '')
        if not model_id or not year:
            return JsonResponse({'modifications': []})
        try:
            year_int = int(year)
        except (TypeError, ValueError):
            return JsonResponse({'modifications': [], 'error': 'Некорректный год'})
        modifications = AutoruModification.objects.filter(
            model_id=model_id
        ).filter(
            Q(ProductionStartYear__lte=year_int) &
            (Q(ProductionEndYear__gte=year_int) | Q(ProductionEndYear=2050) | Q(ProductionEndYear=0))
        ).order_by('name')
        if not modifications.exists():
            modifications = AutoruModification.objects.filter(model_id=model_id).order_by('name')
        return JsonResponse({'modifications': [{'id': m.id, 'name': m.name} for m in modifications]})
    except Exception as e:
        return JsonResponse({'modifications': [], 'error': str(e)})


def user_estimation_api_complectations(request, slug):
    try:
        _validate_estimation_slug(slug)
        modification_id = request.GET.get('modification_id', '')
        if not modification_id:
            return JsonResponse({'complectations': []})
        complectations = AutoruComplectation.objects.filter(modification_id=modification_id).order_by('name')
        return JsonResponse({'complectations': [{'id': c.id, 'name': c.name} for c in complectations]})
    except Exception as e:
        return JsonResponse({'complectations': [], 'error': str(e)})