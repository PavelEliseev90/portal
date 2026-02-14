"""
Сервисы для генерации XML и управления выгрузками
"""
import xml.etree.ElementTree as ET
from xml.dom import minidom
from django.db.models import Q
from refs.models import RefCarsOrganization
from .models import ClassifiedsExportConfig, ClassifiedsExportHistory, ClassifiedsExportLog
from datetime import datetime
import os
from django.conf import settings
import json


class ClassifiedsExportService:
    """Сервис для выгрузки автомобилей"""
    
    def __init__(self, config: ClassifiedsExportConfig):
        self.config = config
    
    def get_cars_queryset(self):
        """Получить queryset автомобилей согласно фильтрам настройки"""
        qs = RefCarsOrganization.objects.all()
        
        # Фильтр по подразделениям
        if self.config.filter_units.exists():
            qs = qs.filter(unit__in=self.config.filter_units.all())
        elif self.config.unit:
            qs = qs.filter(unit=self.config.unit)
        
        # Фильтр по статусам
        if self.config.filter_statuses.exists():
            qs = qs.filter(status__in=self.config.filter_statuses.all())
        
        # Фильтр по новым/б/у
        if self.config.filter_is_new is not None:
            qs = qs.filter(is_new=self.config.filter_is_new)
        
        # Фильтр по цене
        if self.config.filter_min_price is not None:
            qs = qs.filter(price__gte=self.config.filter_min_price)
        if self.config.filter_max_price is not None:
            qs = qs.filter(price__lte=self.config.filter_max_price)
        
        # Фильтр по году
        if self.config.filter_min_year is not None:
            qs = qs.filter(year__gte=self.config.filter_min_year)
        if self.config.filter_max_year is not None:
            qs = qs.filter(year__lte=self.config.filter_max_year)
        
        # Фильтр по маркам
        if self.config.filter_marks:
            marks = [m.strip() for m in self.config.filter_marks.split(',') if m.strip()]
            if marks:
                qs = qs.filter(mark__in=marks)
        
        # Исключить VIN
        if self.config.filter_exclude_vin:
            exclude_vins = [v.strip() for v in self.config.filter_exclude_vin.split('\n') if v.strip()]
            if exclude_vins:
                qs = qs.exclude(vin__in=exclude_vins)
        
        # Исключить зарезервированные
        if not self.config.include_reserved:
            qs = qs.filter(reserve=0)
        
        # Исключить проданные (quantity > 0)
        if not self.config.include_sold:
            qs = qs.filter(quantity__gt=0)
        
        # Ограничение количества
        if self.config.max_cars_per_export:
            qs = qs[:self.config.max_cars_per_export]
        
        return qs
    
    def generate_xml(self, cars):
        """Генерация XML для списка автомобилей"""
        # Получаем шаблон XML из площадки или используем стандартный
        if self.config.platform and self.config.platform.xml_template:
            # Здесь можно использовать шаблон из площадки
            root = ET.fromstring(self.config.platform.xml_template)
        else:
            # Стандартный шаблон
            root = ET.Element('cars')
            root.set('version', '1.0')
            root.set('date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        # Добавляем автомобили
        for car in cars:
            car_element = self._create_car_element(car)
            root.append(car_element)
        
        return root
    
    def _create_car_element(self, car):
        """Создать XML элемент для автомобиля"""
        car_elem = ET.Element('car')
        
        # Получаем маппинги полей
        mappings = self.config.field_mappings.all().order_by('sort_order')
        
        if mappings.exists():
            # Используем маппинги
            for mapping in mappings:
                value = self._get_car_field_value(car, mapping.car_field)
                if value is None or value == '':
                    value = mapping.default_value
                
                # Применяем функцию преобразования если есть
                if mapping.transform_function:
                    value = self._apply_transform(value, mapping.transform_function)
                
                # Создаем элемент
                field_elem = ET.SubElement(car_elem, mapping.platform_field)
                field_elem.text = str(value) if value is not None else ''
        else:
            # Стандартный маппинг без настроек
            self._add_standard_fields(car_elem, car)
        
        return car_elem
    
    def _get_car_field_value(self, car, field_path):
        """Получить значение поля автомобиля по пути (поддержка вложенных полей)"""
        try:
            parts = field_path.split('.')
            value = car
            for part in parts:
                value = getattr(value, part, None)
                if value is None:
                    return None
                # Если это ForeignKey, получаем связанный объект
                if hasattr(value, 'pk'):
                    if hasattr(value, '__str__'):
                        # Если это связанный объект, можно вернуть его строковое представление
                        # или продолжить путь
                        if len(parts) > parts.index(part) + 1:
                            continue
                        else:
                            return str(value)
            return value
        except:
            return None
    
    def _apply_transform(self, value, transform_function):
        """Применить функцию преобразования к значению"""
        # Здесь можно добавить различные функции преобразования
        # Например: 'uppercase', 'lowercase', 'format_price', и т.д.
        transforms = {
            'uppercase': lambda x: str(x).upper(),
            'lowercase': lambda x: str(x).lower(),
            'format_price': lambda x: f"{int(x):,}".replace(',', ' ') if x else '0',
            'format_year': lambda x: str(int(x)) if x else '',
        }
        
        if transform_function in transforms:
            return transforms[transform_function](value)
        return value
    
    def _add_standard_fields(self, car_elem, car):
        """Добавить стандартные поля автомобиля в XML"""
        fields = {
            'vin': car.vin,
            'mark': car.mark,
            'model': car.model,
            'modification': car.modification,
            'year': car.year,
            'price': car.price,
            'run': car.run,
            'color': car.color,
            'engine_volume': car.engine_volume,
            'engine_power': car.engine_power,
            'plate_number': car.plate_number,
        }
        
        # Добавляем связанные объекты
        if car.type_body:
            fields['body_type'] = car.type_body.name
        if car.type_gear:
            fields['gear_type'] = car.type_gear.name
        if car.type_engine:
            fields['engine_type'] = car.type_engine.name
        if car.type_drive:
            fields['drive_type'] = car.type_drive.name
        
        for field_name, field_value in fields.items():
            if field_value is not None and field_value != '':
                field_elem = ET.SubElement(car_elem, field_name)
                field_elem.text = str(field_value)
    
    def export_to_file(self, user=None):
        """Выполнить выгрузку в файл"""
        # Создаем запись истории
        history = ClassifiedsExportHistory.objects.create(
            config=self.config,
            status='processing',
            user=user,
            is_manual=(user is not None),
            date_start=datetime.now()
        )
        
        try:
            # Получаем автомобили
            cars_qs = self.get_cars_queryset()
            cars = list(cars_qs)
            cars_count = len(cars)
            
            history.cars_count = cars_count
            history.save()
            
            if cars_count == 0:
                history.status = 'error'
                history.error_message = 'Не найдено автомобилей для выгрузки'
                history.date_end = datetime.now()
                history.save()
                return history
            
            # Генерируем XML
            root = self.generate_xml(cars)
            
            # Форматируем XML
            xml_string = self._prettify_xml(root)
            
            # Сохраняем файл
            file_name = self._generate_file_name()
            file_path = self._save_file(file_name, xml_string)
            
            # Обновляем историю
            exported_count = 0
            skipped_count = 0
            error_count = 0
            
            for car in cars:
                try:
                    # Создаем лог для каждого автомобиля
                    car_xml = self._create_car_element(car)
                    xml_data = ET.tostring(car_xml, encoding='unicode')
                    
                    ClassifiedsExportLog.objects.create(
                        export_history=history,
                        car=car,
                        status='success',
                        xml_data=xml_data
                    )
                    exported_count += 1
                except Exception as e:
                    ClassifiedsExportLog.objects.create(
                        export_history=history,
                        car=car,
                        status='error',
                        error_message=str(e)
                    )
                    error_count += 1
            
            history.status = 'success' if error_count == 0 else ('partial' if exported_count > 0 else 'error')
            history.cars_exported = exported_count
            history.cars_skipped = skipped_count
            history.cars_errors = error_count
            history.file_path = file_path
            history.file_name = file_name
            history.file_size = len(xml_string.encode('utf-8'))
            history.date_end = datetime.now()
            history.save()
            
            return history
            
        except Exception as e:
            history.status = 'error'
            history.error_message = str(e)
            history.date_end = datetime.now()
            history.save()
            return history
    
    def _prettify_xml(self, elem):
        """Форматировать XML для читаемости"""
        rough_string = ET.tostring(elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ", encoding='utf-8').decode('utf-8')
    
    def _generate_file_name(self):
        """Сгенерировать имя файла по шаблону"""
        template = self.config.file_name_template
        replacements = {
            '{platform}': self.config.platform.code if self.config.platform else 'unknown',
            '{date}': datetime.now().strftime('%Y%m%d_%H%M%S'),
            '{unit}': self.config.unit.code if self.config.unit and hasattr(self.config.unit, 'code') else (self.config.unit.name if self.config.unit else 'all'),
            '{count}': str(self.config.max_cars_per_export) if self.config.max_cars_per_export else 'all',
        }
        
        file_name = template
        for key, value in replacements.items():
            file_name = file_name.replace(key, value)
        
        # Убираем недопустимые символы
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            file_name = file_name.replace(char, '_')
        
        return file_name
    
    def _save_file(self, file_name, xml_content):
        """Сохранить XML файл"""
        # Определяем путь
        base_path = self.config.file_path
        if not base_path.startswith('/'):
            base_path = '/' + base_path
        if not base_path.endswith('/'):
            base_path += '/'
        
        # Полный путь относительно MEDIA_ROOT
        full_path = os.path.join(settings.MEDIA_ROOT, base_path.lstrip('/'))
        
        # Создаем директорию если не существует
        os.makedirs(full_path, exist_ok=True)
        
        # Сохраняем файл
        file_path = os.path.join(full_path, file_name)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        # Возвращаем путь относительно MEDIA_ROOT для сохранения в БД
        return os.path.join(base_path, file_name).replace('\\', '/')

