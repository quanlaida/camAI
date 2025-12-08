# 📋 HƯỚNG DẪN COPY FILE config.py LÊN PI

**Lỗi:** `AttributeError: module 'config' has no attribute 'ENABLE_AUTO_RESTART'`

**Nguyên nhân:** File `config.py` trên Pi thiếu 2 thuộc tính:
- `POLL_INTERVAL = 30`
- `ENABLE_AUTO_RESTART = True`

---

## ✅ **GIẢI PHÁP: COPY FILE config.py MỚI**

### **Cách 1: Copy từ máy tính sang Pi (khuyến nghị)**

```powershell
# Từ Windows PowerShell:
scp out-quan-boxcamai-client\config.py leviathan@raspberrypi:~/out-quan-boxcamai-client/config.py
```

### **Cách 2: SFTP/WinSCP/FileZilla**

Copy file `out-quan-boxcamai-client\config.py` → `~/out-quan-boxcamai-client/config.py` trên Pi

---

## 🔧 **CÁCH 2: SỬA TRỰC TIẾP TRÊN PI**

Nếu không copy được, sửa trực tiếp trên Pi:

```bash
cd ~/out-quan-boxcamai-client
nano config.py
```

**Cuộn xuống cuối file và thêm 2 dòng:**

```python
# Server polling configuration (kiểm tra thay đổi từ server)
POLL_INTERVAL = 30  # Kiểm tra mỗi 30 giây
ENABLE_AUTO_RESTART = True  # Tự động restart khi có thay đổi IP/ROI
```

**Lưu:** `Ctrl+O`, `Enter`, `Ctrl+X`

---

## ✅ **SAU KHI COPY/SỬA - VERIFY:**

```bash
# Trên Pi:
cd ~/out-quan-boxcamai-client

# Kiểm tra có 2 thuộc tính chưa
grep -q "POLL_INTERVAL" config.py && grep -q "ENABLE_AUTO_RESTART" config.py && echo "✅ OK" || echo "❌ Chưa có"

# Hoặc xem 2 dòng cuối
tail -2 config.py
```

**Phải thấy:**
```
POLL_INTERVAL = 30  # Kiểm tra mỗi 30 giây
ENABLE_AUTO_RESTART = True  # Tự động restart khi có thay đổi IP/ROI
```

---

## 🚀 **SAU ĐÓ RESTART SERVICE:**

```bash
sudo systemctl restart boxcamai
sudo journalctl -u boxcamai -f
```

---

## 📊 **LOG CẦN THẤY:**

```
Client info retrieved: {...}
🔄 Server polling thread started (checking every 30s)
   Initial IP: None, Initial ROI: (None, None, None, None)
⏳ Waiting 30s before first check...
[KHÔNG còn lỗi AttributeError]
```

---

**Tạo ngày:** 2024  
**Người tạo:** Auto AI Assistant

