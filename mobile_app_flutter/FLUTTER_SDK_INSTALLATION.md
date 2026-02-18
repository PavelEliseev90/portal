# Установка Flutter SDK

Подробная инструкция по установке Flutter SDK для Windows, macOS и Linux.

## Содержание
1. [Проверка системных требований](#проверка-системных-требований)
2. [Установка на Windows](#установка-на-windows)
3. [Установка на macOS](#установка-на-macos)
4. [Установка на Linux](#установка-на-linux)
5. [Проверка установки](#проверка-установки)
6. [Настройка PATH](#настройка-path)
7. [Решение проблем](#решение-проблем)

---

## Проверка системных требований

### Минимальные требования
- **ОС**: Windows 10 (64-bit) или выше / macOS 10.14 или выше / Linux (64-bit)
- **Дисковое пространство**: 2.8 GB (не включая IDE/инструменты)
- **Инструменты**: Git для Windows, bash, curl, file, mkdir, rm, unzip, which, xz-utils, zip

### Дополнительные требования

**Windows:**
- PowerShell 5.0 или новее
- Windows 10 SDK (для разработки Windows приложений)

**macOS:**
- Xcode (для iOS разработки)
- CocoaPods (для iOS зависимостей)

**Linux:**
- libgtk-3-dev (для разработки Linux приложений)

---

## Установка на Windows

### Способ 1: Установка через официальный архив (Рекомендуется)

1. **Скачайте Flutter SDK:**
   - Перейдите на https://docs.flutter.dev/get-started/install/windows
   - Нажмите "Download Flutter SDK"
   - Скачайте последнюю стабильную версию (например, `flutter_windows_3.x.x-stable.zip`)

2. **Распакуйте архив:**
   ```powershell
   # Создайте папку для Flutter (рекомендуется)
   New-Item -ItemType Directory -Path "C:\src" -Force
   
   # Распакуйте архив в C:\src\flutter
   # Используйте встроенный архиватор Windows или 7-Zip
   ```
   
   **ВАЖНО:** 
   - Не распаковывайте Flutter в папку с пробелами в пути (например, `C:\Program Files\`)
   - Не распаковывайте Flutter в папку, требующую повышенных прав (например, `C:\Windows\`)
   - Рекомендуемый путь: `C:\src\flutter`

3. **Добавьте Flutter в PATH:**
   
   **Через графический интерфейс:**
   - Откройте "Поиск" → введите "переменные среды" → "Изменение системных переменных среды"
   - Нажмите "Переменные среды"
   - В разделе "Системные переменные" найдите `Path` и нажмите "Изменить"
   - Нажмите "Создать" и добавьте: `C:\src\flutter\bin`
   - Нажмите "ОК" во всех окнах
   
   **Через PowerShell (от имени администратора):**
   ```powershell
   [Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\src\flutter\bin", "Machine")
   ```

4. **Перезапустите терминал:**
   - Закройте все открытые окна командной строки/PowerShell
   - Откройте новое окно PowerShell или Command Prompt

5. **Проверьте установку:**
   ```bash
   flutter --version
   flutter doctor
   ```

### Способ 2: Установка через Git (для разработчиков)

1. **Установите Git для Windows:**
   - Скачайте с https://git-scm.com/download/win
   - Установите с настройками по умолчанию

2. **Клонируйте репозиторий Flutter:**
   ```bash
   cd C:\src
   git clone https://github.com/flutter/flutter.git -b stable
   ```

3. **Добавьте в PATH** (см. способ 1, шаг 3)

4. **Проверьте установку:**
   ```bash
   flutter doctor
   ```

### Способ 3: Установка через Chocolatey

1. **Установите Chocolatey** (если еще не установлен):
   ```powershell
   # Запустите PowerShell от имени администратора
   Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
   ```

2. **Установите Flutter:**
   ```powershell
   choco install flutter
   ```

3. **Проверьте установку:**
   ```bash
   flutter doctor
   ```

---

## Установка на macOS

### Способ 1: Установка через официальный архив (Рекомендуется)

1. **Скачайте Flutter SDK:**
   ```bash
   cd ~/development
   # Для Intel Mac
   curl -O https://storage.googleapis.com/flutter_infra_release/releases/stable/macos/flutter_macos_arm64_stable.zip
   
   # Для Apple Silicon (M1/M2/M3)
   curl -O https://storage.googleapis.com/flutter_infra_release/releases/stable/macos/flutter_macos_arm64_stable.zip
   ```

2. **Распакуйте архив:**
   ```bash
   unzip flutter_macos_arm64_stable.zip
   # Или для Intel
   unzip flutter_macos_x64_stable.zip
   ```

3. **Добавьте Flutter в PATH:**
   
   **Для zsh (macOS Catalina и новее):**
   ```bash
   # Откройте ~/.zshrc
   nano ~/.zshrc
   
   # Добавьте строку:
   export PATH="$PATH:$HOME/development/flutter/bin"
   
   # Сохраните (Ctrl+O, Enter, Ctrl+X)
   # Примените изменения:
   source ~/.zshrc
   ```
   
   **Для bash (старые версии macOS):**
   ```bash
   # Откройте ~/.bash_profile
   nano ~/.bash_profile
   
   # Добавьте строку:
   export PATH="$PATH:$HOME/development/flutter/bin"
   
   # Сохраните и примените:
   source ~/.bash_profile
   ```

4. **Проверьте установку:**
   ```bash
   flutter --version
   flutter doctor
   ```

### Способ 2: Установка через Git

1. **Клонируйте репозиторий:**
   ```bash
   cd ~/development
   git clone https://github.com/flutter/flutter.git -b stable
   ```

2. **Добавьте в PATH** (см. способ 1, шаг 3)

3. **Проверьте установку:**
   ```bash
   flutter doctor
   ```

### Способ 3: Установка через Homebrew

1. **Установите Homebrew** (если еще не установлен):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Установите Flutter:**
   ```bash
   brew install --cask flutter
   ```

3. **Проверьте установку:**
   ```bash
   flutter doctor
   ```

---

## Установка на Linux

### Способ 1: Установка через официальный архив (Рекомендуется)

1. **Скачайте Flutter SDK:**
   ```bash
   cd ~/development
   # Для 64-bit Linux
   curl -O https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_3.x.x-stable.tar.xz
   ```

2. **Распакуйте архив:**
   ```bash
   tar xf flutter_linux_3.x.x-stable.tar.xz
   ```

3. **Добавьте Flutter в PATH:**
   ```bash
   # Откройте ~/.bashrc
   nano ~/.bashrc
   
   # Добавьте строку:
   export PATH="$PATH:$HOME/development/flutter/bin"
   
   # Сохраните и примените:
   source ~/.bashrc
   ```

4. **Установите необходимые зависимости:**
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install -y curl git unzip xz-utils zip libglu1-mesa
   
   # Fedora
   sudo dnf install -y curl git unzip xz zip libGLU
   
   # Arch Linux
   sudo pacman -S curl git unzip xz zip libgl
   ```

5. **Проверьте установку:**
   ```bash
   flutter --version
   flutter doctor
   ```

### Способ 2: Установка через Git

1. **Клонируйте репозиторий:**
   ```bash
   cd ~/development
   git clone https://github.com/flutter/flutter.git -b stable
   ```

2. **Добавьте в PATH** (см. способ 1, шаг 3)

3. **Установите зависимости** (см. способ 1, шаг 4)

4. **Проверьте установку:**
   ```bash
   flutter doctor
   ```

### Способ 3: Установка через Snap (Ubuntu)

1. **Установите Flutter:**
   ```bash
   sudo snap install flutter --classic
   ```

2. **Проверьте установку:**
   ```bash
   flutter doctor
   ```

---

## Проверка установки

### Базовая проверка

```bash
# Проверка версии
flutter --version

# Должно показать что-то вроде:
# Flutter 3.x.x • channel stable • https://github.com/flutter/flutter.git
# Framework • revision xxxxx
# Engine • revision xxxxx
# Tools • Dart 3.x.x • DevTools 2.x.x
```

### Полная проверка окружения

```bash
flutter doctor
```

**Ожидаемый вывод (пример для Windows):**
```
Doctor summary (to see all details, run flutter doctor -v):
[✓] Flutter (Channel stable, 3.x.x, on Microsoft Windows [Version 10.x.x])
[✓] Windows Version (Installed version of Windows is version 10 or higher)
[✓] Android toolchain - develop for Android devices (Android SDK version xx.x.x)
[✓] Chrome - develop for the web
[✓] Visual Studio - develop for Windows (Visual Studio Build Tools 2022)
[✓] Android Studio (version 2023.x)
[✓] VS Code (version 1.x.x)
[✓] Connected device (3 available)
[✓] Network resources
```

### Детальная проверка

```bash
flutter doctor -v
```

Показывает подробную информацию о всех компонентах.

---

## Настройка PATH

### Windows

**Временная настройка (для текущей сессии):**
```powershell
$env:Path += ";C:\src\flutter\bin"
```

**Постоянная настройка (через GUI):**
1. Win + R → `sysdm.cpl` → Enter
2. Вкладка "Дополнительно" → "Переменные среды"
3. В "Системные переменные" найдите `Path` → "Изменить"
4. "Создать" → `C:\src\flutter\bin` → "ОК"

**Постоянная настройка (через PowerShell от имени администратора):**
```powershell
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\src\flutter\bin", "Machine")
```

### macOS / Linux

**Временная настройка:**
```bash
export PATH="$PATH:$HOME/development/flutter/bin"
```

**Постоянная настройка (zsh):**
```bash
echo 'export PATH="$PATH:$HOME/development/flutter/bin"' >> ~/.zshrc
source ~/.zshrc
```

**Постоянная настройка (bash):**
```bash
echo 'export PATH="$PATH:$HOME/development/flutter/bin"' >> ~/.bashrc
source ~/.bashrc
```

---

## Решение проблем

### Проблема: "flutter: command not found"

**Причина:** Flutter не добавлен в PATH или терминал не перезапущен.

**Решение:**
1. Проверьте, что Flutter установлен:
   ```bash
   # Windows
   dir C:\src\flutter\bin
   
   # macOS/Linux
   ls ~/development/flutter/bin
   ```

2. Проверьте PATH:
   ```bash
   # Windows
   echo %Path%
   
   # macOS/Linux
   echo $PATH
   ```

3. Убедитесь, что путь к Flutter присутствует в PATH

4. Перезапустите терминал

### Проблема: "Unable to locate Android SDK"

**Решение:**
1. Установите Android Studio
2. Настройте ANDROID_HOME:
   ```bash
   # Windows
   setx ANDROID_HOME "C:\Users\<username>\AppData\Local\Android\Sdk"
   
   # macOS/Linux
   export ANDROID_HOME=$HOME/Library/Android/sdk
   echo 'export ANDROID_HOME=$HOME/Library/Android/sdk' >> ~/.zshrc
   ```

3. Запустите `flutter doctor` снова

### Проблема: "Xcode not installed" (macOS)

**Решение:**
1. Установите Xcode из App Store
2. Откройте Xcode и примите лицензию
3. Установите дополнительные компоненты:
   ```bash
   sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer
   sudo xcodebuild -runFirstLaunch
   ```

### Проблема: "Git not found"

**Решение:**
- **Windows:** Установите Git для Windows с https://git-scm.com/download/win
- **macOS:** Установите Xcode Command Line Tools:
  ```bash
  xcode-select --install
  ```
- **Linux:** Установите Git:
  ```bash
  sudo apt-get install git  # Ubuntu/Debian
  sudo dnf install git      # Fedora
  ```

### Проблема: "Unable to find Chrome"

**Решение:**
- Установите Google Chrome
- Или используйте другой браузер, указав путь:
  ```bash
  flutter config --chrome-executable-path="/path/to/chrome"
  ```

### Проблема: "License not accepted" (Android)

**Решение:**
```bash
# Примите лицензии Android SDK
flutter doctor --android-licenses
# Нажимайте 'y' для принятия всех лицензий
```

### Проблема: Медленная загрузка зависимостей

**Решение:**
1. Используйте зеркало Flutter (для Китая):
   ```bash
   export PUB_HOSTED_URL=https://pub.flutter-io.cn
   export FLUTTER_STORAGE_BASE_URL=https://storage.flutter-io.cn
   ```

2. Или используйте VPN/прокси

### Проблема: "Permission denied" (Linux/macOS)

**Решение:**
```bash
# Убедитесь, что у вас есть права на выполнение
chmod +x ~/development/flutter/bin/flutter

# Или используйте sudo (не рекомендуется)
```

---

## Обновление Flutter

### Обновление до последней стабильной версии

```bash
flutter upgrade
```

### Обновление до конкретной версии

```bash
# Переключитесь на нужную версию
flutter channel stable  # или beta, dev, master
flutter upgrade
```

### Проверка текущей версии

```bash
flutter --version
```

---

## Дополнительные инструменты

### Flutter DevTools

Устанавливается автоматически с Flutter. Запуск:
```bash
flutter pub global activate devtools
flutter pub global run devtools
```

### Dart SDK

Включается автоматически с Flutter. Проверка:
```bash
dart --version
```

---

## Полезные ссылки

- **Официальная документация:** https://docs.flutter.dev
- **Установка Flutter:** https://docs.flutter.dev/get-started/install
- **Настройка редакторов:** https://docs.flutter.dev/get-started/editor
- **Часто задаваемые вопросы:** https://docs.flutter.dev/resources/faq
- **GitHub Flutter:** https://github.com/flutter/flutter

---

## Следующие шаги

После успешной установки Flutter SDK:

1. **Настройте редактор:**
   - VS Code: установите расширение "Flutter"
   - Android Studio: установите плагин "Flutter"
   - IntelliJ IDEA: установите плагин "Flutter"

2. **Создайте первое приложение:**
   ```bash
   flutter create my_app
   cd my_app
   flutter run
   ```

3. **Настройте эмулятор/симулятор:**
   - Android: через Android Studio → AVD Manager
   - iOS: через Xcode → Window → Devices and Simulators

4. **Начните разработку:**
   - Изучите документацию: https://docs.flutter.dev
   - Попробуйте примеры: https://docs.flutter.dev/cookbook
   - Присоединитесь к сообществу: https://flutter.dev/community

---

**Успешной установки! 🚀**

