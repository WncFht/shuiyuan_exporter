import re
from pathlib import Path

from shuiyuan_cache.export.cache_bridge import get_export_cache_bridge
from shuiyuan_cache.export.compat import code_block_fix, quote_in_shuiyuan


def normalize_topic_id(topic: str | int) -> str:
    topic_text = str(topic)
    return topic_text[1:] if topic_text.startswith("L") else topic_text


def build_markdown_filename(topic_id: str, title: str) -> str:
    safe_title = (str(title) + ".md").replace("/", " or ")
    safe_title = re.sub(r'[\/*?:"<>|]', "_", safe_title)
    return f"{topic_id} {safe_title}"


def export_raw_post(
    output_dir: str | Path,
    topic: str | int,
    cache_root: str = "cache",
    cookie_path: str = "cookies.txt",
) -> str:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    topic_id = normalize_topic_id(topic)
    cache_bridge = get_export_cache_bridge(
        cache_root=cache_root, cookie_path=cookie_path
    )

    title = cache_bridge.load_topic_meta(topic_id).get("title") or "Empty"
    filename = build_markdown_filename(topic_id, title)
    output_path = output_dir / filename
    output_path.write_text("", encoding="utf-8")

    ordered_results: list[tuple[int, str]] = []
    for page_no, raw_text in cache_bridge.iter_raw_pages(topic_id):
        ordered_results.append(
            (
                page_no,
                quote_in_shuiyuan(
                    code_block_fix(raw_text),
                    cache_root=cache_root,
                    cookie_path=cookie_path,
                ),
            )
        )

    output_path.write_text(
        "\n".join(text for _, text in ordered_results), encoding="utf-8"
    )
    return filename
