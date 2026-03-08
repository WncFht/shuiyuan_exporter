# Shuiyuan 运行手册

状态：当前有效运行手册（skill-first / cache-first）

## 1. 当前推荐工作流

推荐顺序：

```text
auth -> ensure_cached -> query/summary -> export
```

含义：

1. 先建立长期可复用登录态；
2. 再把 topic 同步到本地缓存；
3. 查询和摘要尽量只读本地缓存；
4. 只有需要给人阅读 Markdown 时再导出。

## 2. 默认运行时目录

当前默认不会把运行时数据写在 repo 根目录，而是写到：

```text
~/.local/share/shuiyuan-cache-skill/
```

主要结构：

```text
~/.local/share/shuiyuan-cache-skill/
  cache/
  exports/
  cookies.txt
```

认证相关：

```text
cache/auth/auth.json
cache/auth/browser_profile/
```

详细结构见：`references/runtime_layout.md`。

## 3. 初始化（mac）

```bash
cd /Users/fanghaotian/Desktop/src/shuiyuan_exporter
uv python install 3.12
uv sync --group dev
```

## 4. 建立认证

推荐方式：独立浏览器 profile + `auth.json`。

```bash
uv run python -m shuiyuan_cache.cli.auth_cli setup
```

查看认证状态：

```bash
uv run python -m shuiyuan_cache.cli.auth_cli status
```

如果只想复用现有 profile 重新导出登录态：

```bash
uv run python -m shuiyuan_cache.cli.auth_cli refresh
```

说明：

- 默认使用 skill runtime 路径；
- 认证优先读取 `cache/auth/auth.json`；
- `cookies.txt` 只作为兼容和回退。

## 5. 缓存一个 topic

推荐使用机器安全的脚本入口：

```bash
uv run python scripts/ensure_cached.py 456491
uv run python scripts/ensure_cached.py https://shuiyuan.sjtu.edu.cn/t/topic/456491 --refresh-mode incremental
uv run python scripts/ensure_cached.py 456491 --refresh-mode full --no-images
```

如果你更喜欢传统 CLI，也可以：

```bash
uv run python -m shuiyuan_cache.cli.sync_cli 456491
```

## 6. 查询和摘要

查询：

```bash
uv run python scripts/query_topic.py 456491 --keyword 安全 --limit 5
uv run python scripts/query_topic.py 456491 --author FleetSnowfluff
uv run python scripts/query_topic.py 456491 --has-images --order desc
```

摘要：

```bash
uv run python scripts/summarize_topic.py 456491 --focus-keyword Openclaw
uv run python scripts/summarize_topic.py 456491 --only-op
uv run python scripts/summarize_topic.py 456491 --recent-days 7
```

这一层应尽量只读本地缓存，而不是重新联网抓取。

## 7. 导出 Markdown

```bash
uv run python scripts/export_topic.py 456491
```

默认输出：

```text
~/.local/share/shuiyuan-cache-skill/exports/<topic_id>/
```

导出策略：

- 优先读 `cache/raw/topics/<topic_id>/`；
- 引用楼层优先读 `cache/raw/post_refs/<topic_id>/`；
- 图片优先复用 `cache/media/images/`；
- 本地缺失时才补抓网络。

## 8. 机器输出约定

`scripts/*.py` 约定：

- `stdout`：只输出 JSON
- `stderr`：输出进度和阶段日志

适合：

- skill 调用
- shell pipeline
- 上层 agent 集成

## 9. 兼容入口

下面入口仍保留，但属于 legacy：

```bash
uv run python -m shuiyuan_cache.cli.export_cli
uv run python main.py
```

它们主要用于兼容旧习惯，不是当前推荐主路径。

## 10. 校验命令

```bash
uv run pre-commit run --all-files
uv run pytest
```

## 11. 进一步阅读

- `docs/README.md`
- `docs/SKILL_DESIGN.md`
- `docs/EXPORT_IO_AND_RATE_LIMITING.md`
- `references/runtime_layout.md`
- `references/output_schema.md`
- `references/troubleshooting.md`
