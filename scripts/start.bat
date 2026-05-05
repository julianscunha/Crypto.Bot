@echo off
setlocal ENABLEDELAYEDEXPANSION

REM === Ir para raiz do projeto ===
cd /d %~dp0\..

REM === Evitar prompt no CTRL+C ===
if not defined PROMPT set PROMPT=$G

REM === PYTHONPATH ===
set PYTHONPATH=%cd%

REM === Validar estrutura ===
python scripts\bootstrap.py

if %errorlevel% neq 0 (
    echo [ERROR] Bootstrap failed
    exit /b %errorlevel%
)

REM === Instalar dependências (silencioso) ===
pip install -r requirements.txt >nul 2>&1

REM === Subir API ===
uvicorn apps.api.main:app --reload