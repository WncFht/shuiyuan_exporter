from pathlib import Path

from shuiyuan_cache.core.config import CacheConfig
from shuiyuan_cache.core.models import TopicInspectResult
from shuiyuan_cache.fetch.topic_fetcher import TopicFetcher
from shuiyuan_cache.store.paths import CachePaths
from shuiyuan_cache.store.sqlite_store import SQLiteStore


MEDIA_IDENTITY_SQL = "COALESCE(NULLIF(upload_ref, ''), NULLIF(media_key, ''), NULLIF(resolved_url, ''), printf('media:%d', media_id))"


class TopicInspectService:
    def __init__(self, config: CacheConfig):
        self.config = config
        self.paths = CachePaths(config)
        self.sqlite_store = SQLiteStore(config.db_path)

    def close(self) -> None:
        self.sqlite_store.close()

    def inspect_topic(self, topic: str | int) -> TopicInspectResult:
        topic_id = TopicFetcher.resolve_topic_id(topic)
        conn = self.sqlite_store.conn
        topic_row = conn.execute("SELECT * FROM topics WHERE topic_id = ?", (topic_id,)).fetchone()
        sync_row = conn.execute("SELECT * FROM sync_state WHERE topic_id = ?", (topic_id,)).fetchone()
        db_post_count = conn.execute("SELECT COUNT(*) FROM posts WHERE topic_id = ?", (topic_id,)).fetchone()[0]
        media_image_count = conn.execute(
            f"SELECT COUNT(DISTINCT {MEDIA_IDENTITY_SQL}) FROM media WHERE topic_id = ? AND media_type = 'image'",
            (topic_id,),
        ).fetchone()[0]
        image_file_count = conn.execute(
            """
            SELECT COUNT(DISTINCT local_path)
            FROM media
            WHERE topic_id = ?
              AND media_type = 'image'
              AND local_path IS NOT NULL
              AND download_status IN ('downloaded', 'skipped')
            """,
            (topic_id,),
        ).fetchone()[0]

        topic_root = self.paths.topic_root(topic_id)
        json_page_count = self._count_files(self.paths.json_pages_dir(topic_id), '*.json')
        raw_page_count = self._count_files(self.paths.raw_pages_dir(topic_id), '*.md')

        issues: list[str] = []
        if not self.paths.topic_json_path(topic_id).exists():
            issues.append('missing topic.json')
        if not self.paths.sync_state_path(topic_id).exists():
            issues.append('missing sync_state.json')
        if topic_row is None:
            issues.append('topic not found in sqlite')
        if db_post_count == 0:
            issues.append('no posts found in sqlite')
        if topic_row is not None and topic_row['posts_count'] and db_post_count < topic_row['posts_count']:
            issues.append('db post count seems lower than expected')
        if json_page_count == 0:
            issues.append('no cached json pages')
        if raw_page_count == 0:
            issues.append('no cached raw pages')

        return TopicInspectResult(
            topic_id=topic_id,
            title=topic_row['title'] if topic_row else None,
            topic_posts_count=topic_row['posts_count'] if topic_row else 0,
            db_post_count=db_post_count,
            json_page_count=json_page_count,
            raw_page_count=raw_page_count,
            media_image_count=media_image_count,
            image_file_count=image_file_count,
            last_posted_at=topic_row['last_posted_at'] if topic_row else None,
            last_sync_status=sync_row['last_sync_status'] if sync_row else None,
            last_sync_mode=sync_row['last_sync_mode'] if sync_row else None,
            last_sync_finished_at=sync_row['last_sync_finished_at'] if sync_row else None,
            cache_path=str(topic_root),
            issues=issues,
        )

    @staticmethod
    def _count_files(path: Path, pattern: str) -> int:
        if not path.exists():
            return 0
        return sum(1 for _ in path.glob(pattern))
