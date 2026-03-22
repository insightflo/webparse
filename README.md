# parse — 통합 콘텐츠 파서

이미지, PDF, HTML을 하나의 CLI로 처리합니다. 입력 타입을 자동 감지하여 적절한 엔진으로 라우팅합니다.

```
parse image.png              → OCR (Apple Vision)
parse document.pdf           → OCR (GLM-OCR)
parse page.html              → HTML→마크다운
parse --url https://...      → fetch + 마크다운
echo "<html>..." | parse     → stdin HTML 감지
```

## 구성 요소

| 모듈 | 역할 | 입력 | 출력 |
|------|------|------|------|
| **webparse** | HTML→구조화 마크다운 | 렌더링된 HTML | 마크다운 |
| **hyocr** | 이미지/PDF OCR | 이미지, PDF | JSON 또는 마크다운 |
| **parse** | 통합 라우터 | 아무 파일 | 적절한 엔진으로 위임 |

## 설치

```bash
pip install -e .
```

**의존성:** Python 3.10+, beautifulsoup4, lxml, requests

**OCR 추가 요구사항 (hyocr):**
- macOS (Apple Vision Framework)
- Apple Vision OCR 바이너리: `apple-vision-ocr/.build/release/apple-vision-ocr`
- PDF 렌더러: `pdftoppm` (poppler)
- GLM-OCR (선택): MLX 서버 또는 SDK

## 사용법

### 통합 CLI (parse)

```bash
# 이미지 OCR
parse screenshot.png

# PDF OCR
parse report.pdf

# HTML → 마크다운
parse page.html

# URL 직접 (JS 렌더링 안됨)
parse --url https://example.com

# stdin 파이프
echo "<html>..." | parse
curl -s https://example.com | parse
```

### webparse 단독

```bash
# stdin
echo "<html>..." | webparse

# 파일
webparse --file saved_page.html

# URL
webparse --url https://example.com
```

### hyocr 단독

```bash
# 자동 엔진 선택
hyocr run image.png

# 엔진 지정
hyocr run document.pdf --engine glm

# 마크다운 출력
hyocr run scan.jpg --format markdown

# 환경 확인
hyocr doctor
```

### 브라우저 도구와 조합

```bash
# cmux 브라우저에서 DOM 추출 후 파이프
cmux browser $SURFACE eval "document.documentElement.outerHTML" | parse

# 어떤 브라우저 도구든 HTML을 stdout으로 내보내면 됩니다
```

## webparse 처리 과정

```
HTML 입력
  ↓
1. 노이즈 제거 — script, style, nav, footer, 광고 패턴 제거
2. 본문 감지 — <main> → <article> → [role="main"] → 텍스트 밀도 → <body>
3. 구조 추출 — 헤딩, 테이블, 리스트, 인용, 코드, 이미지
4. 마크다운 출력
  ↓
LLM이 읽기 좋은 구조화 텍스트
```

## hyocr 아키텍처

```
입력 파일
  ↓
라우팅: PDF → GLM-OCR / 이미지 → Apple Vision
  ↓
품질 점수 55점 이하 → fallback 엔진으로 재시도
  ↓
72% 유사도 기반 결과 병합 (dedup)
  ↓
JSON 또는 마크다운 출력
```

## 프로젝트 구조

```
webparse/                    ← 모노레포 루트
├── parse                    # 통합 라우터 CLI
├── webparse/                # HTML→마크다운 파서
│   ├── cli.py
│   ├── cleaner.py           # 노이즈 제거 (22개 패턴)
│   ├── extractor.py         # 본문 감지 + 구조 추출
│   ├── formatter.py         # 마크다운 렌더링
│   └── models.py
├── hyocr/                   # 하이브리드 OCR 파이프라인
│   ├── cli.py
│   ├── pipeline.py          # 라우팅 + fallback
│   ├── routing.py           # 엔진 선택 로직
│   ├── quality.py           # 품질 점수 계산
│   ├── merge_results.py     # Apple + GLM 결과 병합
│   ├── config.py
│   ├── models.py
│   └── adapters/            # Apple Vision, GLM-OCR 어댑터
├── apple-vision-ocr/        # Swift 바이너리 (Apple Vision Framework)
├── scripts/                 # GLM-OCR 래퍼 스크립트
├── configs/                 # MLX 서버 설정
├── tests/
│   ├── web/                 # webparse 테스트 (62개)
│   └── ocr/                 # hyocr 테스트 (11개)
└── pyproject.toml
```

## 테스트

```bash
pip install -e ".[dev]"

# 전체
pytest tests/ -v

# 웹 파서만
pytest tests/web/ -v

# OCR만
pytest tests/ocr/ -v
```

## 제약사항

- **webparse는 JS 렌더링 안 함.** 동적 페이지는 브라우저 도구로 먼저 렌더링 후 HTML을 전달.
- **hyocr는 macOS 전용.** Apple Vision Framework 의존.
- **외부 API 없음.** 모든 처리는 로컬. 입력 데이터를 외부로 전송하지 않음.

## 라이선스

MIT License — Copyright (c) 2026 개수라발발타
