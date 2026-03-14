"""
Management command для создания миниатюр RegRegInteractivOcenkaFiles.
Обрабатывает файлы оценок с start_estimation >= 01.01.2026.

Использование:
    python manage.py generate_estimation_thumbnails
    python manage.py generate_estimation_thumbnails --dry-run
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime

from register.models import RegRegInteractivOcenkaFiles


class Command(BaseCommand):
    help = 'Создание миниатюр 400×300 для фото RegRegInteractivOcenkaFiles (оценки с 01.01.2026)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать список без генерации',
        )
        parser.add_argument(
            '--date',
            type=str,
            default='2026-01-01',
            help='Дата отсечки (YYYY-MM-DD). По умолчанию 2026-01-01',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        date_str = options['date']
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            dt = timezone.make_aware(dt)
        except ValueError:
            self.stdout.write(self.style.ERROR(f'Неверный формат даты: {date_str}. Используйте YYYY-MM-DD'))
            return

        qs = RegRegInteractivOcenkaFiles.objects.filter(
            estimation__start_estimation__gte=dt,
        ).filter(
            file__isnull=False,
        ).exclude(
            file='',
        ).order_by('id')

        total = qs.count()
        self.stdout.write(f'Найдено записей с файлами (start_estimation >= {date_str}): {total}')

        if dry_run:
            for obj in qs[:20]:
                video = 'видео' if obj.is_video() else 'фото'
                self.stdout.write(f'  id={obj.id} estimation={obj.estimation_id} {obj.file.name} ({video})')
            if total > 20:
                self.stdout.write(f'  ... и ещё {total - 20}')
            return

        ok = 0
        skip = 0
        err = 0
        for obj in qs:
            if not obj.file or not obj.file.name:
                skip += 1
                continue
            if obj.is_video():
                skip += 1
                continue
            try:
                obj._generate_thumbnail()
                ok += 1
                if ok % 50 == 0:
                    self.stdout.write(f'  обработано {ok}...')
            except Exception as e:
                err += 1
                self.stdout.write(self.style.WARNING(f'  id={obj.id}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Готово: создано {ok}, пропущено {skip}, ошибок {err}'))
