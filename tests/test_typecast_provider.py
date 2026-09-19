from dataclasses import replace
from types import SimpleNamespace

import pytest

import src.audio as audio_module
from config import settings
from src.audio import AudioService
from src.models import ScriptScene


def test_typecast_sdk_request_model_contract():
    typecast = pytest.importorskip("typecast")
    from typecast.models import SmartPrompt, TTSRequest

    request = TTSRequest(
        text="이 골목에 이런 집이 있었어요?",
        model="ssfm-v30",
        voice_id="tc_test_voice",
        language="kor",
        prompt=SmartPrompt(emotion_type="smart"),
    )
    assert request.model == "ssfm-v30"
    assert request.voice_id == "tc_test_voice"


def test_typecast_voice_recommendation(monkeypatch):
    fake_settings = replace(
        settings,
        tts_provider="typecast",
        typecast_api_key="test-key",
        typecast_voice_id="",
    )
    monkeypatch.setattr(audio_module, "settings", fake_settings)

    class Response:
        def raise_for_status(self):
            return None
        def json(self):
            return [
                {"voice_id": "tc_recommended", "voice_name": "추천", "score": 0.99}
            ]

    import requests
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: Response())

    service = AudioService("food_vlog", 1.0)
    assert service._resolve_typecast_voice_id() == "tc_recommended"
    assert service._resolve_typecast_voice_id() == "tc_recommended"


def test_typecast_synthesis_uses_smart_emotion(monkeypatch, tmp_path):
    fake_settings = replace(
        settings,
        tts_provider="typecast",
        typecast_api_key="test-key",
        typecast_voice_id="tc_fixed",
        typecast_model="ssfm-v30",
    )
    monkeypatch.setattr(audio_module, "settings", fake_settings)

    captured = {}

    class FakeClient:
        def __init__(self, api_key=None):
            captured["api_key"] = api_key
        def text_to_speech(self, request):
            captured["request"] = request
            return SimpleNamespace(audio_data=b"RIFFfake-wav")

    import typecast
    monkeypatch.setattr(typecast, "Typecast", FakeClient)

    service = AudioService("food_vlog", 1.0)
    output = tmp_path / "raw.wav"
    service._synthesize_raw(ScriptScene("국물이 시원해요.", "국물"), output)

    request = captured["request"]
    assert captured["api_key"] == "test-key"
    assert request.voice_id == "tc_fixed"
    assert request.model == "ssfm-v30"
    assert request.language == "kor"
    assert request.prompt.emotion_type == "smart"
    assert output.read_bytes() == b"RIFFfake-wav"
