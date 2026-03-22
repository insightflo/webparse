from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def render_pdf_pages(pdf_path: Path, output_dir: Path, renderer: str = "pdftoppm") -> list[Path]:
    if shutil.which(renderer) is None:
        raise RuntimeError(f"PDF renderer '{renderer}' is not installed or not on PATH.")

    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = output_dir / "page"
    command = [renderer, "-png", str(pdf_path), str(prefix)]
    subprocess.run(command, check=True, capture_output=True, text=True)
    return sorted(output_dir.glob("page-*.png"))
