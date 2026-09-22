@echo off
:: این فایل را «Run as administrator» اجرا کن (کلیک راست روی آن -> Run as administrator).
:: کاری که انجام می‌دهد:
::  ۱) دسترسی به این پوشه (فایل‌های برنامه و دیتابیس) را فقط برای «مدیران» و SYSTEM می‌گذارد،
::     پس حساب معمولی منشی دیگر نمی‌تواند فایل‌ها را در My Computer ببیند یا باز کند.
::  ۲) یک Scheduled Task می‌سازد که سرور را زیر حساب SYSTEM، هنگام روشن شدن سیستم
::     (قبل از ورود هر کاربری) اجرا می‌کند. پس دیگر لازم نیست منشی وارد ویندوز شود
::     تا سرور بالا بیاید، و حساب او هم لازم نیست به این پوشه دسترسی داشته باشد.
cd /d "%~dp0"

echo [1/3] Locking folder permissions to Administrators and SYSTEM only...
icacls "%~dp0" /inheritance:r >nul
icacls "%~dp0" /grant:r "*S-1-5-32-544:(OI)(CI)F" "SYSTEM:(OI)(CI)F" >nul
if errorlevel 1 (
  echo ERROR: could not set permissions. Did you run this file as Administrator?
  pause
  exit /b 1
)

echo [2/3] Removing the old per-user autostart entry, if any...
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Findent.vbs" >nul 2>&1

echo [3/3] Registering the Findent server as a scheduled task (runs as SYSTEM, at boot)...
schtasks /Create /TN "Findent Server" /TR "wscript.exe \"%~dp0start_hidden.vbs\"" /SC ONSTART /RU SYSTEM /RL HIGHEST /F

echo.
echo Done. Restart the computer to test:
echo  - Findent should be reachable at http://localhost:8000 even before anyone logs in.
echo  - A normal (non-administrator) Windows account should NOT be able to open this folder.
pause
