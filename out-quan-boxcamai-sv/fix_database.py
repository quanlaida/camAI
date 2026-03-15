"""
Script để fix database bị corrupt:
1. Backup file cũ (đổi tên)
2. Xóa file database bị corrupt
3. Tự động tạo lại database mới (sẽ mất dữ liệu cũ nếu không có backup)
"""
import os
import shutil
from datetime import datetime

DB_FILE = 'detections.db'
DB_BACKUP = f'detections_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'

def backup_database():
    """Backup database cũ trước khi fix"""
    if os.path.exists(DB_FILE):
        print(f"📦 Đang backup {DB_FILE} thành {DB_BACKUP}...")
        try:
            shutil.copy2(DB_FILE, DB_BACKUP)
            print(f"✅ Đã backup thành công!")
            return True
        except Exception as e:
            print(f"⚠️ Không thể backup (file có thể bị corrupt): {e}")
            return False
    else:
        print(f"⚠️ Không tìm thấy file {DB_FILE}")
        return False

def remove_corrupt_database():
    """Xóa file database bị corrupt"""
    if os.path.exists(DB_FILE):
        print(f"🗑️ Đang xóa file {DB_FILE} bị corrupt...")
        try:
            os.remove(DB_FILE)
            print(f"✅ Đã xóa file cũ!")
            return True
        except Exception as e:
            print(f"❌ Lỗi khi xóa file: {e}")
            return False
    else:
        print(f"⚠️ File {DB_FILE} không tồn tại")
        return True

def recreate_database():
    """Tạo lại database mới"""
    print()
    print("🔨 Đang tạo lại database mới...")
    try:
        from database_setup import init_database
        engine = init_database()
        print("✅ Đã tạo lại database thành công!")
        return True
    except Exception as e:
        print(f"❌ Lỗi khi tạo database: {e}")
        return False

def main():
    print("=" * 60)
    print("🔧 FIX DATABASE CORRUPT - CamAI Server")
    print("=" * 60)
    print()
    
    # Backup database cũ
    backup_database()
    
    # Xóa file corrupt
    if remove_corrupt_database():
        # Tự động tạo lại database mới
        if recreate_database():
            print()
            print("=" * 60)
            print("✅ HOÀN TẤT!")
            print("=" * 60)
            print()
            print("📋 LƯU Ý QUAN TRỌNG:")
            print("   ⚠️ Database mới đã được tạo, nhưng CHƯA CÓ DỮ LIỆU!")
            print()
            print("📝 BƯỚC TIẾP THEO:")
            print("   1. Chạy server: python server.py")
            print("   2. Vào web interface: http://localhost:5000")
            print("   3. Tab 'Clients' → Click 'Add New Client'")
            print("   4. Nhập Serial Number của máy client (ví dụ: 202500000)")
            print("   5. Lưu lại")
            print()
            print("💡 Sau khi tạo client, detections sẽ bắt đầu được lưu!")
            print()
            print("🔄 Nếu có file detections.db từ máy khác:")
            print("   → Copy vào thư mục này để khôi phục dữ liệu cũ")
            print("   → Hoặc dùng file backup: " + DB_BACKUP)
        else:
            print()
            print("❌ Không thể tạo lại database. Vui lòng chạy: python server.py")
    else:
        print("❌ Không thể xóa file database. Vui lòng xóa thủ công.")

if __name__ == '__main__':
    main()
