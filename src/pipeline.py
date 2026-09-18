from __future__ import annotations

import json
import time
from datetime import datetime
from moviepy import AudioFileClip

from config import settings
from src.audio import AudioService
from src.llm import ScriptGenerator
from src.models import PipelineResult
from src.scraper import get_scraper
from src.subtitles import write_srt
from src.video import VideoRenderer

class Pipeline:
    def __init__(self) -> None:
        settings.ensure_directories()
        self.script_generator = ScriptGenerator()
        self.audio_service = AudioService()
        self.renderer = VideoRenderer()

    def _audio_duration(self, path) -> float:
        with AudioFileClip(str(path)) as audio:
            return float(audio.duration)

    def run(self, url: str) -> PipelineResult:
        started = time.perf_counter()
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        work_dir = settings.temp_dir / run_id
        work_dir.mkdir(parents=True, exist_ok=True)

        print("[1/6] URL 검사 및 본문 추출")
        source = get_scraper(url).extract(url)
        (work_dir / "source.txt").write_text(source.text, encoding="utf-8")

        print(f"[2/6] 숏폼 대본 생성 ({len(source.text):,}자 원문)")
        short_script = self.script_generator.generate(source)

        print("[3/6] TTS 음성 생성")
        audio_path = work_dir / "voice.mp3"
        audio_duration = 0.0

        for attempt in range(3):
            self.audio_service.synthesize(short_script.script, audio_path)
            audio_duration = self._audio_duration(audio_path)

            if audio_duration <= settings.max_video_seconds:
                break

            if attempt == 2:
                raise RuntimeError(
                    f"자동 축약 후에도 음성이 {audio_duration:.1f}초로 "
                    f"{settings.max_video_seconds:.0f}초를 초과했습니다."
                )

            print(
                f"      음성 {audio_duration:.1f}초 → 자동 축약 후 재생성"
            )
            target_chars = max(220, int(len(short_script.script) * 0.82))
            short_script = self.script_generator.shorten(
                short_script,
                target_chars=target_chars,
            )

        (work_dir / "script.json").write_text(
            json.dumps(short_script.__dict__, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(f"[4/6] 자막 타임스탬프 생성 ({audio_duration:.1f}초)")
        subtitles = self.audio_service.transcribe_segments(audio_path)
        write_srt(subtitles, work_dir / "subtitles.srt")

        print("[5/6] 배경 영상 선택")
        backgrounds = sorted(settings.background_dir.glob("*.mp4"))
        background_path = backgrounds[0] if backgrounds else None
        if background_path is None:
            print("      배경 MP4 없음 → 기본 배경 사용")

        print("[6/6] 9:16 MP4 렌더링")
        video_path = settings.output_dir / f"autoshorts_{run_id}.mp4"
        self.renderer.render(background_path, audio_path, subtitles, video_path)

        elapsed = time.perf_counter() - started
        return PipelineResult(
            source=source,
            short_script=short_script,
            audio_path=audio_path,
            video_path=video_path,
            subtitles=subtitles,
            elapsed_seconds=elapsed,
        )
