# 📝 GHI CHÚ CÁC THAY ĐỔI TRÊN CLIENT

File này ghi chú tất cả các thay đổi đã được thực hiện trên các file client.

**Ngày cập nhật:** 2024  
**Mục đích:** Copy các file đã sửa từ máy tính này sang Raspberry Pi

---

## ✅ **CÁC FILE ĐÃ SỬA:**

### **1. `main.py`** ⚠️ **QUAN TRỌNG - SỬA NHIỀU CHỖ**

#### **1.1. Import stream_sender (dòng ~10):**
```python
from stream_sender import start_stream_thread, stop_stream_thread_func, send_video_frame
```

#### **1.2. Sửa hàm `video_capture_process()` (dòng ~14):**
**THÊM tham số `camera_ip=None`:**
```python
def video_capture_process(q, stop_event, source, camera_ip=None):
```

#### **1.3. Sửa logic RTSP link (dòng ~33-42):**
**THAY TOÀN BỘ phần RTSP bằng:**
```python
        if source == 'rtsp':
            # Ưu tiên: camera_ip từ server > config.RTSP_IP
            selected_ip = None
            if camera_ip:
                selected_ip = camera_ip
                print(f"Using camera IP from server: {selected_ip}")
            elif config.RTSP_IP:
                selected_ip = config.RTSP_IP
                print(f"Using camera IP from config: {selected_ip}")
            
            # Check if we have an IP address
            if selected_ip is None:
                print("ERROR: No camera IP address available!")
                print("Please set IP address on server or in config.RTSP_IP")
                return  # Thoát hàm thay vì restart service
            
            # Use OpenCV to read from RTSP stream
            rtspLink = f"rtsp://{config.RTSP_USER}:{config.RTSP_PASS}@{selected_ip}:{config.RTSP_PORT}/cam/realmonitor?channel=1&subtype=1"
            print(f"Connecting to RTSP: rtsp://{config.RTSP_USER}:***@{selected_ip}:{config.RTSP_PORT}/...")
```

#### **1.4. Thêm gửi raw frame ở 4 nơi:**
- Sau `q.put(frame)` trong video file (dòng ~29)
- Sau `q.put(frame)` trong RTSP (dòng ~52)
- Sau `q.put(frame)` trong webcam (dòng ~69)
- Sau `q.put(frame)` trong rpicam (dòng ~101)

**Thêm dòng:**
```python
                    send_video_frame(frame)  # Gửi raw frame về server
```

#### **1.5. Thêm hàm `check_server_updates()` và `server_polling_thread()` (sau hàm `get_info()`):**
**THÊM 2 hàm mới** - Xem code đầy đủ trong file đã sửa

#### **1.6. Khởi tạo `ip_address` (dòng ~247):**
```python
        ip_address = None  # Khởi tạo ip_address
```

#### **1.7. Truyền `ip_address` vào hàm (dòng ~278):**
```python
    capture_proc = Process(target=video_capture_process,
                           args=(frame_queue, stop_event, source, ip_address))
```

#### **1.8. Khởi động threads (sau dòng ~280):**
**THÊM:**
```python
    # Start raw video streaming thread
    start_stream_thread()

    # Start server polling thread để kiểm tra thay đổi từ server
    import threading
    polling_thread = None
    if config.ENABLE_AUTO_RESTART:
        current_roi = (roi_x1, roi_y1, roi_x2, roi_y2)
        polling_thread = threading.Thread(
            target=server_polling_thread,
            args=(stop_event, ip_address, current_roi),
            daemon=True
        )
        polling_thread.start()
```

#### **1.9. Cleanup (dòng ~294):**
```python
        stop_stream_thread_func()  # Dừng raw stream thread
```

---

### **2. `detection.py`** ⚠️ **QUAN TRỌNG - SỬA BUG VÀ THÊM FEATURE**

#### **2.1. Import stream_sender (dòng ~15):**
```python
from stream_sender import send_processed_frame
```

#### **2.2. Sửa BUG class_id (dòng ~163-176):**
**TRƯỚC (SAI):**
```python
                    for i in idxs.flatten():
                        # Get class name
                        class_name = config.CLASS_NAMES[class_id]  # ← BUG: class_id chưa được gán
                        ...
                        # Extract bounding box coordinates
                        x, y, w, h = boxes[i]
                        class_id = class_ids[i]  # ← gán ở đây (SAU khi dùng)
```

**SAU (ĐÚNG):**
```python
                    for i in idxs.flatten():
                        # Extract bounding box coordinates và class_id TRƯỚC
                        x, y, w, h = boxes[i]
                        class_id = class_ids[i]  # ← DI CHUYỂN LÊN TRƯỚC
                        score = scores[i]

                        # Get class name (SAU KHI đã có class_id)
                        class_name = config.CLASS_NAMES[class_id]
```

#### **2.3. Thêm gửi processed frame (sau dòng ~205):**
**THÊM:**
```python
                    # Gửi processed frame (có boxes) về server để stream
                    send_processed_frame(frame_original)
```

#### **2.4. Khởi động processed stream thread (dòng ~38-41):**
**THÊM:**
```python
    # Start processed stream thread
    from stream_sender import start_processed_stream_thread
    start_processed_stream_thread()
```

#### **2.5. Cleanup processed stream thread (trong phần finally):**
**THÊM:**
```python
    # Stop processed stream thread
    from stream_sender import stop_processed_stream_thread_func
    stop_processed_stream_thread_func()
```

---

### **3. `sender.py`** ✅ **SỬA BUG**

#### **3.1. Sửa lỗi response.json().error (dòng ~54-55):**
**TRƯỚC:**
```python
                    print(f"error: {response.json().error}")
```

**SAU:**
```python
                    try:
                        error_data = response.json()
                        print(f"error: {error_data.get('error', 'Unknown error')}")
                    except:
                        print(f"error: {response.text}")
```

---

### **4. `config.py`** ✅ **THÊM CẤU HÌNH**

#### **4.1. Thêm polling configuration (cuối file):**
**THÊM:**
```python
# Server polling configuration (kiểm tra thay đổi từ server)
POLL_INTERVAL = 30  # Kiểm tra mỗi 30 giây
ENABLE_AUTO_RESTART = True  # Tự động restart khi có thay đổi IP/ROI
```

---

### **5. `stream_sender.py`** ⭐ **FILE MỚI - TẠO MỚI HOÀN TOÀN**

**File này CHƯA TỒN TẠI trên Pi, cần TẠO MỚI hoàn toàn.**

**Nội dung file:** Copy toàn bộ file `stream_sender.py` từ máy tính này sang Pi.

**Chức năng:**
- Gửi raw video frames về server (10 FPS)
- Gửi processed video frames (có detection boxes) về server (5 FPS)

---

## 📋 **CHECKLIST KHI COPY LÊN PI:**

- [ ] **`main.py`** - Đã sửa đầy đủ 9 chỗ
- [ ] **`detection.py`** - Đã sửa 5 chỗ (bao gồm sửa bug class_id)
- [ ] **`sender.py`** - Đã sửa bug response.json().error
- [ ] **`config.py`** - Đã thêm polling config
- [ ] **`stream_sender.py`** - ⚠️ **FILE MỚI** - Cần tạo mới hoàn toàn
- [ ] **`requirements.txt`** - File đã có, cần cài: `pip3 install -r requirements.txt`

---

## 🔧 **SAU KHI COPY:**

### **1. Cài đặt dependencies (nếu chưa có):**
```bash
cd out-quan-boxcamai-client
pip3 install -r requirements.txt
```

### **2. Kiểm tra file `stream_sender.py` có tồn tại:**
```bash
ls -la stream_sender.py
```

Nếu không có → Copy file từ máy tính sang.

### **3. Test chạy:**
```bash
python3 main.py --rtsp --not-sent
```

Phải thấy:
- "📹 Video stream sender thread started (raw)"
- "📹 Processed video stream sender thread started (AI detection)"
- "🔄 Server polling thread started (checking every 30s)"

---

## ⚠️ **LƯU Ý QUAN TRỌNG:**

1. **File `stream_sender.py` là FILE MỚI** - Không có trên Pi, phải copy sang
2. **Các file khác** - Chỉ cần thay thế phần đã sửa, hoặc copy toàn bộ file mới
3. **Backup trước khi sửa:** `cp -r out-quan-boxcamai-client out-quan-boxcamai-client-backup`
4. **Kiểm tra import:** Đảm bảo tất cả imports đều đúng

---

## 📦 **CÁC FILE CẦN COPY:**

1. ✅ `main.py` - Đã sửa
2. ✅ `detection.py` - Đã sửa
3. ✅ `sender.py` - Đã sửa
4. ✅ `config.py` - Đã sửa
5. ⭐ **`stream_sender.py`** - **FILE MỚI** (quan trọng nhất!)
6. ✅ `requirements.txt` - Đã có

---

**Tạo ngày:** 2024  
**Người tạo:** Auto AI Assistant

