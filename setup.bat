@echo off
REM Cai dat lan dau: backend (Python venv) + frontend (build)
cd /d "%~dp0"
if not exist .env copy .env.example .env
python -m venv .venv || goto :err
call .venv\Scripts\activate.bat
pip install -r backend\requirements.txt || goto :err
cd frontend
call npm install || goto :err
call npm run build || goto :err
cd ..
echo.
echo Xong. Chay run.bat de khoi dong. Nho dien API key trong file .env (khong bat buoc).
exit /b 0
:err
echo LOI: kiem tra Python 3.11+ va Node.js 18+ da duoc cai.
exit /b 1
