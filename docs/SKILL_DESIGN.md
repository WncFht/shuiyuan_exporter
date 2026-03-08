# Shuiyuan Skill 设计与落地方案

状态：执行中（截至 2026-03-08）

## 1. 当前决定

当前不再把 `shuiyuan_exporter` 视为“外部运行时仓库 + 单独 skill 适配层”的关系。

改为：

> **当前仓库本身就是 skill repo。**

也就是说：

- 仓库根目录直接提供 `SKILL.md`、`agents/`、`references/`、`scripts/`；
- `shuiyuan_cache/` 继续作为 skill 内部的运行时能力层；
- skill 与实现代码位于同一个 Git 仓库内；
- 后续多机器同步以 Git 为主，chezmoi 只负责少量 bootstrap 或入口配置。

## 2. 为什么这样更合理

相比“仓库一份、`.codex/skills/` 一份、chezmoi 再一份”的三处同步，这个方案更好，因为：

1. 只有一个真实源码位置；
2. skill 说明、脚本、实现代码不会漂移；
3. 更适合直接 clone 到 `~/.codex/skills/` 下使用；
4. 后续做版本管理、review、回滚都更直接。

## 3. 但运行数据不能放进 skill repo

虽然当前仓库会直接成为 skill repo，但运行数据仍然不应存放在仓库内。

建议默认放到仓库外，例如：

```text
~/.local/share/shuiyuan-cache-skill/
  cache/
  exports/
  cookies.txt
```

其中：

- `cache/`：原始抓取、SQLite、auth storage state、图片缓存；
- `exports/`：Markdown 导出结果；
- `cookies.txt`：回退用 cookie 文件。

这样可以避免：

- skill repo 被大体积运行数据污染；
- 多机器同步时把本地认证状态和缓存误同步；
- 在 `~/.codex/skills/` 目录内堆积大量运行文件。

## 4. skill 的默认行为

### 4.1 缓存优先

skill 的默认工作流应该是：

```text
inspect -> ensure_cached -> query/summary -> export(optional)
```

规则：

1. 先检查 topic 是否已有可用缓存；
2. 若已有，优先使用本地缓存；
3. 若没有或用户要求刷新，再联网同步；
4. 查询、摘要、导出都尽量复用本地结果。

### 4.2 结构化优先

skill 的主输出应该是结构化 JSON，而不是 Markdown 文本。

Markdown 导出保留，但只是兼容能力。

### 4.3 认证独立维护

skill 不应在每次执行时都重新处理登录流程。

推荐方式：

- 用 `auth_cli` 单独维护浏览器 profile 与 `auth.json`；
- skill 脚本只消费现成认证状态；
- 无法认证时给出清晰排障提示。

## 5. 当前 MVP 能力边界

### 5.1 本轮先落地

1. `inspect_topic`
2. `ensure_topic_cached`
3. `query_topic_posts`
4. `summarize_topic`
5. `export_topic_markdown`

### 5.2 下一轮再做

1. `find_related_topics`
2. `list_latest_topics`
3. `search_forum_topics`
4. `topic_compare`

### 5.3 暂不做

- OCR 主链路
- 音频/视频深处理
- embedding / vector 检索
- 自动登录学校账号

## 6. 现在的仓库形态

目标形态如下：

```text
shuiyuan-cache-skill/
  SKILL.md
  agents/
    openai.yaml
  references/
  scripts/
  docs/
  shuiyuan_cache/
  pyproject.toml
  README.md
```

各层职责：

- `SKILL.md`：告诉 Codex 何时用、怎么用；
- `agents/openai.yaml`：UI 元数据；
- `references/`：输出 schema、运行时目录、排障说明；
- `scripts/`：低自由度、可直接执行的稳定动作；
- `shuiyuan_cache/`：真正的抓取、同步、查询、摘要、导出能力。

## 7. 现在推荐的 service API

为避免 skill 直接依赖 CLI 打印文本，当前仓库需要补一层稳定 API：

- `shuiyuan_cache.skill_api.inspect_topic()`
- `shuiyuan_cache.skill_api.ensure_topic_cached()`
- `shuiyuan_cache.skill_api.query_topic_posts()`
- `shuiyuan_cache.skill_api.summarize_topic()`
- `shuiyuan_cache.skill_api.export_topic_markdown()`

这层 API 的职责：

- 接收 topic id / URL；
- 使用 skill 专用运行时路径；
- 返回稳定 JSON 结构；
- 内部按需调用已有 service。

## 8. 输出契约原则

### 8.1 `inspect_topic`

应返回：

- topic id / title
- sqlite post 数
- raw/json 页数
- image 数
- 最后同步状态
- `usable_for_analysis`
- `usable_for_export`
- `issues`

### 8.2 `ensure_topic_cached`

应返回：

- `topic_id`
- `cache_hit_before`
- `cache_ready_after`
- `sync_executed`
- `effective_mode`
- `sync_result`
- `inspect_before`
- `inspect_after`

### 8.3 `query_topic_posts`

应返回：

- `topic_id`
- `title`
- `total_hits`
- `posts[]`

每条 post 至少应包含：

- `post_number`
- `username`
- `display_name`
- `created_at`
- `updated_at`
- `plain_text`
- `image_paths`
- `reply_to_post_number`
- `is_op`
- `quote_targets`

### 8.4 `summarize_topic`

应返回：

- `topic_id`
- `title`
- `time_range`
- `post_count_in_scope`
- `top_authors`
- `top_keywords`
- `key_posts`
- `image_post_numbers`
- `summary`

### 8.5 `export_topic_markdown`

应返回：

- `topic_id`
- `filename`
- `topic_dir`
- `save_dir`
- 各阶段耗时
- `ensure_cache`

## 9. 与 chezmoi 的关系

如果后面要用 chezmoi，同步重点不应是“再复制一份 skill 内容”，而是：

- 用 Git 管理整个 skill repo；
- 用 chezmoi 管理少量入口配置、bootstrap 命令或 clone 脚本；
- 不要让 chezmoi 再维护第三份完整 skill 内容。

## 10. 本轮执行目标

本轮我建议直接完成：

1. 把仓库根目录补成真正的 skill 目录结构；
2. 新增 `shuiyuan_cache/skill_api/`；
3. 新增可执行脚本；
4. 让导出链路支持 skill 运行时路径；
5. 跑通至少一组 inspect / ensure / query / summary / export 验证。
