# Hackathon — Full Day

Three contributors. Two on code (with Claude Code), one on demo/docs/QA.

Plan reference: `../../Dayzero/docs/superpowers/plans/2026-04-13-navigator-implementation.md` (14 tasks)

---

## Checkpoint Schedule

| Time | Checkpoint | Goal |
|---|---|---|
| **09:00** | Kickoff | Clone repo, venv, install reqs, read CLAUDE.md + plan. Claim tasks. |
| **10:30** | CP1 — Foundation green | Tasks 1–5 merged. Screen + STT + TTS + listener work in isolation. |
| **13:00** | CP2 — Brain online | Tasks 6–8 merged. Vision returns actions; executor runs them; commands intercept. |
| **15:30** | CP3 — Loop alive | Tasks 9–10 merged. End-to-end "open google, search cats" works. |
| **17:30** | CP4 — Polish | Tasks 11–12. Auto-start, full test suite green, bug-bash. |
| **19:00** | CP5 — Demo ready | Task 14 demo verified. Video recorded. Pitch deck done. |
| **20:00** | Submit | |

Miss a checkpoint → drop scope, not quality. Tasks 11 and 13 are first to cut.

---

## Roles

**Lead / Integration (Claude Code).** Owns the agent loop, executor, listener, main.py. Glues everything. After CP2, shifts from building modules to integration, bug triage, PR review.

**AI / Voice (Claude Code).** Owns vision (prompt engineering for Gemini/Claude), STT tuning, screen capture. If time allows, attempts Task 13 (Claude Computer Use) as the demo upgrade.

**Demo / Docs / QA (no Claude Code).** Non-code track, runs in parallel all day:
- Pitch script (~90 sec spoken)
- 2-min demo video with narration
- README with screenshots and install steps
- Devpost / submission form
- Accessibility bug-bash from CP2 onward (use the agent eyes-closed, file every point of confusion)
- Logo / title card / submission polish

Pair-programming OK if they want to write tests or simple logic — lead drives the keyboard.

---

## GitHub Workflow

**Repo:** one repo, `main` protected. Require PR + 1 review to merge.

**Per-task flow:**
```bash
git checkout main && git pull
git checkout -b task-6-vision
# TDD: write test → red → implement → green → commit
git push -u origin task-6-vision
gh pr create --title "task-6: vision module" --body "Closes task 6. Tests green."
# reviewer approves → squash-merge
git branch -d task-6-vision
```

**Commits:** small, frequent. Every green test = a commit. Format: `task-<N>: <what>`.

**PR rules:**
- All tests pass (`pytest -v`).
- One reviewer approval before merge.
- Squash-merge to keep `main` linear.
- Delete branch after merge.

**Merge conflicts:** rebase on latest `main`. If two people touched the same file (shouldn't happen if File Map is respected), the later PR rebases and resolves.

---

## Scope Cuts (in order, if behind)
1. Task 13 (Claude Computer Use upgrade)
2. Task 11 (Windows auto-start)
3. Claude provider in `vision.py` — Gemini-only
4. Watchdog
5. Confirmation prompts — only cut at CP4, not earlier (accessibility matters for judges)

## Do NOT Cut
- Task 14 demo verification
- Task 12 full test run
- README
