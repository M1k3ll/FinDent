@echo off
cd /d "%~dp0"
echo ==== Findent first-time setup ====
where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.11 or newer from python.org
  echo and tick "Add python.exe to PATH" during installation. Then run this file again.
  pause
  exit /b 1
)
if not exist venv python -m venv venv
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
  echo Package installation failed. Check the internet connection and try again.
  pause
  exit /b 1
)
python manage.py makemigrations patients
python manage.py migrate
python manage.py collectstatic --noinput
echo.
echo Now create the manager account (username and password of your choice).
python manage.py createsuperuser
echo.
echo Setup finished. Start the program with start.bat
pause
