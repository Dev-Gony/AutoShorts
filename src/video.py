from __future__ import annotations

import math
import os
from pathlib import Path

from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
)

from src.models import SubtitleSegment


class VideoRenderer:
    WIDTH = 1080
    HEIGHT = 1920

    @staticmethod
    def _find_korean_font() -> str | None:
        custom = os.getenv("AUTOSHORTS_FONT", "").strip()
        candidates = [
            custom,
            r"C:\Windows\Fonts\malgun.ttf",
            r"C:\Windows\Fonts\malgunbd.ttf",
            "/System/Library/Fonts/AppleSDGothicNeo.ttc",
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        ]
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return candidate
        return None

    def _build_image_slideshow(
        self,
        image_paths: list[Path],
        duration: float,
    ):
        per_image = duration / len(image_paths)
        scenes = []

        for index, image_path in enumerate(image_paths):
            image = ImageClip(str(image_path))
            scale = min(self.WIDTH / image.w, self.HEIGHT / image.h)
            fitted = image.resized(scale)

            background = ColorClip(
                size=(self.WIDTH, self.HEIGHT),
                color=(18, 18, 22),
                duration=per_image,
            )
            scene = CompositeVideoClip(
                [
                    background,
                    fitted.with_duration(per_image).with_position("center"),
                ],
                size=(self.WIDTH, self.HEIGHT),
            ).with_duration(per_image)

            if index == len(image_paths) - 1:
                scene = scene.with_duration(
                    max(0.05, duration - per_image * (len(image_paths) - 1))
                )
            scenes.append(scene)

        return concatenate_videoclips(scenes, method="compose")

    def render(
        self,
        background_path: Path | None,
        audio_path: Path,
        subtitles: list[SubtitleSegment],
        output_path: Path,
        image_paths: list[Path] | None = None,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with AudioFileClip(str(audio_path)) as audio:
            duration = audio.duration
            source = None

            if background_path is not None:
                source = VideoFileClip(str(background_path))
                repeats = max(1, math.ceil(duration / source.duration))
                looped = concatenate_videoclips([source] * repeats).subclipped(0, duration)

                scaled = looped.resized(height=self.HEIGHT)
                if scaled.w < self.WIDTH:
                    scaled = looped.resized(width=self.WIDTH)

                vertical = scaled.cropped(
                    x_center=scaled.w / 2,
                    y_center=scaled.h / 2,
                    width=self.WIDTH,
                    height=self.HEIGHT,
                )
            elif image_paths:
                vertical = self._build_image_slideshow(image_paths, duration)
            else:
                vertical = ColorClip(
                    size=(self.WIDTH, self.HEIGHT),
                    color=(24, 24, 28),
                    duration=duration,
                )

            font = self._find_korean_font()
            layers = [vertical]
            try:
                for segment in subtitles:
                    clip = TextClip(
                        text=segment.text,
                        font=font,
                        font_size=64,
                        color="white",
                        stroke_color="black",
                        stroke_width=4,
                        method="caption",
                        size=(900, None),
                        text_align="center",
                    )
                    clip = (
                        clip.with_start(segment.start)
                        .with_duration(max(0.05, segment.end - segment.start))
                        .with_position(("center", 1320))
                    )
                    layers.append(clip)

                final = CompositeVideoClip(
                    layers,
                    size=(self.WIDTH, self.HEIGHT),
                ).with_audio(audio)

                try:
                    final.write_videofile(
                        str(output_path),
                        fps=30,
                        codec="libx264",
                        audio_codec="aac",
                        threads=4,
                        logger=None,
                    )
                finally:
                    final.close()
            finally:
                for layer in layers[1:]:
                    layer.close()
                vertical.close()
                if source is not None:
                    source.close()

        return output_path
