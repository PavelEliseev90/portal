# API Документация для мобильного приложения KorsGroup

## Базовый URL
```
https://ah.kors-group.com/api/a/v1/
```

## Аутентификация
Все запросы (кроме авторизации) требуют Basic Authentication:
```
Authorization: Basic base64(username:password)
```

---

## 1. АВТОРИЗАЦИЯ

### POST /login_in/
Вход в систему

**Request:**
```json
{
  "username": "user@example.com",
  "password": "password123"
}
```

**Response (успех):**
```json
{
  "type": "login",
  "user": "user@example.com",
  "profiles": true,
  "answer": {
    "family": "Иванов",
    "name": "Иван",
    "phone": "+79001234567",
    "email": "user@example.com",
    "role": 0,
    "city": "",
    "date": "01-01-2024 10:00:00"
  },
  "error": ""
}
```

**Response (ошибка):**
```json
{
  "type": "login",
  "user": "",
  "profiles": false,
  "answer": null,
  "error": "Неправильная пара логин / пароль"
}
```

---

### GET /login_info/
Получение информации о текущем пользователе

**Response:**
```json
{
  "type": "login_info",
  "user": {
    "family": "Иванов",
    "name": "Иван",
    "phone": "+79001234567",
    "email": "user@example.com"
  },
  "answer": { ... },
  "error": ""
}
```

---

## 2. РАБОЧИЕ ЛИСТЫ (RLK)

### GET /rlk_eco/
Получение списка рабочих листов для оценки

**Query Parameters:**
- `type` (optional): 1 - Продолжить оценку, 2 - На согласовании

**Response:**
```json
{
  "type": "rlk_eco",
  "user": { ... },
  "objects": [
    {
      "slug": 2847904,
      "estimation": 12345,
      "estimation_vin": "WVWZZZ1KZAW123456",
      "estimation_modification_name": "1.6 MT",
      "estimation_model_name": "Polo",
      "estimation_mark_name": "Volkswagen",
      "estimation_year": 2020,
      "unit_name": "Москва",
      "estimation_start_formated": "15.01.2024 10:30:00",
      "date": "15.01.2024 09:00:00",
      "staff_name": "Иванов И.И.",
      "comment_administrator": "",
      "comment_manager": "",
      "type_contact": "Телефон",
      "customer_name": "Петров П.П.",
      "price_reception": 500000,
      "number": "RLK-2024-001"
    }
  ]
}
```

---

### GET /staff_rlks_unit/
Получение списка подразделений с RLK

**Response:**
```json
{
  "type": "staff_rlks_units",
  "user": { ... },
  "objects": [
    {
      "slug": 1,
      "name": "Москва",
      "count": 5
    }
  ]
}
```

---

### GET /staff_rlk/<rlk_id>/
Получение детальной информации о рабочем листе

**Response:**
```json
{
  "type": "staff_rlk",
  "user": { ... },
  "object": {
    "id": 2847904,
    "nomer": "RLK-2024-001",
    "dataTime": "2024-01-15T09:00:00Z",
    "clientName": "Петров П.П.",
    "phone": "+79001234567",
    "vin_trade_in": "WVWZZZ1KZAW123456",
    "unit": {
      "id": 1,
      "name": "Москва"
    },
    "staff": {
      "id": 10,
      "name": "Иванов И.И."
    }
  }
}
```

---

## 3. НАЧАЛО ОЦЕНКИ

### GET /start_estimation/<rlk_id>/
Начало оценки

**Query Parameters:**
- `type`: 1 - Стандартная, 3 - Дистанционная
- `vin`: VIN номер автомобиля

**Response:**
```json
{
  "type": "start_estimation",
  "user": { ... },
  "objects": {
    "estimation_id": 12345,
    "organizations": [
      {"slug": 1, "name": "Организация 1"}
    ],
    "filials": [
      {"slug": 1, "name": "Филиал 1"}
    ],
    "stores": [
      {"slug": 1, "name": "Склад 1"}
    ],
    "units": [
      {"slug": 1, "name": "Подразделение 1"}
    ],
    "type_receptions": [
      {"slug": 1, "name": "Тип приема 1"}
    ]
  }
}
```

---

## 4. ЭТАПЫ ОЦЕНКИ

### GET /estimation_documents_start/<rlk_id>/
Получение данных для этапа "Документы"

**Response:**
```json
{
  "type": "estimation_documents_start",
  "user": { ... },
  "object": {
    "customer_family": "Петров",
    "customer_name": "Петр",
    "customer_patronymic": "Петрович",
    "customer_phone": "+79001234567",
    "count_key": 2,
    "count_owners": 1,
    "plate_number": "А123БВ777",
    "engine_number": "ENG123456",
    "pts_color": "Белый",
    "pts_number": "77АА123456",
    "sts_number": "77СТ123456",
    "pts_date": "2020-01-15",
    "sts_date": "2020-01-20",
    "organization": {"id": 1, "name": "Организация 1"},
    "filial": {"id": 1, "name": "Филиал 1"},
    "unit": {"id": 1, "name": "Подразделение 1"},
    "store": {"id": 1, "name": "Склад 1"},
    "type_reception": {"id": 1, "name": "Тип приема 1"},
    "type_drive": "Передний"
  }
}
```

---

### POST /estimation_documents_post/<rlk_id>/
Сохранение данных этапа "Документы"

**Request:**
```json
{
  "TimeStart": 1705312800,
  "TimeEnd": 1705313100,
  "CustomerFamily": "Петров",
  "CustomerName": "Петр",
  "CustomerPatronymic": "Петрович",
  "CustomerPhone": "+79001234567",
  "CountKey": 2,
  "CountOwners": 1,
  "PlateNumber": "А123БВ777",
  "EngineNumber": "ENG123456",
  "PtsColor": "Белый",
  "PtsNumber": "77АА123456",
  "StsNumber": "77СТ123456",
  "PtsDate": "2020-01-15",
  "StsDate": "2020-01-20",
  "OrganizationId": 1,
  "FilialId": 1,
  "UnitId": 1,
  "StoreId": 1,
  "TypeReceptionId": 1,
  "TypeDrive": "Передний"
}
```

**Response:**
```json
{
  "type": "estimation_documents_post",
  "user": { ... },
  "answer": "success"
}
```

---

### POST /estimation_salon_post/<rlk_id>/
Сохранение данных этапа "Салон"

**Request:**
```json
{
  "TimeStart": 1705312800,
  "TimeEnd": 1705313100,
  "Run": 50000,
  "RunPodtv": true,
  "RunPodtvText": "Подтвержден по ПТС",
  "RSTrebHim": true,
  "RSKppFail": false,
  "RSRulFail": false,
  "RSPedalFail": false,
  "RSDverFail": false,
  "RSSidenFail": false,
  "RSRTormozOK": true,
  "RSRTormozF": false,
  "RSRConductorOK": true,
  "RSRConductorF": false,
  "RSRWiperOK": true,
  "RSRWiperF": false,
  "RSRSignalOK": true,
  "RSRSignalF": false,
  "RSRPowerWindowsOK": true,
  "RSRPowerWindowsF": false,
  "RSRSeatBeltOK": true,
  "RSRSeatBeltF": false,
  "RSRRunRespond": 1,
  "RSCleaningInt": 1,
  "RSTypeSalonInt": 1,
  "RSDamageKppInt": 0,
  "RSDamageWheelInt": 0,
  "RSDamagePedalInt": 0,
  "RSDamageDoorInt": 0,
  "RSDamageSeatInt": 0,
  "DashboardErrors": [1, 2, 3]
}
```

---

### POST /estimation_test_drive_post/<rlk_id>/
Сохранение данных этапа "Тест-драйв"

**Request:**
```json
{
  "TimeStart": 1705312800,
  "TimeEnd": 1705313100,
  "Engine": 1,
  "CommentEngine": "",
  "Gear": 1,
  "CommentGear": "",
  "Brake": 1,
  "CommentBrake": "",
  "Suspension": 1,
  "CommentSuspension": "",
  "SystemOg": 1,
  "CommentSystemOg": "",
  "Wheel": 1,
  "CommentWheel": "",
  "Conditioner": 1,
  "CommentConditioner": "",
  "Turbo": 1,
  "CommentTurbo": "",
  "Drive": 1,
  "CommentDrive": "",
  "To": 1,
  "Subframe": 1,
  "CommentSubframe": "",
  "HoodTrunkShockAbsorber": 1,
  "CommentHoodTrunkShockAbsorber": "",
  "StapeleType": 1,
  "StapeleHours": 12,
  "StapeleCost": 3000
}
```

**Примечание:** Значения для полей:
- `0` - Не работает / Не исправны
- `1` - Работает / Исправны
- `2` - Есть замечания
- `4` - Не предусмотрены
- `10` - Не проверено (по умолчанию)

---

### POST /estimation_add_fotos/<rlk_id>/
Загрузка фотографий

**Request:** multipart/form-data
- `file`: файл изображения
- `type_file`: тип файла (sts, pts, run, images_remote, и т.д.)
- `type_point`: точка осмотра (опционально)
- `text`: текст (опционально)
- `cor_x`: координата X (опционально)
- `cor_y`: координата Y (опционально)

**Response:**
```json
{
  "type": "estimation_add_fotos",
  "user": { ... },
  "answer": "success",
  "file_id": 12345
}
```

---

## 5. СПРАВОЧНИКИ (для офлайн синхронизации)

### GET /catalogs/manufacturer/
Получение списка производителей

**Response:**
```json
{
  "manufacturers": [
    {"id": 1, "name": "Volkswagen"},
    {"id": 2, "name": "Toyota"}
  ]
}
```

---

### GET /catalogs/models/<manufacturer_id>/
Получение списка моделей по производителю

**Response:**
```json
{
  "models": [
    {"id": 1, "name": "Polo", "manufacturer_id": 1},
    {"id": 2, "name": "Golf", "manufacturer_id": 1}
  ]
}
```

---

### GET /catalogs/modifications/<model_id>/
Получение списка модификаций по модели

**Query Parameters:**
- `year` (optional): Фильтр по году

**Response:**
```json
{
  "modifications": [
    {
      "id": 1,
      "name": "1.6 MT",
      "model_id": 1,
      "year": 2020,
      "engine": "1.6",
      "power": 110,
      "transmission": "MT"
    }
  ]
}
```

---

### GET /catalogs/complectations/<modification_id>/
Получение списка комплектаций по модификации

**Response:**
```json
{
  "complectations": [
    {"id": 1, "name": "Trendline", "modification_id": 1},
    {"id": 2, "name": "Comfortline", "modification_id": 1}
  ]
}
```

---

### GET /catalogs/sync_info/
Получение информации о последнем обновлении справочников

**Response:**
```json
{
  "last_update": "2024-01-15T10:00:00Z",
  "manufacturers_count": 50,
  "models_count": 500,
  "modifications_count": 2000,
  "complectations_count": 5000,
  "total_size_mb": 15.5
}
```

---

## 6. ОСМОТР КУЗОВА И САЛОНА

### GET /api/a/v1/estimation_body_elements/<rlk_id>/<type>/
Получение элементов кузова для осмотра

**Параметры:**
- `rlk_id` - ID рабочего листа
- `type` - тип осмотра (pered, vod, pass, zad, up)

**Response:**
```json
{
  "type": "estimation_body_elements",
  "elements": [
    {
      "name": "капот",
      "code": "kapot",
      "body_elem_name": "Капот",
      "polygon": "100,200,150,200,150,250,100,250",
      "coor_x": [100, 150, 150, 100],
      "coor_y": [200, 200, 250, 250]
    }
  ],
  "existing_marks": [
    {
      "id": 123,
      "type_point": "царапина",
      "x": 120,
      "y": 220,
      "text": "",
      "date": "15-01-2024 10:30",
      "photo_url": "/media/estimation/photos/photo_123.jpg"
    }
  ],
  "base_image_url": "/media_dop/body_capture/sedan_new.png"
}
```

---

### POST /api/a/v1/estimation_body_inspection_post/<rlk_id>/
Сохранение данных осмотра кузова

**Request:**
```json
{
  "inspection_type": "pered",
  "base_image": "data:image/png;base64,...",
  "marks": [
    {
      "type": "царапина",
      "x": 120,
      "y": 220,
      "text": "",
      "element_name": "капот",
      "photo": "data:image/jpeg;base64,..."
    }
  ]
}
```

**Response:**
```json
{
  "type": "estimation_body_inspection_post",
  "answer": "success"
}
```

---

### GET /api/a/v1/estimation_salon_elements/<rlk_id>/
Получение элементов салона для осмотра

**Response:**
```json
{
  "type": "estimation_salon_elements",
  "elements": [
    {
      "name": "передняя панель",
      "code": "panel",
      "polygon": "100,200,150,200,150,250,100,250",
      "coor_x": [100, 150, 150, 100],
      "coor_y": [200, 200, 250, 250]
    }
  ],
  "existing_marks": [],
  "base_image_url": "/media_dop/salon_capture/salon.png"
}
```

---

### POST /api/a/v1/estimation_salon_inspection_post/<rlk_id>/
Сохранение данных осмотра салона

**Request:**
```json
{
  "base_image": "data:image/png;base64,...",
  "marks": [
    {
      "type": "перекрас",
      "x": 120,
      "y": 220,
      "text": "",
      "element_name": "передняя панель",
      "photo": "data:image/jpeg;base64,..."
    }
  ]
}
```

---

## 7. ВЕБ-СОКЕТ ДЛЯ ЧАТА

### Подключение
**URL:** `wss://ah.kors-group.com/ws/rlk_{rlk_id}/`

**Также:** `wss://ah.kors-group.com/ws/rlk_list_eco/` (для списка оценок)

### Отправка сообщения
```json
{
  "chat_id": "123",
  "name": "user@example.com",
  "chat": "rlk_2847904",
  "message": "Текст сообщения",
  "username": "user@example.com",
  "last_name": "Иванов",
  "first_name": "Иван",
  "psevdo_name": "Иванов И.И.",
  "eco": true
}
```

### Получение сообщения
```json
{
  "type": "chat_message",
  "chat_id": "123",
  "chat": "rlk_2847904",
  "message": "Текст сообщения",
  "username": "user@example.com",
  "last_name": "Иванов",
  "first_name": "Иван",
  "psevdo_name": "Иванов И.И.",
  "eco": true,
  "admin": false
}
```

---

## ОБРАБОТКА ОШИБОК

Все API возвращают статус код HTTP:
- `200` - Успех
- `401` - Не авторизован
- `400` - Ошибка валидации
- `404` - Не найдено
- `500` - Внутренняя ошибка сервера

При ошибке в ответе может быть поле `error` с описанием проблемы.

