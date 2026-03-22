"""
[File Purpose] Data classes representing extracted web content elements.
[Main Flow] Cleaner -> Extractor populates these models -> Formatter reads them.
[External Connections] Used by extractor.py and formatter.py.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum, auto
from typing import Any, Optional


class ElementType(Enum):
    """Enumeration of extractable content element types."""

    HEADING = auto()
    PARAGRAPH = auto()
    TABLE = auto()
    LIST = auto()
    BLOCKQUOTE = auto()
    CODE_BLOCK = auto()
    HORIZONTAL_RULE = auto()
    IMAGE = auto()


@dataclass
class Heading:
    """A heading element with its hierarchy level (1-6)."""

    level: int
    text: str


@dataclass
class TableCell:
    """A single cell in a table."""

    text: str
    is_header: bool = False
    colspan: int = 1
    rowspan: int = 1


@dataclass
class TableRow:
    """A row of cells in a table."""

    cells: list[TableCell] = field(default_factory=list)


@dataclass
class Table:
    """A complete table with optional header and body rows."""

    rows: list[TableRow] = field(default_factory=list)
    caption: Optional[str] = None


@dataclass
class ListItem:
    """A single list item, potentially containing nested sub-lists."""

    text: str
    children: list[ListItem] = field(default_factory=list)


@dataclass
class ContentList:
    """An ordered or unordered list."""

    items: list[ListItem] = field(default_factory=list)
    ordered: bool = False


@dataclass
class Paragraph:
    """A paragraph of text content."""

    text: str
    is_block: bool = False  # True if from a <p> tag; False if from a bare text node


@dataclass
class Blockquote:
    """A blockquote element."""

    text: str


@dataclass
class CodeBlock:
    """A preformatted code block."""

    code: str
    language: Optional[str] = None


@dataclass
class Image:
    """An image element with src and optional alt text."""

    src: str
    alt: str = ""


@dataclass
class ContentElement:
    """
    Wrapper that holds any extractable element with its type and
    source-order position for maintaining document flow.
    """

    element_type: ElementType
    content: (
        Heading
        | Table
        | ContentList
        | Paragraph
        | Blockquote
        | CodeBlock
        | Image
        | None
    )
    source_order: int = 0
    confidence: float = 1.0
    source_path: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": self.element_type.name.lower(),
            "source_order": self.source_order,
            "confidence": self.confidence,
            "source_path": self.source_path,
        }
        if self.content is None:
            payload["content"] = None
        else:
            payload["content"] = asdict(self.content)
        return payload


@dataclass
class ParsedDocument:
    """
    The complete parsed result of an HTML document.
    [Purpose] Holds title, all extracted elements in source order, and metadata.
    """

    title: Optional[str] = None
    elements: list[ContentElement] = field(default_factory=list)
    meta_description: Optional[str] = None
    language: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "meta_description": self.meta_description,
            "language": self.language,
            "elements": [element.to_dict() for element in self.elements],
        }
