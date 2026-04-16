import time
import pyautogui
import config

pyautogui.FAILSAFE = True   # Moving mouse to top-left corner aborts
pyautogui.PAUSE = config.ACTION_DELAY


def execute(action: dict, scale_x: float = 1.0, scale_y: float = 1.0) -> None:
    """Execute a single action returned by the vision module.

    scale_x / scale_y convert from screenshot pixel space to pyautogui logical
    pixel space (accounts for DPI scaling + screenshot resize).
    """
    act = action.get("action")

    if act == "click":
        x = int(action["x"] * scale_x)
        y = int(action["y"] * scale_y)
        print(f"[executor] click raw=({action['x']},{action['y']}) scaled=({x},{y})")
        pyautogui.click(x, y)

    elif act == "type":
        pyautogui.write(action["text"], interval=0.05)

    elif act == "key":
        pyautogui.press(action["key"])

    elif act == "scroll":
        direction = action.get("direction", "down")
        amount = int(action.get("amount", 3))
        clicks = amount if direction == "up" else -amount
        pyautogui.scroll(clicks)

    elif act == "wait":
        time.sleep(1.5)

    elif act == "done":
        pass  # Handled by agent.py before executor is called
