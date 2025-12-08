# ✅ KIỂM TRA SERVICE ĐÃ CHẠY THÀNH CÔNG

Service `boxcamai` đã **active (running)** - đây là dấu hiệu tốt!

---

## 🔍 **KIỂM TRA LOG ĐỂ XEM HOẠT ĐỘNG:**

### **1. Xem log real-time:**
```bash
sudo journalctl -u boxcamai -f
```

### **2. Xem log gần đây (50 dòng cuối):**
```bash
sudo journalctl -u boxcamai -n 50
```

### **3. Xem log từ lúc start:**
```bash
sudo journalctl -u boxcamai --since "5 minutes ago"
```

---

## ✅ **CÁC LOG CẦN THẤY:**

Service hoạt động đúng sẽ có các log sau:

```
✅ Client info retrieved: {...}
📹 Video stream sender thread started (raw)
📹 Processed video stream sender thread started (AI detection)
🔄 Server polling thread started (checking every 30s)
Using camera IP from server: <IP>
Connecting to RTSP: rtsp://admin:***@<IP>:554/...
```

---

## ⚠️ **NẾU THẤY LỖI:**

### **Lỗi 1: "Module not found"**
```bash
# Service có thể đang dùng Python hệ thống thay vì venv
# Kiểm tra ExecStart trong service file có trỏ đến venv không
sudo cat /etc/systemd/system/boxcamai.service | grep ExecStart
```

### **Lỗi 2: "Cannot connect to server"**
```bash
# Kiểm tra config
cat /home/leviathan/out-quan-boxcamai-client/config.py | grep SERVER
```

### **Lỗi 3: "No camera detected"**
```bash
# Kiểm tra IP camera trên server
# Hoặc set RTSP_IP trong config.py
```

---

## 🔄 **CÁC LỆNH QUẢN LÝ SERVICE:**

### **Xem status:**
```bash
sudo systemctl status boxcamai
```

### **Xem log:**
```bash
sudo journalctl -u boxcamai -f
```

### **Restart service:**
```bash
sudo systemctl restart boxcamai
```

### **Stop service:**
```bash
sudo systemctl stop boxcamai
```

### **Enable auto-start (tự động chạy khi boot):**
```bash
sudo systemctl enable boxcamai
```

---

## 🎯 **BƯỚC TIẾP THEO:**

1. **Kiểm tra log** để xem service có chạy đúng không
2. **Kiểm tra web dashboard** để xem có nhận được detections không
3. **Kiểm tra live streams** trên web để xem video stream

---

**Tạo ngày:** 2024  
**Người tạo:** Auto AI Assistant

