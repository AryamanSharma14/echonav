"""
TTS — instant, non-blocking speech via a dedicated worker thread.

A fresh pyttsx3 engine is created per utterance: the Windows SAPI5 driver
silently stops speaking after the first runAndWait() if the engine is
reused, so one engine per utterance is the reliable workaround. The
per-call init is ~50 ms — still two orders of magnitude faster than the
old edge_tts + PowerShell approach (~2–3 s).
"""

import queue
import threading
import pyttsx3
import config

_last_utterance: str = ""
_rate: int = config.TTS_RATE
_q: queue.Queue = queue.Queue()


def _worker() -> None:
    while True:
        text, done = _q.get()
        engine = None
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", _rate)
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"[tts] pyttsx3 error: {e}")
        finally:
            try:
                if engine:
                    engine.stop()
            except Exception:
                pass
            if done is not None:
                done.set()


_worker_thread = threading.Thread(target=_worker, daemon=True)
_worker_thread.start()


def speak(text: str) -> None:
    """Blocking — waits until the utterance finishes."""
    global _last_utterance
    _last_utterance = text
    done = threading.Event()
    _q.put((text, done))
    done.wait()


def speak_nonblocking(text: str) -> None:
    """Enqueue and return immediately. Audio plays in the worker thread."""
    global _last_utterance
    _last_utterance = text
    _q.put((text, None))


def speak_last() -> None:
    """Repeat the last spoken utterance."""
    if _last_utterance:
        speak(_last_utterance)


def set_rate(wpm: int) -> None:
    """Set speech rate in words per minute. Clamped to [80, 300]."""
    global _rate
    _rate = max(80, min(300, wpm))
