"""Vision module — ask the configured model for the next single action."""

import base64
import json
import re
import config


SYSTEM_PROMPT = """You are EchoNav, a voice-controlled computer assistant for a blind user on Windows 11.
You see a screenshot of their screen and return ONE action as a JSON object. No markdown, no explanation — just the JSON.

━━━ PRIORITY ORDER — always prefer higher options ━━━
1. Keyboard shortcut (most reliable — no coordinate guessing)
2. Browser address bar (ctrl+l) when navigating to any website
3. Click by pixel coords (last resort — coordinates are approximate)

━━━ STRICT RULES ━━━
- NEVER type the goal phrase verbatim. Type only what a sighted user would type (e.g. "brave", not "open brave").
- NEVER click a search result in a browser. Use ctrl+l then type the URL directly.
- NEVER click a Windows Start search result. After Win + typing, ALWAYS press Enter.
- NEVER interact with the small dark capsule near the bottom of the screen — that is EchoNav's own status bar.
- After every app launch (Win+type+Enter) or ANY page navigation (URL typed + Enter), ALWAYS use {"action":"wait"} before the next step. The page needs time to load.
- If the same action fails twice (no screen change detected), switch strategy completely — never repeat a failed action a third time.
- NEVER declare "done" or narrate success unless you can SEE in the screenshot that the action completed.
- If you're stuck and cannot make progress, use {"action":"done","message":"I got stuck. Please try again."} rather than guessing.

━━━ URLS AND WEBSITES — ALWAYS USE THE BROWSER ━━━
- If the goal contains a domain name (.com, .org, .io, etc.) or a site like "YouTube", "Gmail", "Google", ALWAYS open it in a browser — never via Windows search.
- If a browser isn't open, open one first (e.g. Brave) with Win+type+Enter+wait, then navigate.
- To open a website: key ctrl+l → type the URL → key enter → wait.

━━━ WHEN YOU NEED USER INPUT TO CONTINUE ━━━
If you've completed what's possible but the next step requires the user to speak
(e.g. you opened Gmail Compose and filled the recipient, but the body is empty),
return done immediately with a natural prompt:
  {"action":"done","message":"Ready. What would you like to say in the email?"}
Do NOT sit idle or keep waiting — always hand control back to the user.

━━━ GMAIL-SPECIFIC SHORTCUTS ━━━
Gmail uses keyboard shortcuts — these are the ONLY reliable way to operate Gmail:
  Open Compose:    press "c"
  To field:        already focused when compose opens — type immediately, NO Tab first
  Jump to Subject: press Tab AFTER typing the recipient email
  Jump to Body:    press Tab AFTER typing the subject
  Send email:      press ctrl+enter
IMPORTANT: After navigating to gmail.com, ALWAYS wait one full step before pressing "c".
IMPORTANT: After pressing "c" and waiting, the To field is already active — type the email address right away.

━━━ COMMON FLOWS ━━━

Open an app (non-browser):
  {"action":"key","key":"win","narration":"Opening Windows search"}
  {"action":"type","text":"brave","narration":"Typing app name"}
  {"action":"key","key":"enter","narration":"Launching Brave"}
  {"action":"wait","narration":"Waiting for Brave to open"}

Open a website (ALWAYS use this — never Windows search for websites):
  {"action":"key","key":"ctrl+l","narration":"Focusing browser address bar"}
  {"action":"type","text":"gmail.com","narration":"Typing Gmail URL"}
  {"action":"key","key":"enter","narration":"Navigating to Gmail"}
  {"action":"wait","narration":"Waiting for Gmail to load"}

Compose a Gmail email (ALWAYS extract the real values from the goal — never use placeholders):
  [navigate to gmail.com and wait first]
  {"action":"key","key":"c","narration":"Opening compose window"}
  {"action":"wait","narration":"Waiting for compose to open"}
  ← After the wait, the To field is ALREADY focused. Type the email address immediately — do NOT Tab first.
  {"action":"type","text":"[actual email address from goal]","narration":"Typing recipient email"}
  {"action":"key","key":"tab","narration":"Moving to subject"}
  {"action":"type","text":"[actual subject from goal, or a sensible default]","narration":"Typing subject"}
  {"action":"key","key":"tab","narration":"Moving to message body"}
  [if the body text is unknown, return done asking the user for it]
  {"action":"done","message":"Ready. What would you like to say in the email?"}

━━━ ALL VALID ACTION FORMATS ━━━
{"action":"click","x":450,"y":320,"narration":"..."}
{"action":"type","text":"text to type","narration":"..."}
{"action":"key","key":"enter","narration":"..."}
{"action":"key","key":"ctrl+l","narration":"..."}
{"action":"scroll","direction":"down","amount":3,"narration":"..."}
{"action":"wait","narration":"Waiting for page to load"}
{"action":"done","message":"Task complete message spoken to user"}"""


def get_next_action(screenshot_bytes: bytes, goal: str, history: list) -> dict:
    """Route to the configured AI provider and return a parsed action dict."""
    if config.MODEL_PROVIDER == "groq":
        return _groq_action(screenshot_bytes, goal, history)
    elif config.MODEL_PROVIDER == "gemini":
        return _gemini_action(screenshot_bytes, goal, history)
    else:
        raise ValueError(f"Unknown MODEL_PROVIDER: {config.MODEL_PROVIDER}")


def _extract_values(goal: str) -> str:
    """
    Parse the goal text for structured values the AI often fails to pick up
    on its own (email addresses, URLs). Returns a hint block injected into
    the prompt so the model never has to guess.
    """
    hints = []

    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', goal)
    if emails:
        hints.append(f"Email address(es) found in goal: {', '.join(emails)}")

    urls = re.findall(
        r'\b(?:https?://)?([A-Za-z0-9.-]+\.(?:com|org|io|net|co|in|gov|edu)(?:/\S*)?)\b',
        goal,
    )
    urls = [u for u in urls if not any(u in e for e in emails)]
    if urls:
        hints.append(f"URL(s) found in goal: {', '.join(urls)}")

    if not hints:
        return ""
    return (
        "\nEXTRACTED VALUES — use these exact strings when filling in forms or typing:\n"
        + "\n".join(f"  • {h}" for h in hints)
    )


def _build_user_message(goal: str, history: list) -> str:
    recent = history[-10:]
    history_str = ""
    if recent:
        steps = []
        for h in recent:
            line = f"- {h.get('action')}: {h.get('narration', '')}"
            if not h.get("had_effect", True):
                line += "  ⚠ NO SCREEN CHANGE DETECTED — this action had no visible effect, try a different approach"
            steps.append(line)
        history_str = "\nActions taken so far:\n" + "\n".join(steps)
    extracted = _extract_values(goal)
    return f"Goal: {goal}{extracted}{history_str}\n\nWhat is the single next action?"


def _parse_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) > 1:
            text = parts[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def _groq_action(screenshot_bytes: bytes, goal: str, history: list) -> dict:
    from groq import Groq
    try:
        from groq import RateLimitError
    except ImportError:
        RateLimitError = Exception   # older SDK versions

    client = Groq()
    screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

    try:
        response = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": SYSTEM_PROMPT + "\n\n" + _build_user_message(goal, history)},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{screenshot_b64}"}},
                    ],
                }
            ],
            max_tokens=256,
            temperature=0.0,
        )
        return _parse_response(response.choices[0].message.content)
    except RateLimitError:
        print("[vision] Groq rate limit hit — falling back to Gemini")
        if not config.GEMINI_API_KEY:
            raise RuntimeError("Groq rate limit reached and no GEMINI_API_KEY configured for fallback.")
        return _gemini_action(screenshot_bytes, goal, history)


def _gemini_action(screenshot_bytes: bytes, goal: str, history: list) -> dict:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            SYSTEM_PROMPT,
            _build_user_message(goal, history),
            types.Part.from_bytes(data=screenshot_bytes, mime_type='image/jpeg'),
        ],
    )
    return _parse_response(response.text)
