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

def test_parse_response_extracts_from_preamble_and_suffix():
    raw = 'Sure! Here is the JSON:\n{"action": "click", "element": 3, "narration": "Clicking"}\nHope this helps!'
    result = vision._parse_response(raw)
    assert result["action"] == "click"
    assert result["element"] == 3

def test_parse_response_empty_raises():
    with pytest.raises(ValueError):
        vision._parse_response("")
    with pytest.raises(ValueError):
        vision._parse_response("   \n  ")

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


def test_local_heuristic_website_navigation():
    action0 = vision._local_heuristic_action("open amazon.com", None, [])
    assert action0["action"] == "key"
    assert action0["key"] == "ctrl+l"

    action1 = vision._local_heuristic_action("open amazon.com", None, [action0])
    assert action1["action"] == "type"
    assert "amazon.com" in action1["text"]


def test_local_heuristic_site_search():
    action0 = vision._local_heuristic_action("search youtube for laya", None, [])
    assert action0["action"] == "key"
    assert action0["key"] == "ctrl+l"

    action1 = vision._local_heuristic_action("search youtube for laya", None, [action0])
    assert action1["action"] == "type"
    assert "youtube.com/results?search_query=laya" in action1["text"]


def test_local_heuristic_app_launch():
    action0 = vision._local_heuristic_action("open notepad", None, [])
    assert action0["action"] == "key"
    assert action0["key"] == "win"

    action1 = vision._local_heuristic_action("open notepad", None, [action0])
    assert action1["action"] == "type"
    assert action1["text"] == "notepad"


def test_local_heuristic_element_click():
    from ui_tree import Element
    el = Element(id=4, name="Submit Order", control_type="ButtonControl", left=10, top=10, right=50, bottom=50)
    action = vision._local_heuristic_action("click submit", [el], [])
    assert action["action"] == "click"
    assert action["element"] == 4


def test_local_heuristic_element_click_with_stop_words():
    from ui_tree import Element
    search_box = Element(id=7, name="Search", control_type="EditControl", left=100, top=20, right=300, bottom=40)
    action = vision._local_heuristic_action("click on the search button", [search_box], [])
    assert action["action"] == "click"
    assert action["element"] == 7


def test_get_next_action_fallback_to_heuristic(mocker):
    mocker.patch("vision._groq_action", side_effect=Exception("API connection refused"))
    mocker.patch("vision._gemini_action", side_effect=Exception("Quota exceeded"))
    mocker.patch("vision.config.MODEL_PROVIDER", "groq")
    mocker.patch("vision.config.GEMINI_API_KEY", "mock-key")

    action = vision.get_next_action(b"fake_image", "open amazon", [])
    assert action["action"] == "key"
    assert action["key"] == "ctrl+l"


def test_get_next_action_ollama(mocker):
    fake_action = {"action": "click", "element": 2, "narration": "Clicking button locally"}
    mocker.patch("vision._ollama_action", return_value=fake_action)
    mocker.patch("vision.config.MODEL_PROVIDER", "ollama")

    result = vision.get_next_action(b"fake_image", "click search", [])
    assert result == fake_action
