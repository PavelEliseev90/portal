# Установка Flutter и тестирование мобильного приложения

## 1. Установка Flutter SDK (Windows)

### Шаг 1: Скачайте Flutter
- Откройте: https://docs.flutter.dev/get-started/install/windows
- Нажмите **Download Flutter SDK**
- Скачайте `flutter_windows_X.X.X-stable.zip`

### Шаг 2: Распакуйте
- Создайте папку `C:\src` (если её нет)
- Распакуйте архив в `C:\src\flutter`
- **Не** используйте путь с пробелами (`C:\Program Files`, `C:\Users\Имя User` и т.п.)

### Шаг 3: Добавьте в PATH
1. Win + R → `sysdm.cpl` → Enter
2. Вкладка **Дополнительно** → **Переменные среды**
3. В **Системные переменные** найдите `Path` → **Изменить**
4. **Создать** → `C:\src\flutter\bin` → OK

### Шаг 4: Проверка
Закройте и откройте PowerShell заново, затем:

```powershell
flutter --version
flutter doctor -v
```

### Шаг 5: Лицензии Android (если есть Android SDK)
```powershell
flutter doctor --android-licenses
```
На все запросы отвечайте `y` (yes).

---

## 2. Android Studio (для эмулятора)

1. Скачайте: https://developer.android.com/studio  
2. Установите с настройками по умолчанию  
3. При первом запуске: **More Actions** → **SDK Manager** → установите **Android SDK**  
4. **Device Manager** → **Create Device** → создайте виртуальное устройство  

---

## 3. Запуск приложения

```powershell
cd D:\portal\mobile_app_flutter

flutter pub get
flutter devices
flutter run
```

Если подключено несколько устройств:
```powershell
flutter run -d <device_id>
```

---

## 4. Локальное тестирование с сервером

Если бэкенд запущен локально (например, `http://192.168.1.100:8000`):

1. Откройте `lib/core/constants/app_constants.dart`
2. Измените `baseUrl` на IP вашего компьютера:
   ```dart
   static const String baseUrl = 'http://192.168.1.100:8000';
   static const String apiBaseUrl = '$baseUrl/api/a/v2';
   static const String wsBaseUrl = 'ws://192.168.1.100:8000/ws';
   ```
3. Телефон и компьютер должны быть в одной сети

По умолчанию приложение использует `https://ah.kors-group.com`.

---

## 5. Сборка APK

```powershell
cd D:\portal\mobile_app_flutter
flutter build apk --debug
# Результат: build\app\outputs\flutter-apk\app-debug.apk

flutter build apk --release
# Результат: build\app\outputs\flutter-apk\app-release.apk
```

Установка на устройство:
```powershell
adb install build\app\outputs\flutter-apk\app-debug.apk
```

---

## 6. Частые проблемы

| Ошибка | Решение |
|--------|---------|
| `flutter: command not found` | Добавьте `C:\src\flutter\bin` в PATH и перезапустите терминал |
| `No devices found` | Подключите телефон по USB с включённой отладкой или запустите эмулятор |
| `Gradle build failed` | `flutter clean` → `flutter pub get` → `flutter run` |
| `Android licenses not accepted` | `flutter doctor --android-licenses` |
