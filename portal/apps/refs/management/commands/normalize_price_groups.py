"""
Нормализация ценовых групп к единому формату отображения («1 200», «2 000», …).

Примеры:
  python manage.py normalize_price_groups --dry-run
  python manage.py normalize_price_groups --dry-run --merge-duplicates
  python manage.py normalize_price_groups --merge-duplicates
  python manage.py normalize_price_groups --seed-only
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = (
        'Приводит ценовые группы к каноническому формату: '
        'code=1200, name/label_1c=«1 200». Обновляет справочник, воронку, правила, расчёты Авито. '
        'С --merge-duplicates переносит FK с дублей на каноническую запись и деактивирует дубли.'
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
            '--merge-duplicates',
            action='store_true',
            help='Склеить дубли по code: перенести FK и деактивировать лишние записи',
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
            PRICE_GROUP_LEGACY_PKS,
            find_duplicate_price_groups,
            normalize_price_group_display,
            seed_price_groups,
        )
        from refs.models import RefGroupPrice

        if dry_run:
            self.stdout.write(self.style.WARNING('Режим dry-run: изменения не сохраняются'))

        duplicates = find_duplicate_price_groups()
        self._report_duplicates(duplicates)

        if options['seed_only']:
            if dry_run:
                self.stdout.write('seed_price_groups: будет выполнен без dry-run')
            else:
                seed_price_groups()
                self.stdout.write(self.style.SUCCESS('seed_price_groups() выполнен'))
            return

        stats = {
            'catalog': 0,
            'merged_fk_cars': 0,
            'merged_fk_settings': 0,
            'deactivated': 0,
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

        merge_plan = []
        if options['merge_duplicates'] and duplicates:
            merge_plan = self._build_merge_plan(duplicates, DISPLAY_BY_CODE, PRICE_GROUP_LEGACY_PKS)
            self.stdout.write(f'Слияние дублей: {len(merge_plan)} групп')
            for item in merge_plan:
                dup_ids = ', '.join(str(x.id) for x in item['duplicates'])
                self.stdout.write(
                    f"  code={item['code']}: keep id={item['canonical'].id} "
                    f"({item['canonical'].name!r}), deactivate id=[{dup_ids}]"
                )

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

                if merge_plan:
                    cars, settings, deactivated = self._apply_merge_plan(merge_plan)
                    stats['merged_fk_cars'] = cars
                    stats['merged_fk_settings'] = settings
                    stats['deactivated'] = deactivated
        elif merge_plan:
            cars, settings, deactivated = self._apply_merge_plan(merge_plan, dry_run=True)
            stats['merged_fk_cars'] = cars
            stats['merged_fk_settings'] = settings
            stats['deactivated'] = deactivated

        if not options['skip_funnel']:
            stats['funnel'] = self._normalize_funnel(dry_run, normalize_price_group_display)

        if not options['skip_rules']:
            stats['rules'] = self._normalize_rules(dry_run, normalize_price_group_display)

        if not options['skip_auction']:
            stats['auction'] = self._normalize_auction(dry_run, normalize_price_group_display)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            'Готово. Обновлено: справочник={catalog}, cars.FK={merged_fk_cars}, '
            'settings.FK={merged_fk_settings}, деактивировано={deactivated}, '
            'воронка={funnel}, правила={rules}, расчёты Авито={auction}'.format(**stats)
        ))

    def _report_duplicates(self, duplicates):
        if not duplicates:
            self.stdout.write('Дубликаты по code в refGroupPrice: не найдены')
            return
        self.stdout.write(self.style.WARNING(
            'Найдены дубликаты по code. Для склейки запустите с --merge-duplicates'
        ))
        for code, rows in duplicates.items():
            ids = ', '.join(str(row.id) for row in rows)
            names = ', '.join(repr(row.name) for row in rows)
            self.stdout.write(f'  code={code}: id=[{ids}] name=[{names}]')

    def _build_merge_plan(self, duplicates, display_by_code, legacy_pks):
        plan = []
        for code, rows in duplicates.items():
            target_name = display_by_code.get(code)
            canonical = None
            if target_name:
                for row in rows:
                    if row.name == target_name:
                        canonical = row
                        break
            if canonical is None:
                preferred = legacy_pks.get(code) or []
                by_id = {row.id: row for row in rows}
                for pk in preferred:
                    if pk in by_id:
                        canonical = by_id[pk]
                        break
            if canonical is None:
                canonical = sorted(rows, key=lambda r: r.id)[0]
            dups = [row for row in rows if row.id != canonical.id]
            if dups:
                plan.append({'code': code, 'canonical': canonical, 'duplicates': dups})
        return plan

    def _apply_merge_plan(self, merge_plan, dry_run=False):
        from refs.models import RefCarsOrganization, RefGroupPrice
        from refs.unit_price_group_settings import UnitPriceGroupSettings

        cars_total = 0
        settings_total = 0
        deactivated = 0

        for item in merge_plan:
            canonical = item['canonical']
            for dup in item['duplicates']:
                cars_qs = RefCarsOrganization.objects.filter(group_price_id=dup.id)
                cars_n = cars_qs.count()
                cars_total += cars_n

                settings_qs = UnitPriceGroupSettings.objects.filter(price_group_id=dup.id)
                settings_n = settings_qs.count()
                settings_total += settings_n

                self.stdout.write(
                    f"  id={dup.id} → id={canonical.id}: cars={cars_n}, settings={settings_n}"
                )

                if not dry_run:
                    cars_qs.update(group_price_id=canonical.id)
                    settings_qs.update(price_group_id=canonical.id)
                    # update(), а не save(): иначе save() снова проставит code из name
                    RefGroupPrice.objects.filter(pk=dup.id).update(is_active=False, code='')
                    deactivated += 1
                else:
                    deactivated += 1

        return cars_total, settings_total, deactivated

    def _normalize_funnel(self, dry_run, normalize_fn):
        from analytics.models import TradeInFunnel

        updated = 0
        qs = TradeInFunnel.objects.exclude(zg_name='').only('rlk_id', 'zg_name', 'zna')
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
