# Shuiyuan 本地运行手册

状态：当前运行手册（截至 2026-03-08）

## 1. 这份文档解决什么问题

面向当前已经实现好的仓库，这份手册只回答三件事：

1. 在 mac 上怎么把认证跑通；
2. 怎么把帖子同步到本地缓存；
3. 怎么在本地做导出、查询和摘要分析。

如果你想看设计背景，请读：

- `docs/SYSTEM_DESIGN.md`
- `docs/SCHEMA_AND_API.md`
- `docs/PHASE2_QUERY_ANALYSIS_DESIGN.md`

如果你只想把系统跑起来，优先看本文件。

## 2. 当前推荐工作流

当前仓库已经形成了比较清晰的分层：

1. `auth_cli`：管理登录态
2. `sync_cli`：把 Shuiyuan 帖子同步到本地缓存
3. `query_cli` / `summary_cli`：只读本地缓存做检索和摘要
4. `export_cli`：把缓存转换成 Markdown 阅读产物

推荐顺序是：

```text
auth -> sync -> query/summary -> export
```

也就是说：

- 先解决认证；
- 再把数据拉到本地；
- 后续分析尽量本地化；
- 只有需要给人看 Markdown 时再导出。

## 3. mac 上的初始化步骤

### 3.1 安装依赖

```bash
cd /Users/fanghaotian/Desktop/src/shuiyuan_exporter
uv python install 3.12
uv sync
```

### 3.2 建立独立浏览器认证

推荐使用项目自己的浏览器 profile，而不是长期手工复制 Cookie：

```bash
uv run python -m shuiyuan_cache.cli.auth_cli setup
```

默认行为：

- 使用独立的 Edge profile；
- 你手动登录一次饮水思源；
- 终端回车后保存认证状态。

落盘位置：

- `cache/auth/browser_profile/`
- `cache/auth/auth.json`
- `cookies.txt`

查看状态：

```bash
uv run python -m shuiyuan_cache.cli.auth_cli status
```

如果只是从现有 profile 重新导出认证：

```bash
uv run python -m shuiyuan_cache.cli.auth_cli refresh
```

## 4. 同步帖子到本地缓存

### 4.1 同步单个 topic

```bash
uv run python -m shuiyuan_cache.cli.sync_cli 456491
```

也可以传完整 URL：

```bash
uv run python -m shuiyuan_cache.cli.sync_cli https://shuiyuan.sjtu.edu.cn/t/topic/456491/
```

### 4.2 常用参数

```bash
uv run python -m shuiyuan_cache.cli.sync_cli 456491 --mode full
uv run python -m shuiyuan_cache.cli.sync_cli 456491 --mode refresh-tail --force
uv run python -m shuiyuan_cache.cli.sync_cli 456491 --no-images
```

### 4.3 主要缓存目录

```text
cache/
  auth/
  db/
  media/images/
  raw/topics/<topic_id>/
```

重点目录说明：

- `cache/raw/topics/<topic_id>/topic.json`：topic 元数据；
- `cache/raw/topics/<topic_id>/pages/json/*.json`：分页 JSON；
- `cache/raw/topics/<topic_id>/pages/raw/*.md`：分页 raw markdown；
- `cache/raw/post_refs/<topic_id>/*.raw.md`：按需抓取的单帖 raw；
- `cache/media/images/`：去重后的图片缓存；
- `cache/db/shuiyuan.sqlite`：结构化索引数据库。

## 5. 基于本地缓存做分析

### 5.1 查询

```bash
uv run python -m shuiyuan_cache.cli.query_cli 456491 --keyword 安全 --limit 5
uv run python -m shuiyuan_cache.cli.query_cli 456491 --author FleetSnowfluff
uv run python -m shuiyuan_cache.cli.query_cli 456491 --has-images --order desc
```

### 5.2 摘要

```bash
uv run python -m shuiyuan_cache.cli.summary_cli 456491 --focus-keyword Openclaw
uv run python -m shuiyuan_cache.cli.summary_cli 456491 --only-op
uv run python -m shuiyuan_cache.cli.summary_cli 456491 --recent-days 7
```

这一层默认应该尽量不联网，而是直接读本地数据库和缓存。

## 6. 导出 Markdown

### 6.1 当前导出策略

当前导出链路已经改成“缓存优先”：

- 优先读 `cache/raw/topics/<topic_id>/` 下已有的 `topic.json`、分页 raw、分页 json；
- 引用楼层时优先读 `raw/post_refs/<topic_id>/*.raw.md`；
- 图片优先复用 `cache/media/images/`；
- 只有本地缺失时才补抓网络。

这意味着：

- 先 `sync` 再 `export` 会更稳定；
- 重复导出同一个 topic 会明显更快；
- 导出和分析已经基本与抓取解耦。

### 6.2 导出命令

```bash
uv run python -m shuiyuan_cache.cli.export_cli -n -b 456491
```

兼容旧入口：

```bash
uv run python main.py -n -b 456491
```

输出位置：

```text
posts/456491/
```

## 7. 已验证的命令

以下命令在当前仓库中已经实际跑通：

```bash
uv run python -m shuiyuan_cache.cli.export_cli -n -b 456491
uv run python main.py -n -b 456491
uv run python -m shuiyuan_cache.cli.query_cli 456491 --keyword 安全 --limit 2
uv run python -m shuiyuan_cache.cli.summary_cli 456491 --focus-keyword Openclaw
```

## 8. 对后续 skill 的直接启发

如果后面要做 Shuiyuan skill，建议不要让 skill 直接承担“抓取 + 分析 + 导出”所有责任，而是拆成两段：

### 8.1 数据侧

- 用认证 profile 保持长期可用登录态；
- 用 `sync_cli` 或同等内部 API 增量拉取 topic；
- 持续积累本地缓存与数据库。

### 8.2 skill 侧

- 以本地缓存为主回答问题；
- 只在缓存缺失时触发抓取；
- 输出结构化 post 列表、摘要、相关帖子建议。

一句话说：

> 让抓取成为一个可重复的底层服务，让 skill 主要消费本地缓存。
