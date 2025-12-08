#!/bin/bash
# Script tắt service client và process đang chạy trên Pi

echo "🛑 Tắt service và process client đang tự động chạy..."
echo ""

# Stop và disable service
echo "=== Stopping service ==="
sudo systemctl stop boxcamai 2>/dev/null && echo "✅ Stopped boxcamai service" || echo "⚠️  Service không tồn tại hoặc đã stop"
sudo systemctl disable boxcamai 2>/dev/null && echo "✅ Disabled boxcamai service" || echo "⚠️  Service không tồn tại hoặc đã disable"

# Kill processes
echo ""
echo "=== Killing processes ==="
pkill -f "main.py" 2>/dev/null && echo "✅ Killed main.py processes" || echo "ℹ️  Không có process main.py"
pkill -f "detection" 2>/dev/null && echo "✅ Killed detection processes" || echo "ℹ️  Không có process detection"
pkill -f "stream_sender" 2>/dev/null && echo "✅ Killed stream_sender processes" || echo "ℹ️  Không có process stream_sender"

# Đợi 2 giây
sleep 2

# Kiểm tra lại
echo ""
echo "=== Kiểm tra lại ==="
if sudo systemctl is-active --quiet boxcamai 2>/dev/null; then
    echo "⚠️  Service boxcamai vẫn đang active!"
else
    echo "✅ Service boxcamai đã tắt"
fi

MAIN_PID=$(pgrep -f "main.py")
if [ -n "$MAIN_PID" ]; then
    echo "⚠️  Process main.py vẫn đang chạy (PID: $MAIN_PID)"
    echo "   Đang force kill..."
    kill -9 $MAIN_PID 2>/dev/null
else
    echo "✅ Không còn process main.py"
fi

DETECTION_PID=$(pgrep -f "detection")
if [ -n "$DETECTION_PID" ]; then
    echo "⚠️  Process detection vẫn đang chạy (PID: $DETECTION_PID)"
    kill -9 $DETECTION_PID 2>/dev/null
else
    echo "✅ Không còn process detection"
fi

echo ""
echo "✅ Hoàn thành!"
echo ""
echo "💡 Bây giờ bạn có thể chạy thủ công:"
echo "   cd /home/leviathan/out-quan-boxcamai-client"
echo "   source venv/bin/activate  # nếu dùng venv"
echo "   python3 main.py --rtsp"

