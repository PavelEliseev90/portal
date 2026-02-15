from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Sum, Avg, Case, When, IntegerField, F, ExpressionWrapper, DurationField
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse
from datetime import datetime, timedelta
from calendar import monthrange
import json
from .models import (
    CarPreparation, CarPreparationWorkSchedule, CarPreparationCalendar,
    CarPreparationResource, RefCarPreparationStatus, WorkOrder, WorkOrderItem,
    WorkOrderTemplate, RefRepairZone, WorkOrderItemPhoto, WorkOrderItemMaterial,
    RefCarPreparationStage, RefCarPreparationWork, RefPreparationMaterial,
    CarPreparationComment, CarPreparationCommentFile
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
    """Планирование конкретной подготовки с системой заказ-нарядов"""
    from .models import (RefCarPreparationWork, WorkOrderTemplate, RefRepairZone, 
                        WorkOrder, WorkOrderItem, CarPreparationResource)
    from django.contrib.auth.models import User
    
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
    
    # Получаем шаблоны заказ-нарядов
    templates = WorkOrderTemplate.objects.filter(is_active=True).prefetch_related('works')
    
    # Получаем ремонтные зоны
    repair_zones = RefRepairZone.objects.filter(
        is_active=True,
        unit=preparation.unit
    ).order_by('sort_order', 'name')
    
    # Получаем существующие заказ-наряды по этой подготовке
    work_orders = WorkOrder.objects.filter(
        preparation=preparation
    ).prefetch_related('items__work', 'items__performer', 'repair_zone').order_by('-date_created')
    
    # Получаем всех исполнителей
    performers = User.objects.filter(is_active=True).order_by('username')
    
    # Группируем работы подготовки по этапам для удобного отображения
    preparation_works_by_stage = {}
    for work_item in work_items:
        stage_name = work_item.work.stage.name if work_item.work and work_item.work.stage else 'Без этапа'
        if stage_name not in preparation_works_by_stage:
            preparation_works_by_stage[stage_name] = []
        preparation_works_by_stage[stage_name].append(work_item)
    
    # Получаем комментарии к подготовке
    comments = CarPreparationComment.objects.filter(
        preparation=preparation,
        is_deleted=False
    ).select_related('author').prefetch_related('files').order_by('-date_created')
    
    # Получаем данные интерактивной оценки для автомобиля
    interactive_estimation = None
    body_inspection = None
    interior_inspection = None
    diagnostics = None
    
    try:
        from register.models import RegInteractivOcenka, RegInteractivOcenkaRLK
        from documents.models import DocRLK
        
        # Ищем через DocRLK по автомобилю
        rlk = DocRLK.objects.filter(car=preparation.car).order_by('-id').first()
        if rlk:
            # Пробуем через RegInteractivOcenkaRLK
            estimation_rlk = RegInteractivOcenkaRLK.objects.filter(rlk=rlk).select_related('estimation').first()
            if estimation_rlk and estimation_rlk.estimation:
                interactive_estimation = estimation_rlk.estimation
            else:
                # Пробуем напрямую через RegInteractivOcenka по rlk
                interactive_estimation = RegInteractivOcenka.objects.filter(
                    rlk=rlk
                ).order_by('-id').first()
        
        # Если не нашли через RLK, пробуем по VIN
        if not interactive_estimation and preparation.car.vin:
            interactive_estimation = RegInteractivOcenka.objects.filter(
                vin=preparation.car.vin
            ).order_by('-id').first()
        
        if interactive_estimation:
            body_inspection = interactive_estimation.page_vnesh
            interior_inspection = interactive_estimation.page_salon
            diagnostics = interactive_estimation.page_test_drive
    except Exception as e:
        # Если импорт не удался или нет данных - просто пропускаем
        import traceback
        print(f"Ошибка получения данных интерактивной оценки: {e}")
        print(traceback.format_exc())
    
    context = {
        'preparation': preparation,
        'work_items': work_items,
        'preparation_works_by_stage': preparation_works_by_stage,
        'resources': resources,
        'available_works': available_works,
        'works_by_stage': works_by_stage,
        'templates': templates,
        'repair_zones': repair_zones,
        'work_orders': work_orders,
        'performers': performers,
        'comments': comments,
        'interactive_estimation': interactive_estimation,
        'body_inspection': body_inspection,
        'interior_inspection': interior_inspection,
        'diagnostics': diagnostics,
    }
    
    return render(request, 'car_preparation/schedule_new.html', context)


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
        materials = materials.filter(Q(name__icontains=search) | Q(code__icontains=search))
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
        stock = stock.filter(qty_on_hand__lt=F('min_qty'))
    
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


# ===========================================
# СИСТЕМА ЗАКАЗ-НАРЯДОВ
# ===========================================

@login_required
def work_order_create(request, preparation_id):
    """Создание заказ-наряда из корзины работ"""
    from .models import RefCarPreparationWork
    from django.contrib.auth.models import User
    
    preparation = get_object_or_404(CarPreparation, id=preparation_id)
    
    if request.method == 'POST':
        try:
            # Получаем данные из запроса (поддержка FormData и JSON)
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                work_ids = data.get('work_ids', [])
                template_id = data.get('template_id')
                planned_start_str = data.get('planned_start')
                planned_end_str = data.get('planned_end')
                repair_zone_id = data.get('repair_zone_id')
                title = data.get('title', '')
                description = data.get('description', '')
            else:
                work_ids = request.POST.getlist('work_ids[]')
                template_id = request.POST.get('template_id') or None
                planned_start_str = request.POST.get('planned_start')
                planned_end_str = request.POST.get('planned_end')
                repair_zone_id = request.POST.get('repair_zone_id') or None
                title = request.POST.get('title', '')
                description = request.POST.get('description', '')
            
            if not work_ids:
                return JsonResponse({'success': False, 'error': 'Не выбрано ни одной работы'}, status=400)
            
            # Парсим даты
            planned_start = None
            planned_end = None
            if planned_start_str:
                try:
                    # Формат: YYYY-MM-DDTHH:MM
                    planned_start = datetime.strptime(planned_start_str, '%Y-%m-%dT%H:%M')
                    if timezone.is_naive(planned_start):
                        planned_start = timezone.make_aware(planned_start)
                except:
                    pass
            if planned_end_str:
                try:
                    planned_end = datetime.strptime(planned_end_str, '%Y-%m-%dT%H:%M')
                    if timezone.is_naive(planned_end):
                        planned_end = timezone.make_aware(planned_end)
                except:
                    pass
            
            # Создаем заказ-наряд
            work_order = WorkOrder.objects.create(
                car=preparation.car,
                preparation=preparation,
                template_id=int(template_id) if template_id else None,
                repair_zone_id=int(repair_zone_id) if repair_zone_id else None,
                title=title or 'Заказ-наряд',
                description=description,
                planned_start=planned_start,
                planned_end=planned_end,
                status='scheduled',
                created_by=getattr(request.user, 'staff', None),
                date_created=timezone.now()
            )
            
            # Добавляем работы в заказ-наряд
            sort_order = 0
            for work_id in work_ids:
                try:
                    work = RefCarPreparationWork.objects.get(id=int(work_id))
                    WorkOrderItem.objects.create(
                        work_order=work_order,
                        work=work,
                        sort_order=sort_order,
                        status='pending',
                        planned_start=planned_start,
                        planned_end=planned_end
                    )
                    sort_order += 1
                except (RefCarPreparationWork.DoesNotExist, ValueError):
                    continue
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'work_order_id': work_order.id,
                    'work_order_number': work_order.number,
                    'message': 'Заказ-наряд создан успешно'
                })
            
            return redirect('car_preparation:schedule', preparation_id=preparation_id)
            
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=400)
            raise
    
    return JsonResponse({'success': False, 'error': 'Метод не разрешен'}, status=405)


@login_required
def work_order_timeline(request, car_id):
    """Таймлайн заказ-нарядов по автомобилю"""
    from refs.models import RefCarsOrganization
    
    car = get_object_or_404(RefCarsOrganization, id=car_id)
    
    # Получаем все заказ-наряды по автомобилю
    work_orders = WorkOrder.objects.filter(car=car).prefetch_related(
        'items__work', 'items__performer', 'items__photos', 'repair_zone'
    ).order_by('planned_start', 'date_created')
    
    context = {
        'car': car,
        'work_orders': work_orders,
    }
    
    return render(request, 'car_preparation/work_order_timeline.html', context)


@login_required
def work_order_item_start(request, item_id):
    """Начало выполнения работы в заказ-наряде"""
    item = get_object_or_404(WorkOrderItem, id=item_id)
    
    if request.method == 'POST':
        if item.status == 'completed':
            return JsonResponse({'success': False, 'error': 'Работа уже выполнена'}, status=400)
        
        item.status = 'in_progress'
        item.actual_start = timezone.now()
        if not item.performer:
            item.performer = getattr(request.user, 'staff', None)
        item.save()
        
        # Обновляем статус заказ-наряда
        work_order = item.work_order
        if work_order.status == 'scheduled':
            work_order.status = 'in_progress'
            work_order.actual_start = timezone.now()
            work_order.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Работа начата',
            'actual_start': item.actual_start.strftime('%d.%m.%Y %H:%M') if item.actual_start else ''
        })
    
    return JsonResponse({'success': False, 'error': 'Метод не разрешен'}, status=405)


@login_required
def work_order_item_complete(request, item_id):
    """Завершение работы в заказ-наряде"""
    item = get_object_or_404(WorkOrderItem, id=item_id)
    
    if request.method == 'POST':
        if item.status == 'completed':
            return JsonResponse({'success': False, 'error': 'Работа уже выполнена'}, status=400)
        
        item.status = 'completed'
        item.actual_end = timezone.now()
        item.save()
        
        # Проверяем, все ли работы выполнены
        work_order = item.work_order
        all_completed = work_order.items.exclude(status='completed').count() == 0
        
        if all_completed:
            work_order.status = 'completed'
            work_order.actual_end = timezone.now()
            work_order.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Работа завершена',
            'actual_end': item.actual_end.strftime('%d.%m.%Y %H:%M') if item.actual_end else '',
            'work_order_completed': all_completed
        })
    
    return JsonResponse({'success': False, 'error': 'Метод не разрешен'}, status=405)


@login_required
def work_order_item_photo_upload(request, item_id):
    """Загрузка фотографии к работе в заказ-наряде"""
    item = get_object_or_404(WorkOrderItem, id=item_id)
    
    if request.method == 'POST':
        uploaded_file = request.FILES.get('photo')
        description = request.POST.get('description', '')
        
        if not uploaded_file:
            return JsonResponse({'success': False, 'error': 'Файл не выбран'}, status=400)
        
        # Ограничение размера файла (10 МБ)
        max_size = 10 * 1024 * 1024  # 10 МБ
        if uploaded_file.size > max_size:
            return JsonResponse({'success': False, 'error': 'Размер файла превышает 10 МБ'}, status=400)
        
        # Создаем запись о фотографии
        photo = WorkOrderItemPhoto.objects.create(
            work_order_item=item,
            photo=uploaded_file,
            description=description,
            created_by=getattr(request.user, 'staff', None),
            date_created=timezone.now()
        )
        
        return JsonResponse({
            'success': True,
            'photo': {
                'id': photo.id,
                'url': photo.photo.url if photo.photo else '',
                'description': photo.description,
                'date': photo.date_created.strftime('%d.%m.%Y %H:%M') if photo.date_created else '',
            }
        })
    
    return JsonResponse({'success': False, 'error': 'Метод не разрешен'}, status=405)


@login_required
def work_order_detail(request, work_order_id):
    """Детали заказ-наряда"""
    from django.contrib.auth.models import User
    
    work_order = get_object_or_404(WorkOrder.objects.prefetch_related(
        'items__work', 'items__performer', 'items__photos__created_by', 
        'items__materials__material', 'repair_zone'
    ), id=work_order_id)
    
    performers = User.objects.filter(is_active=True).order_by('username')
    materials = RefPreparationMaterial.objects.filter(is_active=True).order_by('name')
    
    # Общая стоимость материалов по заказ-наряду
    total_materials_cost = WorkOrderItemMaterial.objects.filter(
        work_order_item__work_order=work_order
    ).aggregate(total=Sum('total_price'))['total'] or 0
    
    context = {
        'work_order': work_order,
        'performers': performers,
        'materials': materials,
        'total_materials_cost': total_materials_cost,
    }
    
    return render(request, 'car_preparation/work_order_detail.html', context)


@login_required
def work_order_template_works(request, template_id):
    """API: Получение работ из шаблона заказ-наряда"""
    template = get_object_or_404(WorkOrderTemplate, id=template_id)
    
    works = template.works.all().select_related('stage').order_by('workordertemplatework__sort_order')
    
    works_data = []
    for work in works:
        template_work = template.workordertemplatework_set.get(work=work)
        works_data.append({
            'id': work.id,
            'name': work.name,
            'estimated_time': template_work.estimated_time or work.estimated_time or 0,
            'stage': work.stage.name if work.stage else 'Без этапа',
            'is_required': template_work.is_required,
        })
    
    return JsonResponse({
        'success': True,
        'works': works_data,
        'template_name': template.name,
        'estimated_duration': template.estimated_duration_minutes,
    })


@login_required
def preparation_comment_update(request, preparation_id):
    """Обновление комментария к подготовке (старые поля)"""
    preparation = get_object_or_404(CarPreparation, id=preparation_id)
    
    if request.method == 'POST':
        comment_type = request.POST.get('comment_type', 'comment_initial')
        comment_text = request.POST.get('comment', '').strip()
        
        if comment_type == 'comment_initial':
            preparation.comment_initial = comment_text
        elif comment_type == 'comment_final':
            preparation.comment_final = comment_text
        elif comment_type == 'quality_notes':
            preparation.quality_notes = comment_text
        
        preparation.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Комментарий сохранен'
            })
        
        return redirect('car_preparation:schedule', preparation_id=preparation_id)
    
    return JsonResponse({'success': False, 'error': 'Метод не разрешен'}, status=405)


@login_required
def preparation_comment_add(request, preparation_id):
    """Добавление комментария к подготовке с файлами"""
    preparation = get_object_or_404(CarPreparation, id=preparation_id)
    
    if request.method == 'POST':
        comment_text = request.POST.get('comment', '').strip()
        
        if not comment_text:
            return JsonResponse({'success': False, 'error': 'Комментарий не может быть пустым'}, status=400)
        
        # Получаем RefStaff из пользователя
        try:
            from refs.models import RefStaff
            staff = RefStaff.objects.filter(user=request.user).first()
        except:
            staff = None
        
        # Создаем комментарий
        comment = CarPreparationComment.objects.create(
            preparation=preparation,
            author=staff,
            comment=comment_text,
            date_created=timezone.now()
        )
        
        # Обрабатываем прикрепленные файлы
        uploaded_files = request.FILES.getlist('files[]')
        files_data = []
        
        for uploaded_file in uploaded_files:
            # Ограничение размера файла (50 МБ)
            max_size = 50 * 1024 * 1024  # 50 МБ
            if uploaded_file.size > max_size:
                continue
            
            # Определяем MIME тип
            import mimetypes
            mime_type, _ = mimetypes.guess_type(uploaded_file.name)
            
            comment_file = CarPreparationCommentFile.objects.create(
                comment=comment,
                file=uploaded_file,
                original_filename=uploaded_file.name,
                file_size=uploaded_file.size,
                mime_type=mime_type or 'application/octet-stream',
                date_created=timezone.now()
            )
            
            files_data.append({
                'id': comment_file.id,
                'filename': comment_file.original_filename,
                'url': comment_file.file.url if comment_file.file else '',
                'size': comment_file.file_size,
            })
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'comment_id': comment.id,
                'comment': comment.comment,
                'author': comment.author.name if comment.author else 'Неизвестно',
                'date_created': comment.date_created.strftime('%d.%m.%Y %H:%M') if comment.date_created else '',
                'files': files_data,
                'message': 'Комментарий добавлен'
            })
        
        return redirect('car_preparation:schedule', preparation_id=preparation_id)
    
    return JsonResponse({'success': False, 'error': 'Метод не разрешен'}, status=405)


@login_required
def preparation_comment_delete(request, comment_id):
    """Удаление комментария к подготовке"""
    comment = get_object_or_404(CarPreparationComment, id=comment_id)
    
    if request.method == 'POST':
        # Получаем RefStaff из пользователя
        try:
            from refs.models import RefStaff
            staff = RefStaff.objects.filter(user=request.user).first()
        except:
            staff = None
        
        # Мягкое удаление
        comment.is_deleted = True
        comment.deleted_at = timezone.now()
        comment.deleted_by = staff
        comment.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Комментарий удален'
            })
        
        return redirect('car_preparation:schedule', preparation_id=comment.preparation.id)
    
    return JsonResponse({'success': False, 'error': 'Метод не разрешен'}, status=405)


# ===========================================
# DASHBOARD И УПРАВЛЕНИЕ
# ===========================================

@login_required
def preparation_dashboard(request):
    """Рабочий стол управления подготовкой"""
    from django.db.models import Count, Sum, Avg, Q, F
    from django.utils import timezone
    from datetime import timedelta
    
    # Параметры фильтрации
    unit_id = request.GET.get('unit_id', None)
    date_from = request.GET.get('date_from', None)
    date_to = request.GET.get('date_to', None)
    
    # По умолчанию - текущий месяц
    today = timezone.now().date()
    if not date_from:
        date_from = today.replace(day=1)
    else:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        except:
            date_from = today.replace(day=1)
    
    if not date_to:
        last_day = monthrange(today.year, today.month)[1]
        date_to = today.replace(day=last_day)
    else:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        except:
            last_day = monthrange(today.year, today.month)[1]
            date_to = today.replace(day=last_day)
    
    # Базовые запросы
    date_from_dt = timezone.make_aware(datetime.combine(date_from, datetime.min.time()))
    date_to_dt = timezone.make_aware(datetime.combine(date_to, datetime.max.time()))
    
    # Фильтр по подразделению
    unit_filter = Q()
    if unit_id:
        unit_filter = Q(unit_id=unit_id)
    
    # Статистика по подготовкам
    preparations_query = CarPreparation.objects.filter(
        date_created__gte=date_from_dt,
        date_created__lte=date_to_dt
    ).filter(unit_filter)
    
    total_preparations = preparations_query.count()
    active_preparations = preparations_query.exclude(status__is_final=True).count()
    completed_preparations = preparations_query.filter(status__is_final=True).count()
    
    # Статистика по заказ-нарядам
    work_orders_query = WorkOrder.objects.filter(
        date_created__gte=date_from_dt,
        date_created__lte=date_to_dt
    )
    if unit_id:
        work_orders_query = work_orders_query.filter(car__unit_id=unit_id)
    
    total_work_orders = work_orders_query.count()
    scheduled_work_orders = work_orders_query.filter(status='scheduled').count()
    in_progress_work_orders = work_orders_query.filter(status='in_progress').count()
    completed_work_orders = work_orders_query.filter(status='completed').count()
    
    # Статистика по работам
    work_items_query = WorkOrderItem.objects.filter(
        work_order__date_created__gte=date_from_dt,
        work_order__date_created__lte=date_to_dt
    )
    if unit_id:
        work_items_query = work_items_query.filter(work_order__car__unit_id=unit_id)
    
    total_work_items = work_items_query.count()
    completed_work_items = work_items_query.filter(status='completed').count()
    in_progress_work_items = work_items_query.filter(status='in_progress').count()
    
    # Статистика по исполнителям
    performers_stats = work_items_query.filter(
        performer__isnull=False,
        status='completed',
        actual_start__isnull=False,
        actual_end__isnull=False
    ).values('performer__name').annotate(
        total_works=Count('id')
    ).order_by('-total_works')[:10]
    
    # Добавляем время выполнения для каждого исполнителя
    for stat in performers_stats:
        performer_name = stat['performer__name']
        performer_items = work_items_query.filter(
            performer__name=performer_name,
            status='completed',
            actual_start__isnull=False,
            actual_end__isnull=False
        )
        total_seconds = 0
        for item in performer_items:
            if item.actual_start and item.actual_end:
                delta = item.actual_end - item.actual_start
                total_seconds += delta.total_seconds()
        stat['total_time_minutes'] = int(total_seconds / 60) if total_seconds > 0 else 0
    
    # Статистика по материалам
    materials_stats = WorkOrderItemMaterial.objects.filter(
        work_order_item__work_order__date_created__gte=date_from_dt,
        work_order_item__work_order__date_created__lte=date_to_dt
    )
    if unit_id:
        materials_stats = materials_stats.filter(work_order_item__work_order__car__unit_id=unit_id)
    
    total_materials_cost = materials_stats.aggregate(
        total=Sum('total_price')
    )['total'] or 0
    
    materials_by_type = materials_stats.values('material__name').annotate(
        total_qty=Sum('quantity'),
        total_cost=Sum('total_price')
    ).order_by('-total_cost')[:10]
    
    # Статистика по ремонтным зонам
    zones_stats = work_orders_query.values('repair_zone__name').annotate(
        total_orders=Count('id')
    ).order_by('-total_orders')
    
    # График по дням (заказ-наряды)
    daily_stats = []
    current_date = date_from
    while current_date <= date_to:
        day_start = timezone.make_aware(datetime.combine(current_date, datetime.min.time()))
        day_end = timezone.make_aware(datetime.combine(current_date, datetime.max.time()))
        
        day_orders = WorkOrder.objects.filter(
            date_created__gte=day_start,
            date_created__lte=day_end
        )
        if unit_id:
            day_orders = day_orders.filter(car__unit_id=unit_id)
        
        daily_stats.append({
            'date': current_date.strftime('%d.%m'),
            'created': day_orders.count(),
            'completed': day_orders.filter(status='completed').count(),
        })
        current_date += timedelta(days=1)
    
    # Последние заказ-наряды
    recent_work_orders = work_orders_query.order_by('-date_created')[:10]
    
    # Подразделения для фильтра
    units = RefUnit.objects.filter(buauto=True).order_by('name')
    
    context = {
        'total_preparations': total_preparations,
        'active_preparations': active_preparations,
        'completed_preparations': completed_preparations,
        'total_work_orders': total_work_orders,
        'scheduled_work_orders': scheduled_work_orders,
        'in_progress_work_orders': in_progress_work_orders,
        'completed_work_orders': completed_work_orders,
        'total_work_items': total_work_items,
        'completed_work_items': completed_work_items,
        'in_progress_work_items': in_progress_work_items,
        'performers_stats': performers_stats,
        'total_materials_cost': total_materials_cost,
        'materials_by_type': materials_by_type,
        'zones_stats': zones_stats,
        'daily_stats': daily_stats,
        'recent_work_orders': recent_work_orders,
        'units': units,
        'selected_unit_id': unit_id,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'car_preparation/dashboard.html', context)


@login_required
def work_order_item_material_add(request, item_id):
    """Добавление материала к работе в заказ-наряде"""
    item = get_object_or_404(WorkOrderItem, id=item_id)
    
    if request.method == 'POST':
        material_id = request.POST.get('material_id')
        quantity = float(request.POST.get('quantity', 1) or 1)
        unit_price = float(request.POST.get('unit_price', 0) or 0)
        comment = request.POST.get('comment', '').strip()
        
        if not material_id:
            return JsonResponse({'success': False, 'error': 'Материал не выбран'}, status=400)
        
        try:
            material = RefPreparationMaterial.objects.get(id=int(material_id))
            
            material_item = WorkOrderItemMaterial.objects.create(
                work_order_item=item,
                material=material,
                quantity=quantity,
                unit_price=unit_price,
                comment=comment
            )
            
            return JsonResponse({
                'success': True,
                'material_id': material_item.id,
                'message': 'Материал добавлен'
            })
        except RefPreparationMaterial.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Материал не найден'}, status=404)
    
    return JsonResponse({'success': False, 'error': 'Метод не разрешен'}, status=405)


@login_required
def work_order_item_material_delete(request, material_id):
    """Удаление материала из работы"""
    material_item = get_object_or_404(WorkOrderItemMaterial, id=material_id)
    
    if request.method == 'POST':
        material_item.delete()
        return JsonResponse({
            'success': True,
            'message': 'Материал удален'
        })
    
    return JsonResponse({'success': False, 'error': 'Метод не разрешен'}, status=405)


# ===========================================
# УПРАВЛЕНИЕ РЕМОНТНЫМИ ЗОНАМИ
# ===========================================

@login_required
def repair_zones_list(request):
    """Список ремонтных зон"""
    zones = RefRepairZone.objects.all().select_related('unit').order_by('sort_order', 'name')
    
    context = {
        'zones': zones,
    }
    
    return render(request, 'car_preparation/repair_zones_list.html', context)


@login_required
def repair_zone_create(request):
    """Создание ремонтной зоны"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        description = request.POST.get('description', '').strip()
        unit_id = request.POST.get('unit_id') or None
        is_active = request.POST.get('is_active') == 'on'
        sort_order = int(request.POST.get('sort_order', 0) or 0)
        
        if not name:
            return JsonResponse({'success': False, 'error': 'Название обязательно'}, status=400)
        
        zone = RefRepairZone.objects.create(
            name=name,
            code=code,
            description=description,
            unit_id=int(unit_id) if unit_id else None,
            is_active=is_active,
            sort_order=sort_order
        )
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'zone_id': zone.id,
                'message': 'Ремонтная зона создана'
            })
        
        return redirect('car_preparation:repair_zones_list')
    
    units = RefUnit.objects.filter(buauto=True).order_by('name')
    context = {
        'units': units,
    }
    return render(request, 'car_preparation/repair_zone_form.html', context)


@login_required
def repair_zone_edit(request, zone_id):
    """Редактирование ремонтной зоны"""
    zone = get_object_or_404(RefRepairZone, id=zone_id)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        description = request.POST.get('description', '').strip()
        unit_id = request.POST.get('unit_id') or None
        is_active = request.POST.get('is_active') == 'on'
        sort_order = int(request.POST.get('sort_order', 0) or 0)
        
        if not name:
            return JsonResponse({'success': False, 'error': 'Название обязательно'}, status=400)
        
        zone.name = name
        zone.code = code
        zone.description = description
        zone.unit_id = int(unit_id) if unit_id else None
        zone.is_active = is_active
        zone.sort_order = sort_order
        zone.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Ремонтная зона обновлена'
            })
        
        return redirect('car_preparation:repair_zones_list')
    
    units = RefUnit.objects.filter(buauto=True).order_by('name')
    context = {
        'zone': zone,
        'units': units,
    }
    return render(request, 'car_preparation/repair_zone_form.html', context)


@login_required
def repair_zone_delete(request, zone_id):
    """Удаление ремонтной зоны"""
    zone = get_object_or_404(RefRepairZone, id=zone_id)
    
    if request.method == 'POST':
        # Проверяем, используется ли зона
        if WorkOrder.objects.filter(repair_zone=zone).exists():
            return JsonResponse({
                'success': False,
                'error': 'Невозможно удалить: зона используется в заказ-нарядах'
            }, status=400)
        
        zone.delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Ремонтная зона удалена'
            })
        
        return redirect('car_preparation:repair_zones_list')
    
    return JsonResponse({'success': False, 'error': 'Метод не разрешен'}, status=405)


# ===========================================
# УПРАВЛЕНИЕ ШАБЛОНАМИ ЗАКАЗ-НАРЯДОВ
# ===========================================

@login_required
def work_order_templates_list(request):
    """Список шаблонов заказ-нарядов"""
    templates = WorkOrderTemplate.objects.all().select_related('unit').prefetch_related('works').order_by('name')
    
    context = {
        'templates': templates,
    }
    
    return render(request, 'car_preparation/work_order_templates_list.html', context)


@login_required
def work_order_template_create(request):
    """Создание шаблона заказ-наряда"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        description = request.POST.get('description', '').strip()
        unit_id = request.POST.get('unit_id') or None
        is_active = request.POST.get('is_active') == 'on'
        is_default = request.POST.get('is_default') == 'on'
        estimated_duration = int(request.POST.get('estimated_duration_minutes', 0) or 0)
        work_ids = request.POST.getlist('work_ids[]')
        
        if not name:
            return JsonResponse({'success': False, 'error': 'Название обязательно'}, status=400)
        
        template = WorkOrderTemplate.objects.create(
            name=name,
            code=code,
            description=description,
            unit_id=int(unit_id) if unit_id else None,
            is_active=is_active,
            is_default=is_default,
            estimated_duration_minutes=estimated_duration
        )
        
        # Добавляем работы в шаблон
        from .models import WorkOrderTemplateWork
        sort_order = 0
        for work_id in work_ids:
            try:
                work = RefCarPreparationWork.objects.get(id=int(work_id))
                estimated_time = int(request.POST.get(f'work_{work_id}_time', 0) or 0)
                is_required = request.POST.get(f'work_{work_id}_required') == 'on'
                
                WorkOrderTemplateWork.objects.create(
                    template=template,
                    work=work,
                    sort_order=sort_order,
                    estimated_time=estimated_time,
                    is_required=is_required
                )
                sort_order += 1
            except (RefCarPreparationWork.DoesNotExist, ValueError):
                continue
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'template_id': template.id,
                'message': 'Шаблон создан'
            })
        
        return redirect('car_preparation:work_order_templates_list')
    
    units = RefUnit.objects.filter(buauto=True).order_by('name')
    works = RefCarPreparationWork.objects.filter(is_active=True).select_related('stage').order_by('stage__sort_order', 'sort_order')
    
    # Группируем работы по этапам
    works_by_stage = {}
    for work in works:
        stage_name = work.stage.name if work.stage else 'Без этапа'
        if stage_name not in works_by_stage:
            works_by_stage[stage_name] = []
        works_by_stage[stage_name].append(work)
    
    context = {
        'units': units,
        'works': works,
        'works_by_stage': works_by_stage,
    }
    return render(request, 'car_preparation/work_order_template_form.html', context)


@login_required
def work_order_template_edit(request, template_id):
    """Редактирование шаблона заказ-наряда"""
    template = get_object_or_404(WorkOrderTemplate.objects.prefetch_related('works'), id=template_id)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        description = request.POST.get('description', '').strip()
        unit_id = request.POST.get('unit_id') or None
        is_active = request.POST.get('is_active') == 'on'
        is_default = request.POST.get('is_default') == 'on'
        estimated_duration = int(request.POST.get('estimated_duration_minutes', 0) or 0)
        work_ids = request.POST.getlist('work_ids[]')
        
        if not name:
            return JsonResponse({'success': False, 'error': 'Название обязательно'}, status=400)
        
        template.name = name
        template.code = code
        template.description = description
        template.unit_id = int(unit_id) if unit_id else None
        template.is_active = is_active
        template.is_default = is_default
        template.estimated_duration_minutes = estimated_duration
        template.save()
        
        # Удаляем старые работы
        template.workordertemplatework_set.all().delete()
        
        # Добавляем новые работы
        from .models import WorkOrderTemplateWork
        sort_order = 0
        for work_id in work_ids:
            try:
                work = RefCarPreparationWork.objects.get(id=int(work_id))
                estimated_time = int(request.POST.get(f'work_{work_id}_time', 0) or 0)
                is_required = request.POST.get(f'work_{work_id}_required') == 'on'
                
                WorkOrderTemplateWork.objects.create(
                    template=template,
                    work=work,
                    sort_order=sort_order,
                    estimated_time=estimated_time,
                    is_required=is_required
                )
                sort_order += 1
            except (RefCarPreparationWork.DoesNotExist, ValueError):
                continue
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Шаблон обновлен'
            })
        
        return redirect('car_preparation:work_order_templates_list')
    
    units = RefUnit.objects.filter(buauto=True).order_by('name')
    works = RefCarPreparationWork.objects.filter(is_active=True).select_related('stage').order_by('stage__sort_order', 'sort_order')
    template_works = template.workordertemplatework_set.all().select_related('work')
    selected_work_ids = [tw.work_id for tw in template_works]
    
    # Группируем работы по этапам
    works_by_stage = {}
    for work in works:
        stage_name = work.stage.name if work.stage else 'Без этапа'
        if stage_name not in works_by_stage:
            works_by_stage[stage_name] = []
        works_by_stage[stage_name].append(work)
    
    context = {
        'template': template,
        'units': units,
        'works': works,
        'works_by_stage': works_by_stage,
        'template_works': template_works,
        'selected_work_ids': selected_work_ids,
    }
    return render(request, 'car_preparation/work_order_template_form.html', context)


@login_required
def work_order_template_delete(request, template_id):
    """Удаление шаблона заказ-наряда"""
    template = get_object_or_404(WorkOrderTemplate, id=template_id)
    
    if request.method == 'POST':
        # Проверяем, используется ли шаблон
        if WorkOrder.objects.filter(template=template).exists():
            return JsonResponse({
                'success': False,
                'error': 'Невозможно удалить: шаблон используется в заказ-нарядах'
            }, status=400)
        
        template.delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Шаблон удален'
            })
        
        return redirect('car_preparation:work_order_templates_list')
    
    return JsonResponse({'success': False, 'error': 'Метод не разрешен'}, status=405)


# ===========================================
# ОТЧЕТЫ
# ===========================================

@login_required
def performers_report(request):
    """Отчет по исполнителям"""
    unit_id = request.GET.get('unit_id', None)
    date_from = request.GET.get('date_from', None)
    date_to = request.GET.get('date_to', None)
    
    # По умолчанию - текущий месяц
    today = timezone.now().date()
    if not date_from:
        date_from = today.replace(day=1)
    else:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        except:
            date_from = today.replace(day=1)
    
    if not date_to:
        last_day = monthrange(today.year, today.month)[1]
        date_to = today.replace(day=last_day)
    else:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        except:
            last_day = monthrange(today.year, today.month)[1]
            date_to = today.replace(day=last_day)
    
    date_from_dt = timezone.make_aware(datetime.combine(date_from, datetime.min.time()))
    date_to_dt = timezone.make_aware(datetime.combine(date_to, datetime.max.time()))
    
    # Запрос работ
    work_items_query = WorkOrderItem.objects.filter(
        work_order__date_created__gte=date_from_dt,
        work_order__date_created__lte=date_to_dt,
        performer__isnull=False
    )
    
    if unit_id:
        work_items_query = work_items_query.filter(work_order__car__unit_id=unit_id)
    
    # Группировка по исполнителям
    performers_data = []
    performers_list = work_items_query.values('performer__name', 'performer__id').distinct()
    
    for performer_info in performers_list:
        performer_name = performer_info['performer__name']
        performer_id = performer_info['performer__id']
        
        performer_items = work_items_query.filter(performer_id=performer_id)
        
        total_works = performer_items.count()
        completed_works = performer_items.filter(status='completed').count()
        in_progress_works = performer_items.filter(status='in_progress').count()
        
        # Расчет времени
        total_seconds = 0
        for item in performer_items.filter(status='completed', actual_start__isnull=False, actual_end__isnull=False):
            if item.actual_start and item.actual_end:
                delta = item.actual_end - item.actual_start
                total_seconds += delta.total_seconds()
        
        total_hours = total_seconds / 3600 if total_seconds > 0 else 0
        
        # Стоимость материалов
        materials_cost = WorkOrderItemMaterial.objects.filter(
            work_order_item__performer_id=performer_id,
            work_order_item__work_order__date_created__gte=date_from_dt,
            work_order_item__work_order__date_created__lte=date_to_dt
        ).aggregate(total=Sum('total_price'))['total'] or 0
        
        performers_data.append({
            'performer_id': performer_id,
            'performer_name': performer_name,
            'total_works': total_works,
            'completed_works': completed_works,
            'in_progress_works': in_progress_works,
            'total_hours': round(total_hours, 2),
            'materials_cost': float(materials_cost),
            'avg_time_per_work': round(total_hours / completed_works, 2) if completed_works > 0 else 0,
        })
    
    performers_data.sort(key=lambda x: x['completed_works'], reverse=True)
    
    units = RefUnit.objects.filter(buauto=True).order_by('name')
    
    context = {
        'performers_data': performers_data,
        'units': units,
        'selected_unit_id': unit_id,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'car_preparation/performers_report.html', context)

