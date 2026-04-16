import tts

def test_speak_does_not_raise(mocker):
    mocker.patch("tts._speak_edge", return_value=None)
    tts.speak("Hello world")  # Should not raise

def test_speak_last_replays_last_utterance(mocker):
    mock_speak = mocker.patch("tts._speak_edge", return_value=None)
    tts.speak("First message")
    tts.speak("Second message")
    tts.speak_last()
    # Last call to _speak_edge should repeat "Second message"
    assert mock_speak.call_args_list[-1][0][0] == "Second message"

def test_set_rate_clamps_minimum(mocker):
    mocker.patch("tts._speak_edge", return_value=None)
    tts.set_rate(10)  # Below minimum
    assert tts._rate >= 80

def test_set_rate_clamps_maximum(mocker):
    mocker.patch("tts._speak_edge", return_value=None)
    tts.set_rate(999)  # Above maximum
    assert tts._rate <= 300
