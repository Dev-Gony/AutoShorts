from __future__ import annotations

import bisect
import math
import uuid
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from moviepy import AudioFileClip, VideoClip, VideoFileClip

from src.captions import find_korean_font, make_caption
from src.models import SubtitleSegment


class VisualSourceError(RuntimeError):
    pass


def validate_timeline(segments: list[SubtitleSegment], duration: float) -> None:
    previous = 0.0
    for item in segments:
        if not all(math.isfinite(x) for x in (item.start, item.end)):
            raise ValueError("자막 시간에 유효하지 않은 수치가 있습니다.")
        if item.start < previous - .002 or item.end <= item.start or item.end > duration + .05:
            raise ValueError("자막 시간은 오디오 범위 안에서 순서대로 겹치지 않아야 합니다.")
        previous = item.end
    if not segments:
        raise ValueError("자막이 비어 있습니다.")


class SceneComposer:
    """Use the same pixel compositor for preview PNG and the encoded video."""

    def __init__(self, paths: list[Path], segments: list[SubtitleSegment], duration: float,
                 size=(1080, 1920), title: str = "", font_path: str | None = None):
        validate_timeline(segments, duration)
        self.paths, self.segments, self.duration = paths, segments, duration
        self.width, self.height = size
        self.starts = [s.start for s in segments]
        font_path = font_path or find_korean_font()
        self.cards = [make_caption(s.text, s.emphasis, font_path=font_path, width=self.width, height=self.height) for s in segments]
        self.title = make_caption(title, font_path=font_path, width=self.width, height=self.height, title=True) if title else None
        self.image_indices = []
        for i, segment in enumerate(segments):
            chosen = segment.image_index
            if type(chosen) is not int or not 0 <= chosen < len(paths):
                chosen = min(len(paths) - 1, i * len(paths) // len(segments)) if paths else 0
            self.image_indices.append(chosen)

    @lru_cache(maxsize=3)
    def _base(self, index: int) -> Image.Image:
        with Image.open(self.paths[index]) as original:
            image = ImageOps.exif_transpose(original).convert("RGB")
        size = (self.width, self.height)
        # Full-bleed blurred extension; keep the entire original photo in the foreground.
        backdrop = ImageOps.fit(image, size, method=Image.Resampling.LANCZOS)
        backdrop = backdrop.filter(ImageFilter.GaussianBlur(max(6, self.width * .025)))
        backdrop = ImageEnhance.Brightness(backdrop).enhance(.58)
        fitted = ImageOps.contain(image, (round(self.width * .95), round(self.height * .91)), method=Image.Resampling.LANCZOS)
        backdrop.paste(fitted, ((self.width - fitted.width) // 2, (self.height - fitted.height) // 2))
        return backdrop

    def _moving_image(self, scene: int, phase: float) -> Image.Image:
        base = self._base(self.image_indices[scene])
        phase = min(1.0, max(0.0, phase))
        # Alternate a restrained zoom-in / zoom-out. Foreground remains inside frame.
        scale = 1 + .035 * (phase if scene % 2 == 0 else 1 - phase)
        zoomed = base.resize((round(self.width * scale), round(self.height * scale)), Image.Resampling.BILINEAR)
        x = (zoomed.width - self.width) // 2
        y = (zoomed.height - self.height) // 2
        return zoomed.crop((x, y, x + self.width, y + self.height))

    def frame(self, time: float, background: np.ndarray | None = None) -> np.ndarray:
        t = min(max(0, time), max(0, self.duration - .0001))
        index = max(0, min(len(self.segments) - 1, bisect.bisect_right(self.starts, t) - 1))
        item = self.segments[index]
        if background is None:
            if not self.paths:
                raise VisualSourceError("사진 또는 배경 영상이 없습니다. 빈 화면은 렌더링하지 않습니다.")
            image = self._moving_image(index, (t - item.start) / max(.1, item.end - item.start))
            elapsed = t - item.start
            if index and 0 <= elapsed < .18 and self.image_indices[index] != self.image_indices[index - 1]:
                image = Image.blend(self._moving_image(index - 1, 1), image, elapsed / .18)
        else:
            image = ImageOps.fit(Image.fromarray(background.astype("uint8")).convert("RGB"), (self.width, self.height))
        image = image.convert("RGBA")
        if self.title and t < min(3.4, self.duration):
            image.alpha_composite(self.title.image, (self.title.x, self.title.y))
        if item.start <= t < item.end:
            card = self.cards[index]
            image.alpha_composite(card.image, (card.x, card.y))
        return np.asarray(image.convert("RGB"))

    def close(self) -> None:
        self._base.cache_clear()
        for card in self.cards:
            card.image.close()
        if self.title:
            self.title.image.close()


class VideoRenderer:
    WIDTH, HEIGHT = 1080, 1920
    FPS = 30

    @staticmethod
    def _find_korean_font() -> str:
        return find_korean_font()

    def render(self, background_path: Path | None, audio_path: Path,
               subtitles: list[SubtitleSegment], output_path: Path,
               image_paths: list[Path] | None = None, title: str = "") -> Path:
        paths = [Path(p) for p in image_paths or []]
        if not paths and background_path is None:
            raise VisualSourceError("사용 가능한 사진/영상이 없습니다. 회색 화면 대신 생성을 중단합니다.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        partial = output_path.with_name(f".{output_path.stem}.{uuid.uuid4().hex}.tmp.mp4")
        source = None
        composer = None
        visual = None
        final = None
        try:
            with AudioFileClip(str(audio_path)) as audio:
                duration = float(audio.duration)
                if not math.isfinite(duration) or not 0 < duration < 60:
                    raise ValueError("오디오 길이는 0초 초과, 60초 미만이어야 합니다.")
                composer = SceneComposer(paths, subtitles, duration, (self.WIDTH, self.HEIGHT), title)
                if background_path is not None:
                    source = VideoFileClip(str(background_path), audio=False)
                    if not source.duration or source.duration <= 0:
                        raise VisualSourceError("배경 영상 길이가 올바르지 않습니다.")
                def frame(t):
                    bg = source.get_frame(t % source.duration) if source is not None else None
                    return composer.frame(t, bg)
                visual = VideoClip(frame_function=frame, duration=duration)
                final = visual.with_audio(audio)
                final.write_videofile(
                    str(partial), fps=self.FPS, codec="libx264", audio_codec="aac",
                    audio_bitrate="192k", preset="veryfast", threads=4, logger=None,
                    ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"],
                )
                if not partial.is_file() or partial.stat().st_size < 1024:
                    raise RuntimeError("완성 영상이 비어 있습니다.")
                # Verify the real encoded file, not merely the graph or filename.
                with VideoFileClip(str(partial)) as encoded:
                    if tuple(encoded.size) != (self.WIDTH, self.HEIGHT) or encoded.audio is None:
                        raise RuntimeError("출력 해상도 또는 오디오 트랙 검증 실패")
                    if abs(encoded.duration - duration) > .25:
                        raise RuntimeError("렌더링 전후 길이가 일치하지 않습니다.")
                    for name, t in [("preview", min(1, duration / 2)), ("last-frame", max(0, duration - .15))]:
                        Image.fromarray(encoded.get_frame(t)).save(output_path.with_suffix(f".{name}.png"))
                partial.replace(output_path)
        finally:
            if final is not None:
                final.close()
            if visual is not None:
                visual.close()
            if source is not None:
                source.close()
            if composer is not None:
                composer.close()
            partial.unlink(missing_ok=True)
        return output_path
