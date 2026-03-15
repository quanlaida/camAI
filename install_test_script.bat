@echo off
echo ========================================
echo CAI DAT SCRIPT TEST DETECTION
echo ========================================
echo.

echo [1/2] Kiem tra Python...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python chua duoc cai dat!
    echo Vui long cai dat Python truoc: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo [2/2] Cai dat thu vien can thiet...
python -m pip install --upgrade pip
python -m pip install requests pillow urllib3

echo.
echo ========================================
echo CAI DAT HOAN TAT!
echo ========================================
echo.
echo De chay script test:
echo   python test_detection_from_client.py
echo.
pause
