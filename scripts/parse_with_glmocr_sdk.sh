#!/bin/zsh
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 <image-or-pdf-path> [output-dir]" >&2
  exit 2
fi

INPUT_PATH="$1"
OUTPUT_DIR="${2:-/Users/kwak/Projects/ocr-hybrid-mvp/output/glmocr}"

cd /Users/kwak/Projects/ocr-hybrid-mvp
mkdir -p "$OUTPUT_DIR"

source .venv-sdk/bin/activate

exec glmocr parse "$INPUT_PATH" \
  --config /Users/kwak/Projects/ocr-hybrid-mvp/configs/glmocr-mlx-local.yaml \
  --output "$OUTPUT_DIR"
