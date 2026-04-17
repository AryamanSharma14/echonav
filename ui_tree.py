"""UI element tree snapshot — enumerate interactive controls via Windows UI Automation.

Used by the agent to give the vision model a concrete, numbered list of clickable
things on screen with their exact screen-space coordinates. This replaces
pixel-guessing with deterministic element lookup.

Falls back silently (returns []) if uiautomation isn't installed or the call
errors — the agent then uses pixel clicks as before.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import config


_INTERACTIVE_TYPES = {
    "ButtonControl",
    "EditControl",
    "HyperlinkControl",
    "ListItemControl",
    "MenuItemControl",
    "CheckBoxControl",
    "RadioButtonControl",
    "ComboBoxControl",
    "TabItemControl",
    "TreeItemControl",
    "SplitButtonControl",
    "CustomControl",   # Chromium renders clickable elements as Custom — keep it
}

# When the foreground surface is one of these, UIA enumeration is a trap —
# the tree is huge and cluttered and the model reliably picks the wrong thing.
# Return no elements so the prompt forces the model to use keyboard (Win/Enter/
# ctrl+l) which is the fast, correct path through Start/Search/notifications.
_TRANSIENT_CLASSES = {
    "Windows.UI.Core.CoreWindow",   # Windows 11 Start, Search, Notification Center
    "SearchApp",
    "StartMenuExperienceHost",
    "Shell_TrayWnd",
    "Shell_SecondaryTrayWnd",
}


@dataclass
class Element:
    id: int
    name: str
    control_type: str
    left: int
    top: int
    right: int
    bottom: int

    @property
    def center(self) -> tuple[int, int]:
        return ((self.left + self.right) // 2, (self.top + self.bottom) // 2)

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    def as_prompt_line(self) -> str:
        label = (self.name or "").strip()
        if len(label) > 60:
            label = label[:57] + "..."
        ct = self.control_type.replace("Control", "")
        if label:
            return f"[{self.id}] {ct}: {label}"
        return f"[{self.id}] {ct}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "control_type": self.control_type,
            "bbox": (self.left, self.top, self.right, self.bottom),
            "center": self.center,
        }


def snapshot(max_elements: int | None = None) -> list[Element]:
    """Walk the foreground window's UIA tree and return interactive elements.

    Elements are in screen (monitor) coordinate space — center maps directly
    to pyautogui.click(x, y) without any scaling.
    """
    if not getattr(config, "USE_UIA", True):
        return []

    cap = max_elements or getattr(config, "MAX_UI_ELEMENTS", 60)

    try:
        import uiautomation as auto
    except Exception as e:
        print(f"[ui_tree] uiautomation import failed: {e}")
        return []

    # Chromium-based browsers (Chrome/Brave/Edge) don't expose the page a11y
    # tree to UIA until someone asks for it. Sending WM_GETOBJECT with
    # OBJID_CLIENT wakes the renderer's accessibility engine so the search
    # bar, links, and buttons inside the web page become visible below.
    _wake_chromium_a11y()

    try:
        root = auto.GetForegroundControl()
        if not root:
            return []
    except Exception as e:
        print(f"[ui_tree] GetForegroundControl failed: {e}")
        return []

    if _is_transient_surface(root):
        try:
            cls = root.ClassName
        except Exception:
            cls = "?"
        print(f"[ui_tree] transient surface ({cls}) — skipping UIA; model will use keyboard")
        return []

    collected: list[Element] = []
    _walk(root, collected, depth=0, max_depth=10, cap=cap)

    # De-dup by (center, name) — UIA often reports the same logical control
    # twice when panes wrap buttons.
    seen: set[tuple[int, int, str]] = set()
    unique: list[Element] = []
    for el in collected:
        key = (*el.center, el.name)
        if key in seen:
            continue
        seen.add(key)
        unique.append(el)

    # Re-id sequentially so prompt numbers are contiguous.
    for i, el in enumerate(unique, start=1):
        el.id = i

    return unique[:cap]


def _wake_chromium_a11y() -> None:
    """Poke the foreground HWND tree with WM_GETOBJECT so Chromium builds its
    a11y tree.

    Chrome/Brave/Edge lazily enable accessibility — without this, UIA only sees
    the window chrome (address bar, tab strip) and NOT the page content (search
    boxes, links, buttons). WM_GETOBJECT + OBJID_CLIENT is the same signal
    screen readers send; the renderer responds by turning on a11y for the rest
    of its lifetime.

    The top-level window is usually a wrapper. The real renderer HWND is a
    descendant with class "Chrome_RenderWidgetHostHWND" — we poke every
    descendant so whichever one owns the DOM wakes up.
    """
    try:
        import ctypes
        from ctypes import wintypes

        WM_GETOBJECT = 0x003D
        OBJID_CLIENT = 0xFFFFFFFC  # -4 as unsigned DWORD
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return

        user32.SendMessageW(hwnd, WM_GETOBJECT, 0, OBJID_CLIENT)

        EnumChildProc = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
        )

        def _poke(child_hwnd, _lparam):
            try:
                user32.SendMessageW(child_hwnd, WM_GETOBJECT, 0, OBJID_CLIENT)
            except Exception:
                pass
            return True  # keep enumerating

        user32.EnumChildWindows(hwnd, EnumChildProc(_poke), 0)
    except Exception:
        pass


def _is_transient_surface(control) -> bool:
    try:
        cls = getattr(control, "ClassName", "") or ""
    except Exception:
        cls = ""
    if not isinstance(cls, str):
        cls = ""
    if cls in _TRANSIENT_CLASSES:
        return True
    try:
        name = (getattr(control, "Name", "") or "").lower()
    except Exception:
        name = ""
    if not isinstance(name, str):
        name = ""
    # "Search" window titles on Win11 (search popup) vary by locale — match loosely.
    if cls.startswith("Windows.UI.Core") or (name == "search" and cls == "ApplicationFrameWindow"):
        return True
    return False


def _walk(control, out: list[Element], depth: int, max_depth: int, cap: int) -> None:
    if len(out) >= cap or depth > max_depth:
        return

    try:
        if _should_include(control):
            rect = control.BoundingRectangle
            name = ""
            try:
                name = (control.Name or "").strip()
            except Exception:
                pass
            out.append(
                Element(
                    id=len(out) + 1,
                    name=name,
                    control_type=control.ControlTypeName,
                    left=int(rect.left),
                    top=int(rect.top),
                    right=int(rect.right),
                    bottom=int(rect.bottom),
                )
            )
    except Exception:
        pass   # skip broken control, keep walking

    try:
        children = control.GetChildren()
    except Exception:
        return

    for child in children:
        _walk(child, out, depth + 1, max_depth, cap)
        if len(out) >= cap:
            return


def _should_include(control) -> bool:
    ct = getattr(control, "ControlTypeName", "")
    if ct not in _INTERACTIVE_TYPES:
        return False

    try:
        if control.IsOffscreen:
            return False
    except Exception:
        pass

    try:
        rect = control.BoundingRectangle
    except Exception:
        return False

    w = int(rect.right) - int(rect.left)
    h = int(rect.bottom) - int(rect.top)
    # Drop zero-size and ridiculous controls (>screen) that mean nothing.
    if w < 6 or h < 6 or w > 4000 or h > 4000:
        return False

    # CustomControl with no name is almost always a decorative element in Chromium —
    # skip unless it has an automation id or help text that might help the model.
    if ct == "CustomControl":
        try:
            if not (control.Name or getattr(control, "AutomationId", "")):
                return False
        except Exception:
            return False

    return True


def benchmark() -> None:
    """Quick perf check — run as `python -c 'import ui_tree; ui_tree.benchmark()'`."""
    t0 = time.time()
    els = snapshot()
    dt = (time.time() - t0) * 1000
    print(f"[ui_tree] {len(els)} elements in {dt:.0f} ms")
    for el in els[:20]:
        print("  " + el.as_prompt_line())
