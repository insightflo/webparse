import json
from pathlib import Path

from hyocr.merge_results import merge_apple_glm_files


def test_merge_results_preserves_apple_lines_and_adds_glm_missing_lines(tmp_path: Path) -> None:
    apple_json = tmp_path / "apple.json"
    glm_json = tmp_path / "glm.json"

    apple_payload = {
        "blocks": [
            {"text": "상호 (법인명)", "bbox": {"x": 0.1, "y": 0.7, "width": 0.2, "height": 0.03}},
            {"text": "인사이트플로", "bbox": {"x": 0.4, "y": 0.7, "width": 0.2, "height": 0.03}},
            {"text": "사업자등록일", "bbox": {"x": 0.1, "y": 0.5, "width": 0.2, "height": 0.03}},
            {"text": "2025년 06월 17일", "bbox": {"x": 0.4, "y": 0.5, "width": 0.25, "height": 0.03}},
        ],
        "raw_text": "",
        "markdown": "",
        "tables": [],
    }
    glm_payload = [
        [
            {"label": "table", "content": "상호 (번인명)\n인사이트플로\n사업자등록일\n2025년 06월 17일\n업태\n정보통신업"},
            {"label": "text", "content": "공동사업자\n해당사항이 없습니다."},
        ]
    ]

    apple_json.write_text(json.dumps(apple_payload, ensure_ascii=False), encoding="utf-8")
    glm_json.write_text(json.dumps(glm_payload, ensure_ascii=False), encoding="utf-8")

    merged = merge_apple_glm_files(apple_json, glm_json)

    assert "상호 (법인명)\t인사이트플로" in merged["markdown"]
    assert "업태" in merged["markdown"]
    assert "정보통신업" in merged["markdown"]
    assert merged["meta"]["merged_line_count"] > merged["meta"]["apple_line_count"]


def test_merge_results_skips_obvious_duplicate_lines(tmp_path: Path) -> None:
    apple_json = tmp_path / "apple.json"
    glm_json = tmp_path / "glm.json"

    apple_payload = {
        "blocks": [
            {"text": "사업자등록번호", "bbox": {"x": 0.1, "y": 0.7, "width": 0.2, "height": 0.03}},
            {"text": "820-09-03326", "bbox": {"x": 0.4, "y": 0.7, "width": 0.2, "height": 0.03}},
        ],
        "raw_text": "",
        "markdown": "",
        "tables": [],
    }
    glm_payload = [[{"label": "table", "content": "사업자등록번호\n820-09-03326"}]]

    apple_json.write_text(json.dumps(apple_payload, ensure_ascii=False), encoding="utf-8")
    glm_json.write_text(json.dumps(glm_payload, ensure_ascii=False), encoding="utf-8")

    merged = merge_apple_glm_files(apple_json, glm_json)
    lines = merged["markdown"].splitlines()

    assert lines.count("사업자등록번호\t820-09-03326") == 1
