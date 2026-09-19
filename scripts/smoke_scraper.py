from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scraper import get_scraper


def main() -> int:
    if len(sys.argv) != 2:
        print("사용법: python scripts/smoke_scraper.py <BLOG_URL>")
        return 2

    url = sys.argv[1]
    try:
        content = get_scraper(url).extract(url)
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 1

    print("OK")
    print(f"source={content.source}")
    print(f"title={content.title}")
    print(f"text_chars={len(content.text)}")
    print(f"images={len(content.images)}")
    print("--- preview ---")
    print(content.text[:500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
