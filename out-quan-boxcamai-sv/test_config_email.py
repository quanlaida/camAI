#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script test để kiểm tra App Password từ config/.env
"""
import os
import sys

# Load .env nếu có
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Đã load file .env")
except ImportError:
    print("⚠️  Chưa cài python-dotenv, bỏ qua .env")
except Exception as e:
    print(f"⚠️  Không thể load .env: {e}")

# Import config
import config

print("\n" + "=" * 60)
print("📧 KIỂM TRA CẤU HÌNH EMAIL")
print("=" * 60)

print(f"\n📌 Email Sender:")
print(f"   {config.ALERT_EMAIL_SENDER}")

print(f"\n📌 App Password:")
password = config.ALERT_EMAIL_PASSWORD
if password:
    print(f"   {'*' * len(password)} ({len(password)} ký tự)")
    print(f"   (Giá trị thực: {password})")
else:
    print("   ❌ KHÔNG CÓ PASSWORD!")

print(f"\n📌 Nguồn:")
if os.getenv('ALERT_EMAIL_PASSWORD'):
    print("   ✅ Lấy từ file .env hoặc environment variable")
else:
    print("   ⚠️  Lấy từ config.py (giá trị mặc định)")

print("\n" + "=" * 60)
print("🧪 TEST GỬI EMAIL")
print("=" * 60)

# Test gửi email
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    sender = config.ALERT_EMAIL_SENDER
    password = config.ALERT_EMAIL_PASSWORD
    receiver = input(f"\nNhập email nhận (Enter để dùng {sender}): ").strip() or sender
    
    if not sender or not password:
        print("❌ Thiếu email hoặc password!")
        sys.exit(1)
    
    print(f"\n🔗 Đang kết nối SMTP...")
    server = smtplib.SMTP('smtp.gmail.com', 587, timeout=30)
    print(f"✅ Đã kết nối")
    
    print(f"🔐 Đang bật TLS...")
    server.starttls()
    print(f"✅ Đã bật TLS")
    
    print(f"🔐 Đang đăng nhập với {sender}...")
    server.login(sender, password)
    print(f"✅ Đã đăng nhập thành công!")
    
    # Tạo email
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = receiver
    msg['Subject'] = '✅ Test Email - CamAI'
    
    body = "<html><body><h2>✅ Test Email Thành Công!</h2><p>App Password đã đúng.</p></body></html>"
    msg.attach(MIMEText(body, 'html'))
    
    print(f"📤 Đang gửi email đến {receiver}...")
    server.send_message(msg)
    print(f"✅ Đã gửi email thành công!")
    
    server.quit()
    print(f"\n✅ Hoàn tất! Kiểm tra hộp thư (cả Spam).")
    
except smtplib.SMTPAuthenticationError as e:
    print(f"\n❌ LỖI XÁC THỰC SMTP:")
    print(f"   {str(e)}")
    print(f"\n💡 Giải pháp:")
    print(f"   1. Tạo App Password mới từ: https://myaccount.google.com/apppasswords")
    print(f"   2. Tạo file .env với:")
    print(f"      ALERT_EMAIL_PASSWORD=your-new-app-password")
    print(f"   3. Hoặc cập nhật trong config.py")
    sys.exit(1)
    
except Exception as e:
    print(f"\n❌ LỖI:")
    print(f"   {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
