from __future__ import annotations

from bs4 import BeautifulSoup
from src.models import BlogContent
from src.scraper.base import ContentExtractionError, validate_url
from src.scraper.generic import GenericScraper

class TistoryScraper(GenericScraper):
    BODY_SELECTORS = (".contents_style", ".entry-content", ".article-view", ".tt_article_useless_p_margin", "article")

    def extract(self, url: str) -> BlogContent:
        url = validate_url(url)
        soup = BeautifulSoup(self.fetch_html(url), "html.parser")

        for selector in self.REMOVE_SELECTORS:
            for node in soup.select(selector):
                node.decompose()

        body = None
        for selector in self.BODY_SELECTORS:
            node = soup.select_one(selector)
            if node and node.get_text(strip=True):
                body = node
                break

        if body is None:
            raise ContentExtractionError("티스토리 본문 영역을 찾지 못했습니다.")

        return self.validate_content(BlogContent(
            url=url,
            source="tistory",
            title=self._extract_title(soup),
            text=body.get_text("\n", strip=True),
            images=self._extract_images(body, url),
        ))
