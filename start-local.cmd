@echo off
setlocal
cd /d "%~dp0"
python -X utf8 scripts\start_local.py
if errorlevel 1 pause
endlocal
