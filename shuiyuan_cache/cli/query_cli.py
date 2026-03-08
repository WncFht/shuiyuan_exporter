import argparse
import json
from dataclasses import asdict
from pathlib import Path

from shuiyuan_cache.analysis.post_query import TopicQueryService
from shuiyuan_cache.core.config import CacheConfig
from shuiyuan_cache.skill_api.runtime import default_skill_cache_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Query cached Shuiyuan topic posts.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("topic", help="Topic id or Shuiyuan topic URL")
    parser.add_argument(
        "--cache-root",
        default=str(default_skill_cache_root()),
        help="Local cache root directory",
    )
    parser.add_argument("--keyword", help="Keyword to search in cached posts")
    parser.add_argument("--author", help="Filter by username")
    parser.add_argument(
        "--only-op",
        action="store_true",
        help="Only include posts by the original poster",
    )
    parser.add_argument(
        "--date-from", help="Lower bound date/time (ISO date or datetime)"
    )
    parser.add_argument(
        "--date-to", help="Upper bound date/time (ISO date or datetime)"
    )
    parser.add_argument(
        "--has-images", action="store_true", help="Only include posts with images"
    )
    parser.add_argument(
        "--limit", type=int, default=20, help="Maximum number of posts to return"
    )
    parser.add_argument("--offset", type=int, default=0, help="Offset for pagination")
    parser.add_argument("--order", choices=["asc", "desc"], default="asc")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    service = TopicQueryService(CacheConfig(cache_root=Path(args.cache_root)))
    try:
        result = service.query_topic_posts(
            topic_id=args.topic,
            keyword=args.keyword,
            author=args.author,
            only_op=args.only_op,
            date_from=args.date_from,
            date_to=args.date_to,
            has_images=True if args.has_images else None,
            limit=args.limit,
            offset=args.offset,
            order=args.order,
            include_images=True,
        )
    finally:
        service.close()

    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
        return 0

    print(f"topic_id: {result.topic_id}")
    print(f"total_hits: {result.total_hits}")
    for item in result.items:
        print("---")
        print(f"post_number: #{item.post_number}")
        print(f"username: {item.username}")
        print(f"created_at: {item.created_at}")
        print(f"image_count: {item.image_count}")
        if item.image_paths:
            print("image_paths:")
            for path in item.image_paths:
                print(f"- {path}")
        text = (item.plain_text or "").strip().replace("\n", " ")
        print(f"text: {text[:240]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
