import re
import tomllib
from pathlib import Path

from PIL import Image

from safelink_mcp.server import mcp
from safelink_mcp.tool_contract import (
    K8S_RESOURCE_NAME,
    PLAYMCP_IDENTIFIER,
    SERVER_NAME,
    SERVICE_NAME,
    TOOL_CONTRACTS,
)


def test_playmcp_tool_contract() -> None:
    names = set(TOOL_CONTRACTS)

    assert 1 <= len(SERVER_NAME) <= 128
    assert "kakao" not in SERVER_NAME.lower()
    assert re.fullmatch(r"[A-Za-z0-9]{1,16}", PLAYMCP_IDENTIFIER)
    assert "kakao" not in PLAYMCP_IDENTIFIER.lower()
    assert re.fullmatch(r"[a-z0-9]([-a-z0-9.]*[a-z0-9])?", K8S_RESOURCE_NAME)
    assert "kakao" not in K8S_RESOURCE_NAME.lower()
    assert names == {"is_safety", "safety_explain", "site_image"}
    assert 3 <= len(TOOL_CONTRACTS) <= 10

    for name, contract in TOOL_CONTRACTS.items():
        assert re.fullmatch(r"[A-Za-z0-9_-]{1,128}", name)
        assert "kakao" not in name.lower()
        assert contract["description"]
        assert SERVICE_NAME in contract["description"]
        assert len(contract["description"]) <= 1024
        annotations = contract["annotations"]
        assert annotations["title"]
        assert annotations["readOnlyHint"] is True
        assert annotations["destructiveHint"] is False
        assert annotations["openWorldHint"] is True
        assert annotations["idempotentHint"] is True


def test_mcp_sdk_dependency_is_pinned_to_verified_playmcp_protocol() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    dependencies = pyproject["project"]["dependencies"]
    mcp_dependency = next(item for item in dependencies if item.startswith("mcp[cli]"))

    assert ">=1.28.1" in mcp_dependency
    assert "<1.29" in mcp_dependency


def test_playmcp_endpoint_host_is_allowed_by_mcp_transport_security() -> None:
    security = mcp.settings.transport_security

    assert security is not None
    assert security.enable_dns_rebinding_protection is True
    assert "safelink-visual.playmcp-endpoint.kakaocloud.io" in security.allowed_hosts
    assert "https://playmcp.kakao.com" in security.allowed_origins


def test_playmcp_representative_image_exists() -> None:
    path = Path("assets/playmcp-cover.png")
    assert path.exists()
    assert path.suffix == ".png"
    with Image.open(path) as image:
        assert image.size[0] >= 600
        assert image.size[1] >= 600


def test_playmcp_submission_sheet_matches_form_limits() -> None:
    text = Path("PLAYMCP_SUBMISSION.md").read_text()

    def value_for(label: str) -> str:
        match = re.search(rf"^{re.escape(label)}:\s*(.+)$", text, re.MULTILINE)
        assert match, f"missing field: {label}"
        return match.group(1).strip()

    server_name = value_for("MCP 서버 이름")
    git_url = value_for("Git URL")
    display_name = value_for("MCP 이름")
    identifier = value_for("MCP 식별자")
    description = value_for("MCP 설명")
    endpoint = value_for("MCP Endpoint")

    assert server_name == K8S_RESOURCE_NAME
    assert re.fullmatch(r"[a-z0-9]([-a-z0-9.]*[a-z0-9])?", server_name)
    assert git_url == "https://github.com/studyreadbook4ever/safe-link-visual-mcp.git"
    assert display_name == "Safe Link Visual"
    assert len(display_name) <= 30
    assert identifier == PLAYMCP_IDENTIFIER
    assert re.fullmatch(r"[A-Za-z0-9]{1,16}", identifier)
    assert len(description) <= 500
    assert endpoint == "https://safelink-visual.playmcp-endpoint.kakaocloud.io/mcp"

    examples_match = re.search(r"## 대화 예시.*?```text\n(.*?)```", text, re.DOTALL)
    assert examples_match
    examples = [line.strip() for line in examples_match.group(1).splitlines() if line.strip()]
    assert len(examples) == 3
    assert all(len(example) <= 40 for example in examples)
