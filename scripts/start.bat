@echo off
pip install -r requirements.txt
uvicorn apps.api.main:app --reload
pause
