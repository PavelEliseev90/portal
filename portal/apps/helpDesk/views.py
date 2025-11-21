from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.db.models import Count, Q, F, Sum, Avg
from django.utils import timezone
from django.core.paginator import Paginator
from django.urls import reverse
from django.contrib.auth.models import User
from datetime import datetime, timedelta, date
import json
from calendar import monthrange
from .models import (HelpDeskTask, TaskStatus, Priority, ProjectTag, TaskComment, TaskAttachment, 
                     TaskHistory, SavedFilter, TaskReminder, AutoAssignmentRule)
from .utils import send_task_notification
from django.views.decorators.http import require_POST, require_http_methods
import csv
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment


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
    
    tasks = tasks.annotate(
        comments_count=Count('comments', filter=Q(comments__is_deleted=False), distinct=True),
        attachments_count=Count('attachments', distinct=True),
        observers_count=Count('observers', distinct=True),
    )
    
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

    # Фильтр: только мои задачи (прямой параметр)
    only_my = request.GET.get('my')
    if only_my:
        tasks = tasks.filter(assignee=request.user)
        filtr['my'] = 1
        filtr_count += 1

    # Фильтр: просроченные
    overdue_flag = request.GET.get('overdue')
    if overdue_flag:
        tasks = tasks.filter(
            status__is_closed=False,
            date_deadline__lt=timezone.now()
        )
        filtr['overdue'] = 1
        filtr_count += 1

    # Фильтр: закрытые сегодня
    closed_today = request.GET.get('closed_today')
    if closed_today:
        today = timezone.now().date()
        tasks = tasks.filter(date_closed__date=today)
        filtr['closed_today'] = 1
        filtr_count += 1
    
    # Сортировка
    order_by = request.GET.get('order_by', '-date_created')
    allowed_orders = [
        'date_created', '-date_created',
        'date_deadline', '-date_deadline',
        'date_closed', '-date_closed',
        'title', '-title',
        'status__order', '-status__order',
        'priority__level', '-priority__level',
        'id', '-id',
        'author__username', '-author__username',
        'assignee__username', '-assignee__username',
        'comments_count', '-comments_count',
        'observers_count', '-observers_count',
        'attachments_count', '-attachments_count',
    ]
    if order_by not in allowed_orders:
        order_by = '-date_created'
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
        
        # Дополнительные теги
        task.tags = request.POST.get('tags', '')
        
        task.save()
        
        # Проекты
        project_ids = request.POST.getlist('projects')
        for project_id in project_ids:
            try:
                project = ProjectTag.objects.get(id=int(project_id))
                task.projects.add(project)
            except:
                pass
        
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
        
        # Отправляем уведомление о создании задачи
        send_task_notification(
            task=task,
            action_type='task_created',
            changed_by=request.user,
            request=request
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
        # Сохраняем старые значения для истории и отслеживания изменений
        old_status = task.status
        old_title = task.title
        old_assignee = task.assignee
        old_priority = task.priority
        old_deadline = task.date_deadline
        has_changes = False
        changes_dict = {}
        
        # Обновляем задачу
        new_title = request.POST.get('title', task.title)
        if old_title != new_title:
            has_changes = True
            changes_dict['title'] = f"{old_title} → {new_title}"
        task.title = new_title
        task.description = request.POST.get('description', task.description)
        
        # Исполнитель
        assignee_id = request.POST.get('assignee', '')
        if assignee_id:
            try:
                from django.contrib.auth.models import User
                new_assignee = User.objects.get(id=int(assignee_id))
                if old_assignee != new_assignee:
                    has_changes = True
                    changes_dict['assignee'] = f"{old_assignee.get_full_name() if old_assignee else 'Не назначен'} → {new_assignee.get_full_name() if new_assignee else 'Не назначен'}"
                task.assignee = new_assignee
            except:
                if old_assignee:
                    has_changes = True
                    changes_dict['assignee'] = f"{old_assignee.get_full_name()} → Не назначен"
                task.assignee = None
        else:
            if old_assignee:
                has_changes = True
                changes_dict['assignee'] = f"{old_assignee.get_full_name()} → Не назначен"
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
                    # Отправляем уведомление об изменении статуса
                    send_task_notification(
                        task=task,
                        action_type='status_changed',
                        changed_by=request.user,
                        changes={'old_status': str(old_status) if old_status else '', 'new_status': str(new_status)},
                        request=request
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
                new_priority = Priority.objects.get(id=int(priority_id))
                if old_priority != new_priority:
                    has_changes = True
                    changes_dict['priority'] = f"{old_priority.name if old_priority else 'Не задан'} → {new_priority.name}"
                task.priority = new_priority
            except:
                if old_priority:
                    has_changes = True
                    changes_dict['priority'] = f"{old_priority.name} → Не задан"
                task.priority = None
        else:
            if old_priority:
                has_changes = True
                changes_dict['priority'] = f"{old_priority.name} → Не задан"
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
                new_deadline = datetime.strptime(date_deadline, '%Y-%m-%dT%H:%M')
                if old_deadline != new_deadline:
                    has_changes = True
                    old_deadline_str = old_deadline.strftime('%d.%m.%Y %H:%M') if old_deadline else 'Не задан'
                    changes_dict['date_deadline'] = f"{old_deadline_str} → {new_deadline.strftime('%d.%m.%Y %H:%M')}"
                task.date_deadline = new_deadline
            except:
                pass
        else:
            if old_deadline:
                has_changes = True
                changes_dict['date_deadline'] = f"{old_deadline.strftime('%d.%m.%Y %H:%M')} → Не задан"
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
        
        # Отправляем уведомление об обновлении задачи (если были изменения, но не статус)
        # Статус обрабатывается отдельно выше
        if old_status == task.status and has_changes and changes_dict:
            send_task_notification(
                task=task,
                action_type='task_updated',
                changed_by=request.user,
                changes=changes_dict,
                request=request
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
        
        # Отправляем уведомление о новом комментарии
        send_task_notification(
            task=task,
            action_type='comment_added',
            changed_by=request.user,
            comment=comment,
            request=request
        )
        
        return redirect('helpdesk:task_detail', pk=task.pk)
    
    return redirect('helpdesk:task_detail', pk=task.pk)


@login_required
def task_add_attachment(request, pk):
    """Загрузка файлов к задаче"""

    task = get_object_or_404(HelpDeskTask, pk=pk, is_deleted=False)

    # Проверка прав доступа
    if not request.user.is_superuser:
        if task.author != request.user and task.assignee != request.user:
            if not task.observers.filter(id=request.user.id).exists():
                return JsonResponse({'error': 'Нет доступа'}, status=403)

    if request.method == 'POST':
        files = request.FILES.getlist('files')
        description = request.POST.get('description', '')
        saved_any = False

        for upload in files:
            attachment = TaskAttachment(
                task=task,
                uploaded_by=request.user,
                original_filename=upload.name,
                file=upload,
                file_size=upload.size,
                description=description
            )
            attachment.save()
            saved_any = True

        if saved_any:
            TaskHistory.objects.create(
                task=task,
                user=request.user,
                action='Добавлено вложение',
                comment=f'Загружено файлов: {len(files)}'
            )

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
    
    tasks = tasks.annotate(
        comments_count=Count('comments', filter=Q(comments__is_deleted=False), distinct=True),
        attachments_count=Count('attachments', distinct=True),
        observers_count=Count('observers', distinct=True),
    )
    
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
    
    filters = {}

    # Фильтрация
    status_id = request.GET.get('status')
    if status_id:
        try:
            tasks = tasks.filter(status_id=int(status_id))
            filters['status'] = int(status_id)
        except:
            pass

    priority_id = request.GET.get('priority')
    if priority_id:
        try:
            tasks = tasks.filter(priority_id=int(priority_id))
            filters['priority'] = int(priority_id)
        except:
            pass

    author_id = request.GET.get('author')
    if author_id:
        try:
            tasks = tasks.filter(author_id=int(author_id))
            filters['author'] = int(author_id)
        except:
            pass

    assignee_id = request.GET.get('assignee')
    if assignee_id:
        try:
            tasks = tasks.filter(assignee_id=int(assignee_id))
            filters['assignee'] = int(assignee_id)
        except:
            pass

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

    # Статистика по проектам
    project_stats_qs = tasks.values('projects__id', 'projects__name', 'projects__color').annotate(
        count=Count('id', distinct=True)
    ).order_by('-count')

    project_stats = []
    for item in project_stats_qs:
        if item['projects__id']:
            project_stats.append({
                'name': item['projects__name'] or 'Без проекта',
                'color': item['projects__color'] or '#6c757d',
                'count': item['count']
            })

    no_project_count = tasks.filter(projects__isnull=True).distinct().count()
    if no_project_count and not any(p['name'] == 'Без проекта' for p in project_stats):
        project_stats.append({
            'name': 'Без проекта',
            'color': '#6c757d',
            'count': no_project_count
        })
    
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
    
    statuses = TaskStatus.objects.filter(is_active=True).order_by('order')
    priorities = Priority.objects.all().order_by('-level')
    users = User.objects.filter(is_active=True).order_by('username')

    params = {
        'period': period,
        'status_stats': list(status_stats),
        'priority_stats': list(priority_stats),
        'project_stats': project_stats,
        'creation_data': json.dumps(creation_data),
        'closure_data': json.dumps(closure_data),
        'assignee_stats': list(assignee_stats),
        'filters': filters,
        'statuses': statuses,
        'priorities': priorities,
        'users': users,
    }
    
    return render(request, "help_desk/chart.html", {'params': params})


# ============ НОВЫЕ ФУНКЦИИ ============

@login_required
@require_POST
def task_quick_status_change(request, pk):
    """Быстрое изменение статуса задачи одной кнопкой"""
    task = get_object_or_404(HelpDeskTask, pk=pk, is_deleted=False)
    
    # Проверка прав
    if not request.user.is_superuser:
        if task.author != request.user and task.assignee != request.user:
            if not task.observers.filter(id=request.user.id).exists():
                return JsonResponse({'error': 'Нет доступа'}, status=403)
    
    status_id = request.POST.get('status_id')
    if not status_id:
        return JsonResponse({'error': 'Не указан статус'}, status=400)
    
    try:
        old_status = task.status
        new_status = TaskStatus.objects.get(id=int(status_id))
        
        # Сохраняем старое значение для истории
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
        
        task.save()
        
        # Отправляем уведомление
        if old_status != new_status:
            send_task_notification(
                task=task,
                action_type='status_changed',
                changed_by=request.user,
                changes={'old_status': str(old_status) if old_status else '', 'new_status': str(new_status)},
                request=request
            )
        
        return JsonResponse({
            'success': True,
            'status_id': new_status.id,
            'status_name': new_status.name,
            'status_color': new_status.color,
        })
    except TaskStatus.DoesNotExist:
        return JsonResponse({'error': 'Статус не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def saved_filters(request):
    """Управление сохраненными фильтрами"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'save':
            # Сохранение фильтра
            name = request.POST.get('name', '')
            if not name:
                return JsonResponse({'error': 'Не указано название'}, status=400)
            
            # Получаем параметры из GET запроса
            filter_params = {}
            for key in request.POST.keys():
                if key not in ['action', 'name', 'csrfmiddlewaretoken']:
                    filter_params[key] = request.POST.get(key)
            
            saved_filter = SavedFilter.objects.create(
                user=request.user,
                name=name,
                filter_params=filter_params
            )
            
            return JsonResponse({'success': True, 'id': saved_filter.id, 'name': saved_filter.name})
        
        elif action == 'delete':
            filter_id = request.POST.get('filter_id')
            try:
                saved_filter = SavedFilter.objects.get(id=int(filter_id), user=request.user)
                saved_filter.delete()
                return JsonResponse({'success': True})
            except SavedFilter.DoesNotExist:
                return JsonResponse({'error': 'Фильтр не найден'}, status=404)
    
    # GET запрос - возвращаем список сохраненных фильтров
    saved_filters_list = SavedFilter.objects.filter(user=request.user).order_by('order', 'name')
    filters_data = [{
        'id': f.id,
        'name': f.name,
        'params': f.filter_params,
        'is_default': f.is_default
    } for f in saved_filters_list]
    
    return JsonResponse({'filters': filters_data})


@login_required
def task_duplicate(request, pk):
    """Дублирование задачи"""
    original_task = get_object_or_404(HelpDeskTask, pk=pk, is_deleted=False)
    
    # Создаем копию задачи
    new_task = HelpDeskTask()
    new_task.title = f"{original_task.title} (копия)"
    new_task.description = original_task.description
    new_task.author = request.user
    new_task.assignee = original_task.assignee
    new_task.priority = original_task.priority
    # Статус - первый статус по умолчанию (не копируем)
    new_task.status = TaskStatus.objects.filter(is_active=True).order_by('order').first()
    new_task.tags = original_task.tags
    new_task.save()
    
    # Копируем проекты
    for project in original_task.projects.all():
        new_task.projects.add(project)
    
    # Копируем наблюдателей
    for observer in original_task.observers.all():
        new_task.observers.add(observer)
    
    # Создаем запись в истории
    TaskHistory.objects.create(
        task=new_task,
        user=request.user,
        action='Создана задача',
        comment=f'Скопировано из задачи #{original_task.id}'
    )
    
    # Отправляем уведомление
    send_task_notification(
        task=new_task,
        action_type='task_created',
        changed_by=request.user,
        request=request
    )
    
    return redirect('helpdesk:task_detail', pk=new_task.pk)


@login_required
def task_export(request):
    """Экспорт задач в Excel/CSV"""
    tasks = HelpDeskTask.objects.filter(is_deleted=False)
    
    # Применяем те же фильтры, что и в списке задач
    if not request.user.is_superuser:
        tasks = tasks.filter(
            Q(author=request.user) | 
            Q(assignee=request.user) | 
            Q(observers=request.user)
        ).distinct()
    
    # Фильтры из GET параметров
    status_id = request.GET.get('status', '')
    if status_id:
        try:
            tasks = tasks.filter(status_id=int(status_id))
        except:
            pass
    
    priority_id = request.GET.get('priority', '')
    if priority_id:
        try:
            tasks = tasks.filter(priority_id=int(priority_id))
        except:
            pass
    
    project_id = request.GET.get('project', '')
    if project_id:
        try:
            tasks = tasks.filter(projects__id=int(project_id))
        except:
            pass
    
    assignee_id = request.GET.get('assignee', '')
    if assignee_id:
        try:
            tasks = tasks.filter(assignee_id=int(assignee_id))
        except:
            pass
    
    author_id = request.GET.get('author', '')
    if author_id:
        try:
            tasks = tasks.filter(author_id=int(author_id))
        except:
            pass
    
    # Формат экспорта
    export_format = request.GET.get('format', 'excel')  # excel или csv
    
    if export_format == 'csv':
        # CSV экспорт
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="tasks_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Тема', 'Автор', 'Исполнитель', 'Статус', 'Приоритет', 
            'Дата создания', 'Срок выполнения', 'Проекты', 'Комментариев', 'Вложений'
        ])
        
        for task in tasks[:1000]:  # Ограничение на 1000 задач
            projects_str = ', '.join([p.name for p in task.projects.all()])
            writer.writerow([
                task.id,
                task.title,
                task.author.get_full_name() or task.author.username,
                task.assignee.get_full_name() or task.assignee.username if task.assignee else '',
                task.status.name if task.status else '',
                task.priority.name if task.priority else '',
                task.date_created.strftime('%d.%m.%Y %H:%M'),
                task.date_deadline.strftime('%d.%m.%Y %H:%M') if task.date_deadline else '',
                projects_str,
                task.comments.filter(is_deleted=False).count(),
                task.attachments.count(),
            ])
        
        return response
    
    else:
        # Excel экспорт
        wb = Workbook()
        ws = wb.active
        ws.title = "Задачи"
        
        # Заголовки
        headers = ['ID', 'Тема', 'Автор', 'Исполнитель', 'Статус', 'Приоритет', 
                  'Дата создания', 'Срок выполнения', 'Проекты', 'Комментариев', 'Вложений']
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Данные
        for row_num, task in enumerate(tasks[:1000], 2):  # Ограничение на 1000 задач
            projects_str = ', '.join([p.name for p in task.projects.all()])
            ws.cell(row=row_num, column=1, value=task.id)
            ws.cell(row=row_num, column=2, value=task.title)
            ws.cell(row=row_num, column=3, value=task.author.get_full_name() or task.author.username)
            ws.cell(row=row_num, column=4, value=task.assignee.get_full_name() or task.assignee.username if task.assignee else '')
            ws.cell(row=row_num, column=5, value=task.status.name if task.status else '')
            ws.cell(row=row_num, column=6, value=task.priority.name if task.priority else '')
            ws.cell(row=row_num, column=7, value=task.date_created.strftime('%d.%m.%Y %H:%M'))
            ws.cell(row=row_num, column=8, value=task.date_deadline.strftime('%d.%m.%Y %H:%M') if task.date_deadline else '')
            ws.cell(row=row_num, column=9, value=projects_str)
            ws.cell(row=row_num, column=10, value=task.comments.filter(is_deleted=False).count())
            ws.cell(row=row_num, column=11, value=task.attachments.count())
        
        # Автоширина столбцов
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="tasks_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        wb.save(response)
        
        return response


@login_required
def task_search_autocomplete(request):
    """Поиск с автодополнением"""
    query = request.GET.get('q', '')
    search_type = request.GET.get('type', 'all')  # all, title, author, assignee
    
    if not query or len(query) < 2:
        return JsonResponse({'results': []})
    
    results = []
    
    if search_type in ['all', 'title']:
        # Поиск по названию задач
        tasks = HelpDeskTask.objects.filter(
            is_deleted=False,
            title__icontains=query
        )[:10]
        
        for task in tasks:
            results.append({
                'type': 'task',
                'id': task.id,
                'text': f"#{task.id} - {task.title}",
                'url': reverse('helpdesk:task_detail', kwargs={'pk': task.id}),
            })
    
    if search_type in ['all', 'author', 'assignee']:
        # Поиск по пользователям
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        ).filter(is_active=True)[:10]
        
        for user in users:
            user_name = user.get_full_name() or user.username
            results.append({
                'type': 'user',
                'id': user.id,
                'text': user_name,
                'username': user.username,
            })
    
    return JsonResponse({'results': results})


@login_required
def task_reports(request):
    """Отчеты по задачам"""
    tasks = HelpDeskTask.objects.filter(is_deleted=False)
    
    # Фильтрация для обычных пользователей
    if not request.user.is_superuser:
        tasks = tasks.filter(
            Q(author=request.user) | 
            Q(assignee=request.user) | 
            Q(observers=request.user)
        ).distinct()
    
    # Период для отчета
    period = request.GET.get('period', 'month')
    end_date = timezone.now().date()
    
    if period == 'week':
        start_date = end_date - timedelta(days=7)
    elif period == 'month':
        start_date = end_date - timedelta(days=30)
    elif period == 'quarter':
        start_date = end_date - timedelta(days=90)
    else:  # year
        start_date = end_date - timedelta(days=365)
    
    tasks_in_period = tasks.filter(date_created__date__gte=start_date)
    
    # Отчет по исполнителям
    assignee_report = tasks_in_period.filter(assignee__isnull=False).values(
        'assignee__username', 'assignee__first_name', 'assignee__last_name'
    ).annotate(
        total=Count('id'),
        closed=Count('id', filter=Q(status__is_closed=True)),
        overdue=Count('id', filter=Q(date_deadline__lt=timezone.now(), status__is_closed=False)),
        avg_time=Avg('actual_time'),
    ).order_by('-total')
    
    # Отчет по проектам
    project_report = tasks_in_period.values('projects__name', 'projects__id').annotate(
        total=Count('id', distinct=True),
        closed=Count('id', filter=Q(status__is_closed=True), distinct=True),
    ).exclude(projects__id__isnull=True).order_by('-total')
    
    # Воронка выполнения
    funnel = {
        'created': tasks_in_period.count(),
        'in_progress': tasks_in_period.filter(status__is_closed=False).exclude(status__isnull=True).count(),
        'closed': tasks_in_period.filter(status__is_closed=True).count(),
        'overdue': tasks_in_period.filter(date_deadline__lt=timezone.now(), status__is_closed=False).count(),
    }
    
    # Среднее время выполнения
    closed_tasks = tasks_in_period.filter(date_closed__isnull=False)
    avg_completion_time = None
    if closed_tasks.exists():
        total_seconds = 0
        count = 0
        for task in closed_tasks:
            if task.date_created and task.date_closed:
                delta = task.date_closed - task.date_created
                total_seconds += delta.total_seconds()
                count += 1
        if count > 0:
            avg_seconds = total_seconds / count
            avg_completion_time = timedelta(seconds=avg_seconds)
    
    params = {
        'period': period,
        'start_date': start_date,
        'end_date': end_date,
        'assignee_report': list(assignee_report),
        'project_report': list(project_report),
        'funnel': funnel,
        'avg_completion_time': avg_completion_time,
        'total_tasks': tasks_in_period.count(),
    }
    
    return render(request, "help_desk/reports.html", {'params': params})
