import pytest

from webparse.cleaner import clean_html
from webparse.extractor import extract
from webparse.models import ElementType, Heading, Paragraph


def test_tracks_dom_path_for_block_elements():
    html = "<html><body><main><h1>Main Title</h1><p>Body copy.</p></main></body></html>"

    doc = extract(clean_html(html))

    heading_element = next(
        e for e in doc.elements if e.element_type == ElementType.HEADING
    )
    paragraph_element = next(
        e for e in doc.elements if e.element_type == ElementType.PARAGRAPH
    )

    assert isinstance(heading_element.content, Heading)
    assert isinstance(paragraph_element.content, Paragraph)
    assert (
        heading_element.source_path
        == "html:nth-of-type(1) > body:nth-of-type(1) > main:nth-of-type(1) > h1:nth-of-type(1)"
    )
    assert (
        paragraph_element.source_path
        == "html:nth-of-type(1) > body:nth-of-type(1) > main:nth-of-type(1) > p:nth-of-type(1)"
    )


def test_assigns_confidence_scores_for_text_and_blocks():
    html = "<html><body><main><h1>Main Title</h1>Loose text<p>Body copy.</p></main></body></html>"

    doc = extract(clean_html(html))

    heading_element = next(
        e for e in doc.elements if e.element_type == ElementType.HEADING
    )
    paragraph_elements = [
        e for e in doc.elements if e.element_type == ElementType.PARAGRAPH
    ]
    bare_text_element = next(
        e
        for e in paragraph_elements
        if isinstance(e.content, Paragraph) and not e.content.is_block
    )
    block_paragraph_element = next(
        e
        for e in paragraph_elements
        if isinstance(e.content, Paragraph) and e.content.is_block
    )

    assert heading_element.confidence == pytest.approx(0.99)
    assert bare_text_element.confidence < block_paragraph_element.confidence
    assert (
        bare_text_element.source_path
        == "html:nth-of-type(1) > body:nth-of-type(1) > main:nth-of-type(1) > #text"
    )
