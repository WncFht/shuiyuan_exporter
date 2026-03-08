import argparse
import json
from dataclasses import asdict
from pathlib import Path

from shuiyuan_cache.analysis.topic_summary import TopicSummaryService
from shuiyuan_cache.core.config import CacheConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Summarize cached Shuiyuan topic content.')
    parser.add_argument('topic', help='Topic id or Shuiyuan topic URL')
    parser.add_argument('--cache-root', default='cache', help='Local cache root directory')
    parser.add_argument('--only-op', action='store_true', help='Only summarize the original poster')
    parser.add_argument('--recent-days', type=int, help='Only summarize posts in the most recent N days')
    parser.add_argument('--focus-keyword', action='append', default=[], help='Keyword to count in the summary')
    parser.add_argument('--include-images', action='store_true', help='Include image paths in underlying query context')
    parser.add_argument('--json', action='store_true', help='Output JSON')
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    service = TopicSummaryService(CacheConfig(cache_root=Path(args.cache_root)))
    try:
        summary = service.summarize_topic(
            topic_id=args.topic,
            only_op=args.only_op,
            recent_days=args.recent_days,
            focus_keywords=args.focus_keyword,
            include_images=args.include_images,
        )
    finally:
        service.close()

    if args.json:
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
        return 0

    print(f'topic_id: {summary.topic_id}')
    print(f'title: {summary.title}')
    print(f'time_range: {summary.time_range}')
    print(f'post_count_in_scope: {summary.post_count_in_scope}')
    print(f'summary: {summary.summary_text}')
    if summary.top_authors:
        print('top_authors:')
        for name, count in summary.top_authors:
            print(f'- {name}: {count}')
    if summary.top_keywords:
        print('top_keywords:')
        for name, count in summary.top_keywords:
            print(f'- {name}: {count}')
    if summary.key_posts:
        print('key_posts: ' + ', '.join(f'#{post_no}' for post_no in summary.key_posts))
    if summary.image_post_numbers:
        print('image_posts: ' + ', '.join(f'#{post_no}' for post_no in summary.image_post_numbers))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
