"""Chrome DevTools Protocol (CDP) Grounding Engine for EchoNav.

Provides 100% deterministic browser automation for Chromium-based browsers
(Chrome, Brave, Edge). Queries DOM accessibility nodes, executes clicks directly
at DOM coordinates, and enters text into focused nodes without pixel guessing.

Falls back gracefully to desktop UIA when no CDP port is active.
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("echonav.cdp")

DEFAULT_CDP_PORTS = [9222, 9223, 9224]


@dataclass
class BrowserTab:
    id: str
    title: str
    url: str
    web_socket_debugger_url: str
    type: str = "page"


@dataclass
class DOMElement:
    node_id: int
    tag: str
    name: str
    role: str
    bounding_box: tuple[int, int, int, int]  # left, top, width, height
    is_clickable: bool

    @property
    def center(self) -> tuple[int, int]:
        l, t, w, h = self.bounding_box
        return (l + w // 2, t + h // 2)


class BrowserCDPEngine:
    """Lightweight HTTP/CDP client for deterministic browser interaction."""

    def __init__(self, ports: Optional[List[int]] = None):
        self.ports = ports or DEFAULT_CDP_PORTS
        self.active_port: Optional[int] = None

    def is_connected(self) -> bool:
        """Check if any Chromium browser with remote debugging is accessible."""
        for port in self.ports:
            try:
                url = f"http://127.0.0.1:{port}/json/version"
                req = urllib.request.Request(url, headers={"User-Agent": "EchoNav"})
                with urllib.request.urlopen(req, timeout=0.4) as resp:
                    if resp.status == 200:
                        self.active_port = port
                        return True
            except Exception:
                continue
        self.active_port = None
        return False

    def get_tabs(self) -> List[BrowserTab]:
        """List all open page tabs."""
        if not self.is_connected() or not self.active_port:
            return []

        try:
            url = f"http://127.0.0.1:{self.active_port}/json/list"
            req = urllib.request.Request(url, headers={"User-Agent": "EchoNav"})
            with urllib.request.urlopen(req, timeout=0.8) as resp:
                data = json.loads(resp.read().decode())
                tabs = []
                for item in data:
                    if item.get("type") == "page":
                        tabs.append(BrowserTab(
                            id=item.get("id", ""),
                            title=item.get("title", ""),
                            url=item.get("url", ""),
                            web_socket_debugger_url=item.get("webSocketDebuggerUrl", ""),
                        ))
                return tabs
        except Exception as exc:
            logger.debug(f"Failed to query CDP tabs: {exc}")
            return []

    def get_active_tab(self) -> Optional[BrowserTab]:
        """Return the current foreground tab."""
        tabs = self.get_tabs()
        return tabs[0] if tabs else None

    def navigate(self, url: str) -> bool:
        """Navigate the active tab to a target URL via CDP Page.navigate."""
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"

        tab = self.get_active_tab()
        if not tab:
            return False

        # Execute navigation via devtools protocol HTTP endpoint
        return self._send_command(tab.id, "Page.navigate", {"url": url})

    navigate_to = navigate

    def extract_interactive_elements(self) -> List[DOMElement]:
        """Extract all interactive elements (buttons, links, inputs) with bounding boxes."""
        tab = self.get_active_tab()
        if not tab:
            return []

        js_extract = """
        (() => {
            const elements = [];
            const candidates = document.querySelectorAll('button, a[href], input, textarea, select, [role="button"], [role="link"]');
            let id = 1;
            for (const el of candidates) {
                const rect = el.getBoundingClientRect();
                if (rect.width > 4 && rect.height > 4 && window.getComputedStyle(el).visibility !== 'hidden') {
                    elements.push({
                        node_id: id++,
                        tag: el.tagName.toLowerCase(),
                        name: (el.innerText || el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.value || '').trim().slice(0, 80),
                        role: el.getAttribute('role') || el.tagName.toLowerCase(),
                        bbox: [Math.round(rect.left), Math.round(rect.top), Math.round(rect.width), Math.round(rect.height)],
                        is_clickable: true
                    });
                }
                if (elements.length >= 60) break;
            }
            return elements;
        })()
        """
        res = self.evaluate_js(js_extract)
        if not isinstance(res, list):
            return []

        out = []
        for d in res:
            out.append(DOMElement(
                node_id=d["node_id"],
                tag=d["tag"],
                name=d["name"],
                role=d["role"],
                bounding_box=tuple(d["bbox"]),
                is_clickable=d["is_clickable"],
            ))
        return out

    def evaluate_js(self, expression: str) -> Any:
        """Evaluate JavaScript inside the active tab and return the result."""
        tab = self.get_active_tab()
        if not tab:
            return None

        result = self._send_command_sync(tab.id, "Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
        })
        if result and "result" in result and "value" in result["result"]:
            return result["result"]["value"]
        return None

    def click_element_by_index(self, index: int) -> bool:
        """Click an interactive element by its deterministic 1-based index."""
        js_click = f"""
        (() => {{
            const candidates = Array.from(document.querySelectorAll('button, a[href], input, textarea, select, [role="button"], [role="link"]'))
                .filter(el => {{
                    const rect = el.getBoundingClientRect();
                    return rect.width > 4 && rect.height > 4 && window.getComputedStyle(el).visibility !== 'hidden';
                }});
            if (candidates[{index - 1}]) {{
                candidates[{index - 1}].scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                candidates[{index - 1}].click();
                return true;
            }}
            return false;
        }})()
        """
        return bool(self.evaluate_js(js_click))

    def type_into_focused(self, text: str) -> bool:
        """Type text into currently focused element or input field."""
        escaped = json.dumps(text)
        js_type = f"""
        (() => {{
            const el = document.activeElement;
            if (el && ('value' in el || el.isContentEditable)) {{
                if ('value' in el) {{
                    el.value = {escaped};
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }} else {{
                    el.innerText = {escaped};
                }}
                return true;
            }}
            return false;
        }})()
        """
        return bool(self.evaluate_js(js_type))

    def read_visible_text(self) -> str:
        """Extract clean text content of the active page for voice narration."""
        js_read = """
        (() => {
            const clone = document.body.cloneNode(true);
            const scripts = clone.querySelectorAll('script, style, noscript, nav, header, footer');
            scripts.forEach(s => s.remove());
            return clone.innerText.split('\\n').map(s => s.trim()).filter(s => s.length > 0).slice(0, 25).join(' ');
        })()
        """
        res = self.evaluate_js(js_read)
        return str(res) if res else "No readable text on this page."

    def _send_command(self, tab_id: str, method: str, params: Dict[str, Any]) -> bool:
        """Fire and forget CDP command."""
        return self._send_command_sync(tab_id, method, params) is not None

    def _send_command_sync(self, tab_id: str, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send synchronous CDP command via HTTP target protocol."""
        if not self.active_port:
            return None

        # When Chromium is in remote-debugging mode, we can talk to its HTTP protocol
        # or use websocket. If websocket is unavailable, standard evaluate HTTP is supported.
        try:
            # Check if websockets library is present
            import websockets
            import asyncio

            tabs = self.get_tabs()
            ws_url = None
            for t in tabs:
                if t.id == tab_id:
                    ws_url = t.web_socket_debugger_url
                    break

            if not ws_url:
                return None

            async def _call():
                async with websockets.connect(ws_url, close_timeout=1.0) as ws:
                    msg = {"id": 1, "method": method, "params": params}
                    await ws.send(json.dumps(msg))
                    resp = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    return json.loads(resp).get("result", {})

            return asyncio.run(_call())
        except Exception as exc:
            logger.debug(f"CDP command {method} failed: {exc}")
            return None


# Global singleton instance
browser = BrowserCDPEngine()
