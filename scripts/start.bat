@echo off
setlocal

cd /d %~dp0\..

set PYTHONPATH=%cd%

python scripts\bootstrap.py
if %errorlevel% neq 0 exit /b %errorlevel%

pip install -r requirements.txt >nul 2>&1

echo ==========================================
echo        CRYPTO.BOT - AI TRADING SYSTEM
echo ==========================================
echo.
echo [INFO] Starting API...
echo.

REM === CHAMAR POWERSHELL PRA MANTER PROCESSO ===
powershell -NoExit -Command "python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000"