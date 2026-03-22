from __future__ import annotations

import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from statistics import median
from typing import Any


_GLM_ALLOWED_LABELS = {"text", "table"}
_SIMILARITY_MATCH = 0.72
_SIMILARITY_NEAR = 0.55


@dataclass(slots=True)
class LineCandidate:
    text: str
    normalized: str
    source: str
    order: int


def merge_apple_glm_files(apple_json: str | Path, glm_json: str | Path) -> dict[str, Any]:
    apple_payload = json.loads(Path(apple_json).read_text(encoding="utf-8"))
    glm_payload = json.loads(Path(glm_json).read_text(encoding="utf-8"))

    apple_lines = _extract_apple_lines(apple_payload)
    glm_lines = _extract_glm_lines(glm_payload)
    merged_lines = _merge_line_candidates(apple_lines, glm_lines)
    merged_text = "\n".join(line.text for line in merged_lines if line.text.strip())

    return {
        "raw_text": merged_text,
        "markdown": merged_text,
        "meta": {
            "engines": ["apple", "glm_sdk"],
            "apple_line_count": len(apple_lines),
            "glm_line_count": len(glm_lines),
            "merged_line_count": len(merged_lines),
        },
        "lines": [
            {
                "text": line.text,
                "source": line.source,
                "order": line.order,
            }
            for line in merged_lines
        ],
    }


def _extract_apple_lines(payload: dict[str, Any]) -> list[LineCandidate]:
    blocks = payload.get("blocks", [])
    if not blocks:
        return _lines_from_text(payload.get("raw_text", ""), source="apple")

    heights = [float(block["bbox"]["height"]) for block in blocks if block.get("bbox")]
    tolerance = max(median(heights) * 0.7, 0.008) if heights else 0.012

    rows: list[dict[str, Any]] = []
    ordered_blocks = sorted(
        (block for block in blocks if block.get("text")),
        key=lambda block: (
            -_bbox_center_y(block.get("bbox")),
            _bbox_x(block.get("bbox")),
        ),
    )

    for block in ordered_blocks:
        center_y = _bbox_center_y(block.get("bbox"))
        matched_row = None
        for row in rows:
            if abs(row["y"] - center_y) <= tolerance:
                matched_row = row
                break
        if matched_row is None:
            matched_row = {"y": center_y, "blocks": []}
            rows.append(matched_row)
        matched_row["blocks"].append(block)

    rows.sort(key=lambda row: -row["y"])
    result: list[LineCandidate] = []
    for index, row in enumerate(rows):
        parts = [item.get("text", "").strip() for item in sorted(row["blocks"], key=lambda item: _bbox_x(item.get("bbox")))]
        text = "\t".join(part for part in parts if part)
        if _keep_line(text):
            result.append(_candidate(text, source="apple", order=index))
    return result


def _extract_glm_lines(payload: Any) -> list[LineCandidate]:
    items = payload
    if isinstance(items, list) and items and isinstance(items[0], list):
        items = items[0]
    if not isinstance(items, list):
        return []

    result: list[LineCandidate] = []
    order = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("label") not in _GLM_ALLOWED_LABELS:
            continue
        content = item.get("content") or ""
        for raw_line in content.splitlines():
            line = _clean_glm_line(raw_line)
            if _keep_line(line):
                result.append(_candidate(line, source="glm_sdk", order=order))
                order += 1
    return result


def _merge_line_candidates(apple_lines: list[LineCandidate], glm_lines: list[LineCandidate]) -> list[LineCandidate]:
    if not apple_lines:
        return glm_lines
    if not glm_lines:
        return apple_lines

    apple_match_indexes: list[int | None] = []
    apple_match_scores: list[float] = []
    for glm_line in glm_lines:
        score, index = _best_match(glm_line, apple_lines)
        apple_match_scores.append(score)
        apple_match_indexes.append(index)

    before: dict[int, list[LineCandidate]] = {}
    append: list[LineCandidate] = []
    after: dict[int, list[LineCandidate]] = {}
    seen = {line.normalized for line in apple_lines}

    for glm_index, glm_line in enumerate(glm_lines):
        if glm_line.normalized in seen:
            continue
        match_score = apple_match_scores[glm_index]
        match_index = apple_match_indexes[glm_index]
        if match_index is not None and match_score >= _SIMILARITY_MATCH:
            continue
        if len(glm_line.normalized) <= 6 and match_index is not None and match_score >= _SIMILARITY_NEAR:
            continue
        if not _line_quality_ok(glm_line.text):
            continue

        prev_anchor = _find_anchor(apple_match_indexes, apple_match_scores, glm_index, -1)
        next_anchor = _find_anchor(apple_match_indexes, apple_match_scores, glm_index, 1)

        candidate = glm_line
        if prev_anchor is not None:
            after.setdefault(prev_anchor, []).append(candidate)
        elif next_anchor is not None:
            before.setdefault(next_anchor, []).append(candidate)
        else:
            append.append(candidate)
        seen.add(glm_line.normalized)

    merged: list[LineCandidate] = []
    for apple_index, apple_line in enumerate(apple_lines):
        merged.extend(before.get(apple_index, []))
        merged.append(apple_line)
        merged.extend(after.get(apple_index, []))
    merged.extend(append)
    return merged


def _find_anchor(match_indexes: list[int | None], match_scores: list[float], current_index: int, direction: int) -> int | None:
    scan_range = range(current_index + direction, len(match_indexes), direction)
    for probe in scan_range:
        index = match_indexes[probe]
        score = match_scores[probe]
        if index is not None and score >= _SIMILARITY_NEAR:
            return index
    return None


def _best_match(candidate: LineCandidate, existing: list[LineCandidate]) -> tuple[float, int | None]:
    best_score = 0.0
    best_index: int | None = None
    for index, current in enumerate(existing):
        variants = [current.normalized]
        if "\t" in current.text:
            variants.extend(_normalize_text(part) for part in current.text.split("\t") if part.strip())
        for variant in variants:
            score = SequenceMatcher(None, candidate.normalized, variant).ratio()
            if score > best_score:
                best_score = score
                best_index = index
    return best_score, best_index


def _candidate(text: str, source: str, order: int) -> LineCandidate:
    return LineCandidate(text=text.strip(), normalized=_normalize_text(text), source=source, order=order)


def _lines_from_text(text: str, source: str) -> list[LineCandidate]:
    result: list[LineCandidate] = []
    for index, raw_line in enumerate(text.splitlines()):
        if _keep_line(raw_line):
            result.append(_candidate(raw_line, source=source, order=index))
    return result


def _normalize_text(text: str) -> str:
    folded = text.casefold()
    folded = folded.replace("（", "(").replace("）", ")")
    folded = re.sub(r"\s+", "", folded)
    folded = re.sub(r"[^0-9a-z가-힣()\-./:]", "", folded)
    return folded


def _clean_glm_line(text: str) -> str:
    line = text.strip()
    line = line.replace("（", "(").replace("）", ")")
    line = re.sub(r"\s+", " ", line)
    return line


def _keep_line(text: str) -> bool:
    line = text.strip()
    if not line:
        return False
    if line.startswith("![") or line.startswith("```") or line in {"/", "REPUBLI"}:
        return False
    return True


def _line_quality_ok(text: str) -> bool:
    core = text.strip()
    if len(core) < 2:
        return False
    allowed = sum(1 for char in core if char.isalnum() or char.isspace() or char in "()-./:%,*[]【】")
    ratio = allowed / max(len(core), 1)
    return ratio >= 0.65


def _bbox_center_y(bbox: dict[str, Any] | None) -> float:
    if not bbox:
        return 0.0
    return float(bbox["y"]) + float(bbox["height"]) / 2.0


def _bbox_x(bbox: dict[str, Any] | None) -> float:
    if not bbox:
        return 0.0
    return float(bbox["x"])
