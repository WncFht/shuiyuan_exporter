# 仓库重构计划与当前状态

状态：持续更新（截至 2026-03-08）

## 1. 重构目标

把仓库收敛为：

- `shuiyuan_cache/` 作为唯一主包；
- 根目录只保留少量入口、配置和说明文档；
- 认证、同步、分析、导出、后续 skill 都围绕同一套包内能力构建。

## 2. 当前已经完成的事情

### 2.1 包结构收口

已经完成：

1. 旧导出链路迁入 `shuiyuan_cache/export/`
2. 新增统一 CLI 入口：`shuiyuan_cache/cli/export_cli.py`
3. 根目录仅保留 `main.py` 作为兼容入口
4. 根目录历史脚本文件已基本清理完毕

已经删除的根目录旧文件包括：

- `utils.py`
- `constant.py`
- `image_handler.py`
- `attachments_handler.py`
- `audio_handler.py`
- `video_handler.py`
- `quality_list.py`

### 2.2 认证统一

当前认证优先级已经统一为：

1. `cache/auth/auth.json`
2. `cookies.txt`

也就是说，当前推荐的长期方案已经不是“手工维护 Cookie”，而是“独立浏览器 profile + `auth.json`”。

### 2.3 Phase 1 / Phase 2 主链路已经可用

当前仓库已经具备：

- `auth_cli`
- `sync_cli`
- `query_cli`
- `summary_cli`
- `export_cli`

因此仓库已经不再是“单纯导出脚本”，而是一个最小可用的本地缓存与分析系统。

### 2.4 导出链路已经改成缓存优先

最新状态：

- 原始 Markdown 导出优先读取 `cache/raw/topics/<topic_id>/`
- 楼层引用优先读取 `raw/post_refs/<topic_id>/*.raw.md`
- 图片优先复用 `cache/media/images/`
- 仅在缓存缺失时回退到网络请求

这一步很关键，因为它意味着：

- 抓取与导出已经基本解耦；
- 后续 skill 可以优先消费缓存；
- 批量分析的成本会明显降低。

## 3. 当前推荐用法

### 3.1 推荐命令

- 认证管理：`uv run python -m shuiyuan_cache.cli.auth_cli ...`
- 同步缓存：`uv run python -m shuiyuan_cache.cli.sync_cli ...`
- 查询缓存：`uv run python -m shuiyuan_cache.cli.query_cli ...`
- 摘要分析：`uv run python -m shuiyuan_cache.cli.summary_cli ...`
- 导出 Markdown：`uv run python -m shuiyuan_cache.cli.export_cli ...`

`main.py` 仍然保留，但仅作为兼容入口。

### 3.2 推荐工作流

推荐把日常使用方式固定为：

```text
auth -> sync -> query/summary -> export
```

也就是：

- 先建立长期可复用认证；
- 再把 topic 拉到本地；
- 查询和总结尽量本地做；
- 最后按需导出 Markdown。

## 4. 文档整理建议

当前 `docs/` 中同时存在两类文档：

### 4.1 应继续保留的“当前文档”

- `docs/RUNBOOK.md`
- `docs/SKILL_DESIGN.md`
- `docs/THREAD_POOL_REFACTOR_PLAN.md`
- `docs/REPO_REFACTOR_PLAN.md`

### 4.2 应保留但需要按“历史规划稿”理解的文档

- `docs/history/IMPLEMENTATION_ROADMAP.md`
- `docs/SCHEMA_AND_API.md`
- `docs/history/PHASE1_EXECUTION_SPEC.md`
- `docs/history/PHASE2_EXECUTION_SPEC.md`
- `docs/history/PHASE2_QUERY_ANALYSIS_DESIGN.md`

这些文档仍然有价值，因为它们记录了设计边界和演进思路；
但阅读时应优先参考当前实现，不应把其中的规划型 CLI 示例当成现状。

## 5. 下一步建议

### 5.1 面向 skill 的接口整理

下一阶段建议重点做：

- 将查询结果整理为更稳定的结构化接口；
- 明确“topic 级”“post 级”“related topic 级”输出；
- 设计给 skill 使用的高层 API，而不是直接暴露内部存储细节。

### 5.2 结构化导出

Markdown 仍然有价值，但后续更重要的是：

- topic 级 JSON
- post 级 JSONL
- 图片路径与引用关系的结构化输出

### 5.3 相关帖子发现

在本地缓存和查询能力稳定后，再进入：

- forum search / latest / tag 拉取
- 本地 related rules
- skill 侧的相关推荐能力
