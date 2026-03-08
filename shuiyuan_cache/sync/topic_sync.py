from datetime import datetime, timezone

from shuiyuan_cache.core.config import CacheConfig
from shuiyuan_cache.core.models import SyncResult, SyncStateRecord
from shuiyuan_cache.fetch.session import ShuiyuanSession
from shuiyuan_cache.fetch.sync_planner import SyncPlanner
from shuiyuan_cache.fetch.topic_fetcher import TopicFetcher
from shuiyuan_cache.normalize.media_normalizer import MediaNormalizer
from shuiyuan_cache.normalize.post_normalizer import PostNormalizer
from shuiyuan_cache.store.media_store import MediaStore
from shuiyuan_cache.store.paths import CachePaths
from shuiyuan_cache.store.raw_store import RawStore
from shuiyuan_cache.store.sqlite_store import SQLiteStore


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

    def close(self) -> None:
        self.sqlite_store.close()

    def sync_topic(
        self,
        topic: str | int,
        mode: str = "incremental",
        with_images: bool = True,
        force: bool = False,
    ) -> SyncResult:
        started_at = self._now_iso()
        topic_id = self.fetcher.resolve_topic_id(topic)
        topic_payload = self.fetcher.fetch_topic_meta(topic_id)
        topic_json_path = self.raw_store.save_topic_json(topic_id, topic_payload)
        topic_record = self.post_normalizer.normalize_topic(
            topic_id, topic_payload, str(topic_json_path)
        )
        self.sqlite_store.upsert_topic(topic_record)

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

        inserted_posts = 0
        updated_posts = 0
        inserted_media = 0
        updated_media = 0
        downloaded_images = 0
        skipped_images = 0
        errors: list[str] = []

        for page_no in plan.json_pages_to_fetch:
            try:
                page_payload = self.fetcher.fetch_topic_json_page(topic_id, page_no)
                self.raw_store.save_json_page(topic_id, page_no, page_payload)
                posts, media_records = self.post_normalizer.normalize_posts(
                    topic_id, page_no, page_payload
                )
                page_inserted, page_updated = self.sqlite_store.upsert_posts(posts)
                inserted_posts += page_inserted
                updated_posts += page_updated
                if plan.should_download_images:
                    media_records, page_downloaded, page_skipped, media_errors = (
                        self.media_store.download_images(media_records)
                    )
                    downloaded_images += page_downloaded
                    skipped_images += page_skipped
                    errors.extend(media_errors)
                media_inserted, media_updated = self.sqlite_store.upsert_media(
                    media_records
                )
                inserted_media += media_inserted
                updated_media += media_updated
            except Exception as exc:
                errors.append(f"json page {page_no} failed: {exc}")

        for page_no in plan.raw_pages_to_fetch:
            try:
                raw_text = self.fetcher.fetch_topic_raw_page(topic_id, page_no)
                self.raw_store.save_raw_page(topic_id, page_no, raw_text)
            except Exception as exc:
                errors.append(f"raw page {page_no} failed: {exc}")

        finished_at = self._now_iso()
        sync_state = SyncStateRecord(
            topic_id=topic_id,
            last_known_posts_count=topic_record.posts_count,
            last_known_last_posted_at=topic_record.last_posted_at,
            last_synced_json_page=plan.current_json_pages,
            last_synced_raw_page=plan.current_raw_pages,
            last_synced_post_number=topic_record.posts_count,
            last_sync_mode=plan.mode,
            last_sync_status="partial"
            if errors
            else ("unchanged" if plan.skip_reason else "success"),
            last_sync_started_at=started_at,
            last_sync_finished_at=finished_at,
            last_sync_error="\n".join(errors) if errors else plan.skip_reason,
        )
        self.raw_store.save_sync_state(sync_state)
        self.sqlite_store.upsert_sync_state(sync_state)

        return SyncResult(
            topic_id=topic_id,
            title=topic_record.title,
            mode=plan.mode,
            fetched_json_pages=len(plan.json_pages_to_fetch),
            fetched_raw_pages=len(plan.raw_pages_to_fetch),
            fetched_post_raw_count=0,
            inserted_posts=inserted_posts,
            updated_posts=updated_posts,
            inserted_media=inserted_media,
            updated_media=updated_media,
            downloaded_images=downloaded_images,
            skipped_images=skipped_images,
            status=sync_state.last_sync_status,
            errors=errors,
        )

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
