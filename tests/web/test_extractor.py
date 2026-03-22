"""Tests for webparse.extractor module."""

import pytest
from webparse.cleaner import clean_html
from webparse.extractor import extract
from webparse.models import (
    ContentList,
    ElementType,
    Heading,
    Paragraph,
    Table,
    Blockquote,
    CodeBlock,
    Image,
)


def _extract_html(html: str):
    """Helper: clean + extract in one step."""
    soup = clean_html(html)
    return extract(soup)


class TestTitle:
    def test_extracts_title(self):
        html = '<html><head><title>My Page</title></head><body><p>X</p></body></html>'
        doc = _extract_html(html)
        assert doc.title == "My Page"

    def test_no_title(self):
        html = '<html><body><p>X</p></body></html>'
        doc = _extract_html(html)
        assert doc.title is None


class TestHeadings:
    def test_extracts_h1(self):
        html = '<html><body><h1>Main Title</h1><p>Text</p></body></html>'
        doc = _extract_html(html)
        headings = [e for e in doc.elements if e.element_type == ElementType.HEADING]
        assert len(headings) >= 1
        h = headings[0].content
        assert isinstance(h, Heading)
        assert h.level == 1
        assert h.text == "Main Title"

    def test_preserves_heading_hierarchy(self):
        html = '<html><body><h1>H1</h1><h2>H2</h2><h3>H3</h3></body></html>'
        doc = _extract_html(html)
        headings = [e.content for e in doc.elements if e.element_type == ElementType.HEADING]
        levels = [h.level for h in headings]
        assert levels == [1, 2, 3]


class TestParagraphs:
    def test_extracts_paragraphs(self):
        html = '<html><body><p>First paragraph.</p><p>Second paragraph.</p></body></html>'
        doc = _extract_html(html)
        paras = [e.content for e in doc.elements if e.element_type == ElementType.PARAGRAPH]
        texts = [p.text for p in paras]
        assert "First paragraph." in texts
        assert "Second paragraph." in texts

    def test_collapses_whitespace(self):
        html = '<html><body><p>  Too   many   spaces  </p></body></html>'
        doc = _extract_html(html)
        paras = [e.content for e in doc.elements if e.element_type == ElementType.PARAGRAPH]
        assert any("Too many spaces" in p.text for p in paras)


class TestTables:
    def test_simple_table(self):
        html = """
        <html><body>
        <table>
            <tr><th>Name</th><th>Age</th></tr>
            <tr><td>Alice</td><td>30</td></tr>
            <tr><td>Bob</td><td>25</td></tr>
        </table>
        </body></html>
        """
        doc = _extract_html(html)
        tables = [e.content for e in doc.elements if e.element_type == ElementType.TABLE]
        assert len(tables) == 1
        t = tables[0]
        assert isinstance(t, Table)
        assert len(t.rows) == 3
        assert t.rows[0].cells[0].text == "Name"
        assert t.rows[0].cells[0].is_header is True

    def test_table_with_caption(self):
        html = """
        <html><body>
        <table>
            <caption>User Data</caption>
            <tr><th>Name</th></tr>
            <tr><td>Alice</td></tr>
        </table>
        </body></html>
        """
        doc = _extract_html(html)
        tables = [e.content for e in doc.elements if e.element_type == ElementType.TABLE]
        assert tables[0].caption == "User Data"

    def test_table_with_colspan(self):
        html = """
        <html><body>
        <table>
            <tr><th colspan="2">Full Name</th></tr>
            <tr><td>First</td><td>Last</td></tr>
        </table>
        </body></html>
        """
        doc = _extract_html(html)
        tables = [e.content for e in doc.elements if e.element_type == ElementType.TABLE]
        assert tables[0].rows[0].cells[0].colspan == 2


class TestLists:
    def test_unordered_list(self):
        html = """
        <html><body>
        <ul>
            <li>Apple</li>
            <li>Banana</li>
            <li>Cherry</li>
        </ul>
        </body></html>
        """
        doc = _extract_html(html)
        lists = [e.content for e in doc.elements if e.element_type == ElementType.LIST]
        assert len(lists) == 1
        lst = lists[0]
        assert isinstance(lst, ContentList)
        assert lst.ordered is False
        assert len(lst.items) == 3
        assert lst.items[0].text == "Apple"

    def test_ordered_list(self):
        html = """
        <html><body>
        <ol>
            <li>First</li>
            <li>Second</li>
        </ol>
        </body></html>
        """
        doc = _extract_html(html)
        lists = [e.content for e in doc.elements if e.element_type == ElementType.LIST]
        assert lists[0].ordered is True

    def test_nested_list(self):
        html = """
        <html><body>
        <ul>
            <li>Parent
                <ul>
                    <li>Child 1</li>
                    <li>Child 2</li>
                </ul>
            </li>
            <li>Sibling</li>
        </ul>
        </body></html>
        """
        doc = _extract_html(html)
        lists = [e.content for e in doc.elements if e.element_type == ElementType.LIST]
        assert len(lists) == 1
        lst = lists[0]
        assert len(lst.items) == 2
        assert len(lst.items[0].children) == 2
        assert lst.items[0].children[0].text == "Child 1"


class TestBlockquotes:
    def test_blockquote(self):
        html = '<html><body><blockquote>A wise quote.</blockquote></body></html>'
        doc = _extract_html(html)
        bqs = [e.content for e in doc.elements if e.element_type == ElementType.BLOCKQUOTE]
        assert len(bqs) == 1
        assert bqs[0].text == "A wise quote."


class TestCodeBlocks:
    def test_pre_code(self):
        html = '<html><body><pre><code>print("hello")</code></pre></body></html>'
        doc = _extract_html(html)
        cbs = [e.content for e in doc.elements if e.element_type == ElementType.CODE_BLOCK]
        assert len(cbs) == 1
        assert 'print("hello")' in cbs[0].code


class TestMainContentDetection:
    def test_prefers_main_tag(self):
        html = """
        <html><body>
        <div><p>Noise outside main.</p></div>
        <main><p>Important content here.</p></main>
        </body></html>
        """
        doc = _extract_html(html)
        paras = [e.content.text for e in doc.elements if e.element_type == ElementType.PARAGRAPH]
        assert "Important content here." in paras

    def test_prefers_article_tag(self):
        html = """
        <html><body>
        <div><p>Sidebar junk.</p></div>
        <article><p>The real article.</p></article>
        </body></html>
        """
        doc = _extract_html(html)
        paras = [e.content.text for e in doc.elements if e.element_type == ElementType.PARAGRAPH]
        assert "The real article." in paras


class TestSourceOrder:
    def test_elements_in_source_order(self):
        html = """
        <html><body>
        <h1>Title</h1>
        <p>Intro.</p>
        <h2>Section</h2>
        <p>Body.</p>
        </body></html>
        """
        doc = _extract_html(html)
        types = [e.element_type for e in doc.elements]
        assert types == [
            ElementType.HEADING,
            ElementType.PARAGRAPH,
            ElementType.HEADING,
            ElementType.PARAGRAPH,
        ]
