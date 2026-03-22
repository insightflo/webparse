"""
[File Purpose] Extract structured content elements from a cleaned BeautifulSoup tree.
[Main Flow] Cleaned soup -> find main content region -> walk DOM in source order
             -> produce list of ContentElement objects.
[External Connections] Reads cleaner.py output, produces models consumed by formatter.py.
[Modification Notes] To support a new element type, add a handler in _EXTRACTORS and
                     update the ElementType enum in models.py.
"""

from __future__ import annotations

import re
from typing import Optional

from bs4 import BeautifulSoup, NavigableString, Tag

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
    TableCell,
    TableRow,
)


# ── helpers ───────────────────────────────────────────────────────

def _get_text(tag: Tag, separator: str = " ") -> str:
    """Extract text from a tag, collapsing whitespace."""
    text = tag.get_text(separator=separator)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _find_main_content(soup: BeautifulSoup) -> Tag:
    """
    [Purpose] Locate the main content region of the page.
    [Strategy]
      1. <main> tag
      2. <article> tag
      3. [role='main']
      4. Largest text-dense <div> (by text length)
      5. Fallback: <body> or root
    """
    # 1. <main>
    main = soup.find("main")
    if main and isinstance(main, Tag):
        return main

    # 2. <article>
    article = soup.find("article")
    if article and isinstance(article, Tag):
        return article

    # 3. role=main
    role_main = soup.find(attrs={"role": "main"})
    if role_main and isinstance(role_main, Tag):
        return role_main

    # 4. Largest text-dense div
    body = soup.find("body")
    if body is None:
        # Might be a fragment without <body>
        body = soup

    best: Optional[Tag] = None
    best_len = 0
    for div in body.find_all("div"):  # type: ignore[union-attr]
        if isinstance(div, Tag):
            tl = len(_get_text(div))
            if tl > best_len:
                best_len = tl
                best = div

    if best is not None and best_len > 100:
        return best

    # 5. Fallback
    return body if isinstance(body, Tag) else soup  # type: ignore[return-value]


# ── layout table detection ────────────────────────────────────────

def _is_layout_table(tag: Tag) -> bool:
    """
    [Purpose] Detect layout tables (used for page structure, not data).
    [Strategy] Heuristics:
      - Contains nested tables -> layout
      - Has very few cells per row (1) -> layout wrapper
      - Cells contain block-level elements (divs, headings, lists, other tables) -> layout
      - Very long text in cells (> 200 chars average) -> likely layout
    """
    # Nested tables are a strong signal of layout
    if tag.find("table"):
        return True

    rows = tag.find_all("tr", recursive=False)
    # Also check inside thead/tbody
    for section in tag.find_all(["thead", "tbody", "tfoot"], recursive=False):
        rows.extend(section.find_all("tr", recursive=False))

    if not rows:
        return False

    # Single-column tables are usually layout wrappers
    all_single_col = all(
        len(tr.find_all(["td", "th"], recursive=False)) <= 1
        for tr in rows
    )
    if all_single_col and len(rows) > 2:
        return True

    # Cells containing block elements -> layout
    block_tags = {"div", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "table", "article", "section", "p"}
    for tr in rows:
        for cell in tr.find_all(["td", "th"], recursive=False):
            for child in cell.children:
                if isinstance(child, Tag) and child.name in block_tags:
                    # p tags inside td are OK for data tables, but multiple block elements is layout
                    block_children = [c for c in cell.children if isinstance(c, Tag) and c.name in block_tags]
                    if len(block_children) > 1:
                        return True

    # Very long average cell text -> layout
    total_text = 0
    cell_count = 0
    for tr in rows:
        for cell in tr.find_all(["td", "th"], recursive=False):
            total_text += len(_get_text(cell))
            cell_count += 1
    if cell_count > 0 and total_text / cell_count > 200:
        return True

    return False


# ── element extractors ────────────────────────────────────────────

def _extract_heading(tag: Tag) -> Heading:
    level = int(tag.name[1])  # h1-h6
    return Heading(level=level, text=_get_text(tag))


def _extract_table(tag: Tag) -> Table:
    """
    [Purpose] Parse an HTML <table> into our Table model.
    [Notes] Handles <thead>/<tbody> and bare <tr>, plus colspan/rowspan.
    """
    caption_tag = tag.find("caption")
    caption = _get_text(caption_tag) if caption_tag else None

    rows: list[TableRow] = []
    for tr in tag.find_all("tr"):
        cells: list[TableCell] = []
        for cell in tr.find_all(["td", "th"]):
            colspan = int(cell.get("colspan", 1) or 1)
            rowspan = int(cell.get("rowspan", 1) or 1)
            cells.append(TableCell(
                text=_get_text(cell),
                is_header=(cell.name == "th"),
                colspan=colspan,
                rowspan=rowspan,
            ))
        if cells:
            rows.append(TableRow(cells=cells))

    return Table(rows=rows, caption=caption)


def _extract_list_items(tag: Tag) -> list[ListItem]:
    """Recursively extract list items including nested lists."""
    items: list[ListItem] = []
    for li in tag.find_all("li", recursive=False):
        # Get direct text (excluding nested list text)
        nested = li.find(["ul", "ol"])
        if nested:
            # Get text before the nested list
            text_parts = []
            for child in li.children:
                if isinstance(child, Tag) and child.name in ("ul", "ol"):
                    break
                if isinstance(child, NavigableString):
                    t = str(child).strip()
                    if t:
                        text_parts.append(t)
                elif isinstance(child, Tag):
                    t = _get_text(child)
                    if t:
                        text_parts.append(t)
            text = " ".join(text_parts)
            children = _extract_list_items(nested)
        else:
            text = _get_text(li)
            children = []
        items.append(ListItem(text=text, children=children))
    return items


def _extract_list(tag: Tag) -> ContentList:
    ordered = tag.name == "ol"
    items = _extract_list_items(tag)
    return ContentList(items=items, ordered=ordered)


def _extract_blockquote(tag: Tag) -> Blockquote:
    return Blockquote(text=_get_text(tag))


def _extract_code_block(tag: Tag) -> CodeBlock:
    """Extract <pre> blocks. Detect language from nested <code> class."""
    code_tag = tag.find("code")
    if code_tag and isinstance(code_tag, Tag):
        code_text = code_tag.get_text()
        # Try to detect language from class like "language-python"
        classes = code_tag.get("class", [])
        lang = None
        for cls in (classes if isinstance(classes, list) else [classes]):
            if cls and cls.startswith("language-"):
                lang = cls[len("language-"):]
                break
        return CodeBlock(code=code_text, language=lang)
    return CodeBlock(code=tag.get_text())


def _extract_image(tag: Tag) -> Image:
    src = tag.get("src", "") or ""
    alt = tag.get("alt", "") or ""
    return Image(src=src, alt=alt)


# ── heading tag set ───────────────────────────────────────────────
HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

# Tags we handle explicitly (children not walked separately)
BLOCK_TAGS = HEADING_TAGS | {"table", "ul", "ol", "blockquote", "pre", "img"}


def _walk_and_extract(root: Tag) -> list[ContentElement]:
    """
    [Purpose] Walk the DOM tree in source order, extracting content elements.
    [Strategy] DFS; when we encounter a known block element we extract it and
               skip its children. Text nodes and inline containers become paragraphs.
    """
    elements: list[ContentElement] = []
    order = 0

    def _visit_table_cells(table_tag: Tag) -> None:
        """Walk into layout table cells, treating each cell as a container."""
        for tr in table_tag.find_all("tr"):
            for cell in tr.find_all(["td", "th"]):
                _visit(cell)

    def _visit(node: Tag) -> None:
        nonlocal order
        for child in node.children:
            if isinstance(child, NavigableString):
                text = child.strip()
                if text:
                    elements.append(ContentElement(
                        element_type=ElementType.PARAGRAPH,
                        content=Paragraph(text=text),
                        source_order=order,
                    ))
                    order += 1
                continue

            if not isinstance(child, Tag):
                continue

            tag_name = child.name

            # Headings
            if tag_name in HEADING_TAGS:
                h = _extract_heading(child)
                if h.text:
                    elements.append(ContentElement(
                        element_type=ElementType.HEADING,
                        content=h,
                        source_order=order,
                    ))
                    order += 1
                continue

            # Tables: distinguish data tables from layout tables
            if tag_name == "table":
                if _is_layout_table(child):
                    # Layout table: walk into it like a container
                    _visit_table_cells(child)
                else:
                    t = _extract_table(child)
                    if t.rows:
                        elements.append(ContentElement(
                            element_type=ElementType.TABLE,
                            content=t,
                            source_order=order,
                        ))
                        order += 1
                continue

            # Lists
            if tag_name in ("ul", "ol"):
                lst = _extract_list(child)
                if lst.items:
                    elements.append(ContentElement(
                        element_type=ElementType.LIST,
                        content=lst,
                        source_order=order,
                    ))
                    order += 1
                continue

            # Blockquotes
            if tag_name == "blockquote":
                bq = _extract_blockquote(child)
                if bq.text:
                    elements.append(ContentElement(
                        element_type=ElementType.BLOCKQUOTE,
                        content=bq,
                        source_order=order,
                    ))
                    order += 1
                continue

            # Code blocks
            if tag_name == "pre":
                cb = _extract_code_block(child)
                if cb.code.strip():
                    elements.append(ContentElement(
                        element_type=ElementType.CODE_BLOCK,
                        content=cb,
                        source_order=order,
                    ))
                    order += 1
                continue

            # Images
            if tag_name == "img":
                img = _extract_image(child)
                if img.src:
                    elements.append(ContentElement(
                        element_type=ElementType.IMAGE,
                        content=img,
                        source_order=order,
                    ))
                    order += 1
                continue

            # Horizontal rules
            if tag_name == "hr":
                elements.append(ContentElement(
                    element_type=ElementType.HORIZONTAL_RULE,
                    content=None,
                    source_order=order,
                ))
                order += 1
                continue

            # Paragraphs
            if tag_name == "p":
                text = _get_text(child)
                if text:
                    elements.append(ContentElement(
                        element_type=ElementType.PARAGRAPH,
                        content=Paragraph(text=text, is_block=True),
                        source_order=order,
                    ))
                    order += 1
                continue

            # For other container tags (div, section, span, etc.),
            # recurse into children
            _visit(child)

    _visit(root)
    return elements


# ── public API ────────────────────────────────────────────────────

def extract(soup: BeautifulSoup) -> ParsedDocument:
    """
    [Purpose] Extract a ParsedDocument from a cleaned BeautifulSoup tree.
    [Input] Cleaned BeautifulSoup (noise already removed by cleaner).
    [Output] ParsedDocument with title, elements in source order, and metadata.
    """
    # Title
    title_tag = soup.find("title")
    title = _get_text(title_tag) if title_tag and isinstance(title_tag, Tag) else None

    # Meta description
    meta_desc = None
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and isinstance(meta_tag, Tag):
        meta_desc = meta_tag.get("content", "")

    # Language
    html_tag = soup.find("html")
    lang = None
    if html_tag and isinstance(html_tag, Tag):
        lang = html_tag.get("lang")

    # Find main content area
    main_content = _find_main_content(soup)

    # Walk and extract elements
    elements = _walk_and_extract(main_content)

    # Merge consecutive bare text paragraphs that likely belong together
    elements = _merge_adjacent_paragraphs(elements)

    return ParsedDocument(
        title=title,
        elements=elements,
        meta_description=meta_desc,
        language=lang,
    )


def _merge_adjacent_paragraphs(elements: list[ContentElement]) -> list[ContentElement]:
    """
    [Purpose] Merge adjacent Paragraph elements that are just fragments.
    [Notes] Only merges if both are short (< 80 chars) and adjacent in source order.
    """
    if not elements:
        return elements

    merged: list[ContentElement] = []
    for elem in elements:
        if (
            merged
            and merged[-1].element_type == ElementType.PARAGRAPH
            and elem.element_type == ElementType.PARAGRAPH
            and isinstance(merged[-1].content, Paragraph)
            and isinstance(elem.content, Paragraph)
            # Only merge bare text fragments (not proper <p> blocks).
            and not merged[-1].content.is_block
            and not elem.content.is_block
            # Source-order must be consecutive for this to make sense.
            and elem.source_order == merged[-1].source_order + 1
            and len(merged[-1].content.text) < 80
            and len(elem.content.text) < 80
        ):
            merged[-1].content.text += " " + elem.content.text
            merged[-1].source_order = elem.source_order
        else:
            merged.append(elem)

    return merged
