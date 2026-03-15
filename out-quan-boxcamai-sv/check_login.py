"""
Script để kiểm tra và tạo user đăng nhập
"""
from database_setup import init_database, User, get_session
import hashlib

def check_and_create_user():
    """Kiểm tra và tạo user nếu chưa có"""
    print("=" * 60)
    print("🔍 KIỂM TRA USER ĐĂNG NHẬP")
    print("=" * 60)
    print()
    
    try:
        # Initialize database và lấy session
        engine = init_database()
        session = get_session(engine)
        
        # Kiểm tra user admin
        user = session.query(User).filter(User.username == 'admin').first()
        
        if user:
            print(f"✅ Tìm thấy user: {user.username}")
            print(f"   Password hash: {user.password_hash[:20]}...")
            print()
            
            # Test password
            test_password = 'camai2026'
            test_hash = hashlib.sha256(test_password.encode()).hexdigest()
            
            if user.password_hash == test_hash:
                print("✅ Password hash khớp với 'camai2026'")
            else:
                print("⚠️ Password hash KHÔNG khớp!")
                print(f"   Expected: {test_hash[:20]}...")
                print(f"   Actual:   {user.password_hash[:20]}...")
                print()
                print("💡 Đang cập nhật password...")
                user.password_hash = test_hash
                session.commit()
                print("✅ Đã cập nhật password thành công!")
        else:
            print("⚠️ Không tìm thấy user 'admin'")
            print()
            print("💡 Đang tạo user mới...")
            
            password_hash = hashlib.sha256('camai2026'.encode()).hexdigest()
            new_user = User(username='admin', password_hash=password_hash)
            session.add(new_user)
            session.commit()
            print("✅ Đã tạo user 'admin' với password 'camai2026'")
        
        session.close()
        
        print()
        print("=" * 60)
        print("✅ HOÀN TẤT!")
        print("=" * 60)
        print()
        print("📋 THÔNG TIN ĐĂNG NHẬP:")
        print("   Username: admin")
        print("   Password: camai2026")
        print()
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_and_create_user()
