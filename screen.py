# Stub — implementation owned by task-2-screen (Jai)
# This file exists so agent.py can import it; tests mock it.

import mss
from PIL import Image
import io
import config


def capture() -> bytes:
    """Capture the primary monitor and return JPEG bytes."""
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # Primary monitor (0 = all monitors combined)
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

    if img.width > config.SCREENSHOT_MAX_WIDTH:
        ratio = config.SCREENSHOT_MAX_WIDTH / img.width
        new_height = int(img.height * ratio)
        img = img.resize((config.SCREENSHOT_MAX_WIDTH, new_height), Image.LANCZOS)

    # Mask out the EchoNav overlay (centered 580x82px capsule)
    # so the vision model doesn't see or interact with it
    _mask_overlay(img)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=config.SCREENSHOT_QUALITY)
    return buffer.getvalue()


def _mask_overlay(img: Image.Image) -> None:
    """Blank out the center region where the EchoNav overlay is located."""
    w, h = img.size
    center_x, center_y = w // 2, h // 2
    
    # Overlay is 580x82px centered on screen
    overlay_w, overlay_h = 580, 82
    left = center_x - overlay_w // 2
    top = center_y - overlay_h // 2
    right = left + overlay_w
    bottom = top + overlay_h
    
    # Clamp to image bounds
    left = max(0, left)
    top = max(0, top)
    right = min(w, right)
    bottom = min(h, bottom)
    
    # Fill the region with solid gray (neutral)
    pixels = img.load()
    for x in range(left, right):
        for y in range(top, bottom):
            pixels[x, y] = (128, 128, 128)