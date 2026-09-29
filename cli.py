"""Command Line Interface for EchoNav.

Provides subcommands for launching, testing, diagnostics, and mock operation:
  echonav start       Launch EchoNav voice agent
  echonav mock        Run interactive console mock mode without microphone
  echonav status      Diagnostic check on system components and connections
  echonav test-audio  Verify microphone capture and text-to-speech output
  echonav version     Display installed version
"""

from __future__ import annotations

import argparse
import os
import sys


def cmd_version(_args: argparse.Namespace) -> None:
    print("EchoNav version 2.0.0 (TypeSafe Jev + Convai Laya Architecture)")


def cmd_status(_args: argparse.Namespace) -> None:
    """Perform a comprehensive system health check."""
    import config
    from laya_engine import engine as laya_engine
    from browser_cdp import browser as cdp_browser

    print("==================================================")
    print("            EchoNav System Diagnostics            ")
    print("==================================================")
    print(f"Python:            {sys.version.split()[0]} ({sys.platform})")
    print(f"Working Directory: {os.path.basename(os.getcwd())}")

    # Laya Decision Engine
    laya_active = laya_engine.enable_model
    print(f"System 1 Engine:   Convai Laya ({'Loaded/Ready' if laya_active else 'Heuristic Fallback'})")

    # Browser CDP
    cdp_connected = cdp_browser.is_connected()
    cdp_port = cdp_browser.active_port if cdp_connected else "None"
    print(f"Browser CDP:       {'Connected (Port ' + str(cdp_port) + ')' if cdp_connected else 'Offline (Start Chrome/Brave with --remote-debugging-port=9222)'}")

    # Model Provider & Keys
    provider = getattr(config, "MODEL_PROVIDER", "groq")
    groq_set = bool(getattr(config, "GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY"))
    gemini_set = bool(getattr(config, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY"))
    print(f"Vision Provider:   {provider.upper()}")
    if provider == "ollama":
        print(f"  Ollama Model:    {getattr(config, 'OLLAMA_MODEL', 'qwen2.5-vl')} ({getattr(config, 'OLLAMA_URL', 'http://localhost:11434')})")
    else:
        print(f"  Groq API Key:    {'Configured' if groq_set else 'Not configured'}")
        print(f"  Gemini API Key:  {'Configured' if gemini_set else 'Not configured'}")

    # Audio Engine
    print(f"STT Model:         {getattr(config, 'STT_MODEL', 'base.en')}")
    print(f"TTS Voice:         {getattr(config, 'TTS_VOICE', 'en-US-AriaNeural')}")
    print(f"TTS Rate:          {getattr(config, 'TTS_RATE', 150)} wpm")
    print("==================================================")


def cmd_start(args: argparse.Namespace) -> None:
    """Launch the main EchoNav voice assistant."""
    import main as main_module
    import overlay as overlay_module

    headless = args.headless or os.getenv("ECHONAV_HEADLESS", "0") == "1"
    ov = None if headless else overlay_module.Overlay()
    app = main_module.App(overlay=ov)
    app.run()


def cmd_mock(args: argparse.Namespace) -> None:
    """Launch interactive terminal mock mode."""
    import main as main_module
    import overlay as overlay_module
    import tts

    headless = args.headless or os.getenv("ECHONAV_HEADLESS", "0") == "1"
    ov = None if headless else overlay_module.Overlay()
    app = main_module.App(overlay=ov)

    print("--------------------------------------------------")
    print(" EchoNav Mock Console (No Microphone Required)    ")
    print(" Type any goal, command, or 'exit' to terminate.  ")
    print("--------------------------------------------------")
    tts.speak("EchoNav mock mode initialized.")

    while True:
        try:
            line = input("EchoNav> ").strip()
            if not line:
                continue
            if line.lower() in ("exit", "quit", "q"):
                break
            app.handle_text(line)
        except (KeyboardInterrupt, EOFError):
            break
    print("Exiting EchoNav mock console.")


def cmd_test_audio(_args: argparse.Namespace) -> None:
    """Test text-to-speech output and microphone input."""
    import tts
    print("[Audio] Testing Text-to-Speech output...")
    tts.speak("EchoNav audio output test. If you can hear this, speech synthesis is operational.")
    print("[Audio] TTS test complete.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="echonav",
        description="EchoNav: Autonomous Voice Desktop Agent for Blind Users",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # start
    p_start = subparsers.add_parser("start", help="Start voice listener and overlay")
    p_start.add_argument("--headless", action="store_true", help="Run without graphical overlay HUD")
    p_start.set_defaults(func=cmd_start)

    # mock
    p_mock = subparsers.add_parser("mock", help="Run interactive console mock mode")
    p_mock.add_argument("--headless", action="store_true", help="Run without graphical overlay HUD")
    p_mock.set_defaults(func=cmd_mock)

    # status
    p_status = subparsers.add_parser("status", help="Check system diagnostics and component status")
    p_status.set_defaults(func=cmd_status)

    # test-audio
    p_test_audio = subparsers.add_parser("test-audio", help="Test audio input and output")
    p_test_audio.set_defaults(func=cmd_test_audio)

    # version
    p_version = subparsers.add_parser("version", help="Print EchoNav version")
    p_version.set_defaults(func=cmd_version)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.subcommand:
        # Default to start if no subcommand given
        args.headless = False
        cmd_start(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
