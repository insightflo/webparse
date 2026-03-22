"""End-to-end tests for webparse pipeline."""

import pytest
from webparse.cli import parse_html


class TestEndToEnd:
    def test_full_page(self):
        html = """
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <title>테스트 페이지</title>
            <meta name="description" content="A test page">
            <style>body { font-family: sans-serif; }</style>
            <script>console.log("noise");</script>
        </head>
        <body>
            <nav>
                <a href="/">Home</a>
                <a href="/about">About</a>
            </nav>

            <main>
                <h1>메인 제목</h1>
                <p>첫 번째 단락입니다. 한국어 텍스트 처리를 테스트합니다.</p>

                <h2>두 번째 섹션</h2>
                <p>Python은 훌륭한 프로그래밍 언어입니다.</p>

                <table>
                    <tr><th>항목</th><th>가격</th></tr>
                    <tr><td>사과</td><td>1000원</td></tr>
                    <tr><td>바나나</td><td>2000원</td></tr>
                </table>

                <h3>기능 목록</h3>
                <ul>
                    <li>HTML 파싱</li>
                    <li>노이즈 제거</li>
                    <li>마크다운 변환
                        <ul>
                            <li>테이블 지원</li>
                            <li>리스트 지원</li>
                        </ul>
                    </li>
                </ul>

                <blockquote>인용문입니다.</blockquote>

                <pre><code class="language-python">def hello():
    print("안녕하세요")</code></pre>
            </main>

            <footer>
                <p>Copyright 2024</p>
            </footer>

            <div class="ad-banner">
                <p>광고: 지금 구매하세요!</p>
            </div>
        </body>
        </html>
        """
        result = parse_html(html)

        # Title / headings
        assert "# 메인 제목" in result
        assert "## 두 번째 섹션" in result
        assert "### 기능 목록" in result

        # Paragraphs with Korean
        assert "첫 번째 단락입니다" in result
        assert "Python은 훌륭한" in result

        # Table
        assert "| 항목" in result
        assert "사과" in result
        assert "1000원" in result

        # List
        assert "- HTML 파싱" in result
        assert "- 노이즈 제거" in result
        assert "  - 테이블 지원" in result

        # Blockquote
        assert "> 인용문입니다." in result

        # Code block
        assert "```python" in result
        assert 'print("안녕하세요")' in result

        # Noise removed
        assert "Home" not in result  # nav removed
        assert "Copyright" not in result  # footer removed
        assert "광고" not in result  # ad-banner removed
        assert "console.log" not in result  # script removed
        assert "font-family" not in result  # style removed

    def test_page_without_main_tag(self):
        """When no <main> or <article>, should find the largest text-dense div."""
        html = """
        <html><body>
        <div id="sidebar"><p>Short sidebar.</p></div>
        <div id="content">
            <h1>Article Title</h1>
            <p>This is the main article content that is quite long to ensure
            it gets detected as the main content area. It contains multiple
            sentences and paragraphs to simulate real content.</p>
            <p>Another paragraph with substantial text to make this the
            largest text-dense div on the page.</p>
        </div>
        </body></html>
        """
        result = parse_html(html)
        assert "Article Title" in result
        assert "main article content" in result

    def test_empty_html(self):
        result = parse_html("")
        assert result.strip() == "" or len(result.strip()) < 5

    def test_plain_text_input(self):
        result = parse_html("Just plain text, no HTML tags at all.")
        assert "plain text" in result

    def test_malformed_html(self):
        html = "<h1>Title<p>Para 1<p>Para 2<ul><li>Item</ul>"
        result = parse_html(html)
        assert "Title" in result
        assert "Item" in result

    def test_korean_heavy_page(self):
        html = """
        <html>
        <head><title>한국어 뉴스</title></head>
        <body>
        <article>
            <h1>대한민국 기술 동향</h1>
            <p>최근 인공지능 기술이 빠르게 발전하고 있습니다.
            특히 자연어 처리 분야에서 큰 진전이 있었습니다.</p>
            <h2>주요 기업 현황</h2>
            <table>
                <tr><th>기업</th><th>분야</th><th>직원수</th></tr>
                <tr><td>삼성전자</td><td>반도체</td><td>120,000</td></tr>
                <tr><td>네이버</td><td>검색/AI</td><td>6,000</td></tr>
                <tr><td>카카오</td><td>메신저/AI</td><td>5,000</td></tr>
            </table>
            <ol>
                <li>첫 번째 항목</li>
                <li>두 번째 항목</li>
                <li>세 번째 항목</li>
            </ol>
        </article>
        </body>
        </html>
        """
        result = parse_html(html)
        assert "# 대한민국 기술 동향" in result
        assert "인공지능 기술" in result
        assert "삼성전자" in result
        assert "1. 첫 번째 항목" in result
        assert "2. 두 번째 항목" in result
