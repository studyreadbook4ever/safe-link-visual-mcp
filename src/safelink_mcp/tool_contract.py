SERVER_NAME = "Safe Link Visual MCP"
SERVICE_NAME = "Safe Link Visual MCP(세이프 링크 비주얼 MCP)"
PLAYMCP_IDENTIFIER = "safeLinkVisual"
K8S_RESOURCE_NAME = "safelink-visual"
MCP_DISPLAY_NAME = "Safe Link Visual"
MCP_DISPLAY_NAME_KO = "세이프 링크 비주얼"

READ_ONLY_OPEN_WORLD_ANNOTATIONS = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "openWorldHint": True,
    "idempotentHint": True,
}

TOOL_CONTRACTS = {
    "is_safety": {
        "title": "Check Link Safety",
        "description": (
            f"Checks whether a URL is classified as safe by {SERVICE_NAME}. "
            "Returns true only for '완전 안전하다' and false for '위험할 수 있다'. "
            "Uses a fast read-only ensemble of URL, DNS, HTTP, and HTML signals."
        ),
        "annotations": {
            "title": "Check Link Safety",
            **READ_ONLY_OPEN_WORLD_ANNOTATIONS,
        },
    },
    "safety_explain": {
        "title": "Explain Link Safety",
        "description": (
            f"Returns a compact Korean evidence report from {SERVICE_NAME} explaining "
            "the binary safety decision for a URL. The result is read-only and excludes "
            "large image data."
        ),
        "annotations": {
            "title": "Explain Link Safety",
            **READ_ONLY_OPEN_WORLD_ANNOTATIONS,
        },
    },
    "site_image": {
        "title": "Create Site Image",
        "description": (
            f"Creates a 1024x1024 PNG visual digest with key mobile-page pixels and safety "
            f"cues from {SERVICE_NAME}. Use this when the user needs a compressed visual "
            "preview of a URL before opening it."
        ),
        "annotations": {
            "title": "Create Site Image",
            **READ_ONLY_OPEN_WORLD_ANNOTATIONS,
        },
    },
}
