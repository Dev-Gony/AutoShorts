from __future__ import annotations

from urllib.parse import urlparse
from config import settings
from src.scraper.base import BaseScraper, validate_url
from src.scraper.generic import GenericScraper
from src.scraper.naver import NaverScraper
from src.scraper.tistory import TistoryScraper

def get_scraper(url: str) -> BaseScraper:
    url = validate_url(url)
    host = urlparse(url).netloc.lower()
    kwargs = {
        "min_chars": settings.min_source_chars,
        "timeout": settings.request_timeout_seconds,
    }

    if host == "blog.naver.com" or host.endswith(".blog.naver.com"):
        return NaverScraper(**kwargs)
    if host.endswith("tistory.com"):
        return TistoryScraper(**kwargs)
    return GenericScraper(**kwargs)
