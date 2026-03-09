---
name: shuiyuan-cache-skill
description: Cache-first and live-search access to Shanghai Jiao Tong University Shuiyuan Forum topics. Use when work involves Shuiyuan topic IDs or URLs, when the user wants you to search Shuiyuan for relevant posts or latest discussions, or when you need to trace a specific user's historical posts and related topics. Prefer local cache for known topics, but use live search first for discovery tasks.
---

# Shuiyuan Cache Skill

Use this repository as a self-contained skill repo.

## Choose the right path

Use one of these workflows first:

1. **Known topic id / topic URL** → cache-first
   - `scripts/inspect_topic.py`
   - `scripts/ensure_cached.py` when cache is missing or stale
   - `scripts/query_topic.py` / `scripts/summarize_topic.py`
   - `scripts/export_topic.py` only when Markdown output is explicitly needed
2. **Need a quick candidate list from live Shuiyuan** → header search
   - `scripts/search_forum.py "<query>" --mode header`
   - good for quickly discovering a few topic / post hits before deciding what to cache
3. **Need fuller online search with Discourse syntax** → full-page search
   - `scripts/search_forum.py "<query>" --mode full-page`
   - use when the user says “search Shuiyuan”, “find related posts”, “look for older discussions”, or when you need query syntax like `user:xxx`, `after:...`, `order:latest`
4. **Need author history / author-centered discovery** → author trace
   - `scripts/trace_author.py <username>`
   - optionally add `--keyword` and let it auto-cache the top topic candidates
5. **Need full-thread study / timeline split / image-based reading** → topic study pipeline
   - `scripts/inspect_topic.py <topic>`
   - `scripts/ensure_cached.py <topic> --refresh-mode full` when the user explicitly wants the whole thread and images to be complete
   - `scripts/export_topic.py <topic>` and prefer the default export root unless the user explicitly wants another copy
   - `scripts/plan_topic_study.py <topic> --granularity week`
   - then read representative images directly from the returned local paths

## Auth: how it actually works

The most important thing to know:

- `auth.json` under `cache/auth/` is the primary saved login state
- `browser_profile/` is the dedicated browser profile reused by `auth_cli setup/refresh`
- `cookies.txt` is a fallback **HTTP `Cookie` header string**, not a Netscape cookie-jar file
- if you use `curl`, do **not** pass `cookies.txt` via `-b <file>`; instead send `-H "Cookie: $(cat .../cookies.txt)"`
- `auth_cli status` only checks local files unless you add `--check-live`
- `auth_cli setup` opens a browser window and waits for the user to press Enter in the terminal after login

Preferred auth check:

```bash
uv run python -m shuiyuan_cache.cli.auth_cli status \
  --cache-root "$HOME/.local/share/shuiyuan-cache-skill/cache" \
  --cookie-path "$HOME/.local/share/shuiyuan-cache-skill/cookies.txt" \
  --check-live --json
```

If live auth is missing or expired:

```bash
uv run python -m shuiyuan_cache.cli.auth_cli setup \
  --cache-root "$HOME/.local/share/shuiyuan-cache-skill/cache" \
  --cookie-path "$HOME/.local/share/shuiyuan-cache-skill/cookies.txt" \
  --browser edge
```

## Search guidance

Use the lowest-friction path that matches the user's intent:

- **quick discovery**: `search_forum.py --mode header`
- **fuller Discourse search**: `search_forum.py --mode full-page`
- **author history**: `trace_author.py`
- **exact analysis inside a known topic**: cache it, then use `query_topic.py`

For full-page search, the query string can include Discourse search operators such as:

- `user:username`
- `after:YYYY-MM-DD`
- `before:YYYY-MM-DD`
- `in:title`
- `tag:xxx`
- `category:xxx`
- `order:latest`

If the task is “搜这个人以前说过什么 / 找这个人相关楼”， prefer:

1. `trace_author.py <username>`
2. then cache the top hit topics if needed
3. then use `query_topic.py --author <username>` for exact local filtering inside those topics

## Whole-topic study guidance

When the user wants to **完整阅读一个楼、按时间线切分、结合图片精读**:

- inspect completeness first, then choose whether a full refresh is worth it
- prefer the default export root; avoid `--save-dir` unless the user explicitly wants a duplicate export tree
- use `scripts/plan_topic_study.py` to build weekly or monthly buckets before writing notes
- for image reading, prefer direct visual reading on local paths
- if the user explicitly says not to use OCR, do not use OCR
- if an exported image is missing, fall back to the cache media path when available

## Runtime paths

- Skill runtime data defaults to `~/.local/share/shuiyuan-cache-skill/`
- Override runtime paths with `SHUIYUAN_CACHE_ROOT`, `SHUIYUAN_COOKIE_PATH`, or CLI flags
- The repo itself should stay code-only; cache, auth state, and exports live outside the repo

## Machine output

- `scripts/*.py` keeps `stdout` reserved for JSON payloads
- progress and stage logs are written to `stderr`
- this makes the skill safe for machine consumption while still keeping human-readable progress

## Scripts

- `scripts/search_forum.py`
- `scripts/trace_author.py`
- `scripts/inspect_topic.py`
- `scripts/ensure_cached.py`
- `scripts/query_topic.py`
- `scripts/summarize_topic.py`
- `scripts/export_topic.py`
- `scripts/plan_topic_study.py`

## References

- `docs/DISCOURSE_SEARCH_API_RESEARCH.md`
- `references/output_schema.md`
- `references/topic-study-workflow.md`
- `references/runtime_layout.md`
- `references/troubleshooting.md`
