@echo off
cd /d "%~dp0backend"
call ..\.venv\Scripts\activate.bat
echo Mo trinh duyet: http://127.0.0.1:8000
python -m uvicorn app.main:app_factory --factory --host 127.0.0.1 --port 8000
