# 🔧 HƯỚNG DẪN CẬP NHẬT SERVICE FILE TRÊN PI

Service file hiện tại có 2 lỗi cần sửa:
1. ❌ `ExecStart=/usr/bin/python` → ✅ Nên là `python3`
2. ❌ `--rts` → ✅ Thiếu 'p', nên là `--rtsp`

---

## 🔍 **KIỂM TRA SERVICE FILE HIỆN TẠI:**

```bash
sudo cat /etc/systemd/system/boxcamai.service
```

---

## ✏️ **SỬA SERVICE FILE:**

### **Cách 1: Sửa bằng nano (trực tiếp trên Pi)**

```bash
sudo nano /etc/systemd/system/boxcamai.service
```

**Sửa các dòng:**

1. **Sửa ExecStart:**
   - **Nếu DÙNG venv:**
     ```ini
     ExecStart=/home/leviathan/out-quan-boxcamai-client/venv/bin/python3 /home/leviathan/out-quan-boxcamai-client/main.py --rtsp
     ```
   
   - **Nếu KHÔNG dùng venv:**
     ```ini
     ExecStart=/usr/bin/python3 /home/leviathan/out-quan-boxcamai-client/main.py --rtsp
     ```

2. **Sửa --rts thành --rtsp**

**Lưu:** `Ctrl+X`, `Y`, `Enter`

### **Cách 2: Copy file mới (từ máy tính sang Pi)**

1. Copy file `boxcamai.service` từ máy tính sang Pi
2. Trên Pi, chạy:
```bash
sudo cp boxcamai.service /etc/systemd/system/boxcamai.service
```

---

## 🔄 **SAU KHI SỬA:**

```bash
# Reload systemd
sudo systemctl daemon-reload

# Reset failed state
sudo systemctl reset-failed boxcamai

# Kiểm tra service file đã đúng chưa
sudo systemctl cat boxcamai.service
```

---

## ✅ **SERVICE FILE ĐÚNG (Dùng venv):**

```ini
[Unit]
Description=Du an box camera ket hop nhan dang su dung AI
After=network.target

[Service]
Type=simple
User=leviathan
WorkingDirectory=/home/leviathan/out-quan-boxcamai-client
ExecStart=/home/leviathan/out-quan-boxcamai-client/venv/bin/python3 /home/leviathan/out-quan-boxcamai-client/main.py --rtsp
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

---

## 🚀 **CHẠY LẠI SERVICE:**

```bash
# Start service
sudo systemctl start boxcamai

# Kiểm tra status
sudo systemctl status boxcamai

# Xem log
sudo journalctl -u boxcamai -f
```

---

## 📝 **QUICK FIX (Copy-paste):**

```bash
# Backup service file cũ
sudo cp /etc/systemd/system/boxcamai.service /etc/systemd/system/boxcamai.service.backup

# Sửa service file
sudo nano /etc/systemd/system/boxcamai.service
# Sửa: python → python3, --rts → --rtsp

# Reload và reset
sudo systemctl daemon-reload
sudo systemctl reset-failed boxcamai

# Start lại
sudo systemctl start boxcamai
sudo systemctl status boxcamai
```

---

**Tạo ngày:** 2024  
**Người tạo:** Auto AI Assistant

