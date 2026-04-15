"""Smoke test 4: Gemini vision — send a screenshot + prompt, get structured response."""
import os, io
from pathlib import Path
import google.generativeai as genai
from PIL import Image
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

genai.configure(api_key=key)
model = genai.GenerativeModel("gemini-2.0-flash")

print("Capturing screen...")
img = pyautogui.screenshot()
buf = io.BytesIO()
img.save(buf, format="PNG")

print("Asking Gemini: what's on screen?")
resp = model.generate_content([
    "In one sentence: what application or window is the user currently looking at? Be brief.",
    {"mime_type": "image/png", "data": buf.getvalue()},
])
print(f"Gemini: {resp.text.strip()}")
print("PASS")
