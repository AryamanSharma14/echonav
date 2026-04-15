# EchoNav — Project Instructions for Claude

## Project
Voice-controlled desktop AI agent for blind users. Spacebar-to-talk → Whisper STT → Gemini Vision analyzes screenshot → pyautogui executes one action → edge-tts narrates → loop.

Full-day hackathon. Two Claude Code instances work on this repo in parallel (the `lead` role and the `ai` role). A third contributor works the non-code track (demo, docs, QA) without Claude.

## Source of Truth
- Spec: `../Dayzero/docs/superpowers/specs/2026-04-13-blind-nav-agent-design.md`
- Plan: `../Dayzero/docs/superpowers/plans/2026-04-13-navigator-implementation.md` (14 TDD tasks)
- Hackathon schedule + roles: `docs/HACKATHON.md`
- **Live task list:** `docs/TODO.md` (claim and check off tasks here)
- **Progress log:** `docs/PROGRESS.md` (append-only; read this at session start)

Read the plan before starting a task. Do not re-architect.

## Session Start Ritual (MANDATORY)
Every new Claude session on this repo:
1. `git pull origin master`
2. Read `docs/PROGRESS.md` (top 5 entries) — know what just shipped.
3. Read `docs/TODO.md` — see what's in flight and what's free.
4. Report to the human: "Last push was `<role>` on `<branch>`. Open tasks: X, Y, Z. Which one?"

## Push Protocol (MANDATORY on every push)
Before `git push`, update the shared context so the other Claude is not lost:
1. Update `docs/TODO.md`: flip the task to 🟡 in-progress or ✅ done.
2. Append an entry to `docs/PROGRESS.md` via the helper:
   ```
   bash scripts/log-push.sh "Done: <what>. Next: <what>. Notes: <gotchas>"
   ```
   The helper stamps the time, commits TODO + PROGRESS, and pushes.
3. If the helper is unavailable, add the entry manually (format in `docs/PROGRESS.md`), then commit + push.

**Never push code without a PROGRESS entry.** The other Claude depends on it.

## Multi-Claude Coordination
Two Claude instances, one repo. Rules:
1. **One task = one branch.** Branch name: `task-<N>-<slug>` (e.g. `task-6-vision`).
2. **Before starting**: pull, read PROGRESS + TODO, claim in TODO (flip to 🟡), commit, push.
3. **Never edit files owned by another in-flight task.** File ownership is in the plan's File Map.
4. **TDD is mandatory.** Every green test = a commit.
5. **PR → master** when the task's tests pass. Other side reviews before merge.
6. **Blocked on an interface?** Read that task in the plan — signatures are pre-defined.

## Commit & Doc Voice
- First person, singular. "add X", "fix Y", "I ran Z."
- Never name individual contributors. Use roles (`lead`, `ai`) only in internal docs (`docs/*`), never in commit messages or PR bodies.
- Commit format: `task-<N>: <what>`. No "generated with Claude" footers. No teammate names.

## Hard Rules
- Python 3.11+ target (3.10 works in venv for now). Windows-first.
- Follow the plan task-by-task. TDD. No scope creep.
- Do not touch `../Dayzero/` except to update the plan/spec.
- If a test is flaky, fix the test, not the assertion.

## Running
```
venv\Scripts\activate
pytest -v
python main.py
```

## When in Doubt
Ask. Do not invent module boundaries that aren't in the File Map.
