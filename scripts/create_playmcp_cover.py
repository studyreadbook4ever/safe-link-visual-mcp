from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


OUT = Path("assets/playmcp-cover.png")
SIZE = 1024
SCALE = 4


def s(value: float) -> int:
    return int(round(value * SCALE))


def box(values: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    return tuple(s(value) for value in values)


def point(values: tuple[float, float]) -> tuple[int, int]:
    return tuple(s(value) for value in values)


def bezier(
    start: tuple[float, float],
    control: tuple[float, float],
    end: tuple[float, float],
    steps: int = 96,
) -> list[tuple[int, int]]:
    points = []
    for index in range(steps + 1):
        t = index / steps
        x = (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * control[0] + t**2 * end[0]
        y = (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * control[1] + t**2 * end[1]
        points.append(point((x, y)))
    return points


def lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)

    canvas = SIZE * SCALE
    image = Image.new("RGBA", (canvas, canvas), (248, 250, 252, 255))
    draw = ImageDraw.Draw(image)

    ink = (15, 23, 42)
    soft_ink = (30, 41, 59)
    sclera = (255, 255, 255)
    blue_dark = (30, 64, 175)
    blue_mid = (37, 99, 235)
    blue_light = (147, 197, 253)

    top = bezier((142, 512), (512, 284), (882, 512))
    bottom = bezier((142, 512), (512, 724), (882, 512))
    eye = top + list(reversed(bottom))

    draw.polygon(eye, fill=(*sclera, 255))
    draw.line(top, fill=(*ink, 255), width=s(18), joint="curve")
    draw.line(bottom, fill=(*ink, 235), width=s(14), joint="curve")
    draw.arc(box((182, 322, 842, 720)), 199, 341, fill=(*soft_ink, 92), width=s(5))

    center = (512, 512)
    iris_outer = 146
    iris_inner = 40

    for radius in range(iris_outer, iris_inner, -3):
        t = (iris_outer - radius) / (iris_outer - iris_inner)
        color = lerp(blue_mid, blue_light, t)
        draw.ellipse(
            box((center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius)),
            fill=(*color, 255),
        )

    for angle in range(0, 360, 10):
        radians = math.radians(angle)
        inner = s(48)
        outer = s(134)
        x1 = s(center[0]) + int(math.cos(radians) * inner)
        y1 = s(center[1]) + int(math.sin(radians) * inner)
        x2 = s(center[0]) + int(math.cos(radians) * outer)
        y2 = s(center[1]) + int(math.sin(radians) * outer)
        draw.line((x1, y1, x2, y2), fill=(*blue_dark, 70), width=s(3))

    draw.ellipse(box((366, 366, 658, 658)), outline=(*blue_dark, 210), width=s(7))
    draw.ellipse(box((438, 438, 586, 586)), fill=(8, 13, 28, 255))
    draw.ellipse(box((462, 462, 562, 562)), fill=(2, 6, 23, 255))

    highlight = Image.new("RGBA", image.size, (0, 0, 0, 0))
    highlight_draw = ImageDraw.Draw(highlight)
    highlight_draw.ellipse(box((404, 374, 478, 448)), fill=(255, 255, 255, 232))
    highlight_draw.ellipse(box((560, 568, 594, 602)), fill=(255, 255, 255, 178))
    image.alpha_composite(highlight.filter(ImageFilter.GaussianBlur(s(0.6))))

    final = image.resize((SIZE, SIZE), Image.Resampling.LANCZOS).convert("RGB")
    final.save(OUT, format="PNG", optimize=True)
    print(f"created {OUT}")


if __name__ == "__main__":
    main()
