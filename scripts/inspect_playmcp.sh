#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
PORT="${PORT:-8765}"
BASE_URL="http://127.0.0.1:${PORT}"
SERVER_URL="${BASE_URL}/mcp"
LOG_FILE="${LOG_FILE:-/tmp/safe-link-playmcp-inspector.log}"

"${PYTHON_BIN}" -m uvicorn safelink_mcp.asgi:app --host 127.0.0.1 --port "${PORT}" >"${LOG_FILE}" 2>&1 &
SERVER_PID=$!
trap 'kill "${SERVER_PID}" 2>/dev/null || true' EXIT

for _ in {1..30}; do
  if curl -fsS "${BASE_URL}/healthz" >/dev/null 2>&1; then
    break
  fi
  sleep 0.2
done

curl -fsS "${BASE_URL}/healthz"
echo

SERVER_URL="${SERVER_URL}" "${PYTHON_BIN}" - <<'PY'
import asyncio
import os

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main() -> None:
    async with streamablehttp_client(os.environ["SERVER_URL"]) as (read, write, _):
        async with ClientSession(read, write) as session:
            result = await session.initialize()
            protocol_version = str(result.protocolVersion)
            assert "2025-03-26" <= protocol_version <= "2025-11-25"
            assert result.serverInfo.name == "Safe Link Visual MCP"
            tools = await session.list_tools()
            assert {tool.name for tool in tools.tools} == {
                "is_safety",
                "safety_explain",
                "site_image",
            }
            print(f"sdk initialize ok: protocol={protocol_version}")


asyncio.run(main())
PY

npx @modelcontextprotocol/inspector --cli --transport http "${SERVER_URL}" --method tools/list
npx @modelcontextprotocol/inspector --cli --transport http "${SERVER_URL}" --method tools/call --tool-name is_safety --tool-arg url=https://example.com
npx @modelcontextprotocol/inspector --cli --transport http "${SERVER_URL}" --method tools/call --tool-name safety_explain --tool-arg url=https://example.com >/tmp/safe-link-inspector-explain.json
npx @modelcontextprotocol/inspector --cli --transport http "${SERVER_URL}" --method tools/call --tool-name site_image --tool-arg url=https://example.com >/tmp/safe-link-inspector-image.json

"${PYTHON_BIN}" - <<'PY'
import json
from pathlib import Path

explain = json.loads(Path("/tmp/safe-link-inspector-explain.json").read_text())
image = json.loads(Path("/tmp/safe-link-inspector-image.json").read_text())
assert explain["isError"] is False
assert explain["structuredContent"]["is_safety"] is True
assert image["isError"] is False
assert image["content"][0]["type"] == "image"
assert image["content"][0]["mimeType"] == "image/png"
assert len(image["content"][0]["data"]) > 10000
print("playmcp inspector smoke ok")
PY
