# KakaoCloud Deployment Notes

이 프로젝트는 컨테이너 이미지 또는 Git 기반 배포에 맞춰 준비되어 있습니다.

## Container Image

```bash
docker build -t safe-link-visual-mcp:latest .
docker run --rm -p 8000:8000 safe-link-visual-mcp:latest
```

배포 후 확인:

```bash
curl http://YOUR_HOST:8000/healthz
curl "http://YOUR_HOST:8000/inspect?url=https://example.com"
curl "http://YOUR_HOST:8000/site-image?url=https://example.com" --output site-image.png
```

MCP endpoint:

```text
http://YOUR_HOST:8000/mcp
```

## Compose

```bash
docker compose up --build -d
docker compose logs -f safe-link-visual-mcp
```

## Git-Based Build

KakaoCloud가 Git repository를 직접 받아 컨테이너를 빌드하는 경우:

- Build context: repository root
- Dockerfile: `Dockerfile`
- Exposed port: `8000`
- Health check path: `/healthz`
- MCP path: `/mcp`

GitHub Actions를 사용할 수 있다면 `.github/workflows/container.yml`에서 이미지를 빌드합니다.

- `main` branch 또는 `v*` tag push: `ghcr.io/<owner>/safe-link-visual-mcp` 이미지 push
- 수동 실행(`workflow_dispatch`): `safe-link-visual-mcp.tar` artifact 생성

이미지 tar를 받은 뒤 서버에서 직접 로드할 수도 있습니다.

```bash
docker load -i safe-link-visual-mcp.tar
docker run --rm -p 8000:8000 safe-link-visual-mcp:local
```

## Runtime Environment

선택 환경변수:

```text
SAFE_LINK_FAST_BUDGET=2.4
SAFE_LINK_VISUAL_BUDGET=2.8
SAFE_LINK_TIMEOUT=2
SAFE_LINK_RENDER_TIMEOUT=2
SAFE_LINK_MAX_REDIRECTS=5
```

`SAFE_LINK_FAST_BUDGET`와 `SAFE_LINK_VISUAL_BUDGET`는 각 도구 호출의 전체 응답 시간 예산입니다. 시간이 초과되면 raw error 대신 `위험할 수 있다` 판정과 쉬운 설명을 반환합니다.

## Expected MCP Tools

- `is_safety(url)` -> boolean
- `safety_explain(url)` -> report object
- `site_image(url)` -> PNG image

## Final PlayMCP Submission Flow

1. KakaoCloud에서 MCP 서버 Endpoint를 생성합니다.
2. PlayMCP 개발자 콘솔의 `새로운 MCP 서버 등록`에 아래 URL을 등록합니다.

```text
https://YOUR_PUBLIC_DOMAIN/mcp
```

3. 개발 중에는 `임시 등록`으로 테스트합니다.
4. 최종 서버가 준비되면 `등록 및 심사 요청`을 누릅니다.
5. 심사 통과 후 공개 상태를 `전체 공개`로 바꿉니다.
6. AGENTIC PLAYER 10 페이지에서 `Player 예선 참여`를 눌러 제출합니다.

로컬 Inspector 스모크 테스트:

```bash
PYTHON_BIN=.venv/bin/python scripts/inspect_playmcp.sh
```

이 스크립트는 SDK initialize 응답의 `protocolVersion`이 `2025-03-26` 이상, `2025-11-25` 이하인지도 함께 확인합니다.
