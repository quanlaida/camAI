# 📦 HƯỚNG DẪN CÀI ĐẶT DỰ ÁN

## 🔧 CÀI ĐẶT SERVER

### **Bước 1: Vào thư mục server**
```bash
cd out-quan-boxcamai-sv
```

### **Bước 2: Tạo virtual environment (tùy chọn nhưng khuyến nghị)**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### **Bước 3: Cài đặt dependencies**
```bash
pip install -r requirements.txt
```

### **Bước 4: Chạy server**
```bash
python server.py
```

Server sẽ chạy tại: `http://0.0.0.0:5000` hoặc `http://localhost:5000`

---

## 🔧 CÀI ĐẶT CLIENT (Pi)

### **Bước 1: Vào thư mục client**
```bash
cd out-quan-boxcamai-client
```

### **Bước 2: Cài đặt dependencies**
```bash
pip3 install -r requirements.txt
```

### **Bước 3: Cấu hình**
Mở file `config.py` và chỉnh sửa:
- `CLIENT_NAME`: Tên client (ví dụ: 'raspberry_pi_1')
- `SERVER_HOST`: Địa chỉ server
- `SERVER_PORT`: Port server (443 hoặc 5000)

### **Bước 4: Chạy client**
```bash
# Với RTSP camera
python3 main.py --rtsp

# Với webcam
python3 main.py --webcam

# Với Raspberry Pi camera
python3 main.py --rpicam

# Test với video file
python3 main.py --video test_video.mp4 --not-sent --display
```

---

## 📋 DEPENDENCIES CẦN THIẾT

### **Server:**
- Flask (web framework)
- Flask-CORS (CORS support)
- SQLAlchemy (database ORM)

### **Client:**
- opencv-python (xử lý video)
- numpy (tính toán)
- onnxruntime (chạy AI model)
- requests (HTTP client)

---

## ⚠️ LƯU Ý

1. **Python version**: Cần Python 3.8 trở lên
2. **Models**: Đảm bảo có file model ONNX trong thư mục client (yolov5s.onnx, best.onnx)
3. **Database**: Server sẽ tự động tạo database SQLite khi chạy lần đầu
4. **Images folder**: Server sẽ tự động tạo thư mục `captured_images` để lưu ảnh

---

## 🚀 QUICK START

### **Chạy Server:**
```bash
cd out-quan-boxcamai-sv
pip install -r requirements.txt
python server.py
```

### **Chạy Client (Pi):**
```bash
cd out-quan-boxcamai-client
pip3 install -r requirements.txt
python3 main.py --rtsp
```

---

**Tạo ngày:** 2024
**Người tạo:** Auto AI Assistant

