import math
import re
from typing import Any

from shuiyuan_cache.core.config import CacheConfig
from shuiyuan_cache.core.exceptions import InvalidTopicError
from shuiyuan_cache.fetch.session import ShuiyuanSession


_TOPIC_RE = re.compile(r"(?:/t/topic/|/t/)?([A-Za-z]?\d+)")


class TopicFetcher:
    def __init__(self, config: CacheConfig, session: ShuiyuanSession):
        self.config = config
        self.session = session

    @staticmethod
    def resolve_topic_id(topic: str | int) -> int:
        if isinstance(topic, int):
            return topic
        topic_text = str(topic).strip()
        if topic_text.isdigit():
            return int(topic_text)
        match = _TOPIC_RE.search(topic_text)
        if not match:
            raise InvalidTopicError(f"Invalid topic: {topic}")
        topic_id = match.group(1)
        if topic_id.startswith("L"):
            topic_id = topic_id[1:]
        return int(topic_id)

    def topic_json_url(self, topic_id: int, page_no: int | None = None, track: bool = False) -> str:
        suffix = f"/t/{topic_id}.json"
        params = []
        if page_no is not None:
            params.append(f"page={page_no}")
        if track:
            params.extend(["track_visit=true", "forceLoad=true"])
        query = f"?{'&'.join(params)}" if params else ""
        return f"{self.config.base_url}{suffix}{query}"

    def raw_page_url(self, topic_id: int, page_no: int) -> str:
        return f"{self.config.base_url}/raw/{topic_id}?page={page_no}"

    def raw_post_url(self, topic_id: int, post_number: int) -> str:
        return f"{self.config.base_url}/raw/{topic_id}/{post_number}"

    def fetch_topic_meta(self, topic_id: int) -> dict[str, Any]:
        return self.session.get_json(self.topic_json_url(topic_id))

    def fetch_topic_json_page(self, topic_id: int, page_no: int) -> dict[str, Any]:
        return self.session.get_json(self.topic_json_url(topic_id, page_no=page_no))

    def fetch_topic_raw_page(self, topic_id: int, page_no: int) -> str:
        return self.session.get_text(self.raw_page_url(topic_id, page_no))

    def fetch_post_raw(self, topic_id: int, post_number: int) -> str:
        return self.session.get_text(self.raw_post_url(topic_id, post_number))

    @staticmethod
    def page_count(posts_count: int, page_size: int) -> int:
        return max(1, math.ceil(posts_count / page_size))
