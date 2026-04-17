import time
import pyautogui
import config

pyautogui.FAILSAFE = True   # Moving mouse to top-left corner aborts
pyautogui.PAUSE = config.ACTION_DELAY


def execute(action: dict) -> None:
    """Execute a single action returned by the vision module.

    Click coordinates must already be in physical screen space (agent.py's
    _map_click_to_screen handles the screenshot → screen transform).
    """
    act = action.get("action")

    if act == "click":
        x, y = int(action["x"]), int(action["y"])
        print(f"[executor] click ({x},{y})")
        pyautogui.click(x, y)

    elif act == "type":
        pyautogui.write(action["text"], interval=0.05)

    elif act == "key":
        key = action["key"]
        if "+" in key:   # combo e.g. "ctrl+l", "ctrl+a"
            pyautogui.hotkey(*key.split("+"))
        else:
            pyautogui.press(key)

    elif act == "scroll":
        direction = action.get("direction", "down")
        amount = int(action.get("amount", 3))
        clicks = amount if direction == "up" else -amount
        pyautogui.scroll(clicks)

    elif act == "wait":
        time.sleep(1.5)

    elif act == "done":
        pass  # Handled by agent.py before executor is called
