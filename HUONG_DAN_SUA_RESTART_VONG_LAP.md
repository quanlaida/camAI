# 🔧 SỬA LỖI RESTART VÒNG LẶP VÔ HẠN

**Vấn đề:** Service restart liên tục ngay sau khi start, tạo vòng lặp vô hạn.

**Nguyên nhân:** Polling thread check server ngay lập tức và phát hiện "thay đổi" (do logic so sánh `None` không đúng hoặc check quá sớm).

---

## ✅ **ĐÃ SỬA:**

### **1. Sửa logic so sánh trong `check_server_updates()`:**
- Normalize `None` thành empty string khi so sánh IP
- Cải thiện so sánh ROI với None-safe logic
- Thêm debug log để theo dõi

### **2. Sửa `server_polling_thread()`:**
- **QUAN TRỌNG:** Đợi `POLL_INTERVAL` (30s) **TRƯỚC KHI** check lần đầu tiên
- Thêm log chi tiết hơn
- Thêm delay trước khi restart để log kịp ghi
- Cải thiện error handling

---

## 📋 **CÁC THAY ĐỔI TRONG CODE:**

### **File: `main.py`**

#### **1. Hàm `check_server_updates()`:**
- So sánh IP: normalize `None` → `""` để so sánh chính xác
- Thêm debug log khi phát hiện thay đổi

#### **2. Hàm `server_polling_thread()`:**
- Đợi interval **TRƯỚC** lần check đầu tiên (tránh restart ngay)
- Thêm log initial values
- Cải thiện error handling với traceback

---

## 🚀 **CÁCH CẬP NHẬT:**

### **Trên Pi:**

```bash
# 1. Dừng service
sudo systemctl stop boxcamai

# 2. Backup code cũ (nếu cần)
cd ~/out-quan-boxcamai-client
cp main.py main.py.backup

# 3. Copy file main.py mới từ máy tính sang Pi
# (hoặc sửa trực tiếp trên Pi)

# 4. Restart service
sudo systemctl daemon-reload
sudo systemctl reset-failed boxcamai
sudo systemctl start boxcamai

# 5. Xem log
sudo journalctl -u boxcamai -f
```

---

## ✅ **LOG CẦN THẤY SAU KHI SỬA:**

```
🔄 Server polling thread started (checking every 30s)
   Initial IP: None, Initial ROI: (None, None, None, None)
⏳ Waiting 30s before first check...
🔍 Polling server... (check #1)
✅ No changes - IP: None, ROI: (None, None, None, None)
...
```

**KHÔNG còn restart ngay sau khi start!**

---

## 🔍 **KIỂM TRA:**

```bash
# Xem log
sudo journalctl -u boxcamai -f

# Kiểm tra service không còn restart liên tục
sudo systemctl status boxcamai
```

---

## ⚠️ **LƯU Ý:**

- Polling thread sẽ đợi 30 giây trước khi check lần đầu
- Nếu cần test nhanh, có thể tạm thời giảm `POLL_INTERVAL` trong `config.py`
- Service sẽ chỉ restart khi **thực sự có thay đổi** IP hoặc ROI

---

**Tạo ngày:** 2024  
**Người tạo:** Auto AI Assistant

