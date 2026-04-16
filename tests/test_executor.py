import executor

def test_click_calls_pyautogui(mocker):
    mock_click = mocker.patch("executor.pyautogui.click")
    executor.execute({"action": "click", "x": 100, "y": 200})
    mock_click.assert_called_once_with(100, 200)

def test_type_calls_pyautogui_write(mocker):
    mock_write = mocker.patch("executor.pyautogui.write")
    executor.execute({"action": "type", "text": "hello"})
    mock_write.assert_called_once_with("hello", interval=0.05)

def test_key_calls_pyautogui_press(mocker):
    mock_press = mocker.patch("executor.pyautogui.press")
    executor.execute({"action": "key", "key": "enter"})
    mock_press.assert_called_once_with("enter")

def test_scroll_down_calls_pyautogui_scroll(mocker):
    mock_scroll = mocker.patch("executor.pyautogui.scroll")
    executor.execute({"action": "scroll", "direction": "down", "amount": 3})
    mock_scroll.assert_called_once_with(-3)

def test_scroll_up_calls_pyautogui_scroll(mocker):
    mock_scroll = mocker.patch("executor.pyautogui.scroll")
    executor.execute({"action": "scroll", "direction": "up", "amount": 2})
    mock_scroll.assert_called_once_with(2)

def test_wait_sleeps(mocker):
    mock_sleep = mocker.patch("executor.time.sleep")
    executor.execute({"action": "wait"})
    mock_sleep.assert_called_once_with(1.5)

def test_done_action_is_ignored(mocker):
    mock_click = mocker.patch("executor.pyautogui.click")
    executor.execute({"action": "done", "message": "All done"})
    mock_click.assert_not_called()
