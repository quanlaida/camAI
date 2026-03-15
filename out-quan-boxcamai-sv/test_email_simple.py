#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script test email đơn giản - Kiểm tra cấu hình SMTP Gmail
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import config

def test_email():
    """Test gửi email với cấu hình từ config.py"""
    try:
        sender = config.ALERT_EMAIL_SENDER
        password = config.ALERT_EMAIL_PASSWORD
        receiver = input(f"Nhập email nhận (Enter để dùng {sender}): ").strip() or sender
        
        print(f"\n📧 Cấu hình Email:")
        print(f"   Sender: {sender}")
        print(f"   Password: {'*' * len(password) if password else 'None'}")
        print(f"   Receiver: {receiver}")
        
        if not sender or not password:
            print("❌ Lỗi: Thiếu ALERT_EMAIL_SENDER hoặc ALERT_EMAIL_PASSWORD trong config.py")
            return False
        
        print(f"\n🔗 Đang kết nối SMTP...")
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=30)
        print(f"✅ Đã kết nối SMTP")
        
        print(f"🔐 Đang bật TLS...")
        server.starttls()
        print(f"✅ Đã bật TLS")
        
        print(f"🔐 Đang đăng nhập với {sender}...")
        server.login(sender, password)
        print(f"✅ Đã đăng nhập thành công")
        
        # Tạo email
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = receiver
        msg['Subject'] = '✅ Test Email - CamAI'
        
        body = """
        <html>
        <body>
            <h2>✅ Test Email Thành Công!</h2>
            <p>Nếu bạn nhận được email này, có nghĩa là cấu hình SMTP đã đúng.</p>
        </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))
        
        print(f"📤 Đang gửi email đến {receiver}...")
        server.send_message(msg)
        print(f"✅ Đã gửi email thành công!")
        
        server.quit()
        print(f"\n✅ Hoàn tất! Vui lòng kiểm tra hộp thư (cả Spam).")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"\n❌ Lỗi xác thực SMTP:")
        print(f"   {str(e)}")
        print(f"\n💡 Giải pháp:")
        print(f"   1. Kiểm tra lại App Password trong config.py")
        print(f"   2. Đảm bảo đã bật 2-Step Verification trên Gmail")
        print(f"   3. Tạo App Password mới từ: https://myaccount.google.com/apppasswords")
        return False
        
    except smtplib.SMTPException as e:
        print(f"\n❌ Lỗi SMTP:")
        print(f"   {str(e)}")
        return False
        
    except Exception as e:
        print(f"\n❌ Lỗi:")
        print(f"   {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("🧪 TEST EMAIL - CamAI System")
    print("=" * 60)
    test_email()
