import cv2
import torch
import numpy as np
import argparse
from pathlib import Path
import sys

# Import config để lấy class names và các thông số
CLASS_NAMES = None
CLASS_NAMES2 = None
INPUT_SIZE = 320
DETECTION_THRESHOLD = 0.7
IOU_THRESHOLD = 0.3

try:
    sys.path.append('out-quan-boxcamai-client')
    import config
    CLASS_NAMES = config.CLASS_NAMES
    CLASS_NAMES2 = getattr(config, 'CLASS_NAMES2', None)  # Lấy CLASS_NAMES2 nếu có
    INPUT_SIZE = config.INPUT_SIZE
    DETECTION_THRESHOLD = config.DETECTION_THRESHOLD
    IOU_THRESHOLD = config.IOU_THRESHOLD
except:
    # Fallback nếu không import được config
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
    CLASS_NAMES2 = ['tree', 'drone', 'truck', 'motorcycle', 'crane', 'livestock', 'pole', 'fire', 'smoke', 'kite', 'person']
    INPUT_SIZE = 320
    DETECTION_THRESHOLD = 0.7
    IOU_THRESHOLD = 0.3

def get_model_class_names(model):
    """Lấy class names từ model nếu có"""
    class_names = None
    
    # Thử lấy từ YOLOv5 model
    try:
        if hasattr(model, 'names'):
            class_names = model.names
            if isinstance(class_names, dict):
                # Convert dict to list
                max_id = max(class_names.keys()) if class_names else -1
                names_list = [''] * (max_id + 1)
                for idx, name in class_names.items():
                    names_list[idx] = name
                class_names = names_list
            print(f"[INFO] Tim thay {len(class_names)} classes tu model: {class_names}")
            return class_names
    except:
        pass
    
    # Thử lấy từ model.module.names (nếu model được wrap)
    try:
        if hasattr(model, 'module') and hasattr(model.module, 'names'):
            class_names = model.module.names
            if isinstance(class_names, dict):
                max_id = max(class_names.keys()) if class_names else -1
                names_list = [''] * (max_id + 1)
                for idx, name in class_names.items():
                    names_list[idx] = name
                class_names = names_list
            print(f"[INFO] Tim thay {len(class_names)} classes tu model.module: {class_names}")
            return class_names
    except:
        pass
    
    return None

def non_max_suppression(boxes, scores, threshold):
    """Apply Non-Maximum Suppression to filter overlapping bounding boxes"""
    if len(boxes) == 0:
        return np.array([])

    boxes = np.array(boxes)
    scores = np.array(scores)

    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 0] + boxes[:, 2]
    y2 = boxes[:, 1] + boxes[:, 3]

    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)

        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h

        iou = inter / (areas[i] + areas[order[1:]] - inter)
        inds = np.where(iou <= threshold)[0]
        order = order[inds + 1]

    return np.array(keep)

def load_model(model_path):
    """Load PyTorch model từ file .pt"""
    # Ưu tiên dùng Ultralytics YOLO (phổ biến và dễ sử dụng)
    try:
        from ultralytics import YOLO
        print("[INFO] Dang thu load voi Ultralytics YOLO...")
        model = YOLO(model_path)
        print("[OK] Load model thanh cong voi Ultralytics YOLO!")
        return model
    except Exception as e1:
        print(f"[WARN] Khong the load voi Ultralytics: {e1}")
    
    # Thử với YOLOv5 (cần set weights_only=False)
    try:
        import yolov5
        print("[INFO] Dang thu load voi YOLOv5...")
        # YOLOv5 tự xử lý weights_only trong code của nó
        # Nhưng có thể cần patch torch.load
        import torch
        original_load = torch.load
        def patched_load(*args, **kwargs):
            kwargs['weights_only'] = False
            return original_load(*args, **kwargs)
        torch.load = patched_load
        
        model = yolov5.load(model_path, device='cpu')
        torch.load = original_load  # Restore
        print("[OK] Load model thanh cong voi YOLOv5!")
        return model
    except Exception as e2:
        print(f"[WARN] Khong the load voi YOLOv5: {e2}")
    
    # Thử load trực tiếp với torch.load (cho YOLOv5)
    try:
        print("[INFO] Dang thu load voi PyTorch truc tiep (YOLOv5 format)...")
        # Load với weights_only=False để hỗ trợ YOLOv5
        model = torch.load(model_path, map_location='cpu', weights_only=False)
        
        # Nếu là YOLOv5 model, có thể cần xử lý khác
        if isinstance(model, dict):
            # Nếu là state_dict
            if 'model' in model:
                model = model['model']
            elif 'state_dict' in model:
                print("[WARN] Model file chua state_dict, can model architecture")
                return None
        
        # Set model to eval mode
        if hasattr(model, 'eval'):
            model.eval()
        
        print("[OK] Load model thanh cong voi PyTorch (YOLOv5)!")
        return model
    except Exception as e3:
        print(f"[ERROR] Khong the load model voi bat ky phuong phap nao: {e3}")
        print("[INFO] Thu cai dat yolov5 package: py -m pip install yolov5")
        return None

def preprocess_image(image, input_size=320):
    """Preprocess ảnh để đưa vào model"""
    # Resize ảnh
    resized = cv2.resize(image, (input_size, input_size))
    
    # Convert BGR to RGB
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    
    # Normalize về [0, 1]
    normalized = rgb.astype(np.float32) / 255.0
    
    # Transpose to CHW format
    transposed = np.transpose(normalized, (2, 0, 1))
    
    # Add batch dimension
    tensor = np.expand_dims(transposed, axis=0)
    
    # Convert to torch tensor
    tensor = torch.from_numpy(tensor)
    
    return tensor, resized.shape[:2]

def detect_objects(model, image_tensor, original_shape, input_size=320, conf_threshold=0.7, iou_threshold=0.3):
    """Chạy detection trên ảnh"""
    with torch.no_grad():
        # Chạy inference
        outputs = model(image_tensor)
    
    # Xử lý output tùy theo format của model
    if isinstance(outputs, (list, tuple)):
        outputs = outputs[0]
    
    # Convert to numpy
    if isinstance(outputs, torch.Tensor):
        outputs = outputs.cpu().numpy()
    
    # YOLOv5 output format: [batch, num_anchors, 85] hoặc [num_anchors, 85]
    # 85 = 4 (bbox) + 1 (obj_conf) + 80 (classes) hoặc 4 + 1 + num_classes
    # Remove batch dimension nếu có
    if outputs.ndim == 3:
        outputs = outputs[0]  # [num_anchors, 85]
    
    # Scale từ input_size về original size
    scale_x = original_shape[1] / input_size
    scale_y = original_shape[0] / input_size
    
    # Parse detections
    boxes = []
    scores = []
    class_ids = []
    
    # YOLO format: [x_center, y_center, width, height, obj_conf, class_conf_1, class_conf_2, ...]
    # Hoặc có thể là normalized coordinates
    num_classes = outputs.shape[1] - 5  # Trừ đi 4 bbox + 1 obj_conf
    
    for pred in outputs:
        if len(pred) < 5:
            continue
            
        # Lấy bbox coordinates (có thể là normalized hoặc absolute)
        cx, cy, w, h = pred[0], pred[1], pred[2], pred[3]
        obj_conf = pred[4]
        
        # Kiểm tra xem coordinates có normalized không (thường < 1.0)
        if abs(cx) < 1.0 and abs(cy) < 1.0 and abs(w) < 1.0 and abs(h) < 1.0:
            # Normalized coordinates - scale về pixel
            cx = cx * original_shape[1]
            cy = cy * original_shape[0]
            w = w * original_shape[1]
            h = h * original_shape[0]
        else:
            # Absolute coordinates - scale từ input_size về original
            cx = cx * scale_x
            cy = cy * scale_y
            w = w * scale_x
            h = h * scale_y
        
        # Lấy class scores (từ index 5 trở đi)
        if len(pred) > 5:
            class_scores = pred[5:]
            class_id = np.argmax(class_scores)
            class_conf = class_scores[class_id]
            final_conf = obj_conf * class_conf
        else:
            # Nếu chỉ có obj_conf
            class_id = 0
            final_conf = obj_conf
        
        if final_conf < conf_threshold:
            continue
        
        # Convert từ center format sang corner format
        x1 = int(cx - w / 2)
        y1 = int(cy - h / 2)
        x2 = int(cx + w / 2)
        y2 = int(cy + h / 2)
        
        # Clamp to image bounds
        x1 = max(0, min(x1, original_shape[1] - 1))
        y1 = max(0, min(y1, original_shape[0] - 1))
        x2 = max(x1 + 1, min(x2, original_shape[1]))
        y2 = max(y1 + 1, min(y2, original_shape[0]))
        
        if x2 <= x1 or y2 <= y1:
            continue
        
        boxes.append([x1, y1, x2 - x1, y2 - y1])
        scores.append(float(final_conf))
        class_ids.append(int(class_id))
    
    # Apply NMS
    if len(boxes) > 0:
        keep_indices = non_max_suppression(boxes, scores, iou_threshold)
        filtered_boxes = [boxes[i] for i in keep_indices]
        filtered_scores = [scores[i] for i in keep_indices]
        filtered_class_ids = [class_ids[i] for i in keep_indices]
        
        return filtered_boxes, filtered_scores, filtered_class_ids
    
    return [], [], []

def get_vietnamese_label(class_name):
    """Chuyển class name sang tiếng Việt không dấu, giữ nguyên Drone"""
    # Mapping từ class names sang tiếng Việt không dấu
    vietnamese_map = {
        'tree': 'cay',
        'drone': 'Drone',  # Giữ nguyên
        'truck': 'xe tai',
        'motorcycle': 'xe may',
        'crane': 'cau truc',
        'livestock': 'gia suc',
        'pole': 'cot dien',
        'fire': 'chay',
        'smoke': 'khoi',
        'kite': 'dieu',
        'person': 'nguoi',
        # Fallback cho các class khác
        'bicycle': 'xe dap',
        'car': 'xe hoi',
        'bus': 'xe buyt',
        'bird': 'chim',
        'cow': 'bo',
        'horse': 'ngua',
        'sheep': 'cuu',
    }
    
    # Chuyển sang lowercase để so sánh
    class_lower = class_name.lower()
    
    # Nếu là "drone" (không phân biệt hoa thường), giữ nguyên "Drone"
    if class_lower == 'drone':
        return 'Drone'
    
    # Trả về tiếng Việt không dấu nếu có trong map
    return vietnamese_map.get(class_lower, class_name)

def draw_detections(image, boxes, scores, class_ids, class_names):
    """Vẽ bounding boxes và labels lên ảnh"""
    result_image = image.copy()
    
    for box, score, class_id in zip(boxes, scores, class_ids):
        x, y, w, h = box
        x1, y1 = int(x), int(y)
        x2, y2 = int(x + w), int(y + h)
        
        # Lấy class name
        if class_id < len(class_names):
            class_name = class_names[class_id]
        else:
            class_name = f"class_{class_id}"
        
        # Chuyển sang tiếng Việt không dấu (giữ nguyên Drone)
        display_name = get_vietnamese_label(class_name)
        
        # Vẽ bounding box
        cv2.rectangle(result_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # Vẽ label với tên tiếng Việt
        label = f"{display_name} {score:.2f}"
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        label_y = max(y1, label_size[1] + 10)
        
        # Vẽ background cho text
        cv2.rectangle(result_image, (x1, label_y - label_size[1] - 10), 
                     (x1 + label_size[0], label_y), (0, 255, 0), -1)
        
        # Vẽ text
        cv2.putText(result_image, label, (x1, label_y - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    return result_image

def test_image(model_path, image_path, output_path=None, conf_threshold=None, iou_threshold=None, debug=False):
    """Test ảnh với model .pt"""
    
    # Load model
    print(f"[INFO] Dang load model tu: {model_path}")
    model = load_model(model_path)
    if model is None:
        print("[ERROR] Khong the load model!")
        return False
    
    # Lấy class names từ model hoặc dùng từ config
    model_class_names = get_model_class_names(model)
    if model_class_names:
        # Sử dụng class names từ model (ưu tiên cao nhất)
        active_class_names = model_class_names
        print(f"[INFO] Su dung {len(active_class_names)} classes tu model")
    elif CLASS_NAMES2:
        # Nếu có CLASS_NAMES2, dùng (custom model)
        active_class_names = CLASS_NAMES2
        print(f"[INFO] Su dung CLASS_NAMES2 ({len(active_class_names)} classes): {active_class_names}")
    else:
        # Fallback về CLASS_NAMES mặc định
        active_class_names = CLASS_NAMES
        print(f"[INFO] Su dung CLASS_NAMES mac dinh ({len(active_class_names)} classes)")
    
    # Load ảnh
    print(f"[INFO] Dang load anh tu: {image_path}")
    image = cv2.imread(image_path)
    if image is None:
        print(f"[ERROR] Khong the doc anh tu: {image_path}")
        return False
    
    original_shape = image.shape[:2]
    print(f"[OK] Anh size: {original_shape[1]}x{original_shape[0]}")
    
    # Kiểm tra xem model có phải YOLOv5 không
    try:
        import yolov5
        # Kiểm tra xem model có phải YOLOv5 model không
        model_type = str(type(model))
        if 'yolov5' in model_type.lower() or hasattr(model, 'predict') or 'DetectionModel' in model_type or hasattr(model, 'conf'):
            print("[INFO] Dang chay detection voi YOLOv5 API...")
            conf_thresh = conf_threshold if conf_threshold else DETECTION_THRESHOLD
            iou_thresh = iou_threshold if iou_threshold else IOU_THRESHOLD
            
            # Set confidence và IOU threshold cho model
            # Tạm thời set confidence rất thấp để lấy tất cả detections
            original_conf = None
            if hasattr(model, 'conf'):
                original_conf = model.conf
                model.conf = 0.01  # Set rất thấp để lấy tất cả detections
            if hasattr(model, 'iou'):
                model.iou = iou_thresh
            
            # Sử dụng YOLOv5 API - gọi trực tiếp với image path hoặc numpy array
            try:
                # Thử gọi với image path
                results = model(image_path)
            except:
                # Nếu không được, thử với numpy array
                results = model(image)
            
            # Lấy thông tin detections từ YOLOv5
            boxes = []
            scores = []
            class_ids = []
            
            if results is not None:
                try:
                    detections_df = results.pandas().xyxy[0]
                    if len(detections_df) > 0:
                        # Debug: hiển thị TẤT CẢ detections (kể cả confidence thấp)
                        print(f"[DEBUG] Tim thay {len(detections_df)} detections (voi confidence >= 0.01):")
                        person_detections = []
                        for idx, det in detections_df.iterrows():
                            det_conf = float(det['confidence'])
                            det_class = int(det['class'])
                            det_name = active_class_names[det_class] if det_class < len(active_class_names) else f"class_{det_class}"
                            print(f"  - {det_name}: {det_conf:.3f} tai ({int(det['xmin'])}, {int(det['ymin'])}, {int(det['xmax'])}, {int(det['ymax'])})")
                            if det_name == 'person':
                                person_detections.append((det_conf, det))
                        
                        # Hiển thị thông tin về person detections
                        if person_detections:
                            print(f"\n[INFO] Tim thay {len(person_detections)} person detection(s):")
                            for conf, det in person_detections:
                                print(f"  - person: {conf:.3f} tai ({int(det['xmin'])}, {int(det['ymin'])}, {int(det['xmax'])}, {int(det['ymax'])})")
                        else:
                            print(f"\n[WARN] KHONG tim thay person detection nao trong {len(detections_df)} detections!")
                        
                        # Chỉ lấy detections có confidence >= threshold
                        for _, det in detections_df.iterrows():
                            det_conf = float(det['confidence'])
                            if det_conf < conf_thresh:
                                continue
                            x1, y1, x2, y2 = int(det['xmin']), int(det['ymin']), int(det['xmax']), int(det['ymax'])
                            w = x2 - x1
                            h = y2 - y1
                            boxes.append([x1, y1, w, h])
                            scores.append(det_conf)
                            class_ids.append(int(det['class']))
                except:
                    # Nếu không có pandas(), thử lấy từ results trực tiếp
                    if hasattr(results, 'xyxy') and len(results.xyxy) > 0:
                        print(f"[DEBUG] Tim thay {len(results.xyxy[0])} detections tu results.xyxy:")
                        for det in results.xyxy[0]:
                            det_conf = float(det[4])
                            det_class = int(det[5])
                            det_name = active_class_names[det_class] if det_class < len(active_class_names) else f"class_{det_class}"
                            print(f"  - {det_name}: {det_conf:.3f}")
                            if det_conf >= conf_thresh:
                                x1, y1, x2, y2 = int(det[0]), int(det[1]), int(det[2]), int(det[3])
                                w = x2 - x1
                                h = y2 - y1
                                boxes.append([x1, y1, w, h])
                                scores.append(det_conf)
                                class_ids.append(det_class)
            
            # Restore original confidence
            if original_conf is not None and hasattr(model, 'conf'):
                model.conf = original_conf
            
            if len(boxes) > 0:
                print(f"[OK] Tim thay {len(boxes)} object(s)")
                
                # Vẽ kết quả
                result_image = draw_detections(image, boxes, scores, class_ids, active_class_names)
                
                # Lưu kết quả
                if output_path is None:
                    output_path = image_path.replace('.jpg', '_result.jpg').replace('.png', '_result.png')
                    if output_path == image_path:
                        output_path = str(Path(image_path).stem) + '_result.jpg'
                
                cv2.imwrite(output_path, result_image)
                print(f"[OK] Da luu ket qua vao: {output_path}")
                
                # Hiển thị kết quả
                print("\n[INFO] Chi tiet detections:")
                for i, (box, score, class_id) in enumerate(zip(boxes, scores, class_ids)):
                    class_name = active_class_names[class_id] if class_id < len(active_class_names) else f"class_{class_id}"
                    display_name = get_vietnamese_label(class_name)
                    x, y, w, h = box
                    print(f"  {i+1}. {display_name}: {score:.2f} tai ({x}, {y}, {w}, {h})")
                
                # Hiển thị ảnh (optional)
                try:
                    cv2.imshow('Detection Result', result_image)
                    print("\n[INFO] Nhan phim bat ky de dong cua so...")
                    cv2.waitKey(0)
                    cv2.destroyAllWindows()
                except:
                    print("[WARN] Khong the hien thi anh (co the dang chay headless)")
                
                return True
            else:
                # Thử với confidence thấp hơn nếu không tìm thấy
                print(f"[WARN] Khong tim thay object nao voi confidence={conf_thresh:.2f}")
                if conf_thresh >= 0.3:
                    print(f"[INFO] Thu lai voi confidence thap hon (0.25)...")
                    model.conf = 0.25
                    try:
                        results = model(image_path) if hasattr(model, '__call__') else model(image)
                        if results is not None:
                            try:
                                detections_df = results.pandas().xyxy[0]
                                if len(detections_df) > 0:
                                    boxes = []
                                    scores = []
                                    class_ids = []
                                    for _, det in detections_df.iterrows():
                                        x1, y1, x2, y2 = int(det['xmin']), int(det['ymin']), int(det['xmax']), int(det['ymax'])
                                        w = x2 - x1
                                        h = y2 - y1
                                        boxes.append([x1, y1, w, h])
                                        scores.append(float(det['confidence']))
                                        class_ids.append(int(det['class']))
                                    
                                    if len(boxes) > 0:
                                        print(f"[OK] Tim thay {len(boxes)} object(s) voi confidence thap hon")
                                        result_image = draw_detections(image, boxes, scores, class_ids, active_class_names)
                                        if output_path is None:
                                            output_path = image_path.replace('.jpg', '_result.jpg').replace('.png', '_result.png')
                                            if output_path == image_path:
                                                output_path = str(Path(image_path).stem) + '_result.jpg'
                                        cv2.imwrite(output_path, result_image)
                                        print(f"[OK] Da luu ket qua vao: {output_path}")
                                        print("\n[INFO] Chi tiet detections:")
                                        for i, (box, score, class_id) in enumerate(zip(boxes, scores, class_ids)):
                                            class_name = active_class_names[class_id] if class_id < len(active_class_names) else f"class_{class_id}"
                                            x, y, w, h = box
                                            display_name = get_vietnamese_label(class_name)
                                            print(f"  {i+1}. {display_name}: {score:.2f} tai ({x}, {y}, {w}, {h})")
                                        try:
                                            cv2.imshow('Detection Result', result_image)
                                            print("\n[INFO] Nhan phim bat ky de dong cua so...")
                                            cv2.waitKey(0)
                                            cv2.destroyAllWindows()
                                        except:
                                            pass
                                        return True
                            except:
                                pass
                    except:
                        pass
                print("[WARN] Khong tim thay object nao (co the anh khong co objects hoac confidence threshold qua cao)")
                raise Exception("No detections found")
    except Exception as e_yolo5:
        print(f"[INFO] Khong the dung YOLOv5 API, thu cach khac: {str(e_yolo5)[:100]}")
        pass  # Không phải YOLOv5, tiếp tục
    
    # Kiểm tra xem model có phải Ultralytics YOLO không
    try:
        from ultralytics import YOLO
        if isinstance(model, YOLO):
            # Sử dụng API của Ultralytics (đơn giản hơn)
            print("[INFO] Dang chay detection voi Ultralytics YOLO...")
            conf_thresh = conf_threshold if conf_threshold else DETECTION_THRESHOLD
            iou_thresh = iou_threshold if iou_threshold else IOU_THRESHOLD
            
            results = model(image_path, conf=conf_thresh, iou=iou_thresh, verbose=False)
            result = results[0]
            
            # Lấy thông tin detections
            boxes = []
            scores = []
            class_ids = []
            
            if result.boxes is not None and len(result.boxes) > 0:
                for box in result.boxes:
                    # Lấy tọa độ
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    w = x2 - x1
                    h = y2 - y1
                    boxes.append([int(x1), int(y1), int(w), int(h)])
                    
                    # Lấy confidence và class
                    scores.append(float(box.conf[0].cpu().numpy()))
                    class_ids.append(int(box.cls[0].cpu().numpy()))
            
            print(f"[OK] Tim thay {len(boxes)} object(s)")
            
            # Vẽ kết quả
            result_image = draw_detections(image, boxes, scores, class_ids, active_class_names)
            
            # Lưu kết quả
            if output_path is None:
                output_path = image_path.replace('.jpg', '_result.jpg').replace('.png', '_result.png')
                if output_path == image_path:
                    output_path = str(Path(image_path).stem) + '_result.jpg'
            
            cv2.imwrite(output_path, result_image)
            print(f"[OK] Da luu ket qua vao: {output_path}")
            
            # Hiển thị kết quả
            print("\n[INFO] Chi tiet detections:")
            for i, (box, score, class_id) in enumerate(zip(boxes, scores, class_ids)):
                class_name = active_class_names[class_id] if class_id < len(active_class_names) else f"class_{class_id}"
                display_name = get_vietnamese_label(class_name)
                x, y, w, h = box
                print(f"  {i+1}. {display_name}: {score:.2f} tai ({x}, {y}, {w}, {h})")
            
            # Hiển thị ảnh (optional)
            try:
                cv2.imshow('Detection Result', result_image)
                print("\n[INFO] Nhan phim bat ky de dong cua so...")
                cv2.waitKey(0)
                cv2.destroyAllWindows()
            except:
                print("[WARN] Khong the hien thi anh (co the dang chay headless)")
            
            return True
    except:
        pass  # Không phải Ultralytics, tiếp tục với cách cũ
    
    # Cách cũ cho các model khác
    print("[INFO] Dang preprocess anh...")
    input_tensor, _ = preprocess_image(image, INPUT_SIZE)
    
    # Detection
    print("[INFO] Dang chay detection...")
    conf_thresh = conf_threshold if conf_threshold else DETECTION_THRESHOLD
    iou_thresh = iou_threshold if iou_threshold else IOU_THRESHOLD
    
    boxes, scores, class_ids = detect_objects(
        model, input_tensor, original_shape, 
        INPUT_SIZE, conf_thresh, iou_thresh
    )
    
    print(f"[OK] Tim thay {len(boxes)} object(s)")
    
    # Vẽ kết quả
    result_image = draw_detections(image, boxes, scores, class_ids, active_class_names)
    
    # Lưu kết quả
    if output_path is None:
        output_path = image_path.replace('.jpg', '_result.jpg').replace('.png', '_result.png')
        if output_path == image_path:
            output_path = str(Path(image_path).stem) + '_result.jpg'
    
    cv2.imwrite(output_path, result_image)
    print(f"[OK] Da luu ket qua vao: {output_path}")
    
    # Hiển thị kết quả
    print("\n[INFO] Chi tiet detections:")
    for i, (box, score, class_id) in enumerate(zip(boxes, scores, class_ids)):
        class_name = active_class_names[class_id] if class_id < len(active_class_names) else f"class_{class_id}"
        display_name = get_vietnamese_label(class_name)
        x, y, w, h = box
        print(f"  {i+1}. {display_name}: {score:.2f} tai ({int(x)}, {int(y)}, {int(w)}, {int(h)})")
    
    # Hiển thị ảnh (optional)
    try:
        cv2.imshow('Detection Result', result_image)
        print("\n[INFO] Nhan phim bat ky de dong cua so...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    except:
        print("[WARN] Khong the hien thi anh (co the dang chay headless)")
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Test ảnh với PyTorch model .pt')
    parser.add_argument('--model', type=str, default='best.pt',
                       help='Đường dẫn đến file model .pt (default: best.pt)')
    parser.add_argument('--image', type=str, required=True,
                       help='Đường dẫn đến ảnh cần test')
    parser.add_argument('--output', type=str, default=None,
                       help='Đường dẫn lưu ảnh kết quả (default: tự động tạo tên)')
    parser.add_argument('--conf', type=float, default=None,
                       help=f'Confidence threshold (default: {DETECTION_THRESHOLD})')
    parser.add_argument('--iou', type=float, default=None,
                       help=f'IOU threshold cho NMS (default: {IOU_THRESHOLD})')
    parser.add_argument('--debug', action='store_true',
                       help='Hiển thị tất cả detections (kể cả confidence thấp) để debug')
    
    args = parser.parse_args()
    
    # Kiểm tra file tồn tại
    if not Path(args.model).exists():
        print(f"[ERROR] Khong tim thay file model: {args.model}")
        return
    
    if not Path(args.image).exists():
        print(f"[ERROR] Khong tim thay file anh: {args.image}")
        return
    
    # Chạy test
    success = test_image(args.model, args.image, args.output, args.conf, args.iou, args.debug)
    
    if success:
        print("\n[OK] Test hoan tat!")
    else:
        print("\n[ERROR] Test that bai!")

if __name__ == '__main__':
    main()
