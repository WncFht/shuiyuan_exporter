# Discourse 搜索 API 研究（含 Shuiyuan 实测）

本文目的是回答三个问题：

1. **Discourse 官方到底有哪些搜索相关接口？**
2. **Shuiyuan 当前站点实际上开放并使用了哪些接口 / 参数？**
3. **这些能力能否支撑我们后续做“作者追踪 / 相关楼发现 / 多跳搜索”？**

本文基于两类来源：

- **官方来源**：Discourse 开源仓库源码、官方 `discourse_api` gem；
- **Shuiyuan 实测**：在 `2026-03-09`（Asia/Shanghai）对 `https://shuiyuan.sjtu.edu.cn` 在线请求验证；
- **Shuiyuan 站内参考帖**：`277768`、`315062`。

---

## 1. 结论先行

### 1.1 Discourse 搜索至少有两条主链路

Discourse 的搜索，不是单一接口，而是两条主要链路：

1. **Header / 联想式搜索**
   - 路由：`GET /search/query`
   - 常见请求：`/search/query.json?term=...`
   - 典型用途：顶部搜索框、快速返回少量 topic / post / user / tag / category 分组结果。

2. **Full-page / 全页搜索**
   - 路由：`GET /search`
   - 常见请求：`/search?q=...` 或 `/search.json?q=...`
   - 典型用途：完整搜索页，支持更完整的高级过滤语法、更多结果、分页和排序。

此外还有一个点击日志接口：

3. **搜索点击回传**
   - 路由：`POST /search/click`
   - 用途：上报用户点了哪个搜索结果，更新 `search_log`。

### 1.2 现在我们 skill 实现的是哪一种

当前仓库新增的在线搜索入口 `scripts/search_forum.py` 只调用了：

- `GET /search/query.json?term=...`

也就是说，它是：

- **一跳搜索**
- **偏 header / 联想式搜索**
- 返回的是少量候选 topic / post，适合“先发现，再缓存，再深挖”

它 **不是**：

- 全页搜索爬全量结果；
- 自动作者追踪；
- 自动多跳相关楼发现；
- 自动主题图谱。

### 1.3 多跳搜索有没有现成官方 API

**没有一个“现成的一键多跳 API”。**

但 Discourse 官方搜索链路已经提供了构建多跳搜索的关键积木：

- `search_context[type]=user|topic|category|tag|private_messages`
- full-page 搜索语法，例如：
  - `user:xxx`
  - `category:xxx`
  - `tag:xxx`
  - `before:...`
  - `after:...`
  - `status:...`
  - `in:title`
  - `with:images`
  - `order:latest|oldest|views|likes|read|latest_topic|oldest_topic`

所以“多跳搜索”应该是我们在 skill 里自行编排的 pipeline，而不是期待 Discourse 服务器直接替我们做。

---

## 2. 官方 Discourse 搜索接口

### 2.1 `GET /search/query(.json)`：header / 快速搜索

官方路由中明确存在：

- `get "search/query" => "search#query"`

`SearchController#query` 的核心行为：

- 必须传 `term`
- 可传 `type_filter`
- 可传 `search_for_id`
- 可传 `search_context`
- 可传 `restrict_to_archetype`
- 内部执行 `search_type = :header`
- 返回 `GroupedSearchResultSerializer`

也就是说：

- 这个接口是 **快速搜索**，不是完整搜索页；
- 目标是给 UI 一个“少量分组结果”列表；
- 更适合我们做“发现候选楼”。

### 2.2 `GET /search(.json)`：full-page / 完整搜索

官方路由中明确存在：

- `get "search" => "search#show"`

`SearchController#show` 的核心行为：

- 主要参数是 `q`
- 可带 `page`
- 默认 `type_filter: "topic"`
- 内部执行 `search_type = :full_page`
- 返回 `GroupedSearchResultSerializer`
- 适合完整搜索页与 JSON 结果导出

相比 `query`：

- `show` 更像完整搜索页后端；
- `query` 更像 header / autocomplete 后端；
- `show.json` 一般能拿到更多结果。

### 2.3 `POST /search/click`

官方路由中还存在：

- `post "search/click" => "search#click"`

其用途是记录：

- `search_log_id`
- `search_result_type`
- `search_result_id`

这不是搜索数据接口，但如果以后要完整模拟前端行为、分析搜索点击质量，可能会有用。

---

## 3. 官方支持的核心参数

### 3.1 `term` 与 `q`

- `term`：用于 `/search/query(.json)`
- `q`：用于 `/search(.json)`

两者都进入 `Search.new(...)`，但：

- `term` 更偏 header 搜索；
- `q` 更偏 full-page 搜索。

### 3.2 `search_context`

`SearchController.valid_context_types` 明确允许：

- `user`
- `topic`
- `category`
- `private_messages`
- `tag`

`lookup_search_context` 支持两种传参形式：

1. 嵌套对象：
   - `search_context[type]=user`
   - `search_context[id]=pangbo`

2. 简写形式：
   - `context=user`
   - `context_id=pangbo`

在 controller 内会转换成上下文对象：

- `user` / `private_messages`：按用户名找用户
- `category`：按 category id
- `topic`：按 topic id
- `tag`：按 tag 名

这点非常关键，因为它意味着：

- **作者追踪** 可以不靠全站镜像，先靠 `search_context[user]` 做作者范围检索；
- **单楼深挖** 可以用 `search_context[topic]`；
- **分类 / tag 拓展** 也有天然入口。

### 3.3 `type_filter`

官方 `query` 支持传入 `type_filter`。

不过要注意：

- controller 的支持不等于站点前端一定完整暴露；
- 在 Shuiyuan 实测里，`/search/query.json?term=炒股&type_filter=topic` 返回的 JSON 里依然同时有 `topics` 和 `posts`，说明当前站点上它未必按我们直觉“只留 topic”。

因此：

- **可以记录这个参数存在**；
- 但在 skill 里不要假定它在 Shuiyuan 上一定强约束返回类型。

### 3.4 `search_for_id`

源码支持 `search_for_id=true`，但本文未作为主链路展开。

现阶段对我们更重要的是：

- `search_context`
- full-page 语法
- 结果聚合与多跳策略

### 3.5 `restrict_to_archetype`

`query` 里还支持 `restrict_to_archetype`。

这更偏 Discourse 内部 archetype 范围控制。对 Shuiyuan 一般搜索能力增强不是第一优先级，暂不作为核心设计入口。

---

## 4. 官方高级搜索语法（来自 `lib/search.rb`）

Discourse 的高级搜索语法不是散落在文档里，而是大量写死在 `Search.advanced_filter(...)` 中。

下面列的是**与我们 skill 最相关**的一组。

### 4.1 作者 / 人物相关

- `user:username`
- `@username`
- `created:@username`

用途：

- 搜某个作者发过的内容；
- 搜由谁创建；
- 做“搜到某人后继续追踪他的历史发言”。

### 4.2 topic / 标题 / 回复位置相关

- `in:title` 或简写 `t`
- `in:first`
- `in:replies`
- `in:pinned`
- `in:wiki`

用途：

- 只搜标题；
- 只搜首楼；
- 只搜回复；
- 筛置顶 / wiki 贴。

### 4.3 分类 / 标签 / 组

- `category:...`
- `categories:...`
- `tag:...`
- `tags:...`
- `-tag:...`
- `-tags:...`
- `#tagname`
- `group:...`
- `group_messages:...`

用途：

- 分板块追踪；
- 按标签扩散；
- 做 related-topic discovery。

### 4.4 时间范围

- `before:...`
- `after:...`

用途：

- 看某人某个阶段说过什么；
- 做事件前后演化分析；
- 做增量追踪。

### 4.5 状态 / 结构过滤

- `status:open`
- `status:closed`
- `status:public`
- `status:archived`
- `status:noreplies`
- `status:single_user`

用途：

- 筛开放/封存贴；
- 找无人回复贴；
- 找单人串。

### 4.6 数量 / 热度过滤

- `posts_count:n`
- `min_post_count:n`
- `min_posts:n`
- `max_posts:n`
- `min_views:n`
- `max_views:n`
- `likes:` 不是通用数值过滤，而更多体现在 `in:likes`

用途：

- 找大楼；
- 找冷门楼；
- 按浏览门槛过滤。

### 4.7 用户自己的阅读/交互上下文

- `in:likes`
- `in:bookmarks`
- `in:posted`
- `in:created`
- `in:mine`
- `in:watching`
- `in:tracking`
- `in:seen`
- `in:unseen`
- `in:personal`
- `in:messages`
- `in:personal-direct`
- `in:all-pms`

这类过滤很多需要登录用户上下文，适合以后做“我参与过什么”“我看过什么”的个性化检索，但不是当前 skill 的第一阶段重点。

### 4.8 内容类型 / 媒体 / 语言

- `with:images`
- `filetypes:...`
- `locale:...`

用途：

- 找截图帖；
- 找附件类内容；
- 结合多模态分析。

### 4.9 排序语法

源码中 `@order` 直接支持：

- `order:latest`
- `order:oldest`
- `order:latest_topic`
- `order:oldest_topic`
- `order:views`
- `order:likes`
- `order:read`

这部分在 full-page 搜索里更有意义。

---

## 5. Shuiyuan 实测结果

下面是 `2026-03-09` 对 Shuiyuan 实站做的在线测试结论。

### 5.1 `/search/query.json?term=炒股` 可用

实测：

- 已登录时可正常返回 JSON；
- 顶层键包括：
  - `categories`
  - `grouped_search_result`
  - `groups`
  - `posts`
  - `tags`
  - `topics`
  - `users`

也就是说，Shuiyuan 当前返回不是只有单一结果集，而是一个**分组结果对象 + 顶层便捷取数数组**。

### 5.2 `search_context[type]=user&id=username` 在 Shuiyuan 上可用

实测请求：

- `/search/query.json?term=搜索&search_context[type]=user&search_context[id]=pangbo`

返回结果中，前几个命中帖的 `username` 都是 `pangbo`。

这说明：

- 我们可以直接把“作者范围搜索”做成在线能力；
- 不必一开始就靠站外爬用户主页或全站镜像。

### 5.3 `context=user&context_id=pangbo` 简写在 Shuiyuan 上也可用

也就是说，官方 controller 的简写兼容逻辑在 Shuiyuan 当前版本上也在工作。

### 5.4 `search_context[type]=topic&id=277768` 在 Shuiyuan 上可用

实测请求：

- `/search/query.json?term=搜索&search_context[type]=topic&search_context[id]=277768`

返回结果被限制在 topic `277768` 内。

这意味着：

- 在线单楼检索也是官方支持路径；
- 以后不一定非要先缓存 topic 才能做一次轻量楼内搜索。

### 5.5 `/search.json?q=炒股` 可用，而且结果比 header 搜索多

实测：

- `/search.json?q=炒股` 返回的 `topics` 和 `posts` 数量都明显多于 `query.json`
- 当前 Shuiyuan 测到 `posts=50`、`topics=50`

这说明：

- 如果要做“尽量找全”的搜索，应该优先考虑 full-page 搜索；
- `query.json` 更适合作为快速候选发现。

### 5.6 Full-page 语法 `user:pangbo` 在 Shuiyuan 上可用

实测请求：

- `/search.json?q=搜索 user:pangbo`

结果中可稳定命中 `pangbo` 在不同 topic 的帖子。

这说明：

- **基于 full-page 搜索 + 高级语法**，我们已经能做相当一部分“作者追踪”；
- 多跳搜索的第一跳和第二跳，其实已经有了坚实基础。

### 5.7 `type_filter=topic` 在 Shuiyuan 上需要谨慎使用

虽然官方 controller 支持，但当前 Shuiyuan 实测里：

- `/search/query.json?term=炒股&type_filter=topic`
- 返回的 JSON 依然同时带有 `topics` 和 `posts`

因此当前建议是：

- **把它当作 hint，而不是强约束**；
- 在 skill 里最好自己做二次筛选，而不是完全信任站点返回形态。

---

## 6. 参考主题解读

## 6.1 `277768`《欢迎体验“热议话题”及高级搜索功能》

在线与缓存内容都表明，这个帖最关键的信息有三条：

1. Shuiyuan 在标准 Discourse 搜索之外，至少做了若干**站点级搜索产品增强**：
   - `/hot`
   - `/image-search`
   - 搜索页中的 AI 语义搜索入口
2. 站点维护者给了实际使用建议：
   - **AI 语义搜索** 更适合自然语言句子描述；
   - **关键词搜索** 更适合简短关键词，最好用空格分隔；
   - 缩写 / 人名搜不到时，可以尝试拆字。
3. 这说明 Shuiyuan 搜索体验并不只依赖 Discourse 核心搜索；它还叠加了**图片搜索**和**AI 语义层**。

对 skill 的启发：

- 我们文档里必须区分：
  - **Discourse 核心搜索 API**
  - **Shuiyuan 自定义搜索功能**
- `scripts/search_forum.py` 目前只覆盖了前者。

## 6.2 `315062`《玩源这有！关于Discourse URL的有趣小知识（欢迎补充）》

这个帖虽然不是“搜索 API 说明帖”，但它对我们很重要，因为它总结了 Discourse 常用直接访问技巧：

- `.../raw/<topic_id>/<post_number>` 或相关 raw 访问思路
- `topic_url.json`
- `post_url.json`
- `u/<username>.json`
- `uploads/short-url/...`
- 以及 `lookup-urls` 的坑和短链不总是可直接还原的问题

对 skill 的启发：

- 这个帖说明 Shuiyuan 资深用户已经在实际使用：
  - `topic.json`
  - `post.json`
  - `user.json`
  - 短链解析
- 也说明“站内研究”与官方 Discourse 能力是一致的，文档可以以此为辅助佐证。

---

## 7. 对 skill 设计的直接含义

### 7.1 当前 `search_forum.py` 的定位

当前脚本应被明确理解为：

- **在线一跳候选发现器**
- 调的是 `/search/query.json?term=...`
- 适合先找候选楼，再决定要不要缓存

它不应该被误解为：

- 全站全量搜索器
- 作者图谱构建器
- 自动多跳发现器

### 7.2 如果要做“作者多跳搜索”，推荐的第一版路线

建议做成一个 pipeline：

1. **Hop 1：入口词在线搜索**
   - `query.json?term=...`
   - 或直接 `search.json?q=...`
2. **Hop 2：作者范围搜索**
   - `search.json?q=<query> user:<username>`
   - 或 `query.json?term=<query>&search_context[type]=user&search_context[id]=<username>`
3. **Hop 3：topic 范围搜索**
   - 对命中的 topic 再做 `search_context[type]=topic`
4. **Hop 4：缓存与结构化分析**
   - 对高价值 topic 执行 `ensure_cached`
   - 再做 `query_topic.py --author ... --keyword ...`
5. **Hop 5：相关楼扩展**
   - 从命中的 topic 标题、tag、作者、时间窗口再生成新查询

### 7.3 官方能力能支持到什么程度

官方 Discourse 搜索已足以支持：

- 关键词发现
- 作者范围搜索
- 单楼范围搜索
- 分类 / 标签范围搜索
- 时间窗口过滤
- 标题/首楼/回复过滤
- 部分媒体过滤

官方 Discourse 搜索**不直接提供**：

- 一键作者全站发言时间线 API（搜索层面）
- 一键 related-topics graph
- 一键多跳检索
- 自动主题聚类

这些都需要我们在 skill 端组合实现。

---

## 8. 对仓库的建议

### 8.1 短期建议

优先补三个能力：

1. **full-page search CLI / script**
   - 直接封装 `/search.json?q=...`
   - 支持传完整 query string，如 `user:pangbo 搜索 order:latest`
2. **author trace CLI / script**
   - 输入用户名
   - 先在线搜作者相关帖子
   - 再自动缓存前 N 个 topic
   - 再输出该作者在这些 topic 中的历史发言
3. **related-topic discover CLI / script**
   - 输入 query 或 topic
   - 基于作者、tag、关键词、时间窗口扩展候选楼

### 8.2 文档建议

以后在 skill 文档里，建议明确分成三层：

1. **Discourse 官方核心搜索**
2. **Shuiyuan 自定义搜索能力**（如 `/image-search`、AI 搜索）
3. **我们 skill 的编排层能力**（一跳 / 多跳 / 缓存 / 摘要）

否则很容易再次出现“以为 skill 已经会自动多跳，但其实只是调用了 `query.json`”的误解。

---

## 9. 本文涉及的关键请求示例

### 9.1 Header 搜索

```bash
curl -H "Cookie: <cookie_header>" \
  --get 'https://shuiyuan.sjtu.edu.cn/search/query.json' \
  --data-urlencode 'term=炒股'
```

### 9.2 按作者范围做 header 搜索

```bash
curl -H "Cookie: <cookie_header>" \
  --get 'https://shuiyuan.sjtu.edu.cn/search/query.json' \
  --data-urlencode 'term=搜索' \
  --data-urlencode 'search_context[type]=user' \
  --data-urlencode 'search_context[id]=pangbo'
```

或简写：

```bash
curl -H "Cookie: <cookie_header>" \
  --get 'https://shuiyuan.sjtu.edu.cn/search/query.json' \
  --data-urlencode 'term=搜索' \
  --data-urlencode 'context=user' \
  --data-urlencode 'context_id=pangbo'
```

### 9.3 按 topic 范围做 header 搜索

```bash
curl -H "Cookie: <cookie_header>" \
  --get 'https://shuiyuan.sjtu.edu.cn/search/query.json' \
  --data-urlencode 'term=搜索' \
  --data-urlencode 'search_context[type]=topic' \
  --data-urlencode 'search_context[id]=277768'
```

### 9.4 Full-page 搜索

```bash
curl -H "Cookie: <cookie_header>" \
  --get 'https://shuiyuan.sjtu.edu.cn/search.json' \
  --data-urlencode 'q=搜索 user:pangbo order:latest'
```

---

## 10. 参考来源

### 10.1 官方源码 / 官方客户端

- Discourse `SearchController`
  - https://github.com/discourse/discourse/blob/main/app/controllers/search_controller.rb
- Discourse `Search` 实现
  - https://github.com/discourse/discourse/blob/main/lib/search.rb
- Discourse 路由
  - https://github.com/discourse/discourse/blob/main/config/routes.rb
- 官方 `discourse_api` gem 的搜索调用
  - https://github.com/discourse/discourse_api/blob/main/lib/discourse_api/api/search.rb
- `GroupedSearchResultSerializer`
  - https://github.com/discourse/discourse/blob/main/app/serializers/grouped_search_result_serializer.rb
- `SearchPostSerializer`
  - https://github.com/discourse/discourse/blob/main/app/serializers/search_post_serializer.rb
- `SearchTopicListItemSerializer`
  - https://github.com/discourse/discourse/blob/main/app/serializers/search_topic_list_item_serializer.rb

### 10.2 Shuiyuan 参考帖

- `277768`《欢迎体验“热议话题”及高级搜索功能》
  - https://shuiyuan.sjtu.edu.cn/t/topic/277768
- `315062`《玩源这有！关于Discourse URL的有趣小知识（欢迎补充）》
  - https://shuiyuan.sjtu.edu.cn/t/topic/315062

