# HƯỚNG DẪN CÀI ĐẶT TỰ ĐỘNG CHẠY SERVER KHI BẬT MÁY

## CÁCH 1: DÙNG TASK SCHEDULER (KHUYẾN NGHỊ)

### Bước 1: Tạo file batch script

Tạo file `start_server.bat` trong thư mục server:

```batch
@echo off
cd /d E:\CAM_AI_server\camAI\out-quan-boxcamai-sv
call venv\Scripts\activate.bat
python server.py
```

**Lưu ý:** Thay đường dẫn `E:\CAM_AI_server\camAI\out-quan-boxcamai-sv` bằng đường dẫn thực tế của bạn.

### Bước 2: Tạo Task trong Task Scheduler

1. Mở **Task Scheduler**:
   - Nhấn `Win + R`
   - Gõ: `taskschd.msc`
   - Nhấn Enter

2. Tạo Task mới:
   - Click **Create Basic Task...** (bên phải)
   - **Name:** `CamAI Server Auto Start`
   - **Description:** `Tự động chạy CamAI Server khi đăng nhập`
   - Click **Next**

3. Trigger (Kích hoạt):
   - Chọn **When I log on** (Khi đăng nhập)
   - Click **Next**

4. Action (Hành động):
   - Chọn **Start a program**
   - Click **Next**
   - **Program/script:** Chọn file `start_server.bat` đã tạo
   - **Start in:** `E:\CAM_AI_server\camAI\out-quan-boxcamai-sv`
   - Click **Next**

5. Finish:
   - Tick vào **Open the Properties dialog for this task when I click Finish**
   - Click **Finish**

6. Cấu hình nâng cao:
   - Tab **General:**
     - Tick **Run whether user is logged on or not** (nếu muốn chạy ngay cả khi chưa đăng nhập)
     - Tick **Run with highest privileges**
   - Tab **Conditions:**
     - Bỏ tick **Start the task only if the computer is on AC power** (nếu muốn chạy cả khi dùng pin)
   - Tab **Settings:**
     - Tick **Allow task to be run on demand**
     - Tick **Run task as soon as possible after a scheduled start is missed**
     - **If the task fails, restart every:** `1 minute`
     - **Attempt to restart up to:** `3 times`
   - Click **OK**

### Bước 3: Test Task

1. Right-click vào task vừa tạo
2. Chọn **Run**
3. Kiểm tra xem server có chạy không

---

## CÁCH 2: DÙNG STARTUP FOLDER (ĐƠN GIẢN NHẤT)

### Bước 1: Tạo file batch script

Tạo file `start_server.bat` trong thư mục server (giống Cách 1).

### Bước 2: Tạo shortcut

1. Right-click vào file `start_server.bat`
2. Chọn **Create shortcut**
3. Đổi tên shortcut thành: `CamAI Server`

### Bước 3: Copy vào Startup folder

1. Nhấn `Win + R`
2. Gõ: `shell:startup`
3. Nhấn Enter
4. Copy shortcut `CamAI Server` vào thư mục này

**Lưu ý:** Cách này chỉ chạy khi user đăng nhập, không chạy khi chưa đăng nhập.

---

## CÁCH 3: DÙNG WINDOWS SERVICE (NÂNG CAO)

### Yêu cầu:
- Cài `NSSM` (Non-Sucking Service Manager): https://nssm.cc/download

### Bước 1: Tải và giải nén NSSM

1. Tải NSSM từ: https://nssm.cc/download
2. Giải nén vào: `C:\nssm`

### Bước 2: Tạo file Python wrapper

Tạo file `server_wrapper.py` trong thư mục server:

```python
import sys
import os

# Thay đổi thư mục làm việc
os.chdir(r'E:\CAM_AI_server\camAI\out-quan-boxcamai-sv')

# Thêm thư mục vào Python path
sys.path.insert(0, r'E:\CAM_AI_server\camAI\out-quan-boxcamai-sv')

# Import và chạy server
from server import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
```

### Bước 3: Cài đặt Service

Mở PowerShell/CMD với quyền Administrator:

```powershell
cd C:\nssm\win64
.\nssm install CamAIServer
```

Trong cửa sổ NSSM:
- **Path:** `C:\Python\python.exe` (hoặc đường dẫn Python của bạn)
- **Startup directory:** `E:\CAM_AI_server\camAI\out-quan-boxcamai-sv`
- **Arguments:** `server_wrapper.py`

Tab **Details:**
- **Display name:** `CamAI Server`
- **Description:** `CamAI Detection Server`

Tab **Log on:**
- Chọn account để chạy service

Click **Install service**

### Bước 4: Start Service

```powershell
net start CamAIServer
```

Hoặc:
- Mở **Services** (`services.msc`)
- Tìm **CamAI Server**
- Right-click → **Start**

---

## CÁCH 4: DÙNG SYSTEMD (LINUX)

Nếu bạn dùng Linux, tạo file service:

### Tạo file service

```bash
sudo nano /etc/systemd/system/camai-server.service
```

Nội dung:

```ini
[Unit]
Description=CamAI Server
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/out-quan-boxcamai-sv
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Kích hoạt service

```bash
sudo systemctl daemon-reload
sudo systemctl enable camai-server
sudo systemctl start camai-server
sudo systemctl status camai-server
```

---

## KIỂM TRA TỰ ĐỘNG CHẠY

### Windows:
1. Restart máy
2. Kiểm tra:
   - Task Manager → Processes → Tìm `python.exe`
   - Hoặc mở trình duyệt: `http://localhost:5000`

### Linux:
```bash
sudo systemctl status camai-server
```

---

## XỬ LÝ LỖI

### Server không tự động chạy:

1. **Kiểm tra Task Scheduler:**
   - Mở Task Scheduler
   - Xem **Task Scheduler Library**
   - Tìm task → Xem **Last Run Result**

2. **Kiểm tra Logs:**
   - Task Scheduler → Task → **History** tab
   - Xem lỗi chi tiết

3. **Kiểm tra quyền:**
   - Đảm bảo user có quyền chạy Python
   - Đảm bảo đường dẫn đúng

4. **Test thủ công:**
   - Chạy file `start_server.bat` thủ công
   - Xem có lỗi gì không

---

## TẮT TỰ ĐỘNG CHẠY

### Windows Task Scheduler:
- Mở Task Scheduler
- Tìm task → Right-click → **Disable**

### Startup Folder:
- Xóa shortcut khỏi Startup folder

### Windows Service:
```powershell
net stop CamAIServer
sc config CamAIServer start= disabled
```

### Linux:
```bash
sudo systemctl disable camai-server
sudo systemctl stop camai-server
```

---

## LƯU Ý QUAN TRỌNG

1. **Đường dẫn:** Đảm bảo tất cả đường dẫn trong script đúng với máy của bạn
2. **Virtual Environment:** Phải activate venv trước khi chạy server
3. **Port:** Đảm bảo port 5000 không bị chặn bởi firewall
4. **Database:** Đảm bảo file `detections.db` có quyền đọc/ghi
5. **Cloudflare Tunnel:** Nếu dùng tunnel, cũng cần cài tự động chạy (xem hướng dẫn Cloudflare)

---

## KHUYẾN NGHỊ

- **Windows:** Dùng **Cách 1 (Task Scheduler)** - ổn định và linh hoạt nhất
- **Linux:** Dùng **Cách 4 (Systemd)** - chuẩn cho Linux
- **Đơn giản:** Dùng **Cách 2 (Startup Folder)** nếu chỉ cần chạy khi đăng nhập

