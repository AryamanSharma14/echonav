import time
import pyautogui
import config

pyautogui.FAILSAFE = True   # Moving mouse to top-left corner aborts
pyautogui.PAUSE = config.ACTION_DELAY


def execute(action: dict) -> None:
    """Execute a single action returned by the vision module."""
    act = action.get("action")

    if act == "click":
        pyautogui.click(action["x"], action["y"])

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
