class ShuiyuanCacheError(Exception):
    pass


class InvalidTopicError(ShuiyuanCacheError):
    pass


class FetchError(ShuiyuanCacheError):
    pass


class SyncError(ShuiyuanCacheError):
    pass
