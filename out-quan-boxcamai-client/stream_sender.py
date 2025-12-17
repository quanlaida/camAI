import requests
import threading
import time
import config
import os
from multiprocessing import Queue
import cv2
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

# Global queue để nhận processed frames từ detection process
processed_stream_queue = Queue(maxsize=10)

processed_stream_thread = None
stop_processed_stream_thread = threading.Event()

def send_video_frame(frame):
    """Gửi raw frame về server (được gọi từ video_capture_process)"""
    # Hiện tại không gửi raw stream để giảm tải cho Pi
    # Hàm này được giữ lại để tương thích với code hiện tại
    pass

def send_processed_frame(frame):
    """Thêm processed frame (có detection boxes) vào queue để gửi về server"""
    try:
        # Validate frame
        if frame is None or frame.size == 0:
            print("⚠️ send_processed_frame: Invalid frame (None or empty)")
            return
        
        # Frame skipping: ưu tiên giữ frame MỚI nhất, không để raise queue.Full liên tục
        # Thử put, nếu full thì bỏ bớt frame cũ rồi thử lại 1 lần
        # Resize frame để giảm bandwidth - Tối ưu: dùng INTER_LINEAR (nhanh hơn)
        resized_frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_LINEAR)
        try:
            processed_stream_queue.put_nowait(resized_frame.copy())
        except Exception:
            # Queue có thể bị full giữa lúc full() và put_nowait() (race condition),
            # nên bỏ 1 frame cũ rồi thử lại, nếu vẫn lỗi thì bỏ qua frame này.
            try:
                processed_stream_queue.get_nowait()
            except Exception:
                pass
            try:
                processed_stream_queue.put_nowait(resized_frame.copy())
            except Exception:
                pass
    except Exception as e:
        # Không spam traceback vì lỗi queue.Full không ảnh hưởng logic chính
        print(f"⚠️ Error in send_processed_frame (ignored): {e}")

def processed_stream_worker():
    """Worker thread gửi processed frames về server"""
    global stop_processed_stream_thread
    
    print("📹 Processed video stream sender thread started (AI detection)")
    
    # Adaptive frame rate tracking - Tối ưu cho mượt mà
    target_fps = 25  # Tăng lên 25 FPS cho processed stream để rất mượt
    frame_interval = 1.0 / target_fps
    last_send_time = time.time()
    
    # Session để reuse connection
    session = requests.Session()
    # Tối ưu session: tăng timeout và pool size
    adapter = requests.adapters.HTTPAdapter(pool_connections=1, pool_maxsize=1, max_retries=2)
    session.mount('https://', adapter)
    
    while not stop_processed_stream_thread.is_set():
        try:
            # Lấy frame từ queue với timeout
            try:
                frame = processed_stream_queue.get(timeout=1.0)
            except:
                continue  # Timeout, tiếp tục loop
            
            if frame is None:
                continue
            
            # Encode frame thành JPEG với quality tối ưu cho mượt mà
            # Tối ưu: Giảm quality xuống 65 để tăng tốc encoding (vẫn đủ nhìn cho stream)
            ret, buffer = cv2.imencode('.jpg', frame, [
                cv2.IMWRITE_JPEG_QUALITY, 65,  # Giảm từ 75 xuống 65 để tăng tốc
                cv2.IMWRITE_JPEG_OPTIMIZE, 1,
                cv2.IMWRITE_JPEG_PROGRESSIVE, 0  # Tắt progressive để encode nhanh hơn
            ])
            if not ret:
                continue
            
            # Convert to bytes
            frame_bytes = io.BytesIO(buffer).read()
            
            # Gửi về server với retry logic
            serial_number = get_serial_number()
            if not serial_number:
                continue
            
            files = {'frame': ('processed_frame.jpg', frame_bytes, 'image/jpeg')}
            data = {
                'serial_number': serial_number,
                'frame_type': 'processed'
            }
            
            # Retry logic: thử tối đa 2 lần
            success = False
            for attempt in range(2):
                try:
                    response = session.post(
                        f'https://{config.SERVER_HOST}:{config.SERVER_PORT}/api/video/frame',
                        files=files,
                        data=data,
                        timeout=5  # Tăng timeout từ 2s lên 5s
                    )
                    if response.status_code == 200:
                        success = True
                        break
                except requests.exceptions.RequestException:
                    if attempt < 1:  # Chỉ retry 1 lần
                        time.sleep(0.1)
            
            # Adaptive frame rate
            elapsed = time.time() - last_send_time
            if elapsed < frame_interval:
                time.sleep(frame_interval - elapsed)
            last_send_time = time.time()
        
        except Exception as e:
            print(f"❌ Error in processed stream worker: {e}")
            time.sleep(1)
    
    print("📹 Processed video stream sender thread stopped")

def start_processed_stream_thread():
    """Khởi động thread gửi processed video stream"""
    global processed_stream_thread, stop_processed_stream_thread
    
    if processed_stream_thread is None or not processed_stream_thread.is_alive():
        stop_processed_stream_thread.clear()
        processed_stream_thread = threading.Thread(target=processed_stream_worker, daemon=True)
        processed_stream_thread.start()
        print("📹 Processed video streaming enabled")

def stop_processed_stream_thread_func():
    """Dừng thread gửi processed video stream"""
    global stop_processed_stream_thread
    stop_processed_stream_thread.set()
    if processed_stream_thread and processed_stream_thread.is_alive():
        processed_stream_thread.join(timeout=2)

