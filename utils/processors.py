import os
import cv2
import time
import json
from flask import jsonify
from .config_loader import config
from .model import infer_frame
from .tracking import CentroidTracker

def process_image(model, input_path, output_path):
    """Process gambar dan return raw data"""
    try:
        img = cv2.imread(input_path)
        if img is None:
            return 0, {}
        
        # Use same inference method as video for consistency
        results = infer_frame(model, img, conf=config.get('processing.inference_conf', 0.25))
        
        if not results or len(results) == 0 or results[0] is None:
            return 0, {}
        
        annotated_img = results[0].plot()
        cv2.imwrite(output_path, annotated_img)
        
        # Count objects per class
        class_counts = {}
        if results[0].boxes:
            try:
                for box in results[0].boxes:
                    class_id = int(box.cls[0])
                    # Try different ways to get class name
                    if hasattr(model, 'names') and model.names:
                        class_name = model.names.get(class_id, f'Class {class_id}') if isinstance(model.names, dict) else model.names[class_id]
                    elif hasattr(results[0], 'names') and results[0].names:
                        class_name = results[0].names.get(class_id, f'Class {class_id}') if isinstance(results[0].names, dict) else results[0].names[class_id]
                    else:
                        class_name = f'Class {class_id}'
                    
                    class_counts[class_name] = class_counts.get(class_name, 0) + 1
            except Exception as e:
                print(f"Error counting classes: {e}")
                class_counts = {}
        
        return (len(results[0].boxes) if results[0].boxes else 0), class_counts
    except Exception as e:
        print(f"process_image error: {e}")
        return 0, {}

def process_video(filepath, model, timestamp, output_folder):
    """Process video dengan centroid tracking untuk avoid double counting"""
    try:
        cap = cv2.VideoCapture(filepath)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        output_filename = f"result_{timestamp}.mp4"
        output_path = os.path.join(output_folder, output_filename)
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        frame_count = 0
        prev_time = time.time()
        
        # Tracking untuk unique objects per class
        ct = CentroidTracker(max_disappeared=40, max_distance=50)
        unique_objects = {}  # {class_name: set of object IDs}
        class_counts = {}    # {class_name: count of unique objects}
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Predict - use robust wrapper to support both v8 and v6
            results = infer_frame(model, frame, conf=0.5)
            annotated_frame = results[0].plot()
            
            # Hitung FPS (sesuai yolov8.py)
            curr_time = time.time()
            dt = curr_time - prev_time if curr_time - prev_time > 0 else 1e-6
            fps_display = 1.0 / dt
            prev_time = curr_time
            
            # Draw FPS
            cv2.putText(annotated_frame, f"FPS: {fps_display:.1f}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            
            # Group current detections by class with centroid tracking
            rects = []
            input_class_names = []
            
            if results and len(results) > 0 and results[0].boxes:
                for box in results[0].boxes:
                    try:
                        coords = box.xyxy[0].cpu().numpy().astype(int)
                        x1, y1, x2, y2 = coords
                        cls_id = int(box.cls[0])
                        
                        # Get class name
                        if hasattr(model, 'names') and model.names:
                            class_name = model.names.get(class_id, f'Class {class_id}') if isinstance(model.names, dict) else model.names[cls_id]
                        elif hasattr(results[0], 'names') and results[0].names:
                            class_name = results[0].names.get(class_id, f'Class {class_id}') if isinstance(results[0].names, dict) else results[0].names[class_id]
                        else:
                            class_name = f'Class {class_id}'
                        
                        rects.append((x1, y1, x2, y2))
                        input_class_names.append(class_name)
                    except Exception:
                        continue
            
            # Update Tracker
            objects, obj_class_names = ct.update(rects, input_class_names)
            
            # Update Stats and Draw ID on annotated_frame (from plot)
            for (objectID, centroid) in objects.items():
                # Update stats
                class_name = obj_class_names.get(objectID, "Unknown")
                if class_name not in unique_objects:
                    unique_objects[class_name] = set()
                
                unique_objects[class_name].add(objectID)
                class_counts[class_name] = len(unique_objects[class_name])
                
                # Draw ID - Thinner
                # Only draw if the object is currently detected (disappeared == 0)
                if ct.disappeared[objectID] == 0:
                    text = f"ID {objectID}"
                    cv2.putText(annotated_frame, text, (centroid[0] - 10, centroid[1] - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                    cv2.circle(annotated_frame, (centroid[0], centroid[1]), 3, (0, 255, 0), -1)
            
            out.write(annotated_frame)
            frame_count += 1
        
        cap.release()
        out.release()
        
        # Return total unique objects across all classes
        total_unique = sum(class_counts.values())
        
        return jsonify({
            'success': True,
            'filename': output_filename,
            'type': 'video',
            'model': 'v8',
            'frames': frame_count,
            'detections': total_unique,
            'class_counts': class_counts
        })
    except Exception as e:
        return jsonify({'error': f'Error processing video: {str(e)}'}), 500
