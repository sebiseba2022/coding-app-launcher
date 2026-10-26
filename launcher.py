import os
import sys
import subprocess
import tkinter as tk

# ==============================================================================
# CONFIGURARE APLICAȚII
# ==============================================================================
BRAVE_EXE = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
BRAVE_PROFILE = "--profile-directory=Facultate"

# Căi detectate pe sistemul tău (cu căi alternative de rezervă)
DOCKER_EXE = r"C:\Users\chitu\AppData\Local\Programs\DockerDesktop\Docker Desktop.exe"
DOCKER_FALLBACKS = [
    r"C:\Program Files\Docker\Docker\Docker Desktop.exe",
    os.path.expandvars(r"%USERPROFILE%\Desktop\Docker Desktop.lnk")
]

ANTIGRAVITY_EXE = r"C:\Users\chitu\AppData\Local\Programs\Antigravity IDE\Antigravity IDE.exe"
ANTIGRAVITY_FALLBACKS = [
    r"C:\Users\chitu\AppData\Local\Programs\antigravity\Antigravity.exe",
    r"C:\Program Files\AntigravityIDE\AntigravityIDE.exe",
    os.path.expandvars(r"%USERPROFILE%\Desktop\Antigravity.lnk")
]

GITHUB_EXE = os.path.expandvars(r"%USERPROFILE%\Desktop\GitHub.lnk")
GITHUB_FALLBACKS = [
    r"C:\Users\Chitu\Downloads\GitHub.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\GitHubDesktop\GitHubDesktop.exe")
]

# Durata afișării iconiței/GIF-ului plutitor (3 secunde)
DISPLAY_DURATION_MS = 3000

# ==============================================================================
# UTILITARE
# ==============================================================================
def resource_path(relative_path):
    """
    Returnează calea absolută către resurse (GIF/imagini),
    compatibil atât în modul script cât și după compilare cu PyInstaller.
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

def launch_app(target_path, fallbacks=None, args=None):
    """Lansează o aplicație căutând calea primară sau alternativele."""
    candidates = [target_path] + (fallbacks or [])
    for path in candidates:
        if path and os.path.exists(path):
            try:
                if path.lower().endswith(".lnk") or not args:
                    os.startfile(path)
                else:
                    subprocess.Popen([path] + args)
                return True
            except Exception:
                pass
    return False

def launch_all_apps():
    """Lansează automat toate aplicațiile configurate."""
    apps = [
        (BRAVE_EXE, [BRAVE_EXE], [BRAVE_PROFILE]),
        (DOCKER_EXE, DOCKER_FALLBACKS, None),
        (ANTIGRAVITY_EXE, ANTIGRAVITY_FALLBACKS, None),
        (GITHUB_EXE, GITHUB_FALLBACKS, None)
    ]
    for main_path, fallbacks, args in apps:
        launch_app(main_path, fallbacks, args)

# ==============================================================================
# FLOATING GIF SPLASH (FĂRĂ FEREASTRĂ / CHROME)
# ==============================================================================
class FloatingGifSplash:
    def __init__(self, root):
        self.root = root

        # Fără ramă de fereastră (fără bară de titlu, butoane, chenar)
        self.root.overrideredirect(True)
        # Menține iconița plutitoare deasupra altor ferestre
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#000000")

        # Încărcare cadre GIF animat
        self.gif_path = resource_path("coding_begin.gif")
        self.frames = []
        self.frame_index = 0
        self.load_gif_frames()

        if self.frames:
            w = self.frames[0].width()
            h = self.frames[0].height()
        else:
            w, h = 380, 380

        # Centrare pe ecran
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        # Doar GIF-ul pe ecran, fără niciun alt element vizual
        if self.frames:
            self.label = tk.Label(
                self.root,
                image=self.frames[0],
                bd=0,
                highlightthickness=0,
                bg="#000000"
            )
            self.label.pack(fill="both", expand=True)
            self.animate_gif()

        # Posibilitate de închidere anticipată prin click sau tasta ESC
        self.root.bind("<Escape>", lambda e: self.finish_and_launch())
        self.root.bind("<Button-1>", lambda e: self.finish_and_launch())

        # După exact 3 secunde, închide iconița plutitoare și deschide automat toate aplicațiile
        self.root.after(DISPLAY_DURATION_MS, self.finish_and_launch)

    def load_gif_frames(self):
        if not os.path.exists(self.gif_path):
            return
        idx = 0
        while True:
            try:
                frame = tk.PhotoImage(file=self.gif_path, format=f"gif -index {idx}")
                self.frames.append(frame)
                idx += 1
            except Exception:
                break

    def animate_gif(self):
        if not self.frames:
            return
        self.frame_index = (self.frame_index + 1) % len(self.frames)
        self.label.configure(image=self.frames[self.frame_index])
        self.root.after(70, self.animate_gif)

    def finish_and_launch(self):
        # Distruge fereastra plutitoare
        try:
            self.root.destroy()
        except Exception:
            pass
        # Lansează automat toate aplicațiile
        launch_all_apps()

# ==============================================================================
# MAIN
# ==============================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = FloatingGifSplash(root)
    root.mainloop()
