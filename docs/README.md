# Docs 导航

这个目录现在分成三类：

- **当前有效文档**：今天就能照着运行
- **设计参考文档**：解释模块拆分和能力边界
- **历史规划文档**：记录演进过程，不作为当前实现权威说明

如果你只关心“现在怎么用”，建议按这个顺序读：

1. `SKILL.md`
2. `docs/RUNBOOK.md`
3. `references/runtime_layout.md`
4. `references/output_schema.md`
5. `references/troubleshooting.md`

## 一、当前有效文档

### `docs/RUNBOOK.md`

当前运行手册。适合认证、同步、查询、摘要、导出。

### `docs/SKILL_DESIGN.md`

说明这个仓库为什么直接作为一个 skill repo 来组织。

### `docs/EXPORT_IO_AND_RATE_LIMITING.md`

说明 `stdout/stderr` 机器输出契约，以及大帖限流和补拉策略。

### `docs/THREAD_POOL_REFACTOR_PLAN.md`

说明当前线程池并发设计、边界和后续可继续优化的点。

### `docs/REPO_REFACTOR_PLAN.md`

说明仓库如何从旧导出脚本演进到现在的 cache-first skill repo。

### `docs/DISCOURSE_SEARCH_API_RESEARCH.md`

整理 Discourse 官方搜索 API、Shuiyuan 实测行为，以及多跳搜索可行性。

## 二、设计参考文档

### `docs/SCHEMA_AND_API.md`

缓存结构、数据库与接口契约的设计参考。

### `docs/SYSTEM_DESIGN.md`

系统级详细设计，适合维护者理解模块分层。

## 三、历史规划文档

这些文档已经收进 `docs/history/`，建议按“历史稿”阅读：

- `docs/history/TECHNICAL_PLAN.md`
- `docs/history/IMPLEMENTATION_ROADMAP.md`
- `docs/history/PHASE1_EXECUTION_SPEC.md`
- `docs/history/PHASE2_EXECUTION_SPEC.md`
- `docs/history/PHASE2_QUERY_ANALYSIS_DESIGN.md`

它们的价值主要在于记录：

- 当时的阶段目标
- 设计边界
- 演进顺序
- 为什么系统最后长成现在这样

如果和当前代码不一致，请优先相信：

1. `SKILL.md`
2. `references/*.md`
3. `docs/RUNBOOK.md`
4. 实际代码

## 四、维护者建议阅读顺序

1. `docs/README.md`
2. `docs/RUNBOOK.md`
3. `docs/SKILL_DESIGN.md`
4. `docs/EXPORT_IO_AND_RATE_LIMITING.md`
5. `docs/THREAD_POOL_REFACTOR_PLAN.md`
6. `docs/REPO_REFACTOR_PLAN.md`
7. `docs/SCHEMA_AND_API.md`
8. `docs/SYSTEM_DESIGN.md`
9. `docs/history/*`
