# План оптимизации и ускорения страниц /recognitions/

## Обзор страниц

### Основные страницы (portal/apps/recognition/views.py):
1. `/recognitions/` - `start()` - Главная страница распознавания
2. `/recognitions/op/` - `op()` - ОП распознавания
3. `/recognitions/op/<id>/` - `op_detail()` - Детали ОП
4. `/recognitions/tematiks/` - `tematiks()` - Тематики
5. `/recognitions/tematiks_op/` - `tematiks_op()` - Тематики ОП
6. `/recognitions/questions/` - `records_questions()` - Вопросы
7. `/recognitions/<id>` - `recognition()` - Детали распознавания
8. `/recognitions/check_lists/` - `check_lists()` - Чек-листы
9. `/recognitions/control/` - `control()` - Контроль
10. `/recognitions/cvc_op/` - `cvc_op()` - CVC ОП
11. `/recognitions/report_cvc_kg_op/` - `report_cvc_kg_op()` - Отчет CVC КГ ОП

### Телефония (portal/apps/telephony/views.py):
12. `/telephony/recognitions/` - `telephony_recognitions()` - Главная телефония
13. `/telephony/recognitions/queue/` - `telephony_queue()` - Очередь
14. `/telephony/recognitions/tematiks/` - `telephony_tematiks()` - Тематики
15. `/telephony/recognitions/questions/` - `telephony_questions()` - Вопросы

---

## КРИТИЧЕСКИЕ ПРОБЛЕМЫ И РЕШЕНИЯ

### 1. `/recognitions/` - `start()` (строки 122-177)

**Проблемы:**
- ❌ 10+ отдельных `count()` запросов без кеширования
- ❌ Отсутствие `select_related()` для связанных объектов
- ❌ Множественные агрегации `Sum()` без оптимизации
- ❌ Фильтрация по `rlk__dataTime` без индекса

**Решения:**
```python
# Объединить count запросы в один с использованием annotate
# Добавить select_related('rlk') где необходимо
# Использовать только() для ограничения полей
# Добавить индекс на rlk.dataTime
```

**Приоритет:** 🔴 ВЫСОКИЙ
**Ожидаемое ускорение:** 3-5x

---

### 2. `/recognitions/op/` - `op()` (строки 421-491)

**Проблемы:**
- ❌ **КРИТИЧНО:** N+1 запросы в циклах (строки 455-482)
- ❌ В цикле по городам выполняется запрос для каждого города
- ❌ В цикле по подразделениям выполняется 2 запроса (count + aggregate) для каждого подразделения
- ❌ Отсутствие `select_related()` для `rlk`, `unit`, `city`
- ❌ Фильтрация без индексов

**Решения:**
```python
# Использовать annotate() для предварительного подсчета
# Объединить count и aggregate в один запрос
# Использовать values() с агрегацией вместо циклов
# Добавить select_related('rlk', 'rlk__unit', 'rlk__city')
# Оптимизировать пагинацию
# Добавить индексы на часто используемые поля
```

**Пример оптимизации:**
```python
# Вместо циклов использовать:
from django.db.models import Count, Sum
data = Records_voice_recorder_queue.objects.filter(...).values(
    'rlk__unit__city', 'rlk__unit__city__name',
    'rlk__unit', 'rlk__unit__name'
).annotate(
    count=Count('id'),
    duration_sum=Sum('duration')
).order_by('rlk__unit__city__name', 'rlk__unit__name')
```

**Приоритет:** 🔴 КРИТИЧЕСКИЙ
**Ожидаемое ускорение:** 10-20x

---

### 3. `/recognitions/` - `recognitions()` (строки 787-813)

**Проблемы:**
- ❌ **КРИТИЧНО:** `list(recognitions_list)` загружает ВСЕ записи в память перед пагинацией
- ❌ Отсутствие `select_related()`
- ❌ Фильтр `name__contains` без индекса

**Решения:**
```python
# УДАЛИТЬ list() - передавать QuerySet напрямую в Paginator
paginator = Paginator(recognitions_list, countListRecord)  # БЕЗ list()

# Добавить select_related() если есть связи
# Добавить индекс на name или использовать full-text search
```

**Приоритет:** 🔴 КРИТИЧЕСКИЙ
**Ожидаемое ускорение:** 10-50x (в зависимости от объема данных)

---

### 4. `/recognitions/<id>` - `recognition()` (строки 816-886)

**Проблемы:**
- ❌ `Records_voice_recorder.objects.get(pk=id)` без `select_related()`
- ❌ Парсинг большого JSON в памяти
- ❌ Множественные операции fuzzy matching без оптимизации

**Решения:**
```python
# Добавить select_related() для связанных объектов
# Кешировать распарсенный JSON
# Оптимизировать fuzzy matching (использовать только при необходимости)
# Рассмотреть асинхронную обработку
```

**Приоритет:** 🟡 СРЕДНИЙ
**Ожидаемое ускорение:** 2-3x

---

### 5. `/recognitions/tematiks_op/` - `tematiks_op()` (строки 631-678)

**Проблемы:**
- ❌ Отсутствие `select_related('anketa')`
- ❌ Фильтрация без индексов

**Решения:**
```python
# Добавить select_related('anketa')
# Добавить индекс на name, enabled
```

**Приоритет:** 🟡 СРЕДНИЙ
**Ожидаемое ускорение:** 1.5-2x

---

### 6. `/recognitions/check_lists/` - `check_lists()` (строки 180-226)

**Проблемы:**
- ❌ `Check_settings.objects.all()` без оптимизации
- ❌ Отсутствие `select_related()` для `check_settings`
- ❌ Множественные запросы в цикле

**Решения:**
```python
# Добавить select_related('check_settings_cvc')
# Оптимизировать запросы Settings_check_records
```

**Приоритет:** 🟡 СРЕДНИЙ
**Ожидаемое ускорение:** 2-3x

---

### 7. `/recognitions/check_lists/<id>` - `check_lists_edit()` (строки 229-317)

**Проблемы:**
- ❌ N+1 запросы в цикле `for check_list in list_checklist_cvc:`
- ❌ Множественные запросы `Records_voice_recorder_cvc_checklist_kg.objects.filter()`
- ❌ Отсутствие `prefetch_related()` для ManyToMany

**Решения:**
```python
# Использовать prefetch_related('tematics', 'questions_kg')
# Объединить запросы в один с использованием bulk operations
# Оптимизировать циклы с запросами к БД
```

**Приоритет:** 🔴 ВЫСОКИЙ
**Ожидаемое ускорение:** 5-10x

---

### 8. `/telephony/recognitions/` - `telephony_recognitions()` (строки 39-98)

**Проблемы:**
- ❌ 8+ отдельных `count()` запросов
- ❌ Сложный Subquery без оптимизации
- ❌ Отсутствие кеширования

**Решения:**
```python
# Объединить count запросы
# Оптимизировать Subquery
# Добавить кеширование для статических данных
# Использовать annotate() вместо отдельных count()
```

**Приоритет:** 🔴 ВЫСОКИЙ
**Ожидаемое ускорение:** 3-5x

---

### 9. `/telephony/recognitions/queue/` - `telephony_queue()` (строки 101-121)

**Проблемы:**
- ❌ Использование `.values()` с distinct() может быть неоптимальным
- ❌ Отсутствие индексов на комбинации полей

**Решения:**
- Добавить select_related/prefetch_related где возможно
- Оптимизировать пагинацию
- Добавить индексы

**Приоритет:** 🟡 СРЕДНИЙ
**Ожидаемое ускорение:** 1.5-2x

---

### 9a. `/telephony/recognitions/success/` - `telephony_queue_success()` (строки 124-198)

**Проблемы:**
- ❌ **КРИТИЧНО:** N+1 запросы в циклах (строки 163-189)
- ❌ В цикле по городам выполняется запрос для каждого города
- ❌ В цикле по подразделениям выполняется 2 запроса (count + aggregate) для каждого подразделения
- ❌ Сложный Subquery выполняется многократно
- ❌ Отсутствие `select_related()` для связанных объектов

**Решения:**
```python
# Использовать annotate() для предварительного подсчета
# Объединить count и aggregate в один запрос
# Использовать values() с агрегацией вместо циклов
# Оптимизировать Subquery - вычислить один раз
# Добавить select_related('rlk', 'rlk__unit', 'rlk__city')
```

**Приоритет:** 🔴 КРИТИЧЕСКИЙ
**Ожидаемое ускорение:** 10-20x

---

### 10. `/recognitions/control/` - `control()` (строки 900-996)

**Проблемы:**
- ❌ **КРИТИЧНО:** N+1 запросы в циклах (строки 946-982)
- ❌ В цикле по городам выполняется запрос для каждого города
- ❌ В цикле по подразделениям выполняется 3 запроса (count + 2 filter) для каждого подразделения
- ❌ Сложный Subquery без оптимизации
- ❌ Отсутствие `select_related()` для связанных объектов

**Решения:**
```python
# Использовать annotate() для предварительного подсчета
# Объединить все count запросы в один с использованием Case/When
# Использовать values() с агрегацией вместо циклов
# Оптимизировать Subquery
# Добавить select_related('unit', 'unit__city')
```

**Приоритет:** 🔴 КРИТИЧЕСКИЙ
**Ожидаемое ускорение:** 10-20x

---

## СТИЛИЗАЦИЯ В СТИЛЕ ПОРТАЛА

### Применение единого стиля портала

**Базовый шаблон:** `base_web.html`
**Стили:** `portal-style.css` (классы `.portal-page`, `.portal-header`, `.portal-panel`, `.metric-card`)

**Стандартные компоненты:**
- `.portal-page` - обертка страницы
- `.portal-header` - заголовок страницы
- `.portal-panel` - панели/карточки
- `.metric-card` - карточки с метриками
- Единая цветовая схема: `#002a5a`, `#6c7a92`, `#8ea1ba`, `#f4f7fb`
- Единые скругления: `1.2-1.3rem`
- Единые тени: `0 18px 38px rgba(0, 23, 61, 0.07)`

**План стилизации:**
- Каждая страница будет переделана в едином стиле портала
- Оптимизация и стилизация выполняются одновременно
- Сохранение всей функциональности

---

## ОБЩИЕ ОПТИМИЗАЦИИ

### A. Индексы базы данных

**Критичные индексы:**
```sql
-- Для recognition
CREATE INDEX idx_recognition_date ON recognition_records_voice_recorder(date);
CREATE INDEX idx_recognition_name ON recognition_recognition_call(name);
CREATE INDEX idx_recognition_rlk_datetime ON recognition_records_voice_recorder_queue(rlk_id, dataTime);

-- Для telephony
CREATE INDEX idx_telephony_queue_direction_datajson ON telephony_telephony_records_queue(direction, data_json);
CREATE INDEX idx_telephony_queue_rlk_datetime ON telephony_telephony_records_queue(rlk_id, dataTime);

-- Для CVC
CREATE INDEX idx_cvc_checklist_direction_success ON recognition_records_voice_recorder_cvc_checklist(direction, success);
CREATE INDEX idx_cvc_checklist_rlk_datetime ON recognition_records_voice_recorder_cvc_checklist(rlk_id, dataTime);
```

**Приоритет:** 🔴 ВЫСОКИЙ

---

### B. Кеширование

**Что кешировать:**
1. Статистика на главной странице (TTL: 5-10 минут)
2. Справочники (tematiks, questions) - до изменения
3. Count запросы для дашбордов

**Реализация:**
```python
from django.core.cache import cache

# Пример
cache_key = f'start_stats_{date_start}_{date_end}'
stats = cache.get(cache_key)
if not stats:
    stats = calculate_stats()
    cache.set(cache_key, stats, 600)  # 10 минут
```

**Приоритет:** 🟡 СРЕДНИЙ

---

### C. Оптимизация пагинации

**Проблема:** Использование `list()` перед пагинацией

**Решение:** Всегда передавать QuerySet в Paginator

**Приоритет:** 🔴 КРИТИЧЕСКИЙ

---

### D. select_related и prefetch_related

**Где добавить:**
- Все запросы с ForeignKey должны использовать `select_related()`
- Все ManyToMany должны использовать `prefetch_related()`
- Вложенные связи: `select_related('rlk', 'rlk__unit', 'rlk__city')`

**Приоритет:** 🔴 ВЫСОКИЙ

---

### E. Оптимизация агрегаций

**Проблема:** Множественные отдельные запросы

**Решение:** Использовать `annotate()` для объединения

```python
# Вместо:
count1 = Model1.objects.filter(...).count()
count2 = Model2.objects.filter(...).count()

# Использовать:
from django.db.models import Count, Q
stats = Model.objects.aggregate(
    count1=Count('id', filter=Q(...)),
    count2=Count('id', filter=Q(...))
)
```

**Приоритет:** 🟡 СРЕДНИЙ

---

## ПРИОРИТЕТЫ ВЫПОЛНЕНИЯ

### Фаза 1 (Критично - выполнить немедленно):
1. ✅ **ВЫПОЛНЕНО:** Страница `/recognitions/` - `start()` - оптимизация + стилизация
   - Объединены count запросы в aggregate с фильтрами
   - Добавлен `select_related('rlk')` для оптимизации
   - Переделан шаблон в стиле портала (portal-page, metric-card)
   - Уменьшено количество SQL запросов с 10+ до 5-6
2. ✅ Исправить `list()` в `recognitions()` - строка 800
3. ✅ Устранить N+1 в `op()` - строки 455-482 (использовать annotate + values)
4. ✅ Устранить N+1 в `control()` - строки 946-982 (использовать annotate + values)
5. ✅ Устранить N+1 в `telephony_queue_success()` - строки 163-189 (использовать annotate + values)
6. ✅ Добавить индексы на часто используемые поля
7. ✅ Добавить `select_related()` в `op()`, `control()`

**Ожидаемый эффект:** 10-20x ускорение основных страниц

---

### Фаза 2 (Высокий приоритет - 1-2 недели):
4. ✅ Оптимизировать `start()` - объединить count запросы
5. ✅ Оптимизировать `check_lists_edit()` - убрать N+1
6. ✅ Оптимизировать `telephony_recognitions()` - объединить запросы
7. ✅ Добавить `select_related/prefetch_related` везде

**Ожидаемый эффект:** 3-5x ускорение

---

### Фаза 3 (Средний приоритет - 1 месяц):
8. ✅ Добавить кеширование для статистики
9. ✅ Оптимизировать остальные views
10. ✅ Оптимизировать fuzzy matching в `recognition()`

**Ожидаемый эффект:** 1.5-2x ускорение

---

## МЕТРИКИ ДЛЯ ОТСЛЕЖИВАНИЯ

1. **Время загрузки страницы** (до/после)
2. **Количество SQL запросов** (до/после)
3. **Время выполнения запросов** (до/после)
4. **Использование памяти** (до/после)

**Инструменты:**
- Django Debug Toolbar
- django-silk
- PostgreSQL EXPLAIN ANALYZE

---

## ОЦЕНКА ТРУДОЗАТРАТ

- **Фаза 1:** 2-3 дня
- **Фаза 2:** 1-2 недели
- **Фаза 3:** 2-3 недели

**Общее время:** 3-5 недель

---

## ОЖИДАЕМЫЙ РЕЗУЛЬТАТ

- **Общее ускорение:** 10-30x для основных страниц (особенно с N+1 проблемами)
- **Снижение нагрузки на БД:** 70-90%
- **Улучшение UX:** Значительное сокращение времени загрузки (с 5-10 сек до 0.5-1 сек)
- **Снижение количества SQL запросов:** с 100-500+ до 5-20 на страницу

---

## ДОПОЛНИТЕЛЬНЫЕ РЕКОМЕНДАЦИИ

### Мониторинг производительности

1. **Установить django-debug-toolbar** для разработки
2. **Установить django-silk** для профилирования
3. **Настроить логирование медленных запросов** (> 1 сек)
4. **Использовать PostgreSQL EXPLAIN ANALYZE** для анализа планов запросов

### Дальнейшие оптимизации

1. **Денормализация данных** - создать витрину данных для статистики
2. **Асинхронная обработка** - вынести тяжелые вычисления в фоновые задачи
3. **CDN для статики** - ускорить загрузку CSS/JS
4. **Database connection pooling** - оптимизировать подключения к БД
5. **Read replicas** - использовать реплики для чтения статистики

