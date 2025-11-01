# Система уведомлений - краткое руководство

## Настройка автоматической проверки

Создайте задачу в планировщике (cron) для автоматической проверки:

### Windows (Task Scheduler)
```
python D:\portal_kg\portal_kg\manage.py generate_preparation_notifications
```

### Linux (cron)
```cron
# Проверка каждые 10 минут
*/10 * * * * cd /path/to/project && python manage.py generate_preparation_notifications
```

## Доступ к уведомлениям

### Веб-интерфейс
- Список: `/car_preparation/notifications/`
- В списке подготовок: есть счетчик непрочитанных уведомлений

### API
- Получение: `GET /api/car_preparation/notifications/`
- Статистика: `GET /api/car_preparation/notifications/stats/`
- Отметить прочитанным: `POST /api/car_preparation/notifications/{id}/mark_read/`
- Отметить все: `POST /api/car_preparation/notifications/mark_all_read/`

## Типы уведомлений

1. **work_upcoming** - Работа должна начаться (за 30 мин)
2. **work_overdue** - Работа просрочена
3. **preparation_overdue** - Подготовка просрочена
4. **started** - Работа начата
5. **work_completed** - Работа выполнена

## Тестирование

Для проверки генерации уведомлений без их создания:

```python
from car_preparation.notifications import generate_notifications

# Только статистика без создания
stats = generate_notifications(send_notifications=False)
print(stats)
```

