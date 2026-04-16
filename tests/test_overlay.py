import queue
import pytest
import overlay as ov


def test_update_puts_state_and_text_on_queue():
    o = ov.Overlay()
    o.update("listening", "Listening...")
    state, text = o._queue.get_nowait()
    assert state == "listening"
    assert text == "Listening..."


def test_update_is_callable_from_any_thread(mocker):
    import threading
    o = ov.Overlay()
    errors = []

    def worker():
        try:
            o.update("acting", "Clicking compose")
        except Exception as e:
            errors.append(e)

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    assert not errors
    assert o._queue.qsize() == 1


def test_update_queues_multiple_states_in_order():
    o = ov.Overlay()
    o.update("listening", "")
    o.update("thinking", "")
    o.update("acting", "Clicking Gmail")
    o.update("done", "")

    states = []
    for _ in range(4):
        state, _ = o._queue.get_nowait()
        states.append(state)

    assert states == ["listening", "thinking", "acting", "done"]


def test_all_valid_states_have_color():
    for state in ["idle", "listening", "thinking", "acting", "confirming", "done", "error"]:
        assert state in ov._STATE_COLORS


def test_all_valid_states_have_icon():
    for state in ["idle", "listening", "thinking", "acting", "confirming", "done", "error"]:
        assert state in ov._STATE_ICONS
