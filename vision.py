"""Vision module — ask the configured model for the next single action."""

import base64
import io
import json
import re

from PIL import Image

import config


SYSTEM_PROMPT = """You are EchoNav, a voice-controlled computer assistant for a blind user on Windows 11.
You see a screenshot of the screen and return ONE action as a JSON object. No markdown, no explanation — just the JSON.

━━━ ABSOLUTE RULE — DO ONLY WHAT THE USER ASKED ━━━
Fulfil the user's goal and nothing more. Do NOT add steps, do NOT "helpfully" continue past the goal.
  • "open amazon"         → navigate to amazon.com, then immediately return done.
  • "open gmail"          → navigate to gmail.com, then immediately return done.
  • "open youtube"        → navigate to youtube.com, then immediately return done.
  • "search amazon for X" → open amazon.com, click the search box by element ID, type X, submit, then done.
  • "compose an email to bob@x.com saying hi" → only then should you enter Gmail compose.
If the goal is just "open <site>" or "go to <site>", finish with done as soon as the page is visible.
Never start typing, searching, composing, or clicking into the page unless the user explicitly asked for it.

━━━ HOW TO CLICK — READ THIS CAREFULLY ━━━
The screenshot has RED NUMBERED BOXES drawn over every interactive element
(buttons, links, text fields, menu items). The user message lists each box as:
  [N] ControlType: Label
Picking by number is EXACT — no coordinate guessing. ALWAYS prefer it:

  {"action":"click","element":12,"narration":"Clicking the search box"}

CRITICAL RULES FOR ELEMENT IDS:
- Only use integer IDs that appear in the "INTERACTIVE ELEMENTS" list below.
- If the list says "Valid IDs: 1..25", then 26, 30, 67, etc. are INVALID — never invent them.
- If no element matches your target, do NOT guess a number. Use keyboard (ctrl+l, Enter, Tab, Win) or pixel coords instead.
- When the list is empty (no numbered boxes), you MUST use keyboard shortcuts — no element clicks.

Pixel coords are a last resort and are often wrong — only use them when no element matches AND no keyboard shortcut fits.

  {"action":"click","x":<int>,"y":<int>,"narration":"..."}

━━━ PRIORITY ORDER ━━━
1. Click by element ID (most reliable — numbered box in screenshot)
2. Keyboard shortcut (when the task has a well-known hotkey)
3. Browser address bar (ctrl+l) for navigating to a website
4. Click by pixel coords (last resort — only if no element ID available)

━━━ FLOW: OPEN A WEBSITE (any .com/.org/.io or named site) ━━━
  {"action":"key","key":"ctrl+l","narration":"Focusing the address bar"}
  {"action":"type","text":"amazon.com","narration":"Typing the URL"}
  {"action":"key","key":"enter","narration":"Going to Amazon"}
  {"action":"wait","narration":"Waiting for the page to load"}
  {"action":"done","message":"Amazon is open."}
If no browser is open yet, first launch one (Win + "brave" + Enter + wait), then do the 5 steps above.

━━━ FLOW: OPEN AN APP (non-browser) ━━━
  {"action":"key","key":"win","narration":"Opening Windows search"}
  {"action":"type","text":"notepad","narration":"Typing the app name"}
  {"action":"key","key":"enter","narration":"Launching Notepad"}   ← ALWAYS Enter. NEVER click Start results.
  {"action":"wait","narration":"Waiting for Notepad to open"}
  {"action":"done","message":"Notepad is open."}

━━━ HARD RULE: START / SEARCH / TASKBAR ━━━
After pressing the Win key and typing an app name, your ONLY valid next action is
{"action":"key","key":"enter",...}. DO NOT click in the Start menu, DO NOT use
element IDs there. The highlighted top result is what Enter launches — trust it.

━━━ FLOW: SEARCH ON A WEBSITE (use this — it never fails) ━━━
When the user asks to search a specific site, use URL-based search. This is
keyboard-only and never has to find the search box visually:

  Amazon:  amazon.com/s?k=<query with + for spaces>
  Google:  google.com/search?q=<query>
  YouTube: youtube.com/results?search_query=<query>
  Ebay:    ebay.com/sch/i.html?_nkw=<query>
  Wikipedia: en.wikipedia.org/wiki/Special:Search?search=<query>

Example "search amazon for olive oil":
  {"action":"key","key":"ctrl+l","narration":"Focusing the address bar"}
  {"action":"type","text":"amazon.com/s?k=olive+oil","narration":"Typing the search URL"}
  {"action":"key","key":"enter","narration":"Searching Amazon"}
  {"action":"wait","narration":"Waiting for results"}
  {"action":"done","message":"Here are the Amazon results for olive oil."}

Fallback (only if URL-search doesn't exist for the site): click the search
box by its element ID from the numbered list, type the query, press enter.
NEVER click a search box by pixel coordinates — use URL search instead.

━━━ FLOW: CLICK A LINK OR BUTTON ON A PAGE ━━━
If the target has an element ID in the numbered list, use that. If clicking by
pixel coords 2+ times doesn't change the screen, STOP — the click is landing
on dead space or a covered element. Switch strategy: scroll to bring it into
view, or use keyboard navigation (Tab, Enter) instead of guessing coords.

━━━ FLOW: GMAIL COMPOSE — USE ONLY IF THE USER EXPLICITLY ASKED TO COMPOSE/SEND ━━━
After reaching gmail.com with the inbox loaded:
  {"action":"key","key":"c","narration":"Opening the compose window"}
  {"action":"wait","narration":"Waiting for compose"}
  ← To field is already focused. Type recipient immediately, DO NOT press Tab first.
  {"action":"type","text":"<recipient>","narration":"Typing recipient"}
  {"action":"key","key":"tab","narration":"Moving to subject"}
  {"action":"type","text":"<subject>","narration":"Typing subject"}
  {"action":"key","key":"tab","narration":"Moving to body"}
  {"action":"type","text":"<body>","narration":"Typing the message"}
  Send with ctrl+enter. If the user's goal doesn't provide the body, return
  {"action":"done","message":"Ready. What would you like the email to say?"} and stop.

━━━ STRICT RULES ━━━
- NEVER type the goal phrase verbatim. Type only what a sighted user would type (e.g. "brave", not "open brave").
- When an element ID matches the target, use it. Do NOT use ctrl+l if the user asked you to click something specific.
- NEVER click a Windows Start search result. After Win + typing, press Enter.
- NEVER interact with the small dark capsule near the middle of the screen — that is EchoNav's own status bar.
- After ANY app launch or URL navigation, ALWAYS return wait BEFORE the next action. The page needs time to load.
- If the same action had no screen change twice, switch strategy completely. Never attempt it a third time.
- NEVER declare done unless the screenshot visibly shows the goal is achieved.
- If you are genuinely stuck, return {"action":"done","message":"I got stuck. Please try again."} rather than guessing.

━━━ ALL VALID ACTIONS ━━━
{"action":"click","element":<int>,"narration":"..."}          ← PREFERRED
{"action":"click","x":<int>,"y":<int>,"narration":"..."}      ← fallback only
{"action":"type","text":"...","narration":"..."}
{"action":"key","key":"enter|ctrl+l|tab|win|c|ctrl+enter|...","narration":"..."}
{"action":"scroll","direction":"down|up","amount":<int>,"narration":"..."}
{"action":"wait","narration":"..."}
{"action":"done","message":"Spoken to the user"}"""


def get_next_action(
    screenshot_bytes: bytes,
    goal: str,
    history: list,
    elements: list | None = None,
) -> dict:
    """Route to the configured AI provider and return a parsed action dict.

    `elements` is the UIA snapshot from ui_tree.snapshot() — its labels are
    injected into the prompt so the model can click by ID.
    """
    if config.MODEL_PROVIDER == "groq":
        return _groq_action(screenshot_bytes, goal, history, elements)
    elif config.MODEL_PROVIDER == "gemini":
        return _gemini_action(screenshot_bytes, goal, history, elements)
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


def _screenshot_dims(screenshot_bytes: bytes) -> tuple[int, int]:
    img = Image.open(io.BytesIO(screenshot_bytes))
    return img.width, img.height


def _format_elements(elements: list | None) -> str:
    if not elements:
        return (
            "\nINTERACTIVE ELEMENTS: none available this frame. "
            "DO NOT return any 'element' field — it will be rejected. "
            "Use keyboard shortcuts (ctrl+l, Enter, Tab, Win) or pixel coords only."
        )
    n = len(elements)
    lines = [el.as_prompt_line() for el in elements]
    return (
        f"\nINTERACTIVE ELEMENTS (red numbered boxes in the image) — "
        f"Valid IDs: 1..{n}. Any other ID will be rejected.\n"
        "Click these by ID for pixel-perfect accuracy:\n"
        + "\n".join(lines)
    )


def _build_user_message(
    goal: str,
    history: list,
    screenshot_bytes: bytes | None = None,
    elements: list | None = None,
) -> str:
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
    elements_str = _format_elements(elements)

    dims_str = ""
    if screenshot_bytes is not None:
        try:
            w, h = _screenshot_dims(screenshot_bytes)
            dims_str = (
                f"\nScreenshot is {w}x{h} pixels. "
                f"Any fallback pixel click coordinates MUST be integers with 0 ≤ x < {w} and 0 ≤ y < {h}."
            )
        except Exception:
            pass

    return (
        f"Goal: {goal}{extracted}{dims_str}{elements_str}{history_str}\n\n"
        "What is the single next action? Prefer clicking by element ID when the target is numbered. "
        "Do only what the user asked, then return done."
    )


def _parse_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) > 1:
            text = parts[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def _groq_action(
    screenshot_bytes: bytes, goal: str, history: list, elements: list | None = None
) -> dict:
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
                        {"type": "text", "text": SYSTEM_PROMPT + "\n\n" + _build_user_message(goal, history, screenshot_bytes, elements)},
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
        return _gemini_action(screenshot_bytes, goal, history, elements)


_GEMINI_RETRYABLE_KEYWORDS = (
    "503", "unavailable", "overload", "high demand", "504",
    "resource_exhausted", "deadline", "timeout",
    "404", "not_found", "no longer available",   # a retired model → try next
)


def _gemini_action(
    screenshot_bytes: bytes, goal: str, history: list, elements: list | None = None
) -> dict:
    """Call Gemini with automatic model fallback on capacity errors.

    The primary model can spike to 503/UNAVAILABLE; walking through the fallback
    chain lets the agent keep working when one model is overloaded.
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    contents = [
        SYSTEM_PROMPT,
        _build_user_message(goal, history, screenshot_bytes, elements),
        types.Part.from_bytes(data=screenshot_bytes, mime_type='image/jpeg'),
    ]

    models_to_try = [config.GEMINI_MODEL] + list(
        getattr(config, "GEMINI_FALLBACK_MODELS", [])
    )

    last_err: Exception | None = None
    for model in models_to_try:
        try:
            response = client.models.generate_content(model=model, contents=contents)
            if model != config.GEMINI_MODEL:
                print(f"[vision] Gemini fallback succeeded on {model}")
            return _parse_response(response.text)
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            if any(k in msg for k in _GEMINI_RETRYABLE_KEYWORDS):
                print(f"[vision] Gemini {model} unavailable — trying next fallback")
                continue
            raise   # non-retryable (auth, invalid request, etc.)

    raise last_err if last_err else RuntimeError("All Gemini models failed")
