from __future__ import annotations

from typing import Any

from shuiyuan_cache.core.config import CacheConfig
from shuiyuan_cache.fetch.session import ShuiyuanSession

_VALID_MODES = {"header", "full_page"}
_VALID_CONTEXT_TYPES = {"user", "topic", "category", "tag", "private_messages"}


class ForumSearchFetcher:
    def __init__(self, config: CacheConfig):
        self.config = config
        self.session = ShuiyuanSession(config)

    def close(self) -> None:
        self.session.close()

    def search(
        self,
        query: str,
        *,
        mode: str = "header",
        page: int = 1,
        limit_topics: int = 5,
        limit_posts: int = 5,
        search_context_type: str | None = None,
        search_context_id: str | int | None = None,
    ) -> dict[str, Any]:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("Search query cannot be empty")

        normalized_mode = self._normalize_mode(mode)
        normalized_context_type, normalized_context_id = self._normalize_search_context(
            search_context_type,
            search_context_id,
        )
        resolved_page = max(int(page), 1)
        endpoint = "/search/query.json" if normalized_mode == "header" else "/search.json"
        payload = self.session.get_json(
            endpoint,
            params=self._build_params(
                query=normalized_query,
                mode=normalized_mode,
                page=resolved_page,
                search_context_type=normalized_context_type,
                search_context_id=normalized_context_id,
            ),
        )
        topics = payload.get("topics") or []
        posts = payload.get("posts") or []
        users = payload.get("users") or []
        groups = payload.get("groups") or []
        tags = payload.get("tags") or []
        categories = payload.get("categories") or []
        grouped = payload.get("grouped_search_result") or {}
        topic_by_id = {
            item.get("id"): item for item in topics if item.get("id") is not None
        }

        return {
            "query": normalized_query,
            "mode": normalized_mode,
            "page": resolved_page,
            "search_context": (
                {
                    "type": normalized_context_type,
                    "id": str(normalized_context_id),
                }
                if normalized_context_type and normalized_context_id is not None
                else None
            ),
            "topic_count": len(topics),
            "post_count": len(posts),
            "user_count": len(users),
            "group_count": len(groups),
            "tag_count": len(tags),
            "category_count": len(categories),
            "has_more_full_page_results": bool(
                grouped.get("more_full_page_results")
            ),
            "topics": [
                self._serialize_topic(item) for item in topics[: max(limit_topics, 0)]
            ],
            "posts": [
                self._serialize_post(item, topic_by_id.get(item.get("topic_id")))
                for item in posts[: max(limit_posts, 0)]
            ],
        }

    def _build_params(
        self,
        *,
        query: str,
        mode: str,
        page: int,
        search_context_type: str | None,
        search_context_id: str | int | None,
    ) -> dict[str, Any]:
        params: dict[str, Any]
        if mode == "header":
            params = {"term": query}
        else:
            params = {"q": query, "page": page}
        if search_context_type and search_context_id is not None:
            params["search_context[type]"] = search_context_type
            params["search_context[id]"] = str(search_context_id)
        return params

    @staticmethod
    def _normalize_mode(mode: str) -> str:
        normalized_mode = mode.strip().lower().replace("-", "_")
        if normalized_mode not in _VALID_MODES:
            raise ValueError(f"Unsupported search mode: {mode}")
        return normalized_mode

    @staticmethod
    def _normalize_search_context(
        search_context_type: str | None,
        search_context_id: str | int | None,
    ) -> tuple[str | None, str | int | None]:
        if search_context_type is None and search_context_id is None:
            return None, None
        if search_context_type is None or search_context_id is None:
            raise ValueError(
                "search_context_type and search_context_id must be provided together"
            )
        normalized_type = search_context_type.strip().lower()
        if normalized_type not in _VALID_CONTEXT_TYPES:
            raise ValueError(f"Unsupported search context type: {search_context_type}")
        return normalized_type, search_context_id

    def _serialize_topic(self, item: dict[str, Any]) -> dict[str, Any]:
        topic_id = item.get("id")
        slug = item.get("slug") or "topic"
        return {
            "id": topic_id,
            "title": item.get("title"),
            "slug": slug,
            "posts_count": item.get("posts_count"),
            "views": item.get("views"),
            "created_at": item.get("created_at"),
            "last_posted_at": item.get("last_posted_at") or item.get("bumped_at"),
            "url": self._topic_url(topic_id, slug) if topic_id is not None else None,
        }

    def _serialize_post(
        self,
        item: dict[str, Any],
        topic_item: dict[str, Any] | None,
    ) -> dict[str, Any]:
        topic_id = item.get("topic_id")
        post_number = item.get("post_number")
        resolved_topic = topic_item or (item.get("topic") if isinstance(item.get("topic"), dict) else {})
        slug = resolved_topic.get("slug") or "topic"
        return {
            "topic_id": topic_id,
            "topic_title": resolved_topic.get("title") or item.get("topic_title_headline"),
            "topic_slug": slug,
            "post_number": post_number,
            "username": item.get("username"),
            "created_at": item.get("created_at"),
            "blurb": item.get("blurb"),
            "url": (
                self._post_url(topic_id, slug, post_number)
                if topic_id is not None and post_number is not None
                else None
            ),
        }

    def _topic_url(self, topic_id: int, slug: str) -> str:
        return f"{self.config.base_url.rstrip('/')}/t/{slug}/{topic_id}"

    def _post_url(self, topic_id: int, slug: str, post_number: int) -> str:
        return f"{self._topic_url(topic_id, slug)}/{post_number}"
