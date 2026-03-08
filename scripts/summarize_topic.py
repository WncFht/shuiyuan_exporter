#!/usr/bin/env python3
from __future__ import annotations

import argparse

from common import add_runtime_args, build_progress_reporter, print_json
from shuiyuan_cache.skill_api import ShuiyuanSkillAPI


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Summarize a cached Shuiyuan topic for the skill runtime."
    )
    parser.add_argument("topic", help="Topic id or Shuiyuan topic URL")
    parser.add_argument(
        "--only-op", action="store_true", help="Only summarize the original poster"
    )
    parser.add_argument(
        "--recent-days", type=int, help="Only summarize posts in the most recent N days"
    )
    parser.add_argument(
        "--focus-keyword",
        action="append",
        dest="focus_keywords",
        help="Keyword to count in the summary",
    )
    parser.add_argument(
        "--include-images",
        action="store_true",
        help="Include image paths in the underlying query context",
    )
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
    api = ShuiyuanSkillAPI.from_runtime(
        cache_root=args.cache_root,
        cookie_path=args.cookie_path,
        base_url=args.base_url,
    )
    print_json(
        api.summarize_topic(
            topic=args.topic,
            only_op=args.only_op,
            recent_days=args.recent_days,
            focus_keywords=args.focus_keywords,
            include_images=args.include_images,
            ensure_cached=not args.no_ensure_cached,
            refresh_mode=args.refresh_mode,
            download_images=not args.no_images,
            force_sync=args.force_sync,
            progress_callback=build_progress_reporter("summarize_topic"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
