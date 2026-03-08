import json
from pathlib import Path
from typing import Any, Optional

from shuiyuan_cache.core.models import SyncStateRecord
from shuiyuan_cache.store.paths import CachePaths


class RawStore:
    def __init__(self, paths: CachePaths):
        self.paths = paths
        self.paths.ensure_root()

    def save_topic_json(self, topic_id: int, payload: dict[str, Any]) -> Path:
        path = self.paths.ensure_parent(self.paths.topic_json_path(topic_id))
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def save_json_page(self, topic_id: int, page_no: int, payload: dict[str, Any]) -> Path:
        path = self.paths.ensure_parent(self.paths.json_page_path(topic_id, page_no))
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def save_raw_page(self, topic_id: int, page_no: int, text: str) -> Path:
        path = self.paths.ensure_parent(self.paths.raw_page_path(topic_id, page_no))
        path.write_text(text, encoding="utf-8")
        return path

    def save_post_raw(self, topic_id: int, post_number: int, text: str) -> Path:
        path = self.paths.ensure_parent(self.paths.post_raw_path(topic_id, post_number))
        path.write_text(text, encoding="utf-8")
        return path

    def save_sync_state(self, state: SyncStateRecord) -> Path:
        path = self.paths.ensure_parent(self.paths.sync_state_path(state.topic_id))
        path.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load_sync_state(self, topic_id: int) -> Optional[SyncStateRecord]:
        path = self.paths.sync_state_path(topic_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return SyncStateRecord(**data)
