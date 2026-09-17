"""
Универсальная команда выгрузки данных из Портала в MyKors.

Примеры:
  python manage.py mykors_export --type work_orders --limit 10
  python manage.py mykors_export --type work_orders_ka --limit 10
  python manage.py mykors_export --type service_requests --limit 10
  python manage.py mykors_export --type worksheets --limit 10
  python manage.py mykors_export --type evaluations --limit 10
  python manage.py mykors_export --type agreements --limit 10
  python manage.py mykors_export --type shipments --limit 10
  python manage.py mykors_export --type services_ka --limit 10
  python manage.py mykors_export --type sms --limit 10
  python manage.py mykors_export --type staff --limit 10
  python manage.py mykors_export --type stock --limit 10
  python manage.py mykors_export --type all --limit 10
"""
from django.core.management.base import BaseCommand
from mykors import conf


TYPES_CHOICES = [
    'stock',
    'cars',
    'staff',
    'work_orders',
    'zn',
    'work_orders_ka',
    'zn_ka',
    'services_ka',
    'services',
    'service_requests',
    'requests',
    'worksheets',
    'rlk',
    'evaluations',
    'lo',
    'agreements',
    'shipments',
    'sms',
    'all',
]


class Command(BaseCommand):
    help = 'Универсальная выгрузка сущностей в MyKors'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type', type=str, required=True, choices=TYPES_CHOICES,
            help='Тип сущности для выгрузки (или all)',
        )
        parser.add_argument(
            '--limit', type=int, default=10,
            help='Лимит записей за прогон (по умолчанию 10, 0 = без ограничений)',
        )
        parser.add_argument(
            '--uin', type=str, default='',
            help='Выгрузить конкретный документ по UIN (где применимо)',
        )

    def handle(self, *args, **options):
        if not conf.is_enabled():
            self.stdout.write(self.style.WARNING(
                'MyKors выключен: задайте MYKORS_ENABLED=True и ключи API.'
            ))
            return

        target_type = options['type']
        limit = options['limit'] or None
        uin = options['uin'].strip() or None

        actions = []
        if target_type in ('stock', 'cars', 'all'):
            from mykors.export_cars import export_stock_cars
            actions.append(('Сток автомобилей', lambda: export_stock_cars(limit=limit)))

        if target_type in ('staff', 'all'):
            from mykors.export_staff import export_staff
            actions.append(('Сотрудники', lambda: export_staff(limit=limit)))

        if target_type in ('work_orders', 'zn', 'all'):
            from mykors.export_work_orders import export_work_orders
            actions.append(('Заказ-наряды', lambda: export_work_orders(limit=limit, uin=uin)))

        if target_type in ('work_orders_ka', 'zn_ka', 'all'):
            from mykors.export_work_orders_ka import export_work_orders_ka
            actions.append(('Заказ-наряды КорсАвто', lambda: export_work_orders_ka(limit=limit, uin=uin)))

        if target_type in ('services_ka', 'services', 'all'):
            from mykors.export_services_ka import export_services_ka
            actions.append(('Поступления услуг КорсАвто', lambda: export_services_ka(limit=limit, uin=uin)))

        if target_type in ('service_requests', 'requests', 'all'):
            from mykors.export_service_requests import export_service_requests
            actions.append(('Заявки на ремонт', lambda: export_service_requests(limit=limit, uin=uin)))

        if target_type in ('worksheets', 'rlk', 'all'):
            from mykors.export_worksheets import export_worksheets
            actions.append(('Рабочие листы', lambda: export_worksheets(limit=limit, uin=uin)))

        if target_type in ('evaluations', 'lo', 'all'):
            from mykors.export_evaluations import export_evaluations
            actions.append(('Листы оценок', lambda: export_evaluations(limit=limit, uin=uin)))

        if target_type in ('agreements', 'all'):
            from mykors.export_car_agreements import export_car_agreements
            actions.append(('Соглашения', lambda: export_car_agreements(limit=limit, uin=uin)))

        if target_type in ('shipments', 'all'):
            from mykors.export_car_shipments import export_car_shipments
            actions.append(('Отгрузки', lambda: export_car_shipments(limit=limit, uin=uin)))

        if target_type in ('sms', 'all'):
            from mykors.export_sms import export_sms
            actions.append(('СМС', lambda: export_sms(limit=limit, uin=uin)))

        for label, fn in actions:
            self.stdout.write(f'--- Запуск выгрузки: {label} ---')
            try:
                stats = fn()
                self.stdout.write(self.style.SUCCESS(
                    f'[{label}] Завершено: {stats}'
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'[{label}] Ошибка: {e}'
                ))
