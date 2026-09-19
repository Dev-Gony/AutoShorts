from __future__ import annotations

from pathlib import Path

from config import settings
from src.audio import AudioService
from src.models import ScriptScene

PREVIEW_TEXT = "이 골목에 이런 집이 있었어요? 오늘은 메뉴랑 분위기, 솔직하게 짚어볼게요."


def preview_voice(preset: str = "food_vlog", speed: float | None = None) -> Path:
    settings.ensure_directories()
    output = settings.output_dir / f"voice_preview_{preset}.wav"
    service = AudioService(preset, speed)
    service.synthesize_scenes([ScriptScene(PREVIEW_TEXT, "이런 집")], output)
    return output


def safe_error(exc: Exception) -> str:
    # Provider error bodies may echo API keys. Only expose status, not those bodies.
    code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if code:
        hints = {
            400: "API 요청 형식/모델 지원을 확인하세요.",
            401: "API 키 인증 실패입니다.",
            402: "API 크레딧이 부족합니다.",
            403: "API 키 종류/계정 권한을 확인하세요.",
            404: "설정한 모델을 사용할 수 없습니다.",
            429: "호출 한도/크레딧을 확인하세요. 생성한 발화 캐시는 보존했습니다.",
        }
        return f"API {code}: {hints.get(code, '서비스 오류입니다. 잠시 후 다시 시도하세요.')}"
    text = str(exc)
    for key in (settings.gemini_api_key, settings.openai_api_key, settings.typecast_api_key):
        if key:
            text = text.replace(key, "[REDACTED]")
    return text[:700]
