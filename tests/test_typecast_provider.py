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


def test_top_shorts_voices_ranks_shortform_use_cases(monkeypatch):
    import src.typecast_voices as voice_module
    from src.typecast_voices import top_shorts_voices

    class Response:
        def raise_for_status(self):
            return None
        def json(self):
            return {
                "voices": [
                    {
                        "voice_id": "voice_story",
                        "voice_name": "Story",
                        "age": "young_adult",
                        "use_cases": ["Audiobook", "Storytelling"],
                        "models": [{"version": "ssfm-v30"}],
                    },
                    {
                        "voice_id": "voice_shorts",
                        "voice_name": "Shorts",
                        "age": "young_adult",
                        "use_cases": ["TikTok/Reels/Shorts", "Conversational"],
                        "models": [{"version": "ssfm-v30"}],
                    },
                    {
                        "voice_id": "voice_review",
                        "voice_name": "Review",
                        "age": "middle_age",
                        "use_cases": ["Review", "Video"],
                        "models": [{"version": "ssfm-v30"}],
                    },
                ]
            }

    monkeypatch.setattr(voice_module.requests, "get", lambda *args, **kwargs: Response())
    voices = top_shorts_voices(limit=3)
    assert [voice.voice_id for voice in voices] == [
        "voice_shorts",
        "voice_review",
        "voice_story",
    ]


def test_shorts_score_is_suitability_not_api_popularity():
    from src.typecast_voices import TypecastVoiceCandidate

    voice = TypecastVoiceCandidate(
        voice_id="v1",
        name="Example",
        age="young adult",
        use_cases=("TikTok/Reels/Shorts", "Conversational"),
    )
    assert voice.shorts_score > 0
    assert "TikTok/Reels/Shorts" in voice.shorts_tags


def test_localized_typecast_name_prefers_korean():
    from src.typecast_voices import _candidate

    candidate = _candidate({
        "voice_id": "voice_1",
        "voice_name": {"eng": "Dylan", "kor": "딜런"},
        "gender": "male",
        "age": "young_adult",
        "use_cases": [{"eng": "TikTok/Reels/Shorts", "kor": "틱톡/릴스/쇼츠"}],
    })
    assert candidate is not None
    assert candidate.name == "딜런"
    assert candidate.use_cases == ("틱톡/릴스/쇼츠",)


def test_localized_typecast_name_falls_back_to_english():
    from src.typecast_voices import _candidate

    candidate = _candidate({
        "voice_id": "voice_2",
        "voice_name": {"eng": "Walter"},
    })
    assert candidate is not None
    assert candidate.name == "Walter"


def test_top_korean_shorts_voices_uses_korean_native_query(monkeypatch):
    import src.typecast_voices as voice_module
    from src.typecast_voices import top_korean_shorts_voices

    calls = []

    class Response:
        def __init__(self, payload):
            self.payload = payload
        def raise_for_status(self):
            return None
        def json(self):
            return self.payload

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        if "/recommendations" in url:
            return Response([
                {"voice_id": "ko_voice", "voice_name": {"kor": "한국쇼츠"}, "score": 0.99}
            ])
        return Response({
            "voices": [
                {
                    "voice_id": "ko_voice",
                    "voice_name": {"kor": "한국쇼츠"},
                    "gender": "male",
                    "age": "young_adult",
                    "use_cases": [{"kor": "틱톡/릴스/쇼츠"}],
                    "models": [{"version": "ssfm-v30"}],
                }
            ]
        })

    monkeypatch.setattr(voice_module.requests, "get", fake_get)
    voices = top_korean_shorts_voices("food_vlog", limit=1)

    recommendation = next(call for call in calls if "/recommendations" in call[0])
    query = recommendation[1]["params"]["query"]
    assert "한국어 원어민" in query
    assert "외국인 억양" in query
    assert voices[0].name == "한국쇼츠"
