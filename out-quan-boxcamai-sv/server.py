import config as config
from database_setup import Detection, Client, AlertSettings, init_database, get_session
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy import func
from datetime import datetime
import json
import os
from flask_cors import CORS
from flask import Flask, request, jsonify, send_file, render_template
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
import threading
sys.path.insert(0, '..')


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

        # Gửi email cảnh báo nếu có cấu hình email
        if detection_id and client_id:
            send_alert_email_async(detection_id, client_id)

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
                'email_enabled': False
            }), 200
        
        return jsonify({
            'alert_email': settings.alert_email,
            'email_enabled': settings.email_enabled
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
        
        settings.updated_at = datetime.now()
        session.commit()
        session.close()
        
        return jsonify({'message': 'Alert settings updated successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
    """Nhận video frame từ Pi client (raw hoặc processed)"""
    # Bỏ log để giảm overhead, chỉ log khi có lỗi
    session = None
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
        
        # Tìm client trong database và cập nhật updated_at để track online status
        session = Session()
        try:
            if serial_number:
                # Tìm bằng Serial number (mới)
                client = session.query(Client).filter(Client.serial_number == serial_number).first()
            elif client_name:
                # Tìm bằng name (backward compatibility)
                client = session.query(Client).filter(Client.name == client_name).first()
            else:
                client = None
            
            if not client:
                session.close()
                return jsonify({'error': 'Client not found'}), 404
            
            # Cập nhật updated_at để track online status khi nhận video frame
            client.updated_at = datetime.now()
            session.commit()
            client_id = client.id
        finally:
            session.close()
            session = None
        
        # Lưu frame vào memory
        frame_bytes = frame_file.read()
        
        # Lưu frame vào đúng dictionary dựa trên frame_type (tối ưu: không copy, dùng trực tiếp)
        current_time = datetime.now()
        if frame_type == 'processed':
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

        session.commit()
        print(f"✅ Client {client_id} updated successfully")

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

        session.delete(client)
        session.commit()
        session.close()

        return jsonify({'message': 'Client deleted successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("Starting Object Detection Server...")
    print(
        f"Server will be available at http://{config.SERVER_HOST}:{config.SERVER_PORT}")
    print(f"Images will be stored in: {config.SERVER_IMAGES_DIR}")
    app.run(host=config.SERVER_HOST, port=config.SERVER_PORT, debug=True, threaded=True)
