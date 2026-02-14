# Анализ данных страницы `/cars/warehouse/analysis/`

## Текущая реализация

### View функция: `warehouse_analysis`
**Файл:** `portal/apps/avtosalon/views.py` (строки 2290-2310)

#### Источники данных:

1. **Модель `CarsWarehouseShowcase`** (таблица `carsWarehouseShowcase`)
   - **Откуда:** Последняя созданная витрина склада
   - **Как получается:**
     - Если передан параметр `unit` в GET-запросе → берется последняя витрина для этого подразделения
     - Если `unit` не указан → берется последняя витрина вообще
   - **Запрос:**
     ```python
     showcase = CarsWarehouseShowcase.objects.filter(unit_id=unit_id).order_by('-date_created').first()
     # или
     showcase = CarsWarehouseShowcase.objects.order_by('-date_created').first()
     ```

2. **Модель `RefUnit`** (таблица `refUnit`)
   - **Откуда:** Все подразделения для фильтра
   - **Запрос:**
     ```python
     units = RefUnit.objects.all().order_by('name')
     ```

### Структура данных витрины (`CarsWarehouseShowcase`)

**Модель:** `portal/apps/avtosalon/models.py` (строки 386-417)

#### Поля витрины:

1. **Базовые данные:**
   - `date_created` - Дата создания витрины
   - `unit` - Подразделение ДЦ (ForeignKey к RefUnit)

2. **Статистика (агрегированные данные):**
   - `total_cars` - Всего автомобилей на складе
   - `total_price` - Общая стоимость всех автомобилей
   - `total_cost` - Общая себестоимость всех автомобилей

3. **Проблемы (подсчитанные метрики):**
   - `cars_no_photos` - Автомобили без фото
   - `cars_old_photos` - Автомобили со старыми фото (старше 90 дней)
   - `cars_no_evaluation` - Автомобили без оценки
   - `cars_old_evaluation` - Автомобили со старой оценкой (старше 90 дней)
   - `cars_long_in_stock` - Автомобили долго на складе (более 180 дней)

4. **Дополнительные данные:**
   - `data_json` - JSON с детальными данными (пока не используется)

### Как создается витрина

**View функция:** `warehouse_showcase_create`
**Файл:** `portal/apps/avtosalon/views.py` (строки 2220-2287)
**URL:** `/cars/warehouse/showcase/create/`

#### Процесс создания:

1. **Базовый queryset автомобилей:**
   ```python
   cars_qs = RefCarsOrganization.objects.exclude(quantity=0).select_related(
       'unit', 'status', 'store', 'modification_autoru',
       'modification_autoru__model', 'modification_autoru__model__mark',
       'evaluation', 'lo'
   )
   ```
   - Исключаются автомобили с `quantity=0` (проданные)
   - Используется `select_related` для оптимизации запросов

2. **Фильтрация по подразделению:**
   - Если передан `unit_id`, фильтруются автомобили этого подразделения

3. **Подсчет метрик:**

   **Общая статистика:**
   - `total_cars` = количество автомобилей
   - `total_price` = сумма всех `price`
   - `total_cost` = сумма всех `cost_price`

   **Проблемы:**
   - **Без фото:** Автомобили без записей в `RefCarsOrganizationFiles`
   - **Старые фото:** Автомобили, у которых самая старая фотография старше 90 дней
   - **Без оценки:** Автомобили без связанной оценки (`evaluation__isnull=True`)
   - **Старая оценка:** Автомобили с оценкой старше 90 дней или без оценки
   - **Долго на складе:** Автомобили с `date_reception` старше 180 дней

4. **Сохранение витрины:**
   - Создается запись в таблице `carsWarehouseShowcase`
   - Все подсчитанные метрики сохраняются в полях модели

### Источники данных для подсчета метрик

#### 1. Автомобили (`RefCarsOrganization`)
- **Таблица:** `refCarsOrganization`
- **Поля:**
  - `quantity` - количество (0 = продан)
  - `price` - цена продажи
  - `cost_price` - себестоимость
  - `date_reception` - дата поступления на склад
  - `unit` - подразделение (ForeignKey)
  - `evaluation` - оценка (ForeignKey, может быть NULL)

#### 2. Фотографии (`RefCarsOrganizationFiles`)
- **Таблица:** `refCarsOrganizationFiles`
- **Связь:** ForeignKey от `RefCarsOrganization` (related_name='refcarsorganizationfiles_set')
- **Поля:**
  - `file` - файл фотографии
  - `date` - дата загрузки фотографии

#### 3. Оценки (`RegEstimationRefCarsOrganizations` или связанная модель)
- **Связь:** через поле `evaluation` в `RefCarsOrganization`
- **Поля:**
  - `date` - дата оценки

### Проблема: Несоответствие шаблона и view

**Шаблон ожидает:**
- `params.stats` - статистика (total_cars, no_photos, old_photos, и т.д.)
- `params.analysis_results` - список проблемных автомобилей с пагинацией
- `params.filters` - примененные фильтры
- `params.statuses` - список статусов для фильтра

**View передает:**
- `params.showcase` - объект витрины
- `params.units` - список подразделений
- `params.selected_unit_id` - выбранное подразделение

### Рекомендации

1. **Использовать данные из витрины:**
   - `showcase.total_cars` → `stats.total_cars`
   - `showcase.cars_no_photos` → `stats.no_photos`
   - `showcase.cars_old_photos` → `stats.old_photos`
   - и т.д.

2. **Добавить расчет проблемных автомобилей:**
   - Нужно запрашивать реальные автомобили из `RefCarsOrganization`
   - Применять фильтры из GET-параметров
   - Использовать пагинацию

3. **Добавить фильтры:**
   - Получать статусы из `RefStatusCarsOrganization`
   - Обрабатывать GET-параметры фильтров
   - Применять фильтры к queryset автомобилей

### Схема работы (текущая):

```
1. Пользователь открывает /cars/warehouse/analysis/
   ↓
2. View получает последнюю витрину из CarsWarehouseShowcase
   ↓
3. Передает showcase, units в шаблон
   ↓
4. Шаблон пытается использовать params.stats, params.analysis_results
   ↓
5. ❌ ОШИБКА: данные отсутствуют
```

### Схема работы (правильная):

```
1. Пользователь открывает /cars/warehouse/analysis/
   ↓
2. View получает последнюю витрину (для общей статистики)
   ↓
3. View запрашивает автомобили из RefCarsOrganization с фильтрами
   ↓
4. View подсчитывает метрики и проблемные автомобили
   ↓
5. View применяет пагинацию к списку проблемных автомобилей
   ↓
6. Передает все данные в шаблон:
   - showcase (для общей статистики)
   - stats (метрики)
   - analysis_results (проблемные автомобили с пагинацией)
   - filters (примененные фильтры)
   - statuses (для фильтра)
   - units (для фильтра)
```

