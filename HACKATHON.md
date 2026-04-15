# EchoNav Hackathon — 2026-04-15 (Full Day)

Team: **Aryaman** (lead / integration), **Jai** (AI + voice), **Anya** (testing / demo / docs)

Plan reference: `Dayzero/docs/superpowers/plans/2026-04-13-navigator-implementation.md` (14 tasks)

---

## Checkpoint Schedule

| Time | Checkpoint | Goal |
|---|---|---|
| **09:00** | Kickoff | Clone repo, venv, install reqs, read CLAUDE.md + plan. Assign tasks below. |
| **10:30** | CP1 — Foundation green | Tasks 1–5 merged. Screen + STT + TTS + listener working in isolation. |
| **13:00** | CP2 — Brain online | Tasks 6–8 merged. Vision returns actions; executor runs them; commands intercept. |
| **15:30** | CP3 — Loop alive | Task 9 (agent) + Task 10 (main.py) merged. End-to-end "open google, search cats" works. |
| **17:30** | CP4 — Polish | Tasks 11–12. Auto-start, full test suite green, bug-bash from Anya. |
| **19:00** | CP5 — Demo ready | Task 14 demo verified. Video recorded. Pitch deck done. |
| **20:00** | Submit | |

Miss a checkpoint → drop scope, not quality. Task 11 (auto-start) and Task 13 (Claude Computer Use upgrade) are the first to cut.

---

## Task Board (live — edit to claim)

| # | Task | Owner | Branch | Status |
|---|---|---|---|---|
| 1 | Project setup | Aryaman | `task-1-setup` | ⬜ |
| 2 | Screen capture | Jai | `task-2-screen` | ⬜ |
| 3 | TTS | Anya | `task-3-tts` | ⬜ |
| 4 | STT | Jai | `task-4-stt` | ⬜ |
| 5 | Listener (spacebar) | Aryaman | `task-5-listener` | ⬜ |
| 6 | Vision (Gemini + Claude) | Jai | `task-6-vision` | ⬜ |
| 7 | Executor (pyautogui) | Aryaman | `task-7-executor` | ⬜ |
| 8 | Special voice commands | Anya | `task-8-commands` | ⬜ |
| 9 | Agent loop | Aryaman | `task-9-agent` | ⬜ |
| 10 | main.py wiring | Aryaman + Jai | `task-10-main` | ⬜ |
| 11 | Windows auto-start | Anya | `task-11-autostart` | ⬜ |
| 12 | Full test suite | Anya | `task-12-tests` | ⬜ |
| 13 | Claude Computer Use upgrade | Jai | `task-13-ccu` | ⬜ (stretch) |
| 14 | E2E demo | All | `task-14-demo` | ⬜ |

Legend: ⬜ todo · 🟡 in progress · ✅ merged · ❌ blocked

---

## Role Breakdown

### Aryaman — Lead / Integration
Owns the agent loop, executor, listener, and main.py. You glue everything together. After CP2, your job shifts from coding modules to integration, bug triage, and reviewing Jai's PRs.

### Jai — AI + Voice
Owns the "intelligent" bits: vision module (prompt engineering against Gemini/Claude), STT tuning, screen capture. If time allows, Jai attempts Task 13 (Claude Computer Use) as the flashy demo upgrade.

### Anya — QA / Demo / Docs (NO Claude Code — no AI pair)
Anya does not have Claude Code. Keep her off the critical code path. She owns the non-code surface of the project:

1. **Demo prep (primary)** — pitch script, 2-min demo video, slide deck. Start morning, polish all day.
2. **README + usage docs** — what judges open first. Screenshots, a 30-second "what is this" section, install steps.
3. **Accessibility bug-bash from CP2** — literally close her eyes and try to use the agent. Log every point of confusion in `TODO.md`'s bug list.
4. **Pair-programming** — sit next to Jai or Aryaman for Task 3 (TTS) or Task 8 (commands) if she wants to code. Lead drives the keyboard, she reviews logic and writes test cases on paper.
5. **Judge-facing polish** — project logo, landing screenshot, devpost/submission form.

Reassigned code tasks: **Tasks 3, 8, 11, 12 → Aryaman + Jai.** Anya is not on the Claude-to-Claude sync loop.

---

## GitHub Workflow

**Repo:** one repo, `main` protected.

**Per-task flow:**
```bash
git checkout main && git pull
git checkout -b task-6-vision
# ... TDD: write test, red, green, commit ...
git push -u origin task-6-vision
gh pr create --title "task-6: vision module" --body "Closes task 6. Tests green."
# other teammate reviews, merges
```

**Commits:** small, frequent. Every green test = a commit. `task-6: add gemini JSON schema validator`.

**PR rules:**
- All tests must pass (`pytest -v`).
- Another human (or their Claude) reviews before merge.
- Squash-merge to keep `main` linear.
- Delete branch after merge.

**Merge conflicts:** rebase on latest `main`, not merge commits. If two people touched the same file (shouldn't happen if File Map is respected), the later PR rebases and resolves.

**Claude-to-Claude coordination:** both Claudes read `CLAUDE.md` + `HACKATHON.md` at session start. The task board is the single source of truth for "who's doing what right now." Update it when you claim or finish a task — that's how the other Claude knows you're on it.

---

## Scope Cuts (in order, if behind)
1. Task 13 (Claude Computer Use)
2. Task 11 (auto-start)
3. Claude provider in vision.py — Gemini-only
4. Watchdog
5. Confirmation prompts for destructive actions (⚠ only cut at CP4, not earlier — accessibility matters for judges)

## Do NOT Cut
- Task 14 demo verification
- Task 12 full test run
- README
