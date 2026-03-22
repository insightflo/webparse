#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_PROMPT = "Text Recognition:"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local Ollama wrapper for GLM-OCR.")
    parser.add_argument("input", help="Image path")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    model = os.getenv("GLM_OCR_MODEL", "glm-ocr")
    image_b64 = base64.b64encode(input_path.read_bytes()).decode("ascii")
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": args.prompt,
                "images": [image_b64],
            }
        ],
        "stream": False,
    }

    request = urllib.request.Request(
        url=host + "/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama endpoint error: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach Ollama at {host}. Is `ollama serve` running?") from exc

    content = body.get("message", {}).get("content", "").strip()
    output = {
        "raw_text": content,
        "markdown": content,
        "confidence": None,
        "blocks": [],
        "tables": [],
        "meta": {"backend": "ollama", "host": host, "model": model},
    }
    json.dump(output, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
