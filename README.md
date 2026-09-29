# EchoNav: Autonomous Voice Desktop Agent for Blind Users

EchoNav is an autonomous, voice-driven desktop assistive agent built specifically for blind and low-vision individuals using Windows 11. Unlike traditional screen readers that merely vocalize passive text, EchoNav perceives the screen, reasons about interface hierarchy, executes multi-step computer tasks, and provides continuous, non-blocking verbal narration.

By pairing sub-50ms non-autoregressive decision routing (Convai Laya) with deterministic browser grounding (Chrome DevTools Protocol) and desktop UI Automation Set-of-Mark annotations, EchoNav eliminates coordinate hallucination and delivers real-time assistive computing.

---

## Architectural Overview

```
                          [ User Utterance ]
                                  │
                                  ▼
                     [ Faster-Whisper + VAD ]
                                  │
                                  ▼
                  [ Laya System 1 Decision Engine ]
               (Sub-50ms Non-Autoregressive Intent)
                                  │
       ┌──────────────────────────┼──────────────────────────┐
       │                          │                          │
       ▼                          ▼                          ▼
[ Instant Utility ]     [ Browser Navigation ]     [ Desktop Application ]
(Stop, Volume, Zoom)    (Chrome DevTools CDP)      (UIA + Set-of-Mark)
       │                          │                          │
       │                          ▼                          ▼
       │                 [ DOM Node Selector ]      [ Screen Capture ]
       │                 (Direct CDP Action)        (Masked Status Bar)
       │                          │                          │
       │                          │                          ▼
       │                          │                 [ Vision Perception ]
       │                          │                 (Groq / Gemini / Local)
       │                          │                          │
       └──────────────────────────┼──────────────────────────┘
                                  │
                                  ▼
                   [ Safety Gating & Narration ]
                    ("Say yes to confirm action")
                                  │
                                  ▼
                 [ Action Execution & Sound Queue ]
                      (PyAutoGUI / Edge-TTS)
```

---

## Key Technical Innovations

### 1. Sub-50ms System 1 Decision Engine (Convai Laya)
Monolithic VLM agent loops suffer from 1.5 to 3.0-second latencies per step. EchoNav integrates Convai Laya (`convaiinnovations/laya`), providing an open-source reproduction of TypeSafe Jev. 
- Classifies user intent in sub-50ms into instant utility commands, web navigation, native desktop tasks, or screen queries.
- Pre-evaluates safety probability (`is_destructive`), catching irreversible operations (deletion, transactions, checkout) before physical execution.
- Ships with an instant local heuristic fallback for offline environments and CI test suites.

### 2. Dual-Track Grounding: CDP Web Rail & Desktop UIA Set-of-Mark
- **Browser CDP Engine (`browser_cdp.py`)**: Connects directly to Chromium browsers (Chrome, Brave, Edge) on remote debugging port 9222. Reads exact DOM nodes, bounding boxes, aria-labels, and input fields. Clicks, types, and navigates without visual pixel guessing.
- **Desktop UI Automation (`ui_tree.py` + `annotate.py`)**: For native Windows apps (File Explorer, Notepad, Settings), extracts interactive accessibility tree leaves and paints numbered bounding boxes onto screenshots. The vision model specifies integer IDs (e.g. `{"action": "click", "element": 4}`), avoiding coordinate drift and display scaling errors.

### 3. Transparent, Non-Activating HUD Overlay (`overlay.py`)
- Sits unobtrusively on the screen to provide sighted companions and judges with real-time status.
- Configured with Win32 window styles `WS_EX_TRANSPARENT` (clicks pass through transparent areas to underlying applications) and `WS_EX_NOACTIVATE` (redrawing the HUD never steals keyboard focus from active text fields).
- Screen capture automatically masks the exact bottom region occupied by the HUD capsule, preventing vision models from interacting with the assistant itself.

### 4. Resilient Perception & Audio Pipeline
- **Vision Fallback Chain (`vision.py`)**: Automatically falls back from Groq (LLaMA-4 Scout / LLaMA-3.2-Vision) to Google Gemini 2.5 Flash, and finally to a deterministic local heuristic action generator. EchoNav never crashes or freezes due to rate limits or network drops.
- **Audio Feedback (`stt.py` + `tts.py`)**: Root-mean-square energy calculations discard silence and static before Whisper transcription. Edge Neural TTS delivers voice feedback with immediate speech abortion (`stop_speech()`) when the user speaks or commands a stop.

---

## Installation

### Prerequisites
- Windows 10 or Windows 11 (64-bit)
- Python 3.10 or 3.11
- Microphone and speakers/headphones
- Optional: Groq API Key or Google Gemini API Key

### Setup
```bash
git clone https://github.com/AryamanSharma14/echonav.git
cd echonav

python -m venv .venv
.\.venv\Scripts\activate

pip install -e .
```

### Environment Configuration
Copy the example environment file and configure your API keys:
```bash
cp .env.example .env
```
Edit `.env`:
```env
MODEL_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## Usage

EchoNav provides a unified command-line interface:

### Voice Mode
Launch the complete voice assistant with the HUD status capsule:
```bash
echonav start
```
Hold the tilde key (`~`) or spacebar, speak your task, and release.

To run without the graphical HUD overlay (e.g., in a terminal or headless session):
```bash
echonav start --headless
```

### Mock Console Mode
Test and verify task execution, intent classification, and browser workflows without requiring a physical microphone:
```bash
echonav mock
```
Type commands such as `open amazon.com`, `search youtube for mozart`, or `where am I`.

### System Health Diagnostics
Check system components, virtual environment status, Laya engine initialization, and browser connection:
```bash
echonav status
```

### Audio Self-Test
Verify speech synthesis and audio output:
```bash
echonav test-audio
```

---

## Chromium CDP Setup (Optional for Web Automation)

To enable deterministic DOM-level browser automation, launch your Chromium browser (Chrome, Brave, or Edge) with remote debugging enabled:

```bash
# Brave Browser
brave.exe --remote-debugging-port=9222

# Google Chrome
chrome.exe --remote-debugging-port=9222

# Microsoft Edge
msedge.exe --remote-debugging-port=9222
```

When active, `echonav status` will report:
```
Browser CDP: Connected (Port 9222)
```
Browser goals like `open amazon` or `search youtube for ...` will execute deterministically via direct DOM nodes in under 100ms. If no CDP port is active, EchoNav automatically uses the standard visual agent loop.

---

## Voice Commands Reference

Immediate utility commands are intercepted by the System 1 engine in sub-30ms:

| Command | Action |
|---|---|
| `"stop"` / `"cancel"` / `"abort"` | Immediately halts running tasks and stops speech synthesis |
| `"read the page"` / `"read page"` | Extracts all visible text from the page/document and reads it aloud |
| `"where am I"` | Describes the current active window and focused UI control |
| `"what can I do here"` | Lists interactive buttons, inputs, and links on the screen |
| `"go back"` | Executes browser back / navigation history retreat |
| `"say that again"` / `"repeat that"` | Replays the last verbal narration |
| `"speak slower"` | Decreases TTS speech rate |
| `"speak faster"` | Increases TTS speech rate |
| `"scroll down"` / `"scroll up"` | Scrolls the viewport smoothly |
| `"close tab"` / `"new tab"` | Tab management hotkeys |

---

## Safety and Confirmation

For any potentially destructive action (file deletions, financial checkout, form submission, email sending), EchoNav pauses and asks:

> *"Clicking delete button. Say yes to confirm, or no to cancel."*

The agent waits 15 seconds for verbal confirmation (`"yes"`). If the user says `"no"` or remains silent, the action is cancelled immediately.

---

## Verification & Automated Tests

EchoNav maintains a 100% automated test pass rate with complete headless support.

Run the full test suite:
```bash
pytest -v
```

Test suite coverage:
- `test_agent.py`: Agent goal loops, coordinate scaling, UIA resolution, blacklist mechanics, and CDP fast-path
- `test_annotate.py`: Set-of-Mark visual annotation and monitor offset calculations
- `test_browser_cdp.py`: Chrome DevTools Protocol connections, DOM extraction, and navigation
- `test_cli.py`: Unified CLI parser, subcommands, and mock console
- `test_commands.py`: System 1 voice command interceptor and Laya routing
- `test_executor.py`: PyAutoGUI execution, scrolling, and keyboard actions
- `test_laya_engine.py`: Convai Laya classification, destructive scoring, and heuristic fallbacks
- `test_listener.py`: Push-to-talk audio listener and buffering
- `test_main.py`: Main event loop, thread dispatching, and confirmation routing
- `test_overlay.py`: HUD queue synchronization and visual status states
- `test_screen.py`: Primary monitor screen capture and synthetic buffer fallback
- `test_stt.py`: Whisper speech transcription and RMS silence thresholding
- `test_tts.py`: Speech synthesis queuing, rates, and interruption
- `test_ui_tree.py`: Windows UI Automation accessibility tree traversal and element filtering
- `test_vision.py`: Multi-provider fallback (Groq -> Gemini -> Heuristic) and prompt formatting

**Total: 105 passing tests.**

---

## License

This project is licensed under the MIT License.
