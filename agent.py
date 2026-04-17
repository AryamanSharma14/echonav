import hashlib
import io
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
    last_key = None
    key_repeat_count = 0
    failed_clicks = 0
    last_vision_hash: str | None = None
    consecutive_waits = 0

    _probe = screen.capture()
    scale_x, scale_y, ss_w, ss_h = _compute_scale(_probe)
    screenshot = _probe

    for _step in range(config.MAX_STEPS):
        if _cancel_event.is_set():
            tts.speak("Task cancelled.")
            return

        # Skip a vision call when the screen hasn't changed since last analysis.
        # Wait up to 3 s for the UI to settle before burning another API call.
        if last_vision_hash is not None:
            current_hash = _screenshot_hash(screenshot)
            if current_hash == last_vision_hash:
                for _ in range(2):
                    if _cancel_event.wait(timeout=1.5):
                        return
                    screenshot = screen.capture()
                    if _screenshot_hash(screenshot) != last_vision_hash:
                        break

        action = _get_action_with_retries(screenshot, goal, history)
        last_vision_hash = _screenshot_hash(screenshot)
        if action is None:
            return

        action = _validate_action(action, ss_w, ss_h)
        if action is None:
            history.append({"action": "click", "narration": "skipped — invalid coordinates", "had_effect": False})
            screenshot = screen.capture()
            continue

        print(f"[agent] step {_step + 1}: {action}")

        if action["action"] == "done":
            tts.speak(action.get("message", "Task complete."))
            return

        # Loop detection: fuzzy for clicks (within 20 px), exact for repeated keys
        if action.get("action") == "click":
            x, y = action.get("x", 0), action.get("y", 0)
            if last_click_xy and abs(x - last_click_xy[0]) < 20 and abs(y - last_click_xy[1]) < 20:
                repeat_count += 1
                if repeat_count >= 3:
                    tts.speak("I'm stuck. What would you like me to do?")
                    return
            else:
                repeat_count = 0
                last_click_xy = (x, y)
            last_key = None
            key_repeat_count = 0
        elif action.get("action") == "key":
            key = action.get("key", "")
            if key == last_key:
                key_repeat_count += 1
                if key_repeat_count >= 3:
                    tts.speak("I'm stuck. What would you like me to do?")
                    return
            else:
                last_key = key
                key_repeat_count = 0
            last_click_xy = None
        else:
            last_click_xy = None
            last_key = None
            key_repeat_count = 0

        narration = action.get("narration", "Taking action.")

        # Cap consecutive waits — if the AI keeps waiting, force it to proceed.
        if action.get("action") == "wait":
            consecutive_waits += 1
            if consecutive_waits >= 2:
                tts.speak_nonblocking("Looks like it loaded, moving on.")
                history.append({
                    "action": "wait",
                    "narration": (
                        "SYSTEM OVERRIDE: page is considered loaded. "
                        "DO NOT return 'wait' again. Immediately proceed with the next step of the goal."
                    ),
                    "had_effect": True,
                })
                screenshot = screen.capture()
                last_vision_hash = None
                consecutive_waits = 9999
                continue
            if consecutive_waits == 1:
                tts.speak_nonblocking(narration)
            executor.execute(action, scale_x=scale_x, scale_y=scale_y)
            if _wait_for_action(action):
                return
            screenshot = screen.capture()
            history.append({**action, "had_effect": True})
            continue
        else:
            consecutive_waits = 0

        if _is_major_action(action):
            # Confirmation must be heard before execution — keep blocking TTS.
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

            if _cancel_event.is_set():
                return
            executor.execute(action, scale_x=scale_x, scale_y=scale_y)
        else:
            # Speak while executing — saves ~0.5–1 s per step.
            tts.speak_nonblocking(narration)
            if _cancel_event.is_set():
                return
            executor.execute(action, scale_x=scale_x, scale_y=scale_y)

        if _wait_for_action(action):
            return

        next_screenshot = screen.capture()

        # Key and wait actions don't always change the 16×16 perceptual hash —
        # trust them so we don't falsely retry.
        if action.get("action") in ("key", "wait"):
            had_effect = True
            failed_clicks = 0
        else:
            had_effect = _screenshots_differ(screenshot, next_screenshot)
            if not had_effect:
                print(f"[agent] step {_step + 1}: no screen change detected after action")
                if action.get("action") == "click":
                    failed_clicks += 1
                    if failed_clicks >= 3:
                        tts.speak("I can't interact with that element. Please try rephrasing.")
                        return
            else:
                failed_clicks = 0

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
    """Validate and fix click coordinates from the AI."""
    if action.get("action") != "click":
        return action

    x, y = action.get("x", 0), action.get("y", 0)

    if isinstance(x, float) and isinstance(y, float) and 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
        x = int(x * ss_w)
        y = int(y * ss_h)
        print(f"[agent] normalised coords detected → converted to pixel ({x}, {y})")
        return {**action, "x": x, "y": y}

    x, y = int(x), int(y)

    if x < 0 or y < 0 or x > ss_w or y > ss_h:
        print(f"[agent] out-of-bounds coords ({x}, {y}) for {ss_w}x{ss_h} screenshot — skipping")
        return None

    return {**action, "x": x, "y": y}


def _get_action_with_retries(screenshot: bytes, goal: str, history: list):
    """Wraps vision.get_next_action with retry + a 2.5 s heartbeat message."""
    for attempt in range(config.MAX_RETRIES):
        heartbeat = threading.Timer(
            2.5, lambda: tts.speak_nonblocking("Working on it...")
        )
        heartbeat.start()
        try:
            result = vision.get_next_action(screenshot, goal, history)
            heartbeat.cancel()
            return result
        except Exception as e:
            heartbeat.cancel()
            print(f"[agent] vision error (attempt {attempt + 1}): {e}")
            if attempt == config.MAX_RETRIES - 1:
                tts.speak("I ran into a technical problem. Please try again.")
                return None
            tts.speak("Having trouble, retrying.")
    return None


def _is_major_action(action: dict) -> bool:
    narration = action.get("narration", "").lower()
    return any(kw in narration for kw in config.MAJOR_ACTION_KEYWORDS)


def _wait_for_action(action: dict) -> bool:
    """
    Wait for the UI to respond after an action.

    Uses _cancel_event.wait() instead of time.sleep() so the wait
    unblocks immediately when the user says "stop".

    Returns True if cancelled during the wait (caller must return immediately).
    """
    act = action.get("action")
    if act == "wait":
        return _cancel_event.is_set()
    elif act == "key" and action.get("key") in ("enter", "win"):
        return _cancel_event.wait(timeout=1.5)
    else:
        return _cancel_event.wait(timeout=0.6)


def _screenshot_hash(screenshot_bytes: bytes) -> str:
    """Downsample to 16×16 grayscale and MD5 — fast perceptual change detector."""
    img = Image.open(io.BytesIO(screenshot_bytes))
    small = img.resize((16, 16)).convert("L")
    return hashlib.md5(small.tobytes()).hexdigest()


def _screenshots_differ(before: bytes, after: bytes) -> bool:
    return _screenshot_hash(before) != _screenshot_hash(after)
