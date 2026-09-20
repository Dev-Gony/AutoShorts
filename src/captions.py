from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont


class CaptionLayoutError(ValueError):
    pass


def find_korean_font() -> str:
    custom = os.getenv("AUTOSHORTS_FONT", "").strip()
    windows = Path(os.getenv("WINDIR", "C:/Windows")) / "Fonts"
    local = Path(os.getenv("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts"
    candidates = [Path(custom)] if custom else [
        windows / "Pretendard-ExtraBold.otf",
        windows / "Pretendard-Bold.otf",
        local / "Pretendard-Bold.otf",
        windows / "malgunbd.ttf",
        Path("/usr/share/fonts/truetype/nanum/NanumSquareB.ttf"),
        Path("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
        Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
    ]
    for path in candidates:
        if not path.is_file():
            continue
        try:
            with TTFont(str(path), fontNumber=0, lazy=True) as font:
                cmap = font.getBestCmap() or {}
                if all(ord(c) in cmap for c in "가나다라마바사한글"):
                    return str(path)
        except Exception:
            continue
    raise CaptionLayoutError(
        "한글 폰트를 찾지 못했습니다. AUTOSHORTS_FONT에 로컬 한글 Bold 폰트 경로를 지정하세요. "
        "예: C:/Windows/Fonts/malgunbd.ttf (폰트 파일은 저장소에 포함하지 않습니다.)"
    )


@lru_cache(maxsize=8)
def _supported_chars(path: str) -> frozenset[int]:
    with TTFont(path, fontNumber=0, lazy=True) as font:
        return frozenset((font.getBestCmap() or {}).keys())


@dataclass
class CaptionCard:
    image: Image.Image
    x: int
    y: int
    font_size: int
    lines: list[str]

    @property
    def box(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.x + self.image.width, self.y + self.image.height


def _wrap(text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    # Wrap by measured pixels, including long words, not an estimated character count.
    text = " ".join(text.split())
    if font.getlength(text) <= width:
        return [text]
    breaks = [i for i, c in enumerate(text) if c == " "]
    if not breaks:
        breaks = list(range(1, len(text)))
    balanced = []
    for cut in breaks:
        left, right = text[:cut].rstrip(), text[cut:].lstrip()
        if left and right:
            a, b = font.getlength(left), font.getlength(right)
            if max(a, b) <= width:
                balanced.append((abs(a - b), left, right))
    if balanced:
        _, left, right = min(balanced, key=lambda item: item[0])
        return [left, right]
    lines: list[str] = []
    while text:
        end = 0
        while end < len(text) and font.getlength(text[:end + 1]) <= width:
            end += 1
        if not end:
            raise CaptionLayoutError("자막 가로 영역이 글자 하나보다 작습니다.")
        if end < len(text):
            space = text.rfind(" ", 0, end + 1)
            if space > end // 2:
                end = space
        lines.append(text[:end].rstrip())
        text = text[end:].lstrip()
    return lines


def make_caption(
    text: str, emphasis: str = "", *, font_path: str | None = None,
    width: int = 1080, height: int = 1920, title: bool = False,
) -> CaptionCard:
    if not text.strip():
        raise CaptionLayoutError("빈 자막입니다.")
    font_path = font_path or find_korean_font()
    missing = {c for c in text if not c.isspace() and ord(c) not in _supported_chars(font_path)}
    if missing:
        raise CaptionLayoutError("Font cannot render: " + " ".join(sorted(missing)))
    scale = width / 1080
    # Leave space for Shorts controls on the right and bottom.
    max_width = int(width * (.80 if title else .82))
    pad = max(10, round((24 if title else 22) * scale))
    stroke = max(1, round((2 if title else 3) * scale))
    start_size = round((82 if title else 74) * scale)
    min_size = max(12, round((46 if title else 44) * scale))
    selected = None
    for size in range(start_size, min_size - 1, -1):
        font = ImageFont.truetype(font_path, size)
        lines = _wrap(text, font, max_width - 2 * pad - 2 * stroke)
        if len(lines) <= 2:
            selected = font, lines, size
            break
    if selected is None:
        raise CaptionLayoutError("자막이 2줄 안전영역을 넘습니다. 문장을 더 짧게 나눠주세요.")
    font, lines, size = selected
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    boxes = [probe.textbbox((0, 0), line, font=font, stroke_width=stroke) for line in lines]
    line_height = max(b[3] - b[1] for b in boxes)
    gap = max(5, round(12 * scale))
    card_width = max(b[2] - b[0] for b in boxes) + 2 * pad
    card_height = line_height * len(lines) + gap * (len(lines) - 1) + 2 * pad
    card = Image.new("RGBA", (card_width, card_height))
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle(
        (0, 0, card_width - 1, card_height - 1),
        radius=round((20 if title else 16) * scale),
        fill=(10, 13, 20, 178 if title else 164),
    )
    for n, (line, box) in enumerate(zip(lines, boxes)):
        left = (card_width - (box[2] - box[0])) / 2 - box[0]
        top = pad + n * (line_height + gap) - box[1]
        draw.text((left, top), line, font=font, fill="white", stroke_width=stroke, stroke_fill=(5, 7, 10, 230))
        if emphasis and emphasis in line:
            prefix = line[:line.index(emphasis)]
            draw.text((left + font.getlength(prefix), top), emphasis, font=font, fill=(255, 226, 102), stroke_width=stroke, stroke_fill=(5, 7, 10, 230))
    x = round(width * .47 - card_width / 2)
    y = round(height * .085) if title else round(height * .72 - card_height)
    if x < width * .05 or x + card_width > width * .90 or y < 0 or y + card_height > height * .80:
        raise CaptionLayoutError("자막 안전영역 검증에 실패했습니다.")
    return CaptionCard(card, x, y, size, lines)
