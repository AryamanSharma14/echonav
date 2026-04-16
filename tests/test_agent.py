import threading
import queue
import pytest
import agent


@pytest.fixture(autouse=True)
def no_scale(mocker):
    """Patch helpers that require real image bytes or real timing."""
    mocker.patch("agent._compute_scale", return_value=(1.0, 1.0, 1280, 800))
    mocker.patch("agent._wait_for_action", return_value=False)  # not cancelled, skip sleep
    mocker.patch("agent._screenshots_differ", return_value=True)  # assume actions work


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

    mock_execute.assert_called_once_with(actions[0], scale_x=1.0, scale_y=1.0)


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
