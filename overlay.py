"""
EchoNav status overlay — always-on-top semi-transparent strip at the bottom of the screen.
Shows current agent state so sighted users (and demo judges) can follow along.

Thread-safe: call overlay.update() from any thread.
Run overlay.run() from the MAIN thread — it blocks (tkinter mainloop).
"""

import queue
import tkinter as tk
from tkinter import font as tkfont

_STATE_COLORS = {
    "idle":       "#666666",
    "listening":  "#00e676",   # green
    "thinking":   "#ffca28",   # amber
    "acting":     "#ffffff",   # white
    "confirming": "#ff9800",   # orange
    "done":       "#00e676",   # green
    "error":      "#f44336",   # red
}

_STATE_ICONS = {
    "idle":       "○",
    "listening":  "●",
    "thinking":   "◌",
    "acting":     "▶",
    "confirming": "⚠",
    "done":       "✓",
    "error":      "✗",
}

_DEFAULT_TEXT = {
    "idle":       "Hold spacebar to speak",
    "listening":  "Listening...",
    "thinking":   "Thinking...",
    "confirming": "Say yes to confirm, or no to cancel",
    "done":       "Done",
    "error":      "Something went wrong",
}


class Overlay:
    def __init__(self) -> None:
        self._queue: queue.Queue = queue.Queue()
        self._root = None

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

        # --- Window chrome ---
        root.overrideredirect(True)          # no title bar / borders
        root.attributes("-topmost", True)    # always on top
        root.attributes("-alpha", 0.90)      # slightly transparent
        root.configure(bg="#111111")

        # --- Position: bottom-centre ---
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        w, h = 720, 64
        x = (sw - w) // 2
        y = sh - h - 48
        root.geometry(f"{w}x{h}+{x}+{y}")

        # --- Fonts ---
        icon_fnt = tkfont.Font(family="Segoe UI Emoji", size=16, weight="bold")
        main_fnt = tkfont.Font(family="Segoe UI", size=13)

        # --- Layout ---
        frame = tk.Frame(root, bg="#111111", padx=18, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        self._icon_lbl = tk.Label(
            frame, text=_STATE_ICONS["idle"],
            font=icon_fnt, fg=_STATE_COLORS["idle"], bg="#111111", width=2,
        )
        self._icon_lbl.pack(side=tk.LEFT)

        self._text_lbl = tk.Label(
            frame, text=_DEFAULT_TEXT["idle"],
            font=main_fnt, fg=_STATE_COLORS["idle"], bg="#111111",
            anchor="w",
        )
        self._text_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._poll()
        root.mainloop()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _poll(self) -> None:
        """Drain the queue and refresh labels. Reschedules itself every 100 ms."""
        try:
            while True:
                state, text = self._queue.get_nowait()
                color = _STATE_COLORS.get(state, "#ffffff")
                icon  = _STATE_ICONS.get(state, "○")
                label = text if text else _DEFAULT_TEXT.get(state, "")
                self._icon_lbl.config(text=icon, fg=color)
                self._text_lbl.config(text=label, fg=color)
        except queue.Empty:
            pass
        if self._root:
            self._root.after(100, self._poll)
