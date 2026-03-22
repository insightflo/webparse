from hyocr.models import OCRPage, OCRTable
from hyocr.quality import score_page


def test_quality_prefers_richer_page() -> None:
    sparse = OCRPage(
        source="a.png",
        page=1,
        engine="apple",
        raw_text="A\nB",
        markdown="A\nB",
        confidence=0.2,
    )
    rich = OCRPage(
        source="b.png",
        page=1,
        engine="glm",
        raw_text="Invoice\nItem  Qty  Price\nWidget  3  12.00",
        markdown="| Item | Qty | Price |\n| --- | --- | --- |\n| Widget | 3 | 12.00 |",
        confidence=0.7,
        tables=[OCRTable(markdown="| Item | Qty | Price |")],
    )
    assert score_page(rich) > score_page(sparse)
