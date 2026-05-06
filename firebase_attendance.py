import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import os

# --- INITIALIZE FIREBASE SAFELY ---
# This ensures the app is initialized before any Firestore calls are made
if not firebase_admin._apps:
    # Look for the key in the root folder
    cred_path = "serviceAccountKey.json"
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    else:
        print("❌ Error: serviceAccountKey.json not found!")

# Now it is safe to create the client
db = firestore.client()
executor = ThreadPoolExecutor(max_workers=2)

def sync_dashboard_settings(cams_conf):
    """Updates the Cloud Dashboard mode based on local camera config."""
    try:
        has_exit = any(c.get('type') == 'Exit' for c in cams_conf if c.get('enabled', True))
        
        db.collection("system_settings").document("dashboard_config").set({
            "entry_only_mode": not has_exit,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }, merge=True)
        print(f"📡 Cloud Sync: Dashboard Mode set to {'Entry-Only' if not has_exit else 'Entry-Exit'}")
    except Exception as e:
        print(f"📡 Cloud Sync Error: {e}")

def _log_worker(emp_id, name, role, capture_time, cam_type):
    try:
        doc_id = str(emp_id)
        time_only = capture_time.strftime("%H:%M:%S")
        date_str = capture_time.strftime("%Y-%m-%d")

        user_ref = db.collection("attendance").document(doc_id)
        
        update_data = {
            "id": doc_id, 
            "name": name, 
            "role": role, 
            "status": "Here" if cam_type == "Entry" else "Not Here"
        }
        
        if cam_type == "Exit":
            update_data["today_last_exit"] = time_only
        
        user_ref.set(update_data, merge=True)
        user_ref.collection("history").document(date_str).set({
            "events": firestore.ArrayUnion([{"time": time_only, "type": cam_type}])
        }, merge=True)
    except Exception as e:
        print(f"Cloud Error: {e}")

def log_attendance_cloud(emp_id, name, role, capture_time, cam_type="Entry"):
    executor.submit(_log_worker, emp_id, name, role, capture_time, cam_type)