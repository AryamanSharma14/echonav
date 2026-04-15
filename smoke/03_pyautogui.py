"""Smoke test 3: pyautogui moves mouse in a small square.
If you see the cursor move, you're good. If antivirus blocks it, you'll see no movement."""
import pyautogui, time

print("Moving mouse in a 100px square starting in 2 seconds. Watch your cursor...")
time.sleep(2)
x, y = pyautogui.position()
print(f"Start: ({x},{y})")
pyautogui.moveTo(x + 100, y, duration=0.3)
pyautogui.moveTo(x + 100, y + 100, duration=0.3)
pyautogui.moveTo(x, y + 100, duration=0.3)
pyautogui.moveTo(x, y, duration=0.3)
print("Screenshot test:")
img = pyautogui.screenshot()
print(f"Screenshot size: {img.size}")
print("PASS")
