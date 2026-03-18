@echo off
REM Если нужно свернутое окно
start /min python D:\kors_group\portal\manage.py process_tasks --queue refresh_avtoteka --duration 1