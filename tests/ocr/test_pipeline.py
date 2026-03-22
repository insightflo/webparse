from pathlib import Path

from hyocr.config import Settings
from hyocr.models import OCRPage
from hyocr.pipeline import HybridOCRPipeline


class FakeAdapter:
    def __init__(self, name: str, page: OCRPage) -> None:
        self.name = name
        self.page = page

    def ocr_image(self, image_path: Path, page_number: int) -> OCRPage:
        return OCRPage(
            source=str(image_path),
            page=page_number,
            engine=self.page.engine,
            raw_text=self.page.raw_text,
            markdown=self.page.markdown,
            confidence=self.page.confidence,
            blocks=self.page.blocks,
            tables=self.page.tables,
            meta=dict(self.page.meta),
        )


def test_pipeline_promotes_fallback_when_quality_is_better(tmp_path: Path) -> None:
    image = tmp_path / "shot.png"
    image.write_text("png")
    settings = Settings(
        apple_bin=tmp_path / "apple-bin",
        glm_command="configured",
        pdf_renderer="pdftoppm",
        compare_threshold=80,
        temp_dir=tmp_path / "tmp",
    )
    settings.apple_bin.write_text("bin")

    apple_page = OCRPage(
        source=str(image),
        page=1,
        engine="apple",
        raw_text="x",
        markdown="x",
        confidence=0.1,
    )
    glm_page = OCRPage(
        source=str(image),
        page=1,
        engine="glm",
        raw_text="Invoice\nItem Qty Price\nWidget 3 12.00",
        markdown="Invoice\n\n| Item | Qty | Price |\n| --- | --- | --- |\n| Widget | 3 | 12.00 |",
        confidence=0.8,
    )

    pipeline = HybridOCRPipeline(
        settings=settings,
        apple_adapter=FakeAdapter("apple", apple_page),
        glm_adapter=FakeAdapter("glm", glm_page),
    )

    result = pipeline.process(image)

    assert result.pages[0].engine == "glm"
    assert "comparison" in result.pages[0].meta
