# 🔌 Hướng Dẫn Bật Lại Client Trên Pi Sau Khi Ngắt Điện

## 🎯 Mục Đích

Sau khi Pi bị ngắt điện, cần khởi động lại service để client có thể gửi dữ liệu lên server.

---

## ✅ Các Cách Bật Lại Client

### **Cách 1: Khởi Động Tự Động (Nếu Đã Cài Service)**

Nếu đã cài service `boxcamai.service`, service sẽ **tự động khởi động** khi Pi boot lên.

**Kiểm tra service có đang chạy:**
```bash
sudo systemctl status boxcamai
```

**Nếu service không chạy, khởi động thủ công:**
```bash
sudo systemctl start boxcamai
```

**Kiểm tra lại:**
```bash
sudo systemctl status boxcamai
```

Phải thấy: `Active: active (running)` ✅

---

### **Cách 2: Khởi Động Thủ Công (Nếu Chưa Cài Service)**

**Bước 1: SSH vào Pi**
```bash
ssh leviathan@<IP_PI>
```

**Bước 2: Di chuyển đến thư mục client**
```bash
cd /home/leviathan/out-quan-boxcamai-client
```

**Bước 3: Kích hoạt virtual environment (nếu có)**
```bash
source venv/bin/activate
```

**Bước 4: Chạy client**
```bash
python3 main.py --rtsp
```

Hoặc nếu dùng rpicam:
```bash
python3 main.py --rpicam
```

---

### **Cách 3: Cài Service Để Tự Động Khởi Động**

**Nếu chưa cài service, làm theo các bước sau:**

**Bước 1: Copy file service**
```bash
sudo cp /home/leviathan/out-quan-boxcamai-client/boxcamai.service /etc/systemd/system/
```

**Bước 2: Sửa đường dẫn trong file service (nếu cần)**
```bash
sudo nano /etc/systemd/system/boxcamai.service
```

Kiểm tra các đường dẫn:
- `WorkingDirectory`: Đúng thư mục client
- `ExecStart`: Đúng đường dẫn Python và main.py
- `User`: Đúng username (ví dụ: `leviathan`)

**Bước 3: Reload systemd**
```bash
sudo systemctl daemon-reload
```

**Bước 4: Enable service (tự động khởi động khi boot)**
```bash
sudo systemctl enable boxcamai
```

**Bước 5: Start service**
```bash
sudo systemctl start boxcamai
```

**Bước 6: Kiểm tra status**
```bash
sudo systemctl status boxcamai
```

---

## 🔍 Kiểm Tra Client Đã Chạy Chưa

### **1. Kiểm tra service status:**
```bash
sudo systemctl status boxcamai
```

**Kết quả mong đợi:**
- `Active: active (running)` ✅
- Không có lỗi (errors)

### **2. Kiểm tra log:**
```bash
sudo journalctl -u boxcamai -f
```

**Phải thấy:**
- `Client info retrieved`
- `Starting object detection...`
- `Video stream sender thread started`
- Không có lỗi kết nối server

### **3. Kiểm tra process đang chạy:**
```bash
ps aux | grep main.py
```

**Phải thấy process `main.py` đang chạy**

### **4. Kiểm tra trên Web Dashboard:**

1. Mở trang web dashboard
2. Tab **"Clients"**
3. Tìm client với Serial number của Pi
4. Kiểm tra cột **"Last Seen"** → Phải cập nhật mới
5. Tab **"Detections"** → Chọn client → Phải thấy video stream

---

## 🐛 Troubleshooting

### **Vấn đề: Service không khởi động**

**Kiểm tra:**
```bash
# Xem log chi tiết
sudo journalctl -u boxcamai -n 50

# Kiểm tra file service có đúng không
cat /etc/systemd/system/boxcamai.service

# Kiểm tra đường dẫn Python
which python3
```

**Sửa lỗi:**
- Sửa đường dẫn trong `boxcamai.service`
- Reload: `sudo systemctl daemon-reload`
- Restart: `sudo systemctl restart boxcamai`

---

### **Vấn đề: Service chạy nhưng không gửi dữ liệu**

**Kiểm tra:**

1. **Serial number có đúng không:**
   ```bash
   cat /home/leviathan/out-quan-boxcamai-client/serial_number.txt
   ```
   Phải khớp với Serial number trên server

2. **Server có đang chạy không:**
   - Ping server từ Pi
   - Kiểm tra kết nối mạng

3. **Client có được enable trên server không:**
   - Vào web dashboard → Tab Clients
   - Kiểm tra Status = "Active"
   - Check "Detection Enabled" = ✅

4. **Xem log để biết lỗi:**
   ```bash
   sudo journalctl -u boxcamai -f
   ```

---

### **Vấn đề: Service crash liên tục**

**Kiểm tra:**
```bash
sudo journalctl -u boxcamai -n 100
```

**Nguyên nhân thường gặp:**
- Thiếu dependencies → Cài lại: `pip install -r requirements.txt`
- Lỗi camera → Kiểm tra camera có kết nối không
- Lỗi model → Kiểm tra file `best.onnx` có tồn tại không
- Lỗi network → Kiểm tra kết nối internet

---

## 📝 Lệnh Nhanh (Copy & Paste)

### **Khởi động service:**
```bash
sudo systemctl start boxcamai
```

### **Dừng service:**
```bash
sudo systemctl stop boxcamai
```

### **Restart service:**
```bash
sudo systemctl restart boxcamai
```

### **Xem status:**
```bash
sudo systemctl status boxcamai
```

### **Xem log real-time:**
```bash
sudo journalctl -u boxcamai -f
```

### **Xem log 50 dòng cuối:**
```bash
sudo journalctl -u boxcamai -n 50
```

---

## ✅ Checklist Sau Khi Bật Lại

- [ ] Service đang chạy: `sudo systemctl status boxcamai` → `Active: active (running)`
- [ ] Log không có lỗi: `sudo journalctl -u boxcamai -n 50`
- [ ] Web dashboard → Tab Clients → Status = "Active"
- [ ] Web dashboard → Tab Detections → Chọn client → Có video stream
- [ ] Có detections mới được gửi lên server

---

**Tạo ngày:** 2025-12-09
**Mục đích:** Hướng dẫn khởi động lại client trên Pi sau khi ngắt điện

