# Maxposter Auction Parser

Локальный парсер аукциона Авито (Maxposter) для рабочих станций.  
Работает **отдельно от Django-портала**; синхронизация — только по HTTP API.

Базовый URL портала: **https://ah.kors-group.com**

---

## Как пользоваться (несколько площадок сразу)

Рекомендуемый режим: **отдельный процесс / порт / Playwright на каждую площадку**.  
Площадки не переключаются внутри одного браузера — не пересекаются сессии, дампы и зависания.

### 1. Установка (один раз)

```bat
cd tools\maxposter_auction
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
copy .env.example .env
```

В `.env` укажите общий логин Maxposter:

```env
MAXPOSTER_EMAIL=you@company.com
MAXPOSTER_PASSWORD=secret
PORTAL_BASE=https://ah.kors-group.com
```

### 2. Конфиг площадок

```bat
copy instances.example.json instances.json
```

Откройте `instances.json` и для нужных ДЦ поставьте `"enabled": true`, проверьте порты:

```json
{
  "hubPort": 8005,
  "portalBase": "https://ah.kors-group.com",
  "instances": [
    { "dealerId": "2104", "label": "КорсАвто Тула", "port": 8010, "enabled": true },
    { "dealerId": "2106", "label": "КорсАвто Новомосковск", "port": 8011, "enabled": true }
  ]
}
```

Правила:

- `hubPort` — страница мониторинга (не должна совпадать с портами воркеров)
- у каждой площадки **свой** `port`
- `dealerId` — ID Maxposter (как в profile-switch)

### 3. Запуск всех воркеров

```bat
start_all.bat
```

или:

```bat
python launcher_multi.py
```

Что произойдёт:

1. Откроется **хаб мониторинга**: http://127.0.0.1:8005/monitor.html  
2. Для каждой `enabled` площадки — **отдельное окно CMD** с `server.py`  
3. Данные площадки пишутся в `instances/<dealerId>/` (offers_dump, session, status)

### 4. Мониторинг

Откройте http://127.0.0.1:8005/monitor.html

На карточке площадки видно:

- онлайн / офлайн
- число лотов и время данных
- занятость: reload / ставка / итоги
- ссылки **Открыть viewer** и `/api/instance`

Обновление статусов — каждые 3 секунды.

### 5. Работа в viewer площадки

Пример: http://127.0.0.1:8010/viewer.html

- площадка **зафиксирована** (селект недоступен)
- логин/пароль можно оставить пустыми, если они есть в `.env` воркера
- «Перезагрузить», автоставки, «Итоги лотов» — как раньше
- вкладка **Логи** — полный ход работы (в CMD почти тишина)

### 6. Остановка

- закрыть окно CMD конкретной площадки — остановится только она  
- закрыть окно хаба — пропадёт мониторинг (воркеры продолжат работать)  
- `Ctrl+C` в окне `launcher_multi` — только выход launcher’а

---

## Одна площадка (старый режим)

```bat
start_server.bat
```

или `python launcher.py` → http://127.0.0.1:8005/viewer.html  

В этом режиме выбираете площадку в селекте; данные — в корне `tools/maxposter_auction/` (`offers_dump.json`).

---

## Архитектура

```
[ПК парсера]
  hub :8005  → monitor.html          (без Playwright)
  worker :8010 dealer 2104           Playwright + session 2104
  worker :8011 dealer 2106           Playwright + session 2106
        │
        ├─→ Maxposter
        └─→ Портал ah.kors-group.com  (/api/calculate_car/, ставки, итоги)
```

| Ресурс | Изоляция |
|--------|----------|
| HTTP | свой порт |
| Playwright | свой Chromium |
| Сессия Maxposter | `instances/<id>/maxposter_session.json` |
| Лоты | `instances/<id>/offers_dump.json` |
| Locks reload/bid/outcome | только внутри процесса |

---

## Интеграция с порталом

| Действие | API |
|----------|-----|
| Синхронизация лота + расчёт | `POST /api/calculate_car/` |
| Фиксация ставки | `POST /api/avito_auction_bid_set/` |
| Пакетное состояние ставок | `POST /api/avito_auction_offers_state/` |
| Настройки автоставок | `GET/POST /api/avito_auction_settings/` |
| Решение автоставки | `POST /api/avito_auction_auto_bid_decide/` |
| Очередь итогов | `GET /api/avito_auction_outcome_queue/` |
| Запись итога | `POST /api/avito_auction_outcome_set/` |

### Итоги завершённых лотов

1. Очередь с портала (`outcome_queue`)  
2. Страница лота Maxposter (`…/view`) под той же сессией  
3. Разбор статуса → запись на портал; при **won** / **not_taken** — чат + email  

В viewer: **«Итоги лотов»** или автоцепочка «Итоги после обновления».

### Автоставки

Условия — на портале `/auction_avito/settings/`.  
В viewer локальный переключатель «Автоставки после расчёта» = **Вкл**.

---

## Файлы

| Файл | Назначение |
|------|------------|
| `start_all.bat` / `launcher_multi.py` | Хаб + все воркеры |
| `hub_server.py` / `monitor.html` | Мониторинг |
| `instances.example.json` | Шаблон списка площадок |
| `server.py` | Воркер площадки (`/api/reload`, `/api/bid`, `/api/outcomes`, `/api/instance`) |
| `viewer.html` | UI лотов и логов |
| `script_auction.py` / `script_bid.py` / `script_outcome.py` | Playwright-скрипты |
| `launcher.py` / `start_server.bat` | Одиночный режим |

API воркера для мониторинга: `GET /api/instance`  
API хаба: `GET /api/workers`

---

## Сборка exe

```bat
pip install -r requirements-build.txt
build_exe.bat
```

(Мульти-инстанс в exe — через отдельные процессы с `INSTANCE_DIR` / `PORT`; при необходимости доработайте spec.)

## Секреты и дампы

Не коммитить: `.env`, `instances.json`, `instances/`, `maxposter_session.json`, `offers_dump*.json`.
