# 🛑 HƯỚNG DẪN TẮT SERVER TRÊN RASPBERRY PI

File này hướng dẫn cách kiểm tra và tắt các server đang chạy trên Pi.

---

## 🔍 **BƯỚC 1: KIỂM TRA SERVER ĐANG CHẠY**

### **Kiểm tra process Python đang chạy:**
```bash
# Xem tất cả process Python
ps aux | grep python

# Xem process server.py cụ thể
ps aux | grep server.py

# Xem process Flask
ps aux | grep flask
```

### **Kiểm tra port đang được sử dụng:**
```bash
# Kiểm tra port 5000
sudo lsof -i :5000

# Hoặc
sudo netstat -tulpn | grep 5000

# Kiểm tra port 443 (nếu dùng HTTPS)
sudo lsof -i :443
```

### **Kiểm tra service systemd (nếu chạy như service):**
```bash
# Xem status service boxcamai
sudo systemctl status boxcamai

# Xem tất cả service liên quan
sudo systemctl list-units | grep -i cam
sudo systemctl list-units | grep -i flask
sudo systemctl list-units | grep -i python
```

---

## 🛑 **BƯỚC 2: TẮT SERVER**

### **Cách 1: Tắt process đang chạy (nếu chạy trực tiếp)**

```bash
# Tìm PID của process
ps aux | grep server.py

# Ví dụ output:
# pi 1234 0.5 2.1 ... python3 server.py
# PID ở cột thứ 2 (1234)

# Tắt process bằng PID
kill 1234

# Nếu không tắt được, dùng kill -9 (force kill)
kill -9 1234
```

**Hoặc tắt tất cả process Python server:**
```bash
# Tắt tất cả process server.py
pkill -f server.py

# Tắt tất cả process Python (cẩn thận!)
pkill -f python
```

### **Cách 2: Tắt service systemd**

```bash
# Stop service
sudo systemctl stop boxcamai

# Disable service (không tự động chạy khi boot)
sudo systemctl disable boxcamai

# Kiểm tra đã tắt chưa
sudo systemctl status boxcamai
```

### **Cách 3: Tắt tất cả process trên port cụ thể**

```bash
# Tắt process đang dùng port 5000
sudo fuser -k 5000/tcp

# Hoặc
sudo kill $(sudo lsof -t -i:5000)
```

---

## ✅ **BƯỚC 3: XÁC NHẬN ĐÃ TẮT**

```bash
# Kiểm tra lại không còn process server.py
ps aux | grep server.py
# Phải không có output (hoặc chỉ có dòng grep chính nó)

# Kiểm tra port 5000 không còn được dùng
sudo lsof -i :5000
# Phải không có output

# Kiểm tra service đã stop
sudo systemctl status boxcamai
# Phải hiển thị "inactive (dead)"
```

---

## 🔄 **BƯỚC 4: CHẠY SERVER MỚI (nếu cần)**

Sau khi đã tắt server cũ, có thể chạy server mới:

```bash
cd /home/pi/out-quan-boxcamai-sv
source venv/bin/activate  # Nếu dùng venv
python3 server.py
```

---

## 📝 **QUICK COMMANDS (Copy-paste tất cả):**

```bash
# 1. Kiểm tra process đang chạy
echo "=== Processes ==="
ps aux | grep server.py
echo ""
echo "=== Port 5000 ==="
sudo lsof -i :5000
echo ""
echo "=== Services ==="
sudo systemctl status boxcamai

# 2. Tắt tất cả
echo "=== Stopping... ==="
sudo systemctl stop boxcamai 2>/dev/null
pkill -f server.py
sudo fuser -k 5000/tcp 2>/dev/null
sudo kill $(sudo lsof -t -i:5000) 2>/dev/null

# 3. Xác nhận
echo "=== Checking again ==="
ps aux | grep server.py | grep -v grep
sudo lsof -i :5000
```

---

## ⚠️ **LƯU Ý:**

1. **Kiểm tra kỹ trước khi kill** - Đảm bảo đó là server của bạn
2. **Nếu dùng service** - Dùng `systemctl stop` thay vì kill process
3. **Backup** - Nếu có data quan trọng, backup trước khi tắt

---

**Tạo ngày:** 2024  
**Người tạo:** Auto AI Assistant

