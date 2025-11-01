@echo off
REM Пример выполнения команды генерации уведомлений через планировщик задач Windows
REM Запускать каждые 10-15 минут

cd /d D:\portal_kg\portal_kg
python manage.py generate_preparation_notifications

