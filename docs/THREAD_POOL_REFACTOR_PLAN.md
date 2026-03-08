# 并发改造方案（已执行第一阶段）

## 1. 背景

当前 `shuiyuan_cache` 的主链路已经完成了：

- 认证状态管理
- topic 同步到本地缓存
- SQLite 分析查询
- Markdown 导出
- Skill 运行时封装

但在大帖场景下，性能瓶颈比较明显。根本原因不是 CPU，而是：

- 大量 JSON / raw 页面请求
- 大量图片下载
- 部分导出阶段的按需补抓
- 串行等待网络往返

旧兼容导出代码中已经有线程池分页抓取思路，因此“现在没有并发”并不是因为 Skill 机制限制，而是新链路在实现时优先选择了更简单、稳定、可调试的串行方案。

## 2. 当前 pipeline

### 2.1 同步链路

入口：

- `scripts/ensure_cached.py`
- `ShuiyuanSkillAPI.ensure_topic_cached(...)`
- `TopicSyncService.sync_topic(...)`

主流程：

1. 解析 topic id
2. 获取 topic meta
3. 落盘 `topic.json`
4. 写入 topics 表
5. 根据 `sync_state` 规划需要抓取的 JSON / raw 页
6. 逐页获取 JSON
7. 解析 posts / media
8. 写入 SQLite `posts`
9. 下载图片
10. 写入 SQLite `media`
11. 逐页获取 raw markdown
12. 落盘 raw page
13. 更新 `sync_state.json` 和 SQLite `sync_state`

### 2.2 导出链路

入口：

- `scripts/export_topic.py`
- `export_topic(...)`

主流程：

1. 读取 topic 元数据
2. 拼接整帖 Markdown
3. 解析 JSON 中的图片信息
4. 将图片复制或下载到导出目录
5. 附件 / 视频 / 音频链接重写
6. 对引用楼层按需抓取单帖 raw

## 3. 为什么不能直接把旧线程池照搬过来

旧版线程池能直接工作，是因为它主要做的是“按页抓取”，任务之间几乎没有共享状态。

而新链路里有几个关键共享状态：

- 单条 SQLite 连接
- 共享 `requests.Session`
- 共享图片缓存路径
- 共享同步状态 `sync_state`

因此不能直接做成“每个线程抓一页、解析一页、落库一页”。

如果那样做，会遇到：

- SQLite 线程安全问题
- 同步状态竞争
- 多线程写同一图片文件的竞争
- 出错后难以判断哪一页已经真正提交

## 4. 改造原则

本次改造遵循两个原则：

1. **并发只进入 I/O 密集区**：网络请求、图片下载、导出图片复制/下载
2. **写路径保持单线程**：SQLite、`sync_state`、topic 级状态更新仍由主线程顺序执行

也就是：

- 并发 fetch
- 顺序 commit

## 5. 第一阶段执行内容

本次已经落地以下改造。

### 5.1 同步页抓取并发化

文件：

- `shuiyuan_cache/sync/topic_sync.py`
- `shuiyuan_cache/core/config.py`

策略：

- JSON page 抓取改为线程池并发获取
- raw page 抓取改为线程池并发获取
- 结果仍按页号顺序返回给主线程处理
- 主线程继续负责：
  - 落盘 JSON / raw
  - 解析 posts / media
  - 写 SQLite
  - 更新 sync_state

默认配置：

- `page_fetch_workers = 2`

这意味着：

- 抓取速度提升
- SQLite 仍保持单写者模型
- 进度输出仍然稳定可读

### 5.2 同步图片下载并发化

文件：

- `shuiyuan_cache/store/media_store.py`
- `shuiyuan_cache/core/config.py`

策略：

- 图片下载任务按 `(media_key, ext, resolved_url)` 去重
- 使用线程池并发下载唯一图片任务
- 每个工作线程使用自己的 `ShuiyuanSession`
- 下载完成后仍由主线程统一写入 media 记录

默认配置：

- `image_download_workers = 4`

这样做的好处：

- 避免单页几十张图时逐张等待
- 避免把 SQLite 放进多线程
- 同一页里的重复图片不会并发重复下载
- 默认并发更保守，减少触发论坛 429 限流的概率

### 5.3 导出图片并发化

文件：

- `shuiyuan_cache/export/cache_bridge.py`
- `shuiyuan_cache/export/image_handler.py`
- `shuiyuan_cache/core/config.py`

策略：

- 导出阶段先顺序扫描 JSON，收集图片任务
- 对唯一图片任务进行线程池并发落地
- 优先复用本地 `cache/media/images/`
- 缺失时再联网下载

默认配置：

- `export_image_workers = 4`

### 5.4 单帖 raw 引用缓存从 `raw/topics/` 迁出

文件：

- `shuiyuan_cache/store/paths.py`
- `shuiyuan_cache/export/cache_bridge.py`
- `shuiyuan_cache/store/raw_store.py`（路径透传）

改造前：

- 导出时如果遇到跨帖引用、附件、视频、音频等，需要按需抓某一楼的 raw
- 这些单帖 raw 被写进 `cache/raw/topics/<topic_id>/posts/`
- 结果是 `raw/topics/` 里会出现很多“只有 posts，没有 topic.json / pages / sync_state”的半成品目录

改造后：

- 单帖按需 raw 缓存统一落到：

```text
cache/raw/post_refs/<topic_id>/<post_number>.raw.md
```

这样目录语义更清楚：

- `raw/topics/`：真正的 topic 同步产物
- `raw/post_refs/`：导出 / 引用解析时产生的按需单帖缓存


## 5.5 限流与退避

文件：

- `shuiyuan_cache/fetch/session.py`

本次同时补上了对 `429 Too Many Requests` 的自动重试与退避：

- 对 `429 / 500 / 502 / 503 / 504` 启用状态码重试
- 尊重服务端返回的 `Retry-After`
- 默认 worker 数保持保守值，优先稳定性

## 6. 本次明确不做的事情

为了控制风险，这一轮没有做：

- 多线程直接写 SQLite
- 多线程更新 `sync_state`
- 全面改成 asyncio
- 导出附件 / 视频 / 音频的全面并发化
- 对所有 CLI 暴露 workers 参数

原因：

- 当前最主要瓶颈是网络 I/O
- 先做最安全、收益最高的改造
- 先确保缓存一致性和可调试性不退化

## 7. 后续可继续做的第二阶段

如果后面需要继续提速，建议顺序如下：

1. 给 CLI 暴露 `--page-workers` / `--image-workers`
2. 给导出中的附件 / 视频 / 音频重写加并发
3. 优化 SQLite 写入批量化
4. 在导出阶段增加更细的并发进度
5. 评估是否需要生产者-消费者队列模型

## 8. 验证方法

建议至少验证：

```bash
uv run python -m compileall shuiyuan_cache scripts
uv run pre-commit run --all-files
uv run python scripts/ensure_cached.py https://shuiyuan.sjtu.edu.cn/t/topic/456491 --refresh-mode refresh-tail
uv run python scripts/export_topic.py https://shuiyuan.sjtu.edu.cn/t/topic/456491
```

对于大帖：

```bash
uv run python scripts/ensure_cached.py https://shuiyuan.sjtu.edu.cn/t/topic/187803 --refresh-mode refresh-tail --no-images
```

重点观察：

- 进度是否持续输出
- 是否仍然能稳定落盘
- SQLite 查询是否正常
- `raw/topics/` 是否不再出现新的“只有 posts 的 topic 目录”
- `raw/post_refs/` 是否开始承接引用楼层的单帖 raw 缓存

## 9. 结论

这次改造不是把整个系统“强行并发化”，而是把最适合线程池的区域抽出来：

- 页抓取
- 图片下载
- 导出图片落地

同时继续保持：

- 单线程写 SQLite
- 单线程更新 sync_state
- topic 级缓存结构清晰

这是对当前项目最稳妥的一次第一阶段提速。
