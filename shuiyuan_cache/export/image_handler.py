import re
from pathlib import Path
from urllib.parse import urljoin

from shuiyuan_cache.export.cache_bridge import get_export_cache_bridge
from shuiyuan_cache.export.constants import Shuiyuan_Base, image_extensions


DELETED_IMAGE_PATTERN = re.compile(r'<img src="[a-zA-Z0-9_:\/\-\.]+" alt=".*?" data-orig-src="(.*?)"')
IMAGE_PATTERN = re.compile(r'<img src="([a-zA-Z0-9_:\/\-\.]+)" alt=".*?" data-base62-sha1="(.*?)"')
UPLOAD_IMAGE_PATTERN = re.compile(r'!\[.*?]\(upload://([a-zA-Z0-9\.]+)\)')


def _normalize_topic_id(topic: str | int) -> str:
    topic_text = str(topic)
    return topic_text[1:] if topic_text.startswith('L') else topic_text


def _has_known_image_ext(name: str) -> bool:
    match_ext = re.search(r'\.([a-zA-Z0-9]+)$', name)
    return not match_ext or f'.{match_ext.group(1)}' in image_extensions


def _collect_image_rewrites(topic: str | int, output_image_dir: Path) -> tuple[list[str], list[str]]:
    topic_id = _normalize_topic_id(topic)
    cache_bridge = get_export_cache_bridge()
    deleted_names: list[str] = []
    real_names: list[str] = []

    for post in cache_bridge.iter_json_posts(topic_id):
        html_content = post.get('cooked') or ''
        deleted_names.extend(name.removeprefix('upload://') for name in DELETED_IMAGE_PATTERN.findall(html_content))
        matches = IMAGE_PATTERN.findall(html_content)
        if not matches:
            continue
        for src, name in matches:
            resolved_url = urljoin(Shuiyuan_Base, src)
            ext_match = re.search(r'\.([a-zA-Z0-9]+)(?:$|[?#])', resolved_url)
            if not ext_match:
                continue
            ext = ext_match.group(1)
            cache_bridge.ensure_output_image(name, ext, resolved_url, output_image_dir)
            real_names.append(f'{name}.{ext}')

    return real_names, deleted_names


def img_replace(path: str, filename: str, topic: str):
    print('图片载入中...')
    file_path = Path(path) / filename
    md_content = file_path.read_text(encoding='utf-8')

    name_with_fake_exts = [name for name in UPLOAD_IMAGE_PATTERN.findall(md_content) if _has_known_image_ext(name)]
    image_names, deleted_names = _collect_image_rewrites(topic, Path(path) / 'images')

    for deleted_name in deleted_names:
        try:
            name_with_fake_exts.remove(deleted_name)
        except ValueError:
            continue

    for sha1_with_ext, name in zip(name_with_fake_exts, image_names):
        pattern = r'!\[.*?\]\(upload://{}\)'.format(re.escape(sha1_with_ext))
        md_content = re.sub(pattern, f'![](upload://{name})', md_content)

    def replace(match_obj: re.Match[str]) -> str:
        old_link = match_obj.group(0)
        ext_match = re.search(r'\.([a-zA-Z0-9]+)', old_link)
        if ext_match and ext_match.group(0) not in image_extensions:
            return old_link
        return old_link.replace('upload://', './images/')

    md_content = UPLOAD_IMAGE_PATTERN.sub(replace, md_content)
    file_path.write_text(md_content, encoding='utf-8')
