from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent

@dataclass(frozen=True)
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    script_model: str = os.getenv("SCRIPT_MODEL", "gpt-5.6-luna")
    tts_model: str = os.getenv("TTS_MODEL", "gpt-4o-mini-tts")
    tts_voice: str = os.getenv("TTS_VOICE", "coral")
    transcription_model: str = os.getenv("TRANSCRIPTION_MODEL", "whisper-1")
    request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "20"))
    min_source_chars: int = 100
    max_script_chars: int = 420
    target_video_seconds: float = 50.0
    max_video_seconds: float = 59.0
    output_dir: Path = BASE_DIR / "output"
    temp_dir: Path = BASE_DIR / "temp"
    background_dir: Path = BASE_DIR / "assets" / "backgrounds"

    def ensure_directories(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.background_dir.mkdir(parents=True, exist_ok=True)

settings = Settings()
