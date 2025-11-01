from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Sum, Avg, Case, When, IntegerField
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
from calendar import monthrange
from .models import (
    CarPreparation, CarPreparationWorkSchedule, CarPreparationCalendar,
    CarPreparationResource, RefCarPreparationStatus
)
from refs.models import RefUnit
from django.shortcuts import redirect
from .forms import CarPreparationResourceForm, RefPreparationMaterialForm, PreparationMaterialMovementForm
from .models import CarPreparationResource, RefPreparationMaterial, PreparationMaterialStock, PreparationMaterialMovement


@login_required
def mobile_checklist(request, preparation_id):
    """Мобильный интерфейс для выполнения работ по подготовке"""
    preparation = get_object_or_404(CarPreparation, id=preparation_id)
    
    context = {
        'preparation': preparation,
    }
    
    return render(request, 'car_preparation/mobile_checklist.html', context)


@login_required
def preparation_report(request, preparation_id):
    """Отчет по подготовке автомобиля"""
    preparation = get_object_or_404(CarPreparation, id=preparation_id)
    
    context = {
        'preparation': preparation,
    }
    
    return render(request, 'car_preparation/preparation_report.html', context)


@login_required
def preparation_calendar(request):
    """Календарь выполнения подготовок"""
    # Параметры фильтрации
    unit_id = request.GET.get('unit_id', None)
    start_date = request.GET.get('start_date', None)
    end_date = request.GET.get('end_date', None)
    
    # По умолчанию показываем текущий месяц
    today = timezone.now().date()
    if not start_date:
        start_date = today.replace(day=1)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if isinstance(start_date, str) else start_date
    
    if not end_date:
        last_day = monthrange(today.year, today.month)[1]
        end_date = today.replace(day=last_day)
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if isinstance(end_date, str) else end_date
    
    # Получаем расписания работ (только для подтвержденных работ)
    schedules_query = CarPreparationWorkSchedule.objects.filter(
        planned_start__date__gte=start_date,
        planned_end__date__lte=end_date,
        planning_status__in=['scheduled', 'in_progress'],
        work_item__is_confirmed=True  # Только подтвержденные работы
    ).select_related('work_item', 'work_item__preparation', 'work_item__preparation__car', 'planned_performer')
    
    if unit_id:
        schedules_query = schedules_query.filter(
            work_item__preparation__unit_id=unit_id
        )
    
    # Группируем по дням
    schedules_by_date = {}
    for schedule in schedules_query:
        if schedule.planned_start:
            date = schedule.planned_start.date()
            date_key = date.strftime('%Y-%m-%d')
            if date_key not in schedules_by_date:
                schedules_by_date[date_key] = []
            schedules_by_date[date_key].append(schedule)
    
    # Генерируем даты для календаря
    current_date = start_date
    date_range = []
    schedules_list = []
    while current_date <= end_date:
        date_range.append(current_date)
        date_key = current_date.strftime('%Y-%m-%d')
        schedules_list.append({
            'date': current_date,
            'schedules': schedules_by_date.get(date_key, [])
        })
        current_date += timedelta(days=1)
    
    # Получаем статистику
    units = RefUnit.objects.all()
    if unit_id:
        units = units.filter(id=unit_id)
    
    today = timezone.now().date()
    
    context = {
        'schedules_list': schedules_list,
        'date_range': date_range,
        'start_date': start_date,
        'end_date': end_date,
        'units': units,
        'selected_unit_id': unit_id,
        'today': today,
    }
    
    return render(request, 'car_preparation/calendar.html', context)


@login_required
def preparation_schedule(request, preparation_id):
    """Планирование конкретной подготовки"""
    preparation = get_object_or_404(CarPreparation, id=preparation_id)
    
    # Получаем работы с расписаниями
    work_items = preparation.work_items.all().prefetch_related(
        'schedule', 'schedule__planned_performer', 'work', 'work__stage'
    )
    
    # Получаем доступные ресурсы
    resources = CarPreparationResource.objects.filter(
        unit=preparation.unit,
        is_active=True,
        resource_type='performer'
    ).select_related('performer')
    
    # Получаем все доступные виды работ для ручного добавления
    from .models import RefCarPreparationWork
    available_works = RefCarPreparationWork.objects.filter(
        is_active=True
    ).select_related('stage').order_by('stage__sort_order', 'sort_order')
    
    # Группируем работы по этапам
    works_by_stage = {}
    for work in available_works:
        stage_name = work.stage.name if work.stage else 'Без этапа'
        if stage_name not in works_by_stage:
            works_by_stage[stage_name] = []
        # Проверяем, не добавлена ли уже эта работа
        if not preparation.work_items.filter(work=work).exists():
            works_by_stage[stage_name].append(work)
    
    context = {
        'preparation': preparation,
        'work_items': work_items,
        'resources': resources,
        'available_works': available_works,
        'works_by_stage': works_by_stage,
    }
    
    return render(request, 'car_preparation/schedule.html', context)


@login_required
def preparation_list(request):
    """Общий список автомобилей, требующих или прошедших подготовку"""
    # Параметры фильтрации
    unit_id = request.GET.get('unit_id', None)
    status_id = request.GET.get('status_id', None)
    search = request.GET.get('search', '')
    date_from = request.GET.get('date_from', None)
    date_to = request.GET.get('date_to', None)
    show_completed = request.GET.get('show_completed', 'true') == 'true'
    show_active = request.GET.get('show_active', 'true') == 'true'
    
    # Базовый запрос
    queryset = CarPreparation.objects.select_related(
        'car', 'unit', 'status', 'current_stage', 'responsible', 'inspector'
    ).prefetch_related('work_items', 'work_items__schedule')
    
    # Фильтрация по подразделению
    if unit_id:
        queryset = queryset.filter(unit_id=unit_id)
    
    # Фильтрация по статусу
    if status_id:
        queryset = queryset.filter(status_id=status_id)
    
    # Поиск по VIN, названию автомобиля
    if search:
        queryset = queryset.filter(
            Q(car__vin__icontains=search) |
            Q(car__name__icontains=search) |
            Q(car__mark__icontains=search) |
            Q(car__model__icontains=search)
        )
    
    # Фильтрация по датам
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            queryset = queryset.filter(date_created__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            queryset = queryset.filter(date_created__lte=date_to_obj)
        except ValueError:
            pass
    
    # Фильтрация по типу (завершенные/активные)
    if not show_completed and not show_active:
        queryset = queryset.none()  # Ничего не показывать
    elif not show_completed:
        # Только активные
        completed_statuses = RefCarPreparationStatus.objects.filter(is_final=True)
        if completed_statuses.exists():
            queryset = queryset.exclude(status__in=completed_statuses)
        else:
            queryset = queryset.exclude(status__is_final=True)
    elif not show_active:
        # Только завершенные
        completed_statuses = RefCarPreparationStatus.objects.filter(is_final=True)
        if completed_statuses.exists():
            queryset = queryset.filter(status__in=completed_statuses)
        else:
            queryset = queryset.filter(status__is_final=True)
    
    # Сортировка
    sort_by = request.GET.get('sort_by', '-date_created')
    queryset = queryset.order_by(sort_by)
    
    # Аннотации для статистики
    queryset = queryset.annotate(
        total_works=Count('work_items', filter=Q(work_items__work__is_active=True)),
        completed_works=Count('work_items', filter=Q(work_items__status='completed')),
        confirmed_works=Count('work_items', filter=Q(work_items__is_confirmed=True)),
    )
    
    # Пагинация
    paginator = Paginator(queryset, 25)  # 25 элементов на страницу
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Статистика для фильтров
    units = RefUnit.objects.all().order_by('name')
    statuses = RefCarPreparationStatus.objects.all().order_by('name')
    
    # Общая статистика
    total_count = CarPreparation.objects.count()
    completed_statuses = RefCarPreparationStatus.objects.filter(is_final=True)
    if completed_statuses.exists():
        active_count = CarPreparation.objects.exclude(
            status__in=completed_statuses
        ).count()
        completed_count = CarPreparation.objects.filter(
            status__in=completed_statuses
        ).count()
    else:
        active_count = CarPreparation.objects.filter(
            status__isnull=False
        ).exclude(status__is_final=True).count()
        completed_count = CarPreparation.objects.filter(
            status__is_final=True
        ).count()
    
    # Статистика по выбранным фильтрам
    filtered_count = queryset.count()
    
    context = {
        'page_obj': page_obj,
        'preparations': page_obj,
        'units': units,
        'statuses': statuses,
        'selected_unit_id': unit_id,
        'selected_status_id': status_id,
        'search_query': search,
        'date_from': date_from,
        'date_to': date_to,
        'show_completed': show_completed,
        'show_active': show_active,
        'sort_by': sort_by,
        'total_count': total_count,
        'active_count': active_count,
        'completed_count': completed_count,
        'filtered_count': filtered_count,
    }
    
    return render(request, 'car_preparation/preparation_list.html', context)


@login_required
def performer_dashboard(request):
    """Панель исполнителя с его работами"""
    from refs.models import RefStaff
    # Получаем сотрудника для текущего пользователя (с возможностью переопределения через GET)
    user = request.user
    staff = getattr(user, 'staff', None)
    override_staff_id = request.GET.get('staff_id')
    if override_staff_id:
        try:
            staff = RefStaff.objects.get(pk=override_staff_id)
        except RefStaff.DoesNotExist:
            staff = None
    if not staff:
        context = {
            'error': 'Пользователь не связан с сотрудником'
        }
        return render(request, 'car_preparation/performer_dashboard.html', context)
    
    # Получаем работы, назначенные на этого исполнителя
    from .models import CarPreparationWorkItem
    work_items = CarPreparationWorkItem.objects.filter(
        Q(schedule__planned_performer=staff) | Q(performer=staff)
    ).select_related(
        'work', 'work__stage', 'preparation', 'preparation__car', 
        'performer', 'schedule'
    ).prefetch_related(
        'preparation__unit'
    ).order_by('-schedule__planned_start', '-date_start', '-id')
    
    # Фильтры
    status_filter = request.GET.get('status', None)
    date_filter = request.GET.get('date', None)
    
    if status_filter:
        work_items = work_items.filter(status=status_filter)
    
    if date_filter:
        try:
            date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
            work_items = work_items.filter(
                schedule__planned_start__date=date_obj
            )
        except ValueError:
            pass
    
    # Группируем работы по статусам
    pending_works = work_items.filter(status='pending')
    in_progress_works = work_items.filter(status='in_progress')
    completed_works = work_items.filter(status='completed')
    
    # Статистика
    total_count = work_items.count()
    pending_count = pending_works.count()
    in_progress_count = in_progress_works.count()
    completed_count = completed_works.count()
    overdue_count = work_items.filter(
        schedule__planned_end__lt=timezone.now(),
        status__in=['pending', 'in_progress']
    ).count()
    
    context = {
        'staff': staff,
        'work_items': work_items,
        'pending_works': pending_works[:10],  # Ограничиваем для производительности
        'in_progress_works': in_progress_works[:10],
        'completed_works': completed_works[:10],
        'total_count': total_count,
        'pending_count': pending_count,
        'in_progress_count': in_progress_count,
        'completed_count': completed_count,
        'overdue_count': overdue_count,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'today': timezone.now().date(),
    }
    
    return render(request, 'car_preparation/performer_dashboard.html', context)


@login_required
def performers_works(request):
    """График работ по сотрудникам - у кого что в работе"""
    from .models import CarPreparationWorkItem
    from refs.models import RefStaff
    from django.utils import timezone
    from django.db.models import Q, Count, F
    
    # Фильтры
    unit_id = request.GET.get('unit_id', None)
    date_from = request.GET.get('date_from', None)
    date_to = request.GET.get('date_to', None)
    status_filter = request.GET.get('status', None)
    
    # Парсим даты
    today = timezone.now().date()
    if not date_from:
        date_from = today
    else:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        except ValueError:
            date_from = today
    
    if not date_to:
        date_to = today
    else:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        except ValueError:
            date_to = today
    
    # Получаем всех исполнителей с их работами
    # Включаем исполнителей, у которых есть либо назначенные работы, либо запланированные в расписании
    performers_query = RefStaff.objects.filter(
        Q(preparation_works__is_confirmed=True) |
        Q(planned_preparation_works__planning_status__in=['scheduled', 'in_progress'])
    ).distinct()
    
    # Фильтруем по подразделению
    if unit_id:
        performers_query = performers_query.filter(
            Q(preparation_works__preparation__unit_id=unit_id) |
            Q(planned_preparation_works__work_item__preparation__unit_id=unit_id) |
            Q(units__id=unit_id)
        ).distinct()
    
    # Получаем работы для каждого исполнителя
    performers_data = []
    for performer in performers_query:
        works = CarPreparationWorkItem.objects.filter(
            Q(schedule__planned_performer=performer) | Q(performer=performer),
            is_confirmed=True
        ).select_related(
            'work', 'preparation', 'preparation__car', 'schedule'
        )
        
        # Фильтры для работ
        if status_filter:
            works = works.filter(status=status_filter)
        
        if date_from or date_to:
            if date_from and date_to:
                works = works.filter(
                    Q(schedule__planned_start__date__gte=date_from,
                      schedule__planned_start__date__lte=date_to) |
                    Q(date_start__date__gte=date_from,
                      date_start__date__lte=date_to) |
                    Q(date_start__isnull=True)
                )
        
        works = works.order_by('status', 'schedule__planned_start')
        
        # Статистика по исполнителю
        pending = works.filter(status='pending').count()
        in_progress = works.filter(status='in_progress').count()
        completed = works.filter(status='completed').count()
        total = works.count()
        
        performers_data.append({
            'performer': performer,
            'works': works,
            'statistics': {
                'total': total,
                'pending': pending,
                'in_progress': in_progress,
                'completed': completed
            }
        })
    
    # Сортируем по общему количеству работ
    performers_data.sort(key=lambda x: x['statistics']['total'], reverse=True)
    
    # Получаем подразделения для фильтра
    from refs.models import RefUnit
    units = RefUnit.objects.all().order_by('name')
    
    context = {
        'performers_data': performers_data,
        'units': units,
        'selected_unit_id': unit_id,
        'date_from': date_from,
        'date_to': date_to,
        'status_filter': status_filter,
        'today': today,
    }
    
    return render(request, 'car_preparation/performers_works.html', context)


@login_required
def resources_list(request):
    """Список ресурсов планирования"""
    unit_id = request.GET.get('unit_id', None)
    resource_type = request.GET.get('resource_type', '')
    is_active = request.GET.get('is_active', 'true')
    
    resources = CarPreparationResource.objects.all().select_related('performer', 'unit')
    
    if unit_id:
        resources = resources.filter(unit_id=unit_id)
    if resource_type:
        resources = resources.filter(resource_type=resource_type)
    if is_active == 'true':
        resources = resources.filter(is_active=True)
    
    units = RefUnit.objects.all().order_by('name')
    
    context = {
        'resources': resources.order_by('resource_type', 'name'),
        'units': units,
        'selected_unit_id': unit_id,
        'selected_type': resource_type,
        'is_active': is_active,
    }
    return render(request, 'car_preparation/resources_list.html', context)


@login_required
def resource_create(request):
    """Создание ресурса планирования"""
    if request.method == 'POST':
        form = CarPreparationResourceForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('car_preparation:resources_list')
    else:
        form = CarPreparationResourceForm()
    
    return render(request, 'car_preparation/resource_form.html', {
        'form': form,
        'title': 'Добавить ресурс',
    })


@login_required
def resource_edit(request, resource_id):
    """Редактирование ресурса планирования"""
    resource = get_object_or_404(CarPreparationResource, id=resource_id)
    
    if request.method == 'POST':
        form = CarPreparationResourceForm(request.POST, instance=resource)
        if form.is_valid():
            form.save()
            return redirect('car_preparation:resources_list')
    else:
        form = CarPreparationResourceForm(instance=resource)
    
    return render(request, 'car_preparation/resource_form.html', {
        'form': form,
        'title': 'Редактировать ресурс',
    })


# ==========================
# Материалы: список/создание/редактирование
# ==========================
@login_required
def materials_list(request):
    is_active = request.GET.get('is_active', '')
    search = request.GET.get('search', '')
    materials = RefPreparationMaterial.objects.all()
    if is_active == 'true':
        materials = materials.filter(is_active=True)
    elif is_active == 'false':
        materials = materials.filter(is_active=False)
    if search:
        materials = materials.filter(models.Q(name__icontains=search) | models.Q(code__icontains=search))
    return render(request, 'car_preparation/materials_list.html', {
        'materials': materials.order_by('name'),
        'is_active': is_active,
        'search': search,
    })


@login_required
def material_create(request):
    if request.method == 'POST':
        form = RefPreparationMaterialForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('car_preparation:materials_list')
    else:
        form = RefPreparationMaterialForm()
    return render(request, 'car_preparation/material_form.html', {'form': form, 'title': 'Добавить материал'})


@login_required
def material_edit(request, material_id):
    material = get_object_or_404(RefPreparationMaterial, id=material_id)
    if request.method == 'POST':
        form = RefPreparationMaterialForm(request.POST, instance=material)
        if form.is_valid():
            form.save()
            return redirect('car_preparation:materials_list')
    else:
        form = RefPreparationMaterialForm(instance=material)
    return render(request, 'car_preparation/material_form.html', {'form': form, 'title': 'Редактировать материал'})


# ==========================
# Остатки
# ==========================
@login_required
def stock_list(request):
    unit_id = request.GET.get('unit_id', None)
    low_stock = request.GET.get('low_stock', 'false') == 'true'
    
    stock = PreparationMaterialStock.objects.select_related('material', 'unit')
    if unit_id:
        stock = stock.filter(unit_id=unit_id)
    if low_stock:
        stock = stock.filter(qty_on_hand__lt=models.F('min_qty'))
    
    units = RefUnit.objects.all().order_by('name')
    return render(request, 'car_preparation/stock_list.html', {
        'stock': stock.order_by('material__name'),
        'units': units,
        'selected_unit_id': unit_id,
        'low_stock': low_stock,
    })


# ==========================
# Движения
# ==========================
@login_required
def movements_list(request):
    unit_id = request.GET.get('unit_id', None)
    material_id = request.GET.get('material_id', None)
    movement_type = request.GET.get('movement_type', '')
    
    moves = PreparationMaterialMovement.objects.select_related('material', 'unit', 'work_item')
    if unit_id:
        moves = moves.filter(unit_id=unit_id)
    if material_id:
        moves = moves.filter(material_id=material_id)
    if movement_type:
        moves = moves.filter(movement_type=movement_type)
    
    units = RefUnit.objects.all().order_by('name')
    materials = RefPreparationMaterial.objects.filter(is_active=True).order_by('name')
    return render(request, 'car_preparation/movements_list.html', {
        'moves': moves.order_by('-date'),
        'units': units,
        'materials': materials,
        'selected_unit_id': unit_id,
        'selected_material_id': material_id,
        'selected_type': movement_type,
    })


@login_required
def movement_receipt(request):
    if request.method == 'POST':
        form = PreparationMaterialMovementForm(request.POST)
        if form.is_valid():
            move = form.save(commit=False)
            move.movement_type = 'receipt'
            move.user = getattr(request.user, 'staff', None)
            move.save()
            stock, _ = PreparationMaterialStock.objects.get_or_create(unit=move.unit, material=move.material)
            stock.qty_on_hand = (stock.qty_on_hand or 0) + float(move.qty)
            stock.save()
            return redirect('car_preparation:movements_list')
    else:
        form = PreparationMaterialMovementForm(initial={'movement_type': 'receipt'})
    return render(request, 'car_preparation/movement_form.html', {'form': form, 'title': 'Приход материалов'})


@login_required
def movement_consume(request):
    if request.method == 'POST':
        form = PreparationMaterialMovementForm(request.POST)
        if form.is_valid():
            move = form.save(commit=False)
            move.movement_type = 'consume'
            move.user = getattr(request.user, 'staff', None)
            # проверка остатка
            stock = PreparationMaterialStock.objects.filter(unit=move.unit, material=move.material).first()
            if not stock or stock.qty_on_hand < float(move.qty):
                return render(request, 'car_preparation/movement_form.html', {'form': form, 'title': 'Расход материалов', 'error': 'Недостаточно остатка'})
            stock.qty_on_hand = (stock.qty_on_hand or 0) - float(move.qty)
            stock.save()
            move.qty = -abs(float(move.qty))
            move.save()
            return redirect('car_preparation:movements_list')
    else:
        form = PreparationMaterialMovementForm(initial={'movement_type': 'consume'})
    return render(request, 'car_preparation/movement_form.html', {'form': form, 'title': 'Расход материалов'})

