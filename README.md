# ASCII Camera 🎥→🔤

Real-time ASCII art webcam renderer with a dedicated Tkinter GUI window.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        ASCIICamera                          │
│  (main class – owns the Tkinter window & orchestrates all)  │
└──────────────────────┬──────────────────────────────────────┘
                       │ spawns
        ┌──────────────▼──────────────┐
        │      CaptureThread          │  Background daemon thread
        │  ┌────────────────────────┐ │
        │  │  cv2.VideoCapture      │ │  Reads frames from webcam
        │  │  → flip (mirror)       │ │
        │  │  → cvtColor (gray)     │ │
        │  │  → ASCIIConverter      │ │  Maps pixels → characters
        │  │  → _latest_ascii (str) │ │  Thread-safe via Lock
        │  └────────────────────────┘ │
        └─────────────────────────────┘
                       │ reads every ~33 ms
        ┌──────────────▼──────────────┐
        │   Tkinter _render() loop    │  Runs on main thread via .after()
        │   • Text widget update      │  No flickering (in-place replace)
        │   • FPS label update        │
        └─────────────────────────────┘
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `opencv-python` | Webcam capture, color conversion, resize |
| `numpy` | Vectorised pixel→char lookup (fast LUT) |
| `Pillow` | `ImageTk` for optional colour thumbnail |

Tkinter ships with the Python standard library on all major platforms.

---

## Installation

```bash
# 1. Clone / download the files
cd ascii_camera/

# 2. (Recommended) create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

> **Linux note:** Tkinter may need a separate install:
> `sudo apt install python3-tk`

---

## Running

```bash
# Defaults: 120 columns, extended charset, 30 FPS, camera 0
python ascii_camera.py

# Narrow output, retro "blocks" palette, 24 FPS
python ascii_camera.py --cols 80 --char-set blocks --fps 24

# Show colour thumbnail alongside ASCII art
python ascii_camera.py --color

# Use a second camera
python ascii_camera.py --camera 1

# All options
python ascii_camera.py --help
```

---

## Keyboard Shortcuts (in the GUI window)

| Key | Action |
|---|---|
| `Q` / `Esc` | Quit |
| `+` / `=` | +10 columns (more detail) |
| `-` | −10 columns (larger "pixels") |
| `C` | Toggle colour thumbnail |

---

## CLI Options

```
--cols       INT   Character columns in output        [default: 120]
--fps        INT   Target capture framerate            [default: 30]
--camera     INT   Camera device index                [default: 0]
--char-set   STR   Character palette to use           [default: extended]
                   Choices: standard, extended, blocks, minimal, binary, dots
--color            Show colour thumbnail alongside ASCII art
```

---

## Character Palettes

| Name | Characters (dark → light) |
|---|---|
| `standard` | ` .:-=+*#%@` |
| `extended` | 70-character gradient for maximum tonal range |
| `blocks` | ` ░▒▓█` — Unicode block elements |
| `minimal` | ` .oO@` |
| `binary` | ` 1` |
| `dots` | ` ·•●` |

---

## Performance Notes

- **LUT (Look-Up Table)** conversion: pixel→char mapping is a single numpy
  fancy-index operation on the full frame — O(n) with no Python loops.
- **`cv2.resize` + `INTER_AREA`** downsamples before conversion, keeping the
  data small for the LUT step.
- **Daemon thread** with a sleep throttle avoids burning 100% CPU.
- **Tkinter `.after()`** drives the render loop on the main thread —
  no cross-thread widget mutations, no locks needed for the UI.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `Cannot open camera 0` | Another app is using the webcam; close it, or try `--camera 1` |
| Stretched / squished image | Adjust `ASCIIConverter.CHAR_ASPECT` (default 0.45) to match your font |
| Very slow FPS | Lower `--cols` or `--fps`; or switch to `--char-set standard` |
| Blank window on Linux | Ensure `python3-tk` is installed |
