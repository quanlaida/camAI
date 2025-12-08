# 📋 HƯỚNG DẪN COPY FILE main.py LÊN PI

File `main.py` trên máy tính đã được sửa đúng. Bạn chỉ cần copy lên Pi.

---

## ✅ **FILE ĐÃ SỬA ĐÚNG:**

File: `out-quan-boxcamai-client/main.py`
- ✅ Đã có đoạn code đợi interval trước khi check (dòng 202-209)
- ✅ Logic so sánh IP/ROI đã được cải thiện
- ✅ Thêm debug log chi tiết

---

## 📋 **CÁC CÁCH COPY:**

### **Cách 1: SCP (khuyến nghị - từ máy tính Windows)**

```powershell
# Trên Windows PowerShell
scp out-quan-boxcamai-client\main.py leviathan@raspberrypi:~/out-quan-boxcamai-client/main.py
```

### **Cách 2: SFTP (WinSCP, FileZilla)**

1. Kết nối SFTP đến Pi
2. Copy file `out-quan-boxcamai-client\main.py` 
3. Paste vào `~/out-quan-boxcamai-client/` trên Pi
4. Overwrite file cũ

### **Cách 3: USB / Thẻ nhớ**

1. Copy file `main.py` vào USB/thẻ nhớ
2. Cắm vào Pi
3. Copy từ USB sang:
```bash
cp /media/usb/main.py ~/out-quan-boxcamai-client/main.py
```

### **Cách 4: Sửa trực tiếp trên Pi (nếu không copy được)**

Mở file trên Pi và sửa như hướng dẫn trong `HUONG_DAN_KIEM_TRA_CODE_DA_CAP_NHAT.md`

---

## ✅ **SAU KHI COPY - VERIFY VÀ START:**

```bash
# Trên Pi:

# 1. Verify file đã được copy đúng
cd ~/out-quan-boxcamai-client
grep -q "Waiting.*before first check" main.py && echo "✅ Code mới đã có!" || echo "❌ Chưa có!"

# 2. Dừng tất cả process cũ
chmod +x KILL_ALL_CLIENT_PROCESSES.sh
./KILL_ALL_CLIENT_PROCESSES.sh

# 3. Backup file cũ (tùy chọn)
cp main.py main.py.backup.$(date +%Y%m%d_%H%M%S)

# 4. Reload và start service
sudo systemctl daemon-reload
sudo systemctl reset-failed boxcamai
sudo systemctl start boxcamai

# 5. Xem log
sudo journalctl -u boxcamai -f
```

---

## 📊 **LOG CẦN THẤY (Code mới):**

```
Client info retrieved: {...}
🔄 Server polling thread started (checking every 30s)
   Initial IP: None, Initial ROI: (None, None, None, None)
⏳ Waiting 30s before first check...
[KHÔNG restart ngay - sẽ đợi 30 giây]
🔍 Polling server... (check #1)
✅ No changes - IP: None, ROI: (None, None, None, None)
```

**Nếu thấy "⏳ Waiting 30s before first check..." → Code đã được cập nhật đúng!**

---

## ⚠️ **LƯU Ý:**

- Backup file cũ trước khi copy file mới
- Đảm bảo dừng service và kill hết process cũ
- Kiểm tra log sau khi start để xác nhận code mới đã chạy

---

**Tạo ngày:** 2024  
**Người tạo:** Auto AI Assistant

