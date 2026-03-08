from __future__ import annotations

import os
from pathlib import Path

from shuiyuan_cache.core.config import CacheConfig


_DEFAULT_RUNTIME_ROOT = Path.home() / ".local" / "share" / "shuiyuan-cache-skill"
_DEFAULT_BASE_URL = "https://shuiyuan.sjtu.edu.cn"


def _expand(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def default_skill_runtime_root() -> Path:
    return _expand(os.environ.get("SHUIYUAN_SKILL_HOME", _DEFAULT_RUNTIME_ROOT))


def default_skill_cache_root() -> Path:
    return _expand(
        os.environ.get(
            "SHUIYUAN_CACHE_ROOT",
            default_skill_runtime_root() / "cache",
        )
    )


def default_skill_cookie_path() -> Path:
    return _expand(
        os.environ.get(
            "SHUIYUAN_COOKIE_PATH",
            default_skill_runtime_root() / "cookies.txt",
        )
    )


def default_skill_export_root() -> Path:
    return _expand(
        os.environ.get(
            "SHUIYUAN_EXPORT_ROOT",
            default_skill_runtime_root() / "exports",
        )
    )


def build_skill_config(
    cache_root: str | Path | None = None,
    cookie_path: str | Path | None = None,
    base_url: str = _DEFAULT_BASE_URL,
) -> CacheConfig:
    resolved_cache_root = (
        _expand(cache_root) if cache_root else default_skill_cache_root()
    )
    resolved_cookie_path = (
        _expand(cookie_path) if cookie_path else default_skill_cookie_path()
    )
    resolved_cache_root.mkdir(parents=True, exist_ok=True)
    resolved_cookie_path.parent.mkdir(parents=True, exist_ok=True)
    return CacheConfig(
        cache_root=resolved_cache_root,
        cookie_path=resolved_cookie_path,
        base_url=base_url,
    )
