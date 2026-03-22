import json
import shlex
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from hyocr.adapters.glm import GLMOCRAdapter


def test_glm_adapter_uses_project_sdk_script_as_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    script_path = tmp_path / "parse_with_glmocr_sdk.sh"
    script_path.write_text("#!/bin/zsh\n", encoding="utf-8")
    monkeypatch.setattr("hyocr.config.DEFAULT_GLM_SCRIPT", script_path)

    image_path = tmp_path / "scan file.png"
    payload = {
        "raw_text": "hello",
        "markdown": "# hello",
        "confidence": 0.9,
        "blocks": [{"text": "hello", "kind": "line", "confidence": 0.9}],
        "tables": [],
        "meta": {"source": "mock"},
    }

    adapter = GLMOCRAdapter(None)

    with patch(
        "hyocr.adapters.glm.subprocess.run",
        return_value=SimpleNamespace(stdout=json.dumps(payload)),
    ) as run_mock:
        page = adapter.ocr_image(image_path, page_number=3)

    assert adapter.is_available()
    command = run_mock.call_args.args[0]
    assert shlex.quote(str(script_path)) in command
    assert shlex.quote(str(image_path)) in command
    assert page.engine == "glm"
    assert page.page == 3
    assert page.raw_text == "hello"
    assert page.markdown == "# hello"
    assert page.meta == {"source": "mock"}


def test_glm_adapter_wraps_plain_text_stdout_when_json_is_missing() -> None:
    adapter = GLMOCRAdapter("glm-runner --input {input} --page {page}")

    with patch(
        "hyocr.adapters.glm.subprocess.run",
        return_value=SimpleNamespace(stdout="plain text output\n"),
    ) as run_mock:
        page = adapter.ocr_image(Path("/tmp/plain.png"), page_number=2)

    assert "--page 2" in run_mock.call_args.args[0]
    assert page.raw_text == "plain text output"
    assert page.markdown == "plain text output"
    assert page.blocks == []
    assert page.tables == []
    assert page.meta == {}


def test_glm_adapter_raises_without_env_or_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("hyocr.config.DEFAULT_GLM_SCRIPT", tmp_path / "missing.sh")
    adapter = GLMOCRAdapter(None)

    assert not adapter.is_available()
    with pytest.raises(RuntimeError, match="GLM OCR is not configured"):
        adapter.ocr_image(tmp_path / "missing.png", page_number=1)
