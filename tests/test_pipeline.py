from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import src.pipeline as pipeline_module
import src.scraper as scraper_module
from config import settings
from src.audio import RATE, write_pcm
from src.captions import find_korean_font
from src.models import BlogContent, ScriptScene, ShortScript, SubtitleSegment
from src.pipeline import Pipeline
from src.video import VisualSourceError


class FakeScraper:
    def extract(self, url):
        return BlogContent(url, "generic", "리뷰", "테스트 본문입니다. " * 30, ["https://example.com/photo.jpg"])


class FakeWriter:
    calls = 0
    def generate(self, content, image_paths=None):
        self.calls += 1
        scene = ScriptScene("따뜻한 한 그릇을 소개해요.", "한 그릇", 0)
        return ShortScript("골목에서 찾은 한 그릇", scene.text, scene.text, scenes=[scene])
    def shorten(self, item, target_chars=260):
        return item


class FakeAudio:
    preset, speed = "test", 1.0
    def synthesize_scenes(self, scenes, output_path, progress=None):
        write_pcm(output_path, (np.sin(np.arange(RATE) * .1) * 1000).astype("<i2").tobytes())
        return [SubtitleSegment(0, 1, scenes[0].text, scenes[0].emphasis, 0)]


class FakeRenderer:
    @staticmethod
    def _find_korean_font():
        return find_korean_font()
    def render(self, background_path, audio_path, subtitles, output_path, image_paths=None, title=""):
        assert image_paths and image_paths[0].is_file()
        assert title
        output_path.write_bytes(b"test orchestration only, not a rendered video")
        return output_path


def setup_pipeline(monkeypatch, tmp_path):
    config = replace(settings, temp_dir=tmp_path / "temp", output_dir=tmp_path / "output", background_dir=tmp_path / "backgrounds")
    monkeypatch.setattr(pipeline_module, "settings", config)
    monkeypatch.setattr(scraper_module, "get_scraper", lambda url: FakeScraper())
    writer = FakeWriter()
    pipeline = Pipeline(writer, FakeAudio(), FakeRenderer())
    def images(urls, folder, referer, limit=12):
        path = folder / "image.jpg"
        Image.new("RGB", (400, 400), "red").save(path)
        return [path]
    monkeypatch.setattr(pipeline, "_download_blog_images", images)
    return pipeline, writer


def test_pipeline_keeps_manifest_and_timing(monkeypatch, tmp_path):
    pipeline, _ = setup_pipeline(monkeypatch, tmp_path)
    result = pipeline.run("https://example.com/post")
    assert result.video_path.exists()
    assert result.audio_path.suffix == ".wav"
    import json
    manifest = json.loads((result.work_dir / "manifest.json").read_text())
    assert manifest["timing_method"] == "measured_utterance_pcm"
    assert manifest["images"] == ["image.jpg"]
    assert (result.work_dir / "subtitles.srt").exists()
    assert (result.work_dir / "script.json").exists()


def test_empty_media_stops_before_paid_generation(monkeypatch, tmp_path):
    pipeline, writer = setup_pipeline(monkeypatch, tmp_path)
    monkeypatch.setattr(pipeline, "_download_blog_images", lambda *args: [])
    with pytest.raises(VisualSourceError):
        pipeline.run("https://example.com/post")
    assert writer.calls == 0


def test_run_directories_do_not_collide(monkeypatch, tmp_path):
    pipeline, _ = setup_pipeline(monkeypatch, tmp_path)
    one = pipeline.run("https://example.com/post")
    two = pipeline.run("https://example.com/post")
    assert one.work_dir != two.work_dir
