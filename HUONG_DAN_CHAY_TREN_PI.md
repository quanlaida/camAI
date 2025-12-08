# 📋 HƯỚNG DẪN CHẠY TRÊN RASPBERRY PI

File này liệt kê tất cả các lệnh cần chạy trên Raspberry Pi.

---

## 📦 **BƯỚC 1: CHUẨN BỊ FILES**

### **Copy files từ máy tính sang Pi:**

Bạn có thể dùng một trong các cách:

#### **Cách 1: SCP (nếu Pi có SSH)**
```bash
# Trên máy tính Windows/Mac, chạy:
scp -r out-quan-boxcamai-client pi@<IP_PI>:/home/pi/
```

#### **Cách 2: USB/Thẻ nhớ**
- Copy toàn bộ thư mục `out-quan-boxcamai-client` vào USB
- Cắm vào Pi và copy vào `/home/pi/`

#### **Cách 3: Git (nếu có repo)**
```bash
cd /home/pi
git clone <your-repo-url>
```

---

## 🔧 **BƯỚC 2: VÀO THỦ MỤC VÀ KIỂM TRA**

```bash
# Vào thư mục client
cd /home/pi/out-quan-boxcamai-client

# Kiểm tra files đã có đầy đủ chưa
ls -la

# Phải thấy các file:
# - main.py
# - detection.py
# - sender.py
# - stream_sender.py  ⚠️ FILE MỚI - QUAN TRỌNG
# - config.py
# - utils.py
# - requirements.txt
# - yolov5s.onnx (hoặc best.onnx)
```

---

## 📥 **BƯỚC 3: CÀI ĐẶT DEPENDENCIES**

### ⚠️ **NẾU GẶP LỖI "externally-managed-environment":**

Đây là lỗi phổ biến trên Raspberry Pi OS mới. Có 3 cách giải quyết:

### **CÁCH 1: Dùng Virtual Environment (KHUYẾN NGHỊ) ✅**

```bash
# Đảm bảo đang ở trong thư mục
cd /home/pi/out-quan-boxcamai-client

# Tạo virtual environment
python3 -m venv venv

# Kích hoạt virtual environment
source venv/bin/activate

# Bây giờ pip sẽ dùng venv
pip install -r requirements.txt

# Hoặc cài từng package:
pip install opencv-python numpy onnxruntime requests

# ⚠️ QUAN TRỌNG: Khi chạy program, phải activate venv trước:
source venv/bin/activate
python3 main.py --rtsp
```

### **CÁCH 2: Dùng --break-system-packages (NHANH NHƯNG RỦI RO) ⚠️**

```bash
cd /home/pi/out-quan-boxcamai-client

# Dùng flag --break-system-packages
pip3 install --break-system-packages -r requirements.txt

# Hoặc cài từng package:
pip3 install --break-system-packages opencv-python numpy onnxruntime requests
```

### **CÁCH 3: Cài qua apt (nếu có sẵn) 📦**

```bash
# Cài một số package có sẵn trong apt
sudo apt update
sudo apt install python3-opencv python3-numpy python3-requests

# Vẫn phải cài onnxruntime qua pip (với --break-system-packages hoặc venv)
pip3 install --break-system-packages onnxruntime
```

### **Kiểm tra cài đặt:**
```bash
python3 -c "import cv2; import numpy; import onnxruntime; import requests; print('✅ All packages installed')"
```

---

## ⚙️ **BƯỚC 4: CẤU HÌNH**

### **Sửa file config.py:**

```bash
nano config.py
```

**Cần sửa các dòng:**
```python
# Server Configuration
SERVER_HOST = 'boxcamai.cloud'  # Hoặc IP server của bạn
SERVER_PORT = 443               # Hoặc 5000 nếu server chạy trên port 5000

# Client Configuration
CLIENT_NAME = 'raspberry_pi_1'  # Đặt tên unique cho Pi này

# RTSP Configuration (nếu cần fallback)
RTSP_USER = 'admin'
RTSP_PASS = 'your_password'
RTSP_PORT = '554'
```

**Lưu:** `Ctrl+X`, `Y`, `Enter`

---

## 🧪 **BƯỚC 5: TEST CHẠY THỬ**

### **Test 1: Kiểm tra syntax**
```bash
python3 -m py_compile main.py
python3 -m py_compile detection.py
python3 -m py_compile sender.py
python3 -m py_compile stream_sender.py

# Nếu không có lỗi → OK
```

### **Test 2: Chạy với video file (nếu có)**
```bash
python3 main.py --video test_video.mp4 --not-sent --display
```

### **Test 3: Chạy với RTSP (không gửi lên server)**
```bash
python3 main.py --rtsp --not-sent
```

**Phải thấy các log:**
```
✅ Client info retrieved: {...}
📹 Video stream sender thread started (raw)
📹 Processed video stream sender thread started (AI detection)
🔄 Server polling thread started (checking every 30s)
Using camera IP from server: <IP>
Connecting to RTSP: rtsp://admin:***@<IP>:554/...
```

---

## 🚀 **BƯỚC 6: CHẠY PRODUCTION**

### **Nếu dùng Virtual Environment:**
```bash
# Phải activate venv trước khi chạy
source venv/bin/activate

# Chạy với RTSP (gửi lên server):
python3 main.py --rtsp

# Chạy với Raspberry Pi Camera:
python3 main.py --rpicam

# Chạy với Webcam:
python3 main.py --webcam
```

### **Nếu KHÔNG dùng Virtual Environment:**
```bash
# Chạy trực tiếp
python3 main.py --rtsp
python3 main.py --rpicam
python3 main.py --webcam
```

---

## 🔄 **BƯỚC 7: CHẠY NHƯ SERVICE (TÙY CHỌN)**

### **Tạo systemd service:**

```bash
# Tạo file service
sudo nano /etc/systemd/system/boxcamai.service
```

**Nội dung:**
```ini
[Unit]
Description=BoxCamAI Detection Client
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/out-quan-boxcamai-client
# Nếu dùng venv, dùng dòng này:
ExecStart=/home/pi/out-quan-boxcamai-client/venv/bin/python3 /home/pi/out-quan-boxcamai-client/main.py --rtsp
# Nếu KHÔNG dùng venv, dùng dòng này:
# ExecStart=/usr/bin/python3 /home/pi/out-quan-boxcamai-client/main.py --rtsp
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Kích hoạt service:**
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (tự động chạy khi boot)
sudo systemctl enable boxcamai

# Start service
sudo systemctl start boxcamai

# Kiểm tra status
sudo systemctl status boxcamai

# Xem log
sudo journalctl -u boxcamai -f
```

---

## 🔍 **CÁC LỆNH KIỂM TRA & DEBUG**

### **Kiểm tra process đang chạy:**
```bash
ps aux | grep main.py
```

### **Kiểm tra log real-time:**
```bash
# Nếu chạy trực tiếp
python3 main.py --rtsp

# Nếu chạy service
sudo journalctl -u boxcamai -f
```

### **Kiểm tra kết nối server:**
```bash
python3 -c "
import requests
import config
try:
    response = requests.get(f'https://{config.SERVER_HOST}:{config.SERVER_PORT}/api/clients/by-name/{config.CLIENT_NAME}', timeout=10)
    print('✅ Connected to server')
    print(f'Status: {response.status_code}')
    if response.status_code == 200:
        data = response.json()
        print(f'IP from server: {data.get(\"ip_address\")}')
except Exception as e:
    print(f'❌ Error: {e}')
"
```

### **Dừng process:**
```bash
# Nếu chạy trực tiếp
Ctrl+C

# Nếu chạy service
sudo systemctl stop boxcamai
```

### **Restart service:**
```bash
sudo systemctl restart boxcamai
```

---

## 📊 **KIỂM TRA STREAMS**

### **Kiểm tra raw stream:**
Mở browser: `http://<SERVER_IP>:5000` → Tab "Live Streams" → Click "Raw"

### **Kiểm tra processed stream:**
Tab "Live Streams" → Click "Processed (AI)"

---

## ⚠️ **XỬ LÝ LỖI THƯỜNG GẶP**

### **Lỗi 1: externally-managed-environment**
```bash
# Dùng virtual environment (khuyến nghị)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# HOẶC dùng --break-system-packages
pip3 install --break-system-packages -r requirements.txt
```

### **Lỗi 2: Module not found**
```bash
# Nếu dùng venv: đảm bảo đã activate
source venv/bin/activate
pip install -r requirements.txt

# Nếu không dùng venv
pip3 install --break-system-packages -r requirements.txt
```

### **Lỗi 2: Permission denied**
```bash
# Chạy với sudo (không khuyến nghị) hoặc fix permission
sudo chown -R pi:pi /home/pi/out-quan-boxcamai-client
```

### **Lỗi 3: Cannot connect to server**
```bash
# Kiểm tra network
ping <SERVER_HOST>

# Kiểm tra config
cat config.py | grep SERVER
```

### **Lỗi 4: RTSP stream failed**
```bash
# Kiểm tra IP camera có đúng không
# Kiểm tra RTSP credentials
# Test RTSP link:
ffmpeg -rtsp_transport tcp -i "rtsp://admin:pass@IP:554/..." -frames:v 1 test.jpg
```

### **Lỗi 5: Model file not found**
```bash
# Kiểm tra file model có tồn tại
ls -la *.onnx

# Kiểm tra config.py
cat config.py | grep MODEL_PATH
```

---

## 📝 **TÓM TẮT CÁC LỆNH CHÍNH**

```bash
# 1. Vào thư mục
cd /home/pi/out-quan-boxcamai-client

# 2. Tạo và activate virtual environment (nếu gặp lỗi externally-managed-environment)
python3 -m venv venv
source venv/bin/activate

# 3. Cài dependencies
pip install -r requirements.txt

# 4. Sửa config (nếu cần)
nano config.py

# 5. Test chạy (đảm bảo venv đã activate)
python3 main.py --rtsp --not-sent

# 6. Chạy production
python3 main.py --rtsp

# 7. Kiểm tra log
# (Xem output trên terminal)
```

---

## 🎯 **QUICK START (VỚI VENV - KHUYẾN NGHỊ)**

```bash
cd /home/pi/out-quan-boxcamai-client && \
python3 -m venv venv && \
source venv/bin/activate && \
pip install -r requirements.txt && \
python3 main.py --rtsp
```

## 🎯 **QUICK START (KHÔNG VENV - NHANH)**

```bash
cd /home/pi/out-quan-boxcamai-client && \
pip3 install --break-system-packages -r requirements.txt && \
python3 main.py --rtsp
```

---

**Tạo ngày:** 2024  
**Người tạo:** Auto AI Assistant

