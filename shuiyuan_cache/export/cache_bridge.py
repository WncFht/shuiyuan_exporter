import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from collections.abc import Iterator
from threading import local

from shuiyuan_cache.core.config import CacheConfig
from shuiyuan_cache.fetch.session import ShuiyuanSession
from shuiyuan_cache.fetch.topic_fetcher import TopicFetcher
from shuiyuan_cache.store.paths import CachePaths
from shuiyuan_cache.store.raw_store import RawStore


class ExportCacheBridge:
    def __init__(
        self, cache_root: str | Path = "cache", cookie_path: str | Path = "cookies.txt"
    ):
        self.config = CacheConfig(
            cache_root=Path(cache_root), cookie_path=Path(cookie_path)
        )
        self.paths = CachePaths(self.config)
        self.raw_store = RawStore(self.paths)
        self.session = ShuiyuanSession(self.config)
        self.fetcher = TopicFetcher(self.config, self.session)
        self._worker_local = local()

    def resolve_topic_id(self, topic: str | int) -> int:
        return TopicFetcher.resolve_topic_id(topic)

    def load_topic_meta(self, topic: str | int) -> dict:
        topic_id = self.resolve_topic_id(topic)
        topic_json_path = self.paths.topic_json_path(topic_id)
        if topic_json_path.exists():
            return json.loads(topic_json_path.read_text(encoding="utf-8"))
        payload = self.fetcher.fetch_topic_meta(topic_id)
        self.raw_store.save_topic_json(topic_id, payload)
        return payload

    def iter_json_pages(self, topic: str | int) -> Iterator[tuple[int, dict]]:
        topic_id = self.resolve_topic_id(topic)
        payload = self.load_topic_meta(topic_id)
        total_pages = TopicFetcher.page_count(
            payload.get("posts_count") or 0, self.config.json_page_size
        )
        for page_no in range(1, total_pages + 1):
            json_page_path = self.paths.json_page_path(topic_id, page_no)
            if json_page_path.exists():
                yield page_no, json.loads(json_page_path.read_text(encoding="utf-8"))
                continue
            page_payload = self.fetcher.fetch_topic_json_page(topic_id, page_no)
            self.raw_store.save_json_page(topic_id, page_no, page_payload)
            yield page_no, page_payload

    def iter_json_posts(self, topic: str | int) -> Iterator[dict]:
        for _, payload in self.iter_json_pages(topic):
            yield from payload.get("post_stream", {}).get("posts", [])

    def iter_raw_pages(self, topic: str | int) -> Iterator[tuple[int, str]]:
        topic_id = self.resolve_topic_id(topic)
        payload = self.load_topic_meta(topic_id)
        total_pages = TopicFetcher.page_count(
            payload.get("posts_count") or 0, self.config.raw_page_size
        )
        for page_no in range(1, total_pages + 1):
            raw_page_path = self.paths.raw_page_path(topic_id, page_no)
            if raw_page_path.exists():
                yield page_no, raw_page_path.read_text(encoding="utf-8")
                continue
            raw_text = self.fetcher.fetch_topic_raw_page(topic_id, page_no)
            self.raw_store.save_raw_page(topic_id, page_no, raw_text)
            yield page_no, raw_text

    def get_post_raw(self, topic: str | int, post_number: int) -> str:
        topic_id = self.resolve_topic_id(topic)
        post_raw_path = self.paths.post_raw_path(topic_id, post_number)
        if post_raw_path.exists():
            return post_raw_path.read_text(encoding="utf-8")
        raw_text = self.fetcher.fetch_post_raw(topic_id, post_number)
        self.raw_store.save_post_raw(topic_id, post_number, raw_text)
        return raw_text

    def ensure_output_image(
        self, media_key: str, file_ext: str, resolved_url: str, output_dir: str | Path
    ) -> Path:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{media_key}{self._normalize_ext(file_ext)}"
        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path

        cache_image_path = self.paths.image_path(
            media_key, self._normalize_ext(file_ext)
        )
        if cache_image_path.exists() and cache_image_path.stat().st_size > 0:
            shutil.copyfile(cache_image_path, output_path)
            return output_path

        response = self.session.get_binary(self.session.absolute_url(resolved_url))
        cache_image_path = self.paths.ensure_parent(cache_image_path)
        with open(cache_image_path, "wb") as cache_file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    cache_file.write(chunk)
        shutil.copyfile(cache_image_path, output_path)
        return output_path

    def ensure_output_images(
        self,
        tasks: list[tuple[str, str, str]],
        output_dir: str | Path,
    ) -> None:
        if not tasks:
            return
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        max_workers = min(
            max(self.config.export_image_workers, 1),
            len(tasks),
        )
        if max_workers == 1:
            for task in tasks:
                self._ensure_output_image_task(task, output_dir)
            return
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            list(
                executor.map(
                    lambda task: self._ensure_output_image_task(task, output_dir), tasks
                )
            )

    def _ensure_output_image_task(
        self,
        task: tuple[str, str, str],
        output_dir: Path,
    ) -> Path:
        media_key, file_ext, resolved_url = task
        normalized_ext = self._normalize_ext(file_ext)
        output_path = output_dir / f"{media_key}{normalized_ext}"
        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path

        cache_image_path = self.paths.ensure_parent(
            self.paths.image_path(media_key, normalized_ext)
        )
        if cache_image_path.exists() and cache_image_path.stat().st_size > 0:
            shutil.copyfile(cache_image_path, output_path)
            return output_path

        session = self._get_worker_session()
        response = session.get_binary(session.absolute_url(resolved_url))
        with open(cache_image_path, "wb") as cache_file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    cache_file.write(chunk)
        shutil.copyfile(cache_image_path, output_path)
        return output_path

    def _get_worker_session(self) -> ShuiyuanSession:
        worker_session = getattr(self._worker_local, "session", None)
        if worker_session is None:
            worker_session = ShuiyuanSession(self.config)
            self._worker_local.session = worker_session
        return worker_session

    @staticmethod
    def _normalize_ext(file_ext: str) -> str:
        return file_ext if file_ext.startswith(".") else f".{file_ext}"


@lru_cache(maxsize=1)
def get_export_cache_bridge(
    cache_root: str = "cache", cookie_path: str = "cookies.txt"
) -> ExportCacheBridge:
    return ExportCacheBridge(cache_root=cache_root, cookie_path=cookie_path)
