from __future__ import annotations

from dataclasses import dataclass

import requests

from config import settings
from src.voices import selected_profile


SHORTS_KEYWORDS = (
    "short", "youtube", "tiktok", "social", "content",
    "video", "review", "entertainment", "vlog",
)


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
        haystack = " ".join(self.use_cases).lower()
        return sum(1 for keyword in SHORTS_KEYWORDS if keyword in haystack)


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


def browse_typecast_voices(
    search: str = "",
    gender: str = "",
    age: str = "",
    limit: int = 40,
) -> list[TypecastVoiceCandidate]:
    """Return voices actually exposed by the user's current Typecast API account."""
    response = requests.get(
        f"{settings.typecast_api_base}/v2/voices",
        headers={"X-API-KEY": settings.typecast_api_key},
        params={"model": settings.typecast_model},
        timeout=(5, 25),
    )
    response.raise_for_status()

    search_norm = search.strip().lower()
    gender_norm = gender.strip().lower().replace("_", " ")
    age_norm = age.strip().lower().replace("_", " ")

    result: list[TypecastVoiceCandidate] = []
    seen: set[str] = set()
    for item in _candidate_list(response.json()):
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

    # Surface content/video-oriented voices first, then keep stable name ordering.
    result.sort(key=lambda item: (-item.shorts_score, item.name.lower()))
    return result[:limit]


def recommend_typecast_voices(preset: str, limit: int = 5) -> list[TypecastVoiceCandidate]:
    """Use recommendations, then verify each candidate against V2 voice details."""
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

    verified: list[TypecastVoiceCandidate] = []
    for candidate in raw_candidates[:limit]:
        try:
            detail = requests.get(
                f"{settings.typecast_api_base}/v2/voices/{candidate.voice_id}",
                headers={"X-API-KEY": settings.typecast_api_key},
                timeout=(5, 15),
            )
            detail.raise_for_status()
            payload = detail.json()
            if isinstance(payload, dict):
                enriched = _candidate(payload) or candidate
            else:
                enriched = candidate
            verified.append(TypecastVoiceCandidate(
                voice_id=enriched.voice_id,
                name=enriched.name,
                gender=enriched.gender,
                age=enriched.age,
                score=candidate.score,
                preview_url=enriched.preview_url,
                use_cases=enriched.use_cases,
                models=enriched.models,
            ))
        except requests.RequestException:
            # Recommendation remains usable for TTS, but metadata may be sparse.
            verified.append(candidate)

    if not verified:
        raise RuntimeError("Typecast에서 추천 보이스 후보를 찾지 못했습니다.")
    return verified
