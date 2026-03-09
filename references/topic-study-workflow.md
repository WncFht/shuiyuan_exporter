# Topic Study Workflow

Use this workflow when a user wants to deeply read a whole Shuiyuan thread, split it by timeline, or study it together with images.

## Recommended pipeline

1. **Inspect completeness first**
   - Run `scripts/inspect_topic.py <topic>`.
   - Check whether `db_post_count`, `json_page_count`, and `raw_page_count` are complete enough for analysis/export.

2. **If the user wants the whole thread with images, prefer a full sync**
   - Run `scripts/ensure_cached.py <topic> --refresh-mode full`.
   - Do this only when completeness matters; otherwise incremental refresh is usually enough.

3. **Prefer the default export root unless the user explicitly wants a duplicate copy**
   - Run `scripts/export_topic.py <topic>`.
   - Do **not** pass `--save-dir` just for convenience; that creates another Markdown tree and another image copy.
   - The default export root is `~/.local/share/shuiyuan-cache-skill/exports/<topic_id>/`.

4. **Build timeline buckets before writing notes**
   - Run `scripts/plan_topic_study.py <topic> --granularity week` for detailed study.
   - Run `scripts/plan_topic_study.py <topic> --granularity month` for a lighter first pass.
   - This script returns bucket metadata, key posts, and a representative image path per bucket when available.

5. **Read representative images directly**
   - Prefer direct visual reading on the returned local image path.
   - If the user explicitly forbids OCR, do not use OCR.
   - Some weeks may only have a meme, emoji, or tiny screenshot; note that explicitly instead of inventing detail.

6. **Write notes next to the exported thread**
   - Put study notes beside the exported Markdown, e.g.:
     - `351551 时间线精读.md`
     - `351551 每周精读.md`

7. **Normalize note images before final delivery**
   - Run `scripts/postprocess_study_markdown.py <note.md> [more notes...]`.
   - This rewrites image references into renderable inline images and uses width `320` by default.
   - Use `--check` if you only want to verify whether a note still needs rewriting.

## Important caveats

- Exported images and cache images are related but not identical.
- If an exported image is missing, fall back to the cache media path when available.
- Some media rows are emoji or decorative assets, not study-worthy charts.
- Large threads should be segmented first; reading the whole Markdown linearly is inefficient.

## Useful heuristics for representative images

- Prefer images attached to the original poster.
- Prefer posts containing words like `收益率`, `交割单`, `总结`, `仓位`, `加仓`, `减仓`.
- Prefer larger screenshots over tiny icon-like images.
- If a week only has joke images or emoji, say so clearly in the output.
