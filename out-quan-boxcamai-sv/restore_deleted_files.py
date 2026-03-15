"""
Script để kiểm tra và hướng dẫn khôi phục file ảnh/video đã xóa
LƯU Ý: File đã xóa bằng clear_all_data.py KHÔNG THỂ khôi phục bằng script này
       vì đã bị xóa vĩnh viễn (không vào Recycle Bin)
"""
import os
import sys
from pathlib import Path

CAPTURED_IMAGES_DIR = 'captured_images'
RECORDINGS_DIR = 'recordings'

def check_recycle_bin():
    """Kiểm tra Recycle Bin (chỉ hoạt động trên Windows)"""
    print("=" * 60)
    print("🗑️ KIỂM TRA RECYCLE BIN")
    print("=" * 60)
    print()
    
    if sys.platform != 'win32':
        print("⚠️ Script này chỉ hỗ trợ Windows")
        return False
    
    try:
        import win32api
        import win32con
        from win32com.shell import shell, shellcon
        
        recycle_bin = shell.SHGetSpecialFolderPath(0, shellcon.CSIDL_BITBUCKET, False)
        print(f"📁 Đường dẫn Recycle Bin: {recycle_bin}")
        print()
        
        # Đếm số file trong Recycle Bin
        recycle_files = list(Path(recycle_bin).rglob('*'))
        file_count = len([f for f in recycle_files if f.is_file()])
        
        print(f"📊 Tìm thấy {file_count} file trong Recycle Bin")
        print()
        
        if file_count > 0:
            print("💡 CÓ THỂ KHÔI PHỤC:")
            print("   1. Mở Recycle Bin (thùng rác)")
            print("   2. Tìm các file từ thư mục:")
            print(f"      • {os.path.abspath(CAPTURED_IMAGES_DIR)}")
            print(f"      • {os.path.abspath(RECORDINGS_DIR)}")
            print("   3. Click chuột phải → Restore")
            return True
        else:
            print("⚠️ Recycle Bin trống - file đã bị xóa vĩnh viễn")
            return False
            
    except ImportError:
        print("⚠️ Cần cài đặt pywin32 để kiểm tra Recycle Bin:")
        print("   pip install pywin32")
        return False
    except Exception as e:
        print(f"❌ Lỗi khi kiểm tra Recycle Bin: {e}")
        return False

def check_backup_files():
    """Kiểm tra file backup nếu có"""
    print()
    print("=" * 60)
    print("📦 KIỂM TRA FILE BACKUP")
    print("=" * 60)
    print()
    
    current_dir = Path('.')
    backup_dirs = [
        current_dir / 'backup',
        current_dir / 'backups',
        current_dir.parent / 'backup',
        current_dir.parent / 'backups',
    ]
    
    found_backups = []
    for backup_dir in backup_dirs:
        if backup_dir.exists():
            # Tìm thư mục captured_images và recordings trong backup
            img_backup = backup_dir / CAPTURED_IMAGES_DIR
            vid_backup = backup_dir / RECORDINGS_DIR
            
            if img_backup.exists() or vid_backup.exists():
                found_backups.append(backup_dir)
                print(f"✅ Tìm thấy backup tại: {backup_dir}")
                if img_backup.exists():
                    img_count = len(list(img_backup.rglob('*.*')))
                    print(f"   📸 Ảnh: {img_count} file")
                if vid_backup.exists():
                    vid_count = len(list(vid_backup.rglob('*.*')))
                    print(f"   🎥 Video: {vid_count} file")
                print()
    
    if not found_backups:
        print("⚠️ Không tìm thấy thư mục backup")
        print()
        print("💡 KIỂM TRA THỦ CÔNG:")
        print("   1. Kiểm tra các thư mục:")
        for backup_dir in backup_dirs:
            print(f"      • {backup_dir.absolute()}")
        print("   2. Kiểm tra ổ cứng khác nếu có backup")
        print("   3. Kiểm tra cloud backup (OneDrive, Google Drive, etc.)")
    
    return len(found_backups) > 0

def restore_from_backup(backup_path):
    """Khôi phục từ thư mục backup"""
    print()
    print("=" * 60)
    print("🔄 KHÔI PHỤC TỪ BACKUP")
    print("=" * 60)
    print()
    
    backup_path = Path(backup_path)
    if not backup_path.exists():
        print(f"❌ Thư mục backup không tồn tại: {backup_path}")
        return False
    
    import shutil
    
    # Khôi phục ảnh
    img_backup = backup_path / CAPTURED_IMAGES_DIR
    if img_backup.exists():
        print(f"📸 Đang khôi phục ảnh từ {img_backup}...")
        try:
            if os.path.exists(CAPTURED_IMAGES_DIR):
                shutil.rmtree(CAPTURED_IMAGES_DIR)
            shutil.copytree(img_backup, CAPTURED_IMAGES_DIR)
            img_count = len(list(Path(CAPTURED_IMAGES_DIR).rglob('*.*')))
            print(f"✅ Đã khôi phục {img_count} file ảnh!")
        except Exception as e:
            print(f"❌ Lỗi khi khôi phục ảnh: {e}")
            return False
    
    # Khôi phục video
    vid_backup = backup_path / RECORDINGS_DIR
    if vid_backup.exists():
        print(f"🎥 Đang khôi phục video từ {vid_backup}...")
        try:
            if os.path.exists(RECORDINGS_DIR):
                shutil.rmtree(RECORDINGS_DIR)
            shutil.copytree(vid_backup, RECORDINGS_DIR)
            vid_count = len(list(Path(RECORDINGS_DIR).rglob('*.*')))
            print(f"✅ Đã khôi phục {vid_count} file video!")
        except Exception as e:
            print(f"❌ Lỗi khi khôi phục video: {e}")
            return False
    
    print()
    print("✅ HOÀN TẤT KHÔI PHỤC!")
    return True

def show_recovery_software():
    """Hướng dẫn dùng phần mềm khôi phục file"""
    print()
    print("=" * 60)
    print("🔧 PHẦN MỀM KHÔI PHỤC FILE ĐÃ XÓA")
    print("=" * 60)
    print()
    print("⚠️ LƯU Ý QUAN TRỌNG:")
    print("   • File đã xóa bằng clear_all_data.py KHÔNG vào Recycle Bin")
    print("   • Cần dùng phần mềm khôi phục chuyên dụng")
    print("   • Tỷ lệ thành công phụ thuộc vào:")
    print("     - Thời gian từ lúc xóa đến lúc khôi phục (càng sớm càng tốt)")
    print("     - Dung lượng ổ cứng còn trống (không ghi đè)")
    print("     - Loại ổ cứng (SSD khó khôi phục hơn HDD)")
    print()
    print("📋 PHẦN MỀM KHUYẾN NGHỊ:")
    print()
    print("1. Recuva (Windows - Miễn phí)")
    print("   • Tải: https://www.ccleaner.com/recuva")
    print("   • Dễ sử dụng, giao diện đơn giản")
    print("   • Quét nhanh, hỗ trợ nhiều định dạng")
    print()
    print("2. PhotoRec (Đa nền tảng - Miễn phí)")
    print("   • Tải: https://www.cgsecurity.org/wiki/PhotoRec")
    print("   • Mạnh mẽ, khôi phục nhiều định dạng")
    print("   • Giao diện dòng lệnh (có GUI: TestDisk)")
    print()
    print("3. DiskDigger (Windows - Có bản miễn phí)")
    print("   • Tải: https://diskdigger.org/")
    print("   • Hỗ trợ khôi phục ảnh tốt")
    print()
    print("4. R-Studio (Trả phí - Chuyên nghiệp)")
    print("   • Tải: https://www.r-studio.com/")
    print("   • Mạnh mẽ nhất, khôi phục nhiều định dạng")
    print()
    print("💡 HƯỚNG DẪN SỬ DỤNG RECUVA:")
    print("   1. Tải và cài đặt Recuva")
    print("   2. Chọn loại file: Pictures (cho ảnh) hoặc Video")
    print("   3. Chọn vị trí: Thư mục cụ thể")
    print(f"      • Ảnh: {os.path.abspath(CAPTURED_IMAGES_DIR)}")
    print(f"      • Video: {os.path.abspath(RECORDINGS_DIR)}")
    print("   4. Click 'Scan' và đợi quét")
    print("   5. Chọn file cần khôi phục → Click 'Recover'")
    print("   6. Chọn thư mục đích để lưu file khôi phục")
    print()
    print("⚠️ QUAN TRỌNG:")
    print("   • KHÔNG ghi file mới vào ổ cứng trước khi khôi phục")
    print("   • Khôi phục vào ổ cứng KHÁC (không phải ổ đã xóa)")
    print("   • Càng sớm khôi phục càng tốt")

def main():
    print("=" * 60)
    print("🔄 KHÔI PHỤC FILE ĐÃ XÓA - CamAI Server")
    print("=" * 60)
    print()
    print("⚠️ CẢNH BÁO:")
    print("   File đã xóa bằng clear_all_data.py KHÔNG vào Recycle Bin")
    print("   (đã bị xóa vĩnh viễn bằng os.remove() và shutil.rmtree())")
    print()
    
    # Kiểm tra Recycle Bin
    has_recycle_bin = check_recycle_bin()
    
    # Kiểm tra backup
    has_backup = check_backup_files()
    
    # Nếu không có trong Recycle Bin và không có backup
    if not has_recycle_bin and not has_backup:
        print()
        print("=" * 60)
        print("❌ KHÔNG THỂ KHÔI PHỤC TỰ ĐỘNG")
        print("=" * 60)
        print()
        print("📋 CÁC PHƯƠNG ÁN:")
        print()
        print("1. ✅ Dùng phần mềm khôi phục file (xem hướng dẫn bên dưới)")
        print("2. ✅ Khôi phục từ backup nếu có")
        print("3. ✅ Khôi phục từ cloud backup (OneDrive, Google Drive, etc.)")
        print("4. ⚠️ File đã mất vĩnh viễn nếu không có backup")
        print()
        
        # Hiển thị hướng dẫn phần mềm khôi phục
        show_recovery_software()
    
    # Nếu có backup, hỏi có muốn khôi phục không
    if has_backup:
        print()
        print("=" * 60)
        choice = input("❓ Bạn có muốn khôi phục từ backup không? (yes/no): ").strip().lower()
        if choice == 'yes':
            backup_path = input("Nhập đường dẫn thư mục backup: ").strip()
            if backup_path:
                restore_from_backup(backup_path)

if __name__ == '__main__':
    main()
