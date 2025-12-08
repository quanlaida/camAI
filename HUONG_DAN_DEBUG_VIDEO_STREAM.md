# 🔍 HƯỚNG DẪN DEBUG VIDEO STREAM KHÔNG NHẬN ĐƯỢC

Đã thêm debug logging và cải thiện error handling trong server code.

---

## ✅ **ĐÃ SỬA:**

### **1. Thêm Debug Logging (`server.py` dòng 311, 320, 327):**
- Log khi nhận frame từ client
- Log frame_type và client_id
- Log khi lưu frame vào memory

### **2. Cải thiện Error Handling:**
- Tách riêng lock cho processed và raw frames
- Thêm try-except trong stream generator
- Vẫn gửi frame dù cũ để tránh màn hình đen

---

## 🔍 **CÁCH DEBUG:**

### **1. Kiểm tra Server Log:**

```bash
# Xem log server khi nhận frame
tail -f server.log | grep "Received frame"
# Hoặc nếu chạy trực tiếp
python server.py
```

**Log cần thấy:**
```
Received frame from raspberry_pi_1, frame_type: processed, client_id: 1
Saved processed frame for client 1
```

### **2. Kiểm tra Client (Pi) Log:**

```bash
sudo journalctl -u boxcamai -f | grep "send.*frame"
```

**Log cần thấy:**
```
📹 Processed video stream sender thread started (AI detection)
```

### **3. Test API trực tiếp:**

```bash
# Test xem server có nhận được frame không
curl -X POST https://boxcamai.cloud:443/api/video/frame \
  -F "client_name=raspberry_pi_1" \
  -F "frame_type=processed" \
  -F "frame=@test.jpg"
```

### **4. Kiểm tra Stream Endpoint:**

```bash
# Mở browser và truy cập:
https://boxcamai.cloud:443/api/video/stream/processed/1
```

Nếu thấy stream → Server OK  
Nếu không thấy → Kiểm tra log server

---

## 🐛 **CÁC VẤN ĐỀ CÓ THỂ:**

### **1. Client không gửi frame:**
**Kiểm tra:**
- Pi có đang chạy service không?
- `send_processed_frame()` có được gọi không?
- Network có kết nối không?

### **2. Server không nhận được:**
**Kiểm tra log server:**
- Có thấy "Received frame" không?
- Có lỗi gì không?
- frame_type có đúng "processed" không?

### **3. Server nhận nhưng không lưu:**
**Kiểm tra:**
- `processed_video_frames[client.id]` có tồn tại không?
- Lock có bị deadlock không?

### **4. Stream endpoint không trả về:**
**Kiểm tra:**
- `client_id` có đúng không?
- Frame có trong `processed_video_frames` không?
- Timestamp có hợp lệ không?

---

## ✅ **SAU KHI SỬA:**

1. **Restart server:**
```bash
# Stop server hiện tại
# Start lại
python server.py
```

2. **Kiểm tra log:**
- Xem có log "Received frame" không
- Xem có log "Saved processed frame" không
- Xem có lỗi gì không

3. **Test trên browser:**
- Vào tab "Live Streams"
- Xem có stream không
- Kiểm tra console có lỗi không

---

**Tạo ngày:** 2024  
**Người tạo:** Auto AI Assistant

