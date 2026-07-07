from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT = Path("assets/playmcp-cover.png")
SIZE = 1024


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


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (SIZE, SIZE), (248, 250, 252))
    draw = ImageDraw.Draw(image)

    ink = (15, 23, 42)
    muted = (71, 85, 105)
    red = (220, 38, 38)
    green = (22, 163, 74)
    blue = (37, 99, 235)
    line = (203, 213, 225)
    panel = (255, 255, 255)

    title = font(66, True)
    subtitle = font(36, True)
    body = font(30)
    small = font(24)

    draw.rounded_rectangle((72, 72, 952, 952), radius=64, fill=panel, outline=line, width=4)
    draw.rounded_rectangle((120, 124, 904, 294), radius=36, fill=ink)
    draw.text((164, 154), "Safe Link Visual", font=title, fill=(255, 255, 255))
    draw.text((168, 238), "세이프 링크 비주얼 MCP", font=small, fill=(226, 232, 240))

    draw.rounded_rectangle((142, 340, 486, 604), radius=34, fill=(240, 253, 244), outline=(187, 247, 208), width=3)
    draw.ellipse((190, 386, 272, 468), fill=green)
    draw.line((214, 430, 238, 454, 286, 402), fill=(255, 255, 255), width=14, joint="curve")
    draw.text((188, 508), "완전 안전하다", font=subtitle, fill=green)
    draw.text((188, 558), "true", font=body, fill=muted)

    draw.rounded_rectangle((538, 340, 882, 604), radius=34, fill=(254, 242, 242), outline=(254, 202, 202), width=3)
    draw.ellipse((586, 386, 668, 468), fill=red)
    draw.line((618, 402, 636, 452), fill=(255, 255, 255), width=12)
    draw.ellipse((612, 466, 642, 496), fill=(255, 255, 255))
    draw.text((584, 508), "위험할 수 있다", font=subtitle, fill=red)
    draw.text((584, 558), "false", font=body, fill=muted)

    draw.rounded_rectangle((142, 674, 882, 844), radius=34, fill=(239, 246, 255), outline=(191, 219, 254), width=3)
    draw.rectangle((188, 720, 352, 798), fill=blue)
    draw.rectangle((382, 720, 520, 754), fill=(148, 163, 184))
    draw.rectangle((382, 774, 680, 798), fill=(100, 116, 139))
    draw.text((714, 718), "1024 PNG", font=body, fill=blue)
    draw.text((714, 760), "visual digest", font=small, fill=muted)

    draw.text((142, 882), "링크를 열기 전, 안전 판정과 핵심 화면을 한 장으로", font=small, fill=muted)
    image.save(OUT, format="PNG", optimize=True)
    print(f"created {OUT}")


if __name__ == "__main__":
    main()
