import socket

import pytest

from hyocr.adapters.glm import GLMOCRAdapter
from hyocr.config import PROJECT_ROOT


def _mlx_server_available(host: str = "127.0.0.1", port: int = 8080) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.2):
            return True
    except OSError:
        return False


_skip_reasons: list[str] = []
if not _mlx_server_available():
    _skip_reasons.append("MLX server is not running on 127.0.0.1:8080")
if not (PROJECT_ROOT / ".venv-sdk").is_dir():
    _skip_reasons.append(".venv-sdk directory is missing")
if not (PROJECT_ROOT / "scripts" / "parse_with_glmocr_sdk.sh").is_file():
    _skip_reasons.append("scripts/parse_with_glmocr_sdk.sh is missing")

pytestmark = [pytest.mark.skip(reason="; ".join(_skip_reasons))] if _skip_reasons else []


def test_glm_sdk_e2e_smoke() -> None:
    sample_input = PROJECT_ROOT / "tmp" / "sample.png"
    if not sample_input.is_file():
        pytest.skip(f"Missing E2E sample input: {sample_input}")

    page = GLMOCRAdapter(None).ocr_image(sample_input, page_number=1)

    assert page.engine == "glm"
    assert page.page == 1
    assert page.source == str(sample_input)
    assert isinstance(page.raw_text, str)
    assert isinstance(page.markdown, str)
