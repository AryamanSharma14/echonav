"""Unit tests for EchoNav CLI module."""

import argparse
import cli


def test_cli_version(capsys):
    parser = cli.build_parser()
    args = parser.parse_args(["version"])
    args.func(args)

    captured = capsys.readouterr()
    assert "EchoNav version 2.0.0" in captured.out


def test_cli_status(capsys, mocker):
    mocker.patch("laya_engine.engine.enable_model", True)
    mocker.patch("browser_cdp.browser.is_connected", return_value=False)

    parser = cli.build_parser()
    args = parser.parse_args(["status"])
    args.func(args)

    captured = capsys.readouterr()
    assert "EchoNav System Diagnostics" in captured.out
    assert "System 1 Engine:" in captured.out
    assert "Browser CDP:" in captured.out


def test_cli_parser_subcommands():
    parser = cli.build_parser()

    args_start = parser.parse_args(["start", "--headless"])
    assert args_start.subcommand == "start"
    assert args_start.headless is True

    args_mock = parser.parse_args(["mock"])
    assert args_mock.subcommand == "mock"
    assert args_mock.headless is False

    args_status = parser.parse_args(["status"])
    assert args_status.subcommand == "status"

    args_audio = parser.parse_args(["test-audio"])
    assert args_audio.subcommand == "test-audio"


def test_cli_test_audio(mocker, capsys):
    mock_speak = mocker.patch("tts.speak")
    parser = cli.build_parser()
    args = parser.parse_args(["test-audio"])
    args.func(args)

    mock_speak.assert_called_once()
    assert "operational" in mock_speak.call_args[0][0]


def test_cli_mock_mode_exit(mocker, capsys):
    mocker.patch("main.App")
    mocker.patch("tts.speak")
    mocker.patch("builtins.input", side_effect=["exit"])

    parser = cli.build_parser()
    args = parser.parse_args(["mock", "--headless"])
    args.func(args)

    captured = capsys.readouterr()
    assert "Mock Console" in captured.out
