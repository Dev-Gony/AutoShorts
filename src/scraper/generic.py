from __future__ import annotations

from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from src.models import BlogContent
from src.scraper.base import BaseScraper, ContentExtractionError, validate_url

class GenericScraper(BaseScraper):
    ARTICLE_SELECTORS = ("article","main",".entry-content",".post-content",".article-content",".article-view",".contents_style","#content")
    REMOVE_SELECTORS = ("script","style","noscript","nav","header","footer","aside","form","button",".advertisement",".ads")

    def __init__(self, min_chars: int = 100, timeout: int = 20) -> None:
        super().__init__(min_chars=min_chars)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/152 Safari/537.36"})

    def fetch_html(self, url: str) -> str:
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        if response.apparent_encoding:
            response.encoding = response.apparent_encoding
        return response.text

    def parse_html(self, url: str, html: str, source: str = "generic") -> BlogContent:
        soup = BeautifulSoup(html, "html.parser")
        for selector in self.REMOVE_SELECTORS:
            for node in soup.select(selector):
                node.decompose()
        title = self._extract_title(soup)
        text = self._extract_main_text(soup)
        images = self._extract_images(soup, url)
        return self.validate_content(BlogContent(url=url, source=source, title=title, text=text, images=images))

    def extract(self, url: str) -> BlogContent:
        url = validate_url(url)
        return self.parse_html(url, self.fetch_html(url))

    def _extract_main_text(self, soup: BeautifulSoup) -> str:
        candidates = []
        for selector in self.ARTICLE_SELECTORS:
            for node in soup.select(selector):
                text = node.get_text("\n", strip=True)
                if text:
                    candidates.append(text)
        if not candidates and soup.body:
            candidates.append(soup.body.get_text("\n", strip=True))
        if not candidates:
            raise ContentExtractionError("본문 후보 영역을 찾지 못했습니다.")
        return max(candidates, key=len)

    @staticmethod
    def _extract_title(soup: BeautifulSoup) -> str:
        for selector in ("h1","meta[property='og:title']","title"):
            node = soup.select_one(selector)
            if not node:
                continue
            value = node.get("content","") if node.name == "meta" else node.get_text(" ", strip=True)
            if value:
                return value
        return "Untitled"

    @staticmethod
    def _extract_images(soup: BeautifulSoup, base_url: str) -> list[str]:
        results, seen = [], set()
        for img in soup.select("img"):
            raw = img.get("data-lazy-src") or img.get("data-src") or img.get("src") or ""
            if not raw or raw.startswith("data:"):
                continue
            absolute = urljoin(base_url, raw)
            if absolute not in seen:
                seen.add(absolute)
                results.append(absolute)
        return results
