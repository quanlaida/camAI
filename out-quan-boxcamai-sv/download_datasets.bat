@echo off
chcp 65001 >nul
echo ========================================
echo SCRIPT TẢI DATASET TỪ ROBOFLOW
echo ========================================
echo.

REM Kiểm tra Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Không tìm thấy Python!
    echo Vui lòng cài đặt Python hoặc thêm Python vào PATH
    pause
    exit /b 1
)

echo ✅ Đã tìm thấy Python
python --version
echo.

REM Cài đặt roboflow nếu chưa có
echo Đang kiểm tra roboflow...
python -c "import roboflow" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Đang cài đặt roboflow...
    python -m pip install roboflow
    if %ERRORLEVEL% NEQ 0 (
        echo ❌ Lỗi khi cài đặt roboflow!
        pause
        exit /b 1
    )
    echo ✅ Đã cài đặt roboflow
) else (
    echo ✅ roboflow đã được cài đặt
)
echo.

REM Tạo thư mục nếu chưa có
if not exist "D:\ANH DATASET" (
    echo Đang tạo thư mục D:\ANH DATASET...
    mkdir "D:\ANH DATASET"
)

REM Chạy script tải dataset
echo ========================================
echo BẮT ĐẦU TẢI DATASET
echo ========================================
echo.
python download_roboflow_datasets.py

echo.
echo ========================================
echo HOÀN TẤT
echo ========================================
pause

