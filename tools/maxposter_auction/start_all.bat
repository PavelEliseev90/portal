@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Starting multi-instance Maxposter auction (hub + workers)...
if not exist "instances.json" (
  echo.
  echo Нет instances.json — копирую из instances.example.json
  copy /Y "instances.example.json" "instances.json" >nul
  echo Отредактируйте instances.json: enabled=true для нужных площадок, порты.
  echo.
)
python launcher_multi.py
if errorlevel 1 pause
