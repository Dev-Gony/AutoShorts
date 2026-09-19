from __future__ import annotations

import sys

from config import settings
from src.pipeline import Pipeline


def main() -> int:
    print("=" * 40)
    print("          AutoShorts MVP")
    print("=" * 40)
    print(f"AI Provider: {settings.ai_provider}")

    if not settings.active_api_key:
        key_name = (
            "GEMINI_API_KEY"
            if settings.ai_provider == "gemini"
            else "OPENAI_API_KEY"
        )
        print(f"오류: .env에 {key_name}를 설정하세요.")
        return 1

    url = input("블로그 URL: ").strip()
    if not url:
        print("오류: URL을 입력하세요.")
        return 1

    try:
        result = Pipeline().run(url)
    except Exception as exc:
        print(f"\n실패: {exc}")
        return 1

    print("\n완료!")
    print(f"영상: {result.video_path}")
    print(f"총 소요시간: {result.elapsed_seconds:.1f}초")
    return 0


if __name__ == "__main__":
    sys.exit(main())
