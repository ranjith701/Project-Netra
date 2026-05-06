"""
Global Configuration Variables.
Actual user settings (cameras, skip, GPU) are now stored in 'settings.json'.
"""
import os

# --- PATHS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database")
UNLABELED_DIR = os.path.join(BASE_DIR, "unlabeled_faces")
DB_NAME = "netra.db"
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

# --- USER EXPECTATION & AI SETTINGS ---
# Recognition & Collection Thresholds
COLLECTION_SCORE = 0.70      # Only save if very confident and clear
ATTENDANCE_SCORE = 0.30      # Mark attendance at 65% confidence per expectation
MAX_IMAGES_PER_USER = 5      # Stop collecting after 5 images per user
POSE_STRICTNESS = 0.25       # Ensure face is perfectly front-facing for the dataset

# --- ATTENDANCE LOGIC ---
COOLDOWN_PERIOD = 3000       # Seconds to wait before logging the same person again

# --- DEFAULT CONSTANTS (Used if settings.json is missing) ---
DEFAULT_WIDTH = 640
DEFAULT_FRAME_SKIP = 3

# Dropdown Options for Admin GUI
WIDTH_OPTIONS = ["320", "640", "1280"]
FRAME_SKIP_OPTIONS = ["1", "3", "5", "10", "30"]


# "rtsp://admin:Aura%24em1@192.168.0.101:554/cam/realmonitor?channel=1&subtype=0"