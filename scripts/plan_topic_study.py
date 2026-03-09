#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from common import add_runtime_args, build_progress_reporter, print_json
from shuiyuan_cache.fetch.topic_fetcher import TopicFetcher
from shuiyuan_cache.skill_api import ShuiyuanSkillAPI


KEYWORDS = [
    "科技",
    "软件",
    "中国软件",
    "券商",
    "证券",
    "银行",
    "创新药",
    "医药",
    "军工",
    "机器人",
    "有色",
    "资源",
    "黄金",
    "光伏",
    "消费",
    "芯片",
    "半导体",
    "港股",
    "美股",
    "石油",
    "红利",
    "etf",
    "量化",
    "大盘",
    "指数",
    "仓位",
    "止盈",
    "止损",
    "空仓",
    "建仓",
    "加仓",
    "减仓",
    "低吸",
    "反弹",
    "轮动",
    "情绪",
    "主线",
]

PRIORITY_WORDS = [
    "收益率",
    "交割单",
    "总结",
    "仓位",
    "止盈",
    "止损",
    "空仓",
    "建仓",
    "加仓",
    "减仓",
    "大盘",
    "指数",
    "科技",
    "银行",
    "医药",
    "军工",
    "石油",
    "券商",
    "量化",
    "etf",
    "港股",
    "美股",
    "反弹",
    "轮动",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a weekly/monthly study plan for a cached Shuiyuan topic."
    )
    parser.add_argument("topic", help="Topic id or Shuiyuan topic URL")
    parser.add_argument(
        "--granularity",
        choices=["week", "month"],
        default="week",
        help="Timeline bucket granularity",
    )
    parser.add_argument(
        "--timezone",
        default="Asia/Shanghai",
        help="Timezone used for bucket boundaries",
    )
    parser.add_argument(
        "--limit-key-posts",
        type=int,
        default=3,
        help="Maximum key posts returned per bucket",
    )
    parser.add_argument(
        "--prefer-op-images",
        action="store_true",
        help="Prefer representative images from the original poster",
    )
    parser.add_argument(
        "--min-image-bytes",
        type=int,
        default=8192,
        help="Penalty threshold for tiny images such as emoji or UI fragments",
    )
    parser.add_argument(
        "--no-ensure-cached",
        action="store_true",
        help="Do not auto-sync when cache is missing",
    )
    parser.add_argument(
        "--refresh-mode",
        choices=["none", "incremental", "refresh-tail", "full"],
        default="none",
        help="Refresh mode used if ensure-cache runs",
    )
    parser.add_argument(
        "--no-images", action="store_true", help="Skip image download if sync runs"
    )
    parser.add_argument(
        "--force-sync",
        action="store_true",
        help="Force sync even if topic looks unchanged",
    )
    add_runtime_args(parser, include_export_root=True)
    return parser


def clean_text(text: str | None) -> str:
    normalized = (text or "").replace("\n", " ")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def normalize_ext(file_ext: str | None) -> str:
    if not file_ext:
        return ".bin"
    return file_ext if file_ext.startswith(".") else f".{file_ext}"


def bucket_bounds(dt: datetime, granularity: str) -> tuple[str, str, str]:
    if granularity == "month":
        start = dt.replace(day=1).date()
        if start.month == 12:
            next_month = start.replace(year=start.year + 1, month=1, day=1)
        else:
            next_month = start.replace(month=start.month + 1, day=1)
        end = next_month - timedelta(days=1)
        return start.isoformat(), end.isoformat(), start.strftime("%Y-%m")

    start_dt = dt - timedelta(days=dt.weekday())
    start = start_dt.date()
    end = (start_dt + timedelta(days=6)).date()
    return start.isoformat(), end.isoformat(), start.isoformat()


def score_post(text: str, username: str, op_username: str) -> int:
    score = min(len(text) // 80, 8)
    if username == op_username:
        score += 10
    for word in PRIORITY_WORDS:
        if word.lower() in text.lower():
            score += 4
    if "收益率" in text:
        score += 5
    if "交割单" in text:
        score += 5
    if "总结" in text:
        score += 5
    return score


def score_image_candidate(
    text: str,
    username: str,
    op_username: str,
    prefer_op_images: bool,
    path: Path,
    resolved_url: str | None,
    min_image_bytes: int,
) -> int:
    score = score_post(text=text, username=username, op_username=op_username)
    if username == op_username:
        score += 12 if prefer_op_images else 6
    size = path.stat().st_size if path.exists() else 0
    if size >= 150_000:
        score += 8
    elif size >= 50_000:
        score += 5
    elif size >= min_image_bytes:
        score += 2
    else:
        score -= 30
    lowered_url = (resolved_url or "").lower()
    if "/emoji/" in lowered_url:
        score -= 80
    return score


def build_topic_study_plan(args: argparse.Namespace) -> dict:
    api = ShuiyuanSkillAPI.from_runtime(
        cache_root=args.cache_root,
        cookie_path=args.cookie_path,
        export_root=args.export_root,
        base_url=args.base_url,
    )

    ensure_result = (
        api.ensure_topic_cached(
            topic=args.topic,
            refresh_mode=args.refresh_mode,
            download_images=not args.no_images,
            force=args.force_sync,
            progress_callback=build_progress_reporter("plan_topic_study"),
        )
        if not args.no_ensure_cached
        else None
    )

    topic_id = TopicFetcher.resolve_topic_id(args.topic)
    timezone = ZoneInfo(args.timezone)
    conn = sqlite3.connect(api.config.db_path)
    conn.row_factory = sqlite3.Row
    try:
        topic_row = conn.execute(
            "SELECT title FROM topics WHERE topic_id = ?", (topic_id,)
        ).fetchone()
        post_rows = conn.execute(
            """
            SELECT post_id, post_number, username, created_at, plain_text
            FROM posts
            WHERE topic_id = ?
            ORDER BY created_at, post_number
            """,
            (topic_id,),
        ).fetchall()
        image_rows = conn.execute(
            """
            SELECT p.post_number, p.username, p.created_at, p.plain_text,
                   m.media_key, m.file_ext, m.local_path, m.resolved_url
            FROM posts p
            JOIN media m ON p.post_id = m.post_id
            WHERE p.topic_id = ?
              AND m.media_type = 'image'
            ORDER BY p.created_at, p.post_number, m.media_id
            """,
            (topic_id,),
        ).fetchall()
    finally:
        conn.close()

    if not post_rows:
        raise ValueError(f"No cached posts found for topic #{topic_id}")

    title = topic_row["title"] if topic_row else None
    op_username = post_rows[0]["username"]
    export_topic_dir = Path(api.export_root) / str(topic_id)
    export_images_dir = export_topic_dir / "images"

    buckets: dict[str, dict] = {}
    bucket_posts: dict[str, list[dict]] = defaultdict(list)
    for row in post_rows:
        dt = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
        local_dt = dt.astimezone(timezone)
        bucket_start, bucket_end, bucket_label = bucket_bounds(
            local_dt, args.granularity
        )
        buckets.setdefault(
            bucket_start,
            {
                "bucket_start": bucket_start,
                "bucket_end": bucket_end,
                "label": bucket_label,
            },
        )
        bucket_posts[bucket_start].append(
            {
                "post_number": row["post_number"],
                "username": row["username"],
                "plain_text": clean_text(row["plain_text"]),
            }
        )

    bucket_images: dict[str, list[dict]] = defaultdict(list)
    for row in image_rows:
        dt = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
        local_dt = dt.astimezone(timezone)
        bucket_start, _, _ = bucket_bounds(local_dt, args.granularity)

        ext = normalize_ext(row["file_ext"])
        export_path = export_images_dir / f"{row['media_key']}{ext}"
        cache_path = Path(row["local_path"]).expanduser() if row["local_path"] else None

        chosen_path = None
        source = None
        if export_path.exists() and export_path.stat().st_size > 0:
            chosen_path = export_path
            source = "export"
        elif cache_path and cache_path.exists() and cache_path.stat().st_size > 0:
            chosen_path = cache_path
            source = "cache"

        if chosen_path is None:
            continue

        text = clean_text(row["plain_text"])
        score = score_image_candidate(
            text=text,
            username=row["username"],
            op_username=op_username,
            prefer_op_images=args.prefer_op_images,
            path=chosen_path,
            resolved_url=row["resolved_url"],
            min_image_bytes=args.min_image_bytes,
        )
        bucket_images[bucket_start].append(
            {
                "post_number": row["post_number"],
                "username": row["username"],
                "snippet": text[:220],
                "image_path": str(chosen_path),
                "image_source": source,
                "score": score,
            }
        )

    output_buckets = []
    for bucket_start in sorted(buckets):
        posts = bucket_posts[bucket_start]
        authors = sorted({item["username"] for item in posts})
        op_posts = [item for item in posts if item["username"] == op_username]
        keyword_pool = op_posts or posts
        keyword_text = "\n".join(item["plain_text"].lower() for item in keyword_pool)
        keyword_hits = []
        for keyword in KEYWORDS:
            count = keyword_text.count(keyword.lower())
            if count:
                keyword_hits.append((keyword, count))
        keyword_hits.sort(key=lambda item: (-item[1], item[0]))

        scored_posts = []
        for item in posts:
            scored_posts.append(
                (
                    score_post(
                        text=item["plain_text"],
                        username=item["username"],
                        op_username=op_username,
                    ),
                    item["post_number"],
                    item,
                )
            )
        scored_posts.sort(key=lambda item: (-item[0], item[1]))

        representative_image = None
        if bucket_images[bucket_start]:
            best_image = max(
                bucket_images[bucket_start], key=lambda item: (item["score"], -item["post_number"])
            )
            representative_image = {
                "post_number": best_image["post_number"],
                "username": best_image["username"],
                "snippet": best_image["snippet"],
                "image_path": best_image["image_path"],
                "image_source": best_image["image_source"],
            }

        output_buckets.append(
            {
                **buckets[bucket_start],
                "posts": len(posts),
                "op_posts": len(op_posts),
                "authors": len(authors),
                "first_post_number": posts[0]["post_number"],
                "last_post_number": posts[-1]["post_number"],
                "top_keywords": keyword_hits[:8],
                "key_posts": [
                    {
                        "post_number": item["post_number"],
                        "username": item["username"],
                        "snippet": item["plain_text"][:220],
                    }
                    for _, _, item in scored_posts[: max(args.limit_key_posts, 1)]
                ],
                "representative_image": representative_image,
            }
        )

    return {
        "topic_id": topic_id,
        "title": title,
        "op_username": op_username,
        "granularity": args.granularity,
        "timezone": args.timezone,
        "bucket_count": len(output_buckets),
        "export_topic_dir": str(export_topic_dir),
        "buckets": output_buckets,
        "ensure_cache": ensure_result,
    }


def main() -> int:
    args = build_parser().parse_args()
    print_json(build_topic_study_plan(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
