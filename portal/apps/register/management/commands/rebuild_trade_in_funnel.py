"""
Пересборка витрины TradeInFunnel за период.

Витрина пишется при save() RegInteractivOcenkaRLK / DocLO и не содержит
автоматической истории. Команда прогоняет оценки и активные ЛО за даты.

При обновлении: если price_zna_2 пустой — заполняется из estimation.hub_avg
(с fallback page_remote.hub_avg), затем пишется в витрину zna / ЦГ.

Примеры:
  python manage.py rebuild_trade_in_funnel --from 2024-01-01 --to 2025-12-31 --dry-run
  python manage.py rebuild_trade_in_funnel --from 2024-01-01 --to 2025-12-31
  python manage.py rebuild_trade_in_funnel --from 2023-01-01 --to 2023-12-31 --skip-lo
"""
from __future__ import annotations

import datetime as DT

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q


class Command(BaseCommand):
    help = (
        'Пересобирает TradeInFunnel из RegInteractivOcenkaRLK (+ активные DocLO). '
        'Дозаполняет price_zna_2 из hub_avg при пустом значении.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--from',
            dest='date_from',
            required=True,
            help='Начало периода YYYY-MM-DD (по start_estimation / dataTime ЛО)',
        )
        parser.add_argument(
            '--to',
            dest='date_to',
            required=True,
            help='Конец периода YYYY-MM-DD',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать объём, без записи',
        )
        parser.add_argument(
            '--skip-lo',
            action='store_true',
            help='Не пересохранять DocLO (только оценки → update_trade_in_funnel)',
        )
        parser.add_argument(
            '--chunk',
            type=int,
            default=500,
            help='Размер пачки для прогресса (по умолчанию 500)',
        )

    def handle(self, *args, **options):
        date_from = self._parse_date(options['date_from'], end=False)
        date_to = self._parse_date(options['date_to'], end=True)
        dry_run = options['dry_run']
        skip_lo = options['skip_lo']
        chunk = max(1, options['chunk'])

        from documents.models import DocLO
        from register.models import RegInteractivOcenkaRLK, update_trade_in_funnel

        rlk_qs = (
            RegInteractivOcenkaRLK.objects.filter(
                estimation__isnull=False,
                estimation__start_estimation__gte=date_from,
                estimation__start_estimation__lte=date_to,
            )
            .select_related(
                'rlk',
                'estimation',
                'estimation__page_remote',
                'estimation__modification',
                'estimation__modification__model',
                'estimation__modification__model__mark',
                'estimation__page_salon',
                'estimation__page_documents',
                'page_soglasovanie',
                'type_reception',
                'unit',
                'unit__city',
                'staff_rlk',
                'staff_eco_1_rlk',
                'staff_eco_1_rlk__profiles',
                'staff_eco_2_rlk',
                'staff_eco_2_rlk__profiles',
                'status',
            )
            .order_by('id')
        )
        rlk_count = rlk_qs.count()

        need_zna_count = rlk_qs.filter(
            page_soglasovanie__isnull=False,
        ).filter(
            Q(page_soglasovanie__price_zna_2__isnull=True) | Q(page_soglasovanie__price_zna_2=0)
        ).filter(
            Q(estimation__hub_avg__gt=0) | Q(estimation__page_remote__hub_avg__gt=0)
        ).count()

        lo_ids = []
        if not skip_lo:
            rlk_ids = list(
                rlk_qs.exclude(rlk_id__isnull=True).values_list('rlk_id', flat=True).distinct()
            )
            lo_by_est = set(
                DocLO.objects.filter(active=True, rlk_id__in=rlk_ids).values_list('id', flat=True)
            ) if rlk_ids else set()
            lo_by_date = set(
                DocLO.objects.filter(
                    active=True,
                    rlk__isnull=False,
                    dataTime__gte=date_from,
                    dataTime__lte=date_to,
                ).values_list('id', flat=True)
            )
            lo_ids = sorted(lo_by_est | lo_by_date)
        lo_count = len(lo_ids)

        self.stdout.write(
            f'Период {date_from:%Y-%m-%d} … {date_to:%Y-%m-%d}: '
            f'RegInteractivOcenkaRLK={rlk_count}, DocLO(active)={lo_count}, '
            f'кандидатов дозаполнить price_zna_2 из hub_avg≈{need_zna_count}'
            + (' [dry-run]' if dry_run else '')
        )

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry-run: запись не выполнялась.'))
            return

        ok = 0
        err = 0
        for i, row in enumerate(rlk_qs.iterator(chunk_size=chunk), start=1):
            try:
                update_trade_in_funnel(row)
                ok += 1
            except Exception as exc:
                err += 1
                self.stderr.write(f'RLK link #{row.pk}: {exc}')
            if i % chunk == 0 or i == rlk_count:
                self.stdout.write(f'  оценки: {i}/{rlk_count} (ok={ok}, err={err})')

        lo_ok = 0
        lo_err = 0
        if not skip_lo and lo_ids:
            for i, lo_id in enumerate(lo_ids, start=1):
                try:
                    lo = DocLO.objects.select_related('rlk', 'unit', 'type_reception').get(pk=lo_id)
                    lo.save()
                    lo_ok += 1
                except Exception as exc:
                    lo_err += 1
                    self.stderr.write(f'DocLO #{lo_id}: {exc}')
                if i % chunk == 0 or i == lo_count:
                    self.stdout.write(f'  ЛО: {i}/{lo_count} (ok={lo_ok}, err={lo_err})')

        self.stdout.write(self.style.SUCCESS(
            f'Готово: оценок ok={ok}/err={err}'
            + (f', ЛО ok={lo_ok}/err={lo_err}' if not skip_lo else '')
        ))

    def _parse_date(self, value: str, end: bool) -> DT.datetime:
        try:
            day = DT.datetime.strptime(value.strip(), '%Y-%m-%d')
        except ValueError as exc:
            raise CommandError(f'Неверная дата «{value}», ожидается YYYY-MM-DD') from exc
        if end:
            return day.replace(hour=23, minute=59, second=59, microsecond=0)
        return day.replace(hour=0, minute=0, second=0, microsecond=0)
