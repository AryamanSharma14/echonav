# TODO — live task list

Edit + push to update. Both Claude instances read this at session start.
Legend: ⬜ todo · 🟡 in progress · ✅ done · ❌ blocked

## Pre-hackathon prep ✅ (done 2026-04-15 night)
- [x] ✅ venv + all deps installed
- [x] ✅ Smoke tests: Whisper, TTS, pyautogui, vision — all PASS
- [x] ✅ Groq wired as primary vision provider (free, no billing needed)
- [x] ✅ Coordination docs: CLAUDE.md, HACKATHON.md, TODO.md, PROGRESS.md, log-push.sh
- [x] ✅ GROQ_API_KEY in .env (lead machine)

## CP1 — Foundation ✅
- [x] ✅ **T1** Project setup — `requirements.txt`, `config.py`, `tests/__init__.py` — _lead_
- [x] ✅ **T2** Screen capture (`screen.py`) — mss + Pillow JPEG — _ai_ — merged PR #8
- [x] ✅ **T3** TTS (`tts.py`) — _lead_
- [x] ✅ **T4** STT (`stt.py`) — faster-whisper, model caching — _ai_ — merged PR #9
- [x] ✅ **T5** Listener / spacebar (`listener.py`) — _lead_

## CP2 — Brain ✅
- [x] ✅ **T6** Vision (`vision.py`) — Groq primary, Gemini fallback — _ai_ — merged PR #10
- [x] ✅ **T7** Executor (`executor.py`) — _lead_
- [x] ✅ **T8** Special voice commands (`commands.py`) — _lead_

## CP3 — Loop alive ✅
- [x] ✅ **T9** Agent loop (`agent.py`) — _lead_
- [x] ✅ **T10** `main.py` wiring + overlay — _both_

## CP4 — Polish ✅
- [ ] ⬜ **T11** Windows auto-start (`setup.py`, `watchdog.py`) — cut — scope drop
- [x] ✅ **T12** Full test suite green — 56/56 passing

## CP5 — Demo
- [ ] ⬜ **T13** Claude Computer Use upgrade — cut — scope drop
- [ ] 🟡 **T14** End-to-end demo verification — loop works, reliability tuning in progress

## Non-code track (parallel, all day)
- [ ] ⬜ Pitch script (~90 sec spoken)
- [ ] ⬜ Demo video (2 min, screen + narration)
- [x] ✅ README.md with install steps, usage, architecture, config
- [ ] ⬜ Devpost / submission form filled
- [ ] ⬜ Accessibility bug-bash log
- [ ] ⬜ Project logo / title card

## Known issues / next to fix
- ✅ Normalised coords crash (x/y as 0.0–1.0 floats → (0,0) → FailSafe) — fixed in `agent._validate_action()`
- ✅ Stop command didn't release goal lock fast enough — fixed in `main.py` (3s wait when `_cancel_event` set)
- ✅ No post-action verification — fixed: `_screenshots_differ()` hash check after every action; `had_effect` injected into AI prompt
- ✅ python-dotenv missing on fresh venv — `pip install python-dotenv` (already in requirements.txt, install if missing)
- ⬜ Vision model sometimes clicks Windows search result instead of pressing Enter — system prompt updated, needs live verification
- ⬜ Address bar: Ctrl+L in system prompt but fragile if browser not focused — needs live verification
- ✅ Wait action triggered false "no screen change" → AI re-ran previous step — fixed in `agent.py` (wait always trusted)
- ⬜ `pyautogui.write()` slow for long strings — low priority for demo
