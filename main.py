"""
EchoNav entry point.

Event loop:
  Listener (spacebar hold) → audio → stt.transcribe → text
  If waiting_for_confirmation: route yes/no to confirmation_queue
  Else if commands.check_command(text): handled (may raise StopCommand)
  Else: agent.run_goal(text, ...) in background thread
"""

import queue
import threading

import agent
import commands
import config
import listener as listener_module
import stt
import tts


class App:
    def __init__(self) -> None:
        self._waiting_for_confirmation = threading.Event()
        self._confirmation_queue: queue.Queue = queue.Queue()
        self._listener = listener_module.Listener(
            on_utterance=self._handle_utterance
        )

    def run(self) -> None:
        tts.speak("EchoNav ready. Hold spacebar and speak your task.")
        kb = self._listener.start()
        kb.join()

    def _handle_utterance(self, audio, sample_rate: int) -> None:
        text, confidence = stt.transcribe(audio, sample_rate)

        # --- Confirmation branch ---
        if self._waiting_for_confirmation.is_set():
            lower = text.lower().strip()
            if "yes" in lower:
                self._confirmation_queue.put(True)
            else:
                self._confirmation_queue.put(False)
            return

        # --- Low confidence ---
        if confidence < config.STT_CONFIDENCE_THRESHOLD:
            tts.speak("Sorry, I didn't catch that. Could you repeat?")
            return

        # --- Special commands (stop, go back, read page, …) ---
        try:
            if commands.check_command(text):
                return
        except commands.StopCommand:
            return

        # --- Regular goal → agent loop in background thread ---
        threading.Thread(
            target=agent.run_goal,
            args=(text, self._waiting_for_confirmation, self._confirmation_queue),
            daemon=True,
        ).start()


def main() -> None:
    App().run()


if __name__ == "__main__":
    main()
