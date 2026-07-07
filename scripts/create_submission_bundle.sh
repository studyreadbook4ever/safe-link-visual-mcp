#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACT="${ARTIFACT:-${ROOT_DIR}/dist/safe-link-visual-mcp-source.tar.gz}"

mkdir -p "$(dirname "${ARTIFACT}")"

tar -czf "${ARTIFACT}" \
  --exclude='./.git' \
  --exclude='./.venv' \
  --exclude='./.venv*' \
  --exclude='./__pycache__' \
  --exclude='*/__pycache__' \
  --exclude='./.pytest_cache' \
  --exclude='./.mypy_cache' \
  --exclude='./.ruff_cache' \
  --exclude='./build' \
  --exclude='./dist' \
  --exclude='*.egg-info' \
  -C "${ROOT_DIR}" .

echo "Created ${ARTIFACT}"
