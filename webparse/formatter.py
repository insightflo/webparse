"""
[File Purpose] Convert a ParsedDocument into clean markdown text.
[Main Flow] ParsedDocument -> iterate elements -> emit markdown blocks -> join with blank lines.
[External Connections] Reads models from models.py, called by cli.py.
[Modification Notes] To change markdown style, edit the individual _format_* helpers.
"""

from __future__ import annotations

import html
import json

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


def format_document_json(doc: ParsedDocument) -> str:
    return json.dumps(doc.to_dict(), ensure_ascii=False, indent=2) + "\n"


def format_document_html(doc: ParsedDocument) -> str:
    parts: list[str] = ["<article>"]

    if doc.title:
        has_h1 = any(
            e.element_type == ElementType.HEADING
            and isinstance(e.content, Heading)
            and e.content.level == 1
            for e in doc.elements
        )
        if not has_h1:
            parts.append(f"<h1>{html.escape(doc.title)}</h1>")

    for elem in doc.elements:
        block = _format_element_html(elem)
        if block:
            parts.append(block)

    parts.append("</article>")
    return "\n".join(parts) + "\n"


def _format_element(elem: ContentElement) -> str:
    """Dispatch to the appropriate formatter based on element type."""
    content = elem.content
    if elem.element_type == ElementType.HEADING and isinstance(content, Heading):
        return _format_heading(content)
    if elem.element_type == ElementType.PARAGRAPH and isinstance(content, Paragraph):
        return _format_paragraph(content)
    if elem.element_type == ElementType.TABLE and isinstance(content, Table):
        return _format_table(content)
    if elem.element_type == ElementType.LIST and isinstance(content, ContentList):
        return _format_list(content)
    if elem.element_type == ElementType.BLOCKQUOTE and isinstance(content, Blockquote):
        return _format_blockquote(content)
    if elem.element_type == ElementType.CODE_BLOCK and isinstance(content, CodeBlock):
        return _format_code_block(content)
    if elem.element_type == ElementType.IMAGE and isinstance(content, Image):
        return _format_image(content)
    if elem.element_type == ElementType.HORIZONTAL_RULE:
        return "---"
    return ""


def _format_element_html(elem: ContentElement) -> str:
    attrs = _html_attrs(elem)
    content = elem.content
    if elem.element_type == ElementType.HEADING and isinstance(content, Heading):
        return _format_heading_html(content, attrs)
    if elem.element_type == ElementType.PARAGRAPH and isinstance(content, Paragraph):
        return _format_paragraph_html(content, attrs)
    if elem.element_type == ElementType.TABLE and isinstance(content, Table):
        return _format_table_html(content, attrs)
    if elem.element_type == ElementType.LIST and isinstance(content, ContentList):
        return _format_list_html(content, attrs)
    if elem.element_type == ElementType.BLOCKQUOTE and isinstance(content, Blockquote):
        return _format_blockquote_html(content, attrs)
    if elem.element_type == ElementType.CODE_BLOCK and isinstance(content, CodeBlock):
        return _format_code_block_html(content, attrs)
    if elem.element_type == ElementType.IMAGE and isinstance(content, Image):
        return _format_image_html(content, attrs)
    if elem.element_type == ElementType.HORIZONTAL_RULE:
        return f"<hr{attrs}>"
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
            _render_list_items(
                item.children, ordered=False, indent=indent + 1, lines=lines
            )


def _format_blockquote(bq: Blockquote) -> str:
    bq_lines = bq.text.split("\n")
    return "\n".join(f"> {line}" for line in bq_lines)


def _format_code_block(cb: CodeBlock) -> str:
    lang = cb.language or ""
    return f"```{lang}\n{cb.code}\n```"


def _format_image(img: Image) -> str:
    return f"![{img.alt}]({img.src})"


def _html_attrs(elem: ContentElement) -> str:
    attrs = {
        "data-type": elem.element_type.name.lower(),
        "data-confidence": f"{elem.confidence:.2f}",
    }
    if elem.source_path:
        attrs["data-source-path"] = elem.source_path
    rendered = " ".join(
        f'{key}="{html.escape(value, quote=True)}"' for key, value in attrs.items()
    )
    return f" {rendered}" if rendered else ""


def _format_heading_html(h: Heading, attrs: str) -> str:
    level = min(max(h.level, 1), 6)
    return f"<h{level}{attrs}>{html.escape(h.text)}</h{level}>"


def _format_paragraph_html(p: Paragraph, attrs: str) -> str:
    return f"<p{attrs}>{html.escape(p.text)}</p>"


def _format_table_html(table: Table, attrs: str) -> str:
    if not table.rows:
        return ""

    lines: list[str] = [f"<table{attrs}>"]
    if table.caption:
        lines.append(f"  <caption>{html.escape(table.caption)}</caption>")

    header_rows: list[list] = []
    body_rows: list[list] = []
    for row in table.rows:
        if row.cells and row.cells[0].is_header:
            header_rows.append(row.cells)
        else:
            body_rows.append(row.cells)

    if not header_rows and body_rows:
        header_rows.append(body_rows.pop(0))

    if header_rows:
        lines.append("  <thead>")
        for row in header_rows:
            lines.append("    <tr>")
            for cell in row:
                lines.append(
                    _format_table_cell_html(cell, header=True, indent="      ")
                )
            lines.append("    </tr>")
        lines.append("  </thead>")

    lines.append("  <tbody>")
    for row in body_rows:
        lines.append("    <tr>")
        for cell in row:
            lines.append(_format_table_cell_html(cell, header=False, indent="      "))
        lines.append("    </tr>")
    lines.append("  </tbody>")
    lines.append("</table>")
    return "\n".join(lines)


def _format_table_cell_html(cell, *, header: bool, indent: str) -> str:
    tag = "th" if header or cell.is_header else "td"
    attrs: list[str] = []
    if cell.colspan > 1:
        attrs.append(f'colspan="{cell.colspan}"')
    if cell.rowspan > 1:
        attrs.append(f'rowspan="{cell.rowspan}"')
    attr_text = f" {' '.join(attrs)}" if attrs else ""
    return f"{indent}<{tag}{attr_text}>{html.escape(cell.text)}</{tag}>"


def _format_list_html(cl: ContentList, attrs: str) -> str:
    tag = "ol" if cl.ordered else "ul"
    lines = [f"<{tag}{attrs}>"]
    _render_list_items_html(cl.items, indent=1, lines=lines)
    lines.append(f"</{tag}>")
    return "\n".join(lines)


def _render_list_items_html(
    items: list[ListItem], *, indent: int, lines: list[str]
) -> None:
    prefix = "  " * indent
    for item in items:
        lines.append(f"{prefix}<li>{html.escape(item.text)}")
        if item.children:
            lines.append(f"{prefix}  <ul>")
            _render_list_items_html(item.children, indent=indent + 2, lines=lines)
            lines.append(f"{prefix}  </ul>")
        lines.append(f"{prefix}</li>")


def _format_blockquote_html(bq: Blockquote, attrs: str) -> str:
    return f"<blockquote{attrs}>{html.escape(bq.text)}</blockquote>"


def _format_code_block_html(cb: CodeBlock, attrs: str) -> str:
    class_attr = (
        f' class="language-{html.escape(cb.language, quote=True)}"'
        if cb.language
        else ""
    )
    return f"<pre{attrs}><code{class_attr}>{html.escape(cb.code)}</code></pre>"


def _format_image_html(img: Image, attrs: str) -> str:
    return (
        f'<img{attrs} src="{html.escape(img.src, quote=True)}" '
        f'alt="{html.escape(img.alt, quote=True)}">'
    )
