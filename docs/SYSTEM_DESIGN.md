# Shuiyuan 本地缓存分析系统详细设计

版本：`v0.1`  
状态：设计稿，待评审  
依赖上位文档：`TECHNICAL_PLAN.md`

## 1. 文档目标

这份文档是在 `TECHNICAL_PLAN.md` 基础上的进一步细化，重点回答下面几个“真正开始写代码前必须明确”的问题：

1. 系统的模块边界怎么拆；
2. SQLite 和文件缓存具体怎么配合；
3. 抓取、规范化、媒体、索引、分析分别有哪些输入输出；
4. 增量更新在工程上如何落地；
5. 未来 skill 应暴露哪些高层接口；
6. 第一阶段实现时哪些内容必须做，哪些可以延后。

本文档仍然不涉及代码实现，只做系统设计。

---

## 2. 设计目标

第一阶段系统的目标不是“成为一个全站论坛镜像系统”，而是：

- 对指定 topic / topic 集进行可靠同步；
- 在本地形成可增量更新的数据底座；
- 能快速回答与 topic 相关的查询问题；
- 支持后续做“相关帖子发现”；
- 支持给 LLM 提供结构化文本和图片上下文；
- 保留 Markdown 导出能力，但不让 Markdown 承担主存储职责。

### 2.1 第一阶段必须满足的能力

- 读取 topic 元信息；
- 分页抓取 raw / json；
- 建立 post 级结构化存储；
- 解析并下载图片；
- 支持本地全文检索；
- 支持 `only_op` / 作者 / 日期 / 关键词过滤；
- 支持增量更新；
- 支持将指定 topic 导出成 Markdown。

### 2.2 第一阶段明确不追求的能力

- 全量音视频语义处理；
- 对所有图片统一 OCR；
- 跨全站 embedding 检索；
- 多机并发与服务化部署；
- 自动登录和 Cookie 获取自动化。

---

## 3. 模块拆分

建议未来代码按下面模块拆分。

```text
shuiyuan_exporter/
  core/
    config.py
    models.py
    exceptions.py
  fetch/
    session.py
    topic_fetcher.py
    search_fetcher.py
    sync_planner.py
  normalize/
    topic_normalizer.py
    post_normalizer.py
    media_normalizer.py
  store/
    paths.py
    raw_store.py
    sqlite_store.py
    media_store.py
    fts_store.py
  analysis/
    post_query.py
    topic_summary.py
    related_topics.py
    author_view.py
  render/
    markdown_renderer.py
    json_renderer.py
  cli/
    sync_cli.py
    export_cli.py
    inspect_cli.py
  skill/
    adapter.py
```

### 3.1 `core`

职责：

- 定义统一配置；
- 定义 Topic / Post / Media 等数据模型；
- 定义通用异常。

### 3.2 `fetch`

职责：

- 直接访问 Shuiyuan HTTP 接口；
- 统一请求头和 Cookie 注入；
- 控制分页并发、失败重试、节流；
- 负责原始响应获取，不负责业务分析。

### 3.3 `normalize`

职责：

- 将抓回来的 topic json、page json、raw page 解析为统一对象；
- 提取 post、作者、时间、媒体引用、纯文本；
- 为数据库入库提供结构化记录。

### 3.4 `store`

职责：

- 保存原始响应文件；
- 管理 SQLite；
- 管理全文索引；
- 管理媒体文件与媒体 manifest；
- 记录同步状态。

### 3.5 `analysis`

职责：

- 基于本地缓存完成查询和总结；
- 组织未来 skill 的主要业务逻辑；
- 屏蔽底层抓取和数据库细节。

### 3.6 `render`

职责：

- 把结构化查询结果渲染为 Markdown、JSON、报告文本。

### 3.7 `cli`

职责：

- 提供本地调试和运维入口；
- 支持 `sync`、`export`、`query`、`inspect` 等命令；
- 是未来替代当前 `main.py` 的方向。

### 3.8 `skill`

职责：

- 面向 skill 封装高层接口；
- 输出适合 agent 调用的输入 / 输出协议；
- 可以独立于 CLI 存在。

---

## 4. 数据流设计

完整数据流建议如下：

```text
用户输入 topic / query
  -> 解析目标
  -> 查询本地 sync_state
  -> 判断是否需要联网同步
  -> 抓取层拉取新增数据
  -> 原始响应落盘
  -> 规范化层抽取 Topic/Post/Media
  -> SQLite upsert + FTS 更新
  -> 分析层执行查询 / 总结
  -> 输出层生成 Markdown / JSON / 文本
```

### 4.1 一次全量同步的数据流

1. 获取 `topic.json`；
2. 计算所需 `json pages` 和 `raw pages`；
3. 抓取所有页面；
4. 原始响应落盘；
5. 解析 post、作者、时间、图片引用；
6. 下载图片；
7. 更新 SQLite 与 FTS；
8. 更新 `sync_state`；
9. 可选输出 Markdown 导出。

### 4.2 一次增量同步的数据流

1. 获取最新 `topic.json`；
2. 对比 `posts_count`、`last_posted_at`；
3. 确定新增或可能变化的页面范围；
4. 仅抓取需要补的 raw/json 页面；
5. upsert topic/post/media；
6. 仅下载新增图片；
7. 更新同步状态。

### 4.3 一次本地分析的数据流

1. 用户给出 `topic + filters`；
2. 优先从 SQLite + FTS 检索；
3. 根据需要拼出图片上下文路径；
4. 输出摘要或结构化结果；
5. 默认不联网，除非显式要求刷新。

---

## 5. 文件缓存详细设计

### 5.1 设计原则

原始响应一定要保留，原因有三：

1. 以后规范化逻辑升级时可以重建；
2. 便于排查解析错误；
3. 避免 SQLite 成为唯一事实来源。

### 5.2 原始缓存目录

建议目录：

```text
cache/raw/topics/<topic_id>/
  topic.json
  sync_state.json
  pages/json/0001.json
  pages/json/0002.json
  pages/raw/0001.md
  pages/raw/0002.md
  posts/000001.raw.md
```

### 5.3 文件命名原则

- 页面统一 4 位零填充，如 `0001.json`
- 单帖 raw 用 `post_number` 零填充，如 `000123.raw.md`
- topic 根目录直接使用 `topic_id`
- 不在文件名里混入 title，避免标题变化导致路径漂移

### 5.4 是否需要压缩

第一阶段建议：

- 不主动压缩；
- 保持可读性和调试便利；
- 真正量大时，再评估 gzip / zstd。

---

## 6. SQLite 详细设计

### 6.1 总体设计

SQLite 作为查询与索引核心，文件系统作为原始缓存与媒体仓库。

职责分工：

- 文件缓存：保存原始页面和媒体二进制；
- SQLite：保存结构化实体、关联关系、全文索引、同步状态。

### 6.2 推荐表结构（逻辑级）

#### `topics`

字段建议：

- `topic_id INTEGER PRIMARY KEY`
- `title TEXT NOT NULL`
- `category_id INTEGER`
- `tags_json TEXT`
- `created_at TEXT`
- `last_posted_at TEXT`
- `posts_count INTEGER`
- `reply_count INTEGER`
- `views INTEGER`
- `like_count INTEGER`
- `visible INTEGER`
- `archived INTEGER`
- `closed INTEGER`
- `topic_json_path TEXT`
- `created_ts INTEGER`
- `updated_ts INTEGER`

#### `posts`

字段建议：

- `post_id INTEGER PRIMARY KEY`
- `topic_id INTEGER NOT NULL`
- `post_number INTEGER NOT NULL`
- `username TEXT`
- `display_name TEXT`
- `created_at TEXT`
- `updated_at TEXT`
- `reply_to_post_number INTEGER`
- `is_op INTEGER`
- `like_count INTEGER`
- `raw_markdown TEXT`
- `cooked_html TEXT`
- `plain_text TEXT`
- `raw_page_no INTEGER`
- `json_page_no INTEGER`
- `raw_post_path TEXT`
- `has_images INTEGER`
- `has_attachments INTEGER`
- `has_audio INTEGER`
- `has_video INTEGER`
- `image_count INTEGER`
- `hash_raw TEXT`
- `hash_cooked TEXT`
- `created_ts INTEGER`
- `updated_ts INTEGER`

约束建议：

- `UNIQUE(topic_id, post_number)`

#### `media`

字段建议：

- `media_id INTEGER PRIMARY KEY AUTOINCREMENT`
- `topic_id INTEGER NOT NULL`
- `post_id INTEGER`
- `post_number INTEGER`
- `media_type TEXT NOT NULL`
- `upload_ref TEXT`
- `resolved_url TEXT`
- `local_path TEXT`
- `mime_type TEXT`
- `file_ext TEXT`
- `media_key TEXT`
- `download_status TEXT`
- `content_length INTEGER`
- `created_ts INTEGER`
- `updated_ts INTEGER`

约束建议：

- `UNIQUE(topic_id, post_number, media_type, upload_ref)`

#### `post_quotes`

字段建议：

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `topic_id INTEGER NOT NULL`
- `post_id INTEGER NOT NULL`
- `post_number INTEGER NOT NULL`
- `quoted_topic_id INTEGER`
- `quoted_post_number INTEGER`
- `quote_url TEXT`
- `created_ts INTEGER`

#### `sync_state`

字段建议：

- `topic_id INTEGER PRIMARY KEY`
- `last_known_posts_count INTEGER`
- `last_known_last_posted_at TEXT`
- `last_synced_json_page INTEGER`
- `last_synced_raw_page INTEGER`
- `last_synced_post_number INTEGER`
- `last_sync_status TEXT`
- `last_sync_started_at TEXT`
- `last_sync_finished_at TEXT`
- `last_sync_error TEXT`
- `updated_ts INTEGER`

### 6.3 FTS 设计

建议建一个 `posts_fts` 虚表，用于全文检索。

索引文本建议包含：

- `username`
- `plain_text`
- `raw_markdown`

这样 future queries 会很方便：

- 检索“银行”
- 检索“化工 etf”
- 检索“只看某个作者提到电信的楼层”

---

## 7. 规范化设计

### 7.1 为什么必须有规范化层

raw 页面与 json 页面不是一个视角：

- raw 更适合保留原始 Markdown；
- json 更适合提取作者、时间、cooked HTML、like_count；
- 图片解析通常需要 cooked HTML；
- 引用关系与文字上下文则 often 需要 raw。

因此后续必须统一汇总到一个 `PostRecord` 概念上。

### 7.2 `PostRecord` 逻辑结构

建议逻辑上有这样一个中间对象：

```text
PostRecord
  topic_id
  post_id
  post_number
  username
  display_name
  created_at
  updated_at
  raw_markdown
  cooked_html
  plain_text
  reply_to_post_number
  media_refs[]
  quotes[]
```

### 7.3 规范化来源

字段来源建议：

- `topic json`：topic 元信息、posts_count
- `topic page json`：作者、创建时间、cooked、like_count
- `raw page`：原始 Markdown 大段文本
- `single post raw`：必要时补齐单帖 raw

### 7.4 `plain_text` 的提取原则

建议生成一个适合检索的简化文本视图：

- 去掉 HTML 标签；
- 保留换行与段落边界；
- 不强行保留所有 Markdown 细节；
- 适合全文检索与摘要，而不是适合渲染。

---

## 8. 图片处理详细设计

### 8.1 第一阶段目标

图片处理应当做到：

- 识别 post 中所有图片引用；
- 从 cooked 中找到真实 URL；
- 解析出本地文件名 / key；
- 下载到本地；
- 在数据库记录它属于哪个 post；
- 以后分析时能把图片路径交给 LLM。

### 8.2 为什么不急着 OCR

结合当前目标：

- 你更需要建立“可反复分析”的底座；
- 并不是所有图片都值得 OCR；
- 未来不少问题可以直接把图片发给多模态模型处理。

因此首版只要做到：

- 图片落盘；
- 图片与 post 强关联；
- 支持按 post 抽取图片上下文。

### 8.3 图片下载策略

建议：

- 使用 `media_key` 或 `sha` 做去重；
- 若本地存在且大小正常，则跳过下载；
- 下载失败记录状态，但不阻塞整个 topic 同步。

### 8.4 给 LLM 的图片上下文组织

后续分析接口中，如果某条 post 有图片，可以返回：

- post 文本；
- 图片本地路径列表；
- 图片数量；
- 可选图片说明占位。

这样未来 skill 就能决定：

- 只用文字回答；
- 还是把一两张图一起送给模型。

---

## 9. 增量同步详细设计

### 9.1 同步模式

建议支持三种模式：

- `full`：全量同步 topic
- `incremental`：只同步新增 / 变化部分
- `refresh-tail`：只刷新最后若干页，适合高频活跃帖

### 9.2 同步决策器

建议有一个 `sync_planner` 模块，专门负责根据当前状态决定：

- 是否需要同步；
- 同步哪些 json page；
- 同步哪些 raw page；
- 是否需要补抓单帖 raw；
- 是否需要触发图片下载。

### 9.3 增量策略建议

给定：

- `old_posts_count`
- `new_posts_count`
- `old_last_posted_at`
- `new_last_posted_at`

建议策略：

- 如果完全没变：跳过
- 如果仅少量新增：补抓末尾页
- 如果末尾页变化：回补最后 2~3 页
- 如果异常不一致：触发一次 `refresh-tail` 或小范围重建

### 9.4 为什么要保留 `refresh-tail`

因为一些论坛帖子末页可能发生：

- 编辑；
- 删除；
- 排序细微变化；
- media 映射稍后补齐。

只靠“新增页同步”有时不够稳，因此保留一个末尾回补策略更保险。

---

## 10. 相关帖子发现设计

### 10.1 能力目标

未来相关帖子发现至少包括两种来源：

1. **在线来源**：论坛搜索接口、标签流、最新主题流；
2. **本地来源**：对已缓存 topic 做词法相关搜索与过滤。

### 10.2 在线来源

建议使用：

- `/search/query.json?term=...`
- `/tag/<tag>/l/latest.json`
- `/latest.json`

### 10.3 本地来源

本地相关性第一阶段先不做复杂 embedding，采用规则化方法：

- 标签重合；
- 关键词重合；
- 作者重合；
- 时间窗口接近；
- 标题相似；
- 回复主题相似。

### 10.4 第一阶段输出形式

建议返回：

- topic_id
- title
- 匹配原因
- 最近更新时间
- 标签
- 命中的关键词或来源渠道

---

## 11. Skill 高层接口设计

未来 skill 层建议暴露“面向任务”的接口，而不是低层 HTTP 细节。

### 11.1 `sync_topic`

输入：

- topic url / topic id
- mode=`full|incremental|refresh-tail`
- with_images=`true|false`

输出：

- topic 元信息
- 同步结果摘要
- 新增 posts 数量
- 新增图片数量
- 错误列表

### 11.2 `query_topic_posts`

输入：

- topic id
- keyword
- author
- date_from/date_to
- only_op
- has_images
- limit

输出：

- 命中帖子列表
- 每条帖子的文本摘要
- 图片路径列表

### 11.3 `summarize_topic`

输入：

- topic id
- only_op
- recent_days
- focus_keywords[]

输出：

- topic 摘要
- 高频主题
- 时间线
- 关键楼层列表

### 11.4 `find_related_topics`

输入：

- seed topic id / keyword
- scope=`local|remote|both`
- limit

输出：

- 相关 topic 列表
- 每条关系的命中理由

### 11.5 `export_topic_markdown`

输入：

- topic id
- only_op
- with_images
- time_range

输出：

- 导出文件路径

---

## 12. 第一阶段建议的实现顺序

### Step 1：抽取抓取与存储底座

优先做：

- Session / Cookie / 请求层
- raw / json page 落盘
- SQLite 初始化
- topics / posts / sync_state 表

### Step 2：完成 post 级规范化

优先做：

- page json -> post records
- raw page -> raw markdown merge
- plain_text 生成
- upsert posts

### Step 3：完成图片主链路

优先做：

- media manifest
- 图片 URL 解析
- 图片下载
- 图片与 post 绑定

### Step 4：完成检索与基础分析

优先做：

- FTS5
- only_op
- keyword / author / date 查询
- topic 摘要

### Step 5：完成相关帖子发现

优先做：

- forum search 接入
- tag stream 接入
- 本地相关规则

### Step 6：完成 skill 包装

优先做：

- skill 高层接口
- 错误信息
- 默认输出格式

---

## 13. 工程建议

### 13.1 测试建议

建议从一开始就准备：

- 小 topic 作为回归样本
- 中等 topic 作为媒体样本
- 超长 topic 作为增量同步样本

建议最少有这些测试：

- topic 元信息解析
- page json 解析
- raw page 拼接
- 图片映射正确性
- SQLite upsert 正确性
- 增量同步正确性

### 13.2 配置建议

建议统一配置：

- `cache_root`
- `db_path`
- `cookie_path`
- `max_workers`
- `request_timeout`
- `retry_count`
- `sync_tail_pages`
- `download_images`

### 13.3 可观测性建议

建议加入结构化日志，至少记录：

- 当前 topic
- 当前同步模式
- 当前 page
- 请求失败与重试次数
- 图片下载状态
- SQLite 写入结果

---

## 14. 推荐的第一阶段交付物

如果按这份设计进入实现，建议第一阶段的交付物是：

1. 本地缓存目录结构
2. SQLite 初始 schema
3. `sync_topic` 基础能力
4. post 级结构化缓存
5. 图片下载与 manifest
6. 本地查询接口
7. 基础 Markdown 导出
8. 技术文档与操作说明

---

## 15. 设计总结

这套设计的核心思想可以概括为：

- **原始响应保留**，便于重建；
- **结构化数据库承载分析**，便于查询；
- **图片先保存后理解**，降低复杂度；
- **Markdown 做导出，不做主存储**；
- **同步与分析分层**，服务未来 skill；
- **先把可维护的数据底座搭好，再做高级分析。**

