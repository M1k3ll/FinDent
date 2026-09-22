@echo off
cd /d "%~dp0"
netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul
if not errorlevel 1 (
  start "" http://localhost:8000
  exit /b
)
call venv\Scripts\activate.bat
set FINDENT_OPEN_BROWSER=1
python serve.py
pause
