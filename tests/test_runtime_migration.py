from __future__ import annotations

import json
from pathlib import Path

from shuiyuan_cache.maintenance.runtime_migration import (
    apply_runtime_migration,
    build_runtime_migration_report,
)


def test_build_runtime_migration_report_identifies_repo_only_topics(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"

    (repo_root / "cache/raw/topics/123/pages/json").mkdir(parents=True)
    (repo_root / "cache/raw/topics/123/topic.json").write_text("{}", encoding="utf-8")
    (repo_root / "cache/auth/browser_profile").mkdir(parents=True)
    (repo_root / "cache/auth/auth.json").write_text("{}", encoding="utf-8")
    (repo_root / "cookies.txt").write_text("a=b", encoding="utf-8")

    (runtime_root / "cache/raw/topics/456/pages/json").mkdir(parents=True)
    (runtime_root / "cache/raw/topics/456/topic.json").write_text(
        "{}", encoding="utf-8"
    )

    report = build_runtime_migration_report(
        repo_root=repo_root,
        runtime_root=runtime_root,
    )

    assert report["summary"]["repo_only_topic_dirs"] == ["123"]
    assert report["summary"]["runtime_only_topic_dirs"] == ["456"]
    assert any(action["kind"] == "copy_topic_dir" for action in report["actions"])
    assert any(action["kind"] == "browser_profile" for action in report["actions"])
    assert any(action["kind"] == "auth_json" for action in report["actions"])
    assert any(action["kind"] == "cookies" for action in report["actions"])


def test_apply_runtime_migration_copies_missing_runtime_files(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"

    (repo_root / "cache/raw/topics/123/pages/raw").mkdir(parents=True)
    (repo_root / "cache/raw/topics/123/topic.json").write_text("{}", encoding="utf-8")
    (repo_root / "cache/raw/topics/123/pages/raw/0001.md").write_text(
        "hello", encoding="utf-8"
    )
    (repo_root / "cache/auth/browser_profile").mkdir(parents=True)
    (repo_root / "cache/auth/browser_profile/marker.txt").write_text(
        "ok", encoding="utf-8"
    )
    (repo_root / "cache/auth/auth.json").write_text(
        json.dumps({"cookies": []}), encoding="utf-8"
    )
    (repo_root / "cookies.txt").write_text("a=b", encoding="utf-8")
    (repo_root / "cache/media/images/ab").mkdir(parents=True)
    (repo_root / "cache/media/images/ab/demo.png").write_text("img", encoding="utf-8")

    result = apply_runtime_migration(repo_root=repo_root, runtime_root=runtime_root)

    assert result["status"] == "applied"
    assert (runtime_root / "cache/raw/topics/123/topic.json").exists()
    assert (runtime_root / "cache/raw/topics/123/pages/raw/0001.md").exists()
    assert (runtime_root / "cache/auth/auth.json").exists()
    assert (runtime_root / "cache/auth/browser_profile/marker.txt").exists()
    assert (runtime_root / "cookies.txt").exists()
    assert (runtime_root / "cache/media/images/ab/demo.png").exists()
