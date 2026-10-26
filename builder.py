import os
import sys
import json
import time
import shutil
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk

# ==============================================================================
# CONSTANTE & CĂI
# ==============================================================================
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def resource_path(relative_path):
    """Obține calea unei resurse, căutând în _MEIPASS (PyInstaller) sau în BASE_DIR."""
    if hasattr(sys, "_MEIPASS"):
        meipass_p = os.path.join(sys._MEIPASS, relative_path)
        if os.path.exists(meipass_p):
            return meipass_p
    return os.path.join(BASE_DIR, relative_path)

CONFIG_FILE = os.path.join(BASE_DIR, "launcher_config.json")
DEFAULT_GIF = resource_path("coding_begin.gif")

# ==============================================================================
# UTILITARE SCANARE WINDOWS & PROFILURI BROWSER
# ==============================================================================
def get_browser_profiles():
    """Detectează toate profilurile utilizator din Brave Browser și Google Chrome."""
    profiles = []
    configs = [
        ("Brave", r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Local State", r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ("Chrome", r"%LOCALAPPDATA%\Google\Chrome\User Data\Local State", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    ]
    for bname, ppath, default_exe in configs:
        full_path = os.path.expandvars(ppath)
        if os.path.exists(full_path):
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for pdir, pinfo in data.get("profile", {}).get("info_cache", {}).items():
                    pname = pinfo.get("name", pdir)
                    profiles.append({
                        "browser": bname,
                        "folder": pdir,
                        "name": pname,
                        "exe": default_exe if os.path.exists(default_exe) else "",
                        "arg": f'--profile-directory="{pdir}"',
                        "display": f"{bname}: {pname} (folder: {pdir})"
                    })
            except Exception:
                pass
    return profiles

def scan_windows_shortcuts():
    """Scanează aplicațiile instalate în Windows prin scurtăturile din Start Menu și Desktop."""
    ps_script = """
$w = New-Object -ComObject WScript.Shell
$folders = @(
    [Environment]::GetFolderPath('Programs'),
    [Environment]::GetFolderPath('CommonPrograms'),
    [Environment]::GetFolderPath('Desktop')
)
$items = @()
foreach ($f in $folders) {
    if (Test-Path $f) {
        Get-ChildItem -Path $f -Filter *.lnk -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
            try {
                $sc = $w.CreateShortcut($_.FullName)
                $target = $sc.TargetPath
                if ($target -and (Test-Path $target) -and ($target.ToLower().EndsWith('.exe'))) {
                    $items += [PSCustomObject]@{
                        name = $_.BaseName
                        target = $target
                        args = $sc.Arguments
                    }
                }
            } catch {}
        }
    }
}
$items | ConvertTo-Json -Compress
"""
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            text=True,
            check=True
        )
        if not res.stdout.strip():
            return []
        items = json.loads(res.stdout)
        unique = {}
        ignore_keywords = {"uninstall", "help", "readme", "narrator", "magnify", "livecaptions", "control", "accessibility"}
        for item in items:
            name = item.get("name", "").strip()
            target = item.get("target", "").strip()
            if not name or not target:
                continue
            if any(ign in name.lower() for ign in ignore_keywords):
                continue
            key = (name.lower(), target.lower())
            if key not in unique:
                unique[key] = {
                    "name": name,
                    "path": target,
                    "args": item.get("args", "") or ""
                }
        return sorted(unique.values(), key=lambda x: x["name"].lower())
    except Exception as e:
        print("Eroare scanare aplicații:", e)
        return []

# ==============================================================================
# MOTORUL DE LANSARE PENTRU TESTARE PREVIEW
# ==============================================================================
def run_preview_launcher(config):
    """Lansează o instanță de test a launcher-ului plutitor cu configurația curentă."""
    gif_path = config.get("gif_path", DEFAULT_GIF)
    duration_ms = int(config.get("duration_seconds", 3) * 1000)
    apps = [app for app in config.get("apps", []) if app.get("enabled", True)]

    root = tk.Toplevel()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg="#000000")

    frames = []
    if os.path.exists(gif_path):
        idx = 0
        while True:
            try:
                frame = tk.PhotoImage(file=gif_path, format=f"gif -index {idx}")
                frames.append(frame)
                idx += 1
            except Exception:
                break

    w, h = (frames[0].width(), frames[0].height()) if frames else (380, 380)
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")

    if frames:
        lbl = tk.Label(root, image=frames[0], bd=0, highlightthickness=0, bg="#000000")
        lbl.pack(fill="both", expand=True)

        def animate(idx=0):
            if not root.winfo_exists():
                return
            lbl.configure(image=frames[idx])
            root.after(70, animate, (idx + 1) % len(frames))

        animate()

    def launch_apps_and_close():
        try:
            root.destroy()
        except Exception:
            pass
        for app in apps:
            p = app.get("path", "")
            args = app.get("args", "").strip()
            if p and os.path.exists(p):
                try:
                    if args:
                        subprocess.Popen([p] + args.split())
                    else:
                        os.startfile(p)
                except Exception as ex:
                    print(f"Eroare lansare {p}: {ex}")

    root.bind("<Escape>", lambda e: launch_apps_and_close())
    root.bind("<Button-1>", lambda e: launch_apps_and_close())
    root.after(duration_ms, launch_apps_and_close)

# ==============================================================================
# GENERATORUL DE COD & EXECUTABIL PENTRU PYINSTALLER
# ==============================================================================
RUNNER_CODE_TEMPLATE = '''# Generated by Coding Launcher Builder
import os
import sys
import subprocess
import tkinter as tk

CONFIG = {config_json}

def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

def launch_all():
    for app in CONFIG.get("apps", []):
        if not app.get("enabled", True):
            continue
        p = app.get("path", "")
        args = app.get("args", "").strip()
        if p and os.path.exists(p):
            try:
                if args:
                    subprocess.Popen([p] + args.split())
                else:
                    os.startfile(p)
            except Exception:
                pass

def main():
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg="#000000")

    gif_filename = os.path.basename(CONFIG.get("gif_path", "coding_begin.gif"))
    gif_file = resource_path(gif_filename)

    frames = []
    if os.path.exists(gif_file):
        idx = 0
        while True:
            try:
                f = tk.PhotoImage(file=gif_file, format=f"gif -index {idx}")
                frames.append(f)
                idx += 1
            except Exception:
                break

    w = frames[0].width() if frames else 380
    h = frames[0].height() if frames else 380
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"{{w}}x{{h}}+{{(sw - w) // 2}}+{{(sh - h) // 2}}")

    if frames:
        lbl = tk.Label(root, image=frames[0], bd=0, highlightthickness=0, bg="#000000")
        lbl.pack(fill="both", expand=True)

        def animate(idx=0):
            if not root.winfo_exists():
                return
            lbl.configure(image=frames[idx])
            root.after(70, animate, (idx + 1) % len(frames))

        animate()

    def finish():
        try:
            root.destroy()
        except Exception:
            pass
        launch_all()

    root.bind("<Escape>", lambda e: finish())
    root.bind("<Button-1>", lambda e: finish())

    duration = int(CONFIG.get("duration_seconds", 3) * 1000)
    root.after(duration, finish)
    root.mainloop()

if __name__ == "__main__":
    main()
'''

# ==============================================================================
# INTERFAȚĂ PRINCIPALĂ BUILDER
# ==============================================================================
class LauncherBuilderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Coding Launcher Builder & Configurator")
        self.root.geometry("1060x720")
        self.root.minsize(980, 640)
        self.root.configure(bg="#12131a")

        # Stare internă
        self.scanned_apps = []
        self.browser_profiles = []
        self.gif_thumbnail = None

        self.config = {
            "exe_name": "custom_launcher",
            "gif_path": DEFAULT_GIF,
            "duration_seconds": 3.0,
            "apps": []
        }

        # Încărcare configurație existentă sau implicită
        self.load_config()

        # Construire stiluri TTK Dark
        self.setup_styles()

        # Construire interfață
        self.build_ui()

        # Scanare inițială în fundal
        threading.Thread(target=self.run_background_scans, daemon=True).start()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Configurare culori Dark Cyber
        style.configure(".", background="#12131a", foreground="#F3F4F6", font=("Segoe UI", 9))
        style.configure("Treeview", background="#1a1c26", foreground="#F3F4F6", fieldbackground="#1a1c26", rowheight=26, borderwidth=0)
        style.map("Treeview", background=[("selected", "#374151")], foreground=[("selected", "#00FFA3")])
        style.configure("Treeview.Heading", background="#242838", foreground="#9CA3AF", font=("Segoe UI", 9, "bold"), borderwidth=0)

        style.configure("TCombobox", fieldbackground="#1a1c26", background="#242838", foreground="#F3F4F6", arrowcolor="#00FFA3")
        style.map("TCombobox", fieldbackground=[("readonly", "#1a1c26")])

    def build_ui(self):
        # Header principal
        header_frame = tk.Frame(self.root, bg="#1a1c26", height=60)
        header_frame.pack(fill="x", side="top")

        title_lbl = tk.Label(
            header_frame,
            text="⚡ CODING LAUNCHER BUILDER",
            font=("Consolas", 15, "bold"),
            fg="#00FFA3",
            bg="#1a1c26"
        )
        title_lbl.pack(side="left", padx=20, pady=12)

        subtitle_lbl = tk.Label(
            header_frame,
            text="Scanează aplicații • Configurează profiluri • Alege GIF-ul • Generează .EXE",
            font=("Segoe UI", 9),
            fg="#9CA3AF",
            bg="#1a1c26"
        )
        subtitle_lbl.pack(side="left", padx=10, pady=15)

        # Container principal împărțit în două coloane
        main_paned = tk.PanedWindow(self.root, orient="horizontal", bg="#12131a", bd=0, sashwidth=4)
        main_paned.pack(fill="both", expand=True, padx=15, pady=15)

        # STÂNGA: Scanner Aplicații Windows
        left_frame = tk.Frame(main_paned, bg="#12131a")
        main_paned.add(left_frame, minsize=420)

        # DREAPTA: Configurație Launcher & GIF & Build
        right_frame = tk.Frame(main_paned, bg="#12131a")
        main_paned.add(right_frame, minsize=520)

        self.build_left_panel(left_frame)
        self.build_right_panel(right_frame)

    # --------------------------------------------------------------------------
    # PANOU STÂNGA: SCANARE APLICAȚII
    # --------------------------------------------------------------------------
    def build_left_panel(self, parent):
        # Titlu secțiune
        sec_title = tk.Label(
            parent,
            text="🔍 APLICAȚII WINDOWS DETECTATE",
            font=("Segoe UI", 10, "bold"),
            fg="#60A5FA",
            bg="#12131a"
        )
        sec_title.pack(anchor="w", pady=(0, 6))

        # Bară căutare
        search_box = tk.Frame(parent, bg="#1a1c26", bd=1, relief="solid")
        search_box.pack(fill="x", pady=(0, 8))

        search_icon = tk.Label(search_box, text="🔎", bg="#1a1c26", fg="#9CA3AF", font=("Segoe UI", 10))
        search_icon.pack(side="left", padx=(8, 4))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.filter_scanned_apps())
        search_entry = tk.Entry(
            search_box,
            textvariable=self.search_var,
            bg="#1a1c26",
            fg="white",
            insertbackground="#00FFA3",
            bd=0,
            font=("Segoe UI", 10)
        )
        search_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))

        # Tabel aplicații scanate
        tree_frame = tk.Frame(parent, bg="#12131a")
        tree_frame.pack(fill="both", expand=True)

        self.scan_tree = ttk.Treeview(tree_frame, columns=("name", "path"), show="headings", selectmode="browse")
        self.scan_tree.heading("name", text="Nume Aplicație", anchor="w")
        self.scan_tree.heading("path", text="Cale Executabil", anchor="w")
        self.scan_tree.column("name", width=150, anchor="w")
        self.scan_tree.column("path", width=250, anchor="w")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.scan_tree.yview)
        self.scan_tree.configure(yscrollcommand=scrollbar.set)
        self.scan_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.scan_tree.bind("<Double-1>", lambda e: self.add_selected_scanned_app())

        # Butoane acțiune adăugare
        btn_bar = tk.Frame(parent, bg="#12131a")
        btn_bar.pack(fill="x", pady=8)

        add_btn = tk.Button(
            btn_bar,
            text="➕ Adaugă în Launcher",
            font=("Segoe UI", 9, "bold"),
            bg="#2563EB",
            fg="white",
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.add_selected_scanned_app
        )
        add_btn.pack(side="left", padx=(0, 6))

        browse_btn = tk.Button(
            btn_bar,
            text="📁 Alege fișier manual...",
            font=("Segoe UI", 9),
            bg="#374151",
            fg="white",
            bd=0,
            padx=10,
            pady=6,
            cursor="hand2",
            command=self.browse_custom_exe
        )
        browse_btn.pack(side="left")

        rescan_btn = tk.Button(
            btn_bar,
            text="🔄 Re-scanează",
            font=("Segoe UI", 9),
            bg="#1F2937",
            fg="#9CA3AF",
            bd=0,
            padx=8,
            pady=6,
            cursor="hand2",
            command=lambda: threading.Thread(target=self.run_background_scans, daemon=True).start()
        )
        rescan_btn.pack(side="right")

        # Secțiune: Profiluri Browser Detectate
        browser_box = tk.LabelFrame(
            parent,
            text="🌐 Profiluri Browser Detectate (Brave / Chrome)",
            font=("Segoe UI", 9, "bold"),
            fg="#FACC15",
            bg="#181a24",
            bd=1,
            padx=10,
            pady=8
        )
        browser_box.pack(fill="x", pady=(8, 0))

        self.profile_combo_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(
            browser_box,
            textvariable=self.profile_combo_var,
            state="readonly",
            font=("Segoe UI", 9)
        )
        self.profile_combo.pack(fill="x", pady=(2, 6))

        p_btn_bar = tk.Frame(browser_box, bg="#181a24")
        p_btn_bar.pack(fill="x")

        add_browser_btn = tk.Button(
            p_btn_bar,
            text="➕ Adaugă Browser cu acest Profil",
            font=("Segoe UI", 8, "bold"),
            bg="#059669",
            fg="white",
            bd=0,
            padx=10,
            pady=5,
            cursor="hand2",
            command=self.add_browser_with_profile
        )
        add_browser_btn.pack(side="left")

        apply_prof_btn = tk.Button(
            p_btn_bar,
            text="Aplică argumentul la aplicația selectată",
            font=("Segoe UI", 8),
            bg="#374151",
            fg="#E5E7EB",
            bd=0,
            padx=8,
            pady=5,
            cursor="hand2",
            command=self.apply_profile_to_selected_app
        )
        apply_prof_btn.pack(side="left", padx=6)

    # --------------------------------------------------------------------------
    # PANOU DREAPTA: CONFIGURAȚIE LAUNCHER, GIF & BUILD
    # --------------------------------------------------------------------------
    def build_right_panel(self, parent):
        # 1. Tabel aplicații configurate
        top_bar = tk.Frame(parent, bg="#12131a")
        top_bar.pack(fill="x", pady=(0, 6))

        sec_title = tk.Label(
            top_bar,
            text="🚀 APLICAȚII CONFIGURATE PENTRU LANSARE",
            font=("Segoe UI", 10, "bold"),
            fg="#00FFA3",
            bg="#12131a"
        )
        sec_title.pack(side="left")

        # Tabel aplicații alese
        table_frame = tk.Frame(parent, bg="#12131a")
        table_frame.pack(fill="both", expand=True)

        self.app_tree = ttk.Treeview(
            table_frame,
            columns=("enabled", "name", "args", "path"),
            show="headings",
            selectmode="browse",
            height=6
        )
        self.app_tree.heading("enabled", text="Activ", anchor="center")
        self.app_tree.heading("name", text="Nume", anchor="w")
        self.app_tree.heading("args", text="Argumente / Profil", anchor="w")
        self.app_tree.heading("path", text="Cale Fișier", anchor="w")

        self.app_tree.column("enabled", width=50, anchor="center")
        self.app_tree.column("name", width=140, anchor="w")
        self.app_tree.column("args", width=160, anchor="w")
        self.app_tree.column("path", width=160, anchor="w")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.app_tree.yview)
        self.app_tree.configure(yscrollcommand=scrollbar.set)
        self.app_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.app_tree.bind("<<TreeviewSelect>>", self.on_app_selected_in_tree)

        # Bară comenzi tabel
        app_ctrl_bar = tk.Frame(parent, bg="#12131a")
        app_ctrl_bar.pack(fill="x", pady=(6, 8))

        btn_toggle = tk.Button(
            app_ctrl_bar,
            text="✔/✘ Comută Activ",
            font=("Segoe UI", 8),
            bg="#374151",
            fg="white",
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            command=self.toggle_app_enabled
        )
        btn_toggle.pack(side="left", padx=(0, 4))

        btn_up = tk.Button(
            app_ctrl_bar,
            text="▲ Sus",
            font=("Segoe UI", 8),
            bg="#374151",
            fg="white",
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            command=lambda: self.move_app(-1)
        )
        btn_up.pack(side="left", padx=2)

        btn_down = tk.Button(
            app_ctrl_bar,
            text="▼ Jos",
            font=("Segoe UI", 8),
            bg="#374151",
            fg="white",
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            command=lambda: self.move_app(1)
        )
        btn_down.pack(side="left", padx=2)

        btn_del = tk.Button(
            app_ctrl_bar,
            text="🗑️ Șterge",
            font=("Segoe UI", 8),
            bg="#991B1B",
            fg="white",
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            command=self.delete_selected_app
        )
        btn_del.pack(side="left", padx=4)

        # Formular editare detalii aplicație selectată
        edit_box = tk.LabelFrame(
            parent,
            text="Editează detalii aplicație selectată",
            font=("Segoe UI", 8, "bold"),
            fg="#9CA3AF",
            bg="#181a24",
            bd=1,
            padx=10,
            pady=6
        )
        edit_box.pack(fill="x", pady=(0, 10))

        e_row1 = tk.Frame(edit_box, bg="#181a24")
        e_row1.pack(fill="x", pady=2)
        tk.Label(e_row1, text="Nume:", width=9, anchor="w", fg="#9CA3AF", bg="#181a24").pack(side="left")
        self.edit_name_var = tk.StringVar()
        tk.Entry(e_row1, textvariable=self.edit_name_var, bg="#12131a", fg="white", insertbackground="#00FFA3", bd=1).pack(side="left", fill="x", expand=True)

        e_row2 = tk.Frame(edit_box, bg="#181a24")
        e_row2.pack(fill="x", pady=2)
        tk.Label(e_row2, text="Argumente:", width=9, anchor="w", fg="#9CA3AF", bg="#181a24").pack(side="left")
        self.edit_args_var = tk.StringVar()
        tk.Entry(e_row2, textvariable=self.edit_args_var, bg="#12131a", fg="white", insertbackground="#00FFA3", bd=1).pack(side="left", fill="x", expand=True)

        e_row3 = tk.Frame(edit_box, bg="#181a24")
        e_row3.pack(fill="x", pady=2)
        tk.Label(e_row3, text="Cale fișier:", width=9, anchor="w", fg="#9CA3AF", bg="#181a24").pack(side="left")
        self.edit_path_var = tk.StringVar()
        tk.Entry(e_row3, textvariable=self.edit_path_var, bg="#12131a", fg="white", insertbackground="#00FFA3", bd=1).pack(side="left", fill="x", expand=True)

        btn_save_edit = tk.Button(
            edit_box,
            text="💾 Salvează modificările aplicației",
            font=("Segoe UI", 8, "bold"),
            bg="#2563EB",
            fg="white",
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.save_app_edits
        )
        btn_save_edit.pack(anchor="e", pady=(4, 2))

        # 2. Configurare GIF & Animație
        gif_box = tk.LabelFrame(
            parent,
            text="🎨 Setări GIF Animat / Imagine Plutitoare",
            font=("Segoe UI", 9, "bold"),
            fg="#F472B6",
            bg="#181a24",
            bd=1,
            padx=12,
            pady=8
        )
        gif_box.pack(fill="x", pady=(0, 10))

        gif_inner = tk.Frame(gif_box, bg="#181a24")
        gif_inner.pack(fill="x")

        # Preview thumbnail
        self.gif_thumb_lbl = tk.Label(gif_inner, text="No Preview", bg="#12131a", fg="#6B7280", width=10, height=5)
        self.gif_thumb_lbl.pack(side="left", padx=(0, 12))

        gif_info = tk.Frame(gif_inner, bg="#181a24")
        gif_info.pack(side="left", fill="x", expand=True)

        self.gif_path_lbl = tk.Label(gif_info, text="", font=("Consolas", 8), fg="#D1D5DB", bg="#181a24", anchor="w")
        self.gif_path_lbl.pack(fill="x", pady=(0, 4))

        g_btn_bar = tk.Frame(gif_info, bg="#181a24")
        g_btn_bar.pack(fill="x")

        btn_pick_gif = tk.Button(
            g_btn_bar,
            text="📁 Alege alt GIF / Imagine...",
            font=("Segoe UI", 8, "bold"),
            bg="#DB2777",
            fg="white",
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.pick_custom_gif
        )
        btn_pick_gif.pack(side="left")

        btn_reset_gif = tk.Button(
            g_btn_bar,
            text="Reset la GIF-ul Funny Implicit",
            font=("Segoe UI", 8),
            bg="#374151",
            fg="#E5E7EB",
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            command=self.reset_default_gif
        )
        btn_reset_gif.pack(side="left", padx=6)

        # Durată afișare
        dur_row = tk.Frame(gif_box, bg="#181a24")
        dur_row.pack(fill="x", pady=(8, 0))
        tk.Label(dur_row, text="Durată afișare pe ecran:", font=("Segoe UI", 9), fg="#9CA3AF", bg="#181a24").pack(side="left")
        self.duration_spin = tk.Spinbox(
            dur_row,
            from_=1.0,
            to=10.0,
            increment=0.5,
            width=5,
            font=("Segoe UI", 9, "bold"),
            bg="#12131a",
            fg="white",
            bd=1
        )
        self.duration_spin.delete(0, "end")
        self.duration_spin.insert(0, str(self.config.get("duration_seconds", 3.0)))
        self.duration_spin.pack(side="left", padx=6)
        tk.Label(dur_row, text="secunde", font=("Segoe UI", 9), fg="#9CA3AF", bg="#181a24").pack(side="left")

        # 3. Bară finală: Testare & Build Executabil (.exe)
        build_box = tk.Frame(parent, bg="#12131a")
        build_box.pack(fill="x", pady=(5, 0))

        # Nume executabil
        name_row = tk.Frame(build_box, bg="#12131a")
        name_row.pack(fill="x", pady=(0, 8))
        tk.Label(name_row, text="Nume executabil generat:", font=("Segoe UI", 9), fg="#9CA3AF", bg="#12131a").pack(side="left")
        self.exe_name_var = tk.StringVar(value=self.config.get("exe_name", "custom_launcher"))
        tk.Entry(name_row, textvariable=self.exe_name_var, width=22, font=("Segoe UI", 9, "bold"), bg="#1a1c26", fg="#00FFA3", bd=1).pack(side="left", padx=8)
        tk.Label(name_row, text=".exe", font=("Segoe UI", 9, "bold"), fg="#00FFA3", bg="#12131a").pack(side="left")

        # Butoane principale de acțiune
        action_bar = tk.Frame(build_box, bg="#12131a")
        action_bar.pack(fill="x")

        save_cfg_btn = tk.Button(
            action_bar,
            text="💾 Salvează Configurația",
            font=("Segoe UI", 9),
            bg="#374151",
            fg="white",
            bd=0,
            padx=12,
            pady=8,
            cursor="hand2",
            command=self.save_config_to_disk
        )
        save_cfg_btn.pack(side="left", padx=(0, 6))

        preview_btn = tk.Button(
            action_bar,
            text="▶️ Testează Launcher (Preview)",
            font=("Segoe UI", 9, "bold"),
            bg="#4F46E5",
            fg="white",
            bd=0,
            padx=14,
            pady=8,
            cursor="hand2",
            command=self.on_preview_clicked
        )
        preview_btn.pack(side="left", padx=6)

        self.build_btn = tk.Button(
            action_bar,
            text="⚡ GENEREAZĂ EXECUTABIL (.EXE) ⚡",
            font=("Segoe UI", 10, "bold"),
            bg="#10B981",
            fg="white",
            activebackground="#059669",
            activeforeground="white",
            bd=0,
            padx=18,
            pady=8,
            cursor="hand2",
            command=self.on_build_clicked
        )
        self.build_btn.pack(side="right")

        # Actualizează vizualizarea GIF
        self.update_gif_preview()

    # --------------------------------------------------------------------------
    # BACKGROUND SCANS
    # --------------------------------------------------------------------------
    def run_background_scans(self):
        # 1. Profiluri browser
        profiles = get_browser_profiles()
        self.browser_profiles = profiles

        # 2. Aplicații Windows
        apps = scan_windows_shortcuts()
        self.scanned_apps = apps

        # Actualizare interfață pe firul principal
        self.root.after(0, self.populate_scanned_data)

    def populate_scanned_data(self):
        # Profiluri browser
        combo_vals = [p["display"] for p in self.browser_profiles]
        self.profile_combo["values"] = combo_vals
        if combo_vals:
            self.profile_combo.current(0)

        # Listă aplicații
        self.filter_scanned_apps()

    def filter_scanned_apps(self):
        query = self.search_var.get().lower().strip()
        self.scan_tree.delete(*self.scan_tree.get_children())
        for app in self.scanned_apps:
            if not query or query in app["name"].lower() or query in app["path"].lower():
                self.scan_tree.insert("", "end", values=(app["name"], app["path"]))

    # --------------------------------------------------------------------------
    # GESTIONARE LISTĂ APLICAȚII CONFIGURATE
    # --------------------------------------------------------------------------
    def populate_app_tree(self):
        self.app_tree.delete(*self.app_tree.get_children())
        for app in self.config.get("apps", []):
            status = "✔" if app.get("enabled", True) else "✘"
            self.app_tree.insert("", "end", values=(
                status,
                app.get("name", ""),
                app.get("args", ""),
                app.get("path", "")
            ))

    def add_selected_scanned_app(self):
        sel = self.scan_tree.selection()
        if not sel:
            messagebox.showinfo("Atenție", "Te rugăm să selectezi o aplicație din lista din stânga!")
            return
        vals = self.scan_tree.item(sel[0], "values")
        name, path = vals[0], vals[1]

        # Verifică dacă aplicația selectată este Brave sau Chrome pentru a sugera profilul curent
        args = ""
        if "brave" in name.lower() or "brave.exe" in path.lower():
            # Ia profilul selectat în combobox dacă e de Brave
            prof_idx = self.profile_combo.current()
            if prof_idx >= 0 and prof_idx < len(self.browser_profiles):
                p = self.browser_profiles[prof_idx]
                if p["browser"] == "Brave":
                    args = p["arg"]
        elif "chrome" in name.lower() or "chrome.exe" in path.lower():
            prof_idx = self.profile_combo.current()
            if prof_idx >= 0 and prof_idx < len(self.browser_profiles):
                p = self.browser_profiles[prof_idx]
                if p["browser"] == "Chrome":
                    args = p["arg"]

        self.config["apps"].append({
            "name": name,
            "path": path,
            "args": args,
            "enabled": True
        })
        self.populate_app_tree()

    def browse_custom_exe(self):
        file_path = filedialog.askopenfilename(
            title="Alege fișier executabil sau scurtătură",
            filetypes=[("Executabile și Scurtături", "*.exe;*.lnk;*.bat;*.cmd"), ("Toate fișierele", "*.*")]
        )
        if file_path:
            name = os.path.splitext(os.path.basename(file_path))[0]
            self.config["apps"].append({
                "name": name,
                "path": file_path,
                "args": "",
                "enabled": True
            })
            self.populate_app_tree()

    def add_browser_with_profile(self):
        idx = self.profile_combo.current()
        if idx < 0 or idx >= len(self.browser_profiles):
            messagebox.showinfo("Atenție", "Selectează mai întâi un profil din listă!")
            return
        p = self.browser_profiles[idx]
        exe_path = p.get("exe", "")

        # Dacă calea implicită nu există, caută în lista de aplicații scanate
        if not exe_path or not os.path.exists(exe_path):
            target_key = "brave" if p["browser"] == "Brave" else "chrome"
            for app in self.scanned_apps:
                if target_key in app["name"].lower() or target_key in app["path"].lower():
                    exe_path = app["path"]
                    break

        if not exe_path or not os.path.exists(exe_path):
            messagebox.showerror("Eroare", f"Nu am găsit executabilul pentru {p['browser']}. Te rugăm să îl adaugi manual.")
            return

        self.config["apps"].append({
            "name": f"{p['browser']} ({p['name']})",
            "path": exe_path,
            "args": p["arg"],
            "enabled": True
        })
        self.populate_app_tree()

    def apply_profile_to_selected_app(self):
        sel = self.app_tree.selection()
        if not sel:
            messagebox.showinfo("Atenție", "Selectează o aplicație din tabelul din dreapta pentru a-i aplica profilul!")
            return
        idx = self.app_tree.index(sel[0])
        p_idx = self.profile_combo.current()
        if p_idx < 0 or p_idx >= len(self.browser_profiles):
            return
        p = self.browser_profiles[p_idx]
        self.config["apps"][idx]["args"] = p["arg"]
        self.populate_app_tree()
        self.on_app_selected_in_tree()

    def on_app_selected_in_tree(self, event=None):
        sel = self.app_tree.selection()
        if not sel:
            return
        idx = self.app_tree.index(sel[0])
        app = self.config["apps"][idx]
        self.edit_name_var.set(app.get("name", ""))
        self.edit_args_var.set(app.get("args", ""))
        self.edit_path_var.set(app.get("path", ""))

    def save_app_edits(self):
        sel = self.app_tree.selection()
        if not sel:
            return
        idx = self.app_tree.index(sel[0])
        self.config["apps"][idx]["name"] = self.edit_name_var.get().strip()
        self.config["apps"][idx]["args"] = self.edit_args_var.get().strip()
        self.config["apps"][idx]["path"] = self.edit_path_var.get().strip()
        self.populate_app_tree()

    def toggle_app_enabled(self):
        sel = self.app_tree.selection()
        if not sel:
            return
        idx = self.app_tree.index(sel[0])
        self.config["apps"][idx]["enabled"] = not self.config["apps"][idx].get("enabled", True)
        self.populate_app_tree()

    def delete_selected_app(self):
        sel = self.app_tree.selection()
        if not sel:
            return
        idx = self.app_tree.index(sel[0])
        del self.config["apps"][idx]
        self.populate_app_tree()

    def move_app(self, direction):
        sel = self.app_tree.selection()
        if not sel:
            return
        idx = self.app_tree.index(sel[0])
        new_idx = idx + direction
        if 0 <= new_idx < len(self.config["apps"]):
            item = self.config["apps"].pop(idx)
            self.config["apps"].insert(new_idx, item)
            self.populate_app_tree()
            children = self.app_tree.get_children()
            if children:
                self.app_tree.selection_set(children[new_idx])

    # --------------------------------------------------------------------------
    # GESTIONARE GIF / IMAGINE
    # --------------------------------------------------------------------------
    def pick_custom_gif(self):
        chosen = filedialog.askopenfilename(
            title="Alege GIF animat sau imagine",
            filetypes=[("Imagini și GIF-uri", "*.gif;*.png;*.jpg;*.jpeg;*.webp"), ("Toate fișierele", "*.*")]
        )
        if chosen:
            self.config["gif_path"] = chosen
            self.update_gif_preview()

    def reset_default_gif(self):
        self.config["gif_path"] = DEFAULT_GIF
        self.update_gif_preview()

    def update_gif_preview(self):
        gif_path = self.config.get("gif_path", DEFAULT_GIF)
        if not os.path.exists(gif_path):
            self.gif_path_lbl.configure(text=f"Fișier inexistent: {os.path.basename(gif_path)}", fg="#EF4444")
            self.gif_thumb_lbl.configure(image="", text="Lipsă fișier")
            return

        self.gif_path_lbl.configure(text=f"Selectat: {os.path.basename(gif_path)} ({gif_path})", fg="#A7F3D0")

        try:
            pil_img = Image.open(gif_path)
            pil_img.seek(0)
            pil_img = pil_img.copy()
            pil_img.thumbnail((72, 72))
            self.gif_thumbnail = ImageTk.PhotoImage(pil_img)
            self.gif_thumb_lbl.configure(image=self.gif_thumbnail, text="")
        except Exception as e:
            self.gif_thumb_lbl.configure(image="", text="Preview indisponibil")

    # --------------------------------------------------------------------------
    # CONFIGURARE DISK I/O
    # --------------------------------------------------------------------------
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self.config.update(saved)
                return
            except Exception:
                pass

        # Configurație inițială implicită (aplicațiile detectate pe PC-ul tău)
        self.config["apps"] = [
            {
                "name": "Brave Browser (Facultate)",
                "path": r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                "args": '--profile-directory="Facultate"',
                "enabled": True
            },
            {
                "name": "Docker Desktop",
                "path": r"C:\Users\chitu\AppData\Local\Programs\DockerDesktop\Docker Desktop.exe",
                "args": "",
                "enabled": True
            },
            {
                "name": "Antigravity IDE",
                "path": r"C:\Users\chitu\AppData\Local\Programs\Antigravity IDE\Antigravity IDE.exe",
                "args": "",
                "enabled": True
            },
            {
                "name": "GitHub Desktop",
                "path": os.path.expandvars(r"%USERPROFILE%\Desktop\GitHub.lnk"),
                "args": "",
                "enabled": True
            }
        ]

    def save_config_to_disk(self):
        self.sync_form_to_config()
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Succes", f"Configurația a fost salvată în:\n{CONFIG_FILE}")
        except Exception as e:
            messagebox.showerror("Eroare", f"Nu s-a putut salva configurația:\n{e}")

    def sync_form_to_config(self):
        try:
            dur = float(self.duration_spin.get())
            self.config["duration_seconds"] = dur
        except Exception:
            self.config["duration_seconds"] = 3.0

        exe_name = self.exe_name_var.get().strip()
        if exe_name.lower().endswith(".exe"):
            exe_name = exe_name[:-4]
        self.config["exe_name"] = exe_name or "custom_launcher"

    # --------------------------------------------------------------------------
    # TEST PREVIEW & BUILD .EXE
    # --------------------------------------------------------------------------
    def on_preview_clicked(self):
        self.sync_form_to_config()
        run_preview_launcher(self.config)

    def on_build_clicked(self):
        self.sync_form_to_config()
        exe_name = self.config["exe_name"]
        gif_path = self.config.get("gif_path", DEFAULT_GIF)

        if not os.path.exists(gif_path):
            messagebox.showerror("Eroare", f"Fișierul GIF nu există:\n{gif_path}")
            return

        # Fereastră modală de progres
        prog_win = tk.Toplevel(self.root)
        prog_win.title("Compilare Executabil...")
        prog_win.geometry("520x220")
        prog_win.configure(bg="#12131a")
        prog_win.resizable(False, False)
        prog_win.transient(self.root)
        prog_win.grab_set()

        sw = prog_win.winfo_screenwidth()
        sh = prog_win.winfo_screenheight()
        prog_win.geometry(f"520x220+{(sw - 520) // 2}+{(sh - 220) // 2}")

        p_title = tk.Label(prog_win, text=f"⚡ Compilare {exe_name}.exe în curs...", font=("Consolas", 12, "bold"), fg="#00FFA3", bg="#12131a")
        p_title.pack(pady=(20, 10))

        p_status = tk.Label(prog_win, text="Pregătire script și resurse...", font=("Segoe UI", 9), fg="#9CA3AF", bg="#12131a")
        p_status.pack(pady=4)

        pbar = ttk.Progressbar(prog_win, mode="indeterminate", length=400)
        pbar.pack(pady=15)
        pbar.start(10)

        def build_thread():
            try:
                # 1. Creează fișierul runner temporar dedicat
                runner_filename = f"{exe_name}_runner.py"
                runner_path = os.path.join(BASE_DIR, runner_filename)

                # Asigură că GIF-ul e copiat local dacă e extern
                gif_filename = os.path.basename(gif_path)
                local_gif = os.path.join(BASE_DIR, gif_filename)
                if os.path.abspath(gif_path) != os.path.abspath(local_gif):
                    shutil.copy2(gif_path, local_gif)

                # Scrie codul runner
                formatted_config = json.dumps(self.config, indent=2)
                script_content = RUNNER_CODE_TEMPLATE.format(config_json=formatted_config)
                with open(runner_path, "w", encoding="utf-8") as f:
                    f.write(script_content)

                # 2. Execută PyInstaller
                p_status.configure(text="Rulare PyInstaller (împachetare într-un singur fișier .exe)...")
                python_bin = sys.executable
                if getattr(sys, "frozen", False):
                    python_bin = shutil.which("python") or shutil.which("py") or "python"

                cmd = [
                    python_bin, "-m", "PyInstaller",
                    "--noconsole",
                    "--onefile",
                    "--add-data", f"{gif_filename};.",
                    "--name", exe_name,
                    runner_path
                ]

                proc = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)

                if proc.returncode == 0:
                    out_exe = os.path.join(BASE_DIR, "dist", f"{exe_name}.exe")
                    self.root.after(0, lambda: self.on_build_success(prog_win, out_exe))
                else:
                    err_msg = proc.stderr or proc.stdout
                    self.root.after(0, lambda: self.on_build_error(prog_win, err_msg))
            except Exception as e:
                self.root.after(0, lambda: self.on_build_error(prog_win, str(e)))

        threading.Thread(target=build_thread, daemon=True).start()

    def on_build_success(self, prog_win, out_exe):
        try:
            prog_win.destroy()
        except Exception:
            pass

        ans = messagebox.askyesno(
            "🎉 Compilare Reușită!",
            f"Executabilul a fost generat cu succes!\n\nLocație:\n{out_exe}\n\nVrei să deschizi folderul 'dist' acum?"
        )
        if ans:
            dist_dir = os.path.dirname(out_exe)
            if os.path.exists(dist_dir):
                os.startfile(dist_dir)

    def on_build_error(self, prog_win, error_msg):
        try:
            prog_win.destroy()
        except Exception:
            pass
        messagebox.showerror("Eroare la Compilare", f"PyInstaller a întâmpinat o eroare:\n\n{error_msg[:600]}")

# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = LauncherBuilderApp(root)
    app.populate_app_tree()
    root.mainloop()
