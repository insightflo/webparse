import json

from webparse.cli import parse_html


def test_parse_html_supports_json_output():
    html = "<html><body><main><h1>Main Title</h1><p>Body copy.</p></main></body></html>"

    result = json.loads(parse_html(html, output_format="json"))

    assert result["title"] is None
    assert result["elements"][0]["type"] == "heading"
    assert result["elements"][0]["content"]["text"] == "Main Title"
    assert (
        result["elements"][0]["source_path"]
        == "html:nth-of-type(1) > body:nth-of-type(1) > main:nth-of-type(1) > h1:nth-of-type(1)"
    )
    assert result["elements"][0]["confidence"] == 0.99


def test_parse_html_supports_html_output_with_metadata():
    html = "<html><body><main><h1>Main Title</h1><p>Body copy.</p></main></body></html>"

    result = parse_html(html, output_format="html")

    assert "<article>" in result
    assert (
        '<h1 data-type="heading" data-confidence="0.99" data-source-path="html:nth-of-type(1) &gt; body:nth-of-type(1) &gt; main:nth-of-type(1) &gt; h1:nth-of-type(1)">Main Title</h1>'
        in result
    )
    assert (
        '<p data-type="paragraph" data-confidence="0.97" data-source-path="html:nth-of-type(1) &gt; body:nth-of-type(1) &gt; main:nth-of-type(1) &gt; p:nth-of-type(1)">Body copy.</p>'
        in result
    )
