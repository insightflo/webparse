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
from typing import Optional

from .cleaner import clean_html
from .extractor import extract
from .formatter import format_document


def _read_stdin() -> Optional[str]:
    """Read HTML from stdin if data is piped."""
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return None


def _read_file(path: str) -> str:
    """Read HTML from a file path."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _fetch_url(url: str) -> str:
    """Fetch HTML from a URL using requests (simple, no JS rendering)."""
    import requests
    try:
        resp = requests.get(url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (compatible; webparse/0.1)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        })
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        return resp.text
    except requests.exceptions.SSLError:
        # Retry without SSL verification as a fallback
        import warnings
        warnings.warn("SSL verification failed, retrying without verification", stacklevel=2)
        resp = requests.get(url, timeout=30, verify=False, headers={
            "User-Agent": "Mozilla/5.0 (compatible; webparse/0.1)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        })
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        return resp.text


def parse_html(html: str) -> str:
    """
    [Purpose] Full pipeline: HTML string -> cleaned markdown.
    [Input] Raw HTML string.
    [Output] Clean structured markdown string.
    """
    soup = clean_html(html)
    doc = extract(soup)
    return format_document(doc)


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="webparse",
        description="Convert HTML to clean structured markdown for LLM consumption.",
    )
    parser.add_argument(
        "--file", "-f",
        help="Path to an HTML file to parse",
    )
    parser.add_argument(
        "--url", "-u",
        help="URL to fetch and parse (simple HTTP, no JS rendering)",
    )
    args = parser.parse_args(argv)

    html: Optional[str] = None

    if args.file:
        html = _read_file(args.file)
    elif args.url:
        html = _fetch_url(args.url)
    else:
        html = _read_stdin()

    if html is None:
        parser.print_help()
        sys.exit(1)

    result = parse_html(html)
    sys.stdout.write(result)


if __name__ == "__main__":
    main()
