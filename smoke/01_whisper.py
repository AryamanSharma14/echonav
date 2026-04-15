"""Smoke test 1: record 3 sec from mic, transcribe with faster-whisper."""
import sounddevice as sd
import soundfile as sf
import tempfile, os
from faster_whisper import WhisperModel

SR = 16000
DUR = 3

print(f"Recording {DUR}s — speak now...")
audio = sd.rec(int(DUR * SR), samplerate=SR, channels=1, dtype="float32")
sd.wait()
print("Done recording. Loading Whisper base.en (first run downloads model)...")

tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
tmp.close()
sf.write(tmp.name, audio, SR)

model = WhisperModel("base.en", device="cpu", compute_type="int8")
segments, _ = model.transcribe(tmp.name)
text = " ".join(s.text for s in segments).strip()
os.unlink(tmp.name)

print(f"Transcript: {text!r}")
assert text, "Got empty transcript — mic may not be capturing."
print("PASS")
