"""
Опрос итогов завершённых лотов Maxposter (решение продавца).

Только bulk API: «Продавец выбирает» (2) → «Вас выбрали» (3) → архив (4) → портал.
Очередь портала и Playwright /view сейчас не используются.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

from maxposter_session import (
    MaxposterAuthError,
    apply_cookies,
    clear_session,
    load_session,
    save_session,
    touch_session,
)
from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

from script_auction import (
    SORT_FIELD,
    SORT_FIELD_OFFER_UPDATED,
    STATUS_GROUP_ARCHIVE,
    STATUS_GROUP_WAITING,
    STATUS_GROUP_WON,
    USER_AGENT,
    fetch_autohub_offers_all,
    _extract_authorization_header,
    _login,
    _select_dealer,
)

LOGIN_URL = "https://app.maxposter.ru/login"
AUCTION_URL = "https://app.maxposter.ru/dealer/auction"
AUCTION_WAITING_URL = "https://app.maxposter.ru/dealer/auction?type=old&tab=2"
AUCTION_WINS_URL = "https://app.maxposter.ru/dealer/auction?type=old&tab=3"
AUCTION_ARCHIVE_URL = "https://app.maxposter.ru/dealer/auction?type=old&tab=4"
VIEW_URL_TPL = "https://app.maxposter.ru/dealer/auction/{lot_offer_id}/view"

EMAIL_ENV = "MAXPOSTER_EMAIL"
PASSWORD_ENV = "MAXPOSTER_PASSWORD"
DEALER_ID_ENV = "MAXPOSTER_DEALER_ID"
PORTAL_BASE_ENV = "PORTAL_BASE"
OUTCOME_ITEMS_ENV = "OUTCOME_ITEMS_JSON"
OUTCOME_LIMIT_ENV = "OUTCOME_LIMIT"
OUTCOME_BULK_PAGE_LIMIT_ENV = "OUTCOME_BULK_PAGE_LIMIT"
OUTCOME_WINS_PAGE_LIMIT_ENV = "OUTCOME_WINS_PAGE_LIMIT"
OUTCOME_WINS_MAX_PAGES_ENV = "OUTCOME_WINS_MAX_PAGES"
OUTCOME_ARCHIVE_MAX_PAGES_ENV = "OUTCOME_ARCHIVE_MAX_PAGES"
OUTCOME_WAITING_MAX_PAGES_ENV = "OUTCOME_WAITING_MAX_PAGES"
OUTCOME_SKIP_BULK_WINS_ENV = "OUTCOME_SKIP_BULK_WINS"
OUTCOME_SKIP_BULK_ARCHIVE_ENV = "OUTCOME_SKIP_BULK_ARCHIVE"
OUTCOME_SKIP_BULK_WAITING_ENV = "OUTCOME_SKIP_BULK_WAITING"
OUTCOME_LOG_NAME = "outcome_poll.log"

BULK_PAGE_LIMIT_DEFAULT = 20
WINS_MAX_PAGES_DEFAULT = 2
ARCHIVE_MAX_PAGES_DEFAULT = 2
WAITING_MAX_PAGES_DEFAULT = 2

# status.status из autohub offers/list → outcome_code портала
AUTOHUB_STATUS_TO_OUTCOME: dict[str, str] = {
    "won": "won",
    "winner": "won",
    "seller_chose_you": "won",
    "seller_chose_nothing": "no_selection",
    "seller_chose_other": "lost",
    "seller_chose_another": "lost",
    "chose_other_bidder": "lost",
    "lost": "lost",
    "not_purchased": "not_redeemed",
    "not_redeemed": "not_redeemed",
    "bidder_refused": "we_refused",
    "bidder_refused_other_reason": "we_refused",
    "bidder_refused_price": "we_refused",
    "bidder_refused_other": "we_refused",
    "seller_canceled": "canceled",
    "seller_canceled_archive": "canceled",
    "seller_cancelled": "canceled",
    "canceled": "canceled",
    "cancelled": "canceled",
    "not_taken": "not_taken",
    "not_processed": "not_taken",
    "waiting_seller": "waiting_seller",
    "waiting_for_seller": "waiting_seller",
    "seller_choosing": "waiting_seller",
    "seller_chooses": "waiting_seller",
    "waiting_for_seller_decision": "waiting_seller",
    "seller_decision_pending": "waiting_seller",
    "seller_decision_waiting": "waiting_seller",
}

FINAL_OUTCOME_CODES = frozenset({
    "won",
    "lost",
    "no_selection",
    "not_redeemed",
    "we_refused",
    "not_taken",
    "canceled",
})

INTERESTING_TEXT_RE = re.compile(
    r"аукцион|решени|продавц|выигр|выбран|выбрал|проигра|отмен|"
    r"ждём|ждем|день|побед|никого|покупател|не\s*выкуп|"
    r"не\s*взял|не\s*обработ|доступен\s*другим|отказ|winner|lost",
    re.I,
)

_LOG_LINES: list[str] = []


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def _app_dir() -> str:
    return _env("APP_DIR") or os.path.dirname(os.path.abspath(__file__))


def _log(msg: str) -> None:
    """Пишет в stdout (viewer забирает в «Лог обновлений»). Файл — только опционально."""
    line = str(msg).rstrip()
    print(line, flush=True)
    _LOG_LINES.append(line)
    if _env("OUTCOME_WRITE_FILE") == "1":
        try:
            path = os.path.join(_app_dir(), OUTCOME_LOG_NAME)
            with open(path, "a", encoding="utf-8") as fh:
                from datetime import datetime

                fh.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {line}\n")
        except Exception:
            pass


def _fmt_item(item: dict) -> str:
    car = (item.get("car") or "").strip() or "—"
    return (
        f"lotOfferId={item.get('lotOfferId')} lotId={item.get('lotId')} "
        f"pk={item.get('lotPk')} dealer={item.get('dealerId') or '-'} "
        f"bid={item.get('bid')} prev={item.get('outcomeCode') or '-'} «{car}»"
    )


def _env_required(name: str) -> str:
    val = _env(name)
    if not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


def _portal_base() -> str:
    return _env(PORTAL_BASE_ENV, "https://ah.kors-group.com").rstrip("/")


def _http_json(method: str, url: str, payload: dict | None = None, timeout: int = 60) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"HTTP {exc.code} {url}: {err_body}") from exc


def fetch_outcome_queue(limit: int = 50, dealer_id: str | None = None, lookback_days: int = 30) -> dict:
    qs = f"limit={int(limit)}&lookback_days={int(lookback_days)}"
    if dealer_id:
        qs += f"&dealer_id={urllib.parse.quote(str(dealer_id))}"
    url = f"{_portal_base()}/api/avito_auction_outcome_queue/?{qs}"
    return _http_json("GET", url)


def push_outcome(item: dict, extracted: dict) -> dict:
    url = f"{_portal_base()}/api/avito_auction_outcome_set/"
    payload = {
        "lotOfferId": item.get("lotOfferId"),
        "lotId": item.get("lotId"),
        "dealerId": item.get("dealerId"),
        "title": extracted.get("title") or "",
        "detail": extracted.get("detail") or "",
        "blob": extracted.get("blob") or "",
        "status": extracted.get("status") or "",
        "outcomeCode": extracted.get("outcomeCode") or "",
        "raw": extracted.get("raw") or "",
    }
    offer_payload = item.get("offerPayload")
    if isinstance(offer_payload, dict) and offer_payload.get("lotOfferId"):
        payload["offerPayload"] = offer_payload
    return _http_json("POST", url, payload)


def _build_calc_payload_from_offer(offer: dict, dealer_id: str | None = None) -> dict | None:
    """Тело для /api/calculate_car/ из полного Autohub offer (как worker_loop)."""
    if not isinstance(offer, dict):
        return None
    lot = dict(offer.get("lot") or {})
    lot_offer_id = offer.get("lotOfferId")
    lot_id = lot.get("lotId") or offer.get("lotId")
    if lot_offer_id in (None, "") or lot_id in (None, ""):
        return None
    did = dealer_id if dealer_id not in (None, "") else offer.get("dealerId")
    if did not in (None, ""):
        try:
            lot["dealerId"] = int(did)
        except (TypeError, ValueError):
            lot["dealerId"] = did
    try:
        lot["lotId"] = int(lot_id)
        lot_offer_id = int(lot_offer_id)
    except (TypeError, ValueError):
        return None
    if not lot.get("finishAt") and lot.get("originFinishAt"):
        lot["finishAt"] = lot["originFinishAt"]
    return {
        **offer,
        "lot": lot,
        "lotId": lot["lotId"],
        "lotOfferId": lot_offer_id,
        "dealerId": lot.get("dealerId") if lot.get("dealerId") is not None else did,
        "minPrice": lot.get("minPrice"),
        "minAvailableBid": lot.get("minAvailableBid"),
        "maxAvailableBid": lot.get("maxAvailableBid"),
        "maxBid": lot.get("maxBid"),
        "vehicle": lot.get("vehicle"),
        "autohubVehicle": lot.get("autohubVehicle"),
        "autoteka": lot.get("autoteka"),
        "description": lot.get("description"),
        "sellerPlaceName": lot.get("sellerPlaceName"),
        "finishAt": lot.get("finishAt") or lot.get("originFinishAt"),
        "expiresAt": lot.get("expiresAt"),
        "originFinishAt": lot.get("originFinishAt"),
        "images": lot.get("images") or offer.get("images"),
        "badges": offer.get("badges") or lot.get("badges"),
        "forceRecalc": False,
    }


def push_calculate_if_needed(item: dict, portal: dict) -> dict | None:
    """
    Если портал создал оффер или нет успешного расчёта — POST calculate_car
    с полным offerPayload (статистика / монитор / пересчёт).
    Ошибки расчёта не валят outcome.
    """
    if not (portal.get("offerCreated") or portal.get("needsCalculation")):
        return None
    offer = item.get("offerPayload")
    if not isinstance(offer, dict):
        return None
    calc_payload = _build_calc_payload_from_offer(offer, item.get("dealerId"))
    if not calc_payload:
        return None
    lot_offer_id = calc_payload.get("lotOfferId")
    url = f"{_portal_base()}/api/calculate_car/"
    try:
        data = _http_json("POST", url, calc_payload, timeout=180)
    except Exception as exc:
        print(
            f"CALC_FAIL lotOfferId={lot_offer_id}: {exc}",
            flush=True,
        )
        return {"ok": False, "error": str(exc)}
    answer = data.get("answer") if isinstance(data.get("answer"), dict) else data
    price = None
    if isinstance(answer, dict):
        price = answer.get("estimation_price") or answer.get("buyoutPrice")
    ok = price is not None
    print(
        f"{'CALC_OK' if ok else 'CALC_EMPTY'} lotOfferId={lot_offer_id} "
        f"estimation={price} created={bool(portal.get('offerCreated'))}",
        flush=True,
    )
    return {"ok": ok, "estimation_price": price, "raw": data}


def _bulk_page_limit() -> int:
    for env_name in (OUTCOME_WINS_PAGE_LIMIT_ENV, OUTCOME_BULK_PAGE_LIMIT_ENV):
        raw = _env(env_name, "")
        if raw:
            try:
                return max(1, min(100, int(raw)))
            except (TypeError, ValueError):
                pass
    return BULK_PAGE_LIMIT_DEFAULT


def _wins_page_limit() -> int:
    return _bulk_page_limit()


def _wins_max_pages() -> int:
    try:
        return max(1, min(50, int(_env(OUTCOME_WINS_MAX_PAGES_ENV, str(WINS_MAX_PAGES_DEFAULT)) or WINS_MAX_PAGES_DEFAULT)))
    except (TypeError, ValueError):
        return WINS_MAX_PAGES_DEFAULT


def _archive_max_pages() -> int:
    """Архив: не больше 2 страниц (свежие итоги)."""
    try:
        return max(1, min(2, int(_env(OUTCOME_ARCHIVE_MAX_PAGES_ENV, str(ARCHIVE_MAX_PAGES_DEFAULT)) or ARCHIVE_MAX_PAGES_DEFAULT)))
    except (TypeError, ValueError):
        return ARCHIVE_MAX_PAGES_DEFAULT


def _waiting_max_pages() -> int:
    try:
        return max(1, min(100, int(_env(OUTCOME_WAITING_MAX_PAGES_ENV, str(WAITING_MAX_PAGES_DEFAULT)) or WAITING_MAX_PAGES_DEFAULT)))
    except (TypeError, ValueError):
        return WAITING_MAX_PAGES_DEFAULT


def _skip_bulk_wins() -> bool:
    return _env(OUTCOME_SKIP_BULK_WINS_ENV, "").lower() in ("1", "true", "yes")


def _skip_bulk_archive() -> bool:
    return _env(OUTCOME_SKIP_BULK_ARCHIVE_ENV, "").lower() in ("1", "true", "yes")


def _skip_bulk_waiting() -> bool:
    return _env(OUTCOME_SKIP_BULK_WAITING_ENV, "").lower() in ("1", "true", "yes")


def _map_autohub_status_to_outcome(status_code: str, status_name: str = "") -> str | None:
    code = (status_code or "").strip().lower()
    if not code:
        return None
    if code in AUTOHUB_STATUS_TO_OUTCOME:
        return AUTOHUB_STATUS_TO_OUTCOME[code]
    if code.startswith("bidder_refused"):
        return "we_refused"
    if code.startswith("seller_canceled") or code.startswith("seller_cancelled"):
        return "canceled"
    if code.startswith("waiting") or "seller_choos" in code or "seller_decision" in code:
        return "waiting_seller"
    if "chose_nothing" in code:
        return "no_selection"
    if "chose_other" in code or code.endswith("_lost"):
        return "lost"
    if code in ("won", "winner") or code.endswith("_won"):
        return "won"

    name = (status_name or "").lower()
    if "никого не выбрал" in name:
        return "no_selection"
    if "не выкуплен" in name:
        return "not_redeemed"
    if "наш отказ" in name or name.startswith("отказ"):
        return "we_refused"
    if "отменен" in name or "отменён" in name:
        return "canceled"
    if "жд" in name and "решени" in name:
        return "waiting_seller"
    if "ожидает" in name and "решени" in name:
        return "waiting_seller"
    if "продавец выбирает" in name or "выбирает покуп" in name:
        return "waiting_seller"
    if "не взял" in name or "не обработ" in name:
        return "not_taken"
    if "выбрал друг" in name or "проигра" in name:
        return "lost"
    if "вас выбрали" in name or "выбран" in name:
        return "won"
    return None


def _offer_car_label(offer: dict) -> str:
    lot = offer.get("lot") or {}
    vehicle = lot.get("vehicle") or {}
    brand = (vehicle.get("brand") or {}).get("name") or ""
    model = (vehicle.get("model") or {}).get("name") or ""
    year = vehicle.get("year")
    if isinstance(year, dict):
        year = year.get("name") or year.get("id") or ""
    return " ".join(str(x).strip() for x in (brand, model, year) if str(x).strip()).strip()


def _portal_item_from_api_offer(offer: dict, dealer_id: str | None = None) -> dict:
    lot = offer.get("lot") or {}
    return {
        "lotOfferId": offer.get("lotOfferId"),
        "lotId": lot.get("lotId"),
        "dealerId": offer.get("dealerId") or dealer_id,
        "bid": offer.get("bid"),
        "car": _offer_car_label(offer),
        "offerPayload": offer,
    }


def _extracted_from_api_offer(
    offer: dict,
    *,
    status_group: int,
    outcome_code: str | None = None,
    include_waiting: bool = False,
) -> dict | None:
    status = offer.get("status") or {}
    if isinstance(status, dict):
        status_code = str(status.get("status") or "")
        status_name = str(status.get("name") or "")
    else:
        status_code = str(status or "")
        status_name = ""
    code = outcome_code or _map_autohub_status_to_outcome(status_code, status_name)
    if not code:
        return None
    if code == "waiting_seller" and not include_waiting:
        return None
    lot_offer_id = offer.get("lotOfferId")
    title = status_name or "Аукцион завершен"
    detail = status_name or title
    return {
        "title": title,
        "detail": detail,
        "blob": f"autohub offers/list statusGroup={status_group}",
        "status": status_code,
        "outcomeCode": code,
        "raw": json.dumps(
            {
                "source": "autohub_offers_list",
                "statusGroup": status_group,
                "lotOfferId": lot_offer_id,
                "status": status,
                "isWinner": offer.get("isWinner"),
                "isFinished": offer.get("isFinished"),
            },
            ensure_ascii=False,
        )[:8000],
    }


def _extracted_won_from_api_offer(offer: dict) -> dict:
    extracted = _extracted_from_api_offer(
        offer, status_group=STATUS_GROUP_WON, outcome_code="won"
    )
    if extracted:
        if not extracted.get("detail"):
            extracted["detail"] = "Вас выбрали"
        return extracted
    status = offer.get("status") or {}
    if isinstance(status, dict):
        status_code = str(status.get("status") or "won")
        status_name = str(status.get("name") or "Вас выбрали")
    else:
        status_code = str(status or "won")
        status_name = "Вас выбрали"
    lot_offer_id = offer.get("lotOfferId")
    return {
        "title": status_name or "Аукцион завершен",
        "detail": "Вас выбрали",
        "blob": "autohub offers/list statusGroup=3",
        "status": status_code,
        "outcomeCode": "won",
        "raw": json.dumps(
            {
                "source": "autohub_offers_list",
                "statusGroup": STATUS_GROUP_WON,
                "lotOfferId": lot_offer_id,
                "status": status,
            },
            ensure_ascii=False,
        )[:8000],
    }


def _warm_waiting_headers(page, session_headers: dict | None = None) -> dict:
    headers = dict(session_headers or {})
    try:
        page.goto(AUCTION_WAITING_URL, wait_until="domcontentloaded", timeout=45_000)
        page.wait_for_timeout(400)
        headers.update(_extract_authorization_header(page))
    except Exception as exc:
        print(f"Прогрев waiting tab: {exc}")
    return headers


def _warm_archive_headers(page, session_headers: dict | None = None) -> dict:
    headers = dict(session_headers or {})
    try:
        page.goto(AUCTION_ARCHIVE_URL, wait_until="domcontentloaded", timeout=45_000)
        page.wait_for_timeout(400)
        headers.update(_extract_authorization_header(page))
    except Exception as exc:
        print(f"Прогрев archive tab: {exc}")
    return headers


def _warm_wins_headers(page, session_headers: dict | None = None) -> dict:
    headers = dict(session_headers or {})
    try:
        page.goto(AUCTION_WINS_URL, wait_until="domcontentloaded", timeout=45_000)
        page.wait_for_timeout(400)
        headers.update(_extract_authorization_header(page))
    except Exception as exc:
        print(f"Прогрев wins tab: {exc}")
    return headers


def _warm_headers(page, session_headers: dict | None = None) -> dict:
    headers = dict(session_headers or {})
    try:
        page.goto(AUCTION_URL, wait_until="domcontentloaded", timeout=45_000)
        page.wait_for_timeout(400)
        headers.update(_extract_authorization_header(page))
    except Exception as exc:
        print(f"Прогрев outcome: {exc}")
    return headers


def _ensure_session(page, ctx, email: str, password: str, dealer_id: str, script_dir: str) -> dict:
    if dealer_id:
        cached = load_session(script_dir, email, dealer_id)
        if cached:
            print(f"SESSION_CACHE_TRY (outcome) возраст={cached.get('_age_min', 0):.0f} мин")
            apply_cookies(ctx, page, cached["cookies"])
            touch_session(script_dir, email, dealer_id)
            print("SESSION_CACHE_HIT (outcome)")
            return _warm_headers(page, cached.get("session_headers"))

    print("SESSION_FULL_LOGIN (outcome)")
    _login(page, ctx, email, password)
    if dealer_id:
        _select_dealer(page, ctx, dealer_id)
    headers = _warm_headers(page)
    if dealer_id:
        save_session(script_dir, email, dealer_id, ctx.cookies(), headers)
    return headers


def _walk_strings(obj, out: list[str], depth: int = 0):
    if depth > 8:
        return
    if isinstance(obj, str):
        s = obj.strip()
        if len(s) >= 8 and INTERESTING_TEXT_RE.search(s):
            out.append(s)
    elif isinstance(obj, dict):
        for v in obj.values():
            _walk_strings(v, out, depth + 1)
    elif isinstance(obj, list):
        for v in obj[:200]:
            _walk_strings(v, out, depth + 1)


def _pick_title_detail(texts: list[str]) -> tuple[str, str]:
    title = ""
    detail = ""
    for t in texts:
        low = t.lower()
        if not title and ("аукцион заверш" in low or "аукцион отмен" in low):
            title = t
            continue
        if not detail and (
            "решени" in low or "выигр" in low or "выбран" in low or "выбрал" in low
            or "проигра" in low or "ждём" in low or "ждем" in low or "никого" in low
        ):
            detail = t
            continue
    if not title and texts:
        title = texts[0]
    if not detail and len(texts) > 1:
        detail = texts[1]
    return title, detail


def _extract_status_from_json(payload: dict) -> str:
    if not isinstance(payload, dict):
        return ""
    for key in ("offer", "lotOffer", "data"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            st = nested.get("status")
            if isinstance(st, dict) and st.get("status"):
                return str(st.get("status"))
            if isinstance(st, str):
                return st
    st = payload.get("status")
    if isinstance(st, dict) and st.get("status"):
        return str(st.get("status"))
    if isinstance(st, str):
        return st
    return ""


def extract_outcome_from_view(page, lot_offer_id: int | str) -> dict:
    """Открыть страницу лота, собрать тексты из API + DOM (быстро, без networkidle)."""
    url = VIEW_URL_TPL.format(lot_offer_id=lot_offer_id)
    captured: list[dict] = []

    def on_response(resp):
        try:
            req_url = resp.url or ""
            if "mp-gateway.maxposter.ru" not in req_url and "maxposter" not in req_url:
                return
            ctype = (resp.headers or {}).get("content-type", "")
            if "json" not in ctype:
                return
            if resp.status != 200:
                return
            data = resp.json()
            if isinstance(data, (dict, list)):
                captured.append({"url": req_url, "data": data})
        except Exception:
            pass

    page.on("response", on_response)
    try:
        # networkidle на Maxposter часто висит ~1–1.5 мин — не используем.
        page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        try:
            page.wait_for_function(
                """() => /аукцион|продавц|решени|выигр|выбран|выбрал|никого|не\\s*выкуп|не\\s*взял|не\\s*обработ|доступен|отказ|ждём|ждем/i.test(
                    (document.body && document.body.innerText) || ''
                )""",
                timeout=12_000,
            )
        except PWTimeout:
            page.wait_for_timeout(1500)
    finally:
        try:
            page.remove_listener("response", on_response)
        except Exception:
            pass

    page.wait_for_timeout(600)

    api_texts: list[str] = []
    status_code = ""
    for item in captured:
        data = item.get("data")
        if isinstance(data, dict) and not status_code:
            status_code = _extract_status_from_json(data)
        _walk_strings(data, api_texts)

    # DOM: собираем видимые строки из основного контента.
    dom_texts: list[str] = []
    try:
        dom_texts = page.evaluate(
            """() => {
              const root = document.querySelector('main') || document.body;
              const nodes = root.querySelectorAll('h1,h2,h3,h4,p,div,span,li,section,article');
              const out = [];
              const seen = new Set();
              const re = /аукцион|решени|продавц|выигр|выбран|выбрал|проигра|отмен|ждём|ждем|день|побед|никого|покупател|не выкуп|не взял|не обработ|доступен другим|отказ/i;
              for (const el of nodes) {
                if (!el) continue;
                // Берём листья и короткие блоки; длинные контейнеры режем по строкам ниже.
                const raw = (el.innerText || '').replace(/\\s+/g, ' ').trim();
                if (!raw) continue;
                const chunks = raw.length > 280 ? raw.split(/(?<=[.!?])\\s+|\\n+/).map(s => s.trim()) : [raw];
                for (const t of chunks) {
                  if (t.length < 6 || t.length > 320) continue;
                  if (!re.test(t)) continue;
                  if (seen.has(t)) continue;
                  seen.add(t);
                  out.push(t);
                  if (out.length >= 60) return out;
                }
              }
              return out;
            }"""
        ) or []
    except Exception as exc:
        print(f"DOM extract error lotOfferId={lot_offer_id}: {exc}")

    # Fallback: весь body.innerText построчно — если UI сменился и селекторы пустые.
    if not dom_texts and not api_texts:
        try:
            body_lines = page.evaluate(
                """() => {
                  const t = (document.body && document.body.innerText) || '';
                  return t.split(/\\n+/).map(s => s.replace(/\\s+/g, ' ').trim()).filter(Boolean);
                }"""
            ) or []
            for t in body_lines:
                if len(t) < 6 or len(t) > 320:
                    continue
                if INTERESTING_TEXT_RE.search(t):
                    dom_texts.append(t)
                if len(dom_texts) >= 40:
                    break
            if not dom_texts and body_lines:
                # Последний шанс — склеить кусок body как blob для классификатора.
                blob_fallback = " ".join(body_lines)[:4000]
                if blob_fallback.strip():
                    dom_texts.append(blob_fallback[:500])
            print(
                f"OUTCOME_FALLBACK_BODY lotOfferId={lot_offer_id} "
                f"lines={len(body_lines)} matched={len(dom_texts)}",
                flush=True,
            )
        except Exception as exc:
            print(f"BODY fallback error lotOfferId={lot_offer_id}: {exc}")

    # Повторная короткая пауза, если всё ещё пусто (медленный SPA).
    if not dom_texts and not api_texts:
        try:
            page.wait_for_timeout(2000)
            more = page.evaluate(
                """() => {
                  const t = (document.body && document.body.innerText) || '';
                  return /аукцион|продавц|решени|выигр|выбран|не\\s*выкуп|не\\s*взял|ждём|ждем/i.test(t)
                    ? t.slice(0, 2500) : '';
                }"""
            ) or ""
            if more.strip():
                dom_texts.append(more.strip()[:500])
                print(f"OUTCOME_RETRY_TEXT lotOfferId={lot_offer_id} len={len(more)}", flush=True)
        except Exception:
            pass

    texts = []
    seen = set()
    for t in list(dom_texts) + list(api_texts):
        t = re.sub(r"\s+", " ", str(t)).strip()
        if not t or t in seen:
            continue
        seen.add(t)
        texts.append(t)

    title, detail = _pick_title_detail(texts)
    blob = " | ".join(texts[:20])
    raw = json.dumps(
        {
            "url": url,
            "status": status_code,
            "texts": texts[:30],
            "apiUrls": [c.get("url") for c in captured][:20],
            "extractEmpty": not bool(texts),
        },
        ensure_ascii=False,
    )
    return {
        "title": title,
        "detail": detail,
        "blob": blob,
        "status": status_code,
        "raw": raw,
        "texts": texts,
        "extractEmpty": not bool(texts),
    }


def process_item(page, item: dict, *, idx: int = 1, total: int = 1) -> dict:
    """Опрос одного лота на уже открытой сессии Maxposter."""
    lot_offer_id = item.get("lotOfferId")
    if not lot_offer_id:
        return {"ok": False, "lotOfferId": None, "error": "no lotOfferId", "car": item.get("car") or ""}

    print(f"OUTCOME_CHECK[{idx}/{total}] {_fmt_item(item)}", flush=True)
    extracted = extract_outcome_from_view(page, lot_offer_id)
    title = (extracted.get("title") or "").strip()
    detail = (extracted.get("detail") or "").strip()
    print(
        f"OUTCOME_EXTRACT[{idx}] lotOfferId={lot_offer_id} "
        f"title={title!r} detail={detail!r} texts={len(extracted.get('texts') or [])}",
        flush=True,
    )
    portal = push_outcome(item, extracted)
    calc = push_calculate_if_needed(item, portal)
    code = portal.get("outcomeCode") or "?"
    status = portal.get("statusCode") or "?"
    prev = portal.get("prevOutcome") or item.get("outcomeCode") or "-"
    chat_info = portal.get("chat") or {}
    if chat_info.get("sent"):
        chat_flag = "chat=ok"
    else:
        chat_flag = f"chat={chat_info.get('reason') or 'skip'}"
    row = {
        "ok": True,
        "lotOfferId": lot_offer_id,
        "lotId": item.get("lotId") or portal.get("lotId"),
        "lotPk": item.get("lotPk"),
        "car": item.get("car") or "",
        "bid": item.get("bid"),
        "offerCreated": bool(portal.get("offerCreated")),
        "calculation": calc,
        "extracted": {
            "title": title,
            "detail": detail,
            "status": extracted.get("status"),
            "texts": (extracted.get("texts") or [])[:8],
        },
        "portal": {
            "outcomeCode": code,
            "outcomeTitle": portal.get("outcomeTitle"),
            "outcomeDetail": portal.get("outcomeDetail"),
            "statusCode": status,
            "prevOutcome": prev,
            "becameWon": portal.get("becameWon"),
            "email": portal.get("email"),
            "chat": chat_info,
            "offerCreated": bool(portal.get("offerCreated")),
            "needsCalculation": bool(portal.get("needsCalculation")),
        },
        "msg": (
            f"лот {item.get('lotId')} / offer {lot_offer_id}: "
            f"{prev} → {code} ({title}; {detail}) [{chat_flag}]"
        ),
    }
    print(
        f"OUTCOME_OK[{idx}] lotOfferId={lot_offer_id} lotId={item.get('lotId')} "
        f"«{item.get('car') or '—'}» {prev} → {code}/{status} "
        f"becameWon={bool(portal.get('becameWon'))} {chat_flag}",
        flush=True,
    )
    return row


def _push_bulk_row(
    item: dict,
    extracted: dict,
    *,
    source: str,
    idx: int = 0,
    total: int = 0,
) -> dict:
    lot_offer_id = item.get("lotOfferId")
    tag = f"[{idx}/{total}] " if total else ""
    try:
        portal = push_outcome(item, extracted)
    except RuntimeError as exc:
        err = str(exc)
        if "404" in err and "offer not found" in err.lower():
            return {
                "ok": False,
                "skipped": True,
                "source": source,
                "lotOfferId": lot_offer_id,
                "lotId": item.get("lotId"),
                "car": item.get("car") or "",
                "error": "offer not on portal",
                "msg": f"{tag}{source} skip offer {lot_offer_id}: нет на портале",
            }
        raise

    calc = push_calculate_if_needed(item, portal)

    code = portal.get("outcomeCode") or extracted.get("outcomeCode") or "?"
    prev = portal.get("prevOutcome") or item.get("outcomeCode") or "-"
    chat_info = portal.get("chat") or {}
    row = {
        "ok": True,
        "source": source,
        "lotOfferId": lot_offer_id,
        "lotId": item.get("lotId") or portal.get("lotId"),
        "lotPk": item.get("lotPk"),
        "car": item.get("car") or "",
        "bid": item.get("bid"),
        "offerCreated": bool(portal.get("offerCreated")),
        "needsCalculation": bool(portal.get("needsCalculation")),
        "calculation": calc,
        "extracted": {
            "status": extracted.get("status"),
            "outcomeCode": extracted.get("outcomeCode"),
            "title": extracted.get("title"),
            "detail": extracted.get("detail"),
        },
        "portal": {
            "outcomeCode": code,
            "outcomeTitle": portal.get("outcomeTitle"),
            "outcomeDetail": portal.get("outcomeDetail"),
            "statusCode": portal.get("statusCode") or "?",
            "prevOutcome": prev,
            "becameWon": portal.get("becameWon"),
            "email": portal.get("email"),
            "chat": chat_info,
            "offerCreated": bool(portal.get("offerCreated")),
            "needsCalculation": bool(portal.get("needsCalculation")),
        },
        "msg": (
            f"{tag}{source} lot {item.get('lotId')} / offer {lot_offer_id}: "
            f"{prev} → {code} ({extracted.get('title') or ''})"
            + (" [new]" if portal.get("offerCreated") else "")
        ),
    }
    return row


def _push_won_row(item: dict, extracted: dict, *, idx: int = 0, total: int = 0) -> dict:
    return _push_bulk_row(item, extracted, source="bulk_wins", idx=idx, total=total)


def sync_wins_bulk(
    page,
    ctx,
    *,
    session_headers: dict | None = None,
    dealer_id: str | None = None,
    queue_items: list[dict] | None = None,
) -> dict:
    """
    Список «Вас выбрали» через autohub API → outcome=won на портал.
    Возвращает wonLotOfferIds — их можно убрать из Playwright-очереди.
    """
    headers = _warm_wins_headers(page, session_headers)
    offers = fetch_autohub_offers_all(
        ctx,
        page,
        status_group=STATUS_GROUP_WON,
        extra_headers=headers,
        limit=_bulk_page_limit(),
        max_pages=_wins_max_pages(),
        sort_field=SORT_FIELD_OFFER_UPDATED,
    )
    queue_ids = {
        int(it["lotOfferId"])
        for it in (queue_items or [])
        if it.get("lotOfferId") is not None
    }
    results: list[dict] = []
    won_ids: set[int] = set()
    synced_ids: set[int] = set()
    became_won = 0
    fail = 0
    skipped = 0

    # Все «Вас выбрали» с API — не только пересечение с очередью (могли не попасть в queue).
    targets = offers
    if queue_ids:
        in_queue = sum(
            1 for o in offers
            if o.get("lotOfferId") is not None and int(o.get("lotOfferId")) in queue_ids
        )
        print(
            f"WINS_BULK queue overlap: {in_queue}/{len(offers)} API wins in portal queue "
            f"(push all API wins)",
            flush=True,
        )

    total = len(targets)
    print(f"WINS_BULK start offers={len(offers)} push={total}", flush=True)

    for idx, offer in enumerate(targets, 1):
        lot_offer_id = offer.get("lotOfferId")
        if lot_offer_id is None:
            continue
        try:
            lot_offer_id = int(lot_offer_id)
        except (TypeError, ValueError):
            continue
        won_ids.add(lot_offer_id)

        item = _portal_item_from_api_offer(offer, dealer_id)
        extracted = _extracted_won_from_api_offer(offer)
        car = item.get("car") or "—"
        print(
            f"WINS_BULK[{idx}/{total}] lotOfferId={lot_offer_id} "
            f"lotId={item.get('lotId')} «{car}»",
            flush=True,
        )
        try:
            row = _push_won_row(item, extracted, idx=idx, total=total)
            results.append(row)
            if row.get("skipped"):
                skipped += 1
                print(row.get("msg") or "WINS_BULK skip", flush=True)
                continue
            if not row.get("ok"):
                fail += 1
                continue
            synced_ids.add(lot_offer_id)
            if (row.get("portal") or {}).get("becameWon"):
                became_won += 1
            print(row.get("msg") or "WINS_BULK ok", flush=True)
        except Exception as exc:
            fail += 1
            err = str(exc)[:300]
            results.append({
                "ok": False,
                "source": "bulk_wins",
                "lotOfferId": lot_offer_id,
                "lotId": item.get("lotId"),
                "car": car,
                "error": err,
                "msg": f"WINS_BULK[{idx}/{total}] error offer {lot_offer_id}: {err}",
            })
            print(results[-1]["msg"], flush=True)

    summary = {
        "apiOffers": len(offers),
        "pushed": total,
        "ok": sum(1 for r in results if r.get("ok")),
        "fail": fail,
        "skipped": skipped,
        "becameWon": became_won,
        "wonLotOfferIds": sorted(won_ids),
        "syncedLotOfferIds": sorted(synced_ids),
    }
    print(
        f"WINS_BULK done api={summary['apiOffers']} ok={summary['ok']} "
        f"fail={fail} skip={skipped} becameWon={became_won}",
        flush=True,
    )
    return {
        "ok": fail == 0,
        "results": results,
        "summary": summary,
    }


def sync_waiting_bulk(
    page,
    ctx,
    *,
    session_headers: dict | None = None,
    dealer_id: str | None = None,
    queue_items: list[dict] | None = None,
) -> dict:
    """
    Список «Продавец выбирает» (statusGroup=2) → waiting_seller на портал.
    Пушим все офферы с API, не только пересечение с очередью.
    """
    headers = _warm_waiting_headers(page, session_headers)
    offers = fetch_autohub_offers_all(
        ctx,
        page,
        status_group=STATUS_GROUP_WAITING,
        extra_headers=headers,
        limit=_bulk_page_limit(),
        max_pages=_waiting_max_pages(),
        sort_field=SORT_FIELD,
    )
    queue_ids = {
        int(it["lotOfferId"])
        for it in (queue_items or [])
        if it.get("lotOfferId") is not None
    }
    results: list[dict] = []
    waiting_ids: set[int] = set()
    synced_ids: set[int] = set()
    fail = 0
    skipped = 0
    unmapped = 0

    if queue_ids:
        in_queue = sum(
            1 for o in offers
            if o.get("lotOfferId") is not None and int(o.get("lotOfferId")) in queue_ids
        )
        print(
            f"WAITING_BULK queue overlap: {in_queue}/{len(offers)} API waiting in portal queue "
            f"(push all mappable API offers)",
            flush=True,
        )

    total = len(offers)
    print(f"WAITING_BULK start offers={len(offers)} push={total}", flush=True)

    for idx, offer in enumerate(offers, 1):
        lot_offer_id = offer.get("lotOfferId")
        if lot_offer_id is None:
            continue
        try:
            lot_offer_id = int(lot_offer_id)
        except (TypeError, ValueError):
            continue
        waiting_ids.add(lot_offer_id)

        extracted = _extracted_from_api_offer(
            offer,
            status_group=STATUS_GROUP_WAITING,
            include_waiting=True,
        )
        if not extracted:
            # Вкладка «Продавец выбирает» — даже без известного status.status
            # считаем waiting_seller (как statusGroup=3 всегда won).
            extracted = _extracted_from_api_offer(
                offer,
                status_group=STATUS_GROUP_WAITING,
                outcome_code="waiting_seller",
                include_waiting=True,
            )
        if not extracted:
            unmapped += 1
            status = offer.get("status") or {}
            st = status.get("status") if isinstance(status, dict) else status
            print(
                f"WAITING_BULK[{idx}/{total}] skip lotOfferId={lot_offer_id} "
                f"unmapped status={st!r}",
                flush=True,
            )
            continue

        item = _portal_item_from_api_offer(offer, dealer_id)
        car = item.get("car") or "—"
        code = extracted.get("outcomeCode") or "?"
        print(
            f"WAITING_BULK[{idx}/{total}] lotOfferId={lot_offer_id} "
            f"lotId={item.get('lotId')} status={extracted.get('status')} → {code} «{car}»",
            flush=True,
        )
        try:
            row = _push_bulk_row(
                item,
                extracted,
                source="bulk_waiting",
                idx=idx,
                total=total,
            )
            results.append(row)
            if row.get("skipped"):
                skipped += 1
                print(row.get("msg") or "WAITING_BULK skip", flush=True)
                continue
            if not row.get("ok"):
                fail += 1
                continue
            synced_ids.add(lot_offer_id)
            print(row.get("msg") or "WAITING_BULK ok", flush=True)
        except Exception as exc:
            fail += 1
            err = str(exc)[:300]
            results.append({
                "ok": False,
                "source": "bulk_waiting",
                "lotOfferId": lot_offer_id,
                "lotId": item.get("lotId"),
                "car": car,
                "error": err,
                "msg": f"WAITING_BULK[{idx}/{total}] error offer {lot_offer_id}: {err}",
            })
            print(results[-1]["msg"], flush=True)

    summary = {
        "apiOffers": len(offers),
        "pushed": total - unmapped,
        "ok": sum(1 for r in results if r.get("ok")),
        "fail": fail,
        "skipped": skipped,
        "unmapped": unmapped,
        "waitingLotOfferIds": sorted(waiting_ids),
        "syncedLotOfferIds": sorted(synced_ids),
    }
    print(
        f"WAITING_BULK done api={summary['apiOffers']} ok={summary['ok']} "
        f"fail={fail} skip={skipped} unmapped={unmapped}",
        flush=True,
    )
    return {
        "ok": fail == 0,
        "results": results,
        "summary": summary,
    }


def sync_archive_bulk(
    page,
    ctx,
    *,
    session_headers: dict | None = None,
    dealer_id: str | None = None,
    queue_items: list[dict] | None = None,
) -> dict:
    """
    Список «Архив» через autohub API (statusGroup=4) → финальные итоги на портал.
    """
    headers = _warm_archive_headers(page, session_headers)
    offers = fetch_autohub_offers_all(
        ctx,
        page,
        status_group=STATUS_GROUP_ARCHIVE,
        extra_headers=headers,
        limit=_bulk_page_limit(),
        max_pages=_archive_max_pages(),
        sort_field=SORT_FIELD,
    )
    queue_ids = {
        int(it["lotOfferId"])
        for it in (queue_items or [])
        if it.get("lotOfferId") is not None
    }
    results: list[dict] = []
    archive_ids: set[int] = set()
    synced_ids: set[int] = set()
    fail = 0
    skipped = 0
    unmapped = 0

    if queue_ids:
        in_queue = sum(
            1 for o in offers
            if o.get("lotOfferId") is not None and int(o.get("lotOfferId")) in queue_ids
        )
        print(
            f"ARCHIVE_BULK queue overlap: {in_queue}/{len(offers)} API archive in portal queue "
            f"(push mappable finals)",
            flush=True,
        )

    targets = offers
    total = len(targets)
    print(f"ARCHIVE_BULK start offers={len(offers)} push={total}", flush=True)

    for idx, offer in enumerate(targets, 1):
        lot_offer_id = offer.get("lotOfferId")
        if lot_offer_id is None:
            continue
        try:
            lot_offer_id = int(lot_offer_id)
        except (TypeError, ValueError):
            continue
        archive_ids.add(lot_offer_id)

        extracted = _extracted_from_api_offer(offer, status_group=STATUS_GROUP_ARCHIVE)
        if not extracted:
            unmapped += 1
            status = offer.get("status") or {}
            st = status.get("status") if isinstance(status, dict) else status
            print(
                f"ARCHIVE_BULK[{idx}/{total}] skip lotOfferId={lot_offer_id} "
                f"unmapped status={st!r}",
                flush=True,
            )
            continue

        item = _portal_item_from_api_offer(offer, dealer_id)
        car = item.get("car") or "—"
        code = extracted.get("outcomeCode") or "?"
        print(
            f"ARCHIVE_BULK[{idx}/{total}] lotOfferId={lot_offer_id} "
            f"lotId={item.get('lotId')} status={extracted.get('status')} → {code} «{car}»",
            flush=True,
        )
        try:
            row = _push_bulk_row(
                item,
                extracted,
                source="bulk_archive",
                idx=idx,
                total=total,
            )
            results.append(row)
            if row.get("skipped"):
                skipped += 1
                print(row.get("msg") or "ARCHIVE_BULK skip", flush=True)
                continue
            if not row.get("ok"):
                fail += 1
                continue
            portal_code = (row.get("portal") or {}).get("outcomeCode") or code
            if portal_code in FINAL_OUTCOME_CODES:
                synced_ids.add(lot_offer_id)
            print(row.get("msg") or "ARCHIVE_BULK ok", flush=True)
        except Exception as exc:
            fail += 1
            err = str(exc)[:300]
            results.append({
                "ok": False,
                "source": "bulk_archive",
                "lotOfferId": lot_offer_id,
                "lotId": item.get("lotId"),
                "car": car,
                "error": err,
                "msg": f"ARCHIVE_BULK[{idx}/{total}] error offer {lot_offer_id}: {err}",
            })
            print(results[-1]["msg"], flush=True)

    summary = {
        "apiOffers": len(offers),
        "pushed": total - unmapped,
        "ok": sum(1 for r in results if r.get("ok")),
        "fail": fail,
        "skipped": skipped,
        "unmapped": unmapped,
        "archiveLotOfferIds": sorted(archive_ids),
        "syncedLotOfferIds": sorted(synced_ids),
    }
    print(
        f"ARCHIVE_BULK done api={summary['apiOffers']} ok={summary['ok']} "
        f"fail={fail} skip={skipped} unmapped={unmapped}",
        flush=True,
    )
    return {
        "ok": fail == 0,
        "results": results,
        "summary": summary,
    }


def _merged_synced_ids(*bulks: dict | None, finals_only: bool = True) -> list[int]:
    """lotOfferId успешно записанных в портал. finals_only — только финальные итоги (для пропуска Playwright)."""
    out: set[int] = set()
    for bulk in bulks:
        if not bulk:
            continue
        for row in bulk.get("results") or []:
            if not row.get("ok") or row.get("skipped"):
                continue
            code = (row.get("portal") or {}).get("outcomeCode") or ""
            if finals_only and code not in FINAL_OUTCOME_CODES:
                continue
            oid = row.get("lotOfferId")
            if oid is not None:
                try:
                    out.add(int(oid))
                except (TypeError, ValueError):
                    pass
        if not finals_only:
            for oid in (bulk.get("summary") or {}).get("syncedLotOfferIds") or []:
                try:
                    out.add(int(oid))
                except (TypeError, ValueError):
                    pass
    return sorted(out)


def sync_all_bulk(
    page,
    ctx,
    *,
    session_headers: dict | None = None,
    dealer_id: str | None = None,
    queue_items: list[dict] | None = None,
) -> dict:
    """Bulk: вас выбрали (3) → продавец выбирает (2) → архив (4) → портал.

    Wins первыми (важнее). Ошибка/429 на одной вкладке не отменяет остальные.
    """
    waiting_bulk: dict | None = None
    wins_bulk: dict | None = None
    archive_bulk: dict | None = None
    headers = dict(session_headers or {})

    def _safe(label: str, fn):
        try:
            return fn()
        except MaxposterAuthError:
            raise
        except Exception as exc:
            err = str(exc)[:500]
            print(f"{label}_ERR: {err}", flush=True)
            return {
                "ok": False,
                "error": err,
                "results": [],
                "summary": {
                    "apiOffers": 0,
                    "ok": 0,
                    "fail": 1,
                    "syncedLotOfferIds": [],
                },
            }

    if not _skip_bulk_wins():
        wins_bulk = _safe(
            "WINS_BULK",
            lambda: sync_wins_bulk(
                page,
                ctx,
                session_headers=headers,
                dealer_id=dealer_id,
                queue_items=queue_items,
            ),
        )
        headers = (wins_bulk or {}).get("sessionHeaders") or headers

    if not _skip_bulk_waiting():
        waiting_bulk = _safe(
            "WAITING_BULK",
            lambda: sync_waiting_bulk(
                page,
                ctx,
                session_headers=headers,
                dealer_id=dealer_id,
                queue_items=queue_items,
            ),
        )
        headers = (waiting_bulk or {}).get("sessionHeaders") or headers

    if not _skip_bulk_archive():
        archive_bulk = _safe(
            "ARCHIVE_BULK",
            lambda: sync_archive_bulk(
                page,
                ctx,
                session_headers=headers,
                dealer_id=dealer_id,
                queue_items=queue_items,
            ),
        )

    results: list[dict] = []
    if waiting_bulk:
        results.extend(waiting_bulk.get("results") or [])
    if wins_bulk:
        results.extend(wins_bulk.get("results") or [])
    if archive_bulk:
        results.extend(archive_bulk.get("results") or [])

    synced = _merged_synced_ids(waiting_bulk, wins_bulk, archive_bulk, finals_only=True)
    all_pushed = _merged_synced_ids(waiting_bulk, wins_bulk, archive_bulk, finals_only=False)
    ws_ = (waiting_bulk or {}).get("summary") or {}
    ws = (wins_bulk or {}).get("summary") or {}
    as_ = (archive_bulk or {}).get("summary") or {}
    summary = {
        "waitingApiOffers": ws_.get("apiOffers", 0),
        "winsApiOffers": ws.get("apiOffers", 0),
        "archiveApiOffers": as_.get("apiOffers", 0),
        "ok": sum(1 for r in results if r.get("ok")),
        "fail": sum(1 for r in results if not r.get("ok") and not r.get("skipped")),
        "skipped": sum(1 for r in results if r.get("skipped")),
        "becameWon": ws.get("becameWon", 0),
        "waitingLotOfferIds": ws_.get("waitingLotOfferIds") or [],
        "wonLotOfferIds": ws.get("wonLotOfferIds") or [],
        "archiveLotOfferIds": as_.get("archiveLotOfferIds") or [],
        "syncedLotOfferIds": synced,
        "pushedLotOfferIds": all_pushed,
    }
    ok = True
    # Частичный успех = ok. Жёсткий fail только если ни одна вкладка не дала данных и есть ошибки.
    has_data = bool(results) or any(
        ((b or {}).get("summary") or {}).get("apiOffers", 0) > 0
        for b in (waiting_bulk, wins_bulk, archive_bulk)
    )
    has_errors = any((b or {}).get("error") for b in (waiting_bulk, wins_bulk, archive_bulk))
    if has_errors and not has_data:
        ok = False
    return {
        "ok": ok,
        "waitingBulk": waiting_bulk,
        "winsBulk": wins_bulk,
        "archiveBulk": archive_bulk,
        "results": results,
        "summary": summary,
        "syncedLotOfferIds": synced,
        "pushedLotOfferIds": all_pushed,
        "wonLotOfferIds": summary["wonLotOfferIds"],
    }


def filter_queue_after_bulk(items: list[dict], *bulks: dict | None) -> list[dict]:
    """Убираем из Playwright-очереди лоты с финальным итогом из bulk API."""
    synced = set(_merged_synced_ids(*bulks))
    if not synced:
        return items
    out = []
    for it in items:
        oid = it.get("lotOfferId")
        try:
            oid_int = int(oid) if oid is not None else None
        except (TypeError, ValueError):
            oid_int = None
        if oid_int is not None and oid_int in synced:
            print(
                f"OUTCOME_SKIP_PLAYWRIGHT lotOfferId={oid_int} "
                f"(final via bulk API)",
                flush=True,
            )
            continue
        out.append(it)
    return out


def filter_queue_after_wins(items: list[dict], wins_bulk: dict | None) -> list[dict]:
    return filter_queue_after_bulk(items, wins_bulk)


def _load_items() -> tuple[list[dict], dict]:
    """Возвращает (items, meta) — meta нужна viewer'у при пустой очереди."""
    meta: dict = {
        "enabled": True,
        "queueCount": 0,
        "filteredCount": 0,
        "dealerId": _env(DEALER_ID_ENV) or None,
        "portalBase": _portal_base(),
    }
    raw = _env(OUTCOME_ITEMS_ENV)
    if raw:
        data = json.loads(raw)
        if isinstance(data, dict) and "items" in data:
            items = list(data.get("items") or [])
        elif isinstance(data, list):
            items = data
        else:
            items = []
        meta["queueCount"] = len(items)
        dealer_id = meta["dealerId"]
        if dealer_id:
            items = [
                i for i in items
                if not i.get("dealerId") or str(i.get("dealerId")) == str(dealer_id)
            ]
        meta["filteredCount"] = len(items)
        return items, meta

    limit = int(_env(OUTCOME_LIMIT_ENV, "50") or "50")
    dealer_id = meta["dealerId"]
    queue = fetch_outcome_queue(limit=limit, dealer_id=dealer_id, lookback_days=30)
    meta["enabled"] = bool(queue.get("enabled", True))
    if not meta["enabled"]:
        print("Outcome poll disabled on portal")
        return [], meta
    bf = queue.get("chatBackfill") or {}
    if bf:
        print(
            f"OUTCOME_CHAT_BACKFILL sent={bf.get('sent', 0)} "
            f"skipped={bf.get('skipped', 0)} errors={bf.get('errors', 0)}",
            flush=True,
        )
    items = list(queue.get("items") or [])
    meta["queueCount"] = len(items)
    dealer_id = meta["dealerId"]
    if dealer_id:
        items = [
            i for i in items
            if not i.get("dealerId") or str(i.get("dealerId")) == str(dealer_id)
        ]
    meta["filteredCount"] = len(items)
    return items, meta


def _build_summary(results: list[dict]) -> dict:
    by_code: dict[str, int] = {}
    fail = 0
    won_now = 0
    for r in results:
        if r.get("skipped"):
            continue
        if not r.get("ok"):
            fail += 1
            by_code["error"] = by_code.get("error", 0) + 1
            continue
        code = (r.get("portal") or {}).get("outcomeCode") or "unknown"
        by_code[code] = by_code.get(code, 0) + 1
        if (r.get("portal") or {}).get("becameWon"):
            won_now += 1
    return {
        "total": len(results),
        "ok": sum(1 for r in results if r.get("ok")),
        "fail": fail,
        "becameWon": won_now,
        "byOutcome": by_code,
    }


def main():
    """Только bulk statusGroup 2→3→4 → портал (без очереди и Playwright /view)."""
    return main_bulk_only()


def main_bulk_only() -> dict:
    """Bulk waiting + wins + archive — для /api/outcomes/wins и CLI."""
    global _LOG_LINES
    _LOG_LINES = []
    email = _env_required(EMAIL_ENV)
    password = _env_required(PASSWORD_ENV)
    dealer_id = _env(DEALER_ID_ENV)
    script_dir = _app_dir()

    _log("=" * 72)
    _log(
        f"BULK_ONLY dealer={dealer_id or '-'} portal={_portal_base()} "
        f"(statusGroup 2→3→4, без очереди портала)"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=USER_AGENT, locale="ru-RU")
        page = ctx.new_page()
        try:
            session_headers = _ensure_session(page, ctx, email, password, dealer_id, script_dir)
            bulk = sync_all_bulk(
                page,
                ctx,
                session_headers=session_headers,
                dealer_id=dealer_id,
                queue_items=None,
            )
        except MaxposterAuthError:
            if dealer_id:
                clear_session(script_dir, email, dealer_id)
            raise
        finally:
            browser.close()

    bs = bulk.get("summary") or {}
    _log(
        f"BULK summary waiting_api={bs.get('waitingApiOffers')} "
        f"wins_api={bs.get('winsApiOffers')} "
        f"archive_api={bs.get('archiveApiOffers')} "
        f"ok={bs.get('ok')} becameWon={bs.get('becameWon')} "
        f"synced={len(bs.get('syncedLotOfferIds') or [])}"
    )
    _log("=" * 72)

    payload = {
        **bulk,
        "logLines": list(_LOG_LINES),
        "wonLotOfferIds": bulk.get("wonLotOfferIds") or [],
        "syncedLotOfferIds": bulk.get("syncedLotOfferIds") or [],
        "mode": "bulk_only",
    }
    print(json.dumps(payload, ensure_ascii=False), flush=True)
    return payload


def main_wins_bulk_only() -> dict:
    """Обратная совместимость."""
    return main_bulk_only()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        _log(f"OUTCOME_FATAL: {exc}")
        print(json.dumps({
            "ok": False,
            "error": str(exc),
            "logLines": list(_LOG_LINES),
        }, ensure_ascii=False), flush=True)
        raise SystemExit(1) from exc
