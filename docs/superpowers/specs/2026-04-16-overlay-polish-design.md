# EchoNav Overlay Polish — Design Spec

## Goal

Replace the current single-window centered capsule with a two-layer UI: a full-screen glowing border that signals agent state to everyone in the room, plus a refined minimal-glass center capsule. Zero changes to callers — `overlay.update(state, text)` and `overlay.run()` API unchanged.

## Architecture

`overlay.py` is refactored into two cooperating tkinter windows managed by a single `Overlay` facade.

### ScreenBorder (new)

A fullscreen borderless window that sits behind all content. Its interior is made invisible using Windows' `-transparentcolor` attribute — background set to magic color `#020203`, which Windows renders as fully transparent. A `Canvas.create_rectangle` draws the 2px colored border 3px inset from screen edges. Only the border line is visible; everything else shows through normally.

### CenterCapsule (refactored from current Overlay)

A `Toplevel` child of the ScreenBorder root. 580×82px, dead center of screen. Rounded-rect glass pill drawn on Canvas. Three zones:
- **Left:** 10px filled circle orb, breathing pulse on `listening` only
- **Center:** Segoe UI 14px semibold label, color-matched to state
- **Right:** static symbol at rest; 4-frame spinner (`◜◝◞◟`) during `thinking` / `acting`

### Overlay (public facade)

Same public API as today. Owns one `Tk()` root (ScreenBorder) and one `Toplevel` (CenterCapsule). Single `queue.Queue`, single 100ms poll loop, single 80ms animation loop. Both windows update together on every state change.

## State Color Map

| State      | Color     | Notes                          |
|------------|-----------|--------------------------------|
| idle       | `#3a3f4a` | Dim gray — border always present |
| listening  | `#00d4f5` | Cyan                           |
| thinking   | `#7c6af7` | Violet                         |
| acting     | `#00d97e` | Green                          |
| confirming | `#f5a623` | Amber                          |
| done       | `#00d97e` | Green                          |
| error      | `#e05c5c` | Muted red                      |

Both the screen border and the capsule (border, orb, text, right indicator) use the same color for each state.

## Default Text Per State

| State      | Text                                      |
|------------|-------------------------------------------|
| idle       | Ready for your next task                  |
| listening  | Listening… tell me your next objective    |
| thinking   | Processing screen…                        |
| acting     | Executing action                          |
| confirming | Say yes to confirm, or no to cancel       |
| done       | Task complete                             |
| error      | Something went wrong                      |

## Visual Details

**Screen border:**
- `overrideredirect(True)`, `attributes('-topmost', True)`, `attributes('-alpha', 1.0)`
- Background: `#020203` → `attributes('-transparentcolor', '#020203')`
- Border: `Canvas.create_rectangle(3, 3, sw-3, sh-3, outline=color, width=2)`
- No animation on border — instant color swap on state change
- Idle: dim gray `#3a3f4a` (border always visible, never disappears)

**Center capsule:**
- `Toplevel` with `overrideredirect(True)`, `attributes('-topmost', True)`, `attributes('-alpha', 0.93)`
- Background: `#18191f` (dark glass)
- Rounded-rect body: `create_polygon` with `smooth=True`, fill `#1e1f28`
- Rounded-rect border: same technique, outline = state color, width 2
- Orb pulse: alpha oscillates 80→255 at ±12/step, only during `listening`
- Spinner: cycles `['◜','◝','◞','◟']` every 80ms during `thinking` / `acting`

## Known Constraint

tkinter cannot produce CSS `box-shadow` blur. The screen border is a crisp colored line, not a soft glow. This is acceptable — at full screen scale the color alone clearly communicates state.

## What Does Not Change

- `overlay.Overlay` class name and module path
- `update(state: str, text: str = "")` signature
- `run()` blocking main-thread contract
- All 7 valid state strings
- `_STATE_COLORS` and `_DEFAULT_TEXT` module-level dicts (used by the existing test)
- `tests/test_overlay.py` — all 5 tests must still pass

## Files

- **Modify:** `overlay.py` — full rewrite of internals, same public surface
- **No other files change**
