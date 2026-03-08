from collections import Counter
from datetime import datetime, timedelta, timezone
import re

from shuiyuan_cache.core.config import CacheConfig
from shuiyuan_cache.core.models import TopicSummary
from shuiyuan_cache.fetch.topic_fetcher import TopicFetcher
from shuiyuan_cache.analysis.inspect_service import TopicInspectService
from shuiyuan_cache.analysis.post_query import TopicQueryService


class TopicSummaryService:
    def __init__(self, config: CacheConfig):
        self.config = config
        self.inspect_service = TopicInspectService(config)
        self.query_service = TopicQueryService(config)

    def close(self) -> None:
        self.inspect_service.close()
        self.query_service.close()

    def summarize_topic(
        self,
        topic_id: str | int,
        only_op: bool = False,
        recent_days: int | None = None,
        focus_keywords: list[str] | None = None,
        include_images: bool = False,
    ) -> TopicSummary:
        resolved_topic_id = TopicFetcher.resolve_topic_id(topic_id)
        inspect = self.inspect_service.inspect_topic(resolved_topic_id)
        date_from = None
        if recent_days is not None:
            date_from = (
                (datetime.now(timezone.utc) - timedelta(days=recent_days))
                .replace(microsecond=0)
                .isoformat()
            )
        result = self.query_service.query_topic_posts(
            topic_id=resolved_topic_id,
            only_op=only_op,
            date_from=date_from,
            limit=None,
            include_images=include_images,
        )
        items = result.items
        if not items:
            return TopicSummary(
                topic_id=resolved_topic_id,
                title=inspect.title or f"topic-{resolved_topic_id}",
                summary_text="No cached posts matched the requested summary scope.",
                time_range="N/A",
                post_count_in_scope=0,
                top_authors=[],
                top_keywords=[],
                key_posts=[],
                image_post_numbers=[],
            )

        top_authors = Counter(item.username or "unknown" for item in items).most_common(
            5
        )
        keyword_counts = self._count_keywords(items, focus_keywords or [])
        image_post_numbers = [item.post_number for item in items if item.image_count][
            :10
        ]
        key_posts = self._select_key_posts(items)
        time_range = (
            f"{items[0].created_at or 'unknown'} -> {items[-1].created_at or 'unknown'}"
        )
        summary_text = self._build_summary_text(
            title=inspect.title or f"topic-{resolved_topic_id}",
            post_count=len(items),
            only_op=only_op,
            recent_days=recent_days,
            top_authors=top_authors,
            image_post_numbers=image_post_numbers,
            key_posts=key_posts,
            keyword_counts=keyword_counts,
        )
        return TopicSummary(
            topic_id=resolved_topic_id,
            title=inspect.title or f"topic-{resolved_topic_id}",
            summary_text=summary_text,
            time_range=time_range,
            post_count_in_scope=len(items),
            top_authors=top_authors,
            top_keywords=keyword_counts,
            key_posts=key_posts,
            image_post_numbers=image_post_numbers,
        )

    @staticmethod
    def _count_keywords(items, focus_keywords: list[str]) -> list[tuple[str, int]]:
        if focus_keywords:
            combined = "\n".join(item.plain_text or "" for item in items).lower()
            return [
                (kw, combined.count(kw.lower()))
                for kw in focus_keywords
                if combined.count(kw.lower()) > 0
            ]

        token_counter: Counter[str] = Counter()
        stopwords = {"https", "http", "the", "and", "that", "this", "with", "from"}
        for item in items:
            text = item.plain_text or ""
            for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]{1,}", text):
                token_lower = token.lower()
                if token_lower not in stopwords:
                    token_counter[token_lower] += 1
        return token_counter.most_common(5)

    @staticmethod
    def _select_key_posts(items) -> list[int]:
        selected: list[int] = []
        if items:
            selected.append(items[0].post_number)
        for item in items:
            if item.image_count and item.post_number not in selected:
                selected.append(item.post_number)
            if len(selected) >= 5:
                break
        if items[-1].post_number not in selected:
            selected.append(items[-1].post_number)
        return selected[:6]

    @staticmethod
    def _build_summary_text(
        title: str,
        post_count: int,
        only_op: bool,
        recent_days: int | None,
        top_authors,
        image_post_numbers,
        key_posts,
        keyword_counts,
    ) -> str:
        parts = [
            f'Topic "{title}" matched {post_count} cached posts in the current scope.'
        ]
        if only_op:
            parts.append("The scope is restricted to the original poster.")
        if recent_days is not None:
            parts.append(f"The scope is limited to the most recent {recent_days} days.")
        if top_authors:
            author_text = ", ".join(
                f"{name}({count})" for name, count in top_authors[:3]
            )
            parts.append(f"Most active authors in scope: {author_text}.")
        if keyword_counts:
            keyword_text = ", ".join(
                f"{name}({count})" for name, count in keyword_counts[:5]
            )
            parts.append(f"Notable keywords/tokens: {keyword_text}.")
        if image_post_numbers:
            parts.append(
                f"Image-bearing posts include: {', '.join(f'#{num}' for num in image_post_numbers[:5])}."
            )
        if key_posts:
            parts.append(
                f"Key posts to review: {', '.join(f'#{num}' for num in key_posts)}."
            )
        return " ".join(parts)
