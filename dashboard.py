# from flask import Flask, render_template
# import firebase_admin
# from firebase_admin import credentials, firestore
# from datetime import datetime

# app = Flask(__name__)

# if not firebase_admin._apps:
#     cred = credentials.Certificate("serviceAccountKey.json")
#     firebase_admin.initialize_app(cred)

# db = firestore.client()

# def check_integrity(first_entry_time):
#     try:
#         if first_entry_time == "--:--": return "Pending"
#         fmt = "%H:%M:%S"
#         entry_time = datetime.strptime(first_entry_time, fmt).time()
#         limit_time = datetime.strptime("07:59:00", fmt).time()
#         return "Integrity" if entry_time <= limit_time else "Out of Integrity"
#     except: return "Error"

# def calculate_work_hours(first, last):
#     try:
#         fmt = "%H:%M:%S"
#         d1 = datetime.strptime(first, fmt)
#         d2 = datetime.strptime(last, fmt)
#         diff = d2 - d1
#         h, m = divmod(diff.seconds // 60, 60)
#         return f"{h}h {m}m"
#     except: return "0h 0m"

# @app.route("/")
# def index():
#     today_str = datetime.now().strftime("%Y-%m-%d")
#     sync_time = datetime.now().strftime("%I:%M:%S %p")
    
#     # --- FETCH MODE FROM CLOUD ---
#     try:
#         cfg = db.collection("system_settings").document("dashboard_config").get()
#         entry_only_mode = cfg.to_dict().get("entry_only_mode", True)
#     except:
#         entry_only_mode = True

#     processed_records = []
#     users_ref = db.collection("attendance").stream()

#     for user_doc in users_ref:
#         user_data = user_doc.to_dict()
#         user_id = user_doc.id
        
#         history_ref = db.collection("attendance").document(user_id)\
#                         .collection("history").document(today_str).get()
        
#         history_data = history_ref.to_dict() if history_ref.exists else {"events": []}
#         events = history_data.get("events", [])

#         first_entry = "--:--"
#         last_exit = "--:--"
#         work_time = "0h 0m"

#         if events:
#             sorted_events = sorted(events, key=lambda x: x['time'])
#             first_entry = next((e['time'] for e in sorted_events if e['type'] == 'Entry'), "--:--")
#             exits = [e['time'] for e in sorted_events if e['type'] == 'Exit']
#             last_exit = exits[-1] if exits else "--:--"
            
#             if first_entry != "--:--":
#                 end_ts = last_exit if user_data.get("status") != "Here" else datetime.now().strftime("%H:%M:%S")
#                 work_time = calculate_work_hours(first_entry, end_ts)

#         processed_records.append({
#             "id": user_id, "name": user_data.get("name", "Unknown"),
#             "role": user_data.get("role", "Staff"), "status": user_data.get("status", "Not Here"),
#             "first_entry": first_entry, "last_exit": last_exit,
#             "work_duration": work_time, "integrity_check": check_integrity(first_entry),
#             "history": sorted(events, key=lambda x: x['time'], reverse=True)
#         })

#     return render_template("index.html", records=processed_records, sync_time=sync_time, entry_only_mode=entry_only_mode)

# if __name__ == "__main__":
#     app.run(debug=True)



import csv
import io
from flask import Flask, render_template, request, Response
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

app = Flask(__name__)

# Firebase Initialization
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

def check_integrity(first_entry_time):
    try:
        if first_entry_time == "--:--": return "Pending"
        fmt = "%H:%M:%S"
        entry_time = datetime.strptime(first_entry_time, fmt).time()
        limit_time = datetime.strptime("07:59:00", fmt).time()
        return "Integrity" if entry_time <= limit_time else "Out of Integrity"
    except: return "Error"

def calculate_work_hours(first, last):
    try:
        fmt = "%H:%M:%S"
        d1 = datetime.strptime(first, fmt)
        d2 = datetime.strptime(last, fmt)
        diff = d2 - d1
        h, m = divmod(diff.seconds // 60, 60)
        return f"{h}h {m}m"
    except: return "0h 0m"

@app.route("/")
def index():
    today_str = datetime.now().strftime("%Y-%m-%d")
    sync_time = datetime.now().strftime("%I:%M:%S %p")

    try:
        cfg = db.collection("system_settings").document("dashboard_config").get()
        entry_only_mode = cfg.to_dict().get("entry_only_mode", True)
    except:
        entry_only_mode = True

    processed_records = []
    users_ref = db.collection("attendance").stream()

    for user_doc in users_ref:
        user_data = user_doc.to_dict()
        user_id = user_doc.id
        history_ref = db.collection("attendance").document(user_id)\
                        .collection("history").document(today_str).get()

        history_data = history_ref.to_dict() if history_ref.exists else {"events": []}
        events = history_data.get("events", [])

        first_entry = "--:--"
        last_exit = "--:--"
        work_time = "0h 0m"

        if events:
            sorted_events = sorted(events, key=lambda x: x['time'])
            first_entry = next((e['time'] for e in sorted_events if e['type'] == 'Entry'), "--:--")
            exits = [e['time'] for e in sorted_events if e['type'] == 'Exit']
            last_exit = exits[-1] if exits else "--:--"
            if first_entry != "--:--":
                end_ts = last_exit if user_data.get("status") != "Here" else datetime.now().strftime("%H:%M:%S")
                work_time = calculate_work_hours(first_entry, end_ts)

        processed_records.append({
            "id": user_id, "name": user_data.get("name", "Unknown"),
            "role": user_data.get("role", "Staff"), "status": user_data.get("status", "Not Here"),
            "first_entry": first_entry, "last_exit": last_exit,
            "work_duration": work_time, "integrity_check": check_integrity(first_entry),
            "history": sorted(events, key=lambda x: x['time'], reverse=True)
        })

    return render_template("index.html", records=processed_records, sync_time=sync_time, entry_only_mode=entry_only_mode)

# --- NEW EXPORT ROUTES ---

@app.route("/export")
def export_page():
    return render_template("export.html")

@app.route("/download-csv", methods=['POST'])
def download_csv():
    from_date = request.form.get('from_date')
    to_date = request.form.get('to_date')
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Name', 'Log Type', 'Time'])

    users_ref = db.collection("attendance").stream()
    for user_doc in users_ref:
        user_name = user_doc.to_dict().get("name", "Unknown")
        user_id = user_doc.id
        
        # Stream all history documents for each user
        history_ref = db.collection("attendance").document(user_id).collection("history").stream()
        for day_doc in history_ref:
            date_str = day_doc.id
            if from_date <= date_str <= to_date:
                events = day_doc.to_dict().get("events", [])
                for event in events:
                    writer.writerow([date_str, user_name, event['type'], event['time']])

    output.seek(0)
    # Adding BOM for Excel compatibility with local names
    content = "\ufeff" + output.getvalue()
    
    return Response(
        content,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=Attendance_{from_date}_to_{to_date}.csv"}
    )

if __name__ == "__main__":
    app.run(port=8080, debug=True)