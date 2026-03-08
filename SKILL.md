---
name: shuiyuan-cache-skill
description: Cache-first access to Shanghai Jiao Tong University Shuiyuan Forum topics. Use when work involves Shuiyuan topic IDs or URLs and you need to inspect cache state, sync topic data, query posts by keyword/author/date, summarize discussion threads, or export topic content. This skill prefers local cached data, refreshes from Shuiyuan only when cache is missing or the user explicitly asks to refresh, and works with browser storage state or cookie-based authentication.
---

# Shuiyuan Cache Skill

Use this repository as a self-contained skill repo.

## Workflow

Prefer this order:

1. Inspect local cache with `scripts/inspect_topic.py`.
2. If cache is missing or stale, run `scripts/ensure_cached.py`.
3. Use `scripts/query_topic.py` or `scripts/summarize_topic.py` for structured answers.
4. Only use `scripts/export_topic.py` when Markdown output is explicitly needed.

## Runtime paths

- Skill runtime data defaults to `~/.local/share/shuiyuan-cache-skill/`.
- Override runtime paths with `SHUIYUAN_CACHE_ROOT`, `SHUIYUAN_COOKIE_PATH`, or CLI flags.
- The repo itself should stay code-only; cache, auth state, and exports live outside the repo.

## Machine output

- `scripts/*.py` keeps `stdout` reserved for JSON payloads.
- Progress and stage logs are written to `stderr`.
- This makes the skill safe for machine consumption while still keeping human-readable progress.

## Auth

If a sync request fails because auth is missing or expired, use the same runtime paths with `auth_cli`:

```bash
uv run python -m shuiyuan_cache.cli.auth_cli setup --cache-root "$HOME/.local/share/shuiyuan-cache-skill/cache" --cookie-path "$HOME/.local/share/shuiyuan-cache-skill/cookies.txt"
```

## Chezmoi sync

Recommended split:

- Sync code and skill metadata with git / `chezmoi`.
- Do not sync runtime data under `~/.local/share/shuiyuan-cache-skill/`.
- Do not sync `cookies.txt`, `cache/auth/auth.json`, or `cache/auth/browser_profile/` unless you intentionally accept credential replication risk.

If you keep this repo elsewhere and expose it to Codex with a symlink, let `chezmoi` manage the symlink under `~/.codex/skills/` rather than the runtime cache.

## Scripts

- `scripts/inspect_topic.py`
- `scripts/ensure_cached.py`
- `scripts/query_topic.py`
- `scripts/summarize_topic.py`
- `scripts/export_topic.py`

## References

- `references/output_schema.md`
- `references/runtime_layout.md`
- `references/troubleshooting.md`
