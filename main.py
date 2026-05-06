import os
import sys
import cv2
import time
import json
import math
import threading
import queue
import numpy as np

# --- DLL INJECTION FOR NVIDIA CUDA 12 ---
try:
    import nvidia.cudnn
    import nvidia.cublas
    
    def add_nvidia_path(module):
        base_path = os.path.dirname(module.__file__)
        bin_path = os.path.join(base_path, "bin")
        lib_path = os.path.join(base_path, "lib")
        if os.path.exists(bin_path):
            os.add_dll_directory(bin_path)
        elif os.path.exists(lib_path):
            os.add_dll_directory(lib_path)

    add_nvidia_path(nvidia.cudnn)
    add_nvidia_path(nvidia.cublas)
    print("✅ NVIDIA GPU Drivers Injected.")
except Exception:
    pass

# --- PROJECT IMPORTS ---
import config
import database_manager as db
from face_processor import FaceProcessor
from camera_thread import CameraThread 
from firebase_attendance import log_attendance_cloud, sync_dashboard_settings

# --- GLOBAL SHARED STATE ---
latest_ai_results = {}
results_lock = threading.Lock()

class AIWorker(threading.Thread):
    def __init__(self, face_processor, db_path):
        super().__init__()
        self.face_proc = face_processor
        self.db_path = db_path
        self.input_queue = queue.Queue(maxsize=1)
        self.running = True
        self.last_seen = {} 

    def run(self):
        while self.running:
            try:
                task = self.input_queue.get(timeout=0.01)
            except queue.Empty:
                continue

            cam_index, frame, frame_time, cam_config = task
            try:
                # Resize for AI speed - using 480p is standard for high-speed detection
                h, w = frame.shape[:2]
                ai_scale = 480 / w
                small_frame = cv2.resize(frame, (480, int(h * ai_scale)))

                faces = self.face_proc.detect_and_recognize(small_frame)
                processed_faces = []

                for face in faces:
                    # 1. IDENTIFICATION & RECOGNITION
                    emb = getattr(face, "normed_embedding", None)
                    emp_id, emp_name, score = self.face_proc.find_match(emb)
                    
                    is_identified = emp_id and score >= config.ATTENDANCE_SCORE

                    # 2. LOG ATTENDANCE (Local & Cloud)
                    if is_identified:
                        now = time.time()
                        # Cooldown prevents multi-logging within a few seconds
                        if emp_id not in self.last_seen or (now - self.last_seen[emp_id] > config.COOLDOWN_PERIOD):
                            
                            role = db.get_employee_role(emp_id)
                            c_type = cam_config.get("type", "Entry")
                            c_name = cam_config.get("name", f"Cam {cam_index}")

                            # Local SQLite Log
                            db.log_attendance(
                                employee_name=emp_name, 
                                capture_time=frame_time, 
                                log_type=c_type, 
                                camera_name=c_name
                            ) 
                            
                            # Firebase Cloud Sync
                            log_attendance_cloud(
                                emp_id, 
                                emp_name, 
                                role, 
                                frame_time, 
                                c_type
                            )
                            
                            self.last_seen[emp_id] = now
                            print(f"✅ [{c_type}] Logged: {emp_name} at {c_name}")

                    # 3. POSE & QUALITY CHECK (For auto-dataset collection)
                    kps = face.kps
                    eye_dist = np.linalg.norm(kps[0] - kps[1])
                    yaw_offset = abs(abs(kps[2][0] - kps[1][0]) - abs(kps[2][0] - kps[0][0])) / (eye_dist + 1e-6)
                    
                    if face.det_score >= config.COLLECTION_SCORE and yaw_offset < config.POSE_STRICTNESS:
                        box = face.bbox.astype(int)
                        x1, y1, x2, y2 = max(0, box[0]), max(0, box[1]), min(small_frame.shape[1], box[2]), min(small_frame.shape[0], box[3])
                        face_crop = small_frame[y1:y2, x1:x2]

                        if face_crop.size > 0:
                            if emp_id:
                                user_dir = os.path.join(self.db_path, str(emp_id))
                                os.makedirs(user_dir, exist_ok=True)
                                if len(os.listdir(user_dir)) < config.MAX_IMAGES_PER_USER:
                                    self.face_proc.save_sample(face_crop, user_dir)
                            else:
                                self.face_proc.handle_unknown_face(face_crop)

                    # 4. PREPARE RESULTS FOR DISPLAY
                    display_name = emp_name if emp_id else "Unknown"
                    label = f"{display_name} ({int(score*100)}%)"
                    color = (0, 255, 0) if is_identified else (0, 0, 255)
                    processed_faces.append((label, color, (face.bbox / ai_scale).astype(int)))

                with results_lock:
                    latest_ai_results[cam_index] = processed_faces
            except Exception as e:
                print(f"AI Worker Error: {e}")

    def process_frame(self, cam_index, frame, frame_time, config):
        if self.input_queue.full():
            try: self.input_queue.get_nowait()
            except: pass
        self.input_queue.put((cam_index, frame, frame_time, config))

    def stop(self):
        self.running = False

def create_grid(frames, screen_width=1280, screen_height=720):
    count = len(frames)
    if count == 0: return np.zeros((screen_height, screen_width, 3), dtype=np.uint8)
    cols = math.ceil(math.sqrt(count))
    rows = math.ceil(count / cols)
    tile_w, tile_h = screen_width // cols, screen_height // rows
    canvas = np.zeros((screen_height, screen_width, 3), dtype=np.uint8)
    for idx, img in enumerate(frames):
        r, c = divmod(idx, cols)
        if img is not None:
            resized = cv2.resize(img, (tile_w, tile_h))
            canvas[r*tile_h:(r+1)*tile_h, c*tile_w:(c+1)*tile_w] = resized
    return canvas

def main():
    db.setup_database()
    
    # 1. Load Settings and Sync Dashboard Mode to Cloud
    try:
        with open(config.SETTINGS_FILE, 'r') as f:
            settings = json.load(f)
            cams_conf = [c for c in settings.get('cameras_advanced', []) if c.get('enabled', True)]
    except Exception as e:
        print(f"⚠️ Error loading settings: {e}")
        cams_conf = [{"url": 0, "name": "Default", "type": "Entry"}]

    # Sync to Cloud (Tells hosted dashboard whether to hide/show columns)
    sync_dashboard_settings(cams_conf)

    # 2. Initialize Hardware and Workers
    face_proc = FaceProcessor(debug=False)
    
    camera_threads = []
    for c in cams_conf:
        src = int(c['url']) if str(c['url']).isdigit() else c['url']
        cam = CameraThread(src, name=c['name'])
        camera_threads.append(cam)

    ai_worker = AIWorker(face_proc, config.DB_PATH)
    ai_worker.start()

    frame_counter = 0
    try:
        while True:
            frame_counter += 1
            frames_to_show = []
            
            for i, cam in enumerate(camera_threads):
                frame, frame_time = cam.read()
                if frame is None:
                    frames_to_show.append(None)
                    continue

                # Process every 3rd frame to save resources (Adjust to 5 for 10+ cameras)
                if frame_counter % 3 == 0 and not ai_worker.input_queue.full():
                    ai_worker.process_frame(i, frame.copy(), frame_time, cams_conf[i])

                # Draw latest detections
                with results_lock:
                    for (name, col, box) in latest_ai_results.get(i, []):
                        cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), col, 2)
                        cv2.putText(frame, name, (box[0], box[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, col, 2)
                
                frames_to_show.append(frame)

            # Display Grid
            cv2.imshow('Netra AI Multi-Cam Dashboard', create_grid(frames_to_show))
            
            if cv2.waitKey(1) == ord('q'):
                break
    finally:
        ai_worker.stop()
        for c in camera_threads: c.stop()
        cv2.destroyAllWindows()
        ai_worker.join()
        print("🛑 System Shut Down.")

if __name__ == "__main__":
    main()