from __future__ import annotations

import asyncio
import os
from typing import Any

from safelink_mcp.models import RenderedPage
from safelink_mcp.safety import MOBILE_USER_AGENT, assert_public_hostname, hostname_from_url


_browser_lock = asyncio.Lock()
_playwright: Any | None = None
_browser: Any | None = None


async def _get_browser() -> Any:
    global _browser, _playwright
    try:
        if _browser is not None and _browser.is_connected():
            return _browser
    except Exception:
        _browser = None

    async with _browser_lock:
        try:
            if _browser is not None and _browser.is_connected():
                return _browser
        except Exception:
            _browser = None

        from playwright.async_api import async_playwright

        if _playwright is None:
            _playwright = await async_playwright().start()

        _browser = await _playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-extensions",
                "--disable-background-networking",
                "--disable-sync",
                "--disable-default-apps",
            ],
        )
        return _browser


async def warm_browser() -> None:
    try:
        await _get_browser()
    except Exception:
        pass


async def render_mobile_page(url: str) -> RenderedPage:
    try:
        import playwright.async_api  # noqa: F401
    except Exception as exc:  # pragma: no cover - exercised only without optional runtime deps.
        return RenderedPage(error=f"Playwright를 불러올 수 없습니다: {exc}")

    try:
        assert_public_hostname(hostname_from_url(url))
    except Exception as exc:
        return RenderedPage(error=f"렌더링 차단: {exc}")

    timeout_ms = int(float(os.getenv("SAFE_LINK_RENDER_TIMEOUT", "2")) * 1000)
    context = None
    try:
        browser = await _get_browser()
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            device_scale_factor=2,
            user_agent=MOBILE_USER_AGENT,
            locale="ko-KR",
            accept_downloads=False,
        )
        page = await context.new_page()
        page.set_default_timeout(timeout_ms)

        await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        try:
            await page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 800))
        except Exception:
            pass

        screenshot = await page.screenshot(type="png", full_page=False)
        title = await page.title()
        visible_text = await page.evaluate(
            """() => (document.body && document.body.innerText || '').slice(0, 8000)"""
        )
        elements = await page.evaluate(
            """
            () => {
              const important = [];
              const selectors = [
                'img', 'svg', 'h1', 'h2', 'h3', 'button', 'a', 'input',
                'textarea', '[role=button]', '[aria-label]', 'form'
              ];
              for (const el of document.querySelectorAll(selectors.join(','))) {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                if (rect.width < 12 || rect.height < 12) continue;
                if (style.visibility === 'hidden' || style.display === 'none') continue;
                if (rect.bottom < 0 || rect.right < 0 || rect.top > window.innerHeight) continue;
                const text = (el.innerText || el.alt || el.getAttribute('aria-label') || el.placeholder || '').trim();
                const tag = el.tagName.toLowerCase();
                const area = rect.width * rect.height;
                const isInteractive = tag === 'button' || tag === 'input' || tag === 'textarea' || el.getAttribute('role') === 'button';
                const isHeading = /^h[1-3]$/.test(tag);
                const isMedia = tag === 'img' || tag === 'svg';
                if (area < 900) continue;
                if (!isHeading && !isInteractive && !isMedia && tag !== 'form' && area < 2400) continue;
                let score = Math.min(12, Math.log(area + 1));
                if (/^h[1-3]$/.test(tag)) score += 8;
                if (tag === 'button' || el.getAttribute('role') === 'button') score += 7;
                if (tag === 'input' || tag === 'textarea') score += 9;
                if (tag === 'form') score += 10;
                if (tag === 'img' || tag === 'svg') score += 3;
                if (/login|sign|verify|인증|로그인|확인|결제|지갑|wallet|password/i.test(text)) score += 8;
                important.push({
                  tag,
                  text: text.slice(0, 120),
                  x: Math.max(0, rect.x),
                  y: Math.max(0, rect.y),
                  width: rect.width,
                  height: rect.height,
                  score
                });
              }
              return important.sort((a, b) => b.score - a.score).slice(0, 24);
            }
            """
        )
        forms = await page.evaluate(
            """
            () => Array.from(document.querySelectorAll('form')).slice(0, 6).map((form) => ({
              text: (form.innerText || '').trim().slice(0, 500),
              inputs: Array.from(form.querySelectorAll('input, textarea')).slice(0, 20).map((input) => ({
                type: input.getAttribute('type') || input.tagName.toLowerCase(),
                name: input.getAttribute('name') || '',
                id: input.getAttribute('id') || '',
                placeholder: input.getAttribute('placeholder') || '',
                autocomplete: input.getAttribute('autocomplete') || ''
              }))
            }))
            """
        )
        buttons = await page.evaluate(
            """
            () => Array.from(document.querySelectorAll('button, [role=button], a'))
              .map((el) => (el.innerText || el.getAttribute('aria-label') || '').trim())
              .filter(Boolean)
              .slice(0, 30)
            """
        )
        return RenderedPage(
            screenshot_png=screenshot,
            title=title,
            visible_text=visible_text,
            elements=elements,
            forms=forms,
            buttons=buttons,
        )
    except Exception as exc:
        return RenderedPage(error=f"{exc.__class__.__name__}: {exc}")
    finally:
        if context is not None:
            try:
                await context.close()
            except Exception:
                pass
