from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from shuiyuan_cache.auth.storage_state import build_cookie_header_from_storage_state
from shuiyuan_cache.core.config import CacheConfig
from shuiyuan_cache.core.exceptions import FetchError


class ShuiyuanSession:
    def __init__(self, config: CacheConfig):
        self.config = config
        self.session = requests.Session()
        retry = Retry(
            connect=config.retry_connect,
            status=config.retry_connect,
            backoff_factor=config.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset({"GET"}),
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        headers = {
            "User-Agent": config.user_agent,
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }
        cookie_header = self.resolve_cookie_header()
        if cookie_header:
            headers["Cookie"] = cookie_header
        self.session.headers.update(headers)

    def resolve_cookie_header(self) -> str:
        storage_cookie_text = build_cookie_header_from_storage_state(
            self.config.storage_state_path, self.config.base_url
        )
        if storage_cookie_text:
            return storage_cookie_text
        return self.read_cookie(self.config.cookie_path)

    @staticmethod
    def read_cookie(path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8").strip()

    def absolute_url(self, url: str) -> str:
        if url.startswith("http://") or url.startswith("https://"):
            return url
        base = self.config.base_url.rstrip("/")
        return f"{base}{url}"

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        response = self.session.get(url, timeout=self.config.request_timeout, **kwargs)
        if response.status_code >= 400:
            detail = response.text[:200].replace("\n", " ")
            if "not_logged_in" in detail or "您需要登录" in detail:
                raise FetchError(
                    f"Authentication failed for {url}. Your Shuiyuan cookie may be expired."
                )
            raise FetchError(
                f"Request failed: {response.status_code} {url} :: {detail}"
            )
        if "SJTU Single Sign On" in response.text:
            raise FetchError(
                f"Authentication failed for {url}. Your Shuiyuan cookie may be expired."
            )
        return response

    def get_json(self, url: str) -> dict[str, Any]:
        response = self.get(url)
        return response.json()

    def get_text(self, url: str) -> str:
        response = self.get(url)
        return response.text

    def get_binary(self, url: str) -> requests.Response:
        return self.get(url, stream=True)
