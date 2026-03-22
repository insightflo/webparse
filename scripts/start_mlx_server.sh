#!/bin/zsh
set -euo pipefail

cd /Users/kwak/Projects/ocr-hybrid-mvp

source .venv-mlx/bin/activate

exec mlx_vlm.server --trust-remote-code --port 8080
