from __future__ import annotations

from dataclasses import dataclass

import requests

from config import settings
from src.voices import selected_profile


USE_CASE_WEIGHTS = {
    "tiktok/reels/shorts": 120,
    "shorts": 110,
    "tiktok": 100,
    "reels": 100,
    "youtube": 95,
    "social": 90,
    "review": 85,
    "content": 75,
    "video": 70,
    "ads/promotion": 60,
    "conversational": 55,
    "game": 30,
    "radio/podcast": 15,
    "storytelling": 10,
}

AGE_WEIGHTS = {
    "young adult": 18,
    "teenager": 12,
    "middle age": 4,
}


@dataclass(frozen=True)
class TypecastVoiceCandidate:
    voice_id: str
    name: str
    gender: str = ""
    age: str = ""
    score: float | None = None
    preview_url: str = ""
    use_cases: tuple[str, ...] = ()
    models: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        details = [item for item in (self.gender, self.age) if item]
        if self.use_cases:
            details.append(", ".join(self.use_cases[:2]))
        meta = " · ".join(details)
        if self.score is not None:
            meta = f"{meta} · {self.score:.2f}" if meta else f"{self.score:.2f}"
        return f"{self.name}{' · ' + meta if meta else ''}"

    @property
    def shorts_score(self) -> int:
        """Suitability score for short-form video. This is not a popularity metric."""
        total = AGE_WEIGHTS.get(self.age.lower(), 0)
        if self.preview_url:
            total += 3
        for use_case in self.use_cases:
            normalized = use_case.lower().strip()
            total += USE_CASE_WEIGHTS.get(normalized, 0)
            if normalized not in USE_CASE_WEIGHTS:
                for keyword, weight in USE_CASE_WEIGHTS.items():
                    if keyword in normalized:
                        total += weight
                        break
        return total

    @property
    def shorts_tags(self) -> tuple[str, ...]:
        preferred = []
        for use_case in self.use_cases:
            lowered = use_case.lower()
            if any(
                token in lowered
                for token in ("short", "tiktok", "reels", "youtube", "review", "social", "ads", "conversational")
            ):
                preferred.append(use_case)
        if not preferred:
            preferred = list(self.use_cases[:2])
        return tuple(preferred[:3])


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


def _model_versions(item: dict) -> tuple[str, ...]:
    raw = item.get("models") or []
    versions: list[str] = []
    for model in raw:
        if isinstance(model, str):
            versions.append(model)
        elif isinstance(model, dict):
            version = model.get("version") or model.get("model")
            if version:
                versions.append(str(version))
    return tuple(versions)


def _candidate(item: dict) -> TypecastVoiceCandidate | None:
    voice_id = str(item.get("voice_id") or item.get("id") or "").strip()
    if not voice_id:
        return None
    name = str(
        item.get("voice_name")
        or item.get("name")
        or item.get("display_name")
        or voice_id
    ).strip()
    score = item.get("score")
    try:
        score = float(score) if score is not None else None
    except (TypeError, ValueError):
        score = None

    raw_use_cases = item.get("use_cases") or item.get("use_case") or []
    if isinstance(raw_use_cases, str):
        use_cases = (raw_use_cases,)
    else:
        use_cases = tuple(str(value) for value in raw_use_cases if value)

    return TypecastVoiceCandidate(
        voice_id=voice_id,
        name=name,
        gender=str(item.get("gender") or "").replace("_", " "),
        age=str(item.get("age") or item.get("age_group") or "").replace("_", " "),
        score=score,
        preview_url=str(item.get("preview_url") or item.get("sample_url") or ""),
        use_cases=use_cases,
        models=_model_versions(item),
    )


def _fetch_voice_list() -> list[dict]:
    """Prefer the current v3 endpoint, with v2 fallback for older accounts."""
    headers = {"X-API-KEY": settings.typecast_api_key}
    last_error: Exception | None = None
    for version in ("v3", "v2"):
        try:
            response = requests.get(
                f"{settings.typecast_api_base}/{version}/voices",
                headers=headers,
                params={"model": settings.typecast_model},
                timeout=(5, 25),
            )
            response.raise_for_status()
            return _candidate_list(response.json())
        except requests.RequestException as exc:
            last_error = exc
    if last_error:
        raise last_error
    return []


def browse_typecast_voices(
    search: str = "",
    gender: str = "",
    age: str = "",
    limit: int = 80,
) -> list[TypecastVoiceCandidate]:
    """Return voices actually exposed by the user's current Typecast API account."""
    search_norm = search.strip().lower()
    gender_norm = gender.strip().lower().replace("_", " ")
    age_norm = age.strip().lower().replace("_", " ")

    result: list[TypecastVoiceCandidate] = []
    seen: set[str] = set()
    for item in _fetch_voice_list():
        if not isinstance(item, dict):
            continue
        candidate = _candidate(item)
        if candidate is None or candidate.voice_id in seen:
            continue
        if candidate.models and settings.typecast_model not in candidate.models:
            continue
        if search_norm and search_norm not in candidate.name.lower() and all(
            search_norm not in use_case.lower() for use_case in candidate.use_cases
        ):
            continue
        if gender_norm and candidate.gender.lower() != gender_norm:
            continue
        if age_norm and candidate.age.lower() != age_norm:
            continue
        seen.add(candidate.voice_id)
        result.append(candidate)

    result.sort(key=lambda item: (-item.shorts_score, item.name.lower()))
    return result[:limit]


def top_shorts_voices(limit: int = 8) -> list[TypecastVoiceCandidate]:
    """Rank available API voices by Shorts suitability, not by undisclosed popularity."""
    voices = browse_typecast_voices(limit=200)
    ranked = [voice for voice in voices if voice.shorts_score > 0]
    return (ranked or voices)[:limit]


def recommend_typecast_voices(preset: str, limit: int = 5) -> list[TypecastVoiceCandidate]:
    _, profile = selected_profile(preset)
    response = requests.get(
        f"{settings.typecast_api_base}/v1/voices/recommendations",
        headers={"X-API-KEY": settings.typecast_api_key},
        params={"query": profile.typecast_query},
        timeout=(5, 20),
    )
    response.raise_for_status()

    raw_candidates: list[TypecastVoiceCandidate] = []
    for item in _candidate_list(response.json()):
        if isinstance(item, dict):
            candidate = _candidate(item)
            if candidate:
                raw_candidates.append(candidate)

    if not raw_candidates:
        raise RuntimeError("Typecast에서 추천 보이스 후보를 찾지 못했습니다.")
    return raw_candidates[:limit]
