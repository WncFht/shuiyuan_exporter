from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class CacheConfig:
    cache_root: Path = Path("cache")
    cookie_path: Path = Path("cookies.txt")
    base_url: str = "https://shuiyuan.sjtu.edu.cn"
    user_agent: str = "Mozilla/5.0"
    request_timeout: int = 30
    request_interval_seconds: float = 0.35
    retry_connect: int = 3
    backoff_factor: float = 0.5
    rate_limit_retry_attempts: int = 6
    rate_limit_cooldown_seconds: float = 5.0
    rate_limit_max_cooldown_seconds: float = 30.0
    raw_page_size: int = 100
    json_page_size: int = 20
    tail_refresh_pages: int = 2
    download_images: bool = True
    page_fetch_workers: int = 2
    image_download_workers: int = 4
    export_image_workers: int = 4

    @property
    def db_path(self) -> Path:
        return self.cache_root / "db" / "shuiyuan.sqlite"

    @property
    def auth_root(self) -> Path:
        return self.cache_root / "auth"

    @property
    def storage_state_path(self) -> Path:
        return self.auth_root / "auth.json"

    @property
    def browser_profile_dir(self) -> Path:
        return self.auth_root / "browser_profile"
