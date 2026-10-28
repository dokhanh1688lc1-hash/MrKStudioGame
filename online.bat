@echo off
chcp 65001 >nul
cd /d "%~dp0"
where tailscale >nul 2>nul
if errorlevel 1 (
  echo CHUA CAI TAILSCALE. Tai tai https://tailscale.com/download roi dang nhap, sau do chay lai file nay.
  pause
  exit /b 1
)
tailscale status >nul 2>nul
if errorlevel 1 (
  echo TAILSCALE CHUA DANG NHAP hoac chua chay. Mo ung dung Tailscale, dang nhap, roi chay lai.
  pause
  exit /b 1
)
echo Dang mo truy cap rieng tu qua Tailscale (chi thiet bi cua ban moi vao duoc)...
tailscale serve --bg 8000
if errorlevel 1 (
  echo KHONG BAT DUOC "tailscale serve". Cap nhat Tailscale len ban moi nhat, hoac bat HTTPS/Serve trong trang quan tri Tailscale.
  pause
  exit /b 1
)
echo.
echo ===== DIA CHI ONLINE CUA BAN (mo tren dien thoai / may khac da dang nhap Tailscale) =====
tailscale serve status
echo ==========================================================================
echo Giu cua so nay mo. Dong cua so (hoac bam phim bat ky sau khi ung dung dung) de TAT truy cap online.
echo.
call run.bat
echo Dang tat truy cap online...
tailscale serve reset
pause
