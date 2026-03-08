from shuiyuan_cache.core.config import CacheConfig
from shuiyuan_cache.core.models import SyncStateRecord, TopicRecord
from shuiyuan_cache.fetch.sync_planner import SyncPlanner


def build_topic(
    posts_count: int, last_posted_at: str = "2026-03-09T00:00:00Z"
) -> TopicRecord:
    return TopicRecord(
        topic_id=456,
        title="demo",
        category_id=None,
        tags_json="[]",
        created_at="2026-03-01T00:00:00Z",
        last_posted_at=last_posted_at,
        posts_count=posts_count,
        reply_count=max(posts_count - 1, 0),
        views=None,
        like_count=None,
        visible=True,
        archived=False,
        closed=False,
        topic_json_path="/tmp/topic.json",
    )


def build_state(
    *,
    last_known_posts_count: int,
    last_known_last_posted_at: str,
    last_synced_json_page: int,
    last_synced_raw_page: int,
) -> SyncStateRecord:
    return SyncStateRecord(
        topic_id=456,
        last_known_posts_count=last_known_posts_count,
        last_known_last_posted_at=last_known_last_posted_at,
        last_synced_json_page=last_synced_json_page,
        last_synced_raw_page=last_synced_raw_page,
        last_synced_post_number=last_known_posts_count,
        last_sync_mode="incremental",
        last_sync_status="success",
        last_sync_started_at="2026-03-08T00:00:00Z",
        last_sync_finished_at="2026-03-08T00:01:00Z",
        last_sync_error=None,
    )


def test_full_plan_without_existing_state_fetches_all_pages() -> None:
    planner = SyncPlanner(CacheConfig(json_page_size=20, raw_page_size=100))

    plan = planner.build_plan(build_topic(posts_count=260), None, mode="incremental")

    assert plan.mode == "incremental"
    assert plan.json_pages_to_fetch == list(range(1, 14))
    assert plan.raw_pages_to_fetch == [1, 2, 3]
    assert plan.should_download_images is True


def test_unchanged_topic_skips_incremental_fetch() -> None:
    planner = SyncPlanner(CacheConfig())
    topic = build_topic(posts_count=80, last_posted_at="2026-03-09T10:00:00Z")
    state = build_state(
        last_known_posts_count=80,
        last_known_last_posted_at="2026-03-09T10:00:00Z",
        last_synced_json_page=4,
        last_synced_raw_page=1,
    )

    plan = planner.build_plan(topic, state, mode="incremental")

    assert plan.json_pages_to_fetch == []
    assert plan.raw_pages_to_fetch == []
    assert plan.skip_reason == "topic unchanged"
    assert plan.should_download_images is False


def test_incremental_plan_rewinds_tail_pages() -> None:
    planner = SyncPlanner(
        CacheConfig(json_page_size=20, raw_page_size=100, tail_refresh_pages=2)
    )
    topic = build_topic(posts_count=260, last_posted_at="2026-03-09T10:00:00Z")
    state = build_state(
        last_known_posts_count=240,
        last_known_last_posted_at="2026-03-08T10:00:00Z",
        last_synced_json_page=11,
        last_synced_raw_page=3,
    )

    plan = planner.build_plan(topic, state, mode="incremental")

    assert plan.json_pages_to_fetch == [10, 11, 12, 13]
    assert plan.raw_pages_to_fetch == [2, 3]


def test_refresh_tail_only_fetches_recent_pages() -> None:
    planner = SyncPlanner(
        CacheConfig(json_page_size=20, raw_page_size=100, tail_refresh_pages=2)
    )
    topic = build_topic(posts_count=260, last_posted_at="2026-03-09T10:00:00Z")
    state = build_state(
        last_known_posts_count=240,
        last_known_last_posted_at="2026-03-08T10:00:00Z",
        last_synced_json_page=11,
        last_synced_raw_page=3,
    )

    plan = planner.build_plan(topic, state, mode="refresh-tail")

    assert plan.json_pages_to_fetch == [12, 13]
    assert plan.raw_pages_to_fetch == [2, 3]
