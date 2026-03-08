import argparse
from pathlib import Path

from shuiyuan_cache.core.config import CacheConfig
from shuiyuan_cache.core.exceptions import ShuiyuanCacheError
from shuiyuan_cache.core.progress import build_stream_progress_reporter
from shuiyuan_cache.skill_api.runtime import (
    default_skill_cache_root,
    default_skill_cookie_path,
)
from shuiyuan_cache.sync.topic_sync import TopicSyncService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sync Shuiyuan topics into local cache.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("topic", help="Topic id or Shuiyuan topic URL")
    parser.add_argument(
        "--mode", choices=["full", "incremental", "refresh-tail"], default="incremental"
    )
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
    parser.add_argument("--no-images", action="store_true", help="Skip image download")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force sync even if topic appears unchanged",
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    config = CacheConfig(
        cache_root=Path(args.cache_root),
        cookie_path=Path(args.cookie_path),
        base_url=args.base_url,
        download_images=not args.no_images,
    )
    service = TopicSyncService(config)
    try:
        result = service.sync_topic(
            topic=args.topic,
            mode=args.mode,
            with_images=not args.no_images,
            force=args.force,
            progress_callback=build_stream_progress_reporter(prefix="sync"),
        )
    except ShuiyuanCacheError as exc:
        service.close()
        print(f"sync failed: {exc}")
        return 1
    finally:
        try:
            service.close()
        except Exception:
            pass

    print(f"topic_id: {result.topic_id}")
    print(f"title: {result.title}")
    print(f"mode: {result.mode}")
    print(f"status: {result.status}")
    print(f"fetched_json_pages: {result.fetched_json_pages}")
    print(f"fetched_raw_pages: {result.fetched_raw_pages}")
    print(f"inserted_posts: {result.inserted_posts}")
    print(f"updated_posts: {result.updated_posts}")
    print(f"inserted_media: {result.inserted_media}")
    print(f"updated_media: {result.updated_media}")
    print(f"downloaded_images: {result.downloaded_images}")
    print(f"skipped_images: {result.skipped_images}")
    if result.errors:
        print("errors:")
        for error in result.errors:
            print(f"- {error}")
    return 0 if result.status in {"success", "unchanged", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
