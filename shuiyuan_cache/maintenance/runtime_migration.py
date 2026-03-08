from __future__ import annotations

import hashlib
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shuiyuan_cache.skill_api.runtime import default_skill_runtime_root


@dataclass(slots=True)
class RuntimeLayout:
    repo_root: Path
    runtime_root: Path

    @property
    def repo_cache_root(self) -> Path:
        return self.repo_root / "cache"

    @property
    def runtime_cache_root(self) -> Path:
        return self.runtime_root / "cache"

    @property
    def repo_cookie_path(self) -> Path:
        return self.repo_root / "cookies.txt"

    @property
    def runtime_cookie_path(self) -> Path:
        return self.runtime_root / "cookies.txt"

    @property
    def repo_db_path(self) -> Path:
        return self.repo_cache_root / "db" / "shuiyuan.sqlite"

    @property
    def runtime_db_path(self) -> Path:
        return self.runtime_cache_root / "db" / "shuiyuan.sqlite"

    @property
    def repo_auth_json(self) -> Path:
        return self.repo_cache_root / "auth" / "auth.json"

    @property
    def runtime_auth_json(self) -> Path:
        return self.runtime_cache_root / "auth" / "auth.json"

    @property
    def repo_browser_profile(self) -> Path:
        return self.repo_cache_root / "auth" / "browser_profile"

    @property
    def runtime_browser_profile(self) -> Path:
        return self.runtime_cache_root / "auth" / "browser_profile"

    @property
    def repo_topics_root(self) -> Path:
        return self.repo_cache_root / "raw" / "topics"

    @property
    def runtime_topics_root(self) -> Path:
        return self.runtime_cache_root / "raw" / "topics"

    @property
    def repo_post_refs_root(self) -> Path:
        return self.repo_cache_root / "raw" / "post_refs"

    @property
    def runtime_post_refs_root(self) -> Path:
        return self.runtime_cache_root / "raw" / "post_refs"

    @property
    def repo_images_root(self) -> Path:
        return self.repo_cache_root / "media" / "images"

    @property
    def runtime_images_root(self) -> Path:
        return self.runtime_cache_root / "media" / "images"

    @property
    def repo_posts_dir(self) -> Path:
        return self.repo_root / "posts"

    @property
    def repo_exports_dir(self) -> Path:
        return self.repo_root / "exports"

    @property
    def runtime_legacy_root(self) -> Path:
        return self.runtime_root / "legacy_repo_runtime"


def build_runtime_migration_report(
    repo_root: str | Path,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    layout = RuntimeLayout(
        repo_root=Path(repo_root).expanduser().resolve(),
        runtime_root=(
            Path(runtime_root).expanduser().resolve()
            if runtime_root
            else default_skill_runtime_root()
        ),
    )

    repo_topic_dirs = _list_child_dirs(layout.repo_topics_root)
    runtime_topic_dirs = _list_child_dirs(layout.runtime_topics_root)
    repo_post_ref_dirs = _list_child_dirs(layout.repo_post_refs_root)
    runtime_post_ref_dirs = _list_child_dirs(layout.runtime_post_refs_root)

    repo_only_topic_dirs = sorted(repo_topic_dirs - runtime_topic_dirs)
    runtime_only_topic_dirs = sorted(runtime_topic_dirs - repo_topic_dirs)
    common_topic_dirs = sorted(repo_topic_dirs & runtime_topic_dirs)

    repo_only_post_ref_dirs = sorted(repo_post_ref_dirs - runtime_post_ref_dirs)
    runtime_only_post_ref_dirs = sorted(runtime_post_ref_dirs - repo_post_ref_dirs)

    repo_db_topics = _list_db_topics(layout.repo_db_path)
    runtime_db_topics = _list_db_topics(layout.runtime_db_path)
    repo_only_db_topics = sorted(repo_db_topics - runtime_db_topics)
    runtime_only_db_topics = sorted(runtime_db_topics - repo_db_topics)
    common_db_topics = sorted(repo_db_topics & runtime_db_topics)
    repo_raw_only_without_db_topics = sorted(set(repo_only_topic_dirs) - repo_db_topics)

    repo_image_files = _list_relative_files(layout.repo_images_root)
    runtime_image_files = _list_relative_files(layout.runtime_images_root)
    missing_runtime_image_files = sorted(repo_image_files - runtime_image_files)

    actions: list[dict[str, Any]] = []
    manual_review: list[dict[str, Any]] = []
    cleanup_candidates: list[str] = []

    auth_json_action = _plan_file_copy(
        layout.repo_auth_json,
        layout.runtime_auth_json,
        kind="auth_json",
        reason_missing="runtime auth.json missing; safe to copy repo version",
        reason_conflict="runtime auth.json already exists; keep runtime as canonical",
    )
    _append_plan_result(actions, manual_review, auth_json_action)

    browser_profile_action = _plan_dir_copy(
        layout.repo_browser_profile,
        layout.runtime_browser_profile,
        kind="browser_profile",
        reason_missing="runtime browser_profile missing; safe to copy repo profile",
        reason_conflict="runtime browser_profile already exists; keep runtime as canonical",
    )
    _append_plan_result(actions, manual_review, browser_profile_action)

    cookie_action = _plan_file_copy(
        layout.repo_cookie_path,
        layout.runtime_cookie_path,
        kind="cookies",
        reason_missing="runtime cookies.txt missing; safe to copy repo fallback cookies",
        reason_conflict="runtime cookies.txt already exists; keep runtime as canonical",
    )
    _append_plan_result(actions, manual_review, cookie_action)

    for topic_id in repo_only_topic_dirs:
        actions.append(
            {
                "kind": "copy_topic_dir",
                "source": str(layout.repo_topics_root / topic_id),
                "target": str(layout.runtime_topics_root / topic_id),
                "topic_id": topic_id,
                "reason": "topic exists only in repo raw cache",
            }
        )

    for topic_id in repo_only_post_ref_dirs:
        actions.append(
            {
                "kind": "copy_post_ref_dir",
                "source": str(layout.repo_post_refs_root / topic_id),
                "target": str(layout.runtime_post_refs_root / topic_id),
                "topic_id": topic_id,
                "reason": "post_ref cache exists only in repo raw cache",
            }
        )

    if layout.repo_db_path.exists():
        if not layout.runtime_db_path.exists():
            actions.append(
                {
                    "kind": "copy_db",
                    "source": str(layout.repo_db_path),
                    "target": str(layout.runtime_db_path),
                    "reason": "runtime sqlite database missing; safe to copy repo database",
                }
            )
        elif repo_only_db_topics:
            actions.append(
                {
                    "kind": "merge_db_topics",
                    "source": str(layout.repo_db_path),
                    "target": str(layout.runtime_db_path),
                    "topic_ids": repo_only_db_topics,
                    "reason": "repo database contains topic rows missing from runtime database",
                }
            )

    if missing_runtime_image_files:
        actions.append(
            {
                "kind": "copy_missing_images",
                "source_root": str(layout.repo_images_root),
                "target_root": str(layout.runtime_images_root),
                "count": len(missing_runtime_image_files),
                "sample": missing_runtime_image_files[:10],
                "reason": "repo image cache has files missing from runtime image cache",
            }
        )

    if repo_raw_only_without_db_topics:
        manual_review.append(
            {
                "kind": "raw_topics_without_db_rows",
                "topic_ids": repo_raw_only_without_db_topics,
                "reason": "these topics exist in repo raw cache but not in repo sqlite; apply will copy raw files only, and query/summary may still require a later re-sync",
            }
        )

    for source_dir, name in (
        (layout.repo_posts_dir, "posts"),
        (layout.repo_exports_dir, "exports"),
    ):
        if source_dir.exists():
            target_dir = layout.runtime_legacy_root / name
            if target_dir.exists():
                manual_review.append(
                    {
                        "kind": "legacy_output_dir_conflict",
                        "source": str(source_dir),
                        "target": str(target_dir),
                        "reason": "legacy output directory already archived in runtime; manual review recommended",
                    }
                )
            else:
                actions.append(
                    {
                        "kind": "archive_legacy_output_dir",
                        "source": str(source_dir),
                        "target": str(target_dir),
                        "reason": "repo legacy output directory should be archived outside the repo",
                    }
                )

    for candidate in (
        layout.repo_cache_root,
        layout.repo_cookie_path,
        layout.repo_posts_dir,
        layout.repo_exports_dir,
    ):
        if candidate.exists():
            cleanup_candidates.append(str(candidate))

    return {
        "repo_root": str(layout.repo_root),
        "runtime_root": str(layout.runtime_root),
        "generated_at": _now_iso(),
        "status": "ready_for_safe_apply" if actions else "nothing_to_migrate",
        "summary": {
            "repo_only_topic_dirs": repo_only_topic_dirs,
            "runtime_only_topic_dirs": runtime_only_topic_dirs,
            "common_topic_dirs": common_topic_dirs,
            "repo_only_db_topics": repo_only_db_topics,
            "runtime_only_db_topics": runtime_only_db_topics,
            "common_db_topics": common_db_topics,
            "repo_raw_only_without_db_topics": repo_raw_only_without_db_topics,
            "repo_only_post_ref_dirs": repo_only_post_ref_dirs,
            "runtime_only_post_ref_dirs": runtime_only_post_ref_dirs,
            "missing_runtime_image_files": len(missing_runtime_image_files),
        },
        "path_status": {
            "repo_cache_root": _path_info(layout.repo_cache_root),
            "runtime_cache_root": _path_info(layout.runtime_cache_root),
            "repo_cookie_path": _path_info(layout.repo_cookie_path, with_hash=True),
            "runtime_cookie_path": _path_info(
                layout.runtime_cookie_path, with_hash=True
            ),
            "repo_auth_json": _path_info(layout.repo_auth_json, with_hash=True),
            "runtime_auth_json": _path_info(layout.runtime_auth_json, with_hash=True),
            "repo_browser_profile": _path_info(layout.repo_browser_profile),
            "runtime_browser_profile": _path_info(layout.runtime_browser_profile),
            "repo_db_path": _path_info(layout.repo_db_path),
            "runtime_db_path": _path_info(layout.runtime_db_path),
            "repo_posts_dir": _path_info(layout.repo_posts_dir),
            "repo_exports_dir": _path_info(layout.repo_exports_dir),
        },
        "actions": actions,
        "manual_review": manual_review,
        "cleanup_candidates": cleanup_candidates,
        "safety_notes": [
            "apply 模式只会复制缺失文件、补拷缺失目录、合并 repo-only 的 sqlite topic 数据，不会覆盖 runtime 已存在的认证或缓存。",
            "repo 内运行时目录默认不会自动删除；清理应在 dry-run 和 apply 验证通过后单独执行。",
        ],
    }


def apply_runtime_migration(
    repo_root: str | Path,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    report = build_runtime_migration_report(
        repo_root=repo_root, runtime_root=runtime_root
    )
    layout = RuntimeLayout(
        repo_root=Path(report["repo_root"]),
        runtime_root=Path(report["runtime_root"]),
    )
    executed: list[dict[str, Any]] = []

    for action in report["actions"]:
        kind = action["kind"]
        if kind in {"auth_json", "cookies", "copy_db"}:
            source = Path(action["source"])
            target = Path(action["target"])
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            executed.append({"kind": kind, "status": "copied", "target": str(target)})
            continue

        if kind in {
            "browser_profile",
            "copy_topic_dir",
            "copy_post_ref_dir",
            "archive_legacy_output_dir",
        }:
            source = Path(action["source"])
            target = Path(action["target"])
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, target)
            executed.append({"kind": kind, "status": "copied", "target": str(target)})
            continue

        if kind == "copy_missing_images":
            copied = _copy_missing_files(
                source_root=Path(action["source_root"]),
                target_root=Path(action["target_root"]),
            )
            executed.append({"kind": kind, "status": "copied", "count": copied})
            continue

        if kind == "merge_db_topics":
            merged_topics = _merge_repo_only_topics_into_runtime_db(
                repo_db=layout.repo_db_path,
                runtime_db=layout.runtime_db_path,
                topic_ids=[int(topic_id) for topic_id in action["topic_ids"]],
            )
            executed.append(
                {"kind": kind, "status": "merged", "topic_ids": merged_topics}
            )
            continue

        raise ValueError(f"Unsupported action kind: {kind}")

    report["apply_executed"] = executed
    report["applied_at"] = _now_iso()
    report["status"] = "applied"
    return report


def _plan_file_copy(
    source: Path,
    target: Path,
    *,
    kind: str,
    reason_missing: str,
    reason_conflict: str,
) -> dict[str, Any] | None:
    if not source.exists():
        return None
    if not target.exists():
        return {
            "plan_type": "action",
            "kind": kind,
            "source": str(source),
            "target": str(target),
            "reason": reason_missing,
        }
    if _small_file_hash(source) != _small_file_hash(target):
        return {
            "plan_type": "manual_review",
            "kind": f"{kind}_conflict",
            "source": str(source),
            "target": str(target),
            "reason": reason_conflict,
        }
    return None


def _plan_dir_copy(
    source: Path,
    target: Path,
    *,
    kind: str,
    reason_missing: str,
    reason_conflict: str,
) -> dict[str, Any] | None:
    if not source.exists():
        return None
    if not target.exists():
        return {
            "plan_type": "action",
            "kind": kind,
            "source": str(source),
            "target": str(target),
            "reason": reason_missing,
        }
    return {
        "plan_type": "manual_review",
        "kind": f"{kind}_conflict",
        "source": str(source),
        "target": str(target),
        "reason": reason_conflict,
    }


def _append_plan_result(
    actions: list[dict[str, Any]],
    manual_review: list[dict[str, Any]],
    result: dict[str, Any] | None,
) -> None:
    if result is None:
        return
    if result.get("plan_type") == "manual_review":
        manual_review.append(
            {key: value for key, value in result.items() if key != "plan_type"}
        )
        return
    actions.append({key: value for key, value in result.items() if key != "plan_type"})


def _path_info(path: Path, *, with_hash: bool = False) -> dict[str, Any]:
    info: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
    }
    if not path.exists():
        return info
    stat = path.stat()
    info["size"] = stat.st_size
    info["mtime"] = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    if with_hash and path.is_file() and stat.st_size <= 1024 * 1024:
        info["sha256"] = _small_file_hash(path)
    return info


def _small_file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _list_child_dirs(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {child.name for child in path.iterdir() if child.is_dir()}


def _list_relative_files(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        str(child.relative_to(path)) for child in path.rglob("*") if child.is_file()
    }


def _list_db_topics(db_path: Path) -> set[str]:
    if not db_path.exists():
        return set()
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT topic_id FROM topics").fetchall()
    finally:
        conn.close()
    return {str(row[0]) for row in rows}


def _copy_missing_files(source_root: Path, target_root: Path) -> int:
    if not source_root.exists():
        return 0
    copied = 0
    for source_file in source_root.rglob("*"):
        if not source_file.is_file():
            continue
        relative_path = source_file.relative_to(source_root)
        target_file = target_root / relative_path
        if target_file.exists():
            continue
        target_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, target_file)
        copied += 1
    return copied


def _merge_repo_only_topics_into_runtime_db(
    repo_db: Path,
    runtime_db: Path,
    topic_ids: list[int],
) -> list[int]:
    if not topic_ids:
        return []
    runtime_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(runtime_db)
    try:
        conn.execute("ATTACH DATABASE ? AS source", (str(repo_db),))
        for topic_id in topic_ids:
            conn.execute(
                """
                INSERT OR IGNORE INTO topics (
                  topic_id, title, category_id, tags_json, created_at, last_posted_at,
                  posts_count, reply_count, views, like_count, visible, archived,
                  closed, topic_json_path, created_ts, updated_ts
                )
                SELECT
                  topic_id, title, category_id, tags_json, created_at, last_posted_at,
                  posts_count, reply_count, views, like_count, visible, archived,
                  closed, topic_json_path, created_ts, updated_ts
                FROM source.topics
                WHERE topic_id = ?
                """,
                (topic_id,),
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO posts (
                  post_id, topic_id, post_number, username, display_name, created_at,
                  updated_at, reply_to_post_number, is_op, like_count, raw_markdown,
                  cooked_html, plain_text, raw_page_no, json_page_no, raw_post_path,
                  has_images, has_attachments, has_audio, has_video, image_count,
                  hash_raw, hash_cooked, created_ts, updated_ts
                )
                SELECT
                  post_id, topic_id, post_number, username, display_name, created_at,
                  updated_at, reply_to_post_number, is_op, like_count, raw_markdown,
                  cooked_html, plain_text, raw_page_no, json_page_no, raw_post_path,
                  has_images, has_attachments, has_audio, has_video, image_count,
                  hash_raw, hash_cooked, created_ts, updated_ts
                FROM source.posts
                WHERE topic_id = ?
                """,
                (topic_id,),
            )
            conn.execute(
                """
                INSERT INTO media (
                  topic_id, post_id, post_number, media_type, upload_ref, resolved_url,
                  local_path, mime_type, file_ext, media_key, download_status,
                  content_length, created_ts, updated_ts
                )
                SELECT
                  topic_id, post_id, post_number, media_type, upload_ref, resolved_url,
                  local_path, mime_type, file_ext, media_key, download_status,
                  content_length, created_ts, updated_ts
                FROM source.media
                WHERE topic_id = ?
                """,
                (topic_id,),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO sync_state (
                  topic_id, last_known_posts_count, last_known_last_posted_at,
                  last_synced_json_page, last_synced_raw_page, last_synced_post_number,
                  last_sync_mode, last_sync_status, last_sync_started_at,
                  last_sync_finished_at, last_sync_error, updated_ts
                )
                SELECT
                  topic_id, last_known_posts_count, last_known_last_posted_at,
                  last_synced_json_page, last_synced_raw_page, last_synced_post_number,
                  last_sync_mode, last_sync_status, last_sync_started_at,
                  last_sync_finished_at, last_sync_error, updated_ts
                FROM source.sync_state
                WHERE topic_id = ?
                """,
                (topic_id,),
            )
            conn.execute(
                """
                INSERT INTO post_quotes (
                  topic_id, post_id, post_number, quoted_topic_id,
                  quoted_post_number, quote_url, created_ts
                )
                SELECT
                  topic_id, post_id, post_number, quoted_topic_id,
                  quoted_post_number, quote_url, created_ts
                FROM source.post_quotes
                WHERE topic_id = ?
                """,
                (topic_id,),
            )
            conn.execute("DELETE FROM posts_fts WHERE topic_id = ?", (topic_id,))
            conn.execute(
                """
                INSERT INTO posts_fts (
                  topic_id, post_id, post_number, username, plain_text, raw_markdown
                )
                SELECT
                  topic_id, post_id, post_number, username, plain_text, raw_markdown
                FROM posts
                WHERE topic_id = ?
                """,
                (topic_id,),
            )
        conn.commit()
        conn.execute("DETACH DATABASE source")
    finally:
        conn.close()
    return topic_ids


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
