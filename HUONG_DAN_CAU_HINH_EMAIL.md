# Hướng dẫn cấu hình Email cảnh báo

## 1. Tạo App Password cho Gmail

Để gửi email qua Gmail SMTP, bạn cần tạo **App Password** (không phải mật khẩu thường):

### Bước 1: Bật 2-Step Verification
1. Vào [Google Account Security](https://myaccount.google.com/security)
2. Bật **2-Step Verification** nếu chưa bật

### Bước 2: Tạo App Password
1. Vào [App Passwords](https://myaccount.google.com/apppasswords)
2. Chọn **Select app** → Chọn **Mail**
3. Chọn **Select device** → Chọn **Other (Custom name)** → Nhập tên (ví dụ: "AI Detection Server")
4. Click **Generate**
5. Copy **16 ký tự** password được tạo (ví dụ: `abcd efgh ijkl mnop`)

## 2. Cấu hình trên Server

### Cách 1: Sử dụng biến môi trường (Khuyến nghị)

Tạo file `.env` hoặc set biến môi trường:

```bash
export ALERT_EMAIL_SENDER="your-email@gmail.com"
export ALERT_EMAIL_PASSWORD="abcdefghijklmnop"  # App Password (16 ký tự, không có khoảng trắng)
```

Hoặc trên Windows PowerShell:
```powershell
$env:ALERT_EMAIL_SENDER="your-email@gmail.com"
$env:ALERT_EMAIL_PASSWORD="abcdefghijklmnop"
```

### Cách 2: Sửa trực tiếp trong `config.py`

Mở file `out-quan-boxcamai-sv/config.py` và sửa:

```python
ALERT_EMAIL_SENDER = 'your-email@gmail.com'  # Email gửi đi
ALERT_EMAIL_PASSWORD = 'abcdefghijklmnop'  # App Password (16 ký tự)
```

## 3. Cấu hình Email nhận cảnh báo trên Web

1. Mở web dashboard
2. Tìm phần **"📧 Email cảnh báo"** ở trên cùng
3. Nhập email muốn nhận cảnh báo (ví dụ: `recipient@gmail.com`)
4. Click **"💾 Lưu Email"**
5. Tick vào **"Bật cảnh báo email"**

## 4. Cách hoạt động

- ✅ **Chỉ gửi email khi:**
  - Client có ROI được cấu hình (roi_x1, roi_y1, roi_x2, roi_y2)
  - Có detection mới trong ROI
  - Email cảnh báo đã được bật

- ❌ **KHÔNG gửi email khi:**
  - Client không có ROI
  - Detection ngoài ROI
  - Email cảnh báo chưa được bật

## 5. Nội dung Email

Email sẽ bao gồm:
- 📧 **Tiêu đề:** "🔔 Cảnh báo: [Class Name] được phát hiện trong ROI - [Client Name]"
- 📋 **Thông tin:**
  - Đối tượng được phát hiện
  - Độ tin cậy (%)
  - Thời gian phát hiện
  - Client name
  - Vị trí bounding box
- 🖼️ **Hình ảnh:** Hình ảnh detection được đính kèm trực tiếp trong email

## 6. Test Email

1. Đảm bảo đã cấu hình:
   - ✅ SMTP credentials trong `config.py` hoặc biến môi trường
   - ✅ Email nhận cảnh báo trên web
   - ✅ Đã bật "Bật cảnh báo email"
   - ✅ Client có ROI được cấu hình

2. Kích hoạt detection trong ROI → Email sẽ được gửi tự động

## 7. Troubleshooting

### Lỗi: "SMTP Authentication failed"
- ❌ **Nguyên nhân:** App Password sai hoặc chưa bật 2-Step Verification
- ✅ **Giải pháp:** Tạo lại App Password và kiểm tra lại

### Lỗi: "Connection refused"
- ❌ **Nguyên nhân:** Firewall hoặc network block port 587
- ✅ **Giải pháp:** Cho phép port 587 (SMTP) trong firewall

### Không nhận được email
- Kiểm tra:
  1. ✅ Client có ROI không?
  2. ✅ Email cảnh báo đã được bật chưa?
  3. ✅ SMTP credentials đã đúng chưa?
  4. ✅ Check spam/junk folder
  5. ✅ Check server logs để xem có lỗi gì không

## 8. Lưu ý quan trọng

⚠️ **KHÔNG** dùng mật khẩu Gmail thường → Phải dùng **App Password**
⚠️ App Password chỉ hiển thị 1 lần → Lưu lại cẩn thận
⚠️ Email sẽ được gửi trong background thread → Không làm chậm server

