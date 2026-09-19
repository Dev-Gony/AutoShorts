from dataclasses import replace
import json
import wave

import numpy as np
import pytest

import src.audio as audio_module
from config import settings
from src.audio import AudioService, RATE, read_pcm, split_speech, write_pcm
from src.models import ScriptScene
from src.voices import PROFILES, selected_profile, speech_direction


@pytest.mark.parametrize("preset", list(PROFILES))
def test_presets_include_direction(preset):
    name, profile = selected_profile(preset)
    assert name == preset
    assert profile.voice
    direction = speech_direction(profile, "국물")
    assert "국물" in direction and "TRANSCRIPT" in direction


@pytest.mark.parametrize("speed", [.1, 2, float("nan")])
def test_invalid_speed_stops(speed):
    with pytest.raises(ValueError):
        AudioService(speed=speed)


def test_splitting_does_not_lose_text():
    text = "국물부터 한 입 먹어봤어요. " + "가" * 80
    scenes = split_speech(text)
    assert "".join(s.text.replace(" ", "") for s in scenes) == text.replace(" ", "")
    assert max(len(s.text) for s in scenes) <= 30


def test_pcm_rejects_wrong_rate(tmp_path):
    path = tmp_path / "bad.wav"
    with wave.open(str(path), "wb") as f:
        f.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
        f.writeframes(b"\0\0" * 8000)
    with pytest.raises(ValueError):
        read_pcm(path)


def test_measured_timeline_and_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(audio_module, "settings", replace(settings, ai_provider="gemini", temp_dir=tmp_path))
    calls = []
    service = AudioService("food_vlog", speed=1)
    def synthesize(scene, path):
        calls.append(scene.text)
        data = (np.sin(np.arange(RATE) * 2 * np.pi * 220 / RATE) * 1000).astype("<i2").tobytes()
        write_pcm(path, data)
    monkeypatch.setattr(service, "_synthesize_raw", synthesize)
    scenes = [ScriptScene("국물이 시원해요.", "국물", 0), ScriptScene("면발도 살펴볼게요.", "면발", 1)]
    output = tmp_path / "voice.wav"
    segments = service.synthesize_scenes(scenes, output)
    assert len(calls) == 2
    assert segments[0].start == 0
    assert segments[1].start == pytest.approx(segments[0].end + .08)
    assert segments[-1].end == pytest.approx(len(read_pcm(output)) / (RATE * 2))
    assert [s.image_index for s in segments] == [0, 1]
    service.synthesize_scenes(scenes, output)
    assert len(calls) == 2
    saved = json.loads(output.with_suffix(".timing.json").read_text())
    assert saved[1]["text"] == scenes[1].text


def test_silent_tts_is_not_success(monkeypatch, tmp_path):
    monkeypatch.setattr(audio_module, "settings", replace(settings, ai_provider="gemini", temp_dir=tmp_path))
    service = AudioService(speed=1)
    monkeypatch.setattr(service, "_synthesize_raw", lambda scene, path: write_pcm(path, b"\0\0" * RATE))
    with pytest.raises(RuntimeError, match="소리"):
        service.synthesize_scenes([ScriptScene("확인해요.")], tmp_path / "voice.wav")


def test_missing_timing_does_not_estimate_by_letters(tmp_path):
    with pytest.raises(RuntimeError):
        AudioService().transcribe_segments(tmp_path / "old.wav", "대본", 10)
