"""Smoke test 4: vision — send a screenshot + prompt, get a response.
Uses Groq (free) with llama-4-scout vision. Falls back to Gemini if GEMINI_API_KEY set.
"""
import os, io, base64
from pathlib import Path
import pyautogui

# Load .env
env = Path(__file__).resolve().parent.parent / ".env"
if env.exists():
    for line in env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

# --- Groq path (primary) ---
groq_key = os.environ.get("GROQ_API_KEY", "")
gemini_key = os.environ.get("GEMINI_API_KEY", "")

assert groq_key or gemini_key, "Set GROQ_API_KEY (or GEMINI_API_KEY) in .env"

print("Capturing screen...")
img = pyautogui.screenshot()
buf = io.BytesIO()
img.save(buf, format="PNG")
img_b64 = base64.b64encode(buf.getvalue()).decode()

if groq_key:
    from groq import Groq
    client = Groq(api_key=groq_key)
    print("Asking Groq llama-4-scout: what's on screen?")
    resp = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "In one sentence: what application or window is the user looking at? Be brief."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
            ],
        }],
        max_tokens=100,
    )
    print(f"Groq: {resp.choices[0].message.content.strip()}")
else:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=gemini_key)
    print("Asking Gemini: what's on screen?")
    resp = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            "In one sentence: what application or window is the user looking at? Be brief.",
            types.Part.from_bytes(data=buf.getvalue(), mime_type="image/png"),
        ],
    )
    print(f"Gemini: {resp.text.strip()}")

print("PASS")
