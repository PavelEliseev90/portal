"""
Хаб мониторинга воркеров Maxposter Auction.
Порт по умолчанию: 8005 (из instances.json → hubPort).
Не запускает Playwright — только опрашивает /api/instance у инстансов.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from app_paths import bundle_dir, ensure_runtime_files, root_dir

ROOT = root_dir()
INSTANCES_JSON = os.path.join(ROOT, "instances.json")
EXAMPLE_JSON = os.path.join(ROOT, "instances.example.json")


def _load_config() -> dict:
    path = INSTANCES_JSON if os.path.exists(INSTANCES_JSON) else EXAMPLE_JSON
    if not os.path.exists(path):
        return {"hubPort": 8005, "instances": []}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"hubPort": 8005, "instances": []}
    except Exception:
        return {"hubPort": 8005, "instances": []}


def _probe_worker(item: dict, timeout: float = 2.5) -> dict:
    dealer_id = str(item.get("dealerId") or "").strip()
    label = str(item.get("label") or dealer_id).strip()
    port = int(item.get("port") or 0)
    enabled = item.get("enabled", True) is not False
    base = {
        "dealerId": dealer_id,
        "label": label,
        "port": port,
        "enabled": enabled,
        "url": f"http://127.0.0.1:{port}/viewer.html" if port else None,
        "alive": False,
        "error": None,
    }
    if not enabled:
        base["error"] = "disabled"
        return base
    if not port:
        base["error"] = "no_port"
        return base
    url = f"http://127.0.0.1:{port}/api/instance"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw) if raw else {}
        if not isinstance(data, dict):
            base["error"] = "bad_payload"
            return base
        base.update({
            "alive": True,
            "pid": data.get("pid"),
            "startedAt": data.get("startedAt"),
            "offersCount": data.get("offersCount"),
            "fileTs": data.get("fileTs"),
            "lastReloadOk": data.get("lastReloadOk"),
            "lastReloadTs": data.get("lastReloadTs"),
            "lastReloadError": data.get("lastReloadError"),
            "busy": data.get("busy") or {},
            "instanceDir": data.get("instanceDir"),
            "lockedDealerId": data.get("lockedDealerId") or dealer_id,
            "emailConfigured": data.get("emailConfigured"),
            "worker": data.get("worker") or {},
        })
        return base
    except urllib.error.URLError as exc:
        base["error"] = f"offline: {exc.reason if hasattr(exc, 'reason') else exc}"
        return base
    except Exception as exc:
        base["error"] = f"offline: {exc}"[:200]
        return base


def _workers_payload() -> dict:
    cfg = _load_config()
    items = cfg.get("instances") or []
    if not isinstance(items, list):
        items = []
    workers = []
    with ThreadPoolExecutor(max_workers=min(16, max(1, len(items) or 1))) as pool:
        futs = {pool.submit(_probe_worker, it): it for it in items if isinstance(it, dict)}
        for fut in as_completed(futs):
            workers.append(fut.result())
    workers.sort(key=lambda w: (not w.get("enabled", True), int(w.get("port") or 0), str(w.get("dealerId") or "")))
    alive = sum(1 for w in workers if w.get("alive"))
    enabled = sum(1 for w in workers if w.get("enabled", True))
    return {
        "ok": True,
        "hubPort": int(cfg.get("hubPort") or 8005),
        "configPath": INSTANCES_JSON if os.path.exists(INSTANCES_JSON) else EXAMPLE_JSON,
        "total": len(workers),
        "enabled": enabled,
        "alive": alive,
        "workers": workers,
        "ts": __import__("datetime").datetime.utcnow().isoformat(),
    }


class HubHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=bundle_dir(), **kwargs)

    def log_message(self, format, *args):
        return

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in {"", "/"}:
            self.send_response(302)
            self.send_header("Location", "/monitor.html")
            self.end_headers()
            return
        if path.rstrip("/") == "/api/workers":
            body = json.dumps(_workers_payload(), ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("content-type", "application/json; charset=utf-8")
            self.send_header("content-length", str(len(body)))
            self.send_header("cache-control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()


def main():
    ensure_runtime_files(ROOT)
    # monitor.html лежит в бандле — копировать не обязательно, HubHandler читает bundle_dir
    cfg = _load_config()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("HUB_PORT") or cfg.get("hubPort") or 8005)
    ThreadingHTTPServer.allow_reuse_address = True
    try:
        httpd = ThreadingHTTPServer((host, port), HubHandler)
    except OSError as e:
        print(f"Не удалось запустить хаб на http://{host}:{port}: {e}")
        raise SystemExit(1) from e
    print(f"Monitor hub: http://{host}:{port}/monitor.html")
    print("Не закрывайте это окно, пока нужен мониторинг воркеров.")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
