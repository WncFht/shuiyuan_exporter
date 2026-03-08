# 导出机器输出与大帖限流改造说明

状态：当前实现说明（截至 2026-03-08）

## 1. 文档目标

这份文档只解释两件最近已经落地的改造：

1. 为什么 `export_topic.py` 现在要求 `stdout` 保持纯 JSON；
2. 为什么大帖同步的 `429 Too Many Requests` 处理现在改成了“全局节流 + 冷却退避 + 顺序补拉”。

这不是历史设计稿，而是当前代码行为说明。

如果你只关心“现在怎么调用脚本”，优先看：

- `docs/RUNBOOK.md`
- `references/output_schema.md`
- `SKILL.md`

如果你想理解这次改造具体改了什么、为什么这么改，请看本文件。

## 2. 改造背景

这次改造针对两个非常具体的问题：

### 2.1 `export_topic.py` 的机器消费不够干净

在改造前：

- `scripts/export_topic.py` 末尾确实会打印 JSON；
- 但底层导出链路里的多个模块仍然直接 `print(...)`；
- 于是同一个 `stdout` 里既有阶段日志，也有最终 JSON。

这对人眼问题不大，但对 skill / agent / shell pipeline 不友好。

典型问题是：

```bash
uv run python scripts/export_topic.py 456491 > result.json
```

如果底层同时把“图片载入中...”之类的文本打到 `stdout`，那么 `result.json` 就不再是可直接解析的 JSON 文件。

### 2.2 大帖同步仍然可能因为 `429` 结束为 `partial`

在改造前：

- 系统已经有基础重试和退避；
- 页面抓取也已经引入线程池；
- 但多个 worker 并发请求时，整体请求节奏仍可能偏快；
- 像 `187803` 这种大帖，在一次长同步里仍可能留下部分 JSON page 未成功抓取。

所以问题不是“完全没有重试”，而是：

- 重试粒度还不够贴近 `429`；
- 多线程情况下缺少跨 worker 的全局节流；
- 对速率限制导致的失败页，缺少一个更保守的顺序补拉阶段。

---

## 3. 改造一：`export_topic.py` 的 `stdout/stderr` 契约

## 3.1 当前目标

当前目标非常明确：

- `stdout` 只保留最终 JSON；
- 进度日志和阶段日志统一写到 `stderr`；
- skill 或外部脚本可以稳定地把 `stdout` 当 JSON 解析；
- 人类用户仍然可以在终端看到过程进度。

## 3.2 当前调用链

当前导出链路大致如下：

```text
scripts/export_topic.py
  -> ShuiyuanSkillAPI.export_topic_markdown(...)
    -> export_topic(...)
      -> export_raw_post(...)
      -> img_replace(...)
      -> match_replace(...)
      -> video_replace(...)
      -> audio_replace(...)
```

这条链现在统一通过 `progress_callback` 传递阶段日志，而不是在底层模块里直接 `print(...)`。

## 3.3 关键实现点

### 顶层脚本

`scripts/export_topic.py` 仍然只做两件事：

1. 构造 `ShuiyuanSkillAPI`；
2. 输出最终 JSON。

真正的变化是：

- 它传入的 `progress_callback` 最终会把日志写到 `stderr`；
- 因此 `stdout` 不再被阶段日志污染。

相关代码入口：

- `scripts/export_topic.py`
- `shuiyuan_cache/skill_api/api.py:247`

### Skill API 层

`ShuiyuanSkillAPI.export_topic_markdown(...)` 现在把 `progress_callback` 继续向下传给 `export_topic(...)`，而不是只在 `ensure_cached(...)` 这一层使用。

相关代码：

- `shuiyuan_cache/skill_api/api.py:247`

### 导出主流程

`export_topic(...)` 现在：

- 接收 `progress_callback`；
- 文字导出、图片替换、附件替换、视频替换、音频替换各阶段都只走 `_emit_progress(...)`；
- 自己不再直接向 `stdout` 打文本。

相关代码：

- `shuiyuan_cache/export/topic_exporter.py:13`

### 各媒体处理器

以下模块之前都存在直接 `print(...)`：

- `shuiyuan_cache/export/image_handler.py:72`
- `shuiyuan_cache/export/attachments_handler.py:49`
- `shuiyuan_cache/export/video_handler.py:51`
- `shuiyuan_cache/export/audio_handler.py:60`

现在它们都改成：

- 接收 `progress_callback`；
- 通过统一回调发出“图片载入中...”“文件替换中...”之类的阶段提示；
- 不再直接写 `stdout`。

## 3.4 当前对调用方的意义

这意味着下面这种调用现在是安全的：

```bash
uv run python scripts/export_topic.py 456491 \
  > /tmp/topic.json \
  2> /tmp/topic.log
```

预期行为：

- `/tmp/topic.json`：纯 JSON；
- `/tmp/topic.log`：阶段日志；
- skill / agent 可以只解析 `stdout`；
- CLI 用户仍然能通过 `stderr` 看到进度。

## 3.5 已验证结果

在 2026-03-08 的实际验证中，以下命令已通过：

```bash
uv run python scripts/export_topic.py 456491 --no-ensure-cached \
  > /tmp/shuiyuan_export_stdout.json \
  2> /tmp/shuiyuan_export_stderr.log
```

验证结果：

- `stdout` 成功被 `json.loads(...)` 解析；
- `stderr` 中存在阶段日志；
- `stdout` 不再夹杂“图片载入中”“Exit.”之类的文本。

---

## 4. 改造二：大帖 `429` 限流处理

## 4.1 当前目标

这里的目标不是“永远不触发 `429`”，而是：

- 降低多线程抓取时整体过快的风险；
- 遇到 `429` 时更尊重服务端节奏；
- 把临时限流和真正失败区分开；
- 尽量把“本来只是被限流”的页面补抓回来，避免最终结果落成 `partial`。

## 4.2 当前策略总览

现在的组合策略是：

1. **全局请求节流**：所有 `ShuiyuanSession` 实例共享节奏控制；
2. **`Retry-After` / 冷却退避**：遇到 `429` 时按响应头或保守默认值等待；
3. **会话层限流重试**：单个请求在 `429` 场景下会进行多次尝试；
4. **同步层顺序补拉**：线程池阶段里如果某些页面因限流失败，会被收集起来，再顺序重试一轮。

这四层叠在一起，才构成当前的完整方案。

## 4.3 会话层：全局请求节流

`ShuiyuanSession` 现在不只是一个简单的 `requests.Session` 包装器，而是增加了跨实例共享的节奏控制。

核心思想是：

- 线程池中的多个 worker 虽然各自有 session；
- 但请求发出前都会经过同一个“下次允许请求时间”的检查；
- 因此不会出现每个 worker 都按自己节奏猛发，最后整体速率远高于预期的情况。

相关代码：

- `shuiyuan_cache/fetch/session.py:19`
- `shuiyuan_cache/fetch/session.py:67`
- `shuiyuan_cache/fetch/session.py:116`
- `shuiyuan_cache/fetch/session.py:127`

## 4.4 会话层：`429` 专项处理

当前 `429` 不是简单地混在普通 HTTP 错误里，而是单独建模处理。

相关代码：

- `shuiyuan_cache/core/exceptions.py:16`
- `shuiyuan_cache/fetch/session.py:135`
- `shuiyuan_cache/fetch/session.py:177`

当前逻辑是：

1. 先判断响应是否为 `429`；
2. 如果有 `Retry-After`，优先解析它；
3. 如果没有，就使用保守默认退避时间；
4. 把这段冷却时间注册到全局节流状态；
5. 继续进行有限次数的重试；
6. 若仍失败，则抛出 `RateLimitError`。

这比“直接把 `429` 当普通失败页记下来”要稳得多。

## 4.5 配置项

当前新增的关键配置项在：

- `shuiyuan_cache/core/config.py:12`

具体包括：

- `request_interval_seconds`：普通请求之间的最小间隔；
- `rate_limit_retry_attempts`：`429` 场景下单请求最多重试次数；
- `rate_limit_cooldown_seconds`：默认冷却时间基线；
- `rate_limit_max_cooldown_seconds`：冷却时间上限。

当前默认值偏保守，原因是当前优先级是：

- 先提高稳定性；
- 再看是否需要进一步调快；
- 而不是一开始把吞吐压到极限。

## 4.6 同步层：失败页顺序补拉

仅靠 session 重试还不够，因为线程池阶段里仍可能有个别页面最终返回 `RateLimitError`。

所以 `TopicSyncService` 现在做了第二层兜底：

- 线程池阶段先并发抓；
- 对真正成功的页面直接进入后续处理；
- 对“因限流失败”的页面先收集起来；
- 在线程池阶段完成后，再用单线程顺序重试这些页面。

相关代码：

- `shuiyuan_cache/sync/topic_sync.py:25`
- `shuiyuan_cache/sync/topic_sync.py:254`
- `shuiyuan_cache/sync/topic_sync.py:303`
- `shuiyuan_cache/sync/topic_sync.py:351`
- `shuiyuan_cache/sync/topic_sync.py:371`

这个设计有两个重要意义：

### 第一，保留线程池带来的正常吞吐

如果完全退回单线程，很多中等大小帖子会明显变慢。

### 第二，对限流页面使用更保守的兜底策略

即使并发阶段偶尔踩到服务端节奏，顺序补拉阶段也会以更低压力把缺页补回来。

所以当前并不是“彻底放弃并发”，而是：

- 正常情况下用并发提速；
- 对限流失败页切换到保守模式兜底。

## 4.7 已验证结果

在 2026-03-08 的实际验证中，以下命令已跑通：

```bash
uv run python scripts/ensure_cached.py 187803 \
  --refresh-mode full \
  --no-images \
  --force
```

实际结果：

- `status = success`
- `fetched_json_pages = 188`
- `fetched_raw_pages = 38`
- `errors = 0`
- `inspect_after.last_sync_status = success`
- `db_post_count = 3742`
- `json_page_count = 188`
- `raw_page_count = 38`

也就是说，这个此前可能留下 `partial` 的大帖，在当前实现下已经能够完整同步成功。

---

## 5. 这次改造后，系统行为上有什么变化

## 5.1 对 skill / agent

最重要的变化是：

- 更容易把脚本接入自动化；
- 更容易把 `stdout` 直接作为 JSON 解析；
- 不必再在调用侧写“去除日志行”的脏逻辑。

## 5.2 对 CLI 用户

最重要的变化是：

- 终端里仍然能看到进度；
- 但日志默认走 `stderr`；
- 如果你把 `stdout` 重定向到文件，结果会更干净。

## 5.3 对大帖同步

最重要的变化是：

- 大帖仍然可能比小帖慢；
- 这是当前有意接受的代价；
- 因为当前优先目标是稳定拿全，而不是冒险追求极限速度。

---

## 6. 当前边界与注意事项

### 6.1 这不代表所有 `partial` 都会消失

当前改造主要提升的是 `429` 场景。

如果以后出现：

- 认证失效；
- 网络断连；
- 上游接口结构变化；
- 某些页面内容本身异常；

那么同步仍然可能出现 `partial`，只是错误原因会不同。

### 6.2 这不代表 raw 页面里的 `upload://...` 会被改写

`cache/raw/topics/<topic_id>/pages/raw/*.md` 保存的是论坛 raw markdown 原文。

因此其中出现：

```markdown
![xxx](upload://abc.jpeg)
```

在缓存层本来就是正常现象。

真正的图片路径改写发生在“导出 Markdown 产物”阶段，而不是 raw cache 存储阶段。

### 6.3 这也不意味着线程池可以无限开大

当前线程池依然是保守配置。

原因是：

- session 层虽然有节流；
- 但 worker 数过高仍会增加调度复杂度和瞬时压力；
- 当前更适合先保持低并发、稳定抓全。

---

## 7. 相关文件

### 机器输出改造

- `shuiyuan_cache/export/topic_exporter.py:13`
- `shuiyuan_cache/skill_api/api.py:247`
- `shuiyuan_cache/export/image_handler.py:72`
- `shuiyuan_cache/export/attachments_handler.py:49`
- `shuiyuan_cache/export/video_handler.py:51`
- `shuiyuan_cache/export/audio_handler.py:60`

### 限流与同步改造

- `shuiyuan_cache/fetch/session.py:19`
- `shuiyuan_cache/core/config.py:12`
- `shuiyuan_cache/core/exceptions.py:16`
- `shuiyuan_cache/sync/topic_sync.py:25`
- `shuiyuan_cache/sync/topic_sync.py:254`

---

## 8. 建议阅读顺序

如果你想继续理解当前实现，推荐顺序是：

1. `references/output_schema.md`
2. `docs/EXPORT_IO_AND_RATE_LIMITING.md`
3. `docs/THREAD_POOL_REFACTOR_PLAN.md`
4. `docs/RUNBOOK.md`
5. `shuiyuan_cache/fetch/session.py`
6. `shuiyuan_cache/sync/topic_sync.py`
