#!/bin/bash
# Script reset và tắt service boxcamai

echo "🔧 Reset và tắt service boxcamai..."
echo ""

# Reset failed state
echo "=== Resetting failed state ==="
sudo systemctl reset-failed boxcamai && echo "✅ Reset failed state"

# Stop service
echo ""
echo "=== Stopping service ==="
sudo systemctl stop boxcamai 2>/dev/null && echo "✅ Stopped boxcamai service" || echo "ℹ️  Service đã stop hoặc không tồn tại"

# Disable service
echo ""
echo "=== Disabling service ==="
sudo systemctl disable boxcamai 2>/dev/null && echo "✅ Disabled boxcamai service" || echo "ℹ️  Service đã disable"

# Kill processes
echo ""
echo "=== Killing processes ==="
pkill -f main.py 2>/dev/null && echo "✅ Killed main.py" || echo "ℹ️  Không có process main.py"
pkill -f detection 2>/dev/null && echo "✅ Killed detection" || echo "ℹ️  Không có process detection"

# Reload systemd
echo ""
echo "=== Reloading systemd ==="
sudo systemctl daemon-reload && echo "✅ Reloaded systemd"

# Kiểm tra lại
echo ""
echo "=== Kiểm tra ==="
STATUS=$(sudo systemctl is-active boxcamai 2>/dev/null)
if [ "$STATUS" = "active" ]; then
    echo "⚠️  Service vẫn đang active!"
else
    echo "✅ Service đã tắt hoàn toàn"
fi

FAILED=$(sudo systemctl is-failed boxcamai 2>/dev/null)
if [ "$FAILED" = "failed" ]; then
    echo "⚠️  Service vẫn ở trạng thái failed - có thể cần check service file"
else
    echo "✅ Service không còn failed state"
fi

echo ""
echo "✅ Hoàn thành!"
echo ""
echo "💡 Bây giờ bạn có thể:"
echo "   1. Test chạy thủ công: python3 main.py --rtsp --not-sent"
echo "   2. Hoặc sửa service file và chạy lại: sudo systemctl start boxcamai"

