import io
import json
import os
import subprocess
import sys
import threading
from datetime import datetime
from contextlib import redirect_stderr, redirect_stdout
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from app_paths import app_dir, bundle_dir, ensure_runtime_files, is_frozen

HERE = app_dir()
SCRIPT_PATH = os.path.join(bundle_dir(), "script_auction.py")
SCRIPT_BID_PATH = os.path.join(bundle_dir(), "script_bid.py")
SCRIPT_OUTCOME_PATH = os.path.join(bundle_dir(), "script_outcome.py")
OUT_JSON = os.path.join(HERE, "offers_dump.json")
DEALERS_STATUS_JSON = os.path.join(HERE, "dealers_status.json")

# Жёстко закреплённая площадка (режим multi-instance).
FIXED_DEALER_ID = (os.environ.get("MAXPOSTER_DEALER_ID") or "").strip()
INSTANCE_LABEL = (os.environ.get("INSTANCE_LABEL") or "").strip()
_STARTED_AT = datetime.utcnow().isoformat()
_PID = os.getpid()
_instance_worker = None

_outcome_lock = threading.Lock()
_reload_lock = threading.Lock()
_bid_lock = threading.Lock()


class _OutcomeWorker:
    """
    Один поток для Playwright: session живёт между лотами, без перелогина.
    Вызовы из HTTP-потоков сериализуются через очередь.
    """

    def __init__(self):
        import queue as queue_mod

        self._queue = queue_mod.Queue()
        self._thread = threading.Thread(target=self._loop, name="outcome-worker", daemon=True)
        self._thread.start()
        self._pw = None
        self._browser = None
        self._ctx = None
        self._page = None
        self._email = None
        self._dealer_id = None
        # Сессия Maxposter — в каталоге инстанса, не в общем бандле.
        self._script_dir = HERE

    def _close(self):
        for obj, meth in (
            (self._page, "close"),
            (self._ctx, "close"),
            (self._browser, "close"),
            (self._pw, "stop"),
        ):
            if obj is None:
                continue
            try:
                getattr(obj, meth)()
            except Exception:
                pass
        self._page = self._ctx = self._browser = self._pw = None
        self._email = self._dealer_id = None

    def _ensure(self, email: str, password: str, dealer_id: str):
        import script_outcome as so

        need_new = (
            self._page is None
            or self._email != email
            or str(self._dealer_id or "") != str(dealer_id or "")
        )
        if not need_new:
            return
        self._close()
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=True)
        self._ctx = self._browser.new_context(user_agent=so.USER_AGENT, locale="ru-RU")
        self._page = self._ctx.new_page()
        so._ensure_session(self._page, self._ctx, email, password, dealer_id, self._script_dir)
        self._email = email
        self._dealer_id = dealer_id

    def _run_one(self, job: dict) -> dict:
        import script_outcome as so
        from maxposter_session import MaxposterAuthError, clear_session

        email = job["email"]
        password = job["password"]
        dealer_id = job.get("dealer_id") or ""
        portal_base = job.get("portal_base") or "https://ah.kors-group.com"
        item = job["item"]

        os.environ["PORTAL_BASE"] = portal_base.rstrip("/")
        os.environ["APP_DIR"] = HERE
        os.environ["MAXPOSTER_EMAIL"] = email
        os.environ["MAXPOSTER_PASSWORD"] = password
        if dealer_id:
            os.environ["MAXPOSTER_DEALER_ID"] = str(dealer_id)

        # stdout/stderr скрипта — только в буфер: в CMD не пишем,
        # детали для viewer уже в row.msg / JSON ответа API.
        buf_out = io.StringIO()
        buf_err = io.StringIO()
        try:
            with redirect_stdout(buf_out), redirect_stderr(buf_err):
                self._ensure(email, password, dealer_id)
                return so.process_item(self._page, item, idx=1, total=1)
        except MaxposterAuthError:
            if dealer_id:
                clear_session(self._script_dir, email, dealer_id)
            self._close()
            raise
        except Exception:
            try:
                if self._page is not None and self._page.is_closed():
                    self._close()
            except Exception:
                self._close()
            raise

    def _loop(self):
        while True:
            job, box = self._queue.get()
            try:
                box["result"] = self._run_one(job)
                box["error"] = None
            except Exception as exc:
                box["result"] = None
                box["error"] = exc
            finally:
                box["done"].set()

    def poll_one(self, *, email: str, password: str, dealer_id: str, portal_base: str, item: dict, timeout: float = 180):
        done = threading.Event()
        box = {"done": done, "result": None, "error": None}
        self._queue.put((
            {
                "email": email,
                "password": password,
                "dealer_id": dealer_id,
                "portal_base": portal_base,
                "item": item,
            },
            box,
        ))
        if not done.wait(timeout):
            raise TimeoutError(f"Таймаут опроса одного лота ({int(timeout)} сек)")
        if box["error"] is not None:
            raise box["error"]
        return box["result"]


_outcome_session = _OutcomeWorker()


class _ScriptResult:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _run_script_module(module_name: str, env: dict) -> _ScriptResult:
    old_env = os.environ.copy()
    buf_out = io.StringIO()
    buf_err = io.StringIO()
    try:
        os.environ.update(env)
        os.environ["APP_DIR"] = HERE
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            if module_name == "script_auction":
                import script_auction

                script_auction.main()
            elif module_name == "script_bid":
                import script_bid

                script_bid.main()
            elif module_name == "script_outcome":
                import script_outcome

                script_outcome.main()
            else:
                raise RuntimeError(f"Unknown module: {module_name}")
        return _ScriptResult(0, buf_out.getvalue(), buf_err.getvalue())
    except SystemExit as e:
        code = int(e.code) if isinstance(e.code, int) else 1
        return _ScriptResult(code, buf_out.getvalue(), buf_err.getvalue())
    except Exception as e:
        err = buf_err.getvalue() + f"\n{e}"
        return _ScriptResult(1, buf_out.getvalue(), err)
    finally:
        os.environ.clear()
        os.environ.update(old_env)


def _script_subprocess_env(env: dict) -> dict:
    """UTF-8 для stdout/stderr дочернего Python на Windows."""
    out = env.copy()
    out.setdefault("PYTHONIOENCODING", "utf-8")
    out.setdefault("PYTHONUTF8", "1")
    return out


def _run_script(script_path: str, module_name: str, env: dict, *, timeout: int = 600) -> _ScriptResult:
    env = dict(env)
    env.setdefault("APP_DIR", HERE)
    if is_frozen():
        return _run_script_module(module_name, env)
    run_env = _script_subprocess_env(env)
    try:
        proc = subprocess.run(
            [sys.executable, script_path],
            cwd=HERE,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=run_env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or "") if e.stdout else ""
        err = (e.stderr or "") if e.stderr else ""
        err = f"{err}\nТаймаут {timeout} сек.".strip()
        return _ScriptResult(1, out, err)
    return _ScriptResult(proc.returncode, proc.stdout or "", proc.stderr or "")


_status_lock = threading.Lock()


def _empty_dump(dealer_id: str | None = None) -> dict:
    did = None
    if dealer_id:
        did = int(dealer_id) if str(dealer_id).isdigit() else dealer_id
    return {
        "ts": datetime.utcnow().isoformat(),
        "totalOffers": 0,
        "offers": [],
        "dealerId": did,
    }


def _read_dump_meta() -> dict:
    if not os.path.exists(OUT_JSON):
        return {"count": None, "ts": None, "dealerId": None}
    try:
        with open(OUT_JSON, encoding="utf-8") as f:
            data = json.load(f)
        offers = data.get("offers") or []
        return {
            "count": len(offers),
            "ts": data.get("ts"),
            "dealerId": data.get("dealerId"),
        }
    except Exception:
        return {"count": None, "ts": None, "dealerId": None}


def _load_dealer_status() -> dict:
    if not os.path.exists(DEALERS_STATUS_JSON):
        return {}
    try:
        with open(DEALERS_STATUS_JSON, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_dealer_status(data: dict):
    with open(DEALERS_STATUS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _update_dealer_status_from_reload(
    dealer_id: str,
    ok: bool,
    error: str | None = None,
    count: int | None = None,
) -> dict:
    ts = datetime.utcnow().isoformat()
    meta = _read_dump_meta()
    if count is None:
        count = meta.get("count")
    entry = {
        "dealerId": str(dealer_id),
        "ok": bool(ok),
        "ts": ts,
        "count": count,
        "fileTs": meta.get("ts"),
        "error": (error or "")[:500] if not ok else None,
    }
    with _status_lock:
        data = _load_dealer_status()
        data[str(dealer_id)] = entry
        _save_dealer_status(data)
    return entry


def _dealers_status_payload() -> dict:
    meta = _read_dump_meta()
    dealer_id = FIXED_DEALER_ID or meta.get("dealerId")
    status = _load_dealer_status()
    entry = status.get(str(dealer_id)) if dealer_id is not None else {}
    entry = entry or {}
    dealers = []
    if dealer_id is not None:
        dealers.append(
            {
                "dealerId": str(dealer_id),
                "ok": entry.get("ok", True),
                "ts": entry.get("ts"),
                "count": meta.get("count") if meta.get("count") is not None else entry.get("count"),
                "fileTs": meta.get("ts"),
                "error": entry.get("error"),
            }
        )
    return {"ok": True, "dealers": dealers, "dealerId": dealer_id}


def _resolve_dealer_id(body_dealer: str | None = None) -> str:
    if FIXED_DEALER_ID:
        return FIXED_DEALER_ID
    return str(body_dealer or "").strip()


def _auth_from_body(body: dict) -> tuple[str, str]:
    email = str(body.get("email") or "").strip() or (os.environ.get("MAXPOSTER_EMAIL") or "").strip()
    password = str(body.get("password") or "") or (os.environ.get("MAXPOSTER_PASSWORD") or "")
    return email, password


def _instance_payload() -> dict:
    meta = _read_dump_meta()
    dealer_id = FIXED_DEALER_ID or meta.get("dealerId")
    status = _load_dealer_status()
    entry = status.get(str(dealer_id)) if dealer_id is not None else {}
    entry = entry or {}
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8005"))
    return {
        "ok": True,
        "alive": True,
        "pid": _PID,
        "startedAt": _STARTED_AT,
        "host": host,
        "port": port,
        "url": f"http://{host}:{port}/viewer.html",
        "instanceDir": HERE,
        "lockedDealerId": FIXED_DEALER_ID or None,
        "label": INSTANCE_LABEL or None,
        "dealerId": str(dealer_id) if dealer_id is not None else None,
        "offersCount": meta.get("count"),
        "fileTs": meta.get("ts"),
        "lastReloadOk": entry.get("ok"),
        "lastReloadTs": entry.get("ts"),
        "lastReloadError": entry.get("error"),
        "busy": {
            "reload": _reload_lock.locked(),
            "bid": _bid_lock.locked(),
            "outcome": _outcome_lock.locked(),
        },
        "emailConfigured": bool((os.environ.get("MAXPOSTER_EMAIL") or "").strip()),
        "email": (os.environ.get("MAXPOSTER_EMAIL") or "").strip() or None,
        "portalBase": (os.environ.get("PORTAL_BASE") or os.environ.get("PORTAL_BASE_URL") or "").rstrip("/") or None,
        "worker": (_instance_worker.status() if _instance_worker else {
            "enabled": False,
            "intervalSec": 0,
            "running": False,
        }),
    }


def _reload_script_outcome(proc: _ScriptResult, out_path: str) -> dict:
    """Итог запуска script_auction: ok, skipped, auth_skip, error."""
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    auth_skip = "SKIP_AUTH:" in stdout
    skipped = ("SKIP:" in stdout) and not auth_skip
    ok = proc.returncode == 0 and os.path.exists(out_path) and not auth_skip
    err = None
    if auth_skip:
        for line in stdout.splitlines():
            if "SKIP_AUTH:" in line:
                err = line.strip()
                break
        err = err or "SKIP_AUTH: HTTP 403"
        skipped = True
    elif not ok:
        err = (stderr or stdout or f"exit code {proc.returncode}")[-2000:]
    return {
        "ok": ok,
        "skipped": skipped,
        "auth_skip": auth_skip,
        "error": err,
    }


def _offer_count() -> int | None:
    if not os.path.exists(OUT_JSON):
        return None
    try:
        with open(OUT_JSON, encoding="utf-8") as f:
            data = json.load(f)
        offers = data.get("offers") or []
        return len(offers)
    except Exception:
        return None


def _clear_offers_dump(dealer_id: str | None = None) -> dict:
    out = _empty_dump(dealer_id)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return out


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=HERE, **kwargs)

    def do_GET(self):
        if self.path in {"", "/"}:
            self.send_response(302)
            self.send_header("Location", "/viewer.html")
            self.end_headers()
            return
        route = self.path.split("?", 1)[0].rstrip("/")
        if route == "/api/dealers/status":
            self._send_json(200, _dealers_status_payload())
            return
        if route in {"/api/instance", "/api/health"}:
            self._send_json(200, _instance_payload())
            return
        return super().do_GET()

    def log_message(self, format, *args):
        # HTTP access-лог в CMD не нужен — ход работы смотрим во viewer («Лог обновлений»).
        return

    def _send_json(self, code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(code)
            self.send_header("content-type", "application/json; charset=utf-8")
            self.send_header("content-length", str(len(body)))
            self.send_header("cache-control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            # Клиент закрыл вкладку / оборвал fetch по таймауту — это не ошибка скрипта.
            return

    def _read_json_body(self):
        content_len = int(self.headers.get("content-length", "0") or "0")
        raw_body = self.rfile.read(content_len) if content_len > 0 else b""
        if not raw_body:
            return {}
        return json.loads(raw_body.decode("utf-8"))

    @staticmethod
    def _to_bool(v, default=True):
        if v is None:
            return default
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        if s in {"1", "true", "yes", "y", "on"}:
            return True
        if s in {"0", "false", "no", "n", "off"}:
            return False
        return default

    def do_POST(self):
        route = self.path.rstrip("/")
        if route not in {"/api/reload", "/api/bid", "/api/clear_lots", "/api/outcomes"}:
            self._send_json(404, {"ok": False, "error": "Not found"})
            return

        try:
            body = self._read_json_body()
        except Exception:
            self._send_json(400, {"ok": False, "error": "Invalid JSON body"})
            return

        if route == "/api/clear_lots":
            dealer_id = _resolve_dealer_id(body.get("dealerId")) or None
            try:
                out = _clear_offers_dump(dealer_id)
                self._send_json(200, {
                    "ok": True,
                    "totalOffers": 0,
                    "dealerId": out.get("dealerId"),
                    "ts": out.get("ts"),
                })
            except Exception as e:
                self._send_json(500, {"ok": False, "error": str(e)[:500]})
            return

        email, password = _auth_from_body(body)

        if route == "/api/reload":
            if not email or not password:
                self._send_json(200, {"ok": False, "skipped": True, "reason": "no_auth", "error": "email and password are required"})
                return
            dealer_id = _resolve_dealer_id(body.get("dealerId"))
            if not dealer_id:
                self._send_json(200, {"ok": False, "skipped": True, "reason": "no_dealer", "error": "dealerId is required"})
                return
        elif not email or not password:
            self._send_json(400, {"ok": False, "error": "email and password are required"})
            return

        env = os.environ.copy()
        env["MAXPOSTER_EMAIL"] = email
        env["MAXPOSTER_PASSWORD"] = password
        dealer_id = _resolve_dealer_id(body.get("dealerId"))
        if dealer_id:
            env["MAXPOSTER_DEALER_ID"] = dealer_id
        env.setdefault("APP_DIR", HERE)
        portal_env = (os.environ.get("PORTAL_BASE") or os.environ.get("PORTAL_BASE_URL") or "").rstrip("/")
        if portal_env:
            env.setdefault("PORTAL_BASE", portal_env)

        if route == "/api/reload":
            if not is_frozen() and not os.path.exists(SCRIPT_PATH):
                self._send_json(500, {"ok": False, "error": f"Script not found: {SCRIPT_PATH}"})
                return
            if not _reload_lock.acquire(blocking=False):
                self._send_json(409, {"ok": False, "error": "Reload already running"})
                return
            try:
                env["OUT_PATH"] = OUT_JSON
                proc = _run_script(SCRIPT_PATH, "script_auction", env)
                outcome = _reload_script_outcome(proc, OUT_JSON)
                ok = outcome["ok"]
                skipped = outcome["skipped"]
                err = outcome["error"]
                count = _offer_count()
                status_entry = _update_dealer_status_from_reload(dealer_id, ok, err, count)
                self._send_json(200, {
                    "ok": ok,
                    "skipped": skipped,
                    "auth_skip": outcome["auth_skip"],
                    "error": err,
                    "returncode": proc.returncode,
                    "stdout": (proc.stdout or "")[-8000:],
                    "stderr": (proc.stderr or "")[-8000:],
                    "out_exists": os.path.exists(OUT_JSON),
                    "out_path": OUT_JSON,
                    "dealerId": dealer_id,
                    "count": count if ok else status_entry.get("count"),
                    "ts": status_entry.get("ts"),
                })
            finally:
                _reload_lock.release()
            return

        if route == "/api/outcomes":
            if not is_frozen() and not os.path.exists(SCRIPT_OUTCOME_PATH):
                self._send_json(500, {"ok": False, "error": f"Script not found: {SCRIPT_OUTCOME_PATH}"})
                return
            if not _outcome_lock.acquire(blocking=False):
                self._send_json(409, {"ok": False, "error": "Outcome poll already running"})
                return
            try:
                portal_base = str(body.get("portalBase") or env.get("PORTAL_BASE") or "").rstrip("/")
                items = body.get("items") if isinstance(body.get("items"), list) else None

                # Предпочтительный режим: один лот — живая сессия Playwright без перелогина.
                if items is not None:
                    if not items:
                        self._send_json(200, {
                            "ok": True,
                            "outcome_result": {
                                "ok": True,
                                "count": 0,
                                "okCount": 0,
                                "results": [],
                                "reason": "empty",
                            },
                        })
                        return
                    item = items[0]
                    try:
                        row = _outcome_session.poll_one(
                            email=email,
                            password=password,
                            dealer_id=dealer_id,
                            portal_base=portal_base or "https://ah.kors-group.com",
                            item=item,
                        )
                        ok = bool(row.get("ok"))
                        self._send_json(200 if ok else 500, {
                            "ok": ok,
                            "outcome_result": {
                                "ok": ok,
                                "count": 1,
                                "okCount": 1 if ok else 0,
                                "results": [row],
                                "summary": {
                                    "total": 1,
                                    "ok": 1 if ok else 0,
                                    "fail": 0 if ok else 1,
                                    "becameWon": 1 if (row.get("portal") or {}).get("becameWon") else 0,
                                    "byOutcome": {
                                        ((row.get("portal") or {}).get("outcomeCode") or ("error" if not ok else "unknown")): 1
                                    },
                                },
                            },
                            "error": None if ok else (row.get("error") or row.get("msg")),
                        })
                    except Exception as exc:
                        self._send_json(500, {
                            "ok": False,
                            "error": str(exc)[:500],
                            "outcome_result": {
                                "ok": False,
                                "count": 1,
                                "okCount": 0,
                                "results": [{
                                    "ok": False,
                                    "lotOfferId": item.get("lotOfferId"),
                                    "lotId": item.get("lotId"),
                                    "car": item.get("car") or "",
                                    "error": str(exc)[:300],
                                    "msg": f"лот {item.get('lotId')}: ошибка — {str(exc)[:200]}",
                                }],
                            },
                        })
                    return

                # Legacy batch (весь скрипт целиком) — оставлен на всякий случай.
                limit = body.get("limit", 5)
                try:
                    limit = max(1, min(20, int(limit)))
                except (TypeError, ValueError):
                    limit = 5
                if portal_base:
                    env["PORTAL_BASE"] = portal_base
                env["OUTCOME_LIMIT"] = str(limit)
                proc = _run_script(SCRIPT_OUTCOME_PATH, "script_outcome", env, timeout=600)
                result_payload = None
                for line in reversed((proc.stdout or "").splitlines()):
                    line = line.strip()
                    if not line.startswith("{"):
                        continue
                    try:
                        candidate = json.loads(line)
                    except Exception:
                        continue
                    if "results" in candidate or "count" in candidate or candidate.get("ok") is not None:
                        result_payload = candidate
                        break
                ok = proc.returncode == 0 and bool(result_payload and result_payload.get("ok") is not False)
                if result_payload is None and proc.returncode != 0:
                    err_tail = ((proc.stderr or "") + "\n" + (proc.stdout or "")).strip()[-500:]
                    result_payload = {"ok": False, "error": err_tail or f"script exit {proc.returncode}"}
                self._send_json(200 if ok else 500, {
                    "ok": ok,
                    "returncode": proc.returncode,
                    "stdout": (proc.stdout or "")[-8000:],
                    "stderr": (proc.stderr or "")[-4000:],
                    "outcome_result": result_payload or {},
                    "error": None if ok else (result_payload or {}).get("error") or (proc.stderr or "")[-400:],
                })
            finally:
                _outcome_lock.release()
            return

        if not is_frozen() and not os.path.exists(SCRIPT_BID_PATH):
            self._send_json(500, {"ok": False, "error": f"Script not found: {SCRIPT_BID_PATH}"})
            return
        # Ждём освобождения предыдущей ставки (сериализация Playwright), а не 409 сразу.
        bid_wait_sec = float(os.environ.get("BID_LOCK_WAIT_SEC", "180") or "180")
        if not _bid_lock.acquire(blocking=True, timeout=max(1.0, bid_wait_sec)):
            self._send_json(409, {"ok": False, "error": "Bid already running"})
            return
        try:
            lot_offer_id = str(body.get("lotOfferId") or "").strip()
            lot_id = str(body.get("lotId") or "").strip()
            if not lot_offer_id:
                self._send_json(400, {"ok": False, "error": "lotOfferId is required"})
                return
            if not lot_id:
                self._send_json(400, {"ok": False, "error": "lotId is required"})
                return
            dry_run = self._to_bool(body.get("dryRun", True), default=True)
            bid_amount = body.get("bidAmount", None)
            bid_payload = body.get("bidPayload", None)
            env["LOT_OFFER_ID"] = lot_offer_id
            env["LOT_ID"] = lot_id
            env["DRY_RUN"] = "1" if dry_run else "0"
            if bid_amount is not None and str(bid_amount).strip() != "":
                env["BID_AMOUNT"] = str(bid_amount).strip()
            if isinstance(bid_payload, dict):
                env["BID_PAYLOAD_JSON"] = json.dumps(bid_payload, ensure_ascii=False)
            proc = _run_script(SCRIPT_BID_PATH, "script_bid", env)
            result_payload = None
            for line in reversed((proc.stdout or "").splitlines()):
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    result_payload = json.loads(line)
                    break
                except Exception:
                    continue
            ok = proc.returncode == 0 and bool(result_payload and result_payload.get("ok"))
            self._send_json(200 if ok else 500, {
                "ok": ok,
                "error": (result_payload or {}).get("note"),
                "returncode": proc.returncode,
                "stdout": (proc.stdout or "")[-12000:],
                "stderr": (proc.stderr or "")[-8000:],
                "bid_result": result_payload or {},
            })
        finally:
            _bid_lock.release()


def main():
    global _instance_worker
    ensure_runtime_files(HERE)
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8005"))
    ThreadingHTTPServer.allow_reuse_address = True
    try:
        httpd = ThreadingHTTPServer((host, port), Handler)
    except OSError as e:
        print(f"Не удалось запустить сервер на http://{host}:{port}: {e}")
        print("Закройте другой процесс или задайте другой PORT, например PORT=8006")
        raise SystemExit(1) from e
    url = f"http://{host}:{port}/viewer.html"
    label = INSTANCE_LABEL or FIXED_DEALER_ID or "default"
    print(f"Serving on {url}")
    if FIXED_DEALER_ID:
        print(f"Инстанс: {label} · dealerId={FIXED_DEALER_ID} · dir={HERE}")
    print("Не закрывайте это окно, пока работает эта площадка.")

    try:
        from worker_loop import start_worker_if_configured

        _instance_worker = start_worker_if_configured(OUT_JSON)
    except Exception as exc:
        print(f"[worker] не удалось стартовать фон: {exc}", flush=True)

    httpd.serve_forever()


if __name__ == "__main__":
    main()
