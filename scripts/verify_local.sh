#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"

"${PYTHON_BIN}" -m compileall src tests scripts
"${PYTHON_BIN}" -m pytest
"${PYTHON_BIN}" scripts/smoke_test.py

if command -v npx >/dev/null 2>&1; then
  PYTHON_BIN="${PYTHON_BIN}" scripts/inspect_playmcp.sh
else
  echo "npx not found; skipped MCP Inspector smoke"
fi

if command -v docker >/dev/null 2>&1; then
  docker build -t safe-link-visual-mcp:local .
  echo "docker build ok: safe-link-visual-mcp:local"
elif command -v podman >/dev/null 2>&1; then
  podman build -t safe-link-visual-mcp:local .
  echo "podman build ok: safe-link-visual-mcp:local"
else
  echo "docker/podman not found; skipped image build"
fi
