#!/usr/bin/env python3
from __future__ import annotations

import argparse

from common import add_runtime_args, print_json
from shuiyuan_cache.skill_api import ShuiyuanSkillAPI


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect Shuiyuan topic cache state for the skill runtime."
    )
    parser.add_argument("topic", help="Topic id or Shuiyuan topic URL")
    add_runtime_args(parser)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    api = ShuiyuanSkillAPI.from_runtime(
        cache_root=args.cache_root,
        cookie_path=args.cookie_path,
        base_url=args.base_url,
    )
    print_json(api.inspect_topic(args.topic))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
