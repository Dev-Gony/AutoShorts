import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw
from moviepy import VideoFileClip

from src.audio import RATE, write_pcm
from src.captions import CaptionLayoutError, find_korean_font, make_caption
from src.llm import ScriptGenerationError, parse_plan
from src.media import normalize_image
from src.models import SubtitleSegment
from src.video import SceneComposer, VideoRenderer, VisualSourceError, validate_timeline


@pytest.mark.parametrize("text", ["국물은 시원하고 면발은 쫄깃해요.", "을지로 골목에서 찾은 한 그릇이에요.", "대표 메뉴부터 살펴볼까요?", "가" * 32])
@pytest.mark.parametrize("size", [(1080, 1920), (540, 960), (270, 480)])
def test_caption_pixels_fit_safely(text, size):
    card = make_caption(text, width=size[0], height=size[1])
    x0, y0, x1, y1 = card.box
    assert len(card.lines) <= 2
    assert x0 >= size[0] * .05 and x1 <= size[0] * .9
    assert y1 <= size[1] * .8
    assert card.image.mode == "RGBA"
    # Transparent padding around the card, not text drawn beyond its image canvas.
    assert y0 >= 0 and card.font_size >= 12
    card.image.close()


def test_font_selection_rejects_missing_explicit_font(monkeypatch):
    monkeypatch.setenv("AUTOSHORTS_FONT", "/missing/explicit-font.ttf")
    with pytest.raises(CaptionLayoutError):
        find_korean_font()


def test_overlong_caption_is_not_silently_cut():
    with pytest.raises(CaptionLayoutError):
        make_caption("아주 긴 문장 " * 100)


def test_blank_caption_is_rejected():
    with pytest.raises(CaptionLayoutError):
        make_caption(" ")


@pytest.mark.parametrize("span", [(0, 0), (-1, 1), (0, 4), (float("nan"), 1)])
def test_bad_timing_is_rejected(span):
    with pytest.raises(ValueError):
        validate_timeline([SubtitleSegment(*span, "테스트")], 2)


def test_overlap_is_rejected():
    with pytest.raises(ValueError):
        validate_timeline([SubtitleSegment(0, 1.5, "하나"), SubtitleSegment(1, 2, "둘")], 2)


def fixture_photo(path, shift=0):
    image = Image.new("RGB", (640, 420), (35 + shift, 60, 100))
    draw = ImageDraw.Draw(image)
    for x in range(0, 640, 40):
        draw.rectangle((x, 30, x + 20, 390), fill=(180, 60 + shift, 30))
    image.save(path)


def test_composer_has_motion_and_real_visuals(tmp_path):
    photo = tmp_path / "photo.jpg"
    fixture_photo(photo)
    segments = [SubtitleSegment(0, 2, "국물이 시원해요.", "시원", 0)]
    composer = SceneComposer([photo], segments, 2, size=(270, 480))
    try:
        a, b = composer.frame(.2), composer.frame(1.8)
        assert a.shape == (480, 270, 3)
        assert a.std() > 15
        assert np.mean(np.abs(a.astype(float) - b)) > .2
    finally:
        composer.close()


def test_actual_mp4_has_picture_audio_and_expected_dimensions(tmp_path):
    photo = tmp_path / "photo.jpg"
    fixture_photo(photo)
    audio = tmp_path / "tone.wav"
    write_pcm(audio, (np.sin(np.arange(RATE * 2) * 2 * np.pi * 330 / RATE) * 2000).astype("<i2").tobytes())
    renderer = VideoRenderer()
    renderer.WIDTH, renderer.HEIGHT = 270, 480
    output = tmp_path / "real.mp4"
    renderer.render(None, audio, [SubtitleSegment(0, 2, "국물이 시원해요.", "시원", 0)], output, [photo], "골목의 한 그릇")
    with VideoFileClip(str(output)) as video:
        assert tuple(video.size) == (270, 480)
        assert video.audio is not None
        assert abs(video.duration - 2) < .2
        assert video.get_frame(.5).std() > 15
    assert output.with_suffix(".preview.png").is_file()
    assert output.with_suffix(".last-frame.png").is_file()
    assert not list(tmp_path.glob("*.tmp.mp4"))


def test_no_visual_fallback(tmp_path):
    with pytest.raises(VisualSourceError):
        VideoRenderer().render(None, tmp_path / "unused.wav", [], tmp_path / "no.mp4")
    assert not (tmp_path / "no.mp4").exists()


def valid_plan():
    return {"title": "한 그릇 리뷰", "scenes": [{"text": "골목에서 한 그릇을 찾았어요.", "emphasis": "한 그릇", "image_index": 0} for _ in range(4)]}


def test_plan_keeps_scene_mapping_and_original_text():
    plan = parse_plan(json.dumps(valid_plan()), 420, 1)
    assert len(plan.scenes) == 4 and all(s.image_index == 0 for s in plan.scenes)
    assert plan.script == " ".join(s.text for s in plan.scenes)


@pytest.mark.parametrize("change", ["title", "scenes", "long", "type"])
def test_plan_validation(change):
    data = valid_plan()
    if change == "title":
        data["title"] = "가" * 31
    elif change == "scenes":
        data["scenes"] = []
    elif change == "long":
        data["scenes"][0]["text"] = "가" * 33
    else:
        data["scenes"][0]["text"] = None
    with pytest.raises(ScriptGenerationError):
        parse_plan(json.dumps(data), 420, 1)


def test_invalid_image_index_is_not_hallucinated():
    data = valid_plan()
    data["scenes"][0]["image_index"] = 99
    assert parse_plan(json.dumps(data), 420, 1).scenes[0].image_index is None


def test_fake_image_bytes_are_rejected(tmp_path):
    with pytest.raises(OSError):
        normalize_image(b"this is not a photo", tmp_path / "bad.jpg")


def test_first_scene_hook_must_be_short():
    data = valid_plan()
    data["scenes"][0]["text"] = "첫 장면은 아주 길게 설명부터 시작하면 안 되는 문장이에요"
    with pytest.raises(ScriptGenerationError, match="첫 장면"):
        parse_plan(json.dumps(data, ensure_ascii=False), 420, 1)


def test_duplicate_scene_text_is_rejected():
    data = valid_plan()
    data["scenes"][1]["text"] = data["scenes"][0]["text"]
    with pytest.raises(ScriptGenerationError, match="반복"):
        parse_plan(json.dumps(data, ensure_ascii=False), 420, 1)


def test_caption_sits_above_bottom_ui_safe_zone():
    card = make_caption("국물부터 한입 먹어볼게요.", width=1080, height=1920)
    try:
        assert card.y + card.image.height <= 1920 * .74
    finally:
        card.image.close()
