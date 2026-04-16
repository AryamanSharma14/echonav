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

## 2026-04-16 — lead — master (all lead tasks complete, PRs merged)
- Done: T1 (config/setup), T3 (tts.py), T5 (listener.py), T7 (executor.py), T8 (commands.py), T9 (agent.py), T10 (main.py). Full test suite 38/38 passing. Stubs for screen.py, stt.py, vision.py in place. All feature branches squash-merged to master via PRs #1–#6.
- Next: Waiting on Jai — T2 (screen.py), T4 (stt.py), T6 (vision.py). Once those land, T14 end-to-end demo.
- Notes: commands.py uses string-name dispatch dict so pytest mocking works. agent.py and main.py require stubs as top-level imports for same reason.

## 2026-04-15 22:00 — lead — master (pre-hackathon prep)
- Done: Full environment verified. All 4 smoke tests passing (Whisper STT, edge-tts, pyautogui, Groq vision). Groq wired as primary vision provider (free, llama-4-scout-17b). Switched away from deprecated google-generativeai SDK. Coordination docs written (CLAUDE.md, docs/HACKATHON.md, docs/TODO.md, docs/PROGRESS.md, scripts/log-push.sh).
- Next: T1 project setup at 09:00 kickoff. Then T5 listener, T7 executor, T9 agent loop.
- Notes: Gemini free tier is broken (limit: 0) on current GCP project — Groq is the primary provider now. MODEL_PROVIDER="groq" in config.py. GROQ_API_KEY must be in .env (personal, not committed). Groq model: meta-llama/llama-4-scout-17b-16e-instruct. venv uses Python 3.10.11 (3.11+ target for prod but fine for hackathon). google-genai kept in requirements as Gemini fallback.
