# Инструкция по запуску мобильного приложения KorsGroup на устройстве

## Содержание
1. [Требования](#требования)
2. [Установка Flutter](#установка-flutter)
3. [Настройка Android](#настройка-android)
4. [Настройка iOS](#настройка-ios)
5. [Подготовка проекта](#подготовка-проекта)
6. [Запуск на Android устройстве](#запуск-на-android-устройстве)
7. [Запуск на iOS устройстве](#запуск-на-ios-устройстве)
8. [Настройка API endpoints](#настройка-api-endpoints)
9. [Решение проблем](#решение-проблем)

---

## Требования

### Общие требования
- **Flutter SDK**: версия 3.0.0 или выше
- **Dart SDK**: версия 3.0.0 или выше
- **Git**: для клонирования репозитория
- **Интернет**: для загрузки зависимостей

### Для Android
- **Android Studio**: последняя версия
- **Android SDK**: API Level 21 (Android 5.0) или выше
- **Java Development Kit (JDK)**: версия 11 или выше
- **Android устройство** с включенной отладкой по USB или эмулятор

### Для iOS (только macOS)
- **Xcode**: версия 14.0 или выше
- **CocoaPods**: для управления зависимостями iOS
- **iOS устройство** или симулятор (требуется Apple Developer аккаунт для физического устройства)

---

## Установка Flutter

**📖 Подробная инструкция:** См. [FLUTTER_SDK_INSTALLATION.md](FLUTTER_SDK_INSTALLATION.md)

### Краткая инструкция

#### Windows

1. **Скачайте Flutter SDK:**
   - Перейдите на https://docs.flutter.dev/get-started/install/windows
   - Скачайте последнюю стабильную версию

2. **Распакуйте архив:**
   - Распакуйте в `C:\src\flutter` (или другое удобное место)
   - **ВАЖНО:** Не распаковывайте в папку с пробелами в пути или в `C:\Program Files\`

3. **Добавьте Flutter в PATH:**
   - Откройте "Переменные среды" (Environment Variables)
   - Добавьте `C:\src\flutter\bin` в переменную `Path`
   - Перезапустите терминал

4. **Проверьте установку:**
   ```bash
   flutter doctor
   ```

#### macOS

1. **Скачайте Flutter SDK:**
   ```bash
   cd ~/development
   curl -O https://storage.googleapis.com/flutter_infra_release/releases/stable/macos/flutter_macos_arm64_stable.zip
   unzip flutter_macos_arm64_stable.zip
   ```

2. **Добавьте Flutter в PATH:**
   ```bash
   echo 'export PATH="$PATH:$HOME/development/flutter/bin"' >> ~/.zshrc
   source ~/.zshrc
   ```

3. **Проверьте установку:**
   ```bash
   flutter doctor
   ```

#### Linux

1. **Скачайте Flutter SDK:**
   ```bash
   cd ~/development
   curl -O https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_stable.tar.xz
   tar xf flutter_linux_stable.tar.xz
   ```

2. **Добавьте Flutter в PATH:**
   ```bash
   echo 'export PATH="$PATH:$HOME/development/flutter/bin"' >> ~/.bashrc
   source ~/.bashrc
   ```

3. **Проверьте установку:**
   ```bash
   flutter doctor
   ```

---

## Настройка Android

### 1. Установка Android Studio

1. Скачайте и установите [Android Studio](https://developer.android.com/studio)
2. Запустите Android Studio и выполните настройку мастера установки
3. Установите Android SDK через SDK Manager:
   - Tools → SDK Manager
   - SDK Platforms: выберите Android 5.0 (API 21) и выше
   - SDK Tools: установите Android SDK Build-Tools, Android SDK Platform-Tools, Android Emulator

### 2. Настройка переменных окружения

**Windows:**
```bash
# Добавьте в переменные среды:
ANDROID_HOME = C:\Users\<username>\AppData\Local\Android\Sdk
Path += %ANDROID_HOME%\platform-tools
Path += %ANDROID_HOME%\tools
```

**macOS/Linux:**
```bash
# Добавьте в ~/.zshrc или ~/.bash_profile:
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$PATH:$ANDROID_HOME/platform-tools
export PATH=$PATH:$ANDROID_HOME/tools
```

### 3. Настройка Android устройства

1. **Включите режим разработчика:**
   - Перейдите в Настройки → О телефоне
   - Нажмите 7 раз на "Номер сборки"

2. **Включите отладку по USB:**
   - Настройки → Для разработчиков → Отладка по USB

3. **Подключите устройство:**
   - Подключите устройство к компьютеру через USB
   - На устройстве подтвердите разрешение на отладку

4. **Проверьте подключение:**
   ```bash
   flutter devices
   # Должно показать ваше устройство
   ```

### 4. Создание эмулятора (опционально)

1. Откройте Android Studio
2. Tools → Device Manager → Create Device
3. Выберите устройство и образ системы
4. Запустите эмулятор

---

## Настройка iOS (только macOS)

### 1. Установка Xcode

1. Установите Xcode из App Store
2. Откройте Xcode и примите лицензионное соглашение
3. Установите дополнительные компоненты:
   ```bash
   sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer
   sudo xcodebuild -runFirstLaunch
   ```

### 2. Установка CocoaPods

```bash
sudo gem install cocoapods
```

### 3. Настройка iOS устройства

1. **Подключите устройство к Mac**
2. **В Xcode:**
   - Window → Devices and Simulators
   - Выберите ваше устройство
   - Нажмите "Use for Development"

3. **На устройстве:**
   - Настройки → Основные → Управление устройством
   - Доверьтесь сертификату разработчика

### 4. Создание симулятора (опционально)

1. Откройте Xcode
2. Window → Devices and Simulators
3. Нажмите "+" для создания нового симулятора
4. Выберите устройство и версию iOS

---

## Подготовка проекта

### 1. Перейдите в директорию проекта

```bash
cd mobile_app_flutter
```

### 2. Установите зависимости

```bash
flutter pub get
```

### 3. Проверьте конфигурацию

```bash
flutter doctor -v
```

Убедитесь, что все необходимые компоненты установлены и настроены.

### 4. Настройте API endpoints

Откройте файл `lib/core/constants/app_constants.dart` и при необходимости измените URL:

```dart
static const String baseUrl = 'https://ah.kors-group.com';
static const String apiBaseUrl = '$baseUrl/api/a/v2';
static const String wsBaseUrl = 'wss://ah.kors-group.com/ws';
```

---

## Запуск на Android устройстве

### Способ 1: Через командную строку

1. **Подключите устройство:**
   ```bash
   # Проверьте подключение
   flutter devices
   ```

2. **Запустите приложение:**
   ```bash
   flutter run
   ```

3. **Выберите устройство:**
   - Если подключено несколько устройств, выберите нужное из списка

### Способ 2: Через Android Studio

1. Откройте проект в Android Studio
2. Выберите устройство в верхней панели
3. Нажмите кнопку "Run" (▶️) или `Shift + F10`

### Способ 3: Сборка APK

1. **Debug APK:**
   ```bash
   flutter build apk --debug
   # APK будет в build/app/outputs/flutter-apk/app-debug.apk
   ```

2. **Release APK:**
   ```bash
   flutter build apk --release
   # APK будет в build/app/outputs/flutter-apk/app-release.apk
   ```

3. **Установите APK на устройство:**
   ```bash
   # Через ADB
   adb install build/app/outputs/flutter-apk/app-release.apk
   
   # Или скопируйте APK на устройство и установите вручную
   ```

### Способ 4: App Bundle (для Google Play)

```bash
flutter build appbundle --release
# AAB будет в build/app/outputs/bundle/release/app-release.aab
```

---

## Запуск на iOS устройстве

### Способ 1: Через командную строку

1. **Подключите устройство:**
   ```bash
   # Проверьте подключение
   flutter devices
   ```

2. **Запустите приложение:**
   ```bash
   flutter run
   ```

3. **Выберите устройство:**
   - Если подключено несколько устройств, выберите нужное из списка

### Способ 2: Через Xcode

1. Откройте `ios/Runner.xcworkspace` в Xcode
2. Выберите устройство в верхней панели
3. Нажмите кнопку "Run" (▶️) или `Cmd + R`

### Способ 3: Сборка IPA

1. **Откройте проект в Xcode:**
   ```bash
   open ios/Runner.xcworkspace
   ```

2. **Настройте подписи:**
   - Выберите Runner в навигаторе
   - Перейдите в Signing & Capabilities
   - Выберите вашу команду разработчика
   - Убедитесь, что Bundle Identifier уникален

3. **Соберите архив:**
   - Product → Archive
   - Дождитесь завершения сборки

4. **Экспортируйте IPA:**
   - В окне Organizer выберите архив
   - Нажмите "Distribute App"
   - Следуйте инструкциям мастера

### Способ 4: Через симулятор

```bash
# Запустите симулятор
open -a Simulator

# Запустите приложение
flutter run
```

---

## Настройка API endpoints

### Для разработки

Если вы используете локальный сервер разработки, измените URL в `lib/core/constants/app_constants.dart`:

```dart
// Для локального сервера
static const String baseUrl = 'http://192.168.1.100:8000';  // Замените на IP вашего компьютера
static const String apiBaseUrl = '$baseUrl/api/a/v2';
static const String wsBaseUrl = 'ws://192.168.1.100:8000/ws';
```

**Важно:** 
- Убедитесь, что устройство и компьютер в одной сети
- Для Android: используйте IP адрес компьютера, не `localhost` или `127.0.0.1`
- Для iOS: также используйте IP адрес, не `localhost`

### Для продакшена

Используйте стандартные URL:
```dart
static const String baseUrl = 'https://ah.kors-group.com';
static const String apiBaseUrl = '$baseUrl/api/a/v2';
static const String wsBaseUrl = 'wss://ah.kors-group.com/ws';
```

---

## Решение проблем

### Проблема: "No devices found"

**Решение:**
1. Проверьте подключение устройства:
   ```bash
   # Android
   adb devices
   
   # iOS
   flutter devices
   ```

2. Убедитесь, что отладка по USB включена на устройстве

3. Перезапустите ADB (Android):
   ```bash
   adb kill-server
   adb start-server
   ```

### Проблема: "Gradle build failed" (Android)

**Решение:**
1. Очистите кэш:
   ```bash
   cd android
   ./gradlew clean
   cd ..
   flutter clean
   flutter pub get
   ```

2. Проверьте версию Java:
   ```bash
   java -version
   # Должна быть версия 11 или выше
   ```

3. Обновите Gradle в `android/gradle/wrapper/gradle-wrapper.properties`

### Проблема: "CocoaPods not installed" (iOS)

**Решение:**
```bash
cd ios
pod install
cd ..
flutter clean
flutter pub get
```

### Проблема: "Signing for Runner requires a development team" (iOS)

**Решение:**
1. Откройте `ios/Runner.xcworkspace` в Xcode
2. Выберите Runner в навигаторе
3. Перейдите в Signing & Capabilities
4. Выберите вашу команду разработчика
5. Если команды нет, создайте Apple Developer аккаунт

### Проблема: "Network error" при подключении к API

**Решение:**
1. Проверьте интернет-соединение на устройстве
2. Убедитесь, что URL правильный в `app_constants.dart`
3. Для локального сервера проверьте, что устройство и компьютер в одной сети
4. Проверьте файрвол и настройки безопасности

### Проблема: "WebSocket connection failed"

**Решение:**
1. Проверьте URL WebSocket в `app_constants.dart`
2. Убедитесь, что сервер поддерживает WebSocket
3. Проверьте настройки безопасности (HTTPS/WSS для продакшена)

### Проблема: Приложение не запускается после установки

**Решение:**
1. Проверьте логи:
   ```bash
   flutter logs
   ```

2. Очистите и пересоберите:
   ```bash
   flutter clean
   flutter pub get
   flutter run
   ```

3. Проверьте минимальную версию Android/iOS в:
   - `android/app/build.gradle` (minSdkVersion)
   - `ios/Podfile` (platform :ios)

---

## Полезные команды

### Проверка окружения
```bash
flutter doctor -v          # Подробная информация о настройке
flutter devices           # Список доступных устройств
flutter --version         # Версия Flutter
```

### Очистка проекта
```bash
flutter clean              # Очистка build файлов
flutter pub get            # Переустановка зависимостей
```

### Сборка приложения
```bash
flutter build apk          # Android APK (release)
flutter build appbundle   # Android App Bundle
flutter build ios         # iOS (требует Mac и Xcode)
```

### Запуск с параметрами
```bash
flutter run --release     # Release режим
flutter run --debug       # Debug режим (по умолчанию)
flutter run --profile     # Profile режим (для анализа производительности)
```

### Просмотр логов
```bash
flutter logs              # Логи в реальном времени
flutter logs --clear      # Очистить и показать логи
```

---

## Дополнительная информация

### Горячая перезагрузка

Во время разработки используйте горячую перезагрузку:
- **r** - горячая перезагрузка (Hot Reload)
- **R** - полная перезагрузка (Hot Restart)
- **q** - выход из приложения

### Отладка

1. **Chrome DevTools** (для веб-версии):
   ```bash
   flutter run -d chrome
   ```

2. **VS Code**: установите расширение Flutter для отладки

3. **Android Studio**: встроенный отладчик

### Профилирование производительности

```bash
flutter run --profile
# Затем используйте Flutter DevTools для анализа
```

---

## Контакты и поддержка

При возникновении проблем:
1. Проверьте [официальную документацию Flutter](https://flutter.dev/docs)
2. Проверьте [Flutter GitHub Issues](https://github.com/flutter/flutter/issues)
3. Обратитесь к команде разработки

---

**Удачной разработки! 🚀**

