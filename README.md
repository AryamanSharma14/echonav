# EchoNav

**Voice-controlled desktop AI agent for blind and low-vision users.**

Hold spacebar → speak your task → EchoNav sees your screen, figures out what to click, and does it — narrating every step aloud.

---

## What it does

Most screen readers describe what's on screen. EchoNav acts on it.

| You say | EchoNav does |
|---|---|
| "Open Gmail and compose an email to John" | Navigates to Gmail, clicks Compose, fills in the recipient |
| "Search YouTube for relaxing piano music" | Opens YouTube, types in the search box, hits Enter |
| "Read the page" | Describes all visible text, top to bottom |
| "Where am I?" | One sentence: what app, what screen, what's focused |
| "Go back" | Browser back |
| "Stop" | Halts immediately |

---

## How it works

```
Hold spacebar
      │
      ▼
 Whisper STT  ──►  text
      │
      ▼
 Special command?  ──yes──►  execute instantly (read page, go back, stop…)
      │ no
      ▼
 Screenshot  ──►  Groq vision LLM  ──►  action JSON
      │
      ▼
 Narrate action aloud (edge-tts)
      │
 Major action?  ──yes──►  "Say yes to confirm"
      │ no / confirmed
      ▼
 pyautogui executes (click / type / key / scroll)
      │
      ▼
 Loop until done
```

**Stack:** faster-whisper (STT) · Groq LLaMA-4 Scout (vision) · edge-tts / pyttsx3 (TTS) · pyautogui (automation) · pynput (keyboard) · sounddevice (audio)

---

## Requirements

- Windows 10/11
- Python 3.10+
- A [Groq API key](https://console.groq.com) (free tier is enough)
- A microphone

---

## Install

```bash
git clone https://github.com/AryamanSharma14/echonav.git
cd echonav

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_key_here
```

---

## Run

```bash
venv\Scripts\activate
python main.py
```

You'll hear: **"EchoNav ready. Hold spacebar and speak your task."**

Hold spacebar, say what you want, release. That's it.

---

## Voice commands

These are handled instantly without going to the AI:

| Say | Effect |
|---|---|
| `"read the page"` / `"read page"` | Reads all visible content aloud |
| `"where am I"` | Describes your current screen in one sentence |
| `"what can I do here"` | Lists all buttons, links, and inputs visible |
| `"go back"` | Alt + Left (browser back) |
| `"stop"` / `"cancel"` | Halts the current task immediately |
| `"say that again"` / `"read that again"` | Repeats last spoken text |
| `"speak slower"` | Decreases speech rate |
| `"speak faster"` | Increases speech rate |

---

## Safety

Before any action that could send, delete, submit, or purchase something, EchoNav pauses and says:

> *"Clicking send button. Say yes to confirm, or no to cancel."*

You have 15 seconds to respond. Silence = cancel.

---

## Project structure

```
echonav/
├── main.py        — entry point, event loop
├── agent.py       — goal execution loop (screenshot → AI → act → repeat)
├── commands.py    — special voice commands intercepted before AI
├── executor.py    — translates action JSON → pyautogui calls
├── listener.py    — spacebar hold-to-record
├── tts.py         — text-to-speech (edge-tts + pyttsx3 fallback)
├── screen.py      — screenshot capture
├── stt.py         — speech-to-text (faster-whisper)
├── vision.py      — Groq vision → action JSON
├── config.py      — all tunable settings
└── tests/         — 38 tests, all passing
```

---

## Configuration

All settings in `config.py`:

| Setting | Default | What it does |
|---|---|---|
| `STT_MODEL` | `base.en` | Whisper model size (`base.en` / `small.en`) |
| `STT_CONFIDENCE_THRESHOLD` | `0.6` | Below this, asks you to repeat |
| `TTS_RATE` | `150` | Speech rate in words per minute |
| `TTS_VOICE` | `en-US-AriaNeural` | Edge TTS voice |
| `MAX_STEPS` | `30` | Max actions per goal before giving up |
| `MAX_RETRIES` | `3` | Retries per AI call on failure |
| `ACTION_DELAY` | `0.3s` | Pause between pyautogui actions |
| `SCREENSHOT_QUALITY` | `70` | JPEG compression for screenshots sent to AI |

---

## Run tests

```bash
venv\Scripts\activate
pytest tests/ -v
```

38 tests, all passing.

---

## Built at

DayZero Hackathon · April 2026
