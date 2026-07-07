# PlayMCP Submission Fields

이 문서는 PlayMCP와 Git 소스 빌드 화면에 그대로 옮겨 적기 위한 값만 모았습니다.

## Git 소스 빌드

```text
MCP 서버 이름: safelink-visual
설명: 링크를 열기 전 안전 여부와 핵심 화면 요약 이미지를 제공하는 MCP 서버
Git URL: https://github.com/studyreadbook4ever/safe-link-visual-mcp.git
브랜치 / ref: main
Dockerfile 경로: Dockerfile
PAT: 비공개 저장소일 때만 입력
```

`safelink-visual`은 Kubernetes 리소스 이름 규칙에 맞춘 소문자 영문/하이픈 이름입니다.

## 새로운 MCP 서버 등록

```text
팀프로필 이름: eff0rtchung
대표 이미지: assets/playmcp-cover.png
MCP 이름: Safe Link Visual
MCP 식별자: safeLinkVisual
MCP 설명: 학습 데이터셋은 사용하지 않습니다. URL·DNS·HTTP·HTML·모바일 렌더링 신호를 OWASP SSRF, IANA 특수 IP, IETF URI/IDNA, MDN, Google Safe Browsing 공개 문서를 참고한 규칙으로 검사해 '완전 안전하다/위험할 수 있다'로 판정하고 핵심 화면 요약 이미지를 제공합니다.
인증 방식: 인증 사용하지 않음
MCP Endpoint: https://safelink-visual.playmcp-endpoint.kakaocloud.io/mcp
```

`safeLinkVisual`은 영문/숫자만 사용하며 14자라서 PlayMCP 식별자 제한인 16자 이하를 만족합니다.

## 대화 예시

각 문장은 40자 이하입니다.

```text
이 링크 위험해?
피싱 링크인지 봐줘
사이트 요약 이미지 보여줘
```

## MCP Tools

```text
is_safety(url) -> boolean
safety_explain(url) -> compact Korean report object
site_image(url) -> image/png
```

`is_safety`는 semantic 분류 결과를 boolean으로 반환합니다. `true`는 `완전 안전하다`, `false`는 `위험할 수 있다`를 의미합니다.

`site_image`는 모바일 Safari 계열 User-Agent로 접근한 뒤 작은 장식 요소를 제외하고 큰 제목, 폼, 버튼, 이미지 같은 핵심 요소를 중심으로 1024x1024 PNG 요약 이미지를 만듭니다.

## 최종 확인 명령

```bash
PYTHON_BIN=.venv/bin/python scripts/verify_local.sh
scripts/create_submission_bundle.sh
```
