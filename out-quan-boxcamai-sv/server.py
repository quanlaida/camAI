import config as config
from database_setup import Detection, Client, AlertSettings, init_database, get_session
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy import func
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
from flask_cors import CORS
from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.exceptions import ClientDisconnected
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
import requests
import threading
import shutil
sys.path.insert(0, '..')


# Kiểm tra ffmpeg có sẵn không và lưu đường dẫn
FFMPEG_PATH = None

def check_ffmpeg_available():
    """Kiểm tra xem ffmpeg có được cài đặt và có trong PATH không. Trả về đường dẫn nếu tìm thấy."""
    global FFMPEG_PATH
    
    # Thử tìm trong PATH hiện tại
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        FFMPEG_PATH = ffmpeg_path
        return True
    
    # Nếu không tìm thấy, thử refresh PATH từ environment variables
    try:
        import os
        # Thử cập nhật PATH từ registry (Windows)
        if os.name == 'nt':  # Windows
            try:
                import winreg
                # Lấy PATH từ registry
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as key:
                    system_path_reg = winreg.QueryValueEx(key, "PATH")[0]
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
                    try:
                        user_path_reg = winreg.QueryValueEx(key, "PATH")[0]
                    except FileNotFoundError:
                        user_path_reg = ""
                # Kết hợp PATH
                combined_path = system_path_reg + os.pathsep + user_path_reg
                # Tạm thời cập nhật PATH trong process này
                os.environ['PATH'] = combined_path
                # Thử tìm lại
                ffmpeg_path = shutil.which('ffmpeg')
                if ffmpeg_path:
                    FFMPEG_PATH = ffmpeg_path
                    return True
            except Exception:
                pass
        
        # Thử các đường dẫn phổ biến trên Windows
        if os.name == 'nt':
            common_paths = [
                r"C:\ffmpeg\bin\ffmpeg.exe",
                r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
                r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
                os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"),
            ]
            for path in common_paths:
                if os.path.exists(path):
                    FFMPEG_PATH = path
                    return True
    except Exception:
        pass
    
    return False

FFMPEG_AVAILABLE = check_ffmpeg_available()
if not FFMPEG_AVAILABLE:
    print("⚠️ CẢNH BÁO: ffmpeg không được tìm thấy trên hệ thống!")
    print("   Chức năng ghi video sẽ không hoạt động.")
    print("   Vui lòng cài đặt ffmpeg:")
    print("   - Windows: Tải từ https://ffmpeg.org/download.html hoặc dùng: choco install ffmpeg")
    print("   - Linux: sudo apt-get install ffmpeg (Ubuntu/Debian) hoặc sudo yum install ffmpeg (CentOS/RHEL)")
    print("   - macOS: brew install ffmpeg")
else:
    print(f"✅ ffmpeg đã được tìm thấy và sẵn sàng sử dụng. (Đường dẫn: {FFMPEG_PATH})")


app = Flask(__name__, static_folder='web', template_folder='templates')
# CORS configuration - cho phép tất cả origins để hỗ trợ domain
CORS(app, resources={
    r"/api/*": {"origins": "*"},
    r"/*": {"origins": "*"}
})

# Initialize database
engine = init_database()
Session = sessionmaker(bind=engine)

# Video streaming storage (lưu frames trong memory)
# Format: {client_id: {'frame': bytes, 'timestamp': datetime, 'type': 'raw'|'processed'}}
video_frames = {}
processed_video_frames = {}
import threading
video_frames_lock = threading.Lock()
processed_frames_lock = threading.Lock()

# Video recording state: { client_id: {'process': subprocess.Popen, 'start_time': datetime, 'video_index': int, 'current_output_path': Path} }
recording_processes = {}
recording_lock = threading.Lock()
MAX_VIDEO_DURATION_MINUTES = 30  # Mỗi video tối đa 30 phút

# Monitoring thread để kiểm tra recording processes
def monitor_recording_processes():
    """Thread để monitor các recording processes và tự động cleanup khi process dừng"""
    import time
    while True:
        try:
            time.sleep(5)  # Kiểm tra mỗi 5 giây
            with recording_lock:
                to_remove = []
                for client_id, proc in list(recording_processes.items()):
                    if proc.poll() is not None:
                        # Process đã dừng (có thể do lỗi hoặc crash)
                        print(f"⚠️ Recording process for client {client_id} has stopped unexpectedly (exit code: {proc.returncode})")
                        to_remove.append(client_id)
                
                # Cleanup các process đã dừng
                for client_id in to_remove:
                    recording_processes.pop(client_id, None)
                    print(f"🧹 Cleaned up stopped recording process for client {client_id}")
        except Exception as e:
            print(f"Error in recording monitor thread: {e}")
            time.sleep(5)

# Bắt đầu monitoring thread (chỉ start một lần)
_monitor_thread_started = False
if not _monitor_thread_started:
    monitor_thread = threading.Thread(target=monitor_recording_processes, daemon=True)
    monitor_thread.start()
    _monitor_thread_started = True
    print("✅ Recording monitor thread started")

# Đảm bảo thư mục lưu record tồn tại
try:
    Path(config.VIDEO_RECORD_BASE_DIR).mkdir(parents=True, exist_ok=True)
except Exception as e:
    print(f"⚠️ Cannot create VIDEO_RECORD_BASE_DIR: {e}")

# Tối ưu: Cache client info để tránh query database mỗi request
# Format: {serial_number or client_name: {'id': client_id, 'last_updated': datetime, 'timestamp': float, 'needs_db_update': bool}}
# TTL Cache: Thêm timestamp để tự động expire cache sau TTL
client_cache = {}
client_cache_lock = threading.Lock()
CACHE_TTL = 5  # Cache TTL: 5 giây (tự động refresh sau 5 giây)
client_update_queue = []  # Queue để batch update database
client_update_lock = threading.Lock()

def _batch_update_clients_async():
    """Update clients trong database async (background thread)"""
    if not client_update_queue:
        return
    
    # Copy queue và clear
    with client_update_lock:
        updates = client_update_queue.copy()
        client_update_queue.clear()
    
    # Update database trong background
    def update_db():
        try:
            session = Session()
            try:
                # Group by client_id để update một lần
                client_ids = list(set([u['client_id'] for u in updates]))
                latest_timestamps = {}
                for u in updates:
                    cid = u['client_id']
                    if cid not in latest_timestamps or u['timestamp'] > latest_timestamps[cid]:
                        latest_timestamps[cid] = u['timestamp']
                
                # Batch update
                for client_id, timestamp in latest_timestamps.items():
                    client = session.query(Client).filter(Client.id == client_id).first()
                    if client:
                        client.updated_at = timestamp
                
                session.commit()
            except Exception as e:
                session.rollback()
                print(f"Error in batch update clients: {e}")
            finally:
                session.close()
        except Exception as e:
            print(f"Error in async client update: {e}")
    
    # Chạy trong background thread
    thread = threading.Thread(target=update_db, daemon=True)
    thread.start()

# Background thread để batch update định kỳ (giảm từ 2 giây xuống 0.5 giây để giảm delay)
def _periodic_client_update():
    """Periodic update clients trong database"""
    import time
    while True:
        time.sleep(0.5)  # Update mỗi 0.5 giây (giảm delay từ 2 giây)
        if client_update_queue:
            _batch_update_clients_async()

# Start background thread
_update_thread = threading.Thread(target=_periodic_client_update, daemon=True)
_update_thread.start()

def _invalidate_client_cache(serial_number=None, client_name=None, client_id=None):
    """Invalidate client cache khi client được tạo/cập nhật/xóa"""
    with client_cache_lock:
        if serial_number and serial_number in client_cache:
            del client_cache[serial_number]
        if client_name and client_name in client_cache:
            del client_cache[client_name]
        # Nếu có client_id, xóa tất cả entries có client_id đó
        if client_id:
            keys_to_remove = []
            for key, value in client_cache.items():
                if value.get('id') == client_id:
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del client_cache[key]


@app.route('/')
def index():
    """Serve the main web UI"""
    from flask import make_response
    response = make_response(render_template('index.html', version=datetime.now().strftime('%Y%m%d%H%M%S')))
    # CORS headers cho HTML page
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET'
    return response


@app.route('/style.css')
def serve_css():
    """Serve CSS file with cache busting"""
    response = app.send_static_file('style.css')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    # CORS headers cho static files
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET'
    return response


@app.route('/script.js')
def serve_js():
    """Serve JavaScript file with cache busting"""
    response = app.send_static_file('script.js')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    # CORS headers cho static files
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET'
    return response


@app.route('/api/detections', methods=['POST'])
def receive_detection():
    """Receive detection data from the AI client"""
    try:
        # Get JSON data from form
        json_data = request.form.get('json_data')
        if not json_data:
            return jsonify({'error': 'No JSON data provided'}), 400
        data = json.loads(json_data)

        # Get image file
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        image_file = request.files['image']

        # Validate required fields
        required_fields = ['class_name', 'confidence', 'timestamp']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Get or create client
        client_id = data.get('client_id')
        serial_number = data.get('serial_number')
        client_name = data.get('client_name')  # Backward compatibility
        client = None
        session = None

        if client_id or serial_number or client_name:
            session = Session()
            try:
                if client_id:
                    client = session.query(Client).filter(
                        Client.id == client_id).first()
                elif serial_number:
                    # Tìm bằng Serial number (mới)
                    client = session.query(Client).filter(
                        Client.serial_number == serial_number).first()
                elif client_name:
                    # Tìm bằng name (backward compatibility)
                    client = session.query(Client).filter(
                        Client.name == client_name).first()

                # KHÔNG tự động tạo client nữa - client phải được tạo trên server với Serial number
                if client:
                    client_id = client.id
                    # Cập nhật updated_at để track online status khi có detection
                    client.updated_at = datetime.now()
                    session.commit()
                else:
                    # Client không tồn tại - không thể lưu detection
                    session.close()
                    return jsonify({'error': 'Client not found. Please create client first with correct Serial number.'}), 404
            finally:
                session.close()
                session = None

        # Save image to server directory
        image_filename = data.get('image_path', image_file.filename)
        image_path = os.path.join(config.SERVER_IMAGES_DIR, image_filename)
        image_file.save(image_path)

        class_names = data["class_name"]
        confidences = data["confidence"]
        xs = data["bbox_x"]
        ys = data["bbox_y"]
        ws = data["bbox_width"]
        hs = data["bbox_height"]

        # Create detection record
        session = Session()
        detection_id = None
        try:
            for i in range(len(class_names)):
                detection = Detection(
                    timestamp=datetime.fromisoformat(data['timestamp']),
                    class_name=class_names[i],
                    confidence=float(confidences[i]),
                    image_path=image_filename,
                    bbox_x=int(xs[i]),
                    bbox_y=int(ys[i]),
                    bbox_width=int(ws[i]),
                    bbox_height=int(hs[i]),
                    metadata_json=json.dumps(data.get('metadata', {})),
                    client_id=client_id
                )

                session.add(detection)

            session.commit()
            
            # Lấy detection ID để gửi email (lấy detection đầu tiên trong batch)
            if len(class_names) > 0:
                detection_id = session.query(Detection).filter(
                    Detection.client_id == client_id
                ).order_by(Detection.timestamp.desc()).first().id
        finally:
            session.close()
            session = None

        # Gửi email và Telegram cảnh báo nếu có cấu hình
        if detection_id and client_id:
            send_alert_email_async(detection_id, client_id)
            send_alert_telegram_async(detection_id, client_id)

        return jsonify({'message': 'Detection saved successfully'}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/detections', methods=['GET'])
def get_detections():
    """Get all detections with optional filtering"""
    session = None
    try:
        session = Session()

        # Get query parameters for filtering
        class_name = request.args.get('class')
        client_id = request.args.get('client_id')
        client_name = request.args.get('client_name')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        query = session.query(Detection)

        if class_name:
            query = query.filter(Detection.class_name == class_name)

        if client_id:
            query = query.filter(Detection.client_id == int(client_id))

        if client_name:
            # Join with Client table to filter by client name
            query = query.join(Client).filter(Client.name == client_name)

        # Order by timestamp (most recent first)
        detections = query.options(joinedload(Detection.client)).order_by(
            Detection.timestamp.desc()).offset(offset).limit(limit).all()

        # Convert to JSON-serializable format
        result = []
        for det in detections:
            detection_data = {
                'id': det.id,
                'timestamp': det.timestamp.isoformat(),
                'class_name': det.class_name,
                'confidence': det.confidence,
                'image_path': det.image_path,
                'bbox_x': det.bbox_x,
                'bbox_y': det.bbox_y,
                'bbox_width': det.bbox_width,
                'bbox_height': det.bbox_height,
                'metadata': json.loads(det.metadata_json) if det.metadata_json else {}
            }

            # Add client information if available
            if det.client:
                detection_data['client'] = {
                    'id': det.client.id,
                    'name': det.client.name,
                    'latitude': det.client.latitude,
                    'longitude': det.client.longitude,
                    'is_detect_enabled': det.client.is_detect_enabled
                }

            result.append(detection_data)

        return jsonify(result)

    except Exception as e:
        import traceback
        print(f"ERROR in get_detections: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        # Đảm bảo session luôn được đóng
        if session:
            try:
                session.close()
            except:
                pass


# ==================== TELEGRAM ALERT FUNCTIONS ====================

def send_alert_telegram_async(detection_id, client_id):
    """Gửi Telegram cảnh báo trong background thread"""
    thread = threading.Thread(target=send_alert_telegram, args=(detection_id, client_id))
    thread.daemon = True
    thread.start()

def send_alert_telegram(detection_id, client_id):
    """Gửi Telegram cảnh báo khi có detection trong ROI"""
    session = None
    try:
        # Kiểm tra bot token và chat ID từ config (không dùng database)
        if not config.TELEGRAM_BOT_TOKEN:
            print("⚠️ TELEGRAM_BOT_TOKEN chưa được cấu hình")
            return
        
        if not config.TELEGRAM_ENABLED:
            return  # Telegram bị tắt
        
        chat_id = config.TELEGRAM_CHAT_ID
        if not chat_id:
            print("⚠️ TELEGRAM_CHAT_ID chưa được cấu hình")
            return
        
        session = Session()
        
        # Lấy detection info
        detection = session.query(Detection).filter(Detection.id == detection_id).first()
        if not detection:
            return
        
        # Lấy client info để check ROI
        client = session.query(Client).filter(Client.id == client_id).first()
        if not client:
            return
        
        # CHỈ gửi Telegram nếu client có ROI (kiểm tra roi_regions hoặc roi_x1,y1,x2,y2)
        hasROI = False
        roi_names = []
        if client.roi_regions:
            try:
                roi_list = json.loads(client.roi_regions)
                if isinstance(roi_list, list) and len(roi_list) > 0:
                    hasROI = True
                    roi_names = [roi.get('name', f'ROI {i+1}') for i, roi in enumerate(roi_list) if roi.get('name')]
                    if not roi_names:
                        roi_names = [f'ROI {i+1}' for i in range(len(roi_list))]
            except:
                pass
        if not hasROI:
            hasROI = (client.roi_x1 and client.roi_y1 and client.roi_x2 and client.roi_y2)
            if hasROI:
                roi_names = ['ROI 1']
        
        if not hasROI:
            return
        
        bot_token = config.TELEGRAM_BOT_TOKEN
        
        # Tạo chuỗi tên ROI để hiển thị
        if len(roi_names) == 1:
            roi_display_name = roi_names[0]
        elif len(roi_names) > 1:
            roi_display_name = ', '.join(roi_names)
        else:
            roi_display_name = 'ROI'
        
        # Format timestamp
        timestamp_str = detection.timestamp.strftime('%d/%m/%Y %H:%M:%S')
        
        # Tạo message
        message = f"🚨 *CẢNH BÁO PHÁT HIỆN ĐỐI TƯỢNG*\n\n"
        message += f"📍 *Client:* {client.name}\n"
        message += f"🎯 *Đối tượng:* {detection.class_name}\n"
        message += f"📊 *Độ tin cậy:* {detection.confidence * 100:.1f}%\n"
        message += f"⏰ *Thời gian:* {timestamp_str}\n"
        message += f"🔍 *Khu vực:* {roi_display_name}\n"
        message += f"\n🔗 Xem chi tiết: https://boxcamai.cloud/detections/{detection.id}"
        
        # Gửi text message trước
        send_text_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        text_data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        try:
            response = requests.post(send_text_url, json=text_data, timeout=10)
            if response.status_code == 200:
                print(f"✅ Đã gửi Telegram cảnh báo đến chat_id: {chat_id}")
            else:
                print(f"⚠️ Lỗi gửi Telegram text: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Lỗi khi gửi Telegram text: {e}")
        
        # Gửi ảnh detection nếu có
        if detection.image_path:
            try:
                image_path = os.path.join(config.SERVER_IMAGES_DIR, detection.image_path)
                if os.path.exists(image_path):
                    send_photo_url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
                    with open(image_path, 'rb') as photo:
                        files = {'photo': photo}
                        photo_data = {
                            'chat_id': chat_id,
                            'caption': f"📸 Ảnh phát hiện: {detection.class_name} ({detection.confidence * 100:.1f}%)"
                        }
                        response = requests.post(send_photo_url, data=photo_data, files=files, timeout=10)
                        if response.status_code == 200:
                            print(f"✅ Đã gửi ảnh detection qua Telegram")
                        else:
                            print(f"⚠️ Lỗi gửi Telegram photo: {response.status_code}")
            except Exception as e:
                print(f"❌ Lỗi khi gửi ảnh qua Telegram: {e}")
        
    except Exception as e:
        print(f"❌ Lỗi trong send_alert_telegram: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if session:
            try:
                session.close()
            except:
                pass

# ==================== EMAIL ALERT FUNCTIONS ====================

def send_alert_email_async(detection_id, client_id):
    """Gửi email cảnh báo trong background thread"""
    thread = threading.Thread(target=send_alert_email, args=(detection_id, client_id))
    thread.daemon = True
    thread.start()

def send_alert_email(detection_id, client_id):
    """Gửi email cảnh báo khi có detection trong ROI"""
    session = None
    try:
        session = Session()
        
        # Lấy alert settings
        alert_settings = session.query(AlertSettings).first()
        if not alert_settings or not alert_settings.email_enabled or not alert_settings.alert_email:
            return  # Không có cấu hình email
        
        # Lấy detection info
        detection = session.query(Detection).filter(Detection.id == detection_id).first()
        if not detection:
            return
        
        # Lấy client info để check ROI
        client = session.query(Client).filter(Client.id == client_id).first()
        if not client:
            return
        
        # CHỈ gửi email nếu client có ROI (kiểm tra roi_regions hoặc roi_x1,y1,x2,y2)
        hasROI = False
        roi_names = []  # Danh sách tên ROI
        if client.roi_regions:
            try:
                roi_list = json.loads(client.roi_regions)
                if isinstance(roi_list, list) and len(roi_list) > 0:
                    hasROI = True
                    # Lấy tên các ROI
                    roi_names = [roi.get('name', f'ROI {i+1}') for i, roi in enumerate(roi_list) if roi.get('name')]
                    if not roi_names:
                        roi_names = [f'ROI {i+1}' for i in range(len(roi_list))]
            except:
                pass
        if not hasROI:
            hasROI = (client.roi_x1 and client.roi_y1 and client.roi_x2 and client.roi_y2)
            if hasROI:
                roi_names = ['ROI 1']  # Default name for single ROI
        
        if not hasROI:
            return
        
        email_to = alert_settings.alert_email
        
        # Tạo chuỗi tên ROI để hiển thị
        if len(roi_names) == 1:
            roi_display_name = roi_names[0]
        elif len(roi_names) > 1:
            roi_display_name = ', '.join(roi_names)
        else:
            roi_display_name = 'ROI'
        
        # Đóng session trước khi gửi email (email có thể mất thời gian)
        session.close()
        session = None
        
        # Chuẩn bị email
        subject = f"🔔 Cảnh báo: {detection.class_name} được phát hiện trong {roi_display_name} - {client.name}"
        
        # Tạo nội dung email HTML
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                <h2 style="color: #e74c3c;">🔔 Cảnh báo Phát hiện trong {roi_display_name}</h2>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #2c3e50;">Thông tin Phát hiện:</h3>
                    <p><strong>Đối tượng:</strong> {detection.class_name}</p>
                    <p><strong>Độ tin cậy:</strong> {(detection.confidence * 100):.1f}%</p>
                    <p><strong>Thời gian:</strong> {detection.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>Client:</strong> {client.name}</p>
                    <p><strong>Vùng cảnh báo:</strong> {roi_display_name}</p>
                    <p><strong>Vị trí:</strong> X={detection.bbox_x}, Y={detection.bbox_y}, W={detection.bbox_width}, H={detection.bbox_height}</p>
                </div>
                
                <div style="text-align: center; margin: 20px 0;">
                    <img src="cid:detection_image" style="max-width: 100%; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" alt="Detection Image">
                </div>
                
                <p style="color: #7f8c8d; font-size: 12px; text-align: center; margin-top: 20px;">
                    Đây là email tự động từ hệ thống AI Detection Dashboard
                </p>
            </div>
        </body>
        </html>
        """
        
        # Cấu hình SMTP Gmail
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        smtp_user = config.ALERT_EMAIL_SENDER  # Email gửi đi (từ config)
        smtp_password = config.ALERT_EMAIL_PASSWORD  # App password từ config
        
        if not smtp_user or not smtp_password:
            print("⚠️ Email alert không được cấu hình (thiếu SMTP credentials)")
            return
        
        # Tạo email message
        msg = MIMEMultipart('related')
        msg['From'] = smtp_user
        msg['To'] = email_to
        msg['Subject'] = subject
        
        # Thêm HTML body
        msg.attach(MIMEText(email_body, 'html'))
        
        # Attach hình ảnh
        image_path = os.path.join(config.SERVER_IMAGES_DIR, detection.image_path)
        if os.path.exists(image_path):
            with open(image_path, 'rb') as img_file:
                img_data = img_file.read()
                img = MIMEImage(img_data)
                img.add_header('Content-ID', '<detection_image>')
                img.add_header('Content-Disposition', 'inline', filename=detection.image_path)
                msg.attach(img)
        
        # Gửi email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Đã gửi email cảnh báo đến {email_to}")
        
    except Exception as e:
        import traceback
        print(f"❌ Lỗi khi gửi email cảnh báo: {e}")
        traceback.print_exc()
    finally:
        # Đảm bảo session luôn được đóng
        if session:
            try:
                session.close()
            except:
                pass

@app.route('/api/alert-settings', methods=['GET'])
def get_alert_settings():
    """Lấy cấu hình cảnh báo"""
    try:
        session = Session()
        settings = session.query(AlertSettings).first()
        session.close()
        
        if not settings:
            # Tạo mới nếu chưa có
            session = Session()
            settings = AlertSettings()
            session.add(settings)
            session.commit()
            session.close()
            
            return jsonify({
                'alert_email': None,
                'email_enabled': False,
                # Telegram settings được lấy từ config
                'telegram_chat_id': config.TELEGRAM_CHAT_ID,
                'telegram_enabled': config.TELEGRAM_ENABLED
            }), 200
        
        return jsonify({
            'alert_email': settings.alert_email,
            'email_enabled': settings.email_enabled,
            # Telegram settings được lấy từ config, không từ database
            'telegram_chat_id': config.TELEGRAM_CHAT_ID,
            'telegram_enabled': config.TELEGRAM_ENABLED
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/alert-settings', methods=['POST', 'PUT'])
def update_alert_settings():
    """Cập nhật cấu hình cảnh báo"""
    try:
        data = request.json
        session = Session()
        
        settings = session.query(AlertSettings).first()
        if not settings:
            settings = AlertSettings()
            session.add(settings)
        
        if 'alert_email' in data:
            settings.alert_email = data['alert_email']
        if 'email_enabled' in data:
            settings.email_enabled = data.get('email_enabled', False)
        # Telegram settings được cấu hình trong config.py, không lưu vào database
        
        settings.updated_at = datetime.now()
        session.commit()
        session.close()
        
        return jsonify({'message': 'Alert settings updated successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/alert-settings/test-telegram', methods=['POST'])
def test_telegram_alert():
    """Test gửi Telegram message"""
    try:
        # Lấy chat_id từ config (không dùng database)
        chat_id = config.TELEGRAM_CHAT_ID
        bot_token = config.TELEGRAM_BOT_TOKEN
        
        if not bot_token:
            return jsonify({'error': 'TELEGRAM_BOT_TOKEN chưa được cấu hình trong config'}), 400
        
        if not chat_id:
            return jsonify({'error': 'Vui lòng nhập Chat ID hoặc lưu Chat ID trước'}), 400
        
        # Gửi test message
        send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        message = "✅ *TEST TELEGRAM BOT*\n\nĐây là tin nhắn test từ hệ thống CamAI. Nếu bạn nhận được tin nhắn này, cấu hình Telegram đã hoạt động đúng!"
        
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(send_url, json=data, timeout=10)
        
        if response.status_code == 200:
            return jsonify({'message': f'Đã gửi tin nhắn test đến Telegram chat_id: {chat_id}'}), 200
        else:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get('description', response.text)
            return jsonify({'error': f'Lỗi khi gửi Telegram: {error_msg}'}), 400
            
    except Exception as e:
        return jsonify({'error': f'Lỗi: {str(e)}'}), 500

@app.route('/api/alert-settings/test', methods=['POST'])
def test_alert_settings():
    session = None
    try:
        data = request.get_json() or {}
        test_email = data.get('email')

        session = Session()
        settings = session.query(AlertSettings).first()

        sender = config.ALERT_EMAIL_SENDER
        password = config.ALERT_EMAIL_PASSWORD
        receiver = test_email or (settings.alert_email if settings else None)

        if not sender or not password:
            return jsonify({'error': 'Thiếu ALERT_EMAIL_SENDER hoặc ALERT_EMAIL_PASSWORD'}), 400
        if not receiver:
            return jsonify({'error': 'Thiếu email đích để gửi test'}), 400

        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = receiver
        msg['Subject'] = '✅ Email Test - CamAI Alert'

        # Template sáng, nền trắng, block xanh/vàng nhẹ
        html_body = f"""
        <html>
        <body style="margin:0;padding:0;background:#f4f6fb;font-family:'Inter','Segoe UI',Arial,sans-serif;">
            <div style="max-width:620px;margin:20px auto;padding:0 12px;">
                <div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,0.08);overflow:hidden;">
                    <div style="padding:18px 22px;background:linear-gradient(135deg,#1da1f2 0%,#4f46e5 100%);">
                        <h2 style="margin:0;font-size:22px;color:#ffffff;letter-spacing:0.3px;display:flex;align-items:center;gap:10px;">
                            <span style="font-size:22px;">✅</span> Email Test Thành Công!
                        </h2>
                    </div>
                    <div style="padding:22px;">
                        <p style="margin:0 0 12px 0;font-size:15px;line-height:1.6;color:#1f2937;">
                            Đây là email test từ hệ thống <strong style="color:#0f766e;">AI Detection Dashboard</strong>.
                        </p>
                        <p style="margin:0 0 12px 0;font-size:15px;line-height:1.6;color:#1f2937;">
                            Nếu bạn nhận được email này, có nghĩa là:
                        </p>
                        <div style="margin:0 0 16px 0;padding:14px 16px;background:#e0f2fe;border:1px solid #bae6fd;border-radius:10px;color:#0f172a;">
                            <ul style="margin:0;padding-left:20px;font-size:15px;line-height:1.6;list-style:none;">
                                <li style="margin-bottom:6px;">✅ SMTP đã cấu hình đúng.</li>
                                <li style="margin-bottom:6px;">✅ Email có thể gửi thành công.</li>
                                <li style="margin-bottom:0;">✅ Hệ thống cảnh báo email sẵn sàng.</li>
                            </ul>
                        </div>
                        <div style="margin:0 0 16px 0;padding:14px 16px;background:#fff7e6;border:1px solid #fde68a;border-radius:10px;color:#92400e;font-size:14px;line-height:1.6;">
                            <strong>Lưu ý:</strong><br>
                            Email cảnh báo sẽ được gửi tự động khi có detection trong vùng ROI đã cấu hình.
                        </div>
                        <p style="margin:0;font-size:13px;line-height:1.6;color:#6b7280;text-align:center;padding-top:6px;">
                            Đây là email tự động từ hệ thống AI Detection Dashboard<br>
                            Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                        </p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)

        return jsonify({'message': f'Đã gửi email test đến {receiver}'}), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        if session:
            try:
                session.close()
            except:
                pass

@app.route('/api/detections/stats', methods=['GET'])
def get_detection_stats():
    """Get detection statistics"""
    try:
        session = Session()

        # Get query parameters for filtering
        client_id = request.args.get('client_id')
        client_name = request.args.get('client_name')

        # Base query
        base_query = session.query(Detection)

        if client_id:
            base_query = base_query.filter(
                Detection.client_id == int(client_id))
        elif client_name:
            base_query = base_query.join(Client).filter(
                Client.name == client_name)

        # Get total count
        total_detections = base_query.count()

        # Get detections by class
        class_counts = {}
        results = base_query.with_entities(Detection.class_name).all()
        for (class_name,) in results:
            class_counts[class_name] = class_counts.get(class_name, 0) + 1

        # Get recent detections (last 24 hours)
        from datetime import timedelta
        yesterday = datetime.now() - timedelta(days=1)
        recent_detections = base_query.filter(
            Detection.timestamp >= yesterday).count()

        # Get client statistics
        client_stats = {}
        client_results = session.query(Client).all()
        for client in client_results:
            client_detections = session.query(Detection).filter(
                Detection.client_id == client.id).count()
            client_stats[client.name] = {
                'id': client.id,
                'detections': client_detections,
                'latitude': client.latitude,
                'longitude': client.longitude,
                'is_detect_enabled': client.is_detect_enabled,
                'last_seen': client.updated_at.isoformat() if client.updated_at else None
            }
        active_clients = session.query(Client).filter(
            Client.is_detect_enabled == True).count()

        session.close()

        return jsonify({
            'total_detections': total_detections,
            'recent_detections': recent_detections,
            'detections_by_class': class_counts,
            'clients': client_stats,
            'active_clients': active_clients
        })

    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500


@app.route('/api/images/<path:filename>', methods=['GET'])
def get_image(filename):
    """Serve captured images"""
    try:
        image_path = os.path.join(config.SERVER_IMAGES_DIR, filename)
        if os.path.exists(image_path):
            response = send_file(image_path, mimetype='image/jpeg')
            # CORS headers cho images
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET'
            return response
        else:
            return jsonify({'error': 'Image not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/video/frame', methods=['POST'])
def receive_video_frame():
    """Nhận video frame từ Pi client (raw hoặc processed) - Tối ưu với cache"""
    # Bỏ log để giảm overhead, chỉ log khi có lỗi
    try:
        # Lấy client info từ request - ưu tiên Serial number, fallback về client_name (backward compatibility)
        serial_number = request.form.get('serial_number')
        client_name = request.form.get('client_name')  # Backward compatibility
        frame_type = request.form.get('frame_type', 'raw')  # 'raw' hoặc 'processed'
        
        if not serial_number and not client_name:
            return jsonify({'error': 'serial_number or client_name is required'}), 400
        
        # Lấy frame image
        if 'frame' not in request.files:
            return jsonify({'error': 'No frame file provided'}), 400
        
        frame_file = request.files['frame']
        
        # Tối ưu: Tìm client trong cache trước (tránh query database mỗi request)
        # TTL Cache: Check cache expiration trước khi dùng
        cache_key = serial_number if serial_number else client_name
        client_id = None
        import time
        
        with client_cache_lock:
            if cache_key in client_cache:
                cache_entry = client_cache[cache_key]
                # Check TTL: Nếu cache expired, xóa và query lại từ DB
                current_time = time.time()
                if 'timestamp' in cache_entry and (current_time - cache_entry['timestamp']) < CACHE_TTL:
                    # Cache còn valid
                    client_id = cache_entry['id']
                    cache_entry['needs_db_update'] = True
                    cache_entry['last_updated'] = datetime.now()
                    cache_entry['timestamp'] = current_time  # Refresh timestamp
                else:
                    # Cache expired, xóa và query lại
                    del client_cache[cache_key]
                    cache_entry = None
            
            if cache_key not in client_cache:
                # Cache miss - query database
                session = Session()
                try:
                    if serial_number:
                        client = session.query(Client).filter(Client.serial_number == serial_number).first()
                    elif client_name:
                        client = session.query(Client).filter(Client.name == client_name).first()
                    else:
                        client = None
                    
                    if not client:
                        session.close()
                        return jsonify({'error': 'Client not found'}), 404
                    
                    client_id = client.id
                    # Thêm vào cache với timestamp cho TTL
                    client_cache[cache_key] = {
                        'id': client_id,
                        'last_updated': datetime.now(),
                        'timestamp': time.time(),  # Thêm timestamp cho TTL check
                        'needs_db_update': True
                    }
                finally:
                    session.close()
        
        # Tối ưu: Thêm vào queue để update database async (không block request)
        if client_id:
            with client_update_lock:
                client_update_queue.append({
                    'client_id': client_id,
                    'timestamp': datetime.now()
                })
                # Trigger update nếu queue đầy hoặc đã lâu
                if len(client_update_queue) >= 10:
                    _batch_update_clients_async()
        
        # Lưu frame vào memory
        frame_bytes = frame_file.read()
        
        # Tối ưu: Lưu frame nhanh nhất có thể (giảm lock time)
        current_time = datetime.now()
        if frame_type == 'processed':
            # Tối ưu: Chỉ lock khi cần, update nhanh
            with processed_frames_lock:
                processed_video_frames[client_id] = {
                    'frame': frame_bytes,  # Giữ nguyên bytes, không copy
                    'timestamp': current_time
                }
        else:
            with video_frames_lock:
                video_frames[client_id] = {
                    'frame': frame_bytes,  # Giữ nguyên bytes, không copy
                    'timestamp': current_time
                }
        
        return jsonify({'message': 'Frame received', 'frame_type': frame_type, 'client_id': client_id}), 200
        
    except ClientDisconnected:
        # Client đã ngắt kết nối trước khi server đọc xong - không cần log error, chỉ bỏ qua
        # Đảm bảo session được đóng nếu có
        if session:
            try:
                session.close()
            except:
                pass
        # Return 200 để không làm client retry
        return jsonify({'message': 'Client disconnected'}), 200
        
    except Exception as e:
        import traceback
        print(f"POST /api/video/frame ERROR: {e}")
        traceback.print_exc()
        # Đảm bảo session được đóng nếu có exception
        if session:
            try:
                session.close()
            except:
                pass
        return jsonify({'error': str(e)}), 500


@app.route('/api/video/stream/<int:client_id>')
def video_stream(client_id):
    """MJPEG stream endpoint để hiển thị raw video trên web - Tối ưu cho mượt mà"""
    from flask import Response
    import time
    
    def generate():
        """Generator function để tạo MJPEG stream - Tối ưu performance"""
        last_frame_data = None
        
        while True:
            try:
                frame_data = None
                timestamp = None
                
                # Lấy frame nhanh nhất có thể (giảm lock time)
                with video_frames_lock:
                    if client_id in video_frames:
                        frame_info = video_frames[client_id]
                        frame_data = frame_info['frame']
                        timestamp = frame_info['timestamp']
                
                # Kiểm tra frame cũ (quá 5 giây thì dùng frame cũ)
                if frame_data:
                    age = (datetime.now() - timestamp).total_seconds()
                    if age < 5:
                        last_frame_data = frame_data
                    elif last_frame_data:
                        # Dùng frame cũ để tránh đen
                        frame_data = last_frame_data
                
                # Gửi frame
                if frame_data:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + 
                           frame_data + b'\r\n')
                elif last_frame_data:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + 
                           last_frame_data + b'\r\n')
                else:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n')
                    
            except Exception as e:
                # Nếu lỗi, vẫn gửi frame cũ nếu có
                if last_frame_data:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + 
                           last_frame_data + b'\r\n')
                else:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n')
            
            # Tối ưu FPS: Match với client (20 FPS) để tránh lag
            time.sleep(0.05)  # ~20 FPS (match với client để mượt mà)
    
    response = Response(generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
    # CORS headers cho video stream
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET'
    # Headers để Cloudflare không cache/buffer video stream (quan trọng!)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response.headers['X-Accel-Buffering'] = 'no'  # Tắt buffering cho Nginx
    response.headers['Connection'] = 'keep-alive'
    # Force HTTP/1.1 để tránh QUIC_PROTOCOL_ERROR với Cloudflare HTTP/3
    response.headers['Alt-Svc'] = 'clear'  # Disable HTTP/3 upgrade
    return response


@app.route('/api/video/stream/processed/record/<int:client_id>')
def processed_video_stream_for_record(client_id):
    """
    MJPEG stream endpoint đơn giản cho recording (không dùng multipart boundary).
    Stream JPEG frames liên tục để ffmpeg có thể đọc dễ dàng.
    """
    from flask import Response
    import time
    
    def generate():
        """Generator function để tạo stream JPEG frames liên tục cho recording"""
        while True:
            try:
                frame_data = None
                timestamp = None
                
                # Lấy frame nhanh nhất có thể
                with processed_frames_lock:
                    if client_id in processed_video_frames:
                        frame_info = processed_video_frames[client_id]
                        frame_data = frame_info['frame']
                        timestamp = frame_info['timestamp']
                
                # Chỉ gửi frame mới (dưới 10 giây - tăng từ 5 để tránh ngắt stream)
                if frame_data:
                    age = (datetime.now() - timestamp).total_seconds()
                    if age < 10:
                        yield frame_data
                    else:
                        # Nếu frame quá cũ, vẫn gửi frame cũ để tránh ngắt stream
                        # ffmpeg sẽ xử lý được frame cũ
                        yield frame_data
                        time.sleep(0.05)
                        continue
                else:
                    # Chưa có frame, đợi một chút rồi thử lại
                    # Không gửi gì để tránh làm hỏng stream
                    time.sleep(0.1)
                    continue
                    
            except Exception as e:
                print(f"Error in recording stream for client {client_id}: {e}")
                # Khi có lỗi, vẫn tiếp tục loop để không ngắt stream
                time.sleep(0.1)
                continue
            
            # Match với client framerate (~20 FPS)
            time.sleep(0.05)
    
    response = Response(generate(), mimetype='image/jpeg')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Connection'] = 'keep-alive'
    return response


@app.route('/api/video/stream/processed/<int:client_id>')
def processed_video_stream(client_id):
    """MJPEG stream endpoint để hiển thị processed video (có detection boxes) trên web"""
    from flask import Response
    import time
    
    def generate():
        """Generator function để tạo MJPEG stream từ processed frames - Tối ưu cho mượt mà"""
        last_frame_data = None
        last_frame_time = None
        
        while True:
            try:
                frame_data = None
                timestamp = None
                
                # Lấy frame nhanh nhất có thể (giảm lock time)
                with processed_frames_lock:
                    if client_id in processed_video_frames:
                        frame_info = processed_video_frames[client_id]
                        frame_data = frame_info['frame']
                        timestamp = frame_info['timestamp']
                
                # Kiểm tra frame cũ (quá 15 giây thì dùng frame cũ để tránh đen)
                if frame_data:
                    age = (datetime.now() - timestamp).total_seconds()
                    if age < 15:
                        last_frame_data = frame_data
                        last_frame_time = timestamp
                    elif last_frame_data:
                        # Dùng frame cũ nếu có, tránh màn hình đen
                        frame_data = last_frame_data
                
                # Gửi frame (luôn có frame để tránh đen)
                if frame_data:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + 
                           frame_data + b'\r\n')
                elif last_frame_data:
                    # Fallback: dùng frame cũ
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + 
                           last_frame_data + b'\r\n')
                else:
                    # Chưa có frame nào
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n')
                    
            except Exception as e:
                # Nếu lỗi, vẫn gửi frame cũ nếu có
                if last_frame_data:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + 
                           last_frame_data + b'\r\n')
                else:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n')
            
            # Tối ưu FPS: Match với client (12 FPS) để tránh lag
            time.sleep(0.083)  # ~12 FPS (match với client để mượt mà)
    
    response = Response(generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
    # CORS headers cho processed video stream
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET'
    # Headers để Cloudflare không cache/buffer video stream (quan trọng!)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response.headers['X-Accel-Buffering'] = 'no'  # Tắt buffering cho Nginx
    response.headers['Connection'] = 'keep-alive'
    # Force HTTP/1.1 để tránh QUIC_PROTOCOL_ERROR với Cloudflare HTTP/3
    response.headers['Alt-Svc'] = 'clear'  # Disable HTTP/3 upgrade
    return response


@app.route('/api/detections/<int:detection_id>', methods=['DELETE'])
def delete_detection(detection_id):
    """Xóa một detection"""
    try:
        session = Session()
        detection = session.query(Detection).filter(Detection.id == detection_id).first()
        
        if not detection:
            session.close()
            return jsonify({'error': 'Detection not found'}), 404
        
        # Xóa file ảnh nếu có
        if detection.image_path:
            try:
                image_path = os.path.join(config.SERVER_IMAGES_DIR, detection.image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception as e:
                print(f"Warning: Could not delete image file: {e}")
        
        session.delete(detection)
        session.commit()
        session.close()
        
        return jsonify({'message': 'Detection deleted successfully'}), 200
    except Exception as e:
        if 'session' in locals():
            session.rollback()
            session.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/detections/bulk-delete', methods=['DELETE'])
def bulk_delete_detections():
    """Xóa nhiều detections cùng lúc"""
    try:
        data = request.get_json()
        if not data or 'ids' not in data:
            return jsonify({'error': 'Missing ids in request body'}), 400
        
        detection_ids = data['ids']
        if not isinstance(detection_ids, list) or len(detection_ids) == 0:
            return jsonify({'error': 'Invalid ids format'}), 400
        
        session = Session()
        detections = session.query(Detection).filter(Detection.id.in_(detection_ids)).all()
        
        deleted_count = 0
        for detection in detections:
            # Xóa file ảnh nếu có
            if detection.image_path:
                try:
                    image_path = os.path.join(config.SERVER_IMAGES_DIR, detection.image_path)
                    if os.path.exists(image_path):
                        os.remove(image_path)
                except Exception as e:
                    print(f"Warning: Could not delete image file: {e}")
            
            session.delete(detection)
            deleted_count += 1
        
        session.commit()
        session.close()
        
        return jsonify({'message': f'Deleted {deleted_count} detection(s) successfully'}), 200
    except Exception as e:
        if 'session' in locals():
            session.rollback()
            session.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/detections/<int:detection_id>', methods=['GET'])
def get_detection(detection_id):
    """Get a specific detection by ID"""
    try:
        session = Session()
        detection = session.query(Detection).options(joinedload(
            Detection.client)).filter(Detection.id == detection_id).first()
        session.close()

        if detection:
            result = {
                'id': detection.id,
                'timestamp': detection.timestamp.isoformat(),
                'class_name': detection.class_name,
                'confidence': detection.confidence,
                'image_path': detection.image_path,
                'bbox_x': detection.bbox_x,
                'bbox_y': detection.bbox_y,
                'bbox_width': detection.bbox_width,
                'bbox_height': detection.bbox_height,
                'metadata': json.loads(detection.metadata_json) if detection.metadata_json else {}
            }

            # Add client information if available
            if detection.client:
                result['client'] = {
                    'id': detection.client.id,
                    'name': detection.client.name,
                    'latitude': detection.client.latitude,
                    'longitude': detection.client.longitude,
                    'is_detect_enabled': detection.client.is_detect_enabled
                }

            return jsonify(result)
        else:
            return jsonify({'error': 'Detection not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/clients', methods=['GET'])
def get_clients():
    """Get all clients"""
    session = None
    try:
        session = Session()
        clients_with_count = (
            session.query(Client, func.count(
                Detection.id).label('detection_count'))
            # outer để client không có detection vẫn ra 0
            .outerjoin(Detection, Detection.client_id == Client.id)
            # nhóm theo client
            .group_by(Client.id)
            .all()
        )

        result = []
        for client, count in clients_with_count:
            result.append({
                'id': client.id,
                'name': client.name,
                'serial_number': client.serial_number if hasattr(client, 'serial_number') else None,
                'latitude': client.latitude,
                'longitude': client.longitude,
                'is_detect_enabled': client.is_detect_enabled,
                'ip_address': client.ip_address,
                'show_roi_overlay': getattr(client, 'show_roi_overlay', True),
                # Fallback về 0 nếu None để khớp mặc định UI (chất lượng cao)
                'rtsp_subtype': getattr(client, 'rtsp_subtype', 0) if getattr(client, 'rtsp_subtype', None) is not None else 0,  # 0=chất lượng cao, 1=chất lượng thấp
                'created_at': client.created_at.isoformat() if client.created_at else None,
                'updated_at': client.updated_at.isoformat() if client.updated_at else None,
                'client_detections': count
            })

        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        if session:
            try:
                session.close()
            except:
                pass


@app.route('/api/clients', methods=['POST'])
def create_client():
    """Create a new client"""
    session = None
    try:
        data = request.get_json()
        print(f"📥 Creating client with data: {data}")

        if not data or 'serial_number' not in data:
            return jsonify({'error': 'Serial number is required'}), 400
        
        if not data.get('name'):
            return jsonify({'error': 'Client name is required'}), 400

        session = Session()

        # Check if Serial number already exists
        existing_serial = session.query(Client).filter(
            Client.serial_number == data['serial_number']).first()
        if existing_serial:
            return jsonify({'error': 'Serial number already exists'}), 409
        
        # Check if name already exists (optional, name can be changed)
        existing_name = session.query(Client).filter(
            Client.name == data['name']).first()
        if existing_name:
            return jsonify({'error': 'Client name already exists'}), 409

        client = Client(
            name=data['name'],
            serial_number=data['serial_number'],  # Serial number (required, unique)
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            is_detect_enabled=data.get('is_detect_enabled', True),
            show_roi_overlay=data.get('show_roi_overlay', True),
            ip_address=data.get('ip_address'),
            roi_x1=data.get('roi_x1'),
            roi_y1=data.get('roi_y1'),
            roi_x2=data.get('roi_x2'),
            roi_y2=data.get('roi_y2'),
            roi_regions=data.get('roi_regions')  # Multiple ROI regions (JSON string)
        )

        session.add(client)
        session.commit()
        client_id = client.id
        session.close()
        
        # Tối ưu: Thêm vào cache ngay sau khi tạo
        with client_cache_lock:
            if client.serial_number:
                client_cache[client.serial_number] = {
                    'id': client_id,
                    'last_updated': datetime.now(),
                    'needs_db_update': False
                }
            if client.name:
                client_cache[client.name] = {
                    'id': client_id,
                    'last_updated': datetime.now(),
                    'needs_db_update': False
                }
        
        if 'roi_regions' in data and data['roi_regions']:
            print(f"✅ Created client {client_id} with roi_regions: {data['roi_regions']}")
        else:
            print(f"✅ Created client {client_id} without ROI")
        
        return jsonify({'message': 'Client created successfully', 'id': client_id}), 201

    except Exception as e:
        import traceback
        print(f"❌ ERROR in create_client: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        if session:
            try:
                session.close()
            except:
                pass


@app.route('/api/clients/<int:client_id>', methods=['GET'])
def get_client(client_id):
    """get info of a client"""
    try:
        session = Session()
        client = session.query(Client).filter(Client.id == client_id).first()

        if not client:
            return jsonify({'error': 'Client not found'}), 404

        session.close()

        result = {
            "id": client.id,
            "name": client.name,
            "serial_number": client.serial_number if hasattr(client, 'serial_number') else None,
            "latitude": client.latitude,
            "longitude": client.longitude,
            "is_detect_enabled": client.is_detect_enabled,
            "show_roi_overlay": getattr(client, 'show_roi_overlay', True),
            "roi_x1": client.roi_x1,
            "roi_y1": client.roi_y1,
            "roi_x2": client.roi_x2,
            "roi_y2": client.roi_y2,
            "roi_regions": client.roi_regions,  # Multiple ROI regions
            "ip_address": client.ip_address,
            # Nếu chưa set (None), fallback về 0 (chất lượng cao) để khớp mặc định UI
            "rtsp_subtype": getattr(client, 'rtsp_subtype', 0) if getattr(client, 'rtsp_subtype', None) is not None else 0
        }
        return jsonify(result), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        if session:
            try:
                session.close()
            except:
                pass


@app.route('/api/clients/<int:client_id>/last-frame', methods=['GET'])
def get_frame(client_id):
    """get the last detected frame of a client"""
    try:
        session = Session()
        detection = session.query(Detection).filter(
            Detection.client_id == client_id).order_by(Detection.timestamp.desc()).first()

        session.close()
        result = {
            "image": detection.image_path
        }
        return jsonify(result), 200 
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clients/<int:client_id>/current-frame', methods=['GET'])
def get_current_frame(client_id):
    """Lấy frame hiện tại từ video stream đang chạy để làm nền vẽ ROI"""
    from flask import Response
    try:
        # Lấy frame từ processed_video_frames (frame hiện tại đang stream)
        with processed_frames_lock:
            if client_id in processed_video_frames:
                frame_data = processed_video_frames[client_id]['frame']
                timestamp = processed_video_frames[client_id]['timestamp']
                
                # Kiểm tra frame còn mới không (dưới 30 giây)
                age = (datetime.now() - timestamp).total_seconds()
                if age < 30:
                    # Trả về frame dạng JPEG
                    return Response(frame_data, mimetype='image/jpeg'), 200
        
        # Nếu không có frame hiện tại, lấy frame từ detection cuối cùng
        session = Session()
        detection = session.query(Detection).filter(
            Detection.client_id == client_id).order_by(Detection.timestamp.desc()).first()
        session.close()
        
        if detection:
            image_path = os.path.join(config.SERVER_IMAGES_DIR, detection.image_path)
            if os.path.exists(image_path):
                return send_file(image_path, mimetype='image/jpeg'), 200
        
        return jsonify({'error': 'No frame available'}), 404
            
    except Exception as e:
        print(f"Error getting current frame: {e}")
        return jsonify({'error': str(e)}), 500


def _get_client_safe_name(session, client_id: int) -> str:
    """Helper: lấy tên client và chuyển thành dạng an toàn cho tên thư mục."""
    client = session.query(Client).filter(Client.id == client_id).first()
    if not client:
        return f"client_{client_id}"
    name = client.name or f"client_{client_id}"
    # Chỉ giữ lại ký tự chữ, số, _ và -
    safe = re.sub(r'[^a-zA-Z0-9_-]+', '_', name)
    return safe or f"client_{client_id}"


def _build_record_path(client_id: int, video_index: int = 0) -> Path:
    """Tạo thư mục lưu record theo client + ngày, trả về full path file mp4.
    
    Args:
        client_id: ID của client
        video_index: Số thứ tự video (0, 1, 2, ...) để đánh số các video trong cùng một session
    """
    base = Path(config.VIDEO_RECORD_BASE_DIR)
    session = Session()
    try:
        safe_name = _get_client_safe_name(session, client_id)
    finally:
        session.close()

    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%H%M%S")
    folder = base / safe_name / date_str
    folder.mkdir(parents=True, exist_ok=True)
    
    # Format chuẩn: YYYYMMDD_HHMMSS_ClientName.mp4
    # Tất cả video đều dùng timestamp riêng khi được tạo để sort đúng thứ tự thời gian
    filename = f"{date_str}_{time_str}_{safe_name}.mp4"
    
    return folder / filename

def _split_recording_video(client_id: int):
    """Tự động chia video khi đạt 30 phút: dừng video hiện tại và bắt đầu video mới"""
    if client_id not in recording_processes:
        return
    
    recording_info = recording_processes[client_id]
    proc = recording_info.get('process')
    
    if proc is None or proc.poll() is not None:
        return
    
    # Dừng video hiện tại
    try:
        proc.stdin.write(b'q\n')
        proc.stdin.flush()
        proc.wait(timeout=5)
        print(f"✅ Đã đóng video {recording_info.get('video_index', 0)} cho client {client_id} (đạt 30 phút)")
    except Exception as e:
        print(f"⚠️ Lỗi khi đóng video cũ: {e}")
        try:
            proc.kill()
        except:
            pass
    
    # Tạo video mới
    video_index = recording_info.get('video_index', 0) + 1
    output_path = _build_record_path(client_id, video_index)
    stream_url = f"http://127.0.0.1:{config.SERVER_PORT}/api/video/stream/processed/record/{client_id}"
    
    cmd = [
        FFMPEG_PATH if FFMPEG_PATH else 'ffmpeg',
        '-y',
        '-f', 'mjpeg',
        '-r', '20',
        '-reconnect', '1',
        '-reconnect_at_eof', '1',
        '-reconnect_streamed', '1',
        '-reconnect_delay_max', '2',
        '-timeout', '5000000',
        '-i', stream_url,
        '-c:v', 'libx264',
        '-preset', 'veryfast',
        '-crf', '23',
        '-pix_fmt', 'yuv420p',
        '-r', '20',
        '-movflags', '+faststart',
        '-an',
        '-f', 'mp4',
        '-flush_packets', '1',
        '-avoid_negative_ts', 'make_zero',
        '-fflags', '+genpts',
        str(output_path)
    ]
    
    try:
        log_file = output_path.parent / f"{output_path.stem}_ffmpeg.log"
        with open(log_file, 'w') as log:
            new_proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
        
        # Cập nhật recording info với video mới
        recording_info['process'] = new_proc
        recording_info['start_time'] = datetime.now()
        recording_info['video_index'] = video_index
        recording_info['current_output_path'] = output_path
        
        print(f"✅ Đã bắt đầu video mới (số {video_index + 1}) cho client {client_id}: {output_path}")
    except Exception as e:
        print(f"❌ Lỗi khi tạo video mới cho client {client_id}: {e}")
        # Nếu không tạo được video mới, dừng recording
        recording_processes.pop(client_id, None)


@app.route('/api/recordings/start', methods=['POST'])
def start_recording():
    """
    Bắt đầu ghi video processed stream của 1 client xuống ổ đĩa.

    Request JSON:
      { "client_id": 1 }
    """
    # Kiểm tra ffmpeg trước khi bắt đầu
    if not FFMPEG_AVAILABLE:
        return jsonify({
            'error': 'ffmpeg không được tìm thấy trên server',
            'detail': 'Vui lòng cài đặt ffmpeg để sử dụng chức năng ghi video. Xem hướng dẫn trong console của server.'
        }), 500
    
    data = request.get_json() or {}
    client_id = data.get('client_id')
    if not client_id:
        return jsonify({'error': 'client_id is required'}), 400

    client_id = int(client_id)
    with recording_lock:
        # Kiểm tra xem đã có recording đang chạy chưa
        if client_id in recording_processes:
            existing_info = recording_processes[client_id]
            existing_proc = existing_info.get('process')
            if existing_proc is not None and existing_proc.poll() is None:
                return jsonify({'error': 'Recording already running for this client'}), 409

        # Bắt đầu recording session mới (video_index = 0)
        output_path = _build_record_path(client_id, video_index=0)
        stream_url = f"http://127.0.0.1:{config.SERVER_PORT}/api/video/stream/processed/record/{client_id}"

        cmd = [
            FFMPEG_PATH if FFMPEG_PATH else 'ffmpeg',
            '-y',
            '-f', 'mjpeg',
            '-r', '20',
            '-reconnect', '1',
            '-reconnect_at_eof', '1',
            '-reconnect_streamed', '1',
            '-reconnect_delay_max', '2',
            '-timeout', '5000000',
            '-i', stream_url,
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',
            '-r', '20',
            '-movflags', '+faststart',
            '-an',
            '-f', 'mp4',
            '-flush_packets', '1',
            '-avoid_negative_ts', 'make_zero',
            '-fflags', '+genpts',
            str(output_path)
        ]

        try:
            log_file = output_path.parent / f"{output_path.stem}_ffmpeg.log"
            with open(log_file, 'w') as log:
                proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
            
            # Lưu thông tin recording với cấu trúc mới
            recording_processes[client_id] = {
                'process': proc,
                'start_time': datetime.now(),
                'video_index': 0,
                'current_output_path': output_path
            }
            
            print(f"✅ Started recording session for client {client_id}: {output_path}")
            return jsonify({'message': 'Recording started', 'file_path': str(output_path)}), 200
        except FileNotFoundError:
            return jsonify({
                'error': 'ffmpeg không được tìm thấy trên server',
                'detail': 'Vui lòng cài đặt ffmpeg để sử dụng chức năng ghi video.'
            }), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@app.route('/api/recordings/stop', methods=['POST'])
def stop_recording():
    """
    Dừng ghi video cho 1 client.

    Request JSON:
      { "client_id": 1 }
    """
    data = request.get_json() or {}
    client_id = data.get('client_id')
    if not client_id:
        return jsonify({'error': 'client_id is required'}), 400

    client_id = int(client_id)
    with recording_lock:
        recording_info = recording_processes.get(client_id)
        if not recording_info:
            return jsonify({'error': 'No active recording for this client'}), 404
        
        proc = recording_info.get('process')
        if not proc or proc.poll() is not None:
            # Process đã dừng rồi, chỉ cleanup
            recording_processes.pop(client_id, None)
            return jsonify({'message': 'Recording already stopped'}), 200
        
        # Dừng ffmpeg một cách graceful để file được finalize đúng
        try:
            # Gửi 'q' qua stdin để ffmpeg quit gracefully và finalize file cuối cùng
            try:
                proc.stdin.write(b'q\n')
                proc.stdin.flush()
            except (BrokenPipeError, OSError):
                # stdin có thể đã đóng, thử terminate
                proc.terminate()
            
            # Đợi tối đa 10 giây để ffmpeg finalize file
            try:
                proc.wait(timeout=10)
                video_index = recording_info.get('video_index', 0)
                print(f"✅ Recording stopped gracefully for client {client_id} (đã ghi {video_index + 1} video(s))")
            except subprocess.TimeoutExpired:
                # Nếu quá 10 giây, force kill (nhưng file có thể bị hỏng)
                print(f"⚠️ Recording process did not stop, forcing kill for client {client_id}")
                proc.kill()
                proc.wait()
                print(f"⚠️ File may be corrupted due to forced kill")
        except Exception as e:
            print(f"⚠️ Error stopping recording for client {client_id}: {e}")
            try:
                if proc:
                    proc.kill()
            except:
                pass
        
        # Xóa recording session
        recording_processes.pop(client_id, None)

    return jsonify({'message': 'Recording stopped'}), 200


@app.route('/api/recordings/status/<int:client_id>', methods=['GET'])
def get_recording_status(client_id):
    """Kiểm tra trạng thái recording của 1 client."""
    with recording_lock:
        recording_info = recording_processes.get(client_id)
        if recording_info:
            proc = recording_info.get('process')
            is_recording = proc is not None and proc.poll() is None
            video_index = recording_info.get('video_index', 0)
            start_time = recording_info.get('start_time')
            elapsed_minutes = 0
            if start_time:
                elapsed_minutes = (datetime.now() - start_time).total_seconds() / 60
        else:
            is_recording = False
            video_index = 0
            elapsed_minutes = 0
    
    return jsonify({
        'is_recording': is_recording,
        'client_id': client_id,
        'video_index': video_index,  # Số video hiện tại (0-based)
        'video_count': video_index + 1,  # Tổng số video đã ghi
        'elapsed_minutes': round(elapsed_minutes, 1) if is_recording else 0
    }), 200


@app.route('/api/recordings/<int:client_id>', methods=['GET'])
def list_recordings(client_id):
    """Liệt kê các file record của 1 client."""
    base = Path(config.VIDEO_RECORD_BASE_DIR)
    session = Session()
    try:
        safe_name = _get_client_safe_name(session, client_id)
    finally:
        session.close()

    client_dir = base / safe_name
    results = []
    if client_dir.exists():
        for day_dir in sorted(client_dir.iterdir()):
            if not day_dir.is_dir():
                continue
            for f in sorted(day_dir.glob("*.mp4")):
                rel_path = f.relative_to(base)
                # Lấy thông tin file
                try:
                    file_size = f.stat().st_size
                    file_mtime = f.stat().st_mtime
                except Exception:
                    file_size = 0
                    file_mtime = 0
                
                results.append({
                    'filename': f.name,
                    'date_folder': day_dir.name,
                    'path': str(rel_path).replace('\\', '/'),
                    'url': f"/api/recordings/file/{client_id}/{day_dir.name}/{f.name}",
                    'size': file_size,  # bytes
                    'size_mb': round(file_size / (1024 * 1024), 2) if file_size > 0 else 0,
                    'modified': file_mtime
                })

    return jsonify(results), 200


@app.route('/api/recordings/file/<int:client_id>/<string:date_folder>/<path:filename>', methods=['DELETE'])
def delete_recording_file(client_id, date_folder, filename):
    """Xóa file video đã ghi."""
    from pathlib import Path
    import os
    
    base = Path(config.VIDEO_RECORD_BASE_DIR)
    session = Session()
    try:
        safe_name = _get_client_safe_name(session, client_id)
    finally:
        session.close()

    file_path = base / safe_name / date_folder / filename

    # Đảm bảo file nằm trong VIDEO_RECORD_BASE_DIR (tránh path traversal)
    try:
        file_path.resolve().relative_to(base.resolve())
    except Exception:
        return jsonify({'error': 'Invalid file path'}), 400

    if not file_path.exists():
        return jsonify({'error': 'File not found'}), 404
    
    # Kiểm tra xem file có đang được ghi không
    if client_id in recording_processes:
        recording_info = recording_processes[client_id]
        proc = recording_info.get('process')
        is_recording = proc is not None and proc.poll() is None
        if is_recording:
            # Kiểm tra xem file này có phải là file đang được ghi không
            current_output_path = recording_info.get('current_output_path')
            if current_output_path and str(current_output_path) == str(file_path):
                return jsonify({'error': 'Cannot delete file that is currently being recorded'}), 400
    
    try:
        # Xóa file
        os.remove(file_path)
        return jsonify({'message': 'File deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to delete file: {str(e)}'}), 500


@app.route('/api/recordings/file/<int:client_id>/<string:date_folder>/<path:filename>', methods=['GET'])
def get_recording_file(client_id, date_folder, filename):
    """Trả về file video mp4 đã ghi cho playback."""
    from flask import Response
    import os
    
    base = Path(config.VIDEO_RECORD_BASE_DIR)
    session = Session()
    try:
        safe_name = _get_client_safe_name(session, client_id)
    finally:
        session.close()

    file_path = base / safe_name / date_folder / filename

    # Đảm bảo file nằm trong VIDEO_RECORD_BASE_DIR (tránh path traversal)
    try:
        file_path.resolve().relative_to(base.resolve())
    except Exception:
        return jsonify({'error': 'Invalid file path'}), 400

    if not file_path.exists():
        return jsonify({'error': 'File not found'}), 404
    
    # Kiểm tra file size và trạng thái recording
    try:
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return jsonify({'error': 'Video file is empty or still being recorded'}), 400
        
        # Kiểm tra xem có đang ghi video này không
        with recording_lock:
            recording_info = recording_processes.get(client_id)
            if recording_info:
                proc = recording_info.get('process')
                is_recording = proc is not None and proc.poll() is None
            else:
                is_recording = False
        
        # Nếu đang ghi, file có thể chưa hoàn chỉnh
        if is_recording:
            # Cho phép phát nhưng cảnh báo rằng file đang được ghi
            pass  # Vẫn cho phép phát, nhưng có thể không hoàn chỉnh
    except OSError as e:
        return jsonify({'error': f'Cannot access video file: {str(e)}'}), 500
    
    # Hỗ trợ Range requests cho video streaming (quan trọng!)
    range_header = request.headers.get('Range', None)
    if range_header:
        # Parse range header
        byte_start = 0
        byte_end = file_size - 1
        
        range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
        if range_match:
            byte_start = int(range_match.group(1))
            if range_match.group(2):
                byte_end = int(range_match.group(2))
        
        # Đảm bảo range hợp lệ
        byte_start = max(0, byte_start)
        byte_end = min(file_size - 1, byte_end)
        content_length = byte_end - byte_start + 1
        
        # Đọc phần file được yêu cầu
        with open(file_path, 'rb') as f:
            f.seek(byte_start)
            data = f.read(content_length)
        
        response = Response(data, 206, mimetype='video/mp4', direct_passthrough=True)
        response.headers.add('Content-Range', f'bytes {byte_start}-{byte_end}/{file_size}')
        response.headers.add('Accept-Ranges', 'bytes')
        response.headers.add('Content-Length', str(content_length))
    else:
        # Trả về toàn bộ file nếu không có range request
        response = send_file(str(file_path), mimetype='video/mp4')
        response.headers.add('Accept-Ranges', 'bytes')
        response.headers.add('Content-Length', str(file_size))
    
    # CORS headers
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, HEAD, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Range'
    # Cache headers
    response.headers['Cache-Control'] = 'public, max-age=3600'
    
    return response

@app.route('/api/clients/by-serial/<string:serial_number>', methods=['GET'])
def get_client_by_serial(serial_number):
    """Get client info by Serial number (for clients identification)"""
    session = None
    try:
        session = Session()
        client = session.query(Client).filter(
            Client.serial_number == serial_number).first()

        if not client:
            return jsonify({'error': 'Client with this Serial number not found'}), 404

        result = {
            "id": client.id,
            "name": client.name,
            "serial_number": client.serial_number,
            "latitude": client.latitude,
            "longitude": client.longitude,
            "is_detect_enabled": client.is_detect_enabled,
            "show_roi_overlay": getattr(client, 'show_roi_overlay', True),
            "roi_x1": client.roi_x1,
            "roi_y1": client.roi_y1,
            "roi_x2": client.roi_x2,
            "roi_y2": client.roi_y2,
            "roi_regions": client.roi_regions,  # Multiple ROI regions
            "ip_address": client.ip_address,
            # Fallback về 0 (chất lượng cao) nếu chưa có trong DB
            "rtsp_subtype": getattr(client, 'rtsp_subtype', 0) if getattr(client, 'rtsp_subtype', None) is not None else 0
        }
        return jsonify(result), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        if session:
            try:
                session.close()
            except:
                pass

@app.route('/api/clients/by-name/<string:client_name>', methods=['GET'])
def get_client_by_name(client_name):
    """Get client info by name (backward compatibility)"""
    session = None
    try:
        session = Session()
        client = session.query(Client).filter(
            Client.name == client_name).first()

        if not client:
            return jsonify({'error': 'Client not found'}), 404

        result = {
            "id": client.id,
            "name": client.name,
            "serial_number": client.serial_number if hasattr(client, 'serial_number') else None,
            "latitude": client.latitude,
            "longitude": client.longitude,
            "is_detect_enabled": client.is_detect_enabled,
            "show_roi_overlay": getattr(client, 'show_roi_overlay', True),
            "roi_x1": client.roi_x1,
            "roi_y1": client.roi_y1,
            "roi_x2": client.roi_x2,
            "roi_y2": client.roi_y2,
            "roi_regions": client.roi_regions,  # Multiple ROI regions
            "ip_address": client.ip_address
        }
        return jsonify(result), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        if session:
            try:
                session.close()
            except:
                pass


@app.route('/api/clients/<int:client_id>', methods=['PUT'])
def update_client(client_id):
    """Update a client"""
    session = None
    try:
        data = request.get_json()
        print(f"📥 Updating client {client_id} with data: {data}")

        session = Session()
        client = session.query(Client).filter(Client.id == client_id).first()

        if not client:
            return jsonify({'error': 'Client not found'}), 404

        # Update fields
        # Serial number cannot be changed (read-only after creation)
        if 'serial_number' in data:
            # Only allow update if serial_number is None (for migration)
            if client.serial_number is None:
                # Check if new serial_number already exists
                existing_serial = session.query(Client).filter(
                    Client.serial_number == data['serial_number'], Client.id != client_id).first()
                if existing_serial:
                    return jsonify({'error': 'Serial number already exists'}), 409
                client.serial_number = data['serial_number']
            elif client.serial_number != data['serial_number']:
                return jsonify({'error': 'Serial number cannot be changed'}), 400
        
        if 'name' in data:
            # Check if new name conflicts with existing client
            existing_client = session.query(Client).filter(
                Client.name == data['name'], Client.id != client_id).first()
            if existing_client:
                return jsonify({'error': 'Client with this name already exists'}), 409
            client.name = data['name']

        if 'latitude' in data:
            client.latitude = data['latitude']
        if 'longitude' in data:
            client.longitude = data['longitude']
        if 'is_detect_enabled' in data:
            client.is_detect_enabled = data['is_detect_enabled']
        if 'show_roi_overlay' in data:
            client.show_roi_overlay = data.get('show_roi_overlay', True)
        if 'ip_address' in data:
            client.ip_address = data['ip_address']
        if 'roi_x1' in data:
            client.roi_x1 = data['roi_x1']
        if 'roi_x2' in data:
            client.roi_x2 = data['roi_x2']
        if 'roi_y1' in data:
            client.roi_y1 = data['roi_y1']
        if 'roi_y2' in data:
            client.roi_y2 = data['roi_y2']
        # Always update roi_regions (even if null) to clear old ROI
        if 'roi_regions' in data:
            client.roi_regions = data['roi_regions']  # Multiple ROI regions
            if data['roi_regions']:
                print(f"✅ Updated roi_regions for client {client_id}: {data['roi_regions']}")
            else:
                print(f"✅ Cleared roi_regions for client {client_id}")
        if 'rtsp_subtype' in data:
            rtsp_subtype = int(data['rtsp_subtype'])
            if rtsp_subtype not in [0, 1]:
                return jsonify({'error': 'rtsp_subtype must be 0 (chất lượng cao) or 1 (chất lượng thấp)'}), 400
            client.rtsp_subtype = rtsp_subtype
            print(f"✅ Updated rtsp_subtype for client {client_id}: {rtsp_subtype} ({'chất lượng cao' if rtsp_subtype == 0 else 'chất lượng thấp'})")

        # Lưu old values để invalidate cache
        old_serial = client.serial_number
        old_name = client.name

        session.commit()
        print(f"✅ Client {client_id} updated successfully")
        
        # Tối ưu: Invalidate cache và update cache với giá trị mới
        _invalidate_client_cache(serial_number=old_serial, client_name=old_name, client_id=client_id)
        with client_cache_lock:
            if client.serial_number:
                client_cache[client.serial_number] = {
                    'id': client_id,
                    'last_updated': datetime.now(),
                    'needs_db_update': False
                }
            if client.name:
                client_cache[client.name] = {
                    'id': client_id,
                    'last_updated': datetime.now(),
                    'needs_db_update': False
                }

        return jsonify({'message': 'Client updated successfully'}), 200

    except Exception as e:
        import traceback
        print(f"❌ ERROR in update_client: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        if session:
            try:
                session.close()
            except:
                pass


@app.route('/api/clients/<int:client_id>', methods=['DELETE'])
def delete_client(client_id):
    """Delete a client"""
    try:
        session = Session()
        client = session.query(Client).filter(Client.id == client_id).first()

        if not client:
            session.close()
            return jsonify({'error': 'Client not found'}), 404

        # Lưu thông tin để invalidate cache
        old_serial = client.serial_number
        old_name = client.name

        session.delete(client)
        session.commit()
        session.close()
        
        # Tối ưu: Invalidate cache khi xóa client
        _invalidate_client_cache(serial_number=old_serial, client_name=old_name, client_id=client_id)

        return jsonify({'message': 'Client deleted successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("Starting Object Detection Server...")
    print(
        f"Server will be available at http://{config.SERVER_HOST}:{config.SERVER_PORT}")
    print(f"Images will be stored in: {config.SERVER_IMAGES_DIR}")
    
    # Hiển thị trạng thái Telegram Bot
    if config.TELEGRAM_BOT_TOKEN:
        print(f"✅ Telegram Bot đã được cấu hình (Token: {config.TELEGRAM_BOT_TOKEN[:10]}...)")
        if config.TELEGRAM_CHAT_ID:
            print(f"✅ Telegram Chat ID: {config.TELEGRAM_CHAT_ID}")
            if config.TELEGRAM_ENABLED:
                print("✅ Cảnh báo Telegram: ĐANG BẬT")
            else:
                print("⚠️  Cảnh báo Telegram: ĐANG TẮT")
        else:
            print("⚠️  TELEGRAM_CHAT_ID chưa được cấu hình")
    else:
        print("⚠️  TELEGRAM_BOT_TOKEN chưa được cấu hình")
    
    app.run(host=config.SERVER_HOST, port=config.SERVER_PORT, debug=True, threaded=True)
