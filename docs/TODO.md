# TODO — live task list

Edit + push to update. Both Claude instances read this at session start.
Legend: ⬜ todo · 🟡 in progress · ✅ done · ❌ blocked

## Pre-hackathon prep ✅ (done 2026-04-15 night)
- [x] ✅ venv + all deps installed
- [x] ✅ Smoke tests: Whisper, TTS, pyautogui, vision — all PASS
- [x] ✅ Groq wired as primary vision provider (free, no billing needed)
- [x] ✅ Coordination docs: CLAUDE.md, HACKATHON.md, TODO.md, PROGRESS.md, log-push.sh
- [x] ✅ GROQ_API_KEY in .env (lead machine)

## CP1 — Foundation (target 10:30)
- [ ] ⬜ **T1** Project setup — `requirements.txt`, `config.py`, `tests/__init__.py` — _lead_
- [🟡] ⬜ **T2** Screen capture (`screen.py`) — _ai_
- [ ] ⬜ **T3** TTS (`tts.py`) — _lead_
- [🟡] ⬜ **T4** STT (`stt.py`) — _ai_
- [ ] ⬜ **T5** Listener / spacebar (`listener.py`) — _lead_

## CP2 — Brain ✅ (lead side done)
- [ ] ⬜ **T6** Vision (`vision.py`) — Groq primary, Gemini fallback — _ai_ — stub in place
- [x] ✅ **T7** Executor (`executor.py`) — _lead_
- [x] ✅ **T8** Special voice commands (`commands.py`) — _lead_

## CP3 — Loop alive ✅
- [x] ✅ **T9** Agent loop (`agent.py`) — _lead_
- [x] ✅ **T10** `main.py` wiring — _both_

## CP4 — Polish
- [ ] ⬜ **T11** Windows auto-start (`setup.py`, `watchdog.py`) — _lead_ (cut if behind)
- [x] ✅ **T12** Full test suite green — 38/38 passing — _lead_

## CP5 — Demo
- [ ] ⬜ **T13** Claude Computer Use upgrade — _ai_ (stretch, cut first)
- [ ] 🟡 **T14** End-to-end demo verification — _all_ — blocked on T2/T4/T6

## Non-code track (parallel, all day)
- [ ] ⬜ Pitch script (~90 sec spoken)
- [ ] ⬜ Demo video (2 min, screen + narration)
- [ ] ⬜ README.md with screenshots + install steps
- [ ] ⬜ Devpost / submission form filled
- [ ] ⬜ Accessibility bug-bash log (starts after CP2)
- [ ] ⬜ Project logo / title card

## Bug list
- _(empty)_
