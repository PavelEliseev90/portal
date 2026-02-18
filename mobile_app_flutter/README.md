# KorsGroup Mobile App (Flutter)

Мобильное приложение для интерактивной оценки автомобилей на Flutter.

## 🚀 Быстрый старт

Для быстрого запуска приложения на устройстве см. [QUICK_START.md](QUICK_START.md)

Для подробной инструкции по установке и настройке см. [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)

## 📱 Запуск на устройстве

### Минимальные требования
- Flutter SDK 3.0.0+
- Android устройство с Android 5.0+ или iOS устройство с iOS 12.0+
- Подключение к интернету для первого запуска

### Быстрый запуск

```bash
# 1. Установите зависимости
flutter pub get

# 2. Подключите устройство
flutter devices

# 3. Запустите приложение
flutter run
```

### Подробные инструкции

- **[QUICK_START.md](QUICK_START.md)** - Краткая инструкция для быстрого старта (5 минут)
- **[INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)** - Полная инструкция по установке и настройке

## Структура проекта

```
mobile_app_flutter/
├── lib/
│   ├── main.dart
│   ├── core/
│   │   ├── constants/
│   │   │   └── app_constants.dart
│   │   ├── network/
│   │   │   ├── api_client.dart
│   │   │   ├── api_interceptor.dart
│   │   │   ├── network_exception.dart
│   │   │   └── websocket_service.dart
│   │   ├── database/
│   │   │   ├── database_helper.dart
│   │   │   └── dao/
│   │   │       ├── rlk_dao.dart
│   │   │       ├── inspection_dao.dart
│   │   │       └── catalog_dao.dart
│   │   ├── storage/
│   │   │   └── secure_storage.dart
│   │   └── utils/
│   │       ├── date_formatter.dart
│   │       └── image_utils.dart
│   ├── data/
│   │   ├── models/
│   │   │   ├── user_model.dart
│   │   │   ├── rlk_model.dart
│   │   │   ├── body_element_model.dart
│   │   │   ├── damage_mark_model.dart
│   │   │   └── catalog_model.dart
│   │   ├── repositories/
│   │   │   ├── auth_repository.dart
│   │   │   ├── rlk_repository.dart
│   │   │   ├── inspection_repository.dart
│   │   │   └── catalog_repository.dart
│   │   └── datasources/
│   │       ├── remote_datasource.dart
│   │       └── local_datasource.dart
│   ├── presentation/
│   │   ├── auth/
│   │   │   ├── screens/
│   │   │   │   └── login_screen.dart
│   │   │   └── providers/
│   │   │       └── auth_provider.dart
│   │   ├── estimation/
│   │   │   ├── screens/
│   │   │   │   ├── rlk_list_screen.dart
│   │   │   │   ├── estimation_start_screen.dart
│   │   │   │   ├── documents_screen.dart
│   │   │   │   ├── salon_screen.dart
│   │   │   │   ├── salon_inspection_screen.dart
│   │   │   │   ├── body_inspection_screen.dart
│   │   │   │   ├── complectnost_screen.dart
│   │   │   │   ├── kolesa_screen.dart
│   │   │   │   ├── test_drive_screen.dart
│   │   │   │   ├── proverki_screen.dart
│   │   │   │   ├── soglasovanie_screen.dart
│   │   │   │   └── chat_screen.dart
│   │   │   ├── widgets/
│   │   │   │   ├── rlk_card.dart
│   │   │   │   ├── search_bar.dart
│   │   │   │   ├── filter_dialog.dart
│   │   │   │   ├── estimation_step_indicator.dart
│   │   │   │   ├── body_inspection_widget.dart
│   │   │   │   ├── salon_inspection_widget.dart
│   │   │   │   ├── damage_type_selector.dart
│   │   │   │   ├── canvas_painter.dart
│   │   │   │   └── chat_bubble.dart
│   │   │   └── providers/
│   │   │       ├── rlk_provider.dart
│   │   │       └── estimation_provider.dart
│   │   └── theme/
│   │       ├── app_colors.dart
│   │       ├── app_text_styles.dart
│   │       └── app_theme.dart
│   └── services/
│       ├── sync_service.dart
│       └── offline_service.dart
├── test/
├── android/
├── ios/
└── pubspec.yaml
```

## Установка

1. **Установите Flutter SDK:**
   - 📖 **Подробная инструкция:** [FLUTTER_SDK_INSTALLATION.md](FLUTTER_SDK_INSTALLATION.md)
   - 🌐 **Официальный сайт:** https://docs.flutter.dev/get-started/install
   
2. **Клонируйте репозиторий** (если еще не склонирован)

3. **Установите зависимости:**
```bash
cd mobile_app_flutter
flutter pub get
```

## Запуск

### На эмуляторе/симуляторе
```bash
flutter run
```

### На физическом устройстве

**Android:**
1. Включите "Режим разработчика" на устройстве
2. Включите "Отладка по USB"
3. Подключите устройство и выполните:
```bash
flutter devices  # Проверьте подключение
flutter run       # Запустите приложение
```

**iOS (только Mac):**
1. Подключите iPhone/iPad
2. В Xcode: Window → Devices → Trust device
3. Выполните:
```bash
flutter devices  # Проверьте подключение
flutter run      # Запустите приложение
```

**Подробные инструкции:** см. [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)

## Основные функции

- Авторизация
- Список рабочих листов (RLK) с поиском и фильтрацией
- Интерактивный осмотр кузова (5 типов: перед, зад, бок, крыша)
- Интерактивный осмотр салона
- Все 8 этапов оценки
- Офлайн режим с синхронизацией
- Чат через веб-сокет

