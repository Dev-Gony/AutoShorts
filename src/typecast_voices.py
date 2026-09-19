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


def _candidate_list(payload) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("recommendations", "voices", "results", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            for inner in ("items", "voices", "results"):
                nested = value.get(inner)
                if isinstance(nested, list):
                    return nested
    return []


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
        voice_id = str(item.get("voice_id") or item.get("id") or "").strip()
        if not voice_id or voice_id in seen:
            continue
        seen.add(voice_id)
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
        result.append(TypecastVoiceCandidate(
            voice_id=voice_id,
            name=name,
            gender=str(item.get("gender") or "").replace("_", " "),
            age=str(item.get("age") or "").replace("_", " "),
            score=score,
            preview_url=str(item.get("preview_url") or item.get("sample_url") or ""),
        ))
        if len(result) >= limit:
            break

    if not result:
        raise RuntimeError("Typecast에서 추천 보이스 후보를 찾지 못했습니다.")
    return result
