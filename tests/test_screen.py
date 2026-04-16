import screen

def test_capture_returns_bytes():
    result = screen.capture()
    assert isinstance(result, bytes)
    assert len(result) > 0

def test_capture_is_jpeg():
    result = screen.capture()
    # JPEG files start with FF D8 FF
    assert result[:3] == b'\xff\xd8\xff'

def test_capture_size_within_limit():
    import config
    from PIL import Image
    import io
    result = screen.capture()
    img = Image.open(io.BytesIO(result))
    assert img.width <= config.SCREENSHOT_MAX_WIDTH