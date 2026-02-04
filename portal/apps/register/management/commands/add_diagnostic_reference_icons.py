"""
Management command для автоматического добавления иконок справочника диагностики в шаблон
Использование:
    python manage.py add_diagnostic_reference_icons --template portal/templates/lo/lo_v3.html
"""
from django.core.management.base import BaseCommand
import re
import os


class Command(BaseCommand):
    help = 'Добавление иконок справочника диагностики в шаблон'

    def add_arguments(self, parser):
        parser.add_argument(
            '--template',
            type=str,
            default='portal/templates/lo/lo_v3.html',
            help='Путь к шаблону'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать изменения без сохранения'
        )

    def handle(self, *args, **options):
        template_path = options['template']
        dry_run = options['dry_run']
        
        if not os.path.exists(template_path):
            self.stdout.write(self.style.ERROR(f'Файл не найден: {template_path}'))
            return
        
        # Маппинг разделов и их кодов
        sections = {
            'Двигатель': 'engine',
            'Коробка передач': 'gear',
            'КПП': 'gear',
            'Тормозная система': 'brake',
            'Подвеска': 'suspension',
            'Система выпуска ОГ': 'system_og',
            'Рулевое управление': 'wheel',
            'Кондиционер': 'conditioner',
            'Турбина': 'turbo',
            'Полный привод': 'drive',
            'ТО': 'to',
            'Подрамник': 'subframe',
            'Подушка безопасности': 'airbag',
            'Подушка безопастности': 'airbag',
        }
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = []
        
        # Паттерн для поиска заголовков разделов
        # Ищем различные варианты: <h6>, <h5>, <label> с текстом раздела
        for section_name, category_code in sections.items():
            # Паттерн 1: <h6> с иконкой и названием
            pattern1 = rf'(<h6[^>]*>.*?<span[^>]*class="[^"]*icon[^"]*"[^>]*></span>\s*{re.escape(section_name)}[^<]*</h6>)'
            replacement1 = rf'\1\n        <i class="bi bi-info-circle diagnostic-reference-icon" data-bs-toggle="modal" data-bs-target="#diagnosticReferenceModal" data-category="{category_code}" title="Открыть справочник диагностики"></i>'
            
            # Паттерн 2: <h6> без иконки
            pattern2 = rf'(<h6[^>]*>.*?{re.escape(section_name)}[^<]*</h6>)'
            replacement2 = rf'\1\n        <i class="bi bi-info-circle diagnostic-reference-icon" data-bs-toggle="modal" data-bs-target="#diagnosticReferenceModal" data-category="{category_code}" title="Открыть справочник диагностики"></i>'
            
            # Паттерн 3: <label> или другой тег
            pattern3 = rf'(<label[^>]*>.*?{re.escape(section_name)}[^<]*</label>)'
            replacement3 = rf'\1\n        <i class="bi bi-info-circle diagnostic-reference-icon" data-bs-toggle="modal" data-bs-target="#diagnosticReferenceModal" data-category="{category_code}" title="Открыть справочник диагностики"></i>'
            
            for pattern, replacement in [(pattern1, replacement1), (pattern2, replacement2), (pattern3, replacement3)]:
                matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
                if matches:
                    content = re.sub(pattern, replacement, content, flags=re.IGNORECASE | re.DOTALL)
                    changes_made.append(f'{section_name} ({category_code}): найдено {len(matches)} совпадений')
                    break
        
        # Проверяем, есть ли включение модального окна
        if 'diagnostic_reference_modal.html' not in content:
            # Ищем {% endblock %} и добавляем перед ним
            if '{% endblock %}' in content:
                include_line = '\n{% include \'lo/diagnostic_reference_modal.html\' %}\n'
                content = content.replace('{% endblock %}', include_line + '{% endblock %}')
                changes_made.append('Добавлено включение модального окна')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('Режим dry-run. Изменения не сохранены.'))
            self.stdout.write('\nНайденные изменения:')
            for change in changes_made:
                self.stdout.write(f'  - {change}')
        else:
            if content != original_content:
                with open(template_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.stdout.write(self.style.SUCCESS(f'Файл обновлен: {template_path}'))
                for change in changes_made:
                    self.stdout.write(f'  - {change}')
            else:
                self.stdout.write(self.style.WARNING('Изменений не обнаружено. Возможно, иконки уже добавлены или структура шаблона отличается.'))

