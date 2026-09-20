from __future__ import annotations

from dataclasses import dataclass

from config import settings
from src.typecast_voices import TypecastVoiceCandidate, browse_typecast_voices


@dataclass(frozen=True)
class VideoStyle:
    key: str
    label: str
    description: str
    preset: str


@dataclass(frozen=True)
class ServiceVoice:
    key: str
    label: str
    description: str
    gender: str
    preferred_age: str = ""


VIDEO_STYLES = {
    "food_review": VideoStyle(
        "food_review",
        "맛집 리뷰",
        "메뉴와 분위기를 빠르게 훑는 리뷰형",
        "food_vlog",
    ),
    "product_review": VideoStyle(
        "product_review",
        "제품 리뷰",
        "장점과 특징을 짧고 선명하게 전달",
        "food_vlog",
    ),
    "travel": VideoStyle(
        "travel",
        "여행·체험",
        "현장감과 분위기를 살리는 브이로그형",
        "bright",
    ),
    "information": VideoStyle(
        "information",
        "정보형",
        "핵심 정보를 차분하고 또렷하게 정리",
        "calm",
    ),
}


SERVICE_VOICES = {
    "bright_male": ServiceVoice(
        "bright_male",
        "밝은 남성",
        "빠르고 친근한 리뷰",
        "male",
        "young adult",
    ),
    "bright_female": ServiceVoice(
        "bright_female",
        "밝은 여성",
        "가볍고 생동감 있는 브이로그",
        "female",
        "young adult",
    ),
    "calm_male": ServiceVoice(
        "calm_male",
        "차분한 남성",
        "신뢰감 있는 정보형 리뷰",
        "male",
        "middle age",
    ),
    "calm_female": ServiceVoice(
        "calm_female",
        "차분한 여성",
        "편안하고 자연스러운 설명",
        "female",
        "middle age",
    ),
}


def selected_style(key: str) -> VideoStyle:
    if key not in VIDEO_STYLES:
        return VIDEO_STYLES["food_review"]
    return VIDEO_STYLES[key]


def selected_service_voice(key: str) -> ServiceVoice:
    if key not in SERVICE_VOICES:
        return SERVICE_VOICES["bright_male"]
    return SERVICE_VOICES[key]


def pick_typecast_voice(
    choice: ServiceVoice,
    voices: list[TypecastVoiceCandidate],
) -> TypecastVoiceCandidate | None:
    if not voices:
        return None

    gender = choice.gender.lower()
    preferred_age = choice.preferred_age.lower()

    tiers = [
        [
            voice for voice in voices
            if voice.gender.lower() == gender
            and voice.age.lower() == preferred_age
        ],
        [
            voice for voice in voices
            if voice.gender.lower() == gender
        ],
        [
            voice for voice in voices
            if preferred_age and voice.age.lower() == preferred_age
        ],
        voices,
    ]
    for candidates in tiers:
        if candidates:
            return candidates[0]
    return None


def resolve_service_voice(choice_key: str) -> tuple[str | None, str]:
    """Resolve a service-friendly voice choice to the current provider.

    The UI intentionally works with stable labels such as '밝은 남성'.
    Provider-specific IDs stay behind this boundary so Typecast can later be
    replaced by CLOVA without changing the main user flow.
    """
    choice = selected_service_voice(choice_key)

    if settings.tts_provider == "typecast":
        voices = browse_typecast_voices(limit=200)
        picked = pick_typecast_voice(choice, voices)
        if picked is None:
            raise RuntimeError("현재 음성 서비스에서 사용할 수 있는 보이스를 찾지 못했습니다.")
        return picked.voice_id, picked.name

    # Gemini/OpenAI currently do not require a runtime voice_id in the UI path.
    return None, choice.label
