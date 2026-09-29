#!/usr/bin/env python
"""
Универсальный запуск выгрузки данных в MyKors.
Автоматически использует виртуальное окружение .venv проекта.

Запуск:
    python export_to_mykors.py
    ./export_to_mykors.py
"""
# import os
# import sys

# REAL_FILE = os.path.realpath(__file__)
# BASE_DIR = os.path.dirname(REAL_FILE)
# VENV_PYTHON = os.path.join(BASE_DIR, '.venv', 'bin', 'python')

# # По умолчанию для локальной машины используем порт 5433 (дамп базы портала)
# os.environ.setdefault('LOCAL_DB_PORT', '5433')

# # Если запуск выполнен не из виртуального окружения проекта, автоматически перезапускаем через .venv
# if os.path.exists(VENV_PYTHON) and os.path.realpath(sys.executable) != os.path.realpath(VENV_PYTHON):
#     os.execv(VENV_PYTHON, [VENV_PYTHON, REAL_FILE] + sys.argv[1:])

# # Добавляем пути проекта в sys.path
# PORTAL_DIR = os.path.join(BASE_DIR, 'portal')
# if PORTAL_DIR not in sys.path:
#     sys.path.insert(0, PORTAL_DIR)
# if BASE_DIR not in sys.path:
#     sys.path.insert(0, BASE_DIR)

# # Переключаем рабочий каталог на корень проекта
# os.chdir(BASE_DIR)

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'portal.settings')

# import django
# django.setup()

# from django.core.management import call_command

# if __name__ == '__main__':
#     args = sys.argv[1:]
#     call_command('mykors_export', *args)
