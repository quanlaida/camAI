## Kiến trúc tổng thể camAI

### Thành phần chính

- **Server** (`out-quan-boxcamai-sv/` hoặc bản tương đương trong `sourcecodemayserver/camAI/camAI/out-quan-boxcamai-sv/`):
  - Flask app: API nhận detection, nhận frame video, stream MJPEG cho web.
  - Quản lý client, lưu DB (SQLAlchemy), gửi cảnh báo (email, Telegram).
  - Ghi video từ stream (ffmpeg) và chia file theo thời gian.

- **Client Orange Pi** (`out-quan-boxcamai-client-orangepi/`):
  - Chạy trên Orange Pi, đọc camera (RTSP/webcam/video file).
  - Chạy model ONNX (YOLO-style), hậu xử lý (NMS, ROI, priority classes, IoU cooldown).
  - Gửi kết quả detection + frame đã vẽ bbox lên server.

### Luồng dữ liệu tổng quát

1. **Camera → Client Orange Pi**  
   - `main.py` trên Orange Pi đọc cấu hình từ server (theo serial).  
   - Tạo 2 process:
     - Process capture: đọc frame từ camera → đẩy vào hàng đợi (queue).
     - Process detection: lấy frame từ queue, chạy model ONNX và hậu xử lý.

2. **Client → Server**  
   - Module gửi detection (ví dụ `sender.py`):
     - Gửi JSON detection + ảnh snapshot (multipart) tới API server.  
   - Module gửi stream (ví dụ `stream_sender.py`):
     - Gửi frame JPEG đã vẽ bbox để server stream real-time.

3. **Server xử lý**  
   - API nhận detection:
     - Lưu thông tin vào DB, ghi lại ảnh nếu cần.
     - Kiểm tra điều kiện cảnh báo (class, vùng, mức độ ưu tiên) → gửi email/Telegram.
   - API nhận frame video:
     - Lưu frame vào bộ nhớ / buffer.
     - Cung cấp endpoint stream MJPEG cho web UI.
   - Module ghi video:
     - Dùng ffmpeg ghi lại stream thành file video, tự động chia file theo thời gian (ví dụ mỗi 30 phút).

### Các quyết định kiến trúc chính

- **Multiprocessing trên client**:
  - Capture và detection tách thành 2 process để tận dụng đa nhân CPU, tránh GIL.

- **IoU cooldown & priority classes**:
  - Hạn chế gửi lặp lại khi đối tượng đứng yên bằng cách so sánh IoU với detection cũ và áp timeout.
  - Một số class quan trọng (ví dụ lửa, khói) luôn được ưu tiên gửi cảnh báo.

- **Quản lý client theo serial**:
  - Mỗi box camera lưu `serial_number.txt`.
  - Server quản lý client theo serial, trả về cấu hình phù hợp khi client khởi động.

- **Cập nhật cấu hình tập trung**:
  - Client định kỳ polling server lấy config mới (ROI, overlay, bật/tắt detect, v.v.).
  - Khi có thay đổi quan trọng, service client được restart tự động.

### Lưu ý mở rộng / refactor sau này

- Nếu thêm loại client mới (ví dụ thiết bị khác ngoài Orange Pi):
  - Tái sử dụng cùng API server.
  - Giữ nguyên format JSON detection nếu có thể, hoặc ghi rõ thay đổi format trong `docs/CHANGELOG.md`.

- Nếu đổi DB hoặc hệ thống cảnh báo:
  - Cố gắng giữ nguyên interface (hàm/service) hiện tại.
  - Ghi rõ thay đổi trong `docs/CHANGELOG.md` để AI khác hiểu lý do và phạm vi ảnh hưởng.
