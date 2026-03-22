from __future__ import annotations

from hyocr.models import OCRPage


def score_page(page: OCRPage) -> float:
    text = page.raw_text.strip()
    if not text:
        return 0.0

    lines = [line for line in text.splitlines() if line.strip()]
    char_count = len(text)
    avg_line_length = char_count / max(len(lines), 1)
    confidence = (page.confidence or 0.0) * 30.0
    table_bonus = min(len(page.tables) * 8.0, 16.0)
    line_bonus = min(len(lines) * 1.2, 18.0)
    density_bonus = min(char_count / 40.0, 20.0)
    avg_line_bonus = min(avg_line_length, 16.0)

    penalty = 0.0
    weird_chars = sum(1 for char in text if ord(char) < 32 and char not in "\n\t")
    penalty += weird_chars * 3.0
    if avg_line_length < 3:
        penalty += 12.0

    return max(0.0, min(confidence + table_bonus + line_bonus + density_bonus + avg_line_bonus - penalty, 100.0))


def should_compare(primary: OCRPage, threshold: float) -> bool:
    return score_page(primary) < threshold
