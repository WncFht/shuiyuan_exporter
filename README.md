# Shuiyuan Cache Skill

这是一个 **cache-first 的 Shuiyuan 本地缓存 / 查询 / 导出仓库**，同时也是一个可以直接给 Codex 使用的 skill repo。

当前推荐把它理解成两层：

1. **数据层**：认证、同步、缓存、索引
2. **消费层**：查询、摘要、导出、skill 调用

当前主路径已经不是“直接联网导出 Markdown”，而是：

```text
auth -> ensure_cached -> query/summary -> export
```

## 当前推荐入口

### 1. 初始化环境

```bash
cd /Users/fanghaotian/Desktop/src/shuiyuan_exporter
uv python install 3.12
uv sync --group dev
```

### 2. 建立认证

推荐使用独立浏览器 profile + `auth.json`：

```bash
uv run python -m shuiyuan_cache.cli.auth_cli setup
```

默认会把运行时数据写到：

```text
~/.local/share/shuiyuan-cache-skill/
```

包括：

- `cache/auth/auth.json`
- `cache/auth/browser_profile/`
- `cookies.txt`

### 3. 确保 topic 已缓存

```bash
uv run python scripts/ensure_cached.py 456491
uv run python scripts/ensure_cached.py https://shuiyuan.sjtu.edu.cn/t/topic/456491 --refresh-mode incremental
```

### 4. 查询 / 摘要

```bash
uv run python scripts/query_topic.py 456491 --keyword 安全 --limit 5
uv run python scripts/summarize_topic.py 456491 --focus-keyword Openclaw
```

### 5. 导出 Markdown

```bash
uv run python scripts/export_topic.py 456491
```

导出默认落到：

```text
~/.local/share/shuiyuan-cache-skill/exports/<topic_id>/
```

## 运行时路径

当前推荐保持 **repo 只放代码和文档**，运行时数据放到 skill runtime 目录：

```text
~/.local/share/shuiyuan-cache-skill/
  cache/
  exports/
  cookies.txt
```

可以用这些环境变量覆盖：

- `SHUIYUAN_SKILL_HOME`
- `SHUIYUAN_CACHE_ROOT`
- `SHUIYUAN_COOKIE_PATH`
- `SHUIYUAN_EXPORT_ROOT`

详细结构见：

- `references/runtime_layout.md`
- `references/output_schema.md`
- `references/troubleshooting.md`

## 机器调用入口

给 skill / agent / 自动化优先使用：

- `scripts/inspect_topic.py`
- `scripts/ensure_cached.py`
- `scripts/query_topic.py`
- `scripts/summarize_topic.py`
- `scripts/export_topic.py`

这些脚本约定：

- `stdout` 只输出 JSON
- `stderr` 输出进度日志

## 兼容入口

下面这些入口仍保留，但已经视为 **legacy compatibility**：

- `uv run python -m shuiyuan_cache.cli.export_cli`
- `uv run python main.py`

它们仍可用，但不再是当前推荐工作流。

## 开发校验

```bash
uv run pre-commit install
uv run pre-commit run --all-files
uv run pytest
```

## 文档导航

优先阅读：

1. `SKILL.md`
2. `docs/RUNBOOK.md`
3. `docs/README.md`
4. `references/runtime_layout.md`

如果你要继续做结构整理或二次开发：

- `docs/SKILL_DESIGN.md`
- `docs/EXPORT_IO_AND_RATE_LIMITING.md`
- `docs/THREAD_POOL_REFACTOR_PLAN.md`
- `docs/REPO_REFACTOR_PLAN.md`

## 仓库整理说明

这次整理之后：

- 默认路径统一到 skill runtime
- 根目录不再推荐承载 `cache/`、`posts/`、`cookies.txt` 这类运行时数据
- 历史规划稿集中到 `docs/history/`
- `requirements.txt` 被移除，统一由 `pyproject.toml` + `uv.lock` 管理依赖
