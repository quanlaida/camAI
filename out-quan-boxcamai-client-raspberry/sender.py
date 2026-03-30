import requests
import json
import threading
from multiprocessing import Queue, Event
import time
import config
import os
import io

def get_serial_number():
    """Đọc Serial number từ file serial_number.txt"""
    serial_file = os.path.join(os.path.dirname(__file__), 'serial_number.txt')
    try:
        if os.path.exists(serial_file):
            with open(serial_file, 'r', encoding='utf-8') as f:
                serial = f.read().strip()
                if serial:
                    return serial
        # Fallback: tạo file mới với Serial mặc định
        default_serial = '202500000'
        with open(serial_file, 'w', encoding='utf-8') as f:
            f.write(default_serial)
        print(f"⚠️  Created serial_number.txt with default Serial: {default_serial}")
        return default_serial
    except Exception as e:
        print(f"❌ Error reading serial_number.txt: {e}")
        return None

# Global queue and thread for asynchronous sending
detection_queue = Queue()
send_thread = None
stop_send_thread = Event()

def send_detection_to_server(detection_data, image_bytes=None):
    """Add detection data to queue for asynchronous sending.

    - Nếu `image_bytes` được truyền (client mới): gửi trực tiếp ảnh từ RAM, KHÔNG cần lưu file local.
    - Nếu không có `image_bytes` (client cũ): fallback đọc file từ `config.IMAGES_DIR` như trước.
    """
    # Add client information to detection data
    serial_number = get_serial_number()
    if serial_number:
        detection_data['serial_number'] = serial_number
    else:
        # Fallback to client_name for backward compatibility
        detection_data['client_name'] = config.CLIENT_NAME
    
    detection_data['client_latitude'] = config.CLIENT_LATITUDE 
    detection_data['client_longitude'] = config.CLIENT_LONGITUDE 

    # Gắn kèm image_bytes (nếu có) để worker quyết định cách gửi
    payload = {
        "detection_data": detection_data,
        "image_bytes": image_bytes,
    }
    detection_queue.put(payload)

def send_worker():
    """Background worker to send detections to server"""
    while not stop_send_thread.is_set():
        try:
            # Get detection payload from queue with timeout
            payload = detection_queue.get(timeout=1.0)
            detection_data = payload.get("detection_data") if isinstance(payload, dict) else payload
            image_bytes = payload.get("image_bytes") if isinstance(payload, dict) else None

            print(f"Sending {detection_data['class_name']} to server")

            # Chuẩn bị dữ liệu multipart
            files = None

            # Ưu tiên dùng image_bytes (client mới: không lưu file)
            if image_bytes is not None:
                try:
                    image_filename = detection_data.get("image_path") or "frame.jpg"
                    files = {
                        "image": (image_filename, io.BytesIO(image_bytes), "image/jpeg"),
                    }
                except Exception as e:
                    print(f"Error preparing in-memory image for sending: {e}")
                    detection_queue.task_done()
                    continue
            else:
                # Fallback: client cũ vẫn dùng file trên đĩa
                image_path_full = os.path.join(config.IMAGES_DIR, detection_data.get("image_path", ""))
                if not os.path.exists(image_path_full):
                    print(f"Image file not found: {image_path_full}")
                    detection_queue.task_done()
                    continue
                try:
                    files = {
                        "image": (
                            detection_data.get("image_path", os.path.basename(image_path_full)),
                            open(image_path_full, "rb"),
                            "image/jpeg",
                        )
                    }
                except Exception as e:
                    print(f"Error opening image file: {e}")
                    detection_queue.task_done()
                    continue

            # Send to server as multipart
            try:
                data = {"json_data": json.dumps(detection_data)}
                response = requests.post(
                    f"https://{config.SERVER_HOST}:{config.SERVER_PORT}/api/detections",
                    files=files,
                    data=data,
                    timeout=10,
                )
                if response.status_code in (200, 201):
                    print(f"Detection sent successfully: {detection_data['class_name']}")
                else:
                    print(f"Failed to send detection: HTTP {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"error: {error_data.get('error', 'Unknown error')}")
                    except Exception:
                        print(f"error: {response.text}")
            except requests.exceptions.RequestException as e:
                print(f"Error sending detection: {e}")
            finally:
                # Đóng file nếu là file trên đĩa
                if files:
                    file_obj = files.get("image", (None, None, None))[1]
                    if hasattr(file_obj, "close"):
                        try:
                            file_obj.close()
                        except Exception:
                            pass

            # Mark task as done
            detection_queue.task_done()

        except:
            # Timeout or other exception, continue loop
            continue

def start_send_thread():
    """Start the background sending thread"""
    global send_thread
    if send_thread is None or not send_thread.is_alive():
        stop_send_thread.clear()
        send_thread = threading.Thread(target=send_worker, daemon=True)
        send_thread.start()
        print("Detection sending thread started")

def stop_send_thread_func():
    """Stop the background sending thread"""
    stop_send_thread.set()
    if send_thread and send_thread.is_alive():
        send_thread.join(timeout=5)
        print("Detection sending thread stopped")
