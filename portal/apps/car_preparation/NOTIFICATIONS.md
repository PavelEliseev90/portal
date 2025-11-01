# Система уведомлений по подготовке автомобилей

## Обзор

Система автоматически создает уведомления о:
- Предстоящих работах (за N минут до начала)
- Просроченных работах
- Просроченных подготовках
- Начале и завершении работ

## Типы уведомлений

### 1. Работа должна начаться (`work_upcoming`)
Создается за 30 минут (настраивается) до запланированного времени начала работы.

**Получатели:**
- Исполнитель работы

### 2. Работа просрочена (`work_overdue`)
Создается когда срок выполнения работы прошел, а работа не завершена.

**Получатели:**
- Исполнитель работы
- Ответственный за подготовку

**Приоритет:**
- `high` - если просрочка более 24 часов
- `normal` - если просрочка менее 24 часов

### 3. Подготовка просрочена (`preparation_overdue`)
Создается когда плановый срок подготовки прошел, а подготовка не завершена.

**Получатели:**
- Ответственный за подготовку
- Все исполнители незавершенных работ

**Приоритет:**
- `urgent` - если просрочка более 3 дней
- `high` - если просрочка 3 дня и менее

### 4. Работа начата (`started`)
Создается автоматически при начале выполнения работы.

### 5. Работа выполнена (`work_completed`)
Создается автоматически при завершении работы.

## Автоматическая генерация

### Через management command

Запуск проверки и генерации уведомлений:

```bash
python manage.py generate_preparation_notifications
```

Рекомендуется настроить выполнение через cron каждые 5-15 минут:

```cron
*/10 * * * * cd /path/to/project && python manage.py generate_preparation_notifications
```

### Программно

```python
from car_preparation.notifications import (
    check_overdue_works,
    check_upcoming_works,
    check_overdue_preparations,
    generate_notifications
)

# Генерация всех уведомлений
stats = generate_notifications()

# Или по отдельности
overdue = check_overdue_works()
upcoming = check_upcoming_works(minutes_before=30)
overdue_preps = check_overdue_preparations()
```

## Веб-интерфейс

### Список уведомлений
```
/car_preparation/notifications/
```

**Фильтры:**
- Тип уведомления
- Приоритет
- Статус прочтения
- Показывать прочитанные

### Отметка как прочитанное
- Отдельное уведомление: клик на кнопку "Отметить прочитанным"
- Все уведомления: кнопка "Отметить все как прочитанные"

## API

### Получение уведомлений
```
GET /api/car_preparation/notifications/
GET /api/car_preparation/notifications/?read=false  # Только непрочитанные
GET /api/car_preparation/notifications/?type=work_overdue  # Просроченные работы
GET /api/car_preparation/notifications/?priority=urgent  # Срочные
```

### Статистика уведомлений
```
GET /api/car_preparation/notifications/stats/
Response: {
    "unread_count": 5,
    "urgent_count": 2,
    "overdue_count": 3
}
```

### Отметка как прочитанное
```
POST /api/car_preparation/notifications/{id}/mark_read/
```

### Отметка всех как прочитанных
```
POST /api/car_preparation/notifications/mark_all_read/
Response: {
    "success": true,
    "updated": 10
}
```

## Настройка

### Интервал для предупреждений о начале работы

По умолчанию: 30 минут. Можно изменить в функции `check_upcoming_works(minutes_before=30)` или через параметр команды:

```bash
python manage.py generate_preparation_notifications --upcoming-minutes=60
```

### Защита от дублирования

- Уведомления о просроченных работах создаются не чаще чем раз в час
- Уведомления о предстоящих работах создаются не чаще чем раз в (интервал + 10 минут)
- Уведомления о просроченных подготовках создаются не чаще чем раз в день

## Интеграция с другими каналами

Модель `CarPreparationNotification` поддерживает несколько каналов:
- `channel_email` - Email
- `channel_push` - Push-уведомления
- `channel_sms` - SMS

При создании уведомления можно указать каналы, которые затем могут быть обработаны отдельными сервисами для отправки.

## Примеры использования

### Создание уведомления вручную

```python
from car_preparation.models import CarPreparationNotification
from car_preparation.models import CarPreparation, CarPreparationWorkItem

notification = CarPreparationNotification.objects.create(
    preparation=preparation,
    work_item=work_item,
    notification_type='work_overdue',
    priority='high',
    message='Работа просрочена',
    recipient=staff_member,
    channel_email=True,
    channel_push=True
)
```

### Получение уведомлений для мобильного приложения

```python
# В API endpoint
notifications = CarPreparationNotification.objects.filter(
    recipient=user.staff,
    read=False,
    notification_type__in=['work_upcoming', 'work_overdue']
).order_by('-priority', '-date_created')[:10]
```

## Рекомендации

1. **Регулярная проверка**: Настройте cron на выполнение каждые 10-15 минут
2. **Приоритеты**: Используйте приоритеты для фильтрации важных уведомлений
3. **Интеграция**: Подключите отправку через Email/Push/SMS для критических уведомлений
4. **История**: Старые прочитанные уведомления можно архивировать периодически

