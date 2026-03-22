"""Tests for webparse.cleaner module."""

import pytest
from bs4 import BeautifulSoup
from webparse.cleaner import clean_html


class TestNoiseRemoval:
    """Verify that noise elements are removed from HTML."""

    def test_removes_script_tags(self):
        html = '<html><body><p>Hello</p><script>alert(1)</script></body></html>'
        soup = clean_html(html)
        assert soup.find("script") is None
        assert "Hello" in soup.get_text()

    def test_removes_style_tags(self):
        html = '<html><body><style>body{color:red}</style><p>Content</p></body></html>'
        soup = clean_html(html)
        assert soup.find("style") is None
        assert "Content" in soup.get_text()

    def test_removes_nav_tags(self):
        html = '<html><body><nav><a href="/">Home</a></nav><p>Main content</p></body></html>'
        soup = clean_html(html)
        assert soup.find("nav") is None
        assert "Main content" in soup.get_text()

    def test_removes_footer_tags(self):
        html = '<html><body><p>Content</p><footer>Copyright 2024</footer></body></html>'
        soup = clean_html(html)
        assert soup.find("footer") is None

    def test_removes_header_tags(self):
        html = '<html><body><header><h1>Site Name</h1></header><p>Content</p></body></html>'
        soup = clean_html(html)
        assert soup.find("header") is None

    def test_removes_hidden_elements(self):
        html = '<html><body><div style="display:none">Hidden</div><p>Visible</p></body></html>'
        soup = clean_html(html)
        assert "Hidden" not in soup.get_text()
        assert "Visible" in soup.get_text()

    def test_removes_visibility_hidden(self):
        html = '<html><body><div style="visibility: hidden">Invisible</div><p>OK</p></body></html>'
        soup = clean_html(html)
        assert "Invisible" not in soup.get_text()

    def test_removes_ad_class_divs(self):
        html = '<html><body><div class="ad-banner">Buy now!</div><p>Article</p></body></html>'
        soup = clean_html(html)
        assert "Buy now" not in soup.get_text()

    def test_removes_sidebar_id(self):
        html = '<html><body><div id="sidebar">Links</div><p>Main</p></body></html>'
        soup = clean_html(html)
        assert "Links" not in soup.get_text()

    def test_removes_aria_hidden(self):
        html = '<html><body><div aria-hidden="true">Icon</div><p>Text</p></body></html>'
        soup = clean_html(html)
        assert "Icon" not in soup.get_text()

    def test_removes_comments(self):
        html = '<html><body><!-- TODO: fix this --><p>Content</p></body></html>'
        soup = clean_html(html)
        text = str(soup)
        assert "TODO" not in text

    def test_removes_noscript(self):
        html = '<html><body><noscript>Enable JS</noscript><p>OK</p></body></html>'
        soup = clean_html(html)
        assert soup.find("noscript") is None

    def test_removes_iframe(self):
        html = '<html><body><iframe src="ad.html"></iframe><p>OK</p></body></html>'
        soup = clean_html(html)
        assert soup.find("iframe") is None


class TestAttributeStripping:
    """Verify that non-essential attributes are removed."""

    def test_strips_class_and_id(self):
        html = '<html><body><p class="intro" id="p1">Text</p></body></html>'
        soup = clean_html(html)
        p = soup.find("p")
        assert p is not None
        assert not p.get("class")
        assert not p.get("id")

    def test_preserves_href_on_links(self):
        html = '<html><body><a href="https://example.com" class="btn">Link</a></body></html>'
        soup = clean_html(html)
        a = soup.find("a")
        assert a is not None
        assert a.get("href") == "https://example.com"
        assert not a.get("class")

    def test_preserves_src_alt_on_images(self):
        html = '<html><body><img src="photo.jpg" alt="A photo" class="hero"></body></html>'
        soup = clean_html(html)
        img = soup.find("img")
        assert img is not None
        assert img.get("src") == "photo.jpg"
        assert img.get("alt") == "A photo"
        assert not img.get("class")

    def test_strips_inline_styles(self):
        html = '<html><body><p style="color: red; font-size: 14px;">Styled</p></body></html>'
        soup = clean_html(html)
        p = soup.find("p")
        assert p is not None
        assert not p.get("style")


class TestMalformedHTML:
    """Verify graceful handling of broken markup."""

    def test_handles_unclosed_tags(self):
        html = '<html><body><p>Paragraph without closing<p>Another one</body></html>'
        soup = clean_html(html)
        assert "Paragraph" in soup.get_text()
        assert "Another" in soup.get_text()

    def test_handles_bare_text(self):
        html = 'Just some text without any tags'
        soup = clean_html(html)
        assert "Just some text" in soup.get_text()

    def test_handles_empty_input(self):
        soup = clean_html("")
        assert soup.get_text().strip() == ""


class TestKoreanContent:
    """Verify Korean text is preserved correctly."""

    def test_preserves_korean_text(self):
        html = '<html><body><p>안녕하세요. 이것은 테스트입니다.</p></body></html>'
        soup = clean_html(html)
        assert "안녕하세요" in soup.get_text()
        assert "테스트입니다" in soup.get_text()

    def test_preserves_mixed_korean_english(self):
        html = '<html><body><p>Python은 좋은 프로그래밍 언어입니다.</p></body></html>'
        soup = clean_html(html)
        assert "Python은 좋은 프로그래밍" in soup.get_text()
