"""
Script test gửi detection từ client lên server
So sánh với script test trên máy tính để tìm lỗi
"""
import requests
import json
import os
from datetime import datetime
from PIL import Image
import io
import urllib3

# Tắt cảnh báo SSL nếu dùng self-signed certificate
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Cấu hình server
SERVER_HOST = "boxcamai.cloud"  # Tên miền server
SERVER_PORT = 443  # Port HTTPS
USE_HTTPS = True  # Server dùng HTTPS
PROTOCOL = "https" if USE_HTTPS else "http"
SERVER_URL = f"{PROTOCOL}://{SERVER_HOST}:{SERVER_PORT}/api/detections"

# Thông tin client (giống client thật)
SERIAL_NUMBER = "202500000"  # Thay bằng Serial number thật của client
CLIENT_NAME = "Test Client"

def create_test_image():
    """Tạo ảnh test"""
    img = Image.new('RGB', (640, 480), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return img_bytes

def send_detection_test():
    """Gửi detection test giống client thật"""
    
    # Tạo ảnh test
    image_file = create_test_image()
    
    # Dữ liệu detection (giống client thật)
    timestamp = datetime.now().astimezone()
    detection_data = {
        "timestamp": timestamp.isoformat(),
        "class_name": ["person"],
        "confidence": [0.85],
        "bbox_x": [100],
        "bbox_y": [100],
        "bbox_width": [200],
        "bbox_height": [300],
        "image_path": f"test_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}.jpg",
        "serial_number": SERIAL_NUMBER,
        "client_name": CLIENT_NAME,
        "metadata": {
            "detection_id": timestamp.strftime("%Y%m%d_%H%M%S_%f"),
        },
    }
    
    print("=" * 60)
    print("TEST GỬI DETECTION TỪ CLIENT")
    print("=" * 60)
    print(f"Server: {PROTOCOL}://{SERVER_HOST}:{SERVER_PORT}")
    print(f"Server URL: {SERVER_URL}")
    print(f"Serial number: {SERIAL_NUMBER}")
    print(f"Client name: {CLIENT_NAME}")
    print(f"Timestamp: {detection_data['timestamp']}")
    print(f"Class names: {detection_data['class_name']}")
    print(f"Image path: {detection_data['image_path']}")
    print("=" * 60)
    
    try:
        # Gửi giống client thật
        files = {
            'image': (detection_data['image_path'], image_file, 'image/jpeg')
        }
        data = {
            'json_data': json.dumps(detection_data)
        }
        
        print("📤 Đang gửi detection lên server...")
        verify_ssl = False if USE_HTTPS else True  # Tắt SSL verify nếu dùng HTTPS với self-signed cert
        response = requests.post(
            SERVER_URL,
            files=files,
            data=data,
            timeout=10,
            verify=verify_ssl
        )
        
        print(f"📥 Response status: {response.status_code}")
        print(f"📥 Response: {response.text}")
        
        if response.status_code in (200, 201):
            print("✅ Gửi thành công!")
            return True
        else:
            print(f"❌ Gửi thất bại: HTTP {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"   Error: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Lỗi khi gửi: {e}")
        return False
    except Exception as e:
        print(f"❌ Lỗi không xác định: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_client_exists():
    """Kiểm tra client có tồn tại trên server không"""
    try:
        check_url = f"{PROTOCOL}://{SERVER_HOST}:{SERVER_PORT}/api/clients"
        verify_ssl = False if USE_HTTPS else True  # Tắt SSL verify nếu dùng HTTPS với self-signed cert
        response = requests.get(check_url, timeout=5, verify=verify_ssl)
        
        if response.status_code == 200:
            clients = response.json()
            print("\n📋 Danh sách clients trên server:")
            for client in clients:
                print(f"   - ID: {client.get('id')}, Serial: {client.get('serial_number')}, Name: {client.get('name')}")
                
            # Kiểm tra Serial number có tồn tại không
            serial_exists = any(c.get('serial_number') == SERIAL_NUMBER for c in clients)
            if serial_exists:
                print(f"\n✅ Tìm thấy Serial number: {SERIAL_NUMBER}")
            else:
                print(f"\n❌ KHÔNG TÌM THẤY Serial number: {SERIAL_NUMBER}")
                print("   → Cần tạo client trên server với Serial number này!")
            return serial_exists
        elif response.status_code == 401:
            print(f"⚠️  API yêu cầu đăng nhập (HTTP 401)")
            print(f"   → Bỏ qua bước kiểm tra, sẽ test gửi detection trực tiếp")
            return None  # Không xác định được, nhưng vẫn tiếp tục test
        else:
            print(f"⚠️  Không thể kiểm tra clients: HTTP {response.status_code}")
            print(f"   → Bỏ qua bước kiểm tra, sẽ test gửi detection trực tiếp")
            return None  # Không xác định được, nhưng vẫn tiếp tục test
    except Exception as e:
        print(f"⚠️  Lỗi khi kiểm tra clients: {e}")
        print(f"   → Bỏ qua bước kiểm tra, sẽ test gửi detection trực tiếp")
        return None  # Không xác định được, nhưng vẫn tiếp tục test

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("KIỂM TRA CLIENT TRƯỚC KHI GỬI")
    print("=" * 60)
    client_exists = check_client_exists()
    
    if client_exists is False:
        print("\n⚠️  CẢNH BÁO: Client chưa tồn tại trên server!")
        print("   Vui lòng tạo client trên web với Serial number:", SERIAL_NUMBER)
        print("   Hoặc tiếp tục test để xem lỗi cụ thể...")
        print("\nNhấn Enter để tiếp tục test...", end="")
        try:
            input()
        except KeyboardInterrupt:
            print("\nĐã hủy.")
            exit(0)
    elif client_exists is None:
        print("\n⚠️  Không thể kiểm tra client (cần đăng nhập)")
        print("   Sẽ test gửi detection trực tiếp...")
    
    print("\n" + "=" * 60)
    print("BẮT ĐẦU TEST GỬI DETECTION")
    print("=" * 60)
    success = send_detection_test()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TEST THÀNH CÔNG!")
    else:
        print("❌ TEST THẤT BẠI!")
        print("\nCác nguyên nhân có thể:")
        print("1. Serial number không khớp với database")
        print("2. Server không nhận được dữ liệu đúng format")
        print("3. Lỗi network/firewall")
        print("4. Server đang lỗi")
    print("=" * 60)
