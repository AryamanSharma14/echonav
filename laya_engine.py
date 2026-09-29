"""Laya System 1 Decision Engine for EchoNav.

Provides sub-50ms non-autoregressive decision-making, intent routing,
safety gating, and candidate element scoring using Convai Laya
(open-source TypeSafe Jev reproduction) with an instant local heuristic fallback.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("echonav.laya")

# ---------------------------------------------------------------------------
# Typed Decision Schemas
# ---------------------------------------------------------------------------

INTENT_QUESTIONS: Dict[str, Any] = {
    "intent": {
        "type": "choice",
        "instructions": "What primary category does this voice command belong to?",
        "criteria": {
            "instant_command": "stop, halt, cancel, pause, go back, read page, repeat, speak faster, speak slower, louder, quieter, zoom in, zoom out, close tab, new tab",
            "browser_navigate": "open website, go to amazon, search youtube, browse, check gmail, visit url, online shopping, find on web",
            "desktop_action": "open notepad, launch app, close window, switch application, click button, type text, scroll down, scroll up, windows search",
            "inquire": "where am I, describe screen, what can I do here, what is open, explain what you see",
        },
    },
    "is_destructive": {
        "type": "noul",
        "instructions": "Does this action permanently delete data, submit an order, send an email, close an unsaved file, or transfer money?",
    },
    "urgency": {
        "type": "score",
        "instructions": "How urgent or immediate is this user request?",
        "criteria": ["routine", "time-sensitive", "emergency stop"],
    },
}

SAFETY_KEYWORDS = {
    "send", "sending", "submit", "submitting", "delete", "deleting", "purchase", "purchasing",
    "pay", "paying", "order", "ordering", "book", "booking", "confirm", "confirming",
    "wipe", "wiping", "remove", "removing", "checkout", "transfer", "transferring",
    "erase", "erasing", "drop", "destroy", "destroying"
}

INSTANT_COMMAND_PATTERNS = {
    "stop": ["stop", "cancel", "halt", "abort", "freeze"],
    "read_page": ["read the page", "read page", "read content", "read all text"],
    "where_am_i": ["where am i", "where amn i", "what screen is this", "current app", "where am", "where i am", "what app", "where are we"],
    "describe_screen": ["describe the screen", "describe screen", "what is on screen", "tell me what you see"],
    "list_options": ["what can i do here", "list options", "interactive elements", "what buttons"],
    "go_back": ["go back", "previous page", "back"],
    "repeat": ["say that again", "read that again", "repeat that", "what did you say"],
    "slower": ["speak slower", "talk slower", "slow down"],
    "faster": ["speak faster", "talk faster", "speed up"],
    "scroll_down": ["scroll down", "page down", "move down"],
    "scroll_up": ["scroll up", "page up", "move up"],
    "new_tab": ["new tab", "open tab"],
    "close_tab": ["close tab", "close this tab"],
    "close_window": ["close this", "close window", "exit app"],
    "find_on_page": ["find on page", "search on page", "find text"],
    "zoom_in": ["zoom in", "make larger", "increase zoom"],
    "zoom_out": ["zoom out", "make smaller", "decrease zoom"],
}


@dataclass
class IntentResult:
    category: str  # instant_command | browser_navigate | desktop_action | inquire | unknown
    command_name: Optional[str] = None
    confidence: float = 0.95
    is_destructive: bool = False
    destructive_prob: float = 0.0
    requires_confirmation: bool = False
    source: str = "laya"  # laya | heuristic | exact


@dataclass
class SafetyResult:
    is_destructive: bool
    probability: float
    requires_confirmation: bool
    trigger_keyword: Optional[str] = None


class LayaEngine:
    """Manages the Convai Laya model lifecycle and fast fallbacks."""

    def __init__(self, enable_model: bool = True):
        is_test = bool(os.getenv("PYTEST_CURRENT_TEST"))
        self.enable_model = enable_model and os.getenv("ECHONAV_DISABLE_LAYA", "0") != "1" and not is_test
        self._router = None
        self._initialized = False

    def _get_router(self):
        """Lazy-load the Laya router instance."""
        if bool(os.getenv("PYTEST_CURRENT_TEST")) or os.getenv("ECHONAV_DISABLE_LAYA", "0") == "1":
            return None
        if not self.enable_model:
            return None
        if not self._initialized:
            try:
                from laya import Router
                self._router = Router()
                self._initialized = True
            except Exception as e:
                logger.warning(f"Laya model unavailable ({e}); falling back to heuristic engine.")
                self._initialized = True
                self._router = None
        return self._router

    def classify_intent(self, text: str) -> IntentResult:
        """Classify user utterance into primary execution rail in sub-50ms."""
        clean = text.lower().strip()
        if not clean:
            return IntentResult(category="unknown", confidence=0.0, source="exact")

        # 1. Exact instant command fast-path (<1ms)
        for cmd_name, patterns in INSTANT_COMMAND_PATTERNS.items():
            for pat in patterns:
                if pat in clean:
                    is_destruct = any(w in clean for w in ("delete", "close this", "close window"))
                    return IntentResult(
                        category="instant_command",
                        command_name=cmd_name,
                        confidence=0.99,
                        is_destructive=is_destruct,
                        destructive_prob=0.85 if is_destruct else 0.05,
                        requires_confirmation=False if cmd_name in ("stop", "cancel") else is_destruct,
                        source="exact",
                    )

        # 2. Try Laya System 1 Router if available
        router = self._get_router()
        if router is not None:
            try:
                res = router.predict(text, INTENT_QUESTIONS)
                ans = res.get("answers", {})
                intent_cat = ans.get("intent", {}).get("choice", "desktop_action")
                destruct_prob = float(ans.get("is_destructive", {}).get("noul", 0.0))
                is_destruct = destruct_prob >= 0.70
                return IntentResult(
                    category=intent_cat,
                    confidence=0.92,
                    is_destructive=is_destruct,
                    destructive_prob=destruct_prob,
                    requires_confirmation=is_destruct,
                    source="laya",
                )
            except Exception as e:
                logger.debug(f"Laya prediction failed: {e}; using heuristic fallback.")

        # 3. Deterministic Heuristic Fallback (<1ms)
        return self._heuristic_classify(clean)

    def evaluate_safety(self, action: Any, text: str = "") -> SafetyResult:
        """Evaluate if an action is destructive and requires verbal confirmation."""
        if isinstance(action, str):
            narration = (action + " " + text).lower()
            act_dict = {"narration": action}
        elif isinstance(action, dict):
            narration = (action.get("narration", "") + " " + text).lower()
            act_dict = action
        else:
            narration = text.lower()
            act_dict = {}

        # Check keyword triggers
        matched_kw = None
        for kw in SAFETY_KEYWORDS:
            if re.search(r"\b" + re.escape(kw) + r"\b", narration):
                matched_kw = kw
                break

        # Also check key combinations
        prob = 0.1
        if matched_kw:
            prob = 0.90
        elif act_dict.get("action") == "key" and act_dict.get("key") in ("ctrl+w", "alt+f4", "enter"):
            prob = 0.50

        is_destruct = prob >= 0.75 or matched_kw is not None
        return SafetyResult(
            is_destructive=is_destruct,
            probability=prob,
            requires_confirmation=is_destruct,
            trigger_keyword=matched_kw,
        )

    def _heuristic_classify(self, clean: str) -> IntentResult:
        """Deterministic heuristic classifier for instant zero-latency routing."""
        # Browser keywords
        browser_markers = ["youtube", "google", "amazon", "gmail", "website", "url", ".com", ".org", "browse", "search"]
        inquire_markers = ["where am i", "what is on", "describe", "what can i do", "read"]

        if any(m in clean for m in inquire_markers):
            return IntentResult(category="inquire", confidence=0.88, source="heuristic")
        if any(m in clean for m in browser_markers):
            return IntentResult(category="browser_navigate", confidence=0.90, source="heuristic")

        # Check safety
        is_destruct = any(re.search(r"\b" + kw + r"\b", clean) for kw in SAFETY_KEYWORDS)
        return IntentResult(
            category="desktop_action",
            confidence=0.85,
            is_destructive=is_destruct,
            destructive_prob=0.85 if is_destruct else 0.10,
            requires_confirmation=is_destruct,
            source="heuristic",
        )


# Global singleton instance
engine = LayaEngine()
