@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Installing build dependencies...
python -m pip install -q pyinstaller playwright

echo Building AuctionViewer.exe ...
python -m PyInstaller ^
  --noconfirm ^
  --onefile ^
  --console ^
  --name AuctionViewer ^
  --add-data "viewer.html;." ^
  --hidden-import playwright ^
  --hidden-import playwright.sync_api ^
  --hidden-import script_auction ^
  --hidden-import script_bid ^
  --collect-submodules playwright ^
  launcher.py

if errorlevel 1 (
  echo Build failed.
  pause
  exit /b 1
)

echo.
echo Done: dist\AuctionViewer.exe
echo Copy dist\AuctionViewer.exe on another PC and run it.
echo On first run Chromium may download to folder pw-browsers next to exe.
echo.
pause
