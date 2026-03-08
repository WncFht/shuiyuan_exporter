import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from shuiyuan_cache.export.cache_bridge import get_export_cache_bridge
from shuiyuan_cache.export.constants import Shuiyuan_Base


AUDIO_RAW_PATTERN = re.compile(
    r"\[.*?\|audio\]\(upload://([a-zA-Z0-9]+)\.([a-zA-Z0-9]+)\)"
)


def _normalize_topic_id(topic: str | int) -> str:
    topic_text = str(topic)
    return topic_text[1:] if topic_text.startswith("L") else topic_text


def _extract_audio_urls(cooked_content: str) -> list[str]:
    soup = BeautifulSoup(cooked_content, "html.parser")
    audio_tags = soup.find_all("audio", attrs={"preload": "metadata", "controls": True})
    return [
        source["src"]
        for audio_tag in audio_tags
        for source in audio_tag.find_all("source")
        if source.get("src")
    ]


def _collect_audio_links(topic: str | int) -> list[tuple[str, str]]:
    topic_id = _normalize_topic_id(topic)
    cache_bridge = get_export_cache_bridge()
    url_sha1s: list[tuple[str, str]] = []
    for post in cache_bridge.iter_json_posts(topic_id):
        cooked_match = _extract_audio_urls(post.get("cooked") or "")
        if not cooked_match:
            continue
        raw_content = cache_bridge.get_post_raw(topic_id, int(post["post_number"]))
        raw_match = [
            f"{sha1}.{ext}" for sha1, ext in AUDIO_RAW_PATTERN.findall(raw_content)
        ]
        url_sha1s.extend(
            (urljoin(Shuiyuan_Base, url), sha1)
            for url, sha1 in zip(cooked_match, raw_match)
        )
    return url_sha1s


def audio_replace(path: str, filename: str, topic: str):
    print("文件替换中...")
    file_path = Path(path) / filename
    md_content = file_path.read_text(encoding="utf-8")
    for url, sha1_with_ext in _collect_audio_links(topic):
        md_content = md_content.replace(f"upload://{sha1_with_ext}", url)
    file_path.write_text(md_content, encoding="utf-8")
