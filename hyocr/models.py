from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class BBox:
    x: float
    y: float
    width: float
    height: float


@dataclass(slots=True)
class OCRBlock:
    text: str
    kind: str = "line"
    confidence: float | None = None
    bbox: BBox | None = None


@dataclass(slots=True)
class OCRTable:
    markdown: str
    confidence: float | None = None
    bbox: BBox | None = None


@dataclass(slots=True)
class OCRPage:
    source: str
    page: int
    engine: str
    raw_text: str
    markdown: str
    confidence: float | None = None
    blocks: list[OCRBlock] = field(default_factory=list)
    tables: list[OCRTable] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OCRDocument:
    source: str
    pages: list[OCRPage]
    selected_engine: str
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_markdown(self) -> str:
        chunks: list[str] = []
        multi_page = len(self.pages) > 1
        for page in self.pages:
            if multi_page:
                chunks.append(f"## Page {page.page}")
            chunks.append(page.markdown.strip() or page.raw_text.strip())
        return "\n\n".join(chunk for chunk in chunks if chunk)

