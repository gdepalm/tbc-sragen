@echo off
title TBC Monitoring Dashboard - Kabupaten Sragen
cd /d "%~dp0"
echo ==============================================
echo   TBC MONITORING DASHBOARD - KABUPATEN SRAGEN
echo ==============================================
echo.

set "PY="
py -3.13 --version >nul 2>&1
if not errorlevel 1 set "PY=py -3.13"
if not defined PY (
  py -3.12 --version >nul 2>&1
  if not errorlevel 1 set "PY=py -3.12"
)
if not defined PY (
  py -3 --version >nul 2>&1
  if not errorlevel 1 set "PY=py -3"
)
if not defined PY (
  python --version >nul 2>&1
  if not errorlevel 1 set "PY=python"
)
if not defined PY goto TANPA_PYTHON

if exist ".venv\Scripts\python.exe" goto CEK_PUSTAKA
echo [1/3] Menyiapkan lingkungan Python. Hanya sekali, mohon tunggu...
%PY% -m venv .venv
if errorlevel 1 goto GAGAL

:CEK_PUSTAKA
if exist ".venv\terpasang.txt" goto SIAP
echo [2/3] Memasang pustaka. Hanya sekali, sekitar 2-5 menit, perlu internet...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto GAGAL
echo ok> ".venv\terpasang.txt"

:SIAP
if not exist ".env" copy ".env.example" ".env" >nul
echo.
echo [3/3] Menjalankan website...
echo Browser akan terbuka otomatis. Alamat: http://127.0.0.1:8000
echo JANGAN tutup jendela hitam ini selama website dipakai.
echo Untuk berhenti: tutup jendela ini atau tekan Ctrl+C.
echo.
start "" cmd /c "timeout /t 5 /nobreak >nul & start http://127.0.0.1:8000"
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
echo.
echo Website berhenti.
pause
exit /b 0

:TANPA_PYTHON
echo Python belum terpasang atau tidak terbaca.
echo Pasang Python 3.13 dari https://www.python.org/downloads/
echo dan centang "Add python.exe to PATH" saat memasang.
pause
exit /b 1

:GAGAL
echo.
echo Terjadi kesalahan. Salin tulisan di atas ini dan kirim untuk dibantu.
pause
exit /b 1
