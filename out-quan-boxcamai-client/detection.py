import os
import time
import json
from datetime import datetime

import cv2
import numpy as np
from multiprocessing import Process, Queue, Event  # kept for compatibility with old signatures
import onnxruntime as ort

import config
from sender import start_send_thread, stop_send_thread_func, send_detection_to_server
from stream_sender import (
    start_processed_stream_thread,
    stop_processed_stream_thread_func,
    send_processed_frame,
)


def _load_onnx_session():
    """Load ONNX model and return (session, input_name)."""
    onnx_path = os.path.join(os.path.dirname(__file__), config.MODEL_PATH)
    if not os.path.exists(onnx_path):
        raise FileNotFoundError(f"ONNX model not found: {onnx_path}")

    session_options = ort.SessionOptions()
    session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    
    # GIỚI HẠN SỐ THREAD để điều khiển mức sử dụng CPU
    # intra_op_num_threads: số thread trong 1 operation (gần tương đương số core dùng cho ONNX)
    # inter_op_num_threads: số thread giữa các operations
    intra = getattr(config, "ONNX_INTRA_THREADS", 2)  # đề xuất: 2 core logic
    inter = getattr(config, "ONNX_INTER_THREADS", 1)  # để 1 để tránh overhead
    session_options.intra_op_num_threads = intra
    session_options.inter_op_num_threads = inter
    
    # Dùng SEQUENTIAL để tránh overhead parallel phức tạp, đủ cho 2 thread
    session_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    
    session = ort.InferenceSession(
        onnx_path,
        providers=["CPUExecutionProvider"],
        sess_options=session_options,
    )
    input_name = session.get_inputs()[0].name
    print(
        f"✅ ONNX model loaded with intra={session_options.intra_op_num_threads}, "
        f"inter={session_options.inter_op_num_threads} thread(s)"
    )
    return session, input_name


def _nms(boxes, scores, iou_threshold):
    """Simple Non-Maximum Suppression.

    boxes: Nx4 (x1,y1,x2,y2)
    scores: N
    """
    if len(boxes) == 0:
        return []

    boxes = boxes.astype(np.float32)
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]

    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)

        inds = np.where(iou <= iou_threshold)[0]
        order = order[inds + 1]

    return keep


def _inside_roi(x1, y1, x2, y2, roi_x1, roi_y1, roi_x2, roi_y2, frame_w, frame_h):
    """Check if bbox center is inside ROI (ROI in normalized 0-1)."""
    if roi_x1 is None or roi_y1 is None or roi_x2 is None or roi_y2 is None:
        return True

    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0

    nx = cx / frame_w
    ny = cy / frame_h

    return (roi_x1 <= nx <= roi_x2) and (roi_y1 <= ny <= roi_y2)


def _calculate_iou(box1, box2):
    """Tính IoU giữa 2 box (x1, y1, x2, y2)."""
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2
    
    # Tính intersection
    x1_i = max(x1_1, x1_2)
    y1_i = max(y1_1, y1_2)
    x2_i = min(x2_1, x2_2)
    y2_i = min(y2_1, y2_2)
    
    if x2_i <= x1_i or y2_i <= y1_i:
        return 0.0
    
    inter_area = (x2_i - x1_i) * (y2_i - y1_i)
    box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
    box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
    union_area = box1_area + box2_area - inter_area
    
    if union_area <= 0:
        return 0.0
    
    return inter_area / union_area


def _should_send_detection(current_boxes, current_classes, last_boxes, last_classes, iou_cooldown_threshold):
    """
    Kiểm tra xem có nên gửi detection mới không.
    
    Logic:
    - Nếu không có detection trước đó → gửi
    - Nếu số lượng vật khác nhau → gửi (có vật mới hoặc mất vật)
    - Nếu số lượng giống nhau, so sánh IoU:
      * Match mỗi vật hiện tại với vật trước đó (theo class_name và IoU cao nhất)
      * Nếu IoU trung bình > threshold → không gửi (vật đứng im)
      * Nếu IoU < threshold → gửi (vật di chuyển)
    
    Returns: (should_send: bool, reason: str)
    """
    # Lần đầu tiên hoặc không có detection trước đó → gửi
    if last_boxes is None or len(last_boxes) == 0:
        return True, "First detection"
    
    # Không có detection hiện tại → không gửi (nhưng logic này không nên xảy ra ở đây)
    if len(current_boxes) == 0:
        return False, "No current detections"
    
    # Số lượng vật khác nhau → gửi (có vật mới hoặc mất vật)
    if len(current_boxes) != len(last_boxes):
        return True, f"Object count changed: {len(current_boxes)} vs {len(last_boxes)}"
    
    # Số lượng giống nhau, so sánh IoU
    # Match mỗi vật hiện tại với vật trước đó (ưu tiên cùng class_name và IoU cao nhất)
    matched_indices = set()
    ious = []
    
    for i, (curr_box, curr_class) in enumerate(zip(current_boxes, current_classes)):
        best_iou = 0.0
        best_match_idx = -1
        
        for j, (last_box, last_class) in enumerate(zip(last_boxes, last_classes)):
            if j in matched_indices:
                continue
            
            # Ưu tiên cùng class_name
            if curr_class == last_class:
                iou = _calculate_iou(curr_box, last_box)
                if iou > best_iou:
                    best_iou = iou
                    best_match_idx = j
        
        # Nếu không match được cùng class, thử match với class khác
        if best_match_idx == -1:
            for j, (last_box, last_class) in enumerate(zip(last_boxes, last_classes)):
                if j in matched_indices:
                    continue
                iou = _calculate_iou(curr_box, last_box)
                if iou > best_iou:
                    best_iou = iou
                    best_match_idx = j
        
        if best_match_idx != -1:
            matched_indices.add(best_match_idx)
            ious.append(best_iou)
    
    # Tính IoU trung bình
    if len(ious) == 0:
        return True, "Could not match objects"
    
    avg_iou = sum(ious) / len(ious)
    
    # Nếu IoU trung bình > threshold → vật đứng im → không gửi
    if avg_iou >= iou_cooldown_threshold:
        return False, f"Objects stationary (avg IoU: {avg_iou:.2f} >= {iou_cooldown_threshold})"
    
    # IoU < threshold → vật di chuyển → gửi
    return True, f"Objects moved (avg IoU: {avg_iou:.2f} < {iou_cooldown_threshold})"


def detection_process(
    q,
    stop_event,
    not_sent=False,
    display=False,
    roi_x1=None,
    roi_y1=None,
    roi_x2=None,
    roi_y2=None,
    roi_regions_json=None,  # hiện tại chưa dùng lại multiple ROI ở bản khôi phục
    show_roi_overlay=True,
    priority_classes=None,  # Danh sách class ưu tiên (không cần ROI)
):
    """Quy trình detection chính, khôi phục về trạng thái đơn giản (chưa có cooldown)."""

    # Khởi động thread gửi detection nền
    if not not_sent:
        start_send_thread()

    # Khởi động thread gửi processed video để web xem
    start_processed_stream_thread()

    try:
        session, input_name = _load_onnx_session()
        print("✅ ONNX model loaded for detection")
    except Exception as e:
        print(f"❌ Failed to load ONNX model: {e}")
        # Nếu không load được model thì thoát detection_process nhưng vẫn không làm crash service
        while not stop_event.is_set():
            try:
                _ = q.get(timeout=1.0)
            except Exception:
                pass
        return

    frame_count = 0
    last_send_time = 0.0
    last_detection_boxes = None  # Lưu boxes từ lần gửi trước (list of tuples: (x1, y1, x2, y2))
    last_detection_classes = None  # Lưu class_names từ lần gửi trước

    DETECTION_THRESHOLD = getattr(config, "DETECTION_THRESHOLD", 0.25)
    IOU_THRESHOLD = getattr(config, "IOU_THRESHOLD", 0.3)
    FRAME_SKIP = getattr(config, "FRAME_SKIP", 1)
    TIME_BETWEEN_SEND = getattr(config, "TIME_BETWEEN_SEND", 2.0)
    IOU_COOLDOWN_THRESHOLD = getattr(config, "IOU_COOLDOWN_THRESHOLD", 0.7)
    
    # Priority classes: không cần ROI filter
    if priority_classes is None:
        priority_classes = []
    print(f"🔥 Priority classes (không cần ROI): {priority_classes}")

    # Ưu tiên dùng CLASS_NAMES2 (model custom), fallback qua CLASS_NAMES
    CLASS_NAMES = getattr(config, "CLASS_NAMES2", getattr(config, "CLASS_NAMES", []))

    # Parse multiple ROI regions (nếu có) để vẽ overlay polygon cho đúng với server
    roi_regions = None
    if roi_regions_json:
        try:
            parsed = json.loads(roi_regions_json)
            if isinstance(parsed, list) and len(parsed) > 0:
                roi_regions = parsed
        except Exception as e:
            print(f"⚠️ Error parsing roi_regions_json on client: {e}")
            roi_regions = None

    print(
        f"🔍 Detection loop started: thresh={DETECTION_THRESHOLD}, iou={IOU_THRESHOLD}, "
        f"frame_skip={FRAME_SKIP}, send_interval={TIME_BETWEEN_SEND}s"
    )

    while not stop_event.is_set():
        try:
            try:
                frame = q.get(timeout=1.0)
            except Exception:
                # Không có frame, sleep rất nhỏ để giảm CPU khi idle nhưng không làm chậm
                time.sleep(0.001)
                continue

            if frame is None or frame.size == 0:
                continue

            frame_count += 1

            # Chuẩn hóa kích thước frame về CAMERA_WIDTH x CAMERA_HEIGHT
            try:
                frame = cv2.resize(
                    frame,
                    (config.CAMERA_WIDTH, config.CAMERA_HEIGHT),
                    interpolation=cv2.INTER_LINEAR,
                )
            except Exception as e:
                print(f"⚠️ Error resizing frame: {e}")
                continue

            frame_h, frame_w = frame.shape[:2]
            frame_original = frame.copy()

            # VẼ ROI OVERLAY (chỉ để hiển thị, logic lọc vẫn dùng _inside_roi)
            if show_roi_overlay:
                try:
                    # Độ dày nét tỉ lệ theo kích thước ảnh
                    thickness = max(2, int(min(frame_w, frame_h) / 200))
                    color_roi = (0, 0, 255)  # Đỏ

                    # 1) Vẽ multiple ROI polygon từ roi_regions (giống server dùng cho cảnh báo)
                    if roi_regions:
                        for idx, roi in enumerate(roi_regions):
                            points = roi.get("points")
                            if points:
                                pts = []
                                for pt in points:
                                    x = pt.get("x", 0.0)
                                    y = pt.get("y", 0.0)
                                    # Các điểm đang được lưu ở dạng normalized (0–1) theo width/height
                                    px = int(x * frame_w)
                                    py = int(y * frame_h)
                                    pts.append([px, py])
                                if len(pts) >= 3:
                                    pts_np = np.array(pts, np.int32)
                                    cv2.polylines(frame_original, [pts_np], True, color_roi, thickness)

                                    # Vẽ tên ROI nếu có
                                    name = roi.get("name") or f"ROI {idx+1}"
                                    # Dùng điểm đầu tiên để đặt label
                                    lx, ly = pts[0]
                                    ly_label = ly - 10 if ly - 10 > 10 else ly + 20
                                    cv2.putText(
                                        frame_original,
                                        name,
                                        (lx, ly_label),
                                        cv2.FONT_HERSHEY_SIMPLEX,
                                        0.6,
                                        color_roi,
                                        max(1, thickness - 1),
                                        cv2.LINE_AA,
                                    )

                    # 2) Vẽ ROI hình chữ nhật đơn (backward-compatible) nếu có
                    if roi_x1 is not None and roi_y1 is not None and roi_x2 is not None and roi_y2 is not None:
                        rx1 = int(roi_x1 * frame_w)
                        ry1 = int(roi_y1 * frame_h)
                        rx2 = int(roi_x2 * frame_w)
                        ry2 = int(roi_y2 * frame_h)

                        # Đảm bảo trong khung hình
                        rx1 = max(0, min(frame_w - 1, rx1))
                        ry1 = max(0, min(frame_h - 1, ry1))
                        rx2 = max(0, min(frame_w - 1, rx2))
                        ry2 = max(0, min(frame_h - 1, ry2))

                        cv2.rectangle(frame_original, (rx1, ry1), (rx2, ry2), color_roi, thickness)
                        label_y = ry1 - 10 if ry1 - 10 > 10 else ry1 + 20
                        cv2.putText(
                            frame_original,
                            "ROI",
                            (rx1, label_y),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            color_roi,
                            max(1, thickness - 1),
                            cv2.LINE_AA,
                        )
                except Exception as e:
                    # Không để việc vẽ ROI làm crash detection
                    print(f"⚠️ Error drawing ROI overlay on client: {e}")

            # Bỏ qua frame nếu dùng FRAME_SKIP (nhưng FRAME_SKIP=1 nên không skip)
            if FRAME_SKIP > 1 and (frame_count % FRAME_SKIP) != 0:
                # Vẫn có thể gửi processed frame để web không bị đen
                send_processed_frame(frame_original)
                if display:
                    cv2.imshow("Object Detection", frame_original)
                    if cv2.waitKey(1) & 0xFF == 27:
                        stop_event.set()
                        break
                continue

            # Chuẩn bị input cho ONNX (BGR -> RGB, normalize, NCHW)
            resized = cv2.resize(
                frame_original,
                (config.INPUT_W_SIZE, config.INPUT_H_SIZE),
                interpolation=cv2.INTER_LINEAR,
            )
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            input_tensor = (rgb.astype(np.float32) / 255.0).transpose(2, 0, 1)[
                np.newaxis, :
            ]

            try:
                outputs = session.run(None, {input_name: input_tensor})
                # Bỏ sleep để tăng FPS tối đa (detect mọi frame)
            except Exception as e:
                print(f"❌ ONNX inference error: {e}")
                continue

            if not outputs:
                continue

            pred = outputs[0]
            # Kỳ vọng shape: (1, num_boxes, 5 + num_classes)
            if pred.ndim != 3:
                print(f"⚠️ Unexpected ONNX output shape: {pred.shape}")
                continue

            pred = pred[0]  # (num_boxes, 5 + num_classes)
            if pred.shape[0] == 0:
                # Không có box nào
                send_processed_frame(frame_original)
                if display:
                    cv2.imshow("Object Detection", frame_original)
                    if cv2.waitKey(1) & 0xFF == 27:
                        stop_event.set()
                        break
                continue

            boxes = pred[:, :4]
            obj_conf = pred[:, 4]
            cls_scores = pred[:, 5:]

            if cls_scores.size == 0:
                continue

            cls_ids = np.argmax(cls_scores, axis=1)
            cls_conf = cls_scores[np.arange(cls_scores.shape[0]), cls_ids]
            scores = obj_conf * cls_conf

            # Lọc theo threshold
            mask = scores >= DETECTION_THRESHOLD
            if not np.any(mask):
                send_processed_frame(frame_original)
                if display:
                    cv2.imshow("Object Detection", frame_original)
                    if cv2.waitKey(1) & 0xFF == 27:
                        stop_event.set()
                        break
                continue

            boxes = boxes[mask]
            scores = scores[mask]
            cls_ids = cls_ids[mask]

            # Chuyển từ (cx, cy, w, h) theo pixel input size -> (x1, y1, x2, y2) theo frame hiện tại
            cx = boxes[:, 0]
            cy = boxes[:, 1]
            bw = boxes[:, 2]
            bh = boxes[:, 3]

            scale_x = frame_w / float(config.INPUT_W_SIZE)
            scale_y = frame_h / float(config.INPUT_H_SIZE)

            x1 = (cx - bw / 2) * scale_x
            y1 = (cy - bh / 2) * scale_y
            x2 = (cx + bw / 2) * scale_x
            y2 = (cy + bh / 2) * scale_y

            x1 = np.clip(x1, 0, frame_w - 1)
            y1 = np.clip(y1, 0, frame_h - 1)
            x2 = np.clip(x2, 0, frame_w - 1)
            y2 = np.clip(y2, 0, frame_h - 1)

            # Áp dụng NMS
            boxes_xyxy = np.stack([x1, y1, x2, y2], axis=1)
            keep = _nms(boxes_xyxy, scores, IOU_THRESHOLD)
            if not keep:
                send_processed_frame(frame_original)
                if display:
                    cv2.imshow("Object Detection", frame_original)
                    if cv2.waitKey(1) & 0xFF == 27:
                        stop_event.set()
                        break
                continue

            boxes_xyxy = boxes_xyxy[keep]
            scores = scores[keep]
            cls_ids = cls_ids[keep]

            class_names = []
            confidences = []
            xs = []
            ys = []
            ws = []
            hs = []

            for (bx1, by1, bx2, by2, score, cid) in zip(
                boxes_xyxy[:, 0],
                boxes_xyxy[:, 1],
                boxes_xyxy[:, 2],
                boxes_xyxy[:, 3],
                scores,
                cls_ids,
            ):
                # Định nghĩa class_name trước để kiểm tra priority
                class_name = (
                    CLASS_NAMES[int(cid)] if 0 <= int(cid) < len(CLASS_NAMES) else str(cid)
                )
                
                # Class ưu tiên: bỏ qua ROI filter
                is_priority = class_name in priority_classes
                
                # Lọc theo ROI (nếu có và không phải class ưu tiên)
                if not is_priority:
                    if not _inside_roi(
                        bx1,
                        by1,
                        bx2,
                        by2,
                        roi_x1,
                        roi_y1,
                        roi_x2,
                        roi_y2,
                        frame_w,
                        frame_h,
                    ):
                        continue

                w_box = bx2 - bx1
                h_box = by2 - by1
                if w_box < 20 or h_box < 20:
                    # Bỏ box quá nhỏ, khó nhìn
                    continue

                class_names.append(class_name)
                confidences.append(float(score))
                xs.append(int(bx1))
                ys.append(int(by1))
                ws.append(int(w_box))
                hs.append(int(h_box))

                # Vẽ bbox + label lên frame
                color = (0, 255, 0)
                cv2.rectangle(
                    frame_original,
                    (int(bx1), int(by1)),
                    (int(bx2), int(by2)),
                    color,
                    2,
                )
                label = f"{class_name} {score:.2f}"
                cv2.putText(
                    frame_original,
                    label,
                    (int(bx1), int(max(0, by1 - 5))),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    1,
                    cv2.LINE_AA,
                )

            # Nếu sau ROI & size filter không còn box thì chỉ gửi processed frame
            if not class_names:
                send_processed_frame(frame_original)
                if display:
                    cv2.imshow("Object Detection", frame_original)
                    if cv2.waitKey(1) & 0xFF == 27:
                        stop_event.set()
                        break
                continue

            # Gửi detection lên server theo TIME_BETWEEN_SEND + cooldown IoU
            now = time.time()
            if now - last_send_time >= TIME_BETWEEN_SEND and not not_sent:
                # Chuẩn bị boxes hiện tại để so sánh (list of tuples: (x1, y1, x2, y2))
                current_boxes = [(xs[i], ys[i], xs[i] + ws[i], ys[i] + hs[i]) for i in range(len(xs))]
                current_classes = class_names
                
                # Kiểm tra xem có priority class không
                has_priority_class = any(cls in priority_classes for cls in current_classes)
                
                # Priority classes: Bỏ qua cooldown, luôn gửi
                if has_priority_class:
                    should_send = True
                    priority_class_names = [cls for cls in current_classes if cls in priority_classes]
                    reason = f"Priority class detected: {', '.join(priority_class_names)} (bypass cooldown)"
                else:
                    # Class thường: Kiểm tra cooldown IoU
                    should_send, reason = _should_send_detection(
                        current_boxes,
                        current_classes,
                        last_detection_boxes,
                        last_detection_classes,
                        IOU_COOLDOWN_THRESHOLD
                    )
                
                if should_send:
                    # Dùng thời gian local có timezone để hiển thị đúng ngày/giờ trên Dashboard
                    timestamp = datetime.now().astimezone()
                    image_filename = timestamp.strftime("%Y%m%d_%H%M%S_%f") + ".jpg"
                    image_path = os.path.join(config.IMAGES_DIR, image_filename)
                    try:
                        cv2.imwrite(image_path, frame_original)
                    except Exception as e:
                        print(f"⚠️ Failed to save image: {e}")
                        image_filename = None

                    detection_data = {
                        "timestamp": timestamp.isoformat(),
                        "class_name": class_names,
                        "confidence": confidences,
                        "image_path": image_filename,
                        "bbox_x": xs,
                        "bbox_y": ys,
                        "bbox_width": ws,
                        "bbox_height": hs,
                        "metadata": {
                            "frame_width": frame_w,
                            "frame_height": frame_h,
                            "detection_id": timestamp.strftime("%Y%m%d_%H%M%S_%f"),
                        },
                    }

                    print(f"✅ Sending detections to server: {class_names} (Reason: {reason})")
                    send_detection_to_server(detection_data)
                    last_send_time = now
                    
                    # Lưu detection hiện tại để so sánh lần sau
                    last_detection_boxes = current_boxes
                    last_detection_classes = current_classes
                else:
                    # Không gửi vì vật đứng im
                    print(f"⏸️ Skipping detection (Reason: {reason})")

            # Gửi processed frame để web xem
            send_processed_frame(frame_original)

            if display:
                cv2.imshow("Object Detection", frame_original)
                if cv2.waitKey(1) & 0xFF == 27:
                    stop_event.set()
                    break
            
            # Bỏ sleep để tăng FPS tối đa (detect mọi frame)

        except Exception as e:
            print(f"Detection process error: {e}")
            time.sleep(0.001)
            continue

    # Cleanup
    if not not_sent:
        stop_send_thread_func()
    stop_processed_stream_thread_func()
    if display:
        cv2.destroyAllWindows()


# Giữ main cũ chỉ để chạy standalone khi debug (hiếm dùng trên Pi)
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Debug detection_process standalone")
    parser.add_argument("--video", type=str, help="Path to video file", default=None)
    parser.add_argument("--display", action="store_true", help="Hiển thị cửa sổ video")
    args = parser.parse_args()

    if args.video:
        config.VIDEO_FILE_PATH = args.video

    frame_queue = Queue(maxsize=10)
    stop_evt = Event()

    # Đơn giản đọc từ VIDEO_FILE_PATH
    cap = cv2.VideoCapture(config.VIDEO_FILE_PATH) if config.VIDEO_FILE_PATH else None
    if not cap or not cap.isOpened():
        print("Error: cannot open video for debug")
        exit(1)

    proc = Process(
        target=detection_process,
        args=(frame_queue, stop_evt, False, args.display, None, None, None, None, None, True),
    )
    proc.start()

    try:
        while cap.isOpened():
            ret, f = cap.read()
            if not ret:
                break
            if not frame_queue.full():
                frame_queue.put(f)
            time.sleep(0.01)
    finally:
        stop_evt.set()
        proc.join(timeout=5)
        cap.release()
        print("Detection debug finished")
