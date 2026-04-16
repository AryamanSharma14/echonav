import numpy as np
import stt

def test_load_model_returns_model():
    model = stt.load_model()
    assert model is not None

def test_load_model_is_cached():
    model1 = stt.load_model()
    model2 = stt.load_model()
    assert model1 is model2  # Same object — not loaded twice

def test_transcribe_returns_string_and_float(mocker):
    # Mock WhisperModel to avoid loading weights in tests
    mock_segment = mocker.MagicMock()
    mock_segment.text = " hello world"
    mock_info = mocker.MagicMock()
    mock_info.language_probability = 0.95
    mock_model = mocker.MagicMock()
    mock_model.transcribe.return_value = ([mock_segment], mock_info)
    mocker.patch("stt._model", mock_model)
    mocker.patch("stt.load_model", return_value=mock_model)

    audio = np.zeros(16000, dtype=np.float32)  # 1 second of silence
    text, confidence = stt.transcribe(audio, sample_rate=16000)

    assert isinstance(text, str)
    assert isinstance(confidence, float)
    assert 0.0 <= confidence <= 1.0

def test_transcribe_strips_whitespace(mocker):
    mock_segment = mocker.MagicMock()
    mock_segment.text = "  open gmail  "
    mock_info = mocker.MagicMock()
    mock_info.language_probability = 0.9
    mock_model = mocker.MagicMock()
    mock_model.transcribe.return_value = ([mock_segment], mock_info)
    mocker.patch("stt._model", mock_model)
    mocker.patch("stt.load_model", return_value=mock_model)

    audio = np.zeros(16000, dtype=np.float32)
    text, _ = stt.transcribe(audio)
    assert text == "open gmail"