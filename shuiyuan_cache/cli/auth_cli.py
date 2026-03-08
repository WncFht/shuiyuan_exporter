import argparse
import json
from dataclasses import asdict
from pathlib import Path

from shuiyuan_cache.auth.browser_auth import BrowserAuthManager
from shuiyuan_cache.core.config import CacheConfig
from shuiyuan_cache.skill_api.runtime import (
    default_skill_cache_root,
    default_skill_cookie_path,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Manage dedicated browser auth for Shuiyuan. Defaults target the "
            "external skill runtime under ~/.local/share/shuiyuan-cache-skill/."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup_parser = subparsers.add_parser(
        "setup", help="Open a dedicated browser profile and save auth state"
    )
    _add_common_args(setup_parser)
    setup_parser.add_argument(
        "--browser", choices=["edge", "chrome", "chromium"], default="edge"
    )
    setup_parser.add_argument(
        "--login-url",
        help="Initial URL to open for manual login; defaults to <base-url>/latest",
    )
    setup_parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser headless (not recommended for manual login)",
    )

    refresh_parser = subparsers.add_parser(
        "refresh", help="Reuse the dedicated browser profile and re-export auth files"
    )
    _add_common_args(refresh_parser)
    refresh_parser.add_argument(
        "--browser", choices=["edge", "chrome", "chromium"], default="edge"
    )
    refresh_parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser headless while refreshing the saved state",
    )

    status_parser = subparsers.add_parser(
        "status", help="Show current auth file status"
    )
    _add_common_args(status_parser)
    status_parser.add_argument(
        "--check-live",
        action="store_true",
        help="Verify the saved auth state against a live Shuiyuan request",
    )
    status_parser.add_argument("--json", action="store_true", help="Output JSON")
    return parser


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--cache-root",
        default=str(default_skill_cache_root()),
        help="Local cache root directory",
    )
    parser.add_argument(
        "--cookie-path",
        default=str(default_skill_cookie_path()),
        help="Cookie file path",
    )
    parser.add_argument(
        "--base-url", default="https://shuiyuan.sjtu.edu.cn", help="Shuiyuan base URL"
    )


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    config = CacheConfig(
        cache_root=Path(args.cache_root),
        cookie_path=Path(args.cookie_path),
        base_url=args.base_url,
    )
    manager = BrowserAuthManager(config)

    if args.command == "status":
        payload = manager.auth_status(check_live=args.check_live)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        for key, value in payload.items():
            print(f"{key}: {value}")
        return 0

    if args.command == "setup":
        result = manager.setup_interactive(
            browser=args.browser,
            login_url=args.login_url,
            headless=args.headless,
        )
    else:
        result = manager.refresh_from_profile(
            browser=args.browser,
            headless=args.headless,
        )

    payload = asdict(result)
    for key, value in payload.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
