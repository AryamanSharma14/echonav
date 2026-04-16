# Stub — implementation owned by task-6-vision (Jai)
# This file exists so agent.py can import it; tests mock it.
import base64
import json
import os
import config

SYSTEM_PROMPT = """You are EchoNav, an AI assistant helping a blind user control their computer running Windows 11.
You see a screenshot of their screen and must decide the single best next action.

Rules:
- Respond with ONLY one JSON object, no markdown, no explanation
- Never ask the user to describe the screen or look at anything
- Click visible UI elements by their exact pixel coordinates
- When filling forms, handle one field at a time
- When the goal is fully complete, use the "done" action
- NEVER type the goal phrase verbatim — type only the actual search term or value needed

Windows-specific guidance:
- To open an app (e.g. Brave, Chrome, Notepad): press the Win key, then type ONLY the app name (e.g. "brave"), then press Enter. Do NOT type "open brave" — just "brave".
- To navigate to a website: click the browser address bar, type the URL (e.g. "gmail.com"), press Enter.
- To open a URL directly: use {"action": "key", "key": "win"} then type app name, OR click address bar and type URL.
- The Windows taskbar is at the bottom of the screen. The Start button is the Windows logo on the left.
- If you pressed Win and the search box is open, type only the app name and press Enter.
- If an action did not work after 2 attempts, try a completely different approach.

Valid action formats:
{"action": "click", "x": 450, "y": 320, "narration": "Clicking the Compose button"}
{"action": "type", "text": "brave", "narration": "Typing app name to search"}
{"action": "key", "key": "enter", "narration": "Pressing Enter to open"}
{"action": "key", "key": "win", "narration": "Opening Windows search"}
{"action": "scroll", "direction": "down", "amount": 3, "narration": "Scrolling down to see more"}
{"action": "wait", "narration": "Waiting for the page to load"}
{"action": "done", "message": "Your email has been sent successfully"}"""


def get_next_action(screenshot_bytes: bytes, goal: str, history: list) -> dict:
    """Route to the configured AI provider and return a parsed action dict."""
    if config.MODEL_PROVIDER == "groq":
        return _groq_action(screenshot_bytes, goal, history)
    elif config.MODEL_PROVIDER == "gemini":
        return _gemini_action(screenshot_bytes, goal, history)
    else:
        raise ValueError(f"Unknown MODEL_PROVIDER: {config.MODEL_PROVIDER}")


def _build_user_message(goal: str, history: list) -> str:
    recent = history[-10:]
    history_str = ""
    if recent:
        steps = "\n".join(f"- {h.get('action')}: {h.get('narration', '')}" for h in recent)
        history_str = f"\nActions taken so far:\n{steps}"
    return f"Goal: {goal}{history_str}\n\nWhat is the single next action?"


def _parse_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        # Strip ```json or ``` code fences
        parts = text.split("```")
        if len(parts) > 1:
            text = parts[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def _groq_action(screenshot_bytes: bytes, goal: str, history: list) -> dict:
    from groq import Groq
    
    # Initialize client (it automatically looks for GROQ_API_KEY in the environment)
    client = Groq()
    screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
    
    response = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": SYSTEM_PROMPT + "\n\n" + _build_user_message(goal, history)},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{screenshot_b64}",
                        },
                    },
                ],
            }
        ],
        max_tokens=256,
        temperature=0.0
    )
    return _parse_response(response.choices[0].message.content)


def _gemini_action(screenshot_bytes: bytes, goal: str, history: list) -> dict:
    # Fallback using google-genai SDK per HACKATHON.md
    from google import genai
    from google.genai import types
    
    client = genai.Client()
    
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=[
            SYSTEM_PROMPT, 
            _build_user_message(goal, history),
            types.Part.from_bytes(data=screenshot_bytes, mime_type='image/jpeg')
        ]
    )
    return _parse_response(response.text)