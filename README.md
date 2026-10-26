# 🚀 Coding App Launcher

Un utilitar modern, rapid și vizual pentru pornirea simultană a întregului mediu de lucru / coding (Brave, Docker, IDE, GitHub etc.).

La pornire, afișează o **iconiță plutitoare animată (GIF meme cyberpunk „LET THE CODING BEGIN!”)** fără nicio fereastră standard (borderless splash), iar după 3 secunde deschide automat toate aplicațiile configurate.

---

## ✨ Componente Incluse

### 1. `launcher.py` / `dist/launcher.exe`
- **Floating Icon Splash:** Afișează direct în centrul ecranului GIF-ul animat fără margini, butoane sau ferestre standard (`topmost` + `borderless`).
- **Pornire automată:** După 3 secunde, iconița dispare și deschide automat toate uneltele tale de dezvoltare.
- Poate fi oprit instant oricând printr-un simplu click sau tasta `ESC`.

### 2. `builder.py` (Configurator & Generator Vizual)
O aplicație completă cu interfață grafică modernă (*Dark Cyber UI*) prin care poți:
- 🔍 **Scana automat aplicațiile din Windows:** Detectează peste 130 de aplicații instalate în sistem (Start Menu & Desktop) cu căutare și filtrare instantanee.
- 🌐 **Detecta profilurile de browser:** Citește automat profilurile utilizator din **Brave** și **Google Chrome** și adaugă automat parametrul `--profile-directory="..."`.
- 🎨 **Personaliza vizualul:** Permite alegerea oricărui alt GIF sau imagine (`.gif`, `.png`, `.jpg`), modificarea duratei de afișare și previzualizare thumbnail în timp real.
- ▶️ **Testare imediată (Preview):** Poți testa launcher-ul configurat fără să aștepți compilarea.
- ⚡ **Generare Executabil `.exe`:** Cu un singur click compilează un nou `.exe` de sine stătător în folderul `dist/` cu PyInstaller, împachetând noul GIF și toate setările alese!

---

## 🛠️ Instalare & Cerințe

Ai nevoie de Python 3.10+ instalat.

```powershell
# Clonare repository
git clone https://github.com/sebiseba2022/coding-app-launcher.git
cd coding-app-launcher

# Instalare dependențe
pip install -r requirements.txt
```

---

## 🚀 Utilizare

### Rulare Launcher Rapid:
```powershell
python launcher.py
```
*sau deschide direct executabilul gata compilat din `dist/launcher.exe`.*

### Rulare Builder & Configurator:
```powershell
python builder.py
```

---

## 📦 Compilare Manuală cu PyInstaller (opțional)

Dacă dorești să recompilezi manual `launcher.py`:

```powershell
python -m PyInstaller --noconsole --onefile --add-data "coding_begin.gif;." launcher.py
```
*(Executabilul rezultat va fi salvat în `dist/launcher.exe`)*
