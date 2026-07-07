from __future__ import annotations

import asyncio
import ipaddress
import os
import re
import socket
from dataclasses import dataclass
from html import unescape
from typing import Any
from urllib.parse import quote, unquote, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup

from safelink_mcp.models import RenderedPage, RiskSignal


MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 "
    "Mobile/15E148 Safari/604.1"
)

SUSPICIOUS_TERMS = {
    "login",
    "verify",
    "secure",
    "account",
    "update",
    "confirm",
    "reward",
    "gift",
    "free",
    "airdrop",
    "wallet",
    "otp",
    "password",
    "auth",
    "security",
    "bank",
    "signin",
    "payment",
    "claim",
    "bonus",
    "urgent",
}

SENSITIVE_INPUT_TERMS = {
    "password",
    "passwd",
    "pwd",
    "card",
    "credit",
    "otp",
    "pin",
    "ssn",
    "seed",
    "mnemonic",
    "private",
    "wallet",
    "token",
    "passcode",
}

BRAND_DOMAINS: dict[str, set[str]] = {
    "kakao": {"kakao.com", "kakaocorp.com", "kakaocloud.com"},
    "naver": {"naver.com", "navercloudcorp.com", "line.me"},
    "google": {"google.com", "google.co.kr", "youtube.com", "gmail.com"},
    "apple": {"apple.com", "icloud.com"},
    "microsoft": {"microsoft.com", "live.com", "office.com", "outlook.com"},
    "meta": {"meta.com", "facebook.com", "instagram.com", "threads.net"},
    "facebook": {"facebook.com", "fb.com", "meta.com"},
    "instagram": {"instagram.com", "threads.net", "meta.com"},
    "twitter": {"twitter.com", "x.com"},
    "paypal": {"paypal.com"},
    "toss": {"toss.im", "tossbank.com", "tosspayments.com"},
    "coupang": {"coupang.com"},
    "upbit": {"upbit.com", "upbit.co.kr"},
    "bithumb": {"bithumb.com", "bithumb.co.kr"},
    "binance": {"binance.com"},
    "shinhan": {"shinhan.com", "shinhanbank.co.kr"},
    "woori": {"wooribank.com", "wooribank.co.kr"},
    "hana": {"hanafn.com", "kebhana.com"},
    "kb": {"kbfg.com", "kbstar.com"},
}

SUSPICIOUS_TLDS = {
    "zip",
    "mov",
    "top",
    "xyz",
    "click",
    "work",
    "icu",
    "tk",
    "ml",
    "gq",
    "cf",
    "quest",
    "rest",
    "cam",
}


@dataclass(slots=True)
class FetchResult:
    final_url: str
    redirects: list[str]
    status_code: int | None
    headers: dict[str, str]
    html: str
    signals: list[RiskSignal]
    blocked_reason: str | None = None


class UnsafeTargetError(ValueError):
    """Raised when a URL points to a blocked network target."""


def normalize_url(raw_url: str) -> str:
    value = raw_url.strip()
    if not value:
        raise ValueError("URL이 비어 있습니다.")
    if "://" not in value:
        value = "https://" + value

    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("http 또는 https URL만 검사할 수 있습니다.")
    if not parsed.netloc:
        raise ValueError("호스트가 없는 URL입니다.")

    hostname = parsed.hostname or ""
    try:
        hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValueError("도메인 이름을 IDNA 형식으로 변환할 수 없습니다.") from exc

    netloc = hostname
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    if parsed.username or parsed.password:
        userinfo = parsed.username or ""
        if parsed.password:
            userinfo += ":***"
        netloc = f"{userinfo}@{netloc}"

    path = quote(unquote(parsed.path or "/"), safe="/:%@+~#?&=;,")
    return urlunparse((parsed.scheme, netloc, path, "", parsed.query, ""))


def hostname_from_url(url: str) -> str:
    return (urlparse(url).hostname or "").lower().strip(".")


def registrable_domain(hostname: str) -> str:
    parts = hostname.lower().strip(".").split(".")
    if len(parts) <= 2:
        return hostname.lower().strip(".")
    second_level_suffixes = {
        "co.kr",
        "or.kr",
        "go.kr",
        "ac.kr",
        "ne.kr",
        "co.jp",
        "co.uk",
        "com.au",
    }
    suffix = ".".join(parts[-2:])
    if suffix in second_level_suffixes and len(parts) >= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def is_ip_literal(hostname: str) -> bool:
    try:
        ipaddress.ip_address(hostname.strip("[]"))
        return True
    except ValueError:
        return False


def assert_public_hostname(hostname: str) -> None:
    if not hostname:
        raise UnsafeTargetError("호스트가 비어 있습니다.")
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".localhost"):
        raise UnsafeTargetError("localhost 주소는 SSRF 방지를 위해 접속하지 않습니다.")

    addresses = []
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeTargetError(f"DNS 조회 실패: {exc}") from exc

    for info in infos:
        raw_address = info[4][0]
        try:
            address = ipaddress.ip_address(raw_address)
        except ValueError:
            continue
        addresses.append(str(address))
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        ):
            raise UnsafeTargetError(
                f"내부망/예약 IP({address})로 해석되어 접속하지 않습니다."
            )

    if not addresses:
        raise UnsafeTargetError("공개 IP 주소로 해석되지 않았습니다.")


def analyze_url_lexical(url: str) -> list[RiskSignal]:
    parsed = urlparse(url)
    hostname = hostname_from_url(url)
    host_domain = registrable_domain(hostname)
    signals: list[RiskSignal] = []
    lowered_url = unquote(url).lower()

    if parsed.scheme == "http":
        signals.append(
            RiskSignal(
                "url",
                "HTTPS 미사용",
                16,
                "암호화되지 않은 HTTP 링크입니다.",
                "medium",
            )
        )
    if parsed.username or parsed.password or "@" in parsed.netloc:
        signals.append(
            RiskSignal(
                "url",
                "userinfo 포함 URL",
                65,
                "URL에 '@' 또는 사용자 정보가 포함되어 실제 목적지를 속일 수 있습니다.",
                "critical",
            )
        )
    if len(url) > 220:
        signals.append(
            RiskSignal("url", "매우 긴 URL", 20, f"URL 길이가 {len(url)}자입니다.", "medium")
        )
    elif len(url) > 140:
        signals.append(
            RiskSignal("url", "긴 URL", 10, f"URL 길이가 {len(url)}자입니다.", "low")
        )

    if is_ip_literal(hostname):
        signals.append(
            RiskSignal(
                "url",
                "IP 주소 직접 사용",
                24,
                "도메인 이름 대신 IP 주소로 접속합니다.",
                "medium",
            )
        )

    if "xn--" in hostname:
        signals.append(
            RiskSignal(
                "url",
                "Punycode 도메인",
                20,
                "국제화 도메인 인코딩이 포함되어 있어 문자 혼동 가능성이 있습니다.",
                "medium",
            )
        )

    labels = hostname.split(".")
    if len(labels) >= 5:
        signals.append(
            RiskSignal(
                "url",
                "과도한 서브도메인",
                12,
                f"호스트가 {len(labels)}개 라벨로 구성되어 있습니다.",
                "low",
            )
        )

    tld = labels[-1] if labels else ""
    if tld in SUSPICIOUS_TLDS:
        signals.append(
            RiskSignal(
                "url",
                "주의 TLD",
                8,
                f".{tld} 도메인은 피싱 캠페인에서 자주 악용될 수 있습니다.",
                "low",
            )
        )

    term_hits = sorted(term for term in SUSPICIOUS_TERMS if term in lowered_url)
    if term_hits:
        score = min(6 + len(term_hits) * 3, 22)
        signals.append(
            RiskSignal(
                "url",
                "민감 행동 유도 단어",
                score,
                "URL에 " + ", ".join(term_hits[:8]) + " 단어가 포함되어 있습니다.",
                "low" if score < 14 else "medium",
            )
        )

    for brand, official_domains in BRAND_DOMAINS.items():
        if brand in hostname and not any(
            host_domain == domain or hostname.endswith("." + domain)
            for domain in official_domains
        ):
            signals.append(
                RiskSignal(
                    "brand",
                    "브랜드명 도메인 착시",
                    36,
                    f"호스트에 '{brand}'가 있지만 공식 도메인({', '.join(sorted(official_domains))})이 아닙니다.",
                    "high",
                )
            )

    return signals


def analyze_html(html: str, final_url: str) -> tuple[list[RiskSignal], dict[str, Any]]:
    signals: list[RiskSignal] = []
    soup = BeautifulSoup(html[:2_000_000], "html.parser")
    title = unescape((soup.title.string or "").strip()) if soup.title and soup.title.string else ""
    text = soup.get_text(" ", strip=True)
    lowered_text = text.lower()
    hostname = hostname_from_url(final_url)
    host_domain = registrable_domain(hostname)

    password_inputs = soup.select("input[type=password]")
    sensitive_inputs: list[str] = []
    for input_el in soup.select("input"):
        attributes = " ".join(
            str(input_el.get(attr, "")) for attr in ("type", "name", "id", "placeholder", "autocomplete")
        ).lower()
        if any(term in attributes for term in SENSITIVE_INPUT_TERMS):
            sensitive_inputs.append(attributes[:120])

    if password_inputs:
        signals.append(
            RiskSignal(
                "html",
                "비밀번호 입력폼",
                38,
                f"HTML에서 비밀번호 입력칸 {len(password_inputs)}개를 발견했습니다.",
                "high",
            )
        )
    elif sensitive_inputs:
        signals.append(
            RiskSignal(
                "html",
                "민감정보 입력폼",
                26,
                f"민감정보로 보이는 입력칸 {len(sensitive_inputs)}개를 발견했습니다.",
                "medium",
            )
        )

    download_like = [
        anchor.get("href", "")
        for anchor in soup.select("a[href]")
        if re.search(r"\.(apk|exe|scr|msi|dmg|pkg|bat|cmd|js)(?:[?#].*)?$", anchor.get("href", ""), re.I)
    ]
    if download_like:
        signals.append(
            RiskSignal(
                "html",
                "실행 파일 다운로드 유도",
                55,
                f"실행 파일로 보이는 링크 {len(download_like)}개를 발견했습니다.",
                "critical",
            )
        )

    for brand, official_domains in BRAND_DOMAINS.items():
        if brand in lowered_text and not any(
            host_domain == domain or hostname.endswith("." + domain)
            for domain in official_domains
        ):
            signals.append(
                RiskSignal(
                    "brand",
                    "본문 브랜드 사칭 가능성",
                    28,
                    f"페이지는 '{brand}'를 언급하지만 최종 도메인은 {host_domain}입니다.",
                    "high",
                )
            )
            break

    urgency_terms = [
        "urgent",
        "suspended",
        "locked",
        "verify now",
        "계정",
        "정지",
        "긴급",
        "인증",
        "보상",
        "수령",
        "확인",
    ]
    urgency_hits = [term for term in urgency_terms if term in lowered_text]
    if urgency_hits:
        signals.append(
            RiskSignal(
                "html",
                "긴급 행동 유도 문구",
                min(10 + len(urgency_hits) * 3, 24),
                "페이지 텍스트에 " + ", ".join(urgency_hits[:6]) + " 표현이 있습니다.",
                "medium",
            )
        )

    return signals, {"title": title, "text": text[:4000]}


async def fetch_metadata(url: str) -> FetchResult:
    signals: list[RiskSignal] = []
    parsed_url = urlparse(url)
    if parsed_url.username or parsed_url.password or "@" in parsed_url.netloc:
        return FetchResult(
            final_url=url,
            redirects=[],
            status_code=None,
            headers={},
            html="",
            signals=[
                RiskSignal(
                    "network",
                    "userinfo URL 접속 차단",
                    95,
                    "사용자 정보가 포함된 URL은 목적지 착시와 인증정보 노출 위험이 있어 접속하지 않습니다.",
                    "critical",
                )
            ],
            blocked_reason="URL에 사용자 정보 또는 '@'가 포함되어 있습니다.",
        )

    current_hostname = hostname_from_url(url)
    try:
        assert_public_hostname(current_hostname)
    except UnsafeTargetError as exc:
        return FetchResult(
            final_url=url,
            redirects=[],
            status_code=None,
            headers={},
            html="",
            signals=[
                RiskSignal(
                    "network",
                    "접속 차단 대상",
                    95,
                    str(exc),
                    "critical",
                )
            ],
            blocked_reason=str(exc),
        )

    timeout = httpx.Timeout(float(os.getenv("SAFE_LINK_TIMEOUT", "2")))
    redirects: list[str] = []

    async def on_response(response: httpx.Response) -> None:
        if response.is_redirect:
            location = response.headers.get("location", "")
            if location:
                redirects.append(str(response.url.join(location)))

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        max_redirects=int(os.getenv("SAFE_LINK_MAX_REDIRECTS", "5")),
        headers={
            "User-Agent": MOBILE_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.6",
        },
        event_hooks={"response": [on_response]},
    ) as client:
        try:
            response = await client.get(url)
        except httpx.TooManyRedirects:
            return FetchResult(
                final_url=url,
                redirects=redirects,
                status_code=None,
                headers={},
                html="",
                signals=[
                    RiskSignal(
                        "network",
                        "과도한 리다이렉트",
                        38,
                        "허용된 리다이렉트 횟수를 초과했습니다.",
                        "high",
                    )
                ],
            )
        except httpx.RequestError as exc:
            return FetchResult(
                final_url=url,
                redirects=redirects,
                status_code=None,
                headers={},
                html="",
                signals=[
                    RiskSignal(
                        "network",
                        "접속 실패",
                        24,
                        f"요청 중 오류가 발생했습니다: {exc.__class__.__name__}",
                        "medium",
                    )
                ],
            )

    final_url = str(response.url)
    final_hostname = hostname_from_url(final_url)
    try:
        assert_public_hostname(final_hostname)
    except UnsafeTargetError as exc:
        signals.append(
            RiskSignal(
                "network",
                "리다이렉트 내부망 대상",
                95,
                str(exc),
                "critical",
            )
        )
        return FetchResult(
            final_url=final_url,
            redirects=redirects,
            status_code=response.status_code,
            headers=dict(response.headers),
            html="",
            signals=signals,
            blocked_reason=str(exc),
        )

    if redirects:
        score = min(8 + len(redirects) * 5, 28)
        signals.append(
            RiskSignal(
                "network",
                "리다이렉트 발생",
                score,
                f"{len(redirects)}회 리다이렉트 후 {final_hostname}에 도착했습니다.",
                "low" if score < 18 else "medium",
            )
        )
        if registrable_domain(current_hostname) != registrable_domain(final_hostname):
            signals.append(
                RiskSignal(
                    "network",
                    "다른 도메인으로 이동",
                    20,
                    f"{registrable_domain(current_hostname)}에서 {registrable_domain(final_hostname)}로 이동했습니다.",
                    "medium",
                )
            )

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        signals.append(
            RiskSignal(
                "http",
                "HTML이 아닌 응답",
                12,
                f"응답 Content-Type은 {content_type or 'unknown'}입니다.",
                "low",
            )
        )

    if response.status_code >= 500:
        signals.append(
            RiskSignal("http", "서버 오류 응답", 14, f"HTTP {response.status_code}", "low")
        )
    elif response.status_code >= 400:
        signals.append(
            RiskSignal("http", "클라이언트 오류 응답", 10, f"HTTP {response.status_code}", "low")
        )

    if final_url.startswith("http://"):
        signals.append(
            RiskSignal(
                "http",
                "최종 URL HTTPS 미사용",
                16,
                "리다이렉트 후 최종 URL도 HTTP입니다.",
                "medium",
            )
        )

    html = response.text if response.content else ""
    html_signals, _ = analyze_html(html, final_url) if html else ([], {})
    signals.extend(html_signals)

    return FetchResult(
        final_url=final_url,
        redirects=redirects,
        status_code=response.status_code,
        headers=dict(response.headers),
        html=html,
        signals=signals,
    )


def analyze_rendered_page(rendered: RenderedPage, final_url: str) -> list[RiskSignal]:
    signals: list[RiskSignal] = []
    if rendered.error:
        signals.append(
            RiskSignal(
                "render",
                "브라우저 렌더링 실패",
                18,
                rendered.error,
                "medium",
            )
        )

    if rendered.forms:
        sensitive_form_count = 0
        password_form_count = 0
        for form in rendered.forms:
            for item in form.get("inputs", []):
                joined = " ".join(str(item.get(key, "")) for key in item).lower()
                if item.get("type") == "password":
                    password_form_count += 1
                if any(term in joined for term in SENSITIVE_INPUT_TERMS):
                    sensitive_form_count += 1
        if password_form_count:
            signals.append(
                RiskSignal(
                    "render",
                    "렌더링 화면의 비밀번호 폼",
                    42,
                    f"모바일 렌더링 후 비밀번호 입력칸 {password_form_count}개가 보입니다.",
                    "high",
                )
            )
        elif sensitive_form_count:
            signals.append(
                RiskSignal(
                    "render",
                    "렌더링 화면의 민감정보 폼",
                    28,
                    f"모바일 렌더링 후 민감정보 입력칸 {sensitive_form_count}개가 보입니다.",
                    "medium",
                )
            )

    lowered_text = rendered.visible_text.lower()
    final_domain = registrable_domain(hostname_from_url(final_url))
    for brand, official_domains in BRAND_DOMAINS.items():
        if brand in lowered_text and not any(final_domain == domain for domain in official_domains):
            signals.append(
                RiskSignal(
                    "render",
                    "렌더링 화면 브랜드 불일치",
                    28,
                    f"화면 텍스트는 '{brand}'를 언급하지만 최종 도메인은 {final_domain}입니다.",
                    "high",
                )
            )
            break

    wallet_terms = {"connect wallet", "seed phrase", "private key", "wallet connect", "지갑", "시드"}
    wallet_hits = sorted(term for term in wallet_terms if term in lowered_text)
    if wallet_hits:
        signals.append(
            RiskSignal(
                "render",
                "지갑/시드 문구 유도",
                38,
                "화면에서 " + ", ".join(wallet_hits[:4]) + " 표현을 발견했습니다.",
                "high",
            )
        )

    return signals


def combine_signals(signals: list[RiskSignal]) -> tuple[bool, int, float, str]:
    if not signals:
        return True, 0, 0.72, "명확한 위험 신호를 찾지 못했습니다. 단, 알려지지 않은 신규 피싱은 항상 가능하므로 링크 클릭 전 도메인을 확인하세요."

    raw_score = sum(signal.score for signal in signals if signal.score > 0)
    critical_count = sum(1 for signal in signals if signal.severity == "critical")
    high_count = sum(1 for signal in signals if signal.severity == "high")
    source_count = len({signal.source for signal in signals if signal.score > 0})

    risk_score = min(100, raw_score)
    if critical_count:
        risk_score = max(risk_score, 85)
    elif high_count >= 2:
        risk_score = max(risk_score, 72)
    elif high_count == 1 and source_count >= 2:
        risk_score = max(risk_score, 64)

    is_safety = risk_score < 35 and high_count == 0 and critical_count == 0
    confidence = min(0.98, 0.58 + risk_score / 180 + min(source_count, 4) * 0.04)

    if is_safety:
        summary = "앙상블 검사에서 강한 위험 신호를 찾지 못해 완전 안전하다로 분류했습니다."
    else:
        top = sorted(signals, key=lambda item: item.score, reverse=True)[:3]
        evidence = ", ".join(signal.label for signal in top)
        summary = f"{evidence} 신호 때문에 위험할 수 있다로 분류했습니다."
    return is_safety, risk_score, round(confidence, 3), summary


async def maybe_await_sleep() -> None:
    await asyncio.sleep(0)
