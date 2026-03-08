from shuiyuan_cache.cli.auth_cli import build_parser as build_auth_parser
from shuiyuan_cache.cli.sync_cli import build_parser as build_sync_parser
from shuiyuan_cache.export.constants import default_save_dir
from shuiyuan_cache.export.runtime_defaults import (
    DEFAULT_EXPORT_CACHE_ROOT,
    DEFAULT_EXPORT_COOKIE_PATH,
    DEFAULT_EXPORT_SAVE_DIR,
)
from shuiyuan_cache.skill_api.runtime import (
    build_skill_config,
    default_skill_cache_root,
    default_skill_cookie_path,
    default_skill_export_root,
)


def test_export_defaults_match_skill_runtime() -> None:
    assert DEFAULT_EXPORT_CACHE_ROOT == str(default_skill_cache_root())
    assert DEFAULT_EXPORT_COOKIE_PATH == str(default_skill_cookie_path())
    assert DEFAULT_EXPORT_SAVE_DIR == str(default_skill_export_root())
    assert default_save_dir == str(default_skill_export_root())


def test_cli_defaults_match_skill_runtime() -> None:
    auth_args = build_auth_parser().parse_args(["status"])
    sync_args = build_sync_parser().parse_args(["123"])

    assert auth_args.cache_root == str(default_skill_cache_root())
    assert auth_args.cookie_path == str(default_skill_cookie_path())
    assert sync_args.cache_root == str(default_skill_cache_root())
    assert sync_args.cookie_path == str(default_skill_cookie_path())


def test_build_skill_config_creates_runtime_dirs(tmp_path) -> None:
    cache_root = tmp_path / "cache"
    cookie_path = tmp_path / "cookies" / "cookies.txt"

    config = build_skill_config(cache_root=cache_root, cookie_path=cookie_path)

    assert config.cache_root == cache_root.resolve()
    assert config.cookie_path == cookie_path.resolve()
    assert config.cache_root.exists()
    assert config.cookie_path.parent.exists()
