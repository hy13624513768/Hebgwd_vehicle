@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy\start-local.ps1"
if errorlevel 1 (
  echo.
  echo Startup failed. Check the messages above and .local-run logs.
  pause
)
endlocal
