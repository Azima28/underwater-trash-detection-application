from ultralytics import YOLO
import cv2
import os
import time
from datetime import datetime

# Path ke model YOLOv8 best.pt
model_path = r"c:\Users\agust\Downloads\train5\kaggle\working\train5\weights\best.pt"
source_path = r"C:\Work\project bootcamp\last project\_So_much_plastic_British_diver_films_deluge_of_waste_off_Bali_720P.mp4"  # bisa gambar atau video

# Folder output
output_folder = r"C:\Work\project bootcamp\last project\output"
os.makedirs(output_folder, exist_ok=True)  # buat folder kalau belum ada

# Buat nama file unik berdasarkan timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Load model YOLOv8 dan pakai GPU device 0
model = YOLO(model_path)
model.to("cuda:0")  # pakai GPU 0

# Cek ekstensi file
ext = os.path.splitext(source_path)[1].lower()
if ext in ['.png', '.jpg', '.jpeg', '.bmp']:
    # --- Proses gambar ---
    img = cv2.imread(source_path)
    results = model(img)
    annotated_img = results[0].plot()
    
    # Tampilkan hasil
    cv2.imshow("YOLOv8 Prediction", annotated_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    # Simpan hasil
    output_path = os.path.join(output_folder, f"predicted_{timestamp}{ext}")
    cv2.imwrite(output_path, annotated_img)
    print(f"Prediksi gambar selesai, hasil disimpan di: {output_path}")

elif ext in ['.mp4', '.avi', '.mov', '.mkv']:
    # --- Proses video ---
    cap = cv2.VideoCapture(source_path)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30  # default 30 jika FPS 0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    output_path = os.path.join(output_folder, f"predicted_{timestamp}.mp4")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    prev_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Predict frame
        results = model(frame)
        annotated_frame = results[0].plot()
        # Hitung FPS berdasarkan selisih waktu antar frame (termasuk inference)
        curr_time = time.time()
        dt = curr_time - prev_time if curr_time - prev_time > 0 else 1e-6
        fps_display = 1.0 / dt
        prev_time = curr_time
        # Gambar FPS di pojok kiri atas
        cv2.putText(annotated_frame, f"FPS: {fps_display:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        
        # Tampilkan frame
        cv2.imshow("YOLOv8 Prediction", annotated_frame)
        
        # Write frame ke video output
        out.write(annotated_frame)
        
        # Tekan 'q' untuk keluar lebih cepat
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print(f"Prediksi video selesai, hasil disimpan di: {output_path}")

else:
    print("Format file tidak didukung! Harus gambar (.png/.jpg) atau video (.mp4/.avi).")
