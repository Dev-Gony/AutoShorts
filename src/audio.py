from __future__ import annotations

from pathlib import Path
from openai import OpenAI
from config import settings
from src.models import SubtitleSegment

class AudioService:
    def __init__(self, client: OpenAI | None = None) -> None:
        self.client = client or OpenAI(api_key=settings.openai_api_key)

    def synthesize(self, text: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.client.audio.speech.with_streaming_response.create(
            model=settings.tts_model,
            voice=settings.tts_voice,
            input=text,
        ) as response:
            response.stream_to_file(output_path)
        return output_path

    def transcribe_segments(self, audio_path: Path) -> list[SubtitleSegment]:
        with audio_path.open("rb") as audio:
            result = self.client.audio.transcriptions.create(
                model=settings.transcription_model,
                file=audio,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )

        segments: list[SubtitleSegment] = []
        for segment in getattr(result, "segments", []) or []:
            if hasattr(segment, "start"):
                start, end, text = segment.start, segment.end, segment.text
            else:
                start, end, text = segment["start"], segment["end"], segment["text"]
            text = str(text).strip()
            if text:
                segments.append(SubtitleSegment(float(start), float(end), text))

        if not segments:
            raise RuntimeError("타임스탬프 자막을 생성하지 못했습니다.")
        return segments
