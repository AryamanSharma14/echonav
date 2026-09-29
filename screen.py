"""Screen capture module for EchoNav.

Captures display state, applies downscaling to adhere to VLM limits,
and masks out the local EchoNav status HUD so the vision model does not
interact with or hallucinate over the agent's own interface.
"""

from __future__ import annotations

import io
import logging
import mss
from PIL import Image

import config

logger = logging.getLogger("echonav.screen")


def capture() -> bytes:
    """Capture the primary monitor and return JPEG bytes.

    Falls back to a synthetic desktop placeholder if the GDI context
    is inaccessible (e.g. headless CI, remote sessions, locked desktop).
    """
    try:
        mss_cls = getattr(mss, "MSS", mss.mss)
        with mss_cls() as sct:
            # Primary monitor index is 1; index 0 combines all monitors
            monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            raw = sct.grab(monitor)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    except Exception as exc:
        logger.warning(f"Native BitBlt capture unavailable ({exc}); using synthetic display buffer.")
        # Create a clean fallback desktop frame (1920x1080 dark gray canvas)
        img = Image.new("RGB", (1920, 1080), color=(30, 32, 40))

    if img.width > config.SCREENSHOT_MAX_WIDTH:
        ratio = config.SCREENSHOT_MAX_WIDTH / img.width
        new_height = int(img.height * ratio)
        img = img.resize((config.SCREENSHOT_MAX_WIDTH, new_height), Image.LANCZOS)

    # Mask out the EchoNav overlay at its actual bottom-anchored location
    _mask_overlay(img)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=config.SCREENSHOT_QUALITY)
    return buffer.getvalue()


def _mask_overlay(img: Image.Image) -> None:
    """Blank out the region where the EchoNav overlay capsule is positioned.

    The capsule is horizontally centered and anchored to the bottom of the screen.
    """
    w, h = img.size
    overlay_w = getattr(config, "OVERLAY_WIDTH", 580)
    overlay_h = getattr(config, "OVERLAY_HEIGHT", 82)
    margin_bottom = getattr(config, "OVERLAY_BOTTOM_MARGIN", 60)

    # If downscaled, scale the mask proportionally
    scale = w / 1920.0 if w != 1920 else 1.0
    scaled_w = int(overlay_w * scale)
    scaled_h = int(overlay_h * scale)
    scaled_margin = int(margin_bottom * scale)

    left = (w - scaled_w) // 2
    top = max(0, h - scaled_h - scaled_margin)
    right = min(w, left + scaled_w)
    bottom = min(h, top + scaled_h)

    # Fill overlay region with neutral dark gray so the model sees uniform background
    pixels = img.load()
    for x in range(left, right):
        for y in range(top, bottom):
            pixels[x, y] = (24, 25, 31)