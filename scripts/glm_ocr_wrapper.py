#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_PROMPT = (
    "Convert this document page to clean markdown. Preserve reading order, tables, "
    "lists, headings, code blocks, and visible labels."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpenAI-compatible wrapper for GLM-OCR.")
    parser.add_argument("input", help="Image path")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    base_url = os.getenv("GLM_OCR_OPENAI_BASE_URL")
    model = os.getenv("GLM_OCR_MODEL", "zai-org/GLM-OCR")
    api_key = os.getenv("GLM_OCR_API_KEY", "dummy")
    if not base_url:
        raise RuntimeError("GLM_OCR_OPENAI_BASE_URL is required.")

    mime = mimetypes.guess_type(input_path.name)[0] or "image/png"
    image_b64 = base64.b64encode(input_path.read_bytes()).decode("ascii")
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": args.prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
                ],
            }
        ],
    }

    request = urllib.request.Request(
        url=base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GLM endpoint error: {detail}") from exc

    choices = body.get("choices", [])
    if not choices:
        raise RuntimeError("GLM endpoint returned no choices.")

    content = choices[0]["message"]["content"]
    if isinstance(content, list):
        content = "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    output = {
        "raw_text": content,
        "markdown": content,
        "confidence": None,
        "blocks": [],
        "tables": [],
        "meta": {"endpoint": base_url, "model": model},
    }
    json.dump(output, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
