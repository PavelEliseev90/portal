"""
Модуль для автоматической генерации уведомлений по подготовке автомобилей
"""
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    CarPreparation, CarPreparationWorkItem, CarPreparationWorkSchedule,
    CarPreparationNotification, RefCarPreparationStatus
)


def check_overdue_works(send_notification=True):
    """
    Проверка просроченных работ и создание уведомлений
    
    Args:
        send_notification: Создавать ли уведомления (для тестирования)
    """
    if not send_notification:
        return []
    
    now = timezone.now()
    
    # Ищем работы с просроченным сроком выполнения
    overdue_schedules = CarPreparationWorkSchedule.objects.filter(
        planned_end__lt=now,
        planning_status__in=['scheduled', 'in_progress'],
        work_item__status__in=['pending', 'in_progress'],
        work_item__is_confirmed=True
    ).select_related('work_item', 'work_item__preparation', 'work_item__preparation__car', 
                    'planned_performer', 'work_item__preparation__responsible')
    
    created_notifications = []
    
    for schedule in overdue_schedules:
        # Проверяем, не создано ли уже уведомление за последний час
        recent_notification = CarPreparationNotification.objects.filter(
            work_schedule=schedule,
            notification_type='work_overdue',
            date_created__gte=now - timedelta(hours=1)
        ).exists()
        
        if not recent_notification:
            # Определяем получателей
            recipients = []
            
            # Исполнитель работы
            if schedule.planned_performer:
                recipients.append(schedule.planned_performer)
            
            # Ответственный за подготовку
            prep = schedule.work_item.preparation
            if prep and prep.responsible:
                if prep.responsible not in recipients:
                    recipients.append(prep.responsible)
            
            # Создаем уведомления для каждого получателя
            for recipient in recipients:
                if not recipient:
                    continue
                
                hours_overdue = int((now - schedule.planned_end).total_seconds() / 3600)
                prep = schedule.work_item.preparation
                car_name = prep.car.name if prep and prep.car else "Неизвестный автомобиль"
                car_vin = prep.car.vin if prep and prep.car else ""
                
                notification = CarPreparationNotification.objects.create(
                    preparation=prep,
                    work_item=schedule.work_item,
                    work_schedule=schedule,
                    notification_type='work_overdue',
                    priority='high' if hours_overdue > 24 else 'normal',
                    message=f"Работа '{schedule.work_item.work.name}' просрочена на {hours_overdue} ч. "
                           f"Автомобиль: {car_name} "
                           f"(VIN: {car_vin})",
                    recipient=recipient,
                    auto_created=True,
                    metadata=f'{{"hours_overdue": {hours_overdue}, "planned_end": "{schedule.planned_end}"}}'
                )
                created_notifications.append(notification)
    
    return created_notifications


def check_upcoming_works(minutes_before=30, send_notification=True):
    """
    Проверка работ, которые скоро должны начаться
    
    Args:
        minutes_before: За сколько минут до начала создавать уведомление
        send_notification: Создавать ли уведомления (для тестирования)
    """
    if not send_notification:
        return []
    
    now = timezone.now()
    start_threshold = now + timedelta(minutes=minutes_before)
    
    # Ищем работы, которые должны начаться в ближайшее время
    upcoming_schedules = CarPreparationWorkSchedule.objects.filter(
        planned_start__gte=now,
        planned_start__lte=start_threshold,
        planning_status='scheduled',
        work_item__status='pending',
        work_item__is_confirmed=True
    ).select_related('work_item', 'work_item__preparation', 'work_item__preparation__car',
                    'planned_performer', 'work_item__preparation__responsible')
    
    created_notifications = []
    
    for schedule in upcoming_schedules:
        # Проверяем, не создано ли уже уведомление
        recent_notification = CarPreparationNotification.objects.filter(
            work_schedule=schedule,
            notification_type='work_upcoming',
            date_created__gte=now - timedelta(minutes=minutes_before + 10)
        ).exists()
        
        if not recent_notification:
            # Определяем получателей
            recipients = []
            
            # Исполнитель работы
            if schedule.planned_performer:
                recipients.append(schedule.planned_performer)
            
            # Создаем уведомления
            for recipient in recipients:
                if not recipient:
                    continue
                
                minutes_until = int((schedule.planned_start - now).total_seconds() / 60)
                prep = schedule.work_item.preparation
                car_name = prep.car.name if prep and prep.car else "Неизвестный автомобиль"
                car_vin = prep.car.vin if prep and prep.car else ""
                
                notification = CarPreparationNotification.objects.create(
                    preparation=prep,
                    work_item=schedule.work_item,
                    work_schedule=schedule,
                    notification_type='work_upcoming',
                    priority='normal',
                    message=f"Через {minutes_until} мин. начинается работа '{schedule.work_item.work.name}'. "
                           f"Автомобиль: {car_name} "
                           f"(VIN: {car_vin})",
                    recipient=recipient,
                    auto_created=True,
                    metadata=f'{{"minutes_until": {minutes_until}, "planned_start": "{schedule.planned_start}"}}'
                )
                created_notifications.append(notification)
    
    return created_notifications


def check_overdue_preparations(send_notification=True):
    """
    Проверка просроченных подготовок в целом
    
    Args:
        send_notification: Создавать ли уведомления (для тестирования)
    """
    if not send_notification:
        return []
    
    now = timezone.now()
    
    # Ищем подготовки с просроченным плановым сроком
    overdue_preparations = CarPreparation.objects.filter(
        date_planned_end__lt=now,
        date_end__isnull=True,  # Еще не завершена
        status__is_final=False  # Не в финальном статусе
    ).select_related('car', 'unit', 'responsible', 'status')
    
    created_notifications = []
    
    for preparation in overdue_preparations:
        # Проверяем, не создано ли уже уведомление за последний день
        recent_notification = CarPreparationNotification.objects.filter(
            preparation=preparation,
            notification_type='preparation_overdue',
            date_created__gte=now - timedelta(days=1)
        ).exists()
        
        if not recent_notification:
            # Определяем получателей
            recipients = []
            
            if preparation.responsible:
                recipients.append(preparation.responsible)
            
            # Уведомляем всех исполнителей незавершенных работ
            work_items = preparation.work_items.filter(
                status__in=['pending', 'in_progress'],
                is_confirmed=True
            ).select_related('schedule', 'schedule__planned_performer')
            
            for work_item in work_items:
                if (hasattr(work_item, 'schedule') and 
                    work_item.schedule and 
                    work_item.schedule.planned_performer):
                    if work_item.schedule.planned_performer not in recipients:
                        recipients.append(work_item.schedule.planned_performer)
            
            # Убираем дубликаты и None
            unique_recipients = []
            seen_ids = set()
            for r in recipients:
                if r and r.id not in seen_ids:
                    unique_recipients.append(r)
                    seen_ids.add(r.id)
            recipients = unique_recipients
            
            # Создаем уведомления
            for recipient in recipients:
                days_overdue = int((now.date() - preparation.date_planned_end.date()).days)
                car_name = preparation.car.name if preparation.car else "Неизвестный автомобиль"
                car_vin = preparation.car.vin if preparation.car else ""
                
                notification = CarPreparationNotification.objects.create(
                    preparation=preparation,
                    notification_type='preparation_overdue',
                    priority='urgent' if days_overdue > 3 else 'high',
                    message=f"Подготовка автомобиля {car_name} (VIN: {car_vin}) "
                           f"просрочена на {days_overdue} дн. Прогресс: {preparation.progress_percent}%",
                    recipient=recipient,
                    auto_created=True,
                    metadata=f'{{"days_overdue": {days_overdue}, "progress": {preparation.progress_percent}}}'
                )
                created_notifications.append(notification)
    
    return created_notifications


def generate_notifications(send_notifications=True):
    """
    Главная функция для генерации всех уведомлений
    Возвращает статистику созданных уведомлений
    
    Args:
        send_notifications: Создавать ли уведомления (для тестирования)
    """
    overdue_works = check_overdue_works(send_notification=send_notifications)
    upcoming_works = check_upcoming_works(send_notification=send_notifications)
    overdue_preps = check_overdue_preparations(send_notification=send_notifications)
    
    return {
        'overdue_works': len(overdue_works),
        'upcoming_works': len(upcoming_works),
        'overdue_preparations': len(overdue_preps),
        'total': len(overdue_works) + len(upcoming_works) + len(overdue_preps)
    }


def create_work_started_notification(work_item, performer):
    """
    Создать уведомление о начале работы
    """
    prep = work_item.preparation
    car_name = prep.car.name if prep and prep.car else "Неизвестный автомобиль"
    car_vin = prep.car.vin if prep and prep.car else ""
    recipient = prep.responsible if prep else None
    
    if not recipient:
        return None
    
    notification = CarPreparationNotification.objects.create(
        preparation=prep,
        work_item=work_item,
        work_schedule=getattr(work_item, 'schedule', None),
        notification_type='started',
        priority='normal',
        message=f"Начата работа '{work_item.work.name}' по автомобилю "
               f"{car_name} (VIN: {car_vin})",
        recipient=recipient,
        auto_created=True
    )
    return notification


def create_work_completed_notification(work_item):
    """
    Создать уведомление о завершении работы
    """
    prep = work_item.preparation
    car_name = prep.car.name if prep and prep.car else "Неизвестный автомобиль"
    car_vin = prep.car.vin if prep and prep.car else ""
    recipient = prep.responsible if prep else None
    
    if not recipient:
        return None
    
    notification = CarPreparationNotification.objects.create(
        preparation=prep,
        work_item=work_item,
        work_schedule=getattr(work_item, 'schedule', None),
        notification_type='work_completed',
        priority='normal',
        message=f"Завершена работа '{work_item.work.name}' по автомобилю "
               f"{car_name} (VIN: {car_vin})",
        recipient=recipient,
        auto_created=True
    )
    return notification

