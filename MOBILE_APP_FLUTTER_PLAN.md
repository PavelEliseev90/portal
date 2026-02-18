# План разработки мобильного приложения KorsGroup Portal
## Flutter + Dart для Android и iOS

### Общая информация
- **Платформа**: Flutter 3.x
- **Язык**: Dart
- **Целевые платформы**: Android, iOS
- **Архитектура**: Clean Architecture / MVVM
- **API**: Django REST API (`/api/a/v1/`)

---

## 1. СТРУКТУРА ПРОЕКТА

```
kors_mobile_app/
├── lib/
│   ├── main.dart
│   ├── app/
│   │   ├── app.dart                    # Главный виджет приложения
│   │   └── routes.dart                 # Маршрутизация
│   ├── core/
│   │   ├── constants/
│   │   │   ├── api_endpoints.dart      # API endpoints
│   │   │   ├── app_colors.dart         # Цветовая схема портала
│   │   │   └── app_styles.dart         # Стили портала
│   │   ├── network/
│   │   │   ├── api_client.dart         # HTTP клиент
│   │   │   ├── api_interceptor.dart    # Interceptors для auth
│   │   │   ├── network_exception.dart  # Обработка ошибок
│   │   │   └── websocket_service.dart  # Веб-сокет для чата
│   │   ├── storage/
│   │   │   ├── secure_storage.dart     # Secure storage для токенов
│   │   │   └── local_storage.dart      # SharedPreferences
│   │   ├── database/
│   │   │   ├── database_helper.dart    # SQLite helper
│   │   │   ├── models/
│   │   │   │   ├── offline_estimation_model.dart
│   │   │   │   └── sync_queue_model.dart
│   │   │   └── dao/
│   │   │       ├── catalog_dao.dart    # DAO для справочников
│   │   │       ├── estimation_dao.dart # DAO для оценок
│   │   │       └── sync_queue_dao.dart # DAO для очереди
│   │   ├── sync/
│   │   │   ├── sync_manager.dart       # Менеджер синхронизации
│   │   │   ├── catalog_sync_service.dart # Синхронизация справочников
│   │   │   └── estimation_sync_service.dart # Синхронизация оценок
│   │   ├── connectivity/
│   │   │   └── connectivity_service.dart # Проверка интернета
│   │   └── utils/
│   │       ├── validators.dart
│   │       └── formatters.dart
│   ├── data/
│   │   ├── models/
│   │   │   ├── user_model.dart
│   │   │   ├── rlk_model.dart          # Рабочий лист
│   │   │   ├── estimation_model.dart   # Оценка
│   │   │   └── ...
│   │   ├── repositories/
│   │   │   ├── auth_repository.dart
│   │   │   ├── estimation_repository.dart
│   │   │   └── rlk_repository.dart
│   │   └── datasources/
│   │       ├── remote/
│   │       │   ├── auth_remote_datasource.dart
│   │       │   └── estimation_remote_datasource.dart
│   │       └── local/
│   │           └── auth_local_datasource.dart
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── user_entity.dart
│   │   │   ├── rlk_entity.dart
│   │   │   └── estimation_entity.dart
│   │   └── usecases/
│   │       ├── auth/
│   │       │   ├── login_usecase.dart
│   │       │   └── logout_usecase.dart
│   │       └── estimation/
│   │           ├── get_rlk_list_usecase.dart
│   │           └── start_estimation_usecase.dart
│   └── presentation/
│       ├── auth/
│       │   ├── screens/
│       │   │   └── login_screen.dart
│       │   ├── widgets/
│       │   │   └── login_form.dart
│       │   └── providers/
│       │       └── auth_provider.dart
│       ├── settings/
│       │   ├── screens/
│       │   │   ├── settings_screen.dart
│       │   │   └── sync_screen.dart      # Экран синхронизации справочников
│       │   └── widgets/
│       │       └── sync_progress_widget.dart
│       ├── estimation/
│       │   ├── screens/
│       │   │   ├── rlk_list_screen.dart        # Список рабочих листов
│       │   │   ├── estimation_start_screen.dart # Начало оценки
│       │   │   ├── documents_screen.dart       # Этап 1: Документы
│       │   │   ├── salon_screen.dart           # Этап 2: Салон
│       │   │   ├── salon_inspection_screen.dart # Осмотр салона (интерактивный)
│       │   │   ├── vnesh_screen.dart           # Этап 3: Внешний осмотр
│       │   │   ├── body_inspection_screen.dart # Осмотр кузова (интерактивный)
│       │   │   ├── complectnost_screen.dart     # Этап 4: Комплектность
│       │   │   ├── kolesa_screen.dart          # Этап 5: Колеса
│       │   │   ├── test_drive_screen.dart       # Этап 6: Тест-драйв
│       │   │   ├── proverki_screen.dart        # Этап 7: Проверки
│       │   │   ├── soglasovanie_screen.dart    # Этап 8: Согласование
│       │   │   └── chat_screen.dart            # Чат через веб-сокет
│       │   ├── widgets/
│       │   │   ├── rlk_card.dart
│       │   │   ├── search_bar.dart
│       │   │   ├── filter_dialog.dart
│       │   │   ├── estimation_step_indicator.dart
│       │   │   ├── body_inspection_widget.dart  # Виджет осмотра кузова
│       │   │   ├── salon_inspection_widget.dart # Виджет осмотра салона
│       │   │   ├── damage_type_selector.dart     # Выбор типа повреждения
│       │   │   ├── canvas_painter.dart           # CustomPainter для canvas
│       │   │   └── chat_bubble.dart              # Виджет сообщения чата
│       │   └── providers/
│       │       ├── rlk_list_provider.dart
│       │       └── estimation_provider.dart
│       └── shared/
│           ├── widgets/
│           │   ├── portal_button.dart
│           │   ├── portal_text_field.dart
│           │   ├── portal_card.dart
│           │   └── loading_indicator.dart
│           └── theme/
│               ├── app_theme.dart
│               └── portal_colors.dart
├── test/
├── android/
├── ios/
└── pubspec.yaml
```

---

## 2. ЦВЕТОВАЯ СХЕМА ПОРТАЛА

```dart
// lib/core/constants/app_colors.dart
class PortalColors {
  static const Color primary = Color(0xFF002a5a);      // Основной синий
  static const Color primaryLight = Color(0xFF00509d); // Светлый синий
  static const Color secondary = Color(0xFF6c7a92);    // Серый текст
  static const Color accent = Color(0xFF8ea1ba);       // Акцентный серый
  static const Color background = Color(0xFFf4f7fb);   // Фон
  static const Color success = Color(0xFF22c55e);      // Успех
  static const Color danger = Color(0xFFef4444);      // Опасность
  static const Color warning = Color(0xFFf59e0b);      // Предупреждение
  static const Color white = Color(0xFFFFFFFF);
}
```

---

## 3. API ENDPOINTS

### 3.1 Авторизация
- `POST /api/a/v1/login_in/` - Вход в систему
- `GET /api/a/v1/login_info/` - Информация о пользователе

### 3.2 Рабочие листы (RLK)
- `GET /api/a/v1/rlk_eco/` - Список рабочих листов для оценки
- `GET /api/a/v1/staff_rlks_unit/` - RLK по подразделениям
- `GET /api/a/v1/staff_rlk/<rlk_id>/` - Детали RLK

### 3.3 Оценка
- `GET /api/a/v1/start_estimation/<rlk_id>/` - Начало оценки
- `GET /api/a/v1/estimation_documents_start/<rlk_id>/` - Начало этапа "Документы"
- `POST /api/a/v1/estimation_documents_post/<rlk_id>/` - Сохранение "Документы"
- `POST /api/a/v1/estimation_salon_post/<rlk_id>/` - Сохранение "Салон"
- `POST /api/a/v1/estimation_vnesh_post/<rlk_id>/` - Сохранение "Внешний осмотр"
- `POST /api/a/v1/estimation_complectnost_post/<rlk_id>/` - Сохранение "Комплектность"
- `POST /api/a/v1/estimation_kolesa_post/<rlk_id>/` - Сохранение "Колеса"
- `POST /api/a/v1/estimation_test_drive_post/<rlk_id>/` - Сохранение "Тест-драйв"
- `POST /api/a/v1/estimation_proverki_post/<rlk_id>/` - Сохранение "Проверки"
- `GET /api/a/v1/estimation_soglasovanie_get/<rlk_id>/` - Получение "Согласование"
- `POST /api/a/v1/estimation_soglasovanie_post/<rlk_id>/` - Сохранение "Согласование"
- `POST /api/a/v1/estimation_add_fotos/<rlk_id>/` - Загрузка фотографий

### 3.4 Справочники
- `GET /api/catalogs/manufacturer/` - Производители

---

## 4. ЭТАПЫ ОЦЕНКИ (аналогично lo_v3.html)

### Этап 1: Документы (page_documents)
- Данные клиента (ФИО, телефон)
- Количество ключей, владельцев
- Номера (ПТС, СТС, ГРЗ, двигателя)
- Даты (ПТС, СТС)
- Цвет
- Фотографии ПТС и СТС
- Организация, филиал, подразделение, склад
- Тип приема

### Этап 2: Салон (page_salon)
- Пробег (подтвержденный/неподтвержденный)
- Состояние салона (чистка, повреждения)
- Функции (ручник, дворники, сигнал, стеклоподъемники, ремни)
- Ошибки приборной панели
- Фотографии пробега

### Этап 3: Внешний осмотр (page_vnesh)
- Повреждения (лобовое стекло, световые приборы, подтеки)
- Цвет
- Проверка VIN, двигателя и КПП
- Комментарий
- Фотографии внешнего вида

### Этап 4: Комплектность (page_complectnost)
- Прикуриватель, огнетушитель, коврики
- Трос, домкрат, знак аварийной остановки
- Баллонный ключ, запаска, аптечка

### Этап 5: Колеса (page_kolesa)
- Шины (марка, модель, ширина, профиль, радиус, сезон)
- Диски (модель, тип, радиус, ET, PCD, DIA)

### Этап 6: Тест-драйв (page_test_drive)
- Двигатель, КПП, тормозная система
- Подвеска, система выпуска ОГ
- Колеса, кондиционер, турбина
- Полный привод, ТО
- Подрамник
- Амортизатор капота/багажника
- Стапель (тип, часы, стоимость)
- Комментарии по каждому пункту

### Этап 7: Проверки (page_proverki)
- Проверки по различным системам

### Этап 8: Согласование (page_soglasovanie)
- Цена приема, восстановления, продажи
- Информация о продаже
- Комментарий
- Участники оценки

---

## 5. ОСНОВНЫЕ ЭКРАНЫ

### 5.1 Авторизация
- Поля: логин, пароль
- Кнопка "Войти"
- Обработка ошибок авторизации
- Сохранение токена

### 5.2 Список рабочих листов
- Поиск по VIN, номеру, клиенту
- Фильтры:
  - По подразделению
  - По статусу (новые, в работе, на согласовании)
  - По дате
- Карточки RLK с информацией:
  - Номер RLK
  - Дата создания
  - Клиент
  - VIN (если есть)
  - Статус оценки
  - Подразделение
- Pull-to-refresh
- Пагинация

### 5.3 Начало оценки
- Выбор типа оценки (стандартная/дистанционная)
- Ввод VIN или номера кузова
- Автозаполнение из vin_trade_in
- Кнопка "Начать оценку"

### 5.4 Экраны этапов оценки
- Индикатор прогресса (шаги 1-8)
- Навигация между этапами
- Кнопки "Сохранить" и "Сохранить и продолжить"
- Валидация полей
- Загрузка фотографий
- Выбор из справочников

---

## 6. ЗАВИСИМОСТИ (pubspec.yaml)

```yaml
dependencies:
  flutter:
    sdk: flutter
  
  # State Management
  provider: ^6.1.1
  riverpod: ^2.4.9
  
  # Network
  dio: ^5.4.0
  retrofit: ^4.0.3
  json_annotation: ^4.8.1
  
  # Storage
  shared_preferences: ^2.2.2
  flutter_secure_storage: ^9.0.0
  
  # Local Database (Offline)
  sqflite: ^2.3.0
  path_provider: ^2.1.1
  path: ^1.8.3
  
  # Connectivity
  connectivity_plus: ^5.0.2
  
  # Background Tasks
  workmanager: ^0.5.2
  
  # UI
  cached_network_image: ^3.3.0
  image_picker: ^1.0.5
  flutter_svg: ^2.0.9
  shimmer: ^3.0.0
  
  # Utils
  intl: ^0.19.0
  uuid: ^4.2.1
  path_provider: ^2.1.1
  
  # Navigation
  go_router: ^12.1.3
  
  # Forms
  flutter_form_builder: ^9.1.1
  form_builder_validators: ^9.1.0
  
  # WebSocket
  web_socket_channel: ^2.4.0
  
  # Canvas/Image Processing
  image: ^4.1.3
  path_drawing: ^1.0.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^3.0.1
  build_runner: ^2.4.7
  retrofit_generator: ^8.0.6
  json_serializable: ^6.7.1
```

---

## 7. ПЛАН РАЗРАБОТКИ (ПО ЭТАПАМ)

### Этап 1: Базовая инфраструктура (1-2 недели)
- [ ] Настройка проекта Flutter
- [ ] Настройка архитектуры (Clean Architecture)
- [ ] Настройка сетевого слоя (Dio, interceptors)
- [ ] Настройка хранилища (Secure Storage, SharedPreferences)
- [ ] Базовая тема приложения (цвета, стили портала)
- [ ] Настройка роутинга

### Этап 2: Авторизация (1 неделя)
- [ ] Экран авторизации
- [ ] API интеграция (login_in, login_info)
- [ ] Сохранение токена
- [ ] Проверка авторизации при запуске
- [ ] Выход из системы

### Этап 3: Список рабочих листов (1-2 недели)
- [ ] API интеграция (rlk_eco, staff_rlks_unit)
- [ ] Экран списка RLK
- [ ] Поиск и фильтрация
- [ ] Карточки RLK
- [ ] Pull-to-refresh и пагинация

### Этап 4: Начало оценки (1 неделя)
- [ ] Экран начала оценки
- [ ] Выбор типа оценки
- [ ] Ввод VIN/номера кузова
- [ ] API интеграция (start_estimation)

### Этап 5: Этапы оценки (4-5 недель)
- [ ] Этап 1: Документы
- [ ] Этап 2: Салон
  - [ ] Осмотр салона (интерактивный canvas)
  - [ ] Определение элементов по клику
  - [ ] Выбор типа повреждения (перекрас, перешив, дырка, восстановление)
  - [ ] Сохранение координат и фотографий
- [ ] Этап 3: Внешний осмотр
  - [ ] Осмотр кузова (5 типов: перед, зад, бок, крыша)
  - [ ] Интерактивный canvas для каждого типа
  - [ ] Определение элементов кузова по полигонам
  - [ ] Выбор типа повреждения (16 типов)
  - [ ] Толщиномер с вводом значения
  - [ ] Сохранение координат и фотографий
- [ ] Этап 4: Комплектность
- [ ] Этап 5: Колеса
- [ ] Этап 6: Тест-драйв
- [ ] Этап 7: Проверки
- [ ] Этап 8: Согласование
  - [ ] Экран согласования
  - [ ] Чат через веб-сокет
  - [ ] Отправка/получение сообщений в реальном времени
  - [ ] Уведомления о новых сообщениях
- [ ] Индикатор прогресса
- [ ] Навигация между этапами
- [ ] Загрузка фотографий

### Этап 6: Офлайн режим (2-3 недели)
- [ ] Настройка локальной БД (SQLite)
- [ ] Реализация DAO для справочников
- [ ] Реализация DAO для оценок
- [ ] Реализация DAO для очереди синхронизации
- [ ] Сервис синхронизации справочников
- [ ] Экран синхронизации справочников
- [ ] Сохранение данных оценки локально
- [ ] Механизм очереди синхронизации
- [ ] Автоматическая синхронизация при восстановлении интернета
- [ ] Обработка конфликтов данных
- [ ] UI индикаторы офлайн режима
- [ ] Фоновая синхронизация (workmanager)

### Этап 7: Тестирование и доработка (1-2 недели)
- [ ] Unit тесты
- [ ] Widget тесты
- [ ] Интеграционные тесты
- [ ] Тестирование офлайн режима
- [ ] Тестирование синхронизации
- [ ] Исправление багов
- [ ] Оптимизация производительности

---

## 8. ОСОБЕННОСТИ РЕАЛИЗАЦИИ

### 8.1 State Management
Рекомендуется использовать **Riverpod** или **Provider** для управления состоянием.

### 8.2 Офлайн режим (КРИТИЧЕСКИ ВАЖНО)

#### 8.2.1 Локальная база данных
Использовать **SQLite** (через `sqflite`) или **Hive** для хранения:
- Справочников (марки, модели, модификации, комплектации)
- Данных оценки (все этапы)
- Фотографий (пути к локальным файлам)
- Очереди синхронизации

#### 8.2.2 Синхронизация справочников
**Экран синхронизации справочников:**
- Кнопка "Обновить справочники" в настройках
- Прогресс загрузки
- Индикатор последнего обновления
- Размер загруженных данных

**API для справочников:**
- `GET /api/a/v1/catalogs/manufacturer/` - Производители
- `GET /api/a/v1/catalogs/models/<manufacturer_id>/` - Модели
- `GET /api/a/v1/catalogs/modifications/<model_id>/` - Модификации
- `GET /api/a/v1/catalogs/complectations/<modification_id>/` - Комплектации

**Структура локальной БД:**
```sql
-- Справочники
CREATE TABLE manufacturers (
  id INTEGER PRIMARY KEY,
  name TEXT,
  updated_at INTEGER
);

CREATE TABLE models (
  id INTEGER PRIMARY KEY,
  manufacturer_id INTEGER,
  name TEXT,
  updated_at INTEGER
);

CREATE TABLE modifications (
  id INTEGER PRIMARY KEY,
  model_id INTEGER,
  name TEXT,
  year INTEGER,
  updated_at INTEGER
);

CREATE TABLE complectations (
  id INTEGER PRIMARY KEY,
  modification_id INTEGER,
  name TEXT,
  updated_at INTEGER
);

-- Оценки (офлайн)
CREATE TABLE offline_estimations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  rlk_id INTEGER,
  estimation_id INTEGER,
  step INTEGER, -- 1-8 этап
  data TEXT, -- JSON данные этапа
  photos TEXT, -- JSON массив путей к фото
  status TEXT, -- 'draft', 'pending_sync', 'synced'
  created_at INTEGER,
  updated_at INTEGER,
  synced_at INTEGER
);

-- Очередь синхронизации
CREATE TABLE sync_queue (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  estimation_id INTEGER,
  endpoint TEXT, -- API endpoint
  method TEXT, -- 'POST', 'PUT'
  data TEXT, -- JSON данные
  retry_count INTEGER DEFAULT 0,
  status TEXT, -- 'pending', 'processing', 'failed', 'completed'
  created_at INTEGER,
  last_attempt_at INTEGER
);
```

#### 8.2.3 Работа в офлайн режиме
**Определение статуса подключения:**
- Использовать `connectivity_plus` для проверки интернета
- Показывать индикатор офлайн режима в UI
- Блокировать синхронизацию при отсутствии интернета

**Логика работы:**
1. При начале оценки проверять интернет
2. Если нет интернета - работать в офлайн режиме
3. Сохранять все данные локально
4. При появлении интернета - автоматически синхронизировать

**Сохранение данных:**
- Каждый этап сохраняется в локальную БД сразу
- Фотографии сохраняются в локальное хранилище
- Создается запись в очереди синхронизации

#### 8.2.4 Автоматическая синхронизация
**Фоновая синхронизация:**
- Использовать `workmanager` для фоновых задач
- При восстановлении интернета автоматически запускать синхронизацию
- Обрабатывать очередь синхронизации по порядку

**Механизм синхронизации:**
1. Проверка интернета
2. Получение записей из очереди со статусом 'pending'
3. Отправка данных на сервер
4. Обновление статуса записи
5. При ошибке - увеличение retry_count, повтор через время

**Обработка конфликтов:**
- Если данные на сервере новее - показать диалог выбора
- Возможность просмотра различий
- Выбор: использовать локальные или серверные данные

#### 8.2.5 UI для офлайн режима
- Индикатор офлайн режима в AppBar
- Баннер "Работа в офлайн режиме"
- Счетчик несинхронизированных оценок
- Кнопка "Синхронизировать" в настройках
- Прогресс синхронизации

### 8.3 Загрузка фотографий
- Использование `image_picker` для выбора фото
- Сжатие изображений перед загрузкой
- Прогресс загрузки
- Возможность удаления загруженных фото

### 8.4 Валидация форм
- Валидация VIN (17 символов)
- Валидация номеров документов
- Проверка обязательных полей
- Показ ошибок валидации

### 8.5 UI/UX
- Стиль портала (цвета, скругления, тени)
- Адаптивная верстка для разных размеров экранов
- Анимации переходов
- Индикаторы загрузки
- Обработка ошибок с понятными сообщениями

### 8.6 Интерактивный осмотр кузова/салона
- Canvas для отрисовки изображения автомобиля
- Определение элементов по полигонам (point-in-polygon алгоритм)
- Модальное окно выбора типа повреждения
- Отрисовка отметок на canvas
- Сохранение canvas в base64
- Загрузка фотографий для каждой отметки
- Работа в офлайн режиме с последующей синхронизацией

### 8.7 Веб-сокет для чата
- Подключение к `wss://ah.kors-group.com/ws/rlk_{rlk_id}/`
- Отправка и получение сообщений в реальном времени
- Автоматическое переподключение при разрыве связи
- Сохранение истории сообщений локально
- Уведомления о новых сообщениях
- Индикатор статуса подключения

---

## 9. БУДУЩИЕ РАСШИРЕНИЯ

После реализации интерактивной оценки можно добавить:
- Другие разделы портала
- Уведомления (push notifications)
- Чат с коллегами
- Аналитика и отчеты
- Настройки приложения

---

## 10. ДОКУМЕНТАЦИЯ API

Необходимо задокументировать все используемые API endpoints с примерами запросов и ответов.

---

## СЛЕДУЮЩИЕ ШАГИ

1. Создать структуру проекта Flutter
2. Настроить базовую инфраструктуру
3. Реализовать авторизацию
4. Реализовать список RLK
5. Поэтапно реализовать все этапы оценки

