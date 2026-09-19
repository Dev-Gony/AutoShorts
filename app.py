from __future__ import annotations

import argparse

from config import settings
from src.preview import preview_voice, safe_error
from src.voices import PROFILES


def main() -> int:
    parser = argparse.ArgumentParser(description="AutoShorts: directed voices and scene-based shorts")
    parser.add_argument("--url", help="Blog URL; omitted for an interactive prompt")
    parser.add_argument("--voice", choices=list(PROFILES), help="Voice preset")
    parser.add_argument("--speed", type=float, help="Playback tempo, 0.9 to 1.2; pitch is preserved")
    parser.add_argument("--preview-voice", action="store_true", help="Generate a short voice sample, not a full video")
    parser.add_argument("--rerender", metavar="RUN", help="Re-render a v2 run directory, or latest, without API calls")
    args = parser.parse_args()
    print("AutoShorts | voice + scene quality v2")
    print(f"AI Provider: {settings.ai_provider}")
    try:
        if args.rerender:
            from src.pipeline import rerender
            print(f"영상: {rerender(args.rerender)}")
            return 0
        if not settings.active_api_key:
            raise ValueError(f".env에 {settings.ai_provider.upper()} API 키를 설정하세요.")
        if args.preview_voice:
            path = preview_voice(args.voice or "food_vlog", args.speed)
            print(f"음성 샘플: {path}")
            print("실제 TTS 호출입니다. 같은 설정의 샘플은 캐시를 재사용합니다.")
            return 0
        url = args.url or input("블로그 URL: ").strip()
        if not url:
            raise ValueError("URL을 입력하세요.")
        from src.pipeline import Pipeline
        result = Pipeline(preset=args.voice, speed=args.speed).run(url)
        print(f"영상: {result.video_path}")
        print(f"화면 미리보기: {result.video_path.with_suffix('.preview.png')}")
        print(f"총 소요시간: {result.elapsed_seconds:.1f}초")
        print(f"실행 기록: {result.work_dir}")
        if result.elapsed_seconds >= 180:
            print("주의: 이번 실행은 180초 목표를 초과했습니다. manifest.json에서 단계별 시간을 확인하세요.")
        return 0
    except Exception as exc:
        print(f"실패: {safe_error(exc)}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
