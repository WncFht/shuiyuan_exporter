from __future__ import annotations

import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from threading import Lock
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from shuiyuan_cache.auth.storage_state import build_cookie_header_from_storage_state
from shuiyuan_cache.core.config import CacheConfig
from shuiyuan_cache.core.exceptions import FetchError, RateLimitError


class ShuiyuanSession:
    _request_lock = Lock()
    _next_request_at = 0.0

    def __init__(self, config: CacheConfig):
        self.config = config
        self.session = requests.Session()
        retry = Retry(
            connect=config.retry_connect,
            status=config.retry_connect,
            backoff_factor=config.backoff_factor,
            status_forcelist=[500, 502, 503, 504],
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
        absolute_url = self.absolute_url(url)
        attempts = max(self.config.rate_limit_retry_attempts, 1)
        last_error: RateLimitError | None = None

        for attempt in range(1, attempts + 1):
            self._wait_for_request_slot()
            try:
                response = self.session.get(
                    absolute_url,
                    timeout=self.config.request_timeout,
                    **kwargs,
                )
            except requests.RequestException as exc:
                raise FetchError(f"Request failed for {absolute_url}: {exc}") from exc

            if response.status_code == 429:
                retry_after = self._resolve_retry_after_seconds(response, attempt)
                self._register_global_cooldown(retry_after)
                response.close()
                last_error = RateLimitError(
                    "Rate limited for "
                    f"{absolute_url}. retry_after={retry_after:.1f}s "
                    f"attempt={attempt}/{attempts}",
                    retry_after=retry_after,
                )
                if attempt >= attempts:
                    raise last_error
                time.sleep(retry_after)
                continue

            self._raise_for_bad_response(response, absolute_url)
            return response

        if last_error is not None:
            raise last_error
        raise FetchError(f"Request failed for {absolute_url} without response")

    def get_json(self, url: str) -> dict[str, Any]:
        response = self.get(url)
        return response.json()

    def get_text(self, url: str) -> str:
        response = self.get(url)
        return response.text

    def get_binary(self, url: str) -> requests.Response:
        return self.get(url, stream=True)

    def _wait_for_request_slot(self) -> None:
        interval = max(self.config.request_interval_seconds, 0.0)
        while True:
            with type(self)._request_lock:
                now = time.monotonic()
                wait_seconds = type(self)._next_request_at - now
                if wait_seconds <= 0:
                    type(self)._next_request_at = now + interval
                    return
            time.sleep(min(wait_seconds, 0.5))

    def _register_global_cooldown(self, cooldown_seconds: float) -> None:
        bounded = max(cooldown_seconds, self.config.request_interval_seconds, 0.0)
        with type(self)._request_lock:
            type(self)._next_request_at = max(
                type(self)._next_request_at,
                time.monotonic() + bounded,
            )

    def _resolve_retry_after_seconds(
        self,
        response: requests.Response,
        attempt: int,
    ) -> float:
        header_value = (response.headers.get("Retry-After") or "").strip()
        parsed_header = self._parse_retry_after_header(header_value)
        if parsed_header is not None:
            return min(
                max(parsed_header, self.config.request_interval_seconds),
                self.config.rate_limit_max_cooldown_seconds,
            )
        fallback = min(
            self.config.rate_limit_cooldown_seconds * max(attempt, 1),
            self.config.rate_limit_max_cooldown_seconds,
        )
        return max(fallback, self.config.request_interval_seconds)

    @staticmethod
    def _parse_retry_after_header(value: str) -> float | None:
        if not value:
            return None
        try:
            return max(float(value), 0.0)
        except ValueError:
            pass
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, IndexError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        delta = (parsed - datetime.now(timezone.utc)).total_seconds()
        return max(delta, 0.0)

    @staticmethod
    def _read_response_excerpt(response: requests.Response) -> str:
        content_type = (response.headers.get("Content-Type") or "").lower()
        if not any(token in content_type for token in ("text", "json", "html")):
            return ""
        return response.text[:200].replace("\n", " ")

    def _raise_for_bad_response(
        self,
        response: requests.Response,
        absolute_url: str,
    ) -> None:
        detail = self._read_response_excerpt(response)
        if response.status_code >= 400:
            if "not_logged_in" in detail or "您需要登录" in detail:
                raise FetchError(
                    "Authentication failed for "
                    f"{absolute_url}. Your Shuiyuan cookie may be expired."
                )
            raise FetchError(
                f"Request failed: {response.status_code} {absolute_url} :: {detail}"
            )
        if detail and "SJTU Single Sign On" in detail:
            raise FetchError(
                f"Authentication failed for {absolute_url}. Your Shuiyuan cookie may be expired."
            )
