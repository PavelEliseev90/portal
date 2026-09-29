"""
Универсальная интерактивная и командная выгрузка данных из Портала в MyKors.

Использование:
  1. Интерактивное меню с выбором в терминале:
       python manage.py mykors_export

  2. Прямой запуск из командной строки / cron:
       python manage.py mykors_export --type work_orders --limit 10
       python manage.py mykors_export --type all --limit 100
"""
import sys
from django.core.management.base import BaseCommand
from mykors import conf


MENU_ITEMS = [
    ('stock', 'Сток автомобилей (RefCars + фото)'),
    ('staff', 'Сотрудники (RefStaff + User)'),
    ('work_orders', 'Заказ-наряды (DocZN + работы, товары, исполнители, рекомендации, опросы)'),
    ('work_orders_ka', 'Заказ-наряды КорсАвто (DocZNKA + работы, товары, услуги, исполнители)'),
    ('services_ka', 'Поступления услуг КорсАвто (DocServices + услуги)'),
    ('service_requests', 'Заявки на ремонт (DocServiceRequest + планирование)'),
    ('worksheets', 'Рабочие листы (DocRLK + события, опросы ОП)'),
    ('evaluations', 'Листы оценок (DocLO)'),
    ('agreements', 'Соглашения о покупке автомобилей (DocCarAgreement)'),
    ('shipments', 'Отгрузки автомобилей (DocCarShipment + опросы)'),
    ('sms', 'Сообщения СМС (DocSMS)'),
    ('all', 'Выгрузить ВСЕ типы по очереди'),
]

TYPES_CHOICES = [item[0] for item in MENU_ITEMS] + ['cars', 'zn', 'zn_ka', 'services', 'requests', 'rlk', 'lo']


def execute_export(target_type: str, limit: int = 10, uin: str = None, stdout=None):
    if stdout is None:
        stdout = sys.stdout

    limit_val = limit if limit and limit > 0 else None
    uin_val = uin.strip() if uin and uin.strip() else None

    actions = []
    if target_type in ('stock', 'cars', 'all'):
        from mykors.export_cars import export_stock_cars
        actions.append(('Сток автомобилей', lambda: export_stock_cars(limit=limit_val)))

    if target_type in ('staff', 'all'):
        from mykors.export_staff import export_staff
        actions.append(('Сотрудники', lambda: export_staff(limit=limit_val)))

    if target_type in ('work_orders', 'zn', 'all'):
        from mykors.export_work_orders import export_work_orders
        actions.append(('Заказ-наряды', lambda: export_work_orders(limit=limit_val, uin=uin_val)))

    if target_type in ('work_orders_ka', 'zn_ka', 'all'):
        from mykors.export_work_orders_ka import export_work_orders_ka
        actions.append(('Заказ-наряды КорсАвто', lambda: export_work_orders_ka(limit=limit_val, uin=uin_val)))

    if target_type in ('services_ka', 'services', 'all'):
        from mykors.export_services_ka import export_services_ka
        actions.append(('Поступления услуг КорсАвто', lambda: export_services_ka(limit=limit_val, uin=uin_val)))

    if target_type in ('service_requests', 'requests', 'all'):
        from mykors.export_service_requests import export_service_requests
        actions.append(('Заявки на ремонт', lambda: export_service_requests(limit=limit_val, uin=uin_val)))

    if target_type in ('worksheets', 'rlk', 'all'):
        from mykors.export_worksheets import export_worksheets
        actions.append(('Рабочие листы', lambda: export_worksheets(limit=limit_val, uin=uin_val)))

    if target_type in ('evaluations', 'lo', 'all'):
        from mykors.export_evaluations import export_evaluations
        actions.append(('Листы оценок', lambda: export_evaluations(limit=limit_val, uin=uin_val)))

    if target_type in ('agreements', 'all'):
        from mykors.export_car_agreements import export_car_agreements
        actions.append(('Соглашения', lambda: export_car_agreements(limit=limit_val, uin=uin_val)))

    if target_type in ('shipments', 'all'):
        from mykors.export_car_shipments import export_car_shipments
        actions.append(('Отгрузки', lambda: export_car_shipments(limit=limit_val, uin=uin_val)))

    if target_type in ('sms', 'all'):
        from mykors.export_sms import export_sms
        actions.append(('СМС', lambda: export_sms(limit=limit_val, uin=uin_val)))

    for label, fn in actions:
        stdout.write(f'\n--- Запуск выгрузки: {label} ---\n')
        try:
            stats = fn()
            stdout.write(
                f'[{label}] Завершено: всего={stats.get("total", 0)}, '
                f'отправлено={stats.get("sent", 0)}, создано={stats.get("created", 0)}, '
                f'обновлено={stats.get("updated", 0)}, пропущено={stats.get("skipped", 0)}, '
                f'ошибок={stats.get("errors", 0)}\n'
            )
        except Exception as e:
            stdout.write(f'[{label}] Ошибка: {e}\n')


class Command(BaseCommand):
    help = 'Интерактивная и автоматическая выгрузка сущностей в MyKors'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type', type=str, required=False, default=None, choices=TYPES_CHOICES,
            help='Тип сущности для выгрузки (если не указан, откроется интерактивное меню)',
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
                'MyKors выключен: задайте MYKORS_ENABLED=True и ключи API в настройках.'
            ))
            return

        target_type = options.get('type')
        limit = options.get('limit', 10)
        uin = options.get('uin', '').strip() or None

        # Если аргумент --type передан напрямую, выполняем без интерактива
        if target_type:
            execute_export(target_type, limit=limit, uin=uin, stdout=self.stdout)
            return

        # Интерактивное меню в терминале
        while True:
            self.stdout.write('\n' + '=' * 74)
            self.stdout.write('           ИНТЕГРАЦИЯ MYKORS: МЕНЮ ВЫГРУЗКИ ДАННЫХ В ТЕРМИНАЛЕ')
            self.stdout.write('=' * 74)
            for idx, (_, label) in enumerate(MENU_ITEMS, 1):
                self.stdout.write(f' {idx:2d}. {label}')
            self.stdout.write('  0. Выход\n' + '-' * 74)

            try:
                choice = input('Выберите номер пункта [0-12]: ').strip()
            except (KeyboardInterrupt, EOFError):
                self.stdout.write('\nВыход.')
                break

            if choice in ('0', 'q', 'exit', 'quit', ''):
                self.stdout.write('Выход.')
                break

            try:
                choice_idx = int(choice)
                if not (1 <= choice_idx <= len(MENU_ITEMS)):
                    self.stdout.write(self.style.ERROR('Неверный номер, попробуйте еще раз.'))
                    continue
            except ValueError:
                self.stdout.write(self.style.ERROR('Пожалуйста, введите число.'))
                continue

            selected_type, selected_label = MENU_ITEMS[choice_idx - 1]

            # Запрос лимита
            try:
                limit_input = input('Количество записей (по умолчанию 10, 0 = ВСЕ): ').strip()
                selected_limit = int(limit_input) if limit_input else 10
            except ValueError:
                selected_limit = 10

            selected_uin = None
            if selected_type != 'all':
                try:
                    uin_input = input('UIN конкретного документа (Enter, чтобы выгрузить по порядку): ').strip()
                    selected_uin = uin_input or None
                except (KeyboardInterrupt, EOFError):
                    break

            confirm_str = f'Запустить выгрузку "{selected_label}" (лимит: {selected_limit if selected_limit > 0 else "ВСЕ"})? [Y/n]: '
            try:
                confirm = input(confirm_str).strip().lower()
            except (KeyboardInterrupt, EOFError):
                break

            if confirm in ('', 'y', 'yes', 'д', 'да'):
                self.stdout.write(self.style.NOTICE('Выполняется...'))
                execute_export(selected_type, limit=selected_limit, uin=selected_uin, stdout=self.stdout)
                self.stdout.write(self.style.SUCCESS('\nГотово!'))
            else:
                self.stdout.write('Отменено.')

            try:
                next_action = input('\nНажмите Enter, чтобы вернуться в меню, или 0 для выхода: ').strip()
                if next_action == '0':
                    break
            except (KeyboardInterrupt, EOFError):
                break
