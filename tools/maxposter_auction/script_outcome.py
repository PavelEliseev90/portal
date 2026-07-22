"""
Опрос итогов завершённых лотов Maxposter (решение продавца).

Для каждого lotOfferId из очереди портала открывает
  https://app.maxposter.ru/dealer/auction/{lotOfferId}/view
перехватывает JSON API и/или читает тексты со страницы, затем
POST /api/avito_auction_outcome_set/ на портал.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
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

from script_auction import USER_AGENT, _extract_authorization_header, _login, _select_dealer

LOGIN_URL = "https://app.maxposter.ru/login"
AUCTION_URL = "https://app.maxposter.ru/dealer/auction"
VIEW_URL_TPL = "https://app.maxposter.ru/dealer/auction/{lot_offer_id}/view"

EMAIL_ENV = "MAXPOSTER_EMAIL"
PASSWORD_ENV = "MAXPOSTER_PASSWORD"
DEALER_ID_ENV = "MAXPOSTER_DEALER_ID"
PORTAL_BASE_ENV = "PORTAL_BASE"
OUTCOME_ITEMS_ENV = "OUTCOME_ITEMS_JSON"
OUTCOME_LIMIT_ENV = "OUTCOME_LIMIT"
OUTCOME_LOG_NAME = "outcome_poll.log"

INTERESTING_TEXT_RE = re.compile(
    r"аукцион|решени|продавц|выигр|выбран|выбрал|проигра|отмен|ждём|ждем|день|побед|никого",
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


def fetch_outcome_queue(limit: int = 30) -> dict:
    url = f"{_portal_base()}/api/avito_auction_outcome_queue/?limit={limit}"
    return _http_json("GET", url)


def push_outcome(item: dict, extracted: dict) -> dict:
    url = f"{_portal_base()}/api/avito_auction_outcome_set/"
    payload = {
        "lotOfferId": item.get("lotOfferId"),
        "lotId": item.get("lotId"),
        "title": extracted.get("title") or "",
        "detail": extracted.get("detail") or "",
        "blob": extracted.get("blob") or "",
        "status": extracted.get("status") or "",
        "outcomeCode": extracted.get("outcomeCode") or "",
        "raw": extracted.get("raw") or "",
    }
    return _http_json("POST", url, payload)


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
                """() => /аукцион|продавц|решени|выигр|выбран|выбрал|никого/i.test(
                    (document.body && document.body.innerText) || ''
                )""",
                timeout=8_000,
            )
        except PWTimeout:
            page.wait_for_timeout(900)
    finally:
        try:
            page.remove_listener("response", on_response)
        except Exception:
            pass

    page.wait_for_timeout(400)

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
              const nodes = root.querySelectorAll('h1,h2,h3,h4,p,div,span,li');
              const out = [];
              const seen = new Set();
              for (const el of nodes) {
                if (!el || el.children.length > 4) continue;
                const t = (el.innerText || '').replace(/\\s+/g, ' ').trim();
                if (t.length < 8 || t.length > 280) continue;
                if (!/аукцион|решени|продавц|выигр|выбран|выбрал|проигра|отмен|ждём|ждем|день|побед|никого|покупател|не выкупил/i.test(t)) continue;
                if (seen.has(t)) continue;
                seen.add(t);
                out.push(t);
                if (out.length >= 40) break;
              }
              return out;
            }"""
        ) or []
    except Exception as exc:
        print(f"DOM extract error lotOfferId={lot_offer_id}: {exc}")

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
    code = portal.get("outcomeCode") or "?"
    status = portal.get("statusCode") or "?"
    prev = portal.get("prevOutcome") or item.get("outcomeCode") or "-"
    row = {
        "ok": True,
        "lotOfferId": lot_offer_id,
        "lotId": item.get("lotId") or portal.get("lotId"),
        "lotPk": item.get("lotPk"),
        "car": item.get("car") or "",
        "bid": item.get("bid"),
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
        },
        "msg": (
            f"лот {item.get('lotId')} / offer {lot_offer_id}: "
            f"{prev} → {code} ({title}; {detail})"
        ),
    }
    print(
        f"OUTCOME_OK[{idx}] lotOfferId={lot_offer_id} lotId={item.get('lotId')} "
        f"«{item.get('car') or '—'}» {prev} → {code}/{status} becameWon={bool(portal.get('becameWon'))}",
        flush=True,
    )
    return row


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

    limit = int(_env(OUTCOME_LIMIT_ENV, "20") or "20")
    queue = fetch_outcome_queue(limit=limit)
    meta["enabled"] = bool(queue.get("enabled", True))
    if not meta["enabled"]:
        print("Outcome poll disabled on portal")
        return [], meta
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
    global _LOG_LINES
    _LOG_LINES = []
    email = _env_required(EMAIL_ENV)
    password = _env_required(PASSWORD_ENV)
    dealer_id = _env(DEALER_ID_ENV)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    items, queue_meta = _load_items()
    _log("=" * 72)
    _log(
        f"OUTCOME_START enabled={queue_meta.get('enabled')} "
        f"queue={queue_meta.get('queueCount')} filtered={queue_meta.get('filteredCount')} "
        f"dealer={dealer_id or '-'} portal={_portal_base()} "
        f"log={os.path.join(_app_dir(), OUTCOME_LOG_NAME)}"
    )

    results = []
    if not items:
        reason = "disabled" if not queue_meta.get("enabled") else "empty"
        _log(f"OUTCOME_EMPTY reason={reason} — лотов для опроса нет")
        payload = {
            "ok": True,
            "count": 0,
            "okCount": 0,
            "results": [],
            "reason": reason,
            "summary": _build_summary([]),
            "logLines": list(_LOG_LINES),
            **queue_meta,
        }
        print(json.dumps(payload, ensure_ascii=False), flush=True)
        return

    for idx, item in enumerate(items, 1):
        _log(f"OUTCOME_QUEUE[{idx}/{len(items)}] {_fmt_item(item)}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=USER_AGENT, locale="ru-RU")
        page = ctx.new_page()
        try:
            try:
                _ensure_session(page, ctx, email, password, dealer_id, script_dir)
            except MaxposterAuthError:
                if dealer_id:
                    clear_session(script_dir, email, dealer_id)
                raise

            for idx, item in enumerate(items, 1):
                try:
                    row = process_item(page, item, idx=idx, total=len(items))
                    results.append(row)
                    _log(row.get("msg") or f"OUTCOME row {idx}")
                except MaxposterAuthError:
                    if dealer_id:
                        clear_session(script_dir, email, dealer_id)
                    raise
                except Exception as exc:
                    err = str(exc)[:300]
                    _log(f"OUTCOME_ERR[{idx}] lotOfferId={item.get('lotOfferId')}: {err}")
                    results.append({
                        "ok": False,
                        "lotOfferId": item.get("lotOfferId"),
                        "lotId": item.get("lotId"),
                        "lotPk": item.get("lotPk"),
                        "car": item.get("car") or "",
                        "error": err,
                        "msg": f"лот {item.get('lotId')} / offer {item.get('lotOfferId')}: ошибка — {err}",
                    })
        finally:
            browser.close()

    summary = _build_summary(results)
    by = summary.get("byOutcome") or {}
    by_txt = ", ".join(f"{k}={v}" for k, v in sorted(by.items())) or "—"
    _log(
        f"OUTCOME_DONE ok={summary['ok']}/{summary['total']} fail={summary['fail']} "
        f"becameWon={summary['becameWon']} by=[{by_txt}]"
    )
    _log("=" * 72)
    ok_n = summary["ok"]
    payload = {
        "ok": ok_n == len(results) and summary["fail"] == 0,
        "count": len(results),
        "okCount": ok_n,
        "results": results,
        "summary": summary,
        "logLines": list(_LOG_LINES),
        **queue_meta,
    }
    print(json.dumps(payload, ensure_ascii=False), flush=True)


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
