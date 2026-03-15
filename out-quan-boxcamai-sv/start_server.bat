@echo off
REM ============================================
REM CamAI Server - Auto Start Script
REM ============================================

REM Thay đổi đường dẫn này thành đường dẫn thực tế của bạn
cd /d E:\CAM_AI_server\camAI\out-quan-boxcamai-sv

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Chạy server
python server.py

REM Nếu server bị lỗi và thoát, đợi 5 giây rồi thử lại
if errorlevel 1 (
    echo Server stopped with error. Restarting in 5 seconds...
    timeout /t 5 /nobreak
    goto :eof
)

