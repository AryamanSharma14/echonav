# EchoNav — Project Instructions for Claude

## Project
Voice-controlled desktop AI agent for blind users. Spacebar-to-talk → Whisper STT → Gemini Vision analyzes screenshot → pyautogui executes one action → edge-tts narrates → loop.

Hackathon: **full day, 2026-04-15**. Team of 3: **Aryaman** (lead), **Jai**, **Anya**.

## Source of Truth
- Spec: `C:/Users/aryam/Desktop/yee/coding/Dayzero/docs/superpowers/specs/2026-04-13-blind-nav-agent-design.md`
- Plan: `C:/Users/aryam/Desktop/yee/coding/Dayzero/docs/superpowers/plans/2026-04-13-navigator-implementation.md` (14 TDD tasks)
- Code lives in: `C:/Users/aryam/Desktop/yee/coding/echonav/`
- **Live task list:** `TODO.md` (claim + check off tasks here)
- **Progress log:** `PROGRESS.md` (append-only; read this at session start to sync with the other Claude)

Read the plan before starting a task. Do not re-architect.

## Session Start Ritual (MANDATORY)
Every time a human starts a new Claude session on this repo, do this in order:
1. `git pull origin main`
2. Read `PROGRESS.md` (top 5 entries) → you now know what the other Claude just shipped.
3. Read `TODO.md` → see what's in flight and what's free.
4. Announce to the human: "Last push was `<name>` on `<branch>`. Open tasks: X, Y, Z. Which one?"

## Push Protocol (MANDATORY on every push)
Before `git push`, you MUST update the shared context so the other Claude is not lost:
1. Update `TODO.md`: flip your task to 🟡 in-progress / ✅ done.
2. Append an entry to `PROGRESS.md` using the helper:
   ```
   bash scripts/log-push.sh "Done: <what>. Next: <what>. Notes: <gotchas>"
   ```
   The helper stamps the time, commits TODO+PROGRESS, and pushes.
3. If the helper is unavailable, add the entry manually in the format shown in `PROGRESS.md`, then commit+push.

**Never push code without a PROGRESS.md entry.** The other Claude depends on it for context.

## Multi-Claude Coordination (Aryaman + Jai)
Two humans, two Claude instances, one repo. Rules:

1. **One task = one person = one branch.** Branch name: `task-<N>-<slug>` (e.g. `task-6-vision`).
2. **Before starting**, `git pull origin main`, read `PROGRESS.md` + `TODO.md`. Claim your task in `TODO.md` (flip to 🟡), commit, push.
3. **Never edit files owned by another in-flight task.** File ownership is in the plan's File Map.
4. **Commit every green test.** TDD is mandatory — plan has failing-test-first steps.
5. **PR → main** when the task's test suite passes. The other human/Claude reviews before merge.
6. **If blocked on an interface** (e.g., need `vision.py` signature), read that task in the plan — signatures are pre-defined there.

## Hard Rules
- Python 3.11+, Windows-first.
- Follow the plan task-by-task. TDD. No scope creep.
- Do not touch `Dayzero/` except to update the plan/spec.
- Commit messages: `task-<N>: <what>` — no "generated with Claude" footers.
- If a test is flaky, fix the test, not the assertion.

## Running
```
cd C:/Users/aryam/Desktop/yee/coding/echonav
venv\Scripts\activate
pytest -v
python main.py
```

## When in Doubt
Ask the human. Do not invent module boundaries that aren't in the File Map.
