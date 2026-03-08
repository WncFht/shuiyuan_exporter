from shuiyuan_cache.skill_api.runtime import (
    default_skill_cache_root,
    default_skill_cookie_path,
    default_skill_export_root,
)


DEFAULT_EXPORT_CACHE_ROOT = str(default_skill_cache_root())
DEFAULT_EXPORT_COOKIE_PATH = str(default_skill_cookie_path())
DEFAULT_EXPORT_SAVE_DIR = str(default_skill_export_root())
