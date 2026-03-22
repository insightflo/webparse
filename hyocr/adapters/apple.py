from __future__ import annotations

import json
import subprocess
from pathlib import Path

from hyocr.models import BBox, OCRBlock, OCRPage, OCRTable


class AppleVisionAdapter:
    name = "apple"

    def __init__(self, apple_bin: Path) -> None:
        self.apple_bin = apple_bin

    def is_available(self) -> bool:
        return self.apple_bin.exists()

    def ocr_image(self, image_path: Path, page_number: int) -> OCRPage:
        if not self.is_available():
            raise RuntimeError(f"Apple Vision binary not found at {self.apple_bin}")

        command = [str(self.apple_bin), "ocr", str(image_path)]
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
        payload = json.loads(completed.stdout)
        return _page_from_payload(payload, source=image_path, page_number=page_number, engine="apple")


def _page_from_payload(payload: dict, source: Path, page_number: int, engine: str) -> OCRPage:
    blocks = [
        OCRBlock(
            text=item.get("text", ""),
            kind=item.get("kind", "line"),
            confidence=item.get("confidence"),
            bbox=_bbox_from_dict(item.get("bbox")),
        )
        for item in payload.get("blocks", [])
    ]
    tables = [
        OCRTable(
            markdown=item.get("markdown", ""),
            confidence=item.get("confidence"),
            bbox=_bbox_from_dict(item.get("bbox")),
        )
        for item in payload.get("tables", [])
    ]
    return OCRPage(
        source=str(source),
        page=page_number,
        engine=engine,
        raw_text=payload.get("raw_text", ""),
        markdown=payload.get("markdown", payload.get("raw_text", "")),
        confidence=payload.get("confidence"),
        blocks=blocks,
        tables=tables,
        meta=payload.get("meta", {}),
    )


def _bbox_from_dict(payload: dict | None) -> BBox | None:
    if not payload:
        return None
    return BBox(
        x=float(payload["x"]),
        y=float(payload["y"]),
        width=float(payload["width"]),
        height=float(payload["height"]),
    )
