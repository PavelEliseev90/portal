"""
Запуск нескольких изолированных инстансов (по площадке) + хаб мониторинга.

Каждый инстанс:
  - свой PORT
  - свой INSTANCE_DIR (offers_dump, session, status)
  - свой Playwright / cookies
  - зафиксированный MAXPOSTER_DEALER_ID

Конфиг: instances.json (см. instances.example.json)
Логин/пароль: .env (MAXPOSTER_EMAIL / MAXPOSTER_PASSWORD)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INSTANCES_JSON = ROOT / "instances.json"
EXAMPLE_JSON = ROOT / "instances.example.json"
ENV_FILE = ROOT / ".env"


def _load_dotenv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key:
            out[key] = val
    return out


def _load_config() -> dict:
    path = INSTANCES_JSON if INSTANCES_JSON.exists() else EXAMPLE_JSON
    if not path.exists():
        raise SystemExit(
            f"Нет {INSTANCES_JSON.name}. Скопируйте instances.example.json → instances.json и отметьте площадки."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("instances.json: ожидается объект JSON")
    return data


def _base_env(dotenv: dict) -> dict:
    env = os.environ.copy()
    env.update(dotenv)
    # Унифицируем имя портала
    portal = (env.get("PORTAL_BASE") or env.get("PORTAL_BASE_URL") or "https://ah.kors-group.com").rstrip("/")
    env["PORTAL_BASE"] = portal
    env["PORTAL_BASE_URL"] = portal
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def _spawn(cmd: list[str], env: dict, title: str) -> subprocess.Popen:
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_CONSOLE  # отдельное окно на воркер
        # Заголовок окна через start не нужен — print в server.main
    return subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env=env,
        creationflags=creationflags,
    )


def main() -> None:
    from app_paths import ensure_runtime_files

    ensure_runtime_files(str(ROOT))
    cfg = _load_config()
    dotenv = _load_dotenv(ENV_FILE)
    if not dotenv.get("MAXPOSTER_EMAIL") or not dotenv.get("MAXPOSTER_PASSWORD"):
        print("Внимание: в .env нет MAXPOSTER_EMAIL / MAXPOSTER_PASSWORD — укажите логин в каждом viewer.")

    base = _base_env(dotenv)
    hub_port = int(os.environ.get("HUB_PORT") or cfg.get("hubPort") or 8005)
    portal = base.get("PORTAL_BASE") or "https://ah.kors-group.com"

    instances = [it for it in (cfg.get("instances") or []) if isinstance(it, dict) and it.get("enabled", True) is not False]
    if not instances:
        raise SystemExit("В instances.json нет enabled-площадок.")

    procs: list[subprocess.Popen] = []

    # 1) Хаб мониторинга
    hub_env = base.copy()
    hub_env["HUB_PORT"] = str(hub_port)
    hub_env["PORT"] = str(hub_port)
    print(f"Старт хаба мониторинга :{hub_port}")
    procs.append(_spawn([sys.executable, str(ROOT / "hub_server.py")], hub_env, f"hub:{hub_port}"))

    # 2) Воркеры
    for it in instances:
        dealer_id = str(it.get("dealerId") or "").strip()
        port = int(it.get("port") or 0)
        label = str(it.get("label") or dealer_id).strip()
        if not dealer_id or not port:
            print(f"Пропуск записи без dealerId/port: {it}")
            continue
        if port == hub_port:
            print(f"Пропуск dealer {dealer_id}: порт {port} занят хабом")
            continue

        instance_dir = ROOT / "instances" / dealer_id
        instance_dir.mkdir(parents=True, exist_ok=True)
        ensure_runtime_files(str(instance_dir))

        env = base.copy()
        env["PORT"] = str(port)
        env["HOST"] = "127.0.0.1"
        env["MAXPOSTER_DEALER_ID"] = dealer_id
        env["INSTANCE_DIR"] = str(instance_dir)
        env["INSTANCE_LABEL"] = label
        env["APP_DIR"] = str(instance_dir)
        env["PORTAL_BASE"] = str(it.get("portalBase") or portal).rstrip("/")
        # Фоновый цикл без браузера (reload + calc/ставки + итоги)
        env.setdefault("WORKER_INTERVAL_SEC", str(it.get("workerIntervalSec") or 180))
        env.setdefault("WORKER_AUTO_BID", "1" if it.get("workerAutoBid", True) else "0")
        env.setdefault("WORKER_OUTCOMES", "1" if it.get("workerOutcomes", True) else "0")

        print(f"Старт воркера {label} dealer={dealer_id} :{port} → {instance_dir}")
        procs.append(_spawn([sys.executable, str(ROOT / "server.py")], env, f"{dealer_id}:{port}"))

    def _open_browser():
        time.sleep(1.4)
        webbrowser.open(f"http://127.0.0.1:{hub_port}/monitor.html")

    threading.Thread(target=_open_browser, daemon=True).start()

    print()
    print(f"Мониторинг: http://127.0.0.1:{hub_port}/monitor.html")
    print("Каждая площадка — в своём окне CMD. Закрытие окна = остановка этой площадки.")
    print("Это окно (launcher) можно свернуть; для остановки всех закройте окна воркеров и хаба.")
    print("Ctrl+C здесь — только выход launcher (дочерние процессы продолжат работу).")
    try:
        while True:
            time.sleep(2)
            alive = sum(1 for p in procs if p.poll() is None)
            if alive == 0:
                print("Все дочерние процессы завершились.")
                break
    except KeyboardInterrupt:
        print("\nLauncher остановлен (воркеры в отдельных окнах продолжают работу).")


if __name__ == "__main__":
    main()
