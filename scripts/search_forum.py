#!/usr/bin/env python3
from __future__ import annotations

import argparse

from common import add_runtime_args, print_json
from shuiyuan_cache.skill_api import ShuiyuanSkillAPI


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Search live Shuiyuan topics and posts for the skill runtime."
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
        "--limit-topics", type=int, default=5, help="Maximum topics to return"
    )
    parser.add_argument(
        "--limit-posts", type=int, default=5, help="Maximum posts to return"
    )
    parser.add_argument("--topic-only", action="store_true", help="Hide post hits")
    add_runtime_args(parser)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    api = ShuiyuanSkillAPI.from_runtime(
        cache_root=args.cache_root,
        cookie_path=args.cookie_path,
        base_url=args.base_url,
    )
    print_json(
        api.search_forum(
            query=args.query,
            mode=args.mode,
            page=args.page,
            limit_topics=args.limit_topics,
            limit_posts=0 if args.topic_only else args.limit_posts,
            search_context_type=args.context_type,
            search_context_id=args.context_id,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
