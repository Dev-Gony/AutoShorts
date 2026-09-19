from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from moviepy import AudioFileClip

from config import settings
from src.audio import AudioService, split_speech
from src.captions import make_caption
from src.llm import ScriptGenerator
from src.media import download_images
from src.models import PipelineResult, SubtitleSegment
from src.subtitles import write_srt
from src.video import VideoRenderer, VisualSourceError

ProgressCallback = Callable[[int, int, str], None]


class Pipeline:
    TOTAL_STEPS = 6

    def __init__(
        self,
        script_generator=None,
        audio_service=None,
        renderer=None,
        progress_callback: ProgressCallback | None = None,
        preset=None,
        speed=None,
        voice_id: str | None = None,
    ):
        settings.ensure_directories()
        self.script_generator = script_generator or ScriptGenerator()
        self.audio_service = audio_service or AudioService(preset, speed, voice_id=voice_id)
        self.renderer = renderer or VideoRenderer()
        self.progress_callback = progress_callback

    def _progress(self, step: int, message: str) -> None:
        if self.progress_callback:
            self.progress_callback(step, self.TOTAL_STEPS, message)
        else:
            print(f"[{step}/{self.TOTAL_STEPS}] {message}")

    @staticmethod
    def _audio_duration(path: Path) -> float:
        with AudioFileClip(str(path)) as audio:
            return float(audio.duration)

    def _download_blog_images(self, image_urls, work_dir, referer, limit=12):
        return download_images(image_urls, work_dir / "images", referer, limit)

    def run(self, url: str) -> PipelineResult:
        started = time.perf_counter()
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
        work_dir = settings.temp_dir / run_id
        work_dir.mkdir(parents=True, exist_ok=False)
        timings = {}
        stage = "source"
        try:
            self._progress(1, "본문과 사진 확인")
            from src.scraper import get_scraper
            source = get_scraper(url).extract(url)
            (work_dir / "source.txt").write_text(source.text, encoding="utf-8")
            (work_dir / "source.json").write_text(json.dumps(asdict(source), ensure_ascii=False, indent=2), encoding="utf-8")
            backgrounds = sorted(settings.background_dir.glob("*.mp4"))
            background = backgrounds[0] if backgrounds else None
            images = self._download_blog_images(source.images, work_dir, source.url) if background is None else []
            if not images and background is None:
                raise VisualSourceError("유효한 사진을 받지 못했습니다. 회색 영상은 만들지 않습니다. API 호출 전에 중단했습니다.")
            self.renderer._find_korean_font()
            self._progress(1, f"검증된 사진 {len(images)}장 / 폰트 준비 완료")
            timings[stage] = time.perf_counter() - started

            stage = "script"
            tick = time.perf_counter()
            self._progress(2, "대화체 대본과 장면별 사진 구성")
            script = self.script_generator.generate(source, image_paths=images)
            timings[stage] = time.perf_counter() - tick
            stage = "voice"
            tick = time.perf_counter()
            for attempt in range(2):
                (work_dir / "script.json").write_text(json.dumps(asdict(script), ensure_ascii=False, indent=2), encoding="utf-8")
                for line in [script.title] + [s.text for s in script.scenes or split_speech(script.script)]:
                    make_caption(line)
                audio_path = work_dir / f"voice_{attempt + 1}.wav"
                self._progress(3, "장면별 음성 연출 / 생성된 발화는 캐시 재사용")
                scenes = script.scenes or split_speech(script.script)
                subtitles = self.audio_service.synthesize_scenes(
                    scenes, audio_path,
                    progress=lambda n, total: self._progress(3, f"음성 {n}/{total} 완료"),
                )
                duration = self._audio_duration(audio_path)
                if duration <= settings.max_video_seconds:
                    break
                if attempt:
                    raise RuntimeError(f"음성 {duration:.1f}초: 길이 제한 초과. 대본/음성을 보관했습니다.")
                target = max(100, int(len(script.script) * 50 / duration))
                self._progress(3, f"{duration:.1f}초 → 문장 단위 축약 1회")
                script = self.script_generator.shorten(script, target_chars=target)
            timings[stage] = time.perf_counter() - tick
            stage = "timeline"
            self._progress(4, "실제 발화 길이로 자막·장면 타임라인 확정")
            write_srt(subtitles, work_dir / "subtitles.srt")
            manifest = {
                "schema_version": 2, "title": script.title, "duration": duration,
                "audio": audio_path.name, "images": [p.relative_to(work_dir).as_posix() for p in images],
                "background": str(background.resolve()) if background else None,
                "subtitles": [asdict(s) for s in subtitles],
                "voice_preset": getattr(self.audio_service, "preset", "injected"),
                "voice_speed": getattr(self.audio_service, "speed", None),
                "timing_method": "measured_utterance_pcm", "stage_seconds": timings,
            }
            manifest_path = work_dir / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            self._progress(5, "2줄 자막 안전영역 / 사진 전환 검증")
            stage = "render"
            tick = time.perf_counter()
            self._progress(6, "9:16 영상 렌더링 및 실제 출력 검증")
            video_path = settings.output_dir / f"autoshorts_{run_id}.mp4"
            self.renderer.render(background, audio_path, subtitles, video_path, image_paths=images, title=script.title)
            timings[stage] = time.perf_counter() - tick
            elapsed = time.perf_counter() - started
            manifest.update(elapsed_seconds=elapsed, stage_seconds=timings, kpi_180s_met=elapsed < 180)
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            return PipelineResult(source, script, audio_path, video_path, subtitles, elapsed, work_dir)
        except Exception:
            # Do not persist raw provider exception strings; some echo credentials.
            (work_dir / "failure.json").write_text(json.dumps({
                "stage": stage, "elapsed_seconds": time.perf_counter() - started,
            }), encoding="utf-8")
            raise


def rerender(run: str = "latest") -> Path:
    """Re-encode a v2 run with cached audio/media. No provider client or API calls."""
    if run == "latest":
        runs = sorted(settings.temp_dir.glob("*/manifest.json"), key=lambda p: p.stat().st_mtime)
        if not runs:
            raise FileNotFoundError("v2 저장 결과가 없습니다. 먼저 새 버전으로 한 번 생성하세요.")
        folder = runs[-1].parent
    else:
        folder = Path(run).resolve()
    data = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    output = settings.output_dir / f"{folder.name}_restyled_{uuid.uuid4().hex[:6]}.mp4"
    VideoRenderer().render(
        Path(data["background"]) if data.get("background") else None,
        folder / data["audio"], [SubtitleSegment(**s) for s in data["subtitles"]], output,
        image_paths=[folder / p for p in data["images"]], title=data["title"],
    )
    return output
