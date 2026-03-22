"""
[File Purpose] CLI entry point for webparse. Handles three input modes:
  1. stdin pipe  (echo "<html>..." | python -m webparse)
  2. --file path (python -m webparse --file page.html)
  3. --url URL   (python -m webparse --url https://example.com)
[Main Flow] Read HTML -> clean -> extract -> format -> print to stdout.
[External Connections] Uses cleaner, extractor, formatter modules.
"""

from __future__ import annotations

import argparse
import sys
from typing import Literal
from typing import Optional

from .cleaner import clean_html
from .extractor import extract
from .formatter import format_document, format_document_html, format_document_json


OutputFormat = Literal["markdown", "json", "html"]


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _read_stdin() -> Optional[str]:
    """Read HTML from stdin if data is piped."""
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return None


def _read_file(path: str) -> str:
    """Read HTML from a file path."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _fetch_url(url: str, *, timeout: int = 30) -> str:
    """Fetch HTML from a URL using requests (simple, no JS rendering)."""
    import requests

    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; webparse/0.1)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            },
        )
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        return resp.text
    except requests.exceptions.SSLError:
        # Retry without SSL verification as a fallback
        import warnings

        warnings.warn(
            "SSL verification failed, retrying without verification", stacklevel=2
        )
        resp = requests.get(
            url,
            timeout=timeout,
            verify=False,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; webparse/0.1)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            },
        )
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        return resp.text


def _fetch_url_rendered(url: str, *, timeout: int = 15) -> str:
    """Fetch HTML from a URL after JS rendering using Playwright."""
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is required for --render. Install with: "
            "pip install playwright && playwright install chromium"
        ) from exc

    timeout_ms = timeout * 1000
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=timeout_ms)
                return page.content()
            finally:
                browser.close()
    except PlaywrightTimeoutError as exc:
        raise TimeoutError(
            f"Timed out after {timeout}s while rendering URL: {url}"
        ) from exc
    except PlaywrightError as exc:
        raise RuntimeError(f"Playwright rendering failed for URL: {url}") from exc


def parse_html(html: str, output_format: OutputFormat = "markdown") -> str:
    """
    [Purpose] Full pipeline: HTML string -> cleaned markdown.
    [Input] Raw HTML string.
    [Output] Clean structured markdown string.
    """
    soup = clean_html(html)
    doc = extract(soup)
    if output_format == "json":
        return format_document_json(doc)
    if output_format == "html":
        return format_document_html(doc)
    return format_document(doc)


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="webparse",
        description="Convert HTML to clean structured markdown for LLM consumption.",
    )
    parser.add_argument(
        "--file",
        "-f",
        help="Path to an HTML file to parse",
    )
    parser.add_argument(
        "--url",
        "-u",
        help="URL to fetch and parse",
    )
    parser.add_argument(
        "--render",
        action="store_true",
        help="Render URL with Playwright before parsing (for JS-heavy pages)",
    )
    parser.add_argument(
        "--timeout",
        type=_positive_int,
        help="Timeout in seconds (default: 30 for HTTP, 15 for --render)",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json", "html"),
        default="markdown",
        help="Output format (default: markdown)",
    )
    args = parser.parse_args(argv)

    html: Optional[str] = None

    if args.file:
        html = _read_file(args.file)
    elif args.url:
        if args.render:
            render_timeout = args.timeout if args.timeout is not None else 15
            html = _fetch_url_rendered(args.url, timeout=render_timeout)
        else:
            request_timeout = args.timeout if args.timeout is not None else 30
            html = _fetch_url(args.url, timeout=request_timeout)
    else:
        html = _read_stdin()

    if html is None:
        parser.print_help()
        sys.exit(1)

    result = parse_html(html, output_format=args.format)
    sys.stdout.write(result)


if __name__ == "__main__":
    main()
