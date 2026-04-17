import tts


def test_speak_does_not_raise(mocker):
    mocker.patch.object(tts._q, "put")
    mocker.patch("threading.Event.wait", return_value=None)
    tts.speak("Hello world")   # Should not raise


def test_speak_last_replays_last_utterance(mocker):
    put = mocker.patch.object(tts._q, "put")
    mocker.patch("threading.Event.wait", return_value=None)
    tts.speak("First message")
    tts.speak("Second message")
    tts.speak_last()
    # Last enqueued text should be "Second message"
    last_args, _ = put.call_args_list[-1]
    assert last_args[0][0] == "Second message"


def test_set_rate_clamps_minimum():
    tts.set_rate(10)
    assert tts._rate >= 80


def test_set_rate_clamps_maximum():
    tts.set_rate(999)
    assert tts._rate <= 300


def test_speak_nonblocking_enqueues_without_event(mocker):
    put = mocker.patch.object(tts._q, "put")
    tts.speak_nonblocking("Working on it")
    (args, _) = put.call_args
    text, done = args[0]
    assert text == "Working on it"
    assert done is None
