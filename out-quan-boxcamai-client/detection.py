import cv2
import numpy as np
import onnxruntime as ort
import subprocess
from multiprocessing import Process, Queue, Event
import os
import json
from datetime import datetime
import time
import threading
import argparse
import config
from utils import save_detection_image, non_max_suppression
from sender import send_detection_to_server, start_send_thread, stop_send_thread_func
from stream_sender import send_processed_frame

# Global for last send time
last_send_time = 0.0

# Define the path to the ONNX model file
onnx_path = config.MODEL_PATH

# Create ONNX Runtime inference session with CPU execution provider for running the model
session = ort.InferenceSession(onnx_path, providers=['CPUExecutionProvider'])

# Get model input details
input_details = session.get_inputs()[0]
input_name = input_details.name
input_shape = input_details.shape

# IOU threshold for Non-Maximum Suppression
IOU_THRESH = config.IOU_THRESHOLD

def point_in_polygon(point_x, point_y, polygon_points):
    """
    Check if a point is inside a polygon using ray casting algorithm.
    polygon_points: list of dicts with 'x' and 'y' keys, or list of tuples (x, y)
    Returns: True if point is inside polygon, False otherwise
    """
    if not polygon_points or len(polygon_points) < 3:
        return False
    
    # Convert to list of (x, y) tuples if needed
    if isinstance(polygon_points[0], dict):
        points = [(p['x'], p['y']) for p in polygon_points]
    else:
        points = polygon_points
    
    n = len(points)
    inside = False
    
    j = n - 1
    for i in range(n):
        xi, yi = points[i]
        xj, yj = points[j]
        
        # Check if point is on the edge
        if ((yi > point_y) != (yj > point_y)) and \
           (point_x < (xj - xi) * (point_y - yi) / (yj - yi) + xi):
            inside = not inside
        
        j = i
    
    return inside

# Object detection process function that runs in a separate process for parallel execution


def detection_process(q, stop_event, not_sent=False, display=False, roi_x1=None, roi_y1=None, roi_x2=None, roi_y2=None, roi_regions_json=None, show_roi_overlay=True):
    # Start the sender thread in this process if sending is enabled
    if not not_sent:
        start_send_thread()
    
    # Start processed stream thread
    from stream_sender import start_processed_stream_thread
    start_processed_stream_thread()

    # Main detection loop - runs continuously until stopped
    frame_count = 0

    while True:
        if stop_event.is_set():
            break

        try:
            # Receive frame from queue
            frame = q.get(timeout=1.0)
            frame_count += 1

            # Skip frames for performance optimization
            if frame_count % config.FRAME_SKIP != 0:
                continue

            # Skip invalid frames
            if frame is None or frame.size == 0:
                continue

            frame_original = frame.copy()       # ảnh gốc để lưu và gửi

            # Parse multiple ROI regions if provided
            roi_regions = []
            if roi_regions_json:
                try:
                    roi_regions = json.loads(roi_regions_json)
                    if not isinstance(roi_regions, list):
                        roi_regions = []
                except json.JSONDecodeError:
                    print("⚠️ Error decoding roi_regions_json, using empty list")
                    roi_regions = []
            
            # Backward compatibility: Convert single ROI to multiple ROI format
            if not roi_regions and roi_x1 is not None and roi_y1 is not None and roi_x2 is not None and roi_y2 is not None:
                roi_regions = [{'x1': roi_x1, 'y1': roi_y1, 'x2': roi_x2, 'y2': roi_y2}]
            
            # Validate ROI regions (support both polygon and rectangle formats)
            valid_roi_regions = []
            for roi in roi_regions:
                try:
                    # Check if it's a polygon format (has 'points' key)
                    if 'points' in roi and isinstance(roi['points'], list):
                        # Polygon format - validate points
                        points = roi['points']
                        if len(points) < 3:
                            continue
                        
                        # Validate and clamp points to frame bounds
                        valid_points = []
                        for p in points:
                            px = max(0, min(float(p.get('x', 0)), frame_original.shape[1] - 1))
                            py = max(0, min(float(p.get('y', 0)), frame_original.shape[0] - 1))
                            valid_points.append({'x': px, 'y': py})
                        
                        # Check minimum size (bounding box)
                        xs = [p['x'] for p in valid_points]
                        ys = [p['y'] for p in valid_points]
                        width = max(xs) - min(xs)
                        height = max(ys) - min(ys)
                        
                        if width >= 10 and height >= 10:
                            # Preserve name and color if present
                            valid_roi = {'points': valid_points}
                            if 'name' in roi:
                                valid_roi['name'] = roi['name']
                            if 'color' in roi:
                                valid_roi['color'] = roi['color']
                            if 'colorRgb' in roi:
                                valid_roi['colorRgb'] = roi['colorRgb']
                            valid_roi_regions.append(valid_roi)
                    else:
                        # Rectangle format (backward compatibility)
                        x1 = float(roi.get('x1', 0))
                        y1 = float(roi.get('y1', 0))
                        x2 = float(roi.get('x2', 0))
                        y2 = float(roi.get('y2', 0))
                        
                        # Ensure ROI coordinates are within frame bounds
                        x1 = max(0, min(x1, frame_original.shape[1] - 1))
                        y1 = max(0, min(y1, frame_original.shape[0] - 1))
                        x2 = max(x1 + 1, min(x2, frame_original.shape[1]))
                        y2 = max(y1 + 1, min(y2, frame_original.shape[0]))
                        
                        # Validate ROI size (minimum 10x10 pixels)
                        if (x2 - x1) >= 10 and (y2 - y1) >= 10:
                            # Preserve name and color if present
                            valid_roi = {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2}
                            if 'name' in roi:
                                valid_roi['name'] = roi['name']
                            if 'color' in roi:
                                valid_roi['color'] = roi['color']
                            if 'colorRgb' in roi:
                                valid_roi['colorRgb'] = roi['colorRgb']
                            valid_roi_regions.append(valid_roi)
                except (ValueError, TypeError) as e:
                    print(f"⚠️ Invalid ROI region: {roi}, error: {e}")
                    continue
            
            roi_regions = valid_roi_regions
            
            # Debug: Log ROI regions (only once per frame skip cycle to avoid spam)
            if frame_count % (config.FRAME_SKIP * 30) == 0 and roi_regions:
                print(f"✅ Drawing {len(roi_regions)} ROI region(s) on video stream")
            
            # NO LONGER CROPPING THE FRAME for multiple ROIs
            # Detection will be performed on full frame, then filtered by ROI
            # This allows checking if object is in ALL ROIs

            # Preprocess frame for model input
            # Resize frame to model input size using config values to avoid symbolic shapes
            # Note: For multiple ROIs, we process the full frame_original (not cropped)
            if roi_regions:
                # Use full frame_original for detection
                resized_frame = cv2.resize(
                    frame_original, (config.INPUT_W_SIZE, config.INPUT_H_SIZE))
            else:
                # Single ROI: use cropped frame (backward compatible)
                resized_frame = cv2.resize(
                    frame, (config.INPUT_W_SIZE, config.INPUT_H_SIZE))

            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)

            # Normalize pixel values to [0, 1]
            normalized_frame = rgb_frame.astype(np.float32) / 255.0

            # Transpose to channel-first format (NCHW)
            input_tensor = np.transpose(normalized_frame, (2, 0, 1))

            # Add batch dimension
            input_tensor = np.expand_dims(input_tensor, axis=0)

            # Run inference
            # [1, N, 85] - [batch, detections, 85 values per detection]
            outputs = session.run(None, {input_name: input_tensor})[0]

            # Process model outputs
            # Assuming YOLOv5 output format: [batch, num_boxes, 85] where 85 = 4 bbox + 1 obj + 80 classes
            # Remove the batch dimension from outputs for easier processing
            predictions = np.squeeze(outputs)

            # Ensure predictions is 2D [num_boxes, features]
            if predictions.ndim == 1:
                predictions = np.expand_dims(predictions, axis=0)

            # Filter predictions by confidence threshold
            boxes = []
            scores = []
            class_ids = []
            class_names = []  # for send to server
            confidences = []  # for send to server
            xs = []
            ys = []
            ws = []
            hs = []
            for pred in predictions:
                confidence = pred[4]  # Objectness score
                if confidence < config.DETECTION_THRESHOLD:
                    continue
                # Get class scores (offsets 5-84 in YOLO output format)
                class_scores = pred[5:]
                class_id = np.argmax(class_scores)
                class_score = class_scores[class_id]

                # Combine objectness and class score
                final_score = confidence * class_score

                if final_score < config.DETECTION_THRESHOLD:
                    continue

                # Extract bounding box coordinates (center x, center y, width, height)
                cx, cy, w, h = pred[0], pred[1], pred[2], pred[3]

                # Convert from normalized coordinates to pixel coordinates
                # Scale from INPUT_SIZE back to original frame size
                if roi_regions:
                    # Multiple ROI: scale to full frame_original size
                    scale_x = frame_original.shape[1] / config.INPUT_W_SIZE
                    scale_y = frame_original.shape[0] / config.INPUT_H_SIZE
                    x1 = int((cx - w / 2) * scale_x)
                    y1 = int((cy - h / 2) * scale_y)
                    x2 = int((cx + w / 2) * scale_x)
                    y2 = int((cy + h / 2) * scale_y)
                else:
                    # Single ROI (backward compatible): scale to cropped frame size
                    x1 = int((cx - w / 2) * frame.shape[1])
                    y1 = int((cy - h / 2) * frame.shape[0])
                    x2 = int((cx + w / 2) * frame.shape[1])
                    y2 = int((cy + h / 2) * frame.shape[0])

                boxes.append([x1, y1, x2 - x1, y2 - y1])
                scores.append(float(final_score))
                class_ids.append(class_id)

            # Perform Non-Maximum Suppression if we have any valid detections
            if len(boxes) > 0:
                idxs = non_max_suppression(boxes, scores, IOU_THRESH)
                # Process detections that survived NMS
                if len(idxs) > 0:
                    for i in idxs.flatten():
                        # Extract bounding box coordinates và class_id TRƯỚC
                        x, y, w, h = boxes[i]
                        class_id = class_ids[i]
                        score = scores[i]

                        # Get class name
                        class_name = config.CLASS_NAMES[class_id]

                        # Check if this object should be tracked
                        if config.TRACKED_OBJECTS and class_name not in config.TRACKED_OBJECTS:
                            continue

                        # Validate bbox
                        if not all(isinstance(coord, (int, float)) for coord in [x, y, w, h]) or w <= 0 or h <= 0:
                            continue

                        # Clamp bbox to frame bounds
                        if roi_regions:
                            # Multiple ROI: clamp to full frame_original
                            x = max(0, min(x, frame_original.shape[1] - 1))
                            y = max(0, min(y, frame_original.shape[0] - 1))
                            w = min(w, frame_original.shape[1] - x)
                            h = min(h, frame_original.shape[0] - y)
                        else:
                            # Single ROI: clamp to cropped frame
                            x = max(0, min(x, frame.shape[1] - 1))
                            y = max(0, min(y, frame.shape[0] - 1))
                            w = min(w, frame.shape[1] - x)
                            h = min(h, frame.shape[0] - y)

                        if w <= 0 or h <= 0:
                            continue

                        # Check if detection is within ALL ROI regions (unified ROI logic)
                        if roi_regions:
                            # Calculate bounding box center point
                            bbox_center_x = int(x + w / 2)
                            bbox_center_y = int(y + h / 2)
                            
                            # Check if center point is within ALL ROI regions
                            in_all_rois = True
                            for roi in roi_regions:
                                point_inside = False
                                
                                # Check if it's a polygon format
                                if 'points' in roi:
                                    # Polygon format - use point-in-polygon algorithm
                                    point_inside = point_in_polygon(bbox_center_x, bbox_center_y, roi['points'])
                                else:
                                    # Rectangle format (backward compatibility)
                                    roi_x1_int = int(roi.get('x1', 0))
                                    roi_y1_int = int(roi.get('y1', 0))
                                    roi_x2_int = int(roi.get('x2', 0))
                                    roi_y2_int = int(roi.get('y2', 0))
                                    
                                    point_inside = (roi_x1_int <= bbox_center_x <= roi_x2_int and 
                                                    roi_y1_int <= bbox_center_y <= roi_y2_int)
                                
                                if not point_inside:
                                    in_all_rois = False
                                    break
                            
                            # Skip detection if not in all ROIs
                            if not in_all_rois:
                                continue
                            
                            # Draw bounding box on original frame (no offset needed)
                            label = f"{class_name} {score:.2f}"
                            cv2.rectangle(frame_original, (int(x), int(y)), (int(x + w), int(y + h)), (0, 255, 0), 2)
                            cv2.putText(frame_original, label, (int(x), int(y + 12)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                            
                            xs.append(int(x))
                            ys.append(int(y))
                            ws.append(int(w))
                            hs.append(int(h))
                        else:
                            # Single ROI (backward compatible) - draw with offset
                            roi_x1_int = int(roi_x1) if roi_x1 is not None else 0
                            roi_y1_int = int(roi_y1) if roi_y1 is not None else 0
                            
                            label = f"{class_name} {score:.2f}"
                            cv2.rectangle(frame_original, (int(x + roi_x1_int), int(y + roi_y1_int)),
                                          (int(x + roi_x1_int + w), int(y + roi_y1_int + h)), (0, 255, 0), 2)
                            cv2.putText(frame_original, label, (int(x + roi_x1_int), int(y + roi_y1_int + 12)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                            
                            xs.append(int(x + roi_x1_int))
                            ys.append(int(y + roi_y1_int))
                            ws.append(int(w))
                            hs.append(int(h))
                        
                        class_names.append(class_name)
                        confidences.append(score)
            
            # Draw ROI overlay (optional)
            if show_roi_overlay:
                if roi_regions:
                    for idx, roi in enumerate(roi_regions):
                        roi_name = roi.get('name', f'ROI {idx + 1}')
                        color_rgb = roi.get('colorRgb', [0, 255, 255])  # Default cyan
                        color_bgr = (int(color_rgb[2]), int(color_rgb[1]), int(color_rgb[0]))
                        
                        if 'points' in roi:
                            points = roi['points']
                            if len(points) >= 3:
                                pts = np.array([(int(p['x']), int(p['y'])) for p in points], np.int32)
                                pts = pts.reshape((-1, 1, 2))
                                cv2.polylines(frame_original, [pts], True, color_bgr, 2)
                                if len(points) > 0:
                                    text_x = int(points[0]['x']) + 5
                                    text_y = int(points[0]['y']) - 10
                                    cv2.putText(frame_original, roi_name, (text_x, text_y),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4)
                                    cv2.putText(frame_original, roi_name, (text_x, text_y),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color_bgr, 2)
                        else:
                            cv2.rectangle(frame_original,
                                          (int(roi.get('x1', 0)), int(roi.get('y1', 0))),
                                          (int(roi.get('x2', 0)), int(roi.get('y2', 0))),
                                          color_bgr, 2)
                            text_x = int(roi.get('x1', 0)) + 5
                            text_y = int(roi.get('y1', 0)) - 10
                            cv2.putText(frame_original, roi_name, (text_x, text_y),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4)
                            cv2.putText(frame_original, roi_name, (text_x, text_y),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color_bgr, 2)
                elif roi_x1 is not None and roi_y1 is not None and roi_x2 is not None and roi_y2 is not None:
                    cv2.rectangle(frame_original, (int(roi_x1), int(roi_y1)),
                                  (int(roi_x2), int(roi_y2)), (0, 0, 255), 2)

            # LUÔN gửi processed frame về server (dù có detection hay không)
            # Để web luôn có stream, không báo offline
            send_processed_frame(frame_original)

            # Send every 1 second if any detections are present
            current_time = time.time()
            global last_send_time
            if (current_time - last_send_time) > config.TIME_BETWEEN_SEND:
                if class_names:  # Chỉ gửi detection data khi CÓ detection
                    last_send_time = current_time
                    print(f"Detections found: {class_names}")
                    # Create timestamp
                    timestamp = datetime.now()

                    # Save detection image (using first detection for image saving)
                    print(f"Saving image for detections")
                    image_filename = save_detection_image(frame_original, class_names[0] if class_names else "unknown", confidences[0] if confidences else 0, (
                        xs[0] if xs else 0, ys[0] if ys else 0, ws[0] if ws else 0, hs[0] if hs else 0), timestamp)

                    if image_filename:
                        # Prepare detection data for server
                        detection_data = {
                            'timestamp': timestamp.isoformat(),
                            'class_name': class_names,
                            'confidence': confidences,
                            'image_path': os.path.basename(image_filename),
                            'bbox_x': xs,
                            'bbox_y': ys,
                            'bbox_width': ws,
                            'bbox_height': hs,
                            'metadata': {
                                'frame_width': frame.shape[1],
                                'frame_height': frame.shape[0],
                                'detection_id': f"{timestamp.strftime('%Y%m%d_%H%M%S_%f')}"
                            }
                        }

                        # Queue detection for background sending (non-blocking) only if not disabled
                        if not not_sent:
                            print(f"Sending detections to server")
                            send_detection_to_server(detection_data)

                        # Draw bounding boxes and labels for detections that survived NMS (only if not sending, for display but since headless, optional)
                        # But since we moved draw inside if should_send, here only if not should_send
                        # But since we running headless so no need for this
                        # if not should_send:
                        #     # Create label text with class name and confidence score
                        #     label = f"{class_name} {score:.2f}"
                        #     # Draw green bounding box around detected object
                        #     cv2.rectangle(frame, (int(x), int(y)), (int(x + w), int(y + h)), (0, 255, 0), 2)
                        #     # Draw label text above the bounding box
                        #     cv2.putText(frame, label, (int(x), int(y - 5)),
                        #                 cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            # Display window if enabled
            if display:
                cv2.imshow('Object Detection', frame_original)
                key = cv2.waitKey(1) & 0xFF
                if key == 27:  # ESC key to exit
                    stop_event.set()
                    break

        except Exception as e:
            print(f"Detection process error: {e}")
            continue

    # Cleanup
    if not not_sent:
        stop_send_thread_func()
    
    # Stop processed stream thread
    from stream_sender import stop_processed_stream_thread_func
    stop_processed_stream_thread_func()

    # Close display window if it was opened
    if display:
        cv2.destroyAllWindows()
