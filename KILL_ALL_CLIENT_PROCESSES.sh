#!/bin/bash

echo "🛑 Dừng tất cả process boxcamai..."

# Dừng service
sudo systemctl stop boxcamai 2>/dev/null
sudo systemctl disable boxcamai 2>/dev/null
sudo systemctl reset-failed boxcamai 2>/dev/null

# Kill tất cả process python3 chạy main.py
echo "🔍 Tìm và kill các process python3 chạy main.py..."
pkill -f "python.*main.py" 2>/dev/null
pkill -f "python3.*main.py" 2>/dev/null

# Kill tất cả process python3 trong thư mục client
echo "🔍 Tìm process trong thư mục out-quan-boxcamai-client..."
ps aux | grep "[p]ython.*out-quan-boxcamai-client" | awk '{print $2}' | xargs -r sudo kill -9 2>/dev/null

# Đợi một chút
sleep 2

# Kiểm tra còn process nào không
REMAINING=$(ps aux | grep "[p]ython.*main.py" | wc -l)
if [ "$REMAINING" -gt 0 ]; then
    echo "⚠️ Vẫn còn $REMAINING process đang chạy, force kill..."
    ps aux | grep "[p]ython.*main.py" | awk '{print $2}' | xargs -r sudo kill -9 2>/dev/null
    sleep 1
fi

# Xác nhận
REMAINING=$(ps aux | grep "[p]ython.*main.py" | wc -l)
if [ "$REMAINING" -eq 0 ]; then
    echo "✅ Đã dừng tất cả process boxcamai"
else
    echo "❌ Vẫn còn $REMAINING process (có thể là grep process)"
fi

echo ""
echo "📋 Kiểm tra lại:"
ps aux | grep "[p]ython.*main.py" || echo "Không có process nào đang chạy"

echo ""
echo "✅ Sẵn sàng start service mới!"

