"""Set-of-Mark annotation — draws numbered boxes over interactive elements on
a screenshot so the vision model can pick one by number instead of guessing
pixel coordinates.
"""

from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

import config


_BOX_COLOR = (255, 64, 64)
_LABEL_BG = (255, 64, 64)
_LABEL_FG = (255, 255, 255)


def annotate(
    jpeg_bytes: bytes,
    elements: list,
    scale_x: float,
    scale_y: float,
    offset_x: int,
    offset_y: int,
) -> bytes:
    """Draw numbered boxes on the screenshot.

    `elements` hold screen-space coords (UIA monitor pixels). The screenshot is
    downscaled to SCREENSHOT_MAX_WIDTH and may be offset from the virtual
    desktop origin, so we map: screenshot_x = (screen_x - offset_x) / scale_x.
    """
    if not elements:
        return jpeg_bytes

    img = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)
    font = _load_font()

    for el in elements:
        left = int((el.left - offset_x) / scale_x)
        top = int((el.top - offset_y) / scale_y)
        right = int((el.right - offset_x) / scale_x)
        bottom = int((el.bottom - offset_y) / scale_y)

        # Clamp to image bounds
        left = max(0, min(img.width - 1, left))
        right = max(0, min(img.width - 1, right))
        top = max(0, min(img.height - 1, top))
        bottom = max(0, min(img.height - 1, bottom))

        if right - left < 4 or bottom - top < 4:
            continue

        draw.rectangle([left, top, right, bottom], outline=_BOX_COLOR, width=2)

        label = str(el.id)
        tw, th = _text_size(draw, label, font)
        pad = 2
        lx0 = left
        ly0 = max(0, top - th - pad * 2)
        lx1 = lx0 + tw + pad * 2
        ly1 = ly0 + th + pad * 2
        # If there's no room above the box, place the label inside the top-left corner.
        if ly0 == 0 and top < th + pad * 2:
            ly0 = top
            ly1 = top + th + pad * 2
            lx1 = min(lx0 + tw + pad * 2, img.width - 1)

        draw.rectangle([lx0, ly0, lx1, ly1], fill=_LABEL_BG)
        draw.text((lx0 + pad, ly0 + pad), label, fill=_LABEL_FG, font=font)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=config.SCREENSHOT_QUALITY)
    return buf.getvalue()


def _load_font():
    try:
        return ImageFont.truetype("arial.ttf", 14)
    except Exception:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", 14)
        except Exception:
            return ImageFont.load_default()


def _text_size(draw, text: str, font) -> tuple[int, int]:
    # Pillow ≥ 10 removed .textsize — use textbbox when available.
    if hasattr(draw, "textbbox"):
        l, t, r, b = draw.textbbox((0, 0), text, font=font)
        return r - l, b - t
    return draw.textsize(text, font=font)
