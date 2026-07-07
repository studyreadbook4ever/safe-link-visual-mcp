# Safe Link Visual MCP

Safe Link Visual MCP(세이프 링크 비주얼 MCP)는 사용자가 URL을 열기 전에 링크의 피싱 위험을 보수적으로 분류하고, 필요한 경우 모바일 화면의 핵심 픽셀을 1024x1024 정사각형 이미지로 압축해 제공하는 Remote MCP 서버입니다.

이 서버는 PlayMCP 등록을 염두에 두고 Streamable HTTP, stateless 동작, 3개 도구 구성, 명시적 tool annotations, 정제된 응답 형식을 사용합니다.

## What It Does

- URL을 `완전 안전하다` 또는 `위험할 수 있다`로 2진 분류합니다.
- `is_safety`와 `safety_explain`은 빠른 응답을 위해 URL, DNS, HTTP, HTML 신호만 사용합니다.
- `site_image`는 Playwright 모바일 렌더링을 사용해 실제 사이트 화면의 중요한 영역과 위험 근거를 하나의 PNG 이미지로 압축합니다.
- 서버는 링크를 iframe으로 임베드하지 않고, 격리된 임시 브라우저 컨텍스트에서 관찰한 결과만 반환합니다.

## Data And References

학습 데이터셋은 사용하지 않습니다. Safe Link Visual MCP는 외부 피싱 데이터셋이나 Safe Browsing API를 호출하지 않는 규칙 기반 휴리스틱 검사기입니다.

참고한 공개 문서:

- OWASP Server-Side Request Forgery Prevention Cheat Sheet
- IANA IPv4/IPv6 Special-Purpose Address Registries
- IETF RFC 3986 URI Generic Syntax
- IETF RFC 5890 Internationalized Domain Names for Applications
- MDN URI authority and HTML password input references
- Google Safe Browsing public documentation

## PlayMCP Compatibility

| Item | Value |
| --- | --- |
| MCP transport | Streamable HTTP |
| Server type | Remote MCP server |
| Default endpoint | `/mcp` |
| Session model | Stateless HTTP enabled |
| Auth | None. This server is read-only and does not require user account data. |
| Tool count | 3 |
| Disallowed server/tool name text | Does not use `kakao` in server or tool names |
| SDK | Official Python MCP SDK `mcp>=1.28.1,<1.29` |
| Verified protocol version | `2025-11-25` through SDK initialize smoke |

PlayMCP URL example after deployment:

```text
https://YOUR_PUBLIC_DOMAIN/mcp
```

## PlayMCP Console Copy-Paste Fields

Use these values when registering the public endpoint in PlayMCP.
The full field-by-field Korean submission sheet is in `PLAYMCP_SUBMISSION.md`.

```text
MCP identifier: safeLinkVisual
MCP display name: Safe Link Visual
Server name: Safe Link Visual MCP
Korean name: 세이프 링크 비주얼 MCP
Endpoint URL: https://YOUR_PUBLIC_DOMAIN/mcp
Authentication: None
Transport: Streamable HTTP
```

`safeLinkVisual` is intentionally alphanumeric and 14 characters long because the PlayMCP identifier field allows only English letters/numbers and up to 16 characters.

Git source build fields:

```text
MCP server name: safelink-visual
Description: 링크를 열기 전 안전 여부와 핵심 화면 요약 이미지를 제공하는 MCP 서버
Git URL: https://github.com/studyreadbook4ever/safe-link-visual-mcp.git
Branch/ref: main
Dockerfile path: Dockerfile
PAT: private repository only
```

Short description:

```text
학습 데이터셋은 사용하지 않습니다. URL·DNS·HTTP·HTML·모바일 렌더링 신호를 OWASP SSRF, IANA 특수 IP, IETF URI/IDNA, MDN, Google Safe Browsing 공개 문서를 참고한 규칙으로 검사해 '완전 안전하다/위험할 수 있다'로 판정하고 핵심 화면 요약 이미지를 제공합니다.
```

Long description:

```text
Safe Link Visual MCP(세이프 링크 비주얼 MCP)는 사용자가 낯선 링크를 누르기 전에 URL, DNS, HTTP, HTML, 모바일 렌더링 신호를 검사합니다. 결과는 '완전 안전하다' 또는 '위험할 수 있다'로 단순하게 나누고, 비전공자도 이해할 수 있는 한국어 근거와 추천 행동을 제공합니다. 사이트를 iframe으로 임베드하지 않고 임시 브라우저 컨텍스트에서 관찰한 정보만 사용하며, 느린 사이트는 제한 시간 안에서 보수적으로 위험 판정합니다.
```

## Tools

### `is_safety`

Checks whether a URL is classified as safe by Safe Link Visual MCP(세이프 링크 비주얼 MCP). Returns `true` only for `완전 안전하다` and `false` for `위험할 수 있다`.

Input:

```json
{
  "url": "https://example.com"
}
```

Output:

```json
true
```

Annotations:

```json
{
  "title": "Check Link Safety",
  "readOnlyHint": true,
  "destructiveHint": false,
  "openWorldHint": true,
  "idempotentHint": true
}
```

### `safety_explain`

Returns a compact Korean evidence report from Safe Link Visual MCP(세이프 링크 비주얼 MCP) explaining the binary safety decision. Large image data is excluded.

Input:

```json
{
  "url": "https://example.com"
}
```

Output shape:

```json
{
  "decision": {
    "label": "완전 안전하다",
    "is_safety": true,
    "plain_summary": "자동 검사에서 바로 보이는 피싱 위험 신호는 찾지 못했습니다...",
    "action_advice": "주소가 예상한 사이트와 맞다면 열어도 됩니다..."
  },
  "input_url": "https://example.com",
  "final_url": "https://example.com/",
  "is_safety": true,
  "verdict": "완전 안전하다",
  "risk_score": 0,
  "confidence": 0.72,
  "summary": "명확한 위험 신호를 찾지 못했습니다...",
  "signals": [],
  "report": "# 링크 안전 브리핑..."
}
```

Annotations:

```json
{
  "title": "Explain Link Safety",
  "readOnlyHint": true,
  "destructiveHint": false,
  "openWorldHint": true,
  "idempotentHint": true
}
```

### `site_image`

Creates a 1024x1024 PNG visual digest with key mobile-page pixels and safety cues from Safe Link Visual MCP(세이프 링크 비주얼 MCP). Use this when the user needs a compressed visual preview before opening a URL.

The renderer visits the URL with a mobile Safari-like User-Agent, ignores tiny decorative elements, and crops around larger headings, forms, buttons, images, and other high-signal blocks.

Input:

```json
{
  "url": "https://example.com"
}
```

Output:

```text
image/png
```

Annotations:

```json
{
  "title": "Create Site Image",
  "readOnlyHint": true,
  "destructiveHint": false,
  "openWorldHint": true,
  "idempotentHint": true
}
```

## Ensemble Signals

The current MVP works without external API keys.

- URL lexical signals: HTTPS, long URL, `@`/userinfo, IP literal, punycode, excessive subdomains, suspicious terms, brand-domain mismatch
- Network/HTTP signals: SSRF-safe DNS check, redirects, final-domain change, status code, content type
- HTML signals: password forms, sensitive input fields, executable download links, brand impersonation terms, urgency terms
- Visual signals: used only by `site_image`, based on a mobile Playwright render

The classifier is intentionally conservative. Unknown, unreachable, private-network, or suspicious login-like targets are more likely to become `위험할 수 있다`.

## HTTP Demo Endpoints

These endpoints are not required for MCP clients, but they are useful for deployment smoke tests.

```bash
curl "http://localhost:8000/healthz"
curl "http://localhost:8000/inspect?url=https://example.com"
curl "http://localhost:8000/site-image?url=https://example.com" --output site-image.png
```

To include the image in `/inspect`, pass `include_image=true`.

```bash
curl "http://localhost:8000/inspect?url=https://example.com&include_image=true"
```

## Run Locally

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
python -m playwright install chromium
uvicorn safelink_mcp.asgi:app --host 0.0.0.0 --port 8000
```

MCP endpoint:

```text
http://localhost:8000/mcp
```

Full local verification:

```bash
scripts/verify_local.sh
```

If your Python binary is not `python3`:

```bash
PYTHON_BIN=.venv/bin/python scripts/verify_local.sh
```

## Docker

```bash
docker build -t safe-link-visual-mcp:latest .
docker run --rm -p 8000:8000 safe-link-visual-mcp:latest
```

If you prefer Podman:

```bash
podman build -t safe-link-visual-mcp:latest .
podman run --rm -p 8000:8000 safe-link-visual-mcp:latest
```

Arch Linux quick install:

```bash
sudo pacman -S docker docker-buildx
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Log out and back in after `usermod`, then run:

```bash
scripts/build_image.sh
```

Docker Compose:

```bash
docker compose up --build -d
docker compose logs -f safe-link-visual-mcp
```

## Git / CI Image Build

`.github/workflows/container.yml` runs tests, Playwright smoke tests, and Docker image builds.

- `main` branch or `v*` tag push: pushes `ghcr.io/<owner>/safe-link-visual-mcp`
- `workflow_dispatch`: creates a `safe-link-visual-mcp.tar` image artifact for manual upload

Source bundle without local virtualenv/cache files:

```bash
scripts/create_submission_bundle.sh
```

The archive is written to `dist/safe-link-visual-mcp-source.tar.gz`.

## Environment

```text
SAFE_LINK_FAST_BUDGET=2.4
SAFE_LINK_VISUAL_BUDGET=2.8
SAFE_LINK_TIMEOUT=2
SAFE_LINK_RENDER_TIMEOUT=2
SAFE_LINK_MAX_REDIRECTS=5
MCP_TRANSPORT=streamable-http
```

`SAFE_LINK_FAST_BUDGET` is the full wall-clock budget for `is_safety` and `safety_explain`. `SAFE_LINK_VISUAL_BUDGET` is the full wall-clock budget for `site_image`. When a URL is too slow, the server returns a conservative `위험할 수 있다` result instead of a raw timeout error.

`MCP_TRANSPORT=stdio` is available for local debugging only. PlayMCP deployment should use Streamable HTTP.

## Security Notes

- `file://`, `localhost`, private IPs, link-local addresses, reserved IPs, and metadata-like targets are blocked before fetching.
- `user:pass@host` style URLs are blocked because they can hide the real destination.
- The browser context is temporary, mobile-sized, and download-disabled.
- No OAuth flow is implemented because this service does not access user accounts or store user-private data.
- The result is a risk-reduction aid, not an absolute security guarantee.

## PlayMCP Registration Checklist

1. Deploy the container to a public HTTPS domain.
2. Register the MCP endpoint as `https://YOUR_PUBLIC_DOMAIN/mcp`.
3. Confirm the server name is `Safe Link Visual MCP`.
4. Confirm the PlayMCP identifier is `safeLinkVisual`.
5. Confirm tool names are exactly `is_safety`, `safety_explain`, and `site_image`.
6. Upload the representative image from `assets/playmcp-cover.png`.
7. Run MCP Inspector against the public endpoint before submission.
8. Verify `/healthz` returns `{"ok": true, "service": "safe-link-visual-mcp"}`.

## AGENTIC PLAYER 10 Submission Notes

Official public pages checked on 2026-07-07:

- Contest page: `https://b.kakao.com/views/PlayMCP/AGENTIC_PlAYER_10`
- Kakao press release: `https://www.kakaocorp.com/page/detail/12059`

Current contest flow:

1. Create an MCP server endpoint on KakaoCloud.
2. Register that endpoint in PlayMCP Developer Console using `새로운 MCP 서버 등록`.
3. Use `임시 등록` while testing. Do not submit review from a temporary server.
4. When final, use `등록 및 심사 요청`.
5. After approval, change visibility from `나에게만 공개` to `전체 공개`.
6. Return to the contest page and press `Player 예선 참여`.

Published schedule:

| Step | Period |
| --- | --- |
| Preliminary registration | 2026-06-15 ~ 2026-07-14 |
| Preliminary result | 2026-07-30 |
| Finalist development | 2026-07-30 ~ 2026-08-27 |
| User voting | 2026-08-31 ~ 2026-09-28 |
| Final award ceremony | 2026-10-23 |

Judging emphasis from the official contest page:

- Creativity: Does the idea solve a problem in a new way?
- Convenience: Does the UI/UX give practical everyday value?
- Stability: Does it run reliably, provide accurate data, and avoid security issues?

This project is positioned for that rubric as a link safety briefing tool for non-CS users:

- `is_safety`: quick yes/no safety decision.
- `safety_explain`: plain Korean reason and next action.
- `site_image`: compressed square visual evidence card.

## PlayMCP Inspector Smoke

With dependencies installed:

```bash
PYTHON_BIN=.venv/bin/python scripts/inspect_playmcp.sh
```

This starts the Streamable HTTP server on `127.0.0.1:8765`, runs MCP Inspector `tools/list`, calls all three tools, and verifies `site_image` returns `image/png`.
It also opens a Python SDK Streamable HTTP session and checks `protocolVersion` is between `2025-03-26` and `2025-11-25`.
