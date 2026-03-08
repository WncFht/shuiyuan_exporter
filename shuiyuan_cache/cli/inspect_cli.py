import argparse
import json
from dataclasses import asdict
from pathlib import Path

from shuiyuan_cache.analysis.inspect_service import TopicInspectService
from shuiyuan_cache.core.config import CacheConfig
from shuiyuan_cache.skill_api.runtime import default_skill_cache_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect cached Shuiyuan topic state.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("topic", help="Topic id or Shuiyuan topic URL")
    parser.add_argument(
        "--cache-root",
        default=str(default_skill_cache_root()),
        help="Local cache root directory",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    service = TopicInspectService(CacheConfig(cache_root=Path(args.cache_root)))
    try:
        result = service.inspect_topic(args.topic)
    finally:
        service.close()

    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
        return 0

    print(f"topic_id: {result.topic_id}")
    print(f"title: {result.title}")
    print(f"topic_posts_count: {result.topic_posts_count}")
    print(f"db_post_count: {result.db_post_count}")
    print(f"json_page_count: {result.json_page_count}")
    print(f"raw_page_count: {result.raw_page_count}")
    print(f"media_image_count: {result.media_image_count}")
    print(f"image_file_count: {result.image_file_count}")
    print(f"last_posted_at: {result.last_posted_at}")
    print(f"last_sync_status: {result.last_sync_status}")
    print(f"last_sync_mode: {result.last_sync_mode}")
    print(f"last_sync_finished_at: {result.last_sync_finished_at}")
    print(f"cache_path: {result.cache_path}")
    if result.issues:
        print("issues:")
        for issue in result.issues:
            print(f"- {issue}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
