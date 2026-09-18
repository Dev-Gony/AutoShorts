from __future__ import annotations

import re
from abc import ABC, abstractmethod
from urllib.parse import urlparse

from src.models import BlogContent

class ContentExtractionError(RuntimeError):
    pass

def validate_url(url: str) -> str:
    value = url.strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("http 또는 https 형식의 유효한 URL을 입력하세요.")
    return value

class BaseScraper(ABC):
    def __init__(self, min_chars: int = 100) -> None:
        self.min_chars = min_chars

    @abstractmethod
    def extract(self, url: str) -> BlogContent:
        raise NotImplementedError

    def validate_content(self, content: BlogContent) -> BlogContent:
        content.text = self.clean_text(content.text)
        if len(content.text) < self.min_chars:
            raise ContentExtractionError(f"본문 추출 결과가 너무 짧습니다: {len(content.text)}자")
        return content

    @staticmethod
    def clean_text(text: str) -> str:
        text = text.replace("\u200b", " ").replace("\xa0", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
