import os

# Server Configuration
SERVER_HOST = 'boxcamai.cloud'
SERVER_PORT = 443
SERVER_URL = f"https://{SERVER_HOST}:{SERVER_PORT}/api/detections"

# Database Configuration
# DATABASE_URL = 'sqlite:///server/detections.db' # no need the db in client

# Image Storage Configuration
IMAGES_DIR = os.path.join(os.path.dirname(__file__), 'captured_images')
MAX_IMAGES_PER_DETECTION = 5  # Maximum images to keep per detection class

# Detection Configuration
DETECTION_THRESHOLD = 0.22
IOU_THRESHOLD = 0.3
# FRAME_SKIP: Bỏ qua N frames giữa các lần detection để tăng performance
# Với input 640x640, nên tăng FRAME_SKIP để giảm tải cho Pi
# FRAME_SKIP = 1: Detect mọi frame (chậm nhất, chính xác nhất)
# FRAME_SKIP = 2: Detect mỗi 2 frames (nhanh hơn 2x)
# FRAME_SKIP = 3: Detect mỗi 3 frames (nhanh hơn 3x)
FRAME_SKIP = 1  # Detect mọi frame để chính xác nhất
TIME_BETWEEN_SEND = 2.0

# ONNX Runtime threading (điều khiển số core logic)
# 3 thread ~ dùng khoảng 3 core, mượt hơn nhưng nặng hơn 2 core
ONNX_INTRA_THREADS = 3  # Số thread xử lý trong 1 operation (tương đương ~3 core)
ONNX_INTER_THREADS = 1  # Số thread giữa các operations (thường để 1 là đủ)

# Camera Configuration
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
# CAMERA_FRAMERATE: Tăng framerate để video mượt hơn
# 20 fps: Mượt và cân bằng tốt
# 25 fps: Rất mượt nhưng nặng hơn
CAMERA_FRAMERATE = 20  # Tăng lên 20 FPS để video mượt hơn

# Video File Configuration (set to None to use camera, or provide path to local video file)
VIDEO_FILE_PATH = None # e.g., 'path/to/video.mp4'
# VIDEO_FILE_PATH = './videotest/video-test-2.mp4' # e.g., 'path/to/video.mp4'

# RTSP Configuration
RTSP_USER = 'admin'
RTSP_PASS = 'quan2004'
RTSP_IP = None  # Fallback IP nếu không có IP từ server (ưu tiên IP từ server)
RTSP_PORT = '554'
# RTSP_URL không còn dùng nữa (đã build link động từ IP)
# IP camera sẽ được lấy từ server hoặc config.RTSP_IP
# Model Configuration
# MODEL_PATH = 'yolov5s.onnx'
MODEL_PATH = 'best.onnx'  # Dùng model custom với 11 classes
# Model best.onnx yêu cầu input size 640x640
INPUT_W_SIZE = 640
INPUT_H_SIZE = 640

# Class names for the model
# CLASS_NAMES: COCO dataset (80 classes) - dùng cho model mặc định
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

# CLASS_NAMES2: Custom model với 11 classes (dùng cho best.onnx)
# Thứ tự: tree, drone, truck, motorcycle, crane, livestock, pole, fire, smoke, kite, person
CLASS_NAMES2 = ['tree', 'drone', 'truck', 'motorcycle', 'crane', 'livestock', 'pole', 'fire', 'smoke', 'kite', 'person']
# Create directories if they don't exist
os.makedirs(IMAGES_DIR, exist_ok=True)

# Client Configuration (for identification when sending to server)
CLIENT_NAME = 'raspberry_pi_1'  # Unique name for this client
CLIENT_LATITUDE = None  # GPS latitude (optional)
CLIENT_LONGITUDE = None  # GPS longitude (optional)

# Server polling configuration (kiểm tra thay đổi từ server)
POLL_INTERVAL = 2          # Kiểm tra mỗi 2 giây
POLL_MAX_CHECKS = 0        # 0 = chạy liên tục (không giới hạn số lần kiểm tra)
ENABLE_AUTO_RESTART = True  # Tự động restart khi có thay đổi IP/ROI/subtype