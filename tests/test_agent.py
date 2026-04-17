import threading
import queue
import pytest
import agent


@pytest.fixture(autouse=True)
def no_scale(mocker):
    """Patch helpers that require real image bytes or real timing."""
    mocker.patch("agent._compute_scale", return_value=(1.0, 1.0, 0, 0, 1280, 800))
    mocker.patch("agent._wait_for_action", return_value=False)  # not cancelled, skip sleep
    mocker.patch("agent._screenshots_differ", return_value=True)  # assume actions work
    # UIA snapshot and annotation require a real desktop + real JPEG bytes — skip.
    mocker.patch("agent._safe_snapshot", return_value=[])
    mocker.patch("agent._safe_annotate", side_effect=lambda s, *a, **kw: s)
    # Distinct hashes per call so the cached-vision skip never triggers in tests
    _counter = {"n": 0}
    def _fake_hash(_b):
        _counter["n"] += 1
        return f"hash-{_counter['n']}"
    mocker.patch("agent._screenshot_hash", side_effect=_fake_hash)
    mocker.patch("agent.tts.speak_nonblocking")


def make_queues():
    waiting = threading.Event()
    confirm_q = queue.Queue()
    return waiting, confirm_q


def test_run_goal_completes_on_done(mocker):
    mocker.patch("agent.screen.capture", return_value=b"img")
    mocker.patch("agent.vision.get_next_action", return_value={
        "action": "done", "message": "All done"
    })
    speak = mocker.patch("agent.tts.speak")
    waiting, confirm_q = make_queues()

    agent.run_goal("open gmail", waiting, confirm_q)

    speak.assert_called_with("All done")


def test_run_goal_executes_action_then_done(mocker):
    actions = [
        {"action": "click", "x": 10, "y": 10, "narration": "Clicking"},
        {"action": "done", "message": "Done"},
    ]
    mocker.patch("agent.screen.capture", return_value=b"img")
    mocker.patch("agent.vision.get_next_action", side_effect=actions)
    mocker.patch("agent.tts.speak")
    mock_execute = mocker.patch("agent.executor.execute")
    waiting, confirm_q = make_queues()

    agent.run_goal("click something", waiting, confirm_q)

    # With scale=1.0 and offset=0, mapped coords should equal input coords.
    mock_execute.assert_called_once_with({**actions[0], "x": 10, "y": 10})


def test_run_goal_retries_on_vision_error(mocker):
    call_count = {"n": 0}

    def flaky_vision(*args):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise Exception("API error")
        return {"action": "done", "message": "Done"}

    mocker.patch("agent.screen.capture", return_value=b"img")
    mocker.patch("agent.vision.get_next_action", side_effect=flaky_vision)
    mocker.patch("agent.tts.speak")
    mocker.patch("agent.executor.execute")
    waiting, confirm_q = make_queues()

    agent.run_goal("do something", waiting, confirm_q)
    assert call_count["n"] == 3


def test_run_goal_stops_after_max_retries(mocker):
    mocker.patch("agent.screen.capture", return_value=b"img")
    mocker.patch("agent.vision.get_next_action", side_effect=Exception("always fails"))
    speak = mocker.patch("agent.tts.speak")
    waiting, confirm_q = make_queues()

    agent.run_goal("do something", waiting, confirm_q)

    error_calls = [c for c in speak.call_args_list if "problem" in str(c).lower() or "trouble" in str(c).lower()]
    assert len(error_calls) > 0


def test_major_action_waits_for_confirmation(mocker):
    actions = [
        {"action": "click", "x": 5, "y": 5, "narration": "Clicking send button"},
        {"action": "done", "message": "Sent"},
    ]
    mocker.patch("agent.screen.capture", return_value=b"img")
    mocker.patch("agent.vision.get_next_action", side_effect=actions)
    mocker.patch("agent.tts.speak")
    mocker.patch("agent.executor.execute")
    waiting, confirm_q = make_queues()
    confirm_q.put(True)  # Pre-fill confirmation

    agent.run_goal("send email", waiting, confirm_q)

    assert waiting.is_set() is False  # Should be cleared after confirmation


def test_click_coords_scaled_and_offset(mocker):
    """Clicks must be transformed from screenshot-space to physical-screen-space
    (scale + monitor offset) before reaching the executor."""
    mocker.stopall()  # drop the autouse fixture so we can control the return values
    mocker.patch("agent._compute_scale", return_value=(2.0, 2.0, 100, 50, 1280, 800))
    mocker.patch("agent._wait_for_action", return_value=False)
    mocker.patch("agent._screenshots_differ", return_value=True)
    mocker.patch("agent._safe_snapshot", return_value=[])
    mocker.patch("agent._safe_annotate", side_effect=lambda s, *a, **kw: s)
    _c = {"n": 0}
    def _h(_): _c["n"] += 1; return f"h-{_c['n']}"
    mocker.patch("agent._screenshot_hash", side_effect=_h)
    mocker.patch("agent.tts.speak")
    mocker.patch("agent.tts.speak_nonblocking")

    actions = [
        {"action": "click", "x": 50, "y": 60, "narration": "Clicking"},
        {"action": "done", "message": "Done"},
    ]
    mocker.patch("agent.screen.capture", return_value=b"img")
    mocker.patch("agent.vision.get_next_action", side_effect=actions)
    mock_execute = mocker.patch("agent.executor.execute")

    waiting, confirm_q = make_queues()
    agent.run_goal("click something", waiting, confirm_q)

    # 50*2.0 + 100 = 200, 60*2.0 + 50 = 170
    mock_execute.assert_called_once_with({**actions[0], "x": 200, "y": 170})


def test_element_click_resolves_to_screen_coords(mocker):
    """When the model returns {click, element: N}, agent must look up the element
    in the UIA snapshot and fire the click at its screen-space center — NOT
    scale it again (UIA already returns screen coords)."""
    from ui_tree import Element
    el = Element(id=3, name="Search Amazon", control_type="EditControl",
                 left=500, top=400, right=700, bottom=440)
    mocker.patch("agent._safe_snapshot", return_value=[el])

    actions = [
        {"action": "click", "element": 3, "narration": "Clicking search"},
        {"action": "done", "message": "Done"},
    ]
    mocker.patch("agent.screen.capture", return_value=b"img")
    mocker.patch("agent.vision.get_next_action", side_effect=actions)
    mocker.patch("agent.tts.speak")
    mock_execute = mocker.patch("agent.executor.execute")

    waiting, confirm_q = make_queues()
    agent.run_goal("search amazon for olive oil", waiting, confirm_q)

    # center = ((500+700)//2, (400+440)//2) = (600, 420) in screen space.
    # NO additional scaling should be applied.
    mock_execute.assert_called_once()
    fired = mock_execute.call_args[0][0]
    assert fired["action"] == "click"
    assert fired["x"] == 600
    assert fired["y"] == 420
    assert fired["element"] == 3


def test_failed_element_click_is_blacklisted_next_frame(mocker):
    """If clicking element X produces no screen change, the next vision call
    must NOT see element X in its list — otherwise the model loops forever."""
    from ui_tree import Element
    el_a = Element(id=1, name="Address Bar", control_type="EditControl",
                   left=800, top=60, right=1000, bottom=100)
    el_b = Element(id=2, name="Submit", control_type="ButtonControl",
                   left=200, top=200, right=280, bottom=240)

    mocker.patch("agent._safe_snapshot", return_value=[el_a, el_b])
    # First click: no effect. Second: done.
    mocker.stopall()
    mocker.patch("agent._compute_scale", return_value=(1.0, 1.0, 0, 0, 1280, 800))
    mocker.patch("agent._wait_for_action", return_value=False)
    mocker.patch("agent._safe_annotate", side_effect=lambda s, *a, **kw: s)
    _c = {"n": 0}
    def _h(_): _c["n"] += 1; return f"h-{_c['n']}"
    mocker.patch("agent._screenshot_hash", side_effect=_h)
    mocker.patch("agent.tts.speak")
    mocker.patch("agent.tts.speak_nonblocking")
    # First frame returns snapshot with both; second frame same snapshot.
    mocker.patch("agent._safe_snapshot", return_value=[el_a, el_b])
    # First click has no effect → blacklisted; second call is done.
    mocker.patch("agent._screenshots_differ", side_effect=[False, True])

    actions = [
        {"action": "click", "element": 1, "narration": "Clicking address bar"},
        {"action": "done", "message": "done"},
    ]
    captured_elements: list = []
    def fake_vision(shot, goal, history, elements=None):
        captured_elements.append(list(elements or []))
        return actions.pop(0)

    mocker.patch("agent.screen.capture", return_value=b"img")
    mocker.patch("agent.vision.get_next_action", side_effect=fake_vision)
    mocker.patch("agent.executor.execute")

    waiting, confirm_q = make_queues()
    agent.run_goal("do something", waiting, confirm_q)

    # First vision call saw both elements; second saw only the survivor.
    assert len(captured_elements) == 2
    first_names = [e.name for e in captured_elements[0]]
    second_names = [e.name for e in captured_elements[1]]
    assert "Address Bar" in first_names
    assert "Submit" in first_names
    assert "Address Bar" not in second_names
    assert "Submit" in second_names


def test_unknown_element_id_is_skipped(mocker):
    """If the model hallucinates an element ID not in the snapshot, skip it and
    continue instead of crashing or clicking somewhere random."""
    actions = [
        {"action": "click", "element": 99, "narration": "Clicking ghost"},
        {"action": "done", "message": "Done"},
    ]
    mocker.patch("agent.screen.capture", return_value=b"img")
    mocker.patch("agent.vision.get_next_action", side_effect=actions)
    mocker.patch("agent.tts.speak")
    mock_execute = mocker.patch("agent.executor.execute")

    waiting, confirm_q = make_queues()
    agent.run_goal("do stuff", waiting, confirm_q)

    # No click fired — the ghost element was skipped, then done.
    mock_execute.assert_not_called()


def test_major_action_cancels_on_no(mocker):
    actions = [
        {"action": "click", "x": 5, "y": 5, "narration": "Clicking delete button"},
    ]
    mocker.patch("agent.screen.capture", return_value=b"img")
    mocker.patch("agent.vision.get_next_action", side_effect=actions)
    speak = mocker.patch("agent.tts.speak")
    mock_execute = mocker.patch("agent.executor.execute")
    waiting, confirm_q = make_queues()
    confirm_q.put(False)  # User says no

    agent.run_goal("delete file", waiting, confirm_q)

    mock_execute.assert_not_called()
