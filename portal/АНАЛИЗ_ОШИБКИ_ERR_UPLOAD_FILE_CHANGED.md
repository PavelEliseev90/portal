# Анализ ошибки ERR_UPLOAD_FILE_CHANGED при сохранении интерактивной оценки

## 🔴 Описание ошибки

**Ошибка:** `ERR_UPLOAD_FILE_CHANGED`  
**Сообщение:** "Не удалось получить доступ к файлу. Возможно, он был перемещён, изменён или удалён."

Эта ошибка возникает в браузерах Chrome/Edge при загрузке файлов через форму.

---

## 🔍 Возможные причины

### 1. **Проблема с CSRF токеном** ⭐⭐⭐ (НАИБОЛЕЕ ВЕРОЯТНО)

**Причина:**
- CSRF токен истек во время загрузки файла
- CSRF токен изменился между отправкой формы и обработкой на сервере
- Долгая загрузка файла приводит к истечению срока действия токена

**Как проверить:**
- Откройте DevTools (F12) → Network
- Найдите запрос с ошибкой
- Проверьте заголовок `X-CSRFToken` и сравните с токеном в форме

**Решение:**
```python
# В settings.py уже есть настройки, но можно добавить:
CSRF_COOKIE_AGE = 3600 * 24  # 24 часа вместо дефолтных 1 часа
CSRF_USE_SESSIONS = True  # Использовать сессию для CSRF
```

---

### 2. **Проблема с сессией** ⭐⭐⭐

**Причина:**
- Сессия истекла во время загрузки
- Сессия была изменена другим запросом
- Проблемы с хранением сессии

**Как проверить:**
- Проверьте настройки сессии в `settings.py`
- Проверьте логи сервера на ошибки сессии

**Решение:**
```python
# В settings.py:
SESSION_COOKIE_AGE = 3600 * 24  # 24 часа
SESSION_SAVE_EVERY_REQUEST = True  # Обновлять сессию при каждом запросе
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Не закрывать при закрытии браузера
```

---

### 3. **Проблема с размером файла** ⭐⭐

**Причина:**
- Файл слишком большой
- Превышен лимит `FILE_UPLOAD_MAX_MEMORY_SIZE`
- Превышен лимит веб-сервера (Nginx/Apache)

**Текущие настройки:**
```python
# В settings.py:
FILE_UPLOAD_MAX_MEMORY_SIZE = 262144000000  # ~250 GB (очень большой!)
DATA_UPLOAD_MAX_MEMORY_SIZE = None
```

**Проблема:** Несмотря на большой лимит, веб-сервер (Nginx) может иметь свой лимит.

**Решение:**
```nginx
# В конфигурации Nginx:
client_max_body_size 100M;  # Или больше, если нужно
client_body_timeout 300s;   # Таймаут загрузки
```

---

### 4. **Проблема с таймаутом** ⭐⭐

**Причина:**
- Загрузка файла занимает слишком много времени
- Таймаут на стороне веб-сервера или Django

**Решение:**
```python
# В settings.py (для Django):
DATA_UPLOAD_MAX_MEMORY_SIZE = None  # Уже есть
FILE_UPLOAD_MAX_MEMORY_SIZE = 262144000000  # Уже есть

# Для веб-сервера (Nginx):
client_body_timeout 300s;
proxy_read_timeout 300s;
proxy_connect_timeout 300s;
proxy_send_timeout 300s;
```

---

### 5. **Проблема с `get_or_create` при загрузке файлов** ⭐⭐⭐

**Текущий код (строки 3110-3119):**
```python
files_diagnostic = request.FILES.getlist('file_diagnistic')
for file_object in files_diagnostic: 
    name = file_object.name.lower()
    new_estimation_files, created = RegRegInteractivOcenkaFiles.objects.get_or_create(
        estimation = reg_interactiv_ocenka, 
        type_file = 'diagnostic', 
        type_point = type_point, 
        text = text, 
        cor_x = x, 
        cor_y = y, 
        name = name
    )
    new_estimation_files.file = file_object
    new_estimation_files.user = request.user
    new_estimation_files.save()
```

**Проблема:**
- Если файл с таким же `name` уже существует, `get_or_create` вернет существующую запись
- При попытке сохранить новый файл поверх существующего может возникнуть конфликт
- Файл может быть заблокирован другим процессом

**Решение:**
```python
files_diagnostic = request.FILES.getlist('file_diagnistic')
for file_object in files_diagnostic: 
    try:
        name = file_object.name.lower()
        
        # Генерируем уникальное имя файла
        import uuid
        import os
        file_ext = os.path.splitext(name)[1]
        unique_name = f"{uuid.uuid4()}{file_ext}"
        
        # Создаем новую запись вместо get_or_create
        new_estimation_files = RegRegInteractivOcenkaFiles(
            estimation = reg_interactiv_ocenka,
            type_file = 'diagnostic',
            type_point = type_point,
            text = text,
            cor_x = x,
            cor_y = y,
            name = unique_name,  # Уникальное имя
            file_number = 1,
            user = request.user
        )
        new_estimation_files.file = file_object
        new_estimation_files.save()
        send_diagnostic = True
        reg_interactiv_ocenka.date_diagnostic = DT.datetime.now()
    except Exception as e:
        # Логируем ошибку
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка загрузки файла диагностики: {e}")
        # Продолжаем обработку других файлов
        continue
```

---

### 6. **Проблема с правами доступа к файлам** ⭐

**Причина:**
- Нет прав на запись в директорию `MEDIA_ROOT/estimation/`
- Файл заблокирован другим процессом
- Проблемы с сетевым хранилищем (если используется)

**Решение:**
```python
# Проверка прав доступа перед сохранением
import os
upload_dir = os.path.join(settings.MEDIA_ROOT, 'estimation', 
                         DT.datetime.now().strftime('%Y/%m/%d'))
os.makedirs(upload_dir, exist_ok=True)

# Проверка прав на запись
if not os.access(upload_dir, os.W_OK):
    raise PermissionError(f"Нет прав на запись в {upload_dir}")
```

---

### 7. **Проблема с обработкой файла во время загрузки** ⭐

**Причина:**
- Файл обрабатывается (например, оптимизация изображения) во время загрузки
- Обработка занимает слишком много времени
- Файл изменяется во время обработки

**Решение:**
- Обрабатывать файл после сохранения, а не во время
- Использовать асинхронную обработку (Celery)

---

### 8. **Проблема с множественной отправкой формы** ⭐⭐

**Причина:**
- Пользователь нажал "Сохранить" несколько раз
- Несколько запросов обрабатывают один и тот же файл
- Конфликт при сохранении

**Решение:**
```python
# Добавить защиту от двойной отправки
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import hashlib
import time

# В view:
if 'diagnostic_save' in request.POST:
    # Генерируем уникальный ключ для этой операции
    file_hash = hashlib.md5(
        f"{request.user.id}_{estimation.id}_{time.time()}".encode()
    ).hexdigest()
    
    # Проверяем, не обрабатывается ли уже
    cache_key = f"diagnostic_upload_{estimation.id}"
    if cache.get(cache_key):
        return JsonResponse({'error': 'Загрузка уже выполняется'}, status=400)
    
    # Устанавливаем флаг
    cache.set(cache_key, file_hash, timeout=300)  # 5 минут
    
    try:
        # Обработка файлов
        ...
    finally:
        # Снимаем флаг
        cache.delete(cache_key)
```

---

## 🛠️ Рекомендуемые исправления

### Исправление 1: Улучшенная обработка файлов

```python
# В eco/views.py, функция doc(), блок обработки диагностики:

files_diagnostic = request.FILES.getlist('file_diagnistic')
if files_diagnostic:
    import uuid
    import os
    from django.core.cache import cache
    
    # Защита от двойной отправки
    cache_key = f"diagnostic_upload_{reg_interactiv_ocenka.id}"
    if cache.get(cache_key):
        return JsonResponse({
            'error': 'Загрузка файлов уже выполняется. Подождите...'
        }, status=400)
    
    cache.set(cache_key, True, timeout=300)
    
    try:
        for file_object in files_diagnostic:
            try:
                # Генерируем уникальное имя
                original_name = file_object.name.lower()
                file_ext = os.path.splitext(original_name)[1]
                unique_name = f"{uuid.uuid4()}{file_ext}"
                
                # Создаем новую запись
                new_estimation_files = RegRegInteractivOcenkaFiles(
                    estimation=reg_interactiv_ocenka,
                    type_file='diagnostic',
                    type_point=type_point or '',
                    text=text or '',
                    cor_x=x or 0,
                    cor_y=y or 0,
                    name=unique_name,
                    file_number=1,
                    user=request.user
                )
                new_estimation_files.file = file_object
                new_estimation_files.save()
                send_diagnostic = True
                reg_interactiv_ocenka.date_diagnostic = DT.datetime.now()
                
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Ошибка загрузки файла {file_object.name}: {e}")
                # Продолжаем обработку других файлов
                continue
                
    finally:
        cache.delete(cache_key)
```

---

### Исправление 2: Настройки CSRF и сессии

```python
# В settings.py добавить/изменить:

# CSRF настройки
CSRF_COOKIE_AGE = 3600 * 24  # 24 часа
CSRF_USE_SESSIONS = True
CSRF_COOKIE_SECURE = False  # True для HTTPS
CSRF_COOKIE_HTTPONLY = False

# Сессия
SESSION_COOKIE_AGE = 3600 * 24  # 24 часа
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
```

---

### Исправление 3: JavaScript защита от двойной отправки

```javascript
// В шаблоне формы диагностики:

let isUploading = false;

document.querySelector('form').addEventListener('submit', function(e) {
    if (isUploading) {
        e.preventDefault();
        alert('Загрузка уже выполняется. Подождите...');
        return false;
    }
    
    isUploading = true;
    const submitBtn = this.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Загрузка...';
    
    // Снимаем блокировку через 5 минут (на случай ошибки)
    setTimeout(() => {
        isUploading = false;
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }, 300000);
});
```

---

### Исправление 4: Проверка размера файла на клиенте

```javascript
// В шаблоне формы:

document.querySelector('input[type="file"]').addEventListener('change', function(e) {
    const maxSize = 50 * 1024 * 1024; // 50 MB
    const files = e.target.files;
    
    for (let file of files) {
        if (file.size > maxSize) {
            alert(`Файл ${file.name} слишком большой (${(file.size/1024/1024).toFixed(2)} MB). Максимальный размер: 50 MB`);
            e.target.value = ''; // Очищаем выбор
            return;
        }
    }
});
```

---

## 🔧 Проверка конфигурации веб-сервера

### Для Nginx:

```nginx
# В конфигурации сайта:

client_max_body_size 100M;  # Максимальный размер загружаемого файла
client_body_timeout 300s;   # Таймаут загрузки тела запроса
client_body_buffer_size 128k;

# Для проксирования к Django:
proxy_read_timeout 300s;
proxy_connect_timeout 300s;
proxy_send_timeout 300s;
proxy_buffering off;  # Отключить буферизацию для больших файлов
```

### Для Apache:

```apache
# В .htaccess или конфигурации:

php_value upload_max_filesize 100M
php_value post_max_size 100M
php_value max_execution_time 300
php_value max_input_time 300
```

---

## 📊 Диагностика проблемы

### Шаг 1: Проверка логов

```python
# Добавить логирование в view:

import logging
logger = logging.getLogger(__name__)

files_diagnostic = request.FILES.getlist('file_diagnistic')
logger.info(f"Получено файлов для загрузки: {len(files_diagnostic)}")

for file_object in files_diagnostic:
    logger.info(f"Обработка файла: {file_object.name}, размер: {file_object.size}")
    try:
        # ... код сохранения ...
        logger.info(f"Файл {file_object.name} успешно сохранен")
    except Exception as e:
        logger.error(f"Ошибка сохранения файла {file_object.name}: {e}", exc_info=True)
```

### Шаг 2: Проверка в браузере

1. Откройте DevTools (F12)
2. Перейдите на вкладку Network
3. Попробуйте загрузить файл
4. Найдите запрос с ошибкой
5. Проверьте:
   - Статус код ответа
   - Заголовки запроса (CSRF токен)
   - Тело ответа (текст ошибки)

### Шаг 3: Проверка на сервере

```bash
# Проверка прав доступа
ls -la /path/to/MEDIA_ROOT/estimation/

# Проверка места на диске
df -h /path/to/MEDIA_ROOT/

# Проверка логов Django
tail -f /path/to/logs/django.log
```

---

## ✅ Быстрое решение (временное)

Если нужно быстро решить проблему:

1. **Увеличить таймауты:**
   ```python
   # В settings.py:
   CSRF_COOKIE_AGE = 3600 * 24
   SESSION_COOKIE_AGE = 3600 * 24
   ```

2. **Использовать уникальные имена файлов:**
   ```python
   # Вместо get_or_create использовать просто create с UUID
   ```

3. **Добавить обработку ошибок:**
   ```python
   try:
       # код сохранения
   except Exception as e:
       logger.error(f"Ошибка: {e}")
       return JsonResponse({'error': str(e)}, status=500)
   ```

---

## 🎯 Рекомендуемый порядок действий

1. ✅ **Сначала:** Увеличить таймауты CSRF и сессии
2. ✅ **Затем:** Исправить обработку файлов (уникальные имена)
3. ✅ **Потом:** Добавить защиту от двойной отправки
4. ✅ **И наконец:** Настроить веб-сервер (Nginx/Apache)

---

## 📝 Чек-лист для проверки

- [ ] CSRF токен не истекает во время загрузки
- [ ] Сессия не истекает во время загрузки
- [ ] Размер файла не превышает лимиты
- [ ] Файлы сохраняются с уникальными именами
- [ ] Есть защита от двойной отправки
- [ ] Права доступа к директории корректны
- [ ] Таймауты веб-сервера достаточны
- [ ] Логирование ошибок включено

---

## 💡 Дополнительные рекомендации

1. **Использовать прогресс-бар** для загрузки файлов
2. **Разбивать большие файлы** на части (chunked upload)
3. **Использовать AJAX** для загрузки файлов вместо обычной формы
4. **Валидировать файлы** на клиенте перед отправкой
5. **Показывать понятные сообщения** об ошибках пользователю

