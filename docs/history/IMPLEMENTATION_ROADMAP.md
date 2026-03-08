# Shuiyuan 系统实施路线与 Git 管理约定

版本：`v0.1`  
状态：历史规划稿（已部分实现，当前运行方式请优先参考 `docs/RUNBOOK.md`）  
依赖文档：`docs/history/TECHNICAL_PLAN.md`、`docs/SYSTEM_DESIGN.md`

## 1. 文档目标

本文档回答两个问题：

1. 如果开始实施，推荐按照什么顺序推进；
2. 在推进过程中，Git 如何管理，避免方案漂移和提交混乱。

---

## 2. 总体实施策略

建议采用：

- **小步迭代**
- **每个里程碑独立可验证**
- **先打数据底座，再做分析能力**
- **先稳定本地缓存，再封装 skill**

不建议一开始并行做太多东西，例如：

- 一边重构抓取，一边做搜索，一边做 OCR，一边做 skill。

这样容易把问题耦在一起，难以回退。

---

## 3. 阶段划分

### Phase 0：设计冻结

目标：

- 评审并确认 `docs/history/TECHNICAL_PLAN.md`
- 评审并确认 `docs/SYSTEM_DESIGN.md`
- 决定缓存结构、数据库、图片策略、MVP 范围

交付：

- 文档确认
- 首批实现范围清单

### Phase 1：抓取与持久缓存底座

目标：

- 把当前脚本式抓取拆成可复用抓取层
- 支持原始响应落盘
- 支持 topic 级同步状态记录

关键任务：

- session / request 抽象
- topic.json 获取
- raw/json 分页抓取
- 文件缓存目录初始化
- sync_state 基础能力

完成标准：

- 可以将一个 topic 原始数据完整落盘
- 重复同步不会无限重复抓取

### Phase 2：SQLite 与 post 规范化

目标：

- 将 topic 和 post 转成结构化记录
- 建立最小可查询数据库

关键任务：

- schema 初始化
- topic upsert
- post upsert
- raw_markdown / cooked_html / plain_text 写入
- post_number 与 post_id 对齐

完成标准：

- 能从数据库读出一个 topic 的 post 列表
- 能按作者和时间排序

### Phase 3：图片主链路

目标：

- 解析图片真实 URL
- 下载图片
- 存储 media manifest

关键任务：

- image mapping
- media 表
- 本地路径规范
- 图片下载重试与去重

完成标准：

- 指定 topic 可在本地得到完整图片集合
- 每张图片能定位回所属 post

### Phase 4：查询与分析 MVP

目标：

- 形成“本地优先”的分析能力

关键任务：

- FTS5
- only_op
- keyword / author / date filters
- 基础摘要
- Markdown / JSON 输出

完成标准：

- 能不联网回答常见 topic 查询问题

### Phase 5：相关帖子发现

目标：

- 支持根据 topic / query 找相关 topic

关键任务：

- forum search
- tag/latest 流
- 本地 related rules

完成标准：

- 能返回结构化相关帖子结果

### Phase 6：Skill 封装

目标：

- 将本地缓存分析能力封装成 skill 形式

关键任务：

- 高层接口整理
- skill 文档
- 示例工作流

完成标准：

- 能以 skill 形式完成同步、查询、总结、找相关帖子

---

## 4. 建议的任务拆分粒度

建议每个实现 PR / commit 聚焦一个明确问题，例如：

- 建立 SQLite schema
- 增加 raw page 缓存
- 增加 topic 同步状态
- 增加图片 manifest
- 增加 FTS 查询接口
- 增加 `only_op` 过滤

不建议一个提交同时包含：

- 抓取重构
- Markdown 导出改造
- skill 包装
- OCR 试验

---

## 5. Git 管理建议

你特别提到要“进行 git 的管理”，所以这里单独给出明确建议。

### 5.1 分支策略

建议采用轻量分支模型：

- `main`：始终保持可用
- `feature/cache-foundation`
- `feature/sqlite-schema`
- `feature/image-pipeline`
- `feature/query-mvp`
- `feature/related-topics`
- `feature/skill-adapter`

如果你不想维护过多分支，也可以采用：

- `main`
- 当前工作 `feature/<milestone>`

### 5.2 提交原则

每次提交应当：

- 聚焦一个主题；
- 说明“为什么改”；
- 尽量可回滚；
- 不混入无关格式化或临时文件。

推荐提交信息风格：

```text
Add SQLite schema for cached topic store
Extract raw/json page fetcher and file cache
Add image manifest and local downloader
Implement FTS-based topic post query
Add incremental sync planner for topic updates
```

### 5.3 文档提交原则

设计文档建议与实现同步推进：

- 先提交方案文档；
- 再提交对应实现；
- 实现偏离原方案时，文档要同步更新。

### 5.4 里程碑标签

当每个 phase 稳定时，可以打 tag，例如：

- `design-v1`
- `cache-v1`
- `schema-v1`
- `image-v1`
- `query-v1`
- `skill-v1`

这样以后回看非常方便。

### 5.5 不应提交的内容

应确保以下内容不进入 Git：

- `cookies.txt`
- `.venv/`
- 本地缓存目录
- SQLite 数据库文件
- 大体积媒体文件
- 实验输出、临时日志

### 5.6 实施期间的建议工作流

建议每次开发都遵循：

1. 新建 feature 分支
2. 明确本次目标
3. 实现最小闭环
4. 跑最小验证
5. 更新文档
6. 提交 commit
7. 合并回主线

---

## 6. 建议的目录演进路线

当前仓库已经比这份规划稿更进一步，实际结构更接近：

```text
shuiyuan_exporter/
  docs/
  shuiyuan_cache/
    analysis/
    auth/
    cli/
    core/
    export/
    fetch/
    normalize/
    store/
    sync/
  cache/
  main.py
  README.md
  pyproject.toml
```

说明：

- `shuiyuan_cache/` 已经成为主包；
- `main.py` 只保留为兼容入口；
- `cache/` 属于运行期数据目录，不作为源码结构的一部分；
- 这份文档后续主要保留为“实施思路记录”。

---

## 7. 建议的评审检查清单

在你批准开始实现前，建议确认以下问题：

### 7.1 架构侧

- 是否接受 SQLite 作为第一阶段主数据库？
- 是否接受原始页面与结构化存储并存？
- 是否接受 Markdown 从主结构降级为导出？

### 7.2 范围侧

- 第一阶段是否只做文字 + 图片？
- 是否明确不做 OCR / embedding / 音视频深处理？
- 是否将“相关帖子发现”纳入 MVP？

### 7.3 工程侧

- 缓存目录放在当前仓库内还是单独目录？
- 是否引入 tests 目录？
- 是否接受 feature branch + 小提交策略？

---

## 8. 我建议的下一步

在你批阅完这些文档后，建议正式执行时按下面顺序开始：

1. 确定数据目录和 SQLite 位置
2. 先抽请求与缓存层
3. 再落 schema
4. 再做图片
5. 再做查询
6. 最后封装 skill

一句话说，就是：

> **先把“可持续积累的数据底座”做出来，再做“越来越聪明的分析能力”。**
