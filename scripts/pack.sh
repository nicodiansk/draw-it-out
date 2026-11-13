#!/usr/bin/env bash
# Build the claude.ai skill zip (Settings → Skills): explain/ at the zip root,
# without capture.py (Claude Code only) and without Python caches.
# Usage: bash scripts/pack.sh [out-dir]   (default: dist/)
set -euo pipefail
repo="$(cd "$(dirname "$0")/.." && pwd)"
out="${1:-$repo/dist}"
mkdir -p "$out"
out="$(cd "$out" && pwd)"
zip_path="$out/draw-it-out-explain.zip"
rm -f "$zip_path"
cd "$repo/skills"
zip -qr "$zip_path" explain -x '*__pycache__*' '*.pyc' 'explain/engine/capture.py'
echo "$zip_path"
