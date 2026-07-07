from __future__ import annotations

from io import BytesIO
from textwrap import wrap
from urllib.parse import urlparse

from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont

from safelink_mcp.models import InspectionResult, RenderedPage


CANVAS_SIZE = 1024
BG = (248, 250, 252)
INK = (15, 23, 42)
MUTED = (71, 85, 105)
SAFE = (22, 163, 74)
DANGER = (220, 38, 38)
PANEL = (255, 255, 255)
BORDER = (203, 213, 225)


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf" if bold else "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _rounded_panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill=PANEL) -> None:
    draw.rounded_rectangle(box, radius=18, fill=fill, outline=BORDER, width=2)


def _fit_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, width: int) -> list[str]:
    if not text:
        return []
    approx = max(8, width // max(1, int(getattr(font, "size", 16) * 0.55)))
    lines: list[str] = []
    for raw in text.splitlines():
        for line in wrap(raw, approx):
            while draw.textlength(line, font=font) > width and len(line) > 4:
                line = line[:-2]
            lines.append(line)
    return lines


def _draw_text_block(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    max_width: int,
    max_lines: int,
    line_gap: int = 6,
) -> int:
    x, y = xy
    lines = _fit_text(draw, text, font, max_width)[:max_lines]
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += int(getattr(font, "size", 16)) + line_gap
    return y


def _crop_important_area(screenshot: PILImage.Image, rendered: RenderedPage) -> PILImage.Image:
    width, height = screenshot.size
    elements = sorted(rendered.elements, key=lambda item: item.get("score", 0), reverse=True)[:8]
    if not elements:
        top = 0
        bottom = min(height, int(height * 0.68))
        return screenshot.crop((0, top, width, bottom))

    scale_x = width / 390
    scale_y = height / 844
    xs: list[int] = []
    ys: list[int] = []
    xe: list[int] = []
    ye: list[int] = []
    for element in elements:
        x = int(float(element.get("x", 0)) * scale_x)
        y = int(float(element.get("y", 0)) * scale_y)
        w = int(float(element.get("width", 0)) * scale_x)
        h = int(float(element.get("height", 0)) * scale_y)
        if w * h < 3200:
            continue
        if y > height * 0.82:
            continue
        xs.append(max(0, x - 24))
        ys.append(max(0, y - 24))
        xe.append(min(width, x + w + 24))
        ye.append(min(height, y + h + 24))

    if not xs:
        return screenshot.crop((0, 0, width, min(height, int(height * 0.68))))

    left, top, right, bottom = min(xs), min(ys), max(xe), max(ye)
    min_height = int(height * 0.42)
    if bottom - top < min_height:
        center = (top + bottom) // 2
        top = max(0, center - min_height // 2)
        bottom = min(height, top + min_height)
    return screenshot.crop((left, top, right, bottom))


def _sample_palette(image: PILImage.Image, count: int = 5) -> list[tuple[int, int, int]]:
    small = image.convert("RGB").resize((64, 64))
    colors = small.getcolors(maxcolors=4096) or []
    colors.sort(reverse=True)
    palette: list[tuple[int, int, int]] = []
    for _, color in colors:
        r, g, b = color
        if max(color) > 245 and min(color) > 235:
            continue
        if min(color) < 12 and max(color) < 30:
            continue
        if all(abs(r - pr) + abs(g - pg) + abs(b - pb) > 55 for pr, pg, pb in palette):
            palette.append(color)
        if len(palette) >= count:
            break
    return palette or [(148, 163, 184), (51, 65, 85), (226, 232, 240)]


def build_digest_image(result: InspectionResult, rendered: RenderedPage | None) -> bytes:
    canvas = PILImage.new("RGB", (CANVAS_SIZE, CANVAS_SIZE), BG)
    draw = ImageDraw.Draw(canvas)

    title_font = _font(42, True)
    body_font = _font(25)
    small_font = _font(21)
    tiny_font = _font(17)
    badge_font = _font(24, True)

    verdict_color = SAFE if result.is_safety else DANGER
    draw.rectangle((0, 0, CANVAS_SIZE, 112), fill=verdict_color)
    verdict_text = "완전 안전하다" if result.is_safety else "위험할 수 있다"
    draw.text((36, 28), verdict_text, font=title_font, fill=(255, 255, 255))
    score_text = f"risk {result.risk_score}/100"
    score_width = draw.textlength(score_text, font=badge_font)
    draw.rounded_rectangle((CANVAS_SIZE - score_width - 76, 26, CANVAS_SIZE - 34, 78), radius=16, fill=(255, 255, 255))
    draw.text((CANVAS_SIZE - score_width - 55, 39), score_text, font=badge_font, fill=verdict_color)

    domain = urlparse(result.final_url or result.normalized_url).hostname or result.final_url
    _rounded_panel(draw, (28, 136, 996, 260))
    draw.text((54, 158), "링크가 실제로 도착한 곳", font=tiny_font, fill=MUTED)
    draw.text((54, 185), domain[:58], font=body_font, fill=INK)
    if result.redirects:
        redirect_text = f"redirect {len(result.redirects)}회"
        draw.text((54, 220), redirect_text, font=small_font, fill=MUTED)
    if result.http_status:
        draw.text((820, 220), f"HTTP {result.http_status}", font=small_font, fill=MUTED)

    screenshot = None
    if rendered and rendered.screenshot_png:
        screenshot = PILImage.open(BytesIO(rendered.screenshot_png)).convert("RGB")

    _rounded_panel(draw, (28, 284, 654, 790))
    draw.text((54, 306), "핵심 화면 조각", font=tiny_font, fill=MUTED)
    if screenshot:
        crop = _crop_important_area(screenshot, rendered or RenderedPage())
        crop.thumbnail((570, 416), PILImage.Resampling.LANCZOS)
        x = 28 + (626 - crop.width) // 2
        y = 350 + (390 - crop.height) // 2
        canvas.paste(crop, (x, y))
        palette = _sample_palette(screenshot)
    else:
        draw.text((64, 410), "렌더링 화면 없음", font=title_font, fill=MUTED)
        draw.text((68, 470), result.render_error or "네트워크/브라우저 제한으로 이미지 생성 실패", font=small_font, fill=MUTED)
        palette = [(148, 163, 184), (51, 65, 85), (226, 232, 240)]

    _rounded_panel(draw, (682, 284, 996, 790))
    draw.text((708, 314), "왜 이렇게 봤나", font=badge_font, fill=INK)
    y = 358
    for signal in sorted(result.signals, key=lambda item: item.score, reverse=True)[:5]:
        color = DANGER if signal.score >= 28 else (217, 119, 6) if signal.score >= 14 else MUTED
        draw.ellipse((710, y + 8, 724, y + 22), fill=color)
        y = _draw_text_block(draw, (736, y), signal.label, small_font, INK, 224, 1, 4)
        y = _draw_text_block(draw, (736, y + 1), signal.plain_evidence(), tiny_font, MUTED, 224, 2, 4) + 14
        if y > 742:
            break
    if not result.signals:
        _draw_text_block(draw, (708, 360), "강한 위험 신호 없음", small_font, MUTED, 238, 3)

    _rounded_panel(draw, (28, 814, 996, 976))
    draw.text((54, 838), "사이트 색상 DNA", font=tiny_font, fill=MUTED)
    x = 54
    for color in palette[:5]:
        draw.rounded_rectangle((x, 872, x + 88, 928), radius=12, fill=color)
        x += 104
    summary_x = 594
    draw.text((summary_x, 838), "다음 행동", font=tiny_font, fill=MUTED)
    _draw_text_block(draw, (summary_x, 870), result.action_advice(), small_font, INK, 364, 3, 5)

    out = BytesIO()
    canvas.save(out, format="PNG", optimize=True)
    return out.getvalue()
