"""
Management command для отправки автоматических напоминаний о дедлайнах
Запускать через cron: python manage.py send_deadline_reminders
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from helpDesk.models import DeadlineReminder, HelpDeskTask
from helpDesk.utils import send_task_notification


class Command(BaseCommand):
    help = 'Отправляет напоминания о дедлайнах задач'

    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # Находим все активные напоминания, которые нужно отправить
        reminders = DeadlineReminder.objects.filter(
            is_sent=False,
            task__is_deleted=False,
            task__date_deadline__isnull=False,
            task__status__is_closed=False
        ).select_related('task', 'user')
        
        sent_count = 0
        
        for reminder in reminders:
            # Вычисляем дату, когда нужно отправить напоминание
            reminder_date = reminder.task.date_deadline.date() - timedelta(days=reminder.days_before)
            
            # Если сегодня день отправки или уже просрочено
            if today >= reminder_date:
                try:
                    # Отправляем уведомление конкретному пользователю
                    send_task_notification(
                        task=reminder.task,
                        action_type='deadline_reminder',
                        changed_by=None,
                        request=None,
                        reminder_days=reminder.days_before,
                        recipient_user=reminder.user
                    )
                    
                    # Отмечаем как отправленное
                    reminder.is_sent = True
                    reminder.date_sent = timezone.now()
                    reminder.save()
                    
                    sent_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Отправлено напоминание для задачи #{reminder.task.id} '
                            f'пользователю {reminder.user.username} (за {reminder.days_before} дней)'
                        )
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Ошибка при отправке напоминания для задачи #{reminder.task.id}: {str(e)}'
                        )
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f'Отправлено напоминаний: {sent_count}')
        )

