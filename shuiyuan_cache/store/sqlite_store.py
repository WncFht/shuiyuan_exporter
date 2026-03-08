import sqlite3
import time
from pathlib import Path
from typing import Iterable, Optional

from shuiyuan_cache.core.models import MediaRecord, PostRecord, SyncStateRecord, TopicRecord


SCHEMA = """
CREATE TABLE IF NOT EXISTS topics (
  topic_id INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  category_id INTEGER,
  tags_json TEXT,
  created_at TEXT,
  last_posted_at TEXT,
  posts_count INTEGER,
  reply_count INTEGER,
  views INTEGER,
  like_count INTEGER,
  visible INTEGER,
  archived INTEGER,
  closed INTEGER,
  topic_json_path TEXT,
  created_ts INTEGER NOT NULL,
  updated_ts INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS posts (
  post_id INTEGER PRIMARY KEY,
  topic_id INTEGER NOT NULL,
  post_number INTEGER NOT NULL,
  username TEXT,
  display_name TEXT,
  created_at TEXT,
  updated_at TEXT,
  reply_to_post_number INTEGER,
  is_op INTEGER DEFAULT 0,
  like_count INTEGER DEFAULT 0,
  raw_markdown TEXT,
  cooked_html TEXT,
  plain_text TEXT,
  raw_page_no INTEGER,
  json_page_no INTEGER,
  raw_post_path TEXT,
  has_images INTEGER DEFAULT 0,
  has_attachments INTEGER DEFAULT 0,
  has_audio INTEGER DEFAULT 0,
  has_video INTEGER DEFAULT 0,
  image_count INTEGER DEFAULT 0,
  hash_raw TEXT,
  hash_cooked TEXT,
  created_ts INTEGER NOT NULL,
  updated_ts INTEGER NOT NULL,
  UNIQUE(topic_id, post_number)
);

CREATE TABLE IF NOT EXISTS media (
  media_id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic_id INTEGER NOT NULL,
  post_id INTEGER,
  post_number INTEGER,
  media_type TEXT NOT NULL,
  upload_ref TEXT,
  resolved_url TEXT,
  local_path TEXT,
  mime_type TEXT,
  file_ext TEXT,
  media_key TEXT,
  download_status TEXT,
  content_length INTEGER,
  created_ts INTEGER NOT NULL,
  updated_ts INTEGER NOT NULL,
  UNIQUE(topic_id, post_number, media_type, upload_ref)
);

CREATE TABLE IF NOT EXISTS post_quotes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic_id INTEGER NOT NULL,
  post_id INTEGER NOT NULL,
  post_number INTEGER NOT NULL,
  quoted_topic_id INTEGER,
  quoted_post_number INTEGER,
  quote_url TEXT,
  created_ts INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_state (
  topic_id INTEGER PRIMARY KEY,
  last_known_posts_count INTEGER,
  last_known_last_posted_at TEXT,
  last_synced_json_page INTEGER,
  last_synced_raw_page INTEGER,
  last_synced_post_number INTEGER,
  last_sync_mode TEXT,
  last_sync_status TEXT,
  last_sync_started_at TEXT,
  last_sync_finished_at TEXT,
  last_sync_error TEXT,
  updated_ts INTEGER NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(
  topic_id UNINDEXED,
  post_id UNINDEXED,
  post_number UNINDEXED,
  username,
  plain_text,
  raw_markdown
);
"""


class SQLiteStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.ensure_schema()

    def close(self) -> None:
        self.conn.close()

    def ensure_schema(self) -> None:
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def get_sync_state(self, topic_id: int) -> Optional[SyncStateRecord]:
        row = self.conn.execute("SELECT * FROM sync_state WHERE topic_id = ?", (topic_id,)).fetchone()
        if row is None:
            return None
        data = dict(row)
        data.pop("updated_ts", None)
        return SyncStateRecord(**data)

    def upsert_topic(self, topic: TopicRecord) -> None:
        now_ts = int(time.time())
        self.conn.execute(
            """
            INSERT INTO topics (
              topic_id, title, category_id, tags_json, created_at, last_posted_at,
              posts_count, reply_count, views, like_count, visible, archived, closed,
              topic_json_path, created_ts, updated_ts
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(topic_id) DO UPDATE SET
              title=excluded.title,
              category_id=excluded.category_id,
              tags_json=excluded.tags_json,
              created_at=excluded.created_at,
              last_posted_at=excluded.last_posted_at,
              posts_count=excluded.posts_count,
              reply_count=excluded.reply_count,
              views=excluded.views,
              like_count=excluded.like_count,
              visible=excluded.visible,
              archived=excluded.archived,
              closed=excluded.closed,
              topic_json_path=excluded.topic_json_path,
              updated_ts=excluded.updated_ts
            """,
            (
                topic.topic_id,
                topic.title,
                topic.category_id,
                topic.tags_json,
                topic.created_at,
                topic.last_posted_at,
                topic.posts_count,
                topic.reply_count,
                topic.views,
                topic.like_count,
                int(topic.visible) if topic.visible is not None else None,
                int(topic.archived) if topic.archived is not None else None,
                int(topic.closed) if topic.closed is not None else None,
                topic.topic_json_path,
                now_ts,
                now_ts,
            ),
        )
        self.conn.commit()

    def upsert_posts(self, posts: Iterable[PostRecord]) -> tuple[int, int]:
        posts = list(posts)
        if not posts:
            return 0, 0
        existing_rows = self.conn.execute(
            f"SELECT post_id FROM posts WHERE post_id IN ({','.join(['?'] * len(posts))})",
            [post.post_id for post in posts],
        ).fetchall()
        existing_ids = {row[0] for row in existing_rows}
        now_ts = int(time.time())
        for post in posts:
            self.conn.execute(
                """
                INSERT INTO posts (
                  post_id, topic_id, post_number, username, display_name, created_at,
                  updated_at, reply_to_post_number, is_op, like_count, raw_markdown,
                  cooked_html, plain_text, raw_page_no, json_page_no, raw_post_path,
                  has_images, has_attachments, has_audio, has_video, image_count,
                  hash_raw, hash_cooked, created_ts, updated_ts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(post_id) DO UPDATE SET
                  topic_id=excluded.topic_id,
                  post_number=excluded.post_number,
                  username=excluded.username,
                  display_name=excluded.display_name,
                  created_at=excluded.created_at,
                  updated_at=excluded.updated_at,
                  reply_to_post_number=excluded.reply_to_post_number,
                  is_op=excluded.is_op,
                  like_count=excluded.like_count,
                  raw_markdown=excluded.raw_markdown,
                  cooked_html=excluded.cooked_html,
                  plain_text=excluded.plain_text,
                  raw_page_no=excluded.raw_page_no,
                  json_page_no=excluded.json_page_no,
                  raw_post_path=excluded.raw_post_path,
                  has_images=excluded.has_images,
                  has_attachments=excluded.has_attachments,
                  has_audio=excluded.has_audio,
                  has_video=excluded.has_video,
                  image_count=excluded.image_count,
                  hash_raw=excluded.hash_raw,
                  hash_cooked=excluded.hash_cooked,
                  updated_ts=excluded.updated_ts
                """,
                (
                    post.post_id,
                    post.topic_id,
                    post.post_number,
                    post.username,
                    post.display_name,
                    post.created_at,
                    post.updated_at,
                    post.reply_to_post_number,
                    int(post.is_op),
                    post.like_count,
                    post.raw_markdown,
                    post.cooked_html,
                    post.plain_text,
                    post.raw_page_no,
                    post.json_page_no,
                    post.raw_post_path,
                    int(post.has_images),
                    int(post.has_attachments),
                    int(post.has_audio),
                    int(post.has_video),
                    post.image_count,
                    post.hash_raw,
                    post.hash_cooked,
                    now_ts,
                    now_ts,
                ),
            )
        self.conn.commit()
        self.refresh_fts(posts)
        inserted = sum(1 for post in posts if post.post_id not in existing_ids)
        updated = len(posts) - inserted
        return inserted, updated

    def refresh_fts(self, posts: Iterable[PostRecord]) -> None:
        for post in posts:
            self.conn.execute("DELETE FROM posts_fts WHERE post_id = ?", (post.post_id,))
            self.conn.execute(
                "INSERT INTO posts_fts (topic_id, post_id, post_number, username, plain_text, raw_markdown) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    post.topic_id,
                    post.post_id,
                    post.post_number,
                    post.username,
                    post.plain_text,
                    post.raw_markdown,
                ),
            )
        self.conn.commit()

    def upsert_media(self, media_records: Iterable[MediaRecord]) -> tuple[int, int]:
        media_records = list(media_records)
        if not media_records:
            return 0, 0
        inserted = 0
        updated = 0
        now_ts = int(time.time())
        for media in media_records:
            row = self.conn.execute(
                "SELECT media_id FROM media WHERE topic_id = ? AND post_number = ? AND media_type = ? AND upload_ref IS ?",
                (media.topic_id, media.post_number, media.media_type, media.upload_ref),
            ).fetchone()
            self.conn.execute(
                """
                INSERT INTO media (
                  topic_id, post_id, post_number, media_type, upload_ref, resolved_url,
                  local_path, mime_type, file_ext, media_key, download_status, content_length,
                  created_ts, updated_ts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(topic_id, post_number, media_type, upload_ref) DO UPDATE SET
                  resolved_url=excluded.resolved_url,
                  local_path=excluded.local_path,
                  mime_type=excluded.mime_type,
                  file_ext=excluded.file_ext,
                  media_key=excluded.media_key,
                  download_status=excluded.download_status,
                  content_length=excluded.content_length,
                  updated_ts=excluded.updated_ts
                """,
                (
                    media.topic_id,
                    media.post_id,
                    media.post_number,
                    media.media_type,
                    media.upload_ref,
                    media.resolved_url,
                    media.local_path,
                    media.mime_type,
                    media.file_ext,
                    media.media_key,
                    media.download_status,
                    media.content_length,
                    now_ts,
                    now_ts,
                ),
            )
            if row is None:
                inserted += 1
            else:
                updated += 1
        self.conn.commit()
        return inserted, updated

    def upsert_sync_state(self, state: SyncStateRecord) -> None:
        now_ts = int(time.time())
        self.conn.execute(
            """
            INSERT INTO sync_state (
              topic_id, last_known_posts_count, last_known_last_posted_at,
              last_synced_json_page, last_synced_raw_page, last_synced_post_number,
              last_sync_mode, last_sync_status, last_sync_started_at, last_sync_finished_at,
              last_sync_error, updated_ts
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(topic_id) DO UPDATE SET
              last_known_posts_count=excluded.last_known_posts_count,
              last_known_last_posted_at=excluded.last_known_last_posted_at,
              last_synced_json_page=excluded.last_synced_json_page,
              last_synced_raw_page=excluded.last_synced_raw_page,
              last_synced_post_number=excluded.last_synced_post_number,
              last_sync_mode=excluded.last_sync_mode,
              last_sync_status=excluded.last_sync_status,
              last_sync_started_at=excluded.last_sync_started_at,
              last_sync_finished_at=excluded.last_sync_finished_at,
              last_sync_error=excluded.last_sync_error,
              updated_ts=excluded.updated_ts
            """,
            (
                state.topic_id,
                state.last_known_posts_count,
                state.last_known_last_posted_at,
                state.last_synced_json_page,
                state.last_synced_raw_page,
                state.last_synced_post_number,
                state.last_sync_mode,
                state.last_sync_status,
                state.last_sync_started_at,
                state.last_sync_finished_at,
                state.last_sync_error,
                now_ts,
            ),
        )
        self.conn.commit()
