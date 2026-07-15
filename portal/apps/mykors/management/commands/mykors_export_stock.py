"""
Выгрузка автомобилей в наличии в MyKors.

Примеры:
  python manage.py mykors_export_stock
  python manage.py mykors_export_stock --force
  python manage.py mykors_export_stock --limit 50
  python manage.py mykors_export_stock --car-id 12345
  python manage.py mykors_export_stock --queue   # поставить в background_task
"""
from django.core.management.base import BaseCommand

from mykors import conf


class Command(BaseCommand):
    help = 'Выгрузка авто в наличии (quantity>0) на портал MyKors'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true',
            help='Слать все, даже если payload не менялся',
        )
        parser.add_argument(
            '--limit', type=int, default=0,
            help='Лимит машин за прогон (0 = из настроек / все)',
        )
        parser.add_argument(
            '--car-id', type=int, default=0,
            help='Выгрузить одну машину по ID портала',
        )
        parser.add_argument(
            '--queue', action='store_true',
            help='Поставить задачу в очередь mykors_sync (не блокировать)',
        )
        parser.add_argument(
            '--sync', action='store_true',
            help='Выполнить синхронно в этом процессе (по умолчанию)',
        )

    def handle(self, *args, **options):
        if not conf.is_enabled():
            self.stdout.write(self.style.WARNING(
                'MyKors выключен: задайте MYKORS_ENABLED=True и ключи API.'
            ))
            return

        force = options['force']
        limit = options['limit'] or None
        car_id = options['car_id'] or None

        if options['queue']:
            from mykors.tasks import export_stock_cars_task
            export_stock_cars_task(
                force=force,
                limit=limit or 0,
                car_id=car_id or 0,
            )
            self.stdout.write(self.style.SUCCESS(
                'Задача поставлена в очередь mykors_sync. '
                'Запустите: process_tasks --queue mykors_sync'
            ))
            return

        from mykors.export_cars import export_stock_cars

        stats = export_stock_cars(force=force, limit=limit, car_id=car_id)
        self.stdout.write(self.style.SUCCESS(
            'Готово: total={total} sent={sent} created={created} '
            'updated={updated} skipped={skipped} errors={errors}'.format(**stats)
        ))
