from pathlib import Path

import src.pipeline as pipeline_module
from src.models import BlogContent, ShortScript, SubtitleSegment
from src.pipeline import Pipeline


class FakeScraper:
    def extract(self, url: str) -> BlogContent:
        return BlogContent(
            url=url,
            source="generic",
            title="테스트 블로그",
            text="테스트 본문입니다. " * 30,
            images=[],
        )


class FakeScriptGenerator:
    def generate(self, content: BlogContent) -> ShortScript:
        return ShortScript(
            title="테스트 숏폼",
            hook="이거 알고 계셨나요?",
            script="이것은 자동 생성된 테스트 숏폼 대본입니다.",
            hashtags=["#테스트"],
        )

    def shorten(self, item: ShortScript, target_chars: int = 300) -> ShortScript:
        return item


class FakeAudioService:
    def synthesize(self, text: str, output_path: Path) -> Path:
        output_path.write_bytes(b"fake-audio")
        return output_path

    def transcribe_segments(self, audio_path: Path) -> list[SubtitleSegment]:
        return [
            SubtitleSegment(0.0, 1.5, "이것은 자동 생성된"),
            SubtitleSegment(1.5, 3.0, "테스트 자막입니다."),
        ]


class FakeRenderer:
    def render(
        self,
        background_path,
        audio_path,
        subtitles,
        output_path: Path,
    ) -> Path:
        output_path.write_bytes(b"fake-video")
        return output_path


def test_pipeline_runs_end_to_end_without_external_api(monkeypatch, tmp_path):
    monkeypatch.setattr(pipeline_module, "get_scraper", lambda url: FakeScraper())
    monkeypatch.setattr(pipeline_module.settings, "temp_dir", tmp_path / "temp")
    monkeypatch.setattr(pipeline_module.settings, "output_dir", tmp_path / "output")
    monkeypatch.setattr(pipeline_module.settings, "background_dir", tmp_path / "backgrounds")

    pipeline = Pipeline(
        script_generator=FakeScriptGenerator(),
        audio_service=FakeAudioService(),
        renderer=FakeRenderer(),
    )
    monkeypatch.setattr(pipeline, "_audio_duration", lambda path: 3.0)

    result = pipeline.run("https://example.com/post")

    assert result.source.title == "테스트 블로그"
    assert result.short_script.title == "테스트 숏폼"
    assert len(result.subtitles) == 2
    assert result.video_path.exists()
    assert result.video_path.read_bytes() == b"fake-video"

    work_dirs = list((tmp_path / "temp").iterdir())
    assert len(work_dirs) == 1
    assert (work_dirs[0] / "source.txt").exists()
    assert (work_dirs[0] / "script.json").exists()
    assert (work_dirs[0] / "subtitles.srt").exists()
