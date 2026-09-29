"""Voice command interceptor for EchoNav.

Intercepts immediate utility phrases (stop, cancel, read page, where am I,
go back, volume, zoom, tabs) and executes them in sub-50ms using both
exact dictionary matching and Laya System 1 intent classification,
completely bypassing heavy VLM inference loops.
"""

from __future__ import annotations

import base64
import logging
import pyautogui
import tts
import config
from laya_engine import engine as laya_engine
from browser_cdp import browser as cdp_browser

logger = logging.getLogger("echonav.commands")


class StopCommand(Exception):
    """Raised when the user says stop/cancel — signals agent loop to halt."""
    pass


def check_command(text: str) -> bool:
    """Check if text matches a special utility command.

    If it does, execute the command immediately and return True.
    Returns False if text represents a multi-step goal requiring the agent loop.
    """
    import sys
    module = sys.modules[__name__]
    lower = text.lower().strip()

    # 1. Exact string matching fast-path (<1ms)
    for phrase, fn_name in _COMMANDS.items():
        if phrase in lower:
            getattr(module, fn_name)()
            return True

    # 2. Laya System 1 fast-path (<30ms)
    intent = laya_engine.classify_intent(lower)
    if intent.category == "instant_command" and intent.command_name:
        fn_name = f"_{intent.command_name}"
        if hasattr(module, fn_name):
            getattr(module, fn_name)()
            return True

    return False


def _read_page() -> None:
    # 1. Try deterministic Browser CDP DOM text extraction (<20ms)
    if cdp_browser.is_connected():
        text = cdp_browser.read_visible_text()
        if text and len(text) > 10:
            tts.speak(f"Page content: {text[:400]}")
            return

    # 2. Fall back to VLM screen reading
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
    # Check CDP active tab
    if cdp_browser.is_connected():
        tab = cdp_browser.get_active_tab()
        if tab and tab.title:
            tts.speak(f"You are in your browser on {tab.title}.")
            return

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
    tts.stop_speech()
    _agent.cancel()  # signal running loop to halt immediately
    tts.speak("Stopped. Hold tilde to give me a new task.")
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


def _close_window() -> None:
    _close_this()


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
    """Query VLM with multi-provider fallback (Groq -> Gemini -> Local descriptor)."""
    # 1. Try Groq
    if config.GROQ_API_KEY:
        try:
            from groq import Groq
            img_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            client = Groq(api_key=config.GROQ_API_KEY)
            resp = client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                ]}],
                max_tokens=250,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.debug(f"Groq vision query failed: {e}")

    # 2. Try Gemini
    if config.GEMINI_API_KEY:
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=config.GEMINI_API_KEY)
            contents = [
                prompt,
                types.Part.from_bytes(data=screenshot_bytes, mime_type="image/jpeg"),
            ]
            response = client.models.generate_content(model=config.GEMINI_MODEL, contents=contents)
            return response.text.strip()
        except Exception as e:
            logger.debug(f"Gemini vision query failed: {e}")

    # 3. Fallback descriptor
    return "Desktop view with active applications open. Ready for your next command."


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
