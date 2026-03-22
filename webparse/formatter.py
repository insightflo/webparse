"""
[File Purpose] Convert a ParsedDocument into clean markdown text.
[Main Flow] ParsedDocument -> iterate elements -> emit markdown blocks -> join with blank lines.
[External Connections] Reads models from models.py, called by cli.py.
[Modification Notes] To change markdown style, edit the individual _format_* helpers.
"""

from __future__ import annotations

from .models import (
    Blockquote,
    CodeBlock,
    ContentElement,
    ContentList,
    ElementType,
    Heading,
    Image,
    ListItem,
    Paragraph,
    ParsedDocument,
    Table,
)


def format_document(doc: ParsedDocument) -> str:
    """
    [Purpose] Render a ParsedDocument as a clean markdown string.
    [Input] ParsedDocument with extracted elements.
    [Output] Markdown string ready for LLM consumption.
    """
    parts: list[str] = []

    # Title as H1 if present and not already in elements
    if doc.title:
        has_h1 = any(
            e.element_type == ElementType.HEADING
            and isinstance(e.content, Heading)
            and e.content.level == 1
            for e in doc.elements
        )
        if not has_h1:
            parts.append(f"# {doc.title}")

    for elem in doc.elements:
        block = _format_element(elem)
        if block:
            parts.append(block)

    return "\n\n".join(parts) + "\n" if parts else ""


def _format_element(elem: ContentElement) -> str:
    """Dispatch to the appropriate formatter based on element type."""
    match elem.element_type:
        case ElementType.HEADING:
            return _format_heading(elem.content)  # type: ignore[arg-type]
        case ElementType.PARAGRAPH:
            return _format_paragraph(elem.content)  # type: ignore[arg-type]
        case ElementType.TABLE:
            return _format_table(elem.content)  # type: ignore[arg-type]
        case ElementType.LIST:
            return _format_list(elem.content)  # type: ignore[arg-type]
        case ElementType.BLOCKQUOTE:
            return _format_blockquote(elem.content)  # type: ignore[arg-type]
        case ElementType.CODE_BLOCK:
            return _format_code_block(elem.content)  # type: ignore[arg-type]
        case ElementType.IMAGE:
            return _format_image(elem.content)  # type: ignore[arg-type]
        case ElementType.HORIZONTAL_RULE:
            return "---"
        case _:
            return ""


# ── individual formatters ─────────────────────────────────────────

def _format_heading(h: Heading) -> str:
    prefix = "#" * h.level
    return f"{prefix} {h.text}"


def _format_paragraph(p: Paragraph) -> str:
    return p.text


def _format_table(table: Table) -> str:
    """
    [Purpose] Render a Table as a markdown table with header separator.
    [Notes] If no header row is detected, the first row is used as header.
            Handles colspan by repeating cell text.
    """
    if not table.rows:
        return ""

    lines: list[str] = []

    # Caption
    if table.caption:
        lines.append(f"**{table.caption}**")
        lines.append("")

    # Determine column count
    max_cols = 0
    for row in table.rows:
        col_count = sum(c.colspan for c in row.cells)
        max_cols = max(max_cols, col_count)

    if max_cols == 0:
        return ""

    # Separate header rows from body rows
    header_rows: list[list[str]] = []
    body_rows: list[list[str]] = []

    for row in table.rows:
        expanded: list[str] = []
        for cell in row.cells:
            expanded.append(cell.text)
            # Colspan: add empty cells
            for _ in range(cell.colspan - 1):
                expanded.append("")

        # Pad to max_cols
        while len(expanded) < max_cols:
            expanded.append("")

        if row.cells and row.cells[0].is_header:
            header_rows.append(expanded)
        else:
            body_rows.append(expanded)

    # If no explicit headers, use first row as header
    if not header_rows and body_rows:
        header_rows.append(body_rows.pop(0))

    # Calculate column widths for alignment
    col_widths = [3] * max_cols  # minimum width 3
    all_rows = header_rows + body_rows
    for row_data in all_rows:
        for i, cell_text in enumerate(row_data):
            col_widths[i] = max(col_widths[i], len(cell_text))

    def _render_row(cells: list[str]) -> str:
        padded = [c.ljust(col_widths[i]) for i, c in enumerate(cells)]
        return "| " + " | ".join(padded) + " |"

    # Render header
    for hrow in header_rows:
        lines.append(_render_row(hrow))

    # Separator
    sep_parts = ["-" * col_widths[i] for i in range(max_cols)]
    lines.append("| " + " | ".join(sep_parts) + " |")

    # Body rows
    for brow in body_rows:
        lines.append(_render_row(brow))

    return "\n".join(lines)


def _format_list(cl: ContentList) -> str:
    """Render a ContentList as markdown, handling nesting."""
    lines: list[str] = []
    _render_list_items(cl.items, cl.ordered, indent=0, lines=lines)
    return "\n".join(lines)


def _render_list_items(
    items: list[ListItem],
    ordered: bool,
    indent: int,
    lines: list[str],
) -> None:
    prefix_space = "  " * indent
    for i, item in enumerate(items, start=1):
        marker = f"{i}." if ordered else "-"
        lines.append(f"{prefix_space}{marker} {item.text}")
        if item.children:
            _render_list_items(item.children, ordered=False, indent=indent + 1, lines=lines)


def _format_blockquote(bq: Blockquote) -> str:
    bq_lines = bq.text.split("\n")
    return "\n".join(f"> {line}" for line in bq_lines)


def _format_code_block(cb: CodeBlock) -> str:
    lang = cb.language or ""
    return f"```{lang}\n{cb.code}\n```"


def _format_image(img: Image) -> str:
    return f"![{img.alt}]({img.src})"
