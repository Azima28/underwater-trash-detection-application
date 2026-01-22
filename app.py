from flask import Flask, render_template, request, send_file, jsonify, Response, send_from_directory
import cv2
import os
import uuid

from utils.config_loader import config
from utils.model import get_model
from utils.processors import process_image
from services.stats_service import GlobalTracker
from services.video_service import generate_frames
from services.cleanup_service import clear_folders, start_cleanup_worker, delete_file
import subprocess
import webbrowser
import threading

# Initialize services
global_stats = GlobalTracker()
active_stats = {} # {stream_id: {'detections': N, 'class_counts': {}}}

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = config.get('server.max_content_length_mb', 500) * 1024 * 1024
app.config['UPLOAD_FOLDER'] = config.get('folders.upload', 'uploads')
app.config['OUTPUT_FOLDER'] = config.get('folders.output', 'outputs')

# Create and Clear folders on startup
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
clear_folders([app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER']])

# Start background cleanup worker
start_cleanup_worker(
    [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER']], 
    interval=config.get('cleanup.interval_seconds', 300), 
    max_age=config.get('cleanup.max_age_seconds', 900)
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analytics')
def analytics():
    """Render the dashboard wrapper for Streamlit embedding"""
    return render_template('analytics.html')

@app.route('/api/stats')
def get_global_stats():
    return jsonify(global_stats.get_stats())

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        # Cek file ada
        if 'file' not in request.files:
            return jsonify({'error': 'Tidak ada file'}), 400
        
        file = request.files['file']
        model_choice = request.form.get('model', 'v8')
        user_name = request.form.get('contributor', 'EcoCitizen')
        
        if file.filename == '':
            return jsonify({'error': 'File tidak dipilih'}), 400
        
        # Validasi ekstensi
        allowed_ext = {'.png', '.jpg', '.jpeg', '.bmp', '.mp4', '.avi', '.mov', '.mkv'}
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed_ext:
            return jsonify({'error': f'Format tidak didukung: {ext}'}), 400
        
        # Simpan file
        filename = str(uuid.uuid4()) + "_" + file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Load model
        model = get_model(model_choice)
        
        # Process file
        result_filename = f"result_{filename}"
        result_path = os.path.join(app.config['OUTPUT_FOLDER'], result_filename)
        
        if ext in ['.png', '.jpg', '.jpeg', '.bmp']:
            detections_count, class_counts = process_image(model, filepath, result_path)
            
            # Record Global Stats
            global_stats.record(user_name, detections_count, class_counts)
            
            # Immediate Cleanup of Original Upload (Image is now in output folder)
            delete_file(filepath)
            
            return jsonify({
                'type': 'image',
                'filename': result_filename,
                'detections': detections_count,
                'class_counts': class_counts,
                'model': model_choice,
                'contributor': user_name
            })
        else:
            # Video stream processing indicator
            return jsonify({
                'success': True,
                'type': 'video',
                'stream_id': filename.replace(ext, ''),
                'model': model_choice,
                'contributor': user_name
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stream/<stream_id>')
def stream_video(stream_id):
    """Live stream video processing - real-time output"""
    filepath = None
    
    # Find uploaded file
    for ext in ['.mp4', '.avi', '.mov', '.mkv']:
        test_path = os.path.join(app.config['UPLOAD_FOLDER'], stream_id + ext)
        if os.path.exists(test_path):
            filepath = test_path
            break
    
    if not filepath:
        return jsonify({'error': 'File tidak ditemukan'}), 404
    
    # Capture choices from request Context
    model_choice = request.args.get('model', 'v8')
    user_name = request.args.get('contributor', 'EcoCitizen')

    return Response(
        generate_frames(
            filepath, model_choice, user_name, stream_id, 
            app.config, global_stats, active_stats
        ),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/download/<filename>')
def download_file(filename):
    """Download hasil processing"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'File tidak ditemukan'}), 404
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/image/<filename>')
def serve_image(filename):
    """Serve result image file"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'File tidak ditemukan'}), 404
        return send_file(filepath, mimetype='image/jpeg')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/status/<stream_id>')
def stream_status(stream_id):
    """Check whether processed output for stream_id is ready for download"""
    output_filename = f"result_{stream_id}.mp4"
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
    marker_file = output_path + '.done'
    stats_file = output_path + '.stats.json'
    
    is_ready = os.path.exists(marker_file)
    
    # 1. Prioritize In-Memory Active Stats
    if stream_id in active_stats:
        s = active_stats[stream_id]
        return jsonify({
            'ready': is_ready,
            'filename': output_filename,
            'detections': s['detections'],
            'class_counts': s['class_counts'],
            'status': 'processing' if not is_ready else 'done'
        })

    # 2. Fallback to stats file
    stats = {'detections': 0, 'class_counts': {}, 'frames': 0}
    if os.path.exists(stats_file):
        try:
            import json
            with open(stats_file, 'r') as f:
                stats = json.load(f)
        except Exception as e:
            print(f"Error reading stats: {e}")
    
    return jsonify({
        'ready': is_ready, 
        'filename': output_filename,
        'detections': stats.get('detections', 0),
        'class_counts': stats.get('class_counts', {}),
        'frames': stats.get('frames', 0),
        'status': 'done' if is_ready else 'processing'
    })

if __name__ == '__main__':
    # Start Streamlit in Background
    def run_streamlit():
        try:
            import sys
            import shutil
            streamlit_port = config.get('server.streamlit_port', 8501)
            
            # Check if streamlit is available as a module in current environment
            has_module = False
            try:
                import streamlit
                has_module = True
            except ImportError:
                has_module = False

            if has_module:
                cmd = [sys.executable, "-m", "streamlit", "run", "dashboard.py", 
                       "--server.port", str(streamlit_port), "--server.headless", "true"]
                print(f"[*] Starting Streamlit as module on port {streamlit_port}")
            elif shutil.which("streamlit"):
                cmd = ["streamlit", "run", "dashboard.py", 
                       "--server.port", str(streamlit_port), "--server.headless", "true"]
                print(f"[*] Starting Streamlit as global command on port {streamlit_port}")
            else:
                print("[-] Error: Streamlit not found. Please install it with 'pip install streamlit'")
                return

            subprocess.Popen(cmd)
        except Exception as e:
            print(f"[-] Error starting Streamlit: {e}")

    threading.Thread(target=run_streamlit, daemon=True).start()

    app.run(
        debug=config.get('server.debug', True), 
        use_reloader=True, 
        host=config.get('server.host', '0.0.0.0'), 
        port=config.get('server.port', 5000)
    )
