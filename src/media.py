from __future__ import annotations

import io
import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests
from PIL import Image, ImageOps


def public_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("공개 HTTP 이미지 URL이 아닙니다.")
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("내부 네트워크 이미지 주소는 허용하지 않습니다.")
    return url


def normalize_image(data: bytes, destination: Path) -> Path:
    if len(data) > 10 * 1024 * 1024:
        raise ValueError("이미지 용량 제한 초과")
    with Image.open(io.BytesIO(data)) as image:
        if image.width * image.height > 24_000_000 or min(image.size) < 240:
            raise ValueError("너무 작거나 큰 이미지입니다.")
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
        image.save(destination, "JPEG", quality=93)
    return destination


def download_images(urls: list[str], folder: Path, referer: str, limit: int = 12) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)

    def download(pair):
        index, url = pair
        path = folder / f"{index:02d}.jpg"
        try:
            with requests.Session() as session:
                session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/152 Safari/537.36", "Referer": referer})
                for _ in range(4):
                    with session.get(public_url(url), timeout=(5, 10), allow_redirects=False, stream=True) as response:
                        if response.status_code in {301, 302, 303, 307, 308}:
                            url = urljoin(url, response.headers["Location"])
                            continue
                        response.raise_for_status()
                        parts = []
                        length = 0
                        for part in response.iter_content(65536):
                            length += len(part)
                            if length > 10 * 1024 * 1024:
                                raise ValueError("이미지 용량 제한 초과")
                            parts.append(part)
                        return normalize_image(b"".join(parts), path)
        except (requests.RequestException, ValueError, OSError, KeyError):
            path.unlink(missing_ok=True)
        return None

    # Bounded concurrency and candidates. Preserve source order after validation.
    candidates = list(enumerate(dict.fromkeys(urls)))[:max(limit, 18)]
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(download, candidates))
    return [p for p in results if p is not None][:limit]
