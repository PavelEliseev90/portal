# Maxposter Auction Parser

Локальный парсер аукциона Авито (Maxposter) для рабочих станций.  
Работает **отдельно от Django-портала**; синхронизация — только по HTTP API.

Базовый URL портала: **https://ah.kors-group.com**

## Архитектура

```
[ПК с парсером]                         [Сервер портала]
  Playwright → Maxposter API                Django auction_avito
  viewer.html :8005                    ←→   /api/calculate_car/
                                            /api/avito_auction_bid_set/
                                            UI, чат, лента, история ставок
```

Парсер не требует доступа к БД портала. Достаточно сети до `ah.kors-group.com`.

## Быстрый старт

```bat
cd tools\maxposter_auction
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
copy .env.example .env
REM отредактируйте .env — логин Maxposter
python launcher.py
```

Откроется `http://127.0.0.1:8005/viewer.html`.

Или: `start_server.bat` (только `server.py`, без автo-открытия браузера).

## Интеграция с порталом

| Действие | API | Код |
|----------|-----|-----|
| Синхронизация лота + расчёт | `POST /api/calculate_car/` | `viewer.html` → `buildCalcPayload()` |
| Фиксация ставки в портале | `POST /api/avito_auction_bid_set/` | `viewer.html` после ставки в Maxposter |
| Чтение ставки с портала | `POST /api/avito_auction_offer_get/` | один лот |
| Пакетное чтение ставок | `POST /api/avito_auction_offers_state/` | таблица при загрузке |

URL портала настраивается в viewer (поле «Портал (API)»), по умолчанию `https://ah.kors-group.com`.

### Авто-пересчёт при обновлении ленты

После «Перезагрузить» (или автообновления) парсер сравнивает каждый оффер с предыдущей версией по полям:

- `updatedAt`
- статус (`status.status`)
- ставка (`bid`)
- цены лота (`minPrice`, `maxBid`, `minAvailableBid`, `minBidStep`, `finishAt`)

Если лот **новый** или **изменился** — автоматически вызывается `POST /api/calculate_car/` (синхронизация + расчёт на портале).  
Лоты без изменений не пересчитываются повторно.

## Файлы

| Файл | Назначение |
|------|------------|
| `script_auction.py` | Загрузка лотов из Maxposter |
| `script_bid.py` | Отправка ставки в Maxposter |
| `server.py` | Локальный HTTP-сервер и API `/api/reload`, `/api/bid` |
| `viewer.html` | UI, расчёт, связь с порталом |
| `launcher.py` | Запуск сервера + браузер |

## Сборка exe

```bat
pip install -r requirements-build.txt
build_exe.bat
```

## Связанный код портала

- `portal/apps/auction_avito/` — модели, синхронизация, чат
- `portal/apps/api/views.py` — `calculate_car`, `avito_auction_bid_set`

## Секреты и дампы

Не коммитить: `.env`, `maxposter_session.json`, `offers_dump*.json`.
