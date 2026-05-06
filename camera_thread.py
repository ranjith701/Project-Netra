import cv2
import threading
import time
from datetime import datetime

class CameraThread:
    def __init__(self, src=0, name="Camera"):
        self.src = src
        self.name = name
        # Use DirectShow on Windows for faster startup
        self.cap = cv2.VideoCapture(self.src, cv2.CAP_DSHOW if isinstance(self.src, int) else cv2.CAP_FFMPEG)
        
        # --- CRITICAL FIX: HARDWARE RESOLUTION LIMIT ---
        # Force camera to 720p. This prevents CPU overload.
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        self.ret, self.frame = self.cap.read()
        self.running = True
        self.lock = threading.Lock()
        
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()

    def update(self):
        while self.running:
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    with self.lock:
                        self.ret = ret
                        self.frame = frame
                else:
                    time.sleep(0.1) 
            else:
                time.sleep(1)

    def read(self):
        with self.lock:
            return (self.frame.copy() if self.frame is not None else None), datetime.now()

    def stop(self):
        self.running = False
        self.thread.join()
        self.cap.release()