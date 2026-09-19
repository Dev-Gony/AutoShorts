from __future__ import annotations

import re
import wave
from pathlib import Path

from google import genai
from google.genai import types
from openai import OpenAI

from config import settings
from src.models import SubtitleSegment


class AudioService:
    def __init__(self) -> None:
        self.provider = settings.ai_provider

        if self.provider == "gemini":
            self.gemini = genai.Client(api_key=settings.gemini_api_key)
            self.openai = None
        elif self.provider == "openai":
            self.openai = OpenAI(api_key=settings.openai_api_key)
            self.gemini = None
        else:
            raise ValueError(f"지원하지 않는 AI_PROVIDER: {self.provider}")

    def synthesize(self, text: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if self.provider == "gemini":
            response = self.gemini.models.generate_content(
                model=settings.gemini_tts_model,
                contents=f"한국어로 자연스럽고 또렷하게 읽어주세요.\n\n{text}",
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    ),
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=settings.gemini_tts_voice
                            )
                        )
                    ),
                ),
            )

            audio_bytes = None
            for candidate in response.candidates or []:
                if not candidate.content:
                    continue
                for part in candidate.content.parts or []:
                    inline_data = getattr(part, "inline_data", None)
                    if inline_data and inline_data.data:
                        audio_bytes = inline_data.data
                        break
                if audio_bytes:
                    break

            if not audio_bytes:
                raise RuntimeError("Gemini TTS 응답에서 오디오 데이터를 찾지 못했습니다.")

            with wave.open(str(output_path), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(24000)
                wav.writeframes(audio_bytes)

            return output_path

        with self.openai.audio.speech.with_streaming_response.create(
            model=settings.openai_tts_model,
            voice=settings.openai_tts_voice,
            input=text,
        ) as response:
            response.stream_to_file(output_path)
        return output_path

    def transcribe_segments(
        self,
        audio_path: Path,
        original_text: str | None = None,
        duration: float | None = None,
    ) -> list[SubtitleSegment]:
        if self.provider == "gemini":
            if not original_text or not duration:
                raise RuntimeError(
                    "Gemini 자막 생성에는 원본 대본과 오디오 길이가 필요합니다."
                )
            return self._segments_from_script(original_text, duration)

        with audio_path.open("rb") as audio:
            result = self.openai.audio.transcriptions.create(
                model=settings.openai_transcription_model,
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

    @staticmethod
    def _segments_from_script(text: str, duration: float) -> list[SubtitleSegment]:
        sentences = [
            item.strip()
            for item in re.split(r"(?<=[.!?。！？])\s+|\n+", text)
            if item.strip()
        ]

        chunks: list[str] = []
        for sentence in sentences:
            if len(sentence) <= 28:
                chunks.append(sentence)
                continue

            words = sentence.split()
            current: list[str] = []
            current_len = 0
            for word in words:
                extra = len(word) + (1 if current else 0)
                if current and current_len + extra > 28:
                    chunks.append(" ".join(current))
                    current = [word]
                    current_len = len(word)
                else:
                    current.append(word)
                    current_len += extra
            if current:
                chunks.append(" ".join(current))

        if not chunks:
            chunks = [text.strip()]

        total_chars = sum(max(1, len(chunk)) for chunk in chunks)
        cursor = 0.0
        segments: list[SubtitleSegment] = []

        for index, chunk in enumerate(chunks):
            ratio = max(1, len(chunk)) / total_chars
            segment_duration = duration * ratio
            end = duration if index == len(chunks) - 1 else cursor + segment_duration
            segments.append(
                SubtitleSegment(
                    start=cursor,
                    end=end,
                    text=chunk,
                )
            )
            cursor = end

        return segments
