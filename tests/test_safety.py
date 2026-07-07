import asyncio

import pytest

from safelink_mcp import inspector as inspector_module
from safelink_mcp.safety import analyze_url_lexical, combine_signals, normalize_url
from safelink_mcp.models import InspectionResult, RiskSignal


def test_normalize_adds_https() -> None:
    assert normalize_url("example.com") == "https://example.com/"


def test_brand_impersonation_is_risky() -> None:
    signals = analyze_url_lexical("https://kakao-login.example.com/")
    labels = {signal.label for signal in signals}
    assert "브랜드명 도메인 착시" in labels
    is_safety, score, _, _ = combine_signals(signals)
    assert not is_safety
    assert score >= 35


def test_plain_https_url_can_be_safe() -> None:
    signals = analyze_url_lexical("https://example.com/")
    is_safety, score, _, _ = combine_signals(signals)
    assert is_safety
    assert score == 0


def test_explain_dict_has_non_expert_fields() -> None:
    result = InspectionResult(
        input_url="http://kakao-login.example.com/",
        normalized_url="http://kakao-login.example.com/",
        final_url="http://kakao-login.example.com/",
        is_safety=False,
        verdict="위험할 수 있다",
        risk_score=80,
        confidence=0.9,
        summary="브랜드명 도메인 착시 신호 때문에 위험할 수 있다로 분류했습니다.",
        signals=[
            RiskSignal(
                "brand",
                "브랜드명 도메인 착시",
                36,
                "호스트에 브랜드명이 있지만 공식 도메인이 아닙니다.",
                "high",
            )
        ],
    )

    payload = result.explain_dict()

    assert payload["decision"]["label"] == "위험할 수 있다"
    assert payload["decision"]["is_safety"] is False
    assert "공식 앱이나 검색" in payload["decision"]["action_advice"]
    assert payload["top_reasons"]
    assert payload["signals"][0]["plain_evidence"]
    assert "링크 열기 전 안전 브리핑" in payload["report"]


@pytest.mark.asyncio
async def test_timeout_result_is_conservative(monkeypatch: pytest.MonkeyPatch) -> None:
    async def slow_inspection(*_: object, **__: object) -> InspectionResult:
        await asyncio.sleep(1)
        raise AssertionError("timeout test should not reach this line")

    monkeypatch.setenv("SAFE_LINK_FAST_BUDGET", "0.3")
    monkeypatch.setattr(inspector_module, "_inspect_uncached", slow_inspection)

    result = await inspector_module.inspect_url(
        "https://example.com",
        use_cache=False,
        include_visual=False,
    )

    assert result.verdict == "위험할 수 있다"
    assert result.is_safety is False
    assert any(signal.label == "검사 시간 초과" for signal in result.signals)
