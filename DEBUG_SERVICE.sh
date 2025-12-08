#!/bin/bash

echo "🔍 Debug service boxcamai..."
echo ""

# Tắt service
echo "1️⃣ Dừng service..."
sudo systemctl stop boxcamai 2>/dev/null
sudo systemctl reset-failed boxcamai 2>/dev/null
echo "✅ Đã dừng service"
echo ""

# Xem log lỗi
echo "2️⃣ Xem lỗi gần đây..."
echo "=== Lỗi gần đây ==="
sudo journalctl -u boxcamai -n 50 --no-pager | grep -i -E "error|exception|traceback|failed" || echo "Không tìm thấy lỗi trong 50 dòng log gần nhất"
echo ""

# Test chạy thủ công
echo "3️⃣ Test chạy thủ công (10 giây)..."
cd /home/leviathan/out-quan-boxcamai-client 2>/dev/null || {
    echo "❌ Không tìm thấy thư mục /home/leviathan/out-quan-boxcamai-client"
    exit 1
}

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ Đã kích hoạt venv"
else
    echo "⚠️ Không tìm thấy venv, dùng Python hệ thống"
fi

echo "Chạy: python3 main.py --rtsp --not-sent"
echo "---"
timeout 10 python3 main.py --rtsp --not-sent 2>&1 | head -30 || echo "❌ Có lỗi khi chạy"
echo "---"
echo ""

echo "4️⃣ Kiểm tra service file..."
echo "=== ExecStart ==="
sudo cat /etc/systemd/system/boxcamai.service | grep ExecStart
echo ""

echo "5️⃣ Kiểm tra Python path..."
if [ -f "venv/bin/python3" ]; then
    echo "✅ venv/bin/python3 tồn tại"
    venv/bin/python3 --version
else
    echo "❌ venv/bin/python3 không tồn tại"
    echo "Dùng Python hệ thống:"
    python3 --version
fi
echo ""

echo "✅ Debug xong!"
echo ""
echo "📝 Bước tiếp theo:"
echo "   - Xem log lỗi ở trên"
echo "   - Nếu có lỗi, sửa code/service file"
echo "   - Sau đó chạy: sudo systemctl start boxcamai"

