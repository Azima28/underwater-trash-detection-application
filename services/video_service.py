import cv2
import os
import time
import numpy as np
import json
from utils.config_loader import config
from utils.model import get_model, infer_frame
from utils.tracking import CentroidTracker
from services.cleanup_service import delete_file

def generate_frames(filepath, model_choice, user_name, stream_id, config, global_stats, active_stats):
    try:
        model = get_model(model_choice)
        
        cap = cv2.VideoCapture(filepath)
        prev_time = time.time()

        # Prepare output writer to save processed video concurrently
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        output_filename = f"result_{stream_id}.mp4"
        output_path = os.path.join(config['OUTPUT_FOLDER'], output_filename)
        
        print(f"Starting stream: {stream_id}, model: {model_choice}")
        print(f"Video dims: {width}x{height}, fps: {fps}")
        
        try:
            # We will resize frames to target width, so we need to update writer dims
            target_width = config.get('processing.video_target_width', 640)
            if width > target_width:
                scale_init = target_width / width
                target_height = int(height * scale_init)
            else:
                target_width = width
                target_height = height
            
            print(f"Output Video dims: {target_width}x{target_height}, fps: {fps}")
            out_writer = cv2.VideoWriter(output_path, fourcc, fps, (target_width, target_height))
        except Exception as e:
            print(f"VideoWriter init error: {e}")
            out_writer = None

        # Track detections and class counts during streaming with centroid tracking
        # Adaptive tracking parameters based on video resolution
        adaptive_max_distance = max(50, int(width * 0.05))  # 5% of width
        adaptive_max_disappeared = max(40, int(fps * 1.5))  # 1.5 seconds worth of frames
        print(f"Tracking params: max_distance={adaptive_max_distance}, max_disappeared={adaptive_max_disappeared}")
        ct = CentroidTracker(max_disappeared=adaptive_max_disappeared, max_distance=adaptive_max_distance)
        unique_objects = {}  # {class_name: set of objectIDs}
        class_counts = {}    # {class_name: count of unique objects}
        frame_count = 0      # Track total frames for duration calculation


        # Verify capture
        if not cap.isOpened():
            print(f"Error: Could not open video file: {filepath}")
            # Create error frame
            err_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(err_frame, "Error: Cannot Open Video", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            success, buffer = cv2.imencode('.jpg', err_frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            return

        print(f"Capture opened successfully. Frame count: {int(cap.get(cv2.CAP_PROP_FRAME_COUNT))}")

        while True:
            ret, frame = cap.read()
            if not ret:
                print(f"End of stream or read error at frame {frame_count}")
                break
            
            frame_count += 1
            
            # Validate frame
            if frame is None or frame.size == 0:
                print("Warning: Empty frame received")
                continue
            
            # 1. Prepare Frame for Inference and Annotation
            raw_frame = frame.copy()
            h_orig, w_orig = frame.shape[:2]
            
            # Resize for Inference speed
            max_w_v8 = config.get('processing.max_width_v8', 1024)
            max_w_rtdetr = config.get('processing.max_width_rtdetr', 800)
            target_max_width = max_w_rtdetr if 'rtdetr' in str(model_choice).lower() else max_w_v8
            scale_inference = 1.0
            if w_orig > target_max_width:
                scale_inference = target_max_width / w_orig
                new_h = int(h_orig * scale_inference)
                inf_frame = cv2.resize(frame, (target_max_width, new_h))
            else:
                inf_frame = frame.copy()
                scale_inference = 1.0
            
            # ensure 3 channels
            if len(inf_frame.shape) != 3:
                 inf_frame = cv2.cvtColor(inf_frame, cv2.COLOR_GRAY2BGR)

            try:
                results = infer_frame(model, inf_frame, conf=config.get('processing.inference_conf', 0.25))
            except Exception as e:
                print(f"Frame inference failed: {e}")
                results = []
            
            # 3. Annotation (on original high-res frame)
            annotated_frame = raw_frame.copy()
            inv_scale = 1.0 / scale_inference
            
            if results and len(results) > 0 and results[0].boxes:
                for box in results[0].boxes:
                    try:
                        # Rescale boxes back to original resolution
                        coords = box.xyxy[0].cpu().numpy()
                        x1 = int(coords[0] * inv_scale)
                        y1 = int(coords[1] * inv_scale)
                        x2 = int(coords[2] * inv_scale)
                        y2 = int(coords[3] * inv_scale)
                        
                        conf = float(box.conf[0])
                        cls_id = int(box.cls[0])
                        
                        if hasattr(model, 'names') and model.names:
                            label_text = model.names.get(cls_id, f'Class {cls_id}') if isinstance(model.names, dict) else model.names[cls_id]
                        else:
                            label_text = f'Class {cls_id}'
                        
                        label = f"{label_text} {conf:.2f}"
                        
                        # Draw on original frame (High Res)
                        thickness = max(1, int(w_orig / 800))
                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 0, 255), thickness)
                        
                        font_scale = w_orig / 2400
                        (w_l, h_l), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
                        label_height = int(18 * font_scale)
                        y1_label = max(y1 - label_height, 0) 
                        cv2.rectangle(annotated_frame, (x1, y1_label), (x1 + w_l, y1_label + label_height), (0, 255, 0), -1)
                        cv2.putText(annotated_frame, label, (x1, y1_label + int(14 * font_scale)),
                                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness)
                    except Exception as draw_err:
                        print(f"Error drawing box: {draw_err}")

            # 4. FPS Display (on high-res)
            curr_time = time.time()
            dt = curr_time - prev_time if curr_time - prev_time > 0 else 1e-6
            fps_display = 1.0 / dt
            prev_time = curr_time
            cv2.putText(annotated_frame, f"FPS: {fps_display:.1f}", (20, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

            # 5. Tracking Logic
            rects = []
            input_class_names = []
            if results and len(results) > 0 and results[0].boxes:
                 for box in results[0].boxes:
                    try:
                        coords = box.xyxy[0].cpu().numpy()
                        x1 = int(coords[0] * inv_scale)
                        y1 = int(coords[1] * inv_scale)
                        x2 = int(coords[2] * inv_scale)
                        y2 = int(coords[3] * inv_scale)
                        
                        cls_id = int(box.cls[0])
                        if hasattr(model, 'names') and model.names:
                            label_text = model.names.get(cls_id, f'Class {cls_id}') if isinstance(model.names, dict) else model.names[cls_id]
                        else:
                            label_text = f'Class {cls_id}'
                        
                        rects.append((x1, y1, x2, y2))
                        input_class_names.append(label_text)
                    except Exception:
                        continue

            # Update Tracker
            objects, obj_class_names = ct.update(rects, input_class_names)

            # Update Stats and Draw ID
            for (objectID, centroid) in objects.items():
                class_name = obj_class_names.get(objectID, "Unknown")
                if class_name not in unique_objects:
                    unique_objects[class_name] = set()
                
                unique_objects[class_name].add(objectID)
                class_counts[class_name] = len(unique_objects[class_name])
                
                if ct.disappeared[objectID] == 0:
                    text = f"ID {objectID}"
                    cv2.putText(annotated_frame, text, (centroid[0] - 10, centroid[1] - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                    cv2.circle(annotated_frame, (centroid[0], centroid[1]), 3, (0, 255, 0), -1)

            # 6. Video Writer
            if out_writer is not None:
                try:
                    if annotated_frame.shape[1] != target_width or annotated_frame.shape[0] != target_height:
                         raw_annotated = cv2.resize(annotated_frame, (target_width, target_height))
                    else:
                         raw_annotated = annotated_frame
                    
                    out_writer.write(raw_annotated)
                except Exception as e:
                    print(f"Frame write error: {e}")

            # 7. Encode for Stream
            quality = config.get('processing.jpeg_quality', 80)
            success, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
            if not success:
                print("Failed to encode frame to JPEG")
                continue
            
            frame_bytes = bytes(buffer)
            
            boundary = b'--frame\r\n'
            header = b'Content-Type: image/jpeg\r\nContent-Length: ' + str(len(frame_bytes)).encode() + b'\r\n\r\n'
            footer = b'\r\n'
            chunk = boundary + header + frame_bytes + footer
            
            # 8. In-Memory Stats Update
            if frame_count % 10 == 0:
                active_stats[stream_id] = {
                    'detections': sum(class_counts.values()),
                    'class_counts': class_counts.copy()
                }

            yield chunk

        cap.release()
        if out_writer is not None:
            try:
                out_writer.release()
            except Exception:
                pass
        
        # Save class counts to JSON file
        total_unique = sum(class_counts.values())
        stats_file = output_path + '.stats.json'
        try:
            with open(stats_file, 'w') as f:
                json.dump({
                    'detections': total_unique, 
                    'class_counts': class_counts,
                    'frames': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) if hasattr(cap, 'get') else frame_count,
                    'filename': output_filename
                }, f)
            print(f"Saved stats: {total_unique} unique objects, {len(class_counts)} classes, frames: {frame_count}")
        except Exception as e:
            print(f"Error saving stats: {e}")
        
        # Record Global Stats
        global_stats.record(user_name, total_unique, class_counts)
        
        # Create a marker file
        marker_file = output_path + '.done'
        try:
            with open(marker_file, 'w') as f:
                f.write('done')
        except Exception:
            pass

        if stream_id in active_stats:
            del active_stats[stream_id]
        
        # Immediate Cleanup of Original Upload for Video
        delete_file(filepath)
    except Exception as e:
        print(f"Stream error: {e}")
