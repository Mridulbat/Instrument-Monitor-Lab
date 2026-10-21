@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
  py -3 src\server.py
) else (
  python src\server.py
)
pause
