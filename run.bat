@echo off
setlocal
chcp 65001 >nul

REM === Config: point to your venv Python interpreter ===
set PYTHON_PATH=.\venv\Scripts\python.exe

cd /d "%~dp0"

if not exist "%PYTHON_PATH%" (
    echo ERROR: Python interpreter not found: %PYTHON_PATH%
    echo Please edit PYTHON_PATH in run.bat to point to your venv Python.
    pause
    exit /b 1
)

echo Using Python: %PYTHON_PATH%
"%PYTHON_PATH%" main.py

pause
