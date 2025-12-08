# 🔧 HƯỚNG DẪN SỬA LỖI RESTART QUÁ NHANH

Service đã kết nối được server nhưng bị restart liên tục → `start-limit-hit`.

---

## 🔍 **BƯỚC 1: XEM LOG CHI TIẾT ĐỂ TÌM LỖI**

```bash
# Xem log đầy đủ (không chỉ follow)
sudo journalctl -u boxcamai -n 100 --no-pager

# Hoặc xem từ lúc start
sudo journalctl -u boxcamai --since "10 minutes ago" --no-pager

# Tìm lỗi trong log
sudo journalctl -u boxcamai --no-pager | grep -i error
sudo journalctl -u boxcamai --no-pager | grep -i exception
sudo journalctl -u boxcamai --no-pager | grep -i traceback
```

---

## 🛑 **BƯỚC 2: RESET VÀ TẮT TẠM THỜI**

```bash
# Reset failed state
sudo systemctl reset-failed boxcamai

# Stop service
sudo systemctl stop boxcamai

# Disable tạm thời
sudo systemctl disable boxcamai
```

---

## 🧪 **BƯỚC 3: TEST CHẠY THỦ CÔNG ĐỂ TÌM LỖI**

```bash
cd /home/leviathan/out-quan-boxcamai-client
source venv/bin/activate  # Nếu dùng venv
python3 main.py --rtsp --not-sent
```

**Xem có lỗi gì xuất hiện không:**
- Import error?
- Module not found?
- Runtime error?
- Crash?

---

## 🔧 **BƯỚC 4: SỬA SERVICE FILE - TĂNG RESTART DELAY**

Nếu service crash liên tục, tăng `RestartSec`:

```bash
sudo nano /etc/systemd/system/boxcamai.service
```

**Sửa dòng `RestartSec`:**
```ini
RestartSec=30  # Tăng từ 5 hoặc 10 lên 30 giây
```

**Và có thể thêm:**
```ini
StartLimitInterval=200
StartLimitBurst=5
```

**Full service file nên như này:**
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
RestartSec=30
StartLimitInterval=200
StartLimitBurst=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

---

## 📋 **BƯỚC 5: RELOAD VÀ CHẠY LẠI**

```bash
# Reload systemd
sudo systemctl daemon-reload

# Reset failed state
sudo systemctl reset-failed boxcamai

# Start lại
sudo systemctl start boxcamai

# Xem log real-time
sudo journalctl -u boxcamai -f
```

---

## ⚠️ **NGUYÊN NHÂN THƯỜNG GẶP:**

### **1. Code có lỗi → Service crash**
- ✅ **Giải pháp:** Test chạy thủ công, sửa lỗi

### **2. Module not found**
- ✅ **Giải pháp:** Kiểm tra venv path trong ExecStart

### **3. Permission denied**
- ✅ **Giải pháp:** Kiểm tra User= trong service file

### **4. Cannot connect RTSP**
- ✅ **Giải pháp:** Kiểm tra IP camera, có thể chạy với `--not-sent` tạm thời

---

## 🎯 **QUICK DEBUG SCRIPT:**

```bash
#!/bin/bash
echo "🔍 Debug service boxcamai..."

# Tắt service
sudo systemctl stop boxcamai
sudo systemctl reset-failed boxcamai

# Xem log lỗi
echo ""
echo "=== Lỗi gần đây ==="
sudo journalctl -u boxcamai -n 50 --no-pager | grep -i -E "error|exception|traceback|failed"

# Test chạy thủ công
echo ""
echo "=== Test chạy thủ công (10 giây) ==="
cd /home/leviathan/out-quan-boxcamai-client
source venv/bin/activate 2>/dev/null
timeout 10 python3 main.py --rtsp --not-sent 2>&1 | head -20
```

---

## 📝 **QUICK FIX:**

```bash
# 1. Tắt service
sudo systemctl stop boxcamai
sudo systemctl disable boxcamai
sudo systemctl reset-failed boxcamai

# 2. Tăng RestartSec trong service file
sudo nano /etc/systemd/system/boxcamai.service
# Sửa: RestartSec=30

# 3. Reload và test
sudo systemctl daemon-reload
sudo systemctl reset-failed boxcamai

# 4. Test chạy thủ công trước
cd /home/leviathan/out-quan-boxcamai-client
source venv/bin/activate
python3 main.py --rtsp --not-sent
```

---

**Tạo ngày:** 2024  
**Người tạo:** Auto AI Assistant

