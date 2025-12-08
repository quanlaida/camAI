# 💾 BACKUP SERVICE FILE

Service file nằm tại: `/etc/systemd/system/boxcamai.service`

---

## 🔄 **CÁC CÁCH BACKUP:**

### **Cách 1: Backup vào thư mục home (Trên Pi):**

```bash
# Backup với timestamp
sudo cp /etc/systemd/system/boxcamai.service /home/leviathan/boxcamai.service.backup.$(date +%Y%m%d_%H%M%S)

# Hoặc backup đơn giản
sudo cp /etc/systemd/system/boxcamai.service /home/leviathan/boxcamai.service.backup

# Đổi owner để có thể edit
sudo chown leviathan:leviathan /home/leviathan/boxcamai.service.backup*
```

### **Cách 2: Backup vào thư mục client:**

```bash
sudo cp /etc/systemd/system/boxcamai.service /home/leviathan/out-quan-boxcamai-client/boxcamai.service.backup
sudo chown leviathan:leviathan /home/leviathan/out-quan-boxcamai-client/boxcamai.service.backup
```

### **Cách 3: Xem và copy nội dung:**

```bash
# Xem nội dung
sudo cat /etc/systemd/system/boxcamai.service

# Copy nội dung vào file mới
sudo cat /etc/systemd/system/boxcamai.service > ~/boxcamai.service.backup
```

---

## 📋 **RESTORE TỪ BACKUP:**

```bash
# Restore từ backup
sudo cp /home/leviathan/boxcamai.service.backup /etc/systemd/system/boxcamai.service

# Reload systemd
sudo systemctl daemon-reload

# Reset failed state
sudo systemctl reset-failed boxcamai

# Start lại
sudo systemctl start boxcamai
```

---

## 🔍 **KIỂM TRA BACKUP:**

```bash
# Xem file backup
cat ~/boxcamai.service.backup

# So sánh với file hiện tại
diff ~/boxcamai.service.backup /etc/systemd/system/boxcamai.service
```

---

## 📝 **QUICK BACKUP SCRIPT:**

```bash
#!/bin/bash
BACKUP_DIR="$HOME/backups"
SERVICE_FILE="/etc/systemd/system/boxcamai.service"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"
sudo cp "$SERVICE_FILE" "$BACKUP_DIR/boxcamai.service.backup.$TIMESTAMP"
sudo chown leviathan:leviathan "$BACKUP_DIR/boxcamai.service.backup.$TIMESTAMP"

echo "✅ Đã backup service file đến: $BACKUP_DIR/boxcamai.service.backup.$TIMESTAMP"
```

---

**Đường dẫn service file:** `/etc/systemd/system/boxcamai.service`

