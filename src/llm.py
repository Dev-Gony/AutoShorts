from __future__ import annotations

import json

from google import genai
from google.genai import types
from openai import OpenAI

from config import settings
from src.models import BlogContent, ShortScript


class ScriptGenerationError(RuntimeError):
    pass


class ScriptGenerator:
    def __init__(self) -> None:
        self.provider = settings.ai_provider

        if self.provider == "gemini":
            self.gemini = genai.Client(api_key=settings.gemini_api_key)
            self.openai = None
        elif self.provider == "openai":
            self.openai = OpenAI(api_key=settings.openai_api_key)
            self.gemini = None
        else:
            raise ValueError(f"지원하지 않는 AI_PROVIDER: {self.provider}")

    def _generate_text(self, prompt: str, json_mode: bool = False) -> str:
        if self.provider == "gemini":
            config = None
            if json_mode:
                config = types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            response = self.gemini.models.generate_content(
                model=settings.gemini_script_model,
                contents=prompt,
                config=config,
            )
            return (response.text or "").strip()

        response = self.openai.responses.create(
            model=settings.openai_script_model,
            input=prompt,
        )
        return response.output_text.strip()

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
        raw = self._generate_text(prompt, json_mode=True)

        if raw.startswith("~~~json"):
            raw = raw[7:]
        if raw.endswith("~~~"):
            raw = raw[:-3]
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.endswith("```"):
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
            raise ScriptGenerationError(
                f"대본이 최대 길이를 초과했습니다: {len(script)}자"
            )

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
        script = self._generate_text(prompt, json_mode=False).strip()
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
