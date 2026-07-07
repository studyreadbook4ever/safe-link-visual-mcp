from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT = Path("assets/playmcp-cover.png")
SIZE = 1024
SCALE = 3


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf" if bold else "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def scaled(value: float) -> int:
    return int(round(value * SCALE))


def box(values: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    return tuple(scaled(value) for value in values)


def point(values: tuple[float, float]) -> tuple[int, int]:
    return tuple(scaled(value) for value in values)


def bezier(
    start: tuple[float, float],
    control: tuple[float, float],
    end: tuple[float, float],
    steps: int = 88,
) -> list[tuple[int, int]]:
    points = []
    for index in range(steps + 1):
        t = index / steps
        x = (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * control[0] + t**2 * end[0]
        y = (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * control[1] + t**2 * end[1]
        points.append(point((x, y)))
    return points


def interpolate(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def centered_text_x(draw: ImageDraw.ImageDraw, text: str, text_font: ImageFont.ImageFont) -> float:
    text_box = draw.textbbox((0, 0), text, font=text_font)
    width = (text_box[2] - text_box[0]) / SCALE
    return (SIZE - width) / 2


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas = SIZE * SCALE
    image = Image.new("RGBA", (canvas, canvas), (248, 250, 252, 255))
    draw = ImageDraw.Draw(image)

    ink = (15, 23, 42)
    muted = (71, 85, 105)
    blue = (37, 99, 235)
    deep_blue = (30, 64, 175)
    light_blue = (191, 219, 254)
    green = (22, 163, 74)
    red = (220, 38, 38)

    title = font(60 * SCALE, True)
    subtitle = font(28 * SCALE)
    chip = font(24 * SCALE, True)

    for y in range(canvas):
        t = y / (canvas - 1)
        color = interpolate((248, 250, 252), (226, 232, 240), t)
        draw.line((0, y, canvas, y), fill=(*color, 255))

    for offset, alpha in ((18, 52), (0, 255)):
        draw.rounded_rectangle(
            box((96 + offset, 88 + offset, 928 + offset, 936 + offset)),
            radius=scaled(72),
            fill=(255, 255, 255, alpha),
            outline=(226, 232, 240, alpha),
            width=scaled(2),
        )

    draw.rounded_rectangle(box((156, 150, 868, 242)), radius=scaled(34), fill=(15, 23, 42, 255))
    draw.rounded_rectangle(box((192, 178, 520, 214)), radius=scaled(18), fill=(51, 65, 85, 255))
    draw.rounded_rectangle(box((548, 178, 644, 214)), radius=scaled(18), fill=(*green, 255))
    draw.rounded_rectangle(box((666, 178, 760, 214)), radius=scaled(18), fill=(*red, 255))
    draw.ellipse(box((792, 177, 830, 215)), fill=(*blue, 255))

    top = bezier((174, 458), (512, 218), (850, 458))
    bottom = bezier((174, 458), (512, 660), (850, 458))
    eye_shape = top + list(reversed(bottom))

    shadow = [(x, y + scaled(24)) for x, y in eye_shape]
    draw.polygon(shadow, fill=(15, 23, 42, 38))
    draw.polygon(eye_shape, fill=(255, 255, 255, 255))
    draw.line(top, fill=(15, 23, 42, 255), width=scaled(13), joint="curve")
    draw.line(bottom, fill=(15, 23, 42, 255), width=scaled(13), joint="curve")

    center = (512, 458)
    for radius in range(152, 18, -6):
        t = (152 - radius) / 134
        color = interpolate(deep_blue, light_blue, t)
        draw.ellipse(
            box((center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius)),
            fill=(*color, 255),
        )

    for angle in range(0, 360, 10):
        radians = math.radians(angle)
        inner = scaled(42)
        outer = scaled(140)
        x1 = scaled(center[0]) + int(math.cos(radians) * inner)
        y1 = scaled(center[1]) + int(math.sin(radians) * inner)
        x2 = scaled(center[0]) + int(math.cos(radians) * outer)
        y2 = scaled(center[1]) + int(math.sin(radians) * outer)
        draw.line((x1, y1, x2, y2), fill=(30, 64, 175, 58), width=scaled(3))

    draw.ellipse(box((358, 304, 666, 612)), outline=(30, 64, 175, 255), width=scaled(10))
    draw.ellipse(box((446, 392, 578, 524)), fill=(15, 23, 42, 255))
    draw.ellipse(box((470, 416, 554, 500)), fill=(2, 6, 23, 255))
    draw.ellipse(box((414, 352, 486, 424)), fill=(255, 255, 255, 225))
    draw.ellipse(box((552, 520, 584, 552)), fill=(255, 255, 255, 190))

    draw.rounded_rectangle(
        box((202, 682, 398, 744)),
        radius=scaled(31),
        fill=(240, 253, 244, 255),
        outline=(187, 247, 208, 255),
        width=scaled(2),
    )
    draw.ellipse(box((226, 700, 266, 740)), fill=(*green, 255))
    draw.line((scaled(236), scaled(721), scaled(248), scaled(733), scaled(272), scaled(704)), fill=(255, 255, 255, 255), width=scaled(6))
    draw.text(point((284, 697)), "SAFE", font=chip, fill=green)

    draw.rounded_rectangle(
        box((626, 682, 822, 744)),
        radius=scaled(31),
        fill=(254, 242, 242, 255),
        outline=(254, 202, 202, 255),
        width=scaled(2),
    )
    draw.ellipse(box((650, 700, 690, 740)), fill=(*red, 255))
    draw.line((scaled(670), scaled(708), scaled(670), scaled(724)), fill=(255, 255, 255, 255), width=scaled(5))
    draw.ellipse(box((665, 730, 675, 740)), fill=(255, 255, 255, 255))
    draw.text(point((708, 697)), "RISK", font=chip, fill=red)

    title_text = "Safe Link Visual"
    draw.text(point((centered_text_x(draw, title_text, title), 790)), title_text, font=title, fill=ink)

    subtitle_text = "링크를 열기 전 보는 파란 눈"
    draw.text(point((centered_text_x(draw, subtitle_text, subtitle), 868)), subtitle_text, font=subtitle, fill=muted)

    image = image.resize((SIZE, SIZE), Image.Resampling.LANCZOS).convert("RGB")
    image.save(OUT, format="PNG", optimize=True)
    print(f"created {OUT}")


if __name__ == "__main__":
    main()
