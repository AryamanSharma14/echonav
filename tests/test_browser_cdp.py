import pytest
from browser_cdp import BrowserCDPEngine, BrowserTab, DOMElement


def test_is_connected_false_when_no_browser(mocker):
    engine = BrowserCDPEngine(ports=[99999])
    assert engine.is_connected() is False
    assert engine.active_port is None


def test_is_connected_true_when_version_responds(mocker):
    engine = BrowserCDPEngine(ports=[9222])
    mock_resp = mocker.MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp
    mocker.patch("urllib.request.urlopen", return_value=mock_resp)

    assert engine.is_connected() is True
    assert engine.active_port == 9222


def test_get_tabs_parses_json(mocker):
    engine = BrowserCDPEngine(ports=[9222])
    engine.active_port = 9222

    mock_resp = mocker.MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b'''[
        {"id": "tab1", "title": "Google", "url": "https://google.com", "type": "page", "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/page/tab1"},
        {"id": "tab2", "title": "Service Worker", "url": "", "type": "service_worker"}
    ]'''
    mock_resp.__enter__.return_value = mock_resp
    mocker.patch("urllib.request.urlopen", return_value=mock_resp)

    tabs = engine.get_tabs()
    assert len(tabs) == 1
    assert tabs[0].id == "tab1"
    assert tabs[0].title == "Google"


def test_extract_interactive_elements(mocker):
    engine = BrowserCDPEngine(ports=[9222])
    mocker.patch.object(engine, "get_active_tab", return_value=BrowserTab("t1", "Test", "http://test", "ws://"))
    mocker.patch.object(engine, "evaluate_js", return_value=[
        {"node_id": 1, "tag": "button", "name": "Submit", "role": "button", "bbox": [10, 20, 100, 30], "is_clickable": True},
        {"node_id": 2, "tag": "input", "name": "Email", "role": "textbox", "bbox": [10, 60, 200, 30], "is_clickable": True},
    ])

    elements = engine.extract_interactive_elements()
    assert len(elements) == 2
    assert elements[0].node_id == 1
    assert elements[0].tag == "button"
    assert elements[0].center == (60, 35)


def test_navigate_prepends_https(mocker):
    engine = BrowserCDPEngine(ports=[9222])
    mocker.patch.object(engine, "get_active_tab", return_value=BrowserTab("t1", "Test", "http://test", "ws://"))
    mock_cmd = mocker.patch.object(engine, "_send_command", return_value=True)

    success = engine.navigate("amazon.com")
    assert success is True
    mock_cmd.assert_called_once_with("t1", "Page.navigate", {"url": "https://amazon.com"})
