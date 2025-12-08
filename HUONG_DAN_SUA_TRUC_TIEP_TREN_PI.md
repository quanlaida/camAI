# 🔧 HƯỚNG DẪN SỬA TRỰC TIẾP TRÊN PI

Code mới chưa có trên Pi (`❌ Chưa có`). Có 2 cách để thêm code:

---

## 🎯 **CÁCH 1: DÙNG SCRIPT TỰ ĐỘNG (KHuyến nghị)**

```bash
# Copy file PATCH_MAIN_PY_ON_PI.sh lên Pi
# Sau đó chạy:
chmod +x PATCH_MAIN_PY_ON_PI.sh
./PATCH_MAIN_PY_ON_PI.sh
```

Script sẽ tự động:
- Backup file cũ
- Tìm hàm `server_polling_thread`
- Thêm đoạn code đợi interval
- Verify patch thành công

---

## 🎯 **CÁCH 2: SỬA THỦ CÔNG BẰNG NANO**

### **Bước 1: Mở file**
```bash
cd ~/out-quan-boxcamai-client
nano main.py
```

### **Bước 2: Tìm hàm `server_polling_thread`**
Nhấn `Ctrl+W` (tìm kiếm), gõ: `def server_polling_thread`

### **Bước 3: Tìm dòng cuối cùng trước vòng lặp `while`**
Tìm dòng có nội dung:
```python
    print(f"   Initial IP: {current_ip}, Initial ROI: {current_roi}")
```

### **Bước 4: Thêm đoạn code sau dòng đó**
Sau dòng `print(f"   Initial IP: {current_ip}, Initial ROI: {current_roi}")`, thêm:

```python
    # QUAN TRỌNG: Đợi interval TRƯỚC KHI check lần đầu tiên
    # Để tránh restart ngay sau khi service start
    print(f"⏳ Waiting {config.POLL_INTERVAL}s before first check...")
    stop_event.wait(config.POLL_INTERVAL)
    
    if stop_event.is_set():
        print("🛑 Server polling thread stopped (before first check)")
        return
    
```

**Lưu ý:** Đoạn code này phải nằm **TRƯỚC** dòng `while not stop_event.is_set():`

### **Bước 5: Lưu và thoát**
- Nhấn `Ctrl+O` (lưu)
- Nhấn `Enter` (xác nhận)
- Nhấn `Ctrl+X` (thoát)

### **Bước 6: Verify**
```bash
grep -A 3 "Waiting.*before first check" main.py
```

Nếu thấy output → ✅ Đã sửa thành công!

---

## 📋 **VÍ DỤ CODE ĐÚNG:**

Sau khi sửa, hàm `server_polling_thread` sẽ trông như này:

```python
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
    print(f"   Initial IP: {current_ip}, Initial ROI: {current_roi}")
    
    # THÊM ĐOẠN NÀY ↓↓↓
    # QUAN TRỌNG: Đợi interval TRƯỚC KHI check lần đầu tiên
    # Để tránh restart ngay sau khi service start
    print(f"⏳ Waiting {config.POLL_INTERVAL}s before first check...")
    stop_event.wait(config.POLL_INTERVAL)
    
    if stop_event.is_set():
        print("🛑 Server polling thread stopped (before first check)")
        return
    # KẾT THÚC ĐOẠN THÊM ↑↑↑
    
    while not stop_event.is_set():  # ← Vòng lặp while ở đây
        try:
            poll_count += 1
            print(f"🔍 Polling server... (check #{poll_count})")
            # ... phần còn lại
```

---

## ✅ **SAU KHI SỬA:**

```bash
# 1. Verify code đã đúng
grep -q "Waiting.*before first check" main.py && echo "✅ OK" || echo "❌ Chưa có"

# 2. Dừng process cũ
./KILL_ALL_CLIENT_PROCESSES.sh

# 3. Reload và start
sudo systemctl daemon-reload
sudo systemctl reset-failed boxcamai
sudo systemctl start boxcamai

# 4. Xem log
sudo journalctl -u boxcamai -f
```

---

## 📊 **LOG CẦN THẤY:**

```
Client info retrieved: {...}
🔄 Server polling thread started (checking every 30s)
   Initial IP: None, Initial ROI: (None, None, None, None)
⏳ Waiting 30s before first check...  ← Phải thấy dòng này!
[KHÔNG restart ngay]
```

---

**Tạo ngày:** 2024  
**Người tạo:** Auto AI Assistant

