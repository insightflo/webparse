from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from hyocr.config import PROJECT_ROOT, Settings, resolve_glm_command
from hyocr.merge_results import merge_apple_glm_files
from hyocr.pipeline import HybridOCRPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hyocr", description="Local hybrid OCR pipeline for macOS.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run OCR on an image or PDF.")
    run_parser.add_argument("input", help="Input file path.")
    run_parser.add_argument("--engine", choices=["auto", "apple", "glm"], default="auto")
    run_parser.add_argument("--format", choices=["json", "markdown"], default="json")
    run_parser.add_argument("--out", help="Write output to this file.")

    merge_parser = subparsers.add_parser("merge-results", help="Merge Apple Vision JSON with GLM SDK JSON.")
    merge_parser.add_argument("--apple-json", required=True, help="Path to Apple Vision JSON output.")
    merge_parser.add_argument("--glm-json", required=True, help="Path to GLM SDK JSON output.")
    merge_parser.add_argument("--format", choices=["json", "markdown"], default="json")
    merge_parser.add_argument("--out", help="Write output to this file.")

    subparsers.add_parser("doctor", help="Inspect local OCR dependencies.")
    return parser


def run_command(args: argparse.Namespace) -> int:
    settings = Settings.load()
    pipeline = HybridOCRPipeline(settings)
    document = pipeline.process(args.input, preferred_engine=args.engine)
    payload = json.dumps(document.to_dict(), indent=2, ensure_ascii=False) if args.format == "json" else document.to_markdown()
    return _write_output(payload, args.out)


def doctor_command() -> int:
    settings = Settings.load()
    raw_glm_command = os.getenv("HYOCR_GLM_CMD")
    glm_command = resolve_glm_command(raw_glm_command)
    sdk_venv = PROJECT_ROOT / ".venv-sdk"
    mlx_venv = PROJECT_ROOT / ".venv-mlx"
    shell_scripts = {
        str(path.relative_to(PROJECT_ROOT)): path.is_file()
        for path in sorted((PROJECT_ROOT / "scripts").glob("*.sh"))
    }
    checks = {
        "apple_bin": str(settings.apple_bin),
        "apple_bin_exists": settings.apple_bin.exists(),
        "glm_cmd_env": raw_glm_command or "",
        "glm_cmd": glm_command or "",
        "glm_configured": bool(glm_command),
        "ollama_on_path": shutil.which("ollama") is not None,
        "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        "glm_openai_base_url": os.getenv("GLM_OCR_OPENAI_BASE_URL", ""),
        "pdf_renderer": settings.pdf_renderer,
        "pdf_renderer_on_path": shutil.which(settings.pdf_renderer) is not None,
        "project_root": str(PROJECT_ROOT),
        "venv_sdk_dir": str(sdk_venv),
        "venv_sdk_exists": sdk_venv.is_dir(),
        "venv_mlx_dir": str(mlx_venv),
        "venv_mlx_exists": mlx_venv.is_dir(),
        "shell_scripts": shell_scripts,
    }
    output = json.dumps(checks, indent=2, ensure_ascii=False)
    print(output)
    return 0


def merge_results_command(args: argparse.Namespace) -> int:
    payload_dict = merge_apple_glm_files(args.apple_json, args.glm_json)
    payload = (
        json.dumps(payload_dict, indent=2, ensure_ascii=False)
        if args.format == "json"
        else payload_dict["markdown"]
    )
    return _write_output(payload, args.out)


def _write_output(payload: str, out: str | None) -> int:
    if out:
        output_path = Path(out).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload + ("\n" if not payload.endswith("\n") else ""), encoding="utf-8")
    else:
        sys.stdout.write(payload)
        if not payload.endswith("\n"):
            sys.stdout.write("\n")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "run":
        return run_command(args)
    if args.command == "merge-results":
        return merge_results_command(args)
    if args.command == "doctor":
        return doctor_command()
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
