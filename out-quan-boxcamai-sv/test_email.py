"""
Script test gửi email cảnh báo
Chạy: python test_email.py
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import config

def test_send_email():
    """Test gửi email cảnh báo"""
    try:
        # Cấu hình SMTP Gmail
        smtp_server = 'smtp.gmail.com'
        smtp_port = 587
        smtp_user = config.ALERT_EMAIL_SENDER
        smtp_password = config.ALERT_EMAIL_PASSWORD
        
        if not smtp_user or not smtp_password:
            print("❌ Chưa cấu hình ALERT_EMAIL_SENDER hoặc ALERT_EMAIL_PASSWORD")
            print("📝 Hãy tạo file .env với:")
            print("   ALERT_EMAIL_SENDER=your-email@gmail.com")
            print("   ALERT_EMAIL_PASSWORD=your-app-password")
            print("\n📖 Xem hướng dẫn: HUONG_DAN_SETUP_GMAIL.md")
            return
        
        print(f"📧 Đang gửi test email từ: {smtp_user}")
        print(f"📧 Đến: {smtp_user} (gửi cho chính mình để test)")
        
        # Tạo email
        msg = MIMEMultipart('related')
        msg['From'] = smtp_user
        msg['To'] = smtp_user  # Gửi cho chính mình để test
        msg['Subject'] = '🧪 Test Email Alert - camAI'
        
        # Nội dung email
        from datetime import datetime
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #4CAF50; color: white; padding: 15px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background: #f9f9f9; padding: 20px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 5px 5px; }}
                .success {{ color: #4CAF50; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🧪 Test Email Alert</h2>
                </div>
                <div class="content">
                    <p class="success">✅ Nếu bạn nhận được email này, nghĩa là cấu hình Gmail đã thành công!</p>
                    <hr>
                    <p><strong>📧 Email gửi đi:</strong> {smtp_user}</p>
                    <p><strong>📧 Email nhận:</strong> {smtp_user}</p>
                    <p><strong>🕐 Thời gian:</strong> {current_time}</p>
                    <hr>
                    <p><em>Email này được gửi từ hệ thống camAI để test cấu hình email cảnh báo.</em></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Gửi email
        print("🔄 Đang kết nối đến SMTP server...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        print("🔄 Đang đăng nhập...")
        server.login(smtp_user, smtp_password)
        print("🔄 Đang gửi email...")
        server.send_message(msg)
        server.quit()
        
        print("\n✅ Test email đã được gửi thành công!")
        print(f"📧 Hãy kiểm tra inbox của: {smtp_user}")
        print("   (Nếu không thấy, kiểm tra thư mục Spam/Junk)")
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"\n❌ Lỗi xác thực SMTP: {e}")
        print("\n💡 Có thể do:")
        print("   1. App Password không đúng")
        print("   2. Chưa bật xác thực 2 bước")
        print("   3. Đang dùng mật khẩu Gmail thường thay vì App Password")
        print("\n📖 Xem hướng dẫn: HUONG_DAN_SETUP_GMAIL.md")
    except Exception as e:
        print(f"\n❌ Lỗi khi gửi test email: {e}")
        import traceback
        traceback.print_exc()
        print("\n📖 Xem hướng dẫn: HUONG_DAN_SETUP_GMAIL.md")

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 TEST GỬI EMAIL CẢNH BÁO - camAI")
    print("=" * 60)
    print()
    test_send_email()
    print()
    print("=" * 60)

