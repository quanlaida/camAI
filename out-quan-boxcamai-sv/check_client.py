"""
Script để kiểm tra client có tồn tại trong database không
"""
from database_setup import get_session, Client, Detection

def check_clients():
    """Kiểm tra danh sách clients trong database"""
    print("=" * 60)
    print("🔍 KIỂM TRA CLIENTS TRONG DATABASE")
    print("=" * 60)
    print()
    
    try:
        session = get_session()
        
        # Đếm số lượng clients
        client_count = session.query(Client).count()
        print(f"📊 Tổng số clients trong database: {client_count}")
        print()
        
        if client_count == 0:
            print("⚠️ KHÔNG CÓ CLIENT NÀO TRONG DATABASE!")
            print()
            print("💡 GIẢI PHÁP:")
            print("   1. Vào web interface: http://localhost:5000")
            print("   2. Tab 'Clients' → Click 'Add New Client'")
            print("   3. Nhập Serial Number của máy client (ví dụ: 202500000)")
            print("   4. Nhập tên client (ví dụ: CamAI)")
            print("   5. Lưu lại")
            print()
            print("⚠️ LƯU Ý: Server KHÔNG tự động tạo client nữa!")
            print("   Nếu client chưa có trong database, detections sẽ KHÔNG được lưu!")
        else:
            print("✅ DANH SÁCH CLIENTS:")
            print("-" * 60)
            clients = session.query(Client).all()
            for i, client in enumerate(clients, 1):
                print(f"{i}. ID: {client.id}")
                print(f"   Tên: {client.name}")
                print(f"   Serial Number: {client.serial_number}")
                print(f"   Detect Enabled: {'✅ Có' if client.is_detect_enabled else '❌ Không'}")
                
                # Đếm số detections của client này
                det_count = session.query(Detection).filter(Detection.client_id == client.id).count()
                print(f"   Số detections: {det_count}")
                print()
        
        # Kiểm tra detections
        det_count = session.query(Detection).count()
        print("-" * 60)
        print(f"📊 Tổng số detections trong database: {det_count}")
        
        if det_count == 0:
            print("⚠️ KHÔNG CÓ DETECTION NÀO!")
            print()
            print("💡 NGUYÊN NHÂN CÓ THỂ:")
            print("   1. Client chưa được tạo trong database")
            print("   2. Serial number của client không khớp")
            print("   3. Client chưa gửi detection lên server")
            print("   4. Server đang từ chối lưu detection (check log)")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_clients()
