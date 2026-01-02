# Система подтверждения обработки персональных данных

## Описание

Реализована система для получения согласия клиентов на обработку их персональных данных. Система создает уникальные ссылки для каждого клиента, которые ведут на форму подтверждения согласия.

## Компоненты

### 1. Модель `PersonalDataConsent`

**Файл:** `portal/apps/online/models.py`

Модель хранит информацию о согласиях на обработку персональных данных:

- **Уникальный токен** - для создания ссылки подтверждения
- **ФИО клиента** - фамилия, имя, отчество
- **Номер телефона** - обязательное поле
- **Связи** - с `RefCustomer` и `RefUnit` (опционально)
- **Даты и время** - создания, открытия, подтверждения, отзыва
- **Техническая информация** - IP адрес, User Agent
- **Статус** - подтверждено/отозвано
- **Текст согласия** - сохраненная версия на момент подтверждения

### 2. Views

**Файл:** `portal/apps/online/views.py`

- `personal_data_consent(request, token)` - отображение формы и обработка подтверждения
- `get_consent_text()` - возвращает актуальный текст согласия

### 3. Утилиты

**Файл:** `portal/apps/online/utils.py`

- `create_consent_link()` - создает новую запись согласия и возвращает ссылку
- `get_consent_by_token()` - получает согласие по токену

### 4. URL маршруты

**Файл:** `portal/apps/online/urls.py`

```python
path('consent/<str:token>/', views.personal_data_consent, name='personal_data_consent')
```

### 5. Шаблоны

- `personal_data_consent.html` - форма подтверждения
- `personal_data_consent_success.html` - страница успешного подтверждения
- `personal_data_consent_404.html` - страница ошибки (ссылка не найдена)
- `personal_data_consent_revoked.html` - страница отозванного согласия

### 6. Админка

**Файл:** `portal/apps/online/admin.py`

Модель зарегистрирована в админке Django с удобным интерфейсом для просмотра и управления согласиями.

## Использование

### Создание ссылки для клиента

```python
from online.utils import create_consent_link
from refs.models import RefCustomer, RefUnit

# Создание ссылки с минимальными данными
result = create_consent_link(
    phone='+79991234567',
    unit=unit_object,  # опционально
    customer=customer_object  # опционально
)

# result содержит:
# {
#     'consent': объект PersonalDataConsent,
#     'url': полная ссылка для отправки клиенту,
#     'token': токен для ссылки
# }

# Отправка ссылки клиенту (SMS, email и т.д.)
send_sms(phone, f"Подтвердите согласие: {result['url']}")
```

### Проверка статуса согласия

```python
from online.utils import get_consent_by_token

consent = get_consent_by_token(token)
if consent and consent.confirmed:
    print(f"Согласие подтверждено: {consent.date_confirmed}")
```

## Формат ссылки

Ссылка имеет формат: `/online/consent/<token>/`

Где `token` - это уникальный 32-символьный токен, автоматически генерируемый при создании записи.

## Юридические требования

Форма включает:

1. **Полный текст согласия** согласно ФЗ-152 "О персональных данных"
2. **Обязательные поля** - ФИО и телефон
3. **Чекбокс согласия** - обязательное подтверждение
4. **Логирование** - дата/время создания, открытия, подтверждения
5. **Техническая информация** - IP адрес, User Agent для юридической защиты
6. **Сохранение версии текста** - текст согласия сохраняется на момент подтверждения

## Безопасность

- Уникальные токены (32 символа)
- Защита от CSRF (Django CSRF token)
- Валидация данных на сервере
- Логирование всех действий
- Невозможность повторного подтверждения (показывается страница успеха)

## Миграция

Для применения изменений выполните:

```bash
python manage.py makemigrations online
python manage.py migrate
```

## Пример использования в коде

```python
# В любом view или API endpoint
from online.utils import create_consent_link

def some_view(request):
    # Создаем ссылку для клиента
    result = create_consent_link(
        phone='+79991234567',
        last_name='Иванов',
        first_name='Иван',
        middle_name='Иванович',
        unit=request.user.profile.unit,
        comment='Создано при оформлении заказа'
    )
    
    # Отправляем ссылку клиенту
    send_notification(
        phone=result['consent'].phone,
        message=f"Подтвердите согласие на обработку персональных данных: {result['url']}"
    )
    
    return JsonResponse({'consent_url': result['url']})
```

