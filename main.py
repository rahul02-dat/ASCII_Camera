"""
ascii_camera.py
───────────────────────────────────────────────────────────────
Real-time ASCII art webcam renderer.

Dependencies:
    pip install opencv-python numpy pygame

Run:
    python ascii_camera.py
    python ascii_camera.py --cols 120 --char-set extended --fps 30
───────────────────────────────────────────────────────────────
"""

import argparse
import sys
import threading
import time

import cv2
import numpy as np
import pygame


# ─────────────────────────────────────────────
# ASCII CHARACTER PALETTES
# ─────────────────────────────────────────────

CHAR_SETS = {
    # Ordered dark → light
    "standard":  r" .:-=+*#%@",
    "extended":  r" .'`^\",:;Il!i><~+_-?][}{1)(|\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",
    "blocks":    " ░▒▓█",
    "minimal":   " .oO@",
    "binary":    " 1",
    "dots":      " ·•●",
}


# ─────────────────────────────────────────────
# CORE ENGINE
# ─────────────────────────────────────────────

class ASCIIConverter:
    """Converts a grayscale numpy frame into an ASCII art string."""

    # Terminal/monospace fonts are typically ~2× taller than wide.
    # Compensate by sampling fewer rows relative to columns.
    CHAR_ASPECT = 0.45   # width / height of a typical monospace character

    def __init__(self, char_set: str = "extended"):
        palette = CHAR_SETS.get(char_set, CHAR_SETS["extended"])
        # Build a lookup array: intensity 0-255 → character index
        n = len(palette)
        indices = (np.arange(256) * (n - 1) / 255).astype(np.uint8)
        self._lut = np.array(list(palette), dtype="U1")[indices]   # shape (256,)

    def frame_to_ascii(self, gray: np.ndarray, cols: int = 100) -> str:
        """
        Convert a grayscale frame to an ASCII string.

        Parameters
        ----------
        gray : np.ndarray  – single-channel uint8 frame
        cols : int         – number of character columns in output

        Returns
        -------
        str  – newline-separated ASCII art
        """
        h, w = gray.shape
        # Derive row count so pixels map to square-ish cells on screen
        cell_w = w / cols
        cell_h = cell_w / self.CHAR_ASPECT
        rows = max(1, int(h / cell_h))

        # Resize once (fast); PIL resize for quality, numpy for speed
        small = cv2.resize(gray, (cols, rows), interpolation=cv2.INTER_AREA)

        # Map every pixel to its character via the lookup table
        char_array = self._lut[small]          # shape (rows, cols), dtype U1

        # Join rows into a single string efficiently
        lines = ["".join(row) for row in char_array]
        return "\n".join(lines)


# ─────────────────────────────────────────────
# CAMERA CAPTURE THREAD
# ─────────────────────────────────────────────

class CaptureThread(threading.Thread):
    """
    Background thread: continuously reads frames from the webcam
    and stores the latest converted ASCII string + optional colour image.
    """

    def __init__(self, converter: ASCIIConverter, cols: int,
                 target_fps: int = 30, camera_index: int = 0):
        super().__init__(daemon=True)
        self.converter = converter
        self.cols = cols
        self.target_fps = target_fps
        self.camera_index = camera_index

        self._cap: cv2.VideoCapture | None = None
        self._lock = threading.Lock()
        self._latest_ascii: str = ""
        self._latest_frame: np.ndarray | None = None
        self._running = False
        self._frame_count = 0
        self._fps_actual = 0.0

    # ── public interface ──────────────────────

    @property
    def latest_ascii(self) -> str:
        with self._lock:
            return self._latest_ascii

    @property
    def latest_frame(self) -> np.ndarray | None:
        with self._lock:
            return self._latest_frame

    @property
    def fps_actual(self) -> float:
        return self._fps_actual

    def stop(self):
        self._running = False

    # ── thread body ───────────────────────────

    def run(self):
        self._cap = cv2.VideoCapture(self.camera_index)
        if not self._cap.isOpened():
            raise RuntimeError(
                f"Cannot open camera {self.camera_index}. "
                "Check that a webcam is connected and not in use."
            )

        # Hint the driver at a sensible resolution
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self._cap.set(cv2.CAP_PROP_FPS, self.target_fps)

        interval = 1.0 / self.target_fps
        self._running = True
        t_fps = time.perf_counter()
        fps_frames = 0

        while self._running:
            t0 = time.perf_counter()

            ret, bgr = self._cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            # Mirror so it feels like a selfie cam
            bgr = cv2.flip(bgr, 1)

            # Grayscale for ASCII conversion
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            ascii_str = self.converter.frame_to_ascii(gray, self.cols)

            with self._lock:
                self._latest_ascii = ascii_str
                self._latest_frame = bgr
                self._frame_count += 1

            # Rolling FPS measurement
            fps_frames += 1
            elapsed = time.perf_counter() - t_fps
            if elapsed >= 1.0:
                self._fps_actual = fps_frames / elapsed
                fps_frames = 0
                t_fps = time.perf_counter()

            # Throttle to target FPS
            sleep_t = interval - (time.perf_counter() - t0)
            if sleep_t > 0:
                time.sleep(sleep_t)

        if self._cap:
            self._cap.release()


# ─────────────────────────────────────────────
# PYGAME RENDERER
# ─────────────────────────────────────────────

class ASCIICamera:
    """
    Main application class.  Owns the Pygame window, the capture thread,
    and the render loop.  Pygame is used instead of Tkinter because it
    ships as a pure pip package with no system-library dependencies.
    """

    # ── Appearance ────────────────────────────
    FONT_SIZE  = 13           # px — monospace cell height
    BG_COLOR   = (13,  13,  13)    # near-black
    FG_COLOR   = (0,  255,  65)    # matrix green
    DIM_COLOR  = (0,   85,  20)    # muted green for HUD
    TITLE_H    = 28               # px reserved for top HUD bar
    STATUS_H   = 20               # px reserved for bottom status bar
    PADDING    = 6                # px horizontal padding

    def __init__(self,
                 cols: int = 120,
                 char_set: str = "extended",
                 target_fps: int = 30,
                 camera_index: int = 0):

        self.cols        = cols
        self.target_fps  = target_fps
        self._running    = False

        # ── ASCII engine ──────────────────────
        self.converter = ASCIIConverter(char_set=char_set)

        # ── Camera thread ─────────────────────
        self.capture = CaptureThread(
            converter=self.converter,
            cols=cols,
            target_fps=target_fps,
            camera_index=camera_index,
        )

        # ── Pygame init ───────────────────────
        pygame.init()
        # SysFont falls back gracefully; "couriernew" / "mono" both work
        self._font = pygame.font.SysFont("couriernew,courier,monospace",
                                         self.FONT_SIZE)
        self._char_w, self._char_h = self._font.size("X")

        # Start with a sensible window size; user can resize freely
        init_w = self._char_w * cols + self.PADDING * 2
        init_h = 600
        self._screen = pygame.display.set_mode(
            (init_w, init_h),
            pygame.RESIZABLE,
        )
        pygame.display.set_caption("ASCII Camera")
        self._clock = pygame.time.Clock()

        # Pre-render glyph cache: intensity → pygame.Surface
        # Rendering thousands of individual characters per frame is slow;
        # caching the 95 printable ASCII surfaces cuts render time by ~10×.
        self._glyph_cache: dict[str, pygame.Surface] = {}

    # ── Glyph caching ─────────────────────────

    def _glyph(self, ch: str) -> pygame.Surface:
        """Return a cached pre-rendered surface for a single character."""
        surf = self._glyph_cache.get(ch)
        if surf is None:
            surf = self._font.render(ch, False, self.FG_COLOR, self.BG_COLOR)
            self._glyph_cache[ch] = surf
        return surf

    # ── Render helpers ────────────────────────

    def _draw_hud(self, fps: float):
        """Draw the top title bar and bottom status strip."""
        w = self._screen.get_width()
        h = self._screen.get_height()

        # Separator lines
        pygame.draw.line(self._screen, self.DIM_COLOR,
                         (0, self.TITLE_H - 1), (w, self.TITLE_H - 1))
        pygame.draw.line(self._screen, self.DIM_COLOR,
                         (0, h - self.STATUS_H), (w, h - self.STATUS_H))

        # Title
        title = self._font.render("▶ ASCII CAMERA", False, self.FG_COLOR)
        self._screen.blit(title, (self.PADDING, 4))

        # FPS + cols counter (top-right)
        info = self._font.render(
            f"FPS {fps:5.1f}  COLS {self.cols}", False, self.DIM_COLOR
        )
        self._screen.blit(info, (w - info.get_width() - self.PADDING, 4))

        # Status bar (bottom)
        hint = self._font.render(
            "[Q] Quit    [+/-] Columns    [F] Fullscreen",
            False, self.DIM_COLOR,
        )
        self._screen.blit(hint, (self.PADDING, h - self.STATUS_H + 3))

    def _draw_ascii(self, ascii_str: str):
        """Blit each character glyph from the cache onto the screen."""
        cw, ch = self._char_w, self._char_h
        x0 = self.PADDING
        y0 = self.TITLE_H + 2

        y = y0
        for line in ascii_str.split("\n"):
            x = x0
            for char in line:
                if char != " ":               # skip blitting spaces (BG shows through)
                    self._screen.blit(self._glyph(char), (x, y))
                x += cw
            y += ch

    # ── Main loop ─────────────────────────────

    def run(self):
        self.capture.start()
        self._running = True
        fullscreen = False

        # Give camera time to warm up
        time.sleep(0.4)

        while self._running:
            # ── Events ────────────────────────
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_q, pygame.K_ESCAPE):
                        self._running = False
                    elif event.key in (pygame.K_PLUS, pygame.K_EQUALS,
                                       pygame.K_KP_PLUS):
                        self._adjust_cols(+10)
                    elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        self._adjust_cols(-10)
                    elif event.key == pygame.K_f:
                        fullscreen = not fullscreen
                        flags = pygame.FULLSCREEN if fullscreen else pygame.RESIZABLE
                        self._screen = pygame.display.set_mode(
                            (0, 0) if fullscreen else (800, 600), flags
                        )

                elif event.type == pygame.VIDEORESIZE:
                    # Recalculate columns to fill the new window width
                    new_cols = max(40, (event.w - self.PADDING * 2) // self._char_w)
                    self.cols = new_cols
                    self.capture.cols = new_cols

            # ── Clear ─────────────────────────
            self._screen.fill(self.BG_COLOR)

            # ── ASCII art ─────────────────────
            ascii_str = self.capture.latest_ascii
            if ascii_str:
                self._draw_ascii(ascii_str)

            # ── HUD overlay ───────────────────
            self._draw_hud(self.capture.fps_actual)

            pygame.display.flip()
            self._clock.tick(self.target_fps)

        self.quit()

    # ── Control helpers ───────────────────────

    def _adjust_cols(self, delta: int):
        self.cols = max(40, min(300, self.cols + delta))
        self.capture.cols = self.cols
        self._glyph_cache.clear()  # font size unchanged, but clear anyway

    # ── Cleanup ───────────────────────────────

    def quit(self):
        print("\n[ascii_camera] Shutting down…")
        self.capture.stop()
        time.sleep(0.2)   # let the thread release the camera
        pygame.quit()


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Real-time ASCII art webcam renderer",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--cols",     type=int, default=120,
                   help="Number of character columns")
    p.add_argument("--fps",      type=int, default=30,
                   help="Target capture FPS")
    p.add_argument("--camera",   type=int, default=0,
                   help="Camera device index")
    p.add_argument("--char-set", type=str, default="extended",
                   choices=list(CHAR_SETS.keys()),
                   help="ASCII character palette")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    print("=" * 56)
    print("  ASCII CAMERA  (Pygame backend)")
    print("=" * 56)
    print(f"  Columns   : {args.cols}")
    print(f"  FPS target: {args.fps}")
    print(f"  Char set  : {args.char_set}")
    print(f"  Camera    : {args.camera}")
    print("=" * 56)
    print("  [Q/Esc] Quit    [+/-] Columns    [F] Fullscreen")
    print()

    try:
        app = ASCIICamera(
            cols=args.cols,
            char_set=args.char_set,
            target_fps=args.fps,
            camera_index=args.camera,
        )
        app.run()
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[ascii_camera] Interrupted.")