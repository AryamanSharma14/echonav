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


def test_build_user_message_lists_elements():
    """When UIA elements are supplied, the prompt must list them as numbered lines
    so the model can click by ID."""
    from ui_tree import Element
    els = [
        Element(id=1, name="Search Amazon", control_type="EditControl",
                left=0, top=0, right=100, bottom=30),
        Element(id=2, name="", control_type="ButtonControl",
                left=0, top=0, right=50, bottom=50),
    ]
    msg = vision._build_user_message("search amazon", [], elements=els)
    assert "[1] Edit: Search Amazon" in msg
    assert "[2] Button" in msg
    assert "click these by id" in msg.lower()


def test_build_user_message_no_elements_falls_back():
    msg = vision._build_user_message("goal", [], elements=[])
    assert "none available" in msg.lower()
    assert "keyboard" in msg.lower()


def test_build_user_message_shows_valid_id_range():
    from ui_tree import Element
    els = [
        Element(id=i, name=f"btn{i}", control_type="ButtonControl",
                left=0, top=0, right=10, bottom=10)
        for i in range(1, 6)
    ]
    msg = vision._build_user_message("goal", [], elements=els)
    assert "1..5" in msg


def test_parse_response_click_by_element():
    raw = '{"action":"click","element":7,"narration":"Clicking search"}'
    result = vision._parse_response(raw)
    assert result["action"] == "click"
    assert result["element"] == 7