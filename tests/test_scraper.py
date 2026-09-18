import pytest

from src.scraper.base import ContentExtractionError, validate_url
from src.scraper.generic import GenericScraper

def test_validate_url_accepts_http():
    assert validate_url("https://example.com/post") == "https://example.com/post"

def test_validate_url_rejects_invalid_value():
    with pytest.raises(ValueError):
        validate_url("not-a-url")

def test_generic_parser_extracts_article():
    html = """
    <html>
      <head><title>테스트 글</title></head>
      <body>
        <nav>상단전용네비게이션텍스트</nav>
        <article>
          <p>이것은 테스트 본문입니다. 충분한 길이를 확보하기 위해 문장을 반복합니다.</p>
          <p>AutoShorts 스크래퍼가 광고나 메뉴 대신 본문을 선택해야 합니다.</p>
          <p>마지막 문장까지 포함하여 백 자가 넘는 본문을 구성합니다. 영상 대본의 원재료가 됩니다.</p>
        </article>
      </body>
    </html>
    """
    result = GenericScraper(min_chars=50).parse_html("https://example.com/post", html)
    assert result.title == "테스트 글"
    assert "AutoShorts" in result.text
    assert "상단전용네비게이션텍스트" not in result.text

def test_short_content_is_rejected():
    html = "<html><body><article>짧음</article></body></html>"
    with pytest.raises(ContentExtractionError):
        GenericScraper(min_chars=100).parse_html("https://example.com", html)
