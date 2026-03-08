from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class TopicRecord:
    topic_id: int
    title: str
    category_id: int | None
    tags_json: str
    created_at: str | None
    last_posted_at: str | None
    posts_count: int
    reply_count: int | None
    views: int | None
    like_count: int | None
    visible: bool | None
    archived: bool | None
    closed: bool | None
    topic_json_path: str


@dataclass(slots=True)
class PostRecord:
    post_id: int
    topic_id: int
    post_number: int
    username: str | None
    display_name: str | None
    created_at: str | None
    updated_at: str | None
    reply_to_post_number: int | None
    is_op: bool
    like_count: int
    raw_markdown: str | None
    cooked_html: str | None
    plain_text: str | None
    raw_page_no: int | None
    json_page_no: int | None
    raw_post_path: str | None
    has_images: bool
    has_attachments: bool
    has_audio: bool
    has_video: bool
    image_count: int
    hash_raw: str | None
    hash_cooked: str | None


@dataclass(slots=True)
class MediaRecord:
    topic_id: int
    post_id: int | None
    post_number: int | None
    media_type: str
    upload_ref: str | None
    resolved_url: str | None
    local_path: str | None
    mime_type: str | None
    file_ext: str | None
    media_key: str | None
    download_status: str
    content_length: int | None = None


@dataclass(slots=True)
class SyncStateRecord:
    topic_id: int
    last_known_posts_count: int
    last_known_last_posted_at: str | None
    last_synced_json_page: int
    last_synced_raw_page: int
    last_synced_post_number: int
    last_sync_mode: str | None
    last_sync_status: str
    last_sync_started_at: str | None
    last_sync_finished_at: str | None
    last_sync_error: str | None

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
    skip_reason: str | None = None


@dataclass(slots=True)
class SyncResult:
    topic_id: int
    title: str | None
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


@dataclass(slots=True)
class TopicInspectResult:
    topic_id: int
    title: str | None
    topic_posts_count: int
    db_post_count: int
    json_page_count: int
    raw_page_count: int
    media_image_count: int
    image_file_count: int
    last_posted_at: str | None
    last_sync_status: str | None
    last_sync_mode: str | None
    last_sync_finished_at: str | None
    cache_path: str
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class QueryPostItem:
    post_id: int
    post_number: int
    username: str | None
    created_at: str | None
    plain_text: str | None
    image_paths: list[str] = field(default_factory=list)
    image_count: int = 0
    score: float | None = None


@dataclass(slots=True)
class QueryResult:
    topic_id: int
    total_hits: int
    items: list[QueryPostItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class TopicSummary:
    topic_id: int
    title: str
    summary_text: str
    time_range: str
    post_count_in_scope: int
    top_authors: list[tuple[str, int]] = field(default_factory=list)
    top_keywords: list[tuple[str, int]] = field(default_factory=list)
    key_posts: list[int] = field(default_factory=list)
    image_post_numbers: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
