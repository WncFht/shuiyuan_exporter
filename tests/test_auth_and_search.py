from __future__ import annotations

from shuiyuan_cache.auth.browser_auth import BrowserAuthManager
from shuiyuan_cache.core.config import CacheConfig
from shuiyuan_cache.core.exceptions import FetchError
from shuiyuan_cache.fetch.search_fetcher import ForumSearchFetcher
from shuiyuan_cache.skill_api import ShuiyuanSkillAPI


class _SuccessfulSession:
    def __init__(self, config: CacheConfig):
        self.config = config

    def get_text(self, url: str, **kwargs):  # noqa: ANN003
        assert url == "/latest"
        return "<title>水源社区</title>"

    def close(self) -> None:
        pass


class _FailingSession:
    def __init__(self, config: CacheConfig):
        self.config = config

    def get_text(self, url: str, **kwargs):  # noqa: ANN003
        raise FetchError("Authentication failed for https://shuiyuan.sjtu.edu.cn/latest")

    def close(self) -> None:
        pass


class _HeaderSearchSession:
    def __init__(self, config: CacheConfig):
        self.config = config

    def get_json(self, url: str, **kwargs):  # noqa: ANN003
        assert url == "/search/query.json"
        assert kwargs["params"] == {"term": "炒股"}
        return {
            "topics": [
                {
                    "id": 351551,
                    "title": "牢A投资记录",
                    "slug": "topic",
                    "posts_count": 6217,
                    "views": 59817,
                    "created_at": "2025-02-22T15:31:35.964Z",
                    "last_posted_at": "2026-03-07T15:16:17.716Z",
                }
            ],
            "posts": [
                {
                    "topic_id": 351551,
                    "post_number": 1,
                    "username": "风花雪月",
                    "created_at": "2025-02-22T15:31:36.064Z",
                    "blurb": "经历三年个股熊市的牢A似乎站起来了！",
                }
            ],
            "grouped_search_result": {"more_full_page_results": []},
        }

    def close(self) -> None:
        pass


class _FullPageSearchSession:
    def __init__(self, config: CacheConfig):
        self.config = config

    def get_json(self, url: str, **kwargs):  # noqa: ANN003
        assert url == "/search.json"
        assert kwargs["params"] == {
            "q": "搜索 user:pangbo order:latest",
            "page": 2,
            "search_context[type]": "user",
            "search_context[id]": "pangbo",
        }
        return {
            "topics": [
                {
                    "id": 315062,
                    "title": "搜索的一些心得",
                    "slug": "topic",
                    "posts_count": 99,
                    "views": 1234,
                    "created_at": "2025-10-01T00:00:00.000Z",
                    "bumped_at": "2026-03-01T12:00:00.000Z",
                }
            ],
            "posts": [
                {
                    "topic_id": 315062,
                    "post_number": 18,
                    "username": "pangbo",
                    "created_at": "2026-03-01T12:00:00.000Z",
                    "blurb": "可以先搜索再顺藤摸瓜",
                    "topic": {
                        "id": 315062,
                        "title": "搜索的一些心得",
                        "slug": "topic",
                    },
                },
                {
                    "topic_id": 277768,
                    "post_number": 3,
                    "username": "pangbo",
                    "created_at": "2026-02-15T10:00:00.000Z",
                    "blurb": "另一个结果",
                    "topic": {
                        "id": 277768,
                        "title": "旧讨论串",
                        "slug": "topic",
                    },
                },
            ],
            "users": [{"username": "pangbo"}],
            "groups": [],
            "tags": ["search"],
            "categories": [{"id": 1, "name": "Tech"}],
            "grouped_search_result": {"more_full_page_results": [3]},
        }

    def close(self) -> None:
        pass


def test_auth_status_reports_cookie_file_format(tmp_path) -> None:
    config = CacheConfig(cache_root=tmp_path / "cache", cookie_path=tmp_path / "cookies.txt")
    manager = BrowserAuthManager(config)

    payload = manager.auth_status()

    assert payload["cookie_file_format"] == "http_header"



def test_auth_status_check_live_success(monkeypatch, tmp_path) -> None:
    config = CacheConfig(cache_root=tmp_path / "cache", cookie_path=tmp_path / "cookies.txt")
    manager = BrowserAuthManager(config)
    monkeypatch.setattr("shuiyuan_cache.auth.browser_auth.ShuiyuanSession", _SuccessfulSession)

    payload = manager.auth_status(check_live=True)

    assert payload["live_check_enabled"] is True
    assert payload["live_check_ok"] is True
    assert payload["live_check_error"] is None



def test_auth_status_check_live_failure(monkeypatch, tmp_path) -> None:
    config = CacheConfig(cache_root=tmp_path / "cache", cookie_path=tmp_path / "cookies.txt")
    manager = BrowserAuthManager(config)
    monkeypatch.setattr("shuiyuan_cache.auth.browser_auth.ShuiyuanSession", _FailingSession)

    payload = manager.auth_status(check_live=True)

    assert payload["live_check_enabled"] is True
    assert payload["live_check_ok"] is False
    assert "Authentication failed" in payload["live_check_error"]



def test_search_fetcher_serializes_header_results(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "shuiyuan_cache.fetch.search_fetcher.ShuiyuanSession",
        _HeaderSearchSession,
    )
    fetcher = ForumSearchFetcher(
        CacheConfig(cache_root=tmp_path / "cache", cookie_path=tmp_path / "cookies.txt")
    )
    try:
        payload = fetcher.search("炒股", limit_topics=5, limit_posts=5)
    finally:
        fetcher.close()

    assert payload["query"] == "炒股"
    assert payload["mode"] == "header"
    assert payload["page"] == 1
    assert payload["search_context"] is None
    assert payload["topic_count"] == 1
    assert payload["post_count"] == 1
    assert payload["topics"][0]["url"] == "https://shuiyuan.sjtu.edu.cn/t/topic/351551"
    assert payload["posts"][0]["topic_title"] == "牢A投资记录"
    assert payload["posts"][0]["url"] == "https://shuiyuan.sjtu.edu.cn/t/topic/351551/1"



def test_search_fetcher_serializes_full_page_results_and_context(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(
        "shuiyuan_cache.fetch.search_fetcher.ShuiyuanSession",
        _FullPageSearchSession,
    )
    fetcher = ForumSearchFetcher(
        CacheConfig(cache_root=tmp_path / "cache", cookie_path=tmp_path / "cookies.txt")
    )
    try:
        payload = fetcher.search(
            "搜索 user:pangbo order:latest",
            mode="full-page",
            page=2,
            limit_topics=5,
            limit_posts=5,
            search_context_type="user",
            search_context_id="pangbo",
        )
    finally:
        fetcher.close()

    assert payload["query"] == "搜索 user:pangbo order:latest"
    assert payload["mode"] == "full_page"
    assert payload["page"] == 2
    assert payload["search_context"] == {"type": "user", "id": "pangbo"}
    assert payload["topic_count"] == 1
    assert payload["post_count"] == 2
    assert payload["user_count"] == 1
    assert payload["group_count"] == 0
    assert payload["tag_count"] == 1
    assert payload["category_count"] == 1
    assert payload["has_more_full_page_results"] is True
    assert payload["posts"][0]["topic_title"] == "搜索的一些心得"
    assert payload["posts"][1]["url"] == "https://shuiyuan.sjtu.edu.cn/t/topic/277768/3"



def test_trace_author_combines_live_search_with_cached_queries(tmp_path, monkeypatch) -> None:
    api = ShuiyuanSkillAPI(
        CacheConfig(cache_root=tmp_path / "cache", cookie_path=tmp_path / "cookies.txt")
    )

    def fake_search_forum(
        *,
        query: str,
        mode: str,
        page: int,
        limit_topics: int,
        limit_posts: int,
        search_context_type=None,
        search_context_id=None,
    ) -> dict:
        assert query == "搜索 user:pangbo order:latest"
        assert mode == "full_page"
        assert page == 1
        assert limit_topics == 5
        assert limit_posts == 10
        assert search_context_type is None
        assert search_context_id is None
        return {
            "query": query,
            "mode": mode,
            "page": page,
            "search_context": None,
            "topic_count": 2,
            "post_count": 3,
            "user_count": 1,
            "group_count": 0,
            "tag_count": 0,
            "category_count": 0,
            "has_more_full_page_results": False,
            "topics": [
                {
                    "id": 315062,
                    "title": "搜索的一些心得",
                    "slug": "topic",
                    "url": "https://shuiyuan.sjtu.edu.cn/t/topic/315062",
                },
                {
                    "id": 277768,
                    "title": "旧讨论串",
                    "slug": "topic",
                    "url": "https://shuiyuan.sjtu.edu.cn/t/topic/277768",
                },
            ],
            "posts": [
                {
                    "topic_id": 315062,
                    "topic_title": "搜索的一些心得",
                    "topic_slug": "topic",
                    "post_number": 18,
                    "username": "pangbo",
                    "created_at": "2026-03-01T12:00:00.000Z",
                    "blurb": "第一次命中",
                    "url": "https://shuiyuan.sjtu.edu.cn/t/topic/315062/18",
                },
                {
                    "topic_id": 315062,
                    "topic_title": "搜索的一些心得",
                    "topic_slug": "topic",
                    "post_number": 20,
                    "username": "pangbo",
                    "created_at": "2026-03-02T12:00:00.000Z",
                    "blurb": "第二次命中",
                    "url": "https://shuiyuan.sjtu.edu.cn/t/topic/315062/20",
                },
                {
                    "topic_id": 277768,
                    "topic_title": "旧讨论串",
                    "topic_slug": "topic",
                    "post_number": 3,
                    "username": "pangbo",
                    "created_at": "2026-02-15T10:00:00.000Z",
                    "blurb": "另一个命中",
                    "url": "https://shuiyuan.sjtu.edu.cn/t/topic/277768/3",
                },
            ],
        }

    def fake_ensure_topic_cached(**kwargs) -> dict:
        topic = kwargs["topic"]
        assert topic == 315062
        return {
            "topic_id": topic,
            "cache_hit_before": False,
            "cache_ready_after": True,
            "sync_executed": True,
            "effective_mode": "incremental",
            "sync_result": {"ok": True},
            "inspect_before": {"usable_for_analysis": False},
            "inspect_after": {"usable_for_analysis": True},
        }

    def fake_query_topic_posts(**kwargs) -> dict:
        assert kwargs["topic"] == 315062
        assert kwargs["keyword"] == "搜索"
        assert kwargs["author"] == "pangbo"
        assert kwargs["limit"] == 10
        assert kwargs["order"] == "desc"
        assert kwargs["include_images"] is False
        assert kwargs["ensure_cached"] is False
        return {
            "topic_id": 315062,
            "title": "搜索的一些心得",
            "total_hits": 2,
            "ensure_cache": None,
            "posts": [
                {"post_number": 20, "username": "pangbo"},
                {"post_number": 18, "username": "pangbo"},
            ],
        }

    monkeypatch.setattr(api, "search_forum", fake_search_forum)
    monkeypatch.setattr(api, "ensure_topic_cached", fake_ensure_topic_cached)
    monkeypatch.setattr(api, "query_topic_posts", fake_query_topic_posts)

    payload = api.trace_author("pangbo", keyword="搜索", cache_topics=1)

    assert payload["author"] == "pangbo"
    assert payload["keyword"] == "搜索"
    assert payload["query"] == "搜索 user:pangbo order:latest"
    assert payload["topic_candidates"][0]["topic_id"] == 315062
    assert payload["topic_candidates"][0]["live_post_hits"] == 2
    assert payload["topic_candidates"][0]["latest_live_hit_at"] == "2026-03-02T12:00:00.000Z"
    assert payload["topic_candidates"][1]["topic_id"] == 277768
    assert len(payload["cached_topics"]) == 1
    assert payload["cached_topics"][0]["topic_id"] == 315062
    assert payload["cached_topics"][0]["ensure_cache"] == {
        "topic_id": 315062,
        "cache_hit_before": False,
        "cache_ready_after": True,
        "sync_executed": True,
        "effective_mode": "incremental",
    }
    assert payload["cached_topics"][0]["cached_query"]["total_hits"] == 2
    assert payload["cached_topics"][0]["error"] is None
