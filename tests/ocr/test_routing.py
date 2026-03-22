from pathlib import Path

from hyocr.config import Settings
from hyocr.routing import build_route


def test_pdf_prefers_glm_when_available(tmp_path: Path) -> None:
    pdf = tmp_path / "sample.pdf"
    pdf.write_text("pdf")
    settings = Settings(
        apple_bin=tmp_path / "apple-bin",
        glm_command="echo {}",
        pdf_renderer="pdftoppm",
        compare_threshold=55,
        temp_dir=tmp_path / "tmp",
    )
    settings.apple_bin.write_text("bin")

    route = build_route(pdf, settings)

    assert route.primary == "glm"
    assert route.secondary == "apple"


def test_image_prefers_apple_when_available(tmp_path: Path) -> None:
    image = tmp_path / "shot.png"
    image.write_text("png")
    settings = Settings(
        apple_bin=tmp_path / "apple-bin",
        glm_command="echo {}",
        pdf_renderer="pdftoppm",
        compare_threshold=55,
        temp_dir=tmp_path / "tmp",
    )
    settings.apple_bin.write_text("bin")

    route = build_route(image, settings)

    assert route.primary == "apple"
    assert route.secondary == "glm"
