import threading
import queue
import screen
import tts
import vision
import executor
import config


def run_goal(
    goal: str,
    waiting_for_confirmation: threading.Event,
    confirmation_queue: queue.Queue,
) -> None:
    """
    Run the agent loop for one goal.
    Loops up to MAX_STEPS times: capture → AI → narrate → confirm (if major) → execute.
    """
    history: list = []

    for _step in range(config.MAX_STEPS):
        screenshot = screen.capture()

        action = _get_action_with_retries(screenshot, goal, history)
        if action is None:
            return  # Error already spoken

        print(f"[agent] step {_step + 1}: {action}")

        if action["action"] == "done":
            tts.speak(action.get("message", "Task complete."))
            return

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
