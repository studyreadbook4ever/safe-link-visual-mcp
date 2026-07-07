from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


Verdict = Literal["완전 안전하다", "위험할 수 있다"]


@dataclass(slots=True)
class RiskSignal:
    source: str
    label: str
    score: int
    evidence: str
    severity: Literal["info", "low", "medium", "high", "critical"] = "low"

    def plain_evidence(self) -> str:
        evidence = self.evidence
        if "DNS 조회 실패" in evidence:
            return "주소가 정상적으로 확인되지 않아 접속하지 않았습니다."
        if "내부망/예약 IP" in evidence:
            return "개인 PC나 내부망 주소로 이어질 수 있어 열지 않았습니다."
        if "공식 도메인" in evidence and "호스트에" in evidence:
            return "주소에 유명 서비스명이 섞여 있지만 공식 주소가 아닙니다."
        if "HTTP 링크" in evidence or "HTTP입니다" in evidence:
            return "암호화되지 않은 링크라 로그인이나 결제에 부적절합니다."
        if "URL에" in evidence and "단어가 포함" in evidence:
            return "로그인, 인증, 계정 확인 같은 행동 유도 단어가 보입니다."
        if len(evidence) > 88:
            return evidence[:85].rstrip() + "..."
        return evidence

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "label": self.label,
            "score": self.score,
            "severity": self.severity,
            "evidence": self.evidence,
            "plain_evidence": self.plain_evidence(),
        }


@dataclass(slots=True)
class RenderedPage:
    screenshot_png: bytes | None = None
    title: str = ""
    visible_text: str = ""
    elements: list[dict[str, Any]] = field(default_factory=list)
    forms: list[dict[str, Any]] = field(default_factory=list)
    buttons: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass(slots=True)
class InspectionResult:
    input_url: str
    normalized_url: str
    final_url: str
    is_safety: bool
    verdict: Verdict
    risk_score: int
    confidence: float
    summary: str
    signals: list[RiskSignal]
    redirects: list[str] = field(default_factory=list)
    http_status: int | None = None
    headers: dict[str, str] = field(default_factory=dict)
    title: str = ""
    visible_text_sample: str = ""
    digest_png: bytes | None = None
    render_error: str | None = None
    blocked_reason: str | None = None

    def plain_summary(self) -> str:
        if self.is_safety:
            return (
                "자동 검사에서 바로 보이는 피싱 위험 신호는 찾지 못했습니다. "
                "링크를 열기 전 주소의 도메인이 기대한 사이트와 맞는지만 한 번 더 확인하세요."
            )
        top_labels = ", ".join(
            signal.label for signal in sorted(self.signals, key=lambda item: item.score, reverse=True)[:2]
        )
        if top_labels:
            return f"{top_labels} 신호가 보여서 이 링크는 바로 누르지 않는 편이 좋습니다."
        return "검사 결과가 불완전하거나 위험 신호가 있어 이 링크는 바로 누르지 않는 편이 좋습니다."

    def action_advice(self) -> str:
        if self.is_safety:
            return "주소가 예상한 사이트와 맞다면 열어도 됩니다. 로그인이나 결제를 요구하면 다시 확인하세요."
        return "링크를 열지 말고, 필요하면 공식 앱이나 검색으로 직접 접속하세요."

    def top_reasons(self) -> list[str]:
        if not self.signals:
            return ["강한 위험 신호 없음"]
        return [
            f"{signal.label}: {signal.plain_evidence()}"
            for signal in sorted(self.signals, key=lambda item: item.score, reverse=True)[:3]
        ]

    def explain_dict(self) -> dict[str, Any]:
        return {
            "decision": {
                "label": self.verdict,
                "is_safety": self.is_safety,
                "plain_summary": self.plain_summary(),
                "action_advice": self.action_advice(),
            },
            "input_url": self.input_url,
            "normalized_url": self.normalized_url,
            "final_url": self.final_url,
            "is_safety": self.is_safety,
            "verdict": self.verdict,
            "risk_score": self.risk_score,
            "confidence": self.confidence,
            "summary": self.summary,
            "http_status": self.http_status,
            "redirects": self.redirects,
            "title": self.title,
            "top_reasons": self.top_reasons(),
            "checked_items": [
                "URL 형태",
                "DNS/내부망 차단",
                "리다이렉트",
                "HTTP 상태",
                "HTML 제목/본문",
                "로그인/비밀번호/민감정보 입력폼",
                "브랜드명과 실제 도메인 불일치",
            ],
            "blocked_reason": self.blocked_reason,
            "render_error": self.render_error,
            "headers": {
                key: value
                for key, value in self.headers.items()
                if key.lower()
                in {
                    "content-type",
                    "location",
                    "server",
                    "x-frame-options",
                    "content-security-policy",
                    "strict-transport-security",
                }
            },
            "signals": [signal.as_dict() for signal in self.signals],
            "report": self.report_markdown(),
        }

    def report_markdown(self) -> str:
        lines = [
            "# 링크 열기 전 안전 브리핑",
            "",
            f"- 판정: **{self.verdict}**",
            f"- 한 줄 요약: {self.plain_summary()}",
            f"- 추천 행동: {self.action_advice()}",
            f"- 위험 점수: `{self.risk_score}/100`",
            f"- 최종 URL: `{self.final_url or self.normalized_url}`",
        ]
        if self.http_status is not None:
            lines.append(f"- HTTP 상태: `{self.http_status}`")
        if self.blocked_reason:
            lines.append(f"- 차단 사유: {self.blocked_reason}")
        if self.render_error:
            lines.append(f"- 렌더링 참고: {self.render_error}")
        lines.extend(["", "## 쉬운 설명", self.plain_summary(), "", "## 판단 근거"])
        if not self.signals:
            lines.append("- 명확한 위험 신호를 찾지 못했습니다.")
        for signal in sorted(self.signals, key=lambda item: item.score, reverse=True):
            lines.append(
                f"- {signal.label}: {signal.plain_evidence()}"
            )
        lines.extend(
            [
                "",
                "## 확인한 항목",
                "- URL 형태, DNS/내부망 차단, 리다이렉트, HTTP 상태, HTML 본문, 민감정보 입력폼, 브랜드-도메인 불일치",
            ]
        )
        return "\n".join(lines)
