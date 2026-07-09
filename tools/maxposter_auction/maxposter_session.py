"""Кэш cookies Maxposter (email + dealerId), TTL по умолчанию 30 мин."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

SESSION_FILENAME = "maxposter_session.json"
DEFAULT_TTL_MIN = 30
SESSION_COOKIE_NAMES = ("maxsession", "sfRemember", "maxRememberDealerId")


class MaxposterAuthError(RuntimeError):
    """Сессия недействительна (403 и т.п.)."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def session_file(script_dir: str) -> str:
    return os.path.join(script_dir, SESSION_FILENAME)


def cache_key(email: str, dealer_id: str) -> str:
    raw = f"{email.strip().lower()}|{str(dealer_id).strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def ttl_minutes() -> int:
    raw = (os.environ.get("SESSION_TTL_MIN") or "").strip()
    if not raw:
        return DEFAULT_TTL_MIN
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_TTL_MIN


def _read_store(path: str) -> dict:
    if not os.path.exists(path):
        return {"sessions": {}}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("sessions"), dict):
            return data
    except Exception:
        pass
    return {"sessions": {}}


def _write_store(path: str, store: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def _entry_age_min(entry: dict) -> float:
    ts = entry.get("ts")
    if not ts:
        return float("inf")
    try:
        saved = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if saved.tzinfo is None:
            saved = saved.replace(tzinfo=timezone.utc)
        return (_utcnow() - saved).total_seconds() / 60.0
    except Exception:
        return float("inf")


def load_session(script_dir: str, email: str, dealer_id: str) -> dict | None:
    key = cache_key(email, dealer_id)
    store = _read_store(session_file(script_dir))
    entry = store.get("sessions", {}).get(key)
    if not entry:
        return None
    age = _entry_age_min(entry)
    if age > ttl_minutes():
        print(f"Кэш сессии истёк ({age:.0f} мин > {ttl_minutes()} мин).")
        return None
    cookies = entry.get("cookies") or []
    if not any(c.get("name") == "maxsession" for c in cookies):
        return None
    if str(entry.get("dealerId", "")) != str(dealer_id):
        return None
    entry = dict(entry)
    entry["_age_min"] = age
    return entry


def save_session(
    script_dir: str,
    email: str,
    dealer_id: str,
    cookies: list,
    session_headers: dict | None = None,
) -> None:
    key = cache_key(email, dealer_id)
    path = session_file(script_dir)
    store = _read_store(path)
    headers = {}
    for k, v in (session_headers or {}).items():
        if k.lower() == "cookie":
            continue
        headers[k] = v
    store.setdefault("sessions", {})[key] = {
        "ts": _utcnow().isoformat(),
        "email": email.strip().lower(),
        "dealerId": str(dealer_id),
        "cookies": cookies,
        "session_headers": headers,
    }
    _write_store(path, store)
    print(f"SESSION_CACHE_SAVED key={key} ttl={ttl_minutes()}мин")


def clear_session(script_dir: str, email: str, dealer_id: str) -> None:
    key = cache_key(email, dealer_id)
    path = session_file(script_dir)
    store = _read_store(path)
    sessions = store.get("sessions") or {}
    if key in sessions:
        del sessions[key]
        store["sessions"] = sessions
        _write_store(path, store)
        print(f"SESSION_CACHE_CLEARED key={key}")


def touch_session(script_dir: str, email: str, dealer_id: str) -> None:
    """Продлить TTL при успешном использовании кэша."""
    key = cache_key(email, dealer_id)
    path = session_file(script_dir)
    store = _read_store(path)
    entry = (store.get("sessions") or {}).get(key)
    if not entry:
        return
    entry["ts"] = _utcnow().isoformat()
    store["sessions"][key] = entry
    _write_store(path, store)


def apply_cookies(ctx, page, cookies: list) -> None:
    page.goto("https://app.maxposter.ru/", wait_until="domcontentloaded", timeout=60_000)
    if cookies:
        ctx.add_cookies(cookies)


def is_auth_error(exc: BaseException) -> bool:
    if isinstance(exc, MaxposterAuthError):
        return True
    msg = str(exc).lower()
    return "403" in msg or "авторизац" in msg
