"""Tests for webparse.formatter module."""

import pytest
from webparse.models import (
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
from webparse.formatter import format_document


def _doc_with(*elements: ContentElement, title: str | None = None) -> ParsedDocument:
    return ParsedDocument(title=title, elements=list(elements))


class TestHeadingFormatting:
    def test_h1(self):
        doc = _doc_with(ContentElement(ElementType.HEADING, Heading(1, "Title"), 0))
        result = format_document(doc)
        assert "# Title" in result

    def test_h3(self):
        doc = _doc_with(ContentElement(ElementType.HEADING, Heading(3, "Sub"), 0))
        result = format_document(doc)
        assert "### Sub" in result


class TestTitleHandling:
    def test_title_becomes_h1_if_no_h1_element(self):
        doc = _doc_with(
            ContentElement(ElementType.PARAGRAPH, Paragraph("Body text"), 0),
            title="Page Title",
        )
        result = format_document(doc)
        assert result.startswith("# Page Title")

    def test_title_not_duplicated_if_h1_exists(self):
        doc = _doc_with(
            ContentElement(ElementType.HEADING, Heading(1, "Existing H1"), 0),
            title="Page Title",
        )
        result = format_document(doc)
        assert "# Existing H1" in result
        assert "# Page Title" not in result


class TestParagraphFormatting:
    def test_simple_paragraph(self):
        doc = _doc_with(ContentElement(ElementType.PARAGRAPH, Paragraph("Hello world."), 0))
        result = format_document(doc)
        assert "Hello world." in result


class TestTableFormatting:
    def test_simple_table(self):
        table = Table(rows=[
            TableRow(cells=[TableCell("Name", is_header=True), TableCell("Age", is_header=True)]),
            TableRow(cells=[TableCell("Alice"), TableCell("30")]),
            TableRow(cells=[TableCell("Bob"), TableCell("25")]),
        ])
        doc = _doc_with(ContentElement(ElementType.TABLE, table, 0))
        result = format_document(doc)
        assert "| Name" in result
        assert "| ---" in result or "|---" in result
        assert "Alice" in result
        assert "Bob" in result

    def test_table_with_no_explicit_header(self):
        """First row should be used as header if no th cells."""
        table = Table(rows=[
            TableRow(cells=[TableCell("A"), TableCell("B")]),
            TableRow(cells=[TableCell("1"), TableCell("2")]),
        ])
        doc = _doc_with(ContentElement(ElementType.TABLE, table, 0))
        result = format_document(doc)
        lines = result.strip().split("\n")
        # Should have header, separator, body = 3 lines minimum
        assert len(lines) >= 3

    def test_table_with_caption(self):
        table = Table(
            rows=[
                TableRow(cells=[TableCell("X", is_header=True)]),
                TableRow(cells=[TableCell("1")]),
            ],
            caption="My Table",
        )
        doc = _doc_with(ContentElement(ElementType.TABLE, table, 0))
        result = format_document(doc)
        assert "**My Table**" in result


class TestListFormatting:
    def test_unordered_list(self):
        lst = ContentList(items=[
            ListItem("Apple"),
            ListItem("Banana"),
        ], ordered=False)
        doc = _doc_with(ContentElement(ElementType.LIST, lst, 0))
        result = format_document(doc)
        assert "- Apple" in result
        assert "- Banana" in result

    def test_ordered_list(self):
        lst = ContentList(items=[
            ListItem("First"),
            ListItem("Second"),
        ], ordered=True)
        doc = _doc_with(ContentElement(ElementType.LIST, lst, 0))
        result = format_document(doc)
        assert "1. First" in result
        assert "2. Second" in result

    def test_nested_list(self):
        lst = ContentList(items=[
            ListItem("Parent", children=[
                ListItem("Child 1"),
                ListItem("Child 2"),
            ]),
        ], ordered=False)
        doc = _doc_with(ContentElement(ElementType.LIST, lst, 0))
        result = format_document(doc)
        assert "- Parent" in result
        assert "  - Child 1" in result
        assert "  - Child 2" in result


class TestBlockquoteFormatting:
    def test_blockquote(self):
        doc = _doc_with(ContentElement(ElementType.BLOCKQUOTE, Blockquote("A wise quote."), 0))
        result = format_document(doc)
        assert "> A wise quote." in result


class TestCodeBlockFormatting:
    def test_code_block(self):
        doc = _doc_with(ContentElement(
            ElementType.CODE_BLOCK,
            CodeBlock('print("hi")', language="python"),
            0,
        ))
        result = format_document(doc)
        assert "```python" in result
        assert 'print("hi")' in result
        assert "```" in result

    def test_code_block_no_language(self):
        doc = _doc_with(ContentElement(
            ElementType.CODE_BLOCK,
            CodeBlock("some code"),
            0,
        ))
        result = format_document(doc)
        assert "```\n" in result


class TestImageFormatting:
    def test_image(self):
        doc = _doc_with(ContentElement(ElementType.IMAGE, Image("photo.jpg", "A photo"), 0))
        result = format_document(doc)
        assert "![A photo](photo.jpg)" in result


class TestHorizontalRule:
    def test_hr(self):
        doc = _doc_with(ContentElement(ElementType.HORIZONTAL_RULE, None, 0))
        result = format_document(doc)
        assert "---" in result


class TestCompleteDocument:
    def test_multiple_elements_separated_by_blank_lines(self):
        doc = _doc_with(
            ContentElement(ElementType.HEADING, Heading(1, "Title"), 0),
            ContentElement(ElementType.PARAGRAPH, Paragraph("Intro."), 1),
            ContentElement(ElementType.HEADING, Heading(2, "Section"), 2),
            ContentElement(ElementType.PARAGRAPH, Paragraph("Body."), 3),
        )
        result = format_document(doc)
        # Elements should be separated by blank lines
        assert "\n\n" in result
        lines = result.split("\n\n")
        assert len(lines) >= 4
