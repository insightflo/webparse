from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path

from hyocr.adapters.apple import _page_from_payload
from hyocr.config import resolve_glm_command
from hyocr.models import OCRPage


class GLMOCRAdapter:
    name = "glm"

    def __init__(self, command_template: str | None) -> None:
        self.command_template = resolve_glm_command(command_template)

    def is_available(self) -> bool:
        return bool(self.command_template)

    def ocr_image(self, image_path: Path, page_number: int) -> OCRPage:
        if not self.command_template:
            raise RuntimeError(
                "GLM OCR is not configured. Set HYOCR_GLM_CMD or add scripts/parse_with_glmocr_sdk.sh."
            )

        command = self.command_template.format(
            input=shlex.quote(str(image_path)),
            page=page_number,
        )
        completed = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        stdout = completed.stdout.strip()
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            payload = {
                "raw_text": stdout,
                "markdown": stdout,
                "confidence": None,
                "blocks": [],
                "tables": [],
                "meta": {},
            }
        return _page_from_payload(payload, source=image_path, page_number=page_number, engine="glm")
