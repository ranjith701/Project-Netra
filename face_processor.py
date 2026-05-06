# """
# AI Engine Wrapper.
# Handles InsightFace model loading, detection, and Optimized Image Saving with Passport-style background.
# """
# import os
# import cv2
# import numpy as np
# import threading
# import time
# from insightface.app import FaceAnalysis
# import config
# import database_manager as db  

# class FaceProcessor:
#     def __init__(self, debug=True):
#         self.debug = debug
#         self.app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
#         self.app.prepare(ctx_id=0, det_size=(640, 640))
        
#         self.known_embeddings = []
#         self.known_ids = []
#         self.known_names = []
        
#         self.last_unknown_save = 0
#         self.save_cooldown = 10 
        
#         self.load_known_embeddings()

#     def load_known_embeddings(self):
#         """Caches face embeddings in RAM and maps IDs to real Names."""
#         self.known_embeddings = []
#         self.known_ids = []
#         self.known_names = []
        
#         if not os.path.exists(config.DB_PATH): return

#         print("🔍 Loading Gallery into RAM...")
#         for user_id in os.listdir(config.DB_PATH):
#             user_folder = os.path.join(config.DB_PATH, user_id)
#             if not os.path.isdir(user_folder): continue
            
#             real_name = db.get_employee_name_by_id(user_id)
            
#             for file in os.listdir(user_folder):
#                 if file.lower().endswith(('.png', '.jpg', '.jpeg')):
#                     img_path = os.path.join(user_folder, file)
#                     img = cv2.imread(img_path)
#                     if img is None: continue
                    
#                     faces = self.app.get(img)
#                     if faces:
#                         faces = sorted(faces, key=lambda x: (x.bbox[2]-x.bbox[0])*(x.bbox[3]-x.bbox[1]), reverse=True)
#                         emb = getattr(faces[0], "normed_embedding", None)
#                         if emb is not None:
#                             self.known_embeddings.append(emb)
#                             self.known_ids.append(user_id)
#                             self.known_names.append(real_name)

#         if self.debug: print(f"✅ Loaded {len(self.known_embeddings)} samples for {len(set(self.known_ids))} users.")

#     def detect_and_recognize(self, frame):
#         return self.app.get(frame)

#     def find_match(self, target_embedding, threshold=0.55):
#         if target_embedding is None or not self.known_embeddings:
#             return None, "Unknown", 0.0

#         sims = np.dot(self.known_embeddings, target_embedding)
#         best_idx = np.argmax(sims)
#         score = sims[best_idx]

#         if score > threshold:
#             return self.known_ids[best_idx], self.known_names[best_idx], score
        
#         return None, "Unknown", score

#     # --- UPDATED: PASSPORT STYLE SAVING ---

#     def _create_passport_photo(self, face_img, size=300):
#         """Creates a white background canvas and centers the face crop."""
#         try:
#             h, w = face_img.shape[:2]
#             # Create a solid white square canvas
#             canvas = np.full((size, size, 3), 255, dtype=np.uint8)

#             # Determine scaling to fit face into the square while keeping margins
#             scale = (size * 0.7) / max(h, w)
#             new_w, new_h = int(w * scale), int(h * scale)
#             resized_face = cv2.resize(face_img, (new_w, new_h))

#             # Calculate centering coordinates
#             x_offset = (size - new_w) // 2
#             y_offset = (size - new_h) // 2

#             # Place face on white canvas
#             canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized_face
#             return canvas
#         except Exception as e:
#             print(f"Canvas Error: {e}")
#             return face_img

#     def _background_writer(self, path, img):
#         try:
#             cv2.imwrite(path, img)
#         except Exception as e:
#             print(f"Save Error: {e}")

#     def save_sample(self, face_img, folder):
#         """Processes image to Passport-style and saves Async."""
#         # Step 1: Convert the raw crop to Passport style
#         passport_photo = self._create_passport_photo(face_img)

#         timestamp = int(time.time())
#         filename = f"cap_{timestamp}_{np.random.randint(100,999)}.jpg"
#         path = os.path.join(folder, filename)
#         os.makedirs(folder, exist_ok=True)
        
#         # Step 2: Write to disk in background
#         threading.Thread(target=self._background_writer, args=(path, passport_photo)).start()

#     def handle_unknown_face(self, face_img):
#         now = time.time()
#         if now - self.last_unknown_save > self.save_cooldown:
#             self.save_sample(face_img, config.UNLABELED_DIR)
#             self.last_unknown_save = now
#             if self.debug: print("📸 Unknown passport-style face saved")

"""
AI Engine Wrapper.
Optimized for High-Quality Passport Saving and Sharpened Face Recognition.
"""
import os
import cv2
import numpy as np
import threading
import time
from insightface.app import FaceAnalysis
import config
import database_manager as db  

class FaceProcessor:
    def __init__(self, debug=True):
        self.debug = debug
        # Buffalo_L is the most accurate model for recognition
        self.app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
        self.app.prepare(ctx_id=0, det_size=(640, 640))
        
        self.known_embeddings = []
        self.known_ids = []
        self.known_names = []
        
        self.last_unknown_save = 0
        self.save_cooldown = 10 
        
        self.load_known_embeddings()

    def load_known_embeddings(self):
        """Caches face embeddings in RAM and maps IDs to real Names."""
        self.known_embeddings = []
        self.known_ids = []
        self.known_names = []
        
        if not os.path.exists(config.DB_PATH): return

        if self.debug: print("🔍 Loading Gallery into RAM...")
        for user_id in os.listdir(config.DB_PATH):
            user_folder = os.path.join(config.DB_PATH, user_id)
            if not os.path.isdir(user_folder): continue
            
            real_name = db.get_employee_name_by_id(user_id)
            
            for file in os.listdir(user_folder):
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    img_path = os.path.join(user_folder, file)
                    img = cv2.imread(img_path)
                    if img is None: continue
                    
                    faces = self.app.get(img)
                    if faces:
                        faces = sorted(faces, key=lambda x: (x.bbox[2]-x.bbox[0])*(x.bbox[3]-x.bbox[1]), reverse=True)
                        emb = getattr(faces[0], "normed_embedding", None)
                        if emb is not None:
                            self.known_embeddings.append(emb)
                            self.known_ids.append(user_id)
                            self.known_names.append(real_name)

        if self.debug: print(f"✅ Loaded {len(self.known_embeddings)} face samples.")

    def detect_and_recognize(self, frame):
        return self.app.get(frame)

    def find_match(self, target_embedding, threshold=0.55):
        if target_embedding is None or not self.known_embeddings:
            return None, "Unknown", 0.0

        sims = np.dot(self.known_embeddings, target_embedding)
        best_idx = np.argmax(sims)
        score = sims[best_idx]

        if score > threshold:
            return self.known_ids[best_idx], self.known_names[best_idx], score
        
        return None, "Unknown", score

    # --- ENHANCED: HIGH QUALITY PASSPORT LOGIC ---

    def _create_passport_photo(self, face_img, size=400):
        """Creates a sharpened, high-quality white background canvas."""
        try:
            h, w = face_img.shape[:2]
            
            # 1. Apply Sharpening Filter to improve "blurry" zoomed faces
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            face_img = cv2.filter2D(face_img, -1, kernel)

            # 2. Create white square canvas (increased to 400 for better detail)
            canvas = np.full((size, size, 3), 255, dtype=np.uint8)

            # 3. Determine scaling (70% coverage)
            scale = (size * 0.7) / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            
            # 4. Use INTER_LANCZOS4 (Best for upscaling quality)
            resized_face = cv2.resize(face_img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

            # 5. Calculate centering
            x_offset = (size - new_w) // 2
            y_offset = (size - new_h) // 2

            canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized_face
            return canvas
        except Exception as e:
            if self.debug: print(f"Quality Error: {e}")
            return face_img

    def _background_writer(self, path, img):
        """Save with 100% JPEG quality."""
        try:
            cv2.imwrite(path, img, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
        except Exception as e:
            if self.debug: print(f"Write Error: {e}")

    def save_sample(self, face_img, folder):
        """Async high-quality save."""
        passport_photo = self._create_passport_photo(face_img)
        timestamp = int(time.time())
        filename = f"cap_{timestamp}_{np.random.randint(100,999)}.jpg"
        path = os.path.join(folder, filename)
        os.makedirs(folder, exist_ok=True)
        
        threading.Thread(target=self._background_writer, args=(path, passport_photo)).start()

    def handle_unknown_face(self, face_img):
        now = time.time()
        if now - self.last_unknown_save > self.save_cooldown:
            self.save_sample(face_img, config.UNLABELED_DIR)
            self.last_unknown_save = now
            if self.debug: print("📸 Sharp passport-style face saved.")