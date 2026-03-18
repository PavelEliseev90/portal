@echo off
REM Если нужно свернутое окно
start /min python D:\kors_group\portal\manage.py process_tasks --queue kors_estimation_data --duration 1