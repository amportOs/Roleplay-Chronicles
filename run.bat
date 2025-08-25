@echo off
setlocal ENABLEDELAYEDEXPANSION

REM Resolve project directory (this script's location)
set "PROJECT_DIR=%~dp0"
pushd "%PROJECT_DIR%" >nul

REM Define venv path
set "VENV_DIR=%PROJECT_DIR%.venv"
set "PY_EXE=%VENV_DIR%\Scripts\python.exe"

REM Create virtual environment if missing
if not exist "%PY_EXE%" (
  echo [INFO] Creating virtual environment...
  py -m venv "%VENV_DIR%"
)

REM Upgrade pip (optional but recommended)
"%PY_EXE%" -m pip install --upgrade pip >nul 2>&1

REM Install requirements
echo [INFO] Installing requirements...
"%PY_EXE%" -m pip install -r "%PROJECT_DIR%login_app\requirements.txt"
if errorlevel 1 (
  echo [ERROR] Failed to install dependencies.
  pause
  exit /b 1
)

REM Start Flask app in the login_app directory
pushd "%PROJECT_DIR%login_app" >nul
echo [INFO] Starting Flask server from: %CD%
"%PY_EXE%" app.py
set "EXIT_CODE=%ERRORLEVEL%"
popd >nul

popd >nul
echo [INFO] Server exited with code %EXIT_CODE%.
pause
