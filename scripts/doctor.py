from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import imageio_ffmpeg

from config import settings


def check(name: str, ok: bool, detail: str) -> bool:
    mark = "OK" if ok else "FAIL"
    print(f"[{mark}] {name}: {detail}")
    return ok


def main() -> int:
    checks: list[bool] = []

    checks.append(check("Python", sys.version_info >= (3, 10), sys.version.split()[0]))

    ai_ok = settings.ai_provider in {"gemini", "openai"}
    checks.append(check("AI_PROVIDER", ai_ok, settings.ai_provider))
    ai_key_name = "GEMINI_API_KEY" if settings.ai_provider == "gemini" else "OPENAI_API_KEY"
    checks.append(check(
        ai_key_name,
        bool(settings.active_api_key),
        "설정됨" if settings.active_api_key else ".env에 설정 필요",
    ))

    tts_ok = settings.tts_provider in {"typecast", "gemini", "openai"}
    checks.append(check("TTS_PROVIDER", tts_ok, settings.tts_provider))
    tts_key_name = {
        "typecast": "TYPECAST_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
    }.get(settings.tts_provider, "TTS_API_KEY")
    checks.append(check(
        tts_key_name,
        bool(settings.active_tts_api_key),
        "설정됨" if settings.active_tts_api_key else ".env에 설정 필요",
    ))

    if settings.tts_provider == "typecast":
        check(
            "Typecast voice",
            True,
            settings.typecast_voice_id or "미지정 - 첫 음성 생성 시 추천 API로 자동 선택",
        )

    try:
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        ffmpeg_ok = bool(ffmpeg and Path(ffmpeg).exists())
    except Exception as exc:
        ffmpeg = f"탐지 실패: {exc}"
        ffmpeg_ok = False

    checks.append(check("FFmpeg", ffmpeg_ok, str(ffmpeg)))

    settings.ensure_directories()
    checks.append(check("output directory", settings.output_dir.exists(), str(settings.output_dir)))
    checks.append(check("temp directory", settings.temp_dir.exists(), str(settings.temp_dir)))

    backgrounds = list(settings.background_dir.glob("*.mp4"))
    check(
        "background video",
        True,
        f"{len(backgrounds)}개 등록됨" if backgrounds else "없음 - 블로그 사진을 영상 소스로 사용",
    )

    print()
    if all(checks):
        print("AutoShorts 실행 준비가 완료되었습니다.")
        return 0
    print("실행 전에 FAIL 항목을 해결해주세요.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
