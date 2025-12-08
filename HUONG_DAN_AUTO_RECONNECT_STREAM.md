# 🔄 HƯỚNG DẪN AUTO-RECONNECT STREAM

Đã thêm tính năng **auto-reconnect/retry** khi stream bị ngắt.

---

## ✅ **TÍNH NĂNG ĐÃ THÊM:**

### **1. Auto-Reconnect với Exponential Backoff**
- Tự động reconnect khi stream bị ngắt
- Exponential backoff: 1s → 2s → 4s → 8s → 16s → max 30s
- Reset retry count khi reconnect thành công

### **2. Stream Health Check**
- Check stream health mỗi 5 giây
- Detect khi không có frame mới trong 10 giây
- Tự động trigger reconnect nếu stream dead

### **3. Visual Status Indicator**
- Hiển thị overlay "Reconnecting... (attempt N)" khi đang reconnect
- Hiển thị "● Live" (màu xanh) khi stream hoạt động
- Hiển thị "⚠️ Offline" (màu đỏ) khi stream offline

### **4. Smart State Management**
- Track retry count cho mỗi client
- Lưu stream type (raw/processed) để reconnect đúng stream
- Clear timers khi switch stream type thủ công

---

## 📋 **CÁC FUNCTION MỚI:**

### **`handleStreamLoad(clientId)`**
- Được gọi khi frame load thành công
- Reset retry count
- Hide overlay
- Update last frame time

### **`handleStreamError(clientId)`**
- Được gọi khi stream error
- Trigger reconnect với backoff delay
- Show reconnecting overlay

### **`reconnectStream(clientId)`**
- Reconnect stream với exponential backoff
- Show status overlay với attempt number
- Retry với delay tăng dần

### **`setupStreamHealthCheck(clients)`**
- Check stream health mỗi 5 giây
- Detect dead stream (no frame > 10s)
- Auto-trigger reconnect
- Update health indicator

---

## 🎯 **HOẠT ĐỘNG:**

```
1. Stream đang chạy bình thường
   ↓
2. Stream bị ngắt (error/timeout)
   ↓
3. handleStreamError() được gọi
   ↓
4. Show overlay "Reconnecting... (attempt 1)"
   ↓
5. Đợi 1 giây (backoff delay)
   ↓
6. Reconnect: img.src = new URL
   ↓
7a. Success → handleStreamLoad() → Reset retry, hide overlay
7b. Failed → handleStreamError() → Retry với delay 2s
   ↓
8. Lặp lại với delay tăng: 4s, 8s, 16s, max 30s
```

---

## 🔍 **STREAM HEALTH CHECK:**

- **Interval:** Mỗi 5 giây
- **Timeout:** 10 giây không có frame mới → coi là dead
- **Action:** Tự động trigger reconnect nếu stream dead
- **Indicator:**
  - `● Live` (xanh) = Stream hoạt động bình thường
  - `⚠️ Offline` (đỏ) = Stream offline/dead

---

## 📊 **EXPONENTIAL BACKOFF:**

| Attempt | Delay | Next Retry At |
|---------|-------|---------------|
| 1 | 1s | Now + 1s |
| 2 | 2s | Now + 2s |
| 3 | 4s | Now + 4s |
| 4 | 8s | Now + 8s |
| 5 | 16s | Now + 16s |
| 6+ | 30s | Now + 30s (max) |

**Tổng thời gian max:** ~1 phút (nếu tất cả retry đều fail)

---

## 🎨 **VISUAL INDICATORS:**

### **Overlay (khi reconnecting):**
```
┌─────────────────────┐
│ Reconnecting...     │
│ (attempt 3)         │
└─────────────────────┘
```
- Màu: Đen với opacity 0.8
- Vị trí: Top-left của stream container
- Animation: Pulse (fade in/out)

### **Health Indicator:**
- `● Live` (màu xanh #27ae60) = OK
- `⚠️ Offline` (màu đỏ #e74c3c) = Offline

---

## ✅ **TESTING:**

1. **Test auto-reconnect:**
   - Stop service trên Pi → Stream sẽ ngắt
   - Xem có show overlay "Reconnecting..." không
   - Xem có tự reconnect không khi start lại service

2. **Test health check:**
   - Đợi 10 giây không có frame mới
   - Xem health indicator có chuyển sang "⚠️ Offline" không
   - Xem có tự trigger reconnect không

3. **Test manual switch:**
   - Switch giữa Raw và Processed
   - Xem có reset retry count không
   - Xem có reconnect đúng stream type không

---

## 🐛 **DEBUG:**

Mở Browser Console để xem log:
```javascript
// Log khi reconnect
console.log(`Reconnecting stream for client ${clientId}, attempt ${retryCount}`);

// Log khi health check fail
console.warn(`Stream health check failed for client ${clientId}, last frame: Xs ago`);
```

---

**Tạo ngày:** 2024  
**Người tạo:** Auto AI Assistant

