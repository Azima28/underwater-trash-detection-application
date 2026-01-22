# Troubleshooting YOLOv8/v6 Streaming Issues

## Analysis & Fixes Applied

### Problem 1: Black Video Stream (YOLOv8)
**Root Cause**: 
- `infer_frame()` return format inconsistent (not always wrapped in list)
- Frame encoding or format issues

**Fixes Applied**:
1. Simplified `infer_frame()` to always return list format
2. Added safety checks for `results[0]`
3. Improved JPEG encoding with validation
4. Frame format validation (BGR/grayscale conversion)
5. Frame size matching to VideoWriter dimensions

### Problem 2: YOLOv6 No Streaming (Waiting Only)
**Root Cause**:
- Model loading might have different behavior
- Flask auto-reload interrupting
- Inference method differences

**Fixes Applied**:
1. Unified model loading for v6 & v8
2. Disabled Flask auto-reload (`use_reloader=False`)
3. Used consistent `infer_frame()` wrapper for both
4. Added error handling and debug output

### Problem 3: MJPEG Stream Issues
**Root Cause**:
- Multipart boundary not consistent
- Frame encoding failures not caught
- Missing initial frame validation

**Fixes Applied**:
1. Improved MJPEG boundary format
2. Added frame validation before processing
3. Added encoding success check
4. Better error logging

## Key Code Changes

### 1. `infer_frame()` function (Lines 113-132)
```python
def infer_frame(model, frame, conf=0.5):
    results = model(frame, verbose=False, conf=conf)
    
    # Always return as list
    if not isinstance(results, (list, tuple)):
        results = [results]
    
    return results
```

### 2. Frame validation in generate_frames (Lines 247-252)
```python
if frame is None or frame.size == 0:
    continue

if len(frame.shape) != 3:
    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
```

### 3. MJPEG encoding (Lines 333-346)
```python
success, buffer = cv2.imencode('.jpg', annotated_frame)
if not success:
    continue

frame_bytes = bytes(buffer)
boundary = b'--frame\r\n'
header = b'Content-Type: image/jpeg\r\nContent-Length: ' + str(len(frame_bytes)).encode() + b'\r\n\r\n'
yield boundary + header + frame_bytes + b'\r\n'
```

## Testing Checklist

- [ ] Restart Flask: `python app.py`
- [ ] Upload video with **YOLOv8**
  - [ ] Stream should show frames (not black)
  - [ ] FPS counter visible in top-left
  - [ ] Video saves to output folder
  - [ ] Download button appears
  
- [ ] Upload video with **YOLOv6**
  - [ ] Stream should show frames (same as v8)
  - [ ] FPS counter visible
  - [ ] Video saves
  - [ ] No interruptions/reloads

- [ ] Upload **image** with YOLOv8
  - [ ] Should work as before
  - [ ] Shows detections
  - [ ] Download available

## Debug Output

Watch Flask console for messages like:
```
Starting stream: 20251221_161540, model: v8
Video dims: 1920x1080, fps: 30
Frame 30: encoded 45000 bytes
Frame 60: encoded 42000 bytes
```

If you see errors, they will appear here. Common issues:
- `Inference error` - Model loading problem
- `Failed to encode frame` - Video format issue
- `Frame write error` - VideoWriter problem
- `Frame inference failed` - Model execution issue

## Next Steps if Still Not Working

1. Check Flask server logs (post them here)
2. Check browser console (F12 → Console tab)
3. Verify model files exist:
   - `yolov6.pt`
   - `yolov8n.pt` atau similar
4. Test with small video file first
