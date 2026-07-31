"""
Массовый пересчёт цен интерактивных оценок с записью в историю.

По умолчанию считает только Autohub и пишет в RegInteractivOcenkaPrice.
Обновляет поля авторасчёта на согласовании (persist), если не указан --no-persist.

Примеры:
  python manage.py batch_recalc_interactive_prices --from 2026-01-01 --to 2026-07-31 --dry-run
  python manage.py batch_recalc_interactive_prices --from 2026-01-01 --to 2026-07-31
  python manage.py batch_recalc_interactive_prices --from 2026-06-01 --to 2026-07-31 --unit-id 12
  python manage.py batch_recalc_interactive_prices --ids 123,456,789 --types autohub
  python manage.py batch_recalc_interactive_prices --from 2026-01-01 --to 2026-07-31 --no-persist
  python manage.py batch_recalc_interactive_prices --from 2026-01-01 --to 2026-07-31 --limit 100
"""
from __future__ import annotations

import datetime as DT
import time
import traceback

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q


DEFAULT_TYPES = ('autohub',)
ALLOWED_TYPES = ('autohub', 'autohub_k', 'avito', 'kors', 'custom')


class Command(BaseCommand):
    help = (
        'Пересчёт цен по интерактивным оценкам с сохранением в историю '
        '(RegInteractivOcenkaPrice). По умолчанию тип = autohub.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--from',
            dest='date_from',
            default='',
            help='Начало периода YYYY-MM-DD (по start_estimation)',
        )
        parser.add_argument(
            '--to',
            dest='date_to',
            default='',
            help='Конец периода YYYY-MM-DD (по start_estimation)',
        )
        parser.add_argument(
            '--unit-id',
            type=int,
            default=None,
            help='Фильтр по ДЦ (RegInteractivOcenkaRLK.unit_id)',
        )
        parser.add_argument(
            '--ids',
            default='',
            help='Список ID оценок (RegInteractivOcenka.id) через запятую',
        )
        parser.add_argument(
            '--types',
            default='autohub',
            help='Типы расчёта через запятую: autohub,autohub_k,avito,kors,custom',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Ограничить число оценок (0 = без лимита)',
        )
        parser.add_argument(
            '--offset',
            type=int,
            default=0,
            help='Пропустить первые N оценок',
        )
        parser.add_argument(
            '--chunk',
            type=int,
            default=50,
            help='Размер пачки для прогресса (по умолчанию 50)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать объём, без пересчёта',
        )
        parser.add_argument(
            '--no-persist',
            action='store_true',
            help='Не обновлять цены на согласовании, только история расчёта',
        )
        parser.add_argument(
            '--skip-errors',
            action='store_true',
            default=True,
            help='Продолжать при ошибках (по умолчанию да)',
        )
        parser.add_argument(
            '--stop-on-error',
            action='store_true',
            help='Остановиться на первой ошибке',
        )

    def handle(self, *args, **options):
        calc_types = self._parse_types(options['types'])
        date_from = self._parse_date(options['date_from'], end=False) if options['date_from'] else None
        date_to = self._parse_date(options['date_to'], end=True) if options['date_to'] else None
        estimation_ids = self._parse_ids(options['ids'])
        unit_id = options['unit_id']
        limit = max(0, options['limit'] or 0)
        offset = max(0, options['offset'] or 0)
        chunk = max(1, options['chunk'] or 50)
        dry_run = bool(options['dry_run'])
        persist = not bool(options['no_persist'])
        stop_on_error = bool(options['stop_on_error'])

        if not estimation_ids and date_from is None and date_to is None:
            raise CommandError(
                'Укажите период (--from/--to) или список оценок (--ids). '
                'Полный прогон без фильтра слишком опасен.'
            )

        from register.models import RegInteractivOcenkaRLK

        qs = (
            RegInteractivOcenkaRLK.objects
            .filter(estimation__isnull=False)
            .select_related(
                'estimation',
                'estimation__page_salon',
                'estimation__page_remote',
                'estimation__page_soglasovanie',
                'estimation__modification',
                'page_soglasovanie',
                'unit',
            )
            .order_by('estimation_id')
        )

        if estimation_ids:
            qs = qs.filter(estimation_id__in=estimation_ids)
        if date_from is not None:
            qs = qs.filter(estimation__start_estimation__gte=date_from)
        if date_to is not None:
            qs = qs.filter(estimation__start_estimation__lte=date_to)
        if unit_id:
            qs = qs.filter(Q(unit_id=unit_id) | Q(rlk__unit_id=unit_id) | Q(rlk__unit_dc_id=unit_id))

        total = qs.count()
        if offset:
            qs = qs[offset:]
            total = max(0, total - offset)
        if limit:
            qs = qs[:limit]
            total = min(total, limit)

        self.stdout.write(
            self.style.NOTICE(
                'Оценок: {total} | типы: {types} | persist={persist} | dry_run={dry}'.format(
                    total=total,
                    types=','.join(calc_types),
                    persist=persist,
                    dry=dry_run,
                )
            )
        )

        if dry_run:
            sample = list(qs.values_list('estimation_id', 'estimation__vin')[:20])
            for est_id, vin in sample:
                self.stdout.write('  estimation_id={} vin={}'.format(est_id, vin or ''))
            if total > 20:
                self.stdout.write('  ... и ещё {}'.format(total - 20))
            return

        from eco.views import (
            estimations_price_calculation,
            get_body_estimation_cached,
            get_salon_estimation_cached,
        )
        from register.interactive_price_history import (
            ensure_page_soglasovanie,
            interactive_price_history_context,
        )

        ok = 0
        skipped = 0
        errors = 0
        history_written = 0
        started = time.time()

        # values_list + iterator по id, затем get — меньше памяти на тяжёлых select_related
        id_list = list(qs.values_list('id', flat=True))
        total = len(id_list)

        for idx, rlk_id in enumerate(id_list, start=1):
            try:
                interactiv_rlk = (
                    RegInteractivOcenkaRLK.objects
                    .select_related(
                        'estimation',
                        'estimation__page_salon',
                        'estimation__page_remote',
                        'estimation__page_soglasovanie',
                        'estimation__modification',
                        'page_soglasovanie',
                        'unit',
                    )
                    .get(pk=rlk_id)
                )
                estimation = interactiv_rlk.estimation
                if estimation is None:
                    skipped += 1
                    continue

                ensure_page_soglasovanie(interactiv_rlk=interactiv_rlk, estimation=estimation)
                body_info = get_body_estimation_cached(estimation)
                salon_info = get_salon_estimation_cached(estimation)

                wrote_any = False
                with interactive_price_history_context(
                    user=None,
                    trigger='batch_recalc',
                    save_history=True,
                ):
                    for calc_type in calc_types:
                        result = estimations_price_calculation(
                            interactiv_rlk,
                            estimation,
                            type_calculation=calc_type,
                            user=None,
                            trigger='batch_recalc',
                            save_history=True,
                            body_info=body_info,
                            salon_info=salon_info,
                            persist=persist,
                        )
                        if result is None:
                            continue
                        wrote_any = True
                        history_written += 1

                if wrote_any:
                    ok += 1
                else:
                    skipped += 1

            except Exception as exc:
                errors += 1
                self.stderr.write(
                    self.style.ERROR(
                        '[{}/{}] rlk_id={} error: {}: {}'.format(
                            idx, total, rlk_id, type(exc).__name__, exc,
                        )
                    )
                )
                if stop_on_error:
                    raise
                if options.get('verbosity', 1) >= 2:
                    self.stderr.write(traceback.format_exc())

            if idx % chunk == 0 or idx == total:
                elapsed = time.time() - started
                rate = idx / elapsed if elapsed else 0
                self.stdout.write(
                    '[{}/{}] ok={} skip={} err={} history={} ({:.1f}/s)'.format(
                        idx, total, ok, skipped, errors, history_written, rate,
                    )
                )

        elapsed = time.time() - started
        self.stdout.write(
            self.style.SUCCESS(
                'Готово за {:.1f}с: ok={} skip={} err={} history_rows={}'.format(
                    elapsed, ok, skipped, errors, history_written,
                )
            )
        )

    def _parse_types(self, raw):
        types = []
        for part in (raw or 'autohub').split(','):
            key = part.strip().lower()
            if not key:
                continue
            if key not in ALLOWED_TYPES:
                raise CommandError(
                    'Неизвестный тип расчёта: {!r}. Допустимо: {}'.format(
                        key, ', '.join(ALLOWED_TYPES),
                    )
                )
            if key not in types:
                types.append(key)
        return types or list(DEFAULT_TYPES)

    def _parse_ids(self, raw):
        if not raw:
            return []
        ids = []
        for part in raw.split(','):
            part = part.strip()
            if not part:
                continue
            try:
                ids.append(int(part))
            except ValueError:
                raise CommandError('Некорректный id в --ids: {!r}'.format(part))
        return ids

    def _parse_date(self, value, end=False):
        try:
            day = DT.datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            raise CommandError('Некорректная дата: {!r}, ожидается YYYY-MM-DD'.format(value))
        if end:
            return day.replace(hour=23, minute=59, second=59, microsecond=0)
        return day.replace(hour=0, minute=0, second=0, microsecond=0)
