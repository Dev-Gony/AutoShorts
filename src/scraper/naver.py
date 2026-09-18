from __future__ import annotations

from urllib.parse import urljoin
from bs4 import BeautifulSoup
from src.models import BlogContent
from src.scraper.base import ContentExtractionError, validate_url
from src.scraper.generic import GenericScraper

class NaverScraper(GenericScraper):
    BODY_SELECTORS = (".se-main-container", "#postViewArea", ".post-view", ".se_component_wrap")
    TITLE_SELECTORS = (".se-title-text", ".pcol1 .htitle", ".tit_h3", "meta[property='og:title']", "title")

    def extract(self, url: str) -> BlogContent:
        url = validate_url(url)
        soup = BeautifulSoup(self.fetch_html(url), "html.parser")
        iframe = soup.select_one("iframe#mainFrame")

        if iframe and iframe.get("src"):
            resolved_url = urljoin(url, iframe["src"])
            soup = BeautifulSoup(self.fetch_html(resolved_url), "html.parser")
        else:
            resolved_url = url

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
            raise ContentExtractionError("네이버 블로그 본문 영역을 찾지 못했습니다.")

        title = "Untitled"
        for selector in self.TITLE_SELECTORS:
            node = soup.select_one(selector)
            if not node:
                continue
            title = node.get("content", "") if node.name == "meta" else node.get_text(" ", strip=True)
            if title:
                break

        return self.validate_content(BlogContent(
            url=url,
            source="naver",
            title=title,
            text=body.get_text("\n", strip=True),
            images=self._extract_images(body, resolved_url),
        ))
