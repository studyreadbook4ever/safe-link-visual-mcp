#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-safe-link-visual-mcp:latest}"

if command -v docker >/dev/null 2>&1; then
  docker build -t "${IMAGE_NAME}" .
elif command -v podman >/dev/null 2>&1; then
  podman build -t "${IMAGE_NAME}" .
else
  echo "docker or podman is required to build ${IMAGE_NAME}" >&2
  exit 1
fi

echo "Built ${IMAGE_NAME}"
