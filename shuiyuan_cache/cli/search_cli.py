import argparse
import json
from pathlib import Path

from shuiyuan_cache.core.config import CacheConfig
from shuiyuan_cache.fetch.search_fetcher import ForumSearchFetcher
from shuiyuan_cache.skill_api.runtime import (
    default_skill_cache_root,
    default_skill_cookie_path,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Search live Shuiyuan topics and posts.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("query", help="Search query")
    parser.add_argument(
        "--mode",
        choices=["header", "full-page"],
        default="header",
        help="Use quick header search or full-page Discourse search",
    )
    parser.add_argument(
        "--page", type=int, default=1, help="Full-page search result page"
    )
    parser.add_argument(
        "--context-type",
        choices=["user", "topic", "category", "tag", "private_messages"],
        help="Optional Discourse search context type",
    )
    parser.add_argument(
        "--context-id",
        help="Optional search context identifier (username, topic id, category id, tag)",
    )
    parser.add_argument(
        "--cache-root",
        default=str(default_skill_cache_root()),
        help="Local cache root directory",
    )
    parser.add_argument(
        "--cookie-path",
        default=str(default_skill_cookie_path()),
        help="Fallback cookie file path",
    )
    parser.add_argument(
        "--base-url", default="https://shuiyuan.sjtu.edu.cn", help="Shuiyuan base URL"
    )
    parser.add_argument(
        "--limit-topics", type=int, default=5, help="Maximum topics to return"
    )
    parser.add_argument(
        "--limit-posts", type=int, default=5, help="Maximum posts to return"
    )
    parser.add_argument("--topic-only", action="store_true", help="Hide post hits")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    fetcher = ForumSearchFetcher(
        CacheConfig(
            cache_root=Path(args.cache_root),
            cookie_path=Path(args.cookie_path),
            base_url=args.base_url,
        )
    )
    try:
        payload = fetcher.search(
            query=args.query,
            mode=args.mode,
            page=args.page,
            limit_topics=args.limit_topics,
            limit_posts=0 if args.topic_only else args.limit_posts,
            search_context_type=args.context_type,
            search_context_id=args.context_id,
        )
    finally:
        fetcher.close()

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"mode: {payload['mode']}")
    print(f"query: {payload['query']}")
    if payload["search_context"]:
        print(f"search_context: {payload['search_context']}")
    print(f"topic_count: {payload['topic_count']}")
    for item in payload["topics"]:
        print("---")
        print(f"topic: {item['title']}")
        print(f"url: {item['url']}")
    if not args.topic_only:
        print(f"post_count: {payload['post_count']}")
        for item in payload["posts"]:
            print("---")
            print(f"post: {item['url']}")
            print(f"username: {item['username']}")
            print(f"blurb: {(item['blurb'] or '').strip()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
