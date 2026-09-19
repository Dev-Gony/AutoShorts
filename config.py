from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Settings:
    ai_provider: str = os.getenv("AI_PROVIDER", "gemini").strip().lower()

    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_script_model: str = (
        "gemini-3.5-flash-lite"
        if os.getenv("GEMINI_SCRIPT_MODEL", "gemini-3.5-flash-lite")
        == "gemini-2.5-flash-lite"
        else os.getenv("GEMINI_SCRIPT_MODEL", "gemini-3.5-flash-lite")
    )
    gemini_tts_model: str = os.getenv(
        "GEMINI_TTS_MODEL",
        "gemini-3.1-flash-tts-preview",
    )
    gemini_tts_voice: str = os.getenv("GEMINI_TTS_VOICE", "Kore")
    gemini_transcription_model: str = os.getenv(
        "GEMINI_TRANSCRIPTION_MODEL",
        "gemini-3.5-transcribe",
    )

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_script_model: str = os.getenv(
        "OPENAI_SCRIPT_MODEL",
        "gpt-5.6-luna",
    )
    openai_tts_model: str = os.getenv(
        "OPENAI_TTS_MODEL",
        "gpt-4o-mini-tts",
    )
    openai_tts_voice: str = os.getenv("OPENAI_TTS_VOICE", "coral")
    openai_transcription_model: str = os.getenv(
        "OPENAI_TRANSCRIPTION_MODEL",
        "whisper-1",
    )

    request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "20"))
    min_source_chars: int = 100
    max_script_chars: int = 420
    target_video_seconds: float = 50.0
    max_video_seconds: float = 59.0
    output_dir: Path = BASE_DIR / "output"
    temp_dir: Path = BASE_DIR / "temp"
    background_dir: Path = BASE_DIR / "assets" / "backgrounds"

    @property
    def active_api_key(self) -> str:
        if self.ai_provider == "gemini":
            return self.gemini_api_key
        if self.ai_provider == "openai":
            return self.openai_api_key
        return ""

    @property
    def active_script_model(self) -> str:
        if self.ai_provider == "gemini":
            return self.gemini_script_model
        return self.openai_script_model

    @property
    def active_tts_model(self) -> str:
        if self.ai_provider == "gemini":
            return self.gemini_tts_model
        return self.openai_tts_model

    def ensure_directories(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.background_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
