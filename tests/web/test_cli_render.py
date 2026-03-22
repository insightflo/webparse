import pytest

from webparse import cli


def test_main_url_without_render_uses_requests_fetch(monkeypatch, capsys):
    captured: dict[str, object] = {}

    def fake_fetch(url: str, *, timeout: int = 30) -> str:
        captured["url"] = url
        captured["timeout"] = timeout
        return "<html><body><main><p>static content</p></main></body></html>"

    def fail_render(*args, **kwargs):
        raise AssertionError("render fetch should not be used without --render")

    monkeypatch.setattr(cli, "_fetch_url", fake_fetch)
    monkeypatch.setattr(cli, "_fetch_url_rendered", fail_render)

    cli.main(["--url", "https://example.com"])
    out = capsys.readouterr().out

    assert "static content" in out
    assert captured == {"url": "https://example.com", "timeout": 30}


def test_main_url_with_render_uses_playwright_fetch(monkeypatch, capsys):
    captured: dict[str, object] = {}

    def fail_fetch(*args, **kwargs):
        raise AssertionError("requests fetch should not be used with --render")

    def fake_render_fetch(url: str, *, timeout: int = 15) -> str:
        captured["url"] = url
        captured["timeout"] = timeout
        return "<html><body><main><p>dynamic content</p></main></body></html>"

    monkeypatch.setattr(cli, "_fetch_url", fail_fetch)
    monkeypatch.setattr(cli, "_fetch_url_rendered", fake_render_fetch)

    cli.main(["--url", "https://example.com/app", "--render"])
    out = capsys.readouterr().out

    assert "dynamic content" in out
    assert captured == {"url": "https://example.com/app", "timeout": 15}


def test_main_url_with_render_accepts_custom_timeout(monkeypatch, capsys):
    captured: dict[str, object] = {}

    def fake_render_fetch(url: str, *, timeout: int = 15) -> str:
        captured["url"] = url
        captured["timeout"] = timeout
        return "<html><body><main><p>timeout test</p></main></body></html>"

    monkeypatch.setattr(cli, "_fetch_url_rendered", fake_render_fetch)

    cli.main(["--url", "https://example.com/spa", "--render", "--timeout", "22"])
    out = capsys.readouterr().out

    assert "timeout test" in out
    assert captured == {"url": "https://example.com/spa", "timeout": 22}


def test_timeout_argument_must_be_positive():
    with pytest.raises(SystemExit):
        cli.main(["--url", "https://example.com", "--timeout", "0"])
