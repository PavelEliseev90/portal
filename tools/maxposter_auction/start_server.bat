@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Starting Maxposter auction viewer...
python launcher.py
if errorlevel 1 pause
