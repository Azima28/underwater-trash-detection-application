from ultralytics import YOLO, RTDETR
import os

from .config_loader import config

# Path ke model custom (sesuai config.yaml)
MODELS_DIR = config.get('folders.models', 'models')
YOLOV8_MODEL_PATH = os.path.join(MODELS_DIR, config.get('models.yolov8', 'yolov8n.pt'))
YOLOV11_MODEL_PATH = os.path.join(MODELS_DIR, config.get('models.yolov11', 'yolov11.pt'))
RTDETR_MODEL_PATH = os.path.join(MODELS_DIR, config.get('models.rtdetr', 'rtdetr.pt'))

# Load models (lazy loading saat dibutuhkan)
models = {}

def get_model(model_type=None):
    """Get atau load model YOLOv8 atau RT-DETR"""
    if model_type is None:
        model_type = config.get('models.default', 'v8')
    
    if model_type not in models:
        try:
            if model_type == 'rtdetr':
                path = RTDETR_MODEL_PATH
                print(f"Loading RT-DETR from {path}...")
                model = RTDETR(path)
            elif model_type == 'v11':
                path = YOLOV11_MODEL_PATH
                print(f"Loading YOLOv11 from {path}...")
                model = YOLO(path)
            else:
                # Default to YOLOv8
                path = YOLOV8_MODEL_PATH
                print(f"Loading YOLOv8 from {path}...")
                model = YOLO(path)
            
            # Move to GPU if available
            try:
                model.to("cuda:0")
            except Exception as e:
                print(f"Info: Could not move model {model_type} to GPU: {e}")

            models[model_type] = model
        except Exception as e:
            print(f"Error load model {model_type}: {e}")
            raise
    return models[model_type]


def infer_frame(model, frame, conf=0.5):
    """Standard inference wrapper for YOLO11/YOLOv8/RT-DETR.
    Tuned for MAXIMUM detection quality.
    """
    try:
        # Standard procedure for high-quality environmental monitoring:
        # 1. Use official default confidence (0.25) as baseline for all models
        # 2. Use full precision (FP32) to ensure small trash particles are not missed
        # 3. Use standard resolution (imgsz=640)
        target_conf = 0.25 
        target_half = False # Full FP32 precision for all models now
        
        # Using model.predict() is the formal procedure for passing arguments
        results = model.predict(
            frame, 
            verbose=False, 
            conf=target_conf, 
            half=target_half,
            imgsz=640
        )
        
        if not isinstance(results, (list, tuple)):
            results = [results]
        return results
    except Exception as e:
        print(f"Inference error: {e}")
        import traceback
        traceback.print_exc()
        # Return empty result to continue processing
        from ultralytics.engine.results import Results
        return [Results(orig_img=frame, path=None, names=[], boxes=[])]
