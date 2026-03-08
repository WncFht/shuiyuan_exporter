import pytest

from shuiyuan_cache.fetch.topic_fetcher import TopicFetcher


@pytest.mark.parametrize(
    ("topic", "expected"),
    [
        (123, 123),
        ("123", 123),
        ("L123", 123),
        ("/t/topic/123", 123),
        ("https://shuiyuan.sjtu.edu.cn/t/topic/123/45", 123),
    ],
)
def test_resolve_topic_id(topic, expected: int) -> None:
    assert TopicFetcher.resolve_topic_id(topic) == expected


@pytest.mark.parametrize(
    ("posts_count", "page_size", "expected"),
    [
        (0, 20, 1),
        (1, 20, 1),
        (20, 20, 1),
        (21, 20, 2),
        (101, 100, 2),
    ],
)
def test_page_count(posts_count: int, page_size: int, expected: int) -> None:
    assert TopicFetcher.page_count(posts_count, page_size) == expected
