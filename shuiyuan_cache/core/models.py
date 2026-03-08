from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass(slots=True)
class TopicRecord:
    topic_id: int
    title: str
    category_id: Optional[int]
    tags_json: str
    created_at: Optional[str]
    last_posted_at: Optional[str]
    posts_count: int
    reply_count: Optional[int]
    views: Optional[int]
    like_count: Optional[int]
    visible: Optional[bool]
    archived: Optional[bool]
    closed: Optional[bool]
    topic_json_path: str


@dataclass(slots=True)
class PostRecord:
    post_id: int
    topic_id: int
    post_number: int
    username: Optional[str]
    display_name: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    reply_to_post_number: Optional[int]
    is_op: bool
    like_count: int
    raw_markdown: Optional[str]
    cooked_html: Optional[str]
    plain_text: Optional[str]
    raw_page_no: Optional[int]
    json_page_no: Optional[int]
    raw_post_path: Optional[str]
    has_images: bool
    has_attachments: bool
    has_audio: bool
    has_video: bool
    image_count: int
    hash_raw: Optional[str]
    hash_cooked: Optional[str]


@dataclass(slots=True)
class MediaRecord:
    topic_id: int
    post_id: Optional[int]
    post_number: Optional[int]
    media_type: str
    upload_ref: Optional[str]
    resolved_url: Optional[str]
    local_path: Optional[str]
    mime_type: Optional[str]
    file_ext: Optional[str]
    media_key: Optional[str]
    download_status: str
    content_length: Optional[int] = None


@dataclass(slots=True)
class SyncStateRecord:
    topic_id: int
    last_known_posts_count: int
    last_known_last_posted_at: Optional[str]
    last_synced_json_page: int
    last_synced_raw_page: int
    last_synced_post_number: int
    last_sync_mode: Optional[str]
    last_sync_status: str
    last_sync_started_at: Optional[str]
    last_sync_finished_at: Optional[str]
    last_sync_error: Optional[str]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class SyncPlan:
    topic_id: int
    mode: str
    current_json_pages: int
    current_raw_pages: int
    should_fetch_topic_json: bool
    json_pages_to_fetch: list[int]
    raw_pages_to_fetch: list[int]
    post_numbers_to_fetch: list[int] = field(default_factory=list)
    should_download_images: bool = True
    skip_reason: Optional[str] = None


@dataclass(slots=True)
class SyncResult:
    topic_id: int
    title: Optional[str]
    mode: str
    fetched_json_pages: int
    fetched_raw_pages: int
    fetched_post_raw_count: int
    inserted_posts: int
    updated_posts: int
    inserted_media: int
    updated_media: int
    downloaded_images: int
    skipped_images: int
    status: str
    errors: list[str] = field(default_factory=list)
