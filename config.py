import os

# ---------------------------------------------------------------------------
# Model provider — switch between "gemini" (free) and "claude" (paid, better)
# ---------------------------------------------------------------------------
MODEL_PROVIDER = "gemini"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ---------------------------------------------------------------------------
# Speech-to-text
# ---------------------------------------------------------------------------
STT_MODEL = "base.en"           # faster-whisper model: base.en or small.en
STT_CONFIDENCE_THRESHOLD = 0.6  # below this threshold, ask user to repeat

# ---------------------------------------------------------------------------
# Text-to-speech
# ---------------------------------------------------------------------------
TTS_RATE = 150                   # words per minute baseline
TTS_VOICE = "en-US-AriaNeural"  # Edge TTS voice name

# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------
MAX_STEPS = 30                   # hard cap on actions per goal
MAX_RETRIES = 3                  # retries per AI call on failure
ACTION_DELAY = 0.3               # seconds pause after each pyautogui action

# ---------------------------------------------------------------------------
# Screenshot
# ---------------------------------------------------------------------------
SCREENSHOT_QUALITY = 70          # JPEG compression quality (0–100)
SCREENSHOT_MAX_WIDTH = 1280      # downscale if screen is wider than this

# ---------------------------------------------------------------------------
# Confirmation triggers
# If any of these words appear in an action's narration, agent asks user to
# confirm before executing.
# ---------------------------------------------------------------------------
MAJOR_ACTION_KEYWORDS = [
    "send",
    "submit",
    "delete",
    "purchase",
    "confirm",
    "close",
    "book",
]
