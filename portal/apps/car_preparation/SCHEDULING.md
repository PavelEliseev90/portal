# Руководство по планированию работ и календарю

## Обзор функциональности

Модуль планирования работ позволяет:

1. **Планировать время выполнения работ** - назначение конкретных временных слотов
2. **Назначать исполнителей** - распределение работ между сотрудниками
3. **Управлять приоритетами** - установка приоритетов выполнения
4. **Контролировать загрузку** - отслеживание занятости исполнителей
5. **Визуализировать расписание** - календарное представление работ
6. **Автоматическое планирование** - автоматическое распределение работ

## Модели

### CarPreparationWorkSchedule
Хранит расписание конкретной работы:
- `planned_start` / `planned_end` - временные рамки
- `planned_performer` - назначенный исполнитель
- `priority` - приоритет (low, normal, high, urgent)
- `planning_status` - статус планирования
- `blocks_time` - блокирует ли время исполнителя

### CarPreparationCalendar
Агрегированная статистика по дням:
- Количество подготовок
- Загрузка исполнителей
- Процент использования ресурсов

### CarPreparationResource
Ресурсы для планирования (исполнители, оборудование):
- Рабочее время
- Рабочие дни недели
- Максимальная параллельная загрузка

## Использование

### Создание расписания для работы

```python
from car_preparation.models import CarPreparationWorkSchedule
from datetime import datetime, timedelta

schedule = CarPreparationWorkSchedule.objects.create(
    work_item=work_item,
    planned_start=datetime(2024, 1, 15, 10, 0),
    planned_end=datetime(2024, 1, 15, 11, 30),
    planned_performer=staff_member,
    priority='high',
    planning_status='scheduled',
    blocks_time=True
)
```

### Проверка пересечений

```python
# Проверка, есть ли пересечения с другими работами
overlapping_schedules = CarPreparationWorkSchedule.objects.filter(
    planned_performer=performer,
    planned_start__lt=end_time,
    planned_end__gt=start_time,
    planning_status__in=['scheduled', 'in_progress']
).exclude(work_item=current_work_item)

if overlapping_schedules.exists():
    print("Время занято")
```

### Автоматическое планирование

```python
# Через API
POST /api/car_preparation/schedule/auto/{preparation_id}/

# Или в коде
preparation.auto_schedule()
```

### Получение календаря

**Веб-интерфейс:**
```
/car_preparation/calendar/?unit_id=1&start_date=2024-01-01&end_date=2024-01-31
```

**API:**
```
GET /api/car_preparation/schedule/?date_from=2024-01-01&date_to=2024-01-31&performer_id=5
```

## Веб-интерфейсы

### Календарь (`/car_preparation/calendar/`)
- Отображение работ в календарном виде
- Фильтрация по подразделениям и периодам
- Навигация по месяцам
- Цветовая индикация приоритетов

### Планирование подготовки (`/car_preparation/schedule/{preparation_id}/`)
- Список всех работ подготовки
- Формы для назначения времени и исполнителей
- Кнопка автоматического планирования
- Отображение статусов планирования

## API Endpoints

### Создание расписания
```
POST /api/car_preparation/schedule/create_schedule/
Body: {
    "work_item_id": 123,
    "planned_start": "2024-01-15T10:00:00",
    "planned_end": "2024-01-15T11:30:00",
    "planned_performer_id": 5,
    "priority": "high"
}
```

### Получение расписаний
```
GET /api/car_preparation/schedule/?preparation_id=10&date_from=2024-01-01
```

### Автоматическое планирование
```
POST /api/car_preparation/schedule/auto/{preparation_id}/
```

## Приоритеты

- **low** - Низкий приоритет (серая метка)
- **normal** - Обычный приоритет (синяя метка)
- **high** - Высокий приоритет (красная метка)
- **urgent** - Срочный приоритет (темно-красная метка)

## Проверка доступности ресурсов

Модель `CarPreparationResource` автоматически проверяет:
1. Активность ресурса
2. Рабочие дни недели
3. Рабочее время
4. Текущую загрузку

```python
resource = CarPreparationResource.objects.get(id=resource_id)
if resource.is_available_at(datetime(2024, 1, 15, 10, 0)):
    print("Ресурс доступен")
```

## Интеграция с мобильным приложением

Мобильное приложение может:
- Получать список запланированных работ для исполнителя
- Отмечать начало/окончание работ
- Синхронизировать изменения расписания

```
GET /api/car_preparation/schedule/?performer_id={user_id}&date_from={today}
```

## Рекомендации

1. **Планирование заранее** - создавайте расписания сразу при создании подготовки
2. **Учитывайте приоритеты** - используйте приоритеты для управления очередностью
3. **Контроль загрузки** - следите за процентной загрузкой исполнителей
4. **Автоматизация** - используйте автоматическое планирование для стандартных случаев
5. **Гибкость** - допускайте перепланирование при необходимости

