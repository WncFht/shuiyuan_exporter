# Shuiyuan Skill 设计草案

状态：草案（截至 2026-03-08）

## 1. 目标

这个 skill 的目标不应该只是“帮我抓一个帖子”，而应该是：

- 复用现有 `shuiyuan_cache/` 的认证、同步、查询、摘要能力；
- 优先使用本地缓存回答问题；
- 只有在缓存缺失或明确要求刷新时才联网；
- 输出结构化结果，便于后续继续分析，而不是只吐 Markdown。

一句话说：

> 这个 skill 的本质是“Shuiyuan 本地知识工作台”，不是“网页爬虫快捷键”。

## 2. 设计原则

### 2.1 缓存优先

skill 的默认行为应该是：

1. 先检查 topic 是否已缓存；
2. 若已缓存，优先走本地查询和分析；
3. 若未缓存或用户要求刷新，再触发同步；
4. 同步完成后再回答。

### 2.2 结构化优先

skill 的第一输出不应是 Markdown，而应是结构化数据：

- topic 元信息
- post 列表
- 关键作者
- 图片路径
- 时间范围
- 命中原因
- 引用关系

Markdown 导出更适合作为附加能力，而不是核心接口。

### 2.3 认证与分析解耦

skill 不应在每次执行时都处理登录流程。

推荐模式：

- 认证由独立命令维护：`auth_cli`
- 抓取由独立命令或 API 维护：`sync_cli`
- skill 主要消费本地缓存

这样 skill 会更稳定，也更适合批量分析。

## 3. 推荐能力边界

### 3.1 MVP 必须有

1. `ensure_topic_cached`
2. `query_topic_posts`
3. `summarize_topic`
4. `inspect_topic`
5. `export_topic_markdown`（兼容用途）

### 3.2 第二阶段再做

1. `find_related_topics`
2. `list_latest_topics`
3. `search_forum_topics`
4. `topic_compare`

### 3.3 暂不做

- OCR 主链路
- 音频/视频深处理
- embedding / vector 检索
- 自动替用户登录学校账号

## 4. 建议的 skill 接口

### 4.1 `ensure_topic_cached`

输入：

- `topic`: topic id 或 URL
- `refresh_mode`: `none | incremental | refresh-tail | full`
- `download_images`: bool

输出：

- `topic_id`
- `cache_hit`
- `sync_executed`
- `sync_summary`

### 4.2 `query_topic_posts`

输入：

- `topic`
- `keyword`
- `author`
- `only_op`
- `date_from`
- `date_to`
- `has_images`
- `limit`
- `offset`
- `order`

输出：

- `topic_id`
- `title`
- `total_hits`
- `posts[]`

每条 `post` 建议包含：

- `post_number`
- `username`
- `created_at`
- `plain_text`
- `image_paths`
- `reply_to_post_number`
- `quote_targets`

### 4.3 `summarize_topic`

输入：

- `topic`
- `only_op`
- `recent_days`
- `focus_keywords[]`
- `include_images`

输出：

- `topic_id`
- `title`
- `time_range`
- `post_count_in_scope`
- `top_authors`
- `key_posts`
- `image_posts`
- `summary`

### 4.4 `inspect_topic`

定位是“给操作者看缓存状态”，而不是给终端用户看。

输入：

- `topic`

输出：

- topic 缓存是否存在
- raw/json 页数
- post 数
- media 数
- 最后同步时间
- 是否缺页

### 4.5 `find_related_topics`

这个能力后面很重要，但不要太早做重。

第一版建议支持三类来源：

1. topic 内正文/回复里提到的其他 topic 链接
2. 基于标题关键词的 forum search
3. 基于标签、分类、时间窗口的启发式推荐

## 5. skill 的实际实现方式

### 5.1 不直接包 CLI

skill 不应该只是“帮你执行 shell 命令”。

更好的做法是整理一层稳定服务接口，例如未来增加：

- `shuiyuan_cache/skill_api/cache_service.py`
- `shuiyuan_cache/skill_api/query_service.py`
- `shuiyuan_cache/skill_api/related_service.py`

CLI 继续保留，但 skill 优先调用包内 API。

### 5.2 可以暂时复用现有 CLI 逻辑

在真正抽出 service 之前，skill 的原型阶段可以先复用：

- `sync_cli` 对应的同步逻辑
- `query_cli` 对应的查询逻辑
- `summary_cli` 对应的摘要逻辑
- `inspect_cli` 对应的检查逻辑

但中期一定要下沉到稳定的 Python API。

## 6. 推荐的 skill 目录形态

如果后面正式做成 Codex skill，我建议目录大致如下：

```text
shuiyuan-cache-skill/
  SKILL.md
  references/
    cli_contracts.md
    output_schema.md
    troubleshooting.md
  scripts/
    ensure_cached.py
    query_topic.py
    summarize_topic.py
    inspect_topic.py
```

### 6.1 `SKILL.md` 应该很短

只写：

- 何时使用这个 skill
- 默认采用缓存优先策略
- 遇到缓存缺失时如何同步
- 结果输出应该保持哪些字段

### 6.2 `references/` 放细节

比如：

- topic / post 输出 schema
- 常用命令映射
- 认证排障
- 相关帖子发现策略

### 6.3 `scripts/` 放低自由度动作

比如：

- 规范化 topic 输入
- 统一调用 sync/query/summary
- 把输出整理成稳定 JSON

## 7. 推荐的对话能力

我建议这个 skill 的交互能力至少覆盖：

1. “帮我同步这个 topic”
2. “总结这个 topic 在说什么”
3. “找出提到某个关键词的楼层”
4. “只看楼主在最近 7 天说了什么”
5. “列出带图的关键楼层”
6. “看看这个 topic 有没有缓存完整”
7. “基于这个 topic 找相关帖子”

## 8. 我建议的实现顺序

### Step 1

先补一层稳定的 Python service API：

- `ensure_cached(topic, mode, download_images)`
- `query_posts(...)`
- `summarize_topic(...)`
- `inspect_topic(...)`

### Step 2

把输出 schema 定死，避免 skill 直接依赖 CLI 打印文本。

### Step 3

再创建真正的 Codex skill 文件夹与 `SKILL.md`。

### Step 4

最后再加 related topics 能力。

## 9. 结论

当前仓库已经具备 skill 化的基础条件：

- 有稳定认证来源
- 有本地缓存
- 有结构化查询
- 有摘要能力
- 有兼容导出链路

真正还缺的是：

1. 面向 skill 的稳定 service API；
2. 统一的结构化输出 schema；
3. related topics 的能力补齐。

所以我建议下一步不是直接写一个很重的 skill，而是先把 **service API + output schema** 做薄做稳。
