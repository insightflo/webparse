from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hyocr.config import Settings, resolve_glm_command


@dataclass(slots=True)
class RoutePlan:
    primary: str
    secondary: str | None


def build_route(path: Path, settings: Settings, preferred_engine: str = "auto") -> RoutePlan:
    suffix = path.suffix.lower()
    apple_available = settings.apple_bin.exists()
    glm_available = bool(resolve_glm_command(settings.glm_command))

    if preferred_engine != "auto":
        return RoutePlan(primary=preferred_engine, secondary=None)

    if suffix == ".pdf":
        if glm_available:
            return RoutePlan(primary="glm", secondary="apple" if apple_available else None)
        if apple_available:
            return RoutePlan(primary="apple", secondary=None)
    else:
        if apple_available:
            return RoutePlan(primary="apple", secondary="glm" if glm_available else None)
        if glm_available:
            return RoutePlan(primary="glm", secondary=None)

    raise RuntimeError("No OCR engine is configured. Build the Apple binary and/or set HYOCR_GLM_CMD.")
