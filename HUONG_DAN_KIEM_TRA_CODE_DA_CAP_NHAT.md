# 🔍 KIỂM TRA CODE ĐÃ ĐƯỢC CẬP NHẬT CHƯA

**Vấn đề:** Service vẫn restart liên tục → có thể code mới chưa được copy lên Pi hoặc còn process cũ đang chạy.

---

## 🔍 **BƯỚC 1: KIỂM TRA CODE TRÊN PI**

```bash
# Trên Pi, kiểm tra file main.py có code mới chưa
cd ~/out-quan-boxcamai-client

# Xem hàm server_polling_thread có đợi interval TRƯỚC KHI check không
grep -A 5 "Waiting.*before first check" main.py

# Hoặc xem toàn bộ hàm server_polling_thread
grep -A 50 "def server_polling_thread" main.py | head -60
```

**Code mới PHẢI có dòng:**
```python
⏳ Waiting {config.POLL_INTERVAL}s before first check...
stop_event.wait(config.POLL_INTERVAL)
```

**Nếu KHÔNG thấy** → Code chưa được copy lên Pi!

---

## 🛑 **BƯỚC 2: DỪNG TẤT CẢ PROCESS CŨ**

```bash
# Chạy script kill tất cả process
chmod +x KILL_ALL_CLIENT_PROCESSES.sh
./KILL_ALL_CLIENT_PROCESSES.sh

# Hoặc thủ công:
sudo systemctl stop boxcamai
sudo systemctl disable boxcamai
sudo systemctl reset-failed boxcamai
pkill -f "python.*main.py"
sleep 2
```

---

## 📋 **BƯỚC 3: SAO CHÉP CODE MỚI**

### **Cách 1: Copy từ máy tính sang Pi (khuyến nghị)**

```bash
# Trên máy tính (Windows):
# Copy file main.py lên Pi qua SCP, SFTP, hoặc USB

# Trên Pi, kiểm tra file đã được copy:
cd ~/out-quan-boxcamai-client
cat main.py | grep -A 3 "Waiting.*before first check"
```

### **Cách 2: Sửa trực tiếp trên Pi**

```bash
# Trên Pi
cd ~/out-quan-boxcamai-client
nano main.py
```

**Tìm hàm `server_polling_thread` và sửa:**

```python
def server_polling_thread(stop_event, initial_ip, initial_roi):
    ...
    print(f"🔄 Server polling thread started (checking every {config.POLL_INTERVAL}s)")
    print(f"   Initial IP: {initial_ip}, Initial ROI: {initial_roi}")
    
    # THÊM ĐOẠN NÀY:
    # QUAN TRỌNG: Đợi interval TRƯỚC KHI check lần đầu tiên
    print(f"⏳ Waiting {config.POLL_INTERVAL}s before first check...")
    stop_event.wait(config.POLL_INTERVAL)
    
    if stop_event.is_set():
        print("🛑 Server polling thread stopped (before first check)")
        return
    
    # Sau đó mới vào vòng lặp while
    while not stop_event.is_set():
        ...
```

---

## ✅ **BƯỚC 4: VERIFY CODE ĐÃ ĐÚNG**

```bash
# Kiểm tra code có đúng chưa
cd ~/out-quan-boxcamai-client
python3 -c "
import ast
import sys
with open('main.py', 'r') as f:
    code = f.read()
    if 'Waiting.*before first check' in code or 'stop_event.wait(config.POLL_INTERVAL)' in code.split('def server_polling_thread')[1].split('while')[0]:
        print('✅ Code mới đã có!')
    else:
        print('❌ Code cũ, chưa có sửa đổi!')
        sys.exit(1)
"

# Hoặc kiểm tra đơn giản:
grep -q "Waiting.*before first check" main.py && echo "✅ OK" || echo "❌ Chưa có"
```

---

## 🚀 **BƯỚC 5: START SERVICE MỚI**

```bash
# Đảm bảo đã dừng hết process cũ
./KILL_ALL_CLIENT_PROCESSES.sh

# Reload systemd
sudo systemctl daemon-reload
sudo systemctl reset-failed boxcamai

# Start service
sudo systemctl start boxcamai

# Xem log
sudo journalctl -u boxcamai -f
```

---

## 📊 **LOG CẦN THẤY:**

### **Code MỚI (đúng):**
```
Client info retrieved: {...}
🔄 Server polling thread started (checking every 30s)
   Initial IP: None, Initial ROI: (None, None, None, None)
⏳ Waiting 30s before first check...
[KHÔNG restart ngay]
```

### **Code CŨ (sai):**
```
Client info retrieved: {...}
🔄 Server polling thread started (checking every 30s)
🔍 Polling server... (check #1)
[Restart ngay lập tức]
```

---

## ⚠️ **LƯU Ý:**

- **Code mới PHẢI có** dòng `⏳ Waiting {config.POLL_INTERVAL}s before first check...`
- Nếu không thấy dòng này trong log → Code chưa được cập nhật!
- Đảm bảo đã kill hết process cũ trước khi start service mới

---

**Tạo ngày:** 2024  
**Người tạo:** Auto AI Assistant

