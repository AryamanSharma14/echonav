import base64
import pyautogui
import tts
import config


class StopCommand(Exception):
    """Raised when the user says stop/cancel — signals agent loop to halt."""
    pass


def check_command(text: str) -> bool:
    """
    Check if text matches a special command.
    If it does, execute the command and return True.
    Returns False if text should be treated as a new goal.
    """
    import sys
    module = sys.modules[__name__]
    lower = text.lower().strip()
    for phrase, fn_name in _COMMANDS.items():
        if phrase in lower:
            getattr(module, fn_name)()
            return True
    return False


def _read_page() -> None:
    import screen
    screenshot_bytes = screen.capture()
    response = _ask_vision(
        screenshot_bytes,
        "Read all the text content visible on this screen for a blind user. "
        "Read top to bottom, left to right. Skip navigation menus and focus on main content."
    )
    tts.speak(response)


def _list_options() -> None:
    import screen
    screenshot_bytes = screen.capture()
    response = _ask_vision(
        screenshot_bytes,
        "List all interactive elements on this screen (buttons, links, input fields). "
        "Say each one briefly. Format as a spoken list for a blind user. "
        "Example: 'Compose button, Search box, Inbox link with 5 unread messages'."
    )
    tts.speak(response)


def _where_am_i() -> None:
    import screen
    screenshot_bytes = screen.capture()
    response = _ask_vision(
        screenshot_bytes,
        "In one sentence, describe where this user is on their computer. "
        "Speak directly to the user. "
        "Example: 'You are on Gmail, looking at your inbox with 5 unread emails.'"
    )
    tts.speak(response)


def _describe_screen() -> None:
    import screen
    screenshot_bytes = screen.capture()
    response = _ask_vision(
        screenshot_bytes,
        "Describe what is on this computer screen for a blind user in 2-3 natural sentences. "
        "Say which app or website is open, summarise the main visible content, and mention "
        "one or two things they could interact with next. Speak directly to the user and "
        "keep it conversational."
    )
    tts.speak(response)


def _go_back() -> None:
    pyautogui.hotkey("alt", "left")
    tts.speak("Going back.")


def _stop() -> None:
    import agent as _agent
    _agent.cancel()   # signal running loop to halt at next step
    tts.speak("Stopped. Hold spacebar to give me a new task.")
    raise StopCommand()


def _repeat() -> None:
    tts.speak_last()


def _slower() -> None:
    tts.set_rate(tts._rate - 20)
    tts.speak("Speaking slower.")


def _faster() -> None:
    tts.set_rate(tts._rate + 20)
    tts.speak("Speaking faster.")


def _scroll_down() -> None:
    pyautogui.scroll(-5)
    tts.speak("Scrolled down.")


def _scroll_up() -> None:
    pyautogui.scroll(5)
    tts.speak("Scrolled up.")


def _close_this() -> None:
    pyautogui.hotkey("alt", "F4")
    tts.speak("Closing.")


def _new_tab() -> None:
    pyautogui.hotkey("ctrl", "t")
    tts.speak("New tab opened.")


def _close_tab() -> None:
    pyautogui.hotkey("ctrl", "w")
    tts.speak("Tab closed.")


def _find_on_page() -> None:
    pyautogui.hotkey("ctrl", "f")
    tts.speak("Find box opened.")


def _zoom_in() -> None:
    pyautogui.hotkey("ctrl", "plus")
    tts.speak("Zoomed in.")


def _zoom_out() -> None:
    pyautogui.hotkey("ctrl", "minus")
    tts.speak("Zoomed out.")


def _switch_app() -> None:
    pyautogui.hotkey("alt", "tab")
    tts.speak("Switching app.")


def _copy_that() -> None:
    pyautogui.hotkey("ctrl", "c")
    tts.speak("Copied.")


def _ask_vision(screenshot_bytes: bytes, prompt: str) -> str:
    """Single-shot vision query via Groq — not part of the agent loop."""
    from groq import Groq
    img_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
    client = Groq(api_key=config.GROQ_API_KEY)
    resp = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
        ]}],
        max_tokens=300,
    )
    return resp.choices[0].message.content.strip()


_COMMANDS = {
    "read the page": "_read_page",
    "read page": "_read_page",
    "what can i do here": "_list_options",
    "what can i do": "_list_options",
    "what is on the screen": "_describe_screen",
    "what is on screen": "_describe_screen",
    "what's on the screen": "_describe_screen",
    "what's on screen": "_describe_screen",
    "whats on the screen": "_describe_screen",
    "whats on screen": "_describe_screen",
    "describe the screen": "_describe_screen",
    "describe screen": "_describe_screen",
    "tell me what you see": "_describe_screen",
    "where am i": "_where_am_i",
    "go back": "_go_back",
    "stop": "_stop",
    "cancel": "_stop",
    "say that again": "_repeat",
    "read that again": "_repeat",
    "speak slower": "_slower",
    "speak faster": "_faster",
    "scroll down": "_scroll_down",
    "scroll up": "_scroll_up",
    "close this": "_close_this",
    "new tab": "_new_tab",
    "close tab": "_close_tab",
    "find on page": "_find_on_page",
    "zoom in": "_zoom_in",
    "zoom out": "_zoom_out",
    "switch app": "_switch_app",
    "copy that": "_copy_that",
}
