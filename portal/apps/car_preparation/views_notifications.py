"""
Views для работы с уведомлениями
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
from .models import CarPreparationNotification
from refs.models import RefStaff


@login_required
def notifications_list(request):
    """Список уведомлений пользователя"""
    # Получаем профиль пользователя
    user = request.user
    staff = getattr(user, 'staff', None)
    
    if not staff:
        # Если нет привязки к сотруднику, показываем пустой список
        notifications = CarPreparationNotification.objects.none()
    else:
        # Фильтруем уведомления для текущего пользователя
        notifications = CarPreparationNotification.objects.filter(
            recipient=staff
        ).select_related(
            'preparation', 'preparation__car', 'work_item', 
            'work_item__work', 'work_schedule'
        ).order_by('-date_created')
    
    # Фильтры
    notification_type = request.GET.get('type', None)
    priority = request.GET.get('priority', None)
    read_status = request.GET.get('read', None)
    show_read = request.GET.get('show_read', 'false') == 'true'
    
    if notification_type:
        notifications = notifications.filter(notification_type=notification_type)
    
    if priority:
        notifications = notifications.filter(priority=priority)
    
    if read_status == 'unread':
        notifications = notifications.filter(read=False)
    elif read_status == 'read':
        notifications = notifications.filter(read=True)
    
    if not show_read:
        notifications = notifications.filter(read=False)
    
    # Пагинация
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Статистика
    unread_count = CarPreparationNotification.objects.filter(
        recipient=staff, read=False
    ).count() if staff else 0
    
    urgent_unread = CarPreparationNotification.objects.filter(
        recipient=staff, read=False, priority='urgent'
    ).count() if staff else 0
    
    overdue_count = CarPreparationNotification.objects.filter(
        recipient=staff, read=False, notification_type__in=['work_overdue', 'preparation_overdue']
    ).count() if staff else 0
    
    context = {
        'page_obj': page_obj,
        'notifications': page_obj,
        'unread_count': unread_count,
        'urgent_unread': urgent_unread,
        'overdue_count': overdue_count,
        'notification_types': CarPreparationNotification.TYPE_CHOICES,
        'priorities': CarPreparationNotification.PRIORITY_CHOICES,
        'selected_type': notification_type,
        'selected_priority': priority,
        'selected_read': read_status,
        'show_read': show_read,
    }
    
    return render(request, 'car_preparation/notifications_list.html', context)


@login_required
def notification_mark_read(request, notification_id):
    """Отметить уведомление как прочитанное"""
    from django.http import JsonResponse
    
    user = request.user
    staff = getattr(user, 'staff', None)
    
    if not staff:
        return JsonResponse({'success': False, 'message': 'Пользователь не связан с сотрудником'})
    
    try:
        notification = CarPreparationNotification.objects.get(
            id=notification_id,
            recipient=staff
        )
        notification.read = True
        notification.date_read = timezone.now()
        notification.save()
        return JsonResponse({'success': True})
    except CarPreparationNotification.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Уведомление не найдено'})


@login_required
def notification_mark_all_read(request):
    """Отметить все уведомления как прочитанные"""
    from django.http import JsonResponse
    
    user = request.user
    staff = getattr(user, 'staff', None)
    
    if not staff:
        return JsonResponse({'success': False, 'message': 'Пользователь не связан с сотрудником'})
    
    updated = CarPreparationNotification.objects.filter(
        recipient=staff,
        read=False
    ).update(read=True, date_read=timezone.now())
    
    return JsonResponse({'success': True, 'updated': updated})

