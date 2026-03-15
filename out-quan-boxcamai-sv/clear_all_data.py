"""
Script để xóa sạch tất cả dữ liệu:
1. Xóa tất cả detections trong database
2. Xóa tất cả ảnh trong captured_images
3. Xóa tất cả video trong recordings
4. GIỮ LẠI clients (không xóa)
"""
import os
import shutil
from datetime import datetime
from pathlib import Path

DB_FILE = 'detections.db'
CAPTURED_IMAGES_DIR = 'captured_images'
RECORDINGS_DIR = 'recordings'

def clear_detections():
    """Xóa tất cả detections trong database"""
    print("🗑️ Đang xóa tất cả detections trong database...")
    try:
        from database_setup import get_session, Detection
        session = get_session()
        
        # Đếm số lượng detections trước khi xóa
        count = session.query(Detection).count()
        print(f"   📊 Tìm thấy {count} detections")
        
        if count > 0:
            # Xóa tất cả detections
            session.query(Detection).delete()
            session.commit()
            print(f"   ✅ Đã xóa {count} detections!")
        else:
            print("   ℹ️ Không có detections nào để xóa")
        
        session.close()
        return True
    except Exception as e:
        print(f"   ❌ Lỗi khi xóa detections: {e}")
        return False

def clear_clients():
    """Xóa tất cả clients trong database"""
    print("🗑️ Đang xóa tất cả clients trong database...")
    try:
        from database_setup import get_session, Client
        session = get_session()
        
        # Đếm số lượng clients trước khi xóa
        count = session.query(Client).count()
        print(f"   📊 Tìm thấy {count} clients")
        
        if count > 0:
            # Xóa tất cả clients
            session.query(Client).delete()
            session.commit()
            print(f"   ✅ Đã xóa {count} clients!")
        else:
            print("   ℹ️ Không có clients nào để xóa")
        
        session.close()
        return True
    except Exception as e:
        print(f"   ❌ Lỗi khi xóa clients: {e}")
        return False

def clear_captured_images():
    """Xóa tất cả ảnh trong thư mục captured_images"""
    print("🗑️ Đang xóa tất cả ảnh trong captured_images...")
    try:
        if os.path.exists(CAPTURED_IMAGES_DIR):
            # Đếm số file trước khi xóa
            file_count = 0
            for root, dirs, files in os.walk(CAPTURED_IMAGES_DIR):
                file_count += len(files)
            
            print(f"   📊 Tìm thấy {file_count} file ảnh")
            
            if file_count > 0:
                # Xóa tất cả file và thư mục con
                for root, dirs, files in os.walk(CAPTURED_IMAGES_DIR):
                    for file in files:
                        os.remove(os.path.join(root, file))
                    for dir in dirs:
                        shutil.rmtree(os.path.join(root, dir))
                
                print(f"   ✅ Đã xóa {file_count} file ảnh!")
            else:
                print("   ℹ️ Không có ảnh nào để xóa")
        else:
            print("   ℹ️ Thư mục captured_images không tồn tại")
        
        return True
    except Exception as e:
        print(f"   ❌ Lỗi khi xóa ảnh: {e}")
        return False

def clear_recordings():
    """Xóa tất cả video trong thư mục recordings"""
    print("🗑️ Đang xóa tất cả video trong recordings...")
    try:
        if os.path.exists(RECORDINGS_DIR):
            # Đếm số file trước khi xóa
            file_count = 0
            total_size = 0
            for root, dirs, files in os.walk(RECORDINGS_DIR):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_count += 1
                    total_size += os.path.getsize(file_path)
            
            print(f"   📊 Tìm thấy {file_count} file video ({total_size / (1024*1024):.2f} MB)")
            
            if file_count > 0:
                # Xóa tất cả file và thư mục con (giữ lại cấu trúc thư mục gốc)
                for root, dirs, files in os.walk(RECORDINGS_DIR):
                    for file in files:
                        os.remove(os.path.join(root, file))
                
                print(f"   ✅ Đã xóa {file_count} file video!")
            else:
                print("   ℹ️ Không có video nào để xóa")
        else:
            print("   ℹ️ Thư mục recordings không tồn tại")
        
        return True
    except Exception as e:
        print(f"   ❌ Lỗi khi xóa video: {e}")
        return False

def backup_before_delete():
    """Backup trước khi xóa"""
    backup_dir = Path('backup_before_delete')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / timestamp
    
    print("📦 Đang backup trước khi xóa...")
    try:
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # Backup ảnh
        if os.path.exists(CAPTURED_IMAGES_DIR):
            img_backup = backup_path / CAPTURED_IMAGES_DIR
            shutil.copytree(CAPTURED_IMAGES_DIR, img_backup)
            print(f"   ✅ Đã backup ảnh vào {img_backup}")
        
        # Backup video
        if os.path.exists(RECORDINGS_DIR):
            vid_backup = backup_path / RECORDINGS_DIR
            shutil.copytree(RECORDINGS_DIR, vid_backup)
            print(f"   ✅ Đã backup video vào {vid_backup}")
        
        print(f"   📁 Backup tại: {backup_path.absolute()}")
        return str(backup_path)
    except Exception as e:
        print(f"   ⚠️ Lỗi khi backup: {e}")
        return None

def main():
    print("=" * 60)
    print("🧹 XÓA SẠCH TẤT CẢ DỮ LIỆU - CamAI Server")
    print("=" * 60)
    print()
    print("⚠️ CẢNH BÁO: Script này sẽ xóa:")
    print("   • Tất cả detections trong database")
    print("   • Tất cả ảnh trong captured_images/")
    print("   • Tất cả video trong recordings/")
    print("   • ℹ️ Clients sẽ được GIỮ LẠI")
    print()
    print("⚠️ LƯU Ý: File sẽ bị XÓA VĨNH VIỄN (không vào Recycle Bin)!")
    print()
    
    # Hỏi có muốn backup không
    choice = input("❓ Bạn có muốn BACKUP trước khi xóa không? (yes/no): ").strip().lower()
    backup_path = None
    
    if choice == 'yes':
        backup_path = backup_before_delete()
        if backup_path:
            print()
            print("✅ Backup thành công! Bạn có thể khôi phục sau bằng:")
            print(f"   python restore_deleted_files.py")
        print()
    
    print("=" * 60)
    print("🚀 BẮT ĐẦU XÓA DỮ LIỆU...")
    print("=" * 60)
    print()
    
    # Xóa detections
    clear_detections()
    print()
    
    # Xóa ảnh
    clear_captured_images()
    print()
    
    # Xóa video
    clear_recordings()
    print()
    
    print("=" * 60)
    print("✅ HOÀN TẤT!")
    print("=" * 60)
    print()
    print("📋 ĐÃ XÓA:")
    print("   ✅ Tất cả detections")
    print("   ✅ Tất cả ảnh trong captured_images/")
    print("   ✅ Tất cả video trong recordings/")
    print("   ℹ️ Clients được giữ lại")
    print()
    print("💡 BƯỚC TIẾP THEO:")
    print("   1. Chạy server: python server.py")
    print("   2. Hệ thống sẽ bắt đầu lưu dữ liệu mới")
    print()
    if backup_path:
        print("💾 BACKUP:")
        print(f"   File đã được backup tại: {backup_path}")
        print("   Để khôi phục: python restore_deleted_files.py")

if __name__ == '__main__':
    main()
