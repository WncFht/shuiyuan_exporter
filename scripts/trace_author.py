#!/usr/bin/env python3
from __future__ import annotations

import argparse

from common import add_runtime_args, build_progress_reporter, print_json
from shuiyuan_cache.skill_api import ShuiyuanSkillAPI


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Trace a Shuiyuan author's recent history via live search and cached topic queries."
    )
    parser.add_argument("author", help="Shuiyuan username to trace")
    parser.add_argument(
        "--keyword", help="Optional extra keyword added to the author trace query"
    )
    parser.add_argument(
        "--page", type=int, default=1, help="Full-page search result page"
    )
    parser.add_argument(
        "--limit-topics", type=int, default=5, help="Maximum live topic hits to keep"
    )
    parser.add_argument(
        "--limit-posts", type=int, default=10, help="Maximum live/cached posts to keep"
    )
    parser.add_argument(
        "--cache-topics",
        type=int,
        default=3,
        help="Automatically cache the top N topic candidates for exact local author queries",
    )
    parser.add_argument(
        "--refresh-mode",
        choices=["none", "incremental", "refresh-tail", "full"],
        default="none",
        help="Refresh mode used when auto-caching topic candidates",
    )
    parser.add_argument(
        "--no-images", action="store_true", help="Skip image download if sync runs"
    )
    parser.add_argument(
        "--force-sync",
        action="store_true",
        help="Force topic sync when auto-caching candidates",
    )
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
        api.trace_author(
            author=args.author,
            keyword=args.keyword,
            page=args.page,
            limit_topics=args.limit_topics,
            limit_posts=args.limit_posts,
            cache_topics=args.cache_topics,
            refresh_mode=args.refresh_mode,
            download_images=not args.no_images,
            force_sync=args.force_sync,
            progress_callback=build_progress_reporter("trace_author"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
