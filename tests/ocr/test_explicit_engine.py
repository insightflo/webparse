from pathlib import Path

from hyocr.config import Settings
from hyocr.routing import build_route


def test_explicit_glm_disables_fallback(tmp_path: Path) -> None:
    image = tmp_path / "shot.png"
    image.write_text("png")
    settings = Settings(
        apple_bin=tmp_path / "apple-bin",
        glm_command="configured",
        pdf_renderer="pdftoppm",
        compare_threshold=55,
        temp_dir=tmp_path / "tmp",
    )
    settings.apple_bin.write_text("bin")

    route = build_route(image, settings, preferred_engine="glm")

    assert route.primary == "glm"
    assert route.secondary is None
