"""
Разовый бэкап снимка «итог по правилу» (km_raschet) на день согласования.

Примеры:
  python manage.py backfill_calc_km_rule_snapshots --dry-run
  python manage.py backfill_calc_km_rule_snapshots --lookback-days 90
  python manage.py backfill_calc_km_rule_snapshots --force --lookback-days 60
  python manage.py backfill_calc_km_rule_snapshots --no-live-fallback
"""
from django.core.management.base import BaseCommand

from avtosalon.deal_calc_approval import backfill_km_rule_snapshots


class Command(BaseCommand):
    help = (
        'Проставляет CarCalculations.km_raschet по KMCar на день согласования '
        '(fallback — текущий расчёт правила).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать, что изменится, без записи в БД.',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Перезаписать уже заполненный km_raschet.',
        )
        parser.add_argument(
            '--include-filled',
            action='store_true',
            help='Брать не только пустые km_raschet (имеет смысл с --force).',
        )
        parser.add_argument(
            '--lookback-days',
            type=int,
            default=120,
            help='Глубина выборки КП по датам согласования/создания (по умолчанию 120).',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Ограничить число обработанных КП.',
        )
        parser.add_argument(
            '--no-live-fallback',
            action='store_true',
            help='Не подставлять текущий расчёт, если нет KMCar на дату.',
        )
        parser.add_argument(
            '--verbose-rows',
            action='store_true',
            help='Печатать каждое обновление.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        only_missing = not options['include_filled'] and not force

        def on_progress(calc, value, source, action, old=None):
            if not options['verbose_rows']:
                return
            if action != 'updated':
                return
            self.stdout.write(
                'calc={} rlk={} {} → {} ({})'.format(
                    calc.pk,
                    calc.rlk_id,
                    old,
                    value,
                    source,
                )
            )

        stats = backfill_km_rule_snapshots(
            only_missing=only_missing,
            force=force,
            lookback_days=options['lookback_days'],
            limit=options['limit'],
            dry_run=dry_run,
            allow_live_fallback=not options['no_live_fallback'],
            progress_callback=on_progress,
        )

        prefix = '[dry-run] ' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            '{}checked={} updated={} skipped_same={} skipped_no_value={} by_source={}'.format(
                prefix,
                stats['checked'],
                stats['updated'],
                stats['skipped_same'],
                stats['skipped_no_value'],
                stats['by_source'],
            )
        ))
        self.stdout.write(
            'Источник km_car — снимок компонентов формулы на день согласования; '
            'live — текущий пересчёт (если истории KMCar не было).'
        )
