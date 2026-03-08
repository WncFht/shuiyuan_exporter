from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import local
from typing import Any

from shuiyuan_cache.core.config import CacheConfig
from shuiyuan_cache.core.models import SyncPlan, SyncResult, SyncStateRecord
from shuiyuan_cache.core.exceptions import RateLimitError
from shuiyuan_cache.core.progress import ProgressCallback
from shuiyuan_cache.fetch.session import ShuiyuanSession
from shuiyuan_cache.fetch.sync_planner import SyncPlanner
from shuiyuan_cache.fetch.topic_fetcher import TopicFetcher
from shuiyuan_cache.normalize.media_normalizer import MediaNormalizer
from shuiyuan_cache.normalize.post_normalizer import PostNormalizer
from shuiyuan_cache.store.media_store import MediaStore
from shuiyuan_cache.store.paths import CachePaths
from shuiyuan_cache.store.raw_store import RawStore
from shuiyuan_cache.store.sqlite_store import SQLiteStore


@dataclass(slots=True)
class _PageFetchResult:
    page_no: int
    payload: Any | None
    error: str | None = None
    rate_limited: bool = False


class TopicSyncService:
    def __init__(self, config: CacheConfig):
        self.config = config
        self.paths = CachePaths(config)
        self.raw_store = RawStore(self.paths)
        self.sqlite_store = SQLiteStore(config.db_path)
        self.session = ShuiyuanSession(config)
        self.fetcher = TopicFetcher(config, self.session)
        self.media_normalizer = MediaNormalizer(config)
        self.post_normalizer = PostNormalizer(self.media_normalizer)
        self.media_store = MediaStore(self.paths, self.session)
        self.sync_planner = SyncPlanner(config)
        self._worker_local = local()

    def close(self) -> None:
        self.sqlite_store.close()

    def sync_topic(
        self,
        topic: str | int,
        mode: str = "incremental",
        with_images: bool = True,
        force: bool = False,
        progress_callback: ProgressCallback | None = None,
    ) -> SyncResult:
        started_at = self._now_iso()
        self._emit_progress(progress_callback, f"resolving topic target: {topic}")
        topic_id = self.fetcher.resolve_topic_id(topic)
        self._emit_progress(
            progress_callback, f"resolved topic #{topic_id}; fetching topic metadata"
        )
        topic_payload = self.fetcher.fetch_topic_meta(topic_id)
        topic_json_path = self.raw_store.save_topic_json(topic_id, topic_payload)
        topic_record = self.post_normalizer.normalize_topic(
            topic_id, topic_payload, str(topic_json_path)
        )
        self.sqlite_store.upsert_topic(topic_record)
        self._emit_progress(
            progress_callback,
            f"topic #{topic_id}: {topic_record.title} ({topic_record.posts_count} posts)",
        )

        existing_state = self.sqlite_store.get_sync_state(
            topic_id
        ) or self.raw_store.load_sync_state(topic_id)
        plan = self.sync_planner.build_plan(
            topic_record,
            existing_state,
            mode=mode,
            force=force,
            with_images=with_images,
        )
        self._emit_progress(progress_callback, self._format_plan(plan))
        if plan.skip_reason:
            self._emit_progress(
                progress_callback, f"skipping fetch: {plan.skip_reason}"
            )

        inserted_posts = 0
        updated_posts = 0
        inserted_media = 0
        updated_media = 0
        downloaded_images = 0
        skipped_images = 0
        errors: list[str] = []

        json_total = len(plan.json_pages_to_fetch)
        if json_total:
            self._emit_progress(
                progress_callback,
                f"json fetch stage: pages={json_total}, workers={self._page_fetch_workers(json_total)}",
            )
        for index, (page_no, page_payload, page_error) in enumerate(
            self._iter_json_page_payloads(
                topic_id,
                plan.json_pages_to_fetch,
                progress_callback=progress_callback,
            ),
            start=1,
        ):
            self._emit_progress(
                progress_callback,
                f"json {index}/{json_total}: fetched page {page_no}",
            )
            if page_error:
                errors.append(f"json page {page_no} failed: {page_error}")
                self._emit_progress(
                    progress_callback,
                    f"json {index}/{json_total} page {page_no}: failed: {page_error}",
                )
                continue
            try:
                self.raw_store.save_json_page(topic_id, page_no, page_payload)
                posts, media_records = self.post_normalizer.normalize_posts(
                    topic_id, page_no, page_payload
                )
                page_inserted, page_updated = self.sqlite_store.upsert_posts(posts)
                inserted_posts += page_inserted
                updated_posts += page_updated
                image_candidates = self._count_image_candidates(media_records)
                page_downloaded = 0
                page_skipped = 0
                media_errors: list[str] = []
                if plan.should_download_images and image_candidates:
                    media_records, page_downloaded, page_skipped, media_errors = (
                        self.media_store.download_images(
                            media_records,
                            progress_callback=self._build_page_progress_callback(
                                progress_callback,
                                index,
                                json_total,
                                page_no,
                            ),
                        )
                    )
                    downloaded_images += page_downloaded
                    skipped_images += page_skipped
                    errors.extend(media_errors)
                page_media_inserted, page_media_updated = (
                    self.sqlite_store.upsert_media(media_records)
                )
                inserted_media += page_media_inserted
                updated_media += page_media_updated
                self._emit_progress(
                    progress_callback,
                    "json "
                    f"{index}/{json_total} "
                    f"page {page_no}: "
                    f"posts +{page_inserted} updated {page_updated}, "
                    f"media +{page_media_inserted} updated {page_media_updated}, "
                    f"image_candidates={image_candidates}, "
                    f"downloaded={page_downloaded}, skipped={page_skipped}",
                )
            except Exception as exc:
                errors.append(f"json page {page_no} failed: {exc}")
                self._emit_progress(
                    progress_callback,
                    f"json {index}/{json_total} page {page_no}: failed: {exc}",
                )

        raw_total = len(plan.raw_pages_to_fetch)
        if raw_total:
            self._emit_progress(
                progress_callback,
                f"raw fetch stage: pages={raw_total}, workers={self._page_fetch_workers(raw_total)}",
            )
        for index, (page_no, raw_text, page_error) in enumerate(
            self._iter_raw_page_payloads(
                topic_id,
                plan.raw_pages_to_fetch,
                progress_callback=progress_callback,
            ),
            start=1,
        ):
            if page_error:
                errors.append(f"raw page {page_no} failed: {page_error}")
                self._emit_progress(
                    progress_callback,
                    f"raw {index}/{raw_total} page {page_no}: failed: {page_error}",
                )
                continue
            try:
                self.raw_store.save_raw_page(topic_id, page_no, raw_text)
                self._emit_progress(
                    progress_callback,
                    f"raw {index}/{raw_total} page {page_no}: saved",
                )
            except Exception as exc:
                errors.append(f"raw page {page_no} failed: {exc}")
                self._emit_progress(
                    progress_callback,
                    f"raw {index}/{raw_total} page {page_no}: failed: {exc}",
                )

        finished_at = self._now_iso()
        status = (
            "partial" if errors else ("unchanged" if plan.skip_reason else "success")
        )
        sync_state = SyncStateRecord(
            topic_id=topic_id,
            last_known_posts_count=topic_record.posts_count,
            last_known_last_posted_at=topic_record.last_posted_at,
            last_synced_json_page=plan.current_json_pages,
            last_synced_raw_page=plan.current_raw_pages,
            last_synced_post_number=topic_record.posts_count,
            last_sync_mode=plan.mode,
            last_sync_status=status,
            last_sync_started_at=started_at,
            last_sync_finished_at=finished_at,
            last_sync_error="\n".join(errors) if errors else plan.skip_reason,
        )
        self.raw_store.save_sync_state(sync_state)
        self.sqlite_store.upsert_sync_state(sync_state)
        self._emit_progress(
            progress_callback,
            "sync finished: "
            f"status={status}, "
            f"json_pages={json_total}, "
            f"raw_pages={raw_total}, "
            f"posts +{inserted_posts} updated {updated_posts}, "
            f"media +{inserted_media} updated {updated_media}, "
            f"images downloaded={downloaded_images} skipped={skipped_images}, "
            f"errors={len(errors)}",
        )

        return SyncResult(
            topic_id=topic_id,
            title=topic_record.title,
            mode=plan.mode,
            fetched_json_pages=json_total,
            fetched_raw_pages=raw_total,
            fetched_post_raw_count=0,
            inserted_posts=inserted_posts,
            updated_posts=updated_posts,
            inserted_media=inserted_media,
            updated_media=updated_media,
            downloaded_images=downloaded_images,
            skipped_images=skipped_images,
            status=status,
            errors=errors,
        )

    def _iter_json_page_payloads(
        self,
        topic_id: int,
        page_numbers: list[int],
        progress_callback: ProgressCallback | None = None,
    ):
        if not page_numbers:
            return

        retry_page_numbers: list[int] = []
        max_workers = self._page_fetch_workers(len(page_numbers))
        if max_workers == 1:
            iterator = (
                self._fetch_json_page_task(topic_id, page_no)
                for page_no in page_numbers
            )
            for result in iterator:
                if result.rate_limited:
                    retry_page_numbers.append(result.page_no)
                    self._emit_progress(
                        progress_callback,
                        f"json page {result.page_no}: rate limited; scheduling sequential retry",
                    )
                    continue
                yield result.page_no, result.payload, result.error
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for result in executor.map(
                    lambda page_no: self._fetch_json_page_task(topic_id, page_no),
                    page_numbers,
                ):
                    if result.rate_limited:
                        retry_page_numbers.append(result.page_no)
                        self._emit_progress(
                            progress_callback,
                            f"json page {result.page_no}: rate limited; scheduling sequential retry",
                        )
                        continue
                    yield result.page_no, result.payload, result.error

        if retry_page_numbers:
            self._emit_progress(
                progress_callback,
                f"json cooldown retry stage: pages={len(retry_page_numbers)}, workers=1",
            )
            for page_no in retry_page_numbers:
                result = self._fetch_json_page_task(topic_id, page_no)
                yield result.page_no, result.payload, result.error

    def _iter_raw_page_payloads(
        self,
        topic_id: int,
        page_numbers: list[int],
        progress_callback: ProgressCallback | None = None,
    ):
        if not page_numbers:
            return

        retry_page_numbers: list[int] = []
        max_workers = self._page_fetch_workers(len(page_numbers))
        if max_workers == 1:
            iterator = (
                self._fetch_raw_page_task(topic_id, page_no) for page_no in page_numbers
            )
            for result in iterator:
                if result.rate_limited:
                    retry_page_numbers.append(result.page_no)
                    self._emit_progress(
                        progress_callback,
                        f"raw page {result.page_no}: rate limited; scheduling sequential retry",
                    )
                    continue
                yield result.page_no, result.payload, result.error
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for result in executor.map(
                    lambda page_no: self._fetch_raw_page_task(topic_id, page_no),
                    page_numbers,
                ):
                    if result.rate_limited:
                        retry_page_numbers.append(result.page_no)
                        self._emit_progress(
                            progress_callback,
                            f"raw page {result.page_no}: rate limited; scheduling sequential retry",
                        )
                        continue
                    yield result.page_no, result.payload, result.error

        if retry_page_numbers:
            self._emit_progress(
                progress_callback,
                f"raw cooldown retry stage: pages={len(retry_page_numbers)}, workers=1",
            )
            for page_no in retry_page_numbers:
                result = self._fetch_raw_page_task(topic_id, page_no)
                yield result.page_no, result.payload, result.error

    def _fetch_json_page_task(
        self,
        topic_id: int,
        page_no: int,
    ) -> _PageFetchResult:
        try:
            payload = self._get_worker_fetcher().fetch_topic_json_page(
                topic_id, page_no
            )
            return _PageFetchResult(page_no=page_no, payload=payload)
        except RateLimitError as exc:
            return _PageFetchResult(
                page_no=page_no,
                payload=None,
                error=str(exc),
                rate_limited=True,
            )
        except Exception as exc:
            return _PageFetchResult(page_no=page_no, payload=None, error=str(exc))

    def _fetch_raw_page_task(
        self,
        topic_id: int,
        page_no: int,
    ) -> _PageFetchResult:
        try:
            payload = self._get_worker_fetcher().fetch_topic_raw_page(topic_id, page_no)
            return _PageFetchResult(page_no=page_no, payload=payload)
        except RateLimitError as exc:
            return _PageFetchResult(
                page_no=page_no,
                payload=None,
                error=str(exc),
                rate_limited=True,
            )
        except Exception as exc:
            return _PageFetchResult(page_no=page_no, payload=None, error=str(exc))

    def _get_worker_fetcher(self) -> TopicFetcher:
        worker_fetcher = getattr(self._worker_local, "fetcher", None)
        if worker_fetcher is None:
            worker_session = ShuiyuanSession(self.config)
            worker_fetcher = TopicFetcher(self.config, worker_session)
            self._worker_local.fetcher = worker_fetcher
        return worker_fetcher

    def _page_fetch_workers(self, page_count: int) -> int:
        return min(max(self.config.page_fetch_workers, 1), max(page_count, 1))

    @staticmethod
    def _count_image_candidates(media_records) -> int:
        return sum(
            1
            for media in media_records
            if media.media_type == "image"
            and media.resolved_url
            and media.media_key
            and media.file_ext
        )

    def _format_plan(self, plan: SyncPlan) -> str:
        return (
            "sync plan: "
            f"mode={plan.mode}, "
            f"json={self._format_page_selection(plan.json_pages_to_fetch, plan.current_json_pages)}, "
            f"raw={self._format_page_selection(plan.raw_pages_to_fetch, plan.current_raw_pages)}, "
            f"images={'on' if plan.should_download_images else 'off'}, "
            f"page_workers={max(self.config.page_fetch_workers, 1)}, "
            f"image_workers={max(self.config.image_download_workers, 1)}"
        )

    @staticmethod
    def _format_page_selection(pages: list[int], total_pages: int) -> str:
        if not pages:
            return f"0/{total_pages}"
        if len(pages) == 1:
            return f"{pages[0]} (1/{total_pages})"
        return f"{pages[0]}-{pages[-1]} ({len(pages)}/{total_pages})"

    @staticmethod
    def _build_page_progress_callback(
        progress_callback: ProgressCallback | None,
        index: int,
        total: int,
        page_no: int,
    ) -> ProgressCallback | None:
        if progress_callback is None:
            return None

        def page_progress(message: str) -> None:
            progress_callback(f"json {index}/{total} page {page_no}: {message}")

        return page_progress

    @staticmethod
    def _emit_progress(
        progress_callback: ProgressCallback | None,
        message: str,
    ) -> None:
        if progress_callback is not None:
            progress_callback(message)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
