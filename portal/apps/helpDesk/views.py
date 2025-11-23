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
from functools import wraps
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from .models import (HelpDeskTask, TaskStatus, Priority, ProjectTag, TaskComment, 
                     TaskAttachment, TaskHistory, SavedFilter, DeadlineReminder, TaskRule)
from .utils import send_task_notification


def ajax_login_required(view_func):
    """Декоратор для AJAX запросов, возвращает JSON вместо редиректа"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Требуется авторизация'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


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
    
    # Получаем статусы для быстрых действий
    all_statuses = TaskStatus.objects.filter(is_active=True).order_by('order')
    
    # Находим статус "В работе"
    in_progress_status = None
    for status in all_statuses:
        if 'работа' in status.name.lower() or status.code.lower() in ['in_progress', 'work', 'в_работе']:
            in_progress_status = status
            break
    
    # Если не нашли, берем первый не закрытый статус
    if not in_progress_status:
        in_progress_status = all_statuses.filter(is_closed=False).first()
    
    # Находим статус "Закрыто"
    closed_status = all_statuses.filter(is_closed=True).first()
    
    # Данные для виджета быстрого создания
    users = User.objects.filter(is_active=True).order_by('username')
    priorities = Priority.objects.all().order_by('-level')
    projects = ProjectTag.objects.filter(is_active=True).order_by('order', 'name')
    
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
        'in_progress_status': in_progress_status,
        'closed_status': closed_status,
        'users': users,
        'priorities': priorities,
        'projects': projects,
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
    
    # Получаем статусы для быстрых действий
    all_statuses = TaskStatus.objects.filter(is_active=True).order_by('order')
    
    # Находим статус "В работе"
    in_progress_status = None
    for status in all_statuses:
        if 'работа' in status.name.lower() or status.code.lower() in ['in_progress', 'work', 'в_работе']:
            in_progress_status = status
            break
    
    # Если не нашли, берем первый не закрытый статус
    if not in_progress_status:
        in_progress_status = all_statuses.filter(is_closed=False).first()
    
    # Находим статус "Закрыто"
    closed_status = all_statuses.filter(is_closed=True).first()
    
    # Получаем сохраненные фильтры пользователя
    saved_filters = SavedFilter.objects.filter(
        Q(user=request.user) | Q(is_shared=True)
    ).order_by('order', 'name')
    
    # Применяем сохраненный фильтр, если указан
    saved_filter_id = request.GET.get('saved_filter')
    if saved_filter_id:
        try:
            saved_filter_obj = SavedFilter.objects.filter(
                Q(id=int(saved_filter_id)) & (Q(user=request.user) | Q(is_shared=True))
            ).get()
            
            # Проверяем, нужно ли применять фильтр (если параметры уже все есть, не делаем редирект)
            need_redirect = False
            filter_params = request.GET.copy()
            
            # Добавляем параметры из сохраненного фильтра, если их нет
            for key, value in saved_filter_obj.filter_data.items():
                if key not in filter_params or filter_params[key] != str(value):
                    filter_params[key] = str(value)
                    need_redirect = True
            
            # Убеждаемся, что saved_filter в параметрах
            if 'saved_filter' not in filter_params or filter_params['saved_filter'] != saved_filter_id:
                filter_params['saved_filter'] = saved_filter_id
                need_redirect = True
            
            # Делаем редирект только если нужно применить недостающие параметры
            if need_redirect:
                return redirect(f"{reverse('helpdesk:task_list')}?{filter_params.urlencode()}")
            
            # Если редирект не нужен, применяем фильтры напрямую к tasks
            for key, value in saved_filter_obj.filter_data.items():
                if key == 'nomer' and value:
                    try:
                        tasks = tasks.filter(id=int(value))
                    except:
                        pass
                elif key == 'status' and value:
                    try:
                        tasks = tasks.filter(status_id=int(value))
                    except:
                        pass
                elif key == 'priority' and value:
                    try:
                        tasks = tasks.filter(priority_id=int(value))
                    except:
                        pass
                elif key == 'author' and value:
                    try:
                        tasks = tasks.filter(author_id=int(value))
                    except:
                        pass
                elif key == 'assignee' and value:
                    try:
                        tasks = tasks.filter(assignee_id=int(value))
                    except:
                        pass
                elif key == 'project' and value:
                    try:
                        tasks = tasks.filter(projects__id=int(value))
                    except:
                        pass
                elif key == 'date' and value:
                    try:
                        date_obj = datetime.strptime(value, '%Y-%m-%d').date()
                        tasks = tasks.filter(date_created__date__gte=date_obj)
                    except:
                        pass
                elif key == 'date_end' and value:
                    try:
                        date_obj = datetime.strptime(value, '%Y-%m-%d').date()
                        tasks = tasks.filter(date_created__date__lte=date_obj)
                    except:
                        pass
                elif key == 'search' and value:
                    tasks = tasks.filter(
                        Q(title__icontains=value) | 
                        Q(description__icontains=value)
                    )
                elif key == 'my' and value:
                    tasks = tasks.filter(assignee=request.user)
                elif key == 'overdue' and value:
                    tasks = tasks.filter(
                        status__is_closed=False,
                        date_deadline__lt=timezone.now()
                    )
                elif key == 'closed_today' and value:
                    today = timezone.now().date()
                    tasks = tasks.filter(date_closed__date=today)
        except:
            pass
    
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
        'in_progress_status': in_progress_status,
        'closed_status': closed_status,
        'saved_filters': saved_filters,
        'users': User.objects.filter(is_active=True).order_by('username'),
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
    
    # Создаем объединенный Timeline (история + комментарии)
    timeline_items = []
    
    # Добавляем создание задачи в Timeline
    timeline_items.append({
        'type': 'created',
        'date': task.date_created,
        'user': task.author,
        'action': 'Задача создана',
        'data': {
            'title': task.title,
        }
    })
    
    # Добавляем историю изменений
    for item in history:
        timeline_items.append({
            'type': 'history',
            'date': item.date_created,
            'user': item.user,
            'action': item.action,
            'field_name': item.field_name,
            'old_value': item.old_value,
            'new_value': item.new_value,
            'comment': item.comment,
        })
    
    # Добавляем комментарии
    for comment in comments:
        timeline_items.append({
            'type': 'comment',
            'date': comment.date_created,
            'user': comment.author,
            'action': 'Добавлен комментарий',
            'text': comment.text,
            'is_internal': comment.is_internal,
        })
    
    # Добавляем вложения
    for attachment in attachments:
        timeline_items.append({
            'type': 'attachment',
            'date': attachment.date_uploaded,
            'user': attachment.uploaded_by,
            'action': 'Добавлено вложение',
            'filename': attachment.original_filename,
            'file_url': attachment.file.url,
            'description': attachment.description,
        })
    
    # Сортируем по дате (от новых к старым)
    timeline_items.sort(key=lambda x: x['date'], reverse=True)
    
    # Группируем по датам для отображения
    from collections import defaultdict
    from datetime import datetime
    timeline_by_date = defaultdict(list)
    for item in timeline_items:
        date_key = item['date'].date().strftime('%d.%m.%Y')
        timeline_by_date[date_key].append(item)
    
    # Преобразуем в список кортежей (дата, список элементов) и сортируем по дате (от новых к старым)
    timeline_grouped = sorted(timeline_by_date.items(), 
                             key=lambda x: datetime.strptime(x[0], '%d.%m.%Y'), 
                             reverse=True)
    
    # Получаем статусы для быстрых действий
    all_statuses = TaskStatus.objects.filter(is_active=True).order_by('order')
    
    # Находим статус "В работе" (по коду или названию)
    in_progress_status = None
    for status in all_statuses:
        if 'работа' in status.name.lower() or status.code.lower() in ['in_progress', 'work', 'в_работе']:
            in_progress_status = status
            break
    
    # Если не нашли, берем первый не закрытый статус
    if not in_progress_status:
        in_progress_status = all_statuses.filter(is_closed=False).exclude(id=task.status.id if task.status else None).first()
    
    # Находим статус "Закрыто" (закрывающий статус)
    closed_status = all_statuses.filter(is_closed=True).first()
    
    # Данные для виджета быстрого создания
    users = User.objects.filter(is_active=True).order_by('username')
    priorities = Priority.objects.all().order_by('-level')
    projects = ProjectTag.objects.filter(is_active=True).order_by('order', 'name')
    
    # Получаем напоминания о дедлайне для текущего пользователя
    deadline_reminders = task.reminders.filter(user=request.user).order_by('days_before')
    
    params = {
        'task': task,
        'comments': comments,
        'attachments': attachments,
        'history': history,
        'timeline': timeline_items,
        'timeline_grouped': timeline_grouped,
        'in_progress_status': in_progress_status,
        'closed_status': closed_status,
        'all_statuses': all_statuses,
        'users': users,
        'priorities': priorities,
        'projects': projects,
        'deadline_reminders': deadline_reminders,
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


@csrf_exempt
@ajax_login_required
def task_quick_status_change(request, pk):
    """Быстрое изменение статуса задачи"""
    
    # Проверяем, что это POST запрос
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Неверный метод запроса'}, status=400)
    
    # Проверяем CSRF токен вручную для AJAX запросов
    # Поскольку мы используем @csrf_exempt, проверяем токен вручную
    from django.conf import settings
    
    csrf_token_from_header = request.headers.get('X-CSRFToken') or request.POST.get('csrfmiddlewaretoken')
    csrf_token_from_cookie = request.COOKIES.get(settings.CSRF_COOKIE_NAME, '')
    
    # Базовая проверка наличия токенов
    if not csrf_token_from_header:
        return JsonResponse({'success': False, 'error': 'CSRF токен не найден в запросе. Обновите страницу.'}, status=403)
    
    if not csrf_token_from_cookie:
        return JsonResponse({'success': False, 'error': 'CSRF токен не найден в cookies. Обновите страницу.'}, status=403)
    
    # Django использует замаскированные токены, поэтому простое сравнение может не работать
    # Но для базовой проверки достаточно убедиться, что оба токена присутствуют
    # В production можно использовать стандартную проверку CSRF через middleware
    
    try:
        # Получаем задачу, возвращаем JSON при ошибке вместо HTML
        try:
            task = HelpDeskTask.objects.get(pk=pk, is_deleted=False)
        except HelpDeskTask.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Задача не найдена'}, status=404)
        
        # Проверка прав доступа
        if not request.user.is_superuser:
            if task.author != request.user and task.assignee != request.user:
                if not task.observers.filter(id=request.user.id).exists():
                    return JsonResponse({'success': False, 'error': 'Нет доступа к задаче'}, status=403)
        
        status_id = request.POST.get('status_id')
        if not status_id:
            return JsonResponse({'success': False, 'error': 'Не указан статус'}, status=400)
        
        try:
            status_id_int = int(status_id)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Неверный формат ID статуса'}, status=400)
        
        # Получаем статус, возвращаем JSON при ошибке
        try:
            new_status = TaskStatus.objects.get(id=status_id_int, is_active=True)
        except TaskStatus.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Статус не найден'}, status=404)
        
        old_status = task.status
        
        # Сохраняем старый статус для истории
        old_status_name = old_status.name if old_status else 'Не указан'
        
        # Изменяем статус
        task.status = new_status
        
        # Если статус закрыт, устанавливаем дату закрытия
        if new_status.is_closed and not task.date_closed:
            task.date_closed = timezone.now()
        # Если статус не закрыт, сбрасываем дату закрытия
        elif not new_status.is_closed:
            task.date_closed = None
        
        # Если статус "В работе" и нет даты начала, устанавливаем её
        if not task.date_start:
            # Проверяем, является ли новый статус статусом "в работе"
            # (обычно это статус, который не закрыт и не является начальным)
            if not new_status.is_closed:
                task.date_start = timezone.now()
        
        task.save()
        
        # Создаем запись в истории
        TaskHistory.objects.create(
            task=task,
            user=request.user,
            action=f'Быстрое изменение статуса: {old_status_name} → {new_status.name}',
        )
        
        # Отправляем уведомление об изменении статуса
        try:
            send_task_notification(
                task=task,
                action_type='status_changed',
                changed_by=request.user,
                old_status=old_status,
                new_status=new_status,
                request=request
            )
        except Exception as e:
            # Логируем ошибку отправки уведомления, но не прерываем выполнение
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Ошибка отправки уведомления: {str(e)}')
        
        return JsonResponse({
            'success': True,
            'status': new_status.name,
            'status_color': new_status.color if new_status.color else '#6c757d',
            'message': f'Статус изменен на: {new_status.name}'
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception('Ошибка при изменении статуса задачи')
        return JsonResponse({'success': False, 'error': f'Ошибка при изменении статуса: {str(e)}'}, status=500)


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
        'assignee__username', 'assignee__first_name', 'assignee__last_name'
    ).annotate(
        count=Count('id'),
        closed=Count('id', filter=Q(status__is_closed=True))
    ).order_by('-count')[:10]
    
    # Статистика по авторам
    author_stats = tasks.values(
        'author__username', 'author__first_name', 'author__last_name'
    ).annotate(
        count=Count('id'),
        closed=Count('id', filter=Q(status__is_closed=True))
    ).order_by('-count')[:10]
    
    # Общая статистика
    total_tasks = tasks.count()
    closed_tasks = tasks.filter(status__is_closed=True).count()
    open_tasks = total_tasks - closed_tasks
    overdue_tasks = tasks.filter(
        status__is_closed=False,
        date_deadline__lt=timezone.now()
    ).count()
    tasks_without_assignee = tasks.filter(assignee__isnull=True).count()
    
    # Среднее время выполнения (для закрытых задач)
    closed_tasks_with_dates = tasks.filter(
        status__is_closed=True,
        date_created__isnull=False,
        date_closed__isnull=False
    )
    avg_completion_time = None
    if closed_tasks_with_dates.exists():
        total_days = 0
        count = 0
        for task in closed_tasks_with_dates:
            if task.date_created and task.date_closed:
                delta = task.date_closed - task.date_created
                total_days += delta.total_seconds() / 86400  # дни
                count += 1
        if count > 0:
            avg_completion_time = round(total_days / count, 1)
    
    # Воронка выполнения (по статусам в порядке workflow)
    funnel_data = []
    for status in TaskStatus.objects.filter(is_active=True).order_by('order'):
        count = tasks.filter(status=status).count()
        if count > 0:
            funnel_data.append({
                'name': status.name,
                'count': count,
                'color': status.color
            })
    
    # Статистика по срокам выполнения
    tasks_with_deadline = tasks.filter(date_deadline__isnull=False)
    on_time_tasks = tasks_with_deadline.filter(
        Q(status__is_closed=True) & Q(date_closed__lte=F('date_deadline'))
    ).count()
    late_tasks = tasks_with_deadline.filter(
        Q(status__is_closed=True) & Q(date_closed__gt=F('date_deadline'))
    ).count()
    
    statuses = TaskStatus.objects.filter(is_active=True).order_by('order')
    priorities = Priority.objects.all().order_by('-level')
    users = User.objects.filter(is_active=True).order_by('username')
    projects = ProjectTag.objects.filter(is_active=True).order_by('order', 'name')

    params = {
        'period': period,
        'status_stats': json.dumps(list(status_stats)),
        'priority_stats': json.dumps(list(priority_stats)),
        'project_stats': json.dumps(project_stats),
        'creation_data': json.dumps(creation_data),
        'closure_data': json.dumps(closure_data),
        'assignee_stats': json.dumps(list(assignee_stats)),
        'author_stats': json.dumps(list(author_stats)),
        'funnel_data': json.dumps(funnel_data),
        'filters': filters,
        'statuses': statuses,
        'priorities': priorities,
        'users': users,
        'projects': projects,
        # Общая статистика
        'total_tasks': total_tasks,
        'closed_tasks': closed_tasks,
        'open_tasks': open_tasks,
        'overdue_tasks': overdue_tasks,
        'tasks_without_assignee': tasks_without_assignee,
        'avg_completion_time': avg_completion_time,
        'on_time_tasks': on_time_tasks,
        'late_tasks': late_tasks,
        'tasks_with_deadline': tasks_with_deadline.count(),
    }
    
    return render(request, "help_desk/chart.html", {'params': params})


@login_required
def task_quick_status_change(request, pk):
    """Быстрое изменение статуса задачи"""
    task = get_object_or_404(HelpDeskTask, pk=pk, is_deleted=False)
    
    # Проверка прав
    if not request.user.is_superuser:
        if task.author != request.user and task.assignee != request.user:
            return JsonResponse({'error': 'Нет доступа'}, status=403)
    
    if request.method == 'POST':
        new_status_id = request.POST.get('status_id')
        if new_status_id:
            try:
                old_status = task.status
                new_status = TaskStatus.objects.get(id=int(new_status_id))
                
                if old_status != new_status:
                    task.status = new_status
                    
                    # Если статус закрывающий, устанавливаем дату закрытия
                    if new_status.is_closed and not task.date_closed:
                        task.date_closed = timezone.now()
                    elif not new_status.is_closed:
                        task.date_closed = None
                    
                    task.save()
                    
                    # Запись в историю
                    TaskHistory.objects.create(
                        task=task,
                        user=request.user,
                        action='Быстрое изменение статуса',
                        field_name='status',
                        old_value=str(old_status) if old_status else '',
                        new_value=str(new_status),
                    )
                    
                    # Отправляем уведомление
                    send_task_notification(
                        task=task,
                        action_type='status_changed',
                        changed_by=request.user,
                        changes={'old_status': str(old_status) if old_status else '', 'new_status': str(new_status)},
                        request=request
                    )
                    
                    return JsonResponse({'success': True, 'status': new_status.name, 'status_color': new_status.color})
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Неверный запрос'}, status=400)


@login_required
def task_duplicate(request, pk):
    """Дублирование задачи"""
    original_task = get_object_or_404(HelpDeskTask, pk=pk, is_deleted=False)
    
    # Проверка прав
    if not request.user.is_superuser:
        if original_task.author != request.user:
            return HttpResponseRedirect('/help_desk/')
    
    if request.method == 'POST':
        # Создаем копию задачи
        new_task = HelpDeskTask()
        new_task.title = f"Копия: {original_task.title}"
        new_task.description = original_task.description
        new_task.author = request.user
        
        # Исполнитель и статус не копируем (нужно будет установить заново)
        # Приоритет и проекты копируем
        new_task.priority = original_task.priority
        
        # Устанавливаем первый статус по умолчанию
        new_task.status = TaskStatus.objects.filter(is_active=True).order_by('order').first()
        
        # Временные рамки не копируем
        new_task.tags = original_task.tags
        new_task.save()
        
        # Копируем проекты
        for project in original_task.projects.all():
            new_task.projects.add(project)
        
        # Копируем наблюдателей
        for observer in original_task.observers.all():
            new_task.observers.add(observer)
        
        # Запись в историю
        TaskHistory.objects.create(
            task=new_task,
            user=request.user,
            action='Создана копия задачи',
            comment=f'Копия задачи #{original_task.id}'
        )
        
        # Отправляем уведомление
        send_task_notification(
            task=new_task,
            action_type='task_created',
            changed_by=request.user,
            request=request
        )
        
        return redirect('helpdesk:task_detail', pk=new_task.pk)
    
    return redirect('helpdesk:task_detail', pk=original_task.pk)


@login_required
def save_filter(request):
    """Сохранение фильтра"""
    if request.method == 'POST':
        filter_name = request.POST.get('name', '')
        filter_data = {}
        
        # Собираем данные фильтра из POST
        for key in ['nomer', 'status', 'priority', 'project', 'author', 'assignee', 
                   'date', 'date_end', 'search', 'order_by']:
            value = request.POST.get(key, '')
            if value:
                filter_data[key] = value
        
        if filter_name:
            try:
                saved_filter = SavedFilter.objects.get(user=request.user, name=filter_name)
                saved_filter.filter_data = filter_data
                saved_filter.save()
                return JsonResponse({'success': True, 'message': 'Фильтр обновлен'})
            except SavedFilter.DoesNotExist:
                SavedFilter.objects.create(
                    user=request.user,
                    name=filter_name,
                    filter_data=filter_data
                )
                return JsonResponse({'success': True, 'message': 'Фильтр сохранен'})
    
    return JsonResponse({'error': 'Неверный запрос'}, status=400)


@login_required
def delete_saved_filter(request, filter_id):
    """Удаление сохраненного фильтра"""
    if request.method == 'POST':
        try:
            saved_filter = SavedFilter.objects.get(id=filter_id, user=request.user)
            saved_filter.delete()
            return JsonResponse({'success': True, 'message': 'Фильтр удален'})
        except SavedFilter.DoesNotExist:
            return JsonResponse({'error': 'Фильтр не найден'}, status=404)
    
    return JsonResponse({'error': 'Неверный запрос'}, status=400)


@login_required
def export_tasks(request):
    """Экспорт задач в Excel/CSV"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    from django.http import HttpResponse
    
    tasks = HelpDeskTask.objects.filter(is_deleted=False)
    
    # Применяем те же фильтры, что и в task_list
    if not request.user.is_superuser:
        tasks = tasks.filter(
            Q(author=request.user) | 
            Q(assignee=request.user) | 
            Q(observers=request.user)
        ).distinct()
    
    # Применяем все фильтры из GET параметров (аналогично task_list)
    # Фильтр по номеру
    nomer = request.GET.get('nomer', '')
    if nomer:
        try:
            tasks = tasks.filter(id=int(nomer))
        except:
            pass
    
    # Фильтр по статусу
    status_id = request.GET.get('status', '')
    if status_id:
        try:
            tasks = tasks.filter(status_id=int(status_id))
        except:
            pass
    
    # Фильтр по приоритету
    priority_id = request.GET.get('priority', '')
    if priority_id:
        try:
            tasks = tasks.filter(priority_id=int(priority_id))
        except:
            pass
    
    # Фильтр по автору
    author_id = request.GET.get('author', '')
    if author_id:
        try:
            tasks = tasks.filter(author_id=int(author_id))
        except:
            pass
    
    # Фильтр по исполнителю
    assignee_id = request.GET.get('assignee', '')
    if assignee_id:
        try:
            tasks = tasks.filter(assignee_id=int(assignee_id))
        except:
            pass
    
    # Фильтр по дате от
    date_start = request.GET.get('date', '')
    if date_start:
        try:
            date_obj = datetime.strptime(date_start, '%Y-%m-%d').date()
            tasks = tasks.filter(date_created__date__gte=date_obj)
        except:
            pass
    
    # Фильтр по дате до
    date_end = request.GET.get('date_end', '')
    if date_end:
        try:
            date_obj = datetime.strptime(date_end, '%Y-%m-%d').date()
            tasks = tasks.filter(date_created__date__lte=date_obj)
        except:
            pass
    
    # Фильтр по проекту
    project_id = request.GET.get('project', '')
    if project_id:
        try:
            tasks = tasks.filter(projects__id=int(project_id))
        except:
            pass
    
    # Поиск по тексту
    search = request.GET.get('search', '')
    if search:
        tasks = tasks.filter(
            Q(title__icontains=search) | 
            Q(description__icontains=search)
        )
    
    # Фильтр: только мои задачи
    only_my = request.GET.get('my')
    if only_my:
        tasks = tasks.filter(assignee=request.user)
    
    # Фильтр: просроченные
    overdue_flag = request.GET.get('overdue')
    if overdue_flag:
        tasks = tasks.filter(
            status__is_closed=False,
            date_deadline__lt=timezone.now()
        )
    
    # Фильтр: закрытые сегодня
    closed_today = request.GET.get('closed_today')
    if closed_today:
        today = timezone.now().date()
        tasks = tasks.filter(date_closed__date=today)
    
    # Применяем сохраненный фильтр, если указан
    saved_filter_id = request.GET.get('saved_filter')
    if saved_filter_id:
        try:
            saved_filter_obj = SavedFilter.objects.filter(
                Q(id=int(saved_filter_id)) & (Q(user=request.user) | Q(is_shared=True))
            ).get()
            # Применяем параметры фильтра
            for key, value in saved_filter_obj.filter_data.items():
                if key == 'nomer' and value:
                    try:
                        tasks = tasks.filter(id=int(value))
                    except:
                        pass
                elif key == 'status' and value:
                    try:
                        tasks = tasks.filter(status_id=int(value))
                    except:
                        pass
                elif key == 'priority' and value:
                    try:
                        tasks = tasks.filter(priority_id=int(value))
                    except:
                        pass
                elif key == 'author' and value:
                    try:
                        tasks = tasks.filter(author_id=int(value))
                    except:
                        pass
                elif key == 'assignee' and value:
                    try:
                        tasks = tasks.filter(assignee_id=int(value))
                    except:
                        pass
                elif key == 'project' and value:
                    try:
                        tasks = tasks.filter(projects__id=int(value))
                    except:
                        pass
                elif key == 'date' and value:
                    try:
                        date_obj = datetime.strptime(value, '%Y-%m-%d').date()
                        tasks = tasks.filter(date_created__date__gte=date_obj)
                    except:
                        pass
                elif key == 'date_end' and value:
                    try:
                        date_obj = datetime.strptime(value, '%Y-%m-%d').date()
                        tasks = tasks.filter(date_created__date__lte=date_obj)
                    except:
                        pass
                elif key == 'search' and value:
                    tasks = tasks.filter(
                        Q(title__icontains=value) | 
                        Q(description__icontains=value)
                    )
                elif key == 'my' and value:
                    tasks = tasks.filter(assignee=request.user)
                elif key == 'overdue' and value:
                    tasks = tasks.filter(
                        status__is_closed=False,
                        date_deadline__lt=timezone.now()
                    )
                elif key == 'closed_today' and value:
                    today = timezone.now().date()
                    tasks = tasks.filter(date_closed__date=today)
        except:
            pass
    
    format_type = request.GET.get('format', 'xlsx')
    
    if format_type == 'csv':
        import csv
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="tasks_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Тема', 'Автор', 'Исполнитель', 'Статус', 'Приоритет', 
                        'Дата создания', 'Срок выполнения', 'Проекты'])
        
        for task in tasks:
            projects = ', '.join([p.name for p in task.projects.all()])
            writer.writerow([
                task.id,
                task.title,
                task.author.get_full_name() or task.author.username,
                task.assignee.get_full_name() if task.assignee else 'Не назначен',
                task.status.name if task.status else '',
                task.priority.name if task.priority else '',
                task.date_created.strftime('%d.%m.%Y %H:%M'),
                task.date_deadline.strftime('%d.%m.%Y %H:%M') if task.date_deadline else '',
                projects
            ])
        
        return response
    
    else:  # xlsx
        wb = Workbook()
        ws = wb.active
        ws.title = "Задачи"
        
        # Заголовки
        headers = ['ID', 'Тема', 'Автор', 'Исполнитель', 'Статус', 'Приоритет', 
                  'Дата создания', 'Срок выполнения', 'Проекты', 'Комментарии', 'Вложения']
        
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Данные
        for row, task in enumerate(tasks, 2):
            projects = ', '.join([p.name for p in task.projects.all()])
            comments_count = task.comments.filter(is_deleted=False).count()
            attachments_count = task.attachments.count()
            
            ws.cell(row=row, column=1, value=task.id)
            ws.cell(row=row, column=2, value=task.title)
            ws.cell(row=row, column=3, value=task.author.get_full_name() or task.author.username)
            ws.cell(row=row, column=4, value=task.assignee.get_full_name() if task.assignee else 'Не назначен')
            ws.cell(row=row, column=5, value=task.status.name if task.status else '')
            ws.cell(row=row, column=6, value=task.priority.name if task.priority else '')
            ws.cell(row=row, column=7, value=task.date_created.strftime('%d.%m.%Y %H:%M'))
            ws.cell(row=row, column=8, value=task.date_deadline.strftime('%d.%m.%Y %H:%M') if task.date_deadline else '')
            ws.cell(row=row, column=9, value=projects)
            ws.cell(row=row, column=10, value=comments_count)
            ws.cell(row=row, column=11, value=attachments_count)
        
        # Автоподбор ширины столбцов
        for col in range(1, len(headers) + 1):
            column_letter = get_column_letter(col)
            max_length = 0
            for cell in ws[column_letter]:
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
def task_quick_create(request):
    """Быстрое создание задачи через AJAX"""
    if request.method == 'POST':
        try:
            # Создаем задачу
            task = HelpDeskTask()
            task.title = request.POST.get('title', '').strip()
            
            if not task.title:
                return JsonResponse({'error': 'Тема задачи обязательна'}, status=400)
            
            task.description = request.POST.get('description', '')
            task.author = request.user
            
            # Исполнитель
            assignee_id = request.POST.get('assignee', '')
            if assignee_id:
                try:
                    task.assignee = User.objects.get(id=int(assignee_id))
                except:
                    pass
            
            # Статус - берем первый по умолчанию
            task.status = TaskStatus.objects.filter(is_active=True).order_by('order').first()
            
            # Приоритет
            priority_id = request.POST.get('priority', '')
            if priority_id:
                try:
                    task.priority = Priority.objects.get(id=int(priority_id))
                except:
                    pass
            
            task.save()
            
            # Проекты
            project_ids = request.POST.getlist('projects')
            for project_id in project_ids:
                try:
                    project = ProjectTag.objects.get(id=int(project_id))
                    task.projects.add(project)
                except:
                    pass
            
            # Запись в историю
            TaskHistory.objects.create(
                task=task,
                user=request.user,
                action='Создана задача',
            )
            
            # Отправляем уведомление
            send_task_notification(
                task=task,
                action_type='task_created',
                changed_by=request.user,
                request=request
            )
            
            return JsonResponse({
                'success': True,
                'task_id': task.id,
                'task_url': reverse('helpdesk:task_detail', kwargs={'pk': task.id}),
                'message': 'Задача успешно создана'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Неверный запрос'}, status=400)


@login_required
def task_autocomplete(request):
    """Автодополнение для поиска задач"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    tasks = HelpDeskTask.objects.filter(is_deleted=False)
    
    # Фильтрация для обычных пользователей
    if not request.user.is_superuser:
        tasks = tasks.filter(
            Q(author=request.user) | 
            Q(assignee=request.user) | 
            Q(observers=request.user)
        ).distinct()
    
    # Поиск по названию, автору, исполнителю
    tasks = tasks.filter(
        Q(title__icontains=query) |
        Q(author__username__icontains=query) |
        Q(author__first_name__icontains=query) |
        Q(author__last_name__icontains=query) |
        Q(assignee__username__icontains=query) |
        Q(assignee__first_name__icontains=query) |
        Q(assignee__last_name__icontains=query)
    )[:10]
    
    results = []
    for task in tasks:
        results.append({
            'id': task.id,
            'text': f"#{task.id} - {task.title}",
            'title': task.title,
            'author': task.author.get_full_name() or task.author.username,
            'assignee': task.assignee.get_full_name() if task.assignee else 'Не назначен',
            'status': task.status.name if task.status else '',
            'url': reverse('helpdesk:task_detail', kwargs={'pk': task.pk})
        })
    
    return JsonResponse({'results': results})


@login_required
def add_deadline_reminder(request, pk):
    """Добавление напоминания о дедлайне"""
    task = get_object_or_404(HelpDeskTask, pk=pk, is_deleted=False)
    
    # Проверка прав
    if not request.user.is_superuser:
        if task.author != request.user and task.assignee != request.user:
            if not task.observers.filter(id=request.user.id).exists():
                return JsonResponse({'error': 'Нет доступа'}, status=403)
    
    if request.method == 'POST':
        if not task.date_deadline:
            return JsonResponse({'error': 'У задачи не установлен дедлайн'}, status=400)
        
        days_before = request.POST.get('days_before', '1')
        try:
            days_before = int(days_before)
            if days_before < 1:
                days_before = 1
        except:
            days_before = 1
        
        # Создаем или обновляем напоминание
        reminder, created = DeadlineReminder.objects.get_or_create(
            task=task,
            user=request.user,
            days_before=days_before,
            defaults={'is_sent': False}
        )
        
        if not created:
            reminder.is_sent = False
            reminder.date_sent = None
            reminder.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Напоминание добавлено',
            'reminder_id': reminder.id,
            'days_before': reminder.days_before
        })
    
    return JsonResponse({'error': 'Неверный запрос'}, status=400)


@login_required
def delete_deadline_reminder(request, pk, reminder_id):
    """Удаление напоминания о дедлайне"""
    task = get_object_or_404(HelpDeskTask, pk=pk, is_deleted=False)
    
    if request.method == 'POST':
        try:
            reminder = DeadlineReminder.objects.get(
                id=reminder_id,
                task=task,
                user=request.user
            )
            reminder.delete()
            return JsonResponse({'success': True, 'message': 'Напоминание удалено'})
        except DeadlineReminder.DoesNotExist:
            return JsonResponse({'error': 'Напоминание не найдено'}, status=404)
    
    return JsonResponse({'error': 'Неверный запрос'}, status=400)
