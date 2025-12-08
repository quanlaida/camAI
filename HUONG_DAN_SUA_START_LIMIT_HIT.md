# 🔧 HƯỚNG DẪN SỬA LỖI "start-limit-hit"

Lỗi này xảy ra khi service restart quá nhiều lần trong thời gian ngắn, systemd tự động chặn.

---

## 🛑 **BƯỚC 1: RESET START LIMIT**

```bash
# Reset start limit để service có thể start lại
sudo systemctl reset-failed boxcamai

# Kiểm tra lại status
sudo systemctl status boxcamai
```

---

## 🔍 **BƯỚC 2: TẮT SERVICE HOÀN TOÀN**

```bash
# Stop service
sudo systemctl stop boxcamai

# Disable (không tự động chạy)
sudo systemctl disable boxcamai

# Reset failed state
sudo systemctl reset-failed boxcamai
```

---

## 📝 **BƯỚC 3: KIỂM TRA SERVICE FILE**

Kiểm tra service file có đúng không:

```bash
# Xem service file
sudo cat /etc/systemd/system/boxcamai.service
```

**Service file nên như thế này:**

```ini
[Unit]
Description=BoxCamAI Detection Client
After=network.target

[Service]
Type=simple
User=leviathan
WorkingDirectory=/home/leviathan/out-quan-boxcamai-client
# Nếu dùng venv:
ExecStart=/home/leviathan/out-quan-boxcamai-client/venv/bin/python3 /home/leviathan/out-quan-boxcamai-client/main.py --rtsp
# Nếu KHÔNG dùng venv:
# ExecStart=/usr/bin/python3 /home/leviathan/out-quan-boxcamai-client/main.py --rtsp
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## 🔧 **BƯỚC 4: SỬA SERVICE FILE (nếu cần)**

```bash
# Sửa service file
sudo nano /etc/systemd/system/boxcamai.service
```

**Quan trọng:**
- `User=` phải đúng user (ví dụ: `leviathan` hoặc `pi`)
- `ExecStart=` phải trỏ đúng đường dẫn Python và file main.py
- Nếu dùng venv, phải trỏ đến Python trong venv
- `WorkingDirectory=` phải đúng thư mục

**Sau khi sửa:**
```bash
# Reload systemd
sudo systemctl daemon-reload

# Reset failed state
sudo systemctl reset-failed boxcamai
```

---

## 🧪 **BƯỚC 5: TEST CHẠY THỦ CÔNG TRƯỚC**

Trước khi chạy service, test thủ công xem có lỗi gì không:

```bash
cd /home/leviathan/out-quan-boxcamai-client
source venv/bin/activate  # Nếu dùng venv
python3 main.py --rtsp --not-sent  # Test không gửi lên server
```

Nếu chạy OK → Service file có thể sai.  
Nếu chạy lỗi → Code có vấn đề, cần sửa code trước.

---

## 🚀 **BƯỚC 6: CHẠY LẠI SERVICE**

Sau khi đã sửa xong:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Reset failed state
sudo systemctl reset-failed boxcamai

# Start service
sudo systemctl start boxcamai

# Kiểm tra status
sudo systemctl status boxcamai

# Xem log real-time
sudo journalctl -u boxcamai -f
```

---

## 📋 **QUICK FIX (Copy-paste tất cả):**

```bash
# 1. Reset và tắt
sudo systemctl reset-failed boxcamai
sudo systemctl stop boxcamai
sudo systemctl disable boxcamai

# 2. Kill process còn sót
pkill -f main.py
pkill -f detection

# 3. Kiểm tra và sửa service file (nếu cần)
sudo nano /etc/systemd/system/boxcamai.service

# 4. Sau khi sửa, reload và test
sudo systemctl daemon-reload
sudo systemctl reset-failed boxcamai

# 5. Test chạy thủ công trước
cd /home/leviathan/out-quan-boxcamai-client
source venv/bin/activate
python3 main.py --rtsp --not-sent
```

---

## ⚠️ **NGUYÊN NHÂN THƯỜNG GẶP:**

1. **Service file sai đường dẫn Python**
   - ✅ Sửa `ExecStart=` trỏ đúng Python

2. **Code có lỗi → service crash liên tục**
   - ✅ Test chạy thủ công trước để tìm lỗi

3. **Thiếu dependencies**
   - ✅ Cài đủ packages trong venv

4. **User không đúng**
   - ✅ Sửa `User=` trong service file

---

**Tạo ngày:** 2024  
**Người tạo:** Auto AI Assistant

