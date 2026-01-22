import sys, os, traceback
YOLOV6_DIR = r"c:\Work\project bootcamp\last project\YOLOv6"
if YOLOV6_DIR not in sys.path:
    sys.path.insert(0, YOLOV6_DIR)
print('PYTHONPATH prepended:', YOLOV6_DIR)

try:
    print('Importing yolov6.layers.common DetectBackend...')
    from yolov6.layers.common import DetectBackend
    print('Imported DetectBackend ->', DetectBackend)
except Exception as e:
    print('Import error:', e)
    traceback.print_exc()

# Show any loaded yolov6.tools or tools.infer modules
loaded_tools = [m for m in sys.modules.keys() if 'yolov6' in m and ('tools' in m or 'infer' in m)]
print('Loaded yolov6 tools modules:', loaded_tools)

print('Done')
