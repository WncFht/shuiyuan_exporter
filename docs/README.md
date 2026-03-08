# Docs 导航

这份目录主要包含两类内容：

- **当前可执行文档**：用于今天就能运行、排障、维护 skill
- **设计 / 历史文档**：用于理解系统演进、设计边界和历史决策

如果你只想知道“现在怎么用”，请优先读：

1. `docs/RUNBOOK.md`
2. `docs/SKILL_DESIGN.md`
3. `docs/THREAD_POOL_REFACTOR_PLAN.md`
4. `references/runtime_layout.md`
5. `references/output_schema.md`
6. `references/troubleshooting.md`

## 一、当前文档

### `docs/RUNBOOK.md`

用途：当前仓库的运行手册。  
适合场景：认证、同步、查询、摘要、导出。  
优先级：**最高**。

### `docs/SKILL_DESIGN.md`

用途：当前 skill 仓库形态、职责边界、能力范围说明。  
适合场景：理解这个仓库为什么直接就是一个 skill repo。  
优先级：高。

### `docs/THREAD_POOL_REFACTOR_PLAN.md`

用途：当前并发改造方案与已执行内容说明。  
适合场景：理解为什么现在用了线程池、哪些地方仍保持单线程。  
优先级：高。

### `docs/REPO_REFACTOR_PLAN.md`

用途：仓库从“旧导出脚本”演进到“cache-first skill repo”的收口过程说明。  
适合场景：想理解当前目录结构为什么长这样。  
优先级：中。

## 二、设计参考文档

### `docs/SCHEMA_AND_API.md`

用途：缓存结构、接口契约、命名规则的设计参考。  
说明：当前部分内容已实现，但应以代码与 `docs/RUNBOOK.md` 为准。

### `docs/SYSTEM_DESIGN.md`

用途：系统级详细设计参考。  
说明：适合深入理解模块拆分与设计意图，但不是最直接的使用文档。

## 三、历史规划文档

这些文档建议按“历史稿”理解，不应直接当成当前实现说明：

- `docs/IMPLEMENTATION_ROADMAP.md`
- `docs/PHASE1_EXECUTION_SPEC.md`
- `docs/PHASE2_EXECUTION_SPEC.md`
- `docs/PHASE2_QUERY_ANALYSIS_DESIGN.md`

它们仍然有价值，因为记录了：

- 设计边界
- 阶段目标
- 当时的实现顺序
- 为什么系统最后长成现在这样

但如果文中描述和当前代码不一致，请优先相信：

1. `SKILL.md`
2. `references/*.md`
3. `docs/RUNBOOK.md`
4. 实际代码

## 四、建议阅读顺序

### 如果你是“使用者”

按这个顺序：

1. `SKILL.md`
2. `references/runtime_layout.md`
3. `docs/RUNBOOK.md`
4. `references/output_schema.md`
5. `references/troubleshooting.md`

### 如果你是“维护者”

按这个顺序：

1. `docs/README.md`
2. `docs/RUNBOOK.md`
3. `docs/SKILL_DESIGN.md`
4. `docs/THREAD_POOL_REFACTOR_PLAN.md`
5. `docs/REPO_REFACTOR_PLAN.md`
6. `docs/SCHEMA_AND_API.md`
7. `docs/SYSTEM_DESIGN.md`

## 五、当前 skill 相关权威文件

`docs/` 不是 skill 的唯一说明来源。当前最关键的 skill 文件是：

- `SKILL.md`：skill 触发与核心 workflow
- `agents/openai.yaml`：UI 元数据
- `references/runtime_layout.md`：运行时路径与缓存结构
- `references/output_schema.md`：脚本输出约定
- `references/troubleshooting.md`：排障说明

简单说：

- `docs/` 偏“设计与整理”
- `references/` 偏“给 skill 运行时直接查阅”
