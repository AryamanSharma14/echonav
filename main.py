"""
EchoNav entry point.

Event loop:
  Listener (spacebar hold) → audio → stt.transcribe → text
  If waiting_for_confirmation: route yes/no to confirmation_queue
  Else if commands.check_command(text): handled (may raise StopCommand)
  Else: agent.run_goal(text, ...) in background thread

Overlay (optional): always-on-top status strip shown to sighted users / judges.
  Runs in the main thread (tkinter requirement). App logic runs in background threads.
"""

import queue
import threading

import agent
import commands
import config
import listener as listener_module
import overlay as overlay_module
import stt
import tts


class App:
    def __init__(self, overlay=None) -> None:
        self._overlay = overlay
        self._waiting_for_confirmation = threading.Event()
        self._confirmation_queue: queue.Queue = queue.Queue()
        self._listener = listener_module.Listener(
            on_utterance=self._handle_utterance,
            on_start=self._on_start_recording,
        )

    def run(self) -> None:
        tts.speak("EchoNav ready. Hold spacebar and speak your task.")
        self._listener.start()
        if self._overlay:
            self._overlay.run()   # blocks — tkinter mainloop in main thread
        else:
            threading.Event().wait()   # headless: block forever

    # ------------------------------------------------------------------
    # Listener callbacks
    # ------------------------------------------------------------------

    def _on_start_recording(self) -> None:
        if self._overlay:
            self._overlay.update("listening", "Listening...")

    def _handle_utterance(self, audio, sample_rate: int) -> None:
        if self._overlay:
            self._overlay.update("thinking", "Transcribing...")

        text, confidence = stt.transcribe(audio, sample_rate)

        # --- Confirmation branch ---
        if self._waiting_for_confirmation.is_set():
            lower = text.lower().strip()
            if "yes" in lower:
                self._confirmation_queue.put(True)
            else:
                self._confirmation_queue.put(False)
            if self._overlay:
                self._overlay.update("idle")
            return

        # --- Low confidence ---
        if confidence < config.STT_CONFIDENCE_THRESHOLD:
            tts.speak("Sorry, I didn't catch that. Could you repeat?")
            if self._overlay:
                self._overlay.update("idle")
            return

        # --- Show goal in overlay ---
        if self._overlay:
            self._overlay.update("acting", f'"{text}"')

        # --- Special commands (stop, go back, read page, …) ---
        try:
            if commands.check_command(text):
                if self._overlay:
                    self._overlay.update("idle")
                return
        except commands.StopCommand:
            if self._overlay:
                self._overlay.update("idle")
            return

        # --- Regular goal → agent loop in background thread ---
        threading.Thread(
            target=self._run_goal,
            args=(text,),
            daemon=True,
        ).start()

    def _run_goal(self, text: str) -> None:
        if self._overlay:
            self._overlay.update("acting", text)
        agent.run_goal(text, self._waiting_for_confirmation, self._confirmation_queue)
        if self._overlay:
            self._overlay.update("done")
            # Reset to idle after a short pause
            threading.Timer(2.0, lambda: self._overlay.update("idle")).start()


def main() -> None:
    ov = overlay_module.Overlay()
    App(overlay=ov).run()


if __name__ == "__main__":
    main()
