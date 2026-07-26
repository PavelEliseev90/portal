import os
import shutil
import sys

_RUNTIME_FILES = ("viewer.html", "dealers.js")


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def bundle_dir() -> str:
    """Каталог со скриптами / статикой (в exe — _MEIPASS)."""
    if is_frozen():
        return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
    return os.path.dirname(os.path.abspath(__file__))


def root_dir() -> str:
    """Корень инструмента (рядом с launcher / instances.json)."""
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def app_dir() -> str:
    """Рабочий каталог данных инстанса (offers_dump, session, status)."""
    instance = (os.environ.get("INSTANCE_DIR") or "").strip()
    if instance:
        return os.path.abspath(instance)
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(name: str) -> str:
    return os.path.join(bundle_dir(), name)


def ensure_runtime_files(target_dir: str | None = None) -> str:
    """Копирует viewer/dealers в целевой каталог, если их там ещё нет."""
    dest = os.path.abspath(target_dir or app_dir())
    os.makedirs(dest, exist_ok=True)
    for name in _RUNTIME_FILES:
        src = resource_path(name)
        dst = os.path.join(dest, name)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
        elif os.path.exists(src) and os.path.exists(dst):
            # Обновляем UI при изменении в бандле (по mtime)
            try:
                if os.path.getmtime(src) > os.path.getmtime(dst):
                    shutil.copy2(src, dst)
            except OSError:
                pass
    return dest
