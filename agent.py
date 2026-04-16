import threading
import queue
import screen
import tts
import vision
import executor
import config

_cancel_event = threading.Event()


def cancel() -> None:
    """Signal the running agent loop to stop at the next step."""
    _cancel_event.set()


def run_goal(
    goal: str,
    waiting_for_confirmation: threading.Event,
    confirmation_queue: queue.Queue,
) -> None:
    """
    Run the agent loop for one goal.
    Loops up to MAX_STEPS times: capture → AI → narrate → confirm (if major) → execute.
    """
    _cancel_event.clear()
    history: list = []
    repeat_count = 0
    last_click_xy = None

    for _step in range(config.MAX_STEPS):
        if _cancel_event.is_set():
            tts.speak("Task cancelled.")
            return

        screenshot = screen.capture()

        action = _get_action_with_retries(screenshot, goal, history)
        if action is None:
            return  # Error already spoken

        print(f"[agent] step {_step + 1}: {action}")

        if action["action"] == "done":
            tts.speak(action.get("message", "Task complete."))
            return

        # Loop detection: fuzzy for clicks (within 20px), exact for other actions
        if action.get("action") == "click":
            x, y = action.get("x", 0), action.get("y", 0)
            if last_click_xy and abs(x - last_click_xy[0]) < 20 and abs(y - last_click_xy[1]) < 20:
                repeat_count += 1
                if repeat_count >= 3:
                    tts.speak("I seem to be stuck clicking the same spot. Please try rephrasing.")
                    return
            else:
                repeat_count = 0
                last_click_xy = (x, y)
        else:
            last_click_xy = None

        narration = action.get("narration", "Taking action.")

        if _is_major_action(action):
            tts.speak(f"{narration}. Say yes to confirm, or no to cancel.")
            waiting_for_confirmation.set()
            try:
                confirmed = confirmation_queue.get(timeout=15)
            except queue.Empty:
                confirmed = False
            finally:
                waiting_for_confirmation.clear()

            if not confirmed:
                tts.speak("Okay, what would you like to do instead?")
                return
        else:
            tts.speak(narration)

        executor.execute(action)
        history.append(action)

    tts.speak("I wasn't able to complete that. Would you like me to try a different approach?")


def _get_action_with_retries(screenshot: bytes, goal: str, history: list):
    for attempt in range(config.MAX_RETRIES):
        try:
            return vision.get_next_action(screenshot, goal, history)
        except Exception as e:
            print(f"[agent] vision error (attempt {attempt + 1}): {e}")
            if attempt == config.MAX_RETRIES - 1:
                tts.speak("I ran into a technical problem. Please try again.")
                return None
            tts.speak("Having trouble, retrying.")
    return None


def _is_major_action(action: dict) -> bool:
    narration = action.get("narration", "").lower()
    return any(kw in narration for kw in config.MAJOR_ACTION_KEYWORDS)
