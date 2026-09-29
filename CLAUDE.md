# EchoNav Developer Architecture Guide

EchoNav is an autonomous voice desktop assistant for blind and low-vision users on Windows 11. It combines sub-50ms non-autoregressive decision routing (Convai Laya) with deterministic browser automation (Chrome DevTools Protocol) and desktop Set-of-Mark accessibility tree grounding (Windows UIA).

## Architectural Foundations

1. **System 1 Decision Engine (`laya_engine.py`)**:
   - Built on Convai Laya (`convaiinnovations/laya`), providing sub-50ms intent classification, safety scoring, and candidate element selection.
   - Non-autoregressive fast classification routes voice commands into instant utility actions, deterministic browser navigation, or native desktop actions.
   - Fast deterministic heuristic fallback ensures instantaneous unit tests and zero-downtime offline execution.

2. **Deterministic Browser Grounding (`browser_cdp.py`)**:
   - Connects directly to Chromium browsers (Chrome, Brave, Edge) via Chrome DevTools Protocol (port 9222).
   - Extracts exact DOM accessibility tree nodes with bounding boxes, tag names, roles, and text.
   - Eliminates coordinate guessing for web tasks: navigates URLs directly, clicks DOM nodes via exact viewport coordinates, and types into focused elements.

3. **Desktop Set-of-Mark Grounding (`ui_tree.py` + `annotate.py`)**:
   - For native Windows applications, extracts interactive UI Automation leaves (buttons, inputs, menus).
   - Overlays numbered bounding boxes on screen captures so the Vision Language Model (Groq / Gemini) references elements by integer ID instead of raw pixel coordinates.

4. **Multi-Provider Perception (`vision.py`)**:
   - Resilient fallback chain: Groq (meta-llama/llama-4-scout-17b, llama-3.2-11b) -> Gemini 2.5 Flash -> Local Heuristic Engine.
   - Guaranteed completion without crashes even when API keys are absent or rate limits are reached.

5. **Audio Pipeline (`stt.py` + `tts.py` + `listener.py`)**:
   - STT: Faster-Whisper with RMS voice activity energy thresholding to discard silence and static.
   - TTS: Non-blocking Edge Neural TTS (`en-US-AriaNeural`) with instant abort (`stop_speech()`) on user interrupt.

## CLI Commands

```bash
echonav start       # Start voice agent with HUD overlay
echonav start --headless  # Run without visual HUD
echonav mock        # Interactive console mock mode (no microphone needed)
echonav status      # Check system health, Laya engine, and CDP connection
echonav test-audio  # Test audio synthesis and capture
echonav version     # Output version
```

## Running Tests

```bash
pytest -v
```
All 105 automated unit tests execute with headless mock support.