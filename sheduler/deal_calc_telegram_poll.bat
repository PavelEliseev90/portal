@echo off
REM =============================================================================
REM Long polling Telegram-бота согласования КП
REM -----------------------------------------------------------------------------
REM Нужен, пока Telegram не достучится до webhook портала (Connection timed out).
REM При обрыве сети / падении python процесс перезапускается сам.
REM
REM Запуск: двойной клик или через Планировщик заданий (при старте Windows).
REM Остановка: закрыть окно или Ctrl+C.
REM =============================================================================

setlocal EnableExtensions
cd /d D:\kors_group\portal

set PYTHONUNBUFFERED=1
set RESTART_DELAY=10
set LOGDIR=D:\kors_group\portal\logs
set LOGFILE=%LOGDIR%\deal_calc_telegram_poll.log

if not exist "%LOGDIR%" mkdir "%LOGDIR%"

echo ============================================================>> "%LOGFILE%"
echo [%date% %time%] BAT started >> "%LOGFILE%"
echo Telegram KP poll watchdog. Log: %LOGFILE%
echo Ctrl+C to stop.
echo.

set FIRST_RUN=1

:loop
echo [%date% %time%] Starting deal_calc_telegram_poll...
echo [%date% %time%] Starting deal_calc_telegram_poll...>> "%LOGFILE%"

if "%FIRST_RUN%"=="1" (
  REM Снимаем webhook один раз при старте — иначе getUpdates не работает
  python manage.py deal_calc_telegram_poll --delete-webhook >> "%LOGFILE%" 2>&1
  set FIRST_RUN=0
) else (
  python manage.py deal_calc_telegram_poll >> "%LOGFILE%" 2>&1
)

set EXITCODE=%ERRORLEVEL%
echo [%date% %time%] Process exited code=%EXITCODE%. Restart in %RESTART_DELAY%s...
echo [%date% %time%] Process exited code=%EXITCODE%. Restart in %RESTART_DELAY%s...>> "%LOGFILE%"

timeout /t %RESTART_DELAY% /nobreak >nul
goto loop
