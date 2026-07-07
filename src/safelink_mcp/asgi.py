from __future__ import annotations

import base64
import contextlib
import json
from urllib.parse import parse_qs

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from safelink_mcp.inspector import inspect_url
from safelink_mcp.render import warm_browser
from safelink_mcp.server import mcp


async def healthz(_: Request) -> JSONResponse:
    return JSONResponse({"ok": True, "service": "safe-link-visual-mcp"})


def _url_from_request(request: Request) -> str:
    url = request.query_params.get("url")
    if url:
        return url
    if request.method == "POST":
        raise ValueError("POST 요청은 JSON body를 사용하세요.")
    raise ValueError("url 쿼리 파라미터가 필요합니다.")


async def inspect_get(request: Request) -> JSONResponse:
    try:
        target_url = _url_from_request(request)
        include_image = request.query_params.get("include_image", "false").lower() in {
            "1",
            "true",
            "yes",
        }
        result = await inspect_url(target_url, include_visual=include_image)
        payload = result.explain_dict()
        if include_image and result.digest_png:
            payload["site_image"] = {
                "mime_type": "image/png",
                "base64": base64.b64encode(result.digest_png).decode("ascii"),
                "width": 1024,
                "height": 1024,
            }
        return JSONResponse(payload)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


async def inspect_post(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except json.JSONDecodeError:
        body = {}
    try:
        target_url = str(body.get("url") or "")
        if not target_url:
            raise ValueError("JSON body에 url 필드가 필요합니다.")
        include_image = bool(body.get("include_image", False))
        result = await inspect_url(target_url, include_visual=include_image)
        payload = result.explain_dict()
        if include_image and result.digest_png:
            payload["site_image"] = {
                "mime_type": "image/png",
                "base64": base64.b64encode(result.digest_png).decode("ascii"),
                "width": 1024,
                "height": 1024,
            }
        return JSONResponse(payload)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


async def site_image_get(request: Request) -> Response:
    try:
        target_url = _url_from_request(request)
        result = await inspect_url(target_url)
        if not result.digest_png:
            return JSONResponse({"error": "site_image 생성 실패"}, status_code=500)
        return Response(result.digest_png, media_type="image/png")
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


async def openapi_hint(request: Request) -> JSONResponse:
    query = parse_qs(request.url.query)
    return JSONResponse(
        {
            "service": "Safe Link Visual MCP",
            "mcp_endpoint": "/mcp",
            "tools": ["is_safety", "safety_explain", "site_image"],
            "http_demo": {
                "inspect": "/inspect?url=https://example.com",
                "site_image": "/site-image?url=https://example.com",
            },
            "query": query,
        }
    )


routes = [
    Route("/", openapi_hint, methods=["GET"]),
    Route("/healthz", healthz, methods=["GET"]),
    Route("/inspect", inspect_get, methods=["GET"]),
    Route("/inspect", inspect_post, methods=["POST"]),
    Route("/site-image", site_image_get, methods=["GET"]),
    Mount("/", app=mcp.streamable_http_app()),
]


@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    async with mcp.session_manager.run():
        await warm_browser()
        yield


app = Starlette(routes=routes, lifespan=lifespan)
