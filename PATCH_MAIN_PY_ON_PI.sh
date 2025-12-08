#!/bin/bash

# Script để patch main.py trên Pi
# Chạy script này trên Pi: bash PATCH_MAIN_PY_ON_PI.sh

MAIN_PY="$HOME/out-quan-boxcamai-client/main.py"
BACKUP_FILE="${MAIN_PY}.backup.$(date +%Y%m%d_%H%M%S)"

echo "🔧 Patching main.py trên Pi..."
echo ""

# Backup file cũ
if [ -f "$MAIN_PY" ]; then
    cp "$MAIN_PY" "$BACKUP_FILE"
    echo "✅ Đã backup: $BACKUP_FILE"
else
    echo "❌ Không tìm thấy file: $MAIN_PY"
    exit 1
fi

# Tìm vị trí hàm server_polling_thread
LINE_START=$(grep -n "def server_polling_thread" "$MAIN_PY" | cut -d: -f1)

if [ -z "$LINE_START" ]; then
    echo "❌ Không tìm thấy hàm server_polling_thread"
    exit 1
fi

echo "📍 Tìm thấy hàm tại dòng: $LINE_START"

# Kiểm tra đã có patch chưa
if grep -q "Waiting.*before first check" "$MAIN_PY"; then
    echo "✅ File đã có patch rồi!"
    exit 0
fi

# Tìm dòng print cuối cùng trong phần khởi tạo (trước while loop)
LINE_WHILE=$(awk "NR>$LINE_START && /^[[:space:]]*while not stop_event.is_set/ {print NR; exit}" "$MAIN_PY")

if [ -z "$LINE_WHILE" ]; then
    echo "❌ Không tìm thấy vòng lặp while"
    exit 1
fi

# Tìm dòng print cuối cùng trước while (thường là dòng print Initial IP/ROI)
LINE_BEFORE_WHILE=$((LINE_WHILE - 1))

echo "📝 Thêm code vào sau dòng $LINE_BEFORE_WHILE..."

# Tạo file patch
cat > /tmp/patch_main.py << 'PATCH_EOF'
    # QUAN TRỌNG: Đợi interval TRƯỚC KHI check lần đầu tiên
    # Để tránh restart ngay sau khi service start
    print(f"⏳ Waiting {config.POLL_INTERVAL}s before first check...")
    stop_event.wait(config.POLL_INTERVAL)
    
    if stop_event.is_set():
        print("🛑 Server polling thread stopped (before first check)")
        return
    
PATCH_EOF

# Apply patch bằng sed (thêm sau dòng LINE_BEFORE_WHILE)
sed -i "${LINE_BEFORE_WHILE}r /tmp/patch_main.py" "$MAIN_PY"

# Cleanup
rm -f /tmp/patch_main.py

echo ""
echo "✅ Đã patch xong!"
echo ""
echo "🔍 Verify patch:"
if grep -q "Waiting.*before first check" "$MAIN_PY"; then
    echo "✅ Patch thành công!"
    echo ""
    echo "📋 Xem đoạn code đã thêm:"
    grep -A 7 "Waiting.*before first check" "$MAIN_PY"
else
    echo "❌ Patch thất bại, restore từ backup..."
    cp "$BACKUP_FILE" "$MAIN_PY"
    exit 1
fi

echo ""
echo "🚀 Bước tiếp theo:"
echo "   ./KILL_ALL_CLIENT_PROCESSES.sh"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl reset-failed boxcamai"
echo "   sudo systemctl start boxcamai"
echo "   sudo journalctl -u boxcamai -f"

