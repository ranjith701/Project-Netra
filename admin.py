import os
import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog, ttk
import shutil
import json
import threading
import cv2 
import numpy as np 

# --- PROJECT IMPORTS ---
import config
import database_manager as db
from face_processor import FaceProcessor

GLOBAL_FACE_PROC = None
ALLOWED_EXTENSIONS = ['*.png', '*.jpg', '*.jpeg']

class UserManagementApp:
    def __init__(self, master):
        self.master = master
        master.title("Netra Management Tool")
        master.geometry("750x800")

        self.selected_photo_paths = []
        os.makedirs(config.DB_PATH, exist_ok=True)
        db.setup_database()
        
        self.load_face_processor()
        self.settings = self.get_settings()

        # --- TABS ---
        self.notebook = ttk.Notebook(master)
        self.notebook.pack(pady=10, padx=10, expand=True, fill="both")

        self.add_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.add_tab, text='Enroll User')
        self.setup_add_tab()

        self.manage_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.manage_tab, text='Manage/Delete')
        self.setup_manage_tab()

        self.camera_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.camera_tab, text='Camera Setup')
        self.setup_camera_tab()

        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_tab, text='System Settings')
        self.setup_settings_tab()
        
        self.utilities_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.utilities_tab, text='Utilities')
        self.setup_utilities_tab()
        
        self.status_label = tk.Label(master, text="Initializing AI Engine...", fg="blue")
        self.status_label.pack(pady=5)

    def load_face_processor(self):
        global GLOBAL_FACE_PROC
        def load():
            global GLOBAL_FACE_PROC
            try:
                GLOBAL_FACE_PROC = FaceProcessor()
                self.master.after(0, self.update_status, "AI Engine Ready.", "green")
            except Exception as e:
                self.master.after(0, self.update_status, "AI Engine FAILED.", "red")     
        threading.Thread(target=load).start()
        
    def update_status(self, text, color):
        if hasattr(self, 'status_label'): self.status_label.config(text=text, fg=color)

    # --- TAB 1: ENROLL ---
    def setup_add_tab(self):
        fields = [("Full Name:", "name_var"), ("Role:", "role_var"), ("Organization:", "org_var"), ("Phone:", "phone_var"), ("Email:", "email_var")]
        self.entry_vars = {}
        for i, (label, var_name) in enumerate(fields):
            tk.Label(self.add_tab, text=label).grid(row=i, column=0, sticky='w', padx=5, pady=5)
            var = tk.StringVar()
            tk.Entry(self.add_tab, textvariable=var, width=40).grid(row=i, column=1, padx=5, pady=5)
            self.entry_vars[var_name] = var
            
        tk.Button(self.add_tab, text="Select Photo(s)", command=self.select_photos, bg="#FFEB3B").grid(row=6, column=0, columnspan=2, pady=5, sticky='ew', padx=10)
        self.photo_count_label = tk.Label(self.add_tab, text="0 selected", fg="red")
        self.photo_count_label.grid(row=5, column=1)
        tk.Button(self.add_tab, text="ENROLL EMPLOYEE", command=self.enroll_employee_check_thread, bg="#4CAF50", fg="white").grid(row=7, column=0, columnspan=2, pady=15, sticky='ew', padx=10)

    # --- TAB 2: MANAGE ---
    def setup_manage_tab(self):
        self.user_listbox = tk.Listbox(self.manage_tab, width=50, height=15)
        self.user_listbox.pack(padx=10, pady=10)
        btn_frame = tk.Frame(self.manage_tab)
        btn_frame.pack(fill='x')
        tk.Button(btn_frame, text="Delete User", command=self.delete_user, bg="#F44336", fg="white").pack(side='left', expand=True, fill='x', padx=5)
        tk.Button(btn_frame, text="Open Folder", command=self.open_user_folder, bg="#FF9800").pack(side='left', expand=True, fill='x', padx=5)
        self.load_user_list()

    # --- TAB 3: CAMERA SETUP ---
    def setup_camera_tab(self):
        frame = ttk.Frame(self.camera_tab, padding="10")
        frame.pack(fill='both', expand=True)

        tk.Label(frame, text="URL / IP:").grid(row=0, column=0, sticky='w')
        self.cam_url_var = tk.StringVar()
        tk.Entry(frame, textvariable=self.cam_url_var, width=40).grid(row=0, column=1, pady=2)

        tk.Label(frame, text="Name:").grid(row=1, column=0, sticky='w')
        self.cam_name_var = tk.StringVar(value="Main Gate")
        tk.Entry(frame, textvariable=self.cam_name_var, width=20).grid(row=1, column=1, pady=2, sticky='w')

        tk.Label(frame, text="Type:").grid(row=2, column=0, sticky='w')
        self.cam_type_var = tk.StringVar(value="Entry")
        ttk.Combobox(frame, textvariable=self.cam_type_var, values=["Entry", "Exit"], state="readonly").grid(row=2, column=1, pady=2, sticky='w')

        tk.Label(frame, text="Pair ID:").grid(row=3, column=0, sticky='w')
        self.cam_pair_var = tk.StringVar(value="1")
        tk.Entry(frame, textvariable=self.cam_pair_var, width=5).grid(row=3, column=1, pady=2, sticky='w')

        tk.Button(frame, text="+ Add Camera", command=self.add_camera_config, bg="#4CAF50", fg="white").grid(row=4, column=0, columnspan=2, pady=10, sticky='ew')

        # Treeview
        columns = ('name', 'type', 'pair', 'url', 'status')
        self.cam_tree = ttk.Treeview(frame, columns=columns, show='headings', height=8)
        for c in columns: self.cam_tree.heading(c, text=c.capitalize()); self.cam_tree.column(c, width=80)
        self.cam_tree.column('url', width=150)
        self.cam_tree.grid(row=5, column=0, columnspan=2, sticky='ew')

        btn_box = tk.Frame(frame)
        btn_box.grid(row=6, column=0, columnspan=2, pady=5, sticky='ew')
        tk.Button(btn_box, text="Toggle On/Off", command=self.toggle_camera).pack(side='left', fill='x', expand=True)
        tk.Button(btn_box, text="Delete", command=self.delete_camera_config, bg="#F44336", fg="white").pack(side='left', fill='x', expand=True)
        
        self.refresh_camera_tree()

    # --- TAB 4: SETTINGS ---
    def setup_settings_tab(self):
        frame = ttk.Frame(self.settings_tab, padding="10")
        frame.pack(fill='both', expand=True)
        
        tk.Label(frame, text="Processing Width:").grid(row=0, column=0, sticky='w', pady=5)
        self.width_var = tk.StringVar(value=str(self.settings.get('processing_width', 640)))
        ttk.Combobox(frame, textvariable=self.width_var, values=["320", "640", "1280"]).grid(row=0, column=1, sticky='ew')

        tk.Label(frame, text="Frame Skip:").grid(row=1, column=0, sticky='w', pady=5)
        self.skip_var = tk.StringVar(value=str(self.settings.get('frame_skip', 3)))
        ttk.Combobox(frame, textvariable=self.skip_var, values=["1", "3", "5", "10"]).grid(row=1, column=1, sticky='ew')

        tk.Label(frame, text="Hardware Accel:").grid(row=2, column=0, sticky='w', pady=5)
        self.gpu_var = tk.BooleanVar(value=self.settings.get('use_gpu', False))
        tk.Checkbutton(frame, text="Enable GPU", variable=self.gpu_var).grid(row=2, column=1, sticky='w')

        tk.Button(frame, text="Save Settings", command=self.save_settings, bg="#2196F3", fg="white").grid(row=3, column=0, columnspan=2, pady=15, sticky='ew')

    def setup_utilities_tab(self):
        tk.Button(self.utilities_tab, text="Reload RAM Database", command=self.rebuild_db).pack(pady=20)

    # --- LOGIC ---
    def add_camera_config(self):
        url = self.cam_url_var.get().strip()
        name = self.cam_name_var.get().strip()
        c_type = self.cam_type_var.get()
        pair_id = self.cam_pair_var.get().strip()

        if not url or not name: return messagebox.showerror("Error", "Missing fields")
        
        cam_list = self.settings.get('cameras_advanced', [])
        
        # Validation
        for c in cam_list:
            if c['url'] == url: return messagebox.showerror("Error", "Duplicate URL")
            if c['pair_id'] == pair_id and c['type'] == c_type:
                return messagebox.showerror("Error", f"Pair {pair_id} already has a {c_type}")

        cam_list.append({"url": url, "name": name, "type": c_type, "pair_id": pair_id, "enabled": True})
        self.settings['cameras_advanced'] = cam_list
        self.save_to_json()
        self.refresh_camera_tree()

    def refresh_camera_tree(self):
        for i in self.cam_tree.get_children(): self.cam_tree.delete(i)
        for idx, c in enumerate(self.settings.get('cameras_advanced', [])):
            self.cam_tree.insert('', 'end', iid=idx, values=(c['name'], c['type'], c['pair_id'], c['url'], "✅" if c['enabled'] else "❌"))

    def toggle_camera(self):
        sel = self.cam_tree.selection()
        if sel:
            idx = int(sel[0])
            self.settings['cameras_advanced'][idx]['enabled'] = not self.settings['cameras_advanced'][idx]['enabled']
            self.save_to_json()
            self.refresh_camera_tree()

    def delete_camera_config(self):
        sel = self.cam_tree.selection()
        if sel:
            self.settings['cameras_advanced'].pop(int(sel[0]))
            self.save_to_json()
            self.refresh_camera_tree()

    def save_settings(self):
        self.settings['processing_width'] = int(self.width_var.get())
        self.settings['frame_skip'] = int(self.skip_var.get())
        self.settings['use_gpu'] = self.gpu_var.get()
        self.save_to_json()
        messagebox.showinfo("Saved", "Settings saved. Restart main.py.")

    def get_settings(self):
        try:
            with open(config.SETTINGS_FILE, 'r') as f: return json.load(f)
        except: return {}

    def save_to_json(self):
        with open(config.SETTINGS_FILE, 'w') as f: json.dump(self.settings, f, indent=4)

    # --- ENROLLMENT HELPERS ---
    def select_photos(self):
        paths = filedialog.askopenfilenames(filetypes=[("Images", ALLOWED_EXTENSIONS)])
        if paths:
            self.selected_photo_paths = list(paths)
            self.photo_count_label.config(text=f"{len(paths)} selected", fg="green")

    def enroll_employee_check_thread(self):
        name = self.entry_vars['name_var'].get()
        role = self.entry_vars['role_var'].get()
        if not name or not role or not self.selected_photo_paths:
            return messagebox.showerror("Error", "Missing Name, Role, or Photos")
            
        success, new_id, folder_path = db.add_employee(name, role, "", "", "") 
        if success:
            for i, src in enumerate(self.selected_photo_paths):
                try: shutil.copy2(src, os.path.join(folder_path, f"photo_{new_id}_{i+1}{os.path.splitext(src)[1]}"))
                except: pass
            if GLOBAL_FACE_PROC: GLOBAL_FACE_PROC.load_known_embeddings()
            messagebox.showinfo("Success", f"Enrolled {name} (ID: {new_id})")
            self.load_user_list()
            self.selected_photo_paths = []
            
    def load_user_list(self):
        self.user_listbox.delete(0, tk.END)
        self.users = db.get_all_users()
        for u in self.users: self.user_listbox.insert(tk.END, f"[ID: {u['id']}] {u['name']}")

    def delete_user(self):
        sel = self.user_listbox.curselection()
        if sel and messagebox.askyesno("Delete", "Are you sure?"):
            db.delete_user_by_id(self.users[sel[0]]['id'])
            if GLOBAL_FACE_PROC: GLOBAL_FACE_PROC.load_known_embeddings()
            self.load_user_list()
            
    def open_user_folder(self):
        sel = self.user_listbox.curselection()
        if sel: 
            path = os.path.join(config.DB_PATH, str(self.users[sel[0]]['id']))
            try: os.startfile(path)
            except: pass

    def rebuild_db(self):
        if GLOBAL_FACE_PROC: threading.Thread(target=GLOBAL_FACE_PROC.load_known_embeddings).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = UserManagementApp(root)
    root.mainloop()