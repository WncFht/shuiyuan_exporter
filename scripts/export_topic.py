#!/usr/bin/env python3
from __future__ import annotations

import argparse

from common import add_runtime_args, build_progress_reporter, print_json
from shuiyuan_cache.skill_api import ShuiyuanSkillAPI


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a Shuiyuan topic as Markdown for the skill runtime."
    )
    parser.add_argument("topic", help="Topic id or Shuiyuan topic URL")
    parser.add_argument("--save-dir", help="Override the Markdown export directory")
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
    add_runtime_args(parser, include_export_root=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    api = ShuiyuanSkillAPI.from_runtime(
        cache_root=args.cache_root,
        cookie_path=args.cookie_path,
        export_root=args.export_root,
        base_url=args.base_url,
    )
    print_json(
        api.export_topic_markdown(
            topic=args.topic,
            save_dir=args.save_dir,
            ensure_cached=not args.no_ensure_cached,
            refresh_mode=args.refresh_mode,
            download_images=not args.no_images,
            force_sync=args.force_sync,
            progress_callback=build_progress_reporter("export_topic"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
