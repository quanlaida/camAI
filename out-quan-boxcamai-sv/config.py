import os
from datetime import datetime

# Load environment variables from .env file (if exists)
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load biến môi trường từ file .env
except ImportError:
    # Nếu chưa cài python-dotenv, bỏ qua (vẫn dùng được environment variables)
    pass

# Server Configuration
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 5000
SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}/detect"

# Database Configuration
DATABASE_URL = 'sqlite:///detections.db'

# Image Storage Configuration
IMAGES_DIR = 'captured_images'  # Client images
SERVER_IMAGES_DIR = os.path.join(os.path.dirname(__file__), 'captured_images')  # Server images
MAX_IMAGES_PER_DETECTION = 5  # Maximum images to keep per detection class

# Video Recording Configuration
# Thư mục gốc lưu các file video record (server side)
VIDEO_RECORD_BASE_DIR = os.path.join(os.path.dirname(__file__), 'recordings')

# Email Alert Configuration (Gmail SMTP)
ALERT_EMAIL_SENDER = os.getenv('ALERT_EMAIL_SENDER', '')  # Email gửi đi (ví dụ: your-email@gmail.com)
ALERT_EMAIL_PASSWORD = os.getenv('ALERT_EMAIL_PASSWORD', '')  # App Password từ Gmail (không phải mật khẩu thường)

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8536552488:AAGmQD-vjI9nP3jV4dli1ToNNdKhfcv5rXU')  # Bot token từ @BotFather
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '-5009640116')  # Chat ID của nhóm "Cảnh báo tự động"
TELEGRAM_ENABLED = os.getenv('TELEGRAM_ENABLED', 'true').lower() == 'true'  # Bật/tắt cảnh báo Telegram (mặc định: true)

# Detection Configuration
DETECTION_THRESHOLD = 0.35
IOU_THRESHOLD = 0.45
FRAME_SKIP = 5

# Objects to track (empty list means track all detected objects)
TRACKED_OBJECTS = ['person', 'car', 'truck', 'bus', 'motorbike']  # ['person', 'car', 'truck', 'bus', 'motorbike']

# Camera Configuration
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FRAMERATE = 30

# Video File Configuration (set to None to use camera, or provide path to local video file)
VIDEO_FILE_PATH = None # e.g., 'path/to/video.mp4'
# VIDEO_FILE_PATH = './videotest/video-test-2.mp4' # e.g., 'path/to/video.mp4'

# RTSP Configuration
RTSP_URL = "rtsp://admin:quan2004@192.168.1.102:554/cam/realmonitor?channel=1&subtype=1"
#go lai rtsv vao day la oke
# Model Configuration
# MODEL_PATH = 'yolov5s.onnx'
MODEL_PATH = 'best.onnx'
INPUT_W_SIZE =320
INPUT_H_SIZE = 320
INPUT_SIZE = 320

# Rate limiting configuration
DETECTION_SEND_DELAY = 1  # Delay in seconds between sending detections to server

# Tracking configuration
TRACK_TIMEOUT = 5  # Timeout in seconds for object reappearance to trigger send

# Class names for the model
CLASS_NAMES = [
    "person", "bicycle", "car", "motorbike", "aeroplane", "bus", "train", "truck",
    "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
    "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
    "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
    "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
    "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "sofa",
    "pottedplant", "bed", "diningtable", "toilet", "tvmonitor", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier",
    "toothbrush"
]

CLASS_NAMES2 = ['ambulance', 'bicycle', 'bird', 'bus', 'camel', 'car', 'cow', 'deer', 'drone', 'dump truck', 'excavators', 'goat', 'horse', 'motorcycle', 'person', 'sheep', 'truck', 'wheel loader']

# Create directories if they don't exist
# os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(SERVER_IMAGES_DIR, exist_ok=True)
