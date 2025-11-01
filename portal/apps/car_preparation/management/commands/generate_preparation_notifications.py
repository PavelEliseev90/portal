"""
Management command для автоматической генерации уведомлений
Запускается через cron или планировщик задач
"""
from django.core.management.base import BaseCommand
from car_preparation.notifications import generate_notifications


class Command(BaseCommand):
    help = 'Генерация уведомлений по просроченным и предстоящим работам'

    def add_arguments(self, parser):
        parser.add_argument(
            '--upcoming-minutes',
            type=int,
            default=30,
            help='За сколько минут до начала работы создавать уведомление (по умолчанию 30)',
        )

    def handle(self, *args, **options):
        self.stdout.write('Начинаю генерацию уведомлений...')
        
        stats = generate_notifications()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Создано уведомлений:\n'
                f'  - Просроченные работы: {stats["overdue_works"]}\n'
                f'  - Предстоящие работы: {stats["upcoming_works"]}\n'
                f'  - Просроченные подготовки: {stats["overdue_preparations"]}\n'
                f'  - Всего: {stats["total"]}'
            )
        )

