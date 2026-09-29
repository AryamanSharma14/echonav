"""Offline Speech-to-Text inference engine for EchoNav.

Uses faster-whisper with int8 quantization on local CPU, preceded by a
Root-Mean-Square (RMS) Voice Activity Detection (VAD) energy filter to
prevent hallucinations on silence, background breath, or keyclicks.
"""

from __future__ import annotations

import logging
import os
import tempfile
import numpy as np
import soundfile as sf

import config

logger = logging.getLogger("echonav.stt")

_model = None


def load_model():
    """Load Whisper model once and cache it for the application lifetime."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        # Using int8 quantization for efficient local CPU inference
        _model = WhisperModel(config.STT_MODEL, device="cpu", compute_type="int8")
    return _model


def is_silent(audio_data: np.ndarray, threshold: float = 0.006) -> bool:
    """Check if audio signal is below speech energy threshold (pure silence or static)."""
    if audio_data is None or len(audio_data) == 0:
        return True
    rms = float(np.sqrt(np.mean(audio_data ** 2)))
    return rms < threshold


def transcribe(audio_data: np.ndarray, sample_rate: int = 16000, filter_silence: bool = False) -> tuple[str, float]:
    """Transcribe audio array to text.

    Returns (text, confidence) where confidence is 0.0–1.0.
    """
    if audio_data is None or len(audio_data) == 0:
        return "", 0.0
    if filter_silence and is_silent(audio_data):
        return "", 0.0

    model = load_model()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, audio_data, sample_rate)
        temp_path = f.name

    try:
        segments, info = model.transcribe(temp_path, language="en")
        text = " ".join(s.text.strip() for s in segments).strip()
        confidence = float(min(1.0, max(0.0, info.language_probability or 0.8)))
        return text, confidence
    except Exception as exc:
        logger.error(f"STT transcription failed: {exc}")
        return "", 0.0
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass