"""
Ночная выгрузка TradeInFunnel → MSSQL (DELETE периода + INSERT).

Примеры:
  python manage.py sync_tradeinfunnel_mssql
  python manage.py sync_tradeinfunnel_mssql --days 60
  python manage.py sync_tradeinfunnel_mssql --days 60 --dry-run

Планировщик Windows: sheduler\\sync_tradeinfunnel_mssql.bat ежедневно в 03:00.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        'Выгружает TradeInFunnel в MSSQL за последние N дней: '
        'сначала DELETE по EstimationDate, затем INSERT.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=60,
            help='Сколько дней назад от даты запуска (по умолчанию 60)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только посчитать строки, без записи в MSSQL',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        if days < 1:
            raise CommandError('--days должен быть >= 1')

        from analytics.models import TradeInFunnel
        from eco.mssql_tradeinfunnel import (
            mssql_configured,
            run_tradeinfunnel_mssql_sync,
        )
        import datetime as DT

        now = DT.datetime.now()
        date_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
        date_start = (now - DT.timedelta(days=days)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        self.stdout.write(
            'Период: {start} … {end} ({days} дн.)'.format(
                start=date_start.strftime('%Y-%m-%d %H:%M:%S'),
                end=date_end.strftime('%Y-%m-%d %H:%M:%S'),
                days=days,
            )
        )

        qs = TradeInFunnel.objects.filter(
            date_start_estimation__gte=date_start,
            date_start_estimation__lte=date_end,
        ).exclude(date_start_estimation__isnull=True)
        total = qs.count()
        self.stdout.write(f'Найдено в PostgreSQL: {total}')

        if dry_run:
            self.stdout.write(self.style.WARNING('dry-run: запись в MSSQL пропущена'))
            return

        if not mssql_configured():
            raise CommandError(
                'MSSQL не настроен (MSSQL_TRADEINFUNNEL_ENABLED / SERVER / DATABASE / …)'
            )

        try:
            result = run_tradeinfunnel_mssql_sync(days=days)
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(
            'MSSQL OK: удалено {deleted}, загружено {inserted} → {database} / {table} '
            '(запись в bi_logs: TradeInFunnel)'.format(**result)
        ))
