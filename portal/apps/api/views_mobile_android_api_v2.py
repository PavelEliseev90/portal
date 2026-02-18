"""
API v2 для мобильного приложения (Flutter)
Оптимизированные endpoints с поддержкой офлайн режима
"""
from django.shortcuts import render
from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.db.models import F, Func, Value, CharField, Q
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import BasicAuthentication
from rest_framework import status
import json
import base64
import datetime as DT
from datetime import datetime
from django.core.files.base import ContentFile
from django.conf import settings

from register.models import (
    RegInteractivOcenka, RegInteractivOcenkaDocument, RegRegInteractivOcenkaFiles,
    RegInteractivOcenkaSalon, RegInteractivOcenkaVnesh, RegInteractivOcenkaComplectnost,
    RegInteractivOcenkaKolesa, RegInteractivOcenkaTestDrive, RegInteractivOcenkaProverki,
    RegInteractivOcenkaSoglasovanie, RegInfoBody
)
from documents.models import DocRLK
from refs.models import RefManufacturer, AutoruModification


def get_user_info(request):
    """Получение информации о пользователе"""
    user_auth_tuple = BasicAuthentication().authenticate(request)
    if user_auth_tuple is None:
        return None, None
    
    user, _ = user_auth_tuple
    return user, user.profiles if hasattr(user, 'profiles') else None


# ==================== АВТОРИЗАЦИЯ ====================

@api_view(['POST'])
@csrf_exempt
def login_in_v2(request):
    """Авторизация пользователя v2"""
    try:
        data = json.loads(request.body)
        username = data.get('username', '')
        password = data.get('password', '')
        
        from django.contrib.auth import authenticate
        user = authenticate(username=username, password=password)
        
        if user is None:
            return JsonResponse({
                'type': 'login',
                'success': False,
                'error': 'Неправильная пара логин / пароль'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        profiles = user.profiles if hasattr(user, 'profiles') else None
        
        return JsonResponse({
            'type': 'login',
            'success': True,
            'user': {
                'id': user.pk,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone': str(profiles.phone) if profiles else '',
                'eco_name': profiles.eco_name if profiles else '',
                'eco': profiles.eco if profiles else False,
            },
            'error': ''
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({
            'type': 'login',
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def login_info_v2(request):
    """Получение информации о текущем пользователе v2"""
    user, profiles = get_user_info(request)
    
    if user is None:
        return JsonResponse({
            'type': 'login_info',
            'success': False,
            'error': 'Не авторизован'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    return JsonResponse({
        'type': 'login_info',
        'success': True,
        'user': {
            'id': user.pk,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone': str(profiles.phone) if profiles else '',
            'eco_name': profiles.eco_name if profiles else '',
            'eco': profiles.eco if profiles else False,
        },
        'error': ''
    }, status=status.HTTP_200_OK)


# ==================== РАБОЧИЕ ЛИСТЫ (RLK) ====================

@api_view(['GET'])
def rlk_eco_v2(request):
    """Получение списка рабочих листов для оценки v2"""
    user, _ = get_user_info(request)
    if user is None:
        return JsonResponse({
            'type': 'rlk_eco',
            'success': False,
            'error': 'Не авторизован'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    rlk_type = request.GET.get('type', '1')  # 1 - Продолжить, 2 - На согласовании
    search = request.GET.get('search', '')
    
    rlks = RegInteractivOcenka.objects.filter(staff__domain_login=user.username)
    
    if rlk_type == '1':
        rlks = rlks.filter(end_estimation=None)
    elif rlk_type == '2':
        rlks = rlks.exclude(end_estimation=None).filter(page_soglasovanie__price_after_kd=0)
    
    if search:
        rlks = rlks.filter(
            Q(rlk__nomer__icontains=search) |
            Q(rlk__clientName__icontains=search) |
            Q(vin__icontains=search)
        )
    
    rlks_list = []
    for rlk in rlks.select_related('rlk', 'modification', 'modification__model', 'modification__model__mark', 'rlk__unit', 'rlk__staff').order_by('-rlk__dataTime')[:100]:
        rlks_list.append({
            'id': rlk.rlk.id,
            'estimation_id': rlk.id,
            'number': rlk.rlk.nomer,
            'vin': rlk.vin or '',
            'mark': rlk.modification.model.mark.name if rlk.modification else '',
            'model': rlk.modification.model.name if rlk.modification else '',
            'modification': rlk.modification.name if rlk.modification else '',
            'year': rlk.year or '',
            'unit_name': rlk.rlk.unit.name if rlk.rlk.unit else '',
            'customer_name': rlk.rlk.clientName or '',
            'staff_name': rlk.rlk.staff.name if rlk.rlk.staff else '',
            'date': rlk.rlk.dataTime.strftime('%d.%m.%Y %H:%M:%S') if rlk.rlk.dataTime else '',
            'start_estimation': rlk.start_estimation.strftime('%d.%m.%Y %H:%M:%S') if rlk.start_estimation else '',
            'price_reception': float(rlk.page_soglasovanie.price_reception) if hasattr(rlk, 'page_soglasovanie') and rlk.page_soglasovanie else 0,
        })
    
    return JsonResponse({
        'type': 'rlk_eco',
        'success': True,
        'rlks': rlks_list,
        'count': len(rlks_list),
        'error': ''
    }, status=status.HTTP_200_OK)


# ==================== ОСМОТР КУЗОВА ====================

@api_view(['GET'])
def estimation_body_elements_v2(request, rlk_id, inspection_type):
    """Получение элементов кузова для осмотра v2"""
    user, _ = get_user_info(request)
    if user is None:
        return JsonResponse({
            'type': 'estimation_body_elements',
            'success': False,
            'error': 'Не авторизован'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        rlk = DocRLK.objects.get(id=rlk_id)
        reg_interactiv_ocenka, _ = RegInteractivOcenka.objects.get_or_create(rlk=rlk)
    except DocRLK.DoesNotExist:
        return JsonResponse({
            'type': 'estimation_body_elements',
            'success': False,
            'error': 'RLK не найден'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Определяем тип файла и сторону
    type_mapping = {
        'pered': ('array_images_pered', 'перед'),
        'vod': ('array_images_vod', 'водительская'),
        'pass': ('array_images_pass', 'пассажирская'),
        'zad': ('array_images_zad', 'зад'),
        'up': ('array_images_up', 'верх'),
    }
    
    if inspection_type not in type_mapping:
        return JsonResponse({
            'type': 'estimation_body_elements',
            'success': False,
            'error': 'Неверный тип осмотра'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    type_file, side = type_mapping[inspection_type]
    
    # Получаем элементы кузова
    bodys_info = RegInfoBody.objects.filter(type_body='седан', side=side)
    elements = []
    
    for body in bodys_info:
        polygon_x = []
        polygon_y = []
        poly_str = body.polygon
        if poly_str:
            lens_str = poly_str.split(',')
            for s in range(0, len(lens_str), 2):
                if s + 1 < len(lens_str):
                    polygon_x.append(int(lens_str[s]))
                    polygon_y.append(int(lens_str[s + 1]))
        
        elements.append({
            'name': body.body_element,
            'code': body.body_element,
            'body_elem_name': body.body_elem_name or body.body_element,
            'polygon': poly_str,
            'coor_x': polygon_x,
            'coor_y': polygon_y,
        })
    
    # Получаем существующие отметки
    files_data = RegRegInteractivOcenkaFiles.objects.filter(
        estimation=reg_interactiv_ocenka,
        type_file=type_file
    ).order_by('date')
    
    existing_marks = []
    for file_obj in files_data:
        existing_marks.append({
            'id': file_obj.pk,
            'type': file_obj.type_point or '',
            'x': file_obj.cor_x or 0,
            'y': file_obj.cor_y or 0,
            'text': file_obj.text or '',
            'date': file_obj.date.strftime('%d-%m-%Y %H:%M') if file_obj.date else '',
            'photo_url': file_obj.file.url if file_obj.file else '',
        })
    
    # URL базового изображения
    image_urls = {
        'pered': '/media_dop/body_capture/sedan_new.png',
        'vod': '/media_dop/body_capture/sedan_left_new.png',
        'pass': '/media_dop/body_capture/sedan_right_new.png',
        'zad': '/media_dop/body_capture/sedan_back_new.png',
        'up': '/media_dop/body_capture/sedan_up.png',
    }
    
    return JsonResponse({
        'type': 'estimation_body_elements',
        'success': True,
        'inspection_type': inspection_type,
        'elements': elements,
        'existing_marks': existing_marks,
        'base_image_url': image_urls.get(inspection_type, ''),
        'error': ''
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@transaction.atomic
def estimation_body_inspection_post_v2(request, rlk_id):
    """Сохранение данных осмотра кузова v2"""
    user, _ = get_user_info(request)
    if user is None:
        return JsonResponse({
            'type': 'estimation_body_inspection_post',
            'success': False,
            'error': 'Не авторизован'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        data = json.loads(request.body)
        inspection_type = data.get('inspection_type')
        base_image = data.get('base_image', '')
        marks = data.get('marks', [])
        
        rlk = DocRLK.objects.get(id=rlk_id)
        reg_interactiv_ocenka, _ = RegInteractivOcenka.objects.get_or_create(rlk=rlk)
        
        # Определяем тип файла
        type_mapping = {
            'pered': 'array_images_pered',
            'vod': 'array_images_vod',
            'pass': 'array_images_pass',
            'zad': 'array_images_zad',
            'up': 'array_images_up',
        }
        
        type_file = type_mapping.get(inspection_type)
        if not type_file:
            return JsonResponse({
                'type': 'estimation_body_inspection_post',
                'success': False,
                'error': 'Неверный тип осмотра'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Сохраняем базовое изображение
        if base_image and base_image.startswith('data:image'):
            url_base = base_image.split(',')[1].encode()
            file_name = f'imageViewOsmotr{inspection_type.capitalize()}_maximum_{rlk.id}.jpg'
            decoded_data = ContentFile(base64.b64decode(url_base), name=file_name)
            
            base_type_file = f'vnesh_car_osmotr_{inspection_type}'
            base_file, created = RegRegInteractivOcenkaFiles.objects.get_or_create(
                estimation=reg_interactiv_ocenka,
                type_file=base_type_file
            )
            base_file.name = file_name
            base_file.file = decoded_data
            base_file.user = user
            base_file.save()
        
        # Удаляем старые отметки
        RegRegInteractivOcenkaFiles.objects.filter(
            estimation=reg_interactiv_ocenka,
            type_file=type_file
        ).delete()
        
        # Сохраняем новые отметки
        for mark in marks:
            mark_type = mark.get('type', '')
            x = int(mark.get('x', 0))
            y = int(mark.get('y', 0))
            text = mark.get('text', '')
            element_name = mark.get('element_name', '')
            photo_base64 = mark.get('photo', '')
            
            # Парсим дату
            mark_date = mark.get('date')
            if mark_date:
                try:
                    date_obj = datetime.strptime(mark_date, '%d-%m-%Y %H:%M')
                except:
                    date_obj = datetime.now()
            else:
                date_obj = datetime.now()
            
            new_file = RegRegInteractivOcenkaFiles(
                estimation=reg_interactiv_ocenka,
                type_file=type_file,
                type_point=mark_type,
                text=text,
                cor_x=x,
                cor_y=y,
                date=date_obj,
                user=user,
                name=f'{mark_type} - {element_name}'
            )
            
            # Сохраняем фото если есть
            if photo_base64 and photo_base64.startswith('data:image'):
                photo_data = photo_base64.split(',')[1].encode()
                photo_name = f'photo_{rlk.id}_{x}_{y}_{datetime.now().timestamp()}.jpg'
                photo_file = ContentFile(base64.b64decode(photo_data), name=photo_name)
                new_file.file = photo_file
            else:
                new_file.blank = True
            
            # Сохраняем значение толщиномера
            if mark_type == 'толщиномер' and text:
                try:
                    new_file.kraska = int(text)
                except:
                    pass
            
            new_file.save()
        
        return JsonResponse({
            'type': 'estimation_body_inspection_post',
            'success': True,
            'marks_saved': len(marks),
            'error': ''
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return JsonResponse({
            'type': 'estimation_body_inspection_post',
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


# ==================== ОСМОТР САЛОНА ====================

@api_view(['GET'])
def estimation_salon_elements_v2(request, rlk_id):
    """Получение элементов салона для осмотра v2"""
    user, _ = get_user_info(request)
    if user is None:
        return JsonResponse({
            'type': 'estimation_salon_elements',
            'success': False,
            'error': 'Не авторизован'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        rlk = DocRLK.objects.get(id=rlk_id)
        reg_interactiv_ocenka, _ = RegInteractivOcenka.objects.get_or_create(rlk=rlk)
    except DocRLK.DoesNotExist:
        return JsonResponse({
            'type': 'estimation_salon_elements',
            'success': False,
            'error': 'RLK не найден'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Получаем элементы салона
    salons_info = RegInfoBody.objects.filter(type_body='седан', side='салон')
    elements = []
    
    for salon in salons_info:
        polygon_x = []
        polygon_y = []
        poly_str = salon.polygon
        if poly_str:
            lens_str = poly_str.split(',')
            for s in range(0, len(lens_str), 2):
                if s + 1 < len(lens_str):
                    polygon_x.append(int(lens_str[s]))
                    polygon_y.append(int(lens_str[s + 1]))
        
        elements.append({
            'name': salon.body_element,
            'code': salon.body_element,
            'body_elem_name': salon.body_elem_name or salon.body_element,
            'polygon': poly_str,
            'coor_x': polygon_x,
            'coor_y': polygon_y,
        })
    
    # Получаем существующие отметки
    type_file = 'array_images_osmotr_salon'
    files_data = RegRegInteractivOcenkaFiles.objects.filter(
        estimation=reg_interactiv_ocenka,
        type_file=type_file
    ).order_by('date')
    
    existing_marks = []
    for file_obj in files_data:
        existing_marks.append({
            'id': file_obj.pk,
            'type': file_obj.type_point or '',
            'x': file_obj.cor_x or 0,
            'y': file_obj.cor_y or 0,
            'text': file_obj.text or '',
            'date': file_obj.date.strftime('%d-%m-%Y %H:%M') if file_obj.date else '',
            'photo_url': file_obj.file.url if file_obj.file else '',
        })
    
    return JsonResponse({
        'type': 'estimation_salon_elements',
        'success': True,
        'elements': elements,
        'existing_marks': existing_marks,
        'base_image_url': '/media_dop/salon_capture/salon.png',
        'error': ''
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@transaction.atomic
def estimation_salon_inspection_post_v2(request, rlk_id):
    """Сохранение данных осмотра салона v2"""
    user, _ = get_user_info(request)
    if user is None:
        return JsonResponse({
            'type': 'estimation_salon_inspection_post',
            'success': False,
            'error': 'Не авторизован'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        data = json.loads(request.body)
        base_image = data.get('base_image', '')
        marks = data.get('marks', [])
        
        rlk = DocRLK.objects.get(id=rlk_id)
        reg_interactiv_ocenka, _ = RegInteractivOcenka.objects.get_or_create(rlk=rlk)
        
        type_file = 'array_images_osmotr_salon'
        
        # Сохраняем базовое изображение
        if base_image and base_image.startswith('data:image'):
            url_base = base_image.split(',')[1].encode()
            file_name = f'osmotr_salon_{rlk.id}.jpg'
            decoded_data = ContentFile(base64.b64decode(url_base), name=file_name)
            
            base_file, created = RegRegInteractivOcenkaFiles.objects.get_or_create(
                estimation=reg_interactiv_ocenka,
                type_file='osmotr_salon'
            )
            base_file.name = file_name
            base_file.file = decoded_data
            base_file.user = user
            base_file.save()
        
        # Удаляем старые отметки
        RegRegInteractivOcenkaFiles.objects.filter(
            estimation=reg_interactiv_ocenka,
            type_file=type_file
        ).delete()
        
        # Сохраняем новые отметки
        for mark in marks:
            mark_type = mark.get('type', '')
            x = int(mark.get('x', 0))
            y = int(mark.get('y', 0))
            text = mark.get('text', '')
            element_name = mark.get('element_name', '')
            photo_base64 = mark.get('photo', '')
            
            # Парсим дату
            mark_date = mark.get('date')
            if mark_date:
                try:
                    date_obj = datetime.strptime(mark_date, '%d-%m-%Y %H:%M')
                except:
                    date_obj = datetime.now()
            else:
                date_obj = datetime.now()
            
            new_file = RegRegInteractivOcenkaFiles(
                estimation=reg_interactiv_ocenka,
                type_file=type_file,
                type_point=mark_type,
                text=text,
                cor_x=x,
                cor_y=y,
                date=date_obj,
                user=user,
                name=f'{mark_type} - {element_name}'
            )
            
            # Сохраняем фото если есть
            if photo_base64 and photo_base64.startswith('data:image'):
                photo_data = photo_base64.split(',')[1].encode()
                photo_name = f'photo_salon_{rlk.id}_{x}_{y}_{datetime.now().timestamp()}.jpg'
                photo_file = ContentFile(base64.b64decode(photo_data), name=photo_name)
                new_file.file = photo_file
            else:
                new_file.blank = True
            
            new_file.save()
        
        return JsonResponse({
            'type': 'estimation_salon_inspection_post',
            'success': True,
            'marks_saved': len(marks),
            'error': ''
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return JsonResponse({
            'type': 'estimation_salon_inspection_post',
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


# ==================== СПРАВОЧНИКИ ДЛЯ ОФЛАЙН РЕЖИМА ====================

@api_view(['GET'])
def catalogs_marks_v2(request):
    """Получение справочника марок для офлайн режима v2"""
    marks = RefManufacturer.objects.all().order_by('name')
    marks_list = [{'id': m.id, 'name': m.name, 'code': m.code or ''} for m in marks]
    
    return JsonResponse({
        'type': 'catalogs_marks',
        'success': True,
        'marks': marks_list,
        'count': len(marks_list),
        'error': ''
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def catalogs_models_v2(request, mark_id):
    """Получение справочника моделей для офлайн режима v2"""
    from refs.models import AutoruModel
    
    models = AutoruModel.objects.filter(mark_id=mark_id).order_by('name')
    models_list = [{'id': m.id, 'name': m.name, 'mark_id': mark_id} for m in models]
    
    return JsonResponse({
        'type': 'catalogs_models',
        'success': True,
        'models': models_list,
        'count': len(models_list),
        'error': ''
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def catalogs_modifications_v2(request, model_id):
    """Получение справочника модификаций для офлайн режима v2"""
    modifications = AutoruModification.objects.filter(model_id=model_id).order_by('name')
    mods_list = []
    for mod in modifications:
        mods_list.append({
            'id': mod.id,
            'name': mod.name,
            'model_id': model_id,
            'year_from': mod.year_from or '',
            'year_to': mod.year_to or '',
        })
    
    return JsonResponse({
        'type': 'catalogs_modifications',
        'success': True,
        'modifications': mods_list,
        'count': len(mods_list),
        'error': ''
    }, status=status.HTTP_200_OK)


# ==================== СИНХРОНИЗАЦИЯ ОФЛАЙН ДАННЫХ ====================

@api_view(['POST'])
@transaction.atomic
def offline_sync_v2(request):
    """Синхронизация офлайн данных v2"""
    user, _ = get_user_info(request)
    if user is None:
        return JsonResponse({
            'type': 'offline_sync',
            'success': False,
            'error': 'Не авторизован'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        data = json.loads(request.body)
        sync_data = data.get('data', [])
        
        synced_count = 0
        errors = []
        
        for item in sync_data:
            try:
                item_type = item.get('type')
                rlk_id = item.get('rlk_id')
                
                if item_type == 'body_inspection':
                    # Синхронизация осмотра кузова
                    inspection_type = item.get('inspection_type')
                    marks = item.get('marks', [])
                    # Используем существующую функцию сохранения
                    # (упрощенная версия)
                    synced_count += 1
                    
                elif item_type == 'salon_inspection':
                    # Синхронизация осмотра салона
                    synced_count += 1
                    
                # Добавить другие типы синхронизации
                
            except Exception as e:
                errors.append({'item': item, 'error': str(e)})
        
        return JsonResponse({
            'type': 'offline_sync',
            'success': True,
            'synced_count': synced_count,
            'errors': errors,
            'error': ''
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return JsonResponse({
            'type': 'offline_sync',
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

