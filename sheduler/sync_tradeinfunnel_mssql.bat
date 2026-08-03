@echo off
REM =============================================================================
REM Ночная выгрузка TradeInFunnel → MSSQL за последние 60 дней
REM Планировщик заданий Windows:
REM   Триггер: ежедневно в 03:00
REM   Действие: этот bat
REM   Рабочая папка: D:\kors_group\portal (или путь к репозиторию)
REM Проверка вручную:
REM   python manage.py sync_tradeinfunnel_mssql --days 60 --dry-run
REM =============================================================================

cd /d D:\kors_group\portal
python manage.py sync_tradeinfunnel_mssql --days 60
