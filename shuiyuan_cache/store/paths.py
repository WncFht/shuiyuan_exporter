from pathlib import Path

from shuiyuan_cache.core.config import CacheConfig


class CachePaths:
    def __init__(self, config: CacheConfig):
        self.config = config

    @property
    def root(self) -> Path:
        return self.config.cache_root

    def topic_root(self, topic_id: int) -> Path:
        return self.root / "raw" / "topics" / str(topic_id)

    def topic_json_path(self, topic_id: int) -> Path:
        return self.topic_root(topic_id) / "topic.json"

    def sync_state_path(self, topic_id: int) -> Path:
        return self.topic_root(topic_id) / "sync_state.json"

    def json_pages_dir(self, topic_id: int) -> Path:
        return self.topic_root(topic_id) / "pages" / "json"

    def raw_pages_dir(self, topic_id: int) -> Path:
        return self.topic_root(topic_id) / "pages" / "raw"

    def post_ref_dir(self, topic_id: int) -> Path:
        return self.root / "raw" / "post_refs" / str(topic_id)

    def json_page_path(self, topic_id: int, page_no: int) -> Path:
        return self.json_pages_dir(topic_id) / f"{page_no:04d}.json"

    def raw_page_path(self, topic_id: int, page_no: int) -> Path:
        return self.raw_pages_dir(topic_id) / f"{page_no:04d}.md"

    def post_raw_path(self, topic_id: int, post_number: int) -> Path:
        return self.post_ref_dir(topic_id) / f"{post_number:06d}.raw.md"

    def image_path(self, media_key: str, ext: str) -> Path:
        bucket = (media_key[:2] or "xx").lower()
        ext = ext if ext.startswith(".") else f".{ext}"
        return self.root / "media" / "images" / bucket / f"{media_key}{ext}"

    def ensure_parent(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def ensure_root(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.config.db_path.parent.mkdir(parents=True, exist_ok=True)
