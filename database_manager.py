"""
Handles SQLite operations for local storage (employees, logs).
Enhanced to support Integrity Tracking (Entry/Exit) and Working Hours.
"""
import sqlite3
import os
import shutil 
from datetime import datetime
import config

def get_db_connection():
    """Establish connection and enable Foreign Keys."""
    conn = sqlite3.connect(config.DB_NAME)
    conn.execute('PRAGMA foreign_keys = ON') 
    conn.row_factory = sqlite3.Row
    return conn

def setup_database():
    """Create tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Employee Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        role TEXT NOT NULL,
        organisation TEXT,
        phone TEXT,
        email TEXT
    )''')
    
    # 2. Attendance Table - Updated for Integrity Tracking
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_name TEXT,
        log_type TEXT, -- 'Entry' or 'Exit'
        camera_name TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()
    print("✅ Local Database Setup Complete (Integrity Tracking Enabled).")

def log_attendance(employee_name, capture_time, log_type="Entry", camera_name="Main Cam"):
    """
    Logs movement to local SQLite. 
    Required for First Entry, Last Exit, and Total Hours calculation.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Convert raw camera timestamp (float) to SQLite string
        if isinstance(capture_time, (int, float)):
            dt_obj = datetime.fromtimestamp(capture_time)
        else:
            dt_obj = capture_time
            
        t_str = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
            INSERT INTO attendance (employee_name, log_type, camera_name, timestamp) 
            VALUES (?, ?, ?, ?)
        ''', (employee_name, log_type, camera_name, t_str))
        
        conn.commit()
        print(f"💾 Local Log: {employee_name} | {log_type} | {camera_name}")
        return True
    except Exception as e:
        print(f"❌ Local Log Failed: {e}")
        return False
    finally: 
        conn.close()

# --- NEW: CRITICAL FUNCTIONS FOR MAIN.PY ---

def get_employee_role(employee_id):
    """Fetches role by ID. Required by AIWorker for Firebase logging."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM employees WHERE id = ?", (employee_id,))
        result = cursor.fetchone()
        return result['role'] if result else "Staff"
    finally:
        conn.close()

def get_employee_id_by_name(name):
    """Fetches ID by Name. Helpful for finding the correct image folder."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM employees WHERE name = ?", (name,))
        result = cursor.fetchone()
        return result['id'] if result else None
    finally:
        conn.close()

# --- DASHBOARD & MANAGEMENT FUNCTIONS ---

def get_daily_summary():
    """Calculates summary data for the dashboard."""
    conn = get_db_connection()
    try:
        query = '''
            SELECT 
                employee_name,
                MIN(timestamp) as first_entry,
                MAX(timestamp) as last_exit,
                (SELECT log_type FROM attendance a2 
                 WHERE a2.employee_name = a1.employee_name 
                 ORDER BY timestamp DESC LIMIT 1) as current_status
            FROM attendance a1
            WHERE date(timestamp) = date('now')
            GROUP BY employee_name
        '''
        return conn.execute(query).fetchall()
    finally:
        conn.close()

def add_employee(name, role, organisation, phone, email):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        os.makedirs(config.DB_PATH, exist_ok=True)
        cursor.execute(
            "INSERT INTO employees (name, role, organisation, phone, email) VALUES (?, ?, ?, ?, ?)",
            (name, role, organisation, phone, email)
        )
        emp_id = cursor.lastrowid
        conn.commit()
        folder = os.path.join(config.DB_PATH, str(emp_id))
        os.makedirs(folder, exist_ok=True)
        return (True, emp_id, folder)
    except sqlite3.IntegrityError:
        return (False, "Name already exists.", None) 
    except Exception as e:
        return (False, str(e), None)
    finally:
        conn.close()

def get_employee_name_by_id(employee_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM employees WHERE id = ?", (employee_id,))
        result = cursor.fetchone()
        return result['name'] if result else "Unknown"
    except:
        return "Unknown"
    finally:
        conn.close()

def get_all_users():
    conn = get_db_connection()
    try:
        return conn.execute("SELECT * FROM employees ORDER BY name").fetchall()
    finally:
        conn.close()

def delete_user_by_id(user_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM employees WHERE id = ?", (user_id,))
        conn.commit()
        folder = os.path.join(config.DB_PATH, str(user_id))
        if os.path.exists(folder):
            shutil.rmtree(folder)
        return True, "Deleted successfully."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()