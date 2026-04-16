import threading
import numpy as np
import pytest
import main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_audio(seconds: float = 0.5) -> np.ndarray:
    """Fake mono audio array at 16 kHz."""
    return np.zeros(int(16000 * seconds), dtype="float32")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_handle_utterance_dispatches_to_agent(mocker):
    """Normal goal text → agent.run_goal called, not check_command."""
    mocker.patch("main.stt.transcribe", return_value=("open gmail", 0.9))
    mocker.patch("main.commands.check_command", return_value=False)
    mock_run_goal = mocker.patch("main.agent.run_goal")
    mocker.patch("main.tts.speak")

    app = main.App()
    app._handle_utterance(make_audio(), 16000)

    mock_run_goal.assert_called_once()
    call_args = mock_run_goal.call_args[0]
    assert call_args[0] == "open gmail"


def test_handle_utterance_dispatches_to_commands(mocker):
    """Special command text → check_command returns True, agent NOT called."""
    mocker.patch("main.stt.transcribe", return_value=("go back", 0.9))
    mocker.patch("main.commands.check_command", return_value=True)
    mock_run_goal = mocker.patch("main.agent.run_goal")

    app = main.App()
    app._handle_utterance(make_audio(), 16000)

    mock_run_goal.assert_not_called()


def test_handle_utterance_low_confidence_asks_to_repeat(mocker):
    """Low confidence → tts.speak called asking user to repeat, agent NOT called."""
    mocker.patch("main.stt.transcribe", return_value=("mumble", 0.3))
    mock_run_goal = mocker.patch("main.agent.run_goal")
    speak = mocker.patch("main.tts.speak")

    app = main.App()
    app._handle_utterance(make_audio(), 16000)

    mock_run_goal.assert_not_called()
    spoken = " ".join(str(c) for c in speak.call_args_list).lower()
    assert "repeat" in spoken or "again" in spoken or "catch" in spoken


def test_handle_utterance_yes_confirms_when_waiting(mocker):
    """'yes' while waiting_for_confirmation → True put on confirmation_queue."""
    mocker.patch("main.stt.transcribe", return_value=("yes", 0.95))
    mocker.patch("main.agent.run_goal")

    app = main.App()
    app._waiting_for_confirmation.set()

    app._handle_utterance(make_audio(), 16000)

    assert app._confirmation_queue.get_nowait() is True


def test_handle_utterance_no_cancels_when_waiting(mocker):
    """'no' while waiting_for_confirmation → False put on confirmation_queue."""
    mocker.patch("main.stt.transcribe", return_value=("no", 0.95))
    mocker.patch("main.agent.run_goal")

    app = main.App()
    app._waiting_for_confirmation.set()

    app._handle_utterance(make_audio(), 16000)

    assert app._confirmation_queue.get_nowait() is False


def test_handle_utterance_stop_command_does_not_raise(mocker):
    """StopCommand raised by commands.check_command is caught cleanly."""
    mocker.patch("main.stt.transcribe", return_value=("stop", 0.9))
    mocker.patch("main.commands.check_command", side_effect=main.commands.StopCommand)
    mock_run_goal = mocker.patch("main.agent.run_goal")
    mocker.patch("main.tts.speak")

    app = main.App()
    app._handle_utterance(make_audio(), 16000)  # must not raise

    mock_run_goal.assert_not_called()


def test_handle_utterance_agent_runs_in_thread(mocker):
    """agent.run_goal must be called in a background thread (non-blocking)."""
    ready = threading.Event()
    released = threading.Event()

    def slow_goal(*args, **kwargs):
        ready.set()
        released.wait(timeout=2)

    mocker.patch("main.stt.transcribe", return_value=("open gmail", 0.9))
    mocker.patch("main.commands.check_command", return_value=False)
    mocker.patch("main.agent.run_goal", side_effect=slow_goal)
    mocker.patch("main.tts.speak")

    app = main.App()
    app._handle_utterance(make_audio(), 16000)

    # _handle_utterance should return before slow_goal finishes
    assert ready.wait(timeout=2), "agent.run_goal was never called"
    released.set()
