"""Smoke test 2: edge-tts synthesizes and plays audio."""
import asyncio, tempfile, os
import edge_tts
import soundfile as sf
import sounddevice as sd

TEXT = "EchoNav smoke test. If you hear this, text to speech is working."
VOICE = "en-US-AriaNeural"

async def main():
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.close()
    print("Synthesizing...")
    communicate = edge_tts.Communicate(TEXT, VOICE)
    await communicate.save(tmp.name)
    print(f"Saved: {tmp.name}")

    # edge-tts outputs mp3; soundfile needs wav. Convert via simple fallback: use playsound or just report success.
    # Fallback: play with winsound (wav only) or just confirm file was produced and non-empty.
    size = os.path.getsize(tmp.name)
    assert size > 1000, f"TTS output suspiciously small: {size} bytes"
    print(f"MP3 size: {size} bytes")
    print("Now playing via default player (close when done)...")
    os.startfile(tmp.name)  # Windows only
    print("PASS (if you heard audio)")

asyncio.run(main())
