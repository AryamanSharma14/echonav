import pytest
import vision

def test_parse_response_valid_click():
    raw = '{"action": "click", "x": 100, "y": 200, "narration": "Clicking button"}'
    result = vision._parse_response(raw)
    assert result["action"] == "click"
    assert result["x"] == 100
    assert result["y"] == 200

def test_parse_response_strips_markdown():
    raw = '''```json
{"action": "done", "message": "Done"}
```'''
    result = vision._parse_response(raw)
    assert result["action"] == "done"

def test_parse_response_strips_plain_code_block():
    raw = '''```
{"action": "type", "text": "hello", "narration": "Typing"}
```'''
    result = vision._parse_response(raw)
    assert result["action"] == "type"
    assert result["text"] == "hello"

def test_build_user_message_includes_goal():
    msg = vision._build_user_message("open gmail", [])
    assert "open gmail" in msg

def test_build_user_message_caps_history_at_10():
    history = [{"action": "click", "narration": f"Action {i}"} for i in range(15)]
    msg = vision._build_user_message("goal", history)
    # Only last 10 should appear
    assert "Action 4" not in msg
    assert "Action 14" in msg

def test_get_next_action_groq(mocker):
    fake_action = {"action": "click", "x": 50, "y": 50, "narration": "Clicking"}
    mocker.patch("vision._groq_action", return_value=fake_action)
    mocker.patch("vision.config.MODEL_PROVIDER", "groq")
    result = vision.get_next_action(b"fake_image", "open gmail", [])
    assert result == fake_action