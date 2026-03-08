#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shuiyuan_cache.skill_api.runtime import (
    default_skill_cache_root,
    default_skill_cookie_path,
    default_skill_export_root,
)


def add_runtime_args(parser: argparse.ArgumentParser, *, include_export_root: bool = False) -> None:
    parser.add_argument(
        '--cache-root',
        default=str(default_skill_cache_root()),
        help='Skill runtime cache root',
    )
    parser.add_argument(
        '--cookie-path',
        default=str(default_skill_cookie_path()),
        help='Fallback cookie file path',
    )
    parser.add_argument(
        '--base-url',
        default='https://shuiyuan.sjtu.edu.cn',
        help='Shuiyuan base URL',
    )
    if include_export_root:
        parser.add_argument(
            '--export-root',
            default=str(default_skill_export_root()),
            help='Markdown export root',
        )


def print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
