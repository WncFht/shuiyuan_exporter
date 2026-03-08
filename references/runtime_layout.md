# Runtime Layout

The skill repo should remain code-only.

Default runtime root:

```text
~/.local/share/shuiyuan-cache-skill/
```

Default derived paths:

```text
~/.local/share/shuiyuan-cache-skill/
  cache/
    auth/
    db/
    media/
    raw/
  exports/
  cookies.txt
```

Environment overrides:

- `SHUIYUAN_CACHE_ROOT`
- `SHUIYUAN_COOKIE_PATH`
- `SHUIYUAN_EXPORT_ROOT`

Notes:

- `cache/auth/auth.json` is produced by `auth_cli` when using the same cache root.
- `cookies.txt` is only a fallback; the preferred auth source remains `auth.json`.
- `exports/` is for Markdown output only and should not be committed.
