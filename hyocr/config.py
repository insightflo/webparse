from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GLM_SCRIPT = PROJECT_ROOT / "scripts" / "parse_with_glmocr_sdk.sh"


def resolve_glm_command(command_template: str | None) -> str | None:
    stripped = (command_template or "").strip()
    if stripped:
        return stripped
    if DEFAULT_GLM_SCRIPT.is_file():
        return f"{shlex.quote(str(DEFAULT_GLM_SCRIPT))} {{input}}"
    return None


@dataclass(slots=True)
class Settings:
    apple_bin: Path
    glm_command: str | None
    pdf_renderer: str
    compare_threshold: float
    temp_dir: Path

    @classmethod
    def load(cls) -> "Settings":
        default_apple = PROJECT_ROOT / "apple-vision-ocr" / ".build" / "release" / "apple-vision-ocr"
        temp_dir = Path(os.getenv("HYOCR_TEMP_DIR", PROJECT_ROOT / "tmp"))
        return cls(
            apple_bin=Path(os.getenv("HYOCR_APPLE_BIN", default_apple)),
            glm_command=resolve_glm_command(os.getenv("HYOCR_GLM_CMD")),
            pdf_renderer=os.getenv("HYOCR_PDF_RENDERER", "pdftoppm"),
            compare_threshold=float(os.getenv("HYOCR_COMPARE_THRESHOLD", "55")),
            temp_dir=temp_dir,
        )
