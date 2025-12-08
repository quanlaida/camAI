# 🎯 AI Detection Dashboard - CamAI

Hệ thống phát hiện đối tượng thông minh sử dụng YOLOv5, Flask và Raspberry Pi.

## 📋 Mô tả

Hệ thống bao gồm:
- **Server**: Flask web server để quản lý detections, clients, và hiển thị dashboard
- **Client**: Raspberry Pi client chạy YOLOv5 để phát hiện đối tượng và gửi về server
- **Web Dashboard**: Giao diện web hiện đại để xem detections, quản lý clients, và cấu hình ROI

## 🚀 Tính năng

### Server
- ✅ Web dashboard với giao diện hiện đại
- ✅ Quản lý nhiều clients (Raspberry Pi)
- ✅ Lưu trữ và hiển thị detections
- ✅ Cảnh báo email khi phát hiện trong ROI
- ✅ Video stream từ camera
- ✅ Cấu hình ROI (Region of Interest) - hỗ trợ nhiều ROI hợp nhất
- ✅ Thống kê real-time

### Client
- ✅ Phát hiện đối tượng sử dụng YOLOv5 (ONNX)
- ✅ Tự động gửi detections về server
- ✅ Hỗ trợ RTSP camera
- ✅ Cấu hình ROI từ server
- ✅ Tự động reconnect khi mất kết nối
- ✅ Video stream processing

## 📁 Cấu trúc Project

```
camAI/
├── out-quan-boxcamai-sv/          # Server code
│   ├── server.py                  # Flask server chính
│   ├── database_setup.py          # Database schema
│   ├── config.py                  # Server configuration
│   ├── templates/                 # HTML templates
│   │   └── index.html
│   └── web/                       # Static files
│       ├── script.js
│       └── style.css
│
├── out-quan-boxcamai-client/      # Client code (Raspberry Pi)
│   ├── main.py                    # Main client script
│   ├── detection.py                # YOLOv5 detection logic
│   ├── config.py                  # Client configuration
│   ├── sender.py                  # Send detections to server
│   ├── stream_sender.py           # Send video stream
│   └── utils.py                   # Utility functions
│
└── README.md                      # File này
```

## 🔧 Cài đặt

### Server

1. **Clone repository**
```bash
git clone <repository-url>
cd camAI/out-quan-boxcamai-sv
```

2. **Cài đặt dependencies**
```bash
pip install -r requirements.txt
```

3. **Cấu hình**
- Chỉnh sửa `config.py` nếu cần
- Thiết lập biến môi trường cho email alerts (nếu dùng):
  ```bash
  export ALERT_EMAIL_SENDER="your-email@gmail.com"
  export ALERT_EMAIL_PASSWORD="your-app-password"
  ```

4. **Khởi động server**
```bash
python server.py
```

Server sẽ chạy tại `http://localhost:5000`

### Client (Raspberry Pi)

1. **Copy code lên Raspberry Pi**
```bash
scp -r out-quan-boxcamai-client pi@<pi-ip>:/home/pi/
```

2. **Cài đặt dependencies**
```bash
cd out-quan-boxcamai-client
pip install -r requirements.txt
```

3. **Cấu hình**
- Chỉnh sửa `config.py`:
  - `CLIENT_NAME`: Tên client (phải unique)
  - `SERVER_HOST`: Địa chỉ server
  - `SERVER_PORT`: Port server
  - `RTSP_URL`: URL camera RTSP (hoặc để None nếu dùng IP từ server)

4. **Chạy client**
```bash
python main.py
```

## 📖 Hướng dẫn sử dụng

### 1. Tạo Client mới

1. Mở web dashboard: `http://localhost:5000`
2. Vào tab **"💻 Clients"**
3. Click **"➕ Add New Client"**
4. Điền thông tin:
   - **Name**: Tên client (phải unique)
   - **IP Address**: IP camera RTSP (nếu có)
   - **ROI**: Vẽ vùng quan tâm trên canvas
5. Click **"Save"**

### 2. Cấu hình ROI

1. Mở client modal
2. Click và kéo trên canvas để vẽ ROI
3. Có thể vẽ nhiều ROI (hỗ trợ nhiều ROI hợp nhất)
4. Click **"📸 Chụp ảnh hiện tại"** để lấy frame từ camera làm nền
5. Save để áp dụng

### 3. Cấu hình Email Alerts

1. Trong dashboard, nhập email vào ô **"📧 Email cảnh báo"**
2. Check **"Bật cảnh báo email"**
3. Click **"💾 Lưu Email"**

**Lưu ý**: Cần cấu hình Gmail App Password (xem `HUONG_DAN_CAU_HINH_EMAIL.md`)

## 🔐 Cấu hình Email (Gmail)

1. Bật 2-Step Verification trên Gmail
2. Tạo App Password:
   - Vào Google Account → Security → App passwords
   - Tạo password mới cho "Mail"
3. Set biến môi trường:
```bash
export ALERT_EMAIL_SENDER="your-email@gmail.com"
export ALERT_EMAIL_PASSWORD="your-app-password"
```

## 📝 Requirements

### Server
- Python 3.7+
- Flask
- SQLAlchemy
- OpenCV (nếu cần xử lý ảnh)

### Client
- Python 3.7+
- ONNX Runtime
- OpenCV
- NumPy
- Requests

Xem chi tiết trong `requirements.txt` của mỗi module.

## 🐛 Troubleshooting

### Client không kết nối được server
- Kiểm tra `SERVER_HOST` và `SERVER_PORT` trong `config.py`
- Kiểm tra firewall
- Kiểm tra server đang chạy

### Không nhận được detections
- Kiểm tra camera RTSP URL
- Kiểm tra ROI đã được cấu hình chưa
- Kiểm tra log trên client

### Email không gửi được
- Kiểm tra App Password đã đúng chưa
- Kiểm tra biến môi trường đã set chưa
- Xem log server để debug

## 📚 Tài liệu tham khảo

- `HUONG_DAN_CAU_HINH_EMAIL.md` - Hướng dẫn cấu hình email
- `HUONG_DAN_CHAY_TREN_PI.md` - Hướng dẫn chạy trên Raspberry Pi
- `HUONG_DAN_DEBUG_SERVER.md` - Debug server
- Các file hướng dẫn khác trong thư mục gốc

## 📄 License

[Thêm license của bạn]

## 👥 Contributors

[Thêm tên contributors]

## 🙏 Acknowledgments

- YOLOv5 by Ultralytics
- Flask framework
- OpenCV

