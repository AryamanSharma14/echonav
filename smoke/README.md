# Smoke Tests

Run in order. Each should PASS before hackathon day.

```bash
venv\Scripts\activate

python smoke/01_whisper.py     # records 3 sec of mic, transcribes
python smoke/02_tts.py         # synthesizes speech, plays mp3
python smoke/03_pyautogui.py   # moves your mouse in a square
python smoke/04_gemini.py      # screenshots + asks Gemini what's on screen (needs GEMINI_API_KEY in .env)
```

If any fails, fix TONIGHT. If all pass, you're ready for 09:00 tomorrow.
