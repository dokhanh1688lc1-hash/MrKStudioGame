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
rem Neu ban cu cua ung dung van dang chay (chiem cong 8000) thi tat no truoc de chay ban moi.
powershell -NoProfile -Command "$c=Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue; if($c){foreach($x in $c){$p=Get-Process -Id $x.OwningProcess -ErrorAction SilentlyContinue; if($p -and $p.ProcessName -like 'python*'){Write-Host ('Tat ban cu dang chay (PID '+$p.Id+')...'); Stop-Process -Id $p.Id -Force; Start-Sleep -Seconds 2} else {Write-Host 'CONG 8000 DANG BI CHUONG TRINH KHAC DUNG. Dong chuong trinh do roi chay lai.'; exit 3}}}"
if errorlevel 3 (
  pause
  exit /b 1
)
cd backend
echo Mo trinh duyet: http://127.0.0.1:8000  (dong cua so nay de tat ung dung)
python -m uvicorn app.main:app_factory --factory --host 127.0.0.1 --port 8000
echo.
echo ===== UNG DUNG DA DUNG. Xem loi o tren. =====
pause
