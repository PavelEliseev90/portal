"""
Сравнение затрат оценок: снимок из истории (ДО) vs пересчёт на текущих настройках (ПОСЛЕ).

По умолчанию тип = autohub, период = июль 2026.

Примеры:
  python manage.py compare_estimation_costs --from 2026-07-01 --to 2026-07-31 --dry-run
  python manage.py compare_estimation_costs --from 2026-07-01 --to 2026-07-31 --out D:/tmp/costs_july.xlsx
  python manage.py compare_estimation_costs --from 2026-07-01 --to 2026-07-31 --only-changed --limit 50
  python manage.py compare_estimation_costs --ids 123,456 --out D:/tmp/sample.xlsx
"""
from __future__ import annotations

import datetime as DT
import os
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        'Сравнение затрат подготовка/слесарка/кузов (+ возврат за СС при износе): '
        'история autohub vs пересчёт на текущих коэффициентах. Excel-выгрузка.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--from',
            dest='date_from',
            default='2026-07-01',
            help='Начало периода YYYY-MM-DD (по start_estimation)',
        )
        parser.add_argument(
            '--to',
            dest='date_to',
            default='2026-07-31',
            help='Конец периода YYYY-MM-DD (по start_estimation)',
        )
        parser.add_argument(
            '--type',
            dest='calc_type',
            default='autohub',
            help='Тип расчёта (по умолчанию autohub)',
        )
        parser.add_argument(
            '--unit-id',
            type=int,
            default=None,
            help='Фильтр по ДЦ',
        )
        parser.add_argument(
            '--ids',
            default='',
            help='Список ID оценок через запятую',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Ограничить число оценок (0 = все)',
        )
        parser.add_argument(
            '--only-changed',
            action='store_true',
            help='В Excel только строки с |Δ| > 0.5',
        )
        parser.add_argument(
            '--out',
            default='',
            help='Путь к xlsx (по умолчанию MEDIA_ROOT/temp/...)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только посчитать объём выборки, без пересчёта',
        )

    def handle(self, *args, **options):
        from register.estimation_costs_compare import (
            export_comparisons_to_xlsx,
            iter_july_comparisons,
        )
        from register.models import RegInteractivOcenkaRLK
        from django.db.models import Q

        date_from = self._parse_date(options['date_from'], end=False)
        date_to = self._parse_date(options['date_to'], end=True)
        calc_type = (options['calc_type'] or 'autohub').strip()
        unit_id = options['unit_id']
        limit = max(0, options['limit'] or 0)
        only_changed = bool(options['only_changed'])
        dry_run = bool(options['dry_run'])
        estimation_ids = self._parse_ids(options['ids'])

        qs = RegInteractivOcenkaRLK.objects.filter(estimation__isnull=False)
        if estimation_ids:
            qs = qs.filter(estimation_id__in=estimation_ids)
        else:
            qs = qs.filter(
                estimation__start_estimation__gte=date_from,
                estimation__start_estimation__lte=date_to,
            )
        if unit_id:
            qs = qs.filter(
                Q(unit_id=unit_id)
                | Q(rlk__unit_id=unit_id)
                | Q(rlk__unit_dc_id=unit_id)
            )
        qs = qs.filter(
            Q(estimation__hub_avg__gt=0)
            | Q(estimation__page_remote__hub_avg__gt=0)
        )
        total = qs.count()
        if limit:
            total = min(total, limit)

        self.stdout.write(
            self.style.NOTICE(
                f'Период {date_from.date()} … {date_to.date()} | тип={calc_type} | '
                f'оценок≈{total} | only_changed={only_changed}'
            )
        )

        if dry_run:
            for est_id, vin in qs.values_list('estimation_id', 'estimation__vin')[:30]:
                self.stdout.write(f'  estimation_id={est_id} vin={vin or ""}')
            if total > 30:
                self.stdout.write(f'  ... и ещё {total - 30}')
            return

        out_path = (options['out'] or '').strip()
        if not out_path:
            media = getattr(settings, 'MEDIA_ROOT', None) or os.getcwd()
            temp_dir = os.path.join(media, 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            stamp = DT.datetime.now().strftime('%Y%m%d_%H%M%S')
            out_path = os.path.join(
                temp_dir,
                f'estimation_costs_compare_{calc_type}_{stamp}.xlsx',
            )

        started = time.time()
        comparisons = []
        ok = 0
        skipped = 0

        for comparison in iter_july_comparisons(
            date_from=date_from,
            date_to=date_to,
            calc_type=calc_type,
            unit_id=unit_id,
            limit=limit,
            only_changed=only_changed,
            estimation_ids=estimation_ids or None,
        ):
            comparisons.append(comparison)
            ok += 1
            if ok % 25 == 0:
                self.stdout.write(f'  обработано {ok}...')

        if not comparisons:
            skipped = total
            self.stdout.write(self.style.WARNING('Нет данных для выгрузки (пересчёт вернул пусто).'))
            return

        rows, _ = export_comparisons_to_xlsx(comparisons, out_path)
        elapsed = time.time() - started
        self.stdout.write(
            self.style.SUCCESS(
                f'Готово: оценок={ok}, строк Excel={rows}, файл={out_path}, {elapsed:.1f} сек'
            )
        )
        if skipped:
            self.stdout.write(f'Пропущено (оценка): {skipped}')

    def _parse_date(self, value, end=False):
        try:
            d = DT.datetime.strptime(value.strip(), '%Y-%m-%d')
        except (TypeError, ValueError) as exc:
            raise CommandError(f'Неверная дата: {value}') from exc
        if end:
            return d.replace(hour=23, minute=59, second=59, microsecond=0)
        return d.replace(hour=0, minute=0, second=0, microsecond=0)

    def _parse_ids(self, raw):
        if not raw:
            return []
        ids = []
        for part in str(raw).split(','):
            part = part.strip()
            if not part:
                continue
            try:
                ids.append(int(part))
            except ValueError as exc:
                raise CommandError(f'Неверный id: {part}') from exc
        return ids
