"""
Script test gửi detection từ Raspberry Pi lên server
Chạy trên Raspberry Pi để test kết nối và gửi detection
"""
import requests
import json
import os
from datetime import datetime
import cv2
import numpy as np
import urllib3

# Tắt cảnh báo SSL nếu dùng self-signed certificate
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Cấu hình server
SERVER_HOST = "boxcamai.cloud"  # Tên miền server
SERVER_PORT = 443  # Port HTTPS
USE_HTTPS = True  # Server dùng HTTPS
PROTOCOL = "https" if USE_HTTPS else "http"
SERVER_URL = f"{PROTOCOL}://{SERVER_HOST}:{SERVER_PORT}/api/detections"

# Đọc Serial number từ file (giống client thật)
def get_serial_number():
    """Đọc Serial number từ file serial_number.txt"""
    serial_file = os.path.join(os.path.dirname(__file__), 'serial_number.txt')
    try:
        if os.path.exists(serial_file):
            with open(serial_file, 'r', encoding='utf-8') as f:
                serial = f.read().strip()
                if serial:
                    return serial
        # Fallback: Serial mặc định
        default_serial = '202500000'
        print(f"⚠️  Không tìm thấy serial_number.txt, dùng Serial mặc định: {default_serial}")
        return default_serial
    except Exception as e:
        print(f"❌ Lỗi khi đọc serial_number.txt: {e}")
        return '202500000'

SERIAL_NUMBER = get_serial_number()
CLIENT_NAME = "Raspberry Pi Test"

def create_test_image():
    """Tạo ảnh test bằng OpenCV (giống client thật)"""
    # Tạo ảnh màu đỏ 640x480
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:, :] = (0, 0, 255)  # BGR: màu đỏ
    
    # Vẽ một số hình để giống ảnh thật
    cv2.rectangle(img, (100, 100), (300, 300), (0, 255, 0), 2)
    cv2.putText(img, "TEST DETECTION", (150, 200), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Lưu vào thư mục hiện tại (thay vì /tmp)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if not current_dir:
        current_dir = os.getcwd()
    
    image_filename = f"test_detection_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
    image_path = os.path.join(current_dir, image_filename)
    
    # Tạo ảnh
    success = cv2.imwrite(image_path, img)
    if not success:
        raise Exception(f"Không thể lưu ảnh vào: {image_path}")
    
    # Kiểm tra file có tồn tại không
    if not os.path.exists(image_path):
        raise Exception(f"File ảnh không tồn tại sau khi tạo: {image_path}")
    
    print(f"   File ảnh đã tạo: {image_path}")
    print(f"   Kích thước file: {os.path.getsize(image_path)} bytes")
    
    return image_path

def send_detection_test():
    """Gửi detection test giống client thật"""
    
    print("=" * 60)
    print("TEST GỬI DETECTION TỪ RASPBERRY PI")
    print("=" * 60)
    print(f"Server: {PROTOCOL}://{SERVER_HOST}:{SERVER_PORT}")
    print(f"Server URL: {SERVER_URL}")
    print(f"Serial number: {SERIAL_NUMBER}")
    print(f"Client name: {CLIENT_NAME}")
    print("=" * 60)
    
    # Tạo ảnh test
    print("\n📸 Đang tạo ảnh test...")
    image_path = create_test_image()
    print(f"✅ Đã tạo ảnh: {image_path}")
    
    # Dữ liệu detection (giống client thật)
    timestamp = datetime.now().astimezone()
    detection_data = {
        "timestamp": timestamp.isoformat(),
        "class_name": ["person"],
        "confidence": [0.85],
        "bbox_x": [100],
        "bbox_y": [100],
        "bbox_width": [200],
        "bbox_height": [200],
        "image_path": os.path.basename(image_path),
        "serial_number": SERIAL_NUMBER,
        "client_name": CLIENT_NAME,
        "metadata": {
            "detection_id": timestamp.strftime("%Y%m%d_%H%M%S_%f"),
            "test": True
        },
    }
    
    print(f"\n📝 Dữ liệu detection:")
    print(f"   Timestamp: {detection_data['timestamp']}")
    print(f"   Class names: {detection_data['class_name']}")
    print(f"   Confidence: {detection_data['confidence']}")
    print(f"   Image path: {detection_data['image_path']}")
    
    try:
        # Kiểm tra file ảnh có tồn tại trước khi gửi
        if not os.path.exists(image_path):
            print(f"❌ File ảnh không tồn tại: {image_path}")
            return False
        
        print(f"   ✅ File ảnh tồn tại: {image_path} ({os.path.getsize(image_path)} bytes)")
        
        # Gửi giống client thật
        print(f"\n📤 Đang gửi detection lên server...")
        with open(image_path, 'rb') as img_file:
            files = {
                'image': (detection_data['image_path'], img_file, 'image/jpeg')
            }
            data = {
                'json_data': json.dumps(detection_data)
            }
            
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
        
        # Xóa file ảnh tạm sau khi gửi thành công
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
                print(f"   ✅ Đã xóa file ảnh tạm")
        except Exception as e:
            print(f"   ⚠️  Không thể xóa file ảnh tạm: {e}")
        
        if response.status_code in (200, 201):
            print("\n✅ GỬI THÀNH CÔNG!")
            print("   Detection đã được lưu trên server")
            return True
        else:
            print(f"\n❌ GỬI THẤT BẠI: HTTP {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"   Error: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Lỗi khi gửi: {e}")
        # Xóa file ảnh tạm
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except:
            pass
        return False
    except Exception as e:
        print(f"\n❌ Lỗi không xác định: {e}")
        import traceback
        traceback.print_exc()
        # Xóa file ảnh tạm
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except:
            pass
        return False

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SCRIPT TEST GỬI DETECTION TỪ RASPBERRY PI")
    print("=" * 60)
    print(f"Serial number: {SERIAL_NUMBER}")
    print(f"Server: {PROTOCOL}://{SERVER_HOST}:{SERVER_PORT}")
    print("=" * 60)
    
    success = send_detection_test()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TEST THÀNH CÔNG!")
        print("   Detection đã được gửi và lưu trên server")
    else:
        print("❌ TEST THẤT BẠI!")
        print("\nCác nguyên nhân có thể:")
        print("1. Serial number không khớp với database")
        print("2. Server không nhận được dữ liệu đúng format")
        print("3. Lỗi network/firewall")
        print("4. Server đang lỗi")
        print("\nKiểm tra:")
        print(f"  - Serial number trên Pi: {SERIAL_NUMBER}")
        print(f"  - Serial number trên server: Xem trong web UI")
        print(f"  - Log server khi nhận detection")
    print("=" * 60)
