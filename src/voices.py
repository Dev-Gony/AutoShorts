from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceProfile:
    label: str
    voice: str
    direction: str


PROFILES = {
    "food_vlog": VoiceProfile(
        "맛집·체험 리뷰 / 경쾌한 대화", "Puck",
        "친구에게 방금 찾은 맛집을 소개하는 한국어 크리에이터. 가볍게 미소 짓는 목소리로, "
        "궁금한 첫 문장과 구체적인 특징에 억양 변화를 주세요. 과장하거나 소리 지르지 마세요.",
    ),
    "bright": VoiceProfile(
        "브이로그 / 밝고 편안한 대화", "Aoede",
        "일상을 공유하는 한국어 브이로거. 밝고 편안하게 옆 사람에게 말하듯, "
        "짧은 호흡과 자연스러운 문장 연결을 사용하세요. 광고 성우처럼 연기하지 마세요.",
    ),
    "calm": VoiceProfile(
        "정보·리뷰 / 따뜻하고 차분하게", "Sulafat",
        "한국어로 중요한 정보를 따뜻하게 설명하는 진행자. 차분하지만 단조롭지 않게, "
        "중요한 단어만 살짝 강조하며 자연스럽게 대화하세요.",
    ),
}


def selected_profile(name: str | None = None) -> tuple[str, VoiceProfile]:
    name = name or os.getenv("VOICE_PRESET", "food_vlog").strip()
    if name not in PROFILES:
        raise ValueError("VOICE_PRESET은 food_vlog, bright, calm 중 하나여야 합니다.")
    return name, PROFILES[name]


def speech_direction(profile: VoiceProfile, emphasis: str = "") -> str:
    note = f"강조할 표현: {emphasis}." if emphasis else ""
    return (
        f"# AUDIO PROFILE\n{profile.direction}\n"
        "# DIRECTOR'S NOTES\n표준 한국어로 말하세요. 뉴스·국어책 낭독체가 아니라 실제 대화의 리듬을 사용하세요. "
        "보통 대화보다 조금 경쾌하게, 단어마다 끊지 말고 의미 덩어리로 연결하세요. "
        "문장 끝을 모두 같은 높이로 떨어뜨리지 마세요. 숫자·가격·고유명사는 명확하게 읽으세요. "
        "웃음·감탄사·배경음·인사말을 임의로 추가하지 마세요. "
        f"{note} 아래 TRANSCRIPT만 정확히 말하고 지시문은 읽지 마세요.\n"
    )
