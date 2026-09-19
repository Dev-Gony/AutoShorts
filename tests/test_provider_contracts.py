from dataclasses import replace
from types import SimpleNamespace
import wave

import pytest
from PIL import Image

genai = pytest.importorskip("google.genai")

import src.audio as audio_module
import src.llm as llm_module
from config import settings
from src.audio import AudioService
from src.llm import ScriptGenerator
from src.models import ScriptScene


def test_real_sdk_config_for_directed_gemini_tts(monkeypatch, tmp_path):
    captured = {}
    def generate_content(**kwargs):
        captured.update(kwargs)
        part = SimpleNamespace(inline_data=SimpleNamespace(mime_type="audio/L16;rate=24000", data=b"\1\0" * 12000))
        return SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=[part]))])
    monkeypatch.setattr(genai, "Client", lambda **kwargs: SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)))
    monkeypatch.setattr(audio_module, "settings", replace(settings, ai_provider="gemini", gemini_api_key="test-not-a-secret"))
    output = tmp_path / "voice.wav"
    AudioService("bright")._synthesize_raw(ScriptScene("메뉴부터 살펴볼까요?", "메뉴"), output)
    config = captured["config"]
    assert config.speech_config.voice_config.prebuilt_voice_config.voice_name == "Aoede"
    assert config.automatic_function_calling.disable is True
    assert "AUDIO PROFILE" in captured["contents"] and "TRANSCRIPT" in captured["contents"]
    with wave.open(str(output)) as audio:
        assert audio.getnchannels() == 1 and audio.getframerate() == 24000
        assert audio.getnframes() == 12000


def test_real_sdk_config_and_image_parts_for_scene_planning(monkeypatch, tmp_path):
    captured = {}
    def generate_content(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(text='{"title":"test","scenes":[]}')
    monkeypatch.setattr(genai, "Client", lambda **kwargs: SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)))
    monkeypatch.setattr(llm_module, "settings", replace(settings, ai_provider="gemini", gemini_api_key="test-not-a-secret"))
    path = tmp_path / "photo.jpg"
    Image.new("RGB", (600, 400), "red").save(path)
    assert ScriptGenerator()._request("Scene planning", [path])
    assert captured["config"].response_mime_type == "application/json"
    assert captured["config"].automatic_function_calling.disable is True
    assert captured["contents"][1] == "image_index=0"
    assert captured["contents"][2].inline_data.mime_type == "image/jpeg"
