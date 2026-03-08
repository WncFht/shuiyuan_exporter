#!/usr/bin/env python3
from __future__ import annotations

import argparse

from common import add_runtime_args, build_progress_reporter, print_json
from shuiyuan_cache.skill_api import ShuiyuanSkillAPI


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Query cached Shuiyuan posts for the skill runtime."
    )
    parser.add_argument("topic", help="Topic id or Shuiyuan topic URL")
    parser.add_argument("--keyword", help="Keyword to search in cached posts")
    parser.add_argument("--author", help="Filter by username")
    parser.add_argument(
        "--only-op",
        action="store_true",
        help="Only include posts by the original poster",
    )
    parser.add_argument(
        "--date-from", help="Lower bound date/time (ISO date or datetime)"
    )
    parser.add_argument(
        "--date-to", help="Upper bound date/time (ISO date or datetime)"
    )
    parser.add_argument(
        "--has-images", action="store_true", help="Only include posts with images"
    )
    parser.add_argument(
        "--no-images-filter",
        action="store_true",
        help="Only include posts without images",
    )
    parser.add_argument(
        "--limit", type=int, default=50, help="Maximum number of posts to return"
    )
    parser.add_argument("--offset", type=int, default=0, help="Offset for pagination")
    parser.add_argument("--order", choices=["asc", "desc"], default="asc")
    parser.add_argument(
        "--no-ensure-cached",
        action="store_true",
        help="Do not auto-sync when cache is missing",
    )
    parser.add_argument(
        "--refresh-mode",
        choices=["none", "incremental", "refresh-tail", "full"],
        default="none",
        help="Refresh mode used if ensure-cache runs",
    )
    parser.add_argument(
        "--no-images", action="store_true", help="Skip image download if sync runs"
    )
    parser.add_argument(
        "--force-sync",
        action="store_true",
        help="Force sync even if topic looks unchanged",
    )
    add_runtime_args(parser)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    has_images = None
    if args.has_images:
        has_images = True
    elif args.no_images_filter:
        has_images = False
    api = ShuiyuanSkillAPI.from_runtime(
        cache_root=args.cache_root,
        cookie_path=args.cookie_path,
        base_url=args.base_url,
    )
    print_json(
        api.query_topic_posts(
            topic=args.topic,
            keyword=args.keyword,
            author=args.author,
            only_op=args.only_op,
            date_from=args.date_from,
            date_to=args.date_to,
            has_images=has_images,
            limit=args.limit,
            offset=args.offset,
            order=args.order,
            ensure_cached=not args.no_ensure_cached,
            refresh_mode=args.refresh_mode,
            download_images=not args.no_images,
            force_sync=args.force_sync,
            progress_callback=build_progress_reporter("query_topic"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
