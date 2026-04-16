# Progress Log — append-only

Every push = one new entry at the top. Most recent first.
Format:
```
## <YYYY-MM-DD HH:MM> — <role> — <branch>
- Done: <what shipped>
- Next: <what's picked up>
- Notes: <gotchas, interface decisions, blockers>
```
`<role>` = `lead` or `ai`. No personal names.

---

<!-- New entries go here -->

## 2026-04-16 12:00 — lead — master (end-to-end testing + 8 bug fixes)
- Done: Full live testing of the pipeline. Found and fixed 8 bugs. 56/56 tests green. System now runs end-to-end — Brave opens, navigates to URLs, stop command cancels mid-task.
- Next: T14 reliability tuning. The loop works but needs demo-quality polish. See bug list in TODO.md. Priority: make address bar navigation bulletproof (use Ctrl+L instead of clicking). Then record demo video.
- Notes (READ ALL OF THESE — critical for next session):

  **Bug 1 — GROQ_API_KEY not loaded (FIXED)**
  `config.py` now calls `load_dotenv()` at import time via `python-dotenv`. Added to `requirements.txt`. Without this, every vision call failed silently.

  **Bug 2 — echonav venv missing all packages (FIXED)**
  The local `venv/` didn't have groq, PIL, etc. Fixed by adding a `.pth` file at `venv/Lib/site-packages/navigator.pth` pointing to the navigator venv's site-packages. Both venvs now share packages.

  **Bug 3 — Vision model typed goal text verbatim (FIXED)**
  Model was typing "open Brave" into Windows search instead of just "brave". Fixed by rewriting the system prompt in `vision.py` with explicit Windows-specific rules: type only the app name, navigate via URL bar directly, never search-then-click.

  **Bug 4 — Two agent threads ran in parallel (FIXED)**
  `main.py` now has `_goal_lock = threading.Lock()`. If a goal is already running, new utterances get "Still working on the previous task. Please wait." Lock is released in a `finally` block so it's always cleaned up.

  **Bug 5 — TTS calls overlapped between threads (FIXED)**
  `tts.speak()` now acquires `_speak_lock` before speaking. Calls from different threads queue up instead of playing simultaneously.

  **Bug 6 — "stop" command didn't cancel running agent (FIXED)**
  `agent.py` has a module-level `_cancel_event = threading.Event()` and a `cancel()` function. `commands._stop()` now calls `agent.cancel()` before raising `StopCommand`. The agent checks `_cancel_event` at the start of every step.

  **Bug 7 — Click loop not detected when coords were slightly different (FIXED)**
  Loop detection in `agent.py` is now fuzzy for clicks: if 3 consecutive clicks are all within 20px of each other, agent says "I seem to be stuck" and stops. Previously only exact-match was checked.

  **Bug 8 — DPI scaling: click coordinates 1.5x off (FIXED)**
  Screenshot is captured at 1280x720 (physical resized), but pyautogui uses 1920x1080 (logical). `agent._compute_scale()` computes `scale_x = pyautogui_width / screenshot_width` at goal start (= 1.5 on this machine). `executor.execute()` now takes `scale_x, scale_y` and multiplies click coords before calling pyautogui.

  **Remaining issue — address bar click is fragile**
  Model visually estimates the address bar position (e.g. x=440, y=70 in screenshot space). This works sometimes but misses when Brave isn't maximised. Recommended fix: use `pyautogui.hotkey('ctrl', 'l')` to focus address bar instead of clicking. Add this to the system prompt and/or teach the model to use Ctrl+L.

  **Remaining issue — Start menu: Enter vs click**
  After Win key → typing "brave", model sometimes tries to click the search result visually instead of just pressing Enter. Should always press Enter after typing in Windows search.

## 2026-04-16 10:30 — lead — master (T2 + T4 merged, 50/50 tests)
- Done: Pulled Jai's task-2-screen (screen.py — mss + Pillow JPEG, 3 tests) and task-4-stt (stt.py — faster-whisper int8 CPU, 4 tests). Created PRs #8 and #9, squash-merged both to master. Full suite now 50/50. overlay.py + demo.py already on master from previous session.
- Next: Waiting on Jai — T6 (vision.py). Once that lands, T14 end-to-end demo is unblocked. Non-code track: pitch script, demo video, Devpost form.
- Notes: stt.py uses `_model` global + `load_model()` for caching — model loads once per session. screen.py resizes to `SCREENSHOT_MAX_WIDTH` before JPEG encode. demo.py runnable right now as full UX mock.

## 2026-04-16 — lead — master (all lead tasks complete, PRs merged)
- Done: T1 (config/setup), T3 (tts.py), T5 (listener.py), T7 (executor.py), T8 (commands.py), T9 (agent.py), T10 (main.py). Full test suite 38/38 passing. Stubs for screen.py, stt.py, vision.py in place. All feature branches squash-merged to master via PRs #1–#6.
- Next: Waiting on Jai — T2 (screen.py), T4 (stt.py), T6 (vision.py). Once those land, T14 end-to-end demo.
- Notes: commands.py uses string-name dispatch dict so pytest mocking works. agent.py and main.py require stubs as top-level imports for same reason.

## 2026-04-15 22:00 — lead — master (pre-hackathon prep)
- Done: Full environment verified. All 4 smoke tests passing (Whisper STT, edge-tts, pyautogui, Groq vision). Groq wired as primary vision provider (free, llama-4-scout-17b). Switched away from deprecated google-generativeai SDK. Coordination docs written (CLAUDE.md, docs/HACKATHON.md, docs/TODO.md, docs/PROGRESS.md, scripts/log-push.sh).
- Next: T1 project setup at 09:00 kickoff. Then T5 listener, T7 executor, T9 agent loop.
- Notes: Gemini free tier is broken (limit: 0) on current GCP project — Groq is the primary provider now. MODEL_PROVIDER="groq" in config.py. GROQ_API_KEY must be in .env (personal, not committed). Groq model: meta-llama/llama-4-scout-17b-16e-instruct. venv uses Python 3.10.11 (3.11+ target for prod but fine for hackathon). google-genai kept in requirements as Gemini fallback.
