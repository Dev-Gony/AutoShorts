from __future__ import annotations

import json
from openai import OpenAI
from config import settings
from src.models import BlogContent, ShortScript

class ScriptGenerationError(RuntimeError):
    pass

class ScriptGenerator:
    def __init__(self, client: OpenAI | None = None) -> None:
        self.client = client or OpenAI(api_key=settings.openai_api_key)

    def generate(self, content: BlogContent) -> ShortScript:
        prompt = f"""당신은 한국어 숏폼 영상 전문 작가입니다.
아래 블로그 글을 45~58초 분량의 자연스러운 구어체 대본으로 재구성하세요.

규칙:
- 첫 문장은 강한 훅
- 원문에 없는 사실은 만들지 말 것
- 핵심 경험과 정보 중심
- 과장 광고 문구 금지
- script는 권장 280~380자, 절대 최대 {settings.max_script_chars}자
- 반드시 JSON만 출력
- 필드: title, hook, script, hashtags
- hashtags는 최대 5개

제목: {content.title}
본문:
{content.text[:12000]}
"""
        response = self.client.responses.create(model=settings.script_model, input=prompt)
        raw = response.output_text.strip()
        if raw.startswith("~~~json"):
            raw = raw[7:]
        if raw.endswith("~~~"):
            raw = raw[:-3]
        raw = raw.strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ScriptGenerationError(f"LLM JSON 파싱 실패: {raw[:300]}") from exc

        script = str(data.get("script", "")).strip()
        if not script:
            raise ScriptGenerationError("생성된 대본이 비어 있습니다.")
        if len(script) > settings.max_script_chars:
            raise ScriptGenerationError(f"대본이 최대 길이를 초과했습니다: {len(script)}자")

        return ShortScript(
            title=str(data.get("title", content.title)).strip(),
            hook=str(data.get("hook", "")).strip(),
            script=script,
            hashtags=[str(x) for x in data.get("hashtags", [])][:5],
        )

    def shorten(self, item: ShortScript, target_chars: int = 300) -> ShortScript:
        prompt = f"""아래 한국어 숏폼 대본의 사실관계와 핵심 내용은 유지하면서
약 {target_chars}자 분량으로 더 짧고 빠르게 말할 수 있게 다듬으세요.

규칙:
- 새로운 사실 추가 금지
- 훅 유지
- 자연스러운 구어체
- 결과는 대본 본문만 출력
- {settings.max_script_chars}자를 절대 넘지 말 것

대본:
{item.script}
"""
        response = self.client.responses.create(model=settings.script_model, input=prompt)
        script = response.output_text.strip()
        if not script:
            raise ScriptGenerationError("축약 대본이 비어 있습니다.")
        if len(script) > settings.max_script_chars:
            script = script[: settings.max_script_chars].rstrip()

        return ShortScript(
            title=item.title,
            hook=item.hook,
            script=script,
            hashtags=item.hashtags,
        )
