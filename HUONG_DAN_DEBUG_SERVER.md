# 🔍 HƯỚNG DẪN DEBUG LỖI KẾT NỐI SERVER

## ❌ **LỖI GẶP PHẢI:**

```
Failed to get client info: HTTP 502
Trying to create new client
Failed to create new client: Expecting value: line 1 column 1 (char 0)
```

**Nguyên nhân:** Server không khả dụng hoặc không thể kết nối được.

---

## 🔧 **CÁCH KIỂM TRA VÀ SỬA:**

### **BƯỚC 1: Kiểm tra Server có đang chạy không**

Trên máy server, kiểm tra:
```bash
# Kiểm tra process Python
ps aux | grep server.py

# Hoặc kiểm tra port
netstat -tulpn | grep 5000
# hoặc
sudo lsof -i :5000
```

### **BƯỚC 2: Kiểm tra kết nối từ Pi đến Server**

Trên Pi, chạy:

```bash
# Test ping
ping boxcamai.cloud
# hoặc ping IP server của bạn

# Test HTTP connection
curl -v https://boxcamai.cloud:443/api/clients
# hoặc
curl -v http://<SERVER_IP>:5000/api/clients

# Test với Python
python3 -c "
import requests
try:
    r = requests.get('https://boxcamai.cloud:443/api/clients', timeout=5)
    print(f'Status: {r.status_code}')
    print(f'Response: {r.text[:200]}')
except Exception as e:
    print(f'Error: {e}')
"
```

### **BƯỚC 3: Kiểm tra config trên Pi**

```bash
cd /home/leviathan/out-quan-boxcamai-client
cat config.py | grep SERVER
```

**Đảm bảo:**
- `SERVER_HOST` đúng địa chỉ server
- `SERVER_PORT` đúng port (443 hoặc 5000)
- `CLIENT_NAME` đã được set

### **BƯỚC 4: Sửa config nếu cần**

Nếu server chạy trên `localhost` hoặc IP cục bộ:

```bash
nano config.py
```

**Sửa:**
```python
SERVER_HOST = '192.168.1.100'  # IP server của bạn
SERVER_PORT = 5000             # Hoặc 443 nếu dùng HTTPS
```

### **BƯỚC 5: Chạy với --not-sent (bỏ qua server)**

Nếu server chưa sẵn sàng, có thể chạy tạm thời không gửi lên server:

```bash
python3 main.py --rtsp --not-sent
```

### **BƯỚC 6: Kiểm tra SSL Certificate**

Nếu dùng HTTPS và gặp lỗi SSL:

```bash
# Test với verify=False (chỉ để test)
python3 -c "
import requests
r = requests.get('https://boxcamai.cloud:443/api/clients', verify=False, timeout=5)
print(r.status_code)
"
```

Nếu cần, sửa code để tạm thời bỏ qua SSL verification (chỉ để test).

---

## 🔍 **CÁC NGUYÊN NHÂN PHỔ BIẾN:**

### **1. Server chưa chạy**
- ✅ **Giải pháp:** Start server trước

### **2. Firewall chặn**
- ✅ **Giải pháp:** Mở port 5000 hoặc 443 trên server

### **3. Địa chỉ server sai**
- ✅ **Giải pháp:** Kiểm tra và sửa `SERVER_HOST` trong config.py

### **4. SSL Certificate issue**
- ✅ **Giải pháp:** Dùng HTTP thay vì HTTPS (port 5000) hoặc cài certificate đúng

### **5. Network không kết nối được**
- ✅ **Giải pháp:** Kiểm tra network, VPN, firewall

---

## 🚀 **QUICK FIX:**

### **Option 1: Chạy không cần server (tạm thời)**
```bash
python3 main.py --rtsp --not-sent
```

### **Option 2: Sửa config để dùng HTTP thay vì HTTPS**
```bash
nano config.py
# Sửa:
SERVER_HOST = '192.168.1.100'  # IP server cục bộ
SERVER_PORT = 5000             # HTTP port
```

Và sửa trong `main.py` và `sender.py`:
- Đổi `https://` thành `http://` trong các URL

---

## 📝 **TEST KẾT NỐI SERVER:**

Tạo file test: `test_server.py`

```python
import requests
import config

try:
    url = f'https://{config.SERVER_HOST}:{config.SERVER_PORT}/api/clients'
    print(f"Testing: {url}")
    response = requests.get(url, timeout=10)
    print(f"✅ Status: {response.status_code}")
    print(f"✅ Response: {response.text[:200]}")
except requests.exceptions.SSLError as e:
    print(f"❌ SSL Error: {e}")
    print("💡 Try using HTTP instead of HTTPS")
except requests.exceptions.ConnectionError as e:
    print(f"❌ Connection Error: {e}")
    print("💡 Check if server is running and accessible")
except Exception as e:
    print(f"❌ Error: {e}")
```

Chạy:
```bash
python3 test_server.py
```

---

**Tạo ngày:** 2024  
**Người tạo:** Auto AI Assistant

