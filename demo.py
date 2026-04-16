"""
EchoNav — Mock Demo

Runs the real overlay, real TTS, and real spacebar listener.
STT and vision are scripted so you can demo the full UX without
Jai's modules (screen.py, stt.py, vision.py) being ready.

Usage:
    venv\\Scripts\\activate
    python demo.py

Hold spacebar → speak anything (or say nothing) → watch the overlay
and listen to the narration as EchoNav "completes" a scripted task.

Press Ctrl+C to quit.
"""

import itertools
import queue
import threading
import time

import tts
import overlay as overlay_module
import listener as listener_module
import commands
import config

# ---------------------------------------------------------------------------
# Scripted demo scenarios — cycles through these on each spacebar press
# ---------------------------------------------------------------------------

_SCENARIOS = itertools.cycle([
    {
        "transcript": "open gmail",
        "confidence": 0.92,
        "actions": [
            {"action": "key",   "key": "win",          "narration": "Opening Start menu"},
            {"action": "type",  "text": "gmail",        "narration": "Typing Gmail"},
            {"action": "key",   "key": "enter",         "narration": "Pressing Enter"},
            {"action": "wait",                           "narration": "Waiting for Gmail to load"},
            {"action": "done",  "message": "Gmail is open. You have 3 unread emails."},
        ],
    },
    {
        "transcript": "compose an email to John",
        "confidence": 0.88,
        "actions": [
            {"action": "click", "x": 120, "y": 200,    "narration": "Clicking Compose button"},
            {"action": "click", "x": 400, "y": 320,    "narration": "Clicking the To field"},
            {"action": "type",  "text": "john@example.com", "narration": "Typing recipient address"},
            {"action": "click", "x": 400, "y": 400,    "narration": "Clicking subject line"},
            {"action": "type",  "text": "Hello",        "narration": "Typing subject"},
            {"action": "click", "x": 800, "y": 600,    "narration": "Clicking send button"},
            {"action": "done",  "message": "Email composed and ready to send. Say yes to confirm send."},
        ],
    },
    {
        "transcript": "search YouTube for relaxing piano music",
        "confidence": 0.95,
        "actions": [
            {"action": "key",   "key": "win",           "narration": "Opening browser"},
            {"action": "type",  "text": "youtube.com",  "narration": "Navigating to YouTube"},
            {"action": "key",   "key": "enter",          "narration": "Pressing Enter"},
            {"action": "wait",                            "narration": "Waiting for page to load"},
            {"action": "click", "x": 640, "y": 65,      "narration": "Clicking search bar"},
            {"action": "type",  "text": "relaxing piano music", "narration": "Typing search query"},
            {"action": "key",   "key": "enter",          "narration": "Searching"},
            {"action": "done",  "message": "Search results are showing. Top result: 3-Hour Relaxing Piano Music."},
        ],
    },
    {
        "transcript": "what can I do here",
        "confidence": 0.91,
        "actions": [
            {"action": "done",  "message": (
                "You are on your Windows desktop. "
                "You can open apps by saying their name, "
                "search the web, compose emails, or ask me to read anything on screen."
            )},
        ],
    },
])


# ---------------------------------------------------------------------------
# Fake executor — prints instead of clicking so we don't touch the screen
# ---------------------------------------------------------------------------

def _fake_execute(action: dict) -> None:
    act = action.get("action")
    if act == "click":
        print(f"  [demo] CLICK at ({action.get('x')}, {action.get('y')})")
    elif act == "type":
        print(f"  [demo] TYPE: {action.get('text')!r}")
    elif act == "key":
        print(f"  [demo] KEY: {action.get('key')}")
    elif act == "scroll":
        print(f"  [demo] SCROLL {action.get('direction')} x{action.get('amount')}")
    elif act == "wait":
        time.sleep(0.8)
    # done: no-op


# ---------------------------------------------------------------------------
# Scripted agent loop (replaces agent.run_goal for the demo)
# ---------------------------------------------------------------------------

def _run_scripted_goal(
    scenario: dict,
    overlay,
    waiting_for_confirmation: threading.Event,
    confirmation_queue: queue.Queue,
) -> None:
    for action in scenario["actions"]:
        if action["action"] == "done":
            tts.speak(action.get("message", "Task complete."))
            if overlay:
                overlay.update("done", action.get("message", "Done"))
            time.sleep(2)
            if overlay:
                overlay.update("idle")
            return

        narration = action.get("narration", "Taking action.")

        # Confirmation gate for "major" actions
        if any(kw in narration.lower() for kw in config.MAJOR_ACTION_KEYWORDS):
            tts.speak(f"{narration}. Say yes to confirm, or no to cancel.")
            if overlay:
                overlay.update("confirming", f"{narration} — say yes or no")
            waiting_for_confirmation.set()
            try:
                confirmed = confirmation_queue.get(timeout=15)
            except queue.Empty:
                confirmed = False
            finally:
                waiting_for_confirmation.clear()

            if not confirmed:
                tts.speak("Okay, cancelled.")
                if overlay:
                    overlay.update("idle")
                return
        else:
            tts.speak(narration)
            if overlay:
                overlay.update("acting", narration)

        _fake_execute(action)
        time.sleep(0.4)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

class DemoApp:
    def __init__(self, overlay) -> None:
        self._overlay = overlay
        self._waiting_for_confirmation = threading.Event()
        self._confirmation_queue: queue.Queue = queue.Queue()
        self._listener = listener_module.Listener(
            on_utterance=self._handle_utterance,
            on_start=self._on_start_recording,
        )

    def run(self) -> None:
        tts.speak("EchoNav demo ready. Hold spacebar to begin.")
        self._listener.start()
        if self._overlay:
            self._overlay.run()
        else:
            threading.Event().wait()

    def _on_start_recording(self) -> None:
        if self._overlay:
            self._overlay.update("listening", "Listening...")

    def _handle_utterance(self, audio, sample_rate: int) -> None:
        if self._overlay:
            self._overlay.update("thinking", "Transcribing...")
        time.sleep(0.6)   # simulate STT delay

        scenario = next(_SCENARIOS)
        text = scenario["transcript"]
        confidence = scenario["confidence"]

        print(f"\n[demo] Simulated transcript: {text!r} (confidence: {confidence})")

        # Confirmation response
        if self._waiting_for_confirmation.is_set():
            lower = text.lower()
            self._confirmation_queue.put("yes" in lower)
            if self._overlay:
                self._overlay.update("idle")
            return

        # Special commands still work for real
        try:
            if commands.check_command(text):
                if self._overlay:
                    self._overlay.update("idle")
                return
        except commands.StopCommand:
            if self._overlay:
                self._overlay.update("idle")
            return

        if self._overlay:
            self._overlay.update("acting", f'"{text}"')

        threading.Thread(
            target=_run_scripted_goal,
            args=(scenario, self._overlay,
                  self._waiting_for_confirmation, self._confirmation_queue),
            daemon=True,
        ).start()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("  EchoNav — Mock Demo")
    print("  Hold spacebar → speak (or just release) → watch + listen")
    print("  Real commands (stop, go back, where am I) still work.")
    print("  Ctrl+C to quit.")
    print("=" * 60)

    ov = overlay_module.Overlay()
    DemoApp(overlay=ov).run()


if __name__ == "__main__":
    main()
