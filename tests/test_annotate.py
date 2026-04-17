import io

from PIL import Image

import annotate
from ui_tree import Element


def _blank_jpeg(w=1280, h=720) -> bytes:
    img = Image.new("RGB", (w, h), (240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def test_annotate_no_elements_returns_original():
    data = _blank_jpeg()
    out = annotate.annotate(data, [], 1.0, 1.0, 0, 0)
    assert out is data   # fast path — same object


def test_annotate_draws_boxes_and_changes_bytes():
    data = _blank_jpeg()
    els = [
        Element(id=1, name="Send", control_type="ButtonControl",
                left=100, top=100, right=200, bottom=140),
        Element(id=2, name="Search", control_type="EditControl",
                left=300, top=50, right=900, bottom=90),
    ]
    out = annotate.annotate(data, els, 1.0, 1.0, 0, 0)
    assert out != data
    assert len(out) > 100


def test_annotate_scales_screen_coords_to_screenshot_space():
    """When screenshot is half the screen size, element coords must be halved
    before drawing or the boxes would land off-frame."""
    data = _blank_jpeg(1280, 720)
    el = Element(id=1, name="x", control_type="ButtonControl",
                 left=2000, top=1000, right=2100, bottom=1060)
    # scale 2.0 → screenshot position (1000, 500) → in-bounds
    out = annotate.annotate(data, [el], 2.0, 2.0, 0, 0)
    img = Image.open(io.BytesIO(out))
    assert img.size == (1280, 720)   # unchanged size, just decorated


def test_annotate_handles_offset_origin():
    """Offset subtracts before scaling. Element at (1100, 500) with
    offset (100, 100) and scale 1.0 should land at (1000, 400) in screenshot."""
    data = _blank_jpeg(1280, 720)
    el = Element(id=1, name="x", control_type="ButtonControl",
                 left=1100, top=500, right=1150, bottom=540)
    out = annotate.annotate(data, [el], 1.0, 1.0, 100, 100)
    img = Image.open(io.BytesIO(out))
    assert img.size == (1280, 720)
