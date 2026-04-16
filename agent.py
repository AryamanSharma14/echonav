import hashlib
import io
import time
import threading
import queue
import pyautogui
from PIL import Image
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

    # Compute coordinate scale once: screenshot pixels → pyautogui logical pixels
    _probe = screen.capture()
    scale_x, scale_y, ss_w, ss_h = _compute_scale(_probe)
    # Use the probe as the first screenshot so we don't double-capture
    screenshot = _probe

    for _step in range(config.MAX_STEPS):
        if _cancel_event.is_set():
            tts.speak("Task cancelled.")
            return

        action = _get_action_with_retries(screenshot, goal, history)
        if action is None:
            return  # Error already spoken

        # Validate and normalise click coordinates before anything else
        action = _validate_action(action, ss_w, ss_h)
        if action is None:
            history.append({"action": "click", "narration": "skipped — invalid coordinates", "had_effect": False})
            screenshot = screen.capture()
            continue

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

        executor.execute(action, scale_x=scale_x, scale_y=scale_y)

        # Wait for the UI to respond, then capture the next screenshot
        _wait_for_action(action)
        next_screenshot = screen.capture()
        had_effect = _screenshots_differ(screenshot, next_screenshot)
        if not had_effect:
            print(f"[agent] step {_step + 1}: no screen change detected after action")

        history.append({**action, "had_effect": had_effect})
        screenshot = next_screenshot

    tts.speak("I wasn't able to complete that. Would you like me to try a different approach?")


def _compute_scale(screenshot_bytes: bytes) -> tuple:
    """Return (scale_x, scale_y, ss_w, ss_h) to map screenshot pixel coords → pyautogui logical coords."""
    img = Image.open(io.BytesIO(screenshot_bytes))
    screen_w, screen_h = pyautogui.size()
    scale_x = screen_w / img.width
    scale_y = screen_h / img.height
    print(f"[agent] coord scale: {img.width}x{img.height} screenshot → {screen_w}x{screen_h} logical ({scale_x:.2f}x)")
    return scale_x, scale_y, img.width, img.height


def _validate_action(action: dict, ss_w: int, ss_h: int):
    """
    Validate and fix click coordinates from the AI.

    The AI occasionally returns:
    - Normalised ratios (e.g. 0.308, 0.185) instead of pixel coords
    - Out-of-bounds coords (e.g. negative, or larger than the screenshot)

    Returns a corrected action dict, or None if the action should be skipped.
    """
    if action.get("action") != "click":
        return action

    x, y = action.get("x", 0), action.get("y", 0)

    # Detect normalised coords: both values between 0.0 and 1.0
    if isinstance(x, float) and isinstance(y, float) and 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
        x = int(x * ss_w)
        y = int(y * ss_h)
        print(f"[agent] normalised coords detected → converted to pixel ({x}, {y})")
        return {**action, "x": x, "y": y}

    x, y = int(x), int(y)

    # Bounds check
    if x < 0 or y < 0 or x > ss_w or y > ss_h:
        print(f"[agent] out-of-bounds coords ({x}, {y}) for {ss_w}x{ss_h} screenshot — skipping")
        return None

    return {**action, "x": x, "y": y}


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


def _wait_for_action(action: dict) -> None:
    """Wait an appropriate amount of time after an action for the UI to respond."""
    act = action.get("action")
    if act == "wait":
        pass  # executor already slept 1.5s
    elif act == "key" and action.get("key") in ("enter", "win"):
        time.sleep(1.5)  # launching apps / submitting forms takes longer
    else:
        time.sleep(0.6)  # standard UI response time


def _screenshot_hash(screenshot_bytes: bytes) -> str:
    """Downsample to 16×16 grayscale and MD5 — fast perceptual change detector."""
    img = Image.open(io.BytesIO(screenshot_bytes))
    small = img.resize((16, 16)).convert("L")
    return hashlib.md5(small.tobytes()).hexdigest()


def _screenshots_differ(before: bytes, after: bytes) -> bool:
    """Return True if the screen visibly changed between the two captures."""
    return _screenshot_hash(before) != _screenshot_hash(after)
