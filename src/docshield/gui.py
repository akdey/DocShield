import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import threading
from . import DocShield
from .sessions import SessionManager

class DocShieldGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DocShield - Secure Anonymizer")
        self.root.geometry("500x450")
        self.root.resizable(False, False)
        
        # Style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self._setup_ui()
        
    def _setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header = ttk.Label(main_frame, text="DocShield", font=("Helvetica", 24, "bold"), foreground="#2c3e50")
        header.pack(pady=(0, 10))
        
        subtitle = ttk.Label(main_frame, text="Offline & Stateless Document Protection", font=("Helvetica", 10))
        subtitle.pack(pady=(0, 20))
        
        # File Selection
        file_frame = ttk.LabelFrame(main_frame, text=" 1. Select Document or Folder ", padding="10")
        file_frame.pack(fill=tk.X, pady=10)
        
        self.path_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.path_var, width=40).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(file_frame, text="Browse...", command=self._browse).pack(side=tk.LEFT)
        
        # Key Entry
        key_frame = ttk.LabelFrame(main_frame, text=" 2. Encryption Key (Optional) ", padding="10")
        key_frame.pack(fill=tk.X, pady=10)
        
        self.key_var = tk.StringVar()
        ttk.Entry(key_frame, textvariable=self.key_var, show="*", width=52).pack()
        ttk.Label(key_frame, text="Leave blank for automatic session mode", font=("Helvetica", 8, "italic")).pack(pady=(5, 0))
        
        # Actions
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=20)
        
        self.anon_btn = ttk.Button(btn_frame, text="Anonymize", command=self._run_anonymize)
        self.anon_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        self.deanon_btn = ttk.Button(btn_frame, text="Deanonymize", command=self._run_deanonymize)
        self.deanon_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        # Progress/Status
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, font=("Helvetica", 9), foreground="#7f8c8d")
        self.status_label.pack(pady=10)
        
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        
    def _browse(self):
        path = filedialog.askopenfilename(title="Select File", filetypes=[("Documents", "*.docx *.pdf *.txt"), ("All Files", "*.*")])
        if not path:
            path = filedialog.askdirectory(title="Select Folder")
        if path:
            self.path_var.set(path)
            
    def _run_anonymize(self):
        path = self.path_var.get()
        if not path:
            messagebox.showerror("Error", "Please select a file or folder first.")
            return
            
        self.anon_btn.state(['disabled'])
        self.deanon_btn.state(['disabled'])
        self.progress.pack(fill=tk.X, pady=5)
        self.progress.start()
        
        threading.Thread(target=self._anonymize_thread, args=(path,), daemon=True).start()
        
    def _anonymize_thread(self, path):
        try:
            path_obj = Path(path)
            # Session Mode setup
            session_name = SessionManager.generate_name()
            output_dir = path_obj.parent / f"{session_name}_output"
            output_dir.mkdir(exist_ok=True)
            
            vault_path = SessionManager.create_session_vault(session_name, output_dir)
            key = SessionManager.load_session_key(vault_path)
            
            ds = DocShield(key)
            
            self.status_var.set(f"Anonymizing: {path_obj.name}...")
            
            files = [path_obj] if path_obj.is_file() else list(path_obj.glob("*.*"))
            files = [f for f in files if f.suffix.lower() in [".docx", ".pdf", ".txt"]]
            
            for i, f in enumerate(files, 1):
                dest = output_dir / f"{session_name}_{i}{f.suffix}"
                ds.anonymize_file(f, dest)
                
            self.root.after(0, lambda: self._on_complete(f"Success!\n\nSession: {session_name}\nKey saved to vault folder."))
        except Exception as e:
            self.root.after(0, lambda: self._on_error(str(e)))

    def _run_deanonymize(self):
        path = self.path_var.get()
        if not path:
            messagebox.showerror("Error", "Please select a folder or file first.")
            return
            
        self.anon_btn.state(['disabled'])
        self.deanon_btn.state(['disabled'])
        self.progress.pack(fill=tk.X, pady=5)
        self.progress.start()
        
        threading.Thread(target=self._deanonymize_thread, args=(path,), daemon=True).start()

    def _deanonymize_thread(self, path):
        try:
            path_obj = Path(path)
            # Try to auto-resolve key
            search_dir = path_obj if path_obj.is_dir() else path_obj.parent
            key_files = list(search_dir.glob("*.key"))
            
            if not key_files:
                raise Exception("No .key file found in the selected folder.")
                
            key = SessionManager.load_session_key(key_files[0])
            ds = DocShield(key)
            
            self.status_var.set("Restoring original documents...")
            
            files = [path_obj] if path_obj.is_file() else list(path_obj.glob("*.*"))
            dest_dir = search_dir / "restored"
            dest_dir.mkdir(exist_ok=True)
            
            for f in files:
                if f.suffix.lower() in [".docx", ".pdf", ".txt"]:
                    ds.deanonymize_file(f, dest_dir / f"restored_{f.name}")
                    
            self.root.after(0, lambda: self._on_complete(f"Success!\n\nFiles restored to:\n{dest_dir}"))
        except Exception as e:
            self.root.after(0, lambda: self._on_error(str(e)))

    def _on_complete(self, msg):
        self.progress.stop()
        self.progress.pack_forget()
        self.anon_btn.state(['!disabled'])
        self.deanon_btn.state(['!disabled'])
        self.status_var.set("Ready")
        messagebox.showinfo("DocShield", msg)
        
    def _on_error(self, err):
        self.progress.stop()
        self.progress.pack_forget()
        self.anon_btn.state(['!disabled'])
        self.deanon_btn.state(['!disabled'])
        self.status_var.set("Error occurred")
        messagebox.showerror("Error", err)

    def run(self):
        self.root.mainloop()

def launch_gui():
    app = DocShieldGUI()
    app.run()
