# Troubleshooting

## Auth expired or missing

Rebuild auth state with the same runtime paths used by the skill scripts:

```bash
uv run python -m shuiyuan_cache.cli.auth_cli setup   --cache-root "$HOME/.local/share/shuiyuan-cache-skill/cache"   --cookie-path "$HOME/.local/share/shuiyuan-cache-skill/cookies.txt"
```

Check status:

```bash
uv run python -m shuiyuan_cache.cli.auth_cli status   --cache-root "$HOME/.local/share/shuiyuan-cache-skill/cache"   --cookie-path "$HOME/.local/share/shuiyuan-cache-skill/cookies.txt"
```

## Topic not cached

Run:

```bash
uv run python scripts/ensure_cached.py <topic>
```

## Need a stronger refresh

Use one of:

- `--refresh-mode incremental`
- `--refresh-mode refresh-tail`
- `--refresh-mode full`

## Export produced incomplete media links

Run `ensure_cached.py` first so the raw/json/image cache is available, then rerun `export_topic.py`.

## Multiple machines

Sync the repo with Git. Do not sync runtime data such as:

- `cache/`
- `exports/`
- `cookies.txt`
- browser profile data
