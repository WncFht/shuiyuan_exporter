from __future__ import annotations

from dataclasses import asdict, dataclass
import html
from pathlib import Path
import re
from urllib.parse import urlparse

from shuiyuan_cache.export.constants import image_extensions


_MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_PLAIN_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
_HTML_IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_WIDTH_ATTR_RE = re.compile(r"\swidth\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+)", re.IGNORECASE)


@dataclass(slots=True)
class StudyMarkdownRewriteStats:
    markdown_images_converted: int = 0
    plain_image_links_converted: int = 0
    html_images_normalized: int = 0
    changed: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def rewrite_study_markdown(text: str, *, default_width: int = 320) -> tuple[str, StudyMarkdownRewriteStats]:
    stats = StudyMarkdownRewriteStats()
    rewritten = text

    def replace_html_img(match: re.Match[str]) -> str:
        stats.html_images_normalized += 1
        return _normalize_html_img_width(match.group(0), default_width)

    rewritten = _HTML_IMG_RE.sub(replace_html_img, rewritten)

    def replace_markdown_image(match: re.Match[str]) -> str:
        stats.markdown_images_converted += 1
        alt, target = match.groups()
        return _build_inline_img_tag(target.strip(), alt.strip(), default_width)

    rewritten = _MARKDOWN_IMAGE_RE.sub(replace_markdown_image, rewritten)

    def replace_plain_link(match: re.Match[str]) -> str:
        alt, target = match.groups()
        normalized_target = target.strip()
        if not _looks_like_image_target(normalized_target):
            return match.group(0)
        stats.plain_image_links_converted += 1
        return _build_inline_img_tag(normalized_target, alt.strip(), default_width)

    rewritten = _PLAIN_LINK_RE.sub(replace_plain_link, rewritten)
    stats.changed = rewritten != text
    return rewritten, stats


def rewrite_study_markdown_file(
    path: str | Path,
    *,
    default_width: int = 320,
    write: bool = True,
) -> dict:
    note_path = Path(path).expanduser().resolve()
    original = note_path.read_text(encoding="utf-8")
    rewritten, stats = rewrite_study_markdown(original, default_width=default_width)
    if write and stats.changed:
        note_path.write_text(rewritten, encoding="utf-8")
    payload = stats.to_dict()
    payload.update(
        {
            "path": str(note_path),
            "default_width": default_width,
            "written": bool(write and stats.changed),
        }
    )
    return payload


def _build_inline_img_tag(target: str, alt: str, width: int) -> str:
    escaped_target = html.escape(target, quote=True)
    escaped_alt = html.escape(alt or "image", quote=True)
    return f'<img src="{escaped_target}" alt="{escaped_alt}" width="{width}" />'


def _looks_like_image_target(target: str) -> bool:
    lowered = target.lower()
    if "/images/" in lowered or "/cache/media/images/" in lowered:
        return True
    parsed = urlparse(target)
    suffix = Path(parsed.path).suffix.lower()
    return suffix in {ext.lower() for ext in image_extensions}


def _normalize_html_img_width(tag: str, width: int) -> str:
    stripped = _WIDTH_ATTR_RE.sub("", tag).rstrip()
    if stripped.endswith("/>"):
        stripped = stripped[:-2].rstrip()
        return f'{stripped} width="{width}" />'
    if stripped.endswith(">"):
        stripped = stripped[:-1].rstrip()
        return f'{stripped} width="{width}">'
    return f'{stripped} width="{width}" />'
