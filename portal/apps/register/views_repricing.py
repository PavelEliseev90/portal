"""
Views для управления переоценкой автомобилей
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from datetime import datetime

from .models import RegCarsRepricingHistory, RegCarsRepricingLog
from refs.models import RefUnit, RefCarsOrganization, RefTypeEvaluationCarsOrganization
from .services_repricing import CarsRepricingService


@login_required
def repricing_list(request):
    """Список истории переоценок"""
    search = request.GET.get('search', '')
    unit_id = request.GET.get('unit', '')
    status = request.GET.get('status', '')
    evaluation_id = request.GET.get('evaluation', '')
    
    history = RegCarsRepricingHistory.objects.all()
    
    if search:
        history = history.filter(
            Q(unit__name__icontains=search) |
            Q(error_message__icontains=search)
        )
    
    if unit_id:
        history = history.filter(unit_id=unit_id)
    
    if status:
        history = history.filter(status=status)
    
    if evaluation_id:
        history = history.filter(evaluation_id=evaluation_id)
    
    # Пагинация
    page_number = request.GET.get('page', 1)
    paginator = Paginator(history.order_by('-date_start'), 25)
    page_obj = paginator.get_page(page_number)
    
    units = RefUnit.objects.all().order_by('name')
    evaluations = RefTypeEvaluationCarsOrganization.objects.all().order_by('name')
    
    params = {
        'type': 'repricing_list',
        'page_obj': page_obj,
        'units': units,
        'evaluations': evaluations,
        'filters': {
            'search': search,
            'unit': unit_id,
            'status': status,
            'evaluation': evaluation_id,
        }
    }
    
    return render(request, 'register/repricing_list.html', {'params': params})


@login_required
def repricing_history_detail(request, history_id):
    """Детали переоценки"""
    history = get_object_or_404(RegCarsRepricingHistory, pk=history_id)
    
    # Логи переоценки
    logs = RegCarsRepricingLog.objects.filter(repricing_history=history).order_by('-date_create')
    
    # Пагинация логов
    page_number = request.GET.get('page', 1)
    paginator = Paginator(logs, 50)
    page_obj = paginator.get_page(page_number)
    
    params = {
        'type': 'repricing_history_detail',
        'history': history,
        'page_obj': page_obj,
    }
    
    return render(request, 'register/repricing_history_detail.html', {'params': params})


@login_required
def repricing_run(request, unit_id=None):
    """Запуск переоценки автомобилей"""
    evaluation_id = request.GET.get('evaluation', '')
    
    unit = None
    if unit_id:
        unit = get_object_or_404(RefUnit, pk=unit_id)
    
    evaluation = None
    if evaluation_id:
        evaluation = get_object_or_404(RefTypeEvaluationCarsOrganization, pk=evaluation_id)
    
    try:
        service = CarsRepricingService(unit=unit, evaluation=evaluation)
        history = service.run_repricing(user=request.user)
        
        if history.status == 'success':
            messages.success(request, f'Переоценка выполнена успешно. Обработано автомобилей: {history.cars_processed}, обновлено цен: {history.cars_updated}')
        elif history.status == 'partial':
            messages.warning(request, f'Переоценка выполнена частично. Обработано: {history.cars_processed}, обновлено: {history.cars_updated}, ошибок: {history.cars_errors}')
        else:
            messages.error(request, f'Ошибка переоценки: {history.error_message}')
        
        return redirect('register:repricing_history_detail', history_id=history.id)
    except Exception as e:
        messages.error(request, f'Ошибка при запуске переоценки: {str(e)}')
        return redirect('register:repricing_list')


@login_required
def repricing_units(request):
    """Список подразделений для запуска переоценки"""
    units = RefUnit.objects.all().order_by('name')
    evaluations = RefTypeEvaluationCarsOrganization.objects.all().order_by('name')
    
    # Статистика по последним переоценкам
    units_stats = []
    for unit in units:
        last_repricing = RegCarsRepricingHistory.objects.filter(unit=unit).order_by('-date_start').first()
        stats = {
            'unit': unit,
            'last_repricing': last_repricing,
            'total_repricings': RegCarsRepricingHistory.objects.filter(unit=unit).count(),
            'success_repricings': RegCarsRepricingHistory.objects.filter(unit=unit, status='success').count(),
        }
        units_stats.append(stats)
    
    params = {
        'type': 'repricing_units',
        'units_stats': units_stats,
        'evaluations': evaluations,
    }
    
    return render(request, 'register/repricing_units.html', {'params': params})


@login_required
def repricing_preview_cars(request, unit_id=None):
    """Предпросмотр автомобилей для переоценки (AJAX)"""
    evaluation_id = request.GET.get('evaluation', '')
    
    unit = None
    if unit_id:
        unit = get_object_or_404(RefUnit, pk=unit_id)
    
    evaluation = None
    if evaluation_id:
        evaluation = get_object_or_404(RefTypeEvaluationCarsOrganization, pk=evaluation_id)
    
    try:
        service = CarsRepricingService(unit=unit, evaluation=evaluation)
        cars = service.get_cars_for_repricing()
        
        cars_data = []
        for car in cars[:100]:  # Ограничиваем для предпросмотра
            cars_data.append({
                'id': car.id,
                'vin': car.vin,
                'mark': car.mark,
                'model': car.model,
                'year': car.year,
                'price': car.price,
                'evaluation': car.evaluation.name if car.evaluation else '',
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

