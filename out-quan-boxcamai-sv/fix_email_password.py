"""
Script để xóa password rỗng trong database, buộc server dùng từ config.py
"""
from database_setup import init_database, AlertSettings
from sqlalchemy.orm import sessionmaker

def fix_email_password():
    """Xóa password rỗng trong database"""
    print("=" * 60)
    print("🔧 SỬA LỖI EMAIL PASSWORD")
    print("=" * 60)
    print()
    
    try:
        # Initialize database
        engine = init_database()
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Lấy alert settings
        settings = session.query(AlertSettings).first()
        
        if not settings:
            print("⚠️ Chưa có AlertSettings trong database")
            print("💡 Tạo mới AlertSettings...")
            settings = AlertSettings()
            session.add(settings)
            session.commit()
        
        print(f"📧 Email hiện tại: {settings.alert_email or '(chưa có)'}")
        print(f"🔑 Password trong DB: {settings.alert_email_password[:10] + '...' if settings.alert_email_password else '(rỗng)'}")
        print()
        
        # Xóa password nếu rỗng hoặc None
        if not settings.alert_email_password or not settings.alert_email_password.strip():
            print("💡 Đang xóa password rỗng trong database...")
            settings.alert_email_password = None
            session.commit()
            print("✅ Đã xóa password rỗng!")
            print()
            print("📋 Server sẽ dùng password từ config.py:")
            print("   - Email: camainotify@gmail.com")
            print("   - Password: tthmrawhvfwiadjy")
        else:
            print("✅ Password trong database đã có giá trị")
            print(f"   Password: {settings.alert_email_password[:10]}...")
            print()
            print("💡 Nếu vẫn lỗi, có thể password này không đúng.")
            print("   Bạn có muốn xóa password trong database để dùng từ config.py không?")
            print("   (Nhập 'yes' để xóa)")
            confirm = input("> ").strip().lower()
            if confirm == 'yes':
                settings.alert_email_password = None
                session.commit()
                print("✅ Đã xóa password trong database!")
                print("📋 Server sẽ dùng password từ config.py")
        
        session.close()
        
        print()
        print("=" * 60)
        print("✅ HOÀN TẤT!")
        print("=" * 60)
        print()
        print("🔄 Khởi động lại server và thử lại!")
        print()
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    fix_email_password()
