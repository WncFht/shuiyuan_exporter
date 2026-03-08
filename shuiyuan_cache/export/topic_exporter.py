from __future__ import annotations

import time
from pathlib import Path

from shuiyuan_cache.core.progress import ProgressCallback
from shuiyuan_cache.export.constants import default_save_dir
from shuiyuan_cache.export.export_models import TopicExportResult
from shuiyuan_cache.export.media_rewrite import MEDIA_REWRITE_STEPS
from shuiyuan_cache.export.raw_markdown import export_raw_post, normalize_topic_id
from shuiyuan_cache.export.runtime_defaults import (
    DEFAULT_EXPORT_CACHE_ROOT,
    DEFAULT_EXPORT_COOKIE_PATH,
)


def export_topic(
    topic: str | int,
    save_dir: str = default_save_dir,
    cache_root: str = DEFAULT_EXPORT_CACHE_ROOT,
    cookie_path: str = DEFAULT_EXPORT_COOKIE_PATH,
    progress_callback: ProgressCallback | None = None,
) -> TopicExportResult:
    topic_id = normalize_topic_id(topic)
    _emit_progress(progress_callback, f"topic:{topic_id} 文字备份中...")

    topic_dir = Path(save_dir) / topic_id
    topic_dir.mkdir(parents=True, exist_ok=True)

    total_started_at = time.time()
    stage_started_at = time.time()
    filename = export_raw_post(
        topic_dir,
        topic_id,
        cache_root=cache_root,
        cookie_path=cookie_path,
    )
    raw_seconds = time.time() - stage_started_at
    _emit_progress(progress_callback, f"文字爬取耗时: {raw_seconds} 秒")

    timings = {
        "image_seconds": 0.0,
        "attachment_seconds": 0.0,
        "video_seconds": 0.0,
        "audio_seconds": 0.0,
    }
    for key, label, handler in MEDIA_REWRITE_STEPS:
        stage_started_at = time.time()
        handler(
            path=f"{topic_dir}/",
            filename=filename,
            topic=topic_id,
            cache_root=cache_root,
            cookie_path=cookie_path,
            progress_callback=progress_callback,
        )
        elapsed = time.time() - stage_started_at
        timings[key] = elapsed
        _emit_progress(progress_callback, f"{label}: {elapsed} 秒")

    total_seconds = time.time() - total_started_at
    _emit_progress(
        progress_callback, f"编号为 #{topic_id} 的帖子已备份为本地文件：{filename}"
    )
    _emit_progress(progress_callback, "Exit.")
    return TopicExportResult(
        topic_id=topic_id,
        filename=filename,
        topic_dir=str(topic_dir),
        raw_seconds=raw_seconds,
        image_seconds=timings["image_seconds"],
        attachment_seconds=timings["attachment_seconds"],
        video_seconds=timings["video_seconds"],
        audio_seconds=timings["audio_seconds"],
        total_seconds=total_seconds,
    )


def _emit_progress(
    progress_callback: ProgressCallback | None,
    message: str,
) -> None:
    if progress_callback is not None:
        progress_callback(message)
