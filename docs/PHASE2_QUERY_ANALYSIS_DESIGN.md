# Phase 2 设计稿：本地查询、Inspect 与基础摘要

版本：`v0.1`  
状态：待评审  
依赖文档：`TECHNICAL_PLAN.md`、`docs/SYSTEM_DESIGN.md`、`docs/SCHEMA_AND_API.md`、`docs/PHASE1_EXECUTION_SPEC.md`

## 1. 文档说明

### 1.1 为什么这里还叫 Phase 2

原始路线文档里，`Phase 2` 被定义为“SQLite 与 post 规范化”；但由于当前工程实现中已经提前完成了：

- 原始页面缓存
- SQLite 基础 schema
- `topics/posts/sync_state/media` 的初步落库
- 最小 `sync_cli`

所以在**当前实际进度**下，下一步最自然的阶段已经变成：

> **基于本地缓存，完成 topic 级查询、inspect、基础摘要和图片上下文组织。**

为了跟当前交流习惯保持一致，本文把这一步称为 **Phase 2**。

### 1.2 本文目标

本文只讨论“下一阶段要做什么”，不落代码实现。重点是把下面这些问题定清楚：

1. 本地查询应该支持哪些过滤能力；
2. `inspect` 应该展示哪些缓存与同步信息；
3. 基础摘要做到什么程度算 MVP；
4. 图片上下文应该如何组织给后续 LLM；
5. CLI、内部接口和数据库需要怎么补强；
6. 本阶段应如何拆任务与验收。

---

## 2. 当前基线

在进入 Phase 2 之前，当前系统已经具备：

- `sync_cli` 可对单个 topic 做全量 / 增量 / tail refresh 同步；
- 原始 `topic.json`、分页 `json/raw` 已能落盘；
- SQLite 已有 `topics`、`posts`、`media`、`sync_state`、`posts_fts`；
- 图片可下载并写入 media 记录；
- 同步状态可以在文件和 SQLite 中持久化。

这意味着下一阶段不必再重复解决：

- Cookie 注入
- topic 分页抓取
- 原始缓存目录设计
- SQLite 初始 schema

下一阶段要解决的是：

- **如何把这些数据变成可用的本地查询能力。**

---

## 3. Phase 2 总目标

Phase 2 的总目标是：

> **让系统能在“已同步 topic”的前提下，不联网或尽量少联网地回答常见问题。**

这些问题包括但不限于：

- 这个 topic 最近有没有更新？
- 这个 topic 一共有多少楼、多少作者、多少图片？
- 只看楼主最近说了什么？
- 找出提到某个关键词的楼层；
- 某个作者都说了什么；
- 某个时间区间有哪些相关讨论；
- 带图的楼层有哪些；
- 这帖最近 7 天/30 天在聊什么；
- 后续给 LLM 做总结时，需要哪些图片上下文。

---

## 4. Phase 2 范围

### 4.1 本阶段必做

本阶段建议必须完成：

1. `query` 查询服务
2. `inspect` 检查服务
3. `summary` 基础摘要服务
4. `query_cli`
5. `inspect_cli`
6. 最小 `summary_cli` 或等价内部接口
7. SQLite 查询辅助索引补强
8. 图片上下文拼装逻辑
9. 对 `only_op`、作者、时间、关键词、图片过滤的统一语义定义

### 4.2 本阶段可选

可选但不强制：

- `export` 与新查询层对齐
- query 结果高亮
- topic 热词简易统计
- 最近活跃作者排行

### 4.3 本阶段不做

明确不做：

- OCR
- embedding / vector 检索
- related topics 远端搜索整合
- 复杂摘要链路（例如自动生成长报告）
- 多 topic 聚合查询
- 改造现有 legacy 导出器入口

---

## 5. 目标使用方式

本阶段完成后，希望用户至少能这样使用：

### 5.1 Inspect

```bash
uv run python -m shuiyuan_cache.cli.inspect_cli 456491
```

预期用途：

- 看 topic 是否已同步；
- 看同步状态是否成功；
- 看原始文件是否齐全；
- 看 SQLite 里记录数是否合理；
- 看图片数量；
- 看最近更新时间。

### 5.2 Query

```bash
uv run python -m shuiyuan_cache.cli.query_cli 351551 --keyword 银行 --only-op
uv run python -m shuiyuan_cache.cli.query_cli 351551 --author 风花雪月 --limit 20
uv run python -m shuiyuan_cache.cli.query_cli 351551 --date-from 2026-03-01 --has-images
```

预期用途：

- 快速找楼层；
- 做楼内检索；
- 只看楼主；
- 给后续 LLM 喂更精确的上下文。

### 5.3 Summary

```bash
uv run python -m shuiyuan_cache.cli.summary_cli 351551 --only-op --recent-days 30
```

预期用途：

- 得到一个 topic 的短摘要；
- 看最近一段时间楼里在讨论什么；
- 作为更深层分析的第一步。

---

## 6. Phase 2 核心能力设计

## 6.1 Inspect 能力

`inspect` 的定位不是检索内容，而是“检查本地缓存状态”。

### 6.1.1 输出应包含的字段

建议至少输出：

- `topic_id`
- `title`
- `posts_count`（topic 元信息）
- `db_post_count`（SQLite 中 posts 数）
- `json_page_count`
- `raw_page_count`
- `image_count`
- `last_posted_at`
- `last_sync_status`
- `last_sync_mode`
- `last_sync_finished_at`
- `cache_root`
- `topic_cache_path`
- `topic_json_exists`
- `sync_state_exists`

### 6.1.2 额外的健康检查

建议支持：

- 检查 `topic.json` 是否存在；
- 检查分页文件是否缺页；
- 检查 SQLite 中 `posts_count` 与 topic 元信息是否接近；
- 检查 `media` 表中的图片记录是否与本地文件数量近似一致。

### 6.1.3 为什么 inspect 很重要

它是后续所有 query / summary 的前置检查工具。很多时候用户以为“查询不准”，其实是缓存没同步完整或 Cookie 失效导致的。

---

## 6.2 Query 能力

这是本阶段最重要的部分。

### 6.2.1 最小过滤维度

`query_topic_posts(...)` 第一阶段建议支持：

- `topic_id`
- `keyword`
- `author`
- `only_op`
- `date_from`
- `date_to`
- `has_images`
- `limit`
- `offset`
- `order`

### 6.2.2 `keyword` 语义

建议第一阶段采用：

- 优先用 `posts_fts` 做全文检索；
- keyword 为空时，按普通 SQL 过滤；
- 暂不做复杂布尔搜索语法；
- 暂不做同义词扩展；
- 暂不做拼音、近义改写。

### 6.2.3 `author` 语义

建议：

- 先按 `username` 精确匹配；
- 后续如果需要再扩展模糊匹配。

### 6.2.4 `only_op` 语义

建议：

- 先以 `post_number == 1` 的作者为 topic OP；
- 对该 topic 内所有同作者发言视为楼主发言；
- 第一阶段不处理“楼主改名”这种极少见复杂情况。

### 6.2.5 `date_from/date_to` 语义

建议：

- 使用 `created_at` 过滤；
- 输入允许 ISO 日期，如 `2026-03-01`；
- 内部按 UTC 文本或标准时间戳比较。

### 6.2.6 `has_images` 语义

建议：

- 以 `posts.has_images = 1` 为准；
- 不再扫描 raw/cooked 临时判断。

### 6.2.7 返回内容

每条 query item 建议返回：

- `post_id`
- `post_number`
- `username`
- `created_at`
- `plain_text`
- `image_paths`
- `image_count`
- `score`（若使用 FTS）

### 6.2.8 为什么返回图片路径

因为后续你很可能会让 LLM“读这几层 + 对应截图”，所以 query 接口应该天然把图片上下文一并组织出来，而不是后续再临时查一次 `media` 表。

---

## 6.3 Summary 能力

### 6.3.1 本阶段定位

本阶段的 summary 不追求“特别聪明”，只追求：

- 稳定；
- 快速；
- 可解释；
- 足够给人或 LLM 做下一步分析。

### 6.3.2 MVP 输出

建议 `summarize_topic(...)` 最少输出：

- `title`
- `topic_id`
- `summary_text`
- `time_range`
- `post_count_in_scope`
- `top_authors`
- `top_keywords`
- `image_post_numbers`
- `key_posts`

### 6.3.3 `summary_text` 怎么来

第一阶段建议用规则化摘要而不是全自动大模型摘要：

- 概括 topic 标题与时间范围；
- 统计近 N 天楼内发帖量；
- 列出高频作者；
- 列出高频关键词；
- 截取若干高信号楼层文本拼成 summary context。

也就是说，第一阶段的 summary 更像：

> **结构化摘要上下文生成器**

而不是“最终智能总结器”。

### 6.3.4 为什么这样设计

因为这更稳定，也更适合作为未来 LLM 分析的前置层。

---

## 7. 图片上下文设计

### 7.1 原则

图片在 Phase 2 中的处理目标不是理解图片，而是：

- 找到图片；
- 把图片组织给调用方；
- 让调用方能决定是否把图片交给 LLM。

### 7.2 推荐返回结构

对于 query / summary 中命中的帖子，建议统一附带：

- `image_count`
- `image_paths[]`
- `image_media_keys[]`（可选）

### 7.3 图片上限策略

为了防止单次返回过大，建议：

- query 默认每条 post 最多返回前 `N=3` 张图路径；
- summary 默认只返回关键楼层对应的图；
- 需要完整图集时由 `inspect` 或单独接口提供。

### 7.4 为什么这比 OCR 更适合当前阶段

因为当前目标是把本地分析链条打通，而不是马上解决图像理解本身。

---

## 8. 数据层补强建议

虽然 SQLite 基础表已经有了，但进入查询阶段后，建议补一些查询友好索引。

### 8.1 推荐索引

建议至少增加：

- `posts(topic_id, post_number)`
- `posts(topic_id, username)`
- `posts(topic_id, created_at)`
- `posts(topic_id, has_images)`
- `media(topic_id, post_number, media_type)`

### 8.2 FTS 使用策略

Phase 2 中建议：

- keyword 查询统一通过 `posts_fts` 进入；
- 再联表 `posts` 取结构化字段；
- 如 keyword 为空，则直接查 `posts`。

### 8.3 是否需要立刻加入 trigger

不建议立刻上 SQLite trigger。当前阶段继续保持“应用层更新 FTS”更容易调试。

---

## 9. 内部接口设计

## 9.1 `inspect_topic(...)`

```python
inspect_topic(topic_id: int) -> TopicInspectResult
```

建议输出：

```text
TopicInspectResult
  topic_id
  title
  topic_posts_count
  db_post_count
  json_page_count
  raw_page_count
  media_image_count
  image_file_count
  last_posted_at
  last_sync_status
  last_sync_mode
  last_sync_finished_at
  cache_path
  issues: list[str]
```

## 9.2 `query_topic_posts(...)`

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
  offset: int = 0,
  order: str = "asc",
) -> QueryResult
```

## 9.3 `summarize_topic(...)`

```python
summarize_topic(
  topic_id: int,
  only_op: bool = False,
  recent_days: int | None = None,
  focus_keywords: list[str] | None = None,
  include_images: bool = False,
) -> TopicSummary
```

---

## 10. CLI 设计

## 10.1 `inspect_cli`

建议支持：

```bash
uv run python -m shuiyuan_cache.cli.inspect_cli 456491
```

可选参数：

- `--cache-root`
- `--cookie-path`（主要用于定位配置，不一定要联网）
- `--json`

## 10.2 `query_cli`

建议支持：

```bash
uv run python -m shuiyuan_cache.cli.query_cli 351551 --keyword 银行
uv run python -m shuiyuan_cache.cli.query_cli 351551 --only-op --recent-days 30
uv run python -m shuiyuan_cache.cli.query_cli 351551 --author 风花雪月 --has-images
```

可选参数：

- `--keyword`
- `--author`
- `--only-op`
- `--date-from`
- `--date-to`
- `--has-images`
- `--limit`
- `--offset`
- `--order asc|desc`
- `--json`

## 10.3 `summary_cli`

建议支持：

```bash
uv run python -m shuiyuan_cache.cli.summary_cli 351551 --only-op --recent-days 7
```

---

## 11. 实施拆分建议

Phase 2 建议按下面顺序做：

1. 增加 inspect service
2. 增加 inspect_cli
3. 增加基础 SQL/FTS query service
4. 增加 query_cli
5. 增加图片上下文拼装
6. 增加基础 summary service
7. 增加 summary_cli
8. 做小范围真实 topic 验证

### 11.1 为什么先做 inspect

因为 Phase 2 的所有问题都建立在“缓存已经靠谱”之上，而 inspect 是最直接的验证工具。

### 11.2 为什么 query 在 summary 前

因为 summary 需要依赖 query / stats / filtering 的结果，先做 query 会让 summary 更稳定。

---

## 12. 验收标准

Phase 2 完成后，至少应满足：

### 12.1 Inspect

- 能对已同步 topic 输出缓存状态；
- 能指出明显缺页或缺文件问题；
- 不联网也能工作。

### 12.2 Query

- 能按关键词检索 topic；
- 能只看楼主；
- 能按作者过滤；
- 能按时间区间过滤；
- 能返回图片路径；
- 不联网也能工作。

### 12.3 Summary

- 能给出 topic 基础摘要；
- 能只总结楼主内容；
- 能支持最近 N 天范围；
- 输出足够给人或 LLM 继续使用。

---

## 13. 风险与注意事项

### 13.1 `raw_markdown` 目前并不完整

当前 `posts.raw_markdown` 还不是完整精确重建版，所以 Query 和 Summary 第一阶段建议主要依赖：

- `plain_text`
- `cooked_html`
- `username`
- `created_at`
- `media`

而不是完全依赖 `raw_markdown`。

### 13.2 FTS 结果质量

FTS 对中文可用，但不一定完美。第一阶段先确保“能用”，后续再考虑更复杂的中文检索优化。

### 13.3 图片过多导致返回过大

必须控制单次 query / summary 返回的图片数量与路径数量。

---

## 14. 一句话总结

Phase 2 的目标不是让系统一下子变成“会深度理解帖子”的智能体，而是先把下面这件事做好：

> **在本地缓存已经存在的前提下，让系统稳定地检查 topic、检索楼层、组织图片上下文，并产出可供后续 LLM 使用的基础摘要。**
