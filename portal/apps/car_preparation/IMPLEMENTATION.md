# Руководство по внедрению модуля подготовки автомобилей

## Обзор

Модуль `car_preparation` предоставляет комплексное решение для автоматизации и мобильности работы отдела подготовки автомобилей. Модуль включает в себя:

- Управление этапами и работами по подготовке
- Контроль качества и чек-листы
- Мобильный интерфейс для выполнения работ
- Фотофиксацию этапов
- Отчетность и аналитику
- Интеграцию с мобильными приложениями

## Структура модуля

```
car_preparation/
├── __init__.py
├── apps.py                    # Конфигурация приложения
├── models.py                  # Модели данных
├── admin.py                   # Административный интерфейс
├── serializers.py             # Сериализаторы для API
├── api_views.py               # API Views для REST API
├── views.py                   # Обычные views для веб-интерфейса
├── urls.py                    # URL маршруты
├── tests.py                   # Тесты
├── templates/                 # HTML шаблоны
│   └── car_preparation/
│       ├── mobile_checklist.html      # Мобильный интерфейс
│       └── preparation_report.html    # Отчет
├── README.md                  # Документация
└── IMPLEMENTATION.md          # Данный файл
```

## Шаги внедрения

### 1. Установка модуля

1. Добавьте модуль в `INSTALLED_APPS` в `settings.py`:

```python
INSTALLED_APPS = [
    ...
    'car_preparation.apps.CarPreparationConfig',
    ...
]
```

2. Подключите URLs в главный `urls.py`:

```python
urlpatterns = [
    ...
    path('car_preparation/', include('car_preparation.urls')),
    ...
]
```

3. Для API добавьте в API routes (если используется DRF):

```python
from car_preparation.api_views import (
    CarPreparationViewSet,
    CarPreparationWorkItemViewSet,
    CarPreparationPhotoViewSet,
    CarPreparationChecklistViewSet
)

router.register(r'car_preparation', CarPreparationViewSet, basename='car_preparation')
router.register(r'car_preparation/work_items', CarPreparationWorkItemViewSet, basename='work_item')
router.register(r'car_preparation/photos', CarPreparationPhotoViewSet, basename='photo')
router.register(r'car_preparation/checklists', CarPreparationChecklistViewSet, basename='checklist')
```

### 2. Миграции базы данных

```bash
python manage.py makemigrations car_preparation
python manage.py migrate car_preparation
```

### 3. Настройка справочников

Создайте начальные данные через админ-панель Django:

#### 3.1. Статусы подготовки

- `new` - Новая (начальное состояние)
- `in_progress` - В работе
- `quality_check` - Контроль качества
- `completed` - Завершена
- `cancelled` - Отменена
- `archived` - Архивирована

#### 3.2. Этапы подготовки

Примерные этапы:
1. Приемка и осмотр (sort_order: 10)
2. Диагностика (sort_order: 20)
3. Ремонт и обслуживание (sort_order: 30)
4. Мойка и деталинг (sort_order: 40)
5. Полировка и защита (sort_order: 50)
6. Финальный контроль (sort_order: 60)

#### 3.3. Виды работ

Создайте работы для каждого этапа, например:

**Приемка и осмотр:**
- Внешний осмотр кузова
- Проверка документов
- Проверка комплектности
- Замер пробега

**Диагностика:**
- Компьютерная диагностика
- Проверка систем безопасности
- Проверка электроники
- Диагностика двигателя

**И т.д.**

#### 3.4. Шаблоны подготовки

Создайте шаблоны для разных типов автомобилей:
- "Полная подготовка БУ" - для подержанных автомобилей
- "Базовая подготовка" - минимальная подготовка
- "Премиум подготовка" - расширенная подготовка
- "Срочная подготовка" - ускоренная подготовка

### 4. Интеграция с существующими моделями

#### 4.1. Связь с RefCarsOrganization

Модуль уже интегрирован с моделью `RefCarsOrganization`. При создании подготовки автомобиль связывается через ForeignKey.

#### 4.2. Автоматическое создание подготовки

Можно добавить автоматическое создание подготовки при определенных условиях:

```python
# В сигналах или при создании DocLO
from car_preparation.models import CarPreparation, RefCarPreparationStatus
from refs.models import RefCarsOrganization

def create_preparation_on_estimate(car_organization):
    status_new = RefCarPreparationStatus.objects.get(code='new')
    preparation = CarPreparation.objects.create(
        car=car_organization,
        unit=car_organization.unit,
        status=status_new,
        comment_initial='Автоматически создана при оценке'
    )
    # Применить шаблон
    template = CarPreparationTemplate.objects.filter(
        is_default=True
    ).first()
    if template:
        apply_template_to_preparation(template, preparation)
    return preparation
```

### 5. Мобильное приложение

#### 5.1. Доступ через QR-код

Каждая подготовка имеет уникальный QR-код для быстрого доступа. Код генерируется автоматически или через API endpoint `/api/car_preparation/{id}/qr/`

#### 5.2. REST API для мобильного приложения

API endpoints:

**Подготовки:**
- `GET /api/car_preparation/` - Список подготовок
- `GET /api/car_preparation/?mobile=true` - Активные для мобильного
- `GET /api/car_preparation/?qr_code=XXX` - Поиск по QR
- `POST /api/car_preparation/` - Создание подготовки
- `GET /api/car_preparation/{id}/` - Детали подготовки
- `POST /api/car_preparation/{id}/complete/` - Завершение

**Работы:**
- `GET /api/car_preparation/work_items/?preparation_id={id}` - Работы подготовки
- `POST /api/car_preparation/work_items/{id}/start/` - Начать работу
- `POST /api/car_preparation/work_items/{id}/complete/` - Завершить работу

**Фотографии:**
- `POST /api/car_preparation/photos/` - Загрузить фото
- `GET /api/car_preparation/photos/?work_item_id={id}` - Фото работы

### 6. Примеры использования

#### 6.1. Создание подготовки в коде

```python
from car_preparation.models import CarPreparation, RefCarPreparationStatus, CarPreparationTemplate
from refs.models import RefCarsOrganization, RefUnit, RefStaff

# Получить автомобиль
car = RefCarsOrganization.objects.get(vin='ABC123...')

# Создать подготовку
status_new = RefCarPreparationStatus.objects.get(code='new')
preparation = CarPreparation.objects.create(
    car=car,
    unit=car.unit,
    status=status_new,
    responsible=RefStaff.objects.get(id=responsible_id),
    date_planned_end=datetime.now() + timedelta(days=3),
    comment_initial='Полная подготовка для продажи'
)

# Применить шаблон
template = CarPreparationTemplate.objects.get(name='Полная подготовка БУ')
for template_work in template.carpreparationtemplatework_set.all():
    CarPreparationWorkItem.objects.create(
        preparation=preparation,
        work=template_work.work,
        planned_time=template_work.planned_time,
        cost=template_work.default_cost
    )
```

#### 6.2. Обновление работы через API

```python
import requests

# Завершить работу
response = requests.post(
    f'/api/car_preparation/work_items/{work_item_id}/complete/',
    json={
        'actual_time': 45,
        'cost': 1500.00,
        'comment': 'Работа выполнена качественно',
        'quality': 'excellent'
    },
    headers={'Authorization': 'Token YOUR_TOKEN'}
)
```

#### 6.3. Загрузка фотографий

```python
files = {'photo': open('photo.jpg', 'rb')}
data = {
    'work_item': work_item_id,
    'preparation': preparation_id,
    'description': 'Фото после мойки',
    'latitude': 55.7558,
    'longitude': 37.6173
}
response = requests.post(
    '/api/car_preparation/photos/',
    files=files,
    data=data,
    headers={'Authorization': 'Token YOUR_TOKEN'}
)
```

### 7. Кастомизация

#### 7.1. Добавление собственных этапов и работ

Через админ-панель Django можно легко добавлять новые этапы и виды работ.

#### 7.2. Настройка шаблонов

Создайте шаблоны под специфику вашего бизнеса, определив наборы работ для разных сценариев.

#### 7.3. Интеграция с уведомлениями

Модель `CarPreparationNotification` готова для интеграции с системами уведомлений (Email, SMS, Push).

### 8. Отчетность

Отчеты доступны через веб-интерфейс по URL:
```
/car_preparation/report/{preparation_id}/
```

Отчеты включают:
- Информацию об автомобиле
- Список выполненных работ
- Время и стоимость
- Результаты контроля качества
- Фотофиксацию
- Подписи ответственных

### 9. Рекомендации по использованию

1. **Планирование времени**: Используйте оценки времени для планирования загрузки сотрудников
2. **Контроль качества**: Обязательно используйте чек-листы для финального контроля
3. **Фотофиксация**: Делайте фото на каждом этапе для доказательства качества работ
4. **Мобильность**: Используйте мобильный интерфейс для удобства работы в цехе
5. **Шаблоны**: Создайте несколько шаблонов для разных типов подготовки

### 10. Расширение функциональности

Модуль легко расширяется. Можно добавить:

- Интеграцию с системами учета времени
- Автоматический расчет стоимости на основе норм времени
- Интеграцию с системами закупок для заказа материалов
- Автоматические уведомления менеджеров о просрочках
- Дашборды и аналитику для руководства
- Интеграцию с системами документооборота

## Поддержка

При возникновении вопросов по внедрению модуля обращайтесь к разработчикам или изучайте исходный код в `models.py` и `api_views.py`.

