from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
import uuid
import wave
from dataclasses import asdict
from pathlib import Path

import imageio_ffmpeg
import numpy as np

from config import settings
from src.models import ScriptScene, SubtitleSegment
from src.voices import selected_profile, speech_direction

RATE = 24000
CACHE_VERSION = "directed-utterance-v2"


def read_pcm(path: Path) -> bytes:
    with wave.open(str(path), "rb") as stream:
        if (stream.getnchannels(), stream.getsampwidth(), stream.getframerate()) != (1, 2, RATE):
            raise ValueError("음성은 24kHz mono PCM16 WAV여야 합니다.")
        expected = stream.getnframes() * 2
        data = stream.readframes(stream.getnframes())
    if not data or len(data) % 2 or len(data) != expected:
        raise ValueError("음성 데이터가 비어 있거나 손상되었습니다.")
    return data


def write_pcm(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as stream:
        stream.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        stream.writeframes(data)


def split_speech(text: str, limit: int = 30) -> list[ScriptScene]:
    """Legacy scripts: break at sentence/word boundaries, never drop characters."""
    result: list[ScriptScene] = []
    for sentence in re.split(r"(?<=[.!?。！？])\s+|\n+", text.strip()):
        sentence = sentence.strip()
        while len(sentence) > limit:
            cut = sentence.rfind(" ", 0, limit + 1)
            if cut < limit // 2:
                cut = limit
            result.append(ScriptScene(sentence[:cut].strip()))
            sentence = sentence[cut:].strip()
        if sentence:
            result.append(ScriptScene(sentence))
    if not result:
        raise ValueError("읽을 대본이 없습니다.")
    return result


class AudioService:
    """Directed voices with measured utterance timing, not character-ratio timing."""

    def __init__(self, preset: str | None = None, speed: float | None = None) -> None:
        self.provider = settings.ai_provider
        self.preset, self.profile = selected_profile(preset)
        self.speed = float(speed if speed is not None else os.getenv("VOICE_SPEED", "1.06"))
        if not .9 <= self.speed <= 1.2:
            raise ValueError("VOICE_SPEED는 0.9~1.2 범위여야 합니다.")
        self.gemini = None
        self.openai = None

    def _synthesize_raw(self, scene: ScriptScene, path: Path) -> None:
        direction = speech_direction(self.profile, scene.emphasis)
        if self.provider == "gemini":
            from google import genai
            from google.genai import types

            if self.gemini is None:
                self.gemini = genai.Client(
                    api_key=settings.gemini_api_key,
                    http_options=types.HttpOptions(timeout=60000),
                )
            response = self.gemini.models.generate_content(
                model=settings.gemini_tts_model,
                contents=direction + "\n# TRANSCRIPT\n" + scene.text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=self.profile.voice)
                        )
                    ),
                ),
            )
            candidates = response.candidates or []
            parts = candidates[0].content.parts if candidates and candidates[0].content else []
            chunks: list[bytes] = []
            sample_rate = RATE
            for part in parts or []:
                inline = getattr(part, "inline_data", None)
                if inline and inline.data:
                    mime = (inline.mime_type or "").lower()
                    if not mime.startswith("audio/"):
                        continue
                    rate_match = re.search(r"rate=(\d+)", mime)
                    if rate_match:
                        sample_rate = int(rate_match.group(1))
                    chunks.append(inline.data)
            if not chunks:
                raise RuntimeError("Gemini가 음성을 반환하지 않았습니다. 대본/안전필터/모델 상태를 확인하세요.")
            data = b"".join(chunks)
            if data.startswith(b"RIFF"):
                path.write_bytes(data)
            else:
                if len(data) % 2 or not 8000 <= sample_rate <= 96000:
                    raise RuntimeError("지원하지 않는 Gemini PCM 응답입니다.")
                with wave.open(str(path), "wb") as stream:
                    stream.setparams((1, 2, sample_rate, 0, "NONE", "not compressed"))
                    stream.writeframes(data)
            return
        if self.provider == "openai":
            from openai import OpenAI

            if self.openai is None:
                self.openai = OpenAI(api_key=settings.openai_api_key, timeout=60, max_retries=1)
            options = dict(
                model=settings.openai_tts_model, voice=settings.openai_tts_voice,
                input=scene.text, response_format="wav",
            )
            if "gpt-4o" in settings.openai_tts_model:
                options["instructions"] = direction
            with self.openai.audio.speech.with_streaming_response.create(**options) as response:
                response.stream_to_file(path)
            return
        raise ValueError(f"지원하지 않는 AI_PROVIDER: {self.provider}")

    def _cached_clip(self, scene: ScriptScene) -> Path:
        model = settings.gemini_tts_model if self.provider == "gemini" else settings.openai_tts_model
        voice = self.profile.voice if self.provider == "gemini" else settings.openai_tts_voice
        key = hashlib.sha256(json.dumps({
            "version": CACHE_VERSION, "provider": self.provider, "model": model,
            "voice": voice, "direction": speech_direction(self.profile, scene.emphasis),
            "speed": self.speed, "text": scene.text,
        }, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        folder = settings.temp_dir / "audio_cache"
        folder.mkdir(parents=True, exist_ok=True)
        cache = folder / f"{key}.wav"
        if cache.is_file():
            try:
                read_pcm(cache)
                return cache
            except (ValueError, wave.Error, EOFError):
                cache.unlink(missing_ok=True)
        token = uuid.uuid4().hex
        raw = folder / f"{token}.raw.wav"
        normalized = folder / f"{token}.normalized.wav"
        try:
            # One bounded retry for transient provider server errors; never spin on quota/auth.
            for attempt in range(2):
                try:
                    self._synthesize_raw(scene, raw)
                    break
                except Exception as exc:
                    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
                    if attempt or code not in (500, 502, 503, 504):
                        raise
                    time.sleep(2)
            command = [
                imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(raw), "-vn", "-ac", "1", "-ar", str(RATE),
                "-af", f"atempo={self.speed:.4f}", "-c:a", "pcm_s16le", str(normalized),
            ]
            subprocess.run(command, check=True, capture_output=True, timeout=30)
            samples = np.frombuffer(read_pcm(normalized), dtype="<i2")
            peak = int(np.abs(samples.astype(np.int32)).max())
            if peak < 40:
                raise RuntimeError("생성 음성에 유효한 소리가 없습니다.")
            # Trim only edge silence; retain 70ms around speech and all interior pauses.
            active = np.flatnonzero(np.abs(samples.astype(np.int32)) > max(60, peak * .008))
            if active.size:
                margin = round(RATE * .07)
                samples = samples[max(0, int(active[0]) - margin):min(len(samples), int(active[-1]) + margin + 1)]
            write_pcm(normalized, samples.tobytes())
            normalized.replace(cache)
        finally:
            raw.unlink(missing_ok=True)
            normalized.unlink(missing_ok=True)
        return cache

    def synthesize_scenes(self, scenes: list[ScriptScene], output_path: Path, progress=None) -> list[SubtitleSegment]:
        if not scenes or len(scenes) > 24:
            raise ValueError("음성 장면 수는 1~24개여야 합니다.")
        output_path = Path(output_path)
        if output_path.suffix.lower() != ".wav":
            raise ValueError("장면 음성 출력 경로는 .wav여야 합니다.")
        cursor_frames = 0
        gap_frames = round(RATE * .08)
        chunks: list[bytes] = []
        segments: list[SubtitleSegment] = []
        for index, scene in enumerate(scenes):
            if not scene.text.strip():
                raise ValueError("빈 발화 장면입니다.")
            clip = self._cached_clip(scene)
            data = read_pcm(clip)
            count = len(data) // 2
            segments.append(SubtitleSegment(
                cursor_frames / RATE, (cursor_frames + count) / RATE,
                scene.text, scene.emphasis, scene.image_index,
            ))
            chunks.append(data)
            cursor_frames += count
            if index < len(scenes) - 1:
                chunks.append(b"\0\0" * gap_frames)
                cursor_frames += gap_frames
            if progress:
                progress(index + 1, len(scenes))
        write_pcm(output_path, b"".join(chunks))
        output_path.with_suffix(".timing.json").write_text(
            json.dumps([asdict(s) for s in segments], ensure_ascii=False, indent=2), encoding="utf-8",
        )
        return segments

    def synthesize(self, text: str, output_path: Path) -> Path:
        self.synthesize_scenes(split_speech(text), output_path)
        return output_path

    def transcribe_segments(self, audio_path: Path, original_text=None, duration=None) -> list[SubtitleSegment]:
        timing = audio_path.with_suffix(".timing.json")
        if timing.is_file():
            return [SubtitleSegment(**item) for item in json.loads(timing.read_text(encoding="utf-8"))]
        raise RuntimeError("실측 타이밍 파일이 없습니다. synthesize_scenes로 음성을 생성하세요.")
