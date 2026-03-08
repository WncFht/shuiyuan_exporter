from shuiyuan_cache.core.config import CacheConfig
from shuiyuan_cache.core.models import SyncPlan, SyncStateRecord, TopicRecord
from shuiyuan_cache.fetch.topic_fetcher import TopicFetcher


class SyncPlanner:
    def __init__(self, config: CacheConfig):
        self.config = config

    def build_plan(
        self,
        topic: TopicRecord,
        existing_state: SyncStateRecord | None,
        mode: str,
        force: bool = False,
        with_images: bool = True,
    ) -> SyncPlan:
        current_json_pages = TopicFetcher.page_count(topic.posts_count, self.config.json_page_size)
        current_raw_pages = TopicFetcher.page_count(topic.posts_count, self.config.raw_page_size)

        if mode == "full" or existing_state is None:
            return SyncPlan(
                topic_id=topic.topic_id,
                mode="full" if mode == "full" else mode,
                current_json_pages=current_json_pages,
                current_raw_pages=current_raw_pages,
                should_fetch_topic_json=True,
                json_pages_to_fetch=list(range(1, current_json_pages + 1)),
                raw_pages_to_fetch=list(range(1, current_raw_pages + 1)),
                should_download_images=with_images,
            )

        if not force and self._is_unchanged(topic, existing_state):
            return SyncPlan(
                topic_id=topic.topic_id,
                mode=mode,
                current_json_pages=current_json_pages,
                current_raw_pages=current_raw_pages,
                should_fetch_topic_json=True,
                json_pages_to_fetch=[],
                raw_pages_to_fetch=[],
                should_download_images=False,
                skip_reason="topic unchanged",
            )

        if mode == "refresh-tail":
            json_start = max(1, current_json_pages - self.config.tail_refresh_pages + 1)
            raw_start = max(1, current_raw_pages - self.config.tail_refresh_pages + 1)
        else:
            json_start = max(1, min(existing_state.last_synced_json_page or 1, current_json_pages) - self.config.tail_refresh_pages + 1)
            raw_start = max(1, min(existing_state.last_synced_raw_page or 1, current_raw_pages) - self.config.tail_refresh_pages + 1)

        return SyncPlan(
            topic_id=topic.topic_id,
            mode=mode,
            current_json_pages=current_json_pages,
            current_raw_pages=current_raw_pages,
            should_fetch_topic_json=True,
            json_pages_to_fetch=list(range(json_start, current_json_pages + 1)),
            raw_pages_to_fetch=list(range(raw_start, current_raw_pages + 1)),
            should_download_images=with_images,
        )

    @staticmethod
    def _is_unchanged(topic: TopicRecord, state: SyncStateRecord) -> bool:
        return (
            topic.posts_count == state.last_known_posts_count
            and topic.last_posted_at == state.last_known_last_posted_at
        )
