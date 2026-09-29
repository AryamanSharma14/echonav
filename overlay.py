"""EchoNav status overlay — two-layer accessibility HUD:

1. ScreenBorder: Fullscreen transparent window with 2px colored border indicating system state.
   Configured with Win32 WS_EX_TRANSPARENT so mouse clicks pass through completely to underlying apps.
2. CenterCapsule: High-contrast frosted glass status pill anchored at screen bottom.
   Configured with Win32 WS_EX_NOACTIVATE so redrawing never steals keyboard focus.

Thread-safe: call overlay.update(state, text) from any thread.
Run overlay.run() from the main thread (blocks in tkinter mainloop).
"""

from __future__ import annotations

import logging
import os
import queue
import sys
import tkinter as tk
from tkinter import font as tkfont
from typing import Optional

import config

logger = logging.getLogger("echonav.overlay")

_STATE_COLORS = {
    "idle": "#3a3f4a",        # dim gray — border always visible
    "listening": "#00d4f5",   # cyan
    "thinking": "#7c6af7",    # violet
    "acting": "#00d97e",      # green
    "confirming": "#f5a623",  # amber
    "done": "#00d97e",        # green
    "error": "#e05c5c",       # muted red
}

_DEFAULT_TEXT = {
    "idle": "Ready for your next task",
    "listening": "Listening… tell me your next objective",
    "thinking": "Processing screen…",
    "acting": "Executing action",
    "confirming": "Say yes to confirm, or no to cancel",
    "done": "Task complete",
    "error": "Something went wrong",
}

_TRANSPARENT = "#020203"  # Windows renders this color as fully transparent
_CAP_BG = "#18191f"       # capsule window background
_CAP_INNER = "#1e1f28"    # capsule body fill
_CAP_ALPHA = 0.93


class NullOverlay:
    """Headless dummy overlay for CI/testing or environments without a physical display."""

    def __init__(self) -> None:
        self._queue: queue.Queue = queue.Queue()
        self._history: list = []

    def update(self, state: str, text: str = "") -> None:
        self._queue.put((state, text))
        self._history.append((state, text))

    def run(self) -> None:
        pass


class Overlay:
    """Public facade managing the ambient screen border and floating status capsule."""

    def __init__(self) -> None:
        self._queue: queue.Queue = queue.Queue()
        self._root: Optional[tk.Tk] = None
        self._capsule_win: Optional[tk.Toplevel] = None
        self._border_canvas: Optional[tk.Canvas] = None
        self._border_rect = None
        self._cap_canvas: Optional[tk.Canvas] = None
        self._cap_border = None
        self._orb = None
        self._text_lbl: Optional[tk.Label] = None
        self._right_lbl: Optional[tk.Label] = None
        self._current_state = "idle"
        self._pulse_up = True
        self._pulse_val = 180
        self._spin_idx = 0

    def update(self, state: str, text: str = "") -> None:
        """Thread-safe. Put a state update on the queue."""
        self._queue.put((state, text))

    def run(self) -> None:
        """Blocking — must be called from the main thread.

        Starts the tkinter mainloop; polls the queue every 100 ms for updates.
        """
        if os.getenv("HEADLESS", "0") == "1":
            logger.info("HEADLESS mode set: skipping GUI overlay loop.")
            return

        try:
            sw, sh = self._setup_border()
            self._setup_capsule(sw, sh)
            self._poll()
            self._animate()
            self._root.mainloop()
        except Exception as exc:
            logger.warning(f"Could not initialize Tkinter overlay ({exc}). Continuing headless.")

    @staticmethod
    def _right_symbol(state: str) -> str:
        return {
            "idle": "o",
            "listening": "@",
            "thinking": "*",
            "acting": ">",
            "confirming": "!",
            "done": "+",
            "error": "x",
        }.get(state, "")

    # ── Window setup ──────────────────────────────────────────────────

    def _setup_border(self):
        """Create the fullscreen transparent border window. Returns (sw, sh)."""
        root = tk.Tk()
        self._root = root
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 1.0)
        root.configure(bg=_TRANSPARENT)
        root.attributes("-transparentcolor", _TRANSPARENT)

        if sys.platform == "win32":
            import ctypes
            try:
                sw = ctypes.windll.user32.GetSystemMetrics(0)
                sh = ctypes.windll.user32.GetSystemMetrics(1)
            except Exception:
                sw = root.winfo_screenwidth()
                sh = root.winfo_screenheight()
        else:
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()

        root.geometry(f"{sw}x{sh}+0+0")

        canvas = tk.Canvas(
            root, width=sw, height=sh,
            bg=_TRANSPARENT, highlightthickness=0, bd=0
        )
        canvas.pack()
        self._border_canvas = canvas

        # 2px colored rectangle — 3px inset so it's fully visible
        self._border_rect = canvas.create_rectangle(
            3, 3, sw - 3, sh - 3,
            outline=_STATE_COLORS["idle"], width=2, fill=""
        )

        # Apply Win32 WS_EX_TRANSPARENT & WS_EX_NOACTIVATE so clicks fall through and focus is preserved
        self._apply_win32_styles(root, transparent_clickthrough=True)
        return sw, sh

    def _setup_capsule(self, sw: int, sh: int) -> None:
        """Create the bottom-anchored glass-pill Toplevel child."""
        W = getattr(config, "OVERLAY_WIDTH", 580)
        H = getattr(config, "OVERLAY_HEIGHT", 82)
        bottom_margin = getattr(config, "OVERLAY_BOTTOM_MARGIN", 60)
        x = (sw - W) // 2
        y = max(0, sh - H - bottom_margin)

        win = tk.Toplevel(self._root)
        self._capsule_win = win
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", _CAP_ALPHA)
        win.configure(bg=_CAP_BG)
        win.geometry(f"{W}x{H}+{x}+{y}")

        canvas = tk.Canvas(
            win, width=W, height=H,
            bg=_CAP_BG, highlightthickness=0, bd=0
        )
        canvas.place(x=0, y=0)
        self._cap_canvas = canvas

        r = 36
        # body (dark fill)
        _rounded_rect(canvas, 2, 2, W - 2, H - 2, r, fill=_CAP_INNER, outline="")
        # border (state-colored outline, stored for updates)
        self._cap_border = _rounded_rect(
            canvas, 1, 1, W - 1, H - 1, r,
            fill="", outline=_STATE_COLORS["idle"], width=2
        )

        # left orb
        ox, oy, orb_r = 36, H // 2, 10
        self._orb = canvas.create_oval(
            ox - orb_r, oy - orb_r, ox + orb_r, oy + orb_r,
            fill=_STATE_COLORS["idle"], outline=""
        )

        main_fnt = tkfont.Font(family="Segoe UI", size=13, weight="bold")
        orb_fnt = tkfont.Font(family="Segoe UI Emoji", size=14, weight="bold")

        self._text_lbl = tk.Label(
            win, text=_DEFAULT_TEXT["idle"],
            font=main_fnt, fg=_STATE_COLORS["idle"],
            bg=_CAP_INNER, anchor="center", wraplength=380,
        )
        self._text_lbl.place(x=62, y=0, width=W - 122, height=H)

        self._right_lbl = tk.Label(
            win, text=self._right_symbol("idle"),
            font=orb_fnt, fg=_STATE_COLORS["idle"],
            bg=_CAP_INNER, anchor="center",
        )
        self._right_lbl.place(x=W - 58, y=0, width=52, height=H)

        self._apply_win32_styles(win, transparent_clickthrough=False)

    @staticmethod
    def _apply_win32_styles(window, transparent_clickthrough: bool = False) -> None:
        """Apply Win32 extended window styles to prevent focus stealing and enable clickthrough."""
        if sys.platform != "win32":
            return
        import ctypes
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        WS_EX_NOACTIVATE = 0x08000000
        try:
            window.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id()) or window.winfo_id()
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            new_style = style | WS_EX_LAYERED | WS_EX_NOACTIVATE
            if transparent_clickthrough:
                new_style |= WS_EX_TRANSPARENT
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
        except Exception:
            pass

    # ── Poll & apply ──────────────────────────────────────────────────

    def _poll(self) -> None:
        """Drain queue and update both windows. Reschedules every 100 ms."""
        try:
            while True:
                state, text = self._queue.get_nowait()
                self._apply(state, text)
        except queue.Empty:
            pass
        if self._root:
            self._root.after(100, self._poll)

    def _apply(self, state: str, text: str) -> None:
        self._current_state = state
        color = _STATE_COLORS.get(state, "#ffffff")
        label = text if text else _DEFAULT_TEXT.get(state, "")

        if self._border_canvas and self._border_rect:
            self._border_canvas.itemconfig(self._border_rect, outline=color)
        if self._cap_canvas and self._cap_border:
            self._cap_canvas.itemconfig(self._cap_border, outline=color)
        if self._cap_canvas and self._orb:
            self._cap_canvas.itemconfig(self._orb, fill=color)
        if self._text_lbl:
            self._text_lbl.config(text=label, fg=color)
        if self._right_lbl:
            self._right_lbl.config(text=self._right_symbol(state), fg=color)

    # ── Animation loop ────────────────────────────────────────────────

    def _animate(self) -> None:
        """80 ms loop: orb pulse while listening, spinner while thinking/acting."""
        if not self._root:
            return
        state = self._current_state

        if state == "listening":
            self._pulse_val += 12 if self._pulse_up else -12
            self._pulse_val = max(80, min(255, self._pulse_val))
            if self._pulse_val >= 255:
                self._pulse_up = False
            elif self._pulse_val <= 80:
                self._pulse_up = True
            base = _STATE_COLORS.get(state, "#00d4f5")
            if self._cap_canvas and self._orb:
                self._cap_canvas.itemconfig(self._orb, fill=_blend(base, self._pulse_val))
        else:
            self._pulse_val = 200
            self._pulse_up = True

        if state in ("thinking", "acting"):
            frames = ["\u25dc", "\u25dd", "\u25de", "\u25df"]  # ◜◝◞◟
            self._spin_idx = (self._spin_idx + 1) % len(frames)
            if self._right_lbl:
                self._right_lbl.config(text=frames[self._spin_idx])
        else:
            if self._right_lbl:
                self._right_lbl.config(text=self._right_symbol(state))

        self._root.after(80, self._animate)


# ── Module-level helpers ───────────────────────────────────────────────

def _rounded_rect(canvas, x1, y1, x2, y2, r, **kwargs):
    """Draw a smooth rounded rectangle polygon on canvas. Returns item id."""
    points = [
        x1 + r, y1, x2 - r, y1,
        x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2,
        x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r,
        x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


def _blend(hex_color: str, alpha: int) -> str:
    """Blend hex_color toward capsule bg #18191f. alpha: 80=dim, 255=full color."""
    bg = (0x18, 0x19, 0x1f)
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    a = alpha / 255
    return "#{:02x}{:02x}{:02x}".format(
        int(bg[0] + (r - bg[0]) * a),
        int(bg[1] + (g - bg[1]) * a),
        int(bg[2] + (b - bg[2]) * a),
    )
