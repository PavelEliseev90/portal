# maxposter_active_offers.py
import json
import os
import sys
import traceback
from datetime import datetime

from maxposter_session import (
    MaxposterAuthError,
    apply_cookies,
    clear_session,
    is_auth_error,
    load_session,
    save_session,
    touch_session,
)
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


def _configure_stdio_utf8() -> None:
    if sys.platform != "win32":
        return
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


_configure_stdio_utf8()

LOGIN_URL = "https://app.maxposter.ru/login"
PROFILE_SWITCH_URL = "https://app.maxposter.ru/profile-switch"
AUCTION_URL = "https://app.maxposter.ru/dealer/auction"
OFFERS_URL = "https://mp-gateway.maxposter.ru/maxposter-web/v1/auction/lots/offers/list"

EMAIL_ENV = "MAXPOSTER_EMAIL"
PASSWORD_ENV = "MAXPOSTER_PASSWORD"
DEALER_ID_ENV = "MAXPOSTER_DEALER_ID"

PAGE_LIMIT = 50
# Как в рабочем PowerShell: активные лоты, сортировка по времени окончания.
SORT_FIELD = "lotFinishesAt"
USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36"
)

_SKIP_HEADERS = frozenset({
    "host", "content-length", "connection", "accept-encoding",
    "sec-fetch-site", "sec-fetch-mode", "sec-fetch-dest",
    "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform",
})


def _is_offers_list(req) -> bool:
    return req.method == "POST" and "auction/lots/offers/list" in req.url


def _headers_from_request(req) -> dict:
    out = {}
    for k, v in req.headers.items():
        if k.lower() in _SKIP_HEADERS:
            continue
        out[k] = v
    return out


def _cookie_header(ctx) -> str:
    parts = []
    seen = set()
    for c in ctx.cookies():
        if "maxposter" not in (c.get("domain") or "").lower():
            continue
        name = c.get("name")
        value = c.get("value")
        if not name or value is None or name in seen:
            continue
        seen.add(name)
        parts.append(f"{name}={value}")
    return "; ".join(parts)


def _extract_authorization_header(page) -> dict:
    """
    Пытаемся достать access token из localStorage/sessionStorage.
    Maxposter (SPA) часто хранит JWT там и добавляет Authorization в API.
    """
    try:
        result = page.evaluate(
            """() => {
                const out = [];
                const pushAll = (store, storeName) => {
                    try{
                        for (let i = 0; i < store.length; i++){
                            const k = store.key(i);
                            if (!k) continue;
                            out.push({ store: storeName, key: k, value: store.getItem(k) });
                        }
                    }catch(e){}
                };
                pushAll(localStorage, 'localStorage');
                pushAll(sessionStorage, 'sessionStorage');
                return out;
            }"""
        )
    except Exception:
        result = []

    def _looks_like_jwt(s: str) -> bool:
        parts = s.split(".")
        return len(parts) == 3 and all(len(p) >= 10 for p in parts)

    candidates = []
    for item in result or []:
        k = str(item.get("key") or "")
        v = item.get("value")
        if not isinstance(v, str) or not v.strip():
            continue
        vv = v.strip()
        lk = k.lower()
        if vv.lower().startswith("bearer ") and len(vv) > 20:
            candidates.append(vv)
            continue
        if _looks_like_jwt(vv) and any(x in lk for x in ("token", "auth", "access")):
            candidates.append("Bearer " + vv)
            continue
        # иногда токен внутри JSON
        if any(x in lk for x in ("token", "auth", "access")) and len(vv) > 20:
            try:
                obj = json.loads(vv)
            except Exception:
                obj = None
            if isinstance(obj, dict):
                for kk in ("accessToken", "access_token", "token", "jwt"):
                    tv = obj.get(kk)
                    if isinstance(tv, str) and tv.strip():
                        t = tv.strip()
                        candidates.append(t if t.lower().startswith("bearer ") else ("Bearer " + t))

    # берем самый длинный кандидат (обычно JWT)
    if candidates:
        auth = max(candidates, key=len)
        print(f"Auth token найден в storage (len={len(auth)})")
        return {"authorization": auth}
    print("Auth token в storage не найден")
    return {}


def _offers_body(cursor_value: str, limit: int, *, sort_field: str = SORT_FIELD) -> dict:
    """
    Тело offers/list как в PowerShell:
    filters: только statusGroup=1 (активные), без outbidForExternalUser.
    """
    return {
        "pagination": {
            "mode": "cursor",
            "cursor": {
                "operation": "lt",
                "value": cursor_value,
                "limit": limit,
                "useCount": True,
                "sortField": sort_field,
            },
        },
        "filters": [
            {"field": "statusGroup", "type": "integer", "value": {"integer": 1}},
        ],
    }


def _canonical_list_body(cursor_value: str = "", limit: int = PAGE_LIMIT) -> dict:
    return _offers_body(cursor_value, limit, sort_field=SORT_FIELD)


def _parse_request_body(req) -> dict | None:
    raw = req.post_data
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _body_with_cursor(body: dict, cursor_value: str) -> dict:
    out = json.loads(json.dumps(body))
    cur = out.setdefault("pagination", {}).setdefault("cursor", {})
    cur["value"] = cursor_value
    return out


def _offer_count(payload: dict) -> int:
    offers = payload.get("offers") or []
    cursor = (payload.get("pagination") or {}).get("cursor") or {}
    total = cursor.get("count")
    if isinstance(total, int):
        return max(len(offers), total)
    return len(offers)


def _log_offers_payload(label: str, payload: dict, body: dict | None = None) -> None:
    offers = payload.get("offers") or []
    cursor = (payload.get("pagination") or {}).get("cursor") or {}
    fields = [f.get("field") for f in (body or {}).get("filters") or []]
    print(
        f"{label}: len(offers)={len(offers)}, cursor.count={cursor.get('count')!r}, "
        f"sortField={((body or {}).get('pagination') or {}).get('cursor', {}).get('sortField')!r}, "
        f"filters={fields or '—'}"
    )


def _api_headers(ctx) -> dict:
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "ru,en;q=0.9",
        "content-type": "application/json",
        "origin": "https://app.maxposter.ru",
        "referer": "https://app.maxposter.ru/dealer/auction",
        "x-requested-with": "XMLHttpRequest",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
    }
    cookie = _cookie_header(ctx)
    if cookie:
        headers["cookie"] = cookie
    return headers


def _merge_api_headers(ctx, extra_headers: dict | None) -> dict:
    headers = _api_headers(ctx)
    for k, v in (extra_headers or {}).items():
        if not k or v is None:
            continue
        if str(k).lower() == "cookie":
            continue
        headers[k] = v
    return headers


def _headers_for_browser_fetch(extra_headers: dict | None) -> dict:
    """Все заголовки SPA, кроме запрещённых для fetch(credentials:include)."""
    skip = _SKIP_HEADERS | frozenset({"cookie", "host", "content-length", "connection", "accept-encoding"})
    out = {}
    for k, v in (extra_headers or {}).items():
        if not k or v is None:
            continue
        if str(k).lower() in skip:
            continue
        out[k] = v
    return out


def api_offers_page(
    ctx,
    *,
    cursor_value: str,
    limit: int,
    extra_headers: dict | None = None,
    body_base: dict | None = None,
) -> dict:
    headers = _merge_api_headers(ctx, extra_headers)
    if body_base is not None:
        body = _body_with_cursor(body_base, cursor_value)
    else:
        body = _offers_body(cursor_value, limit)
    resp = ctx.request.post(
        OFFERS_URL,
        data=json.dumps(body),
        headers=headers,
        timeout=60_000,
    )
    if not resp.ok:
        if resp.status == 403:
            raise MaxposterAuthError(
                "Требуется авторизация Maxposter (HTTP 403). "
                "Проверьте dealerId, логин и доступ к аукциону."
            )
        raise RuntimeError(f"HTTP {resp.status}: {resp.text()[:2000]}")
    return resp.json()


def _api_offers_page_or_fetch(
    ctx,
    page,
    *,
    cursor_value: str,
    limit: int,
    extra_headers: dict | None = None,
    body_base: dict | None = None,
) -> dict:
    """API через Playwright request; при ошибке — fetch из контекста страницы (как SPA)."""
    try:
        return api_offers_page(
            ctx,
            cursor_value=cursor_value,
            limit=limit,
            extra_headers=extra_headers,
            body_base=body_base,
        )
    except MaxposterAuthError:
        raise
    except Exception as exc:
        if page is None:
            raise
        print(f"api_offers_page failed ({exc!r}), пробуем page.fetch…")
        if body_base is not None:
            body = _body_with_cursor(body_base, cursor_value)
        else:
            body = _offers_body(cursor_value, limit)
        return _fetch_via_page(page, body, extra_headers)


def _warm_auction_headers(page, session_headers: dict | None) -> dict:
    """Открыть аукцион и подтянуть Authorization для API-запросов."""
    headers = dict(session_headers or {})
    try:
        page.goto(AUCTION_URL, wait_until="load", timeout=60_000)
        headers.update(_extract_authorization_header(page))
    except Exception as exc:
        print(f"Прогрев аукциона: {exc}")
    return headers


# Ключевые cookies после логина и выбора площадки (нужны для API offers/list).
_SESSION_COOKIE_NAMES = ("maxsession", "sfRemember", "maxRememberDealerId")


def _wait_maxsession(ctx, page, timeout_sec: int = 45) -> None:
    for _ in range(timeout_sec):
        if any(c.get("name") == "maxsession" for c in ctx.cookies()):
            return
        page.wait_for_timeout(1000)
    raise RuntimeError("После логина не появилась cookie maxsession.")


def _cookie_map(ctx) -> dict[str, str]:
    out: dict[str, str] = {}
    for c in ctx.cookies():
        name = c.get("name")
        value = c.get("value")
        if name and value is not None:
            out[name] = str(value)
    return out


def _dealer_id_from_cookies(ctx) -> str:
    return _cookie_map(ctx).get("maxRememberDealerId", "").strip()


def _wait_profile_switch_page(page) -> None:
    """После логина Maxposter открывает страницу выбора площадки."""
    try:
        page.wait_for_url(lambda url: "/profile-switch" in url, timeout=30_000)
    except PWTimeout:
        if "/profile-switch" not in page.url:
            print("Не попали на profile-switch после логина, открываем вручную.")
            page.goto(PROFILE_SWITCH_URL, wait_until="load", timeout=60_000)
    page.locator('a[href*="/switch"]').first.wait_for(state="visible", timeout=25_000)
    print(f"Страница выбора площадки: {page.url}")


def _wait_dealer_cookie(ctx, dealer_id: str, page, timeout_sec: int = 30) -> None:
    for _ in range(timeout_sec):
        if _dealer_id_from_cookies(ctx) == dealer_id:
            return
        page.wait_for_timeout(1000)
    raise RuntimeError(
        f"После клика по площадке cookie maxRememberDealerId не стала {dealer_id}. "
        f"Сейчас: {_dealer_id_from_cookies(ctx) or '(нет)'}"
    )


def _log_session_cookies(ctx, dealer_id: str) -> dict[str, str]:
    """Проверяем и логируем cookies сессии перед запросом списка лотов."""
    cmap = _cookie_map(ctx)
    snapshot = {n: cmap[n] for n in _SESSION_COOKIE_NAMES if n in cmap}
    missing = [n for n in _SESSION_COOKIE_NAMES if n not in snapshot]
    if missing:
        print(f"Внимание: нет cookies: {', '.join(missing)}")
    print(
        "Cookies сессии: "
        + ", ".join(
            f"{k}={v[:8]}…" if len(v) > 8 else f"{k}={v}"
            for k, v in snapshot.items()
        )
    )
    if snapshot.get("maxRememberDealerId") != dealer_id:
        raise RuntimeError(
            f"maxRememberDealerId={snapshot.get('maxRememberDealerId')!r}, "
            f"ожидалось {dealer_id!r}"
        )
    return snapshot


def _select_dealer(page, ctx, dealer_id: str) -> None:
    """
    Шаг 2: на profile-switch кликаем площадку /dealer/{id}/switch.
    Шаг 3: ждём maxRememberDealerId и остальные cookies в контексте браузера.
    """
    if not dealer_id:
        raise RuntimeError("Укажите dealerId (площадку) в viewer.")

    cur = _dealer_id_from_cookies(ctx)
    if cur == dealer_id and "/profile-switch" not in page.url:
        print(f"Площадка уже выбрана: dealerId={dealer_id}")
        _log_session_cookies(ctx, dealer_id)
        return

    _wait_profile_switch_page(page)

    switch_sel = f'a[href="/dealer/{dealer_id}/switch"]'
    link = page.locator(switch_sel).first
    try:
        link.wait_for(state="visible", timeout=20_000)
        label = (link.inner_text(timeout=3000) or "").strip()
        print(f"Клик по площадке: {label or dealer_id}")
        link.click()
    except PWTimeout:
        link = page.locator(f'a[href*="/dealer/{dealer_id}/switch"]').first
        link.wait_for(state="visible", timeout=10_000)
        print(f"Клик по площадке dealerId={dealer_id}")
        link.click()

    try:
        page.wait_for_url(lambda url: "/profile-switch" not in url, timeout=30_000)
    except PWTimeout:
        page.wait_for_timeout(2000)

    page.wait_for_timeout(1000)
    _wait_dealer_cookie(ctx, dealer_id, page)
    print(f"Площадка активна, URL={page.url}")
    _log_session_cookies(ctx, dealer_id)


def _goto_auction(page) -> None:
    print(f"Шаг 4 — список лотов: {AUCTION_URL}")
    page.goto(AUCTION_URL, wait_until="load", timeout=60_000)


def _fetch_via_page(page, body: dict, extra_headers: dict | None = None) -> dict:
    """Запрос из контекста страницы (cookies + заголовки как у SPA)."""
    safe_headers = _headers_for_browser_fetch(extra_headers)
    return page.evaluate(
        """async ({ url, body, extraHeaders }) => {
            const headers = {
                'accept': 'application/json, text/plain, */*',
                'content-type': 'application/json',
                'x-requested-with': 'XMLHttpRequest',
                ...(extraHeaders || {}),
            };
            const r = await fetch(url, {
                method: 'POST',
                headers,
                credentials: 'include',
                body: JSON.stringify(body),
            });
            const text = await r.text();
            if (!r.ok) throw new Error('HTTP ' + r.status + ': ' + text.slice(0, 500));
            return JSON.parse(text);
        }""",
        {"url": OFFERS_URL, "body": body, "extraHeaders": safe_headers},
    )


def _fetch_via_page_cursor(page, body_base: dict, cursor_value: str, extra_headers: dict | None = None) -> dict:
    return _fetch_via_page(page, _body_with_cursor(body_base, cursor_value), extra_headers)


def _fetch_offers_list(page, ctx) -> tuple[dict, dict, dict]:
    """
    Прогрев аукциона: перехват успешного ответа SPA offers/list (авторизация + первая страница),
    затем попытка канонического тела (PowerShell); при 403 — данные и тело запроса из SPA.
    """
    session_headers: dict = {}
    canonical_body = _canonical_list_body("", PAGE_LIMIT)
    list_body = canonical_body
    spa_payload: dict | None = None
    spa_body: dict | None = None

    def on_request(req):
        if _is_offers_list(req):
            session_headers.update(_headers_from_request(req))

    def on_response(resp):
        nonlocal spa_payload, spa_body
        if not _is_offers_list(resp.request):
            return
        session_headers.update(_headers_from_request(resp.request))
        body = _parse_request_body(resp.request)
        if not resp.ok:
            return
        try:
            payload = resp.json()
        except Exception:
            return
        _log_offers_payload("  перехват SPA", payload, body)
        if spa_payload is None or _offer_count(payload) >= _offer_count(spa_payload):
            spa_payload = payload
            if body is not None:
                spa_body = body

    page.on("request", on_request)
    page.on("response", on_response)
    try:
        try:
            with page.expect_response(lambda r: _is_offers_list(r.request), timeout=30_000) as resp_info:
                _goto_auction(page)
            resp = resp_info.value
            session_headers.update(_headers_from_request(resp.request))
            if resp.ok:
                print(
                    "SPA offers/list response OK, "
                    f"headers={[k for k in session_headers if k.lower() != 'cookie'][:12]}"
                )
            else:
                print(f"SPA offers/list HTTP {resp.status} (ждём ещё ответы SPA…)")
        except PWTimeout:
            if "auction" not in page.url:
                _goto_auction(page)
            print("Не дождались SPA response offers/list — продолжаем без него.")

        for _ in range(8):
            if spa_payload is not None and _offer_count(spa_payload) > 0:
                break
            page.wait_for_timeout(500)
        session_headers.update(_extract_authorization_header(page))

        first_payload: dict | None = None

        print(
            f"Пробуем каноническое тело: statusGroup=1, sortField={SORT_FIELD}, "
            f"limit={PAGE_LIMIT}, без outbidForExternalUser"
        )
        try:
            first_payload = _api_offers_page_or_fetch(
                ctx,
                page,
                cursor_value="",
                limit=PAGE_LIMIT,
                extra_headers=session_headers or None,
                body_base=canonical_body,
            )
            list_body = canonical_body
            _log_offers_payload("  API (canonical)", first_payload, list_body)
        except MaxposterAuthError as e:
            print(f"API canonical 403: {e}. Пробуем fetch из страницы…")
            try:
                first_payload = _fetch_via_page(page, canonical_body, session_headers or None)
                list_body = canonical_body
                _log_offers_payload("  page.fetch (canonical)", first_payload, list_body)
            except Exception as ex:
                print(f"  page.fetch canonical: {ex}")

        if (first_payload is None or _offer_count(first_payload) == 0) and spa_payload is not None:
            if first_payload is None or _offer_count(spa_payload) > _offer_count(first_payload):
                print("Используем первую страницу из ответа SPA (канонический запрос недоступен или пустой).")
                first_payload = spa_payload
                if spa_body is not None:
                    list_body = json.loads(json.dumps(spa_body))

        if first_payload is None:
            raise MaxposterAuthError(
                "Не удалось получить offers/list: нет ответа SPA и API/fetch вернули 403. "
                "Проверьте dealerId, логин и доступ к аукциону."
            )

        _log_offers_payload("Итог шага 4", first_payload, list_body)
        return first_payload, session_headers, list_body
    finally:
        page.remove_listener("request", on_request)
        page.remove_listener("response", on_response)


def _login(page, ctx, email: str, password: str) -> None:
    """Шаг 1: логин, появление maxsession."""
    print("Шаг 1 — логин")
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    email_input = page.locator("#signin_email")
    password_input = page.locator("#signin_password")
    submit_button = page.locator('button[data-marker="submit"]')
    email_input.wait_for(state="visible")
    password_input.wait_for(state="visible")
    submit_button.wait_for(state="visible")
    email_input.fill(email)
    password_input.fill(password)
    submit_button.click()
    try:
        page.wait_for_url(lambda url: "/login" not in url, timeout=60_000)
    except PWTimeout:
        form_text = page.locator("form").inner_text(timeout=3000).strip()
        raise RuntimeError(
            f"Не дождались выхода со страницы логина. URL: {page.url}\n"
            f"Текст формы: {form_text[:1000]}\n"
            "Проверьте логин, пароль и сообщения об ошибке на форме."
        )
    _wait_maxsession(ctx, page)
    page.wait_for_timeout(1000)
    print(f"Логин OK, URL={page.url}")


def _establish_offers_session(
    page, ctx, email: str, password: str, dealer_id: str, script_dir: str
) -> tuple[dict, dict, dict]:
    """Кэш cookies → быстрый API; при 403 — полный логин и выбор площадки."""
    list_body = _canonical_list_body("", PAGE_LIMIT)
    cached = load_session(script_dir, email, dealer_id)
    if cached:
        age = cached.get("_age_min", 0)
        print(f"SESSION_CACHE_TRY возраст={age:.0f} мин (TTL={os.environ.get('SESSION_TTL_MIN') or '30'})")
        apply_cookies(ctx, page, cached["cookies"])
        session_headers = _warm_auction_headers(page, cached.get("session_headers"))
        try:
            first_payload = _api_offers_page_or_fetch(
                ctx,
                page,
                cursor_value="",
                limit=PAGE_LIMIT,
                extra_headers=session_headers or None,
                body_base=list_body,
            )
            _log_offers_payload("  API (кэш сессии)", first_payload, list_body)
            touch_session(script_dir, email, dealer_id)
            print("SESSION_CACHE_HIT — логин пропущен")
            save_session(script_dir, email, dealer_id, ctx.cookies(), session_headers)
            return first_payload, session_headers, list_body
        except MaxposterAuthError:
            try:
                session_headers = _warm_auction_headers(page, cached.get("session_headers"))
                first_payload = _api_offers_page_or_fetch(
                    ctx,
                    page,
                    cursor_value="",
                    limit=PAGE_LIMIT,
                    extra_headers=session_headers or None,
                    body_base=list_body,
                )
                _log_offers_payload("  API (кэш cookies + auth)", first_payload, list_body)
                touch_session(script_dir, email, dealer_id)
                print("SESSION_CACHE_HIT (auth) — логин пропущен")
                save_session(script_dir, email, dealer_id, ctx.cookies(), session_headers)
                return first_payload, session_headers, list_body
            except Exception:
                clear_session(script_dir, email, dealer_id)
                print("SESSION_CACHE_MISS — сессия недействительна, полный логин")

    print("SESSION_FULL_LOGIN")
    _login(page, ctx, email, password)
    print("Шаг 2–3 — выбор площадки и cookies")
    _select_dealer(page, ctx, dealer_id)
    first_payload, session_headers, list_body = _fetch_offers_list(page, ctx)
    save_session(script_dir, email, dealer_id, ctx.cookies(), session_headers)
    return first_payload, session_headers, list_body


def _skip_auth_dealer(dealer_id: str, message: str) -> None:
    """Пропуск площадки при 403 — сервер идёт к следующей (reload_all)."""
    print(f"SKIP_AUTH: dealerId={dealer_id} — {message}")


def main():
    script_dir = os.environ.get("APP_DIR") or os.path.dirname(os.path.abspath(__file__))
    out_path = (os.environ.get("OUT_PATH") or "").strip() or os.path.join(script_dir, "offers_dump.json")

    email = os.environ.get(EMAIL_ENV, "").strip()
    password = os.environ.get(PASSWORD_ENV, "")
    if not email or not password:
        print(f"SKIP: не переданы {EMAIL_ENV} / {PASSWORD_ENV}, обновление пропущено.")
        return

    dealer_id = (os.environ.get(DEALER_ID_ENV) or "").strip()
    if not dealer_id:
        print(f"SKIP: не указан {DEALER_ID_ENV} — выберите площадку в viewer.")
        return

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=USER_AGENT, locale="ru-RU")
            page = ctx.new_page()
            page.set_default_timeout(60_000)

            print(f"=== Загрузка лотов, dealerId={dealer_id} ===")
            first_payload, session_headers, list_body = _establish_offers_session(
                page, ctx, email, password, dealer_id, script_dir
            )

            all_offers = []
            seen_offer_ids = set()
            cursor_value = ""
            page_num = 0
            payload = first_payload

            while True:
                page_num += 1
                offers = payload.get("offers") or []
                cursor = (payload.get("pagination") or {}).get("cursor") or {}
                next_value = cursor.get("value") or ""
                count = cursor.get("count")

                offer_ids = [o.get("lotOfferId") for o in offers if o.get("lotOfferId") is not None]
                if offer_ids and all(oid in seen_offer_ids for oid in offer_ids):
                    print("Repeated page detected, stopping.")
                    break

                new_added = 0
                for o in offers:
                    oid = o.get("lotOfferId")
                    if oid is None:
                        all_offers.append(o)
                        new_added += 1
                        continue
                    if oid in seen_offer_ids:
                        continue
                    seen_offer_ids.add(oid)
                    all_offers.append(o)
                    new_added += 1

                print(
                    f"Page {page_num}: got {len(offers)} offers, added {new_added} new "
                    f"(cursor.count={count}, next_cursor={next_value!r})"
                )

                if not offers:
                    break
                if not next_value or next_value == cursor_value:
                    break
                cursor_value = next_value
                try:
                    payload = _api_offers_page_or_fetch(
                        ctx,
                        page,
                        cursor_value=cursor_value,
                        limit=PAGE_LIMIT,
                        extra_headers=session_headers or None,
                        body_base=list_body,
                    )
                except MaxposterAuthError:
                    if all_offers:
                        print(
                            f"Пагинация 403 при dealerId={dealer_id}, "
                            f"сохраняем {len(all_offers)} уже загруженных лотов."
                        )
                        break
                    raise
                except Exception as ex:
                    if all_offers and is_auth_error(ex):
                        print(
                            f"Пагинация auth error при dealerId={dealer_id}, "
                            f"сохраняем {len(all_offers)} уже загруженных лотов."
                        )
                        break
                    raise

            out = {
                "ts": datetime.utcnow().isoformat(),
                "totalOffers": len(all_offers),
                "offers": all_offers,
                "dealerId": int(dealer_id) if dealer_id.isdigit() else dealer_id or None,
            }
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False, indent=2)

            save_session(script_dir, email, dealer_id, ctx.cookies(), session_headers)
            print(f"Saved {len(all_offers)} offers to {out_path}")
            browser.close()
    except MaxposterAuthError as e:
        _skip_auth_dealer(dealer_id, str(e))
    except Exception as e:
        if is_auth_error(e):
            _skip_auth_dealer(dealer_id, str(e))
        else:
            raise


if __name__ == "__main__":
    dealer_id = (os.environ.get(DEALER_ID_ENV) or "").strip()
    try:
        main()
    except MaxposterAuthError as e:
        _skip_auth_dealer(dealer_id or "?", str(e))
    except Exception as e:
        if is_auth_error(e):
            _skip_auth_dealer(dealer_id or "?", str(e))
        else:
            traceback.print_exc()
            sys.exit(1)
