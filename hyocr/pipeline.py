from __future__ import annotations

import shutil
from pathlib import Path

from hyocr.adapters.apple import AppleVisionAdapter
from hyocr.adapters.glm import GLMOCRAdapter
from hyocr.config import Settings
from hyocr.models import OCRDocument, OCRPage
from hyocr.pdf import render_pdf_pages
from hyocr.quality import score_page, should_compare
from hyocr.routing import build_route


class HybridOCRPipeline:
    def __init__(
        self,
        settings: Settings,
        apple_adapter: AppleVisionAdapter | None = None,
        glm_adapter: GLMOCRAdapter | None = None,
    ) -> None:
        self.settings = settings
        self.apple = apple_adapter or AppleVisionAdapter(settings.apple_bin)
        self.glm = glm_adapter or GLMOCRAdapter(settings.glm_command)

    def process(self, input_path: str | Path, preferred_engine: str = "auto") -> OCRDocument:
        source = Path(input_path).expanduser().resolve()
        if not source.exists():
            raise FileNotFoundError(source)

        route = build_route(source, self.settings, preferred_engine=preferred_engine)
        page_inputs = self._prepare_pages(source)
        pages: list[OCRPage] = []

        for page_number, page_input in enumerate(page_inputs, start=1):
            primary_page = self._run_engine(route.primary, page_input, page_number)
            primary_score = score_page(primary_page)
            selected_page = primary_page

            if route.secondary and should_compare(primary_page, self.settings.compare_threshold):
                secondary_page = self._run_engine(route.secondary, page_input, page_number)
                secondary_score = score_page(secondary_page)
                selected_page = secondary_page if secondary_score > primary_score else primary_page
                selected_page.meta["comparison"] = {
                    route.primary: primary_score,
                    route.secondary: secondary_score,
                }
            else:
                selected_page.meta["comparison"] = {route.primary: primary_score}

            pages.append(selected_page)

        selected_engines = sorted({page.engine for page in pages})
        return OCRDocument(
            source=str(source),
            pages=pages,
            selected_engine="+".join(selected_engines),
            meta={"page_count": len(pages)},
        )

    def _prepare_pages(self, source: Path) -> list[Path]:
        if source.suffix.lower() != ".pdf":
            return [source]

        output_dir = self.settings.temp_dir / source.stem
        if output_dir.exists():
            shutil.rmtree(output_dir)
        return render_pdf_pages(source, output_dir, renderer=self.settings.pdf_renderer)

    def _run_engine(self, engine: str, page_input: Path, page_number: int) -> OCRPage:
        if engine == "apple":
            return self.apple.ocr_image(page_input, page_number)
        if engine == "glm":
            return self.glm.ocr_image(page_input, page_number)
        raise RuntimeError(f"Unsupported OCR engine: {engine}")
