#!/bin/bash
# Script tắt server trên Pi

echo "🔍 Kiểm tra server đang chạy..."
echo ""

echo "=== Processes Python server.py ==="
ps aux | grep server.py | grep -v grep

echo ""
echo "=== Port 5000 ==="
sudo lsof -i :5000 2>/dev/null || echo "Port 5000 không được sử dụng"

echo ""
echo "=== Service boxcamai ==="
sudo systemctl status boxcamai 2>/dev/null | head -5

echo ""
read -p "Bạn có muốn tắt tất cả server? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🛑 Đang tắt server..."
    
    # Stop service
    sudo systemctl stop boxcamai 2>/dev/null && echo "✅ Stopped boxcamai service"
    
    # Kill processes
    pkill -f server.py && echo "✅ Killed server.py processes"
    
    # Free port 5000
    sudo fuser -k 5000/tcp 2>/dev/null && echo "✅ Freed port 5000"
    
    echo ""
    echo "✅ Hoàn thành! Đang kiểm tra lại..."
    sleep 2
    
    echo ""
    echo "=== Kiểm tra lại ==="
    if ps aux | grep server.py | grep -v grep; then
        echo "⚠️  Vẫn còn process đang chạy!"
    else
        echo "✅ Không còn server nào đang chạy"
    fi
    
    if sudo lsof -i :5000 2>/dev/null; then
        echo "⚠️  Port 5000 vẫn đang được sử dụng!"
    else
        echo "✅ Port 5000 đã được giải phóng"
    fi
else
    echo "❌ Đã hủy"
fi

