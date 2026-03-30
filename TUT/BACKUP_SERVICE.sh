#!/bin/bash

BACKUP_DIR="$HOME/backups"
SERVICE_FILE="/etc/systemd/system/boxcamai.service"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/boxcamai.service.backup.$TIMESTAMP"

# Tạo thư mục backup nếu chưa có
mkdir -p "$BACKUP_DIR"

# Backup service file
sudo cp "$SERVICE_FILE" "$BACKUP_FILE"
sudo chown leviathan:leviathan "$BACKUP_FILE"

echo "✅ Đã backup service file:"
echo "   Từ: $SERVICE_FILE"
echo "   Đến: $BACKUP_FILE"
echo ""
echo "📋 Xem backup:"
echo "   cat $BACKUP_FILE"
echo ""
echo "🔄 Restore từ backup:"
echo "   sudo cp $BACKUP_FILE $SERVICE_FILE"
echo "   sudo systemctl daemon-reload"

