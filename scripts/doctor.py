from __future__ import annotations

import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import settings


def check(name: str, ok: bool, detail: str) -> bool:
    mark = "OK" if ok else "FAIL"
    print(f"[{mark}] {name}: {detail}")
    return ok


def main() -> int:
    checks: list[bool] = []

    checks.append(
        check(
            "Python",
            sys.version_info >= (3, 10),
            sys.version.split()[0],
        )
    )

    checks.append(
        check(
            "OPENAI_API_KEY",
            bool(settings.openai_api_key),
            "설정됨" if settings.openai_api_key else ".env에 설정 필요",
        )
    )

    ffmpeg = shutil.which("ffmpeg")
    checks.append(
        check(
            "FFmpeg",
            bool(ffmpeg),
            ffmpeg or "PATH에서 찾지 못함",
        )
    )

    settings.ensure_directories()

    checks.append(
        check(
            "output directory",
            settings.output_dir.exists(),
            str(settings.output_dir),
        )
    )
    checks.append(
        check(
            "temp directory",
            settings.temp_dir.exists(),
            str(settings.temp_dir),
        )
    )

    backgrounds = list(settings.background_dir.glob("*.mp4"))
    check(
        "background video",
        True,
        f"{len(backgrounds)}개 등록됨"
        if backgrounds
        else "없음 - 기본 단색 배경을 사용하므로 실행 가능",
    )

    print()
    if all(checks):
        print("AutoShorts 실행 준비가 완료되었습니다.")
        return 0

    print("실행 전에 FAIL 항목을 해결해주세요.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
