# Быстрый старт - KorsGroup Mobile App

## Минимальные требования для запуска

- Flutter SDK 3.0.0+
- Android Studio (для Android) или Xcode (для iOS на Mac)
- Подключенное устройство или эмулятор

## Быстрая установка (5 минут)

### 1. Установите Flutter

**📖 Подробная инструкция:** См. [FLUTTER_SDK_INSTALLATION.md](FLUTTER_SDK_INSTALLATION.md)

**Кратко:**

**Windows:**
```bash
# Скачайте с https://docs.flutter.dev/get-started/install/windows
# Распакуйте в C:\src\flutter
# Добавьте C:\src\flutter\bin в PATH через "Переменные среды"
```

**macOS:**
```bash
cd ~/development
curl -O https://storage.googleapis.com/flutter_infra_release/releases/stable/macos/flutter_macos_arm64_stable.zip
unzip flutter_macos_arm64_stable.zip
echo 'export PATH="$PATH:$HOME/development/flutter/bin"' >> ~/.zshrc
source ~/.zshrc
```

**Linux:**
```bash
cd ~/development
curl -O https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_stable.tar.xz
tar xf flutter_linux_stable.tar.xz
echo 'export PATH="$PATH:$HOME/development/flutter/bin"' >> ~/.bashrc
source ~/.bashrc
```

**Проверка:**
```bash
flutter doctor
```

### 2. Настройте устройство

**Android:**
1. Включите "Режим разработчика" (7 нажатий на "Номер сборки")
2. Включите "Отладка по USB"
3. Подключите устройство

**iOS (только Mac):**
1. Подключите iPhone/iPad
2. В Xcode: Window → Devices → Trust device

### 3. Запустите приложение

```bash
cd mobile_app_flutter
flutter pub get
flutter run
```

## Если что-то не работает

### "No devices found"
```bash
# Android
adb devices

# iOS
flutter devices
```

### "Gradle build failed"
```bash
flutter clean
flutter pub get
flutter run
```

### "CocoaPods not installed" (iOS)
```bash
cd ios
pod install
cd ..
flutter run
```

## Настройка API (опционально)

Если используете локальный сервер, измените в `lib/core/constants/app_constants.dart`:

```dart
static const String baseUrl = 'http://192.168.1.100:8000';  // Ваш IP
```

**Важно:** Используйте IP адрес компьютера, не `localhost`!

## Полезные команды

```bash
flutter devices          # Список устройств
flutter run              # Запуск
flutter build apk        # Сборка APK
flutter logs             # Логи
r                        # Горячая перезагрузка (в консоли)
```

## Полная инструкция

См. [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) для подробной инструкции.

