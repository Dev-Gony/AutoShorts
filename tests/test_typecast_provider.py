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


def test_voice_candidate_parser(monkeypatch):
    import src.typecast_voices as voice_module
    from src.typecast_voices import recommend_typecast_voices

    class Response:
        def raise_for_status(self):
            return None
        def json(self):
            return [
                {
                    "voice_id": "tc_one",
                    "voice_name": "쇼츠남",
                    "gender": "male",
                    "age": "young_adult",
                    "score": 0.98,
                    "preview_url": "https://example.com/one.mp3",
                },
                {
                    "voice_id": "tc_two",
                    "voice_name": "쇼츠녀",
                    "gender": "female",
                    "age": "young_adult",
                    "score": 0.95,
                },
            ]

    monkeypatch.setattr(voice_module.requests, "get", lambda *args, **kwargs: Response())
    candidates = recommend_typecast_voices("food_vlog", limit=2)
    assert [item.voice_id for item in candidates] == ["tc_one", "tc_two"]
    assert candidates[0].preview_url.endswith("one.mp3")
    assert "쇼츠남" in candidates[0].label


def test_explicit_typecast_voice_skips_recommendation(monkeypatch):
    fake_settings = replace(
        settings,
        tts_provider="typecast",
        typecast_api_key="test-key",
        typecast_voice_id="",
    )
    monkeypatch.setattr(audio_module, "settings", fake_settings)

    service = AudioService("food_vlog", 1.0, voice_id="tc_manual")
    assert service._resolve_typecast_voice_id() == "tc_manual"



def test_browse_real_typecast_voices_prefers_shorts_use_cases(monkeypatch):
    import src.typecast_voices as voice_module
    from src.typecast_voices import browse_typecast_voices

    class Response:
        def raise_for_status(self):
            return None
        def json(self):
            return {
                "voices": [
                    {
                        "voice_id": "voice_a",
                        "voice_name": "일반 안내",
                        "use_cases": ["announcement"],
                        "models": [{"version": "ssfm-v30"}],
                    },
                    {
                        "voice_id": "voice_b",
                        "voice_name": "영상 리뷰",
                        "use_cases": ["video", "review"],
                        "preview_url": "https://example.com/b.mp3",
                        "models": [{"version": "ssfm-v30"}],
                    },
                ]
            }

    monkeypatch.setattr(voice_module.requests, "get", lambda *args, **kwargs: Response())
    voices = browse_typecast_voices(limit=10)
    assert [voice.voice_id for voice in voices] == ["voice_b", "voice_a"]
    assert voices[0].preview_url.endswith("b.mp3")


def test_browse_real_typecast_voices_filters_model(monkeypatch):
    import src.typecast_voices as voice_module
    from src.typecast_voices import browse_typecast_voices

    class Response:
        def raise_for_status(self):
            return None
        def json(self):
            return {
                "voices": [
                    {
                        "voice_id": "old_voice",
                        "voice_name": "구모델",
                        "models": [{"version": "ssfm-v21"}],
                    },
                    {
                        "voice_id": "new_voice",
                        "voice_name": "신모델",
                        "models": [{"version": "ssfm-v30"}],
                    },
                ]
            }

    monkeypatch.setattr(voice_module.requests, "get", lambda *args, **kwargs: Response())
    voices = browse_typecast_voices(limit=10)
    assert [voice.voice_id for voice in voices] == ["new_voice"]
