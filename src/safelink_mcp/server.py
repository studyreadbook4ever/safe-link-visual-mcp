from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP, Image
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

from safelink_mcp.inspector import inspect_url
from safelink_mcp.tool_contract import SERVER_NAME, TOOL_CONTRACTS


def _tool_annotations(name: str) -> ToolAnnotations:
    return ToolAnnotations(**TOOL_CONTRACTS[name]["annotations"])


def _csv_env(name: str, defaults: tuple[str, ...]) -> list[str]:
    raw = os.getenv(name)
    if raw is None:
        return list(defaults)
    return [item.strip() for item in raw.split(",") if item.strip()]


DEFAULT_ALLOWED_HOSTS = (
    "safelink-visual.playmcp-endpoint.kakaocloud.io",
    "safelink-visual.playmcp-endpoint.kakaocloud.io:*",
    "127.0.0.1:*",
    "localhost:*",
    "[::1]:*",
)

DEFAULT_ALLOWED_ORIGINS = (
    "https://playmcp.kakao.com",
    "https://playmcp.kakaocloud.io",
    "https://safelink-visual.playmcp-endpoint.kakaocloud.io",
    "http://127.0.0.1:*",
    "http://localhost:*",
    "http://[::1]:*",
)


mcp = FastMCP(
    SERVER_NAME,
    instructions=(
        "사용자가 제공한 URL을 격리된 모바일 브라우저 관찰과 규칙 앙상블로 검사합니다. "
        "판정은 완전 안전하다 또는 위험할 수 있다의 보수적 2진 분류입니다."
    ),
    host="0.0.0.0",
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_csv_env("SAFE_LINK_MCP_ALLOWED_HOSTS", DEFAULT_ALLOWED_HOSTS),
        allowed_origins=_csv_env("SAFE_LINK_MCP_ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS),
    ),
)


@mcp.tool(
    title=TOOL_CONTRACTS["is_safety"]["title"],
    description=TOOL_CONTRACTS["is_safety"]["description"],
    annotations=_tool_annotations("is_safety"),
)
async def is_safety(url: str) -> bool:
    """Return True only when the URL is classified as '완전 안전하다'."""
    result = await inspect_url(url, include_visual=False)
    return result.is_safety


@mcp.tool(
    title=TOOL_CONTRACTS["safety_explain"]["title"],
    description=TOOL_CONTRACTS["safety_explain"]["description"],
    annotations=_tool_annotations("safety_explain"),
)
async def safety_explain(url: str) -> dict[str, Any]:
    """Return a Korean evidence report explaining why is_safety is true or false."""
    result = await inspect_url(url, include_visual=False)
    return result.explain_dict()


@mcp.tool(
    title=TOOL_CONTRACTS["site_image"]["title"],
    description=TOOL_CONTRACTS["site_image"]["description"],
    annotations=_tool_annotations("site_image"),
)
async def site_image(url: str) -> Image:
    """Return a 1024x1024 PNG visual safety digest made from the site's mobile view."""
    result = await inspect_url(url, include_visual=True)
    if not result.digest_png:
        raise RuntimeError("site_image 생성에 실패했습니다.")
    return Image(data=result.digest_png, format="png")


def main() -> None:
    transport = os.getenv("MCP_TRANSPORT", "streamable-http").strip().lower()
    if transport in {"stdio", "streamable-http"}:
        mcp.run(transport=transport)
        return
    raise SystemExit(f"Unsupported MCP_TRANSPORT={transport!r}")


if __name__ == "__main__":
    main()
