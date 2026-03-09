from pathlib import Path

from shuiyuan_cache.export.study_markdown import (
    rewrite_study_markdown,
    rewrite_study_markdown_file,
)


def test_rewrite_study_markdown_converts_renderable_images() -> None:
    source = "\n".join(
        [
            "[图像文件](./images/a.jpeg)",
            "![图表](./images/b.png)",
            '<img src="./images/c.png" alt="old" width="420" />',
            "[原楼](./351551 牢A投资记录.md)",
        ]
    )

    rewritten, stats = rewrite_study_markdown(source, default_width=320)

    assert '<img src="./images/a.jpeg" alt="图像文件" width="320" />' in rewritten
    assert '<img src="./images/b.png" alt="图表" width="320" />' in rewritten
    assert '<img src="./images/c.png" alt="old" width="320" />' in rewritten
    assert "[原楼](./351551 牢A投资记录.md)" in rewritten
    assert stats.plain_image_links_converted == 1
    assert stats.markdown_images_converted == 1
    assert stats.html_images_normalized == 1
    assert stats.changed is True


def test_rewrite_study_markdown_file_writes_changes(tmp_path: Path) -> None:
    note_path = tmp_path / "note.md"
    note_path.write_text("![图像文件](./images/example.jpeg)\n", encoding="utf-8")

    payload = rewrite_study_markdown_file(note_path, default_width=280)

    assert payload["written"] is True
    assert payload["default_width"] == 280
    assert 'width="280"' in note_path.read_text(encoding="utf-8")
