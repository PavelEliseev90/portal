import json
import os
import sys

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
BID_CHANGE_URL_TPL = "https://mp-gateway.maxposter.ru/maxposter-web/v1/auction/lots/{lot_id}/bid/change"

EMAIL_ENV = "MAXPOSTER_EMAIL"
PASSWORD_ENV = "MAXPOSTER_PASSWORD"
LOT_OFFER_ID_ENV = "LOT_OFFER_ID"
LOT_ID_ENV = "LOT_ID"
DRY_RUN_ENV = "DRY_RUN"
BID_AMOUNT_ENV = "BID_AMOUNT"
DEALER_ID_ENV = "MAXPOSTER_DEALER_ID"
BID_PAYLOAD_ENV = "BID_PAYLOAD_JSON"


def _bid_headers(extra: dict | None = None) -> dict:
    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "origin": "https://app.maxposter.ru",
        "referer": "https://app.maxposter.ru/",
        "x-requested-with": "XMLHttpRequest",
    }
    if extra:
        headers.update(extra)
    return headers


def _post_bid(ctx, url: str, payload: dict, extra_headers: dict | None = None):
    return ctx.request.post(
        url,
        headers=_bid_headers(extra_headers),
        data=json.dumps(payload, ensure_ascii=False),
        timeout=60_000,
    )


def _warm_bid_headers(page, session_headers: dict | None = None) -> dict:
    """Открыть аукцион и подтянуть Authorization для API bid/change."""
    headers = dict(session_headers or {})
    try:
        page.goto(AUCTION_URL, wait_until="load", timeout=60_000)
        headers.update(_extract_authorization_header(page))
    except Exception as exc:
        print(f"Прогрев заголовков bid: {exc}")
    return headers


def _ensure_maxposter_session(page, ctx, email: str, password: str, dealer_id: str, script_dir: str) -> dict:
    if dealer_id:
        cached = load_session(script_dir, email, dealer_id)
        if cached:
            print(f"SESSION_CACHE_TRY (bid) возраст={cached.get('_age_min', 0):.0f} мин")
            apply_cookies(ctx, page, cached["cookies"])
            touch_session(script_dir, email, dealer_id)
            print("SESSION_CACHE_HIT (bid)")
            return _warm_bid_headers(page, cached.get("session_headers"))

    print("SESSION_FULL_LOGIN (bid)")
    _login(page, ctx, email, password)
    if dealer_id:
        _select_dealer(page, ctx, dealer_id)
    headers = _warm_bid_headers(page)
    if dealer_id:
        save_session(script_dir, email, dealer_id, ctx.cookies(), headers)
    return headers


def _send_bid(ctx, url: str, payload: dict, session_headers: dict) -> dict:
    resp = _post_bid(ctx, url, payload, session_headers)
    if resp.status == 403:
        raise MaxposterAuthError(f"HTTP 403: {resp.text()[:500]}")
    if not resp.ok:
        raise RuntimeError(f"HTTP {resp.status}: {resp.text()[:500]}")
    return resp.json()


def _env_required(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


def _parse_bool(v: str, default: bool = True) -> bool:
    if v is None:
        return default
    s = str(v).strip().lower()
    if s in {"1", "true", "yes", "y", "on"}:
        return True
    if s in {"0", "false", "no", "n", "off"}:
        return False
    return default


def main():
    email = _env_required(EMAIL_ENV)
    password = _env_required(PASSWORD_ENV)
    lot_offer_id = _env_required(LOT_OFFER_ID_ENV)
    lot_id = _env_required(LOT_ID_ENV)
    dry_run = _parse_bool(os.environ.get(DRY_RUN_ENV), default=True)
    bid_amount_raw = (os.environ.get(BID_AMOUNT_ENV) or "").strip()
    bid_amount = float(bid_amount_raw) if bid_amount_raw else None
    bid_payload_json = (os.environ.get(BID_PAYLOAD_ENV) or "").strip()
    if not bid_payload_json:
        raise RuntimeError("Missing BID_PAYLOAD_JSON")
    payload = json.loads(bid_payload_json)
    if bid_amount is not None:
        payload["bid"] = int(bid_amount)
    bid_change_url = BID_CHANGE_URL_TPL.format(lot_id=lot_id)
    result = {
        "ok": False,
        "dry_run": dry_run,
        "lot_offer_id": lot_offer_id,
        "lot_id": lot_id,
        "bid_change_url": bid_change_url,
        "request_payload": payload,
        "note": "",
    }

    script_dir = os.environ.get("APP_DIR") or os.path.dirname(os.path.abspath(__file__))
    dealer_id = (os.environ.get(DEALER_ID_ENV) or "").strip()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=USER_AGENT,
            locale="ru-RU",
            ignore_https_errors=True,
        )
        page = ctx.new_page()
        page.set_default_timeout(60_000)
        try:
            if dry_run:
                if dealer_id:
                    _ensure_maxposter_session(page, ctx, email, password, dealer_id, script_dir)
                else:
                    _login(page, ctx, email, password)
                result["ok"] = True
                result["note"] = "Dry-run API: запрос на bid/change не отправлялся."
                print(json.dumps(result, ensure_ascii=False))
                return

            session_headers = _ensure_maxposter_session(
                page, ctx, email, password, dealer_id, script_dir
            )
            try:
                data = _send_bid(ctx, bid_change_url, payload, session_headers)
            except MaxposterAuthError:
                if not dealer_id:
                    raise
                clear_session(script_dir, email, dealer_id)
                session_headers = _ensure_maxposter_session(
                    page, ctx, email, password, dealer_id, script_dir
                )
                data = _send_bid(ctx, bid_change_url, payload, session_headers)

            if dealer_id:
                save_session(script_dir, email, dealer_id, ctx.cookies(), session_headers)
            result["ok"] = True
            result["response"] = data
            result["note"] = "Ставка отправлена через API bid/change."
            print(json.dumps(result, ensure_ascii=False))

        except PWTimeout:
            result["ok"] = False
            result["note"] = "Timeout during login or lot page operations."
            print(json.dumps(result, ensure_ascii=False))
            return
        finally:
            browser.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        payload = {
            "ok": False,
            "dry_run": _parse_bool(os.environ.get(DRY_RUN_ENV), default=True),
            "lot_offer_id": (os.environ.get(LOT_OFFER_ID_ENV) or "").strip(),
            "lot_id": (os.environ.get(LOT_ID_ENV) or "").strip(),
            "note": f"Ошибка script_bid.py: {e}",
        }
        print(json.dumps(payload, ensure_ascii=False))
        sys.exit(1)
