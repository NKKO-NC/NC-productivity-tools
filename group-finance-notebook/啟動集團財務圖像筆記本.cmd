@echo off
setlocal

set "PROJECT_DIR=%~dp0"
set "PYTHON_EXE=C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
set "APP_URL=http://127.0.0.1:8765"

if not exist "%PYTHON_EXE%" (
  echo Built-in Python runtime was not found:
  echo %PYTHON_EXE%
  echo.
  echo Please reopen this project in Codex and try again.
  pause
  exit /b 1
)

cd /d "%PROJECT_DIR%"

echo Starting Group Finance Notebook...
echo Your browser will open automatically.
echo Close the black window to stop the app.
echo.

start "" cmd /c "timeout /t 2 /nobreak >nul && start \"\" \"%APP_URL%\""
"%PYTHON_EXE%" "%PROJECT_DIR%run.py"
