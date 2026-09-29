"""
Выгрузка сотрудников портала в MyKors.

Примеры:
  python manage.py mykors_export_staff
  python manage.py mykors_export_staff --limit 50
  python manage.py mykors_export_staff --user-id 123
  python manage.py mykors_export_staff --queue
"""
from django.core.management.base import BaseCommand

from mykors import conf


class Command(BaseCommand):
    help = 'Выгрузка сотрудников портала (User + Profiles) в MyKors'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit', type=int, default=0,
            help='Лимит пользователей за прогон (0 = все)',
        )
        parser.add_argument(
            '--user-id', type=int, default=0,
            help='Выгрузить одного сотрудника по ID пользователя',
        )
        parser.add_argument(
            '--queue', action='store_true',
            help='Поставить задачу в очередь mykors_sync (не блокировать)',
        )

    def handle(self, *args, **options):
        if not conf.is_enabled():
            self.stdout.write(self.style.WARNING(
                'MyKors выключен: задайте MYKORS_ENABLED=True и ключи API.'
            ))
            return

        limit = options['limit'] or None
        user_id = options['user_id'] or None

        if options['queue']:
            from mykors.tasks import export_staff_task
            export_staff_task(
                limit=limit or 0,
                user_id=user_id or 0,
            )
            self.stdout.write(self.style.SUCCESS(
                'Задача поставлена в очередь mykors_sync. '
                'Запустите: process_tasks --queue mykors_sync'
            ))
            return

        from mykors.export_staff import export_staff

        stats = export_staff(limit=limit, user_id=user_id)
        self.stdout.write(self.style.SUCCESS(
            'Готово: total={total} sent={sent} created={created} '
            'updated={updated} skipped={skipped} errors={errors}'.format(**stats)
        ))
