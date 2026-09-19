from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BlogContent:
    url: str
    source: str
    title: str
    text: str
    images: list[str] = field(default_factory=list)


@dataclass
class ScriptScene:
    text: str
    emphasis: str = ""
    image_index: int | None = None


@dataclass
class ShortScript:
    title: str
    hook: str
    script: str
    hashtags: list[str] = field(default_factory=list)
    scenes: list[ScriptScene] = field(default_factory=list)


@dataclass
class SubtitleSegment:
    start: float
    end: float
    text: str
    emphasis: str = ""
    image_index: int | None = None


@dataclass
class PipelineResult:
    source: BlogContent
    short_script: ShortScript
    audio_path: Path
    video_path: Path
    subtitles: list[SubtitleSegment]
    elapsed_seconds: float
    work_dir: Path | None = None
