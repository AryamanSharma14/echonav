# Stub — implementation owned by task-4-stt (Jai)
# This file exists so main.py can import it; tests mock it.
import os
import tempfile
import numpy as np
import soundfile as sf
import config

_model = None

def load_model():
    """Load Whisper model once and cache it."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        # Using int8 quantization for efficient local CPU inference
        _model = WhisperModel(config.STT_MODEL, device="cpu", compute_type="int8")
    return _model

def transcribe(audio_data: np.ndarray, sample_rate: int = 16000) -> tuple[str, float]:
    """
    Transcribe audio array to text.
    Returns (text, confidence) where confidence is 0.0–1.0.
    """
    model = load_model()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, audio_data, sample_rate)
        temp_path = f.name

    try:
        segments, info = model.transcribe(temp_path, language="en")
        text = " ".join(s.text.strip() for s in segments).strip()
        # Fallback to 0.8 if language_probability is None
        confidence = float(min(1.0, max(0.0, info.language_probability or 0.8)))
        return text, confidence
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass