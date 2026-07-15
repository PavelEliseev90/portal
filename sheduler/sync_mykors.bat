@echo off
REM Постановка задачи выгрузки стока в MyKors + обработка очереди mykors_sync
REM Планировщик: раз в 15–30 минут. На нагрузку портала почти не влияет (отдельный процесс).

cd /d D:\kors_group\portal
python manage.py mykors_export_stock --queue
python manage.py process_tasks --queue mykors_sync --duration 100
