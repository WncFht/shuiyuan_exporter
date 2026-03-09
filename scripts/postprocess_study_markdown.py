#!/usr/bin/env python3
from __future__ import annotations

import argparse

from common import print_json
from shuiyuan_cache.export.study_markdown import rewrite_study_markdown_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Normalize study-note image markup for Markdown rendering."
    )
    parser.add_argument("paths", nargs="+", help="Study Markdown file(s) to rewrite")
    parser.add_argument(
        "--width",
        type=int,
        default=320,
        help="Default inline image width used for rendered notes",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report pending rewrites without modifying files",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    results = [
        rewrite_study_markdown_file(path, default_width=args.width, write=not args.check)
        for path in args.paths
    ]
    print_json(
        {
            "paths": results,
            "default_width": args.width,
            "check_only": args.check,
            "changed_count": sum(1 for item in results if item["changed"]),
            "written_count": sum(1 for item in results if item["written"]),
        }
    )
    return 1 if args.check and any(item["changed"] for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
