import asyncio
import tempfile
import os
import subprocess
import pyttsx3
import config

_last_utterance: str = ""
_rate: int = config.TTS_RATE


def speak(text: str) -> None:
    """Speak text aloud. Saves utterance for repeat."""
    global _last_utterance
    _last_utterance = text
    try:
        _speak_edge(text)
    except Exception:
        _speak_pyttsx3(text)


def speak_last() -> None:
    """Repeat the last spoken utterance."""
    if _last_utterance:
        speak(_last_utterance)


def set_rate(wpm: int) -> None:
    """Set speech rate in words per minute. Clamped to [80, 300]."""
    global _rate
    _rate = max(80, min(300, wpm))


def _speak_edge(text: str) -> None:
    asyncio.run(_speak_edge_async(text))


async def _speak_edge_async(text: str) -> None:
    import edge_tts
    offset = _rate - 150
    rate_str = f"+{offset}%" if offset >= 0 else f"{offset}%"
    communicate = edge_tts.Communicate(text, config.TTS_VOICE, rate=rate_str)

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        temp_path = f.name

    try:
        await communicate.save(temp_path)
        subprocess.run(
            ["powershell", "-c",
             f"Add-Type -AssemblyName presentationCore; "
             f"$mp = New-Object system.windows.media.mediaplayer; "
             f"$mp.open('{temp_path}'); $mp.Play(); Start-Sleep -s 5; $mp.Stop()"],
            capture_output=True, timeout=30
        )
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


def _speak_pyttsx3(text: str) -> None:
    engine = pyttsx3.init()
    engine.setProperty("rate", _rate)
    engine.say(text)
    engine.runAndWait()
