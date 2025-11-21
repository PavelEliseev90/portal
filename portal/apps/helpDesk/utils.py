from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from django.utils.html import strip_tags


def send_task_notification(task, action_type, changed_by=None, comment=None, changes=None, request=None, reminder_days=None, recipient_user=None):
    """
    Отправка email-уведомлений о изменении задачи
    
    Args:
        task: Объект HelpDeskTask
        action_type: Тип действия ('status_changed', 'task_updated', 'comment_added', 'task_created', 'deadline_reminder')
        changed_by: Пользователь, который внес изменения
        comment: Комментарий (если есть)
        changes: Словарь с изменениями (если есть)
        request: HttpRequest объект для формирования абсолютного URL
        reminder_days: Количество дней до дедлайна (для напоминаний)
        recipient_user: Конкретный пользователь-получатель (для напоминаний)
    """
    # Получаем список получателей
    recipients = set()
    
    # Для напоминаний о дедлайнах отправляем только указанному пользователю
    if action_type == 'deadline_reminder' and recipient_user:
        if recipient_user.email:
            recipients.add(recipient_user.email)
    else:
        # Обычная логика: автор + наблюдатели + исполнитель
        if task.author and task.author.email:
            recipients.add(task.author.email)
        
        # Добавляем наблюдателей
        for observer in task.observers.all():
            if observer.email:
                recipients.add(observer.email)
        
        # Добавляем исполнителя
        if task.assignee and task.assignee.email:
            recipients.add(task.assignee.email)
        
        # Убираем из списка того, кто внес изменения (чтобы не отправлять самому себе)
        if changed_by and changed_by.email and changed_by.email in recipients:
            recipients.remove(changed_by.email)
    
    if not recipients:
        return  # Нет получателей
    
    # Формируем URL задачи
    if request:
        task_url = request.build_absolute_uri(f'/help_desk/task/{task.id}/')
    else:
        try:
            host = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost'
            if not host.startswith('http'):
                # Проверяем, используется ли HTTPS
                protocol = 'https' if getattr(settings, 'SECURE_SSL_REDIRECT', False) else 'http'
                host = f"{protocol}://{host}"
            task_url = f"{host}/help_desk/task/{task.id}/"
        except:
            task_url = f"http://localhost/help_desk/task/{task.id}/"
    
    # Подготовка контекста для шаблона
    context = {
        'task': task,
        'task_url': task_url,
        'action_type': action_type,
        'changed_by': changed_by,
        'comment': comment,
        'changes': changes or {},
        'reminder_days': reminder_days,
    }
    
    # Определяем тему письма в зависимости от типа действия
    if action_type == 'status_changed':
        subject = f'[HelpDesk] Изменен статус задачи #{task.id}: {task.title}'
        template_name = 'help_desk/emails/status_changed.html'
    elif action_type == 'comment_added':
        subject = f'[HelpDesk] Новый комментарий к задаче #{task.id}: {task.title}'
        template_name = 'help_desk/emails/comment_added.html'
    elif action_type == 'task_updated':
        subject = f'[HelpDesk] Обновлена задача #{task.id}: {task.title}'
        template_name = 'help_desk/emails/task_updated.html'
    elif action_type == 'task_created':
        subject = f'[HelpDesk] Создана новая задача #{task.id}: {task.title}'
        template_name = 'help_desk/emails/task_created.html'
    elif action_type == 'deadline_reminder':
        subject = f'[HelpDesk] Напоминание: Дедлайн задачи #{task.id}: {task.title}'
        template_name = 'help_desk/emails/deadline_reminder.html'
    else:
        subject = f'[HelpDesk] Уведомление о задаче #{task.id}: {task.title}'
        template_name = 'help_desk/emails/task_notification.html'
    
    # Рендерим HTML-версию письма
    html_message = render_to_string(template_name, context)
    
    # Создаем текстовую версию (убираем HTML теги)
    text_message = strip_tags(html_message)
    
    # Отправляем письма
    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.EMAIL_HOST_USER_INFO or settings.EMAIL_HOST_USER,
            to=list(recipients),
        )
        email.attach_alternative(html_message, "text/html")
        email.send()
    except Exception as e:
        # Логируем ошибку, но не прерываем выполнение
        print(f"Ошибка отправки email для задачи #{task.id}: {e}")

