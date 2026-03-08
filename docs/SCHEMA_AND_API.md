# Shuiyuan 缓存 Schema 与接口契约

版本：`v0.1`  
状态：设计参考稿（当前仓库已部分实现，实际运行命令请优先参考 `docs/RUNBOOK.md`）  
依赖文档：`TECHNICAL_PLAN.md`、`docs/SYSTEM_DESIGN.md`、`docs/IMPLEMENTATION_ROADMAP.md`

## 1. 文档目标

这份文档只做两件事：

1. 明确第一阶段本地缓存系统的 **数据契约**；
2. 明确第一阶段 CLI / 服务 / skill 的 **接口契约**。

换句话说，这份文档回答的是“开始写代码时，表长什么样、文件长什么样、接口输入输出长什么样”。

---

## 2. 第一阶段范围

第一阶段聚焦：

- topic 元信息
- topic page json
- topic raw page
- post 结构化记录
- 图片 manifest
- 本地检索基础能力
- Markdown 导出兼容

第一阶段暂不强制覆盖：

- 音频 / 视频深处理
- OCR
- embedding / vector 检索
- 自动登录

---

## 3. 缓存目录契约

建议第一阶段固定如下目录约定：

```text
cache/
  raw/
    topics/
      <topic_id>/
        topic.json
        sync_state.json
        pages/
          json/
            0001.json
            0002.json
          raw/
            0001.md
            0002.md
    post_refs/
      <topic_id>/
        000001.raw.md
  media/
    images/
      <bucket>/
        <media_key>.<ext>
  db/
    shuiyuan.sqlite
  exports/
    markdown/
      <topic_id>/
        <topic_id> <title>.md
        images/
```

### 3.1 路径规则

- `topic_id` 统一使用纯数字字符串目录
- 页面统一使用四位零填充：`0001.json`
- 单帖 raw 使用六位零填充：`000001.raw.md`
- `media_key` 优先使用论坛的稳定 key / sha；缺失时退化为 URL hash
- `bucket` 可用 `media_key` 前 2 位做分桶，避免单目录过多文件

### 3.2 原始缓存文件契约

#### `topic.json`

- 来源：`/t/<topic>.json?...`
- 内容：原始 JSON 响应，尽量不做改写
- 用途：重建 topic 元信息、重新规划同步页面

#### `pages/json/0001.json`

- 来源：`/t/<topic>.json?page=1`
- 内容：原始 JSON 响应
- 用途：解析 post 列表、作者、时间、cooked HTML

#### `pages/raw/0001.md`

- 来源：`/raw/<topic>?page=1`
- 内容：原始文本响应
- 用途：保留原始 Markdown 视图、后续重建 raw_markdown / quote 信息

#### `post_refs/<topic_id>/000001.raw.md`

- 来源：`/raw/<topic>/1`
- 内容：单帖原始 raw
- 用途：仅在需要更精细 post 级 raw 时补抓

### 3.3 `sync_state.json` 契约

建议结构：

```json
{
  "topic_id": 351551,
  "last_known_posts_count": 6217,
  "last_known_last_posted_at": "2026-03-07T15:16:17.716Z",
  "last_synced_json_page": 311,
  "last_synced_raw_page": 63,
  "last_synced_post_number": 6217,
  "last_sync_mode": "full",
  "last_sync_status": "success",
  "last_sync_started_at": "2026-03-08T10:00:00Z",
  "last_sync_finished_at": "2026-03-08T10:05:00Z",
  "last_sync_error": null
}
```

用途：

- 做增量更新判断
- 快速展示同步状态
- 作为 SQLite `sync_state` 的文件级镜像

---

## 4. SQLite Schema 契约

以下是第一阶段推荐的最小 SQL schema 草案。

## 4.1 `topics`

```sql
CREATE TABLE IF NOT EXISTS topics (
  topic_id INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  category_id INTEGER,
  tags_json TEXT,
  created_at TEXT,
  last_posted_at TEXT,
  posts_count INTEGER,
  reply_count INTEGER,
  views INTEGER,
  like_count INTEGER,
  visible INTEGER,
  archived INTEGER,
  closed INTEGER,
  topic_json_path TEXT,
  created_ts INTEGER NOT NULL,
  updated_ts INTEGER NOT NULL
);
```

## 4.2 `posts`

```sql
CREATE TABLE IF NOT EXISTS posts (
  post_id INTEGER PRIMARY KEY,
  topic_id INTEGER NOT NULL,
  post_number INTEGER NOT NULL,
  username TEXT,
  display_name TEXT,
  created_at TEXT,
  updated_at TEXT,
  reply_to_post_number INTEGER,
  is_op INTEGER DEFAULT 0,
  like_count INTEGER DEFAULT 0,
  raw_markdown TEXT,
  cooked_html TEXT,
  plain_text TEXT,
  raw_page_no INTEGER,
  json_page_no INTEGER,
  raw_post_path TEXT,
  has_images INTEGER DEFAULT 0,
  has_attachments INTEGER DEFAULT 0,
  has_audio INTEGER DEFAULT 0,
  has_video INTEGER DEFAULT 0,
  image_count INTEGER DEFAULT 0,
  hash_raw TEXT,
  hash_cooked TEXT,
  created_ts INTEGER NOT NULL,
  updated_ts INTEGER NOT NULL,
  UNIQUE(topic_id, post_number)
);
```

## 4.3 `media`

```sql
CREATE TABLE IF NOT EXISTS media (
  media_id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic_id INTEGER NOT NULL,
  post_id INTEGER,
  post_number INTEGER,
  media_type TEXT NOT NULL,
  upload_ref TEXT,
  resolved_url TEXT,
  local_path TEXT,
  mime_type TEXT,
  file_ext TEXT,
  media_key TEXT,
  download_status TEXT,
  content_length INTEGER,
  created_ts INTEGER NOT NULL,
  updated_ts INTEGER NOT NULL,
  UNIQUE(topic_id, post_number, media_type, upload_ref)
);
```

## 4.4 `post_quotes`

```sql
CREATE TABLE IF NOT EXISTS post_quotes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic_id INTEGER NOT NULL,
  post_id INTEGER NOT NULL,
  post_number INTEGER NOT NULL,
  quoted_topic_id INTEGER,
  quoted_post_number INTEGER,
  quote_url TEXT,
  created_ts INTEGER NOT NULL
);
```

## 4.5 `sync_state`

```sql
CREATE TABLE IF NOT EXISTS sync_state (
  topic_id INTEGER PRIMARY KEY,
  last_known_posts_count INTEGER,
  last_known_last_posted_at TEXT,
  last_synced_json_page INTEGER,
  last_synced_raw_page INTEGER,
  last_synced_post_number INTEGER,
  last_sync_mode TEXT,
  last_sync_status TEXT,
  last_sync_started_at TEXT,
  last_sync_finished_at TEXT,
  last_sync_error TEXT,
  updated_ts INTEGER NOT NULL
);
```

## 4.6 `posts_fts`

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(
  topic_id UNINDEXED,
  post_id UNINDEXED,
  post_number UNINDEXED,
  username,
  plain_text,
  raw_markdown
);
```

### 4.6.1 FTS 更新策略

建议第一阶段先使用“应用侧同步更新”：

- post upsert 后同步更新 `posts_fts`
- 暂不强制使用 SQLite trigger
- 便于调试和追踪逻辑

---

## 5. 结构化对象契约

建议未来代码内部至少存在如下逻辑对象。

## 5.1 `TopicRecord`

```text
TopicRecord
  topic_id: int
  title: str
  category_id: int | None
  tags: list[str]
  created_at: str | None
  last_posted_at: str | None
  posts_count: int
  reply_count: int | None
  views: int | None
  like_count: int | None
  visible: bool | None
  archived: bool | None
  closed: bool | None
  topic_json_path: str
```

## 5.2 `PostRecord`

```text
PostRecord
  post_id: int
  topic_id: int
  post_number: int
  username: str | None
  display_name: str | None
  created_at: str | None
  updated_at: str | None
  reply_to_post_number: int | None
  is_op: bool
  like_count: int
  raw_markdown: str | None
  cooked_html: str | None
  plain_text: str | None
  raw_page_no: int | None
  json_page_no: int | None
  raw_post_path: str | None
  has_images: bool
  has_attachments: bool
  has_audio: bool
  has_video: bool
  image_count: int
```

## 5.3 `MediaRecord`

```text
MediaRecord
  topic_id: int
  post_id: int | None
  post_number: int | None
  media_type: str
  upload_ref: str | None
  resolved_url: str | None
  local_path: str | None
  file_ext: str | None
  media_key: str | None
  download_status: str
```

## 5.4 `SyncPlan`

```text
SyncPlan
  topic_id: int
  mode: str
  fetch_topic_json: bool
  json_pages_to_fetch: list[int]
  raw_pages_to_fetch: list[int]
  post_numbers_to_fetch: list[int]
  should_download_images: bool
```

---

## 6. 同步接口契约

第一阶段建议统一提供一套“代码内部接口”，后续 CLI 与 skill 都复用。

## 6.1 `sync_topic(...)`

### 输入

```python
sync_topic(
  topic: str | int,
  mode: Literal["full", "incremental", "refresh-tail"] = "incremental",
  with_images: bool = True,
  force: bool = False,
) -> SyncResult
```

### 输出

```text
SyncResult
  topic_id: int
  title: str | None
  mode: str
  fetched_json_pages: int
  fetched_raw_pages: int
  fetched_post_raw_count: int
  inserted_posts: int
  updated_posts: int
  downloaded_images: int
  skipped_images: int
  status: str
  errors: list[str]
```

### 行为约定

- 默认优先走本地缓存判断
- `force=True` 时忽略部分缓存判断
- 同步失败时尽量保留已成功落盘的部分数据
- 图片下载失败不应让整 topic 同步整体失败

## 6.2 `sync_topics(...)`

### 输入

```python
sync_topics(
  topics: list[str | int],
  mode: Literal["full", "incremental", "refresh-tail"] = "incremental",
  with_images: bool = True,
) -> list[SyncResult]
```

### 行为约定

- 串行即可作为第一阶段默认行为
- 后续再考虑多 topic 并发

---

## 7. 查询接口契约

## 7.1 `query_topic_posts(...)`

### 输入

```python
query_topic_posts(
  topic_id: int,
  keyword: str | None = None,
  author: str | None = None,
  only_op: bool = False,
  date_from: str | None = None,
  date_to: str | None = None,
  has_images: bool | None = None,
  limit: int = 50,
) -> QueryResult
```

### 输出

```text
QueryResult
  topic_id: int
  total_hits: int
  items: list[QueryPostItem]

QueryPostItem
  post_id: int
  post_number: int
  username: str | None
  created_at: str | None
  plain_text: str | None
  image_paths: list[str]
  score: float | None
```

## 7.2 `summarize_topic(...)`

### 输入

```python
summarize_topic(
  topic_id: int,
  only_op: bool = False,
  recent_days: int | None = None,
  focus_keywords: list[str] | None = None,
  include_images: bool = False,
) -> TopicSummary
```

### 输出

```text
TopicSummary
  topic_id: int
  title: str
  summary_text: str
  top_authors: list[tuple[str, int]]
  top_keywords: list[tuple[str, int]]
  key_posts: list[int]
  image_post_numbers: list[int]
```

## 7.3 `find_related_topics(...)`

### 输入

```python
find_related_topics(
  seed_topic_id: int | None = None,
  keyword: str | None = None,
  scope: Literal["local", "remote", "both"] = "both",
  limit: int = 20,
) -> list[RelatedTopic]
```

### 输出

```text
RelatedTopic
  topic_id: int
  title: str
  source: str
  reason: str
  tags: list[str]
  last_posted_at: str | None
```

---

## 8. CLI 契约

第一阶段推荐至少有以下 CLI 形式。

## 8.1 `sync`

```bash
uv run python -m shuiyuan_cache.cli.sync_cli 351551
uv run python -m shuiyuan_cache.cli.sync_cli 351551 --mode full
uv run python -m shuiyuan_cache.cli.sync_cli 351551 --no-images
```

## 8.2 `query`

```bash
uv run python -m shuiyuan_cache.cli.query_cli 351551 --keyword 银行 --only-op
uv run python -m shuiyuan_cache.cli.query_cli 351551 --author 风花雪月 --limit 20
```

## 8.3 `export`

```bash
uv run python -m shuiyuan_cache.cli.export_cli -n -b 351551
```

说明：

- 规划阶段最初只要求先落地 `sync_cli`
- 当前仓库已经实现 `sync_cli` / `query_cli` / `summary_cli` / `export_cli`
- `export_cli` 当前定位仍然是兼容 Markdown 导出，而不是最终的 skill 输出接口

---

## 9. Skill 契约

未来 skill 不应该暴露过多底层实现细节。

建议对外只保留“高层任务接口”：

- 同步 topic
- 查询 topic
- 总结 topic
- 找相关 topic
- 导出 topic

Skill 层返回结果时，建议显式区分：

- 数据来自本地缓存
- 数据来自远端同步
- 数据是否包含图片上下文

---

## 10. 第一阶段实现顺序建议

建议按这个顺序开始写代码：

1. `core/config.py`
2. `store/paths.py`
3. `fetch/session.py`
4. `fetch/topic_fetcher.py`
5. `store/raw_store.py`
6. `store/sqlite_store.py`
7. `fetch/sync_planner.py`
8. `sync_cli`
9. 图片 manifest 与图片下载
10. query / summary 接口

---

## 11. 边界与约束

第一阶段明确边界：

- 不追求 raw page 到 post 级 raw 的完全精确重建
- `raw_markdown` 可以允许暂时为空或部分为空
- `plain_text` 优先用 cooked HTML 提取
- 图片优先保证落盘和关联，不追求内容理解

---

## 12. 总结

这份契约文档的重点不是“理论上最优”，而是：

- 让第一阶段实现有明确边界
- 让不同模块之间有稳定输入输出
- 让后续 skill 可以建立在稳定的数据底座上
- 让 Git 中每一步重构都能对照契约推进
