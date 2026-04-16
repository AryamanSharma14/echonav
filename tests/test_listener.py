import numpy as np
from listener import Listener

def test_listener_can_be_created():
    received = []
    listener = Listener(on_utterance=lambda audio, sr: received.append((audio, sr)))
    assert listener is not None

def test_listener_initial_state_not_recording():
    listener = Listener(on_utterance=lambda a, s: None)
    assert listener._recording is False

def test_audio_callback_appends_chunks_when_recording():
    listener = Listener(on_utterance=lambda a, s: None)
    listener._recording = True
    fake_chunk = np.ones((1024, 1), dtype=np.float32)
    listener._audio_callback(fake_chunk, 1024, None, None)
    assert len(listener._audio_chunks) == 1
    assert np.array_equal(listener._audio_chunks[0], fake_chunk[:, 0])

def test_audio_callback_ignores_chunks_when_not_recording():
    listener = Listener(on_utterance=lambda a, s: None)
    listener._recording = False
    fake_chunk = np.ones((1024, 1), dtype=np.float32)
    listener._audio_callback(fake_chunk, 1024, None, None)
    assert len(listener._audio_chunks) == 0
