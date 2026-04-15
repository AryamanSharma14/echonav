"""Smoke test 4: Gemini vision — send a screenshot + prompt, get structured response."""
import os, io
from pathlib import Path
from google import genai
from google.genai import types
import pyautogui

# Load GEMINI_API_KEY from .env (simple parser, no python-dotenv dep)
env = Path(__file__).resolve().parent.parent / ".env"
if env.exists():
    for line in env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

key = os.environ.get("GEMINI_API_KEY")
assert key and key != "your_gemini_key_here", "Set GEMINI_API_KEY in .env"

client = genai.Client(api_key=key)

print("Capturing screen...")
img = pyautogui.screenshot()
buf = io.BytesIO()
img.save(buf, format="PNG")
img_bytes = buf.getvalue()

print("Asking Gemini: what's on screen?")
resp = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=[
        "In one sentence: what application or window is the user currently looking at? Be brief.",
        types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
    ],
)
print(f"Gemini: {resp.text.strip()}")
print("PASS")
