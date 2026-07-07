from __future__ import annotations

import asyncio
import os
import time
from collections import OrderedDict

from safelink_mcp.digest import build_digest_image
from safelink_mcp.models import InspectionResult, RenderedPage, RiskSignal
from safelink_mcp.render import render_mobile_page
from safelink_mcp.safety import (
    analyze_html,
    analyze_rendered_page,
    analyze_url_lexical,
    combine_signals,
    fetch_metadata,
    normalize_url,
)


class InspectionCache:
    def __init__(self, max_size: int = 128, ttl_seconds: int = 600) -> None:
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._items: OrderedDict[str, tuple[float, InspectionResult]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get_or_set(self, key: str, factory) -> InspectionResult:
        now = time.time()
        async with self._lock:
            if key in self._items:
                created_at, result = self._items[key]
                if now - created_at <= self.ttl_seconds:
                    self._items.move_to_end(key)
                    return result
                self._items.pop(key, None)

        result = await factory()

        async with self._lock:
            self._items[key] = (time.time(), result)
            self._items.move_to_end(key)
            while len(self._items) > self.max_size:
                self._items.popitem(last=False)
        return result


cache = InspectionCache()


def _budget_seconds(include_visual: bool) -> float:
    env_name = "SAFE_LINK_VISUAL_BUDGET" if include_visual else "SAFE_LINK_FAST_BUDGET"
    default = "2.8" if include_visual else "2.4"
    try:
        return max(0.3, float(os.getenv(env_name, default)))
    except ValueError:
        return float(default)


def _timeout_result(
    input_url: str,
    normalized: str,
    *,
    include_visual: bool,
) -> InspectionResult:
    signals = analyze_url_lexical(normalized)
    signals.append(
        RiskSignal(
            "runtime",
            "검사 시간 초과",
            42,
            "정해진 시간 안에 전체 검사를 끝내지 못했습니다. 안전을 확신할 수 없어 보수적으로 막았습니다.",
            "high",
        )
    )
    is_safety, risk_score, confidence, summary = combine_signals(signals)
    rendered = RenderedPage(
        error="검사 시간이 초과되어 실제 화면 일부를 가져오지 못했습니다."
    )
    result = InspectionResult(
        input_url=input_url,
        normalized_url=normalized,
        final_url=normalized,
        is_safety=is_safety,
        verdict="완전 안전하다" if is_safety else "위험할 수 있다",
        risk_score=risk_score,
        confidence=confidence,
        summary=summary,
        signals=signals,
        render_error=rendered.error if include_visual else None,
    )
    if include_visual:
        result.digest_png = build_digest_image(result, rendered)
    return result


async def inspect_url(
    url: str,
    *,
    use_cache: bool = True,
    include_visual: bool = True,
) -> InspectionResult:
    normalized = normalize_url(url)
    cache_key = f"{normalized}|visual={int(include_visual)}"
    budget = _budget_seconds(include_visual)
    try:
        if use_cache:
            return await asyncio.wait_for(
                cache.get_or_set(
                    cache_key,
                    lambda: _inspect_uncached(url, normalized, include_visual=include_visual),
                ),
                timeout=budget,
            )
        return await asyncio.wait_for(
            _inspect_uncached(url, normalized, include_visual=include_visual),
            timeout=budget,
        )
    except TimeoutError:
        return _timeout_result(url, normalized, include_visual=include_visual)


async def _inspect_uncached(
    input_url: str,
    normalized: str,
    *,
    include_visual: bool,
) -> InspectionResult:
    signals: list[RiskSignal] = []
    signals.extend(analyze_url_lexical(normalized))

    fetch = await fetch_metadata(normalized)
    signals.extend(fetch.signals)

    html_title = ""
    visible_sample = ""
    if fetch.html:
        html_signals, html_meta = analyze_html(fetch.html, fetch.final_url)
        # fetch_metadata already includes html signals, but running here gives title/text metadata.
        html_title = html_meta.get("title", "")
        visible_sample = html_meta.get("text", "")[:1200]
        known = {(signal.source, signal.label, signal.evidence) for signal in signals}
        for signal in html_signals:
            key = (signal.source, signal.label, signal.evidence)
            if key not in known:
                signals.append(signal)

    rendered = RenderedPage()
    if include_visual:
        rendered = (
            RenderedPage(error="네트워크 차단 대상은 브라우저로 열지 않았습니다.")
            if fetch.blocked_reason
            else await render_mobile_page(fetch.final_url)
        )
        signals.extend(analyze_rendered_page(rendered, fetch.final_url))

    is_safety, risk_score, confidence, summary = combine_signals(signals)
    verdict = "완전 안전하다" if is_safety else "위험할 수 있다"

    result = InspectionResult(
        input_url=input_url,
        normalized_url=normalized,
        final_url=fetch.final_url,
        is_safety=is_safety,
        verdict=verdict,
        risk_score=risk_score,
        confidence=confidence,
        summary=summary,
        signals=signals,
        redirects=fetch.redirects,
        http_status=fetch.status_code,
        headers=fetch.headers,
        title=rendered.title or html_title,
        visible_text_sample=(rendered.visible_text or visible_sample)[:1200],
        render_error=rendered.error,
        blocked_reason=fetch.blocked_reason,
    )
    if include_visual:
        result.digest_png = build_digest_image(result, rendered)
    return result
