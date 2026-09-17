#!/usr/bin/env python
"""
Удобный запуск выгрузки данных в MyKors прямо из корня проекта.
Запуск:
    python export_to_mykors.py
"""
import os
import sys

# Добавляем пути в PYTHONPATH
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORTAL_DIR = os.path.join(BASE_DIR, 'portal')
sys.path.insert(0, PORTAL_DIR)
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'portal.settings')

import django
django.setup()

from django.core.management import call_command

if __name__ == '__main__':
    args = sys.argv[1:]
    call_command('mykors_export', *args)
