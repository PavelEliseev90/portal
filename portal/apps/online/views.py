from asyncio.windows_events import NULL
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
import datetime
from online.models import Online_doc, Records_online_doc, PersonalDataConsent
from refs.models import RefCity, RefUnit
from django.conf import settings
import json
import requests
from django.template.loader import get_template
from django.core.mail import EmailMultiAlternatives
from django.views.decorators.csrf import csrf_exempt


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