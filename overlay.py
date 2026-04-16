"""
EchoNav status overlay — centered floating glassmorphism HUD capsule.
Shows current agent state so sighted users (and demo judges) can follow along.

Thread-safe: call overlay.update() from any thread.
Run overlay.run() from the MAIN thread — it blocks (tkinter mainloop).
"""

import ctypes
import ctypes.wintypes
import queue
import tkinter as tk
from tkinter import font as tkfont

# State → accent color (orb + border glow)
_STATE_COLORS = {
    "idle":       "#7b8fa1",   # muted blue-gray
    "listening":  "#00d4f5",   # soft cyan
    "thinking":   "#7c6af7",   # violet-blue
    "acting":     "#00d97e",   # soft green
    "confirming": "#f5a623",   # warm amber
    "done":       "#00d97e",   # soft green
    "error":      "#e05c5c",   # muted red
}

_DEFAULT_TEXT = {
    "idle":       "Ready for your next task",
    "listening":  "Listening…  tell me your next objective",
    "thinking":   "Processing screen…",
    "acting":     "Executing action",
    "confirming": "Say yes to confirm, or no to cancel",
    "done":       "Task complete",
    "error":      "Something went wrong",
}

_BG       = "#18191f"   # dark glass base
_BG_FRAME = "#1e1f28"   # slightly lighter inner
_ALPHA    = 0.93


class Overlay:
    def __init__(self) -> None:
        self._queue: queue.Queue = queue.Queue()
        self._root = None
        self._canvas = None          # for orb + border glow
        self._text_lbl = None
        self._right_lbl = None
        self._current_state = "idle"
        self._pulse_up = True        # orb breathing direction
        self._pulse_alpha = 128      # 0-255 brightness of orb (hex)
        self._spin_angle = 0         # spinner frame index

    def update(self, state: str, text: str = "") -> None:
        """Thread-safe. Put a state update on the queue."""
        self._queue.put((state, text))

    def run(self) -> None:
        """
        Blocking — must be called from the main thread.
        Starts the tkinter mainloop; polls the queue every 100 ms for updates.
        """
        root = tk.Tk()
        self._root = root

        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", _ALPHA)
        root.configure(bg=_BG)

        # ── Prevent the overlay from stealing keyboard focus ───────────
        # WS_EX_NOACTIVATE: window never becomes the active window when
        # clicked or shown — keystrokes always go to whatever app had focus.
        root.update_idletasks()   # ensure HWND is allocated
        hwnd = root.winfo_id()
        GWL_EXSTYLE    = -20
        WS_EX_NOACTIVATE = 0x08000000
        current = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, current | WS_EX_NOACTIVATE)

        # ── Position: dead center ──────────────────────────────────────
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        W, H = 580, 82
        x = (sw - W) // 2
        y = (sh - H) // 2
        root.geometry(f"{W}x{H}+{x}+{y}")

        # ── Rounded capsule via Canvas background ──────────────────────
        #   tkinter has no native border-radius, so we draw the shell on a
        #   Canvas and overlay transparent-bg labels on top.
        canvas = tk.Canvas(root, width=W, height=H, bg=_BG,
                           highlightthickness=0, bd=0)
        canvas.place(x=0, y=0)
        self._canvas = canvas
        self._W, self._H = W, H

        # Draw the rounded-rect body (filled dark glass)
        r = 36   # corner radius
        self._body_id = self._rounded_rect(canvas, 2, 2, W - 2, H - 2,
                                           r, fill=_BG_FRAME, outline="")
        # Glow border (redrawn on state change)
        self._border_id = self._rounded_rect(canvas, 1, 1, W - 1, H - 1,
                                             r, fill="", outline="#7b8fa1", width=2)

        # ── Fonts ──────────────────────────────────────────────────────
        orb_fnt  = tkfont.Font(family="Segoe UI Emoji", size=14, weight="bold")
        main_fnt = tkfont.Font(family="Segoe UI", size=14, weight="bold")
        sub_fnt  = tkfont.Font(family="Segoe UI", size=12)

        # ── LEFT: status orb (drawn on canvas as filled oval) ─────────
        orb_cx, orb_cy = 36, H // 2
        orb_r = 10
        self._orb_id = canvas.create_oval(
            orb_cx - orb_r, orb_cy - orb_r,
            orb_cx + orb_r, orb_cy + orb_r,
            fill=_STATE_COLORS["idle"], outline="", tags="orb"
        )
        self._orb_cx = orb_cx
        self._orb_cy = orb_cy

        # ── CENTER: main text label ────────────────────────────────────
        text_lbl = tk.Label(
            root,
            text=_DEFAULT_TEXT["idle"],
            font=main_fnt,
            fg=_STATE_COLORS["idle"],
            bg=_BG_FRAME,
            anchor="center",
            wraplength=380,
        )
        # Place it in the middle of the capsule (leave 60px left for orb, 60px right for indicator)
        text_lbl.place(x=62, y=0, width=W - 122, height=H)
        self._text_lbl = text_lbl

        # ── RIGHT: progress indicator label ───────────────────────────
        right_lbl = tk.Label(
            root,
            text="",
            font=orb_fnt,
            fg=_STATE_COLORS["idle"],
            bg=_BG_FRAME,
            anchor="center",
        )
        right_lbl.place(x=W - 58, y=0, width=52, height=H)
        self._right_lbl = right_lbl

        self._poll()
        self._animate()
        root.mainloop()

    # ──────────────────────────────────────────────────────────────────
    # Thread-safe poll
    # ──────────────────────────────────────────────────────────────────

    def _poll(self) -> None:
        """Drain the queue and refresh widget state. Runs every 100 ms."""
        try:
            while True:
                state, text = self._queue.get_nowait()
                self._apply_state(state, text)
        except queue.Empty:
            pass
        if self._root:
            self._root.after(100, self._poll)

    # ──────────────────────────────────────────────────────────────────
    # State application
    # ──────────────────────────────────────────────────────────────────

    def _apply_state(self, state: str, text: str) -> None:
        self._current_state = state
        color = _STATE_COLORS.get(state, "#ffffff")
        label = text if text else _DEFAULT_TEXT.get(state, "")

        # Update border glow color
        self._canvas.itemconfig(self._border_id, outline=color)

        # Update orb fill (base color — animator will adjust brightness)
        self._canvas.itemconfig(self._orb_id, fill=color)

        # Update center text
        self._text_lbl.config(text=label, fg=color)

        # Update right indicator symbol
        right = self._right_symbol(state)
        self._right_lbl.config(text=right, fg=color)

    @staticmethod
    def _right_symbol(state: str) -> str:
        return {
            "idle":       "○",
            "listening":  "◎",
            "thinking":   "◌",
            "acting":     "▶",
            "confirming": "⚠",
            "done":       "✓",
            "error":      "✗",
        }.get(state, "")

    # ──────────────────────────────────────────────────────────────────
    # Animation loop (orb pulse + spinner)
    # ──────────────────────────────────────────────────────────────────

    def _animate(self) -> None:
        if not self._root:
            return
        state = self._current_state

        # Orb: breathing pulse when listening, steady otherwise
        if state == "listening":
            self._pulse_alpha += 12 if self._pulse_up else -12
            if self._pulse_alpha >= 255:
                self._pulse_alpha = 255
                self._pulse_up = False
            elif self._pulse_alpha <= 80:
                self._pulse_alpha = 80
                self._pulse_up = True
            base = _STATE_COLORS.get(state, "#00d4f5")
            pulsed = self._blend(base, self._pulse_alpha)
            self._canvas.itemconfig(self._orb_id, fill=pulsed)
        else:
            self._pulse_alpha = 200
            self._pulse_up = True

        # Right indicator: spinning dots while thinking/acting
        if state in ("thinking", "acting"):
            frames = ["◜", "◝", "◞", "◟"]
            self._spin_angle = (self._spin_angle + 1) % len(frames)
            self._right_lbl.config(text=frames[self._spin_angle])
        else:
            # Reset to static symbol
            self._right_lbl.config(text=self._right_symbol(state))

        self._root.after(80, self._animate)

    # ──────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _rounded_rect(canvas, x1, y1, x2, y2, r, **kwargs):
        """Draw a rounded rectangle on canvas. Returns item id."""
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]
        return canvas.create_polygon(points, smooth=True, **kwargs)

    @staticmethod
    def _blend(hex_color: str, alpha: int) -> str:
        """Blend hex_color toward #18191f (bg) by alpha (0=bg, 255=full color)."""
        bg = (0x18, 0x19, 0x1f)
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        a = alpha / 255
        nr = int(bg[0] + (r - bg[0]) * a)
        ng = int(bg[1] + (g - bg[1]) * a)
        nb = int(bg[2] + (b - bg[2]) * a)
        return f"#{nr:02x}{ng:02x}{nb:02x}"
