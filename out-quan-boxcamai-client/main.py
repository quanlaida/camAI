import cv2
import subprocess
import sys
import os
import numpy as np
from multiprocessing import Process, Queue, Event
import argparse
import config
from detection import detection_process
from sender import start_send_thread, stop_send_thread_func
from stream_sender import start_stream_thread, stop_stream_thread_func, send_video_frame
# RAW stream đã bỏ - chỉ dùng processed stream để giảm tải cho Pi
import requests


def video_capture_process(q, stop_event, source, camera_ip=None):
    # Đơn giản hoá: luôn dùng stream chất lượng THẤP (subtype=1) cho AI để ổn định
    rtsp_subtype = 1
    if config.VIDEO_FILE_PATH:
        # Use OpenCV to read from local video file
        cap = cv2.VideoCapture(config.VIDEO_FILE_PATH)
        if not cap.isOpened():
            print(f"Error: Could not open video file {config.VIDEO_FILE_PATH}")
            return
        try:
            while not stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    print("End of video file reached.")
                    break
                if frame is not None and not q.full():
                    q.put(frame)
                    # send_video_frame(frame)  # Đã bỏ RAW stream để giảm tải cho Pi
        finally:
            cap.release()
    else:
        if source == 'rtsp':
            # Ưu tiên: camera_ip từ server > config.RTSP_IP
            selected_ip = None
            if camera_ip:
                selected_ip = camera_ip
                print(f"Using camera IP from server: {selected_ip}")
            elif config.RTSP_IP:
                selected_ip = config.RTSP_IP
                print(f"Using camera IP from config: {selected_ip}")
            
            # Check if we have an IP address
            if selected_ip is None:
                print("ERROR: No camera IP address available!")
                print("Please set IP address on server or in config.RTSP_IP")
                return  # Thoát hàm thay vì restart service
            
            # Use OpenCV to read from RTSP stream
            # Luôn dùng subtype=1 (chất lượng thấp ổn định cho AI)
            rtsp_subtype = 1
            rtspLink = f"rtsp://{config.RTSP_USER}:{config.RTSP_PASS}@{selected_ip}:{config.RTSP_PORT}/cam/realmonitor?channel=1&subtype={rtsp_subtype}"
            quality_text = "chất lượng thấp (fixed)"  # luôn low quality
            print(f"Connecting to RTSP ({quality_text}): rtsp://{config.RTSP_USER}:***@{selected_ip}:{config.RTSP_PORT}/cam/realmonitor?channel=1&subtype={rtsp_subtype}")
            # Hiển thị đầy đủ URL (ẩn mật khẩu) mỗi lần kết nối để dễ kiểm tra
            print(f"[RTSP] URL hiện tại: {rtspLink.replace(config.RTSP_PASS, '***')}")
            cap = cv2.VideoCapture(rtspLink)
            if not cap.isOpened():
                print(f"Error: Could not open RTSP stream at {selected_ip}:{config.RTSP_PORT}")
                return
            try:
                while not stop_event.is_set():
                    ret, frame = cap.read()
                    if not ret:
                        print("RTSP stream ended.")
                        break
                    if frame is not None and not q.full():
                        q.put(frame)
                        send_video_frame(frame)  # Gửi raw frame về server
            finally:
                cap.release()
        elif source == 'webcam':
            # Use OpenCV to read from local webcam
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                print("Error: Could not open webcam")
                return
            try:
                while not stop_event.is_set():
                    ret, frame = cap.read()
                    if not ret:
                        print("Webcam capture ended.")
                        break
                    if frame is not None and not q.full():
                        q.put(frame)
                        send_video_frame(frame)  # Gửi raw frame về server
            finally:
                cap.release()
        else:  # rpicam
            # Use rpicam-vid subprocess for camera
            cmd = [
                'rpicam-vid',
                '--width', str(config.CAMERA_WIDTH),
                '--height', str(config.CAMERA_HEIGHT),
                '--framerate', str(config.CAMERA_FRAMERATE),
                '--codec', 'mjpeg',
                '--inline',
                '--timeout', '0',
                '-o', '-',
                '--nopreview'
            ]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=0)
            buffer = b""
            try:
                while not stop_event.is_set():
                    data = proc.stdout.read(1024)
                    if not data:
                        break
                    buffer += data
                    while b'\xff\xd9' in buffer:
                        split_idx = buffer.index(b'\xff\xd9') + 2
                        jpg_data = buffer[:split_idx]
                        buffer = buffer[split_idx:]
                        jpg = np.frombuffer(jpg_data, dtype=np.uint8)
                        frame = cv2.imdecode(jpg, cv2.IMREAD_COLOR)
                        if frame is not None and not q.full():
                            q.put(frame)
                            send_video_frame(frame)  # Gửi raw frame về server
            finally:
                proc.terminate()
                proc.wait()


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
        print(f"⚠️  Please update serial_number.txt with your device Serial!")
        return default_serial
    except Exception as e:
        print(f"❌ Error reading serial_number.txt: {e}")
        return None

def get_info():
    """Lấy thông tin client từ server bằng Serial number"""
    serial_number = get_serial_number()
    if not serial_number:
        print("❌ Cannot get Serial number from file!")
        return None
    
    try:
        response = requests.get(
            f'https://{config.SERVER_HOST}:{config.SERVER_PORT}/api/clients/by-serial/{serial_number}',
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get client info: HTTP {response.status_code}")
            print(f"❌ Serial number '{serial_number}' not found on server!")
            print(f"⚠️  Please create client with this Serial on server first!")
            print(f"⚠️  Client will continue without server connection...")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error getting client info: {e}")
        print(f"⚠️  Cannot connect to server at https://{config.SERVER_HOST}:{config.SERVER_PORT}")
        print(f"⚠️  Please check if server is running and accessible")
        return None


def check_server_updates(current_ip, current_roi, current_roi_regions_json, current_show_overlay, current_rtsp_subtype=None):
    """
    Kiểm tra xem có thay đổi từ server không
    Returns: (ip_changed, roi_changed, overlay_changed, subtype_changed, new_ip, new_roi, new_roi_regions_json, new_show_overlay, new_rtsp_subtype) hoặc None nếu lỗi
    """
    try:
        client_info = get_info()
        if not client_info:
            return None
        
        new_ip = client_info.get('ip_address')
        new_roi = (
            client_info.get('roi_x1'),
            client_info.get('roi_y1'),
            client_info.get('roi_x2'),
            client_info.get('roi_y2')
        )
        new_roi_regions_json = client_info.get('roi_regions')
        new_show_overlay = client_info.get('show_roi_overlay', True)
        # rtsp_subtype hiện không còn dùng cho client (luôn dùng subtype=1)
        new_rtsp_subtype = current_rtsp_subtype
        
        # So sánh IP
        current_ip_normalized = current_ip if current_ip is not None else ""
        new_ip_normalized = new_ip if new_ip is not None else ""
        ip_changed = (current_ip_normalized != new_ip_normalized)
        
        # So sánh ROI (single ROI - backward compatible)
        roi_changed = False
        current_roi_tuple = tuple(x if x is not None else 0 for x in current_roi) if current_roi else (0, 0, 0, 0)
        new_roi_tuple = tuple(x if x is not None else 0 for x in new_roi) if new_roi else (0, 0, 0, 0)
        roi_changed = (current_roi_tuple != new_roi_tuple)
        
        # So sánh multiple ROI regions
        if current_roi_regions_json != new_roi_regions_json:
            roi_changed = True
        overlay_changed = (current_show_overlay is not None and new_show_overlay is not None and current_show_overlay != new_show_overlay)
        
        # Không theo dõi subtype nữa
        subtype_changed = False

        # Debug log (giảm spam: chỉ log khi có thay đổi)
        if ip_changed or roi_changed or overlay_changed or subtype_changed:
            print(f"🔍 Change detected - IP: {ip_changed}, ROI: {roi_changed}, Overlay: {overlay_changed}, Subtype: {subtype_changed}")
            if roi_changed:
                print(f"   ROI regions changed: {current_roi_regions_json} -> {new_roi_regions_json}")
            if overlay_changed:
                print(f"   show_roi_overlay: {current_show_overlay} -> {new_show_overlay}")
            if subtype_changed:
                quality_old = "chất lượng cao" if current_rtsp_subtype == 0 else "chất lượng thấp"
                quality_new = "chất lượng cao" if new_rtsp_subtype == 0 else "chất lượng thấp"
                print(f"   rtsp_subtype: {current_rtsp_subtype} ({quality_old}) -> {new_rtsp_subtype} ({quality_new})")
        
        return (ip_changed, roi_changed, overlay_changed, subtype_changed, new_ip, new_roi, new_roi_regions_json, new_show_overlay, new_rtsp_subtype)
    
    except Exception as e:
        print(f"❌ Error checking server updates: {e}")
        import traceback
        traceback.print_exc()
        return None


def server_polling_thread(stop_event, initial_ip, initial_roi, initial_roi_regions_json, initial_show_overlay, initial_rtsp_subtype=None):
    """
    Thread chạy nền để kiểm tra thay đổi từ server (chỉ kiểm tra MỘT LẦN rồi dừng).
    Nếu phát hiện thay đổi IP, ROI, hoặc rtsp_subtype, tự động restart service.
    Tránh việc restart liên tục do polling lặp.
    """
    import time
    import config
    
    if not config.ENABLE_AUTO_RESTART:
        print("Auto-restart disabled in config, skipping polling thread")
        return
    
    current_ip = initial_ip
    current_roi = initial_roi
    current_roi_regions_json = initial_roi_regions_json
    current_show_overlay = initial_show_overlay
    current_rtsp_subtype = None  # Không dùng subtype nữa
    poll_count = 0
    
    print(f"🔄 Server polling thread started (checking every {config.POLL_INTERVAL}s)")
    print(f"   Initial IP: {current_ip}, Initial ROI: {current_roi}")
    print(f"   Initial ROI regions: {current_roi_regions_json}")
    print(f"   RTSP subtype is fixed to 1 (low quality) on client")
    
    # Đợi interval trước khi check (nếu cần)
    print(f"⏳ Waiting {config.POLL_INTERVAL}s before first check...")
    stop_event.wait(config.POLL_INTERVAL)

    if stop_event.is_set():
        print("🛑 Server polling thread stopped (before check)")
        return

    # Đơn giản hóa: không debounce, không cooldown, phát hiện là restart ngay
    max_polls = getattr(config, 'POLL_MAX_CHECKS', 0)  # 0 = không giới hạn

    while not stop_event.is_set():
        try:
            poll_count += 1
            print(f"🔍 Polling server... (check #{poll_count})")
            
            # Kiểm tra thay đổi
            result = check_server_updates(current_ip, current_roi, current_roi_regions_json, current_show_overlay, current_rtsp_subtype)
            
            if result is None:
                print("⚠️ Could not check server updates, will retry next time")
                # Đợi interval trước khi retry
                stop_event.wait(config.POLL_INTERVAL)
                if stop_event.is_set():
                    break
                continue
            
            ip_changed, roi_changed, overlay_changed, subtype_changed, new_ip, new_roi, new_roi_regions_json, new_show_overlay, new_rtsp_subtype = result
            
            # Phát hiện thay đổi - CHỈ restart nếu thực sự có thay đổi
            if ip_changed:
                print(f"🔄 IP Camera changed detected!")
                print(f"   Old IP: {current_ip}")
                print(f"   New IP: {new_ip}")
                print("🔄 Restarting service to apply changes...")
                # Đợi một chút trước khi restart để log kịp ghi
                time.sleep(1)
                restart_service()
                return  # Thread sẽ kết thúc sau khi restart
            
            if roi_changed:
                print(f"🔄 ROI changed detected!")
                print(f"   Old ROI: {current_roi}")
                print(f"   New ROI: {new_roi}")
                print("🔄 Restarting service to apply changes...")
                # Đợi một chút trước khi restart để log kịp ghi
                time.sleep(1)
                restart_service()
                return  # Thread sẽ kết thúc sau khi restart

            if overlay_changed:
                print(f"🔄 show_roi_overlay changed: {current_show_overlay} -> {new_show_overlay}")
                print("🔄 Restarting service to apply changes...")
                time.sleep(1)
                restart_service()
                return
            
            if subtype_changed:
                quality_old = "chất lượng cao" if current_rtsp_subtype == 0 else "chất lượng thấp"
                quality_new = "chất lượng cao" if new_rtsp_subtype == 0 else "chất lượng thấp"
                print(f"🔄 RTSP subtype changed detected!")
                print(f"   Old subtype: {current_rtsp_subtype} ({quality_old})")
                print(f"   New subtype: {new_rtsp_subtype} ({quality_new})")
                selected_ip = new_ip or current_ip or config.RTSP_IP
                if selected_ip:
                    new_rtsp_url = f"rtsp://{config.RTSP_USER}:{config.RTSP_PASS}@{selected_ip}:{config.RTSP_PORT}/cam/realmonitor?channel=1&subtype={new_rtsp_subtype}"
                    print(f"   [RTSP] URL mới: {new_rtsp_url.replace(config.RTSP_PASS, '***')}")
                print("🔄 Restarting service to apply changes...")
                time.sleep(1)
                restart_service()
                return
            
            # Cập nhật giá trị hiện tại (để lần sau so sánh)
            current_ip = new_ip
            current_roi = new_roi
            current_rtsp_subtype = new_rtsp_subtype
            current_roi_regions_json = new_roi_regions_json
            current_show_overlay = new_show_overlay
            
            if poll_count % 10 == 0:  # Log mỗi 10 lần
                print(f"✅ No critical changes detected (checked {poll_count} times)")

            # Dừng sau max_polls (nếu có giới hạn)
            if max_polls and poll_count >= max_polls:
                print(f"ℹ️ Max polls reached ({max_polls}), stopping polling thread.")
                break

            # Đợi interval trước lần check tiếp theo
            stop_event.wait(config.POLL_INTERVAL)
            if stop_event.is_set():
                break

        except Exception as e:
            print(f"❌ Error in polling thread: {e}")
            import traceback
            traceback.print_exc()
            # Dừng thread nếu lỗi
            break
    
    print("🛑 Server polling thread stopped")


# Hàm create_new_client đã bị xóa vì client không tự động tạo nữa
# Client phải được tạo trên server với Serial number đúng


def stop_service():
    try:
        print("🔄 STOPPING boxcamai service...")

        res = subprocess.run(
            ['sudo', 'systemctl', 'stop', 'boxcamai'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if res.returncode == 0:
            print("✅ Service boxcamai stopped successfully")
            sys.exit(0)  # ✅ Thoát thành công
        else:
            print(f"❌ Failed to stop service: {res.stderr}")
            sys.exit(1)  # ✅ Thoát với lỗi (vì restart thất bại)

    except subprocess.TimeoutExpired:
        print("❌ Timeout when stopping service")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error stopping service: {e}")
        sys.exit(1)


def restart_service():
    """Restart service và thoát clean"""
    try:
        print("🔄 Restarting boxcamai service...")

        res = subprocess.run(
            ['sudo', 'systemctl', 'restart', 'boxcamai'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if res.returncode == 0:
            print("✅ Service boxcamai restarted successfully")
            sys.exit(0)  # ✅ Thoát thành công
        else:
            print(f"❌ Failed to restart service: {res.stderr}")
            sys.exit(1)  # ✅ Thoát với lỗi (vì restart thất bại)

    except subprocess.TimeoutExpired:
        print("❌ Timeout when restarting service")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error restarting service: {e}")
        sys.exit(1)


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Object Detection Client')
    parser.add_argument('--not-sent', action='store_true',
                        help='Run without sending detections to server')
    parser.add_argument('--video', type=str,
                        help='Path to video file for testing')
    parser.add_argument('--rtsp', action='store_true',
                        help='Use RTSP stream for video')
    parser.add_argument('--rpicam', action='store_true',
                        help='Use rpicam for video')
    parser.add_argument('--webcam', action='store_true',
                        help='Use local webcam for video')
    parser.add_argument('--display', action='store_true',
                        help='Display detection results in a window')
    args = parser.parse_args()

    not_sent = args.not_sent

    # Get client info from server
    client_info = get_info()
    if client_info:
        print(f"Client info retrieved: {client_info}")
        is_detect_enabled = client_info.get('is_detect_enabled', True)
        show_roi_overlay = client_info.get('show_roi_overlay', True)
        roi_x1 = client_info.get('roi_x1')
        roi_y1 = client_info.get('roi_y1')
        roi_x2 = client_info.get('roi_x2')
        roi_y2 = client_info.get('roi_y2')
        roi_regions_json = client_info.get('roi_regions')  # Multiple ROI regions
        global ip_address
        ip_address = client_info.get('ip_address')

        # Override not_sent based on server setting
        if not is_detect_enabled:
            not_sent = True
            print("Detection disabled by server")
    else:
        print("Could not retrieve client info, using default settings")
        is_detect_enabled = True
        show_roi_overlay = True
        roi_x1 = roi_y1 = roi_x2 = roi_y2 = None
        roi_regions_json = None
        ip_address = None  # Khởi tạo ip_address

    # Determine video source
    if args.webcam:
        source = 'webcam'
    elif args.rtsp:
        source = 'rtsp'
    elif args.rpicam:
        source = 'rpicam'
    else:
        source = 'rpicam'  # default

    # Note: Sender thread will be started in the detection process
    # if not not_sent:
    #     start_send_thread()

    # Create queue for inter-process communication
    frame_queue = Queue(maxsize=10)
    stop_event = Event()

    # Start detection process
    detection_proc = Process(target=detection_process, args=(
        frame_queue, stop_event, not_sent, args.display, roi_x1, roi_y1, roi_x2, roi_y2, roi_regions_json, show_roi_overlay))
    detection_proc.start()

    # Override config if video file specified via args
    if args.video:
        config.VIDEO_FILE_PATH = args.video

    # Start video capture process (truyền ip_address vào)
    capture_proc = Process(target=video_capture_process,
                           args=(frame_queue, stop_event, source, ip_address))
    capture_proc.start()

    # Start raw video streaming thread - ĐÃ BỎ để giảm tải cho Pi
    # start_stream_thread()  # Chỉ dùng processed stream (hình ảnh đã qua AI detection)

    # Start server polling thread để kiểm tra thay đổi từ server
    import threading
    polling_thread = None
    if config.ENABLE_AUTO_RESTART:
        current_roi = (roi_x1, roi_y1, roi_x2, roi_y2)
        # Lấy rtsp_subtype ban đầu từ server (default 0 để khớp UI)
        initial_rtsp_subtype = None
        if client_info:
            initial_rtsp_subtype = client_info.get('rtsp_subtype', 0)
        polling_thread = threading.Thread(
            target=server_polling_thread,
            args=(stop_event, ip_address, current_roi, roi_regions_json, show_roi_overlay, initial_rtsp_subtype),
            daemon=True
        )
        polling_thread.start()

    try:
        print("Starting object detection...")
        # Wait for processes
        capture_proc.join()
        detection_proc.join()

    except KeyboardInterrupt:
        print("Interrupted by user")

    finally:
        # Cleanup
        stop_event.set()
        # stop_stream_thread_func()  # Đã bỏ RAW stream - không cần dừng
        capture_proc.join(timeout=5)
        detection_proc.join(timeout=5)
        # Note: Sender thread cleanup is now handled in detection process
        # if not not_sent:
        #     stop_send_thread_func()
        print("Detection client stopped")


if __name__ == '__main__':
    main()
