@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\activate.bat (
  echo CHUA CAI DAT: hay chay setup.bat truoc.
  pause
  exit /b 1
)
if not exist frontend\dist\index.html (
  echo CHUA BUILD GIAO DIEN: hay chay setup.bat truoc.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
cd backend
echo Mo trinh duyet: http://127.0.0.1:8000  (dong cua so nay de tat ung dung)
python -m uvicorn app.main:app_factory --factory --host 127.0.0.1 --port 8000
echo.
echo ===== UNG DUNG DA DUNG. Xem loi o tren. =====
pause
