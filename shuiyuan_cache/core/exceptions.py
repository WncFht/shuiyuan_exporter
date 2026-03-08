from __future__ import annotations


class ShuiyuanCacheError(Exception):
    pass


class InvalidTopicError(ShuiyuanCacheError):
    pass


class FetchError(ShuiyuanCacheError):
    pass


class RateLimitError(FetchError):
    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class SyncError(ShuiyuanCacheError):
    pass
