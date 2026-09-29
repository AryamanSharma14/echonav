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

    Falls back smoothly across Groq -> Gemini -> Local Heuristic so the agent
    never hangs if an API key expires, rate limits, or is offline.
    """
    provider = getattr(config, "MODEL_PROVIDER", "groq").lower()

    if provider in ("local", "heuristic"):
        return _local_heuristic_action(goal, elements, history)

    errors = []
    if provider == "ollama":
        try:
            return _ollama_action(screenshot_bytes, goal, history, elements)
        except Exception as e:
            errors.append(f"Ollama: {e}")
    elif provider == "groq":
        try:
            return _groq_action(screenshot_bytes, goal, history, elements)
        except Exception as e:
            errors.append(f"Groq: {e}")
            if getattr(config, "GEMINI_API_KEY", ""):
                try:
                    return _gemini_action(screenshot_bytes, goal, history, elements)
                except Exception as ge:
                    errors.append(f"Gemini: {ge}")
    elif provider == "gemini":
        try:
            return _gemini_action(screenshot_bytes, goal, history, elements)
        except Exception as e:
            errors.append(f"Gemini: {e}")
            if getattr(config, "GROQ_API_KEY", ""):
                try:
                    return _groq_action(screenshot_bytes, goal, history, elements)
                except Exception as ge:
                    errors.append(f"Groq: {ge}")
    else:
        raise ValueError(f"Unknown MODEL_PROVIDER: {config.MODEL_PROVIDER}")

    print(f"[vision] Cloud/local vision providers failed ({'; '.join(errors)}); using local heuristic fallback.")
    return _local_heuristic_action(goal, elements, history)


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
                line += "  [NO EFFECT] NO SCREEN CHANGE DETECTED — this action had no visible effect, try a different approach"
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

    if not getattr(config, "GROQ_API_KEY", "") and not os.getenv("GROQ_API_KEY"):
        raise ValueError("GROQ_API_KEY not configured")

    client = Groq()
    screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
    user_content = SYSTEM_PROMPT + "\n\n" + _build_user_message(goal, history, screenshot_bytes, elements)

    models_to_try = [config.GROQ_MODEL]
    for alt in ["llama-3.2-11b-vision-preview", "llama-3.2-90b-vision-preview"]:
        if alt not in models_to_try:
            models_to_try.append(alt)

    last_err = None
    for model in models_to_try:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_content},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{screenshot_b64}"}},
                        ],
                    }
                ],
                max_tokens=256,
                temperature=0.0,
            )
            return _parse_response(response.choices[0].message.content)
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            if "rate_limit" in msg or "429" in msg or "decommissioned" in msg or "404" in msg or "not_found" in msg:
                print(f"[vision] Groq {model} error ({e}); attempting next vision model")
                continue
            raise

    raise last_err if last_err else RuntimeError("All Groq vision models failed")


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

    if not getattr(config, "GEMINI_API_KEY", "") and not os.getenv("GEMINI_API_KEY"):
        raise ValueError("GEMINI_API_KEY not configured")

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


def _ollama_action(
    screenshot_bytes: bytes, goal: str, history: list, elements: list | None = None
) -> dict:
    """Query a local open-source vision model via Ollama (Qwen2.5-VL, MiniCPM-V, LLaMA-3.2-Vision)."""
    import urllib.request
    import json
    import base64

    b64_image = base64.b64encode(screenshot_bytes).decode("utf-8")
    user_prompt = SYSTEM_PROMPT + "\n\n" + _build_user_message(goal, history, screenshot_bytes, elements)

    payload = {
        "model": getattr(config, "OLLAMA_MODEL", "qwen2.5-vl"),
        "messages": [
            {
                "role": "user",
                "content": user_prompt,
                "images": [b64_image],
            }
        ],
        "stream": False,
        "format": "json",
    }

    base_url = getattr(config, "OLLAMA_URL", "http://localhost:11434").rstrip("/")
    url = f"{base_url}/api/chat"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    with urllib.request.urlopen(req, timeout=60) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        msg = res.get("message", {}).get("content", "{}")
        return _parse_response(msg)


def _local_heuristic_action(goal: str, elements: list | None, history: list) -> dict:
    """Deterministic, zero-latency local fallback action generator.

    Provides reliable navigation and element clicking when offline or when
    cloud API quotas are unavailable.
    """
    clean_goal = goal.lower().strip()
    history_actions = [h.get("action") for h in history]
    num_steps = len(history_actions)

    # 1. Direct website navigation (e.g. "open amazon", "go to youtube.com")
    KNOWN_SITES = {"amazon", "youtube", "google", "gmail", "reddit", "wikipedia", "github", "twitter", "facebook", "linkedin", "netflix"}
    site_match = re.search(r'\b(?:open|go to|browse to|visit)\s+([a-zA-Z0-9\.\-]+(?:\.com|\.org|\.io|\.net)?)\b', clean_goal)
    site = site_match.group(1).lower() if site_match else None
    is_web = site and (any(site.endswith(ext) for ext in (".com", ".org", ".io", ".net", ".edu", ".gov")) or site in KNOWN_SITES)

    if is_web:
        if not any(site.endswith(ext) for ext in (".com", ".org", ".io", ".net", ".edu", ".gov")):
            site = f"{site}.com"

        if num_steps == 0:
            return {"action": "key", "key": "ctrl+l", "narration": f"Focusing address bar for {site}"}
        elif num_steps == 1 and history_actions[-1] == "key":
            return {"action": "type", "text": site, "narration": f"Typing URL {site}"}
        elif num_steps == 2 and history_actions[-1] == "type":
            return {"action": "key", "key": "enter", "narration": f"Navigating to {site}"}
        elif num_steps == 3 and history_actions[-1] == "key":
            return {"action": "wait", "narration": f"Waiting for {site} to load"}
        else:
            return {"action": "done", "message": f"{site} is loaded."}

    # 2. Site search (e.g. "search amazon for coffee", "search youtube for python")
    search_match = re.search(r'\bsearch\s+([a-zA-Z0-9]+)\s+for\s+(.+)$', clean_goal)
    if search_match:
        site, query = search_match.group(1), search_match.group(2).strip()
        query_plus = query.replace(" ", "+")
        url_map = {
            "amazon": f"amazon.com/s?k={query_plus}",
            "google": f"google.com/search?q={query_plus}",
            "youtube": f"youtube.com/results?search_query={query_plus}",
            "wikipedia": f"en.wikipedia.org/wiki/Special:Search?search={query_plus}",
        }
        search_url = url_map.get(site, f"{site}.com/search?q={query_plus}")

        if num_steps == 0:
            return {"action": "key", "key": "ctrl+l", "narration": f"Focusing address bar to search {site}"}
        elif num_steps == 1 and history_actions[-1] == "key":
            return {"action": "type", "text": search_url, "narration": f"Typing search URL"}
        elif num_steps == 2 and history_actions[-1] == "type":
            return {"action": "key", "key": "enter", "narration": f"Executing search for {query}"}
        elif num_steps == 3 and history_actions[-1] == "key":
            return {"action": "wait", "narration": "Waiting for search results"}
        else:
            return {"action": "done", "message": f"Search results for {query} are displayed."}

    # 3. Native app launch (e.g. "open notepad", "launch calculator")
    app_match = re.search(r'\b(?:open|launch|start)\s+([a-zA-Z0-9\s]+)$', clean_goal)
    if app_match:
        app_name = app_match.group(1).strip()
        if num_steps == 0:
            return {"action": "key", "key": "win", "narration": f"Opening Windows search"}
        elif num_steps == 1 and history_actions[-1] == "key":
            return {"action": "type", "text": app_name, "narration": f"Typing {app_name}"}
        elif num_steps == 2 and history_actions[-1] == "type":
            return {"action": "key", "key": "enter", "narration": f"Launching {app_name}"}
        elif num_steps == 3 and history_actions[-1] == "key":
            return {"action": "wait", "narration": f"Waiting for {app_name} to load"}
        else:
            return {"action": "done", "message": f"{app_name} is open."}

    # 4. Element matching from Set-of-Mark accessibility tree
    if elements:
        for el in elements:
            el_name = (el.name or "").lower()
            if el_name and any(w in el_name for w in clean_goal.split() if len(w) > 3):
                return {"action": "click", "element": el.id, "narration": f"Clicking {el.name}"}

    # 5. Default fallback
    if num_steps >= 2:
        return {"action": "done", "message": f"Completed action for {goal}."}
    return {"action": "key", "key": "enter", "narration": "Executing default action"}
