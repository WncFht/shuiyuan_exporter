#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import REPO_ROOT, print_json
from shuiyuan_cache.maintenance import (
    apply_runtime_migration,
    build_runtime_migration_report,
)
from shuiyuan_cache.skill_api.runtime import default_skill_runtime_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect and optionally migrate repo-local runtime data into the "
            "external Shuiyuan skill runtime. Default mode is dry-run."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Repository root that may still contain old runtime data",
    )
    parser.add_argument(
        "--runtime-root",
        default=str(default_skill_runtime_root()),
        help="External skill runtime root",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Execute the safe migration plan instead of only printing the report",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(args.repo_root)
    runtime_root = Path(args.runtime_root)
    if args.apply:
        print_json(
            apply_runtime_migration(repo_root=repo_root, runtime_root=runtime_root)
        )
        return 0
    print_json(
        build_runtime_migration_report(repo_root=repo_root, runtime_root=runtime_root)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
