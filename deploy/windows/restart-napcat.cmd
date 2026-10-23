@echo off
REM Restart NapCat / QQ (called by guard.mjs on Windows).
taskkill /IM QQ.exe /F >nul 2>&1
taskkill /IM NapCatWinBootMain.exe /F >nul 2>&1
timeout /t 3 /nobreak >nul
start "" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\Users\Administrator\qq-dsh-bot\start-napcat.ps1"
exit /b 0
