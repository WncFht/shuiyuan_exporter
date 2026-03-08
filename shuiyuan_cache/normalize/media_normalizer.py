import hashlib
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from shuiyuan_cache.core.config import CacheConfig
from shuiyuan_cache.core.models import MediaRecord


class MediaNormalizer:
    def __init__(self, config: CacheConfig):
        self.config = config

    def normalize_images(self, topic_id: int, post_id: int, post_number: int, cooked_html: str) -> list[MediaRecord]:
        soup = BeautifulSoup(cooked_html or "", "html.parser")
        records: list[MediaRecord] = []
        for image in soup.find_all("img"):
            src = image.get("src") or ""
            resolved_url = self._absolute_url(src)
            upload_ref = image.get("data-orig-src")
            media_key = image.get("data-base62-sha1") or self._fallback_media_key(resolved_url)
            file_ext = self._guess_extension(resolved_url)
            records.append(
                MediaRecord(
                    topic_id=topic_id,
                    post_id=post_id,
                    post_number=post_number,
                    media_type="image",
                    upload_ref=upload_ref,
                    resolved_url=resolved_url,
                    local_path=None,
                    mime_type=None,
                    file_ext=file_ext,
                    media_key=media_key,
                    download_status="pending",
                )
            )
        return records

    def _absolute_url(self, url: str) -> str:
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return f"{self.config.base_url.rstrip('/')}{url}"

    @staticmethod
    def _fallback_media_key(url: str) -> str:
        return hashlib.sha1(url.encode("utf-8")).hexdigest()

    @staticmethod
    def _guess_extension(url: str) -> str:
        path = urlparse(url).path
        if "." not in path:
            return ".img"
        return "." + path.rsplit(".", 1)[-1]
