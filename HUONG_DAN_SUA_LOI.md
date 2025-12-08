# 📝 HƯỚNG DẪN SỬA LỖI CHI TIẾT

File này ghi chú tất cả các thay đổi/sửa lỗi cần thực hiện trên Raspi.

---

## 🐛 **BUG 1: Biến `ip_address` chưa được khai báo trong hàm `video_capture_process`**

### **Vị trí file:**
`out-quan-boxcamai-client/main.py`

### **Vấn đề:**
- Dòng 33: Biến `ip_address` được sử dụng nhưng chưa được khai báo `global`
- Biến này chỉ được khai báo `global` ở dòng 233 trong hàm `main()`, nhưng được dùng ở dòng 33 trong hàm `video_capture_process()`

### **Cách sửa:**

**Bước 1:** Mở file `out-quan-boxcamai-client/main.py`

**Bước 2:** Tìm hàm `video_capture_process` (bắt đầu từ dòng 13)

**Bước 3:** Sửa dòng 13, thêm `global ip_address` vào đầu hàm:

**TRƯỚC:**
```python
def video_capture_process(q, stop_event, source):
    if config.VIDEO_FILE_PATH:
```

**SAU:**
```python
def video_capture_process(q, stop_event, source):
    global ip_address  # ← THÊM DÒNG NÀY
    if config.VIDEO_FILE_PATH:
```

**Hoặc** nếu muốn an toàn hơn, khởi tạo biến ở đầu file:

**Bước 4 (tùy chọn):** Thêm ở đầu file `main.py`, sau các dòng import (khoảng dòng 10):

```python
# Global variable for camera IP address
ip_address = None
```

---

## 🐛 **BUG 2: Sử dụng `class_id` trước khi gán giá trị**

### **Vị trí file:**
`out-quan-boxcamai-client/detection.py`

### **Vấn đề:**
- Dòng 161: Sử dụng `class_id` để lấy `class_name` 
- Nhưng `class_id` chỉ được gán giá trị từ `class_ids[i]` ở dòng 170 (sau đó 9 dòng)
- Điều này sẽ gây lỗi: `class_id` sẽ lấy giá trị từ vòng lặp trước (có thể sai)

### **Cách sửa:**

**Bước 1:** Mở file `out-quan-boxcamai-client/detection.py`

**Bước 2:** Tìm dòng 158-171 (trong hàm `detection_process`)

**Bước 3:** Sửa lại thứ tự, lấy `class_id` trước khi sử dụng:

**TRƯỚC:**
```python
                if len(idxs) > 0:
                    for i in idxs.flatten():
                        # Get class name
                        class_name = config.CLASS_NAMES[class_id]  # ← BUG: class_id chưa được gán
                        # class_name = config.CLASS_NAMES2[class_id]

                        # Check if this object should be tracked
                        if config.TRACKED_OBJECTS and class_name not in config.TRACKED_OBJECTS:
                            continue

                        # Extract bounding box coordinates
                        x, y, w, h = boxes[i]
                        class_id = class_ids[i]  # ← class_id được gán ở đây (SAU khi sử dụng)
                        score = scores[i]
```

**SAU:**
```python
                if len(idxs) > 0:
                    for i in idxs.flatten():
                        # Extract bounding box coordinates và class_id TRƯỚC
                        x, y, w, h = boxes[i]
                        class_id = class_ids[i]  # ← DI CHUYỂN LÊN TRƯỚC
                        score = scores[i]

                        # Get class name (SAU KHI đã có class_id)
                        class_name = config.CLASS_NAMES[class_id]
                        # class_name = config.CLASS_NAMES2[class_id]

                        # Check if this object should be tracked
                        if config.TRACKED_OBJECTS and class_name not in config.TRACKED_OBJECTS:
                            continue
```

**Lưu ý:** Đảm bảo phần code từ dòng 169-171 được di chuyển lên trước dòng 161.

---

## 🐛 **BUG 3: Lỗi truy cập thuộc tính JSON response**

### **Vị trí file:**
`out-quan-boxcamai-client/sender.py`

### **Vấn đề:**
- Dòng 55: `response.json().error` - sai cú pháp
- `response.json()` trả về dictionary, không phải object có thuộc tính `.error`

### **Cách sửa:**

**Bước 1:** Mở file `out-quan-boxcamai-client/sender.py`

**Bước 2:** Tìm dòng 54-55:

**TRƯỚC:**
```python
                else:
                    print(f"Failed to send detection: HTTP {response.status_code}")
                    print(f"error: {response.json().error}")  # ← BUG: sai cú pháp
```

**SAU:**
```python
                else:
                    print(f"Failed to send detection: HTTP {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"error: {error_data.get('error', 'Unknown error')}")  # ← SỬA THÀNH
                    except:
                        print(f"error: {response.text}")  # ← Nếu không parse được JSON
```

---

## 🔧 **FEATURE: Tự động sử dụng IP camera từ Server để tạo RTSP link**

### **Vị trí file:**
`out-quan-boxcamai-client/main.py`

### **Vấn đề:**
- Pi đã nhận được `ip_address` từ server (dòng 234 trong hàm `main()`)
- Nhưng khi gọi `video_capture_process()` (dòng 273-274), biến `ip_address` **KHÔNG được truyền vào** hàm
- Hàm `video_capture_process()` chỉ nhận `(q, stop_event, source)` nên không biết IP camera từ server
- Kết quả: RTSP link không sử dụng IP từ server mà chỉ dùng `config.RTSP_IP` (có thể là None)

### **Giải pháp:**
Truyền `ip_address` vào hàm `video_capture_process()` như một tham số, và ưu tiên sử dụng IP từ server.

### **Cách sửa:**

#### **Bước 1:** Sửa hàm `video_capture_process()` để nhận thêm tham số `camera_ip`

Tìm dòng 13 trong `main.py`:

**TRƯỚC:**
```python
def video_capture_process(q, stop_event, source):
    global ip_address  # (nếu đã thêm từ BUG 1)
    if config.VIDEO_FILE_PATH:
```

**SAU:**
```python
def video_capture_process(q, stop_event, source, camera_ip=None):
    if config.VIDEO_FILE_PATH:
```

#### **Bước 2:** Sửa logic tạo RTSP link (dòng 31-37)

**TRƯỚC:**
```python
        if source == 'rtsp':
            # make sure there is cam ip
            if ip_address is None and config.RTSP_IP is None:
                print("no cam detected")
                restart_service()
            # Use OpenCV to read from RTSP stream
            rtspLink = f"rtsp://{config.RTSP_USER}:{config.RTSP_PASS}@{ip_address if not config.RTSP_IP else config.RTSP_IP}:{config.RTSP_PORT}/cam/realmonitor?channel=1&subtype=1"
```

**SAU:**
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

#### **Bước 3:** Truyền `ip_address` vào khi gọi hàm (dòng 272-275)

Tìm dòng 272-275:

**TRƯỚC:**
```python
    # Start video capture process
    capture_proc = Process(target=video_capture_process,
                           args=(frame_queue, stop_event, source))
    capture_proc.start()
```

**SAU:**
```python
    # Start video capture process (truyền ip_address vào)
    capture_proc = Process(target=video_capture_process,
                           args=(frame_queue, stop_event, source, ip_address))
    capture_proc.start()
```

#### **Bước 4 (QUAN TRỌNG):** Đảm bảo `ip_address` được khởi tạo

Tìm dòng 240-244, sửa để khởi tạo `ip_address`:

**TRƯỚC:**
```python
    else:
        print("Could not retrieve client info, using default settings")
        is_detect_enabled = True
        roi_x1 = roi_y1 = roi_x2 = roi_y2 = None
```

**SAU:**
```python
    else:
        print("Could not retrieve client info, using default settings")
        is_detect_enabled = True
        roi_x1 = roi_y1 = roi_x2 = roi_y2 = None
        ip_address = None  # ← THÊM DÒNG NÀY để đảm bảo biến được khởi tạo
```

### **Tóm tắt thay đổi:**

1. ✅ **Dòng 13:** Thêm tham số `camera_ip=None` vào `video_capture_process()`
2. ✅ **Dòng 31-37:** Sửa logic ưu tiên IP: `camera_ip` > `config.RTSP_IP`
3. ✅ **Dòng 273-274:** Truyền `ip_address` vào hàm khi gọi
4. ✅ **Dòng 244:** Khởi tạo `ip_address = None` nếu không lấy được từ server

### **Logic ưu tiên IP:**
```
1. camera_ip (từ server) ← ƯU TIÊN NHẤT
2. config.RTSP_IP (từ config.py)
3. None → Báo lỗi và thoát
```

---

## 🔄 **FEATURE: Tự động restart khi IP Camera thay đổi trên Web Server**

### **Vị trí file:**
`out-quan-boxcamai-client/main.py`

### **Vấn đề:**
- Hiện tại Pi chỉ lấy thông tin từ server **1 lần khi khởi động** (dòng 225)
- Khi admin thay đổi IP camera trên Web server, Pi **KHÔNG tự động phát hiện** và restart
- Phải **restart thủ công** service hoặc reboot Pi mới áp dụng được IP mới

### **Giải pháp:**
Tạo một **thread riêng** để định kỳ kiểm tra thông tin từ server. Nếu phát hiện IP camera hoặc ROI thay đổi, tự động restart service.

### **Cách sửa:**

#### **Bước 1: Thêm cấu hình polling vào `config.py`**

Mở file `out-quan-boxcamai-client/config.py`, thêm vào cuối file (sau dòng 78):

```python
# Server polling configuration (kiểm tra thay đổi từ server)
POLL_INTERVAL = 30  # Kiểm tra mỗi 30 giây
ENABLE_AUTO_RESTART = True  # Tự động restart khi có thay đổi
```

#### **Bước 2: Tạo hàm polling để kiểm tra thay đổi**

Thêm vào `main.py`, sau hàm `get_info()` (sau dòng 118):

```python
def check_server_updates(current_ip, current_roi):
    """
    Kiểm tra xem có thay đổi từ server không
    Returns: (ip_changed, roi_changed, new_ip, new_roi) hoặc None nếu lỗi
    """
    try:
        client_info = get_info()
        if not client_info:
            return None
        
        new_ip = client_info.get('ip_address')
        new_roi = (
            client_info.get('roi_x1'),
            client_info.get('roi_y1'),
            client_info.get('roi_x2'),
            client_info.get('roi_y2')
        )
        
        # So sánh IP
        ip_changed = (current_ip != new_ip)
        
        # So sánh ROI (None-safe comparison)
        roi_changed = False
        if current_roi != new_roi:
            # Kiểm tra chi tiết hơn (xử lý trường hợp None)
            current_roi_tuple = tuple(x if x is not None else 0 for x in current_roi) if current_roi else (0, 0, 0, 0)
            new_roi_tuple = tuple(x if x is not None else 0 for x in new_roi) if new_roi else (0, 0, 0, 0)
            roi_changed = (current_roi_tuple != new_roi_tuple)
        
        return (ip_changed, roi_changed, new_ip, new_roi)
    
    except Exception as e:
        print(f"Error checking server updates: {e}")
        return None


def server_polling_thread(stop_event, initial_ip, initial_roi):
    """
    Thread chạy nền để kiểm tra thay đổi từ server định kỳ
    Nếu phát hiện thay đổi IP hoặc ROI, tự động restart service
    """
    import time
    import config
    
    if not config.ENABLE_AUTO_RESTART:
        print("Auto-restart disabled in config, skipping polling thread")
        return
    
    current_ip = initial_ip
    current_roi = initial_roi
    poll_count = 0
    
    print(f"🔄 Server polling thread started (checking every {config.POLL_INTERVAL}s)")
    
    while not stop_event.is_set():
        try:
            # Đợi interval giữa các lần kiểm tra
            stop_event.wait(config.POLL_INTERVAL)
            
            if stop_event.is_set():
                break
            
            poll_count += 1
            print(f"🔍 Polling server... (check #{poll_count})")
            
            # Kiểm tra thay đổi
            result = check_server_updates(current_ip, current_roi)
            
            if result is None:
                print("⚠️ Could not check server updates, will retry next time")
                continue
            
            ip_changed, roi_changed, new_ip, new_roi = result
            
            # Phát hiện thay đổi
            if ip_changed:
                print(f"🔄 IP Camera changed detected!")
                print(f"   Old IP: {current_ip}")
                print(f"   New IP: {new_ip}")
                print("🔄 Restarting service to apply changes...")
                restart_service()
                return  # Thread sẽ kết thúc sau khi restart
            
            if roi_changed:
                print(f"🔄 ROI changed detected!")
                print(f"   Old ROI: {current_roi}")
                print(f"   New ROI: {new_roi}")
                print("🔄 Restarting service to apply changes...")
                restart_service()
                return  # Thread sẽ kết thúc sau khi restart
            
            # Cập nhật giá trị hiện tại (để lần sau so sánh)
            current_ip = new_ip
            current_roi = new_roi
            
            if poll_count % 10 == 0:  # Log mỗi 10 lần
                print(f"✅ No changes detected (checked {poll_count} times)")
        
        except Exception as e:
            print(f"❌ Error in polling thread: {e}")
            # Tiếp tục polling dù có lỗi
    
    print("🛑 Server polling thread stopped")
```

#### **Bước 3: Khởi động polling thread trong hàm `main()`**

Tìm hàm `main()`, sau khi tạo các process (sau dòng 275), thêm code khởi động polling thread:

**TRƯỚC:**
```python
    # Start video capture process (truyền ip_address vào)
    capture_proc = Process(target=video_capture_process,
                           args=(frame_queue, stop_event, source, ip_address))
    capture_proc.start()

    try:
        print("Starting object detection...")
```

**SAU:**
```python
    # Start video capture process (truyền ip_address vào)
    capture_proc = Process(target=video_capture_process,
                           args=(frame_queue, stop_event, source, ip_address))
    capture_proc.start()

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

    try:
        print("Starting object detection...")
```

#### **Bước 4: Đảm bảo import threading**

Kiểm tra đầu file `main.py`, đảm bảo có import `threading`:

**Tìm dòng 5-6:**
```python
from multiprocessing import Process, Queue, Event
import argparse
```

**Nếu chưa có, thêm:**
```python
from multiprocessing import Process, Queue, Event
import threading  # ← THÊM DÒNG NÀY
import argparse
```

Hoặc có thể import trực tiếp trong hàm (như đã làm ở Bước 3).

### **Tóm tắt thay đổi:**

1. ✅ **`config.py`** - Thêm 2 biến cấu hình:
   - `POLL_INTERVAL = 30` (giây)
   - `ENABLE_AUTO_RESTART = True`

2. ✅ **`main.py`** - Thêm 2 hàm mới:
   - `check_server_updates()` - Kiểm tra thay đổi
   - `server_polling_thread()` - Thread polling nền

3. ✅ **`main.py`** - Khởi động polling thread sau khi start các process

### **Cách hoạt động:**

```
1. Pi khởi động → Lấy IP và ROI từ server
2. Khởi động polling thread → Kiểm tra mỗi 30 giây
3. So sánh IP/ROI hiện tại với server
4. Nếu khác → Restart service
5. Service restart → Áp dụng IP/ROI mới
```

### **Tùy chỉnh:**

- **Tăng/tăng tần suất kiểm tra:** Sửa `POLL_INTERVAL` trong `config.py` (giây)
- **Tắt auto-restart:** Đặt `ENABLE_AUTO_RESTART = False` trong `config.py`
- **Kiểm tra cả ROI:** Code đã hỗ trợ, sẽ restart nếu ROI thay đổi

### **Log mẫu khi hoạt động:**

```
🔄 Server polling thread started (checking every 30s)
🔍 Polling server... (check #1)
🔍 Polling server... (check #2)
...
🔍 Polling server... (check #5)
🔄 IP Camera changed detected!
   Old IP: 192.168.1.100
   New IP: 192.168.1.200
🔄 Restarting service to apply changes...
```

---

## 📋 **CHECKLIST SAU KHI SỬA:**

Sau khi sửa xong, kiểm tra:

### **BUG FIXES:**
- [ ] Đã sửa `main.py` BUG 1 - thêm `global ip_address` vào hàm `video_capture_process` (hoặc dùng cách truyền tham số)
- [ ] Đã sửa `detection.py` BUG 2 - di chuyển `class_id = class_ids[i]` lên trước khi dùng
- [ ] Đã sửa `sender.py` BUG 3 - sửa cách truy cập error từ JSON response

### **FEATURE - IP Camera từ Server:**
- [ ] Đã sửa `main.py` dòng 13 - thêm tham số `camera_ip=None` vào `video_capture_process()`
- [ ] Đã sửa `main.py` dòng 31-37 - sửa logic ưu tiên IP (camera_ip > config.RTSP_IP)
- [ ] Đã sửa `main.py` dòng 273-274 - truyền `ip_address` vào hàm khi gọi
- [ ] Đã sửa `main.py` dòng 244 - khởi tạo `ip_address = None`

### **FEATURE - Auto Restart khi IP thay đổi:**
- [ ] Đã thêm vào `config.py` - `POLL_INTERVAL = 30` và `ENABLE_AUTO_RESTART = True`
- [ ] Đã thêm hàm `check_server_updates()` vào `main.py`
- [ ] Đã thêm hàm `server_polling_thread()` vào `main.py`
- [ ] Đã khởi động polling thread trong hàm `main()` (sau dòng 275)
- [ ] Đã import `threading` nếu cần

### **FEATURE - Video Stream từ Pi về Web:**
- [ ] **Server:** Đã thêm `video_frames` dict và lock vào `server.py`
- [ ] **Server:** Đã thêm endpoint `/api/video/frame` (POST) vào `server.py`
- [ ] **Server:** Đã thêm endpoint `/api/video/stream/<client_id>` (GET) vào `server.py`
- [ ] **Server:** Đã thêm tab "Live Streams" vào `index.html`
- [ ] **Server:** Đã thêm CSS cho streams vào `style.css`
- [ ] **Server:** Đã thêm JavaScript `loadStreams()` và `displayStreams()` vào `script.js`
- [ ] **Client:** Đã tạo file mới `stream_sender.py`
- [ ] **Client:** Đã import `stream_sender` vào `main.py`
- [ ] **Client:** Đã gọi `send_video_frame()` ở 4 nơi (video, RTSP, webcam, rpicam)
- [ ] **Client:** Đã khởi động và cleanup stream thread trong `main()`

### **TEST:**
- [ ] Đã test lại code bằng cách chạy thử
- [ ] Test: Đặt IP camera trên Web server, kiểm tra Pi có tự động dùng IP đó không
- [ ] Test: Nếu không có IP từ server, kiểm tra có dùng `config.RTSP_IP` không

---

## 🔍 **CÁCH KIỂM TRA:**

### **1. Kiểm tra syntax:**
```bash
cd out-quan-boxcamai-client
python3 -m py_compile main.py
python3 -m py_compile detection.py
python3 -m py_compile sender.py
```

### **2. Test chạy (nếu có webcam hoặc video test):**
```bash
# Test với video file
python3 main.py --video test_video.mp4 --not-sent --display

# Test với webcam
python3 main.py --webcam --not-sent --display

# Test với RTSP (sau khi đã set IP trên server)
python3 main.py --rtsp --not-sent
```

### **3. Test IP Camera từ Server:**
```bash
# Bước 1: Đăng nhập Web server, vào tab Clients
# Bước 2: Edit client, nhập IP camera (ví dụ: 192.168.1.100)
# Bước 3: Save client
# Bước 4: Chạy Pi với RTSP:
python3 main.py --rtsp --not-sent

# Bước 5: Kiểm tra log, phải thấy:
# "Using camera IP from server: 192.168.1.100"
# "Connecting to RTSP: rtsp://admin:***@192.168.1.100:554/..."
```

### **4. Test Auto Restart khi IP thay đổi:**
```bash
# Bước 1: Chạy Pi service
sudo systemctl start boxcamai
# hoặc
python3 main.py --rtsp

# Bước 2: Kiểm tra log để thấy polling thread đã chạy:
sudo journalctl -u boxcamai -f
# Phải thấy: "🔄 Server polling thread started (checking every 30s)"

# Bước 3: Đăng nhập Web server, edit client, thay đổi IP camera
# (ví dụ: từ 192.168.1.100 → 192.168.1.200)

# Bước 4: Đợi tối đa 30 giây (POLL_INTERVAL)
# Kiểm tra log, phải thấy:
# "🔍 Polling server... (check #N)"
# "🔄 IP Camera changed detected!"
# "🔄 Restarting service to apply changes..."

# Bước 5: Service sẽ tự restart và áp dụng IP mới
```

### **5. Debug nếu không hoạt động:**
```bash
# Kiểm tra Pi có nhận được IP từ server không:
python3 -c "
import requests
import config
response = requests.get(f'https://{config.SERVER_HOST}:{config.SERVER_PORT}/api/clients/by-name/{config.CLIENT_NAME}', timeout=10)
if response.status_code == 200:
    data = response.json()
    print('IP from server:', data.get('ip_address'))
    print('ROI:', data.get('roi_x1'), data.get('roi_y1'), data.get('roi_x2'), data.get('roi_y2'))
else:
    print('Error:', response.status_code)
"

# Kiểm tra config polling:
python3 -c "
import config
print('POLL_INTERVAL:', config.POLL_INTERVAL)
print('ENABLE_AUTO_RESTART:', config.ENABLE_AUTO_RESTART)
"
```

---

## 📝 **GHI CHÚ THÊM:**

- Nếu gặp lỗi khác khi chạy, ghi lại lỗi và thông báo để bổ sung vào file này
- Backup code cũ trước khi sửa: `cp -r out-quan-boxcamai-client out-quan-boxcamai-client-backup`
- Các file cần chỉnh sửa:

### **CLIENT (Pi):**
  1. `out-quan-boxcamai-client/config.py`
     - Thêm `POLL_INTERVAL = 30`
     - Thêm `ENABLE_AUTO_RESTART = True`
  2. `out-quan-boxcamai-client/main.py` 
     - Dòng 13: Thêm tham số `camera_ip=None`
     - Sau dòng 118: Thêm hàm `check_server_updates()` và `server_polling_thread()`
     - Dòng 31-37: Sửa logic RTSP link
     - Dòng 244: Khởi tạo `ip_address = None`
     - Dòng 273-274: Truyền `ip_address` vào hàm
     - Sau dòng 275: Khởi động polling thread
     - Import `stream_sender`
     - Gọi `send_video_frame()` ở 4 nơi capture frame
     - Khởi động và cleanup stream thread
  3. `out-quan-boxcamai-client/detection.py` (dòng 158-171) - BUG 2
  4. `out-quan-boxcamai-client/sender.py` (dòng 54-55) - BUG 3
  5. **TẠO MỚI:** `out-quan-boxcamai-client/stream_sender.py`

### **SERVER:**
  1. `out-quan-boxcamai-sv/server.py`
     - Thêm `video_frames` dict và lock
     - Thêm endpoint `/api/video/frame` (POST)
     - Thêm endpoint `/api/video/stream/<client_id>` (GET)
  2. `out-quan-boxcamai-sv/templates/index.html`
     - Thêm tab "Live Streams"
     - Thêm streams-grid container
  3. `out-quan-boxcamai-sv/web/style.css`
     - Thêm CSS cho streams
  4. `out-quan-boxcamai-sv/web/script.js`
     - Thêm `loadStreams()` và `displayStreams()`
     - Sửa `switchTab()` và `initializeApp()`

---

**Tạo ngày:** $(date)
**Người tạo:** Auto AI Assistant

---

## 📹 **FEATURE: Stream Video thô từ Pi về Server và hiển thị trên Web**

### **Mục tiêu:**
- Pi gửi video stream (frames chưa qua AI) về server
- Server lưu trữ frames và cung cấp MJPEG stream
- Web dashboard hiển thị live video stream từ Pi

### **Kiến trúc:**
```
Pi (Client)          Server              Web Browser
    |                   |                      |
    |-- Frame 1 ------->|                      |
    |                   |-- [Lưu frame]        |
    |-- Frame 2 ------->|                      |
    |                   |-- [Lưu frame]        |
    |                   |<--- MJPEG Stream ----|
    |                   |                      |
    |                   |                  [Hiển thị video]
```

---

## **PHẦN 1: SERVER - Nhận và lưu video frames**

### **Vị trí file:**
`out-quan-boxcamai-sv/server.py`

### **Bước 1: Thêm dictionary để lưu frames trong memory**

Tìm dòng 19 (sau `Session = sessionmaker(bind=engine)`), thêm:

```python
# Initialize database
engine = init_database()
Session = sessionmaker(bind=engine)

# Video streaming storage (lưu frames trong memory)
# Format: {client_id: {'frame': bytes, 'timestamp': datetime}}
video_frames = {}
import threading
video_frames_lock = threading.Lock()
```

### **Bước 2: Thêm endpoint nhận video frames từ Pi**

Thêm vào `server.py`, sau endpoint `/api/images/<path:filename>` (sau dòng 271):

```python
@app.route('/api/video/frame', methods=['POST'])
def receive_video_frame():
    """Nhận video frame từ Pi client"""
    try:
        # Lấy client info từ request
        client_name = request.form.get('client_name')
        if not client_name:
            return jsonify({'error': 'client_name is required'}), 400
        
        # Lấy frame image
        if 'frame' not in request.files:
            return jsonify({'error': 'No frame file provided'}), 400
        
        frame_file = request.files['frame']
        
        # Tìm client trong database
        session = Session()
        client = session.query(Client).filter(Client.name == client_name).first()
        session.close()
        
        if not client:
            return jsonify({'error': 'Client not found'}), 404
        
        # Lưu frame vào memory
        frame_bytes = frame_file.read()
        with video_frames_lock:
            video_frames[client.id] = {
                'frame': frame_bytes,
                'timestamp': datetime.now()
            }
        
        return jsonify({'message': 'Frame received'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### **Bước 3: Thêm endpoint MJPEG stream để web hiển thị**

Thêm vào `server.py`, sau endpoint vừa tạo:

```python
@app.route('/api/video/stream/<int:client_id>')
def video_stream(client_id):
    """MJPEG stream endpoint để hiển thị video trên web"""
    from flask import Response
    
    def generate():
        """Generator function để tạo MJPEG stream"""
        while True:
            with video_frames_lock:
                if client_id in video_frames:
                    frame_data = video_frames[client_id]['frame']
                    timestamp = video_frames[client_id]['timestamp']
                    
                    # Kiểm tra frame cũ (quá 5 giây thì không hiển thị)
                    age = (datetime.now() - timestamp).total_seconds()
                    if age < 5:
                        # MJPEG format: boundary + frame data
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + 
                               frame_data + b'\r\n')
                    else:
                        # Frame quá cũ, gửi frame trắng hoặc skip
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n')
            import time
            time.sleep(0.033)  # ~30 FPS
    
    return Response(generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
```

---

## **PHẦN 2: CLIENT (Pi) - Gửi video frames về server**

### **Vị trí file:**
`out-quan-boxcamai-client/main.py` và tạo file mới `stream_sender.py`

### **Bước 1: Tạo file mới `stream_sender.py`**

Tạo file `out-quan-boxcamai-client/stream_sender.py`:

```python
import requests
import threading
import time
import config
from multiprocessing import Queue
import cv2
import io

# Global queue để nhận frames từ video capture process
video_stream_queue = Queue(maxsize=2)  # Chỉ giữ 2 frames (latest)
stream_thread = None
stop_stream_thread = threading.Event()

def send_video_frame(frame):
    """Thêm frame vào queue để gửi về server"""
    try:
        if not video_stream_queue.full():
            # Resize frame để giảm bandwidth (tùy chọn)
            resized_frame = cv2.resize(frame, (640, 480))
            video_stream_queue.put(resized_frame.copy())
    except Exception as e:
        print(f"Error queuing video frame: {e}")

def stream_worker():
    """Worker thread gửi frames về server"""
    global stop_stream_thread
    
    print("📹 Video stream sender thread started")
    
    while not stop_stream_thread.is_set():
        try:
            # Lấy frame từ queue với timeout
            try:
                frame = video_stream_queue.get(timeout=1.0)
            except:
                continue  # Timeout, tiếp tục loop
            
            if frame is None:
                continue
            
            # Encode frame thành JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if not ret:
                continue
            
            # Convert to bytes
            frame_bytes = io.BytesIO(buffer).read()
            
            # Gửi về server
            try:
                files = {'frame': ('frame.jpg', frame_bytes, 'image/jpeg')}
                data = {'client_name': config.CLIENT_NAME}
                
                response = requests.post(
                    f'https://{config.SERVER_HOST}:{config.SERVER_PORT}/api/video/frame',
                    files=files,
                    data=data,
                    timeout=2
                )
                
                if response.status_code != 200:
                    print(f"⚠️ Failed to send video frame: {response.status_code}")
            
            except requests.exceptions.RequestException as e:
                # Không in log liên tục để tránh spam
                pass
            
            # Rate limiting: gửi tối đa 10 FPS (mỗi 0.1s một frame)
            time.sleep(0.1)
        
        except Exception as e:
            print(f"❌ Error in stream worker: {e}")
            time.sleep(1)
    
    print("📹 Video stream sender thread stopped")

def start_stream_thread():
    """Khởi động thread gửi video stream"""
    global stream_thread, stop_stream_thread
    
    if stream_thread is None or not stream_thread.is_alive():
        stop_stream_thread.clear()
        stream_thread = threading.Thread(target=stream_worker, daemon=True)
        stream_thread.start()
        print("📹 Video streaming enabled")

def stop_stream_thread_func():
    """Dừng thread gửi video stream"""
    global stop_stream_thread
    stop_stream_thread.set()
    if stream_thread and stream_thread.is_alive():
        stream_thread.join(timeout=2)
```

### **Bước 2: Sửa `main.py` để gửi frames**

#### **2.1: Import stream_sender**

Thêm vào đầu file `main.py` (sau các dòng import):

```python
from stream_sender import start_stream_thread, stop_stream_thread_func, send_video_frame
```

#### **2.2: Gửi frames trong `video_capture_process`**

Sửa hàm `video_capture_process`, thêm gửi frame sau khi đọc được:

**Tìm dòng 26-27 (trong phần đọc video file):**
```python
                if frame is not None and not q.full():
                    q.put(frame)
```

**Sửa thành:**
```python
                if frame is not None and not q.full():
                    q.put(frame)
                    send_video_frame(frame)  # ← THÊM DÒNG NÀY
```

**Tìm dòng 48-49 (trong phần RTSP):**
```python
                    if frame is not None and not q.full():
                        q.put(frame)
```

**Sửa thành:**
```python
                    if frame is not None and not q.full():
                        q.put(frame)
                        send_video_frame(frame)  # ← THÊM DÒNG NÀY
```

**Tìm dòng 64-65 (trong phần webcam):**
```python
                    if frame is not None and not q.full():
                        q.put(frame)
```

**Sửa thành:**
```python
                    if frame is not None and not q.full():
                        q.put(frame)
                        send_video_frame(frame)  # ← THÊM DÒNG NÀY
```

**Tìm dòng 95-96 (trong phần rpicam):**
```python
                        if frame is not None and not q.full():
                            q.put(frame)
```

**Sửa thành:**
```python
                        if frame is not None and not q.full():
                            q.put(frame)
                            send_video_frame(frame)  # ← THÊM DÒNG NÀY
```

#### **2.3: Khởi động và dừng stream thread**

**Trong hàm `main()`, sau dòng 275 (sau khi start capture_proc):**

```python
    # Start video capture process (truyền ip_address vào)
    capture_proc = Process(target=video_capture_process,
                           args=(frame_queue, stop_event, source, ip_address))
    capture_proc.start()

    # Start video streaming thread
    start_stream_thread()  # ← THÊM DÒNG NÀY

    # Start server polling thread để kiểm tra thay đổi từ server
    ...
```

**Trong phần `finally` (dòng 286-294), thêm cleanup:**

```python
    finally:
        # Cleanup
        stop_event.set()
        stop_stream_thread_func()  # ← THÊM DÒNG NÀY
        capture_proc.join(timeout=5)
        detection_proc.join(timeout=5)
        # Note: Sender thread cleanup is now handled in detection process
        print("Detection client stopped")
```

---

## **PHẦN 3: WEB - Hiển thị video stream**

### **Vị trí file:**
`out-quan-boxcamai-sv/templates/index.html` và `out-quan-boxcamai-sv/web/script.js`

### **Bước 1: Thêm tab "Live Stream" vào HTML**

Mở `templates/index.html`, tìm dòng 13-16 (nav-tabs):

**TRƯỚC:**
```html
            <nav class="nav-tabs">
                <button class="tab-btn active" data-tab="detections">Detections</button>
                <button class="tab-btn" data-tab="clients">Clients</button>
            </nav>
```

**SAU:**
```html
            <nav class="nav-tabs">
                <button class="tab-btn active" data-tab="detections">Detections</button>
                <button class="tab-btn" data-tab="clients">Clients</button>
                <button class="tab-btn" data-tab="streams">Live Streams</button>
            </nav>
```

### **Bước 2: Thêm tab content cho Live Streams**

Tìm sau phần `<!-- Clients Tab Content -->` (sau dòng 108), thêm:

```html
        <!-- Live Streams Tab Content -->
        <div id="streams-tab" class="tab-content" style="display: none;">
            <div class="streams-container">
                <div class="streams-header">
                    <h2>Live Video Streams</h2>
                    <button id="refresh-streams-btn" class="btn-primary">Refresh</button>
                </div>
                <div id="streams-grid" class="streams-grid">
                    <!-- Stream cards will be inserted here -->
                </div>
            </div>
        </div>
```

### **Bước 3: Thêm CSS cho streams**

Thêm vào `web/style.css`, cuối file:

```css
/* Live Streams Styles */
.streams-container {
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.streams-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}

.streams-header h2 {
    margin: 0;
    color: #2c3e50;
}

.streams-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
    gap: 20px;
}

.stream-card {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 15px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.stream-card h3 {
    margin: 0 0 10px 0;
    color: #2c3e50;
    font-size: 18px;
}

.stream-container {
    position: relative;
    width: 100%;
    padding-bottom: 56.25%; /* 16:9 aspect ratio */
    background: #000;
    border-radius: 4px;
    overflow: hidden;
}

.stream-container img {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: contain;
}

.stream-status {
    margin-top: 10px;
    font-size: 12px;
    color: #7f8c8d;
}

.stream-status.active {
    color: #27ae60;
}

.stream-status.inactive {
    color: #e74c3c;
}
```

### **Bước 4: Thêm JavaScript để load và hiển thị streams**

Thêm vào `web/script.js`, cuối file (sau dòng 713):

```javascript
// Live Streams functionality
function loadStreams() {
    // Load clients first
    fetch('/api/clients')
        .then(response => response.json())
        .then(clients => {
            displayStreams(clients);
        })
        .catch(error => {
            console.error('Error loading streams:', error);
        });
}

function displayStreams(clients) {
    const streamsGrid = document.getElementById('streams-grid');
    
    if (clients.length === 0) {
        streamsGrid.innerHTML = '<p style="text-align: center; color: #7f8c8d;">No clients found</p>';
        return;
    }
    
    streamsGrid.innerHTML = clients.map(client => {
        const streamUrl = `/api/video/stream/${client.id}`;
        return `
            <div class="stream-card">
                <h3>${client.name}</h3>
                <div class="stream-container">
                    <img src="${streamUrl}" 
                         alt="Live stream from ${client.name}"
                         onerror="this.style.display='none'; this.parentElement.innerHTML='<div style=\'color:#e74c3c;text-align:center;padding:20px;\'>Stream unavailable</div>'">
                </div>
                <div class="stream-status ${client.is_detect_enabled ? 'active' : 'inactive'}">
                    Status: ${client.is_detect_enabled ? 'Active' : 'Inactive'}
                </div>
            </div>
        `;
    }).join('');
}

// Add event listener for refresh streams button
document.addEventListener('DOMContentLoaded', function() {
    // Add this inside initializeApp() function or at the end
    const refreshStreamsBtn = document.getElementById('refresh-streams-btn');
    if (refreshStreamsBtn) {
        refreshStreamsBtn.addEventListener('click', loadStreams);
    }
});

// Update switchTab function to load streams when tab is opened
// Tìm function switchTab (dòng 68), sửa:
```

**Sửa hàm `switchTab` (tìm dòng 68-86):**

**TRƯỚC:**
```javascript
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.style.display = 'none';
    });
    document.getElementById(`${tabName}-tab`).style.display = 'block';

    // Update controls
    document.getElementById('detections-controls').style.display = tabName === 'detections' ? 'flex' : 'none';
    document.getElementById('clients-controls').style.display = tabName === 'clients' ? 'flex' : 'none';

    currentTab = tabName;
}
```

**SAU:**
```javascript
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.style.display = 'none';
    });
    document.getElementById(`${tabName}-tab`).style.display = 'block';

    // Update controls
    document.getElementById('detections-controls').style.display = tabName === 'detections' ? 'flex' : 'none';
    document.getElementById('clients-controls').style.display = tabName === 'clients' ? 'flex' : 'none';

    // Load streams when streams tab is opened
    if (tabName === 'streams') {
        loadStreams();
    }

    currentTab = tabName;
}
```

**Thêm vào hàm `initializeApp()` (sau dòng 34):**

```javascript
function initializeApp() {
    // Set up event listeners
    document.getElementById('refresh-btn').addEventListener('click', refreshData);
    document.getElementById('class-filter').addEventListener('change', handleFilterChange);
    document.getElementById('client-filter').addEventListener('change', handleClientFilterChange);
    document.getElementById('limit-select').addEventListener('change', handleLimitChange);
    document.getElementById('prev-page').addEventListener('click', () => changePage(-1));
    document.getElementById('next-page').addEventListener('click', () => changePage(1));

    // Client management event listeners
    document.getElementById('add-client-btn').addEventListener('click', () => openClientModal());
    document.getElementById('refresh-clients-btn').addEventListener('click', loadClients);
    
    // Stream refresh button
    const refreshStreamsBtn = document.getElementById('refresh-streams-btn');
    if (refreshStreamsBtn) {
        refreshStreamsBtn.addEventListener('click', loadStreams);
    }

    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => switchTab(e.target.dataset.tab));
    });

    // Load initial data
    loadStats();
    loadDetections();
    loadClients();
    // loadStreams(); // Không load ngay, chỉ load khi mở tab

    // Set up modals
    setupModal();
    setupClientModal();
}
```

---

## **TÓM TẮT THAY ĐỔI:**

### **Server (`out-quan-boxcamai-sv`):**
1. ✅ `server.py` - Thêm `video_frames` dict và lock
2. ✅ `server.py` - Thêm endpoint `/api/video/frame` (POST) để nhận frames
3. ✅ `server.py` - Thêm endpoint `/api/video/stream/<client_id>` (GET) để stream MJPEG
4. ✅ `templates/index.html` - Thêm tab "Live Streams"
5. ✅ `web/style.css` - Thêm CSS cho streams
6. ✅ `web/script.js` - Thêm functions `loadStreams()` và `displayStreams()`

### **Client (`out-quan-boxcamai-client`):**
1. ✅ Tạo file mới `stream_sender.py`
2. ✅ `main.py` - Import `stream_sender`
3. ✅ `main.py` - Gọi `send_video_frame()` ở 4 nơi (video file, RTSP, webcam, rpicam)
4. ✅ `main.py` - Khởi động và cleanup stream thread

---

## **CẤU HÌNH (TÙY CHỌN):**

### **Điều chỉnh FPS và chất lượng:**

**Trong `stream_sender.py`, dòng 70:**
```python
time.sleep(0.1)  # 10 FPS - có thể sửa thành 0.033 (30 FPS) hoặc 0.05 (20 FPS)
```

**Trong `stream_sender.py`, dòng 58:**
```python
ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
# 70 = chất lượng JPEG (0-100), có thể tăng lên 85-90 để rõ hơn
```

**Trong `stream_sender.py`, dòng 53:**
```python
resized_frame = cv2.resize(frame, (640, 480))  # Có thể sửa resolution
```

---

## **TEST:**

### **1. Test trên Server:**
```bash
# Kiểm tra endpoint nhận frame
curl -X POST http://localhost:5000/api/video/frame \
  -F "client_name=raspberry_pi_1" \
  -F "frame=@test_image.jpg"

# Kiểm tra MJPEG stream (thay client_id)
curl http://localhost:5000/api/video/stream/1
```

### **2. Test trên Pi:**
```bash
# Chạy client và kiểm tra log
python3 main.py --rtsp

# Phải thấy: "📹 Video stream sender thread started"
```

### **3. Test trên Web:**
1. Mở browser: `http://your-server:5000`
2. Click tab "Live Streams"
3. Phải thấy video stream từ Pi (nếu đã chạy)

---

## **GHI CHÚ:**

- **Bandwidth:** Mỗi frame ~50-100KB, 10 FPS = ~500KB-1MB/s. Có thể giảm FPS hoặc resolution nếu cần.
- **Latency:** ~100-300ms (tùy network)
- **Memory:** Server lưu 1 frame/client trong memory, rất nhẹ
- **Auto-refresh:** Stream tự động refresh khi mở tab, có thể thêm auto-refresh mỗi 5s nếu cần

---

**Tạo ngày:** $(date)
**Người tạo:** Auto AI Assistant

