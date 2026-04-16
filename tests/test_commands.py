import pytest
import commands

def test_check_command_read_page_returns_true(mocker):
    mocker.patch("commands._read_page")
    assert commands.check_command("read the page") is True

def test_check_command_read_page_case_insensitive(mocker):
    mocker.patch("commands._read_page")
    assert commands.check_command("READ THE PAGE") is True

def test_check_command_where_am_i_returns_true(mocker):
    mocker.patch("commands._where_am_i")
    assert commands.check_command("where am i") is True

def test_check_command_go_back_returns_true(mocker):
    mocker.patch("commands._go_back")
    assert commands.check_command("go back") is True

def test_check_command_stop_returns_true(mocker):
    mocker.patch("commands._stop")
    assert commands.check_command("stop") is True

def test_check_command_cancel_returns_true(mocker):
    mocker.patch("commands._stop")
    assert commands.check_command("please cancel that") is True

def test_check_command_repeat_returns_true(mocker):
    mocker.patch("commands._repeat")
    assert commands.check_command("say that again") is True

def test_check_command_speak_slower_returns_true(mocker):
    mocker.patch("commands._slower")
    assert commands.check_command("speak slower") is True

def test_check_command_unknown_returns_false(mocker):
    assert commands.check_command("open gmail") is False

def test_stop_raises_stop_command(mocker):
    mocker.patch("commands.tts.speak")
    with pytest.raises(commands.StopCommand):
        commands._stop()
