from __future__ import annotations

from pathlib import Path
from src.models import SubtitleSegment

def _timestamp(seconds: float) -> str:
    millis = round(seconds * 1000)
    hours, rem = divmod(millis, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"

def write_srt(segments: list[SubtitleSegment], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    chunks: list[str] = []

    for idx, segment in enumerate(segments, 1):
        chunks.append(
            f"{idx}\n"
            f"{_timestamp(segment.start)} --> {_timestamp(segment.end)}\n"
            f"{segment.text}\n"
        )

    output_path.write_text("\n".join(chunks), encoding="utf-8")
    return output_path
