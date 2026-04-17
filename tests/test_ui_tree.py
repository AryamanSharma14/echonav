"""Smoke tests for ui_tree — we mock the uiautomation module so tests can run
on any platform without poking the real desktop."""

import sys
import types
from unittest.mock import MagicMock

import pytest

import ui_tree


def _fake_rect(left, top, right, bottom):
    r = MagicMock()
    r.left, r.top, r.right, r.bottom = left, top, right, bottom
    return r


def _fake_control(
    ct: str = "ButtonControl",
    name: str = "OK",
    rect=(10, 10, 100, 50),
    offscreen: bool = False,
    children: list | None = None,
    class_name: str = "",
):
    c = MagicMock()
    c.ControlTypeName = ct
    c.Name = name
    c.IsOffscreen = offscreen
    c.BoundingRectangle = _fake_rect(*rect)
    c.AutomationId = ""
    c.ClassName = class_name
    c.GetChildren.return_value = children or []
    return c


def test_snapshot_returns_empty_when_disabled(monkeypatch):
    monkeypatch.setattr(ui_tree.config, "USE_UIA", False)
    assert ui_tree.snapshot() == []


def test_snapshot_skips_when_no_foreground(monkeypatch):
    fake_mod = types.SimpleNamespace(GetForegroundControl=lambda: None)
    monkeypatch.setitem(sys.modules, "uiautomation", fake_mod)
    monkeypatch.setattr(ui_tree.config, "USE_UIA", True)
    assert ui_tree.snapshot() == []


def test_snapshot_collects_interactive_leaves(monkeypatch):
    """A root pane with three interactive children and one offscreen decoy."""
    btn1 = _fake_control("ButtonControl", "Send", (0, 0, 100, 30))
    btn2 = _fake_control("EditControl", "Search Amazon", (120, 0, 420, 40))
    btn3 = _fake_control("HyperlinkControl", "Home", (10, 60, 80, 80))
    decoy = _fake_control("ButtonControl", "Hidden", (0, 0, 100, 30), offscreen=True)
    root = _fake_control("PaneControl", "root", (0, 0, 1000, 1000),
                         children=[btn1, btn2, btn3, decoy])

    fake_mod = types.SimpleNamespace(GetForegroundControl=lambda: root)
    monkeypatch.setitem(sys.modules, "uiautomation", fake_mod)
    monkeypatch.setattr(ui_tree.config, "USE_UIA", True)
    monkeypatch.setattr(ui_tree.config, "MAX_UI_ELEMENTS", 60)

    els = ui_tree.snapshot()
    names = [(e.name, e.control_type) for e in els]
    assert ("Send", "ButtonControl") in names
    assert ("Search Amazon", "EditControl") in names
    assert ("Home", "HyperlinkControl") in names
    assert ("Hidden", "ButtonControl") not in names
    # IDs are sequential from 1
    assert [e.id for e in els] == list(range(1, len(els) + 1))


def test_snapshot_skips_start_menu_surface(monkeypatch):
    """When the foreground is Windows Start / Search, UIA should return [] so the
    model falls back to keyboard shortcuts (Win + type + Enter)."""
    btn = _fake_control("ButtonControl", "Brave", (100, 100, 200, 140))
    root = _fake_control("PaneControl", "Start", (0, 0, 1920, 1080),
                         children=[btn], class_name="Windows.UI.Core.CoreWindow")
    fake_mod = types.SimpleNamespace(GetForegroundControl=lambda: root)
    monkeypatch.setitem(sys.modules, "uiautomation", fake_mod)
    monkeypatch.setattr(ui_tree.config, "USE_UIA", True)
    assert ui_tree.snapshot() == []


def test_element_center_is_midpoint():
    el = ui_tree.Element(id=1, name="x", control_type="ButtonControl",
                         left=100, top=200, right=300, bottom=260)
    assert el.center == (200, 230)


def test_element_prompt_line_includes_type_and_label():
    el = ui_tree.Element(id=4, name="Add to cart", control_type="ButtonControl",
                         left=0, top=0, right=10, bottom=10)
    line = el.as_prompt_line()
    assert line.startswith("[4]")
    assert "Button" in line
    assert "Add to cart" in line


def test_element_prompt_line_truncates_long_labels():
    long = "x" * 200
    el = ui_tree.Element(id=1, name=long, control_type="ButtonControl",
                         left=0, top=0, right=10, bottom=10)
    line = el.as_prompt_line()
    assert len(line) < 90
    assert line.endswith("...")
