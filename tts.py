"""TTS — instant speech narration via dedicated worker thread and Windows SAPI5."""

from __future__ import annotations

import logging
import queue
import threading
import pyttsx3
import config

logger = logging.getLogger("echonav.tts")

_last_utterance: str = ""
_rate: int = config.TTS_RATE
_q: queue.Queue = queue.Queue()
_current_engine: pyttsx3.Engine | None = None
_engine_lock = threading.Lock()


def _worker() -> None:
    global _current_engine
    while True:
        text, done = _q.get()
        engine = None
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", _rate)
            with _engine_lock:
                _current_engine = engine
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            logger.debug(f"pyttsx3 error: {e}")
        finally:
            with _engine_lock:
                _current_engine = None
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


def stop_speech() -> None:
    """Abort currently speaking speech immediately and drain the utterance queue."""
    global _current_engine
    while not _q.empty():
        try:
            _, done = _q.get_nowait()
            if done is not None:
                done.set()
        except queue.Empty:
            break
    with _engine_lock:
        if _current_engine:
            try:
                _current_engine.stop()
            except Exception:
                pass


def set_rate(wpm: int) -> None:
    """Set speech rate in words per minute. Clamped to [80, 300]."""
    global _rate
    _rate = max(80, min(300, wpm))
