import re
import tomllib
from pathlib import Path

from PIL import Image

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


def test_playmcp_representative_image_exists() -> None:
    path = Path("assets/playmcp-cover.png")
    assert path.exists()
    assert path.suffix == ".png"
    with Image.open(path) as image:
        assert image.size[0] >= 600
        assert image.size[1] >= 600
