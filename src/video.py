from __future__ import annotations

import math
from pathlib import Path
from moviepy import AudioFileClip, CompositeVideoClip, TextClip, VideoFileClip, concatenate_videoclips
from src.models import SubtitleSegment

class VideoRenderer:
    WIDTH = 1080
    HEIGHT = 1920

    def render(
        self,
        background_path: Path,
        audio_path: Path,
        subtitles: list[SubtitleSegment],
        output_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with AudioFileClip(str(audio_path)) as audio:
            duration = audio.duration
            background = VideoFileClip(str(background_path))

            try:
                repeats = max(1, math.ceil(duration / background.duration))
                looped = concatenate_videoclips([background] * repeats).subclipped(0, duration)

                scaled = looped.resized(height=self.HEIGHT)
                if scaled.w < self.WIDTH:
                    scaled = looped.resized(width=self.WIDTH)

                vertical = scaled.cropped(
                    x_center=scaled.w / 2,
                    y_center=scaled.h / 2,
                    width=self.WIDTH,
                    height=self.HEIGHT,
                )

                layers = [vertical]
                for segment in subtitles:
                    clip = TextClip(
                        text=segment.text,
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

                final = CompositeVideoClip(layers, size=(self.WIDTH, self.HEIGHT)).with_audio(audio)
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
                    for layer in layers[1:]:
                        layer.close()
                    vertical.close()
                    scaled.close()
                    looped.close()
            finally:
                background.close()

        return output_path
