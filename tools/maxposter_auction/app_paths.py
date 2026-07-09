import os
import shutil
import sys

_RUNTIME_FILES = ("viewer.html",)


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_dir() -> str:
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def bundle_dir() -> str:
    if is_frozen():
        return getattr(sys, "_MEIPASS", app_dir())
    return app_dir()


def resource_path(name: str) -> str:
    return os.path.join(bundle_dir(), name)


def ensure_runtime_files() -> None:
    os.makedirs(app_dir(), exist_ok=True)
    for name in _RUNTIME_FILES:
        src = resource_path(name)
        dst = os.path.join(app_dir(), name)
        if os.path.exists(src):
            if not os.path.exists(dst):
                shutil.copy2(src, dst)
