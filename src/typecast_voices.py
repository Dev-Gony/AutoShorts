from __future__ import annotations

from dataclasses import dataclass

import requests

from config import settings
from src.voices import selected_profile


@dataclass(frozen=True)
class TypecastVoiceCandidate:
    voice_id: str
    name: str
    gender: str = ""
    age: str = ""
    score: float | None = None
    preview_url: str = ""

    @property
    def label(self) -> str:
        details = [item for item in (self.gender, self.age) if item]
        meta = " · ".join(details)
        if self.score is not None:
            meta = f"{meta} · {self.score:.2f}" if meta else f"{self.score:.2f}"
        return f"{self.name}{' · ' + meta if meta else ''}"


@dataclass(frozen=True)
class PopularShortsVoice:
    name: str
    note: str
    source_note: str
    recommended_speed: float = 1.10


POPULAR_SHORTS_VOICES = {
    "박창수": PopularShortsVoice(
        "박창수",
        "충청도 청년 캐릭터. 음식·리뷰·유머 숏폼 쪽을 먼저 비교할 때 가장 우선.",
        "Typecast 공식 콘텐츠에서 요리·유머·리뷰 채널 활용 사례가 소개됨.",
        1.10,
    ),
    "발키리": PopularShortsVoice(
        "발키리",
        "강한 리액션과 밈 느낌. 차분한 리뷰보다 텐션 높은 쇼츠에 적합.",
        "Typecast 공식 콘텐츠에서 유튜브·릴스·틱톡에서 유행한 분노 TTS로 소개됨.",
        1.08,
    ),
    "찬구": PopularShortsVoice(
        "찬구",
        "밈·캐릭터성이 강한 타입. 정보 전달보다 개성 있는 숏폼에 우선 비교.",
        "Typecast 공식 콘텐츠에서 대표 캐릭터 및 유행 밈 사례로 소개됨.",
        1.10,
    ),
    "채린이": PopularShortsVoice(
        "채린이",
        "밝고 캐릭터성 있는 톤을 찾을 때 비교.",
        "Typecast 공식 콘텐츠에서 유튜브·틱톡·릴스 활용 캐릭터로 언급됨.",
        1.08,
    ),
    "호빈이": PopularShortsVoice(
        "호빈이",
        "가볍고 캐릭터성 있는 숏폼 톤 비교용.",
        "Typecast 공식 콘텐츠에서 유튜브·틱톡·릴스 활용 캐릭터로 언급됨.",
        1.10,
    ),
    "미스터 변사": PopularShortsVoice(
        "미스터 변사",
        "과장된 이야기 전달·상황 설명처럼 캐릭터성이 필요한 영상에 비교.",
        "Typecast 공식 콘텐츠에서 개성 있는 TTS 캐릭터로 언급됨.",
        1.06,
    ),
    "덕춘 할배": PopularShortsVoice(
        "덕춘 할배",
        "할아버지 캐릭터 톤. 밈이나 상황극형 쇼츠에 비교.",
        "Typecast 공식 콘텐츠에서 개성 있는 TTS 캐릭터로 언급됨.",
        1.08,
    ),
    "용식": PopularShortsVoice(
        "용식",
        "경상도 사투리 숏폼용으로 비교.",
        "Typecast 공식 릴스 더빙 사투리 TOP3에 포함됨.",
        1.10,
    ),
    "곽두필": PopularShortsVoice(
        "곽두필",
        "전라도 사투리 숏폼용으로 비교.",
        "Typecast 공식 릴스 더빙 사투리 TOP3에 포함됨.",
        1.10,
    ),
}


def _candidate_list(payload) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("recommendations", "voices", "results", "data", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            for inner in ("items", "voices", "results", "data"):
                nested = value.get(inner)
                if isinstance(nested, list):
                    return nested
    return []


def _candidate(item: dict) -> TypecastVoiceCandidate | None:
    voice_id = str(item.get("voice_id") or item.get("id") or "").strip()
    if not voice_id:
        return None
    name = str(
        item.get("voice_name")
        or item.get("name")
        or item.get("display_name")
        or item.get("character_name")
        or voice_id
    ).strip()
    score = item.get("score")
    try:
        score = float(score) if score is not None else None
    except (TypeError, ValueError):
        score = None
    return TypecastVoiceCandidate(
        voice_id=voice_id,
        name=name,
        gender=str(item.get("gender") or "").replace("_", " "),
        age=str(item.get("age") or "").replace("_", " "),
        score=score,
        preview_url=str(item.get("preview_url") or item.get("sample_url") or ""),
    )


def _normalize_name(value: str) -> str:
    return "".join(value.lower().split()).replace("-", "").replace("_", "")


def _find_exact(items: list[dict], name: str) -> TypecastVoiceCandidate | None:
    wanted = _normalize_name(name)
    for item in items:
        if not isinstance(item, dict):
            continue
        candidate = _candidate(item)
        if candidate and _normalize_name(candidate.name) == wanted:
            return candidate
    return None


def resolve_popular_typecast_voice(name: str) -> TypecastVoiceCandidate:
    if name not in POPULAR_SHORTS_VOICES:
        raise ValueError(f"지원하지 않는 인기 쇼츠 보이스: {name}")

    headers = {"X-API-KEY": settings.typecast_api_key}

    # 1) The official voice-list endpoint is the safest way to identify a named
    # character because we only accept an exact name match.
    try:
        response = requests.get(
            f"{settings.typecast_api_base}/v3/voices",
            headers=headers,
            params={"model": settings.typecast_model},
            timeout=(5, 20),
        )
        response.raise_for_status()
        exact = _find_exact(_candidate_list(response.json()), name)
        if exact:
            return exact
    except requests.RequestException:
        # Fall through to recommendations; the UI will still fail closed if
        # Typecast cannot return the exact named character.
        pass

    # 2) Recommendation search helps when the list endpoint is paginated and the
    # named character is not on the first page. Never silently substitute a
    # different character.
    response = requests.get(
        f"{settings.typecast_api_base}/v1/voices/recommendations",
        headers=headers,
        params={
            "query": (
                f"타입캐스트 공식 캐릭터 이름이 정확히 '{name}'인 한국어 보이스. "
                "다른 캐릭터가 아니라 이 이름의 캐릭터를 찾아주세요."
            )
        },
        timeout=(5, 20),
    )
    response.raise_for_status()
    exact = _find_exact(_candidate_list(response.json()), name)
    if exact:
        return exact

    raise RuntimeError(
        f"현재 Typecast API에서 '{name}' 캐릭터의 정확한 voice_id를 확인하지 못했습니다. "
        "해당 캐릭터가 현재 API 모델/계정에서 제공되는지 확인해주세요."
    )


def recommend_typecast_voices(preset: str, limit: int = 5) -> list[TypecastVoiceCandidate]:
    _, profile = selected_profile(preset)
    response = requests.get(
        f"{settings.typecast_api_base}/v1/voices/recommendations",
        headers={"X-API-KEY": settings.typecast_api_key},
        params={"query": profile.typecast_query},
        timeout=(5, 20),
    )
    response.raise_for_status()

    result: list[TypecastVoiceCandidate] = []
    seen: set[str] = set()
    for item in _candidate_list(response.json()):
        if not isinstance(item, dict):
            continue
        candidate = _candidate(item)
        if candidate is None or candidate.voice_id in seen:
            continue
        seen.add(candidate.voice_id)
        result.append(candidate)
        if len(result) >= limit:
            break

    if not result:
        raise RuntimeError("Typecast에서 추천 보이스 후보를 찾지 못했습니다.")
    return result
