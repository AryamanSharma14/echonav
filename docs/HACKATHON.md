# EchoNav — Hackathon Day 1

Three contributors. Two on code (with Claude Code), one on demo/docs/QA.

- Spec: `../Dayzero/docs/superpowers/specs/2026-04-13-blind-nav-agent-design.md`
- Plan: `../Dayzero/docs/superpowers/plans/2026-04-13-navigator-implementation.md` (14 tasks)
- Live task list: `docs/TODO.md` — claim and check off tasks here
- Progress log: `docs/PROGRESS.md` — append-only; read at every session start

> ⚠️ **Submission deadline: 1:00 PM.** Scope cuts are pre-decided below — do not debate mid-day.

> ✅ **Pre-hackathon prep complete** (done 2026-04-15 night): venv + deps installed, smoke tests green (Whisper / TTS / pyautogui / vision), Groq wired as primary vision provider, all coordination docs in place, `GROQ_API_KEY` in `.env` on lead machine.

---

## Checkpoint Schedule

| Time | Checkpoint | Goal |
|---|---|---|
| **09:00** | Kickoff | `git pull origin master`. Run session start ritual (see below). Claim tasks in `docs/TODO.md`. No setup needed — prep is done. |
| **10:00** | CP1 — Foundation green | T1–T5 merged to `master`. Screen + STT + TTS + listener work in isolation. |
| **11:15** | CP2 — Brain online | T6–T8 merged. Vision (Groq) returns actions; executor runs them; commands intercept. |
| **12:00** | CP3 — Loop alive | T9–T10 merged. End-to-end "open Google, search cats" works. |
| **12:30** | CP4 — Polish | T12 full test suite green. Bug-bash. README final. |
| **12:45** | CP5 — Demo ready | T14 all 5 scenarios verified. Demo video recorded and uploaded. |
| **13:00** | Submit | Devpost submitted. |

Miss a checkpoint → cut scope immediately. See pre-decided cuts below.

---

## Session Start Ritual (MANDATORY for both Claude Code instances)

Every new Claude session on this repo — including the 09:00 kickoff:

1. `git pull origin master`
2. Read `docs/PROGRESS.md` (top 5 entries) — know what just shipped.
3. Read `docs/TODO.md` — see what's in flight and what's free.
4. Report to the human: "Last push was `<role>` on `<branch>`. Open tasks: X, Y, Z. Which one?"

Do not start writing code before completing this ritual.

---

## Push Protocol (MANDATORY on every push)

Before `git push`, update shared context so the other Claude is not lost:

1. Update `docs/TODO.md`: flip the task to 🟡 in-progress or ✅ done.
2. Append to `docs/PROGRESS.md` via the helper:
   ```
   bash scripts/log-push.sh "Done: <what>. Next: <what>. Notes: <gotchas>"
   ```
   The helper stamps the time, commits TODO + PROGRESS, and pushes.
3. If the helper is unavailable, add the entry manually, then commit + push.

**Never push code without a PROGRESS entry.** The other Claude depends on it. Under time pressure this step gets skipped — it must not.

---

## Pre-Decided Scope Cuts (already dropped — do not attempt today)

- ~~**T13** Claude Computer Use upgrade~~ — cut
- ~~**T11** Windows auto-start / watchdog~~ — cut
- Vision provider: **Groq primary, Gemini fallback only**. No Claude vision today.

If CP3 slips past 12:15, additionally cut:
- All special voice commands except `stop`, `read the page`, and `where am I`

---

## Roles

**Lead / Integration (Claude Code).** Owns T1, T3, T5, T7, T8, T9, T10, T12. Glues everything. After CP2 (11:15), shifts entirely to integration, bug triage, and PR review — no new features.

**AI / Voice (Claude Code).** Owns T2, T4, T6. Focus: get Groq vision path rock-solid for demo. No T13 today.

**Demo / Docs / QA (no Claude Code).** Parallel track with hard internal deadlines:

| By | Deliverable |
|---|---|
| 11:00 | Pitch script (~90 sec spoken) |
| 11:30 | README with screenshots + install steps |
| 12:00 | Devpost form filled (everything except video link) |
| 12:30 | Accessibility bug-bash log (starts after CP2, file every point of confusion) |
| 12:45 | 2-min demo video recorded, narrated, uploaded — link added to Devpost |
| 13:00 | Logo / title card / final submission polish |

Pair-programming OK if they want to write tests or simple logic — lead drives the keyboard.

---

## GitHub Workflow

**Repo:** one repo, `master` protected. Require PR + 1 review to merge.

**Per-task flow:**
```bash
git checkout master && git pull origin master
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
- Squash-merge to keep `master` linear.
- Delete branch after merge.

**Merge conflicts:** rebase on latest `master`. If two people touched the same file (shouldn't happen if File Map is respected), the later PR rebases and resolves.

---

## Do NOT Cut
- T14 end-to-end demo verification (all 5 scenarios)
- T12 full test run
- README