"""
Нормализация ценовых групп к единому формату отображения («1 200», «2 000», …).

Примеры:
  python manage.py normalize_price_groups --dry-run
  python manage.py normalize_price_groups
  python manage.py normalize_price_groups --seed-only
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = (
        'Приводит ценовые группы к каноническому формату: '
        'code=1200, name/label_1c=«1 200». Обновляет справочник, воронку, правила, расчёты Авито.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать изменения, без записи в БД',
        )
        parser.add_argument(
            '--seed-only',
            action='store_true',
            help='Только seed_price_groups() для справочника refGroupPrice',
        )
        parser.add_argument(
            '--skip-funnel',
            action='store_true',
            help='Не обновлять TradeInFunnel.zg_name',
        )
        parser.add_argument(
            '--skip-rules',
            action='store_true',
            help='Не обновлять EstimationRule.price_group',
        )
        parser.add_argument(
            '--skip-auction',
            action='store_true',
            help='Не обновлять AvitoLotCalculation.price_group',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        from refs.price_groups import (
            DISPLAY_BY_CODE,
            LABEL_1C_BY_CODE,
            find_duplicate_price_groups,
            normalize_price_group_display,
            seed_price_groups,
        )
        from refs.models import RefGroupPrice

        if dry_run:
            self.stdout.write(self.style.WARNING('Режим dry-run: изменения не сохраняются'))

        self._report_duplicates(find_duplicate_price_groups())

        if options['seed_only']:
            if dry_run:
                self.stdout.write('seed_price_groups: будет выполнен (не dry-run для справочника по legacy PK)')
            else:
                seed_price_groups()
                self.stdout.write(self.style.SUCCESS('seed_price_groups() выполнен'))
            return

        stats = {
            'catalog': 0,
            'funnel': 0,
            'rules': 0,
            'auction': 0,
        }

        catalog_updates = []
        for group in RefGroupPrice.objects.all().order_by('id'):
            code = str(group.code or '').strip()
            target_name = DISPLAY_BY_CODE.get(code) if code else None
            target_label = LABEL_1C_BY_CODE.get(code) if code else None
            if not target_name:
                normalized = normalize_price_group_display(group.name)
                for row_code, row_name in DISPLAY_BY_CODE.items():
                    if row_name == normalized:
                        code = row_code
                        target_name = row_name
                        target_label = LABEL_1C_BY_CODE[row_code]
                        break
            changes = []
            if code and group.code != code:
                changes.append(f'code: {group.code!r} → {code!r}')
            if target_name and group.name != target_name:
                changes.append(f'name: {group.name!r} → {target_name!r}')
            if target_label and group.label_1c != target_label:
                changes.append(f'label_1c: {group.label_1c!r} → {target_label!r}')
            if changes:
                catalog_updates.append((group, code, target_name, target_label, changes))

        self.stdout.write(f'Справочник refGroupPrice: {len(catalog_updates)} записей к обновлению')
        for group, code, target_name, target_label, changes in catalog_updates[:20]:
            self.stdout.write(f'  id={group.id}: {"; ".join(changes)}')
        if len(catalog_updates) > 20:
            self.stdout.write(f'  … и ещё {len(catalog_updates) - 20}')

        if not dry_run:
            with transaction.atomic():
                seed_price_groups()
                for group, code, target_name, target_label, _changes in catalog_updates:
                    if code:
                        group.code = code
                    if target_name:
                        group.name = target_name
                    if target_label:
                        group.label_1c = target_label
                    group.save()
                    stats['catalog'] += 1

        if not options['skip_funnel']:
            stats['funnel'] = self._normalize_funnel(dry_run, normalize_price_group_display)

        if not options['skip_rules']:
            stats['rules'] = self._normalize_rules(dry_run, normalize_price_group_display)

        if not options['skip_auction']:
            stats['auction'] = self._normalize_auction(dry_run, normalize_price_group_display)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            'Готово. Обновлено: справочник={catalog}, воронка={funnel}, '
            'правила={rules}, расчёты Авито={auction}'.format(**stats)
        ))

    def _report_duplicates(self, duplicates):
        if not duplicates:
            self.stdout.write('Дубликаты по code в refGroupPrice: не найдены')
            return
        self.stdout.write(self.style.WARNING(
            'Внимание: найдены дубликаты по code (нужно ручное слияние FK):'
        ))
        for code, rows in duplicates.items():
            ids = ', '.join(str(row.id) for row in rows)
            names = ', '.join(repr(row.name) for row in rows)
            self.stdout.write(f'  code={code}: id=[{ids}] name=[{names}]')

    def _normalize_funnel(self, dry_run, normalize_fn):
        from analytics.models import TradeInFunnel

        updated = 0
        qs = TradeInFunnel.objects.exclude(zg_name='').only('id', 'zg_name', 'zna')
        for row in qs.iterator(chunk_size=2000):
            new_name = normalize_fn(row.zg_name, price=row.zna)
            if new_name in ('Неопределена', row.zg_name):
                continue
            updated += 1
            if not dry_run:
                TradeInFunnel.objects.filter(pk=row.pk).update(zg_name=new_name)
        self.stdout.write(f'TradeInFunnel.zg_name: {updated} записей к обновлению')
        return updated

    def _normalize_rules(self, dry_run, normalize_fn):
        from estimation_engine.models import EstimationRule

        updated = 0
        qs = EstimationRule.objects.exclude(price_group='').only('id', 'price_group')
        for rule in qs.iterator(chunk_size=500):
            new_value = normalize_fn(rule.price_group)
            if new_value in ('Неопределена', rule.price_group):
                continue
            updated += 1
            if not dry_run:
                EstimationRule.objects.filter(pk=rule.pk).update(price_group=new_value)
        self.stdout.write(f'EstimationRule.price_group: {updated} записей к обновлению')
        return updated

    def _normalize_auction(self, dry_run, normalize_fn):
        from auction_avito.models import AvitoLotCalculation

        updated = 0
        qs = AvitoLotCalculation.objects.exclude(price_group='').only('id', 'price_group', 'zna')
        for calc in qs.iterator(chunk_size=2000):
            new_value = normalize_fn(calc.price_group, price=calc.zna)
            if new_value in ('Неопределена', calc.price_group):
                continue
            updated += 1
            if not dry_run:
                AvitoLotCalculation.objects.filter(pk=calc.pk).update(price_group=new_value)
        self.stdout.write(f'AvitoLotCalculation.price_group: {updated} записей к обновлению')
        return updated
