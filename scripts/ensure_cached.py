#!/usr/bin/env python3
from __future__ import annotations

import argparse

from common import add_runtime_args, print_json
from shuiyuan_cache.skill_api import ShuiyuanSkillAPI


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Ensure a Shuiyuan topic exists in the skill cache.')
    parser.add_argument('topic', help='Topic id or Shuiyuan topic URL')
    parser.add_argument(
        '--refresh-mode',
        choices=['none', 'incremental', 'refresh-tail', 'full'],
        default='none',
        help='Refresh behavior when checking cache state',
    )
    parser.add_argument('--no-images', action='store_true', help='Skip image download if sync runs')
    parser.add_argument('--force', action='store_true', help='Force sync even if topic looks unchanged')
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
        api.ensure_topic_cached(
            topic=args.topic,
            refresh_mode=args.refresh_mode,
            download_images=not args.no_images,
            force=args.force,
        )
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
