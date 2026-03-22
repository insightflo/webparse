# webparse

Rendered HTML DOM → clean structured Markdown. 어떤 브라우저 도구든 가져온 HTML을 LLM이 읽기 좋은 마크다운으로 변환합니다.

## 왜 필요한가

LLM이 웹 콘텐츠를 처리할 때 두 가지 문제가 있습니다:

1. **JS 렌더링 전 HTML** — `<noscript>` 메시지만 보임 → 브라우저 도구가 렌더링 해결
2. **렌더링됐지만 복잡한 레이아웃** — 테이블, 중첩 리스트, 광고, 네비게이션이 섞여있어 핵심 파악 어려움 → **webparse가 해결**

webparse는 브라우저가 렌더링한 결과물을 받아서 **노이즈를 제거하고 구조를 보존한 마크다운**으로 변환합니다.

## 설치

```bash
pip install -e .
```

**의존성:** Python 3.10+, beautifulsoup4, lxml, requests

## 사용법

```bash
# stdin 파이프 (어떤 브라우저 도구든)
echo "<html>..." | webparse
curl -s https://example.com | webparse

# 파일
webparse --file saved_page.html

# URL (단순 HTTP fetch, JS 렌더링 없음)
webparse --url https://example.com
```

### 브라우저 도구와 조합

```bash
# cmux browse 결과를 파이프
cmux browse export-html https://example.com | webparse

# chrome-devtools로 렌더링 후 파이프
# playwright, puppeteer 등 어떤 도구든 HTML을 stdout으로 내보내면 됩니다
```

## 처리 과정

```
HTML 입력
  ↓
1. 노이즈 제거
   - <script>, <style>, <nav>, <footer>, <header>, <aside> 제거
   - 광고 패턴 (ad, banner, popup, cookie, social 등) 제거
   - aria-hidden, display:none 요소 제거

2. 본문 감지 (4단계 fallback)
   - <main> → <article> → [role="main"] → 최대 텍스트 밀도 div → <body>

3. 구조 추출 (소스 순서 유지)
   - 헤딩 (h1~h6) → 계층 보존
   - 테이블 → 마크다운 테이블 (레이아웃 테이블은 컨테이너로 처리)
   - 리스트 → 중첩 보존
   - 인용 → blockquote
   - 코드 → fenced code block (언어 태그 보존)
   - 이미지 → ![alt](src)

4. 마크다운 출력
  ↓
LLM이 읽기 좋은 구조화 텍스트
```

## 프로젝트 구조

```
webparse/
├── webparse/
│   ├── cli.py          # CLI 진입점 (stdin/--file/--url)
│   ├── cleaner.py      # 노이즈 제거 (22개 패턴)
│   ├── extractor.py    # 구조 추출 (본문 감지 + 요소 분류)
│   ├── formatter.py    # 마크다운 렌더링
│   └── models.py       # 데이터 클래스
├── tests/
│   ├── test_cleaner.py     # 22 tests
│   ├── test_extractor.py   # 16 tests
│   ├── test_formatter.py   # 18 tests
│   └── test_e2e.py         # 6 tests
└── pyproject.toml
```

## 테스트

```bash
pip install -e ".[dev]"
pytest tests/ -v
# 62 tests passed
```

---

## AI 에이전트용 지침

### 이 도구를 사용할 때

- **입력:** 렌더링된 HTML string. URL이 아니라 브라우저가 이미 가져온 HTML.
- **출력:** stdout으로 마크다운. 파일 저장은 호출 측에서 리다이렉션.
- **에러:** 비정상 HTML도 graceful 처리. 빈 입력이면 빈 출력.
- **인코딩:** UTF-8. 한글, 일본어, 중국어 정상 지원.

### 호출 패턴

```bash
# 권장: HTML을 stdin으로 파이프
echo "$HTML_CONTENT" | webparse

# 파일로 저장된 HTML
webparse --file /tmp/rendered_page.html

# URL 직접 (JS 렌더링 안됨 — 정적 페이지만)
webparse --url https://example.com
```

### 출력 특성

- 제목은 `# h1`, `## h2` 형태로 계층 유지
- 테이블은 pipe 형식 마크다운 테이블
- 이미지는 `![alt](src)` — LLM이 설명 요청 가능
- 네비게이션, 광고, 푸터는 자동 제거
- 빈 줄이 연속되지 않음

### 제약사항

- **JS 렌더링 안 함.** 동적 콘텐츠는 브라우저 도구로 먼저 렌더링 후 HTML을 전달해야 함.
- **로그인 필요 페이지 미지원.** 인증 쿠키가 필요한 페이지는 브라우저 도구에서 처리.
- **이미지 OCR 안 함.** 이미지 텍스트 추출은 `hyocr` 사용.
- **PDF 미지원.** PDF 파싱은 `hyocr` 사용.
- **최대 입력 크기 제한 없음.** 단, 매우 큰 HTML(10MB+)은 처리 시간 증가.

---

## 제약조건

1. **순수 파서** — 브라우저 엔진, JS 런타임, 외부 API를 사용하지 않음
2. **무상태** — 캐시, DB, 설정 파일 없음. 입력 → 출력만.
3. **의존성 최소** — beautifulsoup4 + lxml + requests만. 무거운 ML 모델 없음.
4. **개인정보** — 입력 HTML을 외부로 전송하지 않음. 로컬 처리만.

## 라이선스

MIT License

Copyright (c) 2026 개수라발발타

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
