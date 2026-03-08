from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class CacheConfig:
    cache_root: Path = Path("cache")
    cookie_path: Path = Path("cookies.txt")
    base_url: str = "https://shuiyuan.sjtu.edu.cn"
    user_agent: str = "Mozilla/5.0"
    request_timeout: int = 30
    retry_connect: int = 3
    backoff_factor: float = 0.5
    raw_page_size: int = 100
    json_page_size: int = 20
    tail_refresh_pages: int = 2
    download_images: bool = True

    @property
    def db_path(self) -> Path:
        return self.cache_root / "db" / "shuiyuan.sqlite"
