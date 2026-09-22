"""
Выгрузка соглашений о покупке автомобиля (DocCarAgreement) в MyKors.

Примеры:
  python manage.py mykors_export_agreements --limit 10
  python manage.py mykors_export_agreements --uin 6b923ed9-6747-11ed-92b4-3cecef0cf2c3
"""
from django.core.management.base import BaseCommand
from mykors import conf


class Command(BaseCommand):
    help = 'Выгрузка соглашений о покупке автомобиля (DocCarAgreement) в MyKors'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit', type=int, default=10,
            help='Лимит записей за прогон (по умолчанию 10, 0 = все)',
        )
        parser.add_argument(
            '--uin', type=str, default='',
            help='Выгрузить конкретное соглашение по UIN',
        )

    def handle(self, *args, **options):
        if not conf.is_enabled():
            self.stdout.write(self.style.WARNING(
                'MyKors выключен: задайте MYKORS_ENABLED=True и ключи API.'
            ))
            return

        limit = options['limit'] or None
        uin = options['uin'].strip() or None

        from mykors.export_car_agreements import export_car_agreements

        stats = export_car_agreements(limit=limit, uin=uin)
        self.stdout.write(self.style.SUCCESS(
            'Готово: total={total} sent={sent} created={created} '
            'updated={updated} skipped={skipped} errors={errors}'.format(**stats)
        ))
