from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.db.models import Count, Q, F, Sum, Avg
from django.utils import timezone
from django.core.paginator import Paginator
from django.urls import reverse
from datetime import datetime, timedelta, date
import json
from calendar import monthrange
from .models import HelpDeskTask, TaskStatus, Priority, ProjectTag, TaskComment, TaskAttachment, TaskHistory


@login_required
def dashboard(request):
    """Дашборд с задачами, разделенными по статусам"""
    
    # Получаем все активные задачи
    tasks = HelpDeskTask.objects.filter(is_deleted=False)
    
    # Если пользователь не суперпользователь, показываем только его задачи или где он исполнитель
    if not request.user.is_superuser:
        tasks = tasks.filter(
            Q(author=request.user) | 
            Q(assignee=request.user) | 
            Q(observers=request.user)
        ).distinct()
    
    # Группируем по статусам
    statuses = TaskStatus.objects.filter(is_active=True).order_by('order')
    
    tasks_by_status = []
    for status in statuses:
        status_tasks = tasks.filter(status=status)
        tasks_by_status.append({
            'status': status,
            'tasks': status_tasks,
        })
    
    # Статистика
    total_tasks = tasks.count()
    overdue_tasks = tasks.filter(
        date_deadline__lt=timezone.now(),
        status__is_closed=False
    ).count()
    
    my_tasks = tasks.filter(assignee=request.user).count()
    my_overdue = tasks.filter(
        assignee=request.user,
        date_deadline__lt=timezone.now(),
        status__is_closed=False
    ).count()
    
    # Задачи за сегодня
    today = timezone.now().date()
    today_created = tasks.filter(date_created__date=today).count()
    today_closed = tasks.filter(date_closed__date=today).count()
    
    # Задачи за неделю
    week_ago = today - timedelta(days=7)
    week_created = tasks.filter(date_created__date__gte=week_ago).count()
    week_closed = tasks.filter(date_closed__date__gte=week_ago).count()
    
    params = {
        'tasks_by_status': tasks_by_status,
        'statuses': statuses,
        'total_tasks': total_tasks,
        'overdue_tasks': overdue_tasks,
        'my_tasks': my_tasks,
        'my_overdue': my_overdue,
        'today_created': today_created,
        'today_closed': today_closed,
        'week_created': week_created,
        'week_closed': week_closed,
    }
    
    return render(request, "help_desk/dashboard.html", {'params': params})


@login_required
def task_list(request):
    """Список задач с фильтрацией"""
    
    tasks = HelpDeskTask.objects.filter(is_deleted=False)
    
    # Фильтрация для обычных пользователей
    if not request.user.is_superuser:
        tasks = tasks.filter(
            Q(author=request.user) | 
            Q(assignee=request.user) | 
            Q(observers=request.user)
        ).distinct()
    
    # Фильтры из GET параметров
    filtr = {}
    filtr_count = 0
    
    # Фильтр по номеру
    nomer = request.GET.get('nomer', '')
    if nomer:
        try:
            tasks = tasks.filter(id=int(nomer))
            filtr['nomer'] = nomer
            filtr_count += 1
        except:
            pass
    
    # Фильтр по статусу
    status_id = request.GET.get('status', '')
    if status_id:
        try:
            tasks = tasks.filter(status_id=int(status_id))
            filtr['status'] = status_id
            filtr_count += 1
        except:
            pass
    
    # Фильтр по приоритету
    priority_id = request.GET.get('priority', '')
    if priority_id:
        try:
            tasks = tasks.filter(priority_id=int(priority_id))
            filtr['priority'] = priority_id
            filtr_count += 1
        except:
            pass
    
    # Фильтр по автору
    author_id = request.GET.get('author', '')
    if author_id:
        try:
            tasks = tasks.filter(author_id=int(author_id))
            filtr['author'] = author_id
            filtr_count += 1
        except:
            pass
    
    # Фильтр по исполнителю
    assignee_id = request.GET.get('assignee', '')
    if assignee_id:
        try:
            tasks = tasks.filter(assignee_id=int(assignee_id))
            filtr['assignee'] = assignee_id
            filtr_count += 1
        except:
            pass
    
    # Фильтр по дате от
    date_start = request.GET.get('date', '')
    if date_start:
        try:
            date_obj = datetime.strptime(date_start, '%Y-%m-%d').date()
            tasks = tasks.filter(date_created__date__gte=date_obj)
            filtr['dateStart'] = date_start
            filtr_count += 1
        except:
            pass
    
    # Фильтр по дате до
    date_end = request.GET.get('date_end', '')
    if date_end:
        try:
            date_obj = datetime.strptime(date_end, '%Y-%m-%d').date()
            tasks = tasks.filter(date_created__date__lte=date_obj)
            filtr['dateEnd'] = date_end
            filtr_count += 1
        except:
            pass
    
    # Фильтр по проекту
    project_id = request.GET.get('project', '')
    if project_id:
        try:
            tasks = tasks.filter(projects__id=int(project_id))
            filtr['project'] = project_id
            filtr_count += 1
        except:
            pass
    
    # Поиск по тексту
    search = request.GET.get('search', '')
    if search:
        tasks = tasks.filter(
            Q(title__icontains=search) | 
            Q(description__icontains=search)
        )
        filtr['search'] = search
        filtr_count += 1
    
    # Сортировка
    order_by = request.GET.get('order_by', '-date_created')
    if order_by in ['date_created', '-date_created', 'date_deadline', '-date_deadline', 
                   'title', '-title', 'status', '-status']:
        tasks = tasks.order_by(order_by)
    
    # Пагинация
    per_page = int(request.GET.get('count', 25))
    paginator = Paginator(tasks, per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Получаем справочники для фильтров
    statuses = TaskStatus.objects.filter(is_active=True).order_by('order')
    priorities = Priority.objects.all().order_by('-level')
    projects = ProjectTag.objects.filter(is_active=True).order_by('order', 'name')
    
    params = {
        'tasks': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'filtr': filtr,
        'filtr_count': filtr_count,
        'statuses': statuses,
        'priorities': priorities,
        'projects': projects,
        'search': search,
        'order_by': order_by,
    }
    
    return render(request, "help_desk/task_list.html", {'params': params})


@login_required
def task_detail(request, pk):
    """Детальная страница задачи"""
    
    task = get_object_or_404(HelpDeskTask, pk=pk, is_deleted=False)
    
    # Проверка прав доступа
    if not request.user.is_superuser:
        if task.author != request.user and task.assignee != request.user:
            if not task.observers.filter(id=request.user.id).exists():
                return HttpResponseRedirect('/help_desk/')
    
    # Комментарии
    comments = task.comments.filter(is_deleted=False).order_by('-date_created')
    
    # Вложения
    attachments = task.attachments.all().order_by('-date_uploaded')
    
    # История изменений
    history = task.history.all().order_by('-date_created')[:50]
    
    params = {
        'task': task,
        'comments': comments,
        'attachments': attachments,
        'history': history,
    }
    
    return render(request, "help_desk/task_detail.html", {'params': params})


@login_required
def task_create(request):
    """Создание новой задачи"""
    
    if request.method == 'POST':
        # Создаем задачу
        task = HelpDeskTask()
        task.title = request.POST.get('title', '')
        task.description = request.POST.get('description', '')
        task.author = request.user
        
        # Исполнитель
        assignee_id = request.POST.get('assignee', '')
        if assignee_id:
            try:
                from django.contrib.auth.models import User
                task.assignee = User.objects.get(id=int(assignee_id))
            except:
                pass
        
        # Статус
        status_id = request.POST.get('status', '')
        if status_id:
            try:
                task.status = TaskStatus.objects.get(id=int(status_id))
            except:
                # Берем первый статус по умолчанию
                task.status = TaskStatus.objects.filter(is_active=True).order_by('order').first()
        else:
            task.status = TaskStatus.objects.filter(is_active=True).order_by('order').first()
        
        # Приоритет
        priority_id = request.POST.get('priority', '')
        if priority_id:
            try:
                task.priority = Priority.objects.get(id=int(priority_id))
            except:
                pass
        
        # Дата начала
        date_start = request.POST.get('date_start', '')
        if date_start:
            try:
                task.date_start = datetime.strptime(date_start, '%Y-%m-%dT%H:%M')
            except:
                pass
        
        # Срок выполнения
        date_deadline = request.POST.get('date_deadline', '')
        if date_deadline:
            try:
                task.date_deadline = datetime.strptime(date_deadline, '%Y-%m-%dT%H:%M')
            except:
                pass
        
        # Проекты
        project_ids = request.POST.getlist('projects')
        for project_id in project_ids:
            try:
                project = ProjectTag.objects.get(id=int(project_id))
                task.projects.add(project)
            except:
                pass
        
        # Дополнительные теги
        task.tags = request.POST.get('tags', '')
        
        task.save()
        
        # Наблюдатели
        observer_ids = request.POST.getlist('observers')
        for observer_id in observer_ids:
            try:
                from django.contrib.auth.models import User
                observer = User.objects.get(id=int(observer_id))
                task.observers.add(observer)
            except:
                pass
        
        # Создаем запись в истории
        TaskHistory.objects.create(
            task=task,
            user=request.user,
            action='Создана задача',
            comment='Задача создана'
        )
        
        return redirect('helpdesk:task_detail', pk=task.pk)
    
    # GET запрос - форма создания
    statuses = TaskStatus.objects.filter(is_active=True).order_by('order')
    priorities = Priority.objects.all().order_by('-level')
    projects = ProjectTag.objects.filter(is_active=True).order_by('order', 'name')
    from django.contrib.auth.models import User
    users = User.objects.filter(is_active=True).order_by('username')
    
    params = {
        'statuses': statuses,
        'priorities': priorities,
        'projects': projects,
        'users': users,
    }
    
    return render(request, "help_desk/task_form.html", {'params': params})


@login_required
def task_edit(request, pk):
    """Редактирование задачи"""
    
    task = get_object_or_404(HelpDeskTask, pk=pk, is_deleted=False)
    
    # Проверка прав
    if not request.user.is_superuser:
        if task.author != request.user and task.assignee != request.user:
            return HttpResponseRedirect('/help_desk/')
    
    if request.method == 'POST':
        # Сохраняем старое значение статуса для истории
        old_status = task.status
        
        # Обновляем задачу
        task.title = request.POST.get('title', task.title)
        task.description = request.POST.get('description', task.description)
        
        # Исполнитель
        assignee_id = request.POST.get('assignee', '')
        if assignee_id:
            try:
                from django.contrib.auth.models import User
                task.assignee = User.objects.get(id=int(assignee_id))
            except:
                task.assignee = None
        else:
            task.assignee = None
        
        # Статус
        status_id = request.POST.get('status', '')
        if status_id:
            try:
                new_status = TaskStatus.objects.get(id=int(status_id))
                if old_status != new_status:
                    TaskHistory.objects.create(
                        task=task,
                        user=request.user,
                        action='Изменен статус',
                        field_name='status',
                        old_value=str(old_status) if old_status else '',
                        new_value=str(new_status),
                    )
                task.status = new_status
                
                # Если статус закрывающий, устанавливаем дату закрытия
                if new_status.is_closed and not task.date_closed:
                    task.date_closed = timezone.now()
                elif not new_status.is_closed:
                    task.date_closed = None
            except:
                pass
        
        # Приоритет
        priority_id = request.POST.get('priority', '')
        if priority_id:
            try:
                task.priority = Priority.objects.get(id=int(priority_id))
            except:
                task.priority = None
        else:
            task.priority = None
        
        # Дата начала
        date_start = request.POST.get('date_start', '')
        if date_start:
            try:
                task.date_start = datetime.strptime(date_start, '%Y-%m-%dT%H:%M')
            except:
                pass
        
        # Срок выполнения
        date_deadline = request.POST.get('date_deadline', '')
        if date_deadline:
            try:
                task.date_deadline = datetime.strptime(date_deadline, '%Y-%m-%dT%H:%M')
            except:
                pass
        else:
            task.date_deadline = None
        
        # Дополнительные теги
        task.tags = request.POST.get('tags', '')
        
        task.save()
        
        # Проекты
        task.projects.clear()
        project_ids = request.POST.getlist('projects')
        for project_id in project_ids:
            try:
                project = ProjectTag.objects.get(id=int(project_id))
                task.projects.add(project)
            except:
                pass
        
        # Дополнительные теги
        task.tags = request.POST.get('tags', '')
        
        # Наблюдатели
        task.observers.clear()
        observer_ids = request.POST.getlist('observers')
        for observer_id in observer_ids:
            try:
                from django.contrib.auth.models import User
                observer = User.objects.get(id=int(observer_id))
                task.observers.add(observer)
            except:
                pass
        
        TaskHistory.objects.create(
            task=task,
            user=request.user,
            action='Задача обновлена',
        )
        
        return redirect('helpdesk:task_detail', pk=task.pk)
    
    # GET запрос - форма редактирования
    statuses = TaskStatus.objects.filter(is_active=True).order_by('order')
    priorities = Priority.objects.all().order_by('-level')
    projects = ProjectTag.objects.filter(is_active=True).order_by('order', 'name')
    from django.contrib.auth.models import User
    users = User.objects.filter(is_active=True).order_by('username')
    
    params = {
        'task': task,
        'statuses': statuses,
        'priorities': priorities,
        'projects': projects,
        'users': users,
    }
    
    return render(request, "help_desk/task_form.html", {'params': params})


@login_required
def task_add_comment(request, pk):
    """Добавление комментария к задаче"""
    
    task = get_object_or_404(HelpDeskTask, pk=pk, is_deleted=False)
    
    # Проверка прав доступа
    if not request.user.is_superuser:
        if task.author != request.user and task.assignee != request.user:
            if not task.observers.filter(id=request.user.id).exists():
                return JsonResponse({'error': 'Нет доступа'}, status=403)
    
    if request.method == 'POST':
        comment = TaskComment()
        comment.task = task
        comment.author = request.user
        comment.text = request.POST.get('text', '')
        comment.is_internal = request.POST.get('is_internal', '') == 'on'
        comment.save()
        
        TaskHistory.objects.create(
            task=task,
            user=request.user,
            action='Добавлен комментарий',
            comment=f'Комментарий #{comment.id}'
        )
        
        return redirect('helpdesk:task_detail', pk=task.pk)
    
    return redirect('helpdesk:task_detail', pk=task.pk)


@login_required
def calendar(request):
    """Календарь планирования задач"""
    
    # Получаем год и месяц
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))
    
    tasks = HelpDeskTask.objects.filter(is_deleted=False)
    
    # Фильтрация для обычных пользователей
    if not request.user.is_superuser:
        tasks = tasks.filter(
            Q(author=request.user) | 
            Q(assignee=request.user) | 
            Q(observers=request.user)
        ).distinct()
    
    # Задачи с дедлайном в этом месяце
    tasks_in_month = tasks.filter(
        date_deadline__year=year,
        date_deadline__month=month
    )
    
    # Задачи со сроком начала в этом месяце
    tasks_start = tasks.filter(
        date_start__year=year,
        date_start__month=month
    )
    
    # Формируем календарь
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])
    
    calendar_data = []
    current_date = first_day
    week = []
    
    # Дни недели до первого дня месяца
    weekday = current_date.weekday()
    for i in range(weekday):
        week.append({'date': None, 'tasks': []})
    
    # Дни месяца
    while current_date <= last_day:
        day_tasks = []
        for task in tasks_in_month:
            if task.date_deadline and task.date_deadline.date() == current_date:
                day_tasks.append(task)
        
        for task in tasks_start:
            if task.date_start and task.date_start.date() == current_date:
                if task not in day_tasks:
                    day_tasks.append(task)
        
        week.append({
            'date': current_date,
            'tasks': day_tasks,
            'is_today': current_date == timezone.now().date(),
        })
        
        if len(week) == 7:
            calendar_data.append(week)
            week = []
        
        current_date += timedelta(days=1)
    
    # Дополняем последнюю неделю
    while len(week) < 7:
        week.append({'date': None, 'tasks': []})
    if len(week) > 0:
        calendar_data.append(week)
    
    # Навигация по месяцам
    prev_month = month - 1
    prev_year = year
    if prev_month < 1:
        prev_month = 12
        prev_year -= 1
    
    next_month = month + 1
    next_year = year
    if next_month > 12:
        next_month = 1
        next_year += 1
    
    params = {
        'calendar_data': calendar_data,
        'year': year,
        'month': month,
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
        'month_names': ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                       'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'],
    }
    
    return render(request, "help_desk/calendar.html", {'params': params})


@login_required
def chart(request):
    """График выполнения задач"""
    
    tasks = HelpDeskTask.objects.filter(is_deleted=False)
    
    # Фильтрация для обычных пользователей
    if not request.user.is_superuser:
        tasks = tasks.filter(
            Q(author=request.user) | 
            Q(assignee=request.user) | 
            Q(observers=request.user)
        ).distinct()
    
    # Период для графика
    period = request.GET.get('period', 'month')  # week, month, year
    end_date = timezone.now().date()
    
    if period == 'week':
        start_date = end_date - timedelta(days=7)
        days = 7
    elif period == 'month':
        start_date = end_date - timedelta(days=30)
        days = 30
    else:  # year
        start_date = end_date - timedelta(days=365)
        days = 365
    
    # Статистика по статусам
    status_stats = tasks.values('status__name', 'status__color').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Статистика по приоритетам
    priority_stats = tasks.values('priority__name', 'priority__color').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # График создания задач по дням
    creation_data = []
    current_date = start_date
    while current_date <= end_date:
        count = tasks.filter(date_created__date=current_date).count()
        creation_data.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'count': count
        })
        current_date += timedelta(days=1)
    
    # График закрытия задач по дням
    closure_data = []
    current_date = start_date
    while current_date <= end_date:
        count = tasks.filter(date_closed__date=current_date).count()
        closure_data.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'count': count
        })
        current_date += timedelta(days=1)
    
    # Статистика по исполнителям
    assignee_stats = tasks.filter(assignee__isnull=False).values(
        'assignee__username'
    ).annotate(
        count=Count('id'),
        closed=Count('id', filter=Q(status__is_closed=True))
    ).order_by('-count')[:10]
    
    params = {
        'period': period,
        'status_stats': list(status_stats),
        'priority_stats': list(priority_stats),
        'creation_data': json.dumps(creation_data),
        'closure_data': json.dumps(closure_data),
        'assignee_stats': list(assignee_stats),
    }
    
    return render(request, "help_desk/chart.html", {'params': params})
