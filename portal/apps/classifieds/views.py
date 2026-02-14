from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse, FileResponse
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.contrib import messages
from django.conf import settings
import os

from .models import (
    RefClassifiedsPlatform,
    ClassifiedsExportConfig,
    ClassifiedsExportHistory,
    ClassifiedsExportLog,
)
from .services import ClassifiedsExportService
from refs.models import RefUnit, RefStatusCarsOrganization, RefTypeExchange


@login_required
def classifieds_list(request):
    """Список настроек выгрузки"""
    search = request.GET.get('search', '')
    platform_id = request.GET.get('platform', '')
    unit_id = request.GET.get('unit', '')
    status = request.GET.get('status', '')
    
    configs = ClassifiedsExportConfig.objects.all()
    
    if search:
        configs = configs.filter(
            Q(name__icontains=search) |
            Q(platform__name__icontains=search) |
            Q(unit__name__icontains=search)
        )
    
    if platform_id:
        configs = configs.filter(platform_id=platform_id)
    
    if unit_id:
        configs = configs.filter(unit_id=unit_id)
    
    if status:
        configs = configs.filter(status=status)
    
    # Пагинация
    page_number = request.GET.get('page', 1)
    paginator = Paginator(configs.order_by('-date_create'), 25)
    page_obj = paginator.get_page(page_number)
    
    platforms = RefClassifiedsPlatform.objects.filter(is_active=True)
    units = RefUnit.objects.all().order_by('name')
    
    params = {
        'type': 'classifieds_list',
        'page_obj': page_obj,
        'platforms': platforms,
        'units': units,
        'filters': {
            'search': search,
            'platform': platform_id,
            'unit': unit_id,
            'status': status,
        }
    }
    
    return render(request, 'classifieds/list.html', {'params': params})


@login_required
def classifieds_config_detail(request, config_id):
    """Детали настройки выгрузки"""
    config = get_object_or_404(ClassifiedsExportConfig, pk=config_id)
    
    # История выгрузок
    history = ClassifiedsExportHistory.objects.filter(config=config).order_by('-date_start')[:10]
    
    # Статистика
    stats = {
        'total_exports': ClassifiedsExportHistory.objects.filter(config=config).count(),
        'success_exports': ClassifiedsExportHistory.objects.filter(config=config, status='success').count(),
        'error_exports': ClassifiedsExportHistory.objects.filter(config=config, status='error').count(),
        'total_cars_exported': ClassifiedsExportHistory.objects.filter(config=config).aggregate(
            total=Count('cars_exported')
        )['total'] or 0,
    }
    
    params = {
        'type': 'classifieds_config_detail',
        'config': config,
        'history': history,
        'stats': stats,
    }
    
    return render(request, 'classifieds/config_detail.html', {'params': params})


@login_required
def classifieds_config_create(request):
    """Создание новой настройки выгрузки"""
    if request.method == 'POST':
        # Здесь будет обработка формы создания
        # Пока заглушка
        messages.success(request, 'Настройка создана успешно')
        return redirect('classifieds:list')
    
    platforms = RefClassifiedsPlatform.objects.filter(is_active=True)
    units = RefUnit.objects.all().order_by('name')
    statuses = RefStatusCarsOrganization.objects.all().order_by('name')
    type_exchanges = RefTypeExchange.objects.all().order_by('name')
    
    params = {
        'type': 'classifieds_config_create',
        'platforms': platforms,
        'units': units,
        'statuses': statuses,
        'type_exchanges': type_exchanges,
    }
    
    return render(request, 'classifieds/config_form.html', {'params': params})


@login_required
def classifieds_config_edit(request, config_id):
    """Редактирование настройки выгрузки"""
    config = get_object_or_404(ClassifiedsExportConfig, pk=config_id)
    
    if request.method == 'POST':
        # Здесь будет обработка формы редактирования
        messages.success(request, 'Настройка обновлена успешно')
        return redirect('classifieds:config_detail', config_id=config_id)
    
    platforms = RefClassifiedsPlatform.objects.filter(is_active=True)
    units = RefUnit.objects.all().order_by('name')
    statuses = RefStatusCarsOrganization.objects.all().order_by('name')
    type_exchanges = RefTypeExchange.objects.all().order_by('name')
    
    params = {
        'type': 'classifieds_config_edit',
        'config': config,
        'platforms': platforms,
        'units': units,
        'statuses': statuses,
        'type_exchanges': type_exchanges,
    }
    
    return render(request, 'classifieds/config_form.html', {'params': params})


@login_required
def classifieds_export_run(request, config_id):
    """Запуск выгрузки"""
    config = get_object_or_404(ClassifiedsExportConfig, pk=config_id)
    
    if not config.is_active:
        messages.error(request, 'Настройка выгрузки неактивна')
        return redirect('classifieds:config_detail', config_id=config_id)
    
    try:
        service = ClassifiedsExportService(config)
        history = service.export_to_file(user=request.user)
        
        if history.status == 'success':
            messages.success(request, f'Выгрузка выполнена успешно. Выгружено автомобилей: {history.cars_exported}')
        elif history.status == 'partial':
            messages.warning(request, f'Выгрузка выполнена частично. Выгружено: {history.cars_exported}, ошибок: {history.cars_errors}')
        else:
            messages.error(request, f'Ошибка выгрузки: {history.error_message}')
        
        return redirect('classifieds:export_history_detail', history_id=history.id)
    except Exception as e:
        messages.error(request, f'Ошибка при запуске выгрузки: {str(e)}')
        return redirect('classifieds:config_detail', config_id=config_id)


@login_required
def classifieds_export_history(request):
    """История всех выгрузок"""
    search = request.GET.get('search', '')
    config_id = request.GET.get('config', '')
    status = request.GET.get('status', '')
    
    history = ClassifiedsExportHistory.objects.all()
    
    if search:
        history = history.filter(
            Q(config__name__icontains=search) |
            Q(file_name__icontains=search) |
            Q(error_message__icontains=search)
        )
    
    if config_id:
        history = history.filter(config_id=config_id)
    
    if status:
        history = history.filter(status=status)
    
    # Пагинация
    page_number = request.GET.get('page', 1)
    paginator = Paginator(history.order_by('-date_start'), 25)
    page_obj = paginator.get_page(page_number)
    
    configs = ClassifiedsExportConfig.objects.all().order_by('name')
    
    params = {
        'type': 'classifieds_export_history',
        'page_obj': page_obj,
        'configs': configs,
        'filters': {
            'search': search,
            'config': config_id,
            'status': status,
        }
    }
    
    return render(request, 'classifieds/export_history.html', {'params': params})


@login_required
def classifieds_export_history_detail(request, history_id):
    """Детали выгрузки"""
    history = get_object_or_404(ClassifiedsExportHistory, pk=history_id)
    
    # Логи выгрузки
    logs = ClassifiedsExportLog.objects.filter(export_history=history).order_by('-date_create')
    
    # Пагинация логов
    page_number = request.GET.get('page', 1)
    paginator = Paginator(logs, 50)
    page_obj = paginator.get_page(page_number)
    
    params = {
        'type': 'classifieds_export_history_detail',
        'history': history,
        'page_obj': page_obj,
    }
    
    return render(request, 'classifieds/export_history_detail.html', {'params': params})


@login_required
def classifieds_export_download(request, history_id):
    """Скачать файл выгрузки"""
    history = get_object_or_404(ClassifiedsExportHistory, pk=history_id)
    
    if not history.file_path or not history.file_name:
        messages.error(request, 'Файл выгрузки не найден')
        return redirect('classifieds:export_history_detail', history_id=history_id)
    
    # Полный путь к файлу
    file_path = os.path.join(settings.MEDIA_ROOT, history.file_path.lstrip('/'))
    
    if not os.path.exists(file_path):
        messages.error(request, 'Файл не найден на сервере')
        return redirect('classifieds:export_history_detail', history_id=history_id)
    
    try:
        response = FileResponse(open(file_path, 'rb'), content_type='application/xml')
        response['Content-Disposition'] = f'attachment; filename="{history.file_name}"'
        return response
    except Exception as e:
        messages.error(request, f'Ошибка при скачивании файла: {str(e)}')
        return redirect('classifieds:export_history_detail', history_id=history_id)


@login_required
def classifieds_preview_cars(request, config_id):
    """Предпросмотр автомобилей для выгрузки (AJAX)"""
    config = get_object_or_404(ClassifiedsExportConfig, pk=config_id)
    
    try:
        service = ClassifiedsExportService(config)
        cars = service.get_cars_queryset()
        
        cars_data = []
        for car in cars[:100]:  # Ограничиваем для предпросмотра
            cars_data.append({
                'id': car.id,
                'vin': car.vin,
                'mark': car.mark,
                'model': car.model,
                'year': car.year,
                'price': car.price,
                'run': car.run,
                'unit': car.unit.name if car.unit else '',
            })
        
        return JsonResponse({
            'success': True,
            'count': cars.count(),
            'cars': cars_data,
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=400)

