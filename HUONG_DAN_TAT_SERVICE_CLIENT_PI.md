# 🛑 HƯỚNG DẪN TẮT SERVICE CLIENT ĐANG TỰ ĐỘNG CHẠY TRÊN PI

Nếu client đã được cài như service tự động chạy khi boot, cần tắt service trước khi chạy thủ công.

---

## 🔍 **BƯỚC 1: KIỂM TRA SERVICE ĐANG CHẠY**

```bash
# Kiểm tra service boxcamai
sudo systemctl status boxcamai

# Hoặc tìm tất cả service liên quan
sudo systemctl list-units | grep -i cam
sudo systemctl list-units | grep -i box

# Kiểm tra process đang chạy
ps aux | grep main.py
ps aux | grep detection
```

---

## 🛑 **BƯỚC 2: TẮT SERVICE**

```bash
# Stop service
sudo systemctl stop boxcamai

# Disable service (không tự động chạy khi boot)
sudo systemctl disable boxcamai

# Kiểm tra đã tắt chưa
sudo systemctl status boxcamai
# Phải hiển thị: "inactive (dead)"
```

---

## 🔍 **BƯỚC 3: KIỂM TRA PROCESS CÒN CHẠY KHÔNG**

```bash
# Kiểm tra process main.py còn chạy không
ps aux | grep main.py | grep -v grep

# Nếu còn, kill thủ công
pkill -f main.py

# Kiểm tra process detection
ps aux | grep detection | grep -v grep
pkill -f detection
```

---

## ✅ **BƯỚC 4: XÁC NHẬN ĐÃ TẮT HOÀN TOÀN**

```bash
# Kiểm tra lại
echo "=== Service Status ==="
sudo systemctl status boxcamai | head -5

echo ""
echo "=== Processes ==="
ps aux | grep main.py | grep -v grep
ps aux | grep detection | grep -v grep

# Nếu không có output = đã tắt hết ✅
```

---

## 🚀 **BƯỚC 5: CHẠY THỦ CÔNG**

Sau khi đã tắt service, chạy thủ công:

```bash
cd /home/leviathan/out-quan-boxcamai-client

# Activate venv (nếu dùng)
source venv/bin/activate

# Chạy client
python3 main.py --rtsp
```

---

## 📝 **QUICK SCRIPT (Copy-paste tất cả):**

```bash
#!/bin/bash
echo "🛑 Tắt service và process client..."

# Stop service
sudo systemctl stop boxcamai 2>/dev/null && echo "✅ Stopped boxcamai service"
sudo systemctl disable boxcamai 2>/dev/null && echo "✅ Disabled boxcamai service"

# Kill processes
pkill -f main.py && echo "✅ Killed main.py processes"
pkill -f detection && echo "✅ Killed detection processes"

# Kiểm tra lại
echo ""
echo "=== Kiểm tra ==="
if sudo systemctl is-active --quiet boxcamai; then
    echo "⚠️  Service vẫn đang active!"
else
    echo "✅ Service đã tắt"
fi

if ps aux | grep main.py | grep -v grep > /dev/null; then
    echo "⚠️  Process main.py vẫn đang chạy!"
else
    echo "✅ Không còn process main.py"
fi

echo ""
echo "✅ Hoàn thành! Bây giờ có thể chạy: python3 main.py --rtsp"
```

---

## ⚠️ **LƯU Ý:**

1. **Tắt service trước khi chạy thủ công** - Tránh conflict
2. **Nếu muốn chạy service sau** - Enable lại: `sudo systemctl enable boxcamai`
3. **Update service file** - Nếu muốn service chạy code mới, cần update service file

---

## 🔄 **NẾU MUỐN CHẠY SERVICE VỚI CODE MỚI:**

Sau khi update code, restart service:

```bash
# Restart service để chạy code mới
sudo systemctl restart boxcamai

# Xem log
sudo journalctl -u boxcamai -f
```

---

**Tạo ngày:** 2024  
**Người tạo:** Auto AI Assistant

