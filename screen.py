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

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=config.SCREENSHOT_QUALITY)
    return buffer.getvalue()