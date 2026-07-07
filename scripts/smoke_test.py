from __future__ import annotations

import asyncio
from pathlib import Path

from safelink_mcp.render import warm_browser
from safelink_mcp.server import is_safety, safety_explain, site_image


async def main() -> None:
    url = "https://example.com"
    await warm_browser()
    safety = await is_safety(url)
    explain = await safety_explain(url)
    image = await site_image(url)

    assert safety is True
    assert explain["is_safety"] is True
    assert explain["verdict"] == "완전 안전하다"
    assert image.data and len(image.data) > 10_000

    Path("/tmp/safe-link-smoke.png").write_bytes(image.data)

    print("smoke ok")
    print(
        f"verdict={explain['verdict']} score={explain['risk_score']} "
        f"image_bytes={len(image.data)}"
    )
    print("wrote /tmp/safe-link-smoke.png")


if __name__ == "__main__":
    asyncio.run(main())
