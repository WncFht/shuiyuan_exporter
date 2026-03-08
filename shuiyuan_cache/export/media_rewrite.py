from collections.abc import Callable

from shuiyuan_cache.export.attachments_handler import match_replace
from shuiyuan_cache.export.audio_handler import audio_replace
from shuiyuan_cache.export.image_handler import img_replace
from shuiyuan_cache.export.video_handler import video_replace


MEDIA_REWRITE_STEPS: tuple[
    tuple[str, str, Callable[[str, str, str, str, str], None]], ...
] = (
    ("image_seconds", "图片爬取耗时", img_replace),
    ("attachment_seconds", "附件爬取耗时", match_replace),
    ("video_seconds", "视频爬取耗时", video_replace),
    ("audio_seconds", "音频爬取耗时", audio_replace),
)
