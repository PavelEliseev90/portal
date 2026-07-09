"""
Точка входа для сборки в exe (PyInstaller).
Запуск: python launcher.py  или  dist/AuctionViewer.exe
"""
import os
import sys
import threading
import time
import webbrowser


def _ensure_playwright_chromium() -> None:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return
    except Exception:
        pass

    print("Chromium для Playwright не найден. Пробуем установить (нужен интернет)…")
    try:
        from playwright.__main__ import main as playwright_cli

        old_argv = sys.argv
        sys.argv = ["playwright", "install", "chromium"]
        playwright_cli()
        sys.argv = old_argv
        print("Chromium установлен.")
    except Exception as e:
        print(f"Не удалось установить Chromium: {e}")
        print("На этом ПК один раз выполните: playwright install chromium")


def _open_browser(port: int) -> None:
    time.sleep(1.2)
    webbrowser.open(f"http://127.0.0.1:{port}/viewer.html")


def main() -> None:
    from app_paths import ensure_runtime_files, is_frozen

    ensure_runtime_files()

    _ensure_playwright_chromium()

    port = int(os.environ.get("PORT", "8005"))
    if is_frozen():
        threading.Thread(target=_open_browser, args=(port,), daemon=True).start()

    import server

    server.main()


if __name__ == "__main__":
    main()
