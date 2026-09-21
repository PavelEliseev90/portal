# -*- coding: utf-8 -*-
"""
Команда Django для регламентного пересчёта материализованной витрины данных
Центра управления ДЦ (DcCommandCenterShowcase).
Использование:
    python manage.py rebuild_dc_showcase
    python manage.py rebuild_dc_showcase --month 2026-09
    python manage.py rebuild_dc_showcase --unit 12
"""
import time
from datetime import datetime

from django.core.management.base import BaseCommand

from prices_car.command_center_service import (
    get_first_day_of_month,
    rebuild_dc_command_center_showcase,
)
from refs.models import RefUnit


class Command(BaseCommand):
    help = 'Пересчитывает витрину данных Центра Управления ДЦ (DcCommandCenterShowcase) за месяц'

    def add_arguments(self, parser):
        parser.add_argument(
            '--month',
            type=str,
            help='Месяц в формате YYYY-MM (по умолчанию текущий месяц)',
        )
        parser.add_argument(
            '--unit',
            type=int,
            help='ID дилерского центра (если нужно обновить только один ДЦ)',
        )

    def handle(self, *args, **options):
        month_str = options.get('month')
        if month_str:
            try:
                month_start = datetime.strptime(month_str, '%Y-%m').date().replace(day=1)
            except ValueError:
                self.stderr.write(self.style.ERROR(f'Неверный формат месяца: {month_str}. Ожидается YYYY-MM.'))
                return
        else:
            month_start = get_first_day_of_month()

        unit_id = options.get('unit')
        unit = None
        if unit_id:
            unit = RefUnit.objects.filter(id=unit_id).first()
            if not unit:
                self.stderr.write(self.style.ERROR(f'ДЦ с ID {unit_id} не найден.'))
                return

        self.stdout.write(
            f'Начало пересборки витрины за {month_start:%Y-%m}' +
            (f' для ДЦ «{unit.name}»' if unit else ' для всей сети ДЦ') + '...'
        )

        t0 = time.time()
        updated_count = rebuild_dc_command_center_showcase(unit=unit, month_start=month_start)
        elapsed = round(time.time() - t0, 2)

        self.stdout.write(
            self.style.SUCCESS(
                f'Витрина успешно пересчитана за {elapsed} сек! Обновлено записей: {updated_count}.'
            )
        )
