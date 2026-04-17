import hashlib
import io
import threading
import queue
import mss
import pyautogui
from PIL import Image
import screen
import tts
import vision
import executor
import ui_tree
import annotate as annotator
import config

_cancel_event = threading.Event()

_CLICK_FUZZY_RADIUS = 40       # px — "same click" threshold for loop detection
_PIXEL_BLACKLIST_RADIUS = 40   # px — pseudo-bbox around a failed pixel click


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
    Loops up to MAX_STEPS times: capture → UIA snapshot → annotate →
    AI → narrate → confirm (if major) → execute.
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
    hallucination_count = 0
    last_element_id: int | None = None
    element_repeat_count = 0
    force_no_uia = False   # one-shot reset: pass no elements to vision next call
    failed_bboxes: set[tuple[int, int, int, int]] = set()   # element bboxes that didn't respond to a click — hide them from the model until something actually works

    _probe = screen.capture()
    scale_x, scale_y, offset_x, offset_y, ss_w, ss_h = _compute_scale(_probe)
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

        ui_elements = _safe_snapshot()
        print(f"[agent] UIA snapshot: {len(ui_elements)} element(s)")
        if force_no_uia:
            print("[agent] UIA-reset: sending empty element list to break model out of loop")
            effective_elements: list = []
            effective_shot = screenshot   # no boxes to draw
            force_no_uia = False
        else:
            effective_elements = _apply_blacklist(ui_elements, failed_bboxes)
            if failed_bboxes:
                removed = len(ui_elements) - len(effective_elements)
                if removed:
                    print(f"[agent] blacklist hides {removed} unresponsive element(s) this frame")
            effective_shot = _safe_annotate(
                screenshot, effective_elements, scale_x, scale_y, offset_x, offset_y
            )

        action = _get_action_with_retries(effective_shot, goal, history, effective_elements)
        last_vision_hash = _screenshot_hash(screenshot)
        if action is None:
            return

        element_resolved = False
        if action.get("action") == "click" and "element" in action:
            resolved = _resolve_element_click(action, effective_elements)
            if resolved is None:
                eid = action.get("element")
                valid_range = f"1..{len(ui_elements)}" if ui_elements else "none — UIA was empty"
                print(f"[agent] element id {eid} invalid (valid {valid_range}) — skipping")
                history.append({
                    "action": "click",
                    "narration": (
                        f"REJECTED: element id {eid} does not exist. Valid range was {valid_range}. "
                        "STOP picking arbitrary IDs — use a keyboard shortcut or a different strategy."
                    ),
                    "had_effect": False,
                })
                hallucination_count += 1
                if hallucination_count >= 2:
                    force_no_uia = True
                    hallucination_count = 0
                screenshot = screen.capture()
                continue
            action = resolved
            element_resolved = True
            hallucination_count = 0

            # Same element id picked twice in a row — break the loop immediately.
            eid = action["element"]
            if last_element_id == eid:
                element_repeat_count += 1
                if element_repeat_count >= 1:
                    print(f"[agent] element id {eid} repeated — forcing UIA reset")
                    force_no_uia = True
                    element_repeat_count = 0
            else:
                element_repeat_count = 0
            last_element_id = eid
        else:
            last_element_id = None
            element_repeat_count = 0
            action = _validate_action(action, ss_w, ss_h)
            if action is None:
                history.append({"action": "click", "narration": "skipped — invalid coordinates", "had_effect": False})
                screenshot = screen.capture()
                continue

        print(f"[agent] step {_step + 1}: {action}")

        if action["action"] == "done":
            tts.speak(action.get("message", "Task complete."))
            return

        # Loop detection: fuzzy for clicks (within _CLICK_FUZZY_RADIUS px), exact for repeated keys
        if action.get("action") == "click":
            x, y = action.get("x", 0), action.get("y", 0)
            if last_click_xy and abs(x - last_click_xy[0]) < _CLICK_FUZZY_RADIUS and abs(y - last_click_xy[1]) < _CLICK_FUZZY_RADIUS:
                repeat_count += 1
                if repeat_count >= 2:
                    print("[agent] repeated click in same region — forcing UIA reset")
                    force_no_uia = True
                    failed_bboxes.add(_bbox_from_xy(x, y))
                    history.append({
                        "action": "click",
                        "narration": (
                            f"REJECTED: clicked the same region ({x},{y}) {repeat_count+1} times with no effect. "
                            "Switch strategy — use keyboard (ctrl+l + URL) or scroll. Do NOT click this area again."
                        ),
                        "had_effect": False,
                    })
                    screenshot = screen.capture()
                    repeat_count = 0
                    last_click_xy = None
                    continue
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
            executor.execute(_resolve_for_executor(action, element_resolved, scale_x, scale_y, offset_x, offset_y))
            if _wait_for_action(action):
                return
            screenshot = screen.capture()
            history.append({**action, "had_effect": True})
            continue
        else:
            consecutive_waits = 0

        final_action = _resolve_for_executor(action, element_resolved, scale_x, scale_y, offset_x, offset_y)

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
            executor.execute(final_action)
        else:
            # Speak while executing — saves ~0.5–1 s per step.
            tts.speak_nonblocking(narration)
            if _cancel_event.is_set():
                return
            executor.execute(final_action)

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
                    # Blacklist this click target so the model can't pick it again.
                    bbox = action.get("_bbox")
                    if bbox is not None:
                        failed_bboxes.add(bbox)
                        print(f"[agent] blacklisting unresponsive bbox {bbox}")
                    else:
                        region = _bbox_from_xy(action.get("x", 0), action.get("y", 0))
                        failed_bboxes.add(region)
                        print(f"[agent] blacklisting click region {region}")
                    # Second no-effect click → force keyboard-only next frame.
                    if failed_clicks >= 2:
                        force_no_uia = True
            else:
                failed_clicks = 0

        if had_effect:
            failed_bboxes.clear()

        history.append({**action, "had_effect": had_effect})
        screenshot = next_screenshot

    tts.speak("I wasn't able to complete that. Would you like me to try a different approach?")


def _safe_snapshot() -> list:
    try:
        return ui_tree.snapshot()
    except Exception as e:
        print(f"[agent] ui_tree.snapshot failed: {e}")
        return []


def _safe_annotate(screenshot, elements, scale_x, scale_y, offset_x, offset_y) -> bytes:
    try:
        return annotator.annotate(screenshot, elements, scale_x, scale_y, offset_x, offset_y)
    except Exception as e:
        print(f"[agent] annotate failed: {e}")
        return screenshot


def _resolve_element_click(action: dict, elements: list) -> dict | None:
    """Translate {action:click, element:N} into screen-space {x,y} using UIA."""
    eid = action.get("element")
    if not isinstance(eid, int):
        try:
            eid = int(eid)
        except (TypeError, ValueError):
            return None
    for el in elements:
        if el.id == eid:
            x, y = el.center
            label = (el.name or el.control_type)[:40]
            narration = action.get("narration") or f"Clicking {label}"
            return {
                "action": "click",
                "x": int(x),
                "y": int(y),
                "narration": narration,
                "element": eid,
                "_bbox": (el.left, el.top, el.right, el.bottom),
            }
    return None


def _apply_blacklist(elements: list, failed_bboxes: set) -> list:
    """Drop elements whose center falls inside any blacklisted region, then
    renumber so prompt IDs stay contiguous. Using a containment test (not
    equality) also catches pixel-click regions and bbox drift between frames.
    """
    if not failed_bboxes:
        return elements
    regions = list(failed_bboxes)
    kept = []
    for el in elements:
        cx, cy = el.center
        if any(l <= cx <= r and t <= cy <= b for l, t, r, b in regions):
            continue
        kept.append(el)
    for i, el in enumerate(kept, start=1):
        el.id = i
    return kept


def _bbox_from_xy(x: int, y: int) -> tuple[int, int, int, int]:
    """Pseudo-bbox for raw pixel clicks — wide enough that small coord wobble
    from the model (±10 px each retry) still falls inside the blacklist region.
    """
    r = _PIXEL_BLACKLIST_RADIUS
    return (int(x) - r, int(y) - r, int(x) + r, int(y) + r)


def _point_blacklisted(x: int, y: int, regions: set) -> bool:
    for l, t, r, b in regions:
        if l <= x <= r and t <= y <= b:
            return True
    return False


def _resolve_for_executor(
    action: dict,
    element_resolved: bool,
    scale_x: float,
    scale_y: float,
    offset_x: int,
    offset_y: int,
) -> dict:
    """Produce the final screen-space action the executor will fire.

    Element-resolved clicks are already in screen coords (from UIA). Pixel
    clicks from the model are in screenshot space and need scaling.
    """
    if element_resolved:
        return action
    return _map_click_to_screen(action, scale_x, scale_y, offset_x, offset_y)


def _compute_scale(screenshot_bytes: bytes) -> tuple:
    """Map screenshot-pixel coords → physical screen coords on the primary monitor.

    Returns (scale_x, scale_y, offset_x, offset_y, ss_w, ss_h). The offset is the
    primary monitor's origin on the virtual desktop — non-zero when the primary
    monitor isn't at (0,0), e.g. a side-mounted second screen.
    """
    img = Image.open(io.BytesIO(screenshot_bytes))
    with mss.mss() as sct:
        m = sct.monitors[1]   # same index screen.capture uses
    mon_w, mon_h = m["width"], m["height"]
    offset_x, offset_y = m["left"], m["top"]
    scale_x = mon_w / img.width
    scale_y = mon_h / img.height
    print(
        f"[agent] coord scale: screenshot {img.width}x{img.height} → "
        f"monitor {mon_w}x{mon_h} at ({offset_x},{offset_y}) | {scale_x:.3f}x"
    )
    return scale_x, scale_y, offset_x, offset_y, img.width, img.height


def _map_click_to_screen(
    action: dict, scale_x: float, scale_y: float, offset_x: int, offset_y: int
) -> dict:
    """Translate a click's screenshot-space coords into physical screen coords."""
    if action.get("action") != "click":
        return action
    x = int(action["x"] * scale_x) + offset_x
    y = int(action["y"] * scale_y) + offset_y
    return {**action, "x": x, "y": y}


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


def _get_action_with_retries(
    screenshot: bytes, goal: str, history: list, elements: list | None = None
):
    """Wraps vision.get_next_action with retry + a 2.5 s heartbeat message."""
    for attempt in range(config.MAX_RETRIES):
        heartbeat = threading.Timer(
            2.5, lambda: tts.speak_nonblocking("Working on it...")
        )
        heartbeat.start()
        try:
            result = vision.get_next_action(screenshot, goal, history, elements)
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
