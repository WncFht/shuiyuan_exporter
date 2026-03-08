import hashlib
import json
from typing import Any

from bs4 import BeautifulSoup

from shuiyuan_cache.core.models import PostRecord, TopicRecord
from shuiyuan_cache.normalize.media_normalizer import MediaNormalizer


class PostNormalizer:
    def __init__(self, media_normalizer: MediaNormalizer):
        self.media_normalizer = media_normalizer

    @staticmethod
    def normalize_topic(
        topic_id: int, payload: dict[str, Any], topic_json_path: str
    ) -> TopicRecord:
        tags = payload.get("tags") or []
        if tags and isinstance(tags[0], dict):
            tags_json = json.dumps(
                [tag.get("name") for tag in tags], ensure_ascii=False
            )
        else:
            tags_json = json.dumps(tags, ensure_ascii=False)
        return TopicRecord(
            topic_id=topic_id,
            title=payload.get("title") or f"topic-{topic_id}",
            category_id=payload.get("category_id"),
            tags_json=tags_json,
            created_at=payload.get("created_at"),
            last_posted_at=payload.get("last_posted_at"),
            posts_count=payload.get("posts_count") or 0,
            reply_count=payload.get("reply_count"),
            views=payload.get("views"),
            like_count=payload.get("like_count"),
            visible=payload.get("visible"),
            archived=payload.get("archived"),
            closed=payload.get("closed"),
            topic_json_path=topic_json_path,
        )

    def normalize_posts(
        self, topic_id: int, page_no: int, payload: dict[str, Any]
    ) -> tuple[list[PostRecord], list]:
        posts_payload = payload.get("post_stream", {}).get("posts", [])
        posts: list[PostRecord] = []
        media_records = []
        for post in posts_payload:
            cooked_html = post.get("cooked") or ""
            plain_text = self._html_to_text(cooked_html)
            images = self.media_normalizer.normalize_images(
                topic_id=topic_id,
                post_id=post.get("id"),
                post_number=post.get("post_number"),
                cooked_html=cooked_html,
            )
            has_attachments = 'class="attachment"' in cooked_html
            has_video = "data-video-src=" in cooked_html
            has_audio = "<audio" in cooked_html
            media_records.extend(images)
            posts.append(
                PostRecord(
                    post_id=post.get("id"),
                    topic_id=topic_id,
                    post_number=post.get("post_number"),
                    username=post.get("username"),
                    display_name=post.get("name"),
                    created_at=post.get("created_at"),
                    updated_at=post.get("updated_at"),
                    reply_to_post_number=post.get("reply_to_post_number"),
                    is_op=(post.get("post_number") == 1),
                    like_count=post.get("like_count") or 0,
                    raw_markdown=None,
                    cooked_html=cooked_html,
                    plain_text=plain_text,
                    raw_page_no=None,
                    json_page_no=page_no,
                    raw_post_path=None,
                    has_images=bool(images),
                    has_attachments=has_attachments,
                    has_audio=has_audio,
                    has_video=has_video,
                    image_count=len(images),
                    hash_raw=None,
                    hash_cooked=hashlib.sha1(cooked_html.encode("utf-8")).hexdigest()
                    if cooked_html
                    else None,
                )
            )
        return posts, media_records

    @staticmethod
    def _html_to_text(html: str) -> str:
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text("\n", strip=True)
