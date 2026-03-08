from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path

from shuiyuan_cache.analysis.inspect_service import TopicInspectService
from shuiyuan_cache.analysis.post_query import TopicQueryService
from shuiyuan_cache.analysis.topic_summary import TopicSummaryService
from shuiyuan_cache.core.config import CacheConfig
from shuiyuan_cache.core.progress import ProgressCallback
from shuiyuan_cache.export.topic_exporter import export_topic
from shuiyuan_cache.fetch.search_fetcher import ForumSearchFetcher
from shuiyuan_cache.fetch.topic_fetcher import TopicFetcher
from shuiyuan_cache.skill_api.runtime import (
    build_skill_config,
    default_skill_export_root,
)
from shuiyuan_cache.sync.topic_sync import TopicSyncService


_QUOTE_TARGET_RE = re.compile(
    r"https://shuiyuan\.sjtu\.edu\.cn/t/topic/(\d+)(?:/(\d+))?"
)


class ShuiyuanSkillAPI:
    def __init__(self, config: CacheConfig, export_root: str | Path | None = None):
        self.config = config
        self.export_root = (
            Path(export_root).expanduser().resolve()
            if export_root
            else default_skill_export_root()
        )
        self.export_root.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_runtime(
        cls,
        cache_root: str | Path | None = None,
        cookie_path: str | Path | None = None,
        export_root: str | Path | None = None,
        base_url: str = "https://shuiyuan.sjtu.edu.cn",
    ) -> ShuiyuanSkillAPI:
        config = build_skill_config(
            cache_root=cache_root,
            cookie_path=cookie_path,
            base_url=base_url,
        )
        return cls(config=config, export_root=export_root)

    def inspect_topic(self, topic: str | int) -> dict:
        service = TopicInspectService(self.config)
        try:
            result = service.inspect_topic(topic)
        finally:
            service.close()
        payload = result.to_dict()
        payload["usable_for_analysis"] = bool(
            result.db_post_count and result.json_page_count
        )
        payload["usable_for_export"] = bool(
            result.db_post_count and result.json_page_count and result.raw_page_count
        )
        payload["has_issues"] = bool(result.issues)
        return payload

    def search_forum(
        self,
        query: str,
        mode: str = "header",
        page: int = 1,
        limit_topics: int = 5,
        limit_posts: int = 5,
        search_context_type: str | None = None,
        search_context_id: str | int | None = None,
    ) -> dict:
        fetcher = ForumSearchFetcher(self.config)
        try:
            return fetcher.search(
                query=query,
                mode=mode,
                page=page,
                limit_topics=limit_topics,
                limit_posts=limit_posts,
                search_context_type=search_context_type,
                search_context_id=search_context_id,
            )
        finally:
            fetcher.close()

    def search_forum_topics(
        self,
        term: str,
        limit_topics: int = 5,
        limit_posts: int = 5,
    ) -> dict:
        return self.search_forum(
            query=term,
            mode="header",
            limit_topics=limit_topics,
            limit_posts=limit_posts,
        )

    def trace_author(
        self,
        author: str,
        keyword: str | None = None,
        page: int = 1,
        limit_topics: int = 5,
        limit_posts: int = 10,
        cache_topics: int = 3,
        refresh_mode: str = "none",
        download_images: bool = False,
        force_sync: bool = False,
        progress_callback: ProgressCallback | None = None,
    ) -> dict:
        normalized_author = author.strip()
        if not normalized_author:
            raise ValueError("Author cannot be empty")
        normalized_keyword = keyword.strip() if keyword else None
        query = self._build_author_trace_query(normalized_author, normalized_keyword)
        live_search = self.search_forum(
            query=query,
            mode="full_page",
            page=page,
            limit_topics=limit_topics,
            limit_posts=limit_posts,
        )
        topic_candidates = self._build_topic_candidates(
            live_search,
            self.config.base_url,
        )
        cached_topics_payload: list[dict] = []
        for candidate in topic_candidates[: max(cache_topics, 0)]:
            topic_id = candidate["topic_id"]
            payload = {
                "topic_id": topic_id,
                "topic_title": candidate["topic_title"],
                "topic_url": candidate["topic_url"],
                "live_post_hits": candidate["live_post_hits"],
                "latest_live_hit_at": candidate["latest_live_hit_at"],
                "ensure_cache": None,
                "cached_query": None,
                "error": None,
            }
            try:
                ensure_result = self.ensure_topic_cached(
                    topic=topic_id,
                    refresh_mode=refresh_mode,
                    download_images=download_images,
                    force=force_sync,
                    progress_callback=progress_callback,
                )
                payload["ensure_cache"] = self._summarize_ensure_result(ensure_result)
                payload["cached_query"] = self.query_topic_posts(
                    topic=topic_id,
                    keyword=normalized_keyword,
                    author=normalized_author,
                    limit=limit_posts,
                    order="desc",
                    include_images=False,
                    ensure_cached=False,
                )
            except Exception as exc:
                payload["error"] = str(exc)
            cached_topics_payload.append(payload)

        return {
            "author": normalized_author,
            "keyword": normalized_keyword,
            "query": query,
            "live_search": live_search,
            "topic_candidates": topic_candidates,
            "cached_topics": cached_topics_payload,
        }

    def ensure_topic_cached(
        self,
        topic: str | int,
        refresh_mode: str = "none",
        download_images: bool = True,
        force: bool = False,
        progress_callback: ProgressCallback | None = None,
    ) -> dict:
        inspect_before = self.inspect_topic(topic)
        cache_hit_before = inspect_before["usable_for_analysis"]
        sync_executed = False
        sync_result = None
        effective_mode = refresh_mode

        if refresh_mode != "none" or not cache_hit_before:
            effective_mode = refresh_mode if refresh_mode != "none" else "incremental"
            self._emit_progress(
                progress_callback,
                "starting cache sync: "
                f"mode={effective_mode}, "
                f"images={'on' if download_images else 'off'}, "
                f"force={'yes' if force else 'no'}",
            )
            service = TopicSyncService(self.config)
            try:
                result = service.sync_topic(
                    topic=topic,
                    mode=effective_mode,
                    with_images=download_images,
                    force=force,
                    progress_callback=progress_callback,
                )
                sync_result = asdict(result)
            finally:
                service.close()
            sync_executed = True
        else:
            self._emit_progress(
                progress_callback,
                "cache already ready for analysis; skipping sync",
            )

        inspect_after = self.inspect_topic(topic)
        if sync_executed:
            self._emit_progress(
                progress_callback,
                "cache inspection after sync: "
                f"analysis_ready={'yes' if inspect_after['usable_for_analysis'] else 'no'}, "
                f"export_ready={'yes' if inspect_after['usable_for_export'] else 'no'}, "
                f"db_posts={inspect_after['db_post_count']}, "
                f"json_pages={inspect_after['json_page_count']}, "
                f"raw_pages={inspect_after['raw_page_count']}",
            )

        return {
            "topic_id": TopicFetcher.resolve_topic_id(topic),
            "cache_hit_before": cache_hit_before,
            "cache_ready_after": inspect_after["usable_for_analysis"],
            "sync_executed": sync_executed,
            "effective_mode": effective_mode,
            "sync_result": sync_result,
            "inspect_before": inspect_before,
            "inspect_after": inspect_after,
        }

    def query_topic_posts(
        self,
        topic: str | int,
        keyword: str | None = None,
        author: str | None = None,
        only_op: bool = False,
        date_from: str | None = None,
        date_to: str | None = None,
        has_images: bool | None = None,
        limit: int | None = 50,
        offset: int = 0,
        order: str = "asc",
        include_images: bool = True,
        ensure_cached: bool = True,
        refresh_mode: str = "none",
        download_images: bool = True,
        force_sync: bool = False,
        progress_callback: ProgressCallback | None = None,
    ) -> dict:
        ensure_result = (
            self.ensure_topic_cached(
                topic,
                refresh_mode=refresh_mode,
                download_images=download_images,
                force=force_sync,
                progress_callback=progress_callback,
            )
            if ensure_cached
            else None
        )
        resolved_topic_id = TopicFetcher.resolve_topic_id(topic)
        service = TopicQueryService(self.config)
        try:
            op_username = (
                service._get_op_username(resolved_topic_id) if only_op else None
            )
            if only_op and not op_username:
                rows = []
                total_hits = 0
            else:
                rows, total_hits = service._fetch_rows(
                    topic_id=resolved_topic_id,
                    keyword=keyword,
                    author=author,
                    op_username=op_username,
                    date_from=date_from,
                    date_to=date_to,
                    has_images=has_images,
                    limit=limit,
                    offset=offset,
                    order=order,
                )
            image_map = (
                service._load_image_paths(
                    resolved_topic_id, [row["post_number"] for row in rows]
                )
                if include_images and rows
                else {}
            )
        finally:
            service.close()

        inspect_payload = self.inspect_topic(resolved_topic_id)
        items = [
            self._serialize_post(row, image_map.get(row["post_number"], []))
            for row in rows
        ]
        return {
            "topic_id": resolved_topic_id,
            "title": inspect_payload.get("title") or f"topic-{resolved_topic_id}",
            "total_hits": total_hits,
            "ensure_cache": ensure_result,
            "posts": items,
        }

    def summarize_topic(
        self,
        topic: str | int,
        only_op: bool = False,
        recent_days: int | None = None,
        focus_keywords: list[str] | None = None,
        include_images: bool = False,
        ensure_cached: bool = True,
        refresh_mode: str = "none",
        download_images: bool = True,
        force_sync: bool = False,
        progress_callback: ProgressCallback | None = None,
    ) -> dict:
        ensure_result = (
            self.ensure_topic_cached(
                topic,
                refresh_mode=refresh_mode,
                download_images=download_images,
                force=force_sync,
                progress_callback=progress_callback,
            )
            if ensure_cached
            else None
        )
        service = TopicSummaryService(self.config)
        try:
            result = service.summarize_topic(
                topic_id=topic,
                only_op=only_op,
                recent_days=recent_days,
                focus_keywords=focus_keywords,
                include_images=include_images,
            )
        finally:
            service.close()
        payload = asdict(result)
        payload["summary"] = payload.pop("summary_text")
        payload["ensure_cache"] = ensure_result
        return payload

    def export_topic_markdown(
        self,
        topic: str | int,
        save_dir: str | Path | None = None,
        ensure_cached: bool = True,
        refresh_mode: str = "none",
        download_images: bool = True,
        force_sync: bool = False,
        progress_callback: ProgressCallback | None = None,
    ) -> dict:
        ensure_result = (
            self.ensure_topic_cached(
                topic,
                refresh_mode=refresh_mode,
                download_images=download_images,
                force=force_sync,
                progress_callback=progress_callback,
            )
            if ensure_cached
            else None
        )
        resolved_save_dir = (
            Path(save_dir).expanduser().resolve() if save_dir else self.export_root
        )
        resolved_save_dir.mkdir(parents=True, exist_ok=True)
        result = export_topic(
            topic=topic,
            save_dir=str(resolved_save_dir),
            cache_root=str(self.config.cache_root),
            cookie_path=str(self.config.cookie_path),
            progress_callback=progress_callback,
        )
        payload = asdict(result)
        payload["save_dir"] = str(resolved_save_dir)
        payload["ensure_cache"] = ensure_result
        return payload

    @staticmethod
    def _serialize_post(row, image_paths: list[str]) -> dict:
        raw_markdown = row["raw_markdown"] or ""
        return {
            "post_id": row["post_id"],
            "post_number": row["post_number"],
            "username": row["username"],
            "display_name": row["display_name"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "plain_text": row["plain_text"],
            "image_paths": image_paths,
            "image_count": row["image_count"] or 0,
            "score": (
                row["score"]
                if "score" in row.keys() and row["score"] is not None
                else None
            ),
            "reply_to_post_number": row["reply_to_post_number"],
            "is_op": bool(row["is_op"]),
            "like_count": row["like_count"],
            "has_images": bool(row["has_images"]),
            "has_attachments": bool(row["has_attachments"]),
            "has_audio": bool(row["has_audio"]),
            "has_video": bool(row["has_video"]),
            "quote_targets": ShuiyuanSkillAPI._extract_quote_targets(raw_markdown),
        }

    @staticmethod
    def _extract_quote_targets(raw_markdown: str) -> list[dict]:
        targets: list[dict] = []
        seen: set[tuple[int, int | None]] = set()
        for match in _QUOTE_TARGET_RE.finditer(raw_markdown):
            topic_id = int(match.group(1))
            post_number = int(match.group(2)) if match.group(2) else None
            key = (topic_id, post_number)
            if key in seen:
                continue
            seen.add(key)
            targets.append(
                {
                    "topic_id": topic_id,
                    "post_number": post_number,
                    "url": match.group(0),
                }
            )
        return targets

    @staticmethod
    def _build_author_trace_query(author: str, keyword: str | None) -> str:
        parts = []
        if keyword:
            parts.append(keyword)
        parts.extend([f"user:{author}", "order:latest"])
        return " ".join(parts)

    @staticmethod
    def _build_topic_candidates(
        live_search: dict,
        base_url: str,
    ) -> list[dict]:
        candidates: dict[int, dict] = {}
        for topic in live_search.get("topics", []):
            topic_id = topic.get("id")
            if topic_id is None:
                continue
            candidates[topic_id] = {
                "topic_id": topic_id,
                "topic_title": topic.get("title"),
                "topic_url": topic.get("url"),
                "live_post_hits": 0,
                "latest_live_hit_at": None,
            }
        for post in live_search.get("posts", []):
            topic_id = post.get("topic_id")
            if topic_id is None:
                continue
            entry = candidates.setdefault(
                topic_id,
                {
                    "topic_id": topic_id,
                    "topic_title": post.get("topic_title"),
                    "topic_url": None,
                    "live_post_hits": 0,
                    "latest_live_hit_at": None,
                },
            )
            entry["topic_title"] = entry.get("topic_title") or post.get("topic_title")
            entry["topic_url"] = entry.get("topic_url") or ShuiyuanSkillAPI._topic_url(
                base_url,
                topic_id,
                post.get("topic_slug") or "topic",
            )
            entry["live_post_hits"] += 1
            created_at = post.get("created_at")
            if created_at and (
                not entry["latest_live_hit_at"]
                or created_at > entry["latest_live_hit_at"]
            ):
                entry["latest_live_hit_at"] = created_at
        return sorted(
            candidates.values(),
            key=lambda item: (
                item.get("live_post_hits", 0),
                item.get("latest_live_hit_at") or "",
                item.get("topic_id", 0),
            ),
            reverse=True,
        )

    @staticmethod
    def _summarize_ensure_result(payload: dict) -> dict:
        return {
            "topic_id": payload.get("topic_id"),
            "cache_hit_before": payload.get("cache_hit_before"),
            "cache_ready_after": payload.get("cache_ready_after"),
            "sync_executed": payload.get("sync_executed"),
            "effective_mode": payload.get("effective_mode"),
        }

    @staticmethod
    def _topic_url(base_url: str, topic_id: int, slug: str = "topic") -> str:
        return f"{base_url.rstrip('/')}/t/{slug}/{topic_id}"

    @staticmethod
    def _emit_progress(
        progress_callback: ProgressCallback | None,
        message: str,
    ) -> None:
        if progress_callback is not None:
            progress_callback(message)
