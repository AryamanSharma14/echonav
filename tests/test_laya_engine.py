import pytest
from laya_engine import LayaEngine, IntentResult, SafetyResult


def test_instant_command_stop():
    engine = LayaEngine(enable_model=False)
    res = engine.classify_intent("stop right now")
    assert res.category == "instant_command"
    assert res.command_name == "stop"
    assert res.source == "exact"
    assert not res.requires_confirmation


def test_instant_command_read_page():
    engine = LayaEngine(enable_model=False)
    res = engine.classify_intent("read the page please")
    assert res.category == "instant_command"
    assert res.command_name == "read_page"


def test_instant_command_go_back():
    engine = LayaEngine(enable_model=False)
    res = engine.classify_intent("please go back")
    assert res.category == "instant_command"
    assert res.command_name == "go_back"


def test_browser_intent_classification():
    engine = LayaEngine(enable_model=False)
    res = engine.classify_intent("search youtube for relaxing piano music")
    assert res.category == "browser_navigate"


def test_desktop_intent_classification():
    engine = LayaEngine(enable_model=False)
    res = engine.classify_intent("open notepad")
    assert res.category == "desktop_action"


def test_inquire_intent_classification():
    engine = LayaEngine(enable_model=False)
    res = engine.classify_intent("what is on the screen right now")
    assert res.category == "inquire"


def test_safety_check_destructive():
    engine = LayaEngine(enable_model=False)
    action = {"action": "click", "narration": "Clicking the send button on email"}
    safety = engine.evaluate_safety(action)
    assert safety.is_destructive is True
    assert safety.requires_confirmation is True
    assert safety.trigger_keyword == "send"


def test_safety_check_safe():
    engine = LayaEngine(enable_model=False)
    action = {"action": "scroll", "narration": "Scrolling down page"}
    safety = engine.evaluate_safety(action)
    assert safety.is_destructive is False
    assert safety.requires_confirmation is False


def test_laya_mocked_prediction(mocker):
    engine = LayaEngine(enable_model=True)
    fake_router = mocker.MagicMock()
    fake_router.predict.return_value = {
        "answers": {
            "intent": {"choice": "browser_navigate"},
            "is_destructive": {"noul": 0.12},
        }
    }
    mocker.patch.object(engine, "_get_router", return_value=fake_router)
    res = engine.classify_intent("find flights to London")
    assert res.category == "browser_navigate"
    assert res.source == "laya"
    assert not res.is_destructive
