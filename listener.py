import threading
import numpy as np
import sounddevice as sd
import winsound
from pynput import keyboard

SAMPLE_RATE = 16000


class Listener:
    """Detects spacebar hold, records audio, calls on_utterance when released."""

    def __init__(self, on_utterance, on_start=None):
        """
        on_utterance: callable(audio: np.ndarray, sample_rate: int)
            Called in a background thread when the user releases spacebar.
        on_start: optional callable() — called when recording begins (spacebar pressed).
        """
        self._on_utterance = on_utterance
        self._on_start = on_start
        self._recording = False
        self._audio_chunks: list = []
        self._stream = None

    def start(self):
        """Start listening. Returns the pynput listener (call .join() to block)."""
        kb = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        kb.start()
        return kb

    def _on_press(self, key) -> None:
        if key == keyboard.Key.space and not self._recording:
            self._recording = True
            self._audio_chunks = []
            winsound.Beep(880, 80)  # high beep = start recording
            if self._on_start:
                self._on_start()
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                callback=self._audio_callback,
            )
            self._stream.start()

    def _on_release(self, key) -> None:
        if key == keyboard.Key.space and self._recording:
            self._recording = False
            winsound.Beep(440, 80)  # low beep = stop recording
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None

            if self._audio_chunks:
                audio = np.concatenate(self._audio_chunks)
                threading.Thread(
                    target=self._on_utterance,
                    args=(audio, SAMPLE_RATE),
                    daemon=True,
                ).start()

    def _audio_callback(self, indata: np.ndarray, frames: int, time, status) -> None:
        if self._recording:
            self._audio_chunks.append(indata[:, 0].copy())
